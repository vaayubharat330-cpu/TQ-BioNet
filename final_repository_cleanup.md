# final_repository_cleanup.md

This report details the actions performed during the final repository cleanup and verification for TQ-BioNet v3.0 before final freeze.

## Verification of Methodological Freeze
We confirm that **no scientific, preprocessing, algorithmic, or statistical logic was modified**. 
- **Algorithms**: Unchanged (quantum wave module, Persistent Homology module, box-counting fractal module, and Hessian module are completely frozen).
- **Feature Extraction**: Unchanged (feature lists, indexing, parameters, and mathematics are fully preserved).
- **Preprocessing**: Unchanged (local z-score IQR normalization is unchanged).
- **Classifiers**: Unchanged (SVC, XGBoost, and RandomForest architectures, hyperparameters, and seeds are frozen).
- **Ensemble Logic**: Unchanged (Soft voting average of SVM, XGBoost, and RF is frozen).
- **Feature Selection**: Unchanged (Locked subset of 15 features for scaled training, 10 features for Subset 0 validation).
- **Statistics**: Unchanged (Confidence intervals use the exact same Wilson score and Bootstrap CI formulas verified previously).

---

## 1. Files Modified

### 📂 Ablation Study Script
* **File**: `tq_bionet/ablation_study.py`
* **Changes**: Replaced legacy `compute_95_ci` with `compute_wilson_ci` and restored proper `train_and_evaluate_model` logic.

### 📂 Main Execution Script
* **File**: `tq_bionet/run.py`
* **Changes**: Replaced legacy `compute_95_ci` with `compute_wilson_ci` and removed hardcoded path to outputs (saving `roc_curve.png` and `pr_curve.png` dynamically to `outputs/` using `pathlib`). Fixed key name in McNemar results output from `'chi2_statistic'` to `'statistic'`.

### 📂 Loader Verification Script
* **File**: `tq_bionet/verify_loader.py`
* **Changes**: Made CT/MHD data directories fully dynamic using `pathlib`, resolving paths relative to the project root directory. Reconfigured the axial verification slice save path to outputs folder.

### 📂 Clinical Subset 0 Validation Script
* **File**: `tq_bionet/run_luna16_validation_v2.py`
* **Changes**: Replaced hardcoded LUNA16 data directory path with dynamic path resolution using `pathlib`. Reconfigured the curves output path to outputs folder.

### 📂 Scaled Retraining & Validation Suite
* **File**: `tq_bionet/scale_clinical_validation.py`
* **Changes**: Updated `download_and_extract_subset`, `process_and_save_subset`, and `run_retraining` to resolve data directories dynamically using `pathlib` (enabling clean fallbacks to project directory if D: drive is unavailable). Reconfigured `artifacts_dir` to point dynamically to `outputs/` folder.

---

## 2. Deprecations and Moves

### 🗑️ Deleted Legacy Validation Script
* **File**: `tq_bionet/run_luna16_validation.py`
* **Status**: Deprecated and deleted from the package directory to prevent stale imports and confusion.

### 📦 Archived Validation Script
* **File**: `archive/run_luna16_validation.py`
* **Status**: Saved a non-runnable snapshot of the legacy validator in the `archive/` folder for historical record.

### 🗑️ Legacy Cache Cleanup
* **Location**: `luna16_data/`
* **Files Deleted**:
  - `X.npy`
  - `y.npy`
  - `groups.npy`
  - `X_v3_sub0.npy`
  - `groups_v3_sub0.npy`
  - `y_v3_sub0.npy`

---

## 3. Verification Outcomes
All entry scripts were executed sequentially and verified for execution:
1. `run.py` -> **PASS** (Synthetic generation, feature extraction, model evaluations, McNemar consistency, and targeted check cases execute error-free).
2. `ablation_study.py` -> **PASS** (Independent ablation performance evaluations run successfully).
3. `verify_loader.py` -> **PASS** (CT scan resample and axial nodule patch slice checks pass).
4. `run_luna16_validation_v2.py` -> **PASS** (Clinical subset 0 validation executes successfully).
5. `run_all_subsets_scaling.py` -> **PASS** (Reconstructed scaled cohorts, run data audits, evaluated multi-subset models successfully).
