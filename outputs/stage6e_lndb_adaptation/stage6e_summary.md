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


## Stage 6E.1 Audit Addendum

### Feature Cache Alignment
The runner now verifies every cache row against the exact ordered ground-truth CSV rows:
scan ID, binary label, physical coordinates (absolute tolerance 1e-7 mm), and AgrLevel.
A mismatch stops execution before splitting, fitting, or evaluation.

### Fold 3 Conflict Sensitivity (Fixed Predictions)
This is a secondary sensitivity analysis only. The original finding-level Fold 3
metrics above remain the primary evaluation. For exact same-scan coordinates with
conflicting binary labels, one representative row is retained by highest AgrLevel,
then largest Volume, then smallest FindingID. Predictions/probabilities remain those
from the original model; no model retraining or test-time threshold changes occur.

- Primary Fold 3 findings: 320
- Sensitivity-analysis rows: 317
- Conflicting coordinate groups in Fold 3: 3
- Rows in those conflicting groups: 6
- Sensitivity analysis accuracy: 0.6909
- Sensitivity analysis balanced accuracy: 0.6543
- Sensitivity analysis sensitivity/specificity: 0.8325 / 0.4762
- Sensitivity analysis ROC-AUC: 0.6934056345051108

This is not an adjudicated ground truth. It changes the unit for affected coordinates
and must not be presented as the primary result.

### Paired Scan-Cluster Comparison vs Always-Positive Baseline
- Accuracy difference (adapted minus baseline): 0.0906
- Paired scan-cluster bootstrap 95% CI: [0.0227, 0.1637]
- Bootstrap replicates: 5000
- Scan clusters: 58

### Fold 3 Conflict Sensitivity Analysis (Secondary; Predictions Fixed)
- Primary finding rows: 320
- Rows after representative selection: 317
- Conflicting coordinate groups: 3
- Rows collapsed from conflicting groups: 3
- Sensitivity-analysis accuracy: 0.6909
- Sensitivity-analysis balanced accuracy: 0.6543
- Sensitivity-analysis sensitivity / specificity: 0.8325 / 0.4762
- Sensitivity-analysis ROC-AUC: 0.6934056345051108
- Sensitivity-analysis class counts: 191 positive / 126 negative

This secondary analysis changes the unit only at contradictory exact-coordinate groups. It is not an adjudicated ground truth and does not replace the primary finding-level evaluation.
- Bootstrap replicates: 5000
- Scan clusters: 58

This paired interval resamples scans and evaluates both classifiers on the same
resampled findings, accounting for within-scan clustering.
