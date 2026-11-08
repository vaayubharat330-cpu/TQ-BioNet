import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_tq_bionet_architecture():
    # Set up high-res figure (8.5 x 11 aspect ratio friendly)
    fig, ax = plt.subplots(figsize=(9, 11.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 130)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # Color Palette: Professional Medical AI Engineering
    c_dark = '#0F2C59'       # Deep Navy
    c_blue = '#1E56A0'       # Primary Accent Blue
    c_light_blue = '#EBF4F6' # Soft Blue Container
    c_teal = '#028391'       # Physics/TDA Accent
    c_orange = '#F6DCAC'     # Highlight Container
    c_green = '#2E7D32'      # Success / Evaluation
    c_green_bg = '#F1F8F5'   # Performance Box Fill
    c_border = '#333333'     # Box Border

    # 1. Main Header Banner
    h_box = patches.FancyBboxPatch((4, 120), 92, 7.5, boxstyle="round,pad=0.3", 
                                   edgecolor=c_dark, facecolor=c_dark, linewidth=1.5)
    ax.add_patch(h_box)
    ax.text(50, 123.75, "TQ-BioNet v3.0: SYSTEM ARCHITECTURE & ENGINEERING PIPELINE", 
            ha='center', va='center', fontsize=12, fontweight='bold', color='white')

    # Connector 1
    ax.annotate('', xy=(50, 115), xytext=(50, 120), 
                arrowprops=dict(facecolor=c_dark, edgecolor=c_dark, width=1.5, headwidth=6))

    # 2. Stage 1: Volumetric Input & Preprocessing
    stage1_box = patches.FancyBboxPatch((4, 98), 92, 17, boxstyle="round,pad=0.4", 
                                        edgecolor=c_blue, facecolor='#F8FAFC', linewidth=1.4)
    ax.add_patch(stage1_box)
    
    # Title Tag for Stage 1
    t1_box = patches.Rectangle((4, 110), 40, 5, facecolor=c_blue, edgecolor=c_blue)
    ax.add_patch(t1_box)
    ax.text(24, 112.5, "STAGE 1: INPUT CT & ROBUST PREPROCESSING", ha='center', va='center', 
            fontsize=8.5, fontweight='bold', color='white')

    # Step 1A: CT Volume
    ax.text(8, 106.5, "3D Thoracic CT Volume", fontsize=9.5, fontweight='bold', color=c_dark)
    ax.text(8, 103, "• 1,018 LUNA16 Thoracic CT scans", fontsize=8.5, color='#333333')
    ax.text(8, 100, "• Spatial Resampling: 1.0 mm³ isotropic", fontsize=8.5, color='#333333')

    # Arrow 1A -> 1B
    ax.annotate('', xy=(48, 103), xytext=(43, 103), 
                arrowprops=dict(facecolor=c_blue, edgecolor=c_blue, width=1.2, headwidth=5))

    # Step 1B: Patch & IQR Normalization
    ax.text(50, 106.5, "Candidate Extraction & Local Normalization", fontsize=9.5, fontweight='bold', color=c_dark)
    ax.text(50, 103, "• Patch Size: 32×32×32 mm³ volume centered on candidate", fontsize=8.5, color='#333333')
    ax.text(50, 100, "• Local Z-Score IQR: Î = [I − Median(I)] / [IQR(I) + 10⁻⁶]", fontsize=8.5, fontweight='bold', color=c_teal)

    # Connector 2
    ax.annotate('', xy=(50, 92), xytext=(50, 98), 
                arrowprops=dict(facecolor=c_dark, edgecolor=c_dark, width=1.5, headwidth=6))

    # 3. Stage 2: Deterministic Biophysical Feature Extractor Container (Zero Learnable Parameters)
    stage2_box = patches.FancyBboxPatch((4, 46), 92, 46, boxstyle="round,pad=0.5", 
                                        edgecolor=c_teal, facecolor=c_light_blue, linewidth=1.8)
    ax.add_patch(stage2_box)

    # Title Tag for Stage 2
    t2_box = patches.Rectangle((4, 87), 54, 5, facecolor=c_teal, edgecolor=c_teal)
    ax.add_patch(t2_box)
    ax.text(31, 89.5, "STAGE 2: ZERO-PARAMETER BIOPHYSICAL FEATURE ENGINES", ha='center', va='center', 
            fontsize=8.5, fontweight='bold', color='white')
    ax.text(76, 89.5, "Frozen Feature Extractor: W = 0", ha='center', va='center', 
            fontsize=8.5, fontweight='bold', color=c_dark)

    # 4 Parallel Sub-Engines
    # Box 2A: TDA
    b_tda = patches.FancyBboxPatch((6, 61), 20.5, 24, boxstyle="round,pad=0.3", 
                                  edgecolor=c_border, facecolor='white', linewidth=1)
    ax.add_patch(b_tda)
    ax.text(16.25, 82, "Topological Data Analysis", ha='center', va='center', fontsize=8, fontweight='bold', color=c_dark)
    ax.text(16.25, 79.5, "(Sublevel Persistence)", ha='center', va='center', fontsize=7.5, fontstyle='italic', color='#555555')
    ax.text(8, 75, "• Entropy H₀", fontsize=8, fontweight='bold')
    ax.text(8, 71.5, "• 0D Total Pers. Ptot_H₀", fontsize=7.5)
    ax.text(8, 68, "• 1D Loops β₁", fontsize=8, fontweight='bold')
    ax.text(8, 64.5, "• 1D Total Pers. Ptot_H₁", fontsize=7.5)
    ax.text(16.25, 62, "4 Features (0–3)", ha='center', fontsize=7.5, fontweight='bold', color=c_teal)

    # Box 2B: Schrödinger
    b_qm = patches.FancyBboxPatch((28.5, 61), 20.5, 24, boxstyle="round,pad=0.3", 
                                 edgecolor=c_border, facecolor='white', linewidth=1)
    ax.add_patch(b_qm)
    ax.text(38.75, 82, "Schrödinger Physics", ha='center', va='center', fontsize=8, fontweight='bold', color=c_dark)
    ax.text(38.75, 79.5, "(Density Potential Trap)", ha='center', va='center', fontsize=7.5, fontstyle='italic', color='#555555')
    ax.text(30.5, 75, "• Ground State E₀", fontsize=8, fontweight='bold')
    ax.text(30.5, 71.5, "• 1st Excited E₁", fontsize=8)
    ax.text(30.5, 68, "• 2nd Excited E₂", fontsize=8)
    ax.text(30.5, 64.5, "• Solves: Ĥψ = Eψ", fontsize=7.5)
    ax.text(38.75, 62, "3 Features (4–6)", ha='center', fontsize=7.5, fontweight='bold', color=c_teal)

    # Box 2C: 3D Hessian
    b_hess = patches.FancyBboxPatch((51, 61), 20.5, 24, boxstyle="round,pad=0.3", 
                                   edgecolor=c_border, facecolor='white', linewidth=1)
    ax.add_patch(b_hess)
    ax.text(61.25, 82, "3D Hessian Geometry", ha='center', va='center', fontsize=8, fontweight='bold', color=c_dark)
    ax.text(61.25, 79.5, "(Vessel/Blob Separation)", ha='center', va='center', fontsize=7.5, fontstyle='italic', color='#555555')
    ax.text(53, 75, "• Frangi Vesselness V_σ", fontsize=8, fontweight='bold')
    ax.text(53, 71.5, "• 3D Blobness R_B", fontsize=8, fontweight='bold')
    ax.text(53, 68, "• Principal Curv. λ₁", fontsize=7.5)
    ax.text(53, 64.5, "• Curvatures λ₂, λ₃", fontsize=7.5)
    ax.text(61.25, 62, "5 Features (7–11)", ha='center', fontsize=7.5, fontweight='bold', color=c_teal)

    # Box 2D: Fractal
    b_frac = patches.FancyBboxPatch((73.5, 61), 20.5, 24, boxstyle="round,pad=0.3", 
                                   edgecolor=c_border, facecolor='white', linewidth=1)
    ax.add_patch(b_frac)
    ax.text(83.75, 82, "Fractal Complexity", ha='center', va='center', fontsize=8, fontweight='bold', color=c_dark)
    ax.text(83.75, 79.5, "(Textural Coarseness)", ha='center', va='center', fontsize=7.5, fontstyle='italic', color='#555555')
    ax.text(75.5, 75, "• Box-Count Dim. D_F", fontsize=8, fontweight='bold')
    ax.text(75.5, 71.5, "• Lacunarity Box 4", fontsize=7.5)
    ax.text(75.5, 68, "• Lacunarity Box 8", fontsize=7.5)
    ax.text(75.5, 64.5, "• Multi-scale gappiness", fontsize=7.5)
    ax.text(83.75, 62, "3 Features (12–14)", ha='center', fontsize=7.5, fontweight='bold', color=c_teal)

    # Output Vector Bar
    v_box = patches.FancyBboxPatch((8, 48), 84, 8, boxstyle="round,pad=0.3", 
                                   edgecolor=c_dark, facecolor='white', linewidth=1.5)
    ax.add_patch(v_box)
    ax.text(50, 53, "UNIFIED 15-DIMENSIONAL FROZEN FEATURE VECTOR (x ∈ ℝ¹⁵)", 
            ha='center', va='center', fontsize=9.5, fontweight='bold', color=c_dark)
    ax.text(50, 49.5, "Feature Extraction Execution Latency: 24.52 ms  |  Memory: 0 MB GPU VRAM", 
            ha='center', va='center', fontsize=8, fontstyle='italic', color='#444444')

    # Connector 3
    ax.annotate('', xy=(50, 40), xytext=(50, 46), 
                arrowprops=dict(facecolor=c_dark, edgecolor=c_dark, width=1.5, headwidth=6))

    # 4. Stage 3: Soft-Voting Ensemble Classifier & Decision Engine
    stage3_box = patches.FancyBboxPatch((4, 21), 92, 19, boxstyle="round,pad=0.4", 
                                        edgecolor=c_blue, facecolor='#F8FAFC', linewidth=1.4)
    ax.add_patch(stage3_box)

    # Title Tag for Stage 3
    t3_box = patches.Rectangle((4, 35), 44, 5, facecolor=c_blue, edgecolor=c_blue)
    ax.add_patch(t3_box)
    ax.text(26, 37.5, "STAGE 3: CLASSIFIER & DIAGNOSTIC TRIAGE", ha='center', va='center', 
            fontsize=8.5, fontweight='bold', color='white')

    # Sub-Box 3A: Soft-Voting Model
    ax.text(8, 31, "Soft-Voting Ensemble Decision Engine", fontsize=9.5, fontweight='bold', color=c_dark)
    ax.text(8, 27.5, "• Support Vector Machine (RBF Kernel, C=10)", fontsize=8.5)
    ax.text(8, 24.5, "• Extreme Gradient Boosting (XGBoost, 300 Trees)", fontsize=8.5)
    ax.text(8, 21.5, "• Random Forest Classifier (300 Estimators)", fontsize=8.5)

    # Arrow 3A -> 3B
    ax.annotate('', xy=(51, 27.5), xytext=(46, 27.5), 
                arrowprops=dict(facecolor=c_blue, edgecolor=c_blue, width=1.2, headwidth=5))

    # Sub-Box 3B: Outputs
    ax.text(53, 31, "Clinical Referral & Triage Outputs", fontsize=9.5, fontweight='bold', color=c_dark)
    ax.text(53, 27.5, "• Calibrated Posterior Malignancy Risk P(Y=1|x)", fontsize=8.5, fontweight='bold', color=c_teal)
    ax.text(53, 24.5, "• Juxta-Vascular Vessel False-Positive Suppression", fontsize=8.5)
    ax.text(53, 21.5, "• SHAP Physical Feature Explanations for Radiologists", fontsize=8.5)

    # Connector 4
    ax.annotate('', xy=(50, 15), xytext=(50, 21), 
                arrowprops=dict(facecolor=c_dark, edgecolor=c_dark, width=1.5, headwidth=6))

    # 5. Performance Validation Banner
    p_box = patches.FancyBboxPatch((4, 4), 92, 11, boxstyle="round,pad=0.4", 
                                   edgecolor=c_green, facecolor=c_green_bg, linewidth=1.5)
    ax.add_patch(p_box)
    ax.text(50, 12, "AUDITED EMPIRICAL VALIDATION (LUNA16 Independent Subsets 6–9, N = 926)", 
            ha='center', va='center', fontsize=9.5, fontweight='bold', color=c_green)
    ax.text(50, 8.5, "Accuracy: 86.29%   |   Specificity: 90.71%   |   AUC-ROC: 0.9198   |   Precision: 89.81%", 
            ha='center', va='center', fontsize=9, fontweight='bold', color=c_dark)
    ax.text(50, 5.5, "Zero Patient Overlap (Audited)   |   Total Patch Extraction & Inference Latency: 24.59 ms", 
            ha='center', va='center', fontsize=8, fontstyle='italic', color='#333333')

    # Figure label at bottom
    ax.text(50, 1.2, "FIG 1 System Architecture Diagram", ha='center', va='center', fontsize=10.5, fontweight='bold')

    out_file = r'c:\Users\suraj\Desktop\4th yr project\patent_fig1_architecture.png'
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print("New high-fidelity architecture diagram saved:", out_file)

if __name__ == '__main__':
    draw_tq_bionet_architecture()
