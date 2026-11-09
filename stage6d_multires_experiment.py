"""
Stage 6D: Multi-Resolution Resampling and Zero-Shot Evaluation Pipeline
======================================================================

Executes controlled multi-resolution CT resampling experiments on LNDb while holding
the physical field of view constant at ~32 mm:
  - 0.7 mm  (46^3 patch, 32.2 mm FOV)
  - 0.8 mm  (40^3 patch, 32.0 mm FOV)
  - 1.0 mm  (32^3 patch, 32.0 mm FOV, baseline v3.1)
  - 1.25 mm (26^3 patch, 32.5 mm FOV)
  - 1.5 mm  (22^3 patch, 33.0 mm FOV)

Maintains isolated versioned caches on D:\\ drive and evaluates the frozen v3.1
pipeline without retraining or parameter adjustment.
"""

from __future__ import annotations

import argparse
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import SimpleITK as sitk

from tq_bionet.resampling_engine import (
    SPACING_CONFIGS,
    resample_volume_extent_preserving,
    extract_patch_at_physical_point,
    extract_features_from_patch,
    get_array_sha256
)
from tq_bionet.model_config import (
    DEFAULT_DECISION_THRESHOLD,
    load_pipeline_bundle,
    predict_ensemble,
    prune_to_selected_features
)
from tq_bionet.evaluation_metrics import compute_cluster_bootstrap_ci, compute_wilson_ci
from sklearn.metrics import (
    accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix
)


def extract_cohort_features_at_spacing(
    spacing_key: str,
    scans_dir: Path,
    ground_truth_df: pd.DataFrame,
    cache_dir: Path,
    progress_every: int = 20
) -> Dict[str, Any]:
    """
    Extracts features for all findings in ground_truth_df at the specified target resolution,
    and caches the resulting arrays with multi-array SHA-256 verification.
    """
    cfg = SPACING_CONFIGS[spacing_key]
    target_spacing = cfg["spacing"]
    patch_size = cfg["patch_size"]
    physical_fov = cfg["physical_fov_mm"]

    spacing_cache_dir = cache_dir / spacing_key
    spacing_cache_dir.mkdir(parents=True, exist_ok=True)

    x_path = spacing_cache_dir / "X.npy"
    y_path = spacing_cache_dir / "y.npy"
    groups_path = spacing_cache_dir / "groups.npy"
    coords_path = spacing_cache_dir / "coords.npy"
    agr_path = spacing_cache_dir / "agr_levels.npy"
    meta_path = spacing_cache_dir / "metadata.json"

    # Reuse cache if fully valid
    if (x_path.exists() and y_path.exists() and groups_path.exists() and
        coords_path.exists() and agr_path.exists() and meta_path.exists()):
        print(f"   [{spacing_key}] Existing validated cache found at {spacing_cache_dir}. Loading...")
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        X = np.load(x_path)
        y = np.load(y_path)
        groups = np.load(groups_path)
        coords = np.load(coords_path)
        agr_levels = np.load(agr_path)

        # Check hash integrity
        hashes = meta.get("array_hashes", {})
        if (hashes.get("X") == get_array_sha256(X) and
            hashes.get("y") == get_array_sha256(y) and
            hashes.get("groups") == get_array_sha256(groups)):
            print(f"   [{spacing_key}] Cache integrity verified ({len(X)} samples).")
            return {
                "X": X, "y": y, "groups": groups, "coords": coords,
                "agr_levels": agr_levels, "metadata": meta
            }
        else:
            print(f"   [{spacing_key}] Cache hash mismatch. Rebuilding...")

    print(f"\n[EXTRACTION] Processing cohort at {spacing_key} (spacing={target_spacing}, patch={patch_size}^3, FOV={physical_fov} mm)...")
    start_time = time.time()

    lndb_paths = {
        int(re.sub(r"[^\d]", "", p.stem)): p
        for p in scans_dir.glob("*.mhd")
    }

    feature_list, label_list, group_list, coord_list, agr_list = [], [], [], [], []
    scan_groups = ground_truth_df.groupby("LNDbID")
    total_scans = len(scan_groups)
    processed_scans = 0
    extraction_errors = []

    for scan_id, group in scan_groups:
        processed_scans += 1
        mhd_path = lndb_paths.get(int(scan_id))
        if not mhd_path or not mhd_path.is_file():
            extraction_errors.append(f"Scan LNDb-{int(scan_id):04d} file not found.")
            continue

        try:
            itk_img = sitk.ReadImage(str(mhd_path))
            resampled_img = resample_volume_extent_preserving(
                itk_img,
                target_spacing=target_spacing,
                interpolator=sitk.sitkLinear,
                default_value=-1000.0
            )
            resampled_arr = sitk.GetArrayFromImage(resampled_img)
        except Exception as e:
            extraction_errors.append(f"Scan LNDb-{int(scan_id):04d} resampling failed: {e}")
            continue

        for _, row in group.iterrows():
            pt = (float(row["x"]), float(row["y"]), float(row["z"]))
            try:
                patch = extract_patch_at_physical_point(
                    resampled_img,
                    resampled_arr,
                    pt,
                    patch_size=patch_size,
                    fill_value=-1000.0
                )
                f_vec = extract_features_from_patch(patch)
                feature_list.append(f_vec)
                label_list.append(int(row["Nodule"]))
                group_list.append(f"LNDb-{int(scan_id):04d}")
                coord_list.append(list(pt))
                agr_list.append(int(row["AgrLevel"]))
            except Exception as e:
                extraction_errors.append(f"Finding in scan {scan_id} failed: {e}")

        if processed_scans % progress_every == 0 or processed_scans == total_scans:
            print(f"   [{spacing_key}] Processed {processed_scans}/{total_scans} scans ({len(feature_list)} findings extracted)...", flush=True)

    X = np.asarray(feature_list, dtype=np.float64)
    y = np.asarray(label_list, dtype=np.int64)
    groups = np.asarray(group_list)
    coords = np.asarray(coord_list, dtype=np.float64)
    agr_levels = np.asarray(agr_list, dtype=np.int64)

    # Save arrays
    np.save(x_path, X)
    np.save(y_path, y)
    np.save(groups_path, groups)
    np.save(coords_path, coords)
    np.save(agr_path, agr_levels)

    meta = {
        "spacing_key": spacing_key,
        "target_spacing_xyz_mm": list(target_spacing),
        "patch_size_voxels": patch_size,
        "physical_fov_mm": physical_fov,
        "sample_count": len(y),
        "positive_count": int(np.sum(y == 1)),
        "negative_count": int(np.sum(y == 0)),
        "unique_scans": int(len(np.unique(groups))),
        "extraction_duration_seconds": float(time.time() - start_time),
        "errors_count": len(extraction_errors),
        "array_hashes": {
            "X": get_array_sha256(X),
            "y": get_array_sha256(y),
            "groups": get_array_sha256(groups),
            "coords": get_array_sha256(coords),
            "agr_levels": get_array_sha256(agr_levels)
        }
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"   [{spacing_key}] Feature cache saved ({len(X)} samples, {meta['extraction_duration_seconds']:.1f}s).")
    return {
        "X": X, "y": y, "groups": groups, "coords": coords,
        "agr_levels": agr_levels, "metadata": meta
    }


def evaluate_cohort(
    svm, xgb, rf, scaler,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    agr_levels: np.ndarray
) -> Dict[str, Any]:
    """Runs frozen model inference and computes bootstrap metrics and agreement stratification."""
    # Prune to frozen 15 features
    X_pruned = prune_to_selected_features(X)

    # Predict ensemble
    preds = predict_ensemble(svm, xgb, rf, scaler, X_pruned, threshold=DEFAULT_DECISION_THRESHOLD)
    y_prob = preds["ensemble_prob"]
    y_pred = preds["y_pred"]

    acc = accuracy_score(y, y_pred)
    sens = recall_score(y, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = precision_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)
    auc_roc = roc_auc_score(y, y_prob) if len(np.unique(y)) > 1 else 0.5
    ap = average_precision_score(y, y_prob) if len(np.unique(y)) > 1 else 0.5
    brier = brier_score_loss(y, y_prob)

    acc_ci = compute_cluster_bootstrap_ci(y, y_pred, groups, accuracy_score)
    f1_ci = compute_cluster_bootstrap_ci(y, y_pred, groups, f1_score)
    auc_ci = compute_cluster_bootstrap_ci(y, y_prob, groups, roc_auc_score)

    # Agreement level breakdown
    strat = {}
    for agr in sorted(np.unique(agr_levels)):
        mask = (agr_levels == agr)
        sub_y = y[mask]
        sub_pred = y_pred[mask]
        sub_acc = accuracy_score(sub_y, sub_pred) if len(sub_y) > 0 else 0.0
        strat[str(agr)] = {
            "n": int(len(sub_y)),
            "accuracy": float(sub_acc),
            "positive_count": int(np.sum(sub_y == 1))
        }

    return {
        "n": len(y),
        "accuracy": float(acc),
        "accuracy_95ci": acc_ci,
        "sensitivity": float(sens),
        "specificity": float(spec),
        "precision": float(prec),
        "f1": float(f1),
        "f1_95ci": f1_ci,
        "auc_roc": float(auc_roc),
        "auc_roc_95ci": auc_ci,
        "average_precision": float(ap),
        "brier_score": float(brier),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "agreement_stratification": strat
    }


def run_stage6d_experiment(
    scans_dir: Path,
    ground_truth_path: Path,
    cache_base_dir: Path,
    bundle_dir: Path,
    output_reports_dir: Path,
    spacings_to_run: List[str]
):
    print("======================================================================")
    print("     TQ-BioNet Stage 6D: Multi-Resolution Resampling Experiment      ")
    print("======================================================================\n")

    output_reports_dir.mkdir(parents=True, exist_ok=True)
    cache_base_dir.mkdir(parents=True, exist_ok=True)

    # Load ground truth
    df_gt = pd.read_csv(ground_truth_path)
    print(f"Ground truth loaded from {ground_truth_path}: {len(df_gt)} findings across {df_gt['LNDbID'].nunique()} scans.")

    # Load frozen model bundle
    print(f"Loading frozen v3.1 model bundle from {bundle_dir}...")
    svm, xgb, rf, scaler = load_pipeline_bundle(bundle_dir)
    print("Frozen pipeline bundle verified and loaded successfully.")

    comparison_results = {}

    for sp_key in spacings_to_run:
        if sp_key not in SPACING_CONFIGS:
            print(f"Warning: Unknown spacing key {sp_key}, skipping.")
            continue

        cohort_data = extract_cohort_features_at_spacing(
            spacing_key=sp_key,
            scans_dir=scans_dir,
            ground_truth_df=df_gt,
            cache_dir=cache_base_dir
        )

        metrics = evaluate_cohort(
            svm, xgb, rf, scaler,
            X=cohort_data["X"],
            y=cohort_data["y"],
            groups=cohort_data["groups"],
            agr_levels=cohort_data["agr_levels"]
        )

        cfg = SPACING_CONFIGS[sp_key]
        comparison_results[sp_key] = {
            "spacing_xyz_mm": cfg["spacing"],
            "patch_size_voxels": cfg["patch_size"],
            "physical_fov_mm": cfg["physical_fov_mm"],
            "description": cfg["description"],
            "metrics": metrics
        }

        print(f"\n[{sp_key}] Results:")
        print(f"   Accuracy:  {metrics['accuracy']:.4f} [95% CI: {metrics['accuracy_95ci'][0]:.3f} - {metrics['accuracy_95ci'][1]:.3f}]")
        print(f"   AUC-ROC:   {metrics['auc_roc']:.4f} [95% CI: {metrics['auc_roc_95ci'][0]:.3f} - {metrics['auc_roc_95ci'][1]:.3f}]")
        print(f"   F1-Score:  {metrics['f1']:.4f} [95% CI: {metrics['f1_95ci'][0]:.3f} - {metrics['f1_95ci'][1]:.3f}]")
        print(f"   Spec/Sens: {metrics['specificity']:.4f} / {metrics['sensitivity']:.4f}")
        print(f"   AgrLevel 3 (Unanimous) Accuracy: {metrics['agreement_stratification'].get('3', {}).get('accuracy', 0.0):.4f}")

    # Save comparison JSON
    comparison_path = output_reports_dir / "stage6d_multires_comparison.json"
    with comparison_path.open("w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2)

    # Generate Markdown Summary
    md_lines = [
        "# TQ-BioNet Stage 6D: Multi-Resolution Resampling Comparison",
        "",
        "This experiment evaluates the frozen v3.1 model bundle (trained on LUNA16 Subsets 0–5) across five isotropic resampling resolutions while holding the physical field of view constant at ~32 mm.",
        "",
        "| Spacing | Patch Size | Physical FOV | Accuracy [95% CI] | Sensitivity | Specificity | F1-Score | AUC-ROC [95% CI] | 3-Reader Acc |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for sp_key, res in comparison_results.items():
        m = res["metrics"]
        agr3 = m["agreement_stratification"].get("3", {}).get("accuracy", 0.0)
        md_lines.append(
            f"| **{sp_key}** | {res['patch_size_voxels']}^3 | {res['physical_fov_mm']:.1f} mm | "
            f"{m['accuracy']:.4f} [{m['accuracy_95ci'][0]:.3f}-{m['accuracy_95ci'][1]:.3f}] | "
            f"{m['sensitivity']:.4f} | {m['specificity']:.4f} | {m['f1']:.4f} | "
            f"{m['auc_roc']:.4f} [{m['auc_roc_95ci'][0]:.3f}-{m['auc_roc_95ci'][1]:.3f}] | "
            f"{agr3:.4f} |"
        )

    summary_md_path = output_reports_dir / "stage6d_multires_summary.md"
    with summary_md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\nStage 6D evaluation complete. Reports saved to {output_reports_dir}.")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scans-dir", type=Path, default=Path(r"D:\LNDb\extracted"))
    parser.add_argument("--ground-truth", type=Path, default=Path(r"D:\LNDb\annotations\trainset_csv\trainNodules_gt.csv"))
    parser.add_argument("--cache-base-dir", type=Path, default=Path(r"D:\LNDb\cache\stage6d"))
    parser.add_argument("--bundle-dir", type=Path, default=Path("outputs/frozen_v3_1_pipeline"))
    parser.add_argument("--output-reports-dir", type=Path, default=Path("outputs/stage6d_multires_evaluation"))
    parser.add_argument("--spacings", nargs="+", default=["0.8mm", "1.0mm", "1.25mm"],
                        choices=["0.7mm", "0.8mm", "1.0mm", "1.25mm", "1.5mm"])
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_stage6d_experiment(
        scans_dir=args.scans_dir,
        ground_truth_path=args.ground_truth,
        cache_base_dir=args.cache_base_dir,
        bundle_dir=args.bundle_dir,
        output_reports_dir=args.output_reports_dir,
        spacings_to_run=args.spacings
    )
