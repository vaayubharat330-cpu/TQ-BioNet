"""
Stage 6D: Multi-Resolution Extent-Preserving 3D Resampling Engine
================================================================

This module implements a physical-coordinate-preserving resampling engine for 3D CT volumes:
1. Calculates extent-preserving output dimensions:
      output_size = round((input_size - 1) * input_spacing / target_spacing) + 1
   preserving first-to-last voxel-center physical distance.
2. Maintains physical field of view (FOV ~32 mm) across target voxel spacings:
      - 0.7 mm  -> 46^3 voxels (32.2 mm FOV)
      - 0.8 mm  -> 40^3 voxels (32.0 mm FOV)
      - 1.0 mm  -> 32^3 voxels (32.0 mm FOV, baseline)
      - 1.25 mm -> 26^3 voxels (32.5 mm FOV)
      - 1.5 mm  -> 22^3 voxels (33.0 mm FOV)
3. Transforms physical coordinates directly through resampled grid geometry.
4. Extracts and normalizes cubic patches with standard local median/IQR bounds.
5. Computes and validates 31-feature TQ-BioNet feature vectors.
6. Manages isolated, versioned multi-resolution feature caches.
"""

from __future__ import annotations

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import SimpleITK as sitk

from tq_bionet.data_loader import extract_3d_patch
from tq_bionet.pipeline import extract_tq_bio_features, preprocess_patch
from tq_bionet.model_config import FROZEN_31_FEATURES

# Standard multi-resolution configurations maintaining constant ~32 mm physical FOV
SPACING_CONFIGS: Dict[str, Dict[str, Any]] = {
    "0.7mm": {
        "spacing": (0.7, 0.7, 0.7),
        "patch_size": 46,
        "physical_fov_mm": 32.2,
        "description": "High resolution isotropic (0.7 mm, 46^3 patch)"
    },
    "0.8mm": {
        "spacing": (0.8, 0.8, 0.8),
        "patch_size": 40,
        "physical_fov_mm": 32.0,
        "description": "Fine isotropic matching near-native in-plane (0.8 mm, 40^3 patch)"
    },
    "1.0mm": {
        "spacing": (1.0, 1.0, 1.0),
        "patch_size": 32,
        "physical_fov_mm": 32.0,
        "description": "Standard v3.1 baseline isotropic (1.0 mm, 32^3 patch)"
    },
    "1.25mm": {
        "spacing": (1.25, 1.25, 1.25),
        "patch_size": 26,
        "physical_fov_mm": 32.5,
        "description": "Intermediate slice isotropic (1.25 mm, 26^3 patch)"
    },
    "1.5mm": {
        "spacing": (1.5, 1.5, 1.5),
        "patch_size": 22,
        "physical_fov_mm": 33.0,
        "description": "Coarser slice isotropic (1.5 mm, 22^3 patch)"
    }
}


def compute_extent_preserving_size(
    input_size: Tuple[int, int, int],
    input_spacing: Tuple[float, float, float],
    target_spacing: Tuple[float, float, float]
) -> List[int]:
    """
    Computes extent-preserving output grid size:
    round((size - 1) * spacing / target_spacing) + 1
    Preserves exact physical distance between first and last voxel centers.
    """
    new_size = []
    for i in range(3):
        if input_size[i] <= 1:
            new_size.append(1)
        else:
            extent = (input_size[i] - 1) * input_spacing[i]
            count = int(round(extent / target_spacing[i])) + 1
            new_size.append(max(1, count))
    return new_size


def compute_legacy_size(
    input_size: Tuple[int, int, int],
    input_spacing: Tuple[float, float, float],
    target_spacing: Tuple[float, float, float]
) -> List[int]:
    """Computes legacy output size: round(size * spacing / target_spacing)."""
    return [
        int(round(input_size[i] * input_spacing[i] / target_spacing[i]))
        for i in range(3)
    ]


def resample_volume_extent_preserving(
    image: sitk.Image,
    target_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    interpolator=sitk.sitkLinear,
    default_value: float = -1000.0
) -> sitk.Image:
    """
    Resample a 3D SimpleITK image to the target isotropic spacing preserving physical origin,
    direction matrix, and first-to-last voxel center physical extents.
    """
    old_size = image.GetSize()
    old_spacing = image.GetSpacing()

    new_size = compute_extent_preserving_size(old_size, old_spacing, target_spacing)

    resampler = sitk.ResampleImageFilter()
    resampler.SetInterpolator(interpolator)
    resampler.SetOutputSpacing(target_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetDefaultPixelValue(default_value)
    resampler.SetOutputPixelType(sitk.sitkFloat32)

    return resampler.Execute(image)


def extract_patch_at_physical_point(
    resampled_image: sitk.Image,
    resampled_array: np.ndarray,
    physical_point: Tuple[float, float, float],
    patch_size: int,
    fill_value: float = -1000.0
) -> np.ndarray:
    """
    Transforms physical coordinates (x, y, z mm) to the resampled image voxel index
    and extracts a cubic patch of size (patch_size, patch_size, patch_size) with padding.
    """
    voxel_coords = resampled_image.TransformPhysicalPointToIndex(physical_point)
    # SimpleITK index order: (x, y, z) -> numpy array order: (z, y, x)
    x_vox, y_vox, z_vox = voxel_coords[0], voxel_coords[1], voxel_coords[2]
    return extract_3d_patch(
        resampled_array,
        (z_vox, y_vox, x_vox),
        patch_size=patch_size,
        fill_value=fill_value
    )


def extract_features_from_patch(patch: np.ndarray) -> np.ndarray:
    """
    Normalizes a cubic patch with local median/IQR bounds and extracts 31 TQ-BioNet features.
    """
    if patch.ndim != 3 or patch.shape[0] != patch.shape[1] or patch.shape[1] != patch.shape[2]:
        raise ValueError(f"Input patch must be a cubic 3D volume, got shape {patch.shape}")

    normalized = preprocess_patch(patch)
    _, f_vec = extract_tq_bio_features(normalized)

    if len(f_vec) != 31:
        raise ValueError(f"Expected 31 features, got {len(f_vec)}")
    if not np.isfinite(f_vec).all():
        raise ValueError("Non-finite values encountered in extracted feature vector")

    return f_vec


def get_array_sha256(arr: np.ndarray) -> str:
    """Computes SHA-256 hash of a numpy array in C-contiguous layout."""
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()
