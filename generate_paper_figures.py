import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Common color palette
c_dark = '#0F2C59'
c_blue = '#1E56A0'
c_light_blue = '#EBF4F6'
c_teal = '#028391'
c_orange = '#FFF3CD'
c_orange_border = '#856404'
c_green = '#2E7D32'
c_green_bg = '#E8F5E9'
c_red = '#721C24'
c_red_bg = '#F8D7DA'

def make_fig1_existing():
    fig, ax = plt.subplots(figsize=(8, 8.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 110)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # Top block: Radiologist Manual Review
    b1 = patches.FancyBboxPatch((5, 94), 90, 12, boxstyle="round,pad=0.3", edgecolor='black', facecolor='#EAECEE', linewidth=1.2)
    ax.add_patch(b1)
    ax.text(50, 102, "Radiologist / Screening Facility (Manual Review)", ha='center', va='center', fontsize=10.5, fontweight='bold')
    ax.text(50, 97, "Manual axial slice inspection (300–700 slices per CT scan) subject to fatigue", ha='center', va='center', fontsize=8.5, color='#444444')

    ax.annotate('', xy=(50, 88), xytext=(50, 94), arrowprops=dict(facecolor='black', edgecolor='black', width=1.2, headwidth=5))

    # Middle container: Isolated CAD Approaches
    b_mid = patches.FancyBboxPatch((5, 34), 90, 54, boxstyle="round,pad=0.4", edgecolor='black', facecolor='#F8F9FA', linewidth=1.2)
    ax.add_patch(b_mid)
    ax.text(50, 84, "Independent Diagnostic Approaches (Isolated CAD Pipelines)", ha='center', va='center', fontsize=10, fontweight='bold', color=c_dark)

    # Sub-block 1: GLCM
    s1 = patches.Rectangle((8, 70), 84, 10, edgecolor='black', facecolor='white', linewidth=1)
    ax.add_patch(s1)
    ax.text(50, 76, "Handcrafted GLCM Radiomics (Armato et al. [1])", ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(50, 72.5, "Shallow texture descriptors; fails under multi-vendor CT contrast drift", ha='center', va='center', fontsize=8, color='#555555')

    # Sub-block 2: 3D CNNs
    s2 = patches.Rectangle((8, 57), 84, 10, edgecolor='black', facecolor='white', linewidth=1)
    ax.add_patch(s2)
    ax.text(50, 63, "3D Deep Convolutional Networks (3D ResNet / U-Net [2], [4])", ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(50, 59.5, "Opaque black-box models (~11.2M to 34.5M weights); memorizes scanner noise", ha='center', va='center', fontsize=8, color='#555555')

    # Sub-block 3: Vision Transformers
    s3 = patches.Rectangle((8, 44), 84, 10, edgecolor='black', facecolor='white', linewidth=1)
    ax.add_patch(s3)
    ax.text(50, 50, "3D Swin Transformers & DenseNets (Liu et al. [5], Li et al. [6])", ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(50, 46.5, "Massive compute footprint (~28M params); juxta-vascular vessel confusion", ha='center', va='center', fontsize=8, color='#555555')

    # Sub-block 4: Random image splitting
    s4 = patches.Rectangle((8, 36), 84, 6, edgecolor=c_red, facecolor=c_red_bg, linewidth=1)
    ax.add_patch(s4)
    ax.text(50, 39, "Random Patch-Level Splitting Protocol (Data Leakage Risk Across Scans)", ha='center', va='center', fontsize=8, fontweight='bold', color=c_red)

    ax.annotate('', xy=(50, 27), xytext=(50, 34), arrowprops=dict(facecolor='black', edgecolor='black', width=1.2, headwidth=5))

    # Bottom container: Drawbacks
    b_bot = patches.FancyBboxPatch((5, 8), 90, 19, boxstyle="round,pad=0.4", edgecolor=c_orange_border, facecolor=c_orange, linewidth=1.2)
    ax.add_patch(b_bot)
    ax.text(50, 23.5, "Drawbacks of Existing Diagnostic Approach", ha='center', va='center', fontsize=10, fontweight='bold', color=c_orange_border)
    ax.text(8, 19, "• Juxta-Vascular Geometric Ambiguity: Cannot separate spherical nodules from vessels.", fontsize=8, color='#333333')
    ax.text(8, 15.5, "• Black-Box Opacity: Millions of learned weights lack physical clinical interpretability.", fontsize=8, color='#333333')
    ax.text(8, 12, "• Scanner Hardware Drift: High performance drop across GE, Siemens, and Philips CTs.", fontsize=8, color='#333333')

    ax.text(50, 2.5, "FIG 8.1 Existing System: Disconnected Screening Pipeline", ha='center', va='center', fontsize=9.5, fontweight='bold')

    plt.tight_layout()
    plt.savefig(r'c:\Users\suraj\Desktop\4th yr project\fig1_existing_system.png', dpi=300, bbox_inches='tight')
    plt.close()

def make_fig2_proposed():
    fig, ax = plt.subplots(figsize=(8, 9), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 105)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    stages = [
        ("1. Volumetric CT Clinical Intake", "1,018 LUNA16 Thoracic CT scans + Candidate Coordinates (x, y, z)", 86, '#EBF4F6', c_dark),
        ("2. Multimodal Preprocessing Engine", "Isotropic 1.0 mm³ resampling & Local Z-Score IQR Normalization", 68, '#F0F9FF', c_blue),
        ("3. Biophysical Dual-Branch Feature Extraction", "Topological Homology (TDA) & 3D Schrödinger Density-Well Physics", 50, '#FFFBEB', '#92400E'),
        ("4. 3D Differential Geometry & Curvature Modeling", "Multi-scale Hessian Frangi Vesselness & 3D Blobness (V_σ, R_B, λᵢ)", 32, '#F5F3FF', '#5B21B6'),
        ("5. Soft-Voting Ensemble Classification Head", "Calibrated predictions via SVM, XGBoost & RF (86.29% Acc, 0.9198 AUC)", 14, '#ECFDF5', c_green)
    ]

    for title, desc, y_pos, bg_c, border_c in stages:
        b = patches.FancyBboxPatch((6, y_pos), 88, 13, boxstyle="round,pad=0.3", edgecolor=border_c, facecolor=bg_c, linewidth=1.3)
        ax.add_patch(b)
        ax.text(50, y_pos + 8.5, title, ha='center', va='center', fontsize=10, fontweight='bold', color=border_c)
        ax.text(50, y_pos + 4, desc, ha='center', va='center', fontsize=8.5, color='#333333')
        if y_pos > 15:
            ax.annotate('', xy=(50, y_pos - 5), xytext=(50, y_pos), arrowprops=dict(facecolor=c_dark, edgecolor=c_dark, width=1.2, headwidth=5))

    ax.text(50, 3, "FIG 9 Proposed System Framework", ha='center', va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(r'c:\Users\suraj\Desktop\4th yr project\fig2_proposed_framework.png', dpi=300, bbox_inches='tight')
    plt.close()

def make_fig4_bar():
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
    models = ['GLCM Radiomics\n[1]', '3D ResNet-18\n[2]', '3D U-Net\n[4]', '3D DenseNet\n[6]', '3D Swin Trans.\n[5]', 'Proposed\nTQ-BioNet (Ours)']
    accuracies = [74.30, 80.10, 81.40, 83.10, 85.20, 86.29]
    colors = ['#CFD8DC', '#CFD8DC', '#CFD8DC', '#CFD8DC', '#CFD8DC', '#1E88E5']

    bars = ax.bar(models, accuracies, color=colors, edgecolor='black', width=0.6, linewidth=1)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.7, f'{height:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylim(50, 100)
    ax.set_ylabel('Candidate Classification Accuracy (%)', fontsize=10, fontweight='bold')
    ax.set_title('Detection Accuracy across Evaluated Architectures on LUNA16 Benchmark', fontsize=11, fontweight='bold', pad=14)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(r'c:\Users\suraj\Desktop\4th yr project\fig4_accuracy_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    make_fig1_existing()
    make_fig2_proposed()
    make_fig4_bar()
    print("All figures successfully created.")
