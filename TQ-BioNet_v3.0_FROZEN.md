# TQ-BioNet v3.0 Methodology Freeze Certificate

This document formally certifies the technical and methodological freeze of the Topological-Quantum Biophysical Framework (TQ-BioNet) version 3.0.

## Freeze Information
- **Freeze Timestamp**: 2026-07-14T23:35:05+05:30
- **Repository Status**: FROZEN
- **Git Commit Hash**: `unavailable`
- **Algorithm Version**: v3.0
- **Feature Version**: v3.0
- **Cache Format Version**: v3.0
- **Manifest Format Version**: 3.0

---

## Model & Feature Parameters
- **Extracted Feature Dimension**: 31 features
- **Feature Ordering**: Alphabetical (locked via sorted list)
- **Random Seeds**:
  - Retraining split & shuffling seed: `42`
  - Bootstrap resampling seed: `42`
  
### Selected Feature Sets
1. **Scaled Retraining Cohort Feature Set** (15 features):
   - `H0_entropy`
   - `H0_total_persistence`
   - `H1_count`
   - `H1_total_persistence`
   - `blobness_ratio`
   - `fractal_dimension`
   - `hessian_L1`
   - `hessian_L2`
   - `hessian_L3`
   - `lacunarity_4`
   - `lacunarity_8`
   - `quantum_eigenvalue_0`
   - `quantum_eigenvalue_1`
   - `quantum_eigenvalue_2`
   - `vesselness_ratio`
2. **Clinical Validation Subset 0 Feature Set** (10 features):
   - `fractal_dimension`
   - `H0_entropy`
   - `H0_total_persistence`
   - `H1_count`
   - `H1_total_persistence`
   - `lacunarity_4`
   - `lacunarity_8`
   - `quantum_eigenvalue_0`
   - `quantum_eigenvalue_1`
   - `quantum_eigenvalue_2`

---

## Classifier & Ensemble Architecture
- **Classifiers**:
  - **Support Vector Machine (SVM)**: `SVC(C=100.0, gamma='scale', probability=True, random_state=42)`
  - **XGBoost**: `XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.01, eval_metric='logloss', random_state=42)`
  - **Random Forest**: `RandomForestClassifier(n_estimators=150, max_depth=4, random_state=42)`
- **Ensemble Configuration**:
  - Soft voting average of prediction probabilities from SVM, XGBoost, and RF: `(svm_probs + xgb_probs + rf_probs) / 3.0`

---

## Dataset Scope
- **Dataset Used for Development**: LUNA16 Subsets 0–5 (Isotropic 1mm resampling, local z-score IQR normalization, balanced per scan; total 1446 samples: 723 Positives, 723 Negatives).
- **Independent Validation Cohort**: LUNA16 Subsets 6–9 (Completely unseen).

---

## Cache Verification (SHA256 Checksums)
All cached development subsets are stored under `luna16_data/cache/tq_bionet_v3/subset{idx}/X.npy` and verified by the following SHA256 checksums:
- **Subset 0**: `1857f6c9b29539769b7732658fbb33d3e16f459693cba644a9239d87501fe042`
- **Subset 1**: `2f0251f60c141e8d13be8cb73cd70bee30ce9023d4ef6103cd760fbd81378906`
- **Subset 2**: `c8b63e81ff9fbbb4a2c1bc11b06faa82eb33d0754541bbb88bb72076d4e3fea4`
- **Subset 3**: `08a0e442125f94aa7ad3a201ab5746c2d6dd0f3d8b11b9c04c9bd21dd10d19d1`
- **Subset 4**: `48af3566e97a1cd56986391bd8198cb044f3e3097d531dc19c0232421d71c26b`
- **Subset 5**: `7b437ec0b41b7c1ada27109ea2bc7f48162bb1ff0fc0cb9c008b22e4ad1dbb5d`

---

## Hard Freeze Statement

> [!IMPORTANT]
> No algorithmic, preprocessing, feature engineering, hyperparameter, or evaluation modifications are permitted after this freeze.
>
> The independent validation on LUNA16 Subsets 6–9 must be performed using this exact frozen methodology.
