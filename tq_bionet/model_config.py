"""
TQ-BioNet v3.1 Authoritative Model and Feature Configuration.

Single source of truth for:
- 31-dimensional full feature schema
- 15-dimensional frozen selected feature schema
- Authoritative classifier hyperparameters (SVM, XGBoost, Random Forest)
- Scaler contract: SVM strictly on StandardScaler, Trees strictly on raw features
- Ensemble voting and decision threshold
- Probability calibration metrics (Brier score, ECE, calibration curves)
- Model artifact serialization with provenance manifest
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss


FROZEN_31_FEATURES = [
    'H0_count',
    'H0_entropy',
    'H0_max_persistence',
    'H0_mean_persistence',
    'H0_std_persistence',
    'H0_total_persistence',
    'H1_count',
    'H1_entropy',
    'H1_max_persistence',
    'H1_mean_persistence',
    'H1_std_persistence',
    'H1_total_persistence',
    'blobness_ratio',
    'fractal_dimension',
    'hessian_L1',
    'hessian_L2',
    'hessian_L3',
    'lacunarity_2',
    'lacunarity_4',
    'lacunarity_8',
    'quantum_eigenvalue_0',
    'quantum_eigenvalue_1',
    'quantum_eigenvalue_2',
    'quantum_eigenvalue_3',
    'quantum_eigenvalue_4',
    'quantum_eigenvalue_5',
    'quantum_eigenvalue_6',
    'quantum_eigenvalue_7',
    'quantum_eigenvalue_8',
    'quantum_eigenvalue_9',
    'vesselness_ratio'
]

FROZEN_15_SELECTED_FEATURES = [
    'H0_entropy',
    'H0_total_persistence',
    'H1_count',
    'H1_total_persistence',
    'blobness_ratio',
    'fractal_dimension',
    'hessian_L1',
    'hessian_L2',
    'hessian_L3',
    'lacunarity_4',
    'lacunarity_8',
    'quantum_eigenvalue_0',
    'quantum_eigenvalue_1',
    'quantum_eigenvalue_2',
    'vesselness_ratio'
]

DEFAULT_DECISION_THRESHOLD = 0.5


def get_selected_feature_indices(full_feature_names=None):
    """Returns the integer indices of the 15 selected features within the 31 schema."""
    if full_feature_names is None:
        full_feature_names = FROZEN_31_FEATURES
    return [full_feature_names.index(f) for f in FROZEN_15_SELECTED_FEATURES]


def prune_to_selected_features(X_all, full_feature_names=None):
    """Prunes a (N, 31) feature matrix down to (N, 15) using the frozen schema."""
    indices = get_selected_feature_indices(full_feature_names)
    X_arr = np.asarray(X_all, dtype=np.float64)
    if X_arr.ndim != 2 or X_arr.shape[1] != len(FROZEN_31_FEATURES):
        raise ValueError(f"X_all must have shape (N, {len(FROZEN_31_FEATURES)})")
    return X_arr[:, indices]


def create_frozen_classifiers(random_state=42):
    """
    Constructs the authoritative, frozen classifier instances:
    - SVM: RBF kernel, C=100.0, gamma='scale'
    - XGBoost: n_estimators=200, max_depth=5, lr=0.01
    - Random Forest: n_estimators=150, max_depth=4
    """
    svm = SVC(
        C=100.0,
        gamma='scale',
        probability=True,
        random_state=random_state
    )
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.01,
        eval_metric='logloss',
        random_state=random_state
    )
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=4,
        random_state=random_state
    )
    return svm, xgb, rf


def fit_frozen_pipeline(X_dev_selected, y_dev, random_state=42):
    """
    Trains the development pipeline adhering strictly to the scaling contract:
    - Fits a single StandardScaler on X_dev_selected.
    - Trains SVM strictly on scaled features.
    - Trains XGBoost and Random Forest strictly on raw features.
    """
    X_dev_selected = np.asarray(X_dev_selected, dtype=np.float64)
    y_dev = np.asarray(y_dev, dtype=int)
    if X_dev_selected.shape[1] != len(FROZEN_15_SELECTED_FEATURES):
        raise ValueError(f"Input must have {len(FROZEN_15_SELECTED_FEATURES)} columns")

    scaler = StandardScaler()
    X_dev_scaled = scaler.fit_transform(X_dev_selected)

    svm, xgb, rf = create_frozen_classifiers(random_state=random_state)
    svm.fit(X_dev_scaled, y_dev)
    xgb.fit(X_dev_selected, y_dev)
    rf.fit(X_dev_selected, y_dev)

    return svm, xgb, rf, scaler


def predict_ensemble(svm, xgb, rf, scaler, X_selected, threshold=DEFAULT_DECISION_THRESHOLD):
    """
    Computes ensemble predictions adhering strictly to the scaling contract:
    P_ensemble = (P_svm + P_xgb + P_rf) / 3.0
    """
    X_selected = np.asarray(X_selected, dtype=np.float64)
    if X_selected.shape[1] != len(FROZEN_15_SELECTED_FEATURES):
        raise ValueError(f"Input must have {len(FROZEN_15_SELECTED_FEATURES)} columns")

    X_scaled = scaler.transform(X_selected)
    p_svm = svm.predict_proba(X_scaled)[:, 1]
    p_xgb = xgb.predict_proba(X_selected)[:, 1]
    p_rf = rf.predict_proba(X_selected)[:, 1]

    p_ensemble = (p_svm + p_xgb + p_rf) / 3.0
    y_pred = (p_ensemble >= threshold).astype(int)

    return {
        'ensemble_prob': p_ensemble,
        'svm_prob': p_svm,
        'xgb_prob': p_xgb,
        'rf_prob': p_rf,
        'y_pred': y_pred
    }


def compute_calibration_metrics(y_true, y_prob, n_bins=10):
    """
    Computes rigorous calibration diagnostics:
    - Brier score: Mean squared error of probabilities relative to outcomes
    - Expected Calibration Error (ECE): Weighted average difference between confidence and accuracy
    - Reliability curve bin coordinates
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=np.float64)
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have identical lengths")

    brier = float(brier_score_loss(y_true, y_prob))

    # Compute ECE and reliability points
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    # Clip index 10 to bin 9
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    bin_accuracies = []
    bin_confidences = []
    bin_counts = []
    ece = 0.0
    n_samples = len(y_true)

    for b in range(n_bins):
        mask = (bin_indices == b)
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            acc = float(np.mean(y_true[mask]))
            conf = float(np.mean(y_prob[mask]))
            bin_accuracies.append(acc)
            bin_confidences.append(conf)
            ece += (count / n_samples) * abs(acc - conf)
        else:
            bin_accuracies.append(0.0)
            bin_confidences.append(float((bins[b] + bins[b + 1]) / 2.0))

    return {
        'brier_score': brier,
        'expected_calibration_error': float(ece),
        'bin_accuracies': bin_accuracies,
        'bin_confidences': bin_confidences,
        'bin_counts': bin_counts
    }
