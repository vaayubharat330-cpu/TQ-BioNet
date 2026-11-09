"""
Tests for Stage 6F threshold optimization, nested selection, and paired evaluation.
"""

import numpy as np
import pytest
from stage6f_specificity_optimization import (
    sweep_thresholds,
    select_policy_threshold,
    evaluate_true_nested_scan_grouped_validation,
    paired_scan_cluster_threshold_comparison
)
import stage6f_specificity_optimization as s6f


def test_sweep_thresholds_monotonicity():
    y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    probs = np.array([0.9, 0.8, 0.6, 0.4, 0.5, 0.3, 0.2, 0.1])
    df = sweep_thresholds(y_true, probs, t_min=0.1, t_max=0.9, n_steps=9)

    assert len(df) == 9
    # Sensitivity should be monotonically non-increasing
    sens_diffs = np.diff(df["sensitivity"].to_numpy())
    assert np.all(sens_diffs <= 1e-7)
    # Specificity should be monotonically non-decreasing
    spec_diffs = np.diff(df["specificity"].to_numpy())
    assert np.all(spec_diffs >= -1e-7)


def test_select_policy_threshold_sens80():
    # 5 positives, 5 negatives
    y_true = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    # Probs: pos = [0.95, 0.85, 0.75, 0.65, 0.40], neg = [0.60, 0.50, 0.30, 0.20, 0.10]
    probs = np.array([0.95, 0.85, 0.75, 0.65, 0.40, 0.60, 0.50, 0.30, 0.20, 0.10])
    
    # 4/5 = 80% sensitivity requires including at least 4 positives (probs >= 0.65)
    t_opt = select_policy_threshold(y_true, probs, criterion="sens_80", t_min=0.2, t_max=0.8, n_steps=31)
    
    pred = (probs >= t_opt).astype(int)
    sens = np.sum((y_true == 1) & (pred == 1)) / 5.0
    assert sens >= 0.80 - 1e-5


def test_select_policy_threshold_youden():
    y_true = np.array([1, 1, 1, 0, 0, 0])
    probs = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
    # Clear separation at t ~ 0.50 giving J = 1.0 (Sens=1, Spec=1)
    t_opt = select_policy_threshold(y_true, probs, criterion="youden", t_min=0.2, t_max=0.8, n_steps=31)
    pred = (probs >= t_opt).astype(int)
    sens = np.sum((y_true == 1) & (pred == 1)) / 3.0
    spec = np.sum((y_true == 0) & (pred == 0)) / 3.0
    assert sens == 1.0
    assert spec == 1.0
    assert (sens + spec - 1.0) == pytest.approx(1.0)


def test_true_nested_scan_grouped_validation_leak_free():
    # Construct 3 folds of synthetic 15-feature data
    np.random.seed(42)
    n_per_fold = 20
    X_f0 = np.random.randn(n_per_fold, 15)
    X_f1 = np.random.randn(n_per_fold, 15)
    X_f2 = np.random.randn(n_per_fold, 15)
    
    # Make feature 0 strongly predictive
    y_f0 = (X_f0[:, 0] > 0).astype(int)
    y_f1 = (X_f1[:, 0] > 0).astype(int)
    y_f2 = (X_f2[:, 0] > 0).astype(int)

    X_dev = np.vstack([X_f0, X_f1, X_f2])
    y_dev = np.concatenate([y_f0, y_f1, y_f2])
    folds_dev = np.array(["Fold0"] * n_per_fold + ["Fold1"] * n_per_fold + ["Fold2"] * n_per_fold)

    res = evaluate_true_nested_scan_grouped_validation(X_dev, y_dev, folds_dev, criterion="sens_80")
    assert "inner_thresholds_per_fold" in res
    assert len(res["inner_thresholds_per_fold"]) == 3
    assert 0.0 <= res["nested_sensitivity"] <= 1.0
    assert 0.0 <= res["nested_specificity"] <= 1.0
    assert res["nested_accuracy"] > 0.5


def test_nested_validation_leak_free_recording(monkeypatch):
    """
    Explicitly instruments fit_ensemble_predict_probabilities to verify:
    1. Zero outer-fold rows are passed to any inner training model.
    2. Zero outer-fold rows are passed to inner threshold selection.
    3. The outer model is trained strictly using only the two inner folds.
    4. X_train and X_eval are strictly disjoint on every invocation.
    """
    n_per_fold = 15
    np.random.seed(101)
    
    # Embed unique row index in column 0 of X
    total_samples = 3 * n_per_fold
    row_ids = np.arange(total_samples, dtype=float)
    X_mat = np.random.randn(total_samples, 15)
    X_mat[:, 0] = row_ids
    y_arr = np.random.randint(0, 2, size=total_samples)
    
    fold_names = ["Fold0"] * n_per_fold + ["Fold1"] * n_per_fold + ["Fold2"] * n_per_fold
    folds_arr = np.array(fold_names)

    # Track calls to fit_ensemble_predict_probabilities
    recorded_calls = []
    original_fit = s6f.fit_ensemble_predict_probabilities

    def recording_wrapper(X_train, y_train, X_eval):
        train_ids = set(X_train[:, 0].astype(int))
        eval_ids = set(X_eval[:, 0].astype(int))
        recorded_calls.append({
            "train_ids": train_ids,
            "eval_ids": eval_ids,
            "train_size": len(train_ids),
            "eval_size": len(eval_ids)
        })
        return original_fit(X_train, y_train, X_eval)

    monkeypatch.setattr(s6f, "fit_ensemble_predict_probabilities", recording_wrapper)

    res = evaluate_true_nested_scan_grouped_validation(X_mat, y_arr, folds_arr, criterion="sens_80")

    # There should be exactly 9 calls: 3 outer loops * (2 inner CV calls + 1 outer train call)
    assert len(recorded_calls) == 9

    fold_id_map = {
        "Fold0": set(range(0, 15)),
        "Fold1": set(range(15, 30)),
        "Fold2": set(range(30, 45))
    }

    # Verify each outer loop of 3 calls:
    for loop_idx, outer_fold in enumerate(["Fold0", "Fold1", "Fold2"]):
        outer_ids = fold_id_map[outer_fold]
        inner_folds = [f for f in ["Fold0", "Fold1", "Fold2"] if f != outer_fold]
        inner_ids_A = fold_id_map[inner_folds[0]]
        inner_ids_B = fold_id_map[inner_folds[1]]
        all_inner_ids = inner_ids_A | inner_ids_B

        call_inner1 = recorded_calls[loop_idx * 3]
        call_inner2 = recorded_calls[loop_idx * 3 + 1]
        call_outer = recorded_calls[loop_idx * 3 + 2]

        # 1. Inner call 1: train on B, eval on A (zero outer ids)
        assert len(call_inner1["train_ids"] & outer_ids) == 0, f"Outer fold {outer_fold} leaked into inner train 1"
        assert len(call_inner1["eval_ids"] & outer_ids) == 0, f"Outer fold {outer_fold} leaked into inner eval 1"
        assert call_inner1["train_ids"] == inner_ids_B
        assert call_inner1["eval_ids"] == inner_ids_A

        # 2. Inner call 2: train on A, eval on B (zero outer ids)
        assert len(call_inner2["train_ids"] & outer_ids) == 0, f"Outer fold {outer_fold} leaked into inner train 2"
        assert len(call_inner2["eval_ids"] & outer_ids) == 0, f"Outer fold {outer_fold} leaked into inner eval 2"
        assert call_inner2["train_ids"] == inner_ids_A
        assert call_inner2["eval_ids"] == inner_ids_B

        # 3. Outer call: train on all inner (A+B), eval on outer
        assert len(call_outer["train_ids"] & outer_ids) == 0, f"Outer fold {outer_fold} leaked into outer train"
        assert call_outer["train_ids"] == all_inner_ids, "Outer model was not trained strictly on all inner data"
        assert call_outer["eval_ids"] == outer_ids, "Outer model did not evaluate on outer fold"

        # 4. Strict disjointness on all calls
        for c in [call_inner1, call_inner2, call_outer]:
            assert len(c["train_ids"] & c["eval_ids"]) == 0, "Disjointness violated between train and eval"


def test_paired_scan_cluster_threshold_comparison_reproducibility():
    y_true = np.array([1, 1, 0, 0, 1, 0])
    pred_pol = np.array([1, 0, 0, 0, 1, 0])  # Sens = 2/3, Spec = 3/3 = 1.0
    pred_base = np.array([1, 1, 1, 0, 1, 1]) # Sens = 3/3, Spec = 1/3 = 0.33
    groups = np.array(["scanA", "scanA", "scanB", "scanB", "scanC", "scanC"])

    comp1 = paired_scan_cluster_threshold_comparison(y_true, pred_pol, pred_base, groups, n_bootstrap=500, seed=123)
    comp2 = paired_scan_cluster_threshold_comparison(y_true, pred_pol, pred_base, groups, n_bootstrap=500, seed=123)

    assert comp1["specificity_delta"]["observed"] == pytest.approx(comp2["specificity_delta"]["observed"])
    assert comp1["specificity_delta"]["observed"] > 0.5  # Specificity clearly improved
    assert comp1["sensitivity_delta"]["observed"] < 0.0  # Sensitivity decreased
    assert comp1["specificity_delta"]["scan_cluster_95ci"] == comp2["specificity_delta"]["scan_cluster_95ci"]
