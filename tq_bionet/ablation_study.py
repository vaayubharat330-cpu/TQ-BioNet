import numpy as np
import warnings
from sklearn.model_selection import train_test_split

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.synthetic_data import generate_synthetic_dataset
from tq_bionet.pipeline import extract_tq_bio_features, train_and_evaluate_model


        
from tq_bionet.evaluation_metrics import compute_wilson_ci

def run_ablation_study():
    print("======================================================================")
    print("                Running TQ-BioNet Ablation Study                      ")
    print("======================================================================\n")
    
    # 1. Generate dataset
    num_pos = 40
    X_raw, y = generate_synthetic_dataset(num_samples_per_class=num_pos)
    
    # 2. Extract all features
    print("      Extracting features from all patches...")
    X_all = []
    for i in range(len(X_raw)):
        _, f_vec = extract_tq_bio_features(X_raw[i])
        X_all.append(f_vec)
    X_all = np.array(X_all)
    
    # Split datasets (70% Train, 30% Test)
    X_train_all, X_test_all, y_train, y_test = train_test_split(
        X_all, y, test_size=0.30, random_state=42, stratify=y
    )
    
    # Generate keys sorted
    dummy_dict, _ = extract_tq_bio_features(X_raw[0])
    feature_keys = sorted([k for k in dummy_dict.keys() if k != 'extraction_time_sec'])
    
    quantum_indices = [i for i, k in enumerate(feature_keys) if 'quantum' in k]
    topo_indices = [i for i, k in enumerate(feature_keys) if 'H0_' in k or 'H1_' in k]
    fractal_indices = [i for i, k in enumerate(feature_keys) if 'fractal' in k or 'lacunarity' in k]
    
    configurations = {
        "Wave/Quantum Features Only": quantum_indices,
        "Topological (TDA) Features Only": topo_indices,
        "Fractal Geometry Features Only": fractal_indices,
        "Wave + Topological": quantum_indices + topo_indices,
        "Wave + Fractal": quantum_indices + fractal_indices,
        "Topological + Fractal": topo_indices + fractal_indices,
        "Full TQ-BioNet (Combined)": list(range(26))
    }
    
    n_test = len(y_test)
    
    # Tables for SVM and XGBoost
    for model_name in ['svm', 'xgboost']:
        print(f"\n======================================================================")
        print(f"      Ablation Performance Table: {model_name.upper()} Classifier (Independent Test)")
        print(f"======================================================================")
        print(f"{'Configuration':<32} | {'Accuracy [95% CI]':<22} | {'Sens':<6} | {'Spec':<6} | {'F1':<6} | {'AUC':<6}")
        print("-" * 90)
        
        for name, indices in configurations.items():
            X_tr = X_train_all[:, indices]
            X_te = X_test_all[:, indices]
            
            _, res = train_and_evaluate_model(X_tr, y_train, X_te, y_test, model_type=model_name)
            
            successes = int(round(res['accuracy'] * n_test))
            low, high = compute_wilson_ci(successes, n_test)
            acc_ci_str = f"{res['accuracy']:.3f} [{low:.2f}-{high:.2f}]"
            
            print(f"{name:<32} | {acc_ci_str:<22} | {res['sensitivity']:.3f} | {res['specificity']:.3f} | {res['f1_score']:.3f} | {res['auc']:.3f}")
        print("======================================================================\n")

if __name__ == "__main__":
    run_ablation_study()
