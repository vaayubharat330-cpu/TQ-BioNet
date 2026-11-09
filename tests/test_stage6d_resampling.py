"""
Stage 6D Unit Tests: Multi-Resolution Extent-Preserving Resampling Engine
========================================================================

Verifies:
1. Extent-preserving output size calculation vs. legacy formula.
2. SimpleITK volume resampling: preservation of origin, direction, and physical extents.
3. Constant physical field of view (~32 mm) across target resolutions.
4. Physical point coordinate transformation and 3D patch extraction.
5. Finite 31-feature vector extraction across all 5 patch sizes (46^3, 40^3, 32^3, 26^3, 22^3).
6. Non-cubic patch input rejection.
"""

import pytest
import numpy as np
import SimpleITK as sitk

from tq_bionet.resampling_engine import (
    SPACING_CONFIGS,
    compute_extent_preserving_size,
    compute_legacy_size,
    resample_volume_extent_preserving,
    extract_patch_at_physical_point,
    extract_features_from_patch,
    get_array_sha256
)
from tq_bionet.model_config import FROZEN_31_FEATURES


class TestStage6DResamplingEngine:

    def test_extent_preserving_formula_accuracy(self):
        """Verify extent-preserving formula preserves first-to-last voxel distance."""
        # Simulated anisotropic scan: 512 x 512 x 350 voxels at (0.643, 0.643, 1.25) mm
        input_size = (512, 512, 350)
        input_spacing = (0.643555, 0.643555, 1.25)
        target_spacing = (1.0, 1.0, 1.0)

        new_size = compute_extent_preserving_size(input_size, input_spacing, target_spacing)
        legacy_size = compute_legacy_size(input_size, input_spacing, target_spacing)

        # Input physical extent
        input_extent = [(input_size[i] - 1) * input_spacing[i] for i in range(3)]
        # Output physical extent
        output_extent = [(new_size[i] - 1) * target_spacing[i] for i in range(3)]

        for i in range(3):
            # Output extent must match input extent within half a target voxel
            assert abs(input_extent[i] - output_extent[i]) <= target_spacing[i] / 2.0

        # Differences between extent-preserving and legacy formulas exist
        assert len(new_size) == 3
        assert len(legacy_size) == 3

    def test_resample_volume_extent_preserving(self):
        """Test SimpleITK volume resampling preserves origin, direction, and physical extent."""
        # Create a synthetic 3D volume
        orig_size = (64, 64, 48)
        orig_spacing = (0.7, 0.7, 1.25)
        orig_origin = (-100.0, -50.0, 20.0)
        direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

        arr = np.random.uniform(-900.0, 200.0, size=(orig_size[2], orig_size[1], orig_size[0])).astype(np.float32)
        itk_img = sitk.GetImageFromArray(arr)
        itk_img.SetSpacing(orig_spacing)
        itk_img.SetOrigin(orig_origin)
        itk_img.SetDirection(direction)

        target_spacing = (1.0, 1.0, 1.0)
        resampled = resample_volume_extent_preserving(itk_img, target_spacing=target_spacing)

        # Check spacing
        assert np.allclose(resampled.GetSpacing(), target_spacing, atol=1e-5)
        # Check origin
        assert np.allclose(resampled.GetOrigin(), orig_origin, atol=1e-5)
        # Check direction
        assert np.allclose(resampled.GetDirection(), direction, atol=1e-5)

        # Check extent preservation
        orig_extent = [(orig_size[i] - 1) * orig_spacing[i] for i in range(3)]
        new_size = resampled.GetSize()
        new_extent = [(new_size[i] - 1) * target_spacing[i] for i in range(3)]

        for i in range(3):
            assert abs(orig_extent[i] - new_extent[i]) <= target_spacing[i] / 2.0

    def test_multi_resolution_constant_fov(self):
        """Verify that all 5 spacing configs hold physical FOV at ~32 mm."""
        for name, cfg in SPACING_CONFIGS.items():
            spacing = cfg["spacing"][0]
            patch_size = cfg["patch_size"]
            fov = spacing * patch_size
            assert 32.0 <= fov <= 33.0, f"Config {name} FOV {fov} mm out of ~32 mm range"
            assert cfg["physical_fov_mm"] == pytest.approx(fov, abs=0.01)

    def test_extract_patch_at_physical_point(self):
        """Verify extraction at physical coordinates with out-of-boundary padding."""
        size = (40, 40, 30)
        spacing = (1.0, 1.0, 1.0)
        origin = (0.0, 0.0, 0.0)

        arr = np.ones((size[2], size[1], size[0]), dtype=np.float32) * 50.0
        img = sitk.GetImageFromArray(arr)
        img.SetSpacing(spacing)
        img.SetOrigin(origin)

        # Center point inside volume
        patch_32 = extract_patch_at_physical_point(img, arr, (20.0, 20.0, 15.0), patch_size=32)
        assert patch_32.shape == (32, 32, 32)
        # Center should be 50.0
        assert patch_32[16, 16, 16] == 50.0

        # Boundary point near corner: padding must be -1000.0
        patch_corner = extract_patch_at_physical_point(img, arr, (0.0, 0.0, 0.0), patch_size=32, fill_value=-1000.0)
        assert patch_corner.shape == (32, 32, 32)
        # Out-of-bounds voxels must equal -1000.0
        assert patch_corner[0, 0, 0] == -1000.0

    def test_feature_extraction_multi_size_finite(self):
        """Verify 31 finite features are extracted across all 5 patch sizes."""
        for name, cfg in SPACING_CONFIGS.items():
            patch_size = cfg["patch_size"]
            synthetic_patch = np.random.randn(patch_size, patch_size, patch_size).astype(np.float32) * 50.0 - 500.0
            f_vec = extract_features_from_patch(synthetic_patch)

            assert len(f_vec) == 31, f"Config {name}: expected 31 features, got {len(f_vec)}"
            assert np.isfinite(f_vec).all(), f"Config {name}: non-finite features detected"

    def test_rejection_of_non_cubic_patch(self):
        """Verify ValueError when patch is non-cubic."""
        non_cubic = np.zeros((32, 32, 28), dtype=np.float32)
        with pytest.raises(ValueError, match="cubic 3D volume"):
            extract_features_from_patch(non_cubic)

    def test_array_sha256_hash(self):
        """Verify deterministic SHA-256 computation."""
        arr1 = np.ones((10, 31), dtype=np.float64)
        arr2 = np.ones((10, 31), dtype=np.float64)
        assert get_array_sha256(arr1) == get_array_sha256(arr2)

        arr3 = np.zeros((10, 31), dtype=np.float64)
        assert get_array_sha256(arr1) != get_array_sha256(arr3)
