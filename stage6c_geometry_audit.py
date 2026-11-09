"""Stage 6C: audit CT physical geometry and annotation-coordinate integrity.

This is an audit-only script. It does not modify scans, annotations, caches, or models.
It records native geometry and checks physical-coordinate round trips before any
multi-resolution resampling experiment is started.
"""
from __future__ import annotations

import argparse
import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_mhd(path: Path) -> dict:
    reader = sitk.ImageFileReader()
    reader.SetFileName(str(path))
    reader.ReadImageInformation()  # Header only; does not load the voxel array.
    size = tuple(int(v) for v in reader.GetSize())
    spacing = tuple(float(v) for v in reader.GetSpacing())
    origin = tuple(float(v) for v in reader.GetOrigin())
    direction = np.asarray(reader.GetDirection(), dtype=float).reshape(3, 3)
    extent = tuple(
        float((size[i] - 1) * spacing[i]) if size[i] else 0.0
        for i in range(3)
    )
    orthogonality_error = float(
        np.max(np.abs(direction.T @ direction - np.eye(3)))
    )
    determinant = float(np.linalg.det(direction))
    metadata = {}
    for key in reader.GetMetaDataKeys():
        if any(term in key.lower() for term in ("thickness", "spacing", "origin", "direction")):
            try:
                metadata[key] = reader.GetMetaData(key)
            except RuntimeError:
                pass
    raw_path = path.with_suffix(".raw")
    return {
        "scan_file": str(path),
        "scan_id": path.stem,
        "size_xyz": size,
        "spacing_xyz_mm": spacing,
        "origin_xyz_mm": origin,
        "direction_matrix": direction.tolist(),
        "direction_determinant": determinant,
        "direction_orthogonality_max_error": orthogonality_error,
        "physical_extent_xyz_mm": extent,
        "voxel_count": int(np.prod(size)),
        "raw_exists": raw_path.is_file(),
        "raw_bytes": raw_path.stat().st_size if raw_path.is_file() else 0,
        "header_metadata": metadata,
    }


def check_points(scan_path: Path, points: np.ndarray, source: str, scan_id: str):
    """Check physical point -> continuous index -> physical point round trip."""
    image = sitk.ReadImage(str(scan_path))
    rows = []
    for idx, point in enumerate(np.asarray(points, dtype=float)):
        if point.shape != (3,) or not np.isfinite(point).all():
            rows.append({
                "source": source, "scan_id": scan_id, "row_index": idx,
                "status": "invalid_coordinate", "roundtrip_error_mm": None,
                "inside_volume": False,
            })
            continue
        continuous = np.asarray(
            image.TransformPhysicalPointToContinuousIndex(tuple(point)), dtype=float
        )
        reconstructed = np.asarray(
            image.TransformContinuousIndexToPhysicalPoint(tuple(continuous)), dtype=float
        )
        error = float(np.linalg.norm(reconstructed - point))
        size = np.asarray(image.GetSize(), dtype=float)
        inside = bool(np.all(continuous >= -0.5) and np.all(continuous <= size - 0.5))
        rows.append({
            "source": source, "scan_id": scan_id, "row_index": idx,
            "status": "ok" if error <= 1e-4 else "roundtrip_error",
            "roundtrip_error_mm": error, "inside_volume": inside,
            "continuous_index_xyz": continuous.tolist(),
        })
    return rows


def discover_mhds(root: Path):
    return sorted(root.rglob("*.mhd")) if root.exists() else []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--luna-root", type=Path, default=Path("luna16_data"))
    ap.add_argument("--luna-annotations", type=Path, default=Path("luna16_data/annotations.csv"))
    ap.add_argument("--lndb-root", type=Path, default=Path("LNDb"))
    ap.add_argument("--lndb-ground-truth", type=Path,
                    default=Path("LNDb/annotations/trainset_csv/trainNodules_gt.csv"))
    ap.add_argument("--output-dir", type=Path, default=Path("outputs/stage6c_geometry_audit"))
    ap.add_argument("--max-point-checks-per-scan", type=int, default=100)
    args = ap.parse_args()

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    all_geometry, point_checks = [], []
    inventory = {}

    # Dataset scan inventory and header-only physical geometry.
    for dataset, root in (("LUNA16", args.luna_root), ("LNDb", args.lndb_root)):
        paths = discover_mhds(root.resolve())
        inventory[dataset] = {"root": str(root.resolve()), "mhd_count": len(paths)}
        for n, path in enumerate(paths, 1):
            try:
                item = inspect_mhd(path)
                item["dataset"] = dataset
                all_geometry.append(item)
            except Exception as exc:
                all_geometry.append({
                    "dataset": dataset, "scan_file": str(path), "scan_id": path.stem,
                    "inspection_error": f"{type(exc).__name__}: {exc}",
                })
            if n % 50 == 0:
                print(f"{dataset}: inspected {n}/{len(paths)} MHD headers", flush=True)

    # LUNA16 annotation points, matched by seriesuid to MHD stem.
    if args.luna_annotations.is_file():
        ann = pd.read_csv(args.luna_annotations)
        required = {"seriesuid", "coordX", "coordY", "coordZ"}
        if required.issubset(ann.columns):
            for scan_id, group in ann.groupby("seriesuid"):
                matches = [p for p in discover_mhds(args.luna_root.resolve()) if p.stem == str(scan_id)]
                if not matches:
                    continue
                pts = group[["coordX", "coordY", "coordZ"]].to_numpy(dtype=float)
                pts = pts[:args.max_point_checks_per_scan]
                point_checks.extend(check_points(matches[0], pts, "LUNA16_annotations", str(scan_id)))

    # LNDb official physical annotation points. IDs are mapped to LNDb-####.mhd.
    if args.lndb_ground_truth.is_file():
        gt = pd.read_csv(args.lndb_ground_truth)
        required = {"LNDbID", "x", "y", "z"}
        if required.issubset(gt.columns):
            lndb_paths = {p.stem: p for p in discover_mhds(args.lndb_root.resolve())}
            for scan_id, group in gt.groupby("LNDbID"):
                key = f"LNDb-{int(scan_id):04d}"
                path = lndb_paths.get(key)
                if path is None:
                    continue
                pts = group[["x", "y", "z"]].to_numpy(dtype=float)
                pts = pts[:args.max_point_checks_per_scan]
                point_checks.extend(check_points(path, pts, "LNDb_trainNodules_gt", key))

    geom_df = pd.DataFrame(all_geometry)
    geom_df.to_csv(out / "scan_geometry.csv", index=False)
    points_df = pd.DataFrame(point_checks)
    points_df.to_csv(out / "annotation_coordinate_checks.csv", index=False)

    summary = {
        "experiment": "TQ-BioNet Stage 6C native geometry and coordinate audit",
        "audit_only": True,
        "created_local": pd.Timestamp.now().isoformat(),
        "inventory": inventory,
        "scan_header_count": len(all_geometry),
        "header_errors": int(geom_df.get("inspection_error", pd.Series(dtype=object)).notna().sum()),
        "coordinate_checks": len(point_checks),
        "coordinate_roundtrip_failures": int(
            (points_df["status"] != "ok").sum()
        ) if not points_df.empty else 0,
        "coordinates_outside_volume": int(
            (~points_df["inside_volume"].astype(bool)).sum()
        ) if not points_df.empty else 0,
        "dataset_geometry": {},
        "files": {
            "scan_geometry.csv": "Native MHD geometry and physical extents",
            "annotation_coordinate_checks.csv": "Physical coordinate round-trip and in-volume checks",
        },
        "interpretation": [
            "MHD header spacing is voxel-center spacing, not necessarily a separately recorded acquisition slice-thickness value.",
            "A physical-coordinate round trip checks coordinate-system arithmetic, not whether annotation coordinates use the intended patient-coordinate convention.",
            "No image resampling or model fitting is performed by this script.",
        ],
    }
    if not geom_df.empty and "dataset" in geom_df.columns:
        for dataset, group in geom_df.groupby("dataset"):
            valid = group[group.get("inspection_error", pd.Series(index=group.index, dtype=object)).isna()]
            if valid.empty:
                continue
            spacings = np.asarray(valid["spacing_xyz_mm"].tolist(), dtype=float)
            summary["dataset_geometry"][dataset] = {
                "valid_scans": int(len(valid)),
                "spacing_xyz_mm_median": np.median(spacings, axis=0).tolist(),
                "spacing_xyz_mm_min": np.min(spacings, axis=0).tolist(),
                "spacing_xyz_mm_max": np.max(spacings, axis=0).tolist(),
                "direction_orthogonality_max_error": float(
                    np.max(valid["direction_orthogonality_max_error"].to_numpy(dtype=float))
                ),
                "direction_determinant_min": float(
                    np.min(valid["direction_determinant"].to_numpy(dtype=float))
                ),
                "direction_determinant_max": float(
                    np.max(valid["direction_determinant"].to_numpy(dtype=float))
                ),
            }

    # Record reproducible physical patch widths for 32-voxel cubes.
    summary["patch_field_of_view_examples_mm"] = {
        str(s): [round(32 * s, 3)] * 3 for s in (0.7, 0.8, 1.0, 1.25, 1.5)
    }
    summary["extent_preserving_output_size_formula"] = (
        "round((input_size_xyz - 1) * input_spacing_xyz / target_spacing_xyz) + 1"
    )
    summary["current_legacy_formula"] = (
        "round(input_size_xyz * input_spacing_xyz / target_spacing_xyz)"
    )
    summary["notes"] = [
        "The extent-preserving formula preserves first-to-last voxel-center distance.",
        "The legacy formula can differ by approximately one output voxel depending on dimensions and spacing.",
        "The experiment should compare both geometry metadata and annotation-center mapping before model performance.",
    ]

    with (out / "stage6c_geometry_audit.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nStage 6C audit complete. Reports: {out}")


if __name__ == "__main__":
    main()
