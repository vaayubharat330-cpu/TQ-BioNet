# Stage 7 Audit Report: Frozen Independent Validation on LUNA16 Subsets 6–9

**Audit Date**: 2026-11-09  
**Auditor**: Antigravity Autonomous Coding Agent  
**Repository**: `https://github.com/vaayubharat330-cpu/TQ-BioNet.git`  
**Evaluation Commit Reference**: `1a84030c36bfdf9c18a95137b803fc7bcb439350` / `8a6ea3ae1124e9914def8e88b3828a2bdf1a903f`  
**Pipeline Bundle Directory**: `outputs/frozen_v3_1_pipeline/`  
**Validation Artifacts Evaluated**: `outputs/validation_predictions.csv`, `outputs/validation_metrics.json`, `outputs/validation_summary.md`, `outputs/validation_confusion_matrix.csv`, `outputs/experiment_manifest_validation.json`  
**Test Suite Verification**: `tests/test_stage7_validation_audit.py` (8 passing unit/integrity tests; 68/68 total test suite passed)

---

## Executive Summary

Stage 7 performs a rigorous retrospective audit of the held-out validation of the frozen **TQ-BioNet v3.1** pipeline on **LUNA16 Subsets 6–9**. 

This audit confirms three primary conclusions:
1. **The evaluation was genuinely frozen and leak-free**:
   - The model pipeline (`scaler.joblib`, `svm_model.joblib`, `xgb_model.joblib`, `rf_model.joblib`) was trained strictly on Subsets 0–5 ($N=1,446$ candidates across 365 scans) and serialized prior to held-out evaluation.
   - All serialized model artifact hashes match the manifest byte-for-byte.
   - There is **zero overlap** between Development SeriesUIDs (365 scans) and Validation SeriesUIDs (236 scans).
2. **Artifacts are 100% internally consistent**:
   - Recomputing metrics directly from `validation_predictions.csv` matches `validation_metrics.json`, `validation_confusion_matrix.csv`, and `validation_summary.md` exactly ($\le 10^{-6}$ numerical tolerance).
   - Re-running forward inference with the disk-loaded frozen models on the validation feature matrices reproduces `validation_predictions.csv` with zero label discrepancies.
3. **The scientific results establish strong candidate-level discrimination on a balanced benchmark**:
   - On the combined held-out cohort ($N=926$, 236 scans, 1:1 candidate balance), the Voting Ensemble achieves:
     - **Accuracy**: $86.29\%$ [Scan-Cluster Bootstrap 95% CI: $84.0\% - 88.3\%$]
     - **Sensitivity**: $81.86\%$ [Candidate Wilson 95% CI: $78.1\% - 85.1\%$]
     - **Specificity**: $90.71\%$ [Candidate Wilson 95% CI: $87.7\% - 93.0\%$]
     - **Precision**: $89.81\%$ [Candidate Wilson 95% CI: $86.6\% - 92.3\%$]
     - **F1-Score**: $85.65\%$ [Scan-Cluster Bootstrap 95% CI: $83.1\% - 87.9\%$]
     - **ROC-AUC**: $0.9202$ [Scan-Cluster Bootstrap 95% CI: $0.902 - 0.935$]
     - **Brier Score**: $0.1178$
     - **Expected Calibration Error (ECE)**: $0.1057$
   - Performance across individual subsets is exceptionally stable (Accuracy $84.3\% - 88.3\%$, ROC-AUC $0.913 - 0.927$).
   - **Epidemiological Nuance**: These metrics reflect candidate-level classification under an artificial 1:1 balance (463 nodules vs 463 non-nodules). They cannot be directly equated to clinical screening PPV where true nodule prevalence is $< 1-2\%$.

---

## 1. Provenance and Freeze Audit

### 1.1 Model Bundle Hashes and Provenance
The model bundle stored in `outputs/frozen_v3_1_pipeline/` was audited against `pipeline_manifest.json`:

| Artifact | Filename | Recorded SHA256 Checksum | Actual Disk SHA256 Checksum | Match Status |
| :--- | :--- | :--- | :--- | :--- |
| **StandardScaler** | `scaler.joblib` | `42f9ad0338a540f0618aa8781664d027642eb134c75013d775b68d82195acb12` | `42f9ad0338a540f0618aa8781664d027642eb134c75013d775b68d82195acb12` | **VERIFIED** |
| **SVM Model** | `svm_model.joblib` | `68e371e4da830f32135122f6e8a39def279756915922ad7d4effc6ea008499f6` | `68e371e4da830f32135122f6e8a39def279756915922ad7d4effc6ea008499f6` | **VERIFIED** |
| **XGBoost Model** | `xgb_model.joblib` | `6bd8f19379a65f57754a0baacb2f0ecb3509e0f05b2f0e50ed8f7fb3c5cf5ac1` | `6bd8f19379a65f57754a0baacb2f0ecb3509e0f05b2f0e50ed8f7fb3c5cf5ac1` | **VERIFIED** |
| **Random Forest** | `rf_model.joblib` | `13c4832296f056d8ebb38959e051baf60f07608c2f65860c507458f85979eafc` | `13c4832296f056d8ebb38959e051baf60f07608c2f65860c507458f85979eafc` | **VERIFIED** |

### 1.2 Feature Schema and Contract Freeze
- **Extracted Feature Schema**: 31 canonical features (H0/H1 persistence metrics, differential geometry/Hessian eigenvalues, lacunarity, and quantum graph Laplacian eigenvalues).
- **Frozen Selected Subset**: Exactly 15 features matching `FROZEN_15_SELECTED_FEATURES` in `tq_bionet/model_config.py`.
- **Scaling Contract**: 
  - SVM strictly trained and evaluated on `StandardScaler` outputs fit on Development cohort.
  - XGBoost and Random Forest strictly trained and evaluated on unscaled features.
- **Ensemble Policy**: Unweighted soft voting average:
  $$P_{\text{ensemble}} = \frac{P_{\text{SVM}} + P_{\text{XGBoost}} + P_{\text{RandomForest}}}{3}$$
- **Decision Threshold**: Strictly locked at $t = 0.50$. No post-hoc threshold shifting or optimization was performed on Subsets 6–9.

### 1.3 Data Split Disjointness and Zero-Leakage Verification
The cache directories for Subsets 0–5 and Subsets 6–9 were scanned:
- **Development Cohort (Subsets 0–5)**:
  - Total candidate samples: $1,446$ (723 nodules, 723 non-nodules)
  - Total unique CT scans (`SeriesUID`): $365$
- **Validation Cohort (Subsets 6–9)**:
  - Total candidate samples: $926$ (463 nodules, 463 non-nodules)
  - Total unique CT scans (`SeriesUID`): $236$
- **Scan-Level Intersection**:
  $$\text{SeriesUID}_{\text{dev}} \cap \text{SeriesUID}_{\text{val}} = \emptyset \quad (\text{exact overlap} = 0)$$
  *Conclusion: Strict scan-level independence is verified. There is zero scan-level data leakage between the development and validation cohorts.*

---

## 2. Artifact Consistency and Prediction Integrity

### 2.1 Forward Pass Equivalence
The serialized model artifacts were reloaded from disk and evaluated against the raw cached validation features:
- Max absolute error across all 926 probabilities:
  - SVM probability: $\le 1.11 \times 10^{-16}$
  - XGBoost probability: $\le 2.97 \times 10^{-8}$ (due to single/double float precision serialization in CSV)
  - Random Forest probability: $\le 1.11 \times 10^{-16}$
  - Ensemble probability: $\le 1.11 \times 10^{-16}$
- Label classification mismatches: **0 out of 926** ($100.0\%$ exact prediction equivalence).

### 2.2 Confusion Matrix Reconciliation
Recomputation from `validation_predictions.csv` yielded:

| Category | Predicted Positive ($\hat{y}=1$) | Predicted Negative ($\hat{y}=0$) | Total Actual |
| :--- | :--- | :--- | :--- |
| **Actual Nodule ($y=1$)** | **379** (True Positive) | **84** (False Negative) | **463** |
| **Actual Non-Nodule ($y=0$)** | **43** (False Positive) | **420** (True Negative) | **463** |
| **Total Predicted** | **422** | **504** | **926** |

This matches `validation_confusion_matrix.csv`, `validation_summary.md`, and `validation_metrics.json` without any discrepancies.

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

### 3.2 Calibration vs Discrimination Trade-off
- **SVM** demonstrates superior probability calibration ($\text{ECE} = 0.0450$) as a consequence of internal 5-fold Platt scaling fit during development.
- **XGBoost** demonstrates well-balanced discrimination and calibration ($\text{AUC} = 0.9134$, $\text{ECE} = 0.0742$).
- **Voting Ensemble** achieves the highest overall discrimination ($\text{AUC} = 0.9202$) and lowest overall Brier score ($0.1178$), but its ECE increases to $0.1057$. This is an expected mathematical consequence of unweighted soft voting: averaging sigmoidal probabilities shrinks high-confidence predictions toward the decision threshold, creating a modest calibration penalty even while improving boundary classification accuracy.

---

## 4. Subset-Wise Stability Breakdown

To evaluate whether the global performance was skewed by any single fold, each validation subset was audited independently:

| Metric | Subset 6 ($N=258$, 63 scans) | Subset 7 ($N=222$, 54 scans) | Subset 8 ($N=236$, 60 scans) | Subset 9 ($N=210$, 59 scans) | Full Validation ($N=926$, 236 scans) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | 86.43% | **88.29%** | 84.32% | 86.19% | **86.29%** |
| **Sensitivity** | 82.95% | **84.68%** | 79.66% | 80.00% | **81.86%** |
| **Specificity** | 89.92% | 91.89% | 88.98% | **92.38%** | **90.71%** |
| **Precision** | 89.17% | 91.26% | 87.85% | **91.30%** | **89.81%** |
| **F1-Score** | 85.94% | **87.85%** | 83.56% | 85.28% | **85.65%** |
| **ROC-AUC** | **0.9270** | 0.9208 | 0.9192 | 0.9135 | **0.9202** |
| **Confusion Matrix** | TN: 116, FP: 13<br>FN: 22, TP: 107 | TN: 102, FP: 9<br>FN: 17, TP: 94 | TN: 105, FP: 13<br>FN: 24, TP: 94 | TN: 97, FP: 8<br>FN: 21, TP: 84 | TN: 420, FP: 43<br>FN: 84, TP: 379 |

### Stability Observations
- **Consistency Across Cohorts**: Across all 4 subsets, Accuracy ranges narrowly from $84.32\%$ to $88.29\%$, and ROC-AUC ranges from $0.9135$ to $0.9270$.
- **High Specificity Preservation**: Specificity remains $\ge 88.98\%$ in every single held-out subset (peaking at $92.38\%$ in Subset 9), demonstrating that the pipeline consistently suppresses false-positive candidates across diverse scanning environments.

---

## 5. Scientific Interpretation & Clinical Translation Safeguards

When reporting these results in scientific publications and IEEE documentation, the following framing must be maintained:

1. **Candidate-Level Discrimination vs Full Screening Detection**:
   The reported metrics ($86.29\%$ Accuracy, $89.81\%$ Precision) evaluate candidate classification on an artificially balanced dataset ($1:1$ nodule-to-non-nodule ratio, $463:463$). In clinical screening CT scans, non-nodular false-positive candidates outnumber true nodules by $50:1$ to $100:1$. Therefore, candidate-level precision cannot be directly reported as clinical screening Positive Predictive Value (PPV) without explicit prevalence weighting.
2. **Scan-Cluster Grouping**:
   Because multiple nodule candidates often originate from the same CT volume, individual candidate samples within a scan exhibit intra-scan correlation. The scan-cluster bootstrap intervals appropriately account for this grouping, confirming that the ensemble maintains significant discrimination even under clustered variance.
3. **Contrast with LNDb External Validation**:
   The high discrimination on LUNA16 Subsets 6–9 ($\text{AUC} = 0.9202$) contrasts sharply with the zero-shot performance observed on LNDb ($\text{AUC} \approx 0.573$ prior to adaptation, $0.693$ with domain adaptation). This demonstrates that while the topological and biophysical feature representations are highly effective within the LUNA16 acquisition distribution, domain adaptation remains essential when transferring to external clinical protocols with different slice thickness, reconstruction kernels, and annotation criteria.

---

## 6. Audit Certification

- **Provenance**: Certified frozen at commit `1a84030c36bfdf9c18a95137b803fc7bcb439350`.
- **Integrity**: Byte-level checksums for all four serialized model artifacts match `pipeline_manifest.json`.
- **Data Leakage**: Verified zero scan overlap between Subsets 0–5 and Subsets 6–9.
- **Reproducibility**: Verified full replication of `validation_predictions.csv` and all reported summary metrics.
- **Test Suite Status**: 8/8 dedicated Stage 7 audit tests passed; 68/68 full pytest suite passing.
