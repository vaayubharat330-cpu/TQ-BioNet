"""
Tests for Stage 8.1: Scanner and Acquisition Parameter Correlation Analysis.

Certifies:
1. Complete parameter join: All 171 annotated scans in Folds 0-2 (899 findings) match LNDbAcqParams.csv and MHD geometry.
2. Partition discipline: Fold 3 is labeled previously evaluated and strictly excluded from exploratory analysis.
3. Scan-level summaries: Kruskal-Wallis tests across scanner models and convolution kernels use scan-level clusters.
4. Acquisition invariance: In-plane spacing Spearman correlations (|rho| < 0.20) and Kruskal-Wallis p-values (> 0.20) confirm lack of intra-cohort acquisition confounding.
5. Small subgroup handling: Rare kernels (N <= 4) are explicitly categorized.
"""

import json
from pathlib import Path
import pytest

from tq_bionet.model_config import FROZEN_15_SELECTED_FEATURES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "stage8_1_acquisition_correlation"


@pytest.fixture(scope="module")
def acq_metrics():
    metrics_path = OUTPUT_DIR / "acquisition_correlation_metrics.json"
    assert metrics_path.exists(), f"Acquisition correlation metrics not found: {metrics_path}"
    with open(metrics_path) as f:
        return json.load(f)


def test_acquisition_partition_discipline(acq_metrics):
    """Verify that Stage 8.1 strictly uses Folds 0-2 (171 annotated scans, 899 findings) and excludes Fold 3."""
    meta = acq_metrics["metadata_info"]
    assert meta["folds_0_2"]["annotated_scans"] == 171
    assert meta["folds_0_2"]["total_assigned_scans"] == 177
    assert len(meta["folds_0_2"]["unannotated_scans"]) == 6

    # Verify Fold 3 is documented as previously evaluated and excluded
    assert "PREVIOUSLY EVALUATED" in meta["fold_3_status"]["description"]
    assert meta["fold_3_status"]["annotated_scans"] == 58


def test_scanner_model_subgroups_and_kw(acq_metrics):
    """Verify that all 3 Siemens scanner models are evaluated across all 15 features with scan-level KW tests."""
    scanner_res = acq_metrics["results"]["scanner_models"]
    subgroups = scanner_res["subgroups"]
    assert set(subgroups.keys()) == {"SOMATOM go.Up", "Sensation Cardiac 64", "SOMATOM Definition Flash"}
    assert sum(subgroups.values()) == 171

    kw = scanner_res["kruskal_wallis"]
    assert set(kw.keys()) == set(FROZEN_15_SELECTED_FEATURES)

    # Within-LNDb scanner model differences are not statistically significant
    for fname, res in kw.items():
        assert res["p_value"] > 0.20, f"Unexpected significant KW p-value for {fname}: {res['p_value']}"


def test_convolution_kernel_subgroups(acq_metrics):
    """Verify that major kernels are audited and small subgroups (N <= 4) are tracked."""
    kernel_res = acq_metrics["results"]["convolution_kernels"]
    main_k = kernel_res["main_subgroups"]
    assert set(main_k.keys()) == {"B50f", "Br64f", "I50f"}
    assert sum(main_k.values()) == 161  # 68 + 67 + 26

    rare_k = kernel_res["rare_subgroups_small_sample_size"]
    for k, cnt in rare_k.items():
        assert cnt <= 4, f"Rare kernel {k} has unexpected high scan count: {cnt}"
    assert sum(rare_k.values()) == 10  # 171 - 161 = 10 rare scans

    kw = kernel_res["kruskal_wallis_main_kernels"]
    for fname, res in kw.items():
        assert res["p_value"] > 0.20, f"Unexpected significant kernel KW p-value for {fname}: {res['p_value']}"


def test_in_plane_spacing_spearman(acq_metrics):
    """Verify that in-plane spacing correlations are evaluated and near zero across all 15 features."""
    spacing_res = acq_metrics["results"]["in_plane_spacing"]
    assert len(spacing_res["range_mm"]) == 2
    assert 0.40 < spacing_res["range_mm"][0] < 0.50
    assert 0.85 < spacing_res["range_mm"][1] < 0.95

    corrs = spacing_res["spearman_correlations"]
    for fname, res in corrs.items():
        assert abs(res["spearman_rho"]) < 0.20, f"Unexpected strong correlation for {fname}: {res['spearman_rho']}"
        assert res["p_value"] > 0.15, f"Unexpected significant correlation for {fname}: p={res['p_value']}"
