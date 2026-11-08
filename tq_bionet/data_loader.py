import os
import numpy as np
import SimpleITK as sitk
import pydicom

def load_mhd_image(mhd_path):
    """
    Loads an MHD/RAW image (standard in LUNA16) and returns the ITK image object,
    the raw 3D numpy array, the origin, and the spacing.
    """
    if not os.path.exists(mhd_path):
        raise FileNotFoundError(f"MHD file not found: {mhd_path}")
    
    itk_img = sitk.ReadImage(mhd_path)
    img_array = sitk.GetArrayFromImage(itk_img)  # Order: (Z, Y, X)
    origin = np.array(itk_img.GetOrigin())        # Order: (X, Y, Z)
    spacing = np.array(itk_img.GetSpacing())      # Order: (X, Y, Z)
    
    return itk_img, img_array, origin, spacing

def load_dicom_series(dicom_dir):
    """
    Loads a DICOM series from a directory (standard in LIDC-IDRI) and returns
    the ITK image object, the raw 3D numpy array, the origin, and the spacing.
    """
    if not os.path.exists(dicom_dir):
        raise FileNotFoundError(f"DICOM directory not found: {dicom_dir}")
        
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
    reader.SetFileNames(dicom_names)
    itk_img = reader.Execute()
    
    img_array = sitk.GetArrayFromImage(itk_img)  # Order: (Z, Y, X)
    origin = np.array(itk_img.GetOrigin())        # Order: (X, Y, Z)
    spacing = np.array(itk_img.GetSpacing())      # Order: (X, Y, Z)
    
    return itk_img, img_array, origin, spacing

def world_to_voxel(world_coords, origin, spacing, direction=None):
    """
    Convert physical (X, Y, Z) coordinates to NumPy (Z, Y, X) indices.

    SimpleITK maps physical points as: p = origin + direction @ (index * spacing).
    Direction is a row-major 3x3 direction-cosine matrix. Identity is used only
    when callers explicitly omit direction for axis-aligned images.
    """
    world_coords = np.asarray(world_coords, dtype=np.float64)
    origin = np.asarray(origin, dtype=np.float64)
    spacing = np.asarray(spacing, dtype=np.float64)
    direction = np.eye(3) if direction is None else np.asarray(direction, dtype=np.float64).reshape(3, 3)
    if world_coords.shape != (3,) or origin.shape != (3,) or spacing.shape != (3,):
        raise ValueError("world_coords, origin, and spacing must each have shape (3,)")
    if not np.all(np.isfinite(world_coords)) or not np.all(np.isfinite(origin)):
        raise ValueError("world coordinates and origin must be finite")
    if not np.all(np.isfinite(spacing)) or np.any(spacing <= 0):
        raise ValueError("spacing must contain finite positive values")
    if not np.all(np.isfinite(direction)) or abs(np.linalg.det(direction)) < 1e-10:
        raise ValueError("direction must be a finite invertible 3x3 matrix")
    continuous_index = np.linalg.solve(direction, world_coords - origin) / spacing
    voxel_xyz = np.rint(continuous_index).astype(int)
    return int(voxel_xyz[2]), int(voxel_xyz[1]), int(voxel_xyz[0])

def extract_3d_patch(img_array, voxel_center, patch_size=32, fill_value=-1000):
    """
    Extracts a 3D patch of size (patch_size, patch_size, patch_size) centered at voxel_center.
    Handles out-of-boundary cases by padding with fill_value.
    voxel_center order: (Z, Y, X)
    """
    z_c, y_c, x_c = voxel_center
    r = patch_size // 2
    
    # Define bounds in the original array
    z_min, z_max = z_c - r, z_c + r
    y_min, y_max = y_c - r, y_c + r
    x_min, x_max = x_c - r, x_c + r
    
    # Shapes
    sz, sy, sx = img_array.shape
    
    # Initialize patch with fill_value
    patch = np.full((patch_size, patch_size, patch_size), fill_value, dtype=img_array.dtype)
    
    # Compute intersection bounds
    z_start_src = max(0, z_min)
    z_end_src = min(sz, z_max)
    y_start_src = max(0, y_min)
    y_end_src = min(sy, y_max)
    x_start_src = max(0, x_min)
    x_end_src = min(sx, x_max)
    
    # Destination bounds in patch
    z_start_dst = z_start_src - z_min
    z_end_dst = z_end_src - z_min
    y_start_dst = y_start_src - y_min
    y_end_dst = y_end_src - y_min
    x_start_dst = x_start_src - x_min
    x_end_dst = x_end_src - x_min
    
    # Copy sub-volume if valid
    if (z_start_src < z_end_src) and (y_start_src < y_end_src) and (x_start_src < x_end_src):
        patch[z_start_dst:z_end_dst, y_start_dst:y_end_dst, x_start_dst:x_end_dst] = \
            img_array[z_start_src:z_end_src, y_start_src:y_end_src, x_start_src:x_end_src]
            
    return patch

def normalize_patch(patch, hu_min=-1000.0, hu_max=400.0):
    """
    Clips and normalizes HU values of a patch to [0, 1] scale.
    """
    clipped = np.clip(patch, hu_min, hu_max)
    normalized = (clipped - hu_min) / (hu_max - hu_min)
    return normalized

def patient_level_train_test_split(X_data, y_data, patient_ids, test_size=0.30, random_state=42):
    """
    Splits the dataset strictly at the patient level.
    Guarantees that all patches from the same patient go into the same split
    to prevent data leakage (overfitting evaluation).
    """
    unique_patients = np.unique(patient_ids)
    
    # Shuffle and split patient IDs
    rng = np.random.default_rng(seed=random_state)
    shuffled_patients = rng.permutation(unique_patients)
    
    split_idx = int(len(shuffled_patients) * (1.0 - test_size))
    train_patients = shuffled_patients[:split_idx]
    test_patients = shuffled_patients[split_idx:]
    
    # Filter indices based on patient split
    train_indices = [i for i, pid in enumerate(patient_ids) if pid in train_patients]
    test_indices = [i for i, pid in enumerate(patient_ids) if pid in test_patients]
    
    # Extract splits
    X_train = [X_data[i] for i in train_indices]
    X_test = [X_data[i] for i in test_indices]
    y_train = [y_data[i] for i in train_indices]
    y_test = [y_data[i] for i in test_indices]
    
    # Convert back to numpy array if inputs were arrays
    if isinstance(X_data, np.ndarray):
        X_train = np.array(X_train)
        X_test = np.array(X_test)
    if isinstance(y_data, np.ndarray):
        y_train = np.array(y_train)
        y_test = np.array(y_test)
        
    return X_train, X_test, y_train, y_test, train_indices, test_indices

import zipfile
from pathlib import Path

def safe_extract_zip(zip_file_path, target_dir, max_total_bytes=35 * (1024**3)):
    """
    Extracts a ZIP archive securely:
    - Verifies CRC32 archive integrity with testzip().
    - Protects against Zip Slip path traversal using Path.relative_to.
    - Rejects symlink entries.
    - Defends against resource-exhaustion zip bombs (total uncompressed size and compression ratios).
    - Extracts member-by-member securely.
    """
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        bad_file = zip_ref.testzip()
        if bad_file:
            raise RuntimeError(f"Corrupt entry inside zip archive: {bad_file}")

        total_uncompressed = 0
        for member in zip_ref.infolist():
            # Check for symlink attribute (UNIX mode 0o120000)
            mode = (member.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise RuntimeError(f"Symlinks are disallowed in archives: {member.filename}")

            # Check for Zip Slip traversal
            member_path = (target_dir / member.filename).resolve()
            try:
                member_path.relative_to(target_dir)
            except ValueError:
                raise RuntimeError(f"Zip slip path traversal detected: {member.filename}")

            # Resource exhaustion / Zip bomb checks
            total_uncompressed += member.file_size
            if total_uncompressed > max_total_bytes:
                raise RuntimeError(f"Archive exceeds safe uncompressed size limit ({max_total_bytes} bytes)")
            if member.compress_size > 0 and (member.file_size / member.compress_size > 100) and member.file_size > 10 * 1024 * 1024:
                raise RuntimeError(f"Potential zip bomb detected: anomalous compression ratio for {member.filename}")

            # Extract individual member safely
            zip_ref.extract(member, target_dir)
