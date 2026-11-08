import os
import glob
import json
import numpy as np
import pandas as pd
import SimpleITK as sitk
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, recall_score, precision_score, f1_score, confusion_matrix, roc_curve, precision_recall_curve, average_precision_score

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.pipeline import extract_tq_bio_features

def run_lndb_validation():
    print("======================================================================")
    print("        TQ-BioNet v3.0 External Validation on LNDb CT Dataset         ")
    print("======================================================================\n")

    base_dir = Path(__file__).resolve().parent
    lndb_dir = base_dir / "lndb_data"
    extracted_dir = lndb_dir / "extracted"
    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # NOTE: This legacy script is not a valid v3.0 zero-shot external validation:
    # it currently has no frozen 15-feature model artifact or matching LNDb
    # preprocessing/feature-schema pipeline. Stop rather than report misleading metrics.
    raise RuntimeError(
        "LNDb validation is disabled pending a reproducible frozen-model export, "
        "shared preprocessing/resampling, identical selected feature schema, and "
        "verified LNDb label semantics. The previous script trained a different "
        "model and extracted mismatched native-spacing features."
    )

    # 1. Load actual LUNA16 Development Cohort cached features (Subsets 0–5)
    cache_base = base_dir / "luna16_data" / "cache" / "tq_bionet_v3"
    X_dev_list = []
    y_dev_list = []

    for s_idx in range(6):
        x_path = cache_base / f"subset{s_idx}" / "X.npy"
        y_path = cache_base / f"subset{s_idx}" / "y.npy"
        if x_path.exists() and y_path.exists():
            X_sub = np.load(x_path)
            y_sub = np.load(y_path)
            X_dev_list.append(X_sub)
            y_dev_list.append(y_sub)

    if len(X_dev_list) > 0:
        X_dev = np.vstack(X_dev_list)
        y_dev = np.hstack(y_dev_list)
        print(f"Loaded actual LUNA16 Development Cohort (Subsets 0–5): {len(X_dev)} samples, {X_dev.shape[1]} features.")
    else:
        print("Error: Could not load LUNA16 development cache.")
        return

    # 2. Extract LNDb Candidate Patches
    csv_path = lndb_dir / "allNods.csv"
    df_nods = pd.read_csv(csv_path)
    mhd_files = sorted(glob.glob(str(extracted_dir / "*.mhd")))
    print(f"Found {len(mhd_files)} extracted LNDb CT volumes (.mhd)")

    lndb_patches = []
    lndb_labels = []

    print("\nExtracting candidate 3D patches from LNDb volumes...")
    for mhd_path in mhd_files:
        basename = os.path.basename(mhd_path)
        scan_id = int(basename.replace("LNDb-", "").replace(".mhd", ""))
        
        scan_nods = df_nods[df_nods['LNDbID'] == scan_id].copy()
        if len(scan_nods) == 0:
            continue

        try:
            sitk_img = sitk.ReadImage(mhd_path)
            img_arr = sitk.GetArrayFromImage(sitk_img)
            spacing = np.array(sitk_img.GetSpacing())
        except Exception as e:
            continue

        for idx, row in scan_nods.iterrows():
            if pd.isna(row['x']) or pd.isna(row['y']) or pd.isna(row['z']):
                continue

            phys_pt = (float(row['x']), float(row['y']), float(row['z']))
            try:
                vox_idx = sitk_img.TransformPhysicalPointToIndex(phys_pt)
            except Exception:
                continue

            vx, vy, vz = vox_idx
            iz, iy, ix = vz, vy, vx

            half_w = int(round(16.0 / max(0.5, spacing[0])))
            half_h = int(round(16.0 / max(0.5, spacing[1])))
            half_d = int(round(16.0 / max(0.5, spacing[2])))

            z_min, z_max = max(0, iz - half_d), min(img_arr.shape[0], iz + half_d)
            y_min, y_max = max(0, iy - half_h), min(img_arr.shape[1], iy + half_h)
            x_min, x_max = max(0, ix - half_w), min(img_arr.shape[2], ix + half_w)

            patch = img_arr[z_min:z_max, y_min:y_max, x_min:x_max]
            if patch.size < 500:
                continue

            nod_type = str(row['NodType']).lower() if not pd.isna(row['NodType']) else 'none'
            diam = float(row['DiamEq_Rad']) if not pd.isna(row['DiamEq_Rad']) else 0.0

            if nod_type in ['nod', 'mass'] and diam >= 3.0:
                label = 1
            else:
                label = 0

            try:
                _, f_vec = extract_tq_bio_features(patch)
                lndb_patches.append(f_vec)
                lndb_labels.append(label)
            except Exception:
                continue

    X_lndb = np.array(lndb_patches)
    y_lndb = np.array(lndb_labels)
    print(f"\nExtracted {len(X_lndb)} LNDb candidate patches (Positives: {np.sum(y_lndb == 1)}, Negatives: {np.sum(y_lndb == 0)})")

    # 3. Fit scaler and models on actual LUNA16 Development Data
    scaler = StandardScaler()
    X_dev_scaled = scaler.fit_transform(X_dev)
    X_lndb_scaled = scaler.transform(X_lndb)

    clf_svm = SVC(C=10.0, kernel='rbf', probability=True, random_state=42)
    clf_rf = RandomForestClassifier(n_estimators=300, max_features='sqrt', random_state=42)
    clf_xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, eval_metric='logloss', random_state=42)

    ensemble = VotingClassifier(
        estimators=[('svm', clf_svm), ('rf', clf_rf), ('xgb', clf_xgb)],
        voting='soft'
    )
    ensemble.fit(X_dev_scaled, y_dev)
    print("Ensemble model fitted on actual LUNA16 development data.")

    # 4. Evaluate on LNDb
    y_probs = ensemble.predict_proba(X_lndb_scaled)[:, 1]
    y_preds = (y_probs >= 0.50).astype(int)

    auc = roc_auc_score(y_lndb, y_probs)
    acc = accuracy_score(y_lndb, y_preds)
    sens = recall_score(y_lndb, y_preds, pos_label=1)
    spec = recall_score(y_lndb, y_preds, pos_label=0)
    prec = precision_score(y_lndb, y_preds, pos_label=1) if np.sum(y_preds == 1) > 0 else 0.0
    f1 = f1_score(y_lndb, y_preds, pos_label=1) if np.sum(y_preds == 1) > 0 else 0.0
    cm = confusion_matrix(y_lndb, y_preds)

    print("\n======================================================================")
    print("        EXTERNAL VALIDATION RESULTS ON LNDb DATASET                    ")
    print("======================================================================")
    print(f"  Candidate Patches (N) : {len(y_lndb)}")
    print(f"  AUC-ROC               : {auc:.4f}")
    print(f"  Accuracy              : {acc*100:.2f}%")
    print(f"  Specificity           : {spec*100:.2f}%")
    print(f"  Precision             : {prec*100:.2f}%")
    print(f"  Sensitivity (Recall)  : {sens*100:.2f}%")
    print(f"  F1-Score              : {f1:.4f}")
    print(f"  Confusion Matrix      :\n{cm}")
    print("======================================================================\n")

    # 5. Save metrics to JSON
    metrics_dict = {
        'dataset': 'LNDb External Validation',
        'n_samples': int(len(y_lndb)),
        'n_positives': int(np.sum(y_lndb == 1)),
        'n_negatives': int(np.sum(y_lndb == 0)),
        'auc_roc': float(auc),
        'accuracy': float(acc),
        'specificity': float(spec),
        'precision': float(prec),
        'sensitivity': float(sens),
        'f1_score': float(f1),
        'confusion_matrix': cm.tolist()
    }

    metrics_file = output_dir / "lndb_external_validation_metrics.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics_dict, f, indent=4)
    print(f"Saved LNDb metrics to {metrics_file}")

    # Plot ROC and Confusion Matrix
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
    ax.grid(True, linestyle='--', alpha=0.5)
    fpr, tpr, _ = roc_curve(y_lndb, y_probs)
    ax.plot(fpr, tpr, color='#0072CE', lw=2.5, label=f'TQ-BioNet (LNDb AUC = {auc:.4f})')
    ax.plot([0, 1], [0, 1], color='#888888', lw=1.5, linestyle='--', label='Chance Baseline (AUC = 0.50)')
    ax.set_title('External Validation ROC Curve on LNDb Dataset\n(N = {} Candidate Patches, 43 CT Scans)'.format(len(y_lndb)), fontsize=11, fontweight='bold', color='#0F2043')
    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=10, fontweight='bold')
    ax.set_ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=10, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, facecolor='white', fontsize=9.5)
    plt.tight_layout()
    lndb_roc_path = output_dir / "lndb_roc_curve.png"
    plt.savefig(lndb_roc_path, dpi=300)
    plt.close()

    fig, ax = plt.subplots(figsize=(5.5, 4.5), dpi=300)
    cax = ax.matshow(cm, cmap='Blues', alpha=0.85)
    fig.colorbar(cax)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), va='center', ha='center', fontsize=14, fontweight='bold', color='black' if cm[i, j] < 100 else 'white')
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Non-Nodule (0)', 'Nodule (1)'], fontsize=9, fontweight='bold')
    ax.set_yticklabels(['Non-Nodule (0)', 'Nodule (1)'], fontsize=9, fontweight='bold')
    ax.set_title('LNDb External Validation Confusion Matrix\n(N = {} Patches)'.format(len(y_lndb)), fontsize=11, fontweight='bold', color='#0F2043')
    ax.set_xlabel('Predicted Label', fontsize=10, fontweight='bold')
    ax.set_ylabel('True Label', fontsize=10, fontweight='bold')
    plt.tight_layout()
    lndb_cm_path = output_dir / "lndb_confusion_matrix.png"
    plt.savefig(lndb_cm_path, dpi=300)
    plt.close()

    # Artifacts are saved only inside the repository outputs directory.

if __name__ == "__main__":
    run_lndb_validation()
