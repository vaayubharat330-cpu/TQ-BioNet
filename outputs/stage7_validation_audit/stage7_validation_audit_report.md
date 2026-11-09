# Stage 7.1 Audit Report: Frozen Independent Validation on LUNA16 Subsets 6–9

**Audit Date**: 2026-11-09  
**Auditor**: Antigravity Autonomous Coding Agent  
**Repository**: `https://github.com/vaayubharat330-cpu/TQ-BioNet.git`  
**Working Branch**: `audit/repair-v3.1`  
**Git Provenance Chain**:
- Development Model Bundle Commit: `ef7ee87b35053bd527899f6eb17d6969ae1c8cd0` (HEAD at development audit: `665779748635744e160727909b0cbd198a13abe5`)
- Validation Execution Environment Commit: `1a84030c36bfdf9c18a95137b803fc7bcb439350`
- Saved Validation Artifacts Commit: `8a6ea3ae1124e9914def8e88b3828a2bdf1a903f`
**Pipeline Bundle Directory**: `outputs/frozen_v3_1_pipeline/`  
**Validation Artifacts Evaluated**: `outputs/validation_predictions.csv`, `outputs/validation_metrics.json`, `outputs/validation_summary.md`, `outputs/validation_confusion_matrix.csv`, `outputs/experiment_manifest_validation.json`  
**Test Suite Verification**: `tests/test_stage7_validation_audit.py` (9 passing dedicated audit tests; 69/69 full pytest suite passed)

---

## Executive Summary

Stage 7.1 provides a certified, rigorous retrospective audit of the held-out validation of the frozen **TQ-BioNet v3.1** pipeline on **LUNA16 Subsets 6–9**. 

This audit confirms four primary findings:
1. **The evaluation was genuinely frozen and scan-independent**:
   - The model pipeline (`scaler.joblib`, `svm_model.joblib`, `xgb_model.joblib`, `rf_model.joblib`) was trained strictly on Subsets 0–5 ($N=1,446$ candidates across 365 scans) and committed prior to held-out evaluation.
   - All serialized model artifact hashes match the manifest byte-for-byte.
   - There is **zero scan-level overlap** between Development SeriesUIDs (365 scans) and Validation SeriesUIDs (236 scans).
2. **Artifacts are 100% internally consistent**:
   - Recomputing metrics directly from `validation_predictions.csv` matches `validation_metrics.json`, `validation_confusion_matrix.csv`, and `validation_summary.md` exactly ($\le 10^{-6}$ numerical tolerance).
   - Re-running forward inference with the disk-loaded frozen models on the cached validation feature matrices reproduces `validation_predictions.csv` with zero label discrepancies.
   - All 95% confidence intervals (candidate-level Wilson intervals and scan-cluster bootstrap intervals with 1,000 resamples) replicate exactly and are covered by automated regression tests.
3. **The scientific results establish strong candidate-level discrimination on a balanced benchmark**:
   - On the combined held-out cohort ($N=926$, 236 scans, 1:1 candidate balance), the Voting Ensemble achieves:
     - **Accuracy**: $86.29\%$ [Scan-Cluster Bootstrap 95% CI: $83.98\% - 88.33\%$]
     - **Sensitivity**: $81.86\%$ [Candidate Wilson 95% CI: $78.09\% - 85.10\%$]
     - **Specificity**: $90.71\%$ [Candidate Wilson 95% CI: $87.72\% - 93.03\%$]
     - **Precision**: $89.81\%$ [Candidate Wilson 95% CI: $86.56\% - 92.35\%$]
     - **F1-Score**: $85.65\%$ [Scan-Cluster Bootstrap 95% CI: $83.11\% - 87.91\%$]
     - **ROC-AUC**: $0.9202$ [Scan-Cluster Bootstrap 95% CI: $0.9022 - 0.9353$]
     - **Brier Score**: $0.1178$
     - **Expected Calibration Error (ECE)**: $0.1057$
   - Performance across individual subsets is exceptionally stable (Accuracy $84.32\% - 88.29\%$, ROC-AUC $0.9135 - 0.9270$).
4. **Essential Methodological and Epidemiological Boundaries**:
   - **Candidate-Level vs. Screening Prevalence**: The 86.29% accuracy and 89.81% precision reflect classification of pre-selected candidates under an artificial 1:1 balance (463 nodules vs 463 non-nodules). They cannot be equated to clinical screening performance where true nodule prevalence is $< 1-2\%$.
   - **Scan-Level Independence**: Independence is verified at the CT volume (`SeriesUID`) level. Patient-level independence cannot be independently asserted without external identity cross-referencing.
   - **Domain Specificity**: High discrimination on LUNA16 contrasts with zero-shot performance on LNDb ($\text{AUC} \approx 0.573$), demonstrating that transfer to external datasets remains a substantial limitation.

---

## 1. Provenance and Freeze Audit

### 1.1 Chronological Git Provenance Audit Trail
To ensure complete transparency regarding the training, evaluation, and artifact saving sequence, the commit history was mapped:

1. **Working Tree at Stage 5C Development Freeze (`6657797`)**:
   - Commit `665779748635744e160727909b0cbd198a13abe5` represents the repository state when the development 5-fold cross-validation was executed on Subsets 0–5. This SHA was captured inside `outputs/stage5c_development/stage5c_summary.json`.
2. **Model Bundle Serialization and Commit (`ef7ee87`)**:
   - Commit `ef7ee87b35053bd527899f6eb17d6969ae1c8cd0` committed the frozen model bundle (`scaler.joblib`, `svm_model.joblib`, `xgb_model.joblib`, `rf_model.joblib`, and `pipeline_manifest.json`) into the repository.
3. **Validation Script Execution Environment (`1a84030`)**:
   - Commit `1a84030c36bfdf9c18a95137b803fc7bcb439350` added explicit split integrity checks to `run_independent_validation.py`. The evaluation script dynamically recorded its active commit hash into `outputs/experiment_manifest_validation.json` during execution.
4. **Validation Artifacts Commit (`8a6ea3a`)**:
   - Commit `8a6ea3ae1124e9914def8e88b3828a2bdf1a903f` recorded the evaluation outputs (`validation_predictions.csv`, `validation_metrics.json`, `validation_summary.md`, and per-subset JSONs) into repository history.

### 1.2 Model Bundle Hashes vs Historical Manifest
The model bundle stored in `outputs/frozen_v3_1_pipeline/` was audited against `pipeline_manifest.json`:

| Artifact | Filename | Recorded SHA256 Checksum | Actual Disk SHA256 Checksum | Match Status |
| :--- | :--- | :--- | :--- | :--- |
| **StandardScaler** | `scaler.joblib` | `42f9ad0338a540f0618aa8781664d027642eb134c75013d775b68d82195acb12` | `42f9ad0338a540f0618aa8781664d027642eb134c75013d775b68d82195acb12` | **VERIFIED** |
| **SVM Model** | `svm_model.joblib` | `68e371e4da830f32135122f6e8a39def279756915922ad7d4effc6ea008499f6` | `68e371e4da830f32135122f6e8a39def279756915922ad7d4effc6ea008499f6` | **VERIFIED** |
| **XGBoost Model** | `xgb_model.joblib` | `6bd8f19379a65f57754a0baacb2f0ecb3509e0f05b2f0e50ed8f7fb3c5cf5ac1` | `6bd8f19379a65f57754a0baacb2f0ecb3509e0f05b2f0e50ed8f7fb3c5cf5ac1` | **VERIFIED** |
| **Random Forest** | `rf_model.joblib` | `13c4832296f056d8ebb38959e051baf60f07608c2f65860c507458f85979eafc` | `13c4832296f056d8ebb38959e051baf60f07608c2f65860c507458f85979eafc` | **VERIFIED** |

### 1.3 Refitting Experiment vs Historical Provenance
To verify implementation determinism, the training pipeline was refitted from scratch using the cached features from Subsets 0–5 under seed 42. The refitted scaler and SVM parameters matched the saved bundle exactly:
- `scaler.mean_` difference: $0.0$
- `scaler.var_` difference: $0.0$
- `svm.dual_coef_` difference: $0.0$
- `svm.intercept_` difference: $0.0$

*Audit Note on Distinction*: This refitting experiment demonstrates that the code and cached development data deterministically reproduce the model. It serves as empirical confirmation of reproducibility, complementing the git commit chain above which establishes the historical training sequence.

### 1.4 Scan-Cluster Separation (Zero Leakage)
The cache directories for Subsets 0–5 and Subsets 6–9 were audited:
- **Development Cohort (Subsets 0–5)**: $1,446$ candidates across $365$ unique SeriesUIDs.
- **Validation Cohort (Subsets 6–9)**: $926$ candidates across $236$ unique SeriesUIDs.
- **Scan Overlap**:
  $$\text{SeriesUID}_{\text{dev}} \cap \text{SeriesUID}_{\text{val}} = \emptyset \quad (\text{exact count} = 0)$$

*Audit Note on Patient Independence*: Independence is established and verified strictly at the CT scan volume (`SeriesUID`) level. Because the public LUNA16 challenge coordinates and headers do not include canonical patient IDs, patient-level independence is not claimed and must not be assumed without external LIDC-IDRI mapping.

---

## 2. Artifact Consistency and Prediction Integrity

### 2.1 Forward Pass Equivalence
Evaluating the disk-loaded serialized bundle on the cached validation feature matrices reproduces `validation_predictions.csv` with zero label discrepancies:
- Max absolute error across all 926 probabilities:
  - SVM probability: $\le 1.11 \times 10^{-16}$
  - XGBoost probability: $\le 2.97 \times 10^{-8}$ (CSV floating-point serialization precision)
  - Random Forest probability: $\le 1.11 \times 10^{-16}$
  - Ensemble probability: $\le 1.11 \times 10^{-16}$
- Label classification mismatches: **0 out of 926** ($100.0\%$ prediction equivalence).

### 2.2 Confusion Matrix Reconciliation
Recomputation from `validation_predictions.csv` confirms:

| Category | Predicted Positive ($\hat{y}=1$) | Predicted Negative ($\hat{y}=0$) | Total Actual |
| :--- | :--- | :--- | :--- |
| **Actual Nodule ($y=1$)** | **379** (True Positive) | **84** (False Negative) | **463** |
| **Actual Non-Nodule ($y=0$)** | **43** (False Positive) | **420** (True Negative) | **463** |
| **Total Predicted** | **422** | **504** | **926** |

All counts reconcile across `validation_confusion_matrix.csv`, `validation_summary.md`, and `validation_metrics.json`.

---

## 3. Statistical Audit: Combined Subsets 6–9 Results

### 3.1 Model Comparison Table

| Metric [Confidence Interval Method] | Support Vector Machine (SVM) | XGBoost Classifier | Voting Ensemble |
| :--- | :--- | :--- | :--- |
| **Accuracy** [Scan-Cluster Bootstrap 95%] | 84.02% [81.46% – 86.35%] | 85.31% [82.87% – 87.50%] | **86.29% [83.98% – 88.33%]** |
| **Sensitivity** [Candidate Wilson 95%] | 81.64% [77.86% – 84.90%] | 80.13% [76.25% – 83.51%] | **81.86% [78.09% – 85.10%]** |
| **Specificity** [Candidate Wilson 95%] | 86.39% [82.97% – 89.22%] | 90.50% [87.48% – 92.84%] | **90.71% [87.72% – 93.03%]** |
| **Precision** [Candidate Wilson 95%] | 85.71% [82.14% – 88.67%] | 89.40% [86.07% – 92.01%] | **89.81% [86.56% – 92.35%]** |
| **F1-Score** [Scan-Cluster Bootstrap 95%] | 83.63% [80.89% – 86.07%] | 84.51% [81.75% – 86.91%] | **85.65% [83.11% – 87.91%]** |
| **ROC-AUC** [Scan-Cluster Bootstrap 95%] | 0.8945 [0.8726 – 0.9132] | 0.9134 [0.8955 – 0.9297] | **0.9202 [0.9022 – 0.9353]** |
| **Brier Score** (lower is better) | 0.1247 | 0.1180 | **0.1178** |
| **Expected Calibration Error (ECE)** | **0.0450** | 0.0742 | 0.1057 |

### 3.2 Calibration Metrics (Defensible Reporting)
On this validation cohort, the classifiers exhibit different degrees of probability calibration:
- **SVM** achieved the lowest Expected Calibration Error ($\text{ECE} = 0.0450$).
- **XGBoost** achieved an intermediate calibration error ($\text{ECE} = 0.0742$).
- **Voting Ensemble** achieved an Expected Calibration Error of $\text{ECE} = 0.1057$, while attaining the highest discrimination ($\text{AUC} = 0.9202$) and lowest overall mean squared error ($\text{Brier} = 0.1178$).

*Scientific Correction*: Rather than claiming soft voting inherently causes probability degradation, we report the empirical observation that unweighted probability averaging on this cohort yielded higher ECE than its Platt-scaled SVM component, despite improving thresholded accuracy and AUC.

---

## 4. Subset-Wise Stability Breakdown

Auditing Subsets 6, 7, 8, and 9 individually confirms high consistency across all four acquisition subsets:

| Metric | Subset 6 ($N=258$, 63 scans) | Subset 7 ($N=222$, 54 scans) | Subset 8 ($N=236$, 60 scans) | Subset 9 ($N=210$, 59 scans) | Full Validation ($N=926$, 236 scans) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | 86.43% | **88.29%** | 84.32% | 86.19% | **86.29%** |
| **Sensitivity** | 82.95% | **84.68%** | 79.66% | 80.00% | **81.86%** |
| **Specificity** | 89.92% | 91.89% | 88.98% | **92.38%** | **90.71%** |
| **Precision** | 89.17% | 91.26% | 87.85% | **91.30%** | **89.81%** |
| **F1-Score** | 85.94% | **87.85%** | 83.56% | 85.28% | **85.65%** |
| **ROC-AUC** | **0.9270** | 0.9208 | 0.9192 | 0.9135 | **0.9202** |
| **Confusion Matrix** | TN: 116, FP: 13<br>FN: 22, TP: 107 | TN: 102, FP: 9<br>FN: 17, TP: 94 | TN: 105, FP: 13<br>FN: 24, TP: 94 | TN: 97, FP: 8<br>FN: 21, TP: 84 | TN: 420, FP: 43<br>FN: 84, TP: 379 |

- Accuracy varies within a narrow $3.97$ percentage point band ($84.32\% - 88.29\%$).
- Specificity remains strictly $\ge 88.98\%$ in every subset.

---

## 5. Scientific Conclusion & Framing Constraints

The audit confirms the following formal scientific conclusions:

1. **Candidate-Level Discrimination**:
   TQ-BioNet v3.1 demonstrates promising candidate-level discrimination on held-out LUNA16 subsets ($86.29\%$ Accuracy, $0.9202$ ROC-AUC).
2. **Domain Transfer Limitation**:
   Its zero-shot performance on LNDb ($\text{AUC} \approx 0.573$ prior to adaptation, $0.693$ adapted) shows that transferring this feature representation across clinical institutions and scanner protocols remains a substantial limitation.
3. **Non-Clinical Classification Scope**:
   The model must not be described as clinically validated or as a complete pulmonary-nodule detection system. In screening practice, candidate detection occurs against millions of non-nodular voxels where positive predictive value is severely constrained by low disease prevalence.

---

## 6. Audit Certification

- **Provenance**: Verified across commits `6657797`, `ef7ee87`, `1a84030`, and `8a6ea3a`.
- **Integrity**: Serialized bundle SHA256 checksums match `pipeline_manifest.json` byte-for-byte.
- **Data Independence**: Verified zero scan overlap between Subsets 0–5 and Subsets 6–9.
- **Reproducibility**: Verified forward pass equivalence, confusion matrix match, Wilson CIs, and scan-cluster bootstrap CIs.
- **Test Suite Status**: 9/9 dedicated Stage 7 audit tests passed; 69/69 full pytest suite passed.
