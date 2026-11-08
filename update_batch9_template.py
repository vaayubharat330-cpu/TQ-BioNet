import os
import pptx

def main():
    src_path = r'C:\Users\suraj\AppData\Local\Packages\5319275A.51895FA4EA97F_cv1g1gvanyjgm\LocalState\sessions\6FD5C0FDAB681BD5E60C2436F602390ADBD69EE3\transfers\2026-31\Batch-9 PPT.pptx'
    out_path = r'c:\Users\suraj\Desktop\4th yr project\TQ-BioNet_v3_Batch9_Template.pptx'
    
    prs = pptx.Presentation(src_path)
    
    # ---------------- SLIDE 1: Title Slide ----------------
    s1 = prs.slides[0]
    for shape in s1.shapes:
        if shape.has_text_frame:
            txt = shape.text_frame.text
            if 'AUTOMATED STOCK PRICE' in txt or 'TQ-BioNet' in txt or 'T-BioNet' in txt:
                shape.text_frame.text = (
                    "TQ-BioNet: Lung Nodule Classification on Thoracic CT\n"
                    "Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry"
                )
            elif 'Supervisor' in txt:
                shape.text_frame.text = "Supervisor\nMr. Mohd Anwar Ali\n(Assistant Professor)\nIT Department\n"
            elif 'Team Members:' in txt:
                shape.text_frame.text = "Team Members:"
                
        if shape.has_table:
            table = shape.table
            for r_idx in range(len(table.rows)):
                if r_idx == 0:
                    table.cell(0, 0).text = "Roll No"
                    table.cell(0, 1).text = "Name"
                elif r_idx == 1:
                    table.cell(1, 0).text = "23R21A12J7"
                    table.cell(1, 1).text = "V. SURAJ"
                else:
                    table.cell(r_idx, 0).text = ""
                    table.cell(r_idx, 1).text = ""

    # ---------------- SLIDE 2: Contents ----------------
    s2 = prs.slides[1]
    for shape in s2.shapes:
        if shape.has_text_frame and 'CONTENTS' not in shape.text_frame.text:
            shape.text_frame.text = "Abstract\nIntroduction\nProject Title Justification\nExisting System & Disadvantages\nProposed System & Advantages\nObjectives\nScope\nBasic Concepts"

    # ---------------- SLIDE 3: Abstract ----------------
    s3 = prs.slides[2]
    for shape in s3.shapes:
        if shape.has_text_frame and 'Abstract' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Early diagnosis of pulmonary nodules in Thoracic Computed Tomography (CT) scans plays a vital role in improving lung cancer screening outcomes and overall patient prognosis. However, traditional radiomic texture descriptors remain highly sensitive to scanner noise and Hounsfield Unit (HU) contrast variations, while modern deep learning architectures function as opaque black boxes that require massive computational resources and tend to overfit on small clinical cohorts. To address these challenges, this project introduces TQ-BioNet, a mathematically explainable framework combining Topological Data Analysis (TDA), Density Well Physics, and Multi-Scale Differential Geometry for automated nodule classification.\n\n"
                "The framework applies Local Z-Score Interquartile Range (IQR) normalization to eliminate cross-scanner contrast drift. A 15-dimensional frozen feature space is constructed, integrating Persistent Entropy and 1D loop counts for tissue connectivity, discretized 3D Schrödinger potential energy eigenvalues for density wells, and Hessian curvature tensors (Frangi Vesselness & Blobness) for separating nodules from blood vessels. Trained on LUNA16 Subsets 0–5 (1,446 samples) and evaluated on independent Subsets 6–9 (926 samples), the Voting Ensemble model achieved a peak AUC-ROC of 0.9266, an accuracy of 86.43%, and a specificity of 92.38% without uninterpretable neural networks."
            )

    # ---------------- SLIDE 4: Introduction ----------------
    s4 = prs.slides[3]
    for shape in s4.shapes:
        if shape.has_text_frame and 'Introduction' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Lung cancer remains one of the primary causes of global cancer mortality, where early identification of small pulmonary nodules in Thoracic Computed Tomography (CT) scans is crucial for increasing five-year patient survival rates. However, manual screening by radiologists is labor-intensive, time-consuming, and subject to inter-observer variability due to subtle intensity variations across CT scans.\n\n"
                "This project proposes TQ-BioNet, a novel computer-aided diagnosis framework that combines Topological Homology, Density Well Physics, and 3D Hessian Geometry to classify pulmonary nodules. The model applies isotropic voxel resampling, Local Z-Score Interquartile Range (IQR) normalization, 15-dimensional frozen feature extraction, and ensemble learning (SVM + XGBoost) to achieve high diagnostic precision, cross-scanner invariance, and 100% mathematical explainability."
            )

    # ---------------- SLIDE 5: Project Title Justification ----------------
    s5 = prs.slides[4]
    for shape in s5.shapes:
        if shape.has_text_frame and 'Project Title Justification' not in shape.text_frame.text:
            shape.text_frame.text = (
                "The title 'TQ-BioNet: Lung Nodule Classification on Thoracic CT — Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry' accurately reflects the primary technical innovations and mathematical foundations of the research:\n\n"
                "• Topological Homology: Incorporates Persistent Homology invariants (Persistent Entropy H0, 1D loop count β1, and Total Persistence) to capture multi-scale tissue structural connectivity and vascular cavities.\n"
                "• Density Well Physics: Solves discretized 3D potential-well Schrödinger Hamiltonian equations (Hψ = Eψ) to extract energy eigenvalues (E0, E1, E2) modeling nodule density wells.\n"
                "• 3D Hessian Geometry: Uses multi-scale 3D Hessian eigenvalues (Frangi Vesselness Vσ and Blobness RB) and Box-Counting Fractal Dimensions (DF) to discriminate spherical nodules from linear blood vessels.\n"
                "• Frozen Framework: Applies Local Z-Score IQR normalization with zero trainable parameters in feature extraction, guaranteeing zero scanner-noise overfitting and full cross-scanner generalization."
            )

    # ---------------- SLIDE 6: Existing System & Disadvantages ----------------
    s6 = prs.slides[5]
    for shape in s6.shapes:
        if shape.has_text_frame and 'Existing System' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Existing System:\n"
                "Traditional Radiomics and GLCM texture models.\n"
                "3D Deep Convolutional Neural Networks (3D ResNet / U-Net).\n\n"
                "Disadvantages:\n"
                "Existing models fail to handle cross-scanner contrast drift and slice thickness variations.\n"
                "Deep learning architectures function as opaque black boxes lacking clinical explainability.\n"
                "Massive parameter models increase the risk of overfitting to hardware-specific noise.\n"
                "Intensity-based methods struggle to separate spherical nodules from attached blood vessels.\n"
                "Many previous studies do not establish a comprehensive set of invariant biophysical features."
            )

    # ---------------- SLIDE 7: Proposed System & Advantages ----------------
    s7 = prs.slides[6]
    for shape in s7.shapes:
        if shape.has_text_frame and 'Proposed System' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Proposed System:\n"
                "The proposed system introduces a TQ-BioNet feature engineering framework for pulmonary nodule classification. It standardizes CT voxel intensities and extracts a 15-dimensional frozen feature space using Voting Ensemble classifiers to evaluate diagnostic risk.\n\n"
                "Advantages:\n"
                "Improves nodule classification accuracy and specificity.\n"
                "Captures topological connectivity, density wells, and spatial curvature simultaneously.\n"
                "Provides 100% mathematically explainable predictions.\n"
                "Eliminates scanner-noise overfitting using a zero-parameter feature extractor.\n"
                "Achieves consistent high performance across independent validation test cohorts."
            )

    # ---------------- SLIDE 8: Objectives ----------------
    s8 = prs.slides[7]
    for shape in s8.shapes:
        if shape.has_text_frame and 'Objectives' not in shape.text_frame.text:
            shape.text_frame.text = (
                "• To standardize CT voxel intensities across scanner vendors using Local Z-Score IQR normalization.\n"
                "• To extract persistent homology invariants (H0, β1, Ptot) for modeling tissue structural connectivity and vascular cavities.\n"
                "• To formulate a discretized 3D Schrödinger Hamiltonian operator to compute potential-well energy eigenvalues (E0, E1, E2).\n"
                "• To apply multi-scale 3D Hessian differential geometry (Frangi Vesselness Vσ and Blobness RB) to resolve juxta-vascular blood vessel ambiguity.\n"
                "• To build a 15-dimensional frozen feature space with zero trainable parameters to prevent scanner-noise overfitting.\n"
                "• To evaluate the framework across independent validation cohorts (Subsets 6–9) to guarantee zero data leakage."
            )

    # ---------------- SLIDE 9: Scope ----------------
    s9 = prs.slides[8]
    for shape in s9.shapes:
        if shape.has_text_frame and 'Scope' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Prediction & Scope:\n"
                "• Target Domain: Automated classification of pulmonary nodule candidates on 3D thoracic CT scans (LUNA16 dataset, Subsets 0–9).\n"
                "• Preprocessing & Features: Isotropic 1.0mm voxel resampling, 32x32x32 patch extraction, Local Z-Score IQR normalization, and 15D frozen feature extraction (Topology + Density Wells + Differential Geometry).\n"
                "• Classifier Evaluation: Supervised ensemble classification (SVM, XGBoost, Voting Ensemble) evaluated across independent test cohorts (Subsets 6–9).\n\n"
                "Out of Scope / Future Work:\n"
                "• Full-body organ segmentation and black-box 3D convolutional neural networks (excluded to maintain 100% explainability).\n"
                "• Invasive clinical biopsy reports and genomic sequencing data.\n"
                "• Future work may explore 3D topological persistence diagrams and multi-modal clinical metadata integration."
            )

    # ---------------- SLIDE 10: Basic Concepts ----------------
    s10 = prs.slides[9]
    for shape in s10.shapes:
        if shape.has_text_frame and 'Basic Concepts' not in shape.text_frame.text:
            shape.text_frame.text = (
                "Topological Homology (TDA)\n"
                "Computes persistent homology, Betti numbers (β0, β1), and Persistent Entropy across intensity filtration levels to capture tissue structural connectivity.\n\n"
                "Density Well Physics\n"
                "Solves discretized 3D potential-well Schrödinger Hamiltonian equations (Hψ = Eψ) to extract energy eigenvalues (E0, E1, E2) modeling nodule density wells.\n\n"
                "3D Hessian Geometry\n"
                "Evaluates 3D curvature eigenvalues to compute Frangi Vesselness and Blobness ratios for separating nodules from blood vessels.\n\n"
                "Local Z-Score IQR Normalization\n"
                "Standardizes CT voxel intensities using median and interquartile range to eliminate cross-scanner Hounsfield Unit contrast drift.\n\n"
                "Voting Ensemble Learning\n"
                "Combines probability predictions from Support Vector Machines (SVM) and XGBoost for robust final decision-making."
            )

    # Save output
    prs.save(out_path)
    print(f"Successfully updated presentation to final title at: {out_path}")

if __name__ == "__main__":
    main()
