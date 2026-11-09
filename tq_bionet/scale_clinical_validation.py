import urllib.request
import socket
socket.setdefaulttimeout(45.0)
import zipfile
import shutil
import os
import time
import pandas as pd
import numpy as np
import SimpleITK as sitk
import warnings
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, roc_auc_score
import json
import hashlib
import subprocess
from pathlib import Path

warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.pipeline import extract_tq_bio_features
from tq_bionet.data_loader import extract_3d_patch, safe_extract_zip, file_lock
from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_bootstrap_ci, plot_roc_pr_curves

def get_git_commit():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return commit if commit else "unavailable"
    except Exception:
        return "unavailable"

def download_and_extract_subset(subset_idx):
    # Dynamic path resolution (Issue 5 portability)
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    data_dir_c = str(project_root / "luna16_data")
    if os.path.exists("D:\\"):
        data_dir_d = r"D:\LUNA16"
    else:
        data_dir_d = str(project_root / "luna16_data" / "large_data")
        
    os.makedirs(data_dir_d, exist_ok=True)
    
    zip_name = f"subset{subset_idx}.zip"
    zip_path = os.path.join(data_dir_d, zip_name)
    lock_path = zip_path + ".lock"
    
    if subset_idx == 0:
        extract_path = os.path.join(data_dir_c, "subset0")
        target_staging = Path(data_dir_c).resolve()
    else:
        extract_path = os.path.join(data_dir_d, f"subset{subset_idx}")
        target_staging = Path(data_dir_d).resolve()

    with file_lock(lock_path, timeout=120):
        # If the unzipped directory already exists, we skip everything
        if os.path.exists(extract_path) and os.path.isdir(extract_path) and len([f for f in os.listdir(extract_path) if f.endswith('.mhd')]) > 0:
            print(f"\n[STEP 1] Unzipped folder '{extract_path}' already exists and contains scans, skipping download/extraction.")
            return True

        tmp_path = f"{zip_path}.tmp.{os.getpid()}"

        # Verify archive integrity via CRC32 testzip before skipping download
        if os.path.exists(zip_path):
            is_valid_zip = False
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    is_valid_zip = (zf.testzip() is None)
            except Exception:
                is_valid_zip = False

            if is_valid_zip:
                print(f"\n[STEP 1] Zip archive '{zip_path}' verified via CRC32 checksum, skipping download. Proceeding directly to extraction.")
            else:
                print(f"\n[STEP 1] Zip archive '{zip_path}' is corrupt/incomplete. Deleting and redownloading...")
                try:
                    os.remove(zip_path)
                except Exception as e:
                    print(f"   Failed to delete corrupt zip: {e}")
                
                # Download since it was corrupt
                if subset_idx <= 6:
                    url = f"https://zenodo.org/api/records/3723295/files/subset{subset_idx}.zip/content"
                else:
                    url = f"https://zenodo.org/api/records/4121926/files/subset{subset_idx}.zip/content"
                    
                print(f"\n[STEP 1] Downloading {zip_name} from {url}...")
                start_dl = time.time()
                
                global last_report
                last_report = -1
                
                def dl_progress(block_num, block_size, total_size):
                    global last_report
                    downloaded = block_num * block_size
                    percent = int(downloaded * 100 / total_size) if total_size > 0 else 0
                    if percent % 10 == 0 and percent != last_report:
                        print(f"      Downloaded {percent}% ({downloaded / (1024**2):.1f} MB of {total_size / (1024**2):.1f} MB)...", flush=True)
                        last_report = percent
        
                try:
                    urllib.request.urlretrieve(url, tmp_path, reporthook=dl_progress)
                    os.replace(tmp_path, zip_path)
                    print(f"   Successfully downloaded to {zip_path} in {time.time() - start_dl:.1f} seconds.")
                except Exception as e:
                    print(f"   Download failed: {e}")
                    if os.path.exists(tmp_path):
                        try: os.remove(tmp_path)
                        except OSError: pass
                    return False
        else:
            # Zenodo URLs
            if subset_idx <= 6:
                url = f"https://zenodo.org/api/records/3723295/files/subset{subset_idx}.zip/content"
            else:
                url = f"https://zenodo.org/api/records/4121926/files/subset{subset_idx}.zip/content"
                
            print(f"\n[STEP 1] Downloading {zip_name} from {url}...")
            start_dl = time.time()
            
            last_report = -1
            
            def dl_progress(block_num, block_size, total_size):
                global last_report
                downloaded = block_num * block_size
                percent = int(downloaded * 100 / total_size) if total_size > 0 else 0
                if percent % 10 == 0 and percent != last_report:
                    print(f"      Downloaded {percent}% ({downloaded / (1024**2):.1f} MB of {total_size / (1024**2):.1f} MB)...", flush=True)
                    last_report = percent
                    
            try:
                urllib.request.urlretrieve(url, tmp_path, reporthook=dl_progress)
                os.replace(tmp_path, zip_path)
                print(f"   Successfully downloaded to {zip_path} in {time.time() - start_dl:.1f} seconds.")
            except Exception as e:
                print(f"   Download failed: {e}")
                if os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except OSError: pass
                return False
            
        print(f"\n[STEP 2] Extracting {zip_name} to {extract_path}...")
        start_ex = time.time()
        try:
            safe_extract_zip(zip_path, target_staging)
            if not os.path.exists(extract_path) or len([f for f in os.listdir(extract_path) if f.endswith('.mhd')]) == 0:
                raise RuntimeError(f"Extraction verification failed: {extract_path} missing or contains no .mhd scans")
            print(f"   Extraction completed and verified in {time.time() - start_ex:.1f} seconds.")
        except Exception as e:
            print(f"   Extraction failed: {e}")
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                    print(f"   Deleted corrupt zip archive: {zip_path}")
                except Exception as del_err:
                    print(f"   Failed to delete corrupt zip: {del_err}")
            return False
            
        print(f"   Preserving {zip_name} zip archive on D: drive for future reuse.")
        return True
def get_file_sha256(filepath):
    import hashlib
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        chunk = f.read(8192)
        while chunk:
            h.update(chunk)
            chunk = f.read(8192)
    return h.hexdigest()


REQUIRED_CACHE_ARRAY_KEYS = {"X", "y", "groups", "coords"}

def validate_subset_cache(cache_dir, subset_idx):
    """
    Strictly validates a v3.1 subset cache:
    - metadata.json exists and has algorithm_version == 'v3.1'
    - array_hashes contains EXACTLY {"X", "y", "groups", "coords"}
    - all 4 .npy files exist and match their SHA256 hashes exactly
    - array dimensions, non-emptiness, label validity, and finiteness are verified
    Returns (X, y, groups, coords, metadata) or raises ValueError
    """
    cache_path = Path(cache_dir)
    metadata_path = cache_path / "metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"Cache metadata missing at: {metadata_path}")
        
    with metadata_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
        
    if meta.get("algorithm_version") != "v3.1" or meta.get("feature_version") != "v3.1":
        raise ValueError(f"Cache version mismatch: expected v3.1, got {meta.get('algorithm_version')}")
    if meta.get("subset_ids") != [int(subset_idx)]:
        raise ValueError(f"Subset ID mismatch: expected {[int(subset_idx)]}, got {meta.get('subset_ids')}")
    if meta.get("feature_dimension") != 31:
        raise ValueError(f"Feature dimension mismatch: expected 31, got {meta.get('feature_dimension')}")
        
    array_hashes = meta.get("array_hashes")
    if not isinstance(array_hashes, dict) or set(array_hashes.keys()) != REQUIRED_CACHE_ARRAY_KEYS:
        raise ValueError(f"array_hashes must contain exactly {REQUIRED_CACHE_ARRAY_KEYS}, got {set(array_hashes.keys()) if isinstance(array_hashes, dict) else None}")
        
    array_files = {
        "X": cache_path / "X.npy",
        "y": cache_path / "y.npy",
        "groups": cache_path / "groups.npy",
        "coords": cache_path / "coords.npy"
    }
    
    for key, fpath in array_files.items():
        if not fpath.exists():
            raise ValueError(f"Missing cache file: {fpath}")
        actual_h = get_file_sha256(str(fpath))
        if actual_h != array_hashes[key]:
            raise ValueError(f"{key} cache SHA256 mismatch for subset{subset_idx}: expected {array_hashes[key]}, got {actual_h}")
            
    X = np.load(array_files["X"], allow_pickle=False)
    y = np.load(array_files["y"], allow_pickle=False)
    groups = np.load(array_files["groups"], allow_pickle=False)
    coords = np.load(array_files["coords"], allow_pickle=False)
    
    n = len(y)
    if X.ndim != 2 or X.shape != (n, 31):
        raise ValueError(f"Invalid X shape: {X.shape}, expected ({n}, 31)")
    if y.ndim != 1 or groups.ndim != 1 or coords.ndim != 2 or coords.shape != (n, 3):
        raise ValueError("Cache array shape mismatch")
    if len(groups) != n or not np.isfinite(X).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("Invalid feature values or non-binary labels")
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite coordinates")
        
    return X, y, groups, coords, meta

def process_and_save_subset(subset_idx):
    # Dynamic path resolution (Issue 5 portability)
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    data_dir_c = str(project_root / "luna16_data")
    if os.path.exists("D:\\"):
        data_dir_d = r"D:\LUNA16"
    else:
        data_dir_d = str(project_root / "luna16_data" / "large_data")
    
    # Skip reprocessing only if entire cache is validated
    cache_dir = os.path.join(data_dir_c, "cache", "tq_bionet_v3_1", f"subset{subset_idx}")
    try:
        validate_subset_cache(cache_dir, subset_idx)
        print(f"   [STEP 3] Valid, complete v3.1 cache for subset{subset_idx} verified. Skipping extraction.")
        return True
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"   [STEP 3] Cache for subset{subset_idx} invalid or missing ({e}). Proceeding to extract and build...")
        
    annotations_path = os.path.join(data_dir_c, "annotations.csv")
    candidates_path = os.path.join(data_dir_c, "candidates_V2.csv")
    
    if subset_idx == 0:
        subset_dir = os.path.join(data_dir_c, "subset0")
    else:
        subset_dir = os.path.join(data_dir_d, f"subset{subset_idx}")
    
    print(f"\n[STEP 3] Matching annotations and candidates for subset{subset_idx}...")
    ann_df = pd.read_csv(annotations_path)
    cand_df = pd.read_csv(candidates_path)
    
    valid_scans = set([f[:-4] for f in os.listdir(subset_dir) if f.endswith('.mhd')])
    print(f"   Found {len(valid_scans)} valid scans in subset{subset_idx}.")
    
    pos_subset = ann_df[ann_df['seriesuid'].isin(valid_scans)].copy()
    pos_subset['Label'] = 1
    
    neg_candidates = cand_df[(cand_df['seriesuid'].isin(valid_scans)) & (cand_df['class'] == 0)].copy()
    neg_candidates['Label'] = 0
    
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
    print(f"   Balanced dataset for subset{subset_idx}: {len(df_targets)} samples.")
    
    print(f"\n[STEP 4] Extracting TQ-BioNet v2.0 standardized features for subset{subset_idx}...")
    new_spacing = [1.0, 1.0, 1.0]
    patch_size = 32
    half_size = patch_size // 2
    
    feature_vectors = []
    labels = []
    patient_groups = []
    coords_list = []
    
    grouped = df_targets.groupby('seriesuid')
    total_scans = len(grouped)
    scan_idx = 0
    
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
            
            # Extract 32x32x32 patch centered at voxel_coords with -1000 HU (air) padding
            patch = extract_3d_patch(np_image, (z_vox, y_vox, x_vox), patch_size=32, fill_value=-1000.0)
                
            median_val = np.median(patch)
            iqr_val = np.percentile(patch, 75) - np.percentile(patch, 25)
            if iqr_val < 1e-6:
                iqr_val = 1.0
            
            standardized = (patch - median_val) / iqr_val
            clipped = np.clip(standardized, -3.0, 3.0)
            normalized = (clipped + 3.0) / 6.0
            
            _, f_vec = extract_tq_bio_features(normalized)
            
            if np.isnan(f_vec).any() or np.isinf(f_vec).any():
                continue
                
            feature_vectors.append(f_vec)
            labels.append(row['label'])
            patient_groups.append(seriesuid)
            coords_list.append(world_coords)
            
        if scan_idx % 10 == 0 or scan_idx == total_scans:
            print(f"      Processed {scan_idx}/{total_scans} scans...", flush=True)
            
    X_new = np.array(feature_vectors)
    y_new = np.array(labels)
    groups_new = np.array(patient_groups)
    coords_new = np.array(coords_list)
    
    print(f"   Extraction completed in {time.time() - start_time:.1f} seconds. Extracted shape: {X_new.shape}")
    
    # Save inside versioned folder cache
    cache_dir = os.path.join(data_dir_c, "cache", "tq_bionet_v3_1", f"subset{subset_idx}")
    os.makedirs(cache_dir, exist_ok=True)
    
    X_path = os.path.join(cache_dir, "X.npy")
    y_path = os.path.join(cache_dir, "y.npy")
    groups_path = os.path.join(cache_dir, "groups.npy")
    coords_path = os.path.join(cache_dir, "coords.npy")
    
    np.save(X_path, X_new)
    np.save(y_path, y_new)
    np.save(groups_path, groups_new)
    np.save(coords_path, coords_new)
    
    # Generate metadata.json with independent hashes for all arrays
    array_hashes = {
        "X": get_file_sha256(X_path),
        "y": get_file_sha256(y_path),
        "groups": get_file_sha256(groups_path),
        "coords": get_file_sha256(coords_path)
    }
    
    metadata = {
        "algorithm_version": "v3.1",
        "feature_version": "v3.1",
        "preprocessing_version": "local_zscore_iqr_v2.0",
        "feature_dimension": int(X_new.shape[1]),
        "subset_ids": [int(subset_idx)],
        "patient_count": int(len(np.unique(groups_new))),
        "sample_count": int(len(y_new)),
        "creation_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "SHA256 checksum": array_hashes["X"],
        "array_hashes": array_hashes,
        "random_seed": 42
    }
    
    with open(os.path.join(cache_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"   Successfully saved versioned subset{subset_idx} cache and metadata.")
    
    if subset_idx != 0:
        print(f"\n[STEP 6] Cleaning up unzipped raw scans folder from D: drive: {subset_dir}...")
        try:
            shutil.rmtree(subset_dir)
            print("   Raw scans folder successfully deleted.")
        except Exception as e:
            print(f"   Failed to delete raw scans folder: {e}")
    else:
        print(f"\n[STEP 6] Preserving subset0 raw scans folder on C: drive.")
        
    return True

def reconstruct_combined_dataset(subsets_list, data_dir_c):
    import json
    X_parts = []
    y_parts = []
    groups_parts = []
    coords_parts = []
    subsets_parts = []
    
    for subset_idx in subsets_list:
        cache_dir = os.path.join(data_dir_c, "cache", "tq_bionet_v3_1", f"subset{subset_idx}")
        X, y, groups, coords, meta = validate_subset_cache(cache_dir, subset_idx)
        n = len(y)
        X_parts.append(X)
        y_parts.append(y)
        groups_parts.append(groups)
        coords_parts.append(coords)
        subsets_parts.append(np.full(n, subset_idx, dtype=np.int16))
        
    X_combined = np.concatenate(X_parts, axis=0)
    y_combined = np.concatenate(y_parts, axis=0)
    groups_combined = np.concatenate(groups_parts, axis=0)
    coords_combined = np.concatenate(coords_parts, axis=0)
    subsets_combined = np.concatenate(subsets_parts, axis=0)
    
    return X_combined, y_combined, groups_combined, coords_combined, subsets_combined

def run_retraining():
    import json
    from pathlib import Path
    from tq_bionet.model_config import (
        prune_to_selected_features,
        fit_frozen_pipeline,
        predict_ensemble,
        compute_calibration_metrics,
        DEFAULT_DECISION_THRESHOLD
    )
    project_root = Path(__file__).resolve().parent.parent
    data_dir_c = str(project_root / "luna16_data")
    
    print("\n[STEP 7] Reconstructing combined development dataset from versioned caches...")
    X, y, groups, coords, subsets = reconstruct_combined_dataset([0, 1, 2, 3, 4, 5], data_dir_c)
    
    # Automatically generate feature index mapping file
    dummy_patch = np.zeros((16, 16, 16))
    dummy_dict, _ = extract_tq_bio_features(dummy_patch)
    sorted_keys = sorted([k for k in dummy_dict.keys() if k != 'extraction_time_sec'])
    
    # Save feature mapping to mapping CSVs (Issue 5 portability)
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = str(outputs_dir)
    
    mapping_df = pd.DataFrame({'index': range(len(sorted_keys)), 'feature_name': sorted_keys})
    mapping_df.to_csv(os.path.join(outputs_dir, "feature_index_mapping.csv"), index=False)
    mapping_df.to_csv(os.path.join(outputs_dir, "feature_mapping.csv"), index=False)
    
    # Find indices dynamically referencing features by name
    locked_feature_names = [
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
    selected_indices = [sorted_keys.index(name) for name in locked_feature_names]
    X_pruned = X[:, selected_indices]
    
    unique_patients = np.unique(groups)
    np.random.seed(42)
    np.random.shuffle(unique_patients)
    
    split_idx = int(0.7 * len(unique_patients))
    train_patients = unique_patients[:split_idx]
    test_patients = unique_patients[split_idx:]
    
    train_mask = np.isin(groups, train_patients)
    test_mask = np.isin(groups, test_patients)
    
    # RUN DATA INTEGRITY & DUPLICATE CHECKS
    from tq_bionet.data_integrity import verify_data_integrity
    verify_data_integrity(X, y, groups, coords, train_mask, test_mask)
    
    # Start timer for actual training and evaluation run (Issue 5 timer)
    start_eval_time = time.perf_counter()
    
    X_train, y_train = X_pruned[train_mask], y[train_mask]
    X_test, y_test = X_pruned[test_mask], y[test_mask]
    
    print("\n[STEP 8] Re-evaluating models on the scaled dataset...")
    print(f"   Total cohort: {len(X)} samples")
    print(f"   Train set   : {len(X_train)} samples (from {len(train_patients)} scans)")
    print(f"   Test set    : {len(X_test)} samples (from {len(test_patients)} scans)")
    
    svm, xgb, rf, scaler = fit_frozen_pipeline(X_train, y_train, random_state=42)
    pred_res = predict_ensemble(svm, xgb, rf, scaler, X_test, threshold=DEFAULT_DECISION_THRESHOLD)
    svm_probs = pred_res['svm_prob']
    xgb_probs = pred_res['xgb_prob']
    rf_probs = pred_res['rf_prob']
    ensemble_probs = pred_res['ensemble_prob']
    
    train_pos = np.sum(y_train == 1)
    train_neg = np.sum(y_train == 0)
    test_pos = np.sum(y_test == 1)
    test_neg = np.sum(y_test == 0)
    
    svm_preds = (svm_probs >= 0.5).astype(int)
    xgb_preds = (xgb_probs >= 0.5).astype(int)
    ensemble_preds = (ensemble_probs >= 0.5).astype(int)
    
    svm_acc = accuracy_score(y_test, svm_preds)
    svm_sens = recall_score(y_test, svm_preds)
    svm_spec = recall_score(y_test, svm_preds, pos_label=0)
    svm_prec = precision_score(y_test, svm_preds)
    svm_f1 = f1_score(y_test, svm_preds)
    svm_auc = roc_auc_score(y_test, svm_probs)
    
    xgb_acc = accuracy_score(y_test, xgb_preds)
    xgb_sens = recall_score(y_test, xgb_preds)
    xgb_spec = recall_score(y_test, xgb_preds, pos_label=0)
    xgb_prec = precision_score(y_test, xgb_preds)
    xgb_f1 = f1_score(y_test, xgb_preds)
    xgb_auc = roc_auc_score(y_test, xgb_probs)
    
    ens_acc = accuracy_score(y_test, ensemble_preds)
    ens_sens = recall_score(y_test, ensemble_preds)
    ens_spec = recall_score(y_test, ensemble_preds, pos_label=0)
    ens_prec = precision_score(y_test, ensemble_preds)
    ens_f1 = f1_score(y_test, ensemble_preds)
    ens_auc = roc_auc_score(y_test, ensemble_probs)
    
    # Calculate corrected Confidence Intervals (Part 6)
    from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_bootstrap_ci
    
    svm_ci_low_acc, svm_ci_high_acc = compute_wilson_ci(np.sum(svm_preds == y_test), len(y_test))
    xgb_ci_low_acc, xgb_ci_high_acc = compute_wilson_ci(np.sum(xgb_preds == y_test), len(y_test))
    ens_ci_low_acc, ens_ci_high_acc = compute_wilson_ci(np.sum(ensemble_preds == y_test), len(y_test))
    
    svm_ci_low_sens, svm_ci_high_sens = compute_wilson_ci(np.sum((svm_preds == 1) & (y_test == 1)), np.sum(y_test == 1))
    xgb_ci_low_sens, xgb_ci_high_sens = compute_wilson_ci(np.sum((xgb_preds == 1) & (y_test == 1)), np.sum(y_test == 1))
    ens_ci_low_sens, ens_ci_high_sens = compute_wilson_ci(np.sum((ensemble_preds == 1) & (y_test == 1)), np.sum(y_test == 1))
    
    svm_ci_low_spec, svm_ci_high_spec = compute_wilson_ci(np.sum((svm_preds == 0) & (y_test == 0)), np.sum(y_test == 0))
    xgb_ci_low_spec, xgb_ci_high_spec = compute_wilson_ci(np.sum((xgb_preds == 0) & (y_test == 0)), np.sum(y_test == 0))
    ens_ci_low_spec, ens_ci_high_spec = compute_wilson_ci(np.sum((ensemble_preds == 0) & (y_test == 0)), np.sum(y_test == 0))
    
    svm_ci_low_prec, svm_ci_high_prec = compute_wilson_ci(np.sum((svm_preds == 1) & (y_test == 1)), np.sum(svm_preds == 1))
    xgb_ci_low_prec, xgb_ci_high_prec = compute_wilson_ci(np.sum((xgb_preds == 1) & (y_test == 1)), np.sum(xgb_preds == 1))
    ens_ci_low_prec, ens_ci_high_prec = compute_wilson_ci(np.sum((ensemble_preds == 1) & (y_test == 1)), np.sum(ensemble_preds == 1))
    
    svm_ci_low_f1, svm_ci_high_f1 = compute_bootstrap_ci(y_test, svm_preds, f1_score)
    xgb_ci_low_f1, xgb_ci_high_f1 = compute_bootstrap_ci(y_test, xgb_preds, f1_score)
    ens_ci_low_f1, ens_ci_high_f1 = compute_bootstrap_ci(y_test, ensemble_preds, f1_score)
    
    svm_ci_low_auc, svm_ci_high_auc = compute_bootstrap_ci(y_test, svm_probs, roc_auc_score)
    xgb_ci_low_auc, xgb_ci_high_auc = compute_bootstrap_ci(y_test, xgb_probs, roc_auc_score)
    ens_ci_low_auc, ens_ci_high_auc = compute_bootstrap_ci(y_test, ensemble_probs, roc_auc_score)
    
    print("\n==================================================")
    print("      DATASET DISTRIBUTION & STATISTICS")
    print("==================================================")
    print(f"Train Set Size : {len(y_train)} (Positive: {train_pos}, Negative: {train_neg})")
    print(f"Test Set Size  : {len(y_test)} (Positive: {test_pos}, Negative: {test_neg})")
    print("==================================================")
    
    print("\nUPDATED SCALED CLASSIFIER METRICS:")
    print("-" * 128)
    print("METRIC                  | SVM                                 | XGBoost                             | Voting Ensemble")
    print("-" * 128)
    print(f"Accuracy (Wilson)       | {svm_acc:.4f} [{svm_ci_low_acc:.3f} - {svm_ci_high_acc:.3f}]       | {xgb_acc:.4f} [{xgb_ci_low_acc:.3f} - {xgb_ci_high_acc:.3f}]       | {ens_acc:.4f} [{ens_ci_low_acc:.3f} - {ens_ci_high_acc:.3f}]")
    print(f"Sensitivity (Wilson)    | {svm_sens:.4f} [{svm_ci_low_sens:.3f} - {svm_ci_high_sens:.3f}]       | {xgb_sens:.4f} [{xgb_ci_low_sens:.3f} - {xgb_ci_high_sens:.3f}]       | {ens_sens:.4f} [{ens_ci_low_sens:.3f} - {ens_ci_high_sens:.3f}]")
    print(f"Specificity (Wilson)    | {svm_spec:.4f} [{svm_ci_low_spec:.3f} - {svm_ci_high_spec:.3f}]       | {xgb_spec:.4f} [{xgb_ci_low_spec:.3f} - {xgb_ci_high_spec:.3f}]       | {ens_spec:.4f} [{ens_ci_low_spec:.3f} - {ens_ci_high_spec:.3f}]")
    print(f"Precision (Wilson)      | {svm_prec:.4f} [{svm_ci_low_prec:.3f} - {svm_ci_high_prec:.3f}]       | {xgb_prec:.4f} [{xgb_ci_low_prec:.3f} - {xgb_ci_high_prec:.3f}]       | {ens_prec:.4f} [{ens_ci_low_prec:.3f} - {ens_ci_high_prec:.3f}]")
    print(f"F1-Score (Bootstrap)    | {svm_f1:.4f} [{svm_ci_low_f1:.3f} - {svm_ci_high_f1:.3f}]       | {xgb_f1:.4f} [{xgb_ci_low_f1:.3f} - {xgb_ci_high_f1:.3f}]       | {ens_f1:.4f} [{ens_ci_low_f1:.3f} - {ens_ci_high_f1:.3f}]")
    print(f"AUC-ROC (Bootstrap)     | {svm_auc:.4f} [{svm_ci_low_auc:.3f} - {svm_ci_high_auc:.3f}]       | {xgb_auc:.4f} [{xgb_ci_low_auc:.3f} - {xgb_ci_high_auc:.3f}]       | {ens_auc:.4f} [{ens_ci_low_auc:.3f} - {ens_ci_high_auc:.3f}]")
    print("-" * 128)
    
    save_path_roc = os.path.join(artifacts_dir, "luna16_v2_roc_curve.png")
    save_path_pr = os.path.join(artifacts_dir, "luna16_v2_pr_curve.png")
    from tq_bionet.evaluation_metrics import plot_roc_pr_curves
    plot_roc_pr_curves(y_test, ensemble_probs, xgb_probs, save_path_roc, save_path_pr)
    print("Updated ROC/PR curves saved.")
    
    # Save separate metrics for subsets
    subsets_test = subsets[test_mask]
    print("\n==================================================")
    print("      METRICS EVALUATED SEPARATELY FOR EACH SUBSET")
    print("==================================================")
    for sub_idx in np.unique(subsets_test):
        mask_sub = (subsets_test == sub_idx)
        y_sub_test = y_test[mask_sub]
        svm_probs_sub = svm_probs[mask_sub]
        xgb_probs_sub = xgb_probs[mask_sub]
        ensemble_probs_sub = ensemble_probs[mask_sub]
        
        svm_preds_sub = (svm_probs_sub >= 0.5).astype(int)
        xgb_preds_sub = (xgb_probs_sub >= 0.5).astype(int)
        ensemble_preds_sub = (ensemble_probs_sub >= 0.5).astype(int)
        
        sub_svm_acc = accuracy_score(y_sub_test, svm_preds_sub) if len(y_sub_test) > 0 else 0.0
        sub_xgb_acc = accuracy_score(y_sub_test, xgb_preds_sub) if len(y_sub_test) > 0 else 0.0
        sub_xgb_auc = roc_auc_score(y_sub_test, xgb_probs_sub) if (len(y_sub_test) > 0 and len(np.unique(y_sub_test)) > 1) else 0.5
        
        sub_ens_acc = accuracy_score(y_sub_test, ensemble_preds_sub) if len(y_sub_test) > 0 else 0.0
        sub_ens_auc = roc_auc_score(y_sub_test, ensemble_probs_sub) if (len(y_sub_test) > 0 and len(np.unique(y_sub_test)) > 1) else 0.5
        
        print(f"Subset {int(sub_idx)} (N_test = {len(y_sub_test)}) :")
        print(f"   SVM Acc     : {sub_svm_acc:.4f}")
        print(f"   XGBoost Acc : {sub_xgb_acc:.4f} | AUC: {sub_xgb_auc:.4f}")
        print(f"   Ensemble Acc: {sub_ens_acc:.4f} | AUC: {sub_ens_auc:.4f}")
    print("==================================================")
    
    # DUMP REPRODUCIBILITY SPLITS
    repro_indices = {
        "train_indices": list(map(int, np.where(train_mask)[0])),
        "test_indices": list(map(int, np.where(test_mask)[0])),
        "patient_split": {
            "train_patients": list(map(str, train_patients)),
            "test_patients": list(map(str, test_patients))
        },
        "random_seed": 42
    }
    with open("reproducibility_indices.json", "w") as f:
        json.dump(repro_indices, f, indent=4)
    with open(os.path.join(artifacts_dir, "reproducibility_indices.json"), "w") as f:
        json.dump(repro_indices, f, indent=4)
        
    # Measure actual duration (Issue 5 timer)
    eval_duration = time.perf_counter() - start_eval_time

    # GENERATE EXPERIMENT MANIFEST
    manifest = {
        "experiment_id": "tq_bionet_v3_1.0_dev_cohort_repro",
        "date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "git_commit": get_git_commit(),
        "algorithm_version": "v3.1",
        "feature_version": "v3.1",
        "random_seed": 42,
        "subset_list": [0, 1, 2, 3, 4, 5],
        "patient_ids_hash": hashlib.sha256(groups.tobytes()).hexdigest(),
        "sample_count": int(X.shape[0]),
        "feature_dimension": int(X.shape[1]),
        "cache_hashes": {
            f"subset{i}": get_file_sha256(os.path.join(data_dir_c, "cache", "tq_bionet_v3_1", f"subset{i}", "X.npy"))
            for i in [0, 1, 2, 3, 4, 5]
        },
        "runtime_evaluation_sec": float(eval_duration)
    }
    
    with open("experiment_manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)
    with open(os.path.join(artifacts_dir, "experiment_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)
        
    print("Successfully generated reproducibility indices and experiment manifest.")

