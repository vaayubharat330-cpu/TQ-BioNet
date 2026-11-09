"""
Tests for Stage 7: Independent Validation Audit of Held-Out LUNA16 Subsets 6-9.

Certifies:
1. Frozen pipeline bundle integrity, artifact hashes, and schema freeze.
2. Complete SeriesUID disjointness (zero leakage) between Development (Subsets 0-5)
   and Validation (Subsets 6-9) cohorts.
3. Prediction integrity in validation_predictions.csv (shape, probabilities, soft voting, thresholding).
4. Exact numeric reconciliation of metrics, confusion matrix, and ECE against JSON and Markdown artifacts.
5. Per-subset breakdown stability across Subsets 6, 7, 8, and 9.
6. Wilson score and scan-cluster bootstrap interval reproducibility.
7. End-to-end forward pass equivalence using disk-loaded frozen models on cached validation features.
"""

import json
import hashlib
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import (
    accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    brier_score_loss,
)

from tq_bionet.model_config import (
    FROZEN_31_FEATURES,
    FROZEN_15_SELECTED_FEATURES,
    DEFAULT_DECISION_THRESHOLD,
    prune_to_selected_features,
    predict_ensemble,
    compute_calibration_metrics,
)
from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_cluster_bootstrap_ci

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FROZEN_DIR = OUTPUTS_DIR / "frozen_v3_1_pipeline"
CACHE_DIR = PROJECT_ROOT / "luna16_data" / "cache" / "tq_bionet_v3_1"


def test_frozen_model_bundle_integrity_and_provenance():
    """Verify that the frozen v3.1 model bundle matches all manifest hashes and schema contracts."""
    manifest_path = FROZEN_DIR / "pipeline_manifest.json"
    assert manifest_path.exists(), "pipeline_manifest.json missing from frozen bundle"

    with open(manifest_path) as f:
        manifest = json.load(f)

    assert manifest["pipeline_version"] == "v3.1"
    assert manifest["decision_threshold"] == DEFAULT_DECISION_THRESHOLD
    assert manifest["selected_features_15"] == FROZEN_15_SELECTED_FEATURES
    assert manifest["full_features_31"] == FROZEN_31_FEATURES

    file_mapping = {
        "scaler": "scaler.joblib",
        "svm": "svm_model.joblib",
        "xgb": "xgb_model.joblib",
        "rf": "rf_model.joblib",
    }

    for key, filename in file_mapping.items():
        file_path = FROZEN_DIR / filename
        assert file_path.exists(), f"Model artifact {filename} missing"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        expected_hash = manifest["artifact_hashes"][key]
        assert actual_hash == expected_hash, (
            f"Hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}"
        )


def test_development_validation_split_integrity_zero_leakage():
    """Verify that development (0-5) and validation (6-9) cohorts have strictly zero SeriesUID overlap."""
    assert CACHE_DIR.exists(), f"Cache directory {CACHE_DIR} must exist for split audit"

    dev_groups = set()
    dev_sample_count = 0
    for sub in range(6):
        sub_dir = CACHE_DIR / f"subset{sub}"
        assert sub_dir.exists(), f"Subset {sub} cache missing"
        groups = np.load(sub_dir / "groups.npy", allow_pickle=True)
        dev_groups.update(groups.tolist())
        dev_sample_count += len(groups)

    val_groups = set()
    val_sample_count = 0
    for sub in range(6, 10):
        sub_dir = CACHE_DIR / f"subset{sub}"
        assert sub_dir.exists(), f"Subset {sub} cache missing"
        groups = np.load(sub_dir / "groups.npy", allow_pickle=True)
        val_groups.update(groups.tolist())
        val_sample_count += len(groups)

    overlap = dev_groups.intersection(val_groups)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping scans between development and validation cohorts!"
    assert len(dev_groups) == 365, f"Expected 365 development scans, got {len(dev_groups)}"
    assert len(val_groups) == 236, f"Expected 236 validation scans, got {len(val_groups)}"
    assert dev_sample_count == 1446, f"Expected 1446 development samples, got {dev_sample_count}"
    assert val_sample_count == 926, f"Expected 926 validation samples, got {val_sample_count}"


def test_validation_predictions_csv_internal_consistency():
    """Verify predictions CSV schema, zero nulls, exact soft voting math, and decision threshold."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    assert preds_path.exists(), "validation_predictions.csv missing"
    df = pd.read_csv(preds_path)

    expected_cols = [
        "seriesuid", "subset", "x", "y", "z", "true_label",
        "svm_prob", "xgb_prob", "rf_prob", "ensemble_prob", "predicted_label"
    ]
    assert list(df.columns) == expected_cols
    assert len(df) == 926
    assert df.isnull().sum().sum() == 0

    # Label counts: perfectly balanced 1:1 candidate sampling
    assert (df["true_label"] == 1).sum() == 463
    assert (df["true_label"] == 0).sum() == 463

    # All probabilities within [0, 1]
    for col in ["svm_prob", "xgb_prob", "rf_prob", "ensemble_prob"]:
        assert (df[col] >= 0.0).all() and (df[col] <= 1.0).all()

    # Soft voting ensemble math: (svm + xgb + rf) / 3
    expected_ensemble = (df["svm_prob"] + df["xgb_prob"] + df["rf_prob"]) / 3.0
    np.testing.assert_allclose(df["ensemble_prob"].values, expected_ensemble.values, atol=1e-6)

    # Predicted label matching threshold 0.50
    expected_labels = (df["ensemble_prob"] >= 0.5).astype(int)
    np.testing.assert_array_equal(df["predicted_label"].values, expected_labels.values)


def test_confusion_matrix_reconciliation():
    """Verify confusion matrix counts match across CSV, JSON, and Summary MD."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    df = pd.read_csv(preds_path)

    tn, fp, fn, tp = confusion_matrix(df["true_label"], df["predicted_label"]).ravel()
    assert (tn, fp, fn, tp) == (420, 43, 84, 379)

    cm_path = OUTPUTS_DIR / "validation_confusion_matrix.csv"
    assert cm_path.exists(), "validation_confusion_matrix.csv missing"
    df_cm = pd.read_csv(cm_path).set_index("metric")["value"].to_dict()

    assert df_cm["true_negative"] == 420
    assert df_cm["false_positive"] == 43
    assert df_cm["false_negative"] == 84
    assert df_cm["true_positive"] == 379

    summary_path = OUTPUTS_DIR / "validation_summary.md"
    assert summary_path.exists(), "validation_summary.md missing"
    summary_text = summary_path.read_text()
    assert "True Negatives**: 420" in summary_text
    assert "False Positives**: 43" in summary_text
    assert "False Negatives**: 84" in summary_text
    assert "True Positives**: 379" in summary_text


def test_recomputed_metrics_match_stored_validation_metrics_json():
    """Recompute all classification and calibration metrics from predictions and check exact JSON match."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    df = pd.read_csv(preds_path)
    y_true = df["true_label"].values

    metrics_path = OUTPUTS_DIR / "validation_metrics.json"
    assert metrics_path.exists(), "validation_metrics.json missing"
    with open(metrics_path) as f:
        saved = json.load(f)

    model_configs = [
        ("VotingEnsemble", df["ensemble_prob"].values, df["predicted_label"].values),
        ("SVM", df["svm_prob"].values, (df["svm_prob"].values >= 0.5).astype(int)),
        ("XGBoost", df["xgb_prob"].values, (df["xgb_prob"].values >= 0.5).astype(int)),
    ]

    for model_name, y_prob, y_pred in model_configs:
        acc = accuracy_score(y_true, y_pred)
        sens = recall_score(y_true, y_pred)
        tn, fp, _, _ = confusion_matrix(y_true, y_pred).ravel()
        spec = tn / (tn + fp)
        prec = precision_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        auc = roc_auc_score(y_true, y_prob)
        cal = compute_calibration_metrics(y_true, y_prob)

        s = saved[model_name]
        assert np.isclose(acc, s["accuracy"], atol=1e-6)
        assert np.isclose(sens, s["sensitivity"], atol=1e-6)
        assert np.isclose(spec, s["specificity"], atol=1e-6)
        assert np.isclose(prec, s["precision"], atol=1e-6)
        assert np.isclose(f1, s["f1"], atol=1e-6)
        assert np.isclose(auc, s["auc"], atol=1e-6)
        assert np.isclose(cal["brier_score"], s["brier_score"], atol=1e-6)
        assert np.isclose(cal["expected_calibration_error"], s["expected_calibration_error"], atol=1e-6)


def test_wilson_confidence_intervals_match_json():
    """Recompute Wilson score intervals for proportion metrics and verify match with saved JSON."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    df = pd.read_csv(preds_path)
    y_true = df["true_label"].values

    with open(OUTPUTS_DIR / "validation_metrics.json") as f:
        saved = json.load(f)

    for model_name, prob_col in [("VotingEnsemble", "ensemble_prob"), ("SVM", "svm_prob"), ("XGBoost", "xgb_prob")]:
        y_prob = df[prob_col].values
        y_pred = (y_prob >= 0.5).astype(int)

        sens_low, sens_high = compute_wilson_ci(int(np.sum((y_pred == 1) & (y_true == 1))), int(np.sum(y_true == 1)))
        spec_low, spec_high = compute_wilson_ci(int(np.sum((y_pred == 0) & (y_true == 0))), int(np.sum(y_true == 0)))
        prec_low, prec_high = compute_wilson_ci(int(np.sum((y_pred == 1) & (y_true == 1))), int(np.sum(y_pred == 1)))

        s = saved[model_name]
        np.testing.assert_allclose([sens_low, sens_high], s["sensitivity_ci"], atol=1e-6)
        np.testing.assert_allclose([spec_low, spec_high], s["specificity_ci"], atol=1e-6)
        np.testing.assert_allclose([prec_low, prec_high], s["precision_ci"], atol=1e-6)


def test_scan_cluster_bootstrap_confidence_intervals_match_json():
    """Recompute scan-cluster bootstrap intervals for Voting Ensemble and verify exact match with saved JSON."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    df = pd.read_csv(preds_path)
    y_true = df["true_label"].values
    groups = df["seriesuid"].values
    y_prob = df["ensemble_prob"].values
    y_pred = df["predicted_label"].values

    with open(OUTPUTS_DIR / "validation_metrics.json") as f:
        saved = json.load(f)

    ens_saved = saved["VotingEnsemble"]

    acc_ci = compute_cluster_bootstrap_ci(y_true, y_pred, groups, accuracy_score, num_resamples=1000, random_seed=42)
    f1_ci = compute_cluster_bootstrap_ci(y_true, y_pred, groups, f1_score, num_resamples=1000, random_seed=42)
    auc_ci = compute_cluster_bootstrap_ci(y_true, y_prob, groups, roc_auc_score, num_resamples=1000, random_seed=42)

    np.testing.assert_allclose(acc_ci, ens_saved["accuracy_ci"], atol=1e-6)
    np.testing.assert_allclose(f1_ci, ens_saved["f1_ci"], atol=1e-6)
    np.testing.assert_allclose(auc_ci, ens_saved["auc_ci"], atol=1e-6)


def test_per_subset_metrics_reproducibility():
    """Verify that each subset-specific JSON metric file matches recomputation from predictions CSV."""
    df = pd.read_csv(OUTPUTS_DIR / "validation_predictions.csv")

    for sub in [6, 7, 8, 9]:
        sub_json = OUTPUTS_DIR / f"validation_subset{sub}_metrics.json"
        assert sub_json.exists(), f"validation_subset{sub}_metrics.json missing"
        with open(sub_json) as f:
            saved_sub = json.load(f)

        sub_df = df[df["subset"] == sub]
        y_true = sub_df["true_label"].values
        y_prob = sub_df["ensemble_prob"].values
        y_pred = sub_df["predicted_label"].values

        acc = accuracy_score(y_true, y_pred)
        sens = recall_score(y_true, y_pred)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        spec = tn / (tn + fp)
        auc = roc_auc_score(y_true, y_prob)

        s_ens = saved_sub["VotingEnsemble"]
        s_cm = saved_sub["confusion_matrix"]

        assert np.isclose(acc, s_ens["accuracy"], atol=1e-6)
        assert np.isclose(sens, s_ens["sensitivity"], atol=1e-6)
        assert np.isclose(spec, s_ens["specificity"], atol=1e-6)
        assert np.isclose(auc, s_ens["auc"], atol=1e-6)
        assert (tn, fp, fn, tp) == (s_cm["tn"], s_cm["fp"], s_cm["fn"], s_cm["tp"])


def test_frozen_bundle_forward_pass_equivalence():
    """Load the frozen serialized models from disk and verify that running inference on cached features matches exactly."""
    scaler = joblib.load(FROZEN_DIR / "scaler.joblib")
    svm = joblib.load(FROZEN_DIR / "svm_model.joblib")
    xgb = joblib.load(FROZEN_DIR / "xgb_model.joblib")
    rf = joblib.load(FROZEN_DIR / "rf_model.joblib")

    X_val = np.concatenate([np.load(CACHE_DIR / f"subset{s}" / "X.npy") for s in range(6, 10)], axis=0)
    X_val_pruned = prune_to_selected_features(X_val)

    preds = predict_ensemble(svm, xgb, rf, scaler, X_val_pruned, threshold=0.5)

    df_saved = pd.read_csv(OUTPUTS_DIR / "validation_predictions.csv")
    np.testing.assert_allclose(preds["svm_prob"], df_saved["svm_prob"].values, atol=1e-6)
    np.testing.assert_allclose(preds["xgb_prob"], df_saved["xgb_prob"].values, atol=1e-5)
    np.testing.assert_allclose(preds["rf_prob"], df_saved["rf_prob"].values, atol=1e-6)
    np.testing.assert_allclose(preds["ensemble_prob"], df_saved["ensemble_prob"].values, atol=1e-6)
    np.testing.assert_array_equal(preds["y_pred"], df_saved["predicted_label"].values)
