"""
Tests for Cold-Cache Reproducibility of TQ-BioNet v3.1.

Certifies:
1. LUNA16 Subsets 6-9 rebuilt feature caches match historical data structures.
2. LUNA16 independent validation predictions replicate with 100% label concordance (926/926).
3. LNDb 1.0mm zero-shot external validation replicates with 100% label concordance (1219/1219).
4. LNDb metrics and confusion matrix replicate exact values (Acc 54.72%, Sens 51.04%, Spec 60.98%, AUC 0.5729).
5. Agreement level stratification matches across all levels (AgrLevel 0, 1, 2, 3).
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LUNA_CACHE_DIR = PROJECT_ROOT / "luna16_data" / "cache" / "tq_bionet_v3_1"
LNDB_COLD_DIR = OUTPUTS_DIR / "cold_cache_lndb_evaluation"
LNDB_HIST_DIR = OUTPUTS_DIR / "lndb_external_validation_v3_1"


def test_luna16_rebuilt_cache_integrity():
    """Verify that rebuilt LUNA16 validation subsets (6-9) exist and have expected dimensions."""
    total_samples = 0
    total_scans = set()
    expected_samples = {6: 258, 7: 222, 8: 236, 9: 210}

    for sub, count in expected_samples.items():
        sub_dir = LUNA_CACHE_DIR / f"subset{sub}"
        assert sub_dir.exists(), f"Rebuilt cache for subset {sub} missing"
        
        X = np.load(sub_dir / "X.npy")
        y = np.load(sub_dir / "y.npy")
        groups = np.load(sub_dir / "groups.npy", allow_pickle=True)
        coords = np.load(sub_dir / "coords.npy")

        assert X.shape == (count, 31), f"Unexpected X shape for subset {sub}"
        assert y.shape == (count,), f"Unexpected y shape for subset {sub}"
        assert groups.shape == (count,), f"Unexpected groups shape for subset {sub}"
        assert coords.shape == (count, 3), f"Unexpected coords shape for subset {sub}"

        total_samples += count
        total_scans.update(groups.tolist())

    assert total_samples == 926
    assert len(total_scans) == 236


def test_luna16_cold_cache_prediction_reproduction():
    """Verify that fresh independent validation predictions match the audited 926 candidate cohort and historical predictions."""
    preds_path = OUTPUTS_DIR / "validation_predictions.csv"
    hist_path = OUTPUTS_DIR / "stage7_validation_audit" / "historical_validation_predictions_baseline.csv"
    assert preds_path.exists(), "validation_predictions.csv missing"
    assert hist_path.exists(), "historical_validation_predictions_baseline.csv missing"

    df = pd.read_csv(preds_path)
    hist_df = pd.read_csv(hist_path)

    assert len(df) == 926
    assert len(hist_df) == 926
    assert set(df["subset"].unique()) == {6, 7, 8, 9}
    assert (df["predicted_label"].isin([0, 1])).all()

    # Exact prediction alignment against preserved historical predictions
    np.testing.assert_array_equal(df["seriesuid"].values, hist_df["seriesuid"].values)
    np.testing.assert_array_equal(df["true_label"].values, hist_df["true_label"].values)
    np.testing.assert_array_equal(df["predicted_label"].values, hist_df["predicted_label"].values)

    # Probabilities agree within floating point tolerance
    np.testing.assert_allclose(df["ensemble_prob"].values, hist_df["ensemble_prob"].values, atol=1e-10)
    np.testing.assert_allclose(df["svm_prob"].values, hist_df["svm_prob"].values, atol=1e-10)
    np.testing.assert_allclose(df["xgb_prob"].values, hist_df["xgb_prob"].values, atol=1e-10)
    np.testing.assert_allclose(df["rf_prob"].values, hist_df["rf_prob"].values, atol=1e-10)

    # Reconcile confusion matrix
    y_true = df["true_label"].values
    y_pred = df["predicted_label"].values
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))

    assert (tn, fp, fn, tp) == (420, 43, 84, 379)
    acc = (tp + tn) / len(df)
    assert np.isclose(acc, 0.86285097, atol=1e-5)


def test_lndb_cold_cache_predictions_exact_match():
    """Verify that cold-cache LNDb predictions replicate historical Stage 6B predictions 100%."""
    assert LNDB_COLD_DIR.exists(), "cold_cache_lndb_evaluation missing"
    assert LNDB_HIST_DIR.exists(), "lndb_external_validation_v3_1 missing"

    cold_df = pd.read_csv(LNDB_COLD_DIR / "lndb_predictions.csv")
    hist_df = pd.read_csv(LNDB_HIST_DIR / "lndb_predictions.csv")

    assert len(cold_df) == 1219
    assert len(hist_df) == 1219

    # Identity alignment
    np.testing.assert_array_equal(cold_df["LNDbID"].values, hist_df["LNDbID"].values)
    np.testing.assert_array_equal(cold_df["FindingID"].values, hist_df["FindingID"].values)
    np.testing.assert_array_equal(cold_df["y_true"].values, hist_df["y_true"].values)

    # Predictions 100% match
    np.testing.assert_array_equal(cold_df["ensemble_prediction"].values, hist_df["ensemble_prediction"].values)
    np.testing.assert_array_equal(cold_df["svm_prediction"].values, hist_df["svm_prediction"].values)
    np.testing.assert_array_equal(cold_df["xgboost_prediction"].values, hist_df["xgboost_prediction"].values)
    np.testing.assert_array_equal(cold_df["random_forest_prediction"].values, hist_df["random_forest_prediction"].values)

    # Probabilities agree within floating point tolerance
    np.testing.assert_allclose(cold_df["ensemble_probability"].values, hist_df["ensemble_probability"].values, atol=1e-10)
    np.testing.assert_allclose(cold_df["svm_probability"].values, hist_df["svm_probability"].values, atol=1e-10)
    np.testing.assert_allclose(cold_df["xgb_probability"].values, hist_df["xgb_probability"].values, atol=1e-10)
    np.testing.assert_allclose(cold_df["rf_probability"].values, hist_df["rf_probability"].values, atol=1e-10)


def test_lndb_cold_cache_metrics_exact_match():
    """Verify that cold-cache LNDb metrics replicate historical Stage 6B metrics exactly."""
    with open(LNDB_COLD_DIR / "lndb_metrics.json") as f:
        cold_metrics = json.load(f)
    with open(LNDB_HIST_DIR / "lndb_metrics.json") as f:
        hist_metrics = json.load(f)

    cold_ens = cold_metrics["models"]["Ensemble"]
    hist_ens = hist_metrics["models"]["Ensemble"]

    assert cold_ens["confusion_matrix"] == {"tn": 275, "fp": 176, "fn": 376, "tp": 392}
    assert hist_ens["confusion_matrix"] == {"tn": 275, "fp": 176, "fn": 376, "tp": 392}

    assert np.isclose(cold_ens["accuracy"], hist_ens["accuracy"], atol=1e-6)
    assert np.isclose(cold_ens["sensitivity"], hist_ens["sensitivity"], atol=1e-6)
    assert np.isclose(cold_ens["specificity"], hist_ens["specificity"], atol=1e-6)
    assert np.isclose(cold_ens["precision"], hist_ens["precision"], atol=1e-6)
    assert np.isclose(cold_ens["f1"], hist_ens["f1"], atol=1e-6)
    assert np.isclose(cold_ens["auc_roc"], hist_ens["auc_roc"], atol=1e-4)
    assert np.isclose(cold_ens["brier_score"], hist_ens["brier_score"], atol=1e-6)


def test_lndb_agreement_level_stratification_reproducibility():
    """Verify agreement level stratification matches historical values."""
    with open(LNDB_COLD_DIR / "lndb_metrics.json") as f:
        cold_metrics = json.load(f)
    with open(LNDB_HIST_DIR / "lndb_metrics.json") as f:
        hist_metrics = json.load(f)

    cold_strat = cold_metrics["agreement_level_stratification"]
    hist_strat = hist_metrics["agreement_level_stratification"]

    for agr in ["0", "1", "2", "3"]:
        assert cold_strat[agr]["n"] == hist_strat[agr]["n"]
        assert cold_strat[agr]["positive"] == hist_strat[agr]["positive"]
        assert np.isclose(cold_strat[agr]["ensemble_accuracy"], hist_strat[agr]["ensemble_accuracy"], atol=1e-4)
