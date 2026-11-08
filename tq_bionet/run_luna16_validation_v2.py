import SimpleITK as sitk
import pandas as pd
import numpy as np
import os
import time
import warnings
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, roc_auc_score

import json
# Suppress TDA/Ripser output warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.pipeline import extract_tq_bio_features
from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_bootstrap_ci, run_mcnemars_test, plot_roc_pr_curves

def run_validation_v2():
    print("======================================================================")
    print("            TQ-BioNet Stage 4: Clinical LUNA16 Validation v2.0        ")
    print("======================================================================\n")
    
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    data_dir = str(project_root / "luna16_data")
    
    annotations_path = os.path.join(data_dir, "annotations.csv")
    candidates_path = os.path.join(data_dir, "candidates_V2.csv")
    subset_dir = os.path.join(data_dir, "subset0")
    
    # 1. Read files and locate available subset0 scans
    print("Loading datasets annotations...")
    ann_df = pd.read_csv(annotations_path)
    cand_df = pd.read_csv(candidates_path)
    
    valid_scans = set([f[:-4] for f in os.listdir(subset_dir) if f.endswith('.mhd')])
    print(f"Matched {len(valid_scans)} valid scans in subset0.")
    
    # Filter annotations to subset0
    pos_subset = ann_df[ann_df['seriesuid'].isin(valid_scans)].copy()
    pos_subset['Label'] = 1
    
    neg_candidates = cand_df[(cand_df['seriesuid'].isin(valid_scans)) & (cand_df['class'] == 0)].copy()
    neg_candidates['Label'] = 0
    
    # Balanced dataset
    print("Balancing positive/negative coordinate classes scan-by-scan...")
    selected_targets = []
    
    for scan in valid_scans:
        scan_pos = pos_subset[pos_subset['seriesuid'] == scan]
        scan_neg = neg_candidates[neg_candidates['seriesuid'] == scan]
        
        num_pos = len(scan_pos)
        if num_pos == 0:
            continue
            
        for _, pos_row in scan_pos.iterrows():
            selected_targets.append({
                'seriesuid': scan,
                'x': pos_row['coordX'],
                'y': pos_row['coordY'],
                'z': pos_row['coordZ'],
                'label': 1
            })
            
        num_to_sample = min(num_pos, len(scan_neg))
        if num_to_sample > 0:
            sampled_neg = scan_neg.sample(n=num_to_sample, random_state=42)
            for _, neg_row in sampled_neg.iterrows():
                selected_targets.append({
                    'seriesuid': scan,
                    'x': neg_row['coordX'],
                    'y': neg_row['coordY'],
                    'z': neg_row['coordZ'],
                    'label': 0
                })
                
    df_targets = pd.DataFrame(selected_targets)
    print(f"Total balanced dataset: {len(df_targets)} samples ({len(df_targets[df_targets['label'] == 1])} Pos, {len(df_targets[df_targets['label'] == 0])} Neg).")
    
    # 2. Extract features with TQ-BioNet v2.0 Local Standardization
    cache_dir = os.path.join(data_dir, "cache", "tq_bionet_v3", "subset0")
    metadata_path = os.path.join(cache_dir, "metadata.json")
    
    if os.path.exists(metadata_path):
        print("\nLoading cached TQ-BioNet v3.0 Subset 0 features...")
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            
        # Verify metadata
        if meta["feature_dimension"] != 31:
            raise ValueError(f"Feature dimension mismatch for Subset 0 cache: expected 31, got {meta['feature_dimension']}")
            
        X_path = os.path.join(cache_dir, "X.npy")
        
        # Verify SHA256 Checksum
        import hashlib
        h = hashlib.sha256()
        with open(X_path, 'rb') as f:
            chunk = f.read(8192)
            while chunk:
                h.update(chunk)
                chunk = f.read(8192)
        current_hash = h.hexdigest()
        
        if current_hash != meta["SHA256 checksum"]:
            raise ValueError("SHA256 checksum mismatch for Subset 0 cache file!")
            
        X = np.load(X_path)
        y = np.load(os.path.join(cache_dir, "y.npy"))
        groups = np.load(os.path.join(cache_dir, "groups.npy"))
        coords = np.load(os.path.join(cache_dir, "coords.npy"))
        print(f"Loaded features matrix shape: {X.shape}")
    else:
        print("\nStage 2 & 3: Feature Extraction (TQ-BioNet v2.0 Preprocessing)...")
        feature_vectors = []
        labels = []
        patient_groups = []
        coords_list = []
        
        grouped = df_targets.groupby('seriesuid')
        total_scans = len(grouped)
        scan_idx = 0
        
        new_spacing = [1.0, 1.0, 1.0]
        patch_size = 32
        half_size = patch_size // 2
        
        start_time = time.time()
        
        for seriesuid, group in grouped:
            scan_idx += 1
            mhd_path = os.path.join(subset_dir, f"{seriesuid}.mhd")
            
            try:
                image = sitk.ReadImage(mhd_path)
                original_size = image.GetSize()
                original_spacing = image.GetSpacing()
                original_origin = image.GetOrigin()
                original_direction = image.GetDirection()
                
                new_size = [
                    int(round(original_size[i] * original_spacing[i] / new_spacing[i]))
                    for i in range(3)
                ]
                
                resample = sitk.ResampleImageFilter()
                resample.SetInterpolator(sitk.sitkLinear)
                resample.SetOutputSpacing(new_spacing)
                resample.SetSize(new_size)
                resample.SetOutputDirection(original_direction)
                resample.SetOutputOrigin(original_origin)
                resample.SetTransform(sitk.Transform())
                resampled_image = resample.Execute(image)
                
                np_image = sitk.GetArrayFromImage(resampled_image)
            except Exception as e:
                print(f"      Failed to load scan {seriesuid}: {e}")
                continue
                
            for _, row in group.iterrows():
                world_coords = [row['x'], row['y'], row['z']]
                voxel_coords = resampled_image.TransformPhysicalPointToIndex(world_coords)
                
                z_vox, y_vox, x_vox = voxel_coords[2], voxel_coords[1], voxel_coords[0]
                
                z_min = max(0, z_vox - half_size)
                z_max = min(np_image.shape[0], z_vox + half_size)
                y_min = max(0, y_vox - half_size)
                y_max = min(np_image.shape[1], y_vox + half_size)
                x_min = max(0, x_vox - half_size)
                x_max = min(np_image.shape[2], x_vox + half_size)
                
                patch = np_image[z_min:z_max, y_min:y_max, x_min:x_max]
                
                if patch.shape != (32, 32, 32):
                    padded = np.zeros((32, 32, 32))
                    dz = min(32, patch.shape[0])
                    dy = min(32, patch.shape[1])
                    dx = min(32, patch.shape[2])
                    padded[:dz, :dy, :dx] = patch[:dz, :dy, :dx]
                    patch = padded
                    
                median_val = np.median(patch)
                iqr_val = np.percentile(patch, 75) - np.percentile(patch, 25)
                if iqr_val < 1e-6:
                    iqr_val = 1.0
                
                standardized = (patch - median_val) / iqr_val
                clipped = np.clip(standardized, -3.0, 3.0)
                normalized = (clipped + 3.0) / 6.0
                
                f_dict, f_vec = extract_tq_bio_features(normalized)
                
                if np.isnan(f_vec).any() or np.isinf(f_vec).any():
                    continue
                    
                feature_vectors.append(f_vec)
                labels.append(row['label'])
                patient_groups.append(seriesuid)
                coords_list.append(world_coords)
                
            if scan_idx % 10 == 0 or scan_idx == total_scans:
                print(f"      Processed {scan_idx}/{total_scans} scans...", flush=True)
                
        X = np.array(feature_vectors)
        y = np.array(labels)
        groups = np.array(patient_groups)
        coords = np.array(coords_list)
        
        os.makedirs(cache_dir, exist_ok=True)
        np.save(os.path.join(cache_dir, "X.npy"), X)
        np.save(os.path.join(cache_dir, "y.npy"), y)
        np.save(os.path.join(cache_dir, "groups.npy"), groups)
        np.save(os.path.join(cache_dir, "coords.npy"), coords)
        
        # Write metadata.json
        h = hashlib.sha256()
        with open(os.path.join(cache_dir, "X.npy"), 'rb') as f:
            chunk = f.read(8192)
            while chunk:
                h.update(chunk)
                chunk = f.read(8192)
        sha_hash = h.hexdigest()
        
        metadata = {
            "algorithm_version": "v3.0",
            "feature_version": "v3.0",
            "preprocessing_version": "local_zscore_iqr_v2.0",
            "feature_dimension": int(X.shape[1]),
            "subset_ids": [0],
            "patient_count": int(len(np.unique(groups))),
            "sample_count": int(len(y)),
            "creation_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "SHA256 checksum": sha_hash,
            "random_seed": 42
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        elapsed_extraction = time.time() - start_time
        print(f"\nFeature extraction v2.0 saved in {elapsed_extraction:.2f} seconds.")
        
    # 3. Feature Pruning (Prune from 31 down to 10 key features using names)
    dummy_patch = np.zeros((16, 16, 16))
    dummy_dict, _ = extract_tq_bio_features(dummy_patch)
    sorted_keys = sorted([k for k in dummy_dict.keys() if k != 'extraction_time_sec'])
    
    v2_feature_names = [
        'fractal_dimension',
        'H0_entropy',
        'H0_total_persistence',
        'H1_count',
        'H1_total_persistence',
        'lacunarity_4',
        'lacunarity_8',
        'quantum_eigenvalue_0',
        'quantum_eigenvalue_1',
        'quantum_eigenvalue_2'
    ]
    selected_indices = [sorted_keys.index(name) for name in v2_feature_names]
    X_pruned = X[:, selected_indices]
    print(f"Pruned feature space from 31 dimensions to {X_pruned.shape[1]} dimensions.")
    
    # 4. Patient-Level Splitting (70% Train, 30% Test based on patients/groups)
    print("\nStage 4: Training & Evaluation (Patient-Level Split)...")
    unique_patients = np.unique(groups)
    np.random.seed(42)
    np.random.shuffle(unique_patients)
    
    split_idx = int(0.7 * len(unique_patients))
    train_patients = unique_patients[:split_idx]
    test_patients = unique_patients[split_idx:]
    
    train_mask = np.isin(groups, train_patients)
    test_mask = np.isin(groups, test_patients)
    
    # Data Integrity Checks
    from tq_bionet.data_integrity import verify_data_integrity
    verify_data_integrity(X, y, groups, coords, train_mask, test_mask)
    
    X_train, y_train = X_pruned[train_mask], y[train_mask]
    X_test, y_test = X_pruned[test_mask], y[test_mask]
    
    print(f"      Train Set: {len(X_train)} samples (from {len(train_patients)} scans)")
    print(f"      Test Set : {len(X_test)} samples (from {len(test_patients)} scans)")
    
    # 5. Train Voting Ensemble Classifier (SVM + XGBoost + Random Forest)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    svm = SVC(C=100.0, gamma='scale', probability=True, random_state=42)
    xgb = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.01, eval_metric='logloss', random_state=42)
    rf = RandomForestClassifier(n_estimators=150, max_depth=4, random_state=42)
    
    print("Training TQ-BioNet v2.0 Soft Voting Ensemble...")
    svm.fit(X_train_scaled, y_train)
    xgb.fit(X_train, y_train)
    rf.fit(X_train, y_train)
    
    svm_probs = svm.predict_proba(X_test_scaled)[:, 1]
    xgb_probs = xgb.predict_proba(X_test)[:, 1]
    rf_probs = rf.predict_proba(X_test)[:, 1]
    
    ensemble_probs = (svm_probs + xgb_probs + rf_probs) / 3.0
    ensemble_preds = (ensemble_probs >= 0.5).astype(int)
    
    # 6. Calculate metrics with corrected Wilson/Bootstrap Confidence Intervals
    from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_bootstrap_ci
    
    def evaluate(y_true, y_pred, y_prob):
        acc = accuracy_score(y_true, y_pred)
        sens = recall_score(y_true, y_pred)
        tn = np.sum((y_pred == 0) & (y_true == 0))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1 = f1_score(y_true, y_pred)
        auc_val = roc_auc_score(y_true, y_prob)
        
        acc_low, acc_high = compute_wilson_ci(np.sum(y_pred == y_true), len(y_true))
        sens_low, sens_high = compute_wilson_ci(np.sum((y_pred == 1) & (y_true == 1)), np.sum(y_true == 1))
        spec_low, spec_high = compute_wilson_ci(np.sum((y_pred == 0) & (y_true == 0)), np.sum(y_true == 0))
        f1_low, f1_high = compute_bootstrap_ci(y_true, y_pred, f1_score)
        
        return {
            'accuracy': acc, 'accuracy_ci': (acc_low, acc_high),
            'sensitivity': sens, 'sensitivity_ci': (sens_low, sens_high),
            'specificity': spec, 'specificity_ci': (spec_low, spec_high),
            'f1': f1, 'f1_ci': (f1_low, f1_high),
            'auc': auc_val
        }
        
    ensemble_metrics = evaluate(y_test, ensemble_preds, ensemble_probs)
    svm_metrics = evaluate(y_test, svm.predict(X_test_scaled), svm_probs)
    xgb_metrics = evaluate(y_test, xgb.predict(X_test), xgb_probs)
    
    print("\nCLINICAL LUNA16 v2.0 EVALUATION METRICS:")
    print("-" * 90)
    print(f"{'Metric':<15} | {'Voting Ensemble':<30} | {'XGBoost (Solo)':<30}")
    print("-" * 90)
    print(f"{'Accuracy':<15} | {ensemble_metrics['accuracy']:.4f} [{ensemble_metrics['accuracy_ci'][0]:.4f}-{ensemble_metrics['accuracy_ci'][1]:.4f}] | {xgb_metrics['accuracy']:.4f} [{xgb_metrics['accuracy_ci'][0]:.4f}-{xgb_metrics['accuracy_ci'][1]:.4f}]")
    print(f"{'Sensitivity':<15} | {ensemble_metrics['sensitivity']:.4f} [{ensemble_metrics['sensitivity_ci'][0]:.4f}-{ensemble_metrics['sensitivity_ci'][1]:.4f}] | {xgb_metrics['sensitivity']:.4f} [{xgb_metrics['sensitivity_ci'][0]:.4f}-{xgb_metrics['sensitivity_ci'][1]:.4f}]")
    print(f"{'Specificity':<15} | {ensemble_metrics['specificity']:.4f} [{ensemble_metrics['specificity_ci'][0]:.4f}-{ensemble_metrics['specificity_ci'][1]:.4f}] | {xgb_metrics['specificity']:.4f} [{xgb_metrics['specificity_ci'][0]:.4f}-{xgb_metrics['specificity_ci'][1]:.4f}]")
    print(f"{'F1-Score':<15} | {ensemble_metrics['f1']:.4f} [{ensemble_metrics['f1_ci'][0]:.4f}-{ensemble_metrics['f1_ci'][1]:.4f}] | {xgb_metrics['f1']:.4f} [{xgb_metrics['f1_ci'][0]:.4f}-{xgb_metrics['f1_ci'][1]:.4f}]")
    print(f"{'AUC-ROC':<15} | {ensemble_metrics['auc']:.4f}                          | {xgb_metrics['auc']:.4f}")
    print("-" * 90)
    
    # 7. Save Curves for Ensemble (Issue 5 portability)
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    save_path_roc = str(outputs_dir / "luna16_v2_roc_curve.png")
    save_path_pr = str(outputs_dir / "luna16_v2_pr_curve.png")
    plot_roc_pr_curves(y_test, ensemble_probs, xgb_probs, save_path_roc, save_path_pr)
    
    print("======================================================================\n")


if __name__ == "__main__":
    run_validation_v2()
