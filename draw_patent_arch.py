import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_arch_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 10), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 120)
    ax.axis('off')

    # Background color
    fig.patch.set_facecolor('white')

    # Color palette matching patent sample
    c_blue_border = '#1B365D'
    c_header_fill = '#E8EEF5'
    c_box_fill = '#FAFCFF'
    c_accent_fill = '#1E3D59'
    c_green_box = '#E8F5E9'
    c_green_border = '#2E7D32'

    # Top Title Box
    rect_top = patches.Rectangle((3, 108), 94, 7, linewidth=1.5, edgecolor=c_blue_border, facecolor=c_header_fill)
    ax.add_patch(rect_top)
    ax.text(50, 111.5, 'TQ-BioNet System Architecture', ha='center', va='center', fontsize=12, fontweight='bold', color=c_blue_border)

    # Down arrow from top
    ax.annotate('', xy=(50, 104), xytext=(50, 108), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Row 1: Box 1 (Input) & Box 2 (Preprocessing)
    r1 = patches.Rectangle((3, 88), 45, 16, linewidth=1.2, edgecolor='black', facecolor='white')
    ax.add_patch(r1)
    ax.text(25.5, 100.5, '1. Thoracic CT Input', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(5, 96, '• 3D Thoracic CT Scans (1,018 LUNA16 Scans)', fontsize=8)
    ax.text(5, 92.5, '• Nodule Candidate Coordinates (x, y, z)', fontsize=8)
    ax.text(5, 89, '• Patient-Disjoint Partitioning (0–5 Dev / 6–9 Test)', fontsize=8)

    r2 = patches.Rectangle((52, 88), 45, 16, linewidth=1.2, edgecolor='black', facecolor='white')
    ax.add_patch(r2)
    ax.text(74.5, 100.5, '2. Preprocessing Engine', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(54, 96, '• 1.0 mm³ Isotropic 3D Resampling', fontsize=8)
    ax.text(54, 92.5, '• 32×32×32 mm³ Candidate Patch Slicing', fontsize=8)
    ax.text(54, 89, '• Local Z-Score IQR Contrast Normalization', fontsize=8)

    # Arrow between Box 1 and Box 2
    ax.annotate('', xy=(52, 96), xytext=(48, 96), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Arrow from Box 2 down to Feature Extraction
    ax.annotate('', xy=(50, 83), xytext=(74.5, 88), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Box 3: Feature Extraction Container
    r3_outer = patches.Rectangle((3, 44), 94, 39, linewidth=1.5, edgecolor=c_accent_fill, facecolor='white')
    ax.add_patch(r3_outer)

    # Header bar for Box 3
    r3_bar = patches.Rectangle((3, 76), 94, 7, linewidth=1.5, edgecolor=c_accent_fill, facecolor=c_accent_fill)
    ax.add_patch(r3_bar)
    ax.text(50, 79.5, '3. Deterministic Biophysical Feature Extraction (Zero Learnable Parameters)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='white')

    # Sub-box 3A: Topological & Quantum Branch
    r3a = patches.Rectangle((5, 54), 43, 20, linewidth=1.2, edgecolor='#1B365D', facecolor='#F4F7FB')
    ax.add_patch(r3a)
    ax.text(26.5, 70.5, 'Topological Homology & Quantum Physics', ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D')
    ax.text(7, 66.5, '• Sublevel Persistent Entropy (H₀)', fontsize=7.5)
    ax.text(7, 63, '• 1D Betti Numbers (β₁) & Persistence (Ptot)', fontsize=7.5)
    ax.text(7, 59.5, '• 3D Schrödinger Potential Well V(r) = -Î(r)', fontsize=7.5)
    ax.text(7, 56, '• Energy Eigenvalues (E₀, E₁, E₂)', fontsize=7.5)

    # Sub-box 3B: Hessian & Fractal Branch
    r3b = patches.Rectangle((52, 54), 43, 20, linewidth=1.2, edgecolor='#1B365D', facecolor='#F4F7FB')
    ax.add_patch(r3b)
    ax.text(73.5, 70.5, '3D Hessian Geometry & Complexity', ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D')
    ax.text(54, 66.5, '• Multi-Scale Frangi Vesselness Filter (V_σ)', fontsize=7.5)
    ax.text(54, 63, '• 3D Blobness Curvature Ratio (R_B)', fontsize=7.5)
    ax.text(54, 59.5, '• Principal Curvatures (λ₁, λ₂, λ₃)', fontsize=7.5)
    ax.text(54, 56, '• 3D Fractal Dimension (D_F) & Lacunarity', fontsize=7.5)

    # Connector banner for 15D vector
    r_vec = patches.Rectangle((12, 46), 76, 6, linewidth=1.2, edgecolor='#1B365D', facecolor='#E8EEF5')
    ax.add_patch(r_vec)
    ax.text(50, 49, '15-Dimensional Frozen Feature Vector (x ∈ ℝ¹⁵) — Zero Parameters (W = 0)', ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B365D')

    # Arrow down to Classifiers
    ax.annotate('', xy=(50, 39), xytext=(50, 44), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Row 3: Box 4 (Classifier) & Box 5 (Diagnostic Output)
    r4 = patches.Rectangle((3, 23), 45, 16, linewidth=1.2, edgecolor='black', facecolor='white')
    ax.add_patch(r4)
    ax.text(25.5, 35.5, '4. Soft-Voting Ensemble Head', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(5, 31, '• Support Vector Classifier (RBF Kernel)', fontsize=8)
    ax.text(5, 27.5, '• XGBoost Gradient-Boosted Trees', fontsize=8)
    ax.text(5, 24, '• Random Forest Decision Ensemble', fontsize=8)

    r5 = patches.Rectangle((52, 23), 45, 16, linewidth=1.2, edgecolor='black', facecolor='white')
    ax.add_patch(r5)
    ax.text(74.5, 35.5, '5. Diagnostic Clinical Output', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(54, 31, '• Calibrated Malignancy Risk Probability', fontsize=8)
    ax.text(54, 27.5, '• Juxta-Vascular False-Positive Filter', fontsize=8)
    ax.text(54, 24, '• Clinician Decision Support & Triage Report', fontsize=8)

    # Arrow between Box 4 and Box 5
    ax.annotate('', xy=(52, 31), xytext=(48, 31), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Arrow down to performance box
    ax.annotate('', xy=(50, 17), xytext=(50, 23), arrowprops=dict(facecolor='black', edgecolor='black', width=1, headwidth=5))

    # Performance Banner Box
    r_perf = patches.Rectangle((3, 7), 94, 10, linewidth=1.5, edgecolor=c_green_border, facecolor=c_green_box)
    ax.add_patch(r_perf)
    ax.text(50, 13, 'Model Performance: 86.29% Accuracy  |  90.71% Specificity  |  0.9198 AUC-ROC', ha='center', va='center', fontsize=9.5, fontweight='bold', color=c_green_border)
    ax.text(50, 9.5, 'Evaluated on Independent Held-Out LUNA16 Validation Cohort (N = 926 Patches)', ha='center', va='center', fontsize=8.5, fontweight='bold', color=c_green_border)

    # Caption at bottom
    ax.text(50, 2.5, 'FIG 1 System Architecture Diagram', ha='center', va='center', fontsize=11, fontweight='bold')

    out_img = r'c:\Users\suraj\Desktop\4th yr project\patent_fig1_architecture.png'
    plt.tight_layout()
    plt.savefig(out_img, dpi=300, bbox_inches='tight')
    plt.close()
    print("Architecture diagram saved at:", out_img)

if __name__ == '__main__':
    generate_arch_diagram()
