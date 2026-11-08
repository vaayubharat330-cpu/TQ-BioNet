import unittest
import tempfile
import shutil
import zipfile
import json
import joblib
from pathlib import Path
import numpy as np

from tq_bionet.data_loader import safe_extract_zip
from tq_bionet.scale_clinical_validation import reconstruct_combined_dataset, get_file_sha256
from tq_bionet.model_config import (
    fit_frozen_pipeline,
    save_pipeline_bundle,
    load_pipeline_bundle
)


class TestReadinessRepairs(unittest.TestCase):
    """
    Stage 4.4 Verification: Regression tests for secure archive extraction,
    bundle provenance integrity, resource-exhaustion defenses, and multi-array cache verification.
    """

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_extract_zip_prevents_zip_slip(self):
        """Verifies that archive members targeting outside directory trigger RuntimeError."""
        zip_path = self.temp_dir / "malicious.zip"
        target_dir = self.temp_dir / "staging"
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../evil.txt", "malicious payload")

        with self.assertRaises(RuntimeError) as ctx:
            safe_extract_zip(zip_path, target_dir)
        self.assertIn("Zip slip path traversal detected", str(ctx.exception))

    def test_safe_extract_zip_prevents_sibling_prefix_bypass(self):
        """Verifies that sibling paths sharing string prefix cannot bypass containment."""
        target_dir = self.temp_dir / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.temp_dir / "sibling.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../target_sibling/evil.txt", "sibling payload")

        with self.assertRaises(RuntimeError) as ctx:
            safe_extract_zip(zip_path, target_dir)
        self.assertIn("Zip slip path traversal detected", str(ctx.exception))

    def test_safe_extract_zip_rejects_symlinks(self):
        """Verifies that symlinks inside zip archives are rejected."""
        zip_path = self.temp_dir / "symlink.zip"
        target_dir = self.temp_dir / "staging"
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w") as zf:
            info = zipfile.ZipInfo("symlink_entry")
            info.external_attr = 0o120777 << 16
            zf.writestr(info, "/etc/passwd")

        with self.assertRaises(RuntimeError) as ctx:
            safe_extract_zip(zip_path, target_dir)
        self.assertIn("Symlinks are disallowed", str(ctx.exception))

    def test_safe_extract_zip_rejects_size_limit(self):
        """Verifies safe_extract_zip enforces uncompressed byte threshold."""
        zip_path = self.temp_dir / "large.zip"
        target_dir = self.temp_dir / "staging"
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("large.txt", "a" * 1000)

        # Set max_total_bytes to 500 bytes (smaller than 1000)
        with self.assertRaises(RuntimeError) as ctx:
            safe_extract_zip(zip_path, target_dir, max_total_bytes=500)
        self.assertIn("Archive exceeds safe uncompressed size limit", str(ctx.exception))

    def test_safe_extract_zip_normal_extraction(self):
        """Verifies legitimate zip extraction succeeds."""
        zip_path = self.temp_dir / "good.zip"
        target_dir = self.temp_dir / "staging"
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("subset0/scan1.mhd", "header content")
            zf.writestr("subset0/scan1.raw", "raw bytes")

        safe_extract_zip(zip_path, target_dir)
        self.assertTrue((target_dir / "subset0" / "scan1.mhd").exists())
        self.assertTrue((target_dir / "subset0" / "scan1.raw").exists())

    def test_pipeline_bundle_manifest_provenance(self):
        """Verifies manifest records real xgboost package version string, not module name."""
        rng = np.random.RandomState(42)
        X = rng.normal(size=(20, 15))
        y = rng.randint(0, 2, size=20)
        svm, xgb, rf, scaler = fit_frozen_pipeline(X, y)

        bundle_dir = self.temp_dir / "bundle"
        manifest = save_pipeline_bundle(bundle_dir, svm, xgb, rf, scaler)

        xgb_ver = manifest["package_versions"]["xgboost"]
        self.assertNotEqual(xgb_ver, "xgboost.sklearn")
        self.assertFalse(xgb_ver.endswith(".sklearn"))
        self.assertTrue(any(c.isdigit() for c in xgb_ver))

    def test_pipeline_bundle_rejects_missing_artifact(self):
        """Verifies load_pipeline_bundle raises FileNotFoundError if artifact missing."""
        rng = np.random.RandomState(42)
        X = rng.normal(size=(20, 15))
        y = rng.randint(0, 2, size=20)
        svm, xgb, rf, scaler = fit_frozen_pipeline(X, y)

        bundle_dir = self.temp_dir / "bundle"
        save_pipeline_bundle(bundle_dir, svm, xgb, rf, scaler)

        # Delete one model file
        (bundle_dir / "rf_model.joblib").unlink()

        with self.assertRaises(FileNotFoundError):
            load_pipeline_bundle(bundle_dir)

    def test_pipeline_bundle_rejects_incomplete_manifest(self):
        """Verifies load_pipeline_bundle raises ValueError if manifest missing required key."""
        rng = np.random.RandomState(42)
        X = rng.normal(size=(20, 15))
        y = rng.randint(0, 2, size=20)
        svm, xgb, rf, scaler = fit_frozen_pipeline(X, y)

        bundle_dir = self.temp_dir / "bundle"
        save_pipeline_bundle(bundle_dir, svm, xgb, rf, scaler)

        manifest_file = bundle_dir / "pipeline_manifest.json"
        with manifest_file.open("r", encoding="utf-8") as f:
            man = json.load(f)

        del man["artifact_hashes"]["scaler"]
        with manifest_file.open("w", encoding="utf-8") as f:
            json.dump(man, f, indent=2)

        with self.assertRaises(ValueError) as ctx:
            load_pipeline_bundle(bundle_dir)
        self.assertIn("missing required artifact hashes", str(ctx.exception))

    def test_pipeline_bundle_rejects_tampered_artifact(self):
        """Verifies load_pipeline_bundle detects hash mismatch on tampered model."""
        rng = np.random.RandomState(42)
        X = rng.normal(size=(20, 15))
        y = rng.randint(0, 2, size=20)
        svm, xgb, rf, scaler = fit_frozen_pipeline(X, y)

        bundle_dir = self.temp_dir / "bundle"
        save_pipeline_bundle(bundle_dir, svm, xgb, rf, scaler)

        svm_file = bundle_dir / "svm_model.joblib"
        data = bytearray(svm_file.read_bytes())
        data[10] ^= 0xFF
        svm_file.write_bytes(bytes(data))

        with self.assertRaises(ValueError) as ctx:
            load_pipeline_bundle(bundle_dir)
        self.assertIn("Hash mismatch on svm_model.joblib", str(ctx.exception))

    def test_cache_multi_array_tamper_detection(self):
        """Verifies reconstruct_combined_dataset detects tampering with y, groups, or coords."""
        data_dir = self.temp_dir / "luna16_data"
        cache_dir = data_dir / "cache" / "tq_bionet_v3_1" / "subset0"
        cache_dir.mkdir(parents=True, exist_ok=True)

        n = 10
        X = np.ones((n, 31), dtype=np.float64)
        y = np.zeros(n, dtype=np.int16)
        groups = np.array([f"scan_{i}" for i in range(n)])
        coords = np.zeros((n, 3), dtype=np.float64)

        X_p = cache_dir / "X.npy"
        y_p = cache_dir / "y.npy"
        g_p = cache_dir / "groups.npy"
        c_p = cache_dir / "coords.npy"

        np.save(X_p, X)
        np.save(y_p, y)
        np.save(g_p, groups)
        np.save(c_p, coords)

        meta = {
            "algorithm_version": "v3.1",
            "feature_version": "v3.1",
            "feature_dimension": 31,
            "subset_ids": [0],
            "array_hashes": {
                "X": get_file_sha256(str(X_p)),
                "y": get_file_sha256(str(y_p)),
                "groups": get_file_sha256(str(g_p)),
                "coords": get_file_sha256(str(c_p))
            }
        }
        with (cache_dir / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Valid load succeeds
        X_c, y_c, g_c, c_c, s_c = reconstruct_combined_dataset([0], str(data_dir))
        self.assertEqual(len(y_c), n)

        # Tamper with y.npy
        y_tampered = np.ones(n, dtype=np.int16)
        np.save(y_p, y_tampered)

        # Reconstruct must fail on y checksum mismatch
        with self.assertRaises(ValueError) as ctx:
            reconstruct_combined_dataset([0], str(data_dir))
        self.assertIn("y cache SHA256 mismatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
