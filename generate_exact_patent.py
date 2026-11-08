import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=0, bottom=0, left=0, right=0):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_sig_table(doc, sheet_num, total_sheets=2):
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    col_w1 = Inches(4.5)
    col_w2 = Inches(2.0)
    
    cell1 = tbl.cell(0, 0)
    cell1.width = col_w1
    set_cell_margins(cell1)
    p1 = cell1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(0)
    p1.paragraph_format.line_spacing = Pt(13)
    r1 = p1.add_run("Authorized Signatory & Lead Inventor\nDepartment of Information Technology\nMLR Institute of Technology, Hyderabad\nStudent Co-Inventors & Researchers")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(10)
    
    cell2 = tbl.cell(0, 1)
    cell2.width = col_w2
    set_cell_margins(cell2)
    p2 = cell2.paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(0)
    p2.paragraph_format.line_spacing = Pt(13)
    r2 = p2.add_run(f"Number of Sheets: {total_sheets}\nSheet Number: {sheet_num}")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(10)

def p_form2_head(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = Pt(14)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.bold = True

def p_heading(doc, text, space_before=14, space_after=6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = Pt(13.5)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.bold = True

def p_body(doc, text, space_after=6, space_before=0, bold_lead=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = Pt(13.5)
    if bold_lead:
        rb = p.add_run(bold_lead)
        rb.font.name = "Times New Roman"
        rb.font.size = Pt(11)
        rb.font.bold = True
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

def p_formula(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = Pt(14)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.bold = True

TITLE_TEXT = "TQ-BioNet: Lung Nodule Classification on Thoracic CT Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry"

def build():
    doc = docx.Document()
    
    for sec in doc.sections:
        sec.page_width = Inches(8.5)
        sec.page_height = Inches(11.0)
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)
        
    # =========================================================================
    # PAGE 1 (Cover Specification - Clean Legal Entity Identification)
    # =========================================================================
    p_form2_head(doc, "FORM-2")
    p_form2_head(doc, "THE PATENTS ACT, 1970")
    p_form2_head(doc, "(39 OF 1970)")
    p_form2_head(doc, "AND")
    p_form2_head(doc, "THE PATENTS RULES, 2003")
    p_form2_head(doc, "(As Amended)")
    
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    
    p_form2_head(doc, "COMPLETE SPECIFICATION")
    p_form2_head(doc, "(SECTION 10, RULE 13)")
    
    p_heading(doc, "TITLE", space_before=32, space_after=4)
    p_body(doc, TITLE_TEXT, space_after=20)
    
    p_heading(doc, "APPLICANT(S)", space_before=10, space_after=4)
    p_body(doc, "MLR Institute of Technology (An Autonomous Institution affiliated to JNTUH),\nDundigal, Gandimaisamma Mandal, Hyderabad, Telangana – 500043, India. (An Indian Educational Institution).", space_after=10)
    
    p_heading(doc, "INVENTOR(S)", space_before=10, space_after=4)
    p_body(doc, "1. Ch. Upender Rao (Assistant Professor, Dept. of IT, MLR Institute of Technology, Hyderabad, India)\n2. Veludandi Suraj (Dept. of IT, MLR Institute of Technology, Hyderabad, India)\n3. Thatipalli Vijay Durga (Dept. of IT, MLR Institute of Technology, Hyderabad, India)\n4. Patnam Sathwik (Dept. of IT, MLR Institute of Technology, Hyderabad, India)\n5. Tanneru Koushal Kumar (Dept. of IT, MLR Institute of Technology, Hyderabad, India)", space_after=80)
    
    p_end = doc.add_paragraph()
    p_end.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_end.paragraph_format.space_before = Pt(0)
    p_end.paragraph_format.space_after = Pt(0)
    p_end.paragraph_format.line_spacing = Pt(13.5)
    r_end = p_end.add_run("The appended specification particularly describes the invention and the manner in which it is to be performed.")
    r_end.font.name = "Times New Roman"
    r_end.font.size = Pt(11)
    r_end.font.italic = True
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 2 (Field of the Invention & Objectives 1 to 4)
    # =========================================================================
    p_heading(doc, TITLE_TEXT, space_before=0, space_after=12)
    
    p_heading(doc, "Field of the Invention", space_before=8, space_after=4)
    p_body(doc, "The present invention relates generally to computerized image processing systems for volumetric medical imaging, digital radiography analysis, and biophysical computational modeling. More specifically, the invention provides a computer-implemented image-processing system and method for discriminating pulmonary nodule candidate patches from non-nodule anatomical false alarms (such as blood vessel bifurcations and apical pleural scarring) in 3D Thoracic Computed Tomography (CT) volumes.")
    p_body(doc, "The system addresses the technical limitations of conventional black-box convolutional neural networks and empirical radiomics by executing a deterministic biophysical framework (TQ-BioNet). The pipeline suppresses inter-scanner attenuation variations through an adaptive local contrast normalization operator, constructs a 15-dimensional frozen feature space combining Topological Data Analysis, discretized 3D Schrödinger potential-well mechanics, and multi-scale Hessian curvature tensors, and performs candidate classification via a soft-voting ensemble of calibrated classifiers.")
    
    p_heading(doc, "Objective of the Invention", space_before=14, space_after=4)
    p_body(doc, "The primary objective of the present invention is to provide a reliable, computationally efficient, and mathematically transparent computer-implemented candidate screening system that accurately classifies 3D pulmonary nodule candidates into true nodules versus non-nodular false positives without relying on uninterpretable neural network weights.")
    p_body(doc, "Another object of the invention is to substantially suppress inter-scanner attenuation variance and slice thickness disparities across diverse CT scanner vendors by applying a Local Z-Score Interquartile Range (IQR) normalization operator directly on candidate volumetric patches.")
    p_body(doc, "A further object of the invention is to overcome juxta-vascular geometric confusion where spherical nodules attach to pulmonary blood vessels by computing multi-scale 3D Hessian curvature eigenvalues, Frangi vesselness, and blobness ratios that mathematically differentiate cylindrical vessels from spherical nodular lesions having identical Hounsfield Unit density.")
    p_body(doc, "Yet another objective of the invention is to quantify internal nodule micro-architecture and core solid density concentration using sublevel persistent homology entropy and discretized 3D Schrödinger potential-well energy eigenvalues.")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 3 (Remaining Objectives)
    # =========================================================================
    p_body(doc, "An additional objective of the invention is to engineer a compact 15-dimensional feature space requiring zero learnable parameters during extraction, eliminating backpropagation overfitting on hardware artifacts and achieving execution latencies under 25 milliseconds per candidate patch on standard central processing units.")
    p_body(doc, "Finally, the invention aims to provide a calibrated Soft-Voting Ensemble combining Support Vector Machines, Random Forest, and XGBoost to deliver reliable posterior nodule candidate probabilities accompanied by explicit, closed-form geometrical and physical feature attributions.")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 4 (Background of the Invention)
    # =========================================================================
    p_heading(doc, "Background of the Invention", space_before=0, space_after=6)
    p_body(doc, "Lung cancer is the leading cause of cancer-related mortality globally, responsible for over 1.8 million deaths annually. Early identification and prompt clinical management of solitary pulmonary nodules (small round or oval lesions in the lung parenchyma) in 3D Thoracic Computed Tomography (CT) scans is critical for timely surgical intervention, potentially increasing patient five-year survival rates from under 15% to over 65%.")
    p_body(doc, "In typical lung cancer screening workflows, computerized candidate detectors identify hundreds of suspicious volumetric locations across a thoracic scan. A subsequent candidate classification stage must reliably classify each candidate patch as either a true nodule or an anatomical false positive such as a vascular bifurcation, apical pleural thickening, or parenchymal scar tissue.")
    p_body(doc, "Conventional screening workflows rely heavily on manual visual inspection by certified radiologists. However, modern multi-detector CT scanners generate between 300 and 700 thin axial slices per thoracic scan. Reviewing such massive volumetric datasets is labor-intensive, costly, subject to substantial inter-observer disagreement, and inherently prone to diagnostic fatigue when examining large screening cohorts.")
    p_body(doc, "Automated computer vision systems based on machine learning have been investigated to assist radiologists. Nonetheless, existing automated approaches exhibit critical technical limitations. First, traditional radiomic methods relying on Gray-Level Co-Occurrence Matrix (GLCM) texture descriptors and first-order intensity statistics are highly sensitive to scanner vendor parameters, slice thickness (e.g., 0.5 mm vs. 2.5 mm), and tube current, resulting in significant cross-site performance degradation.")
    p_body(doc, "Second, deep learning architectures (such as 3D ResNets, 3D DenseNets, and 3D Vision Transformers) deploy tens of millions of learnable parameters (~11.2M to 86.0M weights). These networks operate as uninterpretable black boxes lacking transparent physical justifications, precluding clinical trust by practicing radiologists while frequently overfitting hardware-specific scanner noise on medical cohorts.")
    p_body(doc, "Third, conventional models fail to handle juxta-vascular nodules—nodules physically anchored to pulmonary blood vessels. Because both soft-tissue nodules and blood vessels exhibit identical Hounsfield Unit (HU) attenuation ranges, intensity-based methods trigger high false-positive misclassification rates at vascular bifurcations.")
    p_body(doc, "The present invention addresses these technical shortcomings by providing an integrated, deterministic biophysical system that combines Local Z-Score IQR contrast normalization, zero-parameter topological homology and Schrödinger density-well mechanics, multi-scale 3D Hessian curvature geometry, and a calibrated Soft-Voting Ensemble.")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 5 (Summary of the Invention & Detailed Description Sec 1)
    # =========================================================================
    p_heading(doc, "Summary of the Invention", space_before=0, space_after=6)
    p_body(doc, "The present invention provides an automated computer-implemented system and method, designated TQ-BioNet, that accurately classifies pulmonary nodule candidates in 3D Thoracic Computed Tomography (CT) volumes through the integration of deterministic biophysical feature extraction with ensemble machine learning.")
    p_body(doc, "A volumetric CT preprocessing unit resamples input 3D CT scans to an isotropic 1.0 mm³ voxel spacing, extracts standardized 32×32×32 mm³ candidate volumes of interest centered on anatomical candidate coordinates, and applies an adaptive Local Z-Score Interquartile Range (IQR) normalization operator to substantially suppress cross-scanner attenuation drift and vendor-specific contrast variations.")
    p_body(doc, "A zero-trainable-parameter biophysical feature extraction engine computes a 15-dimensional frozen feature representation combining Topological Data Analysis (persistent entropy H₀, total 0D persistence, first Betti loop numbers β₁, and 1D persistence), discretized 3D Schrödinger potential-well mechanics (ground-state energy E₀ and excited states E₁, E₂ capturing core density concentration and decay), multi-scale 3D Hessian differential geometry (Frangi vesselness filter V_σ, 3D blobness curvature ratio R_B, and principal eigenvalues λᵢ), and 3D fractal lacunarity.")
    p_body(doc, "A calibrated Soft-Voting Ensemble classification engine combining Support Vector Machines (SVM), Random Forest, and XGBoost gradient-boosted decision trees processes the standardized 15-dimensional vector, outputting a calibrated posterior nodule candidate probability, a juxta-vascular false-positive filter, and an explainable feature attribution report executing in less than 25 milliseconds per candidate patch.")
    
    p_heading(doc, "Detailed Description of the Invention", space_before=14, space_after=4)
    p_body(doc, "The present invention relates to an AI-powered biophysical clinical screening system. The overall architecture of the system is illustrated in Figure 1. The system comprises a presentation layer, a volumetric CT preprocessing pipeline, a deterministic biophysical feature extraction engine, a soft-voting ensemble classifier, and a clinical triage output layer. Each component is detailed below.")
    
    p_heading(doc, "1. Overall System Architecture", space_before=10, space_after=4)
    p_body(doc, "The system architecture includes an interactive clinical dashboard interface, a Python Flask REST API backend, a SimpleITK volumetric medical imaging pipeline, an analytical NumPy and SciPy numerical solver, and a SQLite database managed through SQLAlchemy. The client interface provides a diagnostic dashboard enabling clinicians to input CT volume paths, candidate coordinates (x, y, z), and view interactive nodule candidate probabilities, multi-scale curvature visualizations, and feature contribution charts. Rigorous input validation verifies file format integrity (.mhd, .raw, DICOM) and validates coordinate bounds against CT image dimensions.")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 6 (Detailed Description Sec 2 & 3 - Added Discretization Stencil)
    # =========================================================================
    p_heading(doc, "2. Volumetric Preprocessing and Local Contrast Normalization Pipeline", space_before=0, space_after=4)
    p_body(doc, "To resolve substantial attenuation variances and slice thickness disparities across diverse clinical CT scanner manufacturers (e.g., GE Medical Systems, Siemens, Philips), the system resamples 3D thoracic CT scans to an isotropic 1.0×1.0×1.0 mm³ resolution using 3D B-spline spatial interpolation. A 32×32×32 mm³ candidate volumetric patch I is extracted centered on each candidate location.")
    p_body(doc, "Local contrast standardization is executed using an adaptive Local Z-Score Interquartile Range (IQR) normalization operator to each input candidate patch I:")
    p_formula(doc, "I_normalized = ( I − Median(I) ) / ( IQR(I) + 10⁻⁶ )")
    p_body(doc, "where Median(I) represents the 50th percentile of voxel Hounsfield Units within the candidate patch, and IQR(I) represents the difference between the 75th and 25th percentiles. This formulation substantially suppresses scanner-specific contrast drift and baseline attenuation shifts without retraining or fine-tuning.")
    
    p_heading(doc, "3. Biophysical Feature Extraction and Relational TQ-BioNet Engine", space_before=14, space_after=4)
    p_body(doc, "Unlike conventional deep learning methods that optimize millions of data-driven convolution kernels, the present invention constructs a 15-dimensional frozen feature space x ∈ ℝ¹⁵ parameterized by four zero-trainable-parameter mathematical engines:")
    p_body(doc, "The Topological Homology Engine models the candidate volume through sublevel-set persistent filtration. The system computes the persistent entropy H₀ = −∑ pᵢ log₂(pᵢ) capturing microstructural spatial heterogeneity, the total persistence length of zero-dimensional connected components Ptot_H₀, the first Betti number β₁ quantifying 1D topological loops and tunnels, and the total 1D loop persistence Ptot_H₁.")
    p_body(doc, "The Schrödinger Density-Well Physics Engine models normalized voxel attenuation as an inverted quantum potential well V(r) = −I_normalized(r). The continuous Hamiltonian Ĥ = −(ℏ²/2m)∇² + V(r) is discretized over the 32×32×32 grid using a standard 7-point finite-difference Laplacian stencil:")
    p_formula(doc, "∇²ψ(x,y,z) ≈ [ψ(x+1) + ψ(x-1) + ψ(y+1) + ψ(y-1) + ψ(z+1) + ψ(z-1) − 6ψ(x,y,z)] / h²")
    p_body(doc, "subject to zero Dirichlet boundary conditions ψ|∂Ω = 0 on bounding box Ω. The lowest three algebraic eigenvalues (E₀, E₁, E₂) are solved using an iterative Arnoldi sparse solver, directly quantifying core solid density concentration, asymmetry, and radial spatial decay.")
    p_body(doc, "The 3D Hessian Differential Geometry Engine computes the 3D Hessian matrix of second spatial derivatives across Gaussian scales σ ∈ {1.0, 1.5, 2.0} mm. Eigenvalues |λ₁| ≤ |λ₂| ≤ |λ₃| yield the multi-scale Frangi vesselness filter V_σ measuring tubular structures, and the 3D Blobness curvature ratio R_B = |λ₁| / √(|λ₂ λ₃|) measuring spherical nodule geometry, mathematically suppressing juxta-vascular blood vessel branches. Fractal complexity is captured via the 3D Hausdorff box-counting fractal dimension D_F and multi-scale lacunarity statistics (Lac₄, Lac₈).")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 7 (Detailed Description Sec 4 & 5 - Candidate Probability)
    # =========================================================================
    p_heading(doc, "4. Soft-Voting Ensemble Classifier and Diagnostic Risk Head", space_before=0, space_after=4)
    p_body(doc, "To ensure robust diagnostic discrimination, the 15-dimensional feature representation is normalized using a StandardScaler fitted strictly on training cohort data. The normalized vector is classified by a Soft-Voting Ensemble combining three diverse non-deep-learning classifiers. A calibrated soft-voting formulation computes the ensemble posterior nodule probability:")
    p_formula(doc, "P(Y = 1 | x) = w₁ · P_SVM(Y = 1 | x) + w₂ · P_XGB(Y = 1 | x) + w₃ · P_RF(Y = 1 | x)")
    p_body(doc, "where P_SVM is generated by a Support Vector Classifier with Radial Basis Function (RBF) kernel (C=10, gamma='scale'), P_XGB is generated by an XGBoost gradient-boosted decision tree ensemble (n_estimators=300, max_depth=6), and P_RF is generated by a Random Forest classifier (n_estimators=300, max_features='sqrt'). Diagnostic predictions are obtained by thresholding at τ = 0.50.")
    
    p_heading(doc, "5. Working of the Invention", space_before=14, space_after=4)
    p_body(doc, "During operational inference, as illustrated in Figure 1, the clinical practitioner inputs the patient CT volume and candidate coordinates. The system validates file integrity and isotropic dimensions. The candidate volumetric patch is sliced and normalized using the Local Z-Score IQR operator. Concurrently, the 15-dimensional biophysical feature vector is computed by solving the persistent homology filtration, 3D Schrödinger eigenvalue equations, 3D Hessian curvature tensors, and fractal lacunarity.")
    p_body(doc, "The extracted 15-dimensional feature vector is fed to the pre-fitted Soft-Voting Ensemble, outputting a calibrated nodule candidate probability score. If the probability exceeds 0.50, the candidate is classified as a confirmed pulmonary nodule candidate; otherwise, it is categorized as a benign non-nodule false positive. Multi-scale Frangi vesselness flags juxta-vascular vessel attachments, and runtime latency is recorded.")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 8 (Benefits of the Invention & Claims 1, 2)
    # =========================================================================
    p_heading(doc, "6. Benefits of the Invention", space_before=0, space_after=4)
    p_body(doc, "The present invention delivers major technical and clinical advantages over existing diagnostic tools:")
    p_body(doc, "Provides explicit, closed-form geometrical and physical feature attributions for all 15 features, enabling practicing radiologists to understand the rationale behind every automated decision.", bold_lead="Explicit Feature Interpretability: ")
    p_body(doc, "Feature extraction contains zero learnable weights (W = 0), avoiding backpropagation overfitting on hardware artifacts and eliminating GPU infrastructure dependencies.", bold_lead="Zero-Parameter Feature Extractor: ")
    p_body(doc, "Local Z-Score IQR normalization standardizes contrast across multi-vendor CT scanners, substantially suppressing out-of-distribution performance collapse.", bold_lead="Hardware & Contrast Invariance: ")
    p_body(doc, "Frangi vesselness and Blobness ratios mathematically separate spherical lesions from tubular vessels, drastically cutting false alarms at vascular bifurcations.", bold_lead="Juxta-Vascular Disambiguation: ")
    p_body(doc, "Achieves 86.29% accuracy, 90.71% specificity, and 0.9198 AUC on independent LUNA16 validation (Subsets 6–9, N = 926). In zero-shot cross-center evaluation on the European LNDb cohort featuring thicker slices (1.25–2.5 mm, N = 248), the framework maintained 72.98% accuracy and 81.96% specificity in rejecting false alarms.", bold_lead="Cross-Center Robustness & Reality Check: ")
    p_body(doc, "Total feature extraction requires only 24.52 ms and classifier inference requires 0.0734 ms per candidate patch, enabling instantaneous screening on standard hospital workstations.", bold_lead="Real-Time Clinical Execution: ")
    
    p_heading(doc, "Claims", space_before=14, space_after=4)
    p_body(doc, "We claim:", space_after=4)
    p_body(doc, "1. A computer-implemented image-processing system for candidate-level pulmonary nodule discrimination on 3D thoracic computed tomography (CT), the system comprising: a volumetric CT preprocessing module configured to ingest a 3D thoracic CT volume, extract an isotropic candidate patch centered on anatomical coordinates of a candidate lesion, and normalize voxel intensities using a local median and interquartile range (IQR) operator; a deterministic, zero-trainable-parameter biophysical feature extraction module configured to compute a 15-dimensional feature representation from the normalized candidate patch, the module comprising: a topological data analysis (TDA) unit configured to compute sublevel persistent entropy (H₀), zero-dimensional persistence, first Betti loop numbers (β₁), and one-dimensional persistence; a density-well physics unit configured to model voxel attenuation as an inverted quantum potential well and solve a discretized 3D Schrödinger Hamiltonian eigenvalue equation using a 7-point finite-difference stencil to obtain energy eigenvalues (E₀, E₁, E₂); a multi-scale 3D Hessian differential geometry unit configured to calculate principal Hessian eigenvalues (λ₁, λ₂, λ₃), a multi-scale Frangi vesselness filter response (V_σ), and a 3D blobness ratio (R_B); a structural fractal complexity unit configured to compute 3D box-counting fractal dimension (D_F) and lacunarity statistics; and a calibrated ensemble classification head configured to process the 15-dimensional feature representation and output a calibrated posterior probability classifying the candidate patch as either a true pulmonary nodule or a non-nodule false positive.")
    p_body(doc, "2. The system as claimed in claim 1, wherein the volumetric CT preprocessing module is configured to execute Local Z-Score IQR normalization defined by I_normalized = ( I − Median(I) ) / ( IQR(I) + 10⁻⁶ ), wherein cross-scanner attenuation drift and vendor-specific contrast variations are suppressed without re-training model weights; and wherein the volumetric")
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 9 (Claims 2 contd, 3, 4, 5 & Sheet 1 Footer Table)
    # =========================================================================
    p_body(doc, "preprocessing module executes isotropic 3D spatial resampling to eliminate orientation and aspect ratio distortion across disparate CT reconstruction kernels and slice thicknesses ranging from 0.5 mm to 2.5 mm.", space_before=0, space_after=6)
    p_body(doc, "3. The system as claimed in claim 1, wherein the density-well physics unit models localized tissue attenuation as an inverted potential energy function V(r) = −I_normalized(r), and wherein the discretized Hamiltonian is solved under zero Dirichlet boundary conditions such that the ground-state eigenvalue E₀ and excited-state eigenvalues E₁, E₂ quantify central solid core density concentration and radial decay profiles.")
    p_body(doc, "4. The system as claimed in claim 1, wherein the multi-scale 3D Hessian differential geometry unit calculates second-order spatial partial derivatives across scales σ ∈ {1.0, 1.5, 2.0} mm, and wherein the multi-scale Frangi vesselness filter V_σ and blobness ratio R_B explicitly suppress juxta-vascular blood vessel bifurcations having identical Hounsfield Unit density to pulmonary nodules.")
    p_body(doc, "5. The system as claimed in claim 1, further comprising: a Soft-Voting Ensemble classification head combining probability outputs from a Support Vector Machine (SVM) with radial basis function (RBF) kernel, an XGBoost gradient-boosted decision tree, and a Random Forest classifier; and a decision support engine configured to output calibrated nodule candidate probabilities, feature attribution rankings, and automated candidate triage reports with a processing latency of less than 25 milliseconds per candidate patch.", space_after=140)
    
    add_sig_table(doc, sheet_num=1, total_sheets=2)
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 10 (Figure 1 System Architecture Diagram & Sheet 2 Footer Table)
    # =========================================================================
    p_heading(doc, "Figure 1 System Architecture Diagram", space_before=0, space_after=8)
    
    fig_path = r"c:\Users\suraj\Desktop\4th yr project\patent_fig1_architecture.png"
    if os.path.exists(fig_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(8)
        r_img = p_img.add_run()
        r_img.add_picture(fig_path, width=Inches(6.4))
        
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(0)
    p_sp.paragraph_format.space_after = Pt(20)
    
    add_sig_table(doc, sheet_num=2, total_sheets=2)
    
    doc.add_page_break()
    
    # =========================================================================
    # PAGE 11 (Abstract)
    # =========================================================================
    p_heading(doc, "Abstract", space_before=0, space_after=8)
    p_body(doc, "TQ-BioNet is a computer-implemented image-processing system and method that provides accurate candidate-level classification of pulmonary nodules on 3D Thoracic Computed Tomography (CT) volumes by jointly reasoning over spatial structural topology, quantum-inspired tissue density wells, and differential geometric curvatures. A volumetric preprocessing unit implements isotropic 1.0 mm³ spatial resampling and Local Z-Score Interquartile Range (IQR) normalization to eliminate inter-scanner contrast drift across disparate scanner manufacturers and slice thicknesses. A deterministic, zero-trainable-parameter biophysical feature extraction engine computes a 15-dimensional feature representation combining sublevel persistent homology (H₀, β₁) from Topological Data Analysis (TDA), discretized 3D Schrödinger potential-well energy eigenvalues (E₀, E₁, E₂) modeling central solid core density localization, multi-scale 3D Hessian differential curvature tensors (Frangi vesselness V_σ, 3D blobness R_B, principal eigenvalues λᵢ) suppressing juxta-vascular blood vessel false positives, and 3D fractal lacunarity. A calibrated Soft-Voting Ensemble classification head combining Support Vector Machines, Random Forest, and XGBoost gradient-boosted trees outputs calibrated posterior nodule candidate probabilities. Evaluated on 926 patient-disjoint held-out validation candidate patches from the benchmark LUNA16 archive, the system achieves 86.29% accuracy, 90.71% specificity, 0.9198 AUC-ROC, and retains 72.98% accuracy and 81.96% specificity on external thick-slice CT scans with a runtime of 24.52 milliseconds on standard CPU hardware.")
    
    out_path = r"c:\Users\suraj\Desktop\4th yr project\TQ_BioNet_Patent_Form2_Complete_Specification.docx"
    doc.save(out_path)
    print("Exact 11-page matching Patent Document recompiled successfully at:", out_path)

if __name__ == "__main__":
    build()
