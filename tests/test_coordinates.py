import unittest
import numpy as np
import SimpleITK as sitk

from tq_bionet.data_loader import world_to_voxel, extract_3d_patch


class TestCoordinateAndOrientationSuite(unittest.TestCase):
    """
    Stage 3 Verification: Coordinate geometry, image orientation, and patch extraction.
    Verifies physical-to-voxel mapping against SimpleITK ground-truth across
    identity, sagittal, coronal, anisotropic, and oblique direction matrices.
    """

    def _create_synthetic_itk_image(self, size, origin, spacing, direction):
        """Creates an in-memory SimpleITK image with specified geometry."""
        img = sitk.Image(size[0], size[1], size[2], sitk.sitkFloat32)
        img.SetOrigin(origin)
        img.SetSpacing(spacing)
        img.SetDirection(direction)
        return img

    def test_identity_orientation_against_simpleitk(self):
        """Verifies axis-aligned coordinate mapping matches SimpleITK."""
        size = [128, 128, 64]
        origin = [-100.0, -100.0, -200.0]
        spacing = [1.0, 1.0, 1.0]
        direction = [1, 0, 0,  0, 1, 0,  0, 0, 1]
        
        img = self._create_synthetic_itk_image(size, origin, spacing, direction)
        test_points = [
            [-100.0, -100.0, -200.0],
            [0.0, 0.0, -150.0],
            [27.4, -45.6, -140.2]
        ]
        
        for pt in test_points:
            sitk_xyz = img.TransformPhysicalPointToIndex(pt)
            expected_zyx = (sitk_xyz[2], sitk_xyz[1], sitk_xyz[0])
            computed_zyx = world_to_voxel(pt, origin, spacing, direction=np.eye(3))
            self.assertEqual(computed_zyx, expected_zyx)

    def test_anisotropic_spacing_against_simpleitk(self):
        """Verifies anisotropic voxel dimensions (e.g. 0.65 x 0.85 x 2.5 mm)."""
        size = [256, 256, 120]
        origin = [-150.2, -80.4, -400.0]
        spacing = [0.65, 0.85, 2.5]
        direction = [1, 0, 0,  0, 1, 0,  0, 0, 1]
        
        img = self._create_synthetic_itk_image(size, origin, spacing, direction)
        test_points = [
            [-150.2, -80.4, -400.0],
            [-50.0, 20.0, -200.0],
            [10.5, 85.0, -115.3]
        ]
        
        for pt in test_points:
            sitk_xyz = img.TransformPhysicalPointToIndex(pt)
            expected_zyx = (sitk_xyz[2], sitk_xyz[1], sitk_xyz[0])
            computed_zyx = world_to_voxel(pt, origin, spacing, direction=np.eye(3))
            self.assertEqual(computed_zyx, expected_zyx)

    def test_sagittal_and_coronal_orientations(self):
        """Verifies 90-degree anatomical axis flips (e.g. sagittal / coronal scans)."""
        size = [100, 100, 100]
        origin = [50.0, -50.0, 10.0]
        spacing = [1.2, 1.2, 1.2]

        # Coronal orientation: X->X, Y->Z, Z->-Y
        coronal_dir = [
            1, 0, 0,
            0, 0, 1,
            0, -1, 0
        ]
        img_coronal = self._create_synthetic_itk_image(size, origin, spacing, coronal_dir)
        pt = [80.0, -20.0, 40.0]
        sitk_xyz = img_coronal.TransformPhysicalPointToIndex(pt)
        expected_zyx = (sitk_xyz[2], sitk_xyz[1], sitk_xyz[0])
        computed_zyx = world_to_voxel(pt, origin, spacing, direction=coronal_dir)
        self.assertEqual(computed_zyx, expected_zyx)

        # Sagittal orientation: X->Y, Y->Z, Z->X
        sagittal_dir = [
            0, 1, 0,
            0, 0, 1,
            1, 0, 0
        ]
        img_sagittal = self._create_synthetic_itk_image(size, origin, spacing, sagittal_dir)
        sitk_xyz = img_sagittal.TransformPhysicalPointToIndex(pt)
        expected_zyx = (sitk_xyz[2], sitk_xyz[1], sitk_xyz[0])
        computed_zyx = world_to_voxel(pt, origin, spacing, direction=sagittal_dir)
        self.assertEqual(computed_zyx, expected_zyx)

    def test_oblique_direction_matrices(self):
        """Verifies continuous 3D rotation angles (arbitrary oblique scans)."""
        size = [128, 128, 128]
        origin = [-120.0, 30.0, -250.0]
        spacing = [0.8, 0.8, 1.25]

        # 35-degree rotation around Z axis, 15-degree around X axis
        az = np.radians(35.0)
        ax = np.radians(15.0)
        Rz = np.array([
            [np.cos(az), -np.sin(az), 0],
            [np.sin(az),  np.cos(az), 0],
            [0,          0,           1]
        ])
        Rx = np.array([
            [1, 0,           0],
            [0, np.cos(ax), -np.sin(ax)],
            [0, np.sin(ax),  np.cos(ax)]
        ])
        R_oblique = (Rz @ Rx).flatten().tolist()

        img_oblique = self._create_synthetic_itk_image(size, origin, spacing, R_oblique)
        test_points = [
            [-100.0, 50.0, -200.0],
            [-60.0, 80.0, -180.0],
            [-110.5, 45.3, -220.8]
        ]

        for pt in test_points:
            sitk_xyz = img_oblique.TransformPhysicalPointToIndex(pt)
            expected_zyx = (sitk_xyz[2], sitk_xyz[1], sitk_xyz[0])
            computed_zyx = world_to_voxel(pt, origin, spacing, direction=R_oblique)
            self.assertEqual(computed_zyx, expected_zyx)

    def test_round_trip_physical_to_voxel(self):
        """Round-trip: physical -> voxel -> reconstructed physical."""
        origin = np.array([-150.0, -150.0, -350.0])
        spacing = np.array([0.75, 0.75, 1.5])
        theta = np.radians(25.0)
        R = np.array([
            [np.cos(theta), -np.sin(theta), 0],
            [np.sin(theta),  np.cos(theta), 0],
            [0,             0,              1]
        ])
        
        # Test 20 arbitrary world points
        rng = np.random.RandomState(42)
        world_pts = rng.uniform(-100, 100, size=(20, 3))
        
        # Maximum theoretical physical displacement for half-voxel rounding:
        # ||Delta P||_2 = ||R @ (spacing * Delta I)||_2 = ||spacing * Delta I||_2 <= 0.5 * ||spacing||_2
        max_euclidean_error = 0.5 * np.linalg.norm(spacing)

        for w_pt in world_pts:
            zyx = world_to_voxel(w_pt, origin, spacing, direction=R)
            xyz_idx = np.array([zyx[2], zyx[1], zyx[0]], dtype=float)
            recon_pt = origin + R @ (xyz_idx * spacing)
            euclidean_error = np.linalg.norm(recon_pt - w_pt)
            self.assertLessEqual(
                euclidean_error, max_euclidean_error + 1e-6,
                f"Physical reconstruction error ({euclidean_error:.4f} mm) exceeds half-voxel diagonal ({max_euclidean_error:.4f} mm)"
            )

        # Also verify strict component-wise bounds for axis-aligned identity grid
        for w_pt in world_pts:
            zyx = world_to_voxel(w_pt, origin, spacing, direction=np.eye(3))
            xyz_idx = np.array([zyx[2], zyx[1], zyx[0]], dtype=float)
            recon_pt = origin + np.eye(3) @ (xyz_idx * spacing)
            component_error = np.abs(recon_pt - w_pt)
            self.assertTrue(np.all(component_error <= 0.5 * spacing + 1e-6))

    def test_extract_3d_patch_center_and_bounds(self):
        """Verifies interior patch extraction retains proper center and shape."""
        volume = np.arange(64 * 64 * 64, dtype=np.float32).reshape(64, 64, 64)
        center_zyx = (32, 32, 32)
        patch = extract_3d_patch(volume, center_zyx, patch_size=32)
        
        self.assertEqual(patch.shape, (32, 32, 32))
        # Center of extracted patch (index 16, 16, 16) must match volume at (32, 32, 32)
        self.assertEqual(patch[16, 16, 16], volume[32, 32, 32])

    def test_extract_3d_patch_all_six_faces(self):
        """Verifies padding behavior when candidate is centered on each of the 6 volume faces."""
        sz, sy, sx = 64, 64, 64
        fill_val = -1000.0
        volume = np.full((sz, sy, sx), 100.0, dtype=np.float32)

        face_centers = {
            '-Z face': (0, 32, 32),
            '+Z face': (sz - 1, 32, 32),
            '-Y face': (32, 0, 32),
            '+Y face': (32, sy - 1, 32),
            '-X face': (32, 32, 0),
            '+X face': (32, 32, sx - 1),
        }

        for face_name, center in face_centers.items():
            patch = extract_3d_patch(volume, center, patch_size=32, fill_value=fill_val)
            self.assertEqual(patch.shape, (32, 32, 32), f"[{face_name}] Patch must be exactly 32x32x32")
            # The nodule center is at (16, 16, 16)
            self.assertEqual(patch[16, 16, 16], 100.0, f"[{face_name}] Center must hold volume voxel")
            # Outside portions must be padded with fill_value
            self.assertTrue(np.any(patch == fill_val), f"[{face_name}] Outside boundary must contain fill_value")

    def test_extract_3d_patch_all_eight_corners(self):
        """Verifies padding when candidate is centered at volume corners."""
        sz, sy, sx = 64, 64, 64
        fill_val = -1000.0
        volume = np.full((sz, sy, sx), 50.0, dtype=np.float32)

        corners = [
            (0, 0, 0),
            (0, 0, sx - 1),
            (0, sy - 1, 0),
            (0, sy - 1, sx - 1),
            (sz - 1, 0, 0),
            (sz - 1, 0, sx - 1),
            (sz - 1, sy - 1, 0),
            (sz - 1, sy - 1, sx - 1)
        ]

        for c_idx, corner in enumerate(corners):
            patch = extract_3d_patch(volume, corner, patch_size=32, fill_value=fill_val)
            self.assertEqual(patch.shape, (32, 32, 32))
            self.assertEqual(patch[16, 16, 16], 50.0)
            self.assertTrue(np.any(patch == fill_val))


if __name__ == "__main__":
    unittest.main()
