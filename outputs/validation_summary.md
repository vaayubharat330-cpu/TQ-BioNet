# TQ-BioNet v3.1 Independent Validation Summary

This document summarizes the final evaluation outcomes of the frozen TQ-BioNet v3.1 framework on the independent evaluation cohort (SeriesUID-separated Subsets 6-9). Note: SeriesUID separation establishes scan-level independence, which is conditional on confirming patient-level separation where scans originate from distinct individuals.

## Validation Scope
- **Validation Date**: 2026-11-08 19:05:35 UTC
- **Development Cohort**: Subsets 0-5 (1446 samples) - Used for classifier training
- **Validation Cohort**: Subsets 6-9 (926 samples) - Used for validation testing
- **Feature Pipeline Version**: v3.1 (Isotropic 1.0mm, Local Z-Score IQR Preprocessing)
- **Features Pruned**: 15 key biophysical/topological features

## Independent Validation Cohort Metrics (Combined Subsets 6-9)

| Metric [CI Type] | Support Vector Machine (SVM) | XGBoost Classifier | Voting Ensemble |
| :--- | :--- | :--- | :--- |
| **Accuracy** [Scan-Cluster Bootstrap 95%] | 0.8402 [0.815 - 0.864] | 0.8531 [0.829 - 0.875] | 0.8629 [0.840 - 0.883] |
| **Sensitivity** [Candidate Wilson 95%] | 0.8164 [0.779 - 0.849] | 0.8013 [0.763 - 0.835] | 0.8186 [0.781 - 0.851] |
| **Specificity** [Candidate Wilson 95%] | 0.8639 [0.830 - 0.892] | 0.9050 [0.875 - 0.928] | 0.9071 [0.877 - 0.930] |
| **Precision** [Candidate Wilson 95%] | 0.8571 [0.821 - 0.887] | 0.8940 [0.861 - 0.920] | 0.8981 [0.866 - 0.923] |
| **F1-Score** [Scan-Cluster Bootstrap 95%] | 0.8363 [0.809 - 0.861] | 0.8451 [0.818 - 0.869] | 0.8565 [0.831 - 0.879] |
| **AUC-ROC** [Scan-Cluster Bootstrap 95%] | 0.8945 [0.873 - 0.913] | 0.9134 [0.895 - 0.930] | 0.9202 [0.902 - 0.935] |

## Ensemble Confusion Matrix
- **True Negatives**: 420
- **False Positives**: 43
- **False Negatives**: 84
- **True Positives**: 379
