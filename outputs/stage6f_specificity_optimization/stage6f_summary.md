# TQ-BioNet Stage 6F: Development Specificity Optimization & Retrospective Fold 3 Summary

This experiment evaluates decision threshold optimization and false-positive reduction strictly using Development data (Folds 0–2), followed by a retrospective evaluation on the Stage 6E Fold 3 cohort.

> [!IMPORTANT]
> **Methodological Framing & Retrospective Qualification**:
> Fold 3 was previously evaluated during Stage 6E and therefore is **not** an untouched, prospective test cohort. The evaluations reported below are explicitly designated as **retrospective held-out analyses** applied to the frozen Stage 6E Fold 3 predicted probabilities. This experiment is a candidate-classification study rather than a clinical screening deployment.

## 1. Development Model Comparison (Folds 0–2 Scan-Grouped OOF)

| Model Architecture | Features | ROC-AUC | PR-AUC | Brier Score | Accuracy @ 0.50 | Sensitivity @ 0.50 | Specificity @ 0.50 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Adapted SVM (RBF)** | 15 frozen | 0.6228 | 0.7187 | 0.2205 | 66.96% | **93.07%** | 20.19% |
| **Adapted Random Forest** | 15 frozen | **0.6598** | **0.7427** | **0.2121** | **69.30%** | 88.21% | 35.40% |
| **Adapted XGBoost** | 15 frozen | 0.6394 | 0.7228 | 0.2371 | 62.29% | 68.46% | **51.24%** |
| **Adapted Soft Ensemble** | 15 frozen | 0.6504 | 0.7332 | 0.2155 | 68.19% | 84.06% | 39.75% |

*Note on performance breakdown:* Random Forest achieves the highest overall discrimination (AUC 0.6598, PR-AUC 0.7427, Brier 0.2121), XGBoost provides the highest specificity at default threshold (51.24%), SVM achieves the highest sensitivity (93.07%), and the Soft Ensemble provides a balanced consensus across all three.

## 2. True Leak-Free Nested Development Threshold Selection (Folds 0–2)

Thresholds were selected strictly on inner folds using an inner 2-fold cross-validation scheme where outer validation folds were completely excluded from both model training and threshold tuning:

| Policy Constraint | Frozen Threshold ($t^*$) | Inner Fold Selected Thresholds | Nested Sensitivity | Nested Specificity | Nested Balanced Acc | Nested Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary: Sens $\ge 80\%$** | **0.52** | Fold0: 0.49, Fold1: 0.53, Fold2: 0.51 | **82.15%** | 39.75% | 60.95% | 66.96% |
| **Secondary: Sens $\ge 75\%$** | **0.53** | Fold0: 0.54, Fold1: 0.55, Fold2: 0.54 | 73.83%* | 46.58% | 60.21% | 64.07% |
| **Secondary: Max Youden $J$** | **0.50** | Fold0: 0.57, Fold1: 0.66, Fold2: 0.63 | 60.14% | 59.32% | 59.73% | 59.84% |

*\*Qualification on sensitivity constraint:* The secondary policy constrained to $\ge 75\%$ on inner training folds achieved 73.83% on unseen outer validation folds. This demonstrates that finite-sample sampling variation across folds can cause slight empirical boundary offsets when applying fixed thresholds to unseen cohorts.

## 3. Retrospective Evaluation on Fold 3 ($N=320$ Findings, 58 Scans)

| Metric [Scan-Cluster 95% CI] | Stage 6E Baseline ($t=0.50$) | Primary Policy ($t^*=0.52$) | Secondary Policy ($t^*=0.53$) | Secondary Youden ($t^*=0.50$) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | 68.75% [63.0% – 74.2%] | **65.31%** [59.7% – 70.5%] | 65.62% | 68.75% |
| **Balanced Accuracy** | 65.27% | **62.51%** | 63.15% | 65.27% |
| **Sensitivity** | 83.25% [76.9% – 88.5%] | **76.96%** [70.9% – 82.4%] | 75.92% | 83.25% |
| **Specificity** | 47.29% [38.2% – 56.4%] | **48.06%** [37.0% – 60.8%] | 50.39% | 47.29% |
| **Precision (PPV)** | 70.04% | **68.69%** | 69.38% | 70.04% |
| **F1-Score** | 76.08% | **72.59%** | 72.50% | 76.08% |
| **Youden Index ($J$)** | 0.3053 | **0.2503** | 0.2630 | 0.3053 |
| **Confusion Matrix [TN, FP, FN, TP]** | [61, 68, 32, 159] | [62, 67, 44, 147] | [65, 64, 46, 145] | [61, 68, 32, 159] |

## 4. Paired Scan-Cluster Bootstrap Comparison (Primary Policy vs Baseline $t=0.50$)

Paired bootstrap across 5,000 resampled scan clusters evaluates whether changes in performance are statistically meaningful:
- **Specificity Difference**: +0.78 percentage points [95% CI: +0.00% to +2.86%]
- **Sensitivity Difference**: -6.28 percentage points [95% CI: -9.90% to -3.05%]
- **Accuracy Difference**: -3.44 percentage points [95% CI: -5.64% to -1.55%]

*Statistical interpretation:* Because the specificity interval crosses zero ([0.00%, +2.86%]), an increase from 0.50 to 0.52 does not establish a statistically significant specificity gain. Conversely, the sensitivity reduction ([-9.90%, -3.05%]) and accuracy reduction ([-5.64%, -1.55%]) are both strictly negative.

## 5. Radiologist Agreement Stratification on Fold 3 (Primary Policy $t^*=0.52$)
- **AgrLevel 0** (non-nodules, N=129): Accuracy = 48.06% (Specificity)
- **AgrLevel 1** (1-reader nodules, N=133): Accuracy = 74.44% (Sensitivity)
- **AgrLevel 2** (2-reader consensus, N=47): Accuracy = 80.85% (Sensitivity)
- **AgrLevel 3** (3-reader unanimous, N=11): Accuracy = 90.91% (Sensitivity)

## 6. Secondary Conflict Sensitivity on Fold 3 (Primary Policy $t^*=0.52$)
- Findings evaluated: 317 (after collapsing 3 conflicting coordinate groups from 6 raw rows to 3 representative rows).
- Accuracy: 65.62%
- Balanced Accuracy: 62.69%
- Sensitivity: 76.96%
- Specificity: 48.41%

## 7. Scientific Conclusion
Within the scope of the tested models and operating points, decision threshold adjustment alone does not solve the low-specificity challenge on LNDb without an unacceptable reduction in nodule sensitivity. Isolating the root cause (e.g., whether vascular parenchymal feature representation, scanner protocol shift, or label noise) requires further targeted ablations and feature-family experiments.
