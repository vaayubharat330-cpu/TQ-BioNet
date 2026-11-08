import numpy as np
from collections import Counter

def verify_data_integrity(X, y, groups, coords, train_mask=None, test_mask=None):
    """
    Checks for duplicates and data leakage across the pipeline.
    Uses composite sample identities and patient-grouped coordinate verification.
    Returns True if PASS, raises ValueError on FAIL.
    """
    print("--------------------------------------------------")
    print("      DATA INTEGRITY & REPRODUCIBILITY AUDIT      ")
    print("--------------------------------------------------")
    
    # Ensure numpy array types
    X = np.array(X)
    y = np.array(y)
    groups = np.array(groups)
    coords = np.array(coords)
    
    # 1. Check duplicate patients leakage between train and test splits
    if train_mask is not None and test_mask is not None:
        train_patients = set(groups[train_mask])
        test_patients = set(groups[test_mask])
        overlap = train_patients.intersection(test_patients)
        if len(overlap) > 0:
            print(f"[FAIL] Data Leakage Detected! {len(overlap)} patients overlap between train and test splits.")
            raise ValueError("FAIL: Patient train/test split leakage detected.")
        else:
            print("[PASS] Patient splitting respected (no overlap between splits).")
            
    # 2. Check composite Sample Identity duplicates
    # Unique Sample identity definition: (patient_id, x, y, z, label)
    sample_identities = []
    for i in range(len(y)):
        patient_id = str(groups[i])
        x_val = round(float(coords[i, 0]), 4)
        y_val = round(float(coords[i, 1]), 4)
        z_val = round(float(coords[i, 2]), 4)
        label_val = int(y[i])
        sample_identities.append((patient_id, x_val, y_val, z_val, label_val))
        
    counts = Counter(sample_identities)
    dup_sample_count = sum(1 for item, count in counts.items() if count > 1)
    if dup_sample_count > 0:
        print(f"[FAIL] Duplicate Sample Identities Detected! {dup_sample_count} composite sample IDs occur multiple times.")
        raise ValueError("FAIL: Duplicate composite sample IDs detected.")
    else:
        print("[PASS] Composite sample identities are unique.")
        
    # 3. Check duplicate coordinates INSIDE the same patient
    # Group coordinates by patient seriesuid
    patient_coords_map = {}
    for i in range(len(y)):
        pid = str(groups[i])
        pt_coords = (round(float(coords[i, 0]), 4), round(float(coords[i, 1]), 4), round(float(coords[i, 2]), 4))
        if pid not in patient_coords_map:
            patient_coords_map[pid] = []
        patient_coords_map[pid].append(pt_coords)
        
    dup_coords_in_patient = 0
    for pid, pt_coord_list in patient_coords_map.items():
        coord_counts = Counter(pt_coord_list)
        dup_coords_in_patient += sum(1 for item, count in coord_counts.items() if count > 1)
        
    if dup_coords_in_patient > 0:
        print(f"[FAIL] Duplicate coordinates detected inside same patient scans: {dup_coords_in_patient} overlaps.")
        raise ValueError("FAIL: Duplicate patch coordinates within patient detected.")
    else:
        print("[PASS] Coordinates within each patient scan are unique.")
        
    # 4. Check duplicate feature vectors
    unique_vectors, vector_counts = np.unique(X, axis=0, return_counts=True)
    duplicate_vectors_count = np.sum(vector_counts > 1)
    if duplicate_vectors_count > 0:
        print(f"[FAIL] Duplicate Feature Vectors Detected! {duplicate_vectors_count} feature vectors are identical.")
        raise ValueError("FAIL: Duplicate feature vectors detected in matrix.")
    else:
        print("[PASS] Feature vectors are unique (no duplicates).")
        
    # 5. Check patient IDs formatting
    invalid_ids = np.sum((groups == "") | (groups == None))
    if invalid_ids > 0:
        print(f"[FAIL] Invalid Patient/Sample IDs detected: {invalid_ids} rows are invalid.")
        raise ValueError("FAIL: Invalid sample IDs in patient groups.")
    else:
        print("[PASS] Patient IDs formatting verified.")
        
    print("[PASS] Data integrity checks completed successfully.")
    print("--------------------------------------------------")
    return True
