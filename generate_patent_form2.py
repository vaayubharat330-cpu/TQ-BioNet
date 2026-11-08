import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def add_hr(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(6)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'),   'single')
    bottom.set(qn('w:sz'),    '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '1A365D')
    pBdr.append(bottom)
    pPr.append(pBdr)

def p_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(4)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0, 32, 96)

def p_sec_hdr(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after  = Pt(4)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = RGBColor(16, 44, 87)

def p_sub_hdr(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(2)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(10.5)
    r.font.bold = True

def p_body(doc, text, indent=False, justify=True):
    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.line_spacing = Pt(13)
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.25)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(10)

def p_bullet(doc, text, bold_title=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before     = Pt(1)
    p.paragraph_format.space_after      = Pt(3)
    p.paragraph_format.left_indent       = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    r_b = p.add_run("• ")
    r_b.font.name = "Times New Roman"
    r_b.font.size = Pt(10)
    if bold_title:
        r_bt = p.add_run(bold_title + " ")
        r_bt.font.name = "Times New Roman"
        r_bt.font.size = Pt(10)
        r_bt.font.bold = True
    r_t = p.add_run(text)
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(10)

def p_claim(doc, num, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before     = Pt(4)
    p.paragraph_format.space_after      = Pt(4)
    p.paragraph_format.left_indent       = Inches(0.3)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    r_n = p.add_run(f"{num}. ")
    r_n.font.name = "Times New Roman"
    r_n.font.size = Pt(10)
    r_n.font.bold = True
    r_t = p.add_run(text)
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(10)

def build_patent_form2():
    doc = docx.Document()

    for sec in doc.sections:
        sec.page_width    = Inches(8.5)
        sec.page_height   = Inches(11.0)
        sec.top_margin    = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin   = Inches(1.0)
        sec.right_margin  = Inches(1.0)

    # COVER / FORM-2 HEADER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("FORM-2\nTHE PATENTS ACT, 1970\n(39 OF 1970)\nAND\nTHE PATENTS RULES, 2003\n(As Amended)\n\nCOMPLETE SPECIFICATION\n(SECTION 10, RULE 13)")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)
    r.font.bold = True

    add_hr(doc)

    p_sec_hdr(doc, "TITLE OF THE INVENTION")
    p_body(doc, "A DETERMINISTIC ZERO-PARAMETER BIOPHYSICAL SYSTEM AND METHOD FOR 3D THORACIC CT PULMONARY NODULE CLASSIFICATION USING TOPOLOGICAL HOMOLOGY, DENSITY-WELL MECHANICS, AND MULTI-SCALE HESSIAN GEOMETRY (TQ-BioNet)", justify=False)

    p_sec_hdr(doc, "APPLICANT(S)")
    p_body(doc, "Students of Research & Development Faculty, Department of Information Technology, MLR Institute of Technology, Dundigal, Hyderabad, Telangana – 500043, India and Indian Nationals.")
    p_body(doc, "Student Innovators & Co-Inventors:\n1. Veludandi Suraj (Roll No: 23R21A12J7)\n2. Thatipalli Vijay Durga (Roll No: 23R21A12J4)\n3. Patnam Sathwik (Roll No: 23R21A12H2)\n4. Tanneru Koushal Kumar (Roll No: 23R21A12J2)")
    p_body(doc, "Faculty Supervisor & Lead Inventor:\nCh. Upender Rao, Assistant Professor, Department of Information Technology, MLR Institute of Technology, Hyderabad, Telangana, India.")

    p_body(doc, "The appended specification particularly describes the invention and the manner in which it is to be performed.", indent=True)

    doc.add_page_break()

    # SPECIFICATION BODY
    p_title(doc, "A DETERMINISTIC ZERO-PARAMETER BIOPHYSICAL SYSTEM AND METHOD FOR 3D THORACIC CT PULMONARY NODULE CLASSIFICATION USING TOPOLOGICAL HOMOLOGY, DENSITY-WELL MECHANICS, AND MULTI-SCALE HESSIAN GEOMETRY (TQ-BioNet)")
    add_hr(doc)

    p_sec_hdr(doc, "FIELD OF THE INVENTION")
    p_body(doc, "The present invention relates generally to artificial intelligence-based medical imaging diagnostics, computer-aided candidate screening (CAD), and biophysical computational modeling. More specifically, the invention relates to an explainable, hardware-invariant, zero-trainable-parameter computer-aided system and method for discriminating true pulmonary nodules from anatomical false positives (such as juxta-vascular blood vessel bifurcations, apical pleural scarring, and parenchymal atelectasis) within 3D Thoracic Computed Tomography (CT) volumes.")

    p_sec_hdr(doc, "BACKGROUND OF THE INVENTION AND PRIOR ART")
    p_body(doc, "Pulmonary nodule screening in 3D Thoracic Computed Tomography (CT) is the critical initial stage in computer-aided early detection of lung cancer, the leading cause of worldwide cancer-related mortality. Following volumetric candidate detection across isotropic CT scans, clinical CAD systems must classify candidate anatomical volumes of interest into true nodular lesions versus non-nodular false-positive structures.")
    p_body(doc, "However, existing automated CAD pipelines suffer from three severe technological limitations:")
    p_bullet(doc, "Solitary spherical nodules frequently attach to or grow contiguous with pulmonary blood vessels. Because blood vessels and soft-tissue nodules exhibit identical Hounsfield Unit (HU) radiological density ranges, conventional intensity-based and first-order statistical radiomic descriptors generate excessive false-positive alarms at vascular bifurcations.", "1. Juxta-Vascular Geometric Ambiguity:")
    p_bullet(doc, "Recent deep learning methodologies (such as 3D Convolutional Neural Networks, 3D ResNets, 3D DenseNets, and 3D Vision Transformers) deploy tens of millions of learnable weights (~11.2M to 86.0M parameters). These networks operate as uninterpretable black boxes lacking transparent physical justifications, precluding clinical trust by practicing thoracic radiologists and overfitting scanner-specific noise.", "2. Black-Box Opacity & Excessive Parameterization:")
    p_bullet(doc, "Inter-hospital variations in CT scanner vendors (e.g., GE, Siemens, Philips), slice thickness (0.5 mm to 2.5 mm), tube current, and reconstruction kernels cause severe shifts in attenuation histograms, drastically degrading deep-learning accuracy during multi-center deployment.", "3. Cross-Scanner Contrast and Hardware Drift:")

    p_sec_hdr(doc, "OBJECTIVES OF THE INVENTION")
    p_bullet(doc, "To provide a deterministic, mathematically transparent, and zero-trainable-parameter biophysical system (TQ-BioNet) that accurately classifies 3D thoracic CT pulmonary nodule candidates.", "Primary Objective:")
    p_bullet(doc, "To eliminate cross-scanner attenuation and contrast variations across disparate CT scanner vendors and slice thicknesses using an adaptive Local Z-Score Interquartile Range (IQR) normalization pipeline.", "Secondary Objective:")
    p_bullet(doc, "To overcome juxta-vascular false positives by integrating multi-scale 3D Hessian curvature eigenvalues, Frangi vesselness, and Blobness ratios to mathematically distinguish cylindrical blood vessels from spherical nodules.", "Third Objective:")
    p_bullet(doc, "To capture structural tissue micro-heterogeneity and core density localization using sublevel persistent entropy (H0), 1D topological loop counts (beta_1), and discretized 3D Schrödinger potential-well energy eigenvalues (E0, E1, E2).", "Fourth Objective:")
    p_bullet(doc, "To construct a compact, highly discriminatory 15-dimensional frozen feature representation that executes in under 25 ms per candidate volume on standard CPU hardware.", "Fifth Objective:")

    doc.add_page_break()

    p_sec_hdr(doc, "SUMMARY OF THE INVENTION")
    p_body(doc, "The present invention provides an explainable computer-implemented system and method, designated TQ-BioNet, for automated pulmonary nodule candidate classification in 3D Thoracic CT scans.")
    p_body(doc, "The system comprises: (a) an adaptive preprocessing engine that resamples CT volumes to 1.0 mm³ isotropic spacing, extracts 32×32×32 mm³ candidate volumes, and standardizes intensities via Local Z-Score IQR normalization; (b) a 15-dimensional zero-parameter biophysical feature extractor combining Topological Data Analysis (H0, beta_1, Ptot), discretized 3D Schrödinger potential-well energy eigenvalues (E0, E1, E2), multi-scale 3D Hessian differential geometry (Frangi vesselness, Blobness, eigenvalues), and 3D fractal lacunarity; and (c) a calibrated Soft-Voting Ensemble combining SVM, Random Forest, and XGBoost classifiers.")

    p_sec_hdr(doc, "DETAILED DESCRIPTION OF THE INVENTION")
    p_sub_hdr(doc, "1. Overall System Architecture and Pipeline")
    p_body(doc, "The system comprises an image preprocessing engine, a deterministic biophysical feature extraction pipeline, and an ensemble decision engine. 3D Thoracic CT scans (such as the 1,018 LUNA16 scans) are ingested and resampled to 1.0 mm³ isotropic resolution. Patches of 32×32×32 voxels centered on candidate coordinates are extracted and standardized using Local Z-Score IQR normalization.")

    p_sub_hdr(doc, "2. Biophysical Feature Engineering Components")
    p_body(doc, "The 15-dimensional frozen feature vector x in R^15 is composed of four deterministic mathematical sub-engines:")
    p_bullet(doc, "Features 0–3: Sublevel persistent entropy H0 = -sum(p_i * log2(p_i)), total 0D persistence Ptot_H0, 1D Betti number beta_1, and total 1D loop persistence Ptot_H1.", "• Topological Homology (TDA):")
    p_bullet(doc, "Features 4–6: Solves H_psi = E*psi with V(r) = -I_hat(r). The eigenvalues E0, E1, E2 capture core solid density concentration, asymmetry, and spatial decay.", "• Schrödinger Potential Mechanics:")
    p_bullet(doc, "Features 7–11: Principal eigenvalues (lambda_1, lambda_2, lambda_3), Frangi vesselness filter V_sigma measuring tubular structures, and Blobness ratio R_B = |lambda_1| / sqrt(|lambda_2 * lambda_3|).", "• 3D Hessian Geometry:")
    p_bullet(doc, "Features 12–14: 3D box-counting fractal dimension D_F and multi-scale lacunarity (Lac_4, Lac_8).", "• Fractal Complexity:")

    p_sub_hdr(doc, "3. Soft-Voting Ensemble Classifier and Clinical Calibration")
    p_body(doc, "The 15-dimensional vector is standardized using a StandardScaler fitted on development data and classified using a soft-voting ensemble of RBF-kernel SVM, Random Forest, and XGBoost. The calibrated probability is compared against an operating threshold tau = 0.50 to output diagnostic referral decisions.")

    doc.add_page_break()

    p_sec_hdr(doc, "BENEFITS OF THE INVENTION")
    p_bullet(doc, "Unlike black-box neural networks, every feature corresponds to an explicit physical and geometrical quantity.", "1. Complete Mathematical Explainability:")
    p_bullet(doc, "Requires zero training weights or GPU backward propagation for feature extraction, eliminating the risk of memorizing hardware-specific scanner noise.", "2. Zero-Parameter Feature Extractor (W = 0):")
    p_bullet(doc, "Achieves 86.29% Accuracy, 90.71% Specificity, and 0.9198 AUC-ROC on 926 patient-disjoint held-out validation patches.", "3. High Diagnostic Performance:")
    p_bullet(doc, "Feature extraction latency is 24.52 ms and inference latency is 0.0734 ms per candidate on standard CPU hardware.", "4. Sub-25 ms Ultra-Fast Inference:")

    p_sec_hdr(doc, "CLAIMS")
    p_body(doc, "We claim:")
    p_claim(doc, 1, "An automated computer-implemented biophysical system for 3D thoracic computed tomography (CT) pulmonary nodule candidate classification, the system comprising: a volumetric preprocessing unit configured to receive a 3D thoracic CT volume, extract an isotropic 3D candidate patch centered on anatomical coordinates of a candidate lesion, and normalize voxel intensities of the candidate patch using a local median and interquartile range (IQR) operator; a deterministic, zero-trainable-parameter biophysical feature extraction engine configured to compute a 15-dimensional feature representation from the normalized 3D candidate patch, the engine comprising: a topological data analysis (TDA) module configured to calculate sublevel persistent entropy (H0), zero-dimensional persistence, first Betti loop numbers (beta_1), and one-dimensional persistence; a density-well physics module configured to model voxel attenuation as an inverted quantum potential well and solve a discretized 3D Schrödinger Hamiltonian eigenvalue equation to obtain energy eigenvalues (E0, E1, E2); a multi-scale 3D Hessian differential geometry module configured to calculate principal Hessian eigenvalues (lambda_1, lambda_2, lambda_3), a multi-scale Frangi vesselness filter response (V_sigma), and a 3D blobness ratio (R_B); a structural fractal complexity module configured to compute 3D box-counting fractal dimension (D_F) and lacunarity statistics; and a calibrated ensemble classification engine configured to receive the 15-dimensional feature representation and output a calibrated diagnostic posterior probability classifying the candidate patch as either a true pulmonary nodule or a non-nodule false positive.")
    p_claim(doc, 2, "The system as claimed in claim 1, wherein the volumetric preprocessing unit executes Local Z-Score IQR normalization defined by I_hat = [I - Median(I)] / [IQR(I) + 1e-6], wherein cross-scanner attenuation drift and vendor-specific contrast variations are eliminated without re-training model weights.")
    p_claim(doc, 3, "The system as claimed in claim 1, wherein the density-well physics module models localized tissue attenuation as an inverted potential energy function V(r) = -I_hat(r), and wherein the ground-state eigenvalue E0 and excited-state eigenvalues E1, E2 capture central solid core density concentration and radial decay profiles.")
    p_claim(doc, 4, "The system as claimed in claim 1, wherein the 3D Hessian differential geometry module calculates second-order spatial partial derivatives across scales sigma in {1.0, 1.5, 2.0} mm, and wherein the multi-scale Frangi vesselness filter V_sigma and blobness ratio R_B explicitly suppress juxta-vascular blood vessel bifurcations having identical Hounsfield Unit density to pulmonary nodules.")
    p_claim(doc, 5, "The system as claimed in claim 1, wherein the calibrated ensemble classification engine comprises a Soft-Voting Ensemble combining probability outputs from a Support Vector Machine (SVM) with radial basis function (RBF) kernel, an XGBoost gradient-boosted decision tree, and a Random Forest classifier.")
    p_claim(doc, 6, "A computer-implemented method for 3D thoracic CT pulmonary nodule candidate classification using the system of claim 1, comprising the steps of: extracting an isotropic 32x32x32 mm³ candidate patch from a 3D thoracic CT scan; applying Local Z-Score IQR normalization to standardize local voxel attenuation; computing a 15-dimensional deterministic biophysical feature vector comprising topological persistence metrics, 3D Schrödinger potential-well energy eigenvalues, 3D Hessian curvature and vesselness values, and fractal lacunarity; and evaluating the 15-dimensional feature vector using an ensemble classifier to generate an explainable nodule diagnostic prediction with a feature extraction latency of less than 25 milliseconds per patch.")

    # SIGNATURE BLOCK
    p_body(doc, "\nLead Faculty & Lead Inventor:\nCh. Upender Rao, Assistant Professor, Department of IT, MLRIT, Hyderabad.\n\nCo-Inventors & Student Researchers:\nVeludandi Suraj (23R21A12J7)\nThatipalli Vijay Durga (23R21A12J4)\nPatnam Sathwik (23R21A12H2)\nTanneru Koushal Kumar (23R21A12J2)")

    doc.add_page_break()

    # ABSTRACT PAGE
    p_sec_hdr(doc, "ABSTRACT")
    p_body(doc, "A deterministic, zero-trainable-parameter biophysical system and method (TQ-BioNet) is disclosed for candidate-level pulmonary nodule classification on 3D Thoracic Computed Tomography (CT). To eliminate cross-scanner attenuation drift across disparate CT hardware vendors and slice thicknesses, candidate volumes of interest are preprocessed using an adaptive Local Z-Score Interquartile Range (IQR) normalization operator. A 15-dimensional frozen biophysical feature extractor combines sublevel persistent homology (H0, beta_1) from Topological Data Analysis (TDA), discretized 3D Schrödinger potential-well energy eigenvalues (E0, E1, E2) modeling tissue density traps, multi-scale 3D Hessian differential curvature tensors (V_sigma, R_B, lambda_i) suppressing juxta-vascular blood vessel false positives, and 3D fractal lacunarity. A calibrated soft-voting ensemble maps the 15-dimensional representation into a posterior malignancy probability. Evaluated on 926 patient-disjoint held-out validation patches from the LUNA16 benchmark, the system achieves 86.29% accuracy, 90.71% specificity, 0.9198 AUC-ROC, and a total runtime of 24.52 milliseconds per candidate patch on standard CPU hardware with 100% mathematical explainability.")

    out_file = r"c:\Users\suraj\Desktop\4th yr project\TQ_BioNet_Patent_Form2_Complete_Specification.docx"
    doc.save(out_file)
    print("Patent specification DOCX generated at:", out_file)

if __name__ == "__main__":
    build_patent_form2()
