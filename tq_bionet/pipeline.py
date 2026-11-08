import numpy as np
import time
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, roc_auc_score, confusion_matrix
import xgboost as xgb
from scipy.ndimage import gaussian_filter

from skimage.transform import resize
from tq_bionet.quantum_module import solve_schrodinger_equation
from tq_bionet.topological_module import extract_point_cloud, compute_persistence_features
from tq_bionet.fractal_module import extract_fractal_features

def preprocess_patch(patch):
    """
    Calculates local z-score/IQR standardization on the raw patch, preserving 
    scale cues.
    """
    patch = np.asarray(patch, dtype=np.float64)
    if patch.ndim != 3 or any(d < 2 for d in patch.shape):
        raise ValueError("patch must be a 3D array with every dimension >= 2")
    if not np.all(np.isfinite(patch)):
        raise ValueError("patch must contain only finite values")
    median_val = np.median(patch)
    iqr_val = np.percentile(patch, 75) - np.percentile(patch, 25)
    if iqr_val < 1e-6:
        iqr_val = 1.0
        
    standardized = (patch - median_val) / iqr_val
    # Clip to standard IQR deviations [-3.0, 3.0]
    clipped = np.clip(standardized, -3.0, 3.0)
    # Map linearly to [0.0, 1.0] for potential well solving
    normalized = (clipped + 3.0) / 6.0
    return normalized

def compute_3d_structure_features(patch, sigma=1.0):
    """
    Computes 3D Hessian eigenvalues to detect tubular vs. spherical structures.
    """
    # Smooth patch to compute stable derivatives
    patch = np.asarray(patch, dtype=np.float64)
    if patch.ndim != 3 or any(d < 2 for d in patch.shape):
        raise ValueError("patch must be a 3D array with every dimension >= 2")
    if not np.all(np.isfinite(patch)):
        raise ValueError("patch must contain only finite values")
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma must be finite and > 0")
    smoothed = gaussian_filter(patch, sigma=sigma)
    
    # Compute 1st derivatives
    dz, dy, dx = np.gradient(smoothed)
    
    # Compute 2nd derivatives
    dzz, dzy, dzx = np.gradient(dz)
    _, dyy, dyx = np.gradient(dy)
    _, _, dxx = np.gradient(dx)
    
    # Extract eigenvalues at the center of the patch
    center_idx = patch.shape[0] // 2
    H_center = np.array([
        [dzz[center_idx, center_idx, center_idx], dzy[center_idx, center_idx, center_idx], dzx[center_idx, center_idx, center_idx]],
        [dzy[center_idx, center_idx, center_idx], dyy[center_idx, center_idx, center_idx], dyx[center_idx, center_idx, center_idx]],
        [dzx[center_idx, center_idx, center_idx], dyx[center_idx, center_idx, center_idx], dxx[center_idx, center_idx, center_idx]]
    ])
    
    # Calculate sorted absolute eigenvalues
    eigenvalues = np.linalg.eigvalsh(H_center)
    eigenvalues = sorted(np.abs(eigenvalues))
    
    L1, L2, L3 = eigenvalues[0], eigenvalues[1], eigenvalues[2]
    
    # Compute ratios (avoiding division by zero)
    R_B = L1 / (np.sqrt(L2 * L3) + 1e-6)  # Nodule (blob) indicator
    R_A = L2 / (L3 + 1e-6)               # Plate vs. Line indicator
    
    return {
        'blobness_ratio': R_B,
        'hessian_L1': L1,
        'hessian_L2': L2,
        'hessian_L3': L3,
        'vesselness_ratio': R_A
    }

def extract_tq_bio_features(normalized_patch, mass_coef='adaptive', potential_scale='adaptive', threshold=0.01, downsample_size=16):
    """
    Extracts all physical, topological, and fractal features from a 3D CT patch,
    augmented with 3D Hessian structure tensor eigenvalues to detect vessels (TQ-BioNet v3.0).
    """
    start_time = time.time()
    normalized_patch = np.asarray(normalized_patch, dtype=np.float64)
    if normalized_patch.ndim != 3 or len(set(normalized_patch.shape)) != 1:
        raise ValueError("normalized_patch must be a cubic 3D array")
    if any(d < 2 for d in normalized_patch.shape) or not np.all(np.isfinite(normalized_patch)):
        raise ValueError("normalized_patch must have dimensions >= 2 and contain finite values")
    if not np.isfinite(threshold):
        raise ValueError("threshold must be finite")
    if downsample_size is not None and (not isinstance(downsample_size, int) or downsample_size < 2):
        raise ValueError("downsample_size must be None or an integer >= 2")
    
    # Compute self-adaptive biophysical parameters if requested
    if potential_scale == 'adaptive':
        std_val = np.std(normalized_patch)
        potential_scale = 100.0 * (0.25 / (std_val + 1e-6))
        potential_scale = np.clip(potential_scale, 50.0, 300.0)
        
    if mass_coef == 'adaptive':
        var_val = np.var(normalized_patch)
        mass_coef = 1.0 * (0.06 / (var_val + 1e-6))
        mass_coef = np.clip(mass_coef, 0.2, 5.0)
    
    # Downsample patch if requested to speed up eigensolver
    if downsample_size is not None and downsample_size < normalized_patch.shape[0]:
        working_patch = resize(
            normalized_patch,
            (downsample_size, downsample_size, downsample_size),
            order=1,
            mode='reflect',
            anti_aliasing=True
        )
    else:
        working_patch = normalized_patch
    
    # 1. Quantum Module: Solve Schrödinger equation
    eigenvalues, _, prob_density = solve_schrodinger_equation(
        working_patch, 
        mass_coef=mass_coef, 
        potential_scale=potential_scale, 
        num_eigenvalues=10
    )
    
    # 2. Topological Module: Persistent Homology
    point_cloud = extract_point_cloud(prob_density, threshold=threshold, max_points=400)
    topo_features, _ = compute_persistence_features(point_cloud)
    
    # 3. Fractal Module: 3D Fractal Dimension & Lacunarity
    fractal_features = extract_fractal_features(prob_density, threshold=threshold)
    
    # 4. Hessian structure tensor ratios (v3.0 improvements)
    hessian_features = compute_3d_structure_features(working_patch)
    
    # 5. Integrate all features
    features_dict = {}
    
    # Append Quantum features
    for i, ev in enumerate(eigenvalues):
        features_dict[f'quantum_eigenvalue_{i}'] = ev
        
    # Append Topological features
    features_dict.update(topo_features)
    
    # Append Fractal features
    features_dict.update(fractal_features)
    
    # Append Hessian features
    features_dict.update(hessian_features)
    
    # Time taken
    features_dict['extraction_time_sec'] = time.time() - start_time
    
    # Sort keys for consistent vector ordering
    sorted_keys = sorted([k for k in features_dict.keys() if k != 'extraction_time_sec'])
    features_vector = np.asarray([features_dict[k] for k in sorted_keys], dtype=np.float64)
    if not np.all(np.isfinite(features_vector)):
        raise FloatingPointError("Feature extraction produced NaN or infinite values")
    
    return features_dict, features_vector

def train_and_evaluate_model(X_train, y_train, X_test, y_test, model_type='svm'):
    if model_type == 'svm':
        model = SVC(kernel='rbf', C=10.0, probability=True, random_state=42)
    elif model_type == 'xgboost':
        model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            random_state=42,
            eval_metric='logloss'
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
        
    # Train
    start_t = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_t
    
    # Predict
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
    
    # Calculate standard metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    sens = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    # Specificity
    cm = confusion_matrix(y_test, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    else:
        spec = 0.0
        
    # AUC
    auc = roc_auc_score(y_test, y_prob) if y_prob is not None else 0.0
    
    results = {
        'model_type': model_type,
        'accuracy': acc,
        'precision': prec,
        'sensitivity': sens,
        'specificity': spec,
        'f1_score': f1,
        'auc': auc,
        'train_time_sec': train_time
    }
    
    return model, results
