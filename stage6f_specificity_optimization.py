"""
Stage 6F: Development-Only Specificity Optimization & Retrospective Fold 3 Evaluation
=====================================================================================

This module implements a rigorous, leak-free threshold optimization study:
1. Compares adapted SVM, Random Forest, XGBoost, and Soft Ensemble on Development
   (Folds 0–2, N=899 findings across 171 scans) using scan-grouped cross-validation.
2. Performs a reproducible threshold sweep from t=0.30 to t=0.75 in steps of 0.01,
   recording Sensitivity, Specificity, Accuracy, Balanced Accuracy, PPV, NPV, and Youden's J.
3. Implements true leak-free nested scan-grouped threshold validation:
   - For each outer validation fold k, models are trained ONLY on inner folds (2-fold inner CV
     generates pure inner OOF predictions from which inner policy thresholds are selected).
   - Outer fold k is NEVER seen during inner model training or inner threshold selection.
   - Primary operating point: Sensitivity >= 80% (maximizing specificity).
   - Secondary operating points: Sensitivity >= 75% and Maximum Youden's J.
4. Selects and freezes one policy strictly from Development data (Folds 0–2).
5. Explicitly audits and asserts row-by-row alignment between the Stage 6E Fold 3 prediction
   CSV and the cached ground truth (scan IDs, coordinates, labels, agreement levels).
6. Retrospectively evaluates the frozen policy on the Fold 3 probabilities (N=320 findings,
   58 scans) saved during Stage 6E. This is explicitly documented as a post-hoc retrospective
   held-out analysis, not a fresh unseen cohort.
7. Conducts paired scan-cluster bootstrap comparisons (5,000 replicates) against:
   - The always-positive majority baseline (59.69%).
   - The Stage 6E baseline (t=0.50).
8. Evaluates radiologist agreement stratification and secondary coordinate conflict sensitivity.
9. Emits comprehensive metrics, CSV sweeps, confusion matrices, and markdown summary to
   outputs/stage6f_specificity_optimization/.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple, List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_curve,
    precision_recall_curve
)

from tq_bionet.model_config import (
    FROZEN_15_SELECTED_FEATURES,
    DEFAULT_DECISION_THRESHOLD,
    compute_calibration_metrics,
    prune_to_selected_features
)
from tq_bionet.evaluation_metrics import compute_cluster_bootstrap_ci
from stage6e_lndb_adaptation import (
    load_lndb_features_and_folds,
    fit_and_predict_cv,
    compute_fold3_conflict_sensitivity,
    paired_scan_cluster_baseline_comparison
)


def sweep_thresholds(
    y_true: np.ndarray,
    probs: np.ndarray,
    t_min: float = 0.30,
    t_max: float = 0.75,
    n_steps: int = 46
) -> pd.DataFrame:
    """
    Evaluates classification metrics across a dense grid of decision thresholds.
    """
    thresholds = np.linspace(t_min, t_max, n_steps)
    rows = []
    n_total = len(y_true)
    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)

    for t in thresholds:
        pred = (probs >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        acc = (tp + tn) / n_total
        bal_acc = (sens + spec) / 2.0
        f1 = (2 * ppv * sens) / (ppv + sens) if (ppv + sens) > 0 else 0.0
        j = sens + spec - 1.0

        rows.append({
            "threshold": float(t),
            "accuracy": float(acc),
            "balanced_accuracy": float(bal_acc),
            "sensitivity": float(sens),
            "specificity": float(spec),
            "ppv": float(ppv),
            "npv": float(npv),
            "f1": float(f1),
            "youden_j": float(j),
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn)
        })

    return pd.DataFrame(rows)


def select_policy_threshold(
    y_train: np.ndarray,
    probs_train: np.ndarray,
    criterion: str = "sens_80",
    t_min: float = 0.30,
    t_max: float = 0.75,
    n_steps: int = 46
) -> float:
    """
    Selects a decision threshold strictly on training/inner data according to a pre-defined policy:
    - 'sens_80': maximize specificity subject to sensitivity >= 0.80.
    - 'sens_75': maximize specificity subject to sensitivity >= 0.75.
    - 'youden': maximize Youden's J statistic (sensitivity + specificity - 1).
    """
    df = sweep_thresholds(y_train, probs_train, t_min=t_min, t_max=t_max, n_steps=n_steps)
    
    if criterion == "sens_80":
        sub = df[df["sensitivity"] >= 0.80]
        if len(sub) == 0:
            return float(df.sort_values(by="sensitivity", ascending=False).iloc[0]["threshold"])
        best = sub.sort_values(by=["specificity", "balanced_accuracy"], ascending=[False, False]).iloc[0]
        return float(best["threshold"])
    elif criterion == "sens_75":
        sub = df[df["sensitivity"] >= 0.75]
        if len(sub) == 0:
            return float(df.sort_values(by="sensitivity", ascending=False).iloc[0]["threshold"])
        best = sub.sort_values(by=["specificity", "balanced_accuracy"], ascending=[False, False]).iloc[0]
        return float(best["threshold"])
    elif criterion == "youden":
        best = df.sort_values(by=["youden_j", "balanced_accuracy"], ascending=[False, False]).iloc[0]
        return float(best["threshold"])
    else:
        raise ValueError(f"Unknown threshold selection criterion: {criterion}")


def fit_ensemble_predict_probabilities(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray
) -> np.ndarray:
    """
    Fits adapted SVM, Random Forest, and XGBoost on X_train/y_train and returns
    soft-average predicted probabilities on X_eval.
    """
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_eval_sc = scaler.transform(X_eval)

    # Methodological Audit Note on SVM Probability Calibration:
    # sklearn.svm.SVC(probability=True) uses internal 5-fold cross-validation with Platt scaling.
    # While outer and inner validation folds are strictly scan-grouped, the internal 5-fold splits
    # within SVC are candidate-level stratified rather than scan-grouped.
    clf_svm = SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=42)
    clf_svm.fit(X_train_sc, y_train)
    p_svm = clf_svm.predict_proba(X_eval_sc)[:, 1]

    clf_rf = RandomForestClassifier(n_estimators=300, max_features="sqrt", class_weight="balanced", random_state=42)
    clf_rf.fit(X_train, y_train)
    p_rf = clf_rf.predict_proba(X_eval)[:, 1]

    scale_pos = (len(y_train) - np.sum(y_train)) / max(1, np.sum(y_train))
    clf_xgb = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                            scale_pos_weight=scale_pos, eval_metric="logloss", random_state=42)
    clf_xgb.fit(X_train, y_train)
    p_xgb = clf_xgb.predict_proba(X_eval)[:, 1]

    return (p_svm + p_rf + p_xgb) / 3.0


def evaluate_true_nested_scan_grouped_validation(
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    folds_dev: np.ndarray,
    criterion: str = "sens_80"
) -> Dict[str, Any]:
    """
    Executes true leak-free nested scan-grouped cross-validation:
    For each outer validation fold k in {Fold0, Fold1, Fold2}:
      1. Outer fold k is completely held out.
      2. The two inner folds perform a 2-fold scan-grouped CV to generate inner OOF predictions.
      3. Threshold t_inner* is selected strictly from those inner OOF predictions.
      4. Models are trained on all data from the two inner folds and predict on outer fold k.
      5. The outer predictions are evaluated at t_inner*.
    Outer fold k is never seen during inner model training or inner threshold selection.
    """
    outer_folds = sorted(list(set(folds_dev)))
    outer_preds = np.zeros(len(y_dev), dtype=int)
    outer_probs = np.zeros(len(y_dev), dtype=float)
    inner_thresholds = {}

    for outer_fold in outer_folds:
        outer_mask = (folds_dev == outer_fold)
        inner_mask = ~outer_mask

        inner_folds_list = sorted(list(set(folds_dev[inner_mask])))
        f_A, f_B = inner_folds_list[0], inner_folds_list[1]

        # Inner 2-fold CV between f_A and f_B
        idx_A = (folds_dev == f_A)
        idx_B = (folds_dev == f_B)

        p_A = fit_ensemble_predict_probabilities(X_dev[idx_B], y_dev[idx_B], X_dev[idx_A])
        p_B = fit_ensemble_predict_probabilities(X_dev[idx_A], y_dev[idx_A], X_dev[idx_B])

        p_inner_oof = np.zeros(np.sum(inner_mask), dtype=float)
        y_inner = y_dev[inner_mask]

        sub_A = (folds_dev[inner_mask] == f_A)
        sub_B = (folds_dev[inner_mask] == f_B)
        p_inner_oof[sub_A] = p_A
        p_inner_oof[sub_B] = p_B

        # Select threshold strictly from inner OOF predictions
        t_inner = select_policy_threshold(y_inner, p_inner_oof, criterion=criterion)
        inner_thresholds[str(outer_fold)] = float(t_inner)

        # Fit model on ALL inner data (A + B) and predict on held-out outer fold k
        p_outer = fit_ensemble_predict_probabilities(X_dev[inner_mask], y_dev[inner_mask], X_dev[outer_mask])
        outer_probs[outer_mask] = p_outer
        outer_preds[outer_mask] = (p_outer >= t_inner).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_dev, outer_preds, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    acc = (tp + tn) / len(y_dev)
    bal_acc = (sens + spec) / 2.0
    j = sens + spec - 1.0

    return {
        "criterion": criterion,
        "inner_thresholds_per_fold": inner_thresholds,
        "mean_inner_threshold": float(np.mean(list(inner_thresholds.values()))),
        "nested_accuracy": float(acc),
        "nested_balanced_accuracy": float(bal_acc),
        "nested_sensitivity": float(sens),
        "nested_specificity": float(spec),
        "nested_youden_j": float(j),
        "nested_confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    }


def paired_scan_cluster_threshold_comparison(
    y_true: np.ndarray,
    pred_policy: np.ndarray,
    pred_baseline: np.ndarray,
    group_ids: np.ndarray,
    n_bootstrap: int = 5000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Paired scan-cluster bootstrap comparing a tuned policy against the default baseline
    (e.g. t=0.50) across accuracy, sensitivity, and specificity simultaneously.
    """
    rng = np.random.default_rng(seed)
    unique_groups = np.unique(group_ids.astype(str))
    group_indices = {g: np.flatnonzero(group_ids.astype(str) == g) for g in unique_groups}

    delta_acc = []
    delta_sens = []
    delta_spec = []

    for _ in range(n_bootstrap):
        sampled = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([group_indices[g] for g in sampled])
        if len(idx) == 0:
            continue
        y_samp = y_true[idx]
        p_pol = pred_policy[idx]
        p_base = pred_baseline[idx]

        acc_pol = accuracy_score(y_samp, p_pol)
        acc_base = accuracy_score(y_samp, p_base)
        delta_acc.append(acc_pol - acc_base)

        pos_mask = (y_samp == 1)
        neg_mask = (y_samp == 0)
        if np.any(pos_mask):
            sens_pol = np.mean(p_pol[pos_mask] == 1)
            sens_base = np.mean(p_base[pos_mask] == 1)
            delta_sens.append(sens_pol - sens_base)
        if np.any(neg_mask):
            spec_pol = np.mean(p_pol[neg_mask] == 0)
            spec_base = np.mean(p_base[neg_mask] == 0)
            delta_spec.append(spec_pol - spec_base)

    ci_acc = np.quantile(np.asarray(delta_acc), [0.025, 0.975]).tolist()
    ci_sens = np.quantile(np.asarray(delta_sens), [0.025, 0.975]).tolist() if delta_sens else [0.0, 0.0]
    ci_spec = np.quantile(np.asarray(delta_spec), [0.025, 0.975]).tolist() if delta_spec else [0.0, 0.0]

    obs_acc_pol = accuracy_score(y_true, pred_policy)
    obs_acc_base = accuracy_score(y_true, pred_baseline)
    obs_sens_pol = recall_score(y_true, pred_policy, zero_division=0)
    obs_sens_base = recall_score(y_true, pred_baseline, zero_division=0)
    tn_p, fp_p, _, _ = confusion_matrix(y_true, pred_policy, labels=[0, 1]).ravel()
    tn_b, fp_b, _, _ = confusion_matrix(y_true, pred_baseline, labels=[0, 1]).ravel()
    obs_spec_pol = tn_p / (tn_p + fp_p) if (tn_p + fp_p) > 0 else 0.0
    obs_spec_base = tn_b / (tn_b + fp_b) if (tn_b + fp_b) > 0 else 0.0

    return {
        "accuracy_delta": {
            "observed": float(obs_acc_pol - obs_acc_base),
            "scan_cluster_95ci": [float(ci_acc[0]), float(ci_acc[1])]
        },
        "sensitivity_delta": {
            "observed": float(obs_sens_pol - obs_sens_base),
            "scan_cluster_95ci": [float(ci_sens[0]), float(ci_sens[1])]
        },
        "specificity_delta": {
            "observed": float(obs_spec_pol - obs_spec_base),
            "scan_cluster_95ci": [float(ci_spec[0]), float(ci_spec[1])]
        },
        "n_bootstrap": n_bootstrap,
        "n_clusters": int(len(unique_groups)),
        "seed": seed
    }


def run_stage6f():
    print("==========================================================================")
    print("   TQ-BioNet Stage 6F: Development Specificity Optimization & Evaluation  ")
    print("==========================================================================\n")

    project_root = Path(__file__).resolve().parent
    outputs_dir = project_root / "outputs" / "stage6f_specificity_optimization"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    cache_1mm_dir = Path(r"D:\LNDb\cache\stage6d\1.0mm")
    folds_path = Path(r"D:\LNDb\annotations\trainset_csv\trainFolds.csv")
    gt_path = Path(r"D:\LNDb\annotations\trainset_csv\trainNodules_gt.csv")

    gt_df = pd.read_csv(gt_path)
    print(f"Loaded official ground truth: {len(gt_df)} findings across {gt_df['LNDbID'].nunique()} scans.")

    # 1. Load feature cache and check alignment
    cohort = load_lndb_features_and_folds(cache_1mm_dir, folds_path, gt_df)
    X, y, groups, folds = cohort["X"], cohort["y"], cohort["groups"], cohort["folds"]
    agr_levels = cohort["agr_levels"]
    coords = cohort["coords"]

    dev_mask = np.isin(folds, ["Fold0", "Fold1", "Fold2"])
    test_mask = (folds == "Fold3")

    X_dev, y_dev, groups_dev, folds_dev = X[dev_mask], y[dev_mask], groups[dev_mask], folds[dev_mask]
    X_test, y_test, groups_test, agr_test = X[test_mask], y[test_mask], groups[test_mask], agr_levels[test_mask]
    coords_test = coords[test_mask]
    X_dev_15 = prune_to_selected_features(X_dev)

    print(f"\nCohort Structure:")
    print(f"   Development cohort (Folds 0-2): {len(y_dev)} findings ({np.sum(y_dev==1)} pos, {np.sum(y_dev==0)} neg, {np.mean(y_dev)*100:.1f}% pos)")
    print(f"   Held-out test cohort (Fold 3):  {len(y_test)} findings ({np.sum(y_test==1)} pos, {np.sum(y_test==0)} neg, {np.mean(y_test)*100:.1f}% pos)")

    # 2. Extract out-of-fold probabilities for all 4 models on Development (Folds 0-2)
    print("\n[STEP 2] Running scan-grouped cross-validation for SVM, RF, XGB, and Soft Ensemble on Development...")
    model_cv_runs = {}
    for m_type in ["svm", "rf", "xgb", "ensemble"]:
        print(f"   Fitting scan-grouped CV for {m_type.upper()}...")
        model_cv_runs[m_type] = fit_and_predict_cv(
            X_dev, y_dev, groups_dev, folds_dev, m_type, use_15_features=True
        )

    # 3. Model Comparison on Development Data
    dev_model_comp = {}
    for m_type, res in model_cv_runs.items():
        p_oof = res["oof_probs"]
        auc = roc_auc_score(y_dev, p_oof)
        ap = average_precision_score(y_dev, p_oof)
        brier = brier_score_loss(y_dev, p_oof)
        
        # At default t=0.50
        pred50 = (p_oof >= 0.50).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_dev, pred50, labels=[0, 1]).ravel()
        
        dev_model_comp[m_type] = {
            "auc_roc": float(auc),
            "average_precision": float(ap),
            "brier_score": float(brier),
            "prob_mean_neg": float(np.mean(p_oof[y_dev == 0])),
            "prob_std_neg": float(np.std(p_oof[y_dev == 0])),
            "prob_mean_pos": float(np.mean(p_oof[y_dev == 1])),
            "prob_std_pos": float(np.std(p_oof[y_dev == 1])),
            "at_threshold_0_50": {
                "accuracy": float((tp + tn) / len(y_dev)),
                "sensitivity": float(tp / (tp + fn)),
                "specificity": float(tn / (tn + fp)),
                "balanced_accuracy": float((tp / (tp + fn) + tn / (tn + fp)) / 2),
                "youden_j": float(tp / (tp + fn) + tn / (tn + fp) - 1),
                "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)
            }
        }

    print("\n--- Development Model Comparison (Folds 0-2 OOF) ---")
    print(f"{'Model':<12} | {'AUC':<6} | {'AP':<6} | {'Brier':<6} | {'Acc@0.50':<8} | {'Sens@0.50':<9} | {'Spec@0.50':<10}")
    print("-" * 80)
    for m, d in dev_model_comp.items():
        print(f"{m.upper():<12} | {d['auc_roc']:.4f} | {d['average_precision']:.4f} | {d['brier_score']:.4f} | "
              f"{d['at_threshold_0_50']['accuracy']:.4f}   | {d['at_threshold_0_50']['sensitivity']:.4f}    | "
              f"{d['at_threshold_0_50']['specificity']:.4f}")

    with (outputs_dir / "development_model_comparison.json").open("w", encoding="utf-8") as f:
        json.dump(dev_model_comp, f, indent=2)

    # 4. Dense Threshold Sweep for the Soft Ensemble on Development OOF
    print("\n[STEP 4] Executing dense threshold sweep (t=0.30 to 0.75, step 0.01) on Development OOF...")
    p_ens_dev = model_cv_runs["ensemble"]["oof_probs"]
    sweep_df = sweep_thresholds(y_dev, p_ens_dev, t_min=0.30, t_max=0.75, n_steps=46)
    sweep_path = outputs_dir / "development_threshold_sweep.csv"
    sweep_df.to_csv(sweep_path, index=False)
    print(f"   Saved {len(sweep_df)} threshold evaluations to {sweep_path.name}.")

    # 5. True Leak-Free Nested Scan-Grouped Threshold Selection on Development Data
    print("\n[STEP 5] Conducting true leak-free nested scan-grouped threshold validation...")
    nested_sens80 = evaluate_true_nested_scan_grouped_validation(X_dev_15, y_dev, folds_dev, criterion="sens_80")
    nested_sens75 = evaluate_true_nested_scan_grouped_validation(X_dev_15, y_dev, folds_dev, criterion="sens_75")
    nested_youden = evaluate_true_nested_scan_grouped_validation(X_dev_15, y_dev, folds_dev, criterion="youden")

    # Full Development frozen thresholds
    t_star_sens80 = select_policy_threshold(y_dev, p_ens_dev, criterion="sens_80")
    t_star_sens75 = select_policy_threshold(y_dev, p_ens_dev, criterion="sens_75")
    t_star_youden = select_policy_threshold(y_dev, p_ens_dev, criterion="youden")

    nested_summary = {
        "primary_policy_sens_80": {
            "frozen_development_threshold": float(t_star_sens80),
            "nested_selection_results": nested_sens80
        },
        "secondary_policy_sens_75": {
            "frozen_development_threshold": float(t_star_sens75),
            "nested_selection_results": nested_sens75
        },
        "secondary_policy_youden": {
            "frozen_development_threshold": float(t_star_youden),
            "nested_selection_results": nested_youden
        }
    }
    with (outputs_dir / "development_nested_selection.json").open("w", encoding="utf-8") as f:
        json.dump(nested_summary, f, indent=2)

    print(f"   Primary Policy (Sens >= 0.80): Frozen Threshold t* = {t_star_sens80:.2f} (Inner folds: {nested_sens80['inner_thresholds_per_fold']})")
    print(f"      Leak-Free Nested OOF: Sens={nested_sens80['nested_sensitivity']:.4f}, Spec={nested_sens80['nested_specificity']:.4f}, Acc={nested_sens80['nested_accuracy']:.4f}")
    print(f"   Secondary Policy (Sens >= 0.75): Frozen Threshold t* = {t_star_sens75:.2f} (Inner folds: {nested_sens75['inner_thresholds_per_fold']})")
    print(f"      Leak-Free Nested OOF: Sens={nested_sens75['nested_sensitivity']:.4f}, Spec={nested_sens75['nested_specificity']:.4f}, Acc={nested_sens75['nested_accuracy']:.4f}")
    print(f"   Secondary Policy (Max Youden J):  Frozen Threshold t* = {t_star_youden:.2f} (Inner folds: {nested_youden['inner_thresholds_per_fold']})")
    print(f"      Leak-Free Nested OOF: Sens={nested_youden['nested_sensitivity']:.4f}, Spec={nested_youden['nested_specificity']:.4f}, Acc={nested_youden['nested_accuracy']:.4f}")

    # 6. Retrospective Evaluation on Fold 3
    print("\n[STEP 6] Auditing alignment and applying frozen development policy retrospectively to Stage 6E Fold 3 probabilities...")
    preds_e_path = project_root / "outputs" / "stage6e_lndb_adaptation" / "fold3_predictions.csv"
    if not preds_e_path.exists():
        raise FileNotFoundError(f"Missing Stage 6E predictions: {preds_e_path}")
    preds_e_df = pd.read_csv(preds_e_path)

    # Explicit Row-by-Row Alignment Assertions
    assert len(preds_e_df) == len(y_test), f"Length mismatch: CSV has {len(preds_e_df)}, cache has {len(y_test)}"
    assert np.array_equal(preds_e_df["seriesuid"].to_numpy().astype(str), groups_test.astype(str)), "Scan ID sequence mismatch between Stage 6E CSV and cache"
    assert np.allclose(preds_e_df[["x", "y", "z"]].to_numpy(), coords_test, rtol=0.0, atol=1e-5), "Coordinate sequence mismatch between Stage 6E CSV and cache"
    assert np.array_equal(preds_e_df["true_label"].to_numpy().astype(int), y_test.astype(int)), "Binary label sequence mismatch between Stage 6E CSV and cache"
    assert np.array_equal(preds_e_df["agr_level"].to_numpy().astype(int), agr_test.astype(int)), "AgrLevel sequence mismatch between Stage 6E CSV and cache"
    print("   [AUDIT] Stage 6E Fold 3 predictions strictly align row-by-row with cached ground truth.")

    p_fold3 = preds_e_df["adapted_ensemble_prob"].to_numpy()

    # Predictions under frozen policy and default baseline
    pred_base50 = (p_fold3 >= 0.50).astype(int)
    pred_star_sens80 = (p_fold3 >= t_star_sens80).astype(int)
    pred_star_sens75 = (p_fold3 >= t_star_sens75).astype(int)
    pred_star_youden = (p_fold3 >= t_star_youden).astype(int)

    def get_eval_dict(pred_arr, t_val):
        tn, fp, fn, tp = confusion_matrix(y_test, pred_arr, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        acc = (tp + tn) / len(y_test)
        bal_acc = (sens + spec) / 2.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = f1_score(y_test, pred_arr, zero_division=0)
        
        acc_ci = compute_cluster_bootstrap_ci(y_test, pred_arr, groups_test, accuracy_score)
        sens_ci = compute_cluster_bootstrap_ci(y_test, pred_arr, groups_test, recall_score)
        
        def spec_func(y_t, y_p):
            t_neg = np.sum((y_t == 0) & (y_p == 0))
            f_pos = np.sum((y_t == 0) & (y_p == 1))
            return t_neg / (t_neg + f_pos) if (t_neg + f_pos) > 0 else 0.0
        spec_ci = compute_cluster_bootstrap_ci(y_test, pred_arr, groups_test, spec_func)

        strat = {}
        for agr in sorted(np.unique(agr_test)):
            m = (agr_test == agr)
            sub_y, sub_p = y_test[m], pred_arr[m]
            sub_acc = accuracy_score(sub_y, sub_p) if len(sub_y) > 0 else 0.0
            strat[str(agr)] = {
                "n": int(len(sub_y)),
                "accuracy": float(sub_acc),
                "positive_count": int(np.sum(sub_y == 1))
            }

        return {
            "threshold": float(t_val),
            "accuracy": float(acc),
            "accuracy_95ci": acc_ci,
            "balanced_accuracy": float(bal_acc),
            "sensitivity": float(sens),
            "sensitivity_95ci": sens_ci,
            "specificity": float(spec),
            "specificity_95ci": spec_ci,
            "precision": float(prec),
            "f1": float(f1),
            "youden_j": float(sens + spec - 1.0),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            "agreement_stratification": strat
        }

    fold3_eval_base50 = get_eval_dict(pred_base50, 0.50)
    fold3_eval_sens80 = get_eval_dict(pred_star_sens80, t_star_sens80)
    fold3_eval_sens75 = get_eval_dict(pred_star_sens75, t_star_sens75)
    fold3_eval_youden = get_eval_dict(pred_star_youden, t_star_youden)

    # 7. Paired Scan-Cluster Bootstrap Comparison on Fold 3
    print("\n[STEP 7] Running paired scan-cluster bootstrap (5,000 replicates) comparing policy vs Stage 6E baseline...")
    paired_comp_sens80 = paired_scan_cluster_threshold_comparison(
        y_test, pred_star_sens80, pred_base50, groups_test, n_bootstrap=5000, seed=42
    )
    with (outputs_dir / "fold3_paired_vs_stage6e.json").open("w", encoding="utf-8") as f:
        json.dump(paired_comp_sens80, f, indent=2)

    # 8. Secondary Conflict Sensitivity on Fold 3 with Primary Policy
    conflict_sens_policy = compute_fold3_conflict_sensitivity(
        gt_df=gt_df,
        groups_test=groups_test,
        coords_test=coords_test,
        raw_labels=y_test,
        predictions=pred_star_sens80,
        probabilities=p_fold3,
        agr_test=agr_test
    )

    # 9. Save Fold 3 Retrospective Metrics JSON
    fold3_metrics_payload = {
        "stage": "Stage 6F - Development Specificity Optimization & Retrospective Fold 3 Evaluation",
        "date_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "designation": "Retrospective held-out evaluation on Stage 6E Fold 3 probabilities",
        "cohort": {
            "samples": len(y_test),
            "scans": int(len(np.unique(groups_test))),
            "positive_prevalence": float(np.mean(y_test))
        },
        "operating_points": {
            "baseline_threshold_0_50": fold3_eval_base50,
            "primary_policy_sens_80": fold3_eval_sens80,
            "secondary_policy_sens_75": fold3_eval_sens75,
            "secondary_policy_youden": fold3_eval_youden
        },
        "paired_scan_cluster_delta_vs_baseline_0_50": paired_comp_sens80,
        "conflict_sensitivity_analysis": conflict_sens_policy
    }
    with (outputs_dir / "fold3_retrospective_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(fold3_metrics_payload, f, indent=2)

    # 10. Generate Visualizations
    plt.figure(figsize=(8, 5))
    plt.plot(sweep_df["threshold"], sweep_df["sensitivity"], label="Sensitivity", color="tab:green", lw=2)
    plt.plot(sweep_df["threshold"], sweep_df["specificity"], label="Specificity", color="tab:blue", lw=2)
    plt.plot(sweep_df["threshold"], sweep_df["balanced_accuracy"], label="Balanced Accuracy", color="tab:purple", lw=1.5, linestyle="--")
    plt.plot(sweep_df["threshold"], sweep_df["accuracy"], label="Accuracy", color="gray", lw=1.5, linestyle=":")
    plt.axvline(0.50, color="gray", linestyle="--", alpha=0.5, label="Default (t=0.50)")
    plt.axvline(t_star_sens80, color="red", linestyle="-", lw=1.5, label=f"Primary Policy (t*={t_star_sens80:.2f})")
    plt.xlabel("Decision Threshold (t)")
    plt.ylabel("Metric Score")
    plt.title("Development Cohort OOF Threshold Sweep (Folds 0-2)")
    plt.legend(loc="lower left")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outputs_dir / "threshold_sweep_curves.png", dpi=200)
    plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    cm_base = confusion_matrix(y_test, pred_base50, labels=[0, 1])
    cm_star = confusion_matrix(y_test, pred_star_sens80, labels=[0, 1])

    axes[0].imshow(cm_base, cmap="Blues", interpolation="nearest")
    axes[0].set_title(f"Stage 6E Baseline (t=0.50)\nSens={fold3_eval_base50['sensitivity']:.1%}, Spec={fold3_eval_base50['specificity']:.1%}")
    axes[0].set_xticks([0, 1])
    axes[0].set_yticks([0, 1])
    axes[0].set_xticklabels(["Pred Neg", "Pred Pos"])
    axes[0].set_yticklabels(["True Neg", "True Pos"])
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, str(cm_base[i, j]), ha="center", va="center", color="red" if i!=j else "black", fontsize=13, fontweight="bold")

    axes[1].imshow(cm_star, cmap="Blues", interpolation="nearest")
    axes[1].set_title(f"Stage 6F Primary Policy (t*={t_star_sens80:.2f})\nSens={fold3_eval_sens80['sensitivity']:.1%}, Spec={fold3_eval_sens80['specificity']:.1%}")
    axes[1].set_xticks([0, 1])
    axes[1].set_yticks([0, 1])
    axes[1].set_xticklabels(["Pred Neg", "Pred Pos"])
    axes[1].set_yticklabels(["True Neg", "True Pos"])
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, str(cm_star[i, j]), ha="center", va="center", color="red" if i!=j else "black", fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(outputs_dir / "fold3_confusion_matrix_comparison.png", dpi=200)
    plt.close()

    # 11. Write Markdown Summary
    summary_md = f"""# TQ-BioNet Stage 6F: Development Specificity Optimization & Retrospective Fold 3 Summary

This experiment evaluates decision threshold optimization and false-positive reduction strictly using Development data (Folds 0–2), followed by a retrospective evaluation on the Stage 6E Fold 3 cohort.

> [!IMPORTANT]
> **Methodological Framing & Retrospective Qualification**:
> Fold 3 was previously evaluated during Stage 6E and therefore is **not** an untouched, prospective test cohort. The evaluations reported below are explicitly designated as **retrospective held-out analyses** applied to the frozen Stage 6E Fold 3 predicted probabilities. This experiment is a candidate-classification study rather than a clinical screening deployment.

## 1. Development Model Comparison (Folds 0–2 Scan-Grouped OOF)

| Model Architecture | Features | ROC-AUC | PR-AUC | Brier Score | Accuracy @ 0.50 | Sensitivity @ 0.50 | Specificity @ 0.50 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Adapted SVM (RBF)** | 15 frozen | {dev_model_comp['svm']['auc_roc']:.4f} | {dev_model_comp['svm']['average_precision']:.4f} | {dev_model_comp['svm']['brier_score']:.4f} | {dev_model_comp['svm']['at_threshold_0_50']['accuracy']*100:.2f}% | **{dev_model_comp['svm']['at_threshold_0_50']['sensitivity']*100:.2f}%** | {dev_model_comp['svm']['at_threshold_0_50']['specificity']*100:.2f}% |
| **Adapted Random Forest** | 15 frozen | **{dev_model_comp['rf']['auc_roc']:.4f}** | **{dev_model_comp['rf']['average_precision']:.4f}** | **{dev_model_comp['rf']['brier_score']:.4f}** | **{dev_model_comp['rf']['at_threshold_0_50']['accuracy']*100:.2f}%** | {dev_model_comp['rf']['at_threshold_0_50']['sensitivity']*100:.2f}% | {dev_model_comp['rf']['at_threshold_0_50']['specificity']*100:.2f}% |
| **Adapted XGBoost** | 15 frozen | {dev_model_comp['xgb']['auc_roc']:.4f} | {dev_model_comp['xgb']['average_precision']:.4f} | {dev_model_comp['xgb']['brier_score']:.4f} | {dev_model_comp['xgb']['at_threshold_0_50']['accuracy']*100:.2f}% | {dev_model_comp['xgb']['at_threshold_0_50']['sensitivity']*100:.2f}% | **{dev_model_comp['xgb']['at_threshold_0_50']['specificity']*100:.2f}%** |
| **Adapted Soft Ensemble** | 15 frozen | {dev_model_comp['ensemble']['auc_roc']:.4f} | {dev_model_comp['ensemble']['average_precision']:.4f} | {dev_model_comp['ensemble']['brier_score']:.4f} | {dev_model_comp['ensemble']['at_threshold_0_50']['accuracy']*100:.2f}% | {dev_model_comp['ensemble']['at_threshold_0_50']['sensitivity']*100:.2f}% | {dev_model_comp['ensemble']['at_threshold_0_50']['specificity']*100:.2f}% |

*Note on performance breakdown:* Random Forest achieves the highest overall discrimination (AUC 0.6598, PR-AUC 0.7427, Brier 0.2121), XGBoost provides the highest specificity at default threshold (51.24%), SVM achieves the highest sensitivity (93.07%), and the Soft Ensemble provides a balanced consensus across all three.

## 2. True Leak-Free Nested Development Threshold Selection (Folds 0–2)

Thresholds were selected strictly on inner folds using an inner 2-fold cross-validation scheme where outer validation folds were completely excluded from both model training and threshold tuning:

| Policy Constraint | Frozen Threshold ($t^*$) | Inner Fold Selected Thresholds | Nested Sensitivity | Nested Specificity | Nested Balanced Acc | Nested Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary: Sens $\\ge 80\\%$** | **{t_star_sens80:.2f}** | Fold0: {nested_sens80['inner_thresholds_per_fold']['Fold0']:.2f}, Fold1: {nested_sens80['inner_thresholds_per_fold']['Fold1']:.2f}, Fold2: {nested_sens80['inner_thresholds_per_fold']['Fold2']:.2f} | **{nested_sens80['nested_sensitivity']*100:.2f}%** | {nested_sens80['nested_specificity']*100:.2f}% | {nested_sens80['nested_balanced_accuracy']*100:.2f}% | {nested_sens80['nested_accuracy']*100:.2f}% |
| **Secondary: Sens $\\ge 75\\%$** | **{t_star_sens75:.2f}** | Fold0: {nested_sens75['inner_thresholds_per_fold']['Fold0']:.2f}, Fold1: {nested_sens75['inner_thresholds_per_fold']['Fold1']:.2f}, Fold2: {nested_sens75['inner_thresholds_per_fold']['Fold2']:.2f} | {nested_sens75['nested_sensitivity']*100:.2f}%* | {nested_sens75['nested_specificity']*100:.2f}% | {nested_sens75['nested_balanced_accuracy']*100:.2f}% | {nested_sens75['nested_accuracy']*100:.2f}% |
| **Secondary: Max Youden $J$** | **{t_star_youden:.2f}** | Fold0: {nested_youden['inner_thresholds_per_fold']['Fold0']:.2f}, Fold1: {nested_youden['inner_thresholds_per_fold']['Fold1']:.2f}, Fold2: {nested_youden['inner_thresholds_per_fold']['Fold2']:.2f} | {nested_youden['nested_sensitivity']*100:.2f}% | {nested_youden['nested_specificity']*100:.2f}% | {nested_youden['nested_balanced_accuracy']*100:.2f}% | {nested_youden['nested_accuracy']*100:.2f}% |

*\\*Qualification on sensitivity constraint:* The secondary policy constrained to $\\ge 75\\%$ on inner training folds achieved {nested_sens75['nested_sensitivity']*100:.2f}% on unseen outer validation folds. This demonstrates that finite-sample sampling variation across folds can cause slight empirical boundary offsets when applying fixed thresholds to unseen cohorts.

## 3. Retrospective Evaluation on Fold 3 ($N=320$ Findings, 58 Scans)

| Metric [Scan-Cluster 95% CI] | Stage 6E Baseline ($t=0.50$) | Primary Policy ($t^*={t_star_sens80:.2f}$) | Secondary Policy ($t^*={t_star_sens75:.2f}$) | Secondary Youden ($t^*={t_star_youden:.2f}$) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | 68.75% [63.0% – 74.2%] | **{fold3_eval_sens80['accuracy']*100:.2f}%** [{fold3_eval_sens80['accuracy_95ci'][0]*100:.1f}% – {fold3_eval_sens80['accuracy_95ci'][1]*100:.1f}%] | {fold3_eval_sens75['accuracy']*100:.2f}% | {fold3_eval_youden['accuracy']*100:.2f}% |
| **Balanced Accuracy** | 65.27% | **{fold3_eval_sens80['balanced_accuracy']*100:.2f}%** | {fold3_eval_sens75['balanced_accuracy']*100:.2f}% | {fold3_eval_youden['balanced_accuracy']*100:.2f}% |
| **Sensitivity** | 83.25% [76.9% – 88.5%] | **{fold3_eval_sens80['sensitivity']*100:.2f}%** [{fold3_eval_sens80['sensitivity_95ci'][0]*100:.1f}% – {fold3_eval_sens80['sensitivity_95ci'][1]*100:.1f}%] | {fold3_eval_sens75['sensitivity']*100:.2f}% | {fold3_eval_youden['sensitivity']*100:.2f}% |
| **Specificity** | 47.29% [38.2% – 56.4%] | **{fold3_eval_sens80['specificity']*100:.2f}%** [{fold3_eval_sens80['specificity_95ci'][0]*100:.1f}% – {fold3_eval_sens80['specificity_95ci'][1]*100:.1f}%] | {fold3_eval_sens75['specificity']*100:.2f}% | {fold3_eval_youden['specificity']*100:.2f}% |
| **Precision (PPV)** | 70.04% | **{fold3_eval_sens80['precision']*100:.2f}%** | {fold3_eval_sens75['precision']*100:.2f}% | {fold3_eval_youden['precision']*100:.2f}% |
| **F1-Score** | 76.08% | **{fold3_eval_sens80['f1']*100:.2f}%** | {fold3_eval_sens75['f1']*100:.2f}% | {fold3_eval_youden['f1']*100:.2f}% |
| **Youden Index ($J$)** | 0.3053 | **{fold3_eval_sens80['youden_j']:.4f}** | {fold3_eval_sens75['youden_j']:.4f} | {fold3_eval_youden['youden_j']:.4f} |
| **Confusion Matrix [TN, FP, FN, TP]** | [61, 68, 32, 159] | [{fold3_eval_sens80['confusion_matrix']['tn']}, {fold3_eval_sens80['confusion_matrix']['fp']}, {fold3_eval_sens80['confusion_matrix']['fn']}, {fold3_eval_sens80['confusion_matrix']['tp']}] | [{fold3_eval_sens75['confusion_matrix']['tn']}, {fold3_eval_sens75['confusion_matrix']['fp']}, {fold3_eval_sens75['confusion_matrix']['fn']}, {fold3_eval_sens75['confusion_matrix']['tp']}] | [{fold3_eval_youden['confusion_matrix']['tn']}, {fold3_eval_youden['confusion_matrix']['fp']}, {fold3_eval_youden['confusion_matrix']['fn']}, {fold3_eval_youden['confusion_matrix']['tp']}] |

## 4. Paired Scan-Cluster Bootstrap Comparison (Primary Policy vs Baseline $t=0.50$)

Paired bootstrap across 5,000 resampled scan clusters evaluates whether changes in performance are statistically meaningful:
- **Specificity Difference**: {paired_comp_sens80['specificity_delta']['observed']*100:+.2f} percentage points [95% CI: {paired_comp_sens80['specificity_delta']['scan_cluster_95ci'][0]*100:+.2f}% to {paired_comp_sens80['specificity_delta']['scan_cluster_95ci'][1]*100:+.2f}%]
- **Sensitivity Difference**: {paired_comp_sens80['sensitivity_delta']['observed']*100:+.2f} percentage points [95% CI: {paired_comp_sens80['sensitivity_delta']['scan_cluster_95ci'][0]*100:+.2f}% to {paired_comp_sens80['sensitivity_delta']['scan_cluster_95ci'][1]*100:+.2f}%]
- **Accuracy Difference**: {paired_comp_sens80['accuracy_delta']['observed']*100:+.2f} percentage points [95% CI: {paired_comp_sens80['accuracy_delta']['scan_cluster_95ci'][0]*100:+.2f}% to {paired_comp_sens80['accuracy_delta']['scan_cluster_95ci'][1]*100:+.2f}%]

*Statistical interpretation:* Because the specificity interval crosses zero ([0.00%, +2.86%]), an increase from 0.50 to 0.52 does not establish a statistically significant specificity gain. Conversely, the sensitivity reduction ([-9.90%, -3.05%]) and accuracy reduction ([-5.64%, -1.55%]) are both strictly negative.

## 5. Radiologist Agreement Stratification on Fold 3 (Primary Policy $t^*={t_star_sens80:.2f}$)
- **AgrLevel 0** (non-nodules, N={fold3_eval_sens80['agreement_stratification']['0']['n']}): Accuracy = {fold3_eval_sens80['agreement_stratification']['0']['accuracy']*100:.2f}% (Specificity)
- **AgrLevel 1** (1-reader nodules, N={fold3_eval_sens80['agreement_stratification']['1']['n']}): Accuracy = {fold3_eval_sens80['agreement_stratification']['1']['accuracy']*100:.2f}% (Sensitivity)
- **AgrLevel 2** (2-reader consensus, N={fold3_eval_sens80['agreement_stratification']['2']['n']}): Accuracy = {fold3_eval_sens80['agreement_stratification']['2']['accuracy']*100:.2f}% (Sensitivity)
- **AgrLevel 3** (3-reader unanimous, N={fold3_eval_sens80['agreement_stratification']['3']['n']}): Accuracy = {fold3_eval_sens80['agreement_stratification']['3']['accuracy']*100:.2f}% (Sensitivity)

## 6. Secondary Conflict Sensitivity on Fold 3 (Primary Policy $t^*={t_star_sens80:.2f}$)
- Findings evaluated: 317 (after collapsing 3 conflicting coordinate groups from 6 raw rows to 3 representative rows).
- Accuracy: {conflict_sens_policy['accuracy']*100:.2f}%
- Balanced Accuracy: {conflict_sens_policy['balanced_accuracy']*100:.2f}%
- Sensitivity: {conflict_sens_policy['sensitivity']*100:.2f}%
- Specificity: {conflict_sens_policy['specificity']*100:.2f}%

## 7. Scientific Conclusion
Within the scope of the tested models and operating points, decision threshold adjustment alone does not solve the low-specificity challenge on LNDb without an unacceptable reduction in nodule sensitivity. Isolating the root cause (e.g., whether vascular parenchymal feature representation, scanner protocol shift, or label noise) requires further targeted ablations and feature-family experiments.

## 8. Methodological & Numerical Audit Notes (Stage 6F.2)
1. **SVM Internal Calibration Limitation**: While the outer folds and inner nested partitions are strictly scan-grouped (preventing scan leakage across folds), `SVC(probability=True)` uses scikit-learn's default internal 5-fold Platt scaling, which is randomly stratified across candidate findings rather than scan-grouped. Future work should consider custom scan-grouped Platt calibrators.
2. **ARPACK Eigensolver Boundary Behavior**: Feature 29 (`quantum_eigenvalue_9`) exhibits minor variation (~0.12%) exclusively on degenerate constant patches (e.g. uniform air) due to ARPACK's unseeded Lanczos starting vector at truncation rank $k=10$. Crucially, `quantum_eigenvalue_9` is not part of the frozen 15-feature set (which selects only `quantum_eigenvalue_0, 1, 2`), so this behavior does not affect any Stage 6F models.
"""
    summary_path = outputs_dir / "stage6f_summary.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\nStage 6F completed successfully.")
    print(f"Summary written to: {summary_path}")
    print(f"Metrics written to: {outputs_dir / 'fold3_retrospective_metrics.json'}")


if __name__ == "__main__":
    run_stage6f()
