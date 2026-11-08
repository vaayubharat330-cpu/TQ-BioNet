import unittest
import tempfile
import shutil
import zipfile
import json
import joblib
from pathlib import Path
import numpy as np

from tq_bionet.data_loader import safe_extract_zip
from tq_bionet.model_config import (
    fit_frozen_pipeline,
    save_pipeline_bundle,
    load_pipeline_bundle
)


class TestReadinessRepairs(unittest.TestCase):
    """
    Stage 4.4 Verification: Regression tests for secure archive extraction,
    bundle provenance integrity, and tamper detection.
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
            # Traversal entry
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
            # Sibling entry: /temp/target_sibling/evil.txt
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
            # Set UNIX symlink mode: 0o120777 << 16
            info.external_attr = 0o120777 << 16
            zf.writestr(info, "/etc/passwd")

        with self.assertRaises(RuntimeError) as ctx:
            safe_extract_zip(zip_path, target_dir)
        self.assertIn("Symlinks are disallowed", str(ctx.exception))

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
        # Must be valid version string like "1.7.6" or "2.0.0", not "xgboost.sklearn"
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

        # Remove scaler from artifact hashes
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

        # Tamper with svm_model.joblib
        svm_file = bundle_dir / "svm_model.joblib"
        data = bytearray(svm_file.read_bytes())
        data[10] ^= 0xFF  # flip byte
        svm_file.write_bytes(bytes(data))

        with self.assertRaises(ValueError) as ctx:
            load_pipeline_bundle(bundle_dir)
        self.assertIn("Hash mismatch on svm_model.joblib", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
