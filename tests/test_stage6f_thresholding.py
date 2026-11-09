"""
Tests for Stage 6F threshold optimization, nested selection, and paired evaluation.
"""

import numpy as np
import pytest
from stage6f_specificity_optimization import (
    sweep_thresholds,
    select_policy_threshold,
    evaluate_nested_grouped_thresholds,
    paired_scan_cluster_threshold_comparison
)


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


def test_nested_grouped_thresholds_no_outer_leakage():
    # Construct 3 folds with different distribution patterns
    y_dev = np.array([
        1, 1, 0, 0,   # Fold0
        1, 1, 0, 0,   # Fold1
        1, 1, 0, 0    # Fold2
    ])
    probs_dev = np.array([
        0.8, 0.7, 0.3, 0.2,
        0.85, 0.75, 0.25, 0.15,
        0.9, 0.65, 0.35, 0.1
    ])
    folds_dev = np.array([
        "Fold0", "Fold0", "Fold0", "Fold0",
        "Fold1", "Fold1", "Fold1", "Fold1",
        "Fold2", "Fold2", "Fold2", "Fold2"
    ])

    res = evaluate_nested_grouped_thresholds(y_dev, probs_dev, folds_dev, criterion="sens_80")
    assert "inner_thresholds_per_fold" in res
    assert len(res["inner_thresholds_per_fold"]) == 3
    assert res["nested_sensitivity"] >= 0.80 - 1e-5
    assert res["nested_accuracy"] > 0.5


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
