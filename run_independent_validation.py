import sys
import os
import time
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, roc_auc_score, confusion_matrix

# Add current directory to path to locate tq_bionet package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tq_bionet.scale_clinical_validation import (
    download_and_extract_subset,
    process_and_save_subset,
    reconstruct_combined_dataset,
    get_file_sha256,
    get_git_commit
)
from tq_bionet.pipeline import extract_tq_bio_features
from tq_bionet.evaluation_metrics import compute_wilson_ci, compute_bootstrap_ci, compute_cluster_bootstrap_ci
from tq_bionet.model_config import (
    FROZEN_31_FEATURES,
    FROZEN_15_SELECTED_FEATURES,
    prune_to_selected_features,
    fit_frozen_pipeline,
    predict_ensemble,
    compute_calibration_metrics,
    save_pipeline_bundle,
    DEFAULT_DECISION_THRESHOLD
)

def run_independent_validation():
    print("======================================================================")
    print("      TQ-BioNet Stage 5: Independent Validation (Subsets 6-9)        ")
    print("======================================================================\n")
    
    start_time_all = time.perf_counter()
    
    project_root = Path(__file__).resolve().parent
    data_dir_c = str(project_root / "luna16_data")
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Check/Download/Process subsets 6, 7, 8, 9
    validation_subsets = [6, 7, 8, 9]
    print(f"Verifying caches for independent validation subsets: {validation_subsets}...")
    for idx in validation_subsets:
        # Validate every cache array, schema, version and checksum before reuse.
        cache_valid = False
        try:
            reconstruct_combined_dataset([idx], data_dir_c)
            cache_valid = True
        except (OSError, ValueError, KeyError, FileNotFoundError) as cache_error:
            print(f"   Subset {idx} cache invalid or missing: {cache_error}")
        if cache_valid:
            print(f"   Subset {idx} v3.1 cache verified.")
        else:
            print(f"   Re-building subset {idx} v3.1 cache...")
            # Download and extract raw scan files
            dl_success = False
            for attempt in range(1, 11):
                print(f"      Check/Download Attempt {attempt}/10 for subset {idx}...")
                if download_and_extract_subset(idx):
                    dl_success = True
                    break
                else:
                    print(f"      Attempt failed. Waiting {15 * attempt} seconds...")
                    time.sleep(15 * attempt)
            
            if not dl_success:
                raise RuntimeError(f"Failed to acquire subset {idx} raw files after 10 attempts.")
                
            # Process and cache subset
            process_and_save_subset(idx)
            
    print("\nAll independent validation subset caches verified.")
    
    # 1. Reconstruct Development Dataset (Subsets 0-5)
    print("\nReconstructing development cohort (Subsets 0-5) for model training...")
    X_dev, y_dev, groups_dev, coords_dev, subsets_dev = reconstruct_combined_dataset([0, 1, 2, 3, 4, 5], data_dir_c)
    print(f"   Development cohort size: {len(X_dev)} samples")
    
    # 2. Reconstruct Validation Dataset (Subsets 6-9)
    print("Reconstructing independent validation cohort (Subsets 6-9) for evaluation...")
    X_val, y_val, groups_val, coords_val, subsets_val = reconstruct_combined_dataset(validation_subsets, data_dir_c)
    print(f"   Independent validation cohort size: {len(X_val)} samples")
    
    # 3. Feature Selection: Prune to 15 frozen features using central model_config
    X_dev_pruned = prune_to_selected_features(X_dev)
    X_val_pruned = prune_to_selected_features(X_val)

    # 4 & 5. Fit Frozen Classifiers on full Development Cohort
    print("\nTraining frozen SVM, XGBoost, and RF classifiers on the full development cohort...")
    svm, xgb, rf, scaler = fit_frozen_pipeline(X_dev_pruned, y_dev, random_state=42)

    # Save frozen pipeline bundle
    save_pipeline_bundle(outputs_dir / "frozen_v3_1_pipeline", svm, xgb, rf, scaler)

    # 6. Evaluate on Independent Validation Cohort using predict_ensemble
    print("Evaluating models on independent validation cohort...")
    preds_dict = predict_ensemble(svm, xgb, rf, scaler, X_val_pruned, threshold=DEFAULT_DECISION_THRESHOLD)
    svm_probs = preds_dict['svm_prob']
    xgb_probs = preds_dict['xgb_prob']
    rf_probs = preds_dict['rf_prob']
    ensemble_probs = preds_dict['ensemble_prob']
    ensemble_preds = preds_dict['y_pred']
    svm_preds = (svm_probs >= DEFAULT_DECISION_THRESHOLD).astype(int)
    xgb_preds = (xgb_probs >= DEFAULT_DECISION_THRESHOLD).astype(int)
    
    # Calculate performance metrics with scan-cluster bootstrap intervals and calibration
    def evaluate_model(y_true, y_pred, y_prob, groups=None):
        acc = accuracy_score(y_true, y_pred)
        sens = recall_score(y_true, y_pred) if np.sum(y_true == 1) > 0 else 0.0
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        prec = precision_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        auc_val = roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0.5

        cal = compute_calibration_metrics(y_true, y_prob)
        
        # Scan-cluster bootstrap confidence intervals when scan groups provided
        if groups is not None and len(np.unique(groups)) > 1:
            auc_ci = compute_cluster_bootstrap_ci(y_true, y_prob, groups, roc_auc_score)
            f1_ci = compute_cluster_bootstrap_ci(y_true, y_pred, groups, f1_score)
            acc_ci = compute_cluster_bootstrap_ci(y_true, y_pred, groups, accuracy_score)
        else:
            auc_ci = compute_bootstrap_ci(y_true, y_prob, roc_auc_score)
            f1_ci = compute_bootstrap_ci(y_true, y_pred, f1_score)
            acc_ci = compute_wilson_ci(int(np.sum(y_pred == y_true)), len(y_true))

        sens_low, sens_high = compute_wilson_ci(int(np.sum((y_pred == 1) & (y_true == 1))), int(np.sum(y_true == 1)))
        spec_low, spec_high = compute_wilson_ci(int(np.sum((y_pred == 0) & (y_true == 0))), int(np.sum(y_true == 0)))
        prec_low, prec_high = compute_wilson_ci(int(np.sum((y_pred == 1) & (y_true == 1))), int(np.sum(y_pred == 1)))
        
        return {
            "accuracy": acc, "accuracy_ci": acc_ci,
            "sensitivity": sens, "sensitivity_ci": (sens_low, sens_high),
            "specificity": spec, "specificity_ci": (spec_low, spec_high),
            "precision": prec, "precision_ci": (prec_low, prec_high),
            "f1": f1, "f1_ci": f1_ci,
            "auc": auc_val, "auc_ci": auc_ci,
            "brier_score": cal["brier_score"],
            "expected_calibration_error": cal["expected_calibration_error"],
            "cm": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        }
        
    metrics_ens = evaluate_model(y_val, ensemble_preds, ensemble_probs, groups=groups_val)
    metrics_svm = evaluate_model(y_val, svm_preds, svm_probs, groups=groups_val)
    metrics_xgb = evaluate_model(y_val, xgb_preds, xgb_probs, groups=groups_val)
    
    # 7. Outputs Save & Cleanup
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Evaluate each subset separately and save per-subset JSON metrics
    per_subset_metrics = {}
    for sub in validation_subsets:
        mask = (subsets_val == sub)
        if np.sum(mask) > 0:
            m_ens = evaluate_model(y_val[mask], ensemble_preds[mask], ensemble_probs[mask], groups=groups_val[mask])
            m_svm = evaluate_model(y_val[mask], svm_preds[mask], svm_probs[mask], groups=groups_val[mask])
            m_xgb = evaluate_model(y_val[mask], xgb_preds[mask], xgb_probs[mask], groups=groups_val[mask])
            
            sub_dict = {
                "SVM": {k: v for k, v in m_svm.items() if k != "cm"},
                "XGBoost": {k: v for k, v in m_xgb.items() if k != "cm"},
                "VotingEnsemble": {k: v for k, v in m_ens.items() if k != "cm"},
                "confusion_matrix": m_ens["cm"]
            }
            per_subset_metrics[sub] = sub_dict
            
            sub_path = outputs_dir / f"validation_subset{sub}_metrics.json"
            with open(sub_path, "w") as f:
                json.dump(sub_dict, f, indent=4)
                    
    # Save predictions
    df_preds = pd.DataFrame({
        "seriesuid": groups_val,
        "subset": subsets_val,
        "x": coords_val[:, 0],
        "y": coords_val[:, 1],
        "z": coords_val[:, 2],
        "true_label": y_val,
        "svm_prob": svm_probs,
        "xgb_prob": xgb_probs,
        "rf_prob": rf_probs,
        "ensemble_prob": ensemble_probs,
        "predicted_label": ensemble_preds
    })
    preds_path = outputs_dir / "validation_predictions.csv"
    df_preds.to_csv(preds_path, index=False)
    
    # Save confusion matrix
    cm = metrics_ens["cm"]
    df_cm = pd.DataFrame({
        "metric": ["true_negative", "false_positive", "false_negative", "true_positive"],
        "value": [cm["tn"], cm["fp"], cm["fn"], cm["tp"]]
    })
    cm_path = outputs_dir / "validation_confusion_matrix.csv"
    df_cm.to_csv(cm_path, index=False)
    
    # Save metrics JSON
    metrics_dict = {
        "SVM": {k: v for k, v in metrics_svm.items() if k != "cm"},
        "XGBoost": {k: v for k, v in metrics_xgb.items() if k != "cm"},
        "VotingEnsemble": {k: v for k, v in metrics_ens.items() if k != "cm"}
    }
    metrics_path = outputs_dir / "validation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics_dict, f, indent=4)
        
    # Save experiment manifest JSON
    runtime_duration = time.perf_counter() - start_time_all
    manifest_val = {
        "phase": "Independent Validation",
        "date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "git_commit": get_git_commit(),
        "algorithm_version": "v3.1",
        "feature_version": "v3.1",
        "random_seed": 42,
        "subset_list": validation_subsets,
        "sample_count": int(len(y_val)),
        "feature_dimension": 15,
        "cache_hashes": {
            f"subset{i}": get_file_sha256(os.path.join(data_dir_c, "cache", "tq_bionet_v3_1", f"subset{i}", "X.npy"))
            for i in validation_subsets
        },
        "runtime_evaluation_sec": float(runtime_duration)
    }
    manifest_path = outputs_dir / "experiment_manifest_validation.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_val, f, indent=4)
        
    # Save validation summary markdown
    summary_md = f"""# TQ-BioNet v3.1 Independent Validation Summary

This document summarizes the final evaluation outcomes of the frozen TQ-BioNet v3.1 framework on the independent evaluation cohort (SeriesUID-separated Subsets 6–9). Note: SeriesUID separation establishes scan-level independence, which is conditional on confirming patient-level separation where scans originate from distinct individuals.

## Validation Scope
- **Validation Date**: {manifest_val["date"]} UTC
- **Development Cohort**: Subsets 0–5 (1446 samples) - Used for classifier training
- **Validation Cohort**: Subsets 6–9 ({len(y_val)} samples) - Used for validation testing
- **Feature Pipeline Version**: v3.1 (Isotropic 1.0mm, Local Z-Score IQR Preprocessing)
- **Features Pruned**: 15 key biophysical/topological features

## Independent Validation Cohort Metrics (Combined Subsets 6–9)

| Metric [CI Type] | Support Vector Machine (SVM) | XGBoost Classifier | Voting Ensemble |
| :--- | :--- | :--- | :--- |
| **Accuracy** [Scan-Cluster Bootstrap 95%] | {metrics_svm["accuracy"]:.4f} [{metrics_svm["accuracy_ci"][0]:.3f} - {metrics_svm["accuracy_ci"][1]:.3f}] | {metrics_xgb["accuracy"]:.4f} [{metrics_xgb["accuracy_ci"][0]:.3f} - {metrics_xgb["accuracy_ci"][1]:.3f}] | {metrics_ens["accuracy"]:.4f} [{metrics_ens["accuracy_ci"][0]:.3f} - {metrics_ens["accuracy_ci"][1]:.3f}] |
| **Sensitivity** [Candidate Wilson 95%] | {metrics_svm["sensitivity"]:.4f} [{metrics_svm["sensitivity_ci"][0]:.3f} - {metrics_svm["sensitivity_ci"][1]:.3f}] | {metrics_xgb["sensitivity"]:.4f} [{metrics_xgb["sensitivity_ci"][0]:.3f} - {metrics_xgb["sensitivity_ci"][1]:.3f}] | {metrics_ens["sensitivity"]:.4f} [{metrics_ens["sensitivity_ci"][0]:.3f} - {metrics_ens["sensitivity_ci"][1]:.3f}] |
| **Specificity** [Candidate Wilson 95%] | {metrics_svm["specificity"]:.4f} [{metrics_svm["specificity_ci"][0]:.3f} - {metrics_svm["specificity_ci"][1]:.3f}] | {metrics_xgb["specificity"]:.4f} [{metrics_xgb["specificity_ci"][0]:.3f} - {metrics_xgb["specificity_ci"][1]:.3f}] | {metrics_ens["specificity"]:.4f} [{metrics_ens["specificity_ci"][0]:.3f} - {metrics_ens["specificity_ci"][1]:.3f}] |
| **Precision** [Candidate Wilson 95%] | {metrics_svm["precision"]:.4f} [{metrics_svm["precision_ci"][0]:.3f} - {metrics_svm["precision_ci"][1]:.3f}] | {metrics_xgb["precision"]:.4f} [{metrics_xgb["precision_ci"][0]:.3f} - {metrics_xgb["precision_ci"][1]:.3f}] | {metrics_ens["precision"]:.4f} [{metrics_ens["precision_ci"][0]:.3f} - {metrics_ens["precision_ci"][1]:.3f}] |
| **F1-Score** [Scan-Cluster Bootstrap 95%] | {metrics_svm["f1"]:.4f} [{metrics_svm["f1_ci"][0]:.3f} - {metrics_svm["f1_ci"][1]:.3f}] | {metrics_xgb["f1"]:.4f} [{metrics_xgb["f1_ci"][0]:.3f} - {metrics_xgb["f1_ci"][1]:.3f}] | {metrics_ens["f1"]:.4f} [{metrics_ens["f1_ci"][0]:.3f} - {metrics_ens["f1_ci"][1]:.3f}] |
| **AUC-ROC** [Scan-Cluster Bootstrap 95%] | {metrics_svm["auc"]:.4f} [{metrics_svm["auc_ci"][0]:.3f} - {metrics_svm["auc_ci"][1]:.3f}] | {metrics_xgb["auc"]:.4f} [{metrics_xgb["auc_ci"][0]:.3f} - {metrics_xgb["auc_ci"][1]:.3f}] | {metrics_ens["auc"]:.4f} [{metrics_ens["auc_ci"][0]:.3f} - {metrics_ens["auc_ci"][1]:.3f}] |

## Ensemble Confusion Matrix
- **True Negatives**: {cm["tn"]}
- **False Positives**: {cm["fp"]}
- **False Negatives**: {cm["fn"]}
- **True Positives**: {cm["tp"]}
"""
    summary_path = outputs_dir / "validation_summary.md"
    with open(summary_path, "w") as f:
        f.write(summary_md)
            
    print("\nValidation artifacts saved to outputs directory successfully.")
    
    print("\n--------------------------------------------------")
    print("Independent validation completed successfully.")
    print("Development cohort was NOT modified.")
    print("Frozen methodology preserved.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    run_independent_validation()
