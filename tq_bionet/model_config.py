"""
TQ-BioNet v3.1 Authoritative Model and Feature Configuration.

Single source of truth for:
- 31-dimensional full feature schema
- 15-dimensional frozen selected feature schema
- Authoritative classifier hyperparameters (SVM, XGBoost, Random Forest)
- Scaler contract: SVM strictly on StandardScaler, Trees strictly on raw features
- Ensemble voting and decision threshold
- Probability calibration metrics (Brier score, ECE, reliability curves)
- Model artifact serialization with provenance manifest
"""

import os
import json
import joblib
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
    Computes rigorous calibration diagnostics with full input validation:
    - Brier score: Mean squared error of probabilities relative to outcomes
    - Expected Calibration Error (ECE): Weighted average difference between confidence and accuracy
    - Reliability curve bin coordinates
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=np.float64)
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have identical lengths")
    if len(y_true) == 0:
        raise ValueError("y_true and y_prob must not be empty")
    if not np.all(np.isfinite(y_prob)):
        raise ValueError("y_prob must contain only finite numbers")
    if np.any(y_prob < 0.0) or np.any(y_prob > 1.0):
        raise ValueError("y_prob values must be strictly in the range [0.0, 1.0]")
    if not np.all(np.isin(y_true, [0, 1])):
        raise ValueError("y_true must contain only binary labels (0 or 1)")
    if not isinstance(n_bins, (int, np.integer)) or n_bins < 2:
        raise ValueError("n_bins must be an integer >= 2")

    brier = float(brier_score_loss(y_true, y_prob))

    # Compute ECE and reliability points
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    # Clip index n_bins to bin n_bins - 1
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


def save_pipeline_bundle(output_dir, svm, xgb, rf, scaler, metadata=None):
    """
    Saves the entire trained pipeline bundle with full provenance:
    - Estimators and scaler serialized via joblib
    - Manifest with feature schema, threshold, git commit, package versions, and SHA256 hashes
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    joblib.dump(scaler, out_path / "scaler.joblib")
    joblib.dump(svm, out_path / "svm_model.joblib")
    joblib.dump(xgb, out_path / "xgb_model.joblib")
    joblib.dump(rf, out_path / "rf_model.joblib")

    import sklearn
    import xgboost
    import scipy

    manifest = {
        "pipeline_version": "v3.1",
        "full_features_31": FROZEN_31_FEATURES,
        "selected_features_15": FROZEN_15_SELECTED_FEATURES,
        "decision_threshold": DEFAULT_DECISION_THRESHOLD,
        "package_versions": {
            "scikit-learn": sklearn.__version__,
            "xgboost": getattr(xgboost, "__version__", "unknown"),
            "scipy": scipy.__version__,
            "numpy": np.__version__
        },
        "artifact_hashes": {
            "scaler": hashlib.sha256((out_path / "scaler.joblib").read_bytes()).hexdigest(),
            "svm": hashlib.sha256((out_path / "svm_model.joblib").read_bytes()).hexdigest(),
            "xgb": hashlib.sha256((out_path / "xgb_model.joblib").read_bytes()).hexdigest(),
            "rf": hashlib.sha256((out_path / "rf_model.joblib").read_bytes()).hexdigest()
        }
    }
    if metadata:
        manifest["metadata"] = metadata

    manifest_file = out_path / "pipeline_manifest.json"
    with manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


REQUIRED_ARTIFACT_KEYS = {"scaler", "svm", "xgb", "rf"}

def load_pipeline_bundle(bundle_dir):
    """Loads a previously saved pipeline bundle and verifies manifest schema and integrity."""
    in_path = Path(bundle_dir)
    manifest_file = in_path / "pipeline_manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found in bundle: {bundle_dir}")

    with manifest_file.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Validate manifest schema
    if manifest.get("pipeline_version") != "v3.1":
        raise ValueError(f"Incompatible pipeline version: {manifest.get('pipeline_version')}")
    if manifest.get("full_features_31") != FROZEN_31_FEATURES:
        raise ValueError("31-feature schema in manifest does not match FROZEN_31_FEATURES")
    if manifest.get("selected_features_15") != FROZEN_15_SELECTED_FEATURES:
        raise ValueError("15-feature schema in manifest does not match FROZEN_15_SELECTED_FEATURES")

    # 2. Check required artifact presence
    hashes = manifest.get("artifact_hashes", {})
    missing_keys = REQUIRED_ARTIFACT_KEYS - set(hashes.keys())
    if missing_keys:
        raise ValueError(f"Manifest missing required artifact hashes: {missing_keys}")

    # 3. Verify hashes and load artifacts
    for key in REQUIRED_ARTIFACT_KEYS:
        fname = f"{key}_model.joblib" if key != "scaler" else "scaler.joblib"
        file_path = in_path / fname
        if not file_path.exists():
            raise FileNotFoundError(f"Missing bundle artifact file: {fname}")
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != hashes[key]:
            raise ValueError(f"Hash mismatch on {fname}: expected {hashes[key]}, got {actual_hash}")

    scaler = joblib.load(in_path / "scaler.joblib")
    svm = joblib.load(in_path / "svm_model.joblib")
    xgb = joblib.load(in_path / "xgb_model.joblib")
    rf = joblib.load(in_path / "rf_model.joblib")

    return svm, xgb, rf, scaler, manifest
