# TQ-BioNet v3.0 Repository Freeze Report

This report confirms the execution and outcome of the final repository cleanup and methodology freeze for TQ-BioNet v3.0.

## 1. Files Modified & Relocated
- **Modified**: `tq_bionet/run_all_subsets_scaling.py`
  - Replaced the last remaining absolute path reference (`C:\Users\suraj\Desktop\4th yr project\luna16_data`) with dynamic pathname resolution using `pathlib` relative to `__file__`.
- **Relocated**: `tq_bionet/run_luna16_validation.py` -> `archive/run_luna16_validation.py`
  - Moved the deprecated validation script to the `archive/` directory and added a formal deprecation header indicating that it is retained only for historical reference and not used in the active pipeline.
- **Created**: `TQ-BioNet_v3.0_FROZEN.md`
  - Contains the formal freeze certificate detailing the exact model parameters, feature selections, classifiers, random seeds, and subset SHA256 cache checksums.

---

## 2. Repository Cleanup Summary
- **No Hardcoded Absolute Paths**: All scripts (`run.py`, `ablation_study.py`, `verify_loader.py`, `run_luna16_validation_v2.py`, and `run_all_subsets_scaling.py`) are now completely path-independent, resolving raw directories relative to the dynamically located repository root or fallbacks.
- **Legacy Cache Removal**: Deprecated cache files (`X.npy`, `groups.npy`, `y.npy`, etc.) were removed, forcing evaluations to run purely through the robust versioned cache format.
- **Legacy Imports Migrated**: Removed all stale references to `compute_95_ci` and updated the CI calculations to use Wilson and Bootstrap intervals.

---

## 3. Methodology Freeze Summary
- **Freeze Status**: **FROZEN**
- **Freeze Timestamp**: 2026-07-14T23:35:05+05:30
- **Algorithm Version**: v3.0
- **Feature Version**: v3.0
- **Model Architectures & Hyperparameters**: Frozen
- **Train/Test Splitting**: Frozen Patient-level partitioning (`random_seed=42`)
- **Extracted Feature Space**: 31 features, alphabetized

---

## 4. Verification Summary
All entry scripts were run sequentially to verify execution and correct behavior under path-independent caching:
- **`verify_loader.py`**: **PASS** (CT resampling and axial patch check slices outputted successfully).
- **`run.py`**: **PASS** (Synthetic nodule diagnostics and McNemar classification consistency verified).
- **`ablation_study.py`**: **PASS** (Ablation table evaluates successfully).
- **`run_luna16_validation_v2.py`**: **PASS** (Validation on Subset 0 completes immediately via cache with correct Wilson/Bootstrap metrics).
- **`run_all_subsets_scaling.py`**: **PASS** (Reconstructed combined cohort of 1446 samples from Subsets 0–5 caching instantly and evaluating Soft Voting Ensemble AUC to **0.9340**).

---

## 5. Final Statement

> **The repository is now frozen as TQ-BioNet v3.0 Frozen and is ready for independent validation on LUNA16 Subsets 6–9.**
