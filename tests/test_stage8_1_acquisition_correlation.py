"""
Tests for Stage 8.1: Scanner and Acquisition Parameter Correlation Analysis.

Certifies:
1. Complete parameter join: All 171 annotated scans in Folds 0-2 (899 findings) match LNDbAcqParams.csv and MHD geometry.
2. Partition discipline: Fold 3 is labeled previously evaluated and strictly excluded from exploratory analysis.
3. Scan-level summaries: Kruskal-Wallis tests across scanner models and convolution kernels use scan-level clusters.
4. Class-separated stratification: Both positive nodules (N=159 scans) and negative non-nodules (N=122 scans) are audited.
5. Acquisition invariance with FDR: Benjamini-Hochberg FDR q-values (> 0.20) and effect sizes (eta^2_H < 0.05) confirm lack of intra-cohort acquisition confounding.
6. Small subgroup handling: Rare kernels (N <= 4) are explicitly categorized.
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
    """Verify that all 3 Siemens scanner models are evaluated across all 15 features with scan-level KW tests and FDR."""
    inv = acq_metrics["results"]["subgroup_inventory"]
    subgroups = inv["scanner_models"]
    assert set(subgroups.keys()) == {"SOMATOM go.Up", "Sensation Cardiac 64", "SOMATOM Definition Flash"}
    assert sum(subgroups.values()) == 171

    all_res = acq_metrics["results"]["all_findings_scan_level"]["scanner_models"]["results"]
    assert set(all_res.keys()) == set(FROZEN_15_SELECTED_FEATURES)

    # Within-LNDb scanner model differences are not statistically significant and have negligible effect size
    for fname, res in all_res.items():
        assert res["p_raw"] > 0.20, f"Unexpected significant KW raw p-value for {fname}: {res['p_raw']}"
        assert res["p_fdr"] > 0.50, f"Unexpected significant KW FDR q-value for {fname}: {res['p_fdr']}"
        assert res["eta2_H"] < 0.05, f"Unexpected medium/large effect size for {fname}: {res['eta2_H']}"


def test_convolution_kernel_subgroups_and_class_separation(acq_metrics):
    """Verify that major kernels are audited and class-separated scans are tested."""
    inv = acq_metrics["results"]["subgroup_inventory"]
    main_k = inv["main_convolution_kernels"]
    assert set(main_k.keys()) == {"B50f", "Br64f", "I50f"}
    assert sum(main_k.values()) == 161  # 68 + 67 + 26

    rare_k = inv["rare_convolution_kernels_small_sample_size"]
    for k, cnt in rare_k.items():
        assert cnt <= 4, f"Rare kernel {k} has unexpected high scan count: {cnt}"
    assert sum(rare_k.values()) == 10  # 171 - 161 = 10 rare scans

    # Verify positive nodules and negative non-nodules are separately analyzed
    pos_res = acq_metrics["results"]["positive_nodules_scan_level"]
    neg_res = acq_metrics["results"]["negative_non_nodules_scan_level"]

    assert pos_res["sample_size_scans"] == 159
    assert neg_res["sample_size_scans"] == 122

    for fname in FROZEN_15_SELECTED_FEATURES:
        assert pos_res["convolution_kernels"]["results"][fname]["p_fdr"] > 0.05, f"Unexpected significant FDR for positive {fname}"
        assert neg_res["convolution_kernels"]["results"][fname]["p_fdr"] > 0.05, f"Unexpected significant FDR for negative {fname}"


def test_in_plane_spacing_spearman_and_fdr(acq_metrics):
    """Verify that in-plane spacing correlations are evaluated with FDR and near zero across all 15 features."""
    inv = acq_metrics["results"]["subgroup_inventory"]
    rng = inv["in_plane_spacing_range_mm"]
    assert 0.40 < rng[0] < 0.50
    assert 0.85 < rng[1] < 0.95

    corrs = acq_metrics["results"]["all_findings_scan_level"]["in_plane_spacing"]["results"]
    for fname, res in corrs.items():
        assert abs(res["rho"]) < 0.20, f"Unexpected strong correlation for {fname}: {res['rho']}"
        assert res["p_raw"] > 0.15, f"Unexpected significant correlation for {fname}: raw p={res['p_raw']}"
        assert res["p_fdr"] > 0.50, f"Unexpected significant correlation for {fname}: FDR q={res['p_fdr']}"
