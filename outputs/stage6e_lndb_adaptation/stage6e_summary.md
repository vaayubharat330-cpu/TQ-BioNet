# TQ-BioNet Stage 6E: LNDb Domain Adaptation and Grouped Evaluation Summary

This experiment evaluates scan-grouped development and adaptation on LNDb using the official challenge partition structure (Folds 0–2 for Development, Fold 3 as Held-Out Test). All models evaluated on Fold 3 are explicitly designated as **LNDb-Adapted**, distinguishing them from the frozen v3.1 zero-shot benchmark.

## Cohort Partitioning (Official LNDb Challenge Folds)
- **Development Cohort (Folds 0, 1, 2)**: 899 candidate findings across 171 scans (577 positive, 322 negative, 64.2% positive).
- **Held-Out Test Cohort (Fold 3)**: 320 candidate findings across 58 scans (191 positive, 129 negative, 59.7% positive).
- **Scan-Level Disjointness**: Exactly 0 overlapping scans between Development and Fold 3.

## Conflicting Coordinate Audit
- **Identified Locations**: 6 coordinate locations (12 total rows) where conflicting binary labels (`Nodule=1` and `Nodule=0`) exist at identical physical $(x,y,z)$ coordinates within the same CT volume.
- **Handling**: Preserved transparently in the primary evaluation without silent deletion; detailed in `conflicting_coordinates_audit.csv`.

## Development Cross-Validation Performance (Folds 0–2, Scan-Grouped)

| Model Configuration | Feature Set | Accuracy | Balanced Acc | Sensitivity | Specificity | F1-Score | AUC-ROC | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | — | 0.6418 | 0.5000 | 1.0000 | 0.0000 | 0.7818 | 0.5000 | 0.2317 |
| **Frozen Zero-Shot v3.1** | 15 frozen | 0.5662 | 0.5783 | 0.5355 | 0.6211 | 0.6131 | 0.5991 | 0.2676 |
| **Adapted SVM (RBF)** | 15 frozen | 0.6696 | 0.5663 | 0.9307 | 0.2019 | 0.7834 | 0.6228 | 0.2205 |
| **Adapted XGBoost** | 15 frozen | 0.6229 | 0.5985 | 0.6846 | 0.5124 | 0.6997 | 0.6394 | 0.2371 |
| **Adapted Random Forest** | 15 frozen | 0.6930 | 0.6181 | 0.8821 | 0.3540 | 0.7867 | 0.6598 | 0.2121 |
| **Adapted Ensemble** | 15 frozen | 0.6819 | 0.6190 | 0.8406 | 0.3975 | 0.7723 | 0.6504 | 0.2155 |
| **Adapted Ensemble** | 31 all | 0.6563 | 0.5936 | 0.8146 | 0.3727 | 0.7526 | 0.6345 | 0.2204 |

## Final Evaluation on Untouched Held-Out Cohort (Fold 3, N=320)

| Metric [Confidence Interval] | Majority Baseline | Frozen Zero-Shot v3.1 | LNDb-Adapted Ensemble (15 feat) | LNDb-Adapted Ensemble (31 feat) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** [Scan-Cluster 95% CI] | 0.5969 | 0.4938 | **0.6875** [0.630 - 0.742] | **0.6656** [0.613 - 0.718] |
| **Balanced Accuracy** | 0.5000 | 0.5080 | **0.6527** | **0.6293** |
| **Sensitivity** | 1.0000 | 0.4346 | 0.8325 | 0.8168 |
| **Specificity** | 0.0000 | 0.5814 | 0.4729 | 0.4419 |
| **Precision** | 0.5969 | 0.6860 | 0.7004 | 0.6842 |
| **F1-Score** [Scan-Cluster 95% CI] | 0.7476 | 0.5061 | **0.7608** [0.703 - 0.811] | **0.7446** [0.690 - 0.796] |
| **AUC-ROC** [Scan-Cluster 95% CI] | 0.5000 | 0.4980 | **0.6913** [0.625 - 0.758] | **0.6849** [0.615 - 0.758] |
| **Average Precision (AP)** | 0.5969 | 0.6348 | **0.7692** | **0.7635** |
| **Brier Score** | 0.2407 | 0.3010 | **0.2156** | **0.2159** |
| **ECE** | — | — | **0.0617** | **0.0223** |

## Agreement Stratification on Fold 3 (Adapted Ensemble 15-feat)
- **AgrLevel 0** (non-nodules, N=129): Accuracy = 47.29%
- **AgrLevel 1** (1-reader nodules, N=133): Accuracy = 81.20%
- **AgrLevel 2** (2-reader consensus, N=47): Accuracy = 87.23%
- **AgrLevel 3** (3-reader unanimous, N=11): Accuracy = 90.91%
