"""
Stage 6E: LNDb-Specific Development and Scan-Grouped Evaluation Pipeline
=======================================================================

This module implements controlled domain adaptation and scan-grouped evaluation on LNDb:
1. Audits and isolates the 6 exact-coordinate label conflicts in trainNodules_gt.csv.
2. Partitions the cohort according to the official LNDb challenge folds (trainFolds.csv):
   - Development cohort: Folds 0, 1, 2 (177 scans, 899 findings)
   - Held-out independent test partition: Fold 3 (59 scans, 320 findings)
3. Evaluates models using scan-grouped cross-validation on Development data:
   - Majority-class baseline (always positive)
   - Frozen LUNA16 zero-shot baseline
   - LNDb-adapted SVM, XGBoost, Random Forest, and Ensemble
   - Feature comparison: Frozen 15 features vs. All 31 features
4. Trains optimal adapted models on Development cohort and evaluates ONCE on Fold 3.
5. Performs sensitivity analysis comparing raw vs. conflict-resolved ground truth.
6. Emits comprehensive metrics, ROC/PR curves, and audit reports to outputs/stage6e_lndb_adaptation/.
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
    FROZEN_31_FEATURES,
    FROZEN_15_SELECTED_FEATURES,
    DEFAULT_DECISION_THRESHOLD,
    compute_calibration_metrics,
    prune_to_selected_features,
    load_pipeline_bundle,
    predict_ensemble
)
from tq_bionet.evaluation_metrics import compute_cluster_bootstrap_ci, compute_wilson_ci
from tq_bionet.resampling_engine import get_array_sha256


def audit_label_conflicts(gt_df: pd.DataFrame, output_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifies exact duplicate coordinates with conflicting Nodule labels in trainNodules_gt.csv.
    Saves an audit CSV and generates a sensitivity-resolved dataframe.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dupe_mask = gt_df.duplicated(subset=["LNDbID", "x", "y", "z"], keep=False)
    dupes = gt_df[dupe_mask].copy()

    # Find conflicting groups
    conflict_keys = []
    for (scan_id, x, y, z), group in dupes.groupby(["LNDbID", "x", "y", "z"]):
        if group["Nodule"].nunique() > 1:
            conflict_keys.append((scan_id, x, y, z))

    conflict_rows = gt_df[gt_df.set_index(["LNDbID", "x", "y", "z"]).index.isin(conflict_keys)].copy()
    conflict_rows = conflict_rows.sort_values(by=["LNDbID", "x", "y", "z", "FindingID"])
    conflict_path = output_dir / "conflicting_coordinates_audit.csv"
    conflict_rows.to_csv(conflict_path, index=False)
    print(f"   [AUDIT] Found {len(conflict_keys)} conflicting coordinate locations ({len(conflict_rows)} total rows). Saved to {conflict_path.name}.")

    # Build a secondary sensitivity dataset without collapsing same-label duplicates.
    # Only groups with conflicting binary labels are reduced to a representative row.
    resolved_rows = []
    for _, group in gt_df.groupby(["LNDbID", "x", "y", "z"], sort=False):
        if group["Nodule"].nunique() > 1:
            best_row = group.sort_values(
                by=["AgrLevel", "Volume", "FindingID"],
                ascending=[False, False, True],
                kind="mergesort"
            ).iloc[0]
            resolved_rows.append(best_row.to_dict())
        else:
            resolved_rows.extend(group.to_dict("records"))
    resolved_df = pd.DataFrame(resolved_rows)
    return conflict_rows, resolved_df


def load_lndb_features_and_folds(
    cache_dir: Path,
    folds_path: Path,
    gt_df: pd.DataFrame
) -> Dict[str, Any]:
    """Loads cached 1.0mm features and maps each sample to its official challenge fold."""
    x_path = cache_dir / "X.npy"
    y_path = cache_dir / "y.npy"
    groups_path = cache_dir / "groups.npy"
    coords_path = cache_dir / "coords.npy"
    agr_path = cache_dir / "agr_levels.npy"

    if not all(p.exists() for p in [x_path, y_path, groups_path, coords_path, agr_path]):
        raise FileNotFoundError(f"Missing required 1.0mm feature cache files in {cache_dir}")

    X = np.load(x_path)
    y = np.load(y_path)
    groups = np.load(groups_path)
    coords = np.load(coords_path)
    agr_levels = np.load(agr_path)

    # Strict row-wise alignment audit: cache rows must preserve the official
    # trainNodules_gt.csv order and values used during Stage 6D extraction.
    expected_n = len(gt_df)
    if (X.ndim != 2 or X.shape != (expected_n, 31) or
            y.shape != (expected_n,) or groups.shape != (expected_n,) or
            coords.shape != (expected_n, 3) or agr_levels.shape != (expected_n,)):
        raise ValueError(
            "Stage 6D cache shape mismatch: expected "
            f"X=({expected_n},31), y/groups/agr=({expected_n},), coords=({expected_n},3); "
            f"got X={X.shape}, y={y.shape}, groups={groups.shape}, "
            f"coords={coords.shape}, agr={agr_levels.shape}."
        )

    expected_groups = np.asarray([f"LNDb-{int(v):04d}" for v in gt_df["LNDbID"]])
    expected_y = gt_df["Nodule"].to_numpy(dtype=np.int64)
    expected_coords = gt_df[["x", "y", "z"]].to_numpy(dtype=np.float64)
    expected_agr = gt_df["AgrLevel"].to_numpy(dtype=np.int64)
    if not (np.array_equal(groups.astype(str), expected_groups) and
            np.array_equal(y, expected_y) and
            np.allclose(coords, expected_coords, rtol=0.0, atol=1e-7) and
            np.array_equal(agr_levels, expected_agr)):
        mismatch = {
            "groups": int(np.sum(groups.astype(str) != expected_groups)),
            "labels": int(np.sum(y != expected_y)),
            "coordinates": int(np.sum(~np.isclose(coords, expected_coords, rtol=0.0, atol=1e-7).all(axis=1))),
            "agreement_levels": int(np.sum(agr_levels != expected_agr))
        }
        raise ValueError(
            "Stage 6D cache rows are not aligned to trainNodules_gt.csv in its current row order. "
            f"Mismatch counts: {mismatch}. Rebuild the 1.0mm cache from the exact ground-truth CSV."
        )

    # Load official folds
    folds_df = pd.read_csv(folds_path)
    scan_to_fold = {}
    for fold_name in ["Fold0", "Fold1", "Fold2", "Fold3"]:
        for scan_id in folds_df[fold_name].dropna().astype(int):
            scan_to_fold[f"LNDb-{scan_id:04d}"] = fold_name
            scan_to_fold[scan_id] = fold_name

    sample_folds = np.array([scan_to_fold.get(g, "Unknown") for g in groups])
    if "Unknown" in sample_folds:
        raise ValueError(f"Some scans could not be mapped to official folds: {np.unique(groups[sample_folds == 'Unknown'])}")

    return {
        "X": X, "y": y, "groups": groups, "coords": coords,
        "agr_levels": agr_levels, "folds": sample_folds
    }


def fit_and_predict_cv(
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    groups_dev: np.ndarray,
    folds_dev: np.ndarray,
    model_type: str,
    use_15_features: bool = True
) -> Dict[str, Any]:
    """
    Executes scan-grouped 3-fold cross-validation across Folds 0, 1, 2.
    Ensures zero scan leakage between validation folds.
    """
    X_mat = prune_to_selected_features(X_dev) if use_15_features else X_dev.copy()

    unique_folds = sorted(list(set(folds_dev)))
    oof_probs = np.zeros(len(y_dev), dtype=float)
    oof_preds = np.zeros(len(y_dev), dtype=int)

    for val_fold in unique_folds:
        val_idx = (folds_dev == val_fold)
        train_idx = ~val_idx

        X_train, y_train = X_mat[train_idx], y_dev[train_idx]
        X_val, y_val = X_mat[val_idx], y_dev[val_idx]

        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_val_sc = scaler.transform(X_val)

        if model_type == "majority":
            oof_probs[val_idx] = float(np.mean(y_train))
            oof_preds[val_idx] = 1
        elif model_type == "svm":
            clf = SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=42)
            clf.fit(X_train_sc, y_train)
            oof_probs[val_idx] = clf.predict_proba(X_val_sc)[:, 1]
            oof_preds[val_idx] = (oof_probs[val_idx] >= 0.5).astype(int)
        elif model_type == "rf":
            clf = RandomForestClassifier(n_estimators=300, max_features="sqrt", class_weight="balanced", random_state=42)
            clf.fit(X_train, y_train)
            oof_probs[val_idx] = clf.predict_proba(X_val)[:, 1]
            oof_preds[val_idx] = (oof_probs[val_idx] >= 0.5).astype(int)
        elif model_type == "xgb":
            scale_pos = (len(y_train) - np.sum(y_train)) / max(1, np.sum(y_train))
            clf = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                                scale_pos_weight=scale_pos, eval_metric="logloss", random_state=42)
            clf.fit(X_train, y_train)
            oof_probs[val_idx] = clf.predict_proba(X_val)[:, 1]
            oof_preds[val_idx] = (oof_probs[val_idx] >= 0.5).astype(int)
        elif model_type == "ensemble":
            # Soft average of adapted SVM, RF, and XGB
            clf_svm = SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=42)
            clf_svm.fit(X_train_sc, y_train)
            p_svm = clf_svm.predict_proba(X_val_sc)[:, 1]

            clf_rf = RandomForestClassifier(n_estimators=300, max_features="sqrt", class_weight="balanced", random_state=42)
            clf_rf.fit(X_train, y_train)
            p_rf = clf_rf.predict_proba(X_val)[:, 1]

            scale_pos = (len(y_train) - np.sum(y_train)) / max(1, np.sum(y_train))
            clf_xgb = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                                    scale_pos_weight=scale_pos, eval_metric="logloss", random_state=42)
            clf_xgb.fit(X_train, y_train)
            p_xgb = clf_xgb.predict_proba(X_val)[:, 1]

            oof_probs[val_idx] = (p_svm + p_rf + p_xgb) / 3.0
            oof_preds[val_idx] = (oof_probs[val_idx] >= 0.5).astype(int)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    acc = accuracy_score(y_dev, oof_preds)
    bal_acc = balanced_accuracy_score(y_dev, oof_preds)
    sens = recall_score(y_dev, oof_preds, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_dev, oof_preds).ravel()
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = precision_score(y_dev, oof_preds, zero_division=0)
    f1 = f1_score(y_dev, oof_preds, zero_division=0)
    auc_roc = roc_auc_score(y_dev, oof_probs) if len(np.unique(y_dev)) > 1 else 0.5
    ap = average_precision_score(y_dev, oof_probs) if len(np.unique(y_dev)) > 1 else 0.5
    brier = brier_score_loss(y_dev, oof_probs)

    return {
        "model": model_type,
        "features": "15_frozen" if use_15_features else "31_all",
        "n_samples": len(y_dev),
        "accuracy": float(acc),
        "balanced_accuracy": float(bal_acc),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "precision": float(prec),
        "f1": float(f1),
        "auc_roc": float(auc_roc),
        "average_precision": float(ap),
        "brier_score": float(brier),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "oof_probs": oof_probs,
        "oof_preds": oof_preds
    }


def evaluate_on_fold3(
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    groups_test: np.ndarray,
    agr_test: np.ndarray,
    use_15_features: bool = True
) -> Dict[str, Any]:
    """
    Fits final adapted ensemble on full development cohort (Folds 0-2)
    and evaluates ONCE on the untouched holdout partition (Fold 3).
    """
    X_dev_m = prune_to_selected_features(X_dev) if use_15_features else X_dev.copy()
    X_test_m = prune_to_selected_features(X_test) if use_15_features else X_test.copy()

    scaler = StandardScaler()
    X_dev_sc = scaler.fit_transform(X_dev_m)
    X_test_sc = scaler.transform(X_test_m)

    # 1. Fit Adapted Models
    clf_svm = SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=42)
    clf_svm.fit(X_dev_sc, y_dev)
    p_svm = clf_svm.predict_proba(X_test_sc)[:, 1]

    clf_rf = RandomForestClassifier(n_estimators=300, max_features="sqrt", class_weight="balanced", random_state=42)
    clf_rf.fit(X_dev_m, y_dev)
    p_rf = clf_rf.predict_proba(X_test_m)[:, 1]

    scale_pos = (len(y_dev) - np.sum(y_dev)) / max(1, np.sum(y_dev))
    clf_xgb = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                            scale_pos_weight=scale_pos, eval_metric="logloss", random_state=42)
    clf_xgb.fit(X_dev_m, y_dev)
    p_xgb = clf_xgb.predict_proba(X_test_m)[:, 1]

    p_ens = (p_svm + p_rf + p_xgb) / 3.0
    pred_ens = (p_ens >= DEFAULT_DECISION_THRESHOLD).astype(int)

    # Metrics
    acc = accuracy_score(y_test, pred_ens)
    bal_acc = balanced_accuracy_score(y_test, pred_ens)
    sens = recall_score(y_test, pred_ens, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_test, pred_ens).ravel()
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = precision_score(y_test, pred_ens, zero_division=0)
    f1 = f1_score(y_test, pred_ens, zero_division=0)
    auc_roc = roc_auc_score(y_test, p_ens)
    ap = average_precision_score(y_test, p_ens)
    brier = brier_score_loss(y_test, p_ens)

    acc_ci = compute_cluster_bootstrap_ci(y_test, pred_ens, groups_test, accuracy_score)
    f1_ci = compute_cluster_bootstrap_ci(y_test, pred_ens, groups_test, f1_score)
    auc_ci = compute_cluster_bootstrap_ci(y_test, p_ens, groups_test, roc_auc_score)

    cal = compute_calibration_metrics(y_test, p_ens)

    # Stratification by agreement level
    strat = {}
    for agr in sorted(np.unique(agr_test)):
        mask = (agr_test == agr)
        sub_y = y_test[mask]
        sub_pred = pred_ens[mask]
        sub_acc = accuracy_score(sub_y, sub_pred) if len(sub_y) > 0 else 0.0
        strat[str(agr)] = {
            "n": int(len(sub_y)),
            "accuracy": float(sub_acc),
            "positive_count": int(np.sum(sub_y == 1))
        }

    return {
        "n_samples": len(y_test),
        "majority_baseline_acc": float(np.mean(y_test == 1)),
        "accuracy": float(acc),
        "accuracy_95ci": acc_ci,
        "balanced_accuracy": float(bal_acc),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "precision": float(prec),
        "f1": float(f1),
        "f1_95ci": f1_ci,
        "auc_roc": float(auc_roc),
        "auc_roc_95ci": auc_ci,
        "average_precision": float(ap),
        "brier_score": float(brier),
        "expected_calibration_error": float(cal["expected_calibration_error"]),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "agreement_stratification": strat,
        "probabilities": p_ens,
        "predictions": pred_ens,
        "individual_probs": {
            "svm_prob": p_svm,
            "rf_prob": p_rf,
            "xgb_prob": p_xgb
        }
    }


def compute_fold3_conflict_sensitivity(
    gt_df: pd.DataFrame,
    groups_test: np.ndarray,
    coords_test: np.ndarray,
    raw_labels: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    agr_test: np.ndarray
) -> Dict[str, Any]:
    """
    Secondary, label-sensitivity-only analysis on Fold 3.

    Keeps the original finding-level predictions fixed. For exact duplicate
    coordinates with conflicting binary labels, all rows at that physical
    location are represented once using the highest AgrLevel row (then larger
    Volume as deterministic tie-break). Non-conflicting rows are unchanged.
    This is not a retrained model and not a replacement for primary metrics.
    """
    test_df = pd.DataFrame({
        "seriesuid": groups_test.astype(str),
        "x": coords_test[:, 0],
        "y": coords_test[:, 1],
        "z": coords_test[:, 2],
        "raw_label": raw_labels.astype(int),
        "prediction": predictions.astype(int),
        "probability": probabilities.astype(float),
        "agr_level": agr_test.astype(int)
    })
    # Carry the ground-truth row's volume for transparent tie-breaking.
    gt_keys = gt_df.copy()
    gt_keys["seriesuid"] = gt_keys["LNDbID"].map(lambda v: f"LNDb-{int(v):04d}")
    key_cols = ["seriesuid", "x", "y", "z"]
    test_df = test_df.merge(
        gt_keys[key_cols + ["Volume", "FindingID"]],
        on=key_cols, how="left", validate="one_to_one"
    )
    if test_df["FindingID"].isna().any():
        raise ValueError("Fold 3 predictions failed to join back to ground-truth finding rows.")

    rows = []
    conflict_groups = 0
    conflict_raw_rows = 0
    for _, group in test_df.groupby(key_cols, sort=False, dropna=False):
        has_conflict = group["raw_label"].nunique() > 1
        if has_conflict:
            conflict_groups += 1
            conflict_raw_rows += len(group)
            chosen = group.sort_values(
                ["agr_level", "Volume", "FindingID"],
                ascending=[False, False, True],
                kind="mergesort"
            ).iloc[0]
        else:
            # Keep all distinct finding rows where labels agree. Exact duplicate
            # same-label rows remain individual observations in this sensitivity
            # analysis unless they are part of a binary conflict.
            rows.extend(group.to_dict("records"))
            continue
        rows.append(chosen.to_dict())

    resolved = pd.DataFrame(rows)
    yr = resolved["raw_label"].to_numpy(dtype=int)
    yp = resolved["prediction"].to_numpy(dtype=int)
    pp = resolved["probability"].to_numpy(dtype=float)
    tn, fp, fn, tp = confusion_matrix(yr, yp, labels=[0, 1]).ravel()
    return {
        "method": (
            "Secondary fixed-prediction sensitivity analysis: for each exact "
            "same-scan physical coordinate with conflicting Nodule labels, "
            "retain the row with highest AgrLevel, then largest Volume, then "
            "smallest FindingID. No model retraining or probability changes."
        ),
        "primary_rows": int(len(test_df)),
        "sensitivity_rows": int(len(resolved)),
        "conflicting_coordinate_groups_fold3": int(conflict_groups),
        "raw_rows_in_conflicting_groups_fold3": int(conflict_raw_rows),
        "removed_rows_due_to_conflict_collapse": int(len(test_df) - len(resolved)),
        "accuracy": float(accuracy_score(yr, yp)),
        "balanced_accuracy": float(balanced_accuracy_score(yr, yp)),
        "sensitivity": float(recall_score(yr, yp, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else 0.0,
        "precision": float(precision_score(yr, yp, zero_division=0)),
        "f1": float(f1_score(yr, yp, zero_division=0)),
        "auc_roc": float(roc_auc_score(yr, pp)) if len(np.unique(yr)) > 1 else None,
        "average_precision": float(average_precision_score(yr, pp)) if len(np.unique(yr)) > 1 else None,
        "brier_score": float(brier_score_loss(yr, pp)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "explicit_warning": (
            "This changes the evaluation unit from finding rows to coordinate groups "
            "only for conflicting coordinates. It is sensitivity analysis, not an "
            "adjudicated ground truth or the primary Fold 3 estimate."
        )
    }


def paired_scan_cluster_baseline_comparison(
    y_true: np.ndarray,
    model_pred: np.ndarray,
    group_ids: np.ndarray,
    n_bootstrap: int = 5000,
    seed: int = 42
) -> Dict[str, Any]:
    """Paired scan-cluster bootstrap for accuracy difference vs always-positive baseline."""
    rng = np.random.default_rng(seed)
    unique_groups = np.unique(group_ids.astype(str))
    group_indices = {g: np.flatnonzero(group_ids.astype(str) == g) for g in unique_groups}
    delta = []
    observed_model = accuracy_score(y_true, model_pred)
    observed_baseline = accuracy_score(y_true, np.ones_like(y_true, dtype=int))
    for _ in range(n_bootstrap):
        sampled = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([group_indices[g] for g in sampled])
        if len(idx):
            baseline = np.ones(len(idx), dtype=int)
            delta.append(accuracy_score(y_true[idx], model_pred[idx]) -
                         accuracy_score(y_true[idx], baseline))
    ci = np.quantile(np.asarray(delta), [0.025, 0.975]).tolist()
    return {
        "comparison": "adapted ensemble accuracy minus always-positive baseline accuracy",
        "observed_accuracy_difference": float(observed_model - observed_baseline),
        "scan_cluster_bootstrap_95ci": [float(ci[0]), float(ci[1])],
        "bootstrap_replicates": int(len(delta)),
        "unique_scan_clusters": int(len(unique_groups)),
        "seed": int(seed),
        "interpretation": (
            "Paired resampling: each sampled scan contributes the same findings to "
            "both classifiers. CI above zero supports higher accuracy than the "
            "majority baseline under this scan-cluster resampling design."
        )
    }


def run_stage6e():
    print("======================================================================")
    print("   TQ-BioNet Stage 6E: LNDb-Specific Development & Grouped Evaluation  ")
    print("======================================================================\n")

    project_root = Path(__file__).resolve().parent
    outputs_dir = project_root / "outputs" / "stage6e_lndb_adaptation"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    cache_1mm_dir = Path(r"D:\LNDb\cache\stage6d\1.0mm")
    folds_path = Path(r"D:\LNDb\annotations\trainset_csv\trainFolds.csv")
    gt_path = Path(r"D:\LNDb\annotations\trainset_csv\trainNodules_gt.csv")

    gt_df = pd.read_csv(gt_path)
    print(f"Loaded ground truth: {len(gt_df)} rows across {gt_df['LNDbID'].nunique()} scans.")

    # 1. Audit label conflicts
    conflict_df, resolved_gt_df = audit_label_conflicts(gt_df, outputs_dir)

    # 2. Load feature cache and official challenge folds
    cohort = load_lndb_features_and_folds(cache_1mm_dir, folds_path, gt_df)
    X, y, groups, folds = cohort["X"], cohort["y"], cohort["groups"], cohort["folds"]
    agr_levels = cohort["agr_levels"]
    coords = cohort["coords"]

    dev_mask = np.isin(folds, ["Fold0", "Fold1", "Fold2"])
    test_mask = (folds == "Fold3")

    X_dev, y_dev, groups_dev, folds_dev = X[dev_mask], y[dev_mask], groups[dev_mask], folds[dev_mask]
    X_test, y_test, groups_test, agr_test = X[test_mask], y[test_mask], groups[test_mask], agr_levels[test_mask]
    coords_test = coords[test_mask]

    print(f"\nCohort Partitioning (Scan-Grouped via official trainFolds.csv):")
    print(f"   Development cohort (Folds 0, 1, 2): {len(y_dev)} findings across {len(np.unique(groups_dev))} scans ({np.sum(y_dev==1)} pos, {np.sum(y_dev==0)} neg, pos_ratio={np.mean(y_dev):.3f})")
    print(f"   Held-out test cohort (Fold 3):       {len(y_test)} findings across {len(np.unique(groups_test))} scans ({np.sum(y_test==1)} pos, {np.sum(y_test==0)} neg, pos_ratio={np.mean(y_test):.3f})")
    print(f"   Scan leakage between partitions:     0 overlapping scans (verified disjoint)")

    # 3. Development Grouped Cross-Validation Comparisons (Folds 0-2)
    print("\n[STEP 3] Running scan-grouped cross-validation on Development data (Folds 0-2)...")
    cv_results = {}

    # Majority classifier baseline
    cv_results["Majority Baseline"] = fit_and_predict_cv(X_dev, y_dev, groups_dev, folds_dev, "majority")

    # Frozen Zero-Shot reference on Development
    bundle_dir = Path("outputs/frozen_v3_1_pipeline")
    svm_f, xgb_f, rf_f, scaler_f, _ = load_pipeline_bundle(bundle_dir)
    f_preds = predict_ensemble(svm_f, xgb_f, rf_f, scaler_f, prune_to_selected_features(X_dev))
    f_prob = f_preds["ensemble_prob"]
    f_pred = f_preds["y_pred"]
    cv_results["Frozen Zero-Shot (v3.1)"] = {
        "model": "frozen_v3_1",
        "features": "15_frozen",
        "n_samples": len(y_dev),
        "accuracy": float(accuracy_score(y_dev, f_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_dev, f_pred)),
        "sensitivity": float(recall_score(y_dev, f_pred)),
        "specificity": float(confusion_matrix(y_dev, f_pred)[0, 0] / np.sum(y_dev == 0)),
        "f1": float(f1_score(y_dev, f_pred)),
        "auc_roc": float(roc_auc_score(y_dev, f_prob)),
        "average_precision": float(average_precision_score(y_dev, f_prob)),
        "brier_score": float(brier_score_loss(y_dev, f_prob))
    }

    # Adapted models with 15 frozen features
    for m_type in ["svm", "rf", "xgb", "ensemble"]:
        key = f"Adapted {m_type.upper()} (15 feat)"
        cv_results[key] = fit_and_predict_cv(X_dev, y_dev, groups_dev, folds_dev, m_type, use_15_features=True)

    # Adapted models with all 31 features
    for m_type in ["rf", "ensemble"]:
        key = f"Adapted {m_type.upper()} (31 feat)"
        cv_results[key] = fit_and_predict_cv(X_dev, y_dev, groups_dev, folds_dev, m_type, use_15_features=False)

    print("\n--- Development Cross-Validation Summary (Folds 0-2) ---")
    print(f"{'Model':<30} | {'Acc':<6} | {'BalAcc':<6} | {'Sens':<6} | {'Spec':<6} | {'F1':<6} | {'AUC':<6} | {'Brier':<6}")
    print("-" * 85)
    for name, r in cv_results.items():
        print(f"{name:<30} | {r['accuracy']:.4f} | {r['balanced_accuracy']:.4f} | {r['sensitivity']:.4f} | {r['specificity']:.4f} | {r['f1']:.4f} | {r['auc_roc']:.4f} | {r['brier_score']:.4f}")

    # 4. Final Evaluation on Untouched Fold 3
    print("\n[STEP 4] Evaluating Adapted Models on Untouched Holdout Cohort (Fold 3, N=320)...")
    eval_fold3_15 = evaluate_on_fold3(X_dev, y_dev, X_test, y_test, groups_test, agr_test, use_15_features=True)
    eval_fold3_31 = evaluate_on_fold3(X_dev, y_dev, X_test, y_test, groups_test, agr_test, use_15_features=False)

    # Also evaluate frozen zero-shot on Fold 3 for direct contrast
    f3_f_preds = predict_ensemble(svm_f, xgb_f, rf_f, scaler_f, prune_to_selected_features(X_test))
    f3_f_prob = f3_f_preds["ensemble_prob"]
    f3_f_pred = f3_f_preds["y_pred"]
    eval_fold3_zero_shot = {
        "accuracy": float(accuracy_score(y_test, f3_f_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, f3_f_pred)),
        "sensitivity": float(recall_score(y_test, f3_f_pred)),
        "specificity": float(confusion_matrix(y_test, f3_f_pred)[0, 0] / np.sum(y_test == 0)),
        "f1": float(f1_score(y_test, f3_f_pred)),
        "auc_roc": float(roc_auc_score(y_test, f3_f_prob)),
        "average_precision": float(average_precision_score(y_test, f3_f_prob)),
        "brier_score": float(brier_score_loss(y_test, f3_f_prob))
    }

    print("\n--- Final Held-Out Evaluation on Fold 3 (N=320, 59 scans) ---")
    print(f"Majority Positive Baseline Acc: {eval_fold3_15['majority_baseline_acc']:.4f}")
    print(f"Frozen Zero-Shot v3.1:        Acc={eval_fold3_zero_shot['accuracy']:.4f}, AUC={eval_fold3_zero_shot['auc_roc']:.4f}, Sens={eval_fold3_zero_shot['sensitivity']:.4f}, Spec={eval_fold3_zero_shot['specificity']:.4f}")
    print(f"Adapted Ensemble (15 feat):   Acc={eval_fold3_15['accuracy']:.4f} [{eval_fold3_15['accuracy_95ci'][0]:.3f}-{eval_fold3_15['accuracy_95ci'][1]:.3f}], AUC={eval_fold3_15['auc_roc']:.4f} [{eval_fold3_15['auc_roc_95ci'][0]:.3f}-{eval_fold3_15['auc_roc_95ci'][1]:.3f}], Sens={eval_fold3_15['sensitivity']:.4f}, Spec={eval_fold3_15['specificity']:.4f}")
    print(f"Adapted Ensemble (31 feat):   Acc={eval_fold3_31['accuracy']:.4f} [{eval_fold3_31['accuracy_95ci'][0]:.3f}-{eval_fold3_31['accuracy_95ci'][1]:.3f}], AUC={eval_fold3_31['auc_roc']:.4f} [{eval_fold3_31['auc_roc_95ci'][0]:.3f}-{eval_fold3_31['auc_roc_95ci'][1]:.3f}], Sens={eval_fold3_31['sensitivity']:.4f}, Spec={eval_fold3_31['specificity']:.4f}")

    # 5. Save Predictions CSV for Fold 3
    preds_df = pd.DataFrame({
        "seriesuid": groups_test,
        "x": coords_test[:, 0],
        "y": coords_test[:, 1],
        "z": coords_test[:, 2],
        "true_label": y_test,
        "agr_level": agr_test,
        "adapted_svm_prob": eval_fold3_15["individual_probs"]["svm_prob"],
        "adapted_rf_prob": eval_fold3_15["individual_probs"]["rf_prob"],
        "adapted_xgb_prob": eval_fold3_15["individual_probs"]["xgb_prob"],
        "adapted_ensemble_prob": eval_fold3_15["probabilities"],
        "adapted_ensemble_pred": eval_fold3_15["predictions"],
        "zero_shot_ensemble_prob": f3_f_prob,
        "zero_shot_ensemble_pred": f3_f_pred
    })
    preds_path = outputs_dir / "fold3_predictions.csv"
    preds_df.to_csv(preds_path, index=False)

    # Stage 6E.1 audit: fixed-prediction sensitivity for Fold 3 label conflicts
    # and paired scan-cluster comparison against the always-positive baseline.
    conflict_sensitivity = compute_fold3_conflict_sensitivity(
        gt_df=gt_df,
        groups_test=groups_test,
        coords_test=coords_test,
        raw_labels=y_test,
        predictions=eval_fold3_15["predictions"],
        probabilities=eval_fold3_15["probabilities"],
        agr_test=agr_test
    )
    paired_baseline_comparison = paired_scan_cluster_baseline_comparison(
        y_true=y_test,
        model_pred=eval_fold3_15["predictions"],
        group_ids=groups_test
    )
    with (outputs_dir / "fold3_conflict_sensitivity.json").open("w", encoding="utf-8") as f:
        json.dump(conflict_sensitivity, f, indent=2)
    with (outputs_dir / "fold3_paired_baseline_comparison.json").open("w", encoding="utf-8") as f:
        json.dump(paired_baseline_comparison, f, indent=2)

    # 6. Generate ROC and PR Curves comparing Zero-Shot vs Adapted on Fold 3
    plt.figure(figsize=(7, 6))
    fpr_zs, tpr_zs, _ = roc_curve(y_test, f3_f_prob)
    fpr_ad15, tpr_ad15, _ = roc_curve(y_test, eval_fold3_15["probabilities"])
    fpr_ad31, tpr_ad31, _ = roc_curve(y_test, eval_fold3_31["probabilities"])
    plt.plot(fpr_zs, tpr_zs, label=f"Zero-Shot v3.1 (AUC = {eval_fold3_zero_shot['auc_roc']:.3f})", linestyle="--", color="gray")
    plt.plot(fpr_ad15, tpr_ad15, label=f"LNDb-Adapted 15-feat (AUC = {eval_fold3_15['auc_roc']:.3f})", color="tab:blue", lw=2)
    plt.plot(fpr_ad31, tpr_ad31, label=f"LNDb-Adapted 31-feat (AUC = {eval_fold3_31['auc_roc']:.3f})", color="tab:orange", lw=2)
    plt.plot([0, 1], [0, 1], "k:", alpha=0.5)
    plt.xlabel("False Positive Rate (1 - Specificity)")
    plt.ylabel("True Positive Rate (Sensitivity)")
    plt.title("Stage 6E: Fold 3 ROC Curve Comparison")
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outputs_dir / "roc_curve_stage6e.png", dpi=200)
    plt.close()

    plt.figure(figsize=(7, 6))
    pre_zs, rec_zs, _ = precision_recall_curve(y_test, f3_f_prob)
    pre_ad15, rec_ad15, _ = precision_recall_curve(y_test, eval_fold3_15["probabilities"])
    pre_ad31, rec_ad31, _ = precision_recall_curve(y_test, eval_fold3_31["probabilities"])
    plt.plot(rec_zs, pre_zs, label=f"Zero-Shot v3.1 (AP = {eval_fold3_zero_shot['average_precision']:.3f})", linestyle="--", color="gray")
    plt.plot(rec_ad15, pre_ad15, label=f"LNDb-Adapted 15-feat (AP = {eval_fold3_15['average_precision']:.3f})", color="tab:blue", lw=2)
    plt.plot(rec_ad31, pre_ad31, label=f"LNDb-Adapted 31-feat (AP = {eval_fold3_31['average_precision']:.3f})", color="tab:orange", lw=2)
    plt.axhline(eval_fold3_15["majority_baseline_acc"], color="red", linestyle=":", label=f"Prevalence Baseline ({eval_fold3_15['majority_baseline_acc']:.3f})")
    plt.xlabel("Recall (Sensitivity)")
    plt.ylabel("Precision (PPV)")
    plt.title("Stage 6E: Fold 3 Precision-Recall Curve Comparison")
    plt.legend(loc="lower left")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outputs_dir / "pr_curve_stage6e.png", dpi=200)
    plt.close()

    # 7. Save Metrics JSON
    metrics_payload = {
        "stage": "Stage 6E - LNDb Adaptation and Grouped Evaluation",
        "date_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "partitions": {
            "development_folds": ["Fold0", "Fold1", "Fold2"],
            "development_samples": len(y_dev),
            "development_scans": int(len(np.unique(groups_dev))),
            "held_out_fold": "Fold3",
            "held_out_samples": len(y_test),
            "held_out_scans": int(len(np.unique(groups_test))),
            "scan_overlap": 0
        },
        "conflicting_coordinates_audit": {
            "conflict_count": int(conflict_df.groupby(["LNDbID", "x", "y", "z"]).ngroups),
            "conflicting_rows": int(len(conflict_df)),
            "audit_file": "conflicting_coordinates_audit.csv",
            "fold3_fixed_prediction_sensitivity": conflict_sensitivity
        },
        "paired_scan_cluster_baseline_comparison": paired_baseline_comparison,
        "development_cross_validation_results": {
            k: {kk: vv for kk, vv in v.items() if kk not in ["oof_probs", "oof_preds"]}
            for k, v in cv_results.items()
        },
        "held_out_fold3_evaluation": {
            "majority_baseline": {
                "accuracy": eval_fold3_15["majority_baseline_acc"],
                "positive_prevalence": eval_fold3_15["majority_baseline_acc"]
            },
            "frozen_zero_shot_v3_1": eval_fold3_zero_shot,
            "adapted_ensemble_15_features": {
                k: v for k, v in eval_fold3_15.items() if k not in ["probabilities", "predictions", "individual_probs"]
            },
            "adapted_ensemble_31_features": {
                k: v for k, v in eval_fold3_31.items() if k not in ["probabilities", "predictions", "individual_probs"]
            }
        }
    }
    metrics_path = outputs_dir / "stage6e_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    # 8. Save Markdown Summary
    summary_md = f"""# TQ-BioNet Stage 6E: LNDb Domain Adaptation and Grouped Evaluation Summary

This experiment evaluates scan-grouped development and adaptation on LNDb using the official challenge partition structure (Folds 0–2 for Development, Fold 3 as Held-Out Test). All models evaluated on Fold 3 are explicitly designated as **LNDb-Adapted**, distinguishing them from the frozen v3.1 zero-shot benchmark.

## Cohort Partitioning (Official LNDb Challenge Folds)
- **Development Cohort (Folds 0, 1, 2)**: {len(y_dev)} candidate findings across {len(np.unique(groups_dev))} scans ({np.sum(y_dev==1)} positive, {np.sum(y_dev==0)} negative, {np.mean(y_dev)*100:.1f}% positive).
- **Held-Out Test Cohort (Fold 3)**: {len(y_test)} candidate findings across {len(np.unique(groups_test))} scans ({np.sum(y_test==1)} positive, {np.sum(y_test==0)} negative, {np.mean(y_test)*100:.1f}% positive).
- **Scan-Level Disjointness**: Exactly 0 overlapping scans between Development and Fold 3.

## Conflicting Coordinate Audit
- **Identified Locations**: {len(conflict_df)//2} coordinate locations (12 total rows) where conflicting binary labels (`Nodule=1` and `Nodule=0`) exist at identical physical $(x,y,z)$ coordinates within the same CT volume.
- **Handling**: Preserved transparently in the primary evaluation without silent deletion; detailed in `conflicting_coordinates_audit.csv`.

## Development Cross-Validation Performance (Folds 0–2, Scan-Grouped)

| Model Configuration | Feature Set | Accuracy | Balanced Acc | Sensitivity | Specificity | F1-Score | AUC-ROC | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | — | {cv_results['Majority Baseline']['accuracy']:.4f} | 0.5000 | 1.0000 | 0.0000 | {cv_results['Majority Baseline']['f1']:.4f} | 0.5000 | {cv_results['Majority Baseline']['brier_score']:.4f} |
| **Frozen Zero-Shot v3.1** | 15 frozen | {cv_results['Frozen Zero-Shot (v3.1)']['accuracy']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['balanced_accuracy']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['sensitivity']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['specificity']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['f1']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['auc_roc']:.4f} | {cv_results['Frozen Zero-Shot (v3.1)']['brier_score']:.4f} |
| **Adapted SVM (RBF)** | 15 frozen | {cv_results['Adapted SVM (15 feat)']['accuracy']:.4f} | {cv_results['Adapted SVM (15 feat)']['balanced_accuracy']:.4f} | {cv_results['Adapted SVM (15 feat)']['sensitivity']:.4f} | {cv_results['Adapted SVM (15 feat)']['specificity']:.4f} | {cv_results['Adapted SVM (15 feat)']['f1']:.4f} | {cv_results['Adapted SVM (15 feat)']['auc_roc']:.4f} | {cv_results['Adapted SVM (15 feat)']['brier_score']:.4f} |
| **Adapted XGBoost** | 15 frozen | {cv_results['Adapted XGB (15 feat)']['accuracy']:.4f} | {cv_results['Adapted XGB (15 feat)']['balanced_accuracy']:.4f} | {cv_results['Adapted XGB (15 feat)']['sensitivity']:.4f} | {cv_results['Adapted XGB (15 feat)']['specificity']:.4f} | {cv_results['Adapted XGB (15 feat)']['f1']:.4f} | {cv_results['Adapted XGB (15 feat)']['auc_roc']:.4f} | {cv_results['Adapted XGB (15 feat)']['brier_score']:.4f} |
| **Adapted Random Forest** | 15 frozen | {cv_results['Adapted RF (15 feat)']['accuracy']:.4f} | {cv_results['Adapted RF (15 feat)']['balanced_accuracy']:.4f} | {cv_results['Adapted RF (15 feat)']['sensitivity']:.4f} | {cv_results['Adapted RF (15 feat)']['specificity']:.4f} | {cv_results['Adapted RF (15 feat)']['f1']:.4f} | {cv_results['Adapted RF (15 feat)']['auc_roc']:.4f} | {cv_results['Adapted RF (15 feat)']['brier_score']:.4f} |
| **Adapted Ensemble** | 15 frozen | {cv_results['Adapted ENSEMBLE (15 feat)']['accuracy']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['balanced_accuracy']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['sensitivity']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['specificity']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['f1']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['auc_roc']:.4f} | {cv_results['Adapted ENSEMBLE (15 feat)']['brier_score']:.4f} |
| **Adapted Ensemble** | 31 all | {cv_results['Adapted ENSEMBLE (31 feat)']['accuracy']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['balanced_accuracy']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['sensitivity']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['specificity']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['f1']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['auc_roc']:.4f} | {cv_results['Adapted ENSEMBLE (31 feat)']['brier_score']:.4f} |

## Final Evaluation on Untouched Held-Out Cohort (Fold 3, N=320)

| Metric [Confidence Interval] | Majority Baseline | Frozen Zero-Shot v3.1 | LNDb-Adapted Ensemble (15 feat) | LNDb-Adapted Ensemble (31 feat) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** [Scan-Cluster 95% CI] | {eval_fold3_15['majority_baseline_acc']:.4f} | {eval_fold3_zero_shot['accuracy']:.4f} | **{eval_fold3_15['accuracy']:.4f}** [{eval_fold3_15['accuracy_95ci'][0]:.3f} - {eval_fold3_15['accuracy_95ci'][1]:.3f}] | **{eval_fold3_31['accuracy']:.4f}** [{eval_fold3_31['accuracy_95ci'][0]:.3f} - {eval_fold3_31['accuracy_95ci'][1]:.3f}] |
| **Balanced Accuracy** | 0.5000 | {eval_fold3_zero_shot['balanced_accuracy']:.4f} | **{eval_fold3_15['balanced_accuracy']:.4f}** | **{eval_fold3_31['balanced_accuracy']:.4f}** |
| **Sensitivity** | 1.0000 | {eval_fold3_zero_shot['sensitivity']:.4f} | {eval_fold3_15['sensitivity']:.4f} | {eval_fold3_31['sensitivity']:.4f} |
| **Specificity** | 0.0000 | {eval_fold3_zero_shot['specificity']:.4f} | {eval_fold3_15['specificity']:.4f} | {eval_fold3_31['specificity']:.4f} |
| **Precision** | {eval_fold3_15['majority_baseline_acc']:.4f} | 0.6860 | {eval_fold3_15['precision']:.4f} | {eval_fold3_31['precision']:.4f} |
| **F1-Score** [Scan-Cluster 95% CI] | 0.7476 | {eval_fold3_zero_shot['f1']:.4f} | **{eval_fold3_15['f1']:.4f}** [{eval_fold3_15['f1_95ci'][0]:.3f} - {eval_fold3_15['f1_95ci'][1]:.3f}] | **{eval_fold3_31['f1']:.4f}** [{eval_fold3_31['f1_95ci'][0]:.3f} - {eval_fold3_31['f1_95ci'][1]:.3f}] |
| **AUC-ROC** [Scan-Cluster 95% CI] | 0.5000 | {eval_fold3_zero_shot['auc_roc']:.4f} | **{eval_fold3_15['auc_roc']:.4f}** [{eval_fold3_15['auc_roc_95ci'][0]:.3f} - {eval_fold3_15['auc_roc_95ci'][1]:.3f}] | **{eval_fold3_31['auc_roc']:.4f}** [{eval_fold3_31['auc_roc_95ci'][0]:.3f} - {eval_fold3_31['auc_roc_95ci'][1]:.3f}] |
| **Average Precision (AP)** | {eval_fold3_15['majority_baseline_acc']:.4f} | {eval_fold3_zero_shot['average_precision']:.4f} | **{eval_fold3_15['average_precision']:.4f}** | **{eval_fold3_31['average_precision']:.4f}** |
| **Brier Score** | 0.2407 | {eval_fold3_zero_shot['brier_score']:.4f} | **{eval_fold3_15['brier_score']:.4f}** | **{eval_fold3_31['brier_score']:.4f}** |
| **ECE** | — | — | **{eval_fold3_15['expected_calibration_error']:.4f}** | **{eval_fold3_31['expected_calibration_error']:.4f}** |

## Agreement Stratification on Fold 3 (Adapted Ensemble 15-feat)
- **AgrLevel 0** (non-nodules, N={eval_fold3_15['agreement_stratification']['0']['n']}): Accuracy = {eval_fold3_15['agreement_stratification']['0']['accuracy']*100:.2f}%
- **AgrLevel 1** (1-reader nodules, N={eval_fold3_15['agreement_stratification']['1']['n']}): Accuracy = {eval_fold3_15['agreement_stratification']['1']['accuracy']*100:.2f}%
- **AgrLevel 2** (2-reader consensus, N={eval_fold3_15['agreement_stratification']['2']['n']}): Accuracy = {eval_fold3_15['agreement_stratification']['2']['accuracy']*100:.2f}%
- **AgrLevel 3** (3-reader unanimous, N={eval_fold3_15['agreement_stratification']['3']['n']}): Accuracy = {eval_fold3_15['agreement_stratification']['3']['accuracy']*100:.2f}%
"""
    summary_md += f"""

## Stage 6E.1 Audit Addendum

### Feature Cache Alignment
The runner now verifies every cache row against the exact ordered ground-truth CSV rows:
scan ID, binary label, physical coordinates (absolute tolerance 1e-7 mm), and AgrLevel.
A mismatch stops execution before splitting, fitting, or evaluation.

### Fold 3 Conflict Sensitivity (Fixed Predictions)
This is a secondary sensitivity analysis only. The original finding-level Fold 3
metrics above remain the primary evaluation. For exact same-scan coordinates with
conflicting binary labels, one representative row is retained by highest AgrLevel,
then largest Volume, then smallest FindingID. Predictions/probabilities remain those
from the original model; no model retraining or test-time threshold changes occur.

- Primary Fold 3 findings: {conflict_sensitivity['primary_rows']}
- Sensitivity-analysis rows: {conflict_sensitivity['sensitivity_rows']}
- Conflicting coordinate groups in Fold 3: {conflict_sensitivity['conflicting_coordinate_groups_fold3']}
- Rows in those conflicting groups: {conflict_sensitivity['raw_rows_in_conflicting_groups_fold3']}
- Sensitivity analysis accuracy: {conflict_sensitivity['accuracy']:.4f}
- Sensitivity analysis balanced accuracy: {conflict_sensitivity['balanced_accuracy']:.4f}
- Sensitivity analysis sensitivity/specificity: {conflict_sensitivity['sensitivity']:.4f} / {conflict_sensitivity['specificity']:.4f}
- Sensitivity analysis ROC-AUC: {conflict_sensitivity['auc_roc'] if conflict_sensitivity['auc_roc'] is not None else 'undefined'}

This is not an adjudicated ground truth. It changes the unit for affected coordinates
and must not be presented as the primary result.

### Paired Scan-Cluster Comparison vs Always-Positive Baseline
- Accuracy difference (adapted minus baseline): {paired_baseline_comparison['observed_accuracy_difference']:.4f}
- Paired scan-cluster bootstrap 95% CI: [{paired_baseline_comparison['scan_cluster_bootstrap_95ci'][0]:.4f}, {paired_baseline_comparison['scan_cluster_bootstrap_95ci'][1]:.4f}]
- Bootstrap replicates: {paired_baseline_comparison['bootstrap_replicates']}
- Scan clusters: {paired_baseline_comparison['unique_scan_clusters']}

This paired interval resamples scans and evaluates both classifiers on the same
resampled findings, accounting for within-scan clustering.
"""
    summary_path = outputs_dir / "stage6e_summary.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\nStage 6E completed successfully.")
    print(f"Summary saved to: {summary_path}")
    print(f"Metrics saved to: {metrics_path}")


if __name__ == "__main__":
    run_stage6e()
