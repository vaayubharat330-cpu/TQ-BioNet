import numpy as np
import time
import warnings
from sklearn.model_selection import train_test_split

# Suppress ripser column-to-row warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

# Import modules from tq_bionet package
from tq_bionet.synthetic_data import (
    generate_synthetic_dataset,
    make_solid_sphere,
    make_ggo_nodule,
    make_spiculated_nodule,
    make_juxta_vascular_nodule,
    make_vascular_bifurcation
)
from tq_bionet.pipeline import extract_tq_bio_features, train_and_evaluate_model

def run_main_pipeline():
    print("======================================================================")
    print("   Running Topological-Quantum Biophysical Framework (TQ-BioNet)")
    print("======================================================================\n")
    
    # 1. Generate Synthetic Dataset
    print("[1/4] Generating balanced synthetic CT patch dataset...")
    # Generate 40 positive nodule patches (10 benign, 10 GGO, 10 spiculated, 10 juxta-vascular)
    # and 40 negative patches (vascular crossings)
    num_pos = 40
    X_raw, y = generate_synthetic_dataset(num_samples_per_class=num_pos)
    print(f"      Total generated patches: {X_raw.shape[0]}")
    print(f"      Class distribution: Positive = {np.sum(y == 1)}, Negative = {np.sum(y == 0)}")
    
    # 2. Extract Features for the dataset
    print("\n[2/4] Extracting TQ-BioNet features (Schrödinger, Homology, Fractals)...")
    print("      (Note: This computes numerical finite-difference eigenvalues and persistence diagrams)")
    
    X_features = []
    start_time = time.time()
    
    for i in range(len(X_raw)):
        if (i + 1) % 10 == 0 or (i + 1) == len(X_raw):
            print(f"      Processed {i + 1}/{len(X_raw)} patches...")
            
        _, f_vec = extract_tq_bio_features(
            X_raw[i], 
            mass_coef='adaptive', 
            potential_scale='adaptive', 
            threshold=0.01
        )
        X_features.append(f_vec)
        
    X_features = np.array(X_features)
    feature_time = time.time() - start_time
    print(f"      Feature extraction complete! Feature matrix shape: {X_features.shape}")
    print(f"      Average extraction time per 3D patch: {feature_time / len(X_raw):.4f} seconds")
    
    # Generate mock Patient IDs to test Patient-Level Splitting (no leakage)
    # We have 80 samples. We define 20 unique patients (each having 4 patches).
    patient_ids = np.repeat(np.arange(20), 4)
    
    # 3. Partition Data strictly at the Patient Level (Zero Leakage)
    from tq_bionet.data_loader import patient_level_train_test_split
    X_train, X_test, y_train, y_test, _, _ = patient_level_train_test_split(
        X_features, y, patient_ids, test_size=0.30, random_state=42
    )
    
    print(f"\n[3/4] Patient-level data partitioning complete:")
    print(f"      Train set size: {X_train.shape[0]} (Positives: {np.sum(y_train == 1)})")
    print(f"      Test set size: {X_test.shape[0]} (Positives: {np.sum(y_test == 1)})")
    print(f"      Unique patients in Train: {len(np.unique(patient_ids[:int(len(patient_ids)*0.7)]))}")
    print(f"      Unique patients in Test : {len(np.unique(patient_ids[int(len(patient_ids)*0.7):]))}")
    
    # 4. Train and Evaluate Classifiers
    print("\n[4/4] Training and evaluating standard classifiers...")
    
    # Evaluate SVM
    svm_model, svm_results = train_and_evaluate_model(X_train, y_train, X_test, y_test, model_type='svm')
    # Evaluate XGBoost
    xgb_model, xgb_results = train_and_evaluate_model(X_train, y_train, X_test, y_test, model_type='xgboost')
    
    # Calculate statistical metrics: 95% Confidence Intervals
    from tq_bionet.evaluation_metrics import compute_wilson_ci, run_mcnemars_test, plot_roc_pr_curves
    n_test = len(y_test)
    svm_low, svm_high = compute_wilson_ci(int(round(svm_results['accuracy'] * n_test)), n_test)
    xgb_low, xgb_high = compute_wilson_ci(int(round(xgb_results['accuracy'] * n_test)), n_test)
    
    # Run McNemar's Test for classifier consistency comparison
    svm_preds = svm_model.predict(X_test)
    xgb_preds = xgb_model.predict(X_test)
    mcnemar = run_mcnemars_test(y_test, svm_preds, xgb_preds)
    
    # Plot and save ROC & PR curves (Issue 5 portability)
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    svm_probs = svm_model.predict_proba(X_test)[:, 1]
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    plot_roc_pr_curves(
        y_test, svm_probs, xgb_probs,
        save_path_roc=str(outputs_dir / "roc_curve.png"),
        save_path_pr=str(outputs_dir / "pr_curve.png")
    )
    
    # Display results
    print("\n======================================================================")
    print("                        MODEL PERFORMANCE RESULTS                     ")
    print("======================================================================")
    print(f"{'Metric':<18} | {'Support Vector Machine (SVM)':<28} | {'XGBoost Classifier':<20}")
    print("-" * 74)
    print(f"{'Accuracy [95% CI]':<18} | {svm_results['accuracy']:.4f} [{svm_low*100:.1f}%-{svm_high*100:.1f}%]   | {xgb_results['accuracy']:.4f} [{xgb_low*100:.1f}%-{xgb_high*100:.1f}%]")
    print(f"{'Sensitivity (Rec)':<18} | {svm_results['sensitivity']:.4f}                       | {xgb_results['sensitivity']:.4f}")
    print(f"{'Specificity':<18} | {svm_results['specificity']:.4f}                       | {xgb_results['specificity']:.4f}")
    print(f"{'F1-Score':<18} | {svm_results['f1_score']:.4f}                       | {xgb_results['f1_score']:.4f}")
    print(f"{'AUC Score':<18} | {svm_results['auc']:.4f}                       | {xgb_results['auc']:.4f}")
    print(f"{'Train Time':<18} | {svm_results['train_time_sec'] * 1000:.2f} ms                     | {xgb_results['train_time_sec'] * 1000:.2f} ms")
    print("-" * 74)
    print("  * McNemar's Test Significance (SVM vs. XGBoost):")
    print(f"    - Discordant predictions: b={mcnemar['b_discordant']} (SVM correct, XGB incorrect)")
    print(f"                              c={mcnemar['c_discordant']} (SVM incorrect, XGB correct)")
    print(f"    - Statistic: {mcnemar['statistic']:.4f}")
    print(f"    - p-value: {mcnemar['p_value']:.4f} (Statistically Significant: {mcnemar['statistically_significant']})")
    print("======================================================================\n")
    
    # 5. Targeted Case Validations
    print("======================================================================")
    print("                  TARGETED TEST CASE DIAGNOSTICS")
    print("======================================================================")
    
    # Test cases: GGO, Spiculated Nodule, Juxta-Vascular Nodule, and Vascular Crossing
    cases = {
        "Faint GGO Nodule (Case 1)": make_ggo_nodule(),
        "Spiculated Malignant Nodule (Case 2/3)": make_spiculated_nodule(),
        "Juxta-Vascular Nodule (Case 2 attachment)": make_juxta_vascular_nodule(),
        "Vascular Crossing/Bifurcation (Case 3 imposter)": make_vascular_bifurcation()
    }
    
    for name, patch in cases.items():
        # Get features
        _, f_vec = extract_tq_bio_features(patch)
        f_vec = f_vec.reshape(1, -1)
        
        # Predict using SVM
        svm_label = svm_model.predict(f_vec)[0]
        svm_prob = svm_model.predict_proba(f_vec)[0, 1]
        svm_status = "NODULE" if svm_label == 1 else "NO NODULE"
        
        # Predict using XGBoost
        xgb_label = xgb_model.predict(f_vec)[0]
        xgb_prob = xgb_model.predict_proba(f_vec)[0, 1]
        xgb_status = "NODULE" if xgb_label == 1 else "NO NODULE"
        
        print(f"  * {name:<50}")
        print(f"    - SVM Decision    : {svm_status:<10} (Confidence: {svm_prob * 100:.2f}%)")
        print(f"    - XGBoost Decision: {xgb_status:<10} (Confidence: {xgb_prob * 100:.2f}%)")
    print("======================================================================\n")

if __name__ == "__main__":
    run_main_pipeline()
