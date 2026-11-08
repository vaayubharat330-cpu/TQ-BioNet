import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_activity_diagram():
    fig, ax = plt.subplots(figsize=(6, 9), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 110)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # Initial state (black circle)
    circle_init = patches.Circle((50, 104), 2.5, facecolor='black', edgecolor='black')
    ax.add_patch(circle_init)

    steps = [
        "Launch TQ-BioNet Clinical Workstation",
        "Load 3D Thoracic CT Volume (.mhd / DICOM)",
        "Isotropic 1.0 mm³ Resampling & Slicing",
        "Local Z-Score IQR Normalization",
        "Extract 15D Biophysical Feature Vector\n(TDA + Schrödinger + 3D Hessian + Fractal)",
        "Soft-Voting Ensemble Decision Engine\n(SVM + XGBoost + Random Forest)",
        "Generate Juxta-Vascular Vesselness Filter",
        "Display Nodule Probability, SHAP & Save to DB"
    ]

    y = 96
    ax.annotate('', xy=(50, y), xytext=(50, 101.5), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=4))

    for i, step in enumerate(steps):
        h = 6.5 if '\n' not in step else 8.5
        box = patches.FancyBboxPatch((10, y - h), 80, h, boxstyle="round,pad=0.3", edgecolor='#1B365D', facecolor='#F4F7FB', linewidth=1.2)
        ax.add_patch(box)
        ax.text(50, y - h/2, step, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D')
        
        if i < len(steps) - 1:
            next_y = y - h - 4
            ax.annotate('', xy=(50, next_y), xytext=(50, y - h), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=4))
            y = next_y
        else:
            y = y - h

    # Final state (bullseye)
    c_out = patches.Circle((50, y - 5), 2.8, facecolor='white', edgecolor='black', linewidth=1)
    c_in = patches.Circle((50, y - 5), 1.8, facecolor='black', edgecolor='black')
    ax.add_patch(c_out)
    ax.add_patch(c_in)
    ax.annotate('', xy=(50, y - 2.2), xytext=(50, y), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=4))

    out_p = r'c:\Users\suraj\Desktop\4th yr project\uml_activity_diagram.png'
    plt.tight_layout()
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
    plt.close()

def draw_usecase_diagram():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # System boundary
    rect = patches.Rectangle((30, 8), 65, 84, edgecolor='#1B365D', facecolor='#FAFCFF', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(62.5, 88, "TQ-BioNet Screening System Boundary", ha='center', va='center', fontsize=10, fontweight='bold', color='#1B365D')

    # Use cases
    use_cases = [
        ("Input CT Path & Nodule Coordinates", 78),
        ("Run 3D Isotropic Preprocessing", 68),
        ("Extract 15D Biophysical Feature Vector", 58),
        ("Execute Soft-Voting Ensemble Prediction", 48),
        ("Inspect 3D Vesselness & SHAP Explanations", 38),
        ("Export Clinical Audit Report", 28),
        ("Retrain / Re-audit Benchmark Weights", 18)
    ]

    for uc, y_pos in use_cases:
        ellipse = patches.Ellipse((62.5, y_pos), 46, 7.5, edgecolor='#1B365D', facecolor='white', linewidth=1.1)
        ax.add_patch(ellipse)
        ax.text(62.5, y_pos, uc, ha='center', va='center', fontsize=8, fontweight='bold', color='#1B365D')

    # Actor 1: Clinician / Radiologist (Left)
    ax.text(14, 58, "👤\nRadiologist /\nClinician", ha='center', va='center', fontsize=10, fontweight='bold')
    for _, y_pos in use_cases[:6]:
        ax.plot([18, 39.5], [58, y_pos], color='#555555', linestyle='-', linewidth=1)

    # Actor 2: System Administrator (Right)
    ax.text(97, 24, "👤\nSystem\nAdmin", ha='center', va='center', fontsize=9, fontweight='bold')
    ax.plot([85.5, 93], [18, 24], color='#555555', linestyle='-', linewidth=1)

    out_p = r'c:\Users\suraj\Desktop\4th yr project\uml_usecase_diagram.png'
    plt.tight_layout()
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
    plt.close()

def draw_sequence_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    lifelines = [
        ("Clinician UI", 12),
        ("Flask REST API", 37),
        ("TQ-BioNet Engine", 63),
        ("SQLite Database", 88)
    ]

    for name, x in lifelines:
        box = patches.FancyBboxPatch((x - 9, 88), 18, 8, boxstyle="round,pad=0.2", edgecolor='#1B365D', facecolor='#E8EEF5', linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, 92, name, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D')
        ax.plot([x, x], [88, 12], color='#777777', linestyle='--', linewidth=1)

    messages = [
        (12, 37, 80, "1: POST /api/predict (CT_volume, coords)", '->'),
        (37, 63, 70, "2: extract_features(I_patch, IQR_norm)", '->'),
        (63, 63, 60, "3: solve_tda + schrodinger + hessian", 'loop'),
        (63, 37, 50, "4: return 15D vector & ensemble prob", '-->'),
        (37, 88, 40, "5: INSERT PredictionRecord (prob, SHAP)", '->'),
        (88, 37, 30, "6: Return Record_ID & commit", '-->'),
        (37, 12, 20, "7: Render JSON (prob, vessel_flag, latency)", '-->')
    ]

    for x1, x2, y, text, style in messages:
        if style == '->':
            ax.annotate('', xy=(x2, y), xytext=(x1, y), arrowprops=dict(facecolor='black', edgecolor='black', width=0.8, headwidth=4))
        elif style == '-->':
            ax.annotate('', xy=(x2, y), xytext=(x1, y), arrowprops=dict(facecolor='black', edgecolor='black', linestyle='--', width=0.8, headwidth=4))
        elif style == 'loop':
            ax.plot([x1, x1+6, x1+6, x1], [y+2, y+2, y-2, y-2], color='black', linewidth=0.8)
            ax.annotate('', xy=(x1, y-2), xytext=(x1+2, y-2), arrowprops=dict(facecolor='black', edgecolor='black', width=0.8, headwidth=4))
        ax.text((x1 + x2)/2, y + 2, text, ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#1B365D')

    out_p = r'c:\Users\suraj\Desktop\4th yr project\uml_sequence_diagram.png'
    plt.tight_layout()
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
    plt.close()

def draw_class_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # Class 1: TQBioNetExtractor (Top Left)
    r1 = patches.Rectangle((6, 52), 40, 42, edgecolor='#1B365D', facecolor='#F4F7FB', linewidth=1.2)
    ax.add_patch(r1)
    ax.text(26, 90, "TQBioNetExtractor", ha='center', va='center', fontsize=9, fontweight='bold', color='#1B365D')
    ax.plot([6, 46], [86, 86], color='#1B365D', linewidth=1)
    ax.text(8, 82, "- patch_size: int = 32\n- mass_coef: float = 1.0\n- scales: list = [1.0, 1.5, 2.0]", fontsize=7.5)
    ax.plot([6, 46], [71, 71], color='#1B365D', linewidth=1)
    ax.text(8, 62, "+ extract_15d_vector(I): ndarray\n+ solve_schrodinger(I): list\n+ compute_hessian_vessel(I): dict\n+ compute_sublevel_tda(I): dict", fontsize=7.5)

    # Class 2: PredictionService (Top Right)
    r2 = patches.Rectangle((54, 52), 40, 42, edgecolor='#2E7D32', facecolor='#F1F8F5', linewidth=1.2)
    ax.add_patch(r2)
    ax.text(74, 90, "PredictionService", ha='center', va='center', fontsize=9, fontweight='bold', color='#2E7D32')
    ax.plot([54, 94], [86, 86], color='#2E7D32', linewidth=1)
    ax.text(56, 82, "- svm_model: SVC\n- xgb_model: XGBClassifier\n- rf_model: RandomForest", fontsize=7.5)
    ax.plot([54, 94], [71, 71], color='#2E7D32', linewidth=1)
    ax.text(56, 62, "+ predict_candidate(I): dict\n+ soft_voting_predict(x): float\n+ generate_shap_report(x): dict\n+ benchmark_latency(): float", fontsize=7.5)

    # Class 3: VolumePreprocessor (Bottom Left)
    r3 = patches.Rectangle((6, 6), 40, 36, edgecolor='#B45309', facecolor='#FFFBEB', linewidth=1.2)
    ax.add_patch(r3)
    ax.text(26, 38, "VolumePreprocessor", ha='center', va='center', fontsize=9, fontweight='bold', color='#B45309')
    ax.plot([6, 46], [34, 34], color='#B45309', linewidth=1)
    ax.text(8, 28, "- target_spacing: tuple = (1,1,1)\n- hu_clip: tuple = (-1024, 400)", fontsize=7.5)
    ax.plot([6, 46], [22, 22], color='#B45309', linewidth=1)
    ax.text(8, 14, "+ resample_isotropic(img): Image\n+ extract_patch(img, xyz): ndarray\n+ local_iqr_normalize(patch): ndarray", fontsize=7.5)

    # Class 4: PredictionRecord ORM (Bottom Right)
    r4 = patches.Rectangle((54, 6), 40, 36, edgecolor='#6D28D9', facecolor='#F5F3FF', linewidth=1.2)
    ax.add_patch(r4)
    ax.text(74, 38, "PredictionRecord (ORM)", ha='center', va='center', fontsize=9, fontweight='bold', color='#6D28D9')
    ax.plot([54, 94], [34, 34], color='#6D28D9', linewidth=1)
    ax.text(56, 28, "- id: int (Primary Key)\n- candidate_coord: str\n- nodule_prob: float", fontsize=7.5)
    ax.plot([54, 94], [22, 22], color='#6D28D9', linewidth=1)
    ax.text(56, 14, "+ to_dict(): dict\n+ save(): bool\n+ delete(): bool", fontsize=7.5)

    # Connecting arrows
    ax.annotate('«uses»', xy=(54, 73), xytext=(46, 73), arrowprops=dict(facecolor='black', edgecolor='black', width=0.8, headwidth=4), fontsize=7.5)
    ax.annotate('«preprocesses»', xy=(26, 52), xytext=(26, 42), arrowprops=dict(facecolor='black', edgecolor='black', width=0.8, headwidth=4), fontsize=7.5)
    ax.annotate('«persists»', xy=(74, 52), xytext=(74, 42), arrowprops=dict(facecolor='black', edgecolor='black', width=0.8, headwidth=4), fontsize=7.5)

    out_p = r'c:\Users\suraj\Desktop\4th yr project\uml_class_diagram.png'
    plt.tight_layout()
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    draw_activity_diagram()
    draw_usecase_diagram()
    draw_sequence_diagram()
    draw_class_diagram()
    print("All 4 UML diagrams successfully generated.")
