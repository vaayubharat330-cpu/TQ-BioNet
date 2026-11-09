"""
Stage 6B: zero-shot external validation on the official LNDb public cohort.

This script uses the frozen TQ-BioNet v3.1 bundle trained on LUNA16 subsets 0-5.
It never fits, fine-tunes, calibrates, or selects thresholds on LNDb.
Labels come only from the official trainNodules_gt.csv Nodule column.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
import sklearn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
import scipy
import xgboost

warnings.filterwarnings("ignore", category=UserWarning, module="ripser")

from tq_bionet.data_loader import extract_3d_patch
from tq_bionet.evaluation_metrics import compute_cluster_bootstrap_ci, compute_wilson_ci
from tq_bionet.model_config import (
    FROZEN_31_FEATURES,
    FROZEN_15_SELECTED_FEATURES,
    DEFAULT_DECISION_THRESHOLD,
    load_pipeline_bundle,
    predict_ensemble,
    prune_to_selected_features,
)
from tq_bionet.pipeline import extract_tq_bio_features, preprocess_patch


PATCH_SIZE = 32
ISOTROPIC_SPACING = (1.0, 1.0, 1.0)
EXPECTED_GT_COLUMNS = {
    "LNDbID", "FindingID", "x", "y", "z", "AgrLevel", "Nodule"
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unavailable"


def resample_isotropic(image: sitk.Image) -> sitk.Image:
    """Match the LUNA16 v3.1 resampling geometry: preserve origin/direction."""
    old_size = image.GetSize()
    old_spacing = image.GetSpacing()
    new_size = [
        int(round(old_size[i] * old_spacing[i] / ISOTROPIC_SPACING[i]))
        for i in range(3)
    ]
    if any(size < PATCH_SIZE for size in new_size):
        raise ValueError(f"Resampled image dimensions too small: {new_size}")

    resampler = sitk.ResampleImageFilter()
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetOutputSpacing(ISOTROPIC_SPACING)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetDefaultPixelValue(-1000.0)
    resampler.SetOutputPixelType(sitk.sitkFloat32)
    return resampler.Execute(image)


def validate_ground_truth(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Official ground truth not found: {csv_path}. "
            "Expected trainNodules_gt.csv from trainset_csv.zip."
        )

    frame = pd.read_csv(csv_path)
    missing = EXPECTED_GT_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Ground-truth CSV missing required columns: {sorted(missing)}")

    required = ["LNDbID", "FindingID", "x", "y", "z", "AgrLevel", "Nodule"]
    if frame[required].isna().any().any():
        raise ValueError("Ground-truth CSV contains nulls in required columns.")
    if not frame["Nodule"].isin([0, 1]).all():
        raise ValueError("Nodule labels must be binary 0/1.")
    if not frame["AgrLevel"].isin([0, 1, 2, 3]).all():
        raise ValueError("Unexpected AgrLevel values.")
    if not np.isfinite(frame[["x", "y", "z"]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite physical coordinates in ground truth.")
    if frame.duplicated(["LNDbID", "FindingID"]).any():
        duplicates = frame.loc[
            frame.duplicated(["LNDbID", "FindingID"], keep=False),
            ["LNDbID", "FindingID"]
        ].head(10)
        raise ValueError(
            "Duplicate (LNDbID, FindingID) records detected: "
            + duplicates.to_dict(orient="records").__repr__()
        )

    frame["LNDbID"] = frame["LNDbID"].astype(int)
    frame["FindingID"] = frame["FindingID"].astype(int)
    frame["Nodule"] = frame["Nodule"].astype(int)
    frame["AgrLevel"] = frame["AgrLevel"].astype(int)
    return frame.sort_values(["LNDbID", "FindingID"]).reset_index(drop=True)


def extract_features(
    ground_truth: pd.DataFrame,
    extracted_dir: Path,
    progress_every: int = 10,
):
    mhd_by_id = {}
    for path in extracted_dir.glob("*.mhd"):
        stem = path.stem
        if not stem.startswith("LNDb-"):
            continue
        try:
            scan_id = int(stem.split("-", 1)[1])
        except ValueError:
            continue
        if scan_id in mhd_by_id:
            raise RuntimeError(f"Multiple MHD files found for LNDbID {scan_id}")
        mhd_by_id[scan_id] = path

    if not mhd_by_id:
        raise FileNotFoundError(f"No LNDb-*.mhd files found in {extracted_dir}")

    gt_ids = set(ground_truth["LNDbID"].unique().tolist())
    available_ids = set(mhd_by_id)
    missing_scans = sorted(gt_ids - available_ids)
    if missing_scans:
        raise RuntimeError(
            f"{len(missing_scans)} ground-truth scan IDs have no extracted MHD: "
            f"{missing_scans[:20]}"
        )

    if len(FROZEN_31_FEATURES) != 31 or len(FROZEN_15_SELECTED_FEATURES) != 15:
        raise RuntimeError("Frozen v3.1 feature schema has unexpected dimensions.")

    records = []
    feature_rows = []
    exclusions = []
    scan_ids = sorted(gt_ids)
    start = time.perf_counter()

    for scan_number, scan_id in enumerate(scan_ids, start=1):
        scan_rows = ground_truth[ground_truth["LNDbID"] == scan_id]
        mhd_path = mhd_by_id[scan_id]
        raw_path = mhd_path.with_suffix(".raw")

        try:
            if not raw_path.is_file() or raw_path.stat().st_size == 0:
                raise FileNotFoundError(f"Missing or empty paired RAW: {raw_path}")
            source_image = sitk.ReadImage(str(mhd_path))
            image_1mm = resample_isotropic(source_image)
            volume = sitk.GetArrayFromImage(image_1mm)
        except Exception as exc:
            for row in scan_rows.itertuples(index=False):
                exclusions.append({
                    "LNDbID": int(row.LNDbID),
                    "FindingID": int(row.FindingID),
                    "reason": f"scan_load_or_resample_failed: {type(exc).__name__}: {exc}",
                })
            continue

        for row in scan_rows.itertuples(index=False):
            key = (int(row.LNDbID), int(row.FindingID))
            try:
                physical_point = (float(row.x), float(row.y), float(row.z))
                voxel_xyz = image_1mm.TransformPhysicalPointToIndex(physical_point)
                voxel_zyx = (voxel_xyz[2], voxel_xyz[1], voxel_xyz[0])

                patch = extract_3d_patch(
                    volume, voxel_zyx, patch_size=PATCH_SIZE, fill_value=-1000.0
                )
                if patch.shape != (PATCH_SIZE, PATCH_SIZE, PATCH_SIZE):
                    raise ValueError(f"Unexpected patch shape: {patch.shape}")
                normalized = preprocess_patch(patch)
                feature_dict, feature_vector = extract_tq_bio_features(normalized)

                actual_names = sorted(
                    name for name in feature_dict if name != "extraction_time_sec"
                )
                if actual_names != FROZEN_31_FEATURES:
                    raise ValueError(
                        "Extracted feature names/order do not match frozen v3.1 schema."
                    )
                if feature_vector.shape != (31,) or not np.isfinite(feature_vector).all():
                    raise ValueError("Feature vector has invalid shape or non-finite values.")

                feature_rows.append(feature_vector)
                records.append({
                    "LNDbID": key[0],
                    "FindingID": key[1],
                    "x": float(row.x),
                    "y": float(row.y),
                    "z": float(row.z),
                    "AgrLevel": int(row.AgrLevel),
                    "y_true": int(row.Nodule),
                })
            except Exception as exc:
                exclusions.append({
                    "LNDbID": key[0],
                    "FindingID": key[1],
                    "reason": f"patch_or_feature_failed: {type(exc).__name__}: {exc}",
                })

        if scan_number % progress_every == 0 or scan_number == len(scan_ids):
            print(
                f"Processed {scan_number}/{len(scan_ids)} annotated scans; "
                f"features={len(feature_rows)}, exclusions={len(exclusions)}",
                flush=True,
            )

    if not feature_rows:
        raise RuntimeError("No LNDb features were extracted successfully.")

    X_all = np.vstack(feature_rows).astype(np.float64, copy=False)
    y = np.asarray([record["y_true"] for record in records], dtype=np.int8)
    groups = np.asarray([record["LNDbID"] for record in records], dtype=np.int32)
    if X_all.shape != (len(records), 31) or len(y) != len(groups):
        raise RuntimeError("Extracted feature/label/group arrays have inconsistent shapes.")
    if set(np.unique(y)) != {0, 1}:
        raise RuntimeError("Both classes are required for external evaluation.")

    print(f"Feature extraction finished in {time.perf_counter() - start:.1f}s.")
    return X_all, y, groups, records, exclusions, sorted(mhd_by_id)


def evaluate_one_model(y_true, probabilities, groups, threshold):
    predictions = (probabilities >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    n = len(y_true)
    positives = int(np.sum(y_true == 1))
    negatives = int(np.sum(y_true == 0))
    predicted_positive = int(np.sum(predictions == 1))

    metrics = {
        "n": int(n),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "accuracy_wilson_95ci": compute_wilson_ci(
            int(np.sum(predictions == y_true)), n
        ),
        "sensitivity": float(recall_score(y_true, predictions, zero_division=0)),
        "sensitivity_wilson_95ci": compute_wilson_ci(tp, positives),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else None,
        "specificity_wilson_95ci": compute_wilson_ci(tn, negatives),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "precision_wilson_95ci": compute_wilson_ci(tp, predicted_positive),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "auc_roc": float(roc_auc_score(y_true, probabilities)),
        "average_precision": float(average_precision_score(y_true, probabilities)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "decision_threshold": float(threshold),
    }
    # Resample entire scans, not individual findings, for clustered uncertainty.
    for metric_name, metric_fn, values in (
        ("accuracy", accuracy_score, predictions),
        ("f1", f1_score, predictions),
        ("auc_roc", roc_auc_score, probabilities),
    ):
        metrics[f"{metric_name}_scan_cluster_bootstrap_95ci"] = (
            compute_cluster_bootstrap_ci(
                y_true, values, groups, metric_fn, num_resamples=1000,
                confidence=0.95, random_seed=42
            )
        )
    return metrics, predictions


def save_curves(y_true, probability_sets, output_dir: Path):
    plt.figure(figsize=(7, 6))
    for name, probabilities in probability_sets.items():
        fpr, tpr, _ = roc_curve(y_true, probabilities)
        plt.plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_true, probabilities):.4f})")
    plt.plot([0, 1], [0, 1], linestyle="--", label="Chance")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("LNDb zero-shot external validation — ROC")
    plt.grid(True, linestyle=":")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(output_dir / "roc_curve.png", dpi=220)
    plt.close()

    plt.figure(figsize=(7, 6))
    for name, probabilities in probability_sets.items():
        from sklearn.metrics import precision_recall_curve
        precision, recall, _ = precision_recall_curve(y_true, probabilities)
        ap = average_precision_score(y_true, probabilities)
        plt.plot(recall, precision, label=f"{name} (AP={ap:.4f})")
    plt.axhline(float(np.mean(y_true)), linestyle="--", label="Positive prevalence")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("LNDb zero-shot external validation — Precision/Recall")
    plt.grid(True, linestyle=":")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(output_dir / "precision_recall_curve.png", dpi=220)
    plt.close()


def run_lndb_validation(args):
    project_root = Path(__file__).resolve().parent
    extracted_dir = Path(args.extracted_dir).resolve()
    ground_truth_path = Path(args.ground_truth).resolve()
    bundle_dir = Path(args.bundle_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not extracted_dir.is_dir():
        raise FileNotFoundError(f"LNDb extracted directory not found: {extracted_dir}")

    print("TQ-BioNet v3.1 — Stage 6B zero-shot LNDb external validation")
    print(f"Ground truth: {ground_truth_path}")
    print(f"CT volumes:  {extracted_dir}")
    print(f"Frozen model: {bundle_dir}")

    # Verify model hashes and feature schema before reading any CT volume.
    svm, xgb_model, rf, scaler, model_manifest = load_pipeline_bundle(bundle_dir)
    if model_manifest.get("decision_threshold") != DEFAULT_DECISION_THRESHOLD:
        raise RuntimeError("Loaded bundle threshold differs from frozen v3.1 threshold.")
    if model_manifest.get("selected_features_15") != FROZEN_15_SELECTED_FEATURES:
        raise RuntimeError("Loaded bundle feature selection differs from frozen v3.1.")
    model_hashes = dict(model_manifest["artifact_hashes"])

    ground_truth = validate_ground_truth(ground_truth_path)
    print(
        f"Ground truth rows={len(ground_truth)}; "
        f"positive={int((ground_truth.Nodule == 1).sum())}; "
        f"negative={int((ground_truth.Nodule == 0).sum())}; "
        f"annotated scans={ground_truth.LNDbID.nunique()}"
    )
    print("AgrLevel distribution:")
    print(
        ground_truth.groupby(["AgrLevel", "Nodule"]).size()
        .rename("findings").to_string()
    )

    X_all, y_true, groups, records, exclusions, all_scan_ids = extract_features(
        ground_truth, extracted_dir, progress_every=args.progress_every
    )
    X_selected = prune_to_selected_features(X_all)
    prediction_bundle = predict_ensemble(
        svm, xgb_model, rf, scaler, X_selected,
        threshold=DEFAULT_DECISION_THRESHOLD
    )

    probability_sets = {
        "SVM": prediction_bundle["svm_prob"],
        "XGBoost": prediction_bundle["xgb_prob"],
        "Random Forest": prediction_bundle["rf_prob"],
        "Ensemble": prediction_bundle["ensemble_prob"],
    }
    metrics = {}
    prediction_columns = pd.DataFrame(records)
    prediction_columns["svm_probability"] = probability_sets["SVM"]
    prediction_columns["xgb_probability"] = probability_sets["XGBoost"]
    prediction_columns["rf_probability"] = probability_sets["Random Forest"]
    prediction_columns["ensemble_probability"] = probability_sets["Ensemble"]

    for name, probabilities in probability_sets.items():
        result, predictions = evaluate_one_model(
            y_true, probabilities, groups, DEFAULT_DECISION_THRESHOLD
        )
        metrics[name] = result
        prediction_columns[f"{name.lower().replace(' ', '_')}_prediction"] = predictions

    # Agreement-stratified results are descriptive only; no threshold tuning.
    agreement_metrics = {}
    for level in sorted(prediction_columns["AgrLevel"].unique()):
        mask = prediction_columns["AgrLevel"].to_numpy() == level
        if len(np.unique(y_true[mask])) == 2:
            agreement_metrics[str(int(level))] = {
                "n": int(mask.sum()),
                "positive": int(np.sum(y_true[mask] == 1)),
                "negative": int(np.sum(y_true[mask] == 0)),
                "ensemble_auc_roc": float(
                    roc_auc_score(y_true[mask], probability_sets["Ensemble"][mask])
                ),
                "ensemble_accuracy": float(
                    accuracy_score(
                        y_true[mask],
                        prediction_bundle["y_pred"][mask]
                    )
                ),
            }
        else:
            agreement_metrics[str(int(level))] = {
                "n": int(mask.sum()),
                "positive": int(np.sum(y_true[mask] == 1)),
                "negative": int(np.sum(y_true[mask] == 0)),
                "ensemble_auc_roc": None,
                "ensemble_accuracy": float(
                    accuracy_score(
                        y_true[mask],
                        prediction_bundle["y_pred"][mask]
                    )
                ),
            }

    predictions_path = output_dir / "lndb_predictions.csv"
    exclusions_path = output_dir / "lndb_exclusions.csv"
    metrics_path = output_dir / "lndb_metrics.json"
    manifest_path = output_dir / "lndb_external_validation_manifest.json"
    prediction_columns.to_csv(predictions_path, index=False)
    pd.DataFrame(exclusions, columns=["LNDbID", "FindingID", "reason"]).to_csv(
        exclusions_path, index=False
    )
    save_curves(y_true, probability_sets, output_dir)

    metrics_payload = {
        "dataset": "LNDb official public train/validation cohort",
        "task": "candidate/finding-level binary nodule classification",
        "n_evaluated": int(len(y_true)),
        "n_positive": int(np.sum(y_true == 1)),
        "n_negative": int(np.sum(y_true == 0)),
        "n_scans": int(len(np.unique(groups))),
        "models": metrics,
        "agreement_level_stratification": agreement_metrics,
        "excluded_findings": int(len(exclusions)),
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    try:
        ingestion_manifest_path = project_root / "outputs" / "lndb_ingestion_manifest.json"
        ingestion_manifest_hash = (
            sha256_file(ingestion_manifest_path) if ingestion_manifest_path.is_file() else None
        )
    except OSError:
        ingestion_manifest_hash = None

    manifest = {
        "experiment": "TQ-BioNet v3.1 Stage 6B zero-shot LNDb external validation",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": git_commit(),
        "pipeline_version": model_manifest["pipeline_version"],
        "training_dataset": "LUNA16 subsets 0-5",
        "external_dataset": "LNDb official public train/validation cohort",
        "zero_shot": True,
        "no_retraining": True,
        "no_threshold_tuning": True,
        "decision_threshold": DEFAULT_DECISION_THRESHOLD,
        "patch_size_voxels": [PATCH_SIZE] * 3,
        "resampling_spacing_xyz_mm": list(ISOTROPIC_SPACING),
        "preprocessing": "tq_bionet.pipeline.preprocess_patch (median/IQR, clip [-3,3], map [0,1])",
        "feature_schema_31": FROZEN_31_FEATURES,
        "selected_feature_schema_15": FROZEN_15_SELECTED_FEATURES,
        "model_artifact_sha256": model_hashes,
        "ground_truth_csv": str(ground_truth_path),
        "ground_truth_csv_sha256": sha256_file(ground_truth_path),
        "ingestion_manifest_sha256": ingestion_manifest_hash,
        "source_scan_count": int(len(all_scan_ids)),
        "ground_truth_findings": int(len(ground_truth)),
        "ground_truth_annotated_scan_count": int(ground_truth.LNDbID.nunique()),
        "evaluated_findings": int(len(y_true)),
        "evaluated_scan_count": int(len(np.unique(groups))),
        "excluded_findings": int(len(exclusions)),
        "extracted_feature_shape": list(X_all.shape),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "scikit_learn_version": sklearn.__version__,
        "xgboost_version": xgboost.__version__,
        "simpleitk_version": sitk.Version_VersionString(),
        "output_files": [
            predictions_path.name,
            exclusions_path.name,
            metrics_path.name,
            "roc_curve.png",
            "precision_recall_curve.png",
        ],
        "label_semantics": {
            "source_column": "trainNodules_gt.csv:Nodule",
            "positive_label": 1,
            "negative_label": 0,
            "agreement_column": "AgrLevel",
            "agreement_is_reported_not_used_to_relabel": True,
        },
        "caveats": [
            "Series/scan-level clustered confidence intervals do not establish patient-level independence.",
            "This is the publicly available LNDb cohort, not the hidden challenge test set.",
            "Candidate/finding-level performance is not patient-level diagnosis or clinical validation.",
            "Probability outputs are not asserted to be calibrated on LNDb.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nStage 6B completed.")
    print(f"Evaluated findings: {len(y_true)} ({int(np.sum(y_true == 1))} positive, {int(np.sum(y_true == 0))} negative)")
    print(f"Scans represented: {len(np.unique(groups))}")
    print(f"Excluded findings: {len(exclusions)}")
    print("\nEnsemble metrics:")
    print(json.dumps(metrics["Ensemble"], indent=2))
    print(f"\nArtifacts: {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extracted-dir", default=r"D:\LNDb\extracted",
        help="Directory containing LNDb-*.mhd and paired .raw files."
    )
    parser.add_argument(
        "--ground-truth",
        default=r"D:\LNDb\annotations\trainset_csv\trainNodules_gt.csv",
        help="Official LNDb trainNodules_gt.csv path."
    )
    parser.add_argument(
        "--bundle-dir",
        default="outputs/frozen_v3_1_pipeline",
        help="Frozen v3.1 model bundle directory; never overwritten."
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/lndb_external_validation_v3_1",
        help="New output directory for Stage 6B artifacts."
    )
    parser.add_argument("--progress-every", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    run_lndb_validation(parse_args())
