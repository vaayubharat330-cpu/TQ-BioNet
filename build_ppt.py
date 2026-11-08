import os
import pptx
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Colors
    NAVY = RGBColor(15, 32, 67)
    BLUE_ACCENT = RGBColor(0, 114, 206)
    DARK_GRAY = RGBColor(50, 50, 50)
    LIGHT_BG = RGBColor(245, 247, 250)
    WHITE = RGBColor(255, 255, 255)
    BORDER_COLOR = RGBColor(210, 215, 225)
    CARD_BG = RGBColor(255, 255, 255)
    
    blank_layout = prs.slide_layouts[6]
    
    def add_header(slide, title_text, category_text="TQ-BioNet v3.0 Presentation"):
        # Header banner shape
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.9))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = BLUE_ACCENT
        p_cat.font.name = "Calibri"
        
        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY
        p_title.font.name = "Calibri"

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=BORDER_COLOR):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
        return shape

    # ==================== SLIDE 1: TITLE SLIDE ====================
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.fill.background()
    
    # Title box
    tbox = slide1.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.333), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p1 = tf1.paragraphs[0]
    p1.text = "TQ-BioNet v3.0"
    p1.font.size = Pt(38)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(77, 184, 255)
    p1.font.name = "Calibri"
    
    p2 = tf1.add_paragraph()
    p2.text = "A Frozen Topological Quantum & Biophysical Feature Engineering Framework for Automated Pulmonary Nodule Classification"
    p2.font.size = Pt(20)
    p2.font.color.rgb = WHITE
    p2.font.name = "Calibri"
    
    # Divider line
    line = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(3.6), Inches(11.333), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE_ACCENT
    line.line.fill.background()
    
    # Info Card: Supervisor
    c1 = add_card(slide1, 1.0, 4.0, 5.4, 2.7, bg_color=RGBColor(24, 45, 85), border_color=BLUE_ACCENT)
    tb_sup = slide1.shapes.add_textbox(Inches(1.2), Inches(4.1), Inches(5.0), Inches(2.5))
    tf_sup = tb_sup.text_frame
    tf_sup.word_wrap = True
    
    ps1 = tf_sup.paragraphs[0]
    ps1.text = "SUPERVISOR"
    ps1.font.size = Pt(12)
    ps1.font.bold = True
    ps1.font.color.rgb = BLUE_ACCENT
    
    ps2 = tf_sup.add_paragraph()
    ps2.text = "Mr. Mohd Anwar Ali"
    ps2.font.size = Pt(18)
    ps2.font.bold = True
    ps2.font.color.rgb = WHITE
    
    ps3 = tf_sup.add_paragraph()
    ps3.text = "Assistant Professor\nIT Department"
    ps3.font.size = Pt(14)
    ps3.font.color.rgb = RGBColor(200, 215, 235)

    # Info Card: Team Members
    c2 = add_card(slide1, 6.9, 4.0, 5.4, 2.7, bg_color=RGBColor(24, 45, 85), border_color=BLUE_ACCENT)
    tb_team = slide1.shapes.add_textbox(Inches(7.1), Inches(4.1), Inches(5.0), Inches(2.5))
    tf_team = tb_team.text_frame
    tf_team.word_wrap = True
    
    pt1 = tf_team.paragraphs[0]
    pt1.text = "TEAM MEMBERS"
    pt1.font.size = Pt(12)
    pt1.font.bold = True
    pt1.font.color.rgb = BLUE_ACCENT
    
    pt2 = tf_team.add_paragraph()
    pt2.text = "Roll No\t\tName\n23R21A12J7\tV. SURAJ"
    pt2.font.size = Pt(15)
    pt2.font.color.rgb = WHITE

    # ==================== SLIDE 2: CONTENTS ====================
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "Table of Contents")
    
    items = [
        "1. Abstract", "2. Introduction", "3. Project Title Justification",
        "4. Existing System & Disadvantages", "5. Proposed System & Advantages",
        "6. Objectives", "7. Scope", "8. Basic Concepts"
    ]
    
    for i, item in enumerate(items):
        row = i // 2
        col = i % 2
        left = 1.0 + col * 5.8
        top = 1.6 + row * 1.3
        
        add_card(slide2, left, top, 5.5, 1.1, bg_color=LIGHT_BG)
        tb = slide2.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.2), Inches(5.1), Inches(0.7))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = item
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = NAVY

    # ==================== SLIDE 3: ABSTRACT ====================
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Abstract")
    
    add_card(slide3, 0.8, 1.5, 11.733, 5.3, bg_color=LIGHT_BG)
    tb3 = slide3.shapes.add_textbox(Inches(1.1), Inches(1.7), Inches(11.133), Inches(4.9))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    
    p_abs1 = tf3.paragraphs[0]
    p_abs1.text = "Early diagnosis of pulmonary nodules in Thoracic Computed Tomography (CT) scans is vital for improving lung cancer prognosis. However, traditional radiomic features are highly sensitive to scanner noise and Hounsfield Unit (HU) contrast variations, while modern 3D Deep Convolutional Neural Networks (CNNs) operate as uninterpretable 'black boxes' prone to overfitting on medical datasets. To address these challenges, this project introduces TQ-BioNet v3.0, a mathematically explainable framework combining Topological Data Analysis (TDA), Quantum-Inspired Spectral Mechanics, and Multi-Scale Differential Geometry for automated nodule classification."
    p_abs1.font.size = Pt(15)
    p_abs1.font.color.rgb = DARK_GRAY
    p_abs1.space_after = Pt(14)
    
    p_abs2 = tf3.add_paragraph()
    p_abs2.text = "The framework applies Local Z-Score Interquartile Range (IQR) normalization to eliminate cross-scanner contrast drift. A 15-dimensional frozen feature space is constructed, integrating Persistent Entropy and 1D loop counts for tissue connectivity, discretized 3D Schrödinger potential energy eigenvalues for density wells, and Hessian curvature tensors (Frangi Vesselness & Blobness) for separating nodules from blood vessels. Trained on LUNA16 Subsets 0–5 (1,446 samples) and evaluated on independent Subsets 6–9 (926 samples), the Voting Ensemble model achieved a peak AUC-ROC of 0.9266, an accuracy of 86.43%, and a specificity of 92.38% without uninterpretable neural networks."
    p_abs2.font.size = Pt(15)
    p_abs2.font.color.rgb = DARK_GRAY

    # ==================== SLIDE 4: INTRODUCTION ====================
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Introduction")
    
    intro_boxes = [
        ("Clinical Need", "Lung cancer is a leading cause of global cancer mortality. Early detection of small pulmonary nodules in thoracic CT scans significantly improves patient survival rates."),
        ("Current Challenges", "Manual screening is labor-intensive and subject to radiologist variability. Automated tools suffer from scanner contrast drift, noise, and ground-glass nodule ambiguity."),
        ("Proposed Solution", "TQ-BioNet v3.0 presents a frozen, zero-parameter feature engineering framework combining topology, quantum energy states, and differential geometry for hardware-invariant classification.")
    ]
    
    for i, (title, desc) in enumerate(intro_boxes):
        top = 1.6 + i * 1.8
        add_card(slide4, 0.8, top, 11.733, 1.5, bg_color=LIGHT_BG)
        
        tb = slide4.shapes.add_textbox(Inches(1.1), Inches(top + 0.15), Inches(11.133), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(18)
        pt.font.bold = True
        pt.font.color.rgb = BLUE_ACCENT
        
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(14)
        pd.font.color.rgb = DARK_GRAY

    # ==================== SLIDE 5: PROJECT TITLE JUSTIFICATION ====================
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "Project Title Justification")
    
    pillars = [
        ("Topological (TQ)", "Persistent Homology", "Extracts Persistent Entropy (H0), 1D Loop counts (β1), and Total Persistence to model structural connectivity and internal vascular cavities."),
        ("Quantum (TQ)", "Schrödinger Spectral Mechanics", "Solves discretized 3D potential-well Hamiltonian equations (Hψ = Eψ) to extract energy eigenvalues (E0, E1, E2) modeling nodule density wells."),
        ("Biophysical Geometry", "3D Hessian Differential Geometry", "Computes 3D curvature eigenvalues to extract Frangi Vesselness (Vσ), Blobness Ratios (RB), and Fractal Dimensions to separate spherical nodules from linear vessels."),
        ("v3.0 Framework", "Local Z-Score IQR Standardization", "Integrates Local Z-Score IQR intensity normalization with a frozen 15-dimensional feature space, ensuring cross-scanner invariance and zero data leakage.")
    ]
    
    for i, (head, sub, desc) in enumerate(pillars):
        row = i // 2
        col = i % 2
        left = 0.8 + col * 5.95
        top = 1.5 + row * 2.8
        
        add_card(slide5, left, top, 5.78, 2.6, bg_color=LIGHT_BG)
        tb = slide5.shapes.add_textbox(Inches(left + 0.25), Inches(top + 0.2), Inches(5.28), Inches(2.2))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p1 = tf.paragraphs[0]
        p1.text = head
        p1.font.size = Pt(18)
        p1.font.bold = True
        p1.font.color.rgb = NAVY
        
        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = BLUE_ACCENT
        p2.space_after = Pt(6)
        
        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(13)
        p3.font.color.rgb = DARK_GRAY

    # ==================== SLIDE 6: EXISTING SYSTEM & DISADVANTAGES ====================
    slide6 = prs.slides.add_slide(blank_layout)
    add_header(slide6, "Existing System & Disadvantages")
    
    add_card(slide6, 0.8, 1.5, 5.7, 5.4, bg_color=LIGHT_BG)
    tb_ex = slide6.shapes.add_textbox(Inches(1.05), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_ex = tb_ex.text_frame
    tf_ex.word_wrap = True
    
    pe1 = tf_ex.paragraphs[0]
    pe1.text = "EXISTING APPROACHES"
    pe1.font.size = Pt(18)
    pe1.font.bold = True
    pe1.font.color.rgb = NAVY
    pe1.space_after = Pt(10)
    
    ex_list = [
        "Traditional Radiomics: First-order intensity statistics and GLCM texture descriptors.",
        "3D Deep Learning: End-to-end 3D Convolutional Neural Networks (3D ResNet, 3D U-Net).",
        "Classification Models: Basic binary thresholding or isolated classifiers."
    ]
    for item in ex_list:
        p = tf_ex.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(14)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)
        
    add_card(slide6, 6.833, 1.5, 5.7, 5.4, bg_color=RGBColor(253, 242, 242), border_color=RGBColor(240, 180, 180))
    tb_dis = slide6.shapes.add_textbox(Inches(7.083), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_dis = tb_dis.text_frame
    tf_dis.word_wrap = True
    
    pd1 = tf_dis.paragraphs[0]
    pd1.text = "KEY DISADVANTAGES"
    pd1.font.size = Pt(18)
    pd1.font.bold = True
    pd1.font.color.rgb = RGBColor(180, 40, 40)
    pd1.space_after = Pt(10)
    
    dis_list = [
        "Scanner Drift Sensitivity: Highly vulnerable to slice thickness, noise, and HU contrast variations across CT vendors.",
        "Black-Box Uninterpretability: 3D CNNs rely on millions of parameters lacking clinical explainability.",
        "Overfitting Risk: High risk of memorizing scanner-specific artifacts on small medical datasets.",
        "Juxta-Vascular Failure: Struggles to distinguish spherical nodules from attached linear blood vessels."
    ]
    for item in dis_list:
        p = tf_dis.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(13)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    # ==================== SLIDE 7: PROPOSED SYSTEM & ADVANTAGES ====================
    slide7 = prs.slides.add_slide(blank_layout)
    add_header(slide7, "Proposed System & Advantages")
    
    add_card(slide7, 0.8, 1.5, 5.7, 5.4, bg_color=LIGHT_BG)
    tb_prop = slide7.shapes.add_textbox(Inches(1.05), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_prop = tb_prop.text_frame
    tf_prop.word_wrap = True
    
    pp1 = tf_prop.paragraphs[0]
    pp1.text = "PROPOSED ARCHITECTURE"
    pp1.font.size = Pt(18)
    pp1.font.bold = True
    pp1.font.color.rgb = NAVY
    pp1.space_after = Pt(10)
    
    prop_list = [
        "Local Z-Score IQR Normalization: Standardizes CT voxel intensities against scanner drift.",
        "15D Frozen Feature Space: Zero trainable weights in feature extraction (Topology + Quantum + Geometry).",
        "Voting Ensemble Classifier: Combines SVM and XGBoost for robust decision-making."
    ]
    for item in prop_list:
        p = tf_prop.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(14)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    add_card(slide7, 6.833, 1.5, 5.7, 5.4, bg_color=RGBColor(240, 248, 255), border_color=BLUE_ACCENT)
    tb_adv = slide7.shapes.add_textbox(Inches(7.083), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_adv = tb_adv.text_frame
    tf_adv.word_wrap = True
    
    pa1 = tf_adv.paragraphs[0]
    pa1.text = "KEY ADVANTAGES"
    pa1.font.size = Pt(18)
    pa1.font.bold = True
    pa1.font.color.rgb = BLUE_ACCENT
    pa1.space_after = Pt(10)
    
    adv_list = [
        "100% Mathematically Explainable: Derived from proven physics, topology, and geometry math.",
        "Zero Overfitting: Feature extractor has zero parameters to overfit scanner noise.",
        "Juxta-Vascular Discrimination: Effectively separates nodules from attached blood vessels.",
        "High Generalization: Evaluated on independent test sets (Subsets 6–9) achieving 0.9266 AUC-ROC."
    ]
    for item in adv_list:
        p = tf_adv.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(13)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    # ==================== SLIDE 8: OBJECTIVES ====================
    slide8 = prs.slides.add_slide(blank_layout)
    add_header(slide8, "Objectives")
    
    objs = [
        "Standardize CT Intensity: Implement Local Z-Score IQR normalization to remove cross-scanner HU contrast drift.",
        "Extract Topological Invariants: Construct Persistent Homology modules to extract Persistent Entropy (H0) and 1D loop counts (β1).",
        "Model Density Operator: Formulate discretized 3D Schrödinger Hamiltonian equations to compute potential-well eigenvalues (E0, E1, E2).",
        "Distinguish Nodules from Vessels: Apply multi-scale 3D Hessian geometry (Vesselness Vσ and Blobness RB) for juxta-vascular separation.",
        "Evaluate Independent Validation: Benchmark frozen classifiers on independent test sets (Subsets 6–9) to guarantee zero data leakage."
    ]
    
    for i, obj in enumerate(objs):
        top = 1.5 + i * 1.05
        add_card(slide8, 0.8, top, 11.733, 0.95, bg_color=LIGHT_BG)
        tb = slide8.shapes.add_textbox(Inches(1.1), Inches(top + 0.1), Inches(11.133), Inches(0.75))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"{i+1}. {obj}"
        p.font.size = Pt(14)
        p.font.color.rgb = DARK_GRAY

    # ==================== SLIDE 9: SCOPE ====================
    slide9 = prs.slides.add_slide(blank_layout)
    add_header(slide9, "Scope of the Project")
    
    add_card(slide9, 0.8, 1.5, 5.7, 5.4, bg_color=LIGHT_BG)
    tb_in = slide9.shapes.add_textbox(Inches(1.05), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_in = tb_in.text_frame
    tf_in.word_wrap = True
    
    pi1 = tf_in.paragraphs[0]
    pi1.text = "IN-SCOPE"
    pi1.font.size = Pt(18)
    pi1.font.bold = True
    pi1.font.color.rgb = NAVY
    pi1.space_after = Pt(10)
    
    in_list = [
        "Target Domain: 3D Thoracic CT imaging for pulmonary nodule candidate classification.",
        "Preprocessing: Isotropic 1.0mm voxel resampling, 32x32x32 patch extraction, Local Z-Score IQR normalization.",
        "Feature Vector: 15-dimensional frozen space (Topology + Quantum Mechanics + Differential Geometry).",
        "Validation: Independent multi-subset testing (Subsets 6–9) using Voting Ensemble classifiers."
    ]
    for item in in_list:
        p = tf_in.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(13)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    add_card(slide9, 6.833, 1.5, 5.7, 5.4, bg_color=RGBColor(245, 245, 245), border_color=RGBColor(200, 200, 200))
    tb_out = slide9.shapes.add_textbox(Inches(7.083), Inches(1.7), Inches(5.2), Inches(5.0))
    tf_out = tb_out.text_frame
    tf_out.word_wrap = True
    
    po1 = tf_out.paragraphs[0]
    po1.text = "OUT-OF-SCOPE"
    po1.font.size = Pt(18)
    po1.font.bold = True
    po1.font.color.rgb = RGBColor(120, 120, 120)
    po1.space_after = Pt(10)
    
    out_list = [
        "Deep Neural Networks: End-to-end 3D CNNs are excluded to guarantee 100% mathematical explainability.",
        "Full 3D Segmentation: Focus is on patch-level candidate classification rather than full-body organ segmentation.",
        "Clinical Biopsy Data: Restricted to non-invasive CT radiological scans; tissue biopsy lab data is excluded."
    ]
    for item in out_list:
        p = tf_out.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(13)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    # ==================== SLIDE 10: BASIC CONCEPTS ====================
    slide10 = prs.slides.add_slide(blank_layout)
    add_header(slide10, "Basic Concepts")
    
    concepts = [
        ("Topological Data Analysis (TDA)", "Computes persistent homology, Betti numbers (β0, β1), and Persistent Entropy across intensity filtration levels to capture tissue connectivity."),
        ("Quantum Schrödinger Dynamics", "Solves discretized 3D potential-well Hamiltonian equations (Hψ = Eψ) to extract energy eigenvalues (E0, E1, E2) modeling nodule density wells."),
        ("3D Hessian Differential Geometry", "Evaluates 3D curvature eigenvalues to compute Frangi Vesselness and Blobness ratios for separating nodules from blood vessels."),
        ("Local Z-Score IQR Normalization", "Standardizes voxel intensities using local median and interquartile range to eliminate cross-scanner Hounsfield Unit contrast drift."),
        ("Voting Ensemble Classifier", "Combines probability predictions from Support Vector Machines (SVM) and XGBoost for robust final decision-making.")
    ]
    
    for i, (title, desc) in enumerate(concepts):
        top = 1.5 + i * 1.05
        add_card(slide10, 0.8, top, 11.733, 0.95, bg_color=LIGHT_BG)
        tb = slide10.shapes.add_textbox(Inches(1.1), Inches(top + 0.1), Inches(11.133), Inches(0.75))
        tf = tb.text_frame
        tf.word_wrap = True
        
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = BLUE_ACCENT
        
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = DARK_GRAY

    # ==================== SLIDE 11: THANK YOU ====================
    slide11 = prs.slides.add_slide(blank_layout)
    bg11 = slide11.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg11.fill.solid()
    bg11.fill.fore_color.rgb = NAVY
    bg11.line.fill.background()
    
    tb11 = slide11.shapes.add_textbox(Inches(1.0), Inches(2.5), Inches(11.333), Inches(2.5))
    tf11 = tb11.text_frame
    tf11.word_wrap = True
    
    pty1 = tf11.paragraphs[0]
    pty1.text = "THANK YOU!"
    pty1.alignment = PP_ALIGN.CENTER
    pty1.font.size = Pt(54)
    pty1.font.bold = True
    pty1.font.color.rgb = RGBColor(77, 184, 255)
    pty1.font.name = "Calibri"
    
    pty2 = tf11.add_paragraph()
    pty2.text = "Questions & Discussion"
    pty2.alignment = PP_ALIGN.CENTER
    pty2.font.size = Pt(24)
    pty2.font.color.rgb = WHITE
    pty2.font.name = "Calibri"

    output_path = r"c:\Users\suraj\Desktop\4th yr project\TQ-BioNet_v3_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_presentation()
