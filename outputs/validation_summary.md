# TQ-BioNet v3.0 Independent Validation Summary

This document summarizes the final evaluation outcomes of the frozen TQ-BioNet v3.0 framework on the completely unseen independent validation cohort (Subsets 6–9).

## Validation Scope
- **Validation Date**: 2026-09-21 03:53:46 UTC
- **Development Cohort**: Subsets 0–5 (1446 samples) - Used for classifier training
- **Validation Cohort**: Subsets 6–9 (926 samples) - Used for validation testing
- **Feature Pipeline Version**: v3.0 (Isotropic 1.0mm, Local Z-Score IQR Preprocessing)
- **Features Pruned**: 15 key biophysical/topological features

## Independent Validation Cohort Metrics (Combined Subsets 6–9)

| Metric | Support Vector Machine (SVM) | XGBoost Classifier | Voting Ensemble |
| :--- | :--- | :--- | :--- |
| **Accuracy** | 0.8359 [0.811 - 0.858] | 0.8542 [0.830 - 0.875] | 0.8629 [0.839 - 0.884] |
| **Sensitivity** | 0.8056 [0.767 - 0.839] | 0.7991 [0.760 - 0.833] | 0.8186 [0.781 - 0.851] |
| **Specificity** | 0.8661 [0.832 - 0.894] | 0.9093 [0.880 - 0.932] | 0.9071 [0.877 - 0.930] |
| **Precision** | 0.8575 [0.821 - 0.887] | 0.8981 [0.865 - 0.924] | 0.8981 [0.866 - 0.923] |
| **F1-Score** | 0.8307 [0.803 - 0.859] | 0.8457 [0.818 - 0.870] | 0.8565 [0.830 - 0.881] |
| **AUC-ROC** | 0.8940 [0.872 - 0.914] | 0.9134 [0.894 - 0.930] | 0.9198 [0.901 - 0.936] |

## Ensemble Confusion Matrix
- **True Negatives**: 420
- **False Positives**: 43
- **False Negatives**: 84
- **True Positives**: 379
