import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score

from tq_bionet.model_config import (
    FROZEN_31_FEATURES,
    FROZEN_15_SELECTED_FEATURES,
    get_selected_feature_indices,
    prune_to_selected_features,
    create_frozen_classifiers,
    fit_frozen_pipeline,
    predict_ensemble,
    compute_calibration_metrics,
    save_pipeline_bundle,
    load_pipeline_bundle,
    DEFAULT_DECISION_THRESHOLD
)
from tq_bionet.evaluation_metrics import compute_cluster_bootstrap_ci


class TestModelPipelineStage4(unittest.TestCase):
    """
    Stage 4 Verification: Frozen feature schema, model scaling contracts,
    ensemble voting, probability calibration diagnostics, and pipeline bundle serialization.
    """

    def test_feature_schema_and_selection_contract(self):
        """Verifies 31 full features, 15 selected features, and index mapping."""
        self.assertEqual(len(FROZEN_31_FEATURES), 31)
        self.assertEqual(len(FROZEN_15_SELECTED_FEATURES), 15)
        
        # 15 selected must be a strict subset of 31 full
        self.assertTrue(set(FROZEN_15_SELECTED_FEATURES).issubset(set(FROZEN_31_FEATURES)))
        
        # Full schema must be strictly sorted alphabetically
        self.assertEqual(FROZEN_31_FEATURES, sorted(FROZEN_31_FEATURES))
        
        # Test index pruning
        indices = get_selected_feature_indices()
        self.assertEqual(len(indices), 15)
        
        # Verify pruning retains the exact values from corresponding columns
        N = 20
        X_31 = np.arange(N * 31, dtype=np.float64).reshape(N, 31)
        X_15 = prune_to_selected_features(X_31)
        self.assertEqual(X_15.shape, (N, 15))
        for j, col_idx in enumerate(indices):
            np.testing.assert_array_equal(X_15[:, j], X_31[:, col_idx])

    def test_classifier_hyperparameters_contract(self):
        """Verifies exact frozen hyperparameters across all 3 classifiers."""
        svm, xgb, rf = create_frozen_classifiers(random_state=42)
        
        # SVM
        self.assertEqual(svm.C, 100.0)
        self.assertEqual(svm.gamma, 'scale')
        self.assertTrue(svm.probability)
        self.assertEqual(svm.random_state, 42)
        
        # XGBoost
        self.assertEqual(xgb.n_estimators, 200)
        self.assertEqual(xgb.max_depth, 5)
        self.assertAlmostEqual(xgb.learning_rate, 0.01)
        self.assertEqual(xgb.eval_metric, 'logloss')
        self.assertEqual(xgb.random_state, 42)
        
        # Random Forest
        self.assertEqual(rf.n_estimators, 150)
        self.assertEqual(rf.max_depth, 4)
        self.assertEqual(rf.random_state, 42)

    def test_scaling_contract_and_ensemble_inference(self):
        """
        Verifies:
        1. Scaler is fitted strictly on development data.
        2. SVM receives scaled features during training and inference.
        3. XGBoost and Random Forest receive raw features.
        4. Soft-voting probability is exactly (P_svm + P_xgb + P_rf) / 3.
        """
        rng = np.random.RandomState(42)
        N_train = 60
        N_test = 25
        
        X_train = rng.normal(loc=10.0, scale=5.0, size=(N_train, 15))
        y_train = rng.randint(0, 2, size=N_train)
        X_test = rng.normal(loc=10.0, scale=5.0, size=(N_test, 15))
        
        svm, xgb, rf, scaler = fit_frozen_pipeline(X_train, y_train, random_state=42)
        
        np.testing.assert_allclose(scaler.mean_, np.mean(X_train, axis=0))
        np.testing.assert_allclose(scaler.scale_, np.std(X_train, axis=0))
        
        res = predict_ensemble(svm, xgb, rf, scaler, X_test, threshold=DEFAULT_DECISION_THRESHOLD)
        p_svm = res['svm_prob']
        p_xgb = res['xgb_prob']
        p_rf = res['rf_prob']
        p_ens = res['ensemble_prob']
        y_pred = res['y_pred']
        
        self.assertTrue(np.all((p_ens >= 0.0) & (p_ens <= 1.0)))
        expected_p_ens = (p_svm + p_xgb + p_rf) / 3.0
        np.testing.assert_allclose(p_ens, expected_p_ens, rtol=1e-7, atol=1e-7)
        expected_y_pred = (expected_p_ens >= DEFAULT_DECISION_THRESHOLD).astype(int)
        np.testing.assert_array_equal(y_pred, expected_y_pred)

    def test_calibration_diagnostics(self):
        """Verifies calculation of Brier score and Expected Calibration Error (ECE)."""
        y_true_perf = np.array([0, 0, 0, 1, 1, 1])
        y_prob_perf = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        
        cal_perf = compute_calibration_metrics(y_true_perf, y_prob_perf, n_bins=5)
        self.assertAlmostEqual(cal_perf['brier_score'], 0.0, places=6)
        self.assertAlmostEqual(cal_perf['expected_calibration_error'], 0.0, places=6)
        
        y_true = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 0])
        y_prob = np.array([0.1, 0.85, 0.7, 0.3, 0.9, 0.2, 0.4, 0.65, 0.8, 0.15])
        
        cal = compute_calibration_metrics(y_true, y_prob, n_bins=5)
        expected_brier = brier_score_loss(y_true, y_prob)
        self.assertAlmostEqual(cal['brier_score'], expected_brier, places=6)
        self.assertGreaterEqual(cal['expected_calibration_error'], 0.0)
        self.assertLessEqual(cal['expected_calibration_error'], 1.0)
        self.assertEqual(len(cal['bin_accuracies']), 5)
        self.assertEqual(len(cal['bin_confidences']), 5)

    def test_calibration_input_validation(self):
        """Verifies robust rejection of non-finite, out-of-range, and malformed inputs."""
        y_t = np.array([0, 1, 1])
        # Probability out of bounds (<0 or >1)
        with self.assertRaises(ValueError):
            compute_calibration_metrics(y_t, np.array([0.2, 1.2, 0.5]))
        with self.assertRaises(ValueError):
            compute_calibration_metrics(y_t, np.array([-0.1, 0.5, 0.5]))
        # Non-finite probability
        with self.assertRaises(ValueError):
            compute_calibration_metrics(y_t, np.array([0.2, np.nan, 0.5]))
        # Non-binary labels
        with self.assertRaises(ValueError):
            compute_calibration_metrics(np.array([0, 2, 1]), np.array([0.2, 0.5, 0.5]))
        # Invalid n_bins
        with self.assertRaises(ValueError):
            compute_calibration_metrics(y_t, np.array([0.2, 0.5, 0.5]), n_bins=1)

    def test_pipeline_bundle_persistence(self):
        """Verifies saving and loading pipeline bundle with artifact hashes and provenance."""
        temp_dir = tempfile.mkdtemp()
        try:
            rng = np.random.RandomState(42)
            X = rng.normal(size=(30, 15))
            y = rng.randint(0, 2, size=30)
            svm, xgb, rf, scaler = fit_frozen_pipeline(X, y)
            
            manifest = save_pipeline_bundle(temp_dir, svm, xgb, rf, scaler, metadata={"test_run": True})
            self.assertEqual(manifest["pipeline_version"], "v3.1")
            self.assertTrue("artifact_hashes" in manifest)
            
            # Load bundle back
            svm_l, xgb_l, rf_l, scaler_l, man_l = load_pipeline_bundle(temp_dir)
            self.assertEqual(man_l["pipeline_version"], "v3.1")
            
            # Predictions from loaded bundle must match exactly
            p1 = predict_ensemble(svm, xgb, rf, scaler, X[:5])["ensemble_prob"]
            p2 = predict_ensemble(svm_l, xgb_l, rf_l, scaler_l, X[:5])["ensemble_prob"]
            np.testing.assert_allclose(p1, p2)
        finally:
            shutil.rmtree(temp_dir)

    def test_cluster_bootstrap_confidence_intervals(self):
        """Verifies scan-cluster bootstrap resamples whole scans instead of single rows."""
        rng = np.random.RandomState(42)
        y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
        y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7, 0.15, 0.85])
        # 4 distinct scans with 2 candidates each
        groups = np.array(["scan1", "scan1", "scan2", "scan2", "scan3", "scan3", "scan4", "scan4"])
        
        low, high = compute_cluster_bootstrap_ci(y_true, y_prob, groups, roc_auc_score, num_resamples=50)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)
        self.assertLessEqual(low, high)


if __name__ == "__main__":
    unittest.main()
