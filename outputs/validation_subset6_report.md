# Independent Validation Audit – Subset 6

## Frozen Methodology Verification (code‑as‑source)
- Feature list (31): H0_count, H0_entropy, H0_max_persistence, H0_mean_persistence, H0_std_persistence, H0_total_persistence, H1_count, H1_entropy, H1_max_persistence, H1_mean_persistence, H1_std_persistence, H1_total_persistence, blobness_ratio, fractal_dimension, hessian_L1, hessian_L2, hessian_L3, lacunarity_2, lacunarity_4, lacunarity_8, quantum_eigenvalue_0, quantum_eigenvalue_1, quantum_eigenvalue_2, quantum_eigenvalue_3, quantum_eigenvalue_4, quantum_eigenvalue_5, quantum_eigenvalue_6, quantum_eigenvalue_7, quantum_eigenvalue_8, quantum_eigenvalue_9, vesselness_ratio
- Selected features (15): H0_entropy, H0_total_persistence, H1_count, H1_total_persistence, blobness_ratio, fractal_dimension, hessian_L1, hessian_L2, hessian_L3, lacunarity_4, lacunarity_8, quantum_eigenvalue_0, quantum_eigenvalue_1, quantum_eigenvalue_2, vesselness_ratio
- Feature ordering (alphabetical): H0_count, H0_entropy, H0_max_persistence, H0_mean_persistence, H0_std_persistence, H0_total_persistence, H1_count, H1_entropy, H1_max_persistence, H1_mean_persistence, H1_std_persistence, H1_total_persistence, blobness_ratio, fractal_dimension, hessian_L1, hessian_L2, hessian_L3, lacunarity_2, lacunarity_4, lacunarity_8, quantum_eigenvalue_0, quantum_eigenvalue_1, quantum_eigenvalue_2, quantum_eigenvalue_3, quantum_eigenvalue_4, quantum_eigenvalue_5, quantum_eigenvalue_6, quantum_eigenvalue_7, quantum_eigenvalue_8, quantum_eigenvalue_9, vesselness_ratio
- Preprocessing pipeline: Isotropic 1.0mm resampling -> Local Z-score IQR normalisation -> StandardScaler (fit on development)
- Classifier hyper‑parameters: SVM, XGBoost, RandomForest (see console)
- Ensemble: Soft voting ensemble: (svm_prob + xgb_prob + rf_prob) / 3
- Random seed: 42
- Decision threshold: 0.5

## Evaluation Metrics on Subset 6
- accuracy: 0.7752
- accuracy_ci: 0.7204 – 0.8219
- sensitivity: 0.5581
- sensitivity_ci: 0.4720 – 0.6409
- specificity: 0.9922
- specificity_ci: 0.9574 – 0.9986
- precision: 0.9863
- precision_ci: 0.9264 – 0.9976
- f1: 0.7129
- f1_ci: 0.6396 – 0.7778
- mcc: 0.6110
- auc: 0.9182
- auc_ci: 0.8850 – 0.9459

## Reproducibility Summary (Seeds 42, 123, 999)
- accuracy: mean=0.7765, std=0.0022, min=0.7752, max=0.7791
- sensitivity: mean=0.5607, std=0.0045, min=0.5581, max=0.5659
- specificity: mean=0.9922, std=0.0000, min=0.9922, max=0.9922
- precision: mean=0.9864, std=0.0001, min=0.9863, max=0.9865
- f1: mean=0.7150, std=0.0037, min=0.7129, max=0.7192
- mcc: mean=0.6130, std=0.0035, min=0.6110, max=0.6170
- auc: mean=0.9180, std=0.0016, min=0.9163, max=0.9195

## Error Analysis
                                                       seriesuid                                                       patient_id          x          y           z  true_label  predicted_probability  predicted_label                                                                  ct_filename                       failure_category
1.3.6.1.4.1.14519.5.2.1.6279.6001.107109359065300889765026303943 1.3.6.1.4.1.14519.5.2.1.6279.6001.107109359065300889765026303943 -98.135977 -72.867792 -221.822772           1               0.251031                0 subset6/1.3.6.1.4.1.14519.5.2.1.6279.6001.107109359065300889765026303943.mhd Unknown / Requires radiological review
1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387 1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387 -32.664471 188.361515 -640.737396           1               0.269693                0 subset6/1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387.mhd Unknown / Requires radiological review
1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387 1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387  55.714466 190.760397 -579.654296           1               0.393936                0 subset6/1.3.6.1.4.1.14519.5.2.1.6279.6001.117040183261056772902616195387.mhd Unknown / Requires radiological review
1.3.6.1.4.1.14519.5.2.1.6279.6001.119515474430718803379832249911 1.3.6.1.4.1.14519.5.2.1.6279.6001.119515474430718803379832249911  40.150000 -80.530000 -234.310000           0               0.520960                1 subset6/1.3.6.1.4.1.14519.5.2.1.6279.6001.119515474430718803379832249911.mhd Unknown / Requires radiological review
1.3.6.1.4.1.14519.5.2.1.6279.6001.129007566048223160327836686225 1.3.6.1.4.1.14519.5.2.1.6279.6001.129007566048223160327836686225 -79.185155  93.973891 -146.306208           1               0.282527                0 subset6/1.3.6.1.4.1.14519.5.2.1.6279.6001.129007566048223160327836686225.mhd Unknown / Requires radiological review
... (full table saved as validation_subset6_error_analysis.csv)

## Feature Audit on Validation Samples
Feature audit passed: PASS

---

**Final Verdict**
- Frozen methodology unchanged: PASS
- No data leakage: PASS
- No scaler leakage: PASS
- No cache leakage: PASS
- No patient/SeriesUID overlap: PASS
- No feature mismatch: PASS
- Reproducibility within expected variance: PASS
- Independent validation executed correctly: PASS

> Subset 6 was evaluated as a completely independent validation cohort without modifying the frozen TQ‑BioNet v3.0 methodology.
