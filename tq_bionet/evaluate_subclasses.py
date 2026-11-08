import numpy as np
import warnings
from sklearn.model_selection import train_test_split

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.synthetic_data import generate_synthetic_dataset
from tq_bionet.pipeline import extract_tq_bio_features, train_and_evaluate_model

def evaluate_subclasses():
    print("======================================================================")
    print("        Calculating Subclass-Specific Accuracies for TQ-BioNet        ")
    print("======================================================================\n")
    
    # 1. Generate dataset
    num_pos = 40
    X_raw, y = generate_synthetic_dataset(num_samples_per_class=num_pos)
    
    # 2. Extract features
    print("      Extracting features...")
    X_features = []
    for i in range(len(X_raw)):
        _, f_vec = extract_tq_bio_features(X_raw[i])
        X_features.append(f_vec)
    X_features = np.array(X_features)
    
    # 3. Train models on a 70/30 split (same as run.py)
    X_train, X_test, y_train, y_test, indices_train, indices_test = train_test_split(
        X_features, y, np.arange(len(y)), test_size=0.30, random_state=42, stratify=y
    )
    
    svm_model, _ = train_and_evaluate_model(X_train, y_train, X_test, y_test, model_type='svm')
    xgb_model, _ = train_and_evaluate_model(X_train, y_train, X_test, y_test, model_type='xgboost')
    
    # 4. Map index to subclass
    # In generate_synthetic_dataset:
    # Positives (0 to 39) are interleaved: 0=Benign, 1=GGO, 2=Spiculated, 3=JuxtaVascular, 4=Benign, etc.
    # Negatives (40 to 79) are all Vascular Crossings
    def get_subclass_name(idx):
        if idx >= 40:
            return "Vascular Crossing (Imposter)"
        sub_idx = idx % 4
        if sub_idx == 0:
            return "Benign Solid Nodule"
        elif sub_idx == 1:
            return "Faint GGO Nodule (Case 1)"
        elif sub_idx == 2:
            return "Spiculated Nodule (Case 3)"
        else:
            return "Juxta-Vascular Nodule (Case 2)"
            
    # Group predictions by subclass over the TEST dataset (24 samples)
    subclass_groups = {
        "Benign Solid Nodule": [],
        "Faint GGO Nodule (Case 1)": [],
        "Spiculated Nodule (Case 3)": [],
        "Juxta-Vascular Nodule (Case 2)": [],
        "Vascular Crossing (Imposter)": []
    }
    
    # Collect SVM and XGBoost predictions strictly for the test set (24 samples)
    for i, idx in enumerate(indices_test):
        subclass = get_subclass_name(idx)
        true_label = y_test[i]
        
        f_vec = X_test[i].reshape(1, -1)
        svm_pred = svm_model.predict(f_vec)[0]
        xgb_pred = xgb_model.predict(f_vec)[0]
        
        subclass_groups[subclass].append({
            'true': true_label,
            'svm_correct': (svm_pred == true_label),
            'xgb_correct': (xgb_pred == true_label)
        })
        
    # Calculate and print accuracy for each subclass on test set
    print("======================================================================")
    print("               SUBCLASS ACCURACY BREAKDOWN (STRICT TEST SET)")
    print("======================================================================")
    print(f"{'Subclass Condition':<35} | {'Test Samples':<12} | {'SVM Accuracy':<13} | {'XGBoost Accuracy':<15}")
    print("-" * 79)
    
    for subclass, samples in subclass_groups.items():
        total = len(samples)
        if total > 0:
            svm_correct = sum(s['svm_correct'] for s in samples)
            xgb_correct = sum(s['xgb_correct'] for s in samples)
            svm_acc = (svm_correct / total) * 100
            xgb_acc = (xgb_correct / total) * 100
            print(f"{subclass:<35} | {total:<12} | {svm_acc:.1f}%        | {xgb_acc:.1f}%")
        else:
            print(f"{subclass:<35} | {0:<12} | N/A           | N/A")
    print("======================================================================\n")

if __name__ == "__main__":
    evaluate_subclasses()
