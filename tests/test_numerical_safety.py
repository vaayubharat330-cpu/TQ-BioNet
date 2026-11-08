import unittest
import numpy as np

from tq_bionet.quantum_module import build_1d_laplacian, build_3d_laplacian, solve_schrodinger_equation
from tq_bionet.fractal_module import compute_3d_lacunarity, extract_fractal_features, box_counting_3d


class TestNumericalSafety(unittest.TestCase):
    def test_laplacian_rejects_invalid_grid(self):
        with self.assertRaises(ValueError):
            build_1d_laplacian(1)
        with self.assertRaises(ValueError):
            build_3d_laplacian(0)

    def test_quantum_solver_rejects_non_cubic_and_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            solve_schrodinger_equation(np.zeros((3, 3, 4)))
        patch = np.zeros((3, 3, 3), dtype=float)
        patch[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            solve_schrodinger_equation(patch)

    def test_quantum_solver_caps_requested_eigenpairs(self):
        patch = np.zeros((3, 3, 3), dtype=float)
        values, waves, density = solve_schrodinger_equation(patch, num_eigenvalues=100)
        self.assertLessEqual(len(values), patch.size - 2)
        self.assertEqual(waves.shape[0], len(values))
        self.assertTrue(np.isfinite(density).all())
        self.assertAlmostEqual(float(density.max()), 1.0, places=6)

    def test_lacunarity_handles_box_larger_than_volume(self):
        mask = np.zeros((2, 2, 2), dtype=bool)
        self.assertEqual(compute_3d_lacunarity(mask, box_size=8), 0.0)
        mask[0, 0, 0] = True
        value = compute_3d_lacunarity(mask, box_size=8)
        self.assertTrue(np.isfinite(value))
        self.assertGreaterEqual(value, 1.0)

    def test_fractal_features_are_finite_for_degenerate_volume(self):
        density = np.zeros((4, 4, 4), dtype=float)
        features = extract_fractal_features(density)
        self.assertTrue(all(np.isfinite(v) for v in features.values()))

    def test_box_counting_rejects_non_3d_input(self):
        with self.assertRaises(ValueError):
            box_counting_3d(np.zeros((4, 4), dtype=bool))


if __name__ == "__main__":
    unittest.main()
