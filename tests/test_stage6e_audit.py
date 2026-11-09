"""Focused tests for Stage 6E.1 integrity and sensitivity-analysis helpers."""

import numpy as np
import pandas as pd
import pytest

from stage6e_lndb_adaptation import (
    load_lndb_features_and_folds,
    compute_fold3_conflict_sensitivity,
    paired_scan_cluster_baseline_comparison,
)


def test_cache_alignment_rejects_row_reordering(tmp_path):
    gt = pd.DataFrame({
        "LNDbID": [1, 2],
        "x": [1.0, 2.0], "y": [3.0, 4.0], "z": [5.0, 6.0],
        "Nodule": [1, 0], "AgrLevel": [1, 0],
    })
    np.save(tmp_path / "X.npy", np.zeros((2, 31)))
    np.save(tmp_path / "y.npy", np.array([0, 1]))
    np.save(tmp_path / "groups.npy", np.array(["LNDb-0002", "LNDb-0001"]))
    np.save(tmp_path / "coords.npy", np.array([[2., 4., 6.], [1., 3., 5.]]))
    np.save(tmp_path / "agr_levels.npy", np.array([0, 1]))
    folds = tmp_path / "trainFolds.csv"
    pd.DataFrame({"Fold0": [1], "Fold1": [2], "Fold2": [np.nan], "Fold3": [np.nan]}).to_csv(folds, index=False)

    with pytest.raises(ValueError, match="not aligned"):
        load_lndb_features_and_folds(tmp_path, folds, gt)


def test_cache_alignment_accepts_exact_order(tmp_path):
    gt = pd.DataFrame({
        "LNDbID": [1, 2],
        "x": [1.0, 2.0], "y": [3.0, 4.0], "z": [5.0, 6.0],
        "Nodule": [1, 0], "AgrLevel": [1, 0],
    })
    np.save(tmp_path / "X.npy", np.zeros((2, 31)))
    np.save(tmp_path / "y.npy", np.array([1, 0]))
    np.save(tmp_path / "groups.npy", np.array(["LNDb-0001", "LNDb-0002"]))
    np.save(tmp_path / "coords.npy", np.array([[1., 3., 5.], [2., 4., 6.]]))
    np.save(tmp_path / "agr_levels.npy", np.array([1, 0]))
    folds = tmp_path / "trainFolds.csv"
    pd.DataFrame({"Fold0": [1], "Fold1": [2], "Fold2": [np.nan], "Fold3": [np.nan]}).to_csv(folds, index=False)

    out = load_lndb_features_and_folds(tmp_path, folds, gt)
    assert out["X"].shape == (2, 31)
    assert out["folds"].tolist() == ["Fold0", "Fold1"]


def test_conflict_sensitivity_collapses_only_conflicting_coordinate(tmp_path):
    gt = pd.DataFrame({
        "LNDbID": [278, 278, 288],
        "x": [1., 1., 2.], "y": [3., 3., 4.], "z": [5., 5., 6.],
        "Volume": [10., 20., 8.], "FindingID": [2, 4, 8],
    })
    out = compute_fold3_conflict_sensitivity(
        gt_df=gt,
        groups_test=np.array(["LNDb-0278", "LNDb-0278", "LNDb-0288"]),
        coords_test=np.array([[1., 3., 5.], [1., 3., 5.], [2., 4., 6.]]),
        raw_labels=np.array([0, 1, 0]),
        predictions=np.array([1, 1, 0]),
        probabilities=np.array([0.8, 0.8, 0.2]),
        agr_test=np.array([0, 1, 0]),
    )
    assert out["primary_rows"] == 3
    assert out["sensitivity_rows"] == 2
    assert out["conflicting_coordinate_groups_fold3"] == 1
    assert out["raw_rows_in_conflicting_groups_fold3"] == 2
    assert out["removed_rows_due_to_conflict_collapse"] == 1


def test_conflict_sensitivity_preserves_all_nonconflicting_duplicate_rows():
    # Identical labels at duplicated coordinates are not collapsed by this audit.
    gt = pd.DataFrame({
        "LNDbID": [5, 5],
        "x": [1., 1.], "y": [2., 2.], "z": [3., 3.],
        "Volume": [5., 4.], "FindingID": [1, 2],
    })
    out = compute_fold3_conflict_sensitivity(
        gt_df=gt,
        groups_test=np.array(["LNDb-0005", "LNDb-0005"]),
        coords_test=np.array([[1., 2., 3.], [1., 2., 3.]]),
        raw_labels=np.array([1, 1]),
        predictions=np.array([1, 0]),
        probabilities=np.array([0.8, 0.2]),
        agr_test=np.array([1, 1]),
    )
    assert out["sensitivity_rows"] == 2
    assert out["conflicting_coordinate_groups_fold3"] == 0


def test_paired_baseline_bootstrap_returns_expected_observed_delta():
    y = np.array([1, 0, 1, 0])
    pred = np.array([1, 1, 0, 0])
    groups = np.array(["A", "A", "B", "B"])
    out = paired_scan_cluster_baseline_comparison(y, pred, groups, n_bootstrap=200, seed=7)
    assert out["observed_accuracy_difference"] == pytest.approx(0.0)
    assert out["unique_scan_clusters"] == 2
    assert out["bootstrap_replicates"] == 200
