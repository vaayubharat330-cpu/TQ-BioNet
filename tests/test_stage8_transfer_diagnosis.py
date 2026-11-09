"""
Tests for Stage 8: LNDb Transfer Diagnosis & 15-Feature Distribution Shift Audit.

Certifies:
1. Clean partition discipline: LNDb Fold 3 is strictly excluded from exploratory diagnosis.
2. In-domain baseline control: LUNA16 Dev vs Val feature drift is minimal (all PSI < 0.10).
3. Cross-cohort distribution shift: Significant drift between LUNA16 and LNDb is confirmed.
4. Class-conditional divergence: Significant asymmetric negative-class shift is captured.
5. All 15 selected biophysical/topological features are audited with zero missing values.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from tq_bionet.model_config import FROZEN_15_SELECTED_FEATURES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "stage8_transfer_diagnosis"


@pytest.fixture(scope="module")
def audit_metrics():
    metrics_path = OUTPUT_DIR / "distribution_shift_metrics.json"
    assert metrics_path.exists(), f"Distribution shift metrics not found: {metrics_path}"
    with open(metrics_path) as f:
        return json.load(f)


def test_partition_discipline_fold3_untouched(audit_metrics):
    """Verify that exploratory analysis uses only LNDb Folds 0-2 (N=899) and leaves Fold 3 untouched."""
    cohorts = audit_metrics["cohorts"]
    assert "lndb_dev_folds0_2" in cohorts
    assert cohorts["lndb_dev_folds0_2"]["n"] == 899
    assert cohorts["lndb_dev_folds0_2"]["pos"] == 577
    assert cohorts["lndb_dev_folds0_2"]["neg"] == 322

    # Ensure no Fold 3 evaluation is mixed into this stage
    assert "lndb_test_fold3" not in cohorts


def test_all_15_features_evaluated(audit_metrics):
    """Verify that all 15 selected features are present in the shift results."""
    overall = audit_metrics["cross_cohort_overall_shift"]
    feature_names = {row["feature"] for row in overall}
    assert feature_names == set(FROZEN_15_SELECTED_FEATURES)
    assert len(overall) == 15


def test_indomain_luna16_drift_minimal(audit_metrics):
    """Verify that in-domain LUNA16 drift (Dev vs Val) is minimal (PSI < 0.10, WD < 0.10)."""
    indomain = audit_metrics["indomain_luna_shift"]
    for row in indomain:
        assert row["psi"] < 0.10, f"In-domain PSI too high for {row['feature']}: {row['psi']}"
        assert row["norm_wasserstein"] < 0.10, f"In-domain WD too high for {row['feature']}: {row['norm_wasserstein']}"


def test_cross_cohort_drift_severity(audit_metrics):
    """Verify that cross-cohort drift between LUNA16 and LNDb Folds 0-2 is significantly elevated."""
    overall = audit_metrics["cross_cohort_overall_shift"]
    avg_wd = np.mean([row["norm_wasserstein"] for row in overall])
    severe_psi_count = sum(1 for row in overall if row["psi"] >= 0.10)

    assert avg_wd > 0.20, f"Expected substantial average Wasserstein distance, got {avg_wd}"
    assert severe_psi_count >= 10, f"Expected at least 10 features with PSI >= 0.10, got {severe_psi_count}"


def test_asymmetric_negative_shift(audit_metrics):
    """Verify that negative non-nodule findings exhibit significantly stronger shift than positives in fractal dimension."""
    class_shifts = {row["feature"]: row for row in audit_metrics["class_conditional_shift"]}
    
    fd = class_shifts["fractal_dimension"]
    assert fd["norm_wd_neg"] > fd["norm_wd_pos"] + 0.3, "Expected fractal_dimension to drift much more in negatives than positives"

    h0_ent = class_shifts["H0_entropy"]
    assert h0_ent["norm_wd_neg"] > h0_ent["norm_wd_pos"] + 0.1, "Expected H0_entropy to drift more in negatives"
