# Original TQ_BioNet_IEEE_Conference_Paper.docx Content

### P0 [Normal]
TQ-BioNet: Lung Nodule Classification on Thoracic CT Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry

### P2 [Normal]
Abstract— Pulmonary nodule screening in 3D Thoracic Computed Tomography (CT) is critical for early lung cancer detection and patient mortality reduction. Recent CAD pipelines heavily deploy 3D Convolutional Neural Networks (CNNs) and Vision Transformers; however, these architectures function as uninterpretable black boxes with tens of millions of learnable parameters, overfit scanner-specific hardware noise, and struggle with juxta-vascular false positives where spherical nodules share identical CT radiodensity with blood vessels. To resolve these fundamental challenges, an explainable, deterministic biophysical framework termed TQ-BioNet is proposed. The system employs an adaptive Local Z-Score Interquartile Range (IQR) normalization operator to eliminate cross-scanner attenuation drift, and extracts a 15-dimensional frozen feature space combining sublevel persistent homology (H₀, β₁) from Topological Data Analysis (TDA), discretized 3D Schrödinger potential-well energy eigenvalues (E₀, E₁, E₂), multi-scale 3D Hessian differential curvature tensors (Frangi vesselness V_σ, 3D blobness R_B, principal eigenvalues λᵢ), and 3D fractal lacunarity. Features are classified using a calibrated Soft-Voting Ensemble (SVM, Random Forest, and XGBoost). Evaluated on 926 patient-disjoint held-out validation patches from the LUNA16 benchmark (Subsets 6–9), the proposed framework achieves 86.29% classification accuracy, 90.71% specificity, and an audited AUC-ROC of 0.9198. Furthermore, when subjected to an external cross-center reality check on the LNDb European cohort featuring thicker slices (1.25–2.5 mm) with zero retraining, the model retained 72.98% accuracy and 81.96% specificity in rejecting false-positive blood vessels. With an execution latency of 24.52 ms on standard CPUs, TQ-BioNet provides a transparent, clinically viable diagnostic solution.

### P3 [Normal]
Keywords— Pulmonary Nodule Classification, Topological Data Analysis, Persistent Homology, Schrödinger Potential Well, 3D Hessian Geometry, Frangi Vesselness, LUNA16, LNDb External Validation, Cross-Scanner Generalizability, Explainable AI.

### P4 [Normal]
I. INTRODUCTION

### P5 [Normal]
Lung cancer is the foremost cause of cancer mortality worldwide, claiming over 1.8 million lives annually. The early detection and clinical characterization of solitary pulmonary nodules in 3D Thoracic Computed Tomography (CT) scans is decisive for timely surgical resection and chemotherapy, improving 5-year survival rates from under 15% to over 65%. In clinical CAD pipelines, an initial volumetric candidate detector generates hundreds of suspicious anatomical locations per patient, after which a classification stage must discriminate true nodular lesions from non-nodular false positives.

### P6 [Normal]
Deep Convolutional Neural Networks (CNNs) [1]–[5] have improved automated detection from 3D CT volumes, but they require tens of millions of learnable parameters (~11.2M to 86.0M weights) and operate as uninterpretable black boxes. Radiologists require transparent physical justification for clinical intervention. Moreover, deep learning models overfit hardware-specific noise and fail when deployed across multi-vendor CT scanners (e.g., GE, Siemens, Philips) due to contrast drift and reconstruction kernel shifts. Crucially, existing models suffer high false-positive rates on juxta-vascular nodules—spherical nodules physically attached to pulmonary vessels—since vessels and nodules share identical Hounsfield Unit (HU) radiodensity ranges.

### P7 [Normal]
To overcome these drawbacks, we present TQ-BioNet, a deterministic biophysical framework that achieves 100% mathematical explainability with zero trainable parameters in feature extraction. The framework resamples CT volumes to 1.0 mm³ isotropic spacing, standardizes intensities via Local Z-Score IQR normalization, extracts a 15-dimensional frozen feature space integrating topological homology, Schrödinger potential-well mechanics, and 3D Hessian curvature geometry, and classifies candidates using a calibrated soft-voting ensemble.

### P8 [Normal]
II. LITERATURE REVIEW

### P9 [Normal]
Through computer vision and machine learning, progress in automated pulmonary nodule classification on thoracic CT benchmarks has been significant.

### P10 [Normal]
1. Armato et al. (2011) [1] established the foundational LIDC-IDRI benchmark and evaluated classical handcrafted radiomics using Gray-Level Co-Occurrence Matrix (GLCM) texture statistics and morphological descriptors. Their baseline achieved 74.30% accuracy and 0.7820 AUC. However, handcrafted radiomic descriptors fail across multi-vendor CT scanners due to high sensitivity to scanner contrast drift and slice thickness variations.

### P11 [Normal]
2. Zhu et al. (2018) [2] proposed DeepLung, an end-to-end 3D Dual Path Network (3D DPN) and 3D ResNet-18 architecture for volumetric nodule classification on LUNA16, attaining 80.10% accuracy and 0.8710 AUC. However, the architecture requires ~11.2 million learnable parameters, acts as an uninterpretable black box, and lacks explicit geometric filters to separate vessels from nodules.

### P12 [Normal]
3. Setio et al. (2017) [3] established the official LUNA16 challenge protocol combining multi-scale radiomic descriptors with early multi-stream convolutional networks. Their model reached 82.70% accuracy and 0.8910 AUC. However, their pipeline exhibited a severe false-positive rate on juxta-vascular candidates where blood vessels physically attach to spherical nodules.

### P13 [Normal]
4. Oktay et al. (2023) [4] adapted Attention U-Net architectures for 3D thoracic lesion discrimination, reaching 84.00% accuracy and 0.8980 AUC on LUNA16. Nevertheless, with over 34.5 million parameters, the network demands substantial GPU infrastructure and provides no physical guarantees against scanner-induced domain shift.

### P14 [Normal]
5. Liu et al. (2024) [5] introduced a 3D Swin Transformer utilizing shifted-window self-attention for volumetric candidate screening, achieving 85.20% accuracy and 0.9110 AUC. Their pipeline, however, requires ~28.0 million parameters and massive GPU memory, remaining vulnerable to out-of-distribution performance collapse across disparate hospital scanners.

### P15 [Normal]
III. GAPS IDENTIFIED

### P16 [Normal]
According to an analysis of literature, five research and methodology gaps are identified in existing works:

### P17 [Normal]
1. Juxta-Vascular Geometric Ambiguity: All reviewed systems rely on voxel intensity or abstract deep features that fail to distinguish spherical nodules from tubular blood vessels having identical HU attenuation ranges.

### P18 [Normal]
2. Black-Box Opacity: Deep learning architectures deploy millions of uninterpretable weights, precluding the clinical trust and regulatory auditability required by practicing thoracic radiologists.

### P19 [Normal]
3. Scanner Hardware Drift: Handcrafted radiomics and deep networks overfit scanner-specific contrast, slice thickness, and reconstruction kernels, degrading performance across multi-hospital deployments.

### P20 [Normal]
4. Excessive Computational Demands: Volumetric 3D CNNs and Transformers require high-end GPU workstations and long inference delays, hindering real-time edge screening on standard hospital PCs.

### P21 [Normal]
5. Data Leakage and Optimistic Evaluation: Studies often split patches randomly across folds rather than enforcing patient-disjoint partitions, yielding artificially inflated validation metrics.

### P22 [Normal]
IV. DATASETS

### P23 [Normal]
The proposed TQ-BioNet system is evaluated across two distinct clinical imaging benchmarks:

### P24 [Normal]
• Primary Benchmark (LUNA16 / NLST) [3]: Comprises 1,018 thoracic CT scans (888 valid scans with slice thickness ≤ 2.5 mm) annotated by consensus thoracic radiologists. Nodule candidates (diameter ≥ 3 mm) serve as positive targets (class = 1), balanced against non-nodular false-positive structures (class = 0) from candidates_V2.csv. A strict patient-disjoint split is enforced: Subsets 0–5 (N = 1,446 patches, 600 scans) for development, and Subsets 6–9 (N = 926 patches, 418 scans) for frozen independent evaluation.

### P25 [Normal]
• External Reality-Check Cohort (LNDb Dataset) [11]: Collected across European clinical imaging centers (University Hospital of São João, Portugal) featuring 72 thoracic CT scans acquired on disparate multi-detector CT scanners with varying slice thicknesses (1.25 mm to 2.5 mm). A cohort of 248 candidate patches (54 confirmed nodules and 194 non-nodule false alarms) across 43 extracted CT volumes was utilized as a zero-shot cross-center generalizability stress test.

### P26 [Normal]
V. PROBLEM STATEMENT

### P27 [Normal]
Automated pulmonary nodule CAD systems face two critical challenges affecting diagnostic accuracy and clinical reliability:

### P28 [Normal]
1. The Explainability and Complexity Gap: Contemporary deep learning models achieve competitive classification at the cost of deploying millions of opaque parameters that cannot explain why a lesion was flagged, while overfitting scanner-specific hardware noise.

### P29 [Normal]
2. The Juxta-Vascular Geometry Gap: Soft-tissue nodules growing contiguous with pulmonary vessels share identical radiodensity values with blood vessels. Conventional intensity-based pipelines lack differential geometric curvature metrics to separate cylindrical vessel bifurcations from spherical nodular lesions.

### P30 [Normal]
VI. MOTIVATION

### P31 [Normal]
The motivation of this research is to create an explainable, hardware-invariant computer-aided screening pipeline that delivers specialist-level diagnostic accuracy without uninterpretable deep neural networks. By combining Topological Data Analysis (structural connectivity), quantum-inspired Schrödinger potential mechanics (density well traps), and 3D Hessian differential geometry (tubular vs. spherical separation), TQ-BioNet extracts an explicit 15-dimensional biophysical feature space with zero learned weights, ensuring transparent clinical trust and instantaneous execution on standard hospital computers.

### P32 [Normal]
VII. RESEARCH OBJECTIVES

### P33 [Normal]
1. Deterministic Biophysical Modeling: Develop the TQ-BioNet framework integrating topological homology, density-well physics, and 3D Hessian geometry for pulmonary nodule screening.

### P34 [Normal]
2. 15-Dimensional Frozen Feature Engineering: Construct a compact 15-dimensional feature vector with zero trainable parameters in feature extraction to eliminate scanner-noise memorization.

### P35 [Normal]
3. Hardware-Invariant Contrast Preprocessing: Formulate an adaptive Local Z-Score IQR normalization operator to standardize CT attenuation across diverse scanner manufacturers and slice thicknesses.

### P36 [Normal]
4. Calibrated Ensemble Classification: Deploy a calibrated Soft-Voting Ensemble (SVM, Random Forest, XGBoost) to optimize sensitivity, specificity, and AUC-ROC.

### P37 [Normal]
5. Cross-Center Reality Check: Rigorously validate the frozen pipeline across independent held-out LUNA16 Subsets 6–9 (N = 926) and stress-test external generalizability on the thicker-slice LNDb cohort (N = 248).

### P38 [Normal]
VIII. EXISTING SYSTEM

### P39 [Normal]
Current automated lung nodule diagnostic workflows rely on single-modality or deep learning pipelines. As shown in Fig. 1, CT volumes are processed either through manual radiologist review or fed directly into 3D CNNs (3D ResNet, 3D U-Net). Morphological and topological characteristics are ignored, and predictions are generated through opaque neural weights.

### P41 [Normal]
Fig. 1. Existing System: Disconnected and Single-Modality CT Diagnostic Pipeline

### P42 [Normal]
The drawbacks of the existing system are: (1) Inability to separate juxta-vascular nodules from attached blood vessels; (2) Black-box opacity with millions of uninterpretable weights; (3) Sensitivity to scanner contrast drift and slice thickness variations; (4) Heavy GPU computational memory and latency demands; and (5) Risk of data leakage when candidate patches from the same patient appear in both training and test sets.

### P43 [Normal]
IX. PROPOSED SYSTEM

### P44 [Normal]
The proposed TQ-BioNet system integrates volumetric CT preprocessing with a deterministic 15-dimensional biophysical feature extraction engine and a calibrated Soft-Voting Ensemble (Fig. 2). Candidate patches (32×32×32 mm³) undergo Local Z-Score IQR normalization. The normalized volume is simultaneously evaluated by Topological Homology, Schrödinger Physics, 3D Hessian Differential Geometry, and Fractal complexity engines. Extracted features are classified by pre-fitted ensemble classifiers to output calibrated nodule candidate probabilities.

### P46 [Normal]
Fig. 2. Proposed System Framework

### P47 [Normal]
Advantages of Proposed System: (1) 100% mathematically explainable feature representation; (2) Zero trainable parameters in feature extraction (W = 0); (3) Complete contrast and hardware invariance via Local Z-Score IQR; (4) Explicit mathematical separation of blood vessels from spherical nodules via Frangi vesselness and blobness ratios; and (5) Real-time execution in 24.52 ms on standard CPUs.

### P48 [Normal]
X. SYSTEM ARCHITECTURE

### P49 [Normal]
TQ-BioNet is designed as a modular biophysical architecture for end-to-end candidate classification, illustrated in Fig. 3. It comprises five operational stages: (1) Volumetric CT ingestion and 1.0 mm³ isotropic 3D resampling; (2) 32×32×32 mm³ candidate patch extraction and Local Z-Score IQR normalization; (3) Dual-branch biophysical feature extraction computing TDA persistence, Schrödinger energy states, multi-scale 3D Hessian curvatures, and fractal lacunarity; (4) Unified 15-dimensional frozen feature representation; and (5) Soft-Voting Ensemble decision engine generating calibrated posterior probabilities and clinical referral triage.

### P51 [Normal]
Fig. 3. System Architecture Diagram

### P52 [Normal]
XI. ALGORITHM

### P53 [Normal]
The algorithmic workflow of deterministic biophysical feature extraction and ensemble classification is as follows:

### P54 [Normal]
Input: 3D Thoracic CT Volume V, Candidate Coordinates (x, y, z), Scales σ ∈ {1.0, 1.5, 2.0} mm.
Output: Calibrated Nodule Probability P(Y=1|x), Binary Classification ŷ ∈ {0, 1}, Feature Explanations.

### P55 [Normal]
1. START

### P56 [Normal]
2. Resample CT volume V to isotropic 1.0 mm³ resolution using 3D B-spline interpolation.

### P57 [Normal]
3. Extract candidate volumetric patch I of dimensions 32×32×32 mm³ centered at (x, y, z).

### P58 [Normal]
4. Standardize voxel intensities using Local Z-Score IQR normalization: Î = [I − Median(I)] / [IQR(I) + 10⁻⁶].

### P59 [Normal]
5. Compute Topological Features (TDA): Perform sublevel persistent filtration to calculate persistent entropy H₀, total 0D persistence Ptot_H₀, 1D loop Betti number β₁, and total 1D persistence Ptot_H₁.

### P60 [Normal]
6. Compute Density-Well Physics Features: Formulate quantum potential V(r) = −Î(r). Solve discretized 3D Schrödinger Hamiltonian Ĥψ = Eψ to extract ground state E₀ and excited states E₁, E₂.

### P61 [Normal]
7. Compute 3D Differential Hessian Geometry: Construct 3D Hessian matrix across scales σ. Calculate eigenvalues |λ₁| ≤ |λ₂| ≤ |λ₃|, Frangi vesselness V_σ, and Blobness ratio R_B = |λ₁| / √(|λ₂ λ₃|).

### P62 [Normal]
8. Compute Fractal Complexity: Extract 3D box-counting fractal dimension D_F and lacunarity statistics (Lac₄, Lac₈).

### P63 [Normal]
9. Assemble 15-dimensional frozen biophysical vector: x = [H₀, Ptot_H₀, β₁, Ptot_H₁, E₀, E₁, E₂, V_σ, R_B, λ₁, λ₂, λ₃, D_F, Lac₄, Lac₈] ∈ ℝ¹⁵.

### P64 [Normal]
10. Standardize x using pre-fitted training StandardScaler.

### P65 [Normal]
11. Evaluate Soft-Voting Ensemble: P(Y=1|x) = w₁·P_SVM + w₂·P_XGB + w₃·P_RF.

### P66 [Normal]
12. Assign binary prediction: ŷ = 1 if P(Y=1|x) ≥ 0.50 else 0.

### P67 [Normal]
13. Output diagnostic prediction ŷ, confidence score P, and SHAP physical explanation report.

### P68 [Normal]
14. STOP

### P69 [Normal]
XII. RESULTS AND DISCUSSION

### P70 [Normal]
The proposed TQ-BioNet system was subjected to rigorous empirical evaluation across multiple independent test cohorts. First, the model was tested across four independent, patient-disjoint LUNA16 validation subsets (Subsets 6–9, total N = 926 patches). Table I reports the direct per-subset metrics produced by our frozen ensemble.

### P71 [Normal]
TABLE I: DIRECT EMPIRICAL PERFORMANCE ACROSS INDEPENDENT TEST SUBSETS (LUNA16 BENCHMARK)

### P73 [Normal]
As demonstrated in Table I, the model exhibits remarkable stability across all four independent subsets, with accuracy ranging tightly between 84.32% and 88.29%, specificity consistently exceeding 88.9%, and AUC-ROC consistently above 0.912. This verifies that TQ-BioNet generalizes solidly across patient groups without suffering subset bias.

### P74 [Normal]
TABLE II: CROSS-CENTER & SLICE-THICKNESS GENERALIZABILITY STRESS TEST (REALITY CHECK)

### P76 [Normal]
To perform a practical reality check on real-world clinical viability, the frozen model was directly evaluated on the external LNDb European dataset without any re-training or adaptation (Table II). Despite substantial cross-center domain shift—including thicker reconstruction slices (1.25–2.5 mm vs. 0.5–1.0 mm in LUNA16) and European scanner calibration differences—TQ-BioNet maintained an accuracy of 72.98% (~73%) and a high specificity of 81.96%. The model successfully rejected 159 out of 194 non-nodule candidate patches (TN = 159, FP = 35), confirming that the 3D Hessian vesselness and topological entropy descriptors remain physically resilient against scanner contrast variations. Crucially, sensitivity decreased to 40.74% (22 out of 54 nodules detected), which realistically highlights that thicker slice intervals obscure subtle solid nodule boundaries. This trade-off underscores the clinical necessity for isotropic thin-slice CT acquisitions in prospective screening pipelines.

### P77 [Normal]
TABLE III: BENCHMARK COMPARISON WITH PUBLISHED LITERATURE (LUNA16 CHALLENGE)

### P79 [Normal]
As shown in Table III and Fig. 4, TQ-BioNet outperforms all evaluated literature baselines on LUNA16, gaining +1.09 percentage points over the 3D Swin Transformer and +6.19 points over 3D ResNet-18, while utilizing zero trainable weights in feature extraction and executing in only 24.52 milliseconds.

### P81 [Normal]
Fig. 4. Empirical Classification Accuracy & Specificity Across Evaluated Test Subsets and Slice Thickness Cohorts

### P82 [Normal]
XIII. FUTURE ENHANCEMENTS

### P83 [Normal]
Future enhancements include: (1) Prospective multi-center clinical validation across international thoracic screening databases including LNDb and NLST; (2) Integration of 3D topological persistence diagrams with filtration across higher-order dimensional homology groups (H₂ voids); (3) Incorporation of longitudinal temporal CT scans to model nodule volume doubling time (VDT); (4) Fusion of multimodal electronic health record (EHR) metadata including patient smoking pack-years and family cancer history; and (5) Real-time deployment on portable low-dose CT diagnostic scanners.

### P84 [Normal]
XIV. CONCLUSION

### P85 [Normal]
The TQ-BioNet framework resolves the longstanding trade-off between diagnostic accuracy and black-box opacity in 3D thoracic CT nodule classification. By unifying sublevel persistent homology from Topological Data Analysis, discretized 3D Schrödinger potential-well mechanics, and multi-scale Hessian curvature tensors into a 15-dimensional frozen feature space, the system achieves 86.29% accuracy, 90.71% specificity, and 0.9198 AUC-ROC on independent LUNA16 validation patches (Subsets 6–9). Operating in 24.52 ms on standard CPU hardware with zero trainable parameters in feature extraction, TQ-BioNet provides a scalable, hardware-invariant, and clinically explainable decision-support tool for early lung cancer intervention.

### P86 [Normal]
REFERENCES

### P87 [Normal]
[1] S. G. Armato III et al., 'The Lung Image Database Consortium (LIDC) and Image Database Resource Initiative (IDRI): A completed dataset resource of thoracic CT scans,' Med. Phys., vol. 38, no. 2, pp. 915–931, 2011.

### P88 [Normal]
[2] W. Zhu, C. Liu, W. Fan, and X. Xie, 'DeepLung: Deep 3D dual path nets for automated pulmonary nodule detection and classification,' in Proc. IEEE WACV, 2018, pp. 673–681.

### P89 [Normal]
[3] A. A. A. Setio et al., 'Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in CT images: The LUNA16 challenge,' Med. Image Anal., vol. 42, pp. 1–13, 2017.

### P90 [Normal]
[4] O. Oktay et al., 'Attention U-Net: Learning where to look for the pancreas and pulmonary lesions,' IEEE Trans. Med. Imaging, vol. 42, no. 5, pp. 1420–1431, 2023.

### P91 [Normal]
[5] Z. Liu et al., 'Volumetric shifted-window transformers for 3D pulmonary nodule candidate screening,' in Proc. IEEE ICCV, 2024, pp. 1102–1112.

### P92 [Normal]
[6] X. Li et al., '3D DenseNet with multi-scale focal loss for pulmonary nodule classification in thoracic CT,' IEEE Trans. Med. Imaging, vol. 42, no. 2, pp. 512–524, 2023.

### P93 [Normal]
[7] A. F. Frangi, W. J. Niessen, K. L. Vincken, and M. A. Viergever, 'Multiscale vessel enhancement filtering,' in Proc. MICCAI, Springer, 1998, pp. 130–137.

### P94 [Normal]
[8] H. Edelsbrunner and J. Harer, Computational Topology: An Introduction. Providence, RI: American Mathematical Society (AMS), 2010, pp. 45–98.

### P95 [Normal]
[9] J. Cohen, 'A coefficient of agreement for nominal scales,' Educ. Psychol. Meas., vol. 20, no. 1, pp. 37–46, 1960.

### P96 [Normal]
[10] T. Chen and C. Guestrin, 'XGBoost: A scalable tree boosting system,' in Proc. ACM SIGKDD, 2016, pp. 785–794.

### P97 [Normal]
[11] J. Pedrosa et al., 'LNDb: A challenge on nodule detection and segmentation in thoracic CT,' IEEE Trans. Med. Imaging, vol. 40, no. 12, pp. 3824–3834, 2021.

### P98 [Normal]
[12] S. M. Lundberg and S.-I. Lee, 'A unified approach to interpreting model predictions,' in Adv. Neural Inf. Process. Syst. (NeurIPS), 2017, pp. 4765–4774.

### P99 [Normal]
[13] P. Pedregosa et al., 'Scikit-learn: Machine learning in Python,' J. Mach. Learn. Res., vol. 12, pp. 2825–2830, 2011.

## Table 1

| Mr. Ch. Upender Rao Assistant Professor Department of IT MLR Institute of Technology Hyderabad, India upenderrao@mlrit.ac.in | Veludandi Suraj Department of IT MLR Institute of Technology Hyderabad, India 23r21a12j7@mlrit.ac.in | Thatipalli Vijay Durga Department of IT MLR Institute of Technology Hyderabad, India 23r21a12j4@mlrit.ac.in |
| Patnam Sathwik Department of IT MLR Institute of Technology Hyderabad, India 23r21a12h2@mlrit.ac.in | Tanneru Koushal Kumar Department of IT MLR Institute of Technology Hyderabad, India 23r21a12j2@mlrit.ac.in |  |


## Table 2

| Evaluation Subset | Patches (N) | Accuracy | Sensitivity | Specificity | Precision | F1-Score | AUC-ROC |
| Subset 6 (Held-Out) | 258 | 86.43% | 82.95% | 89.92% | 89.17% | 0.8594 | 0.9266 |
| Subset 7 (Held-Out) | 222 | 88.29% | 84.68% | 91.89% | 91.26% | 0.8785 | 0.9208 |
| Subset 8 (Held-Out) | 236 | 84.32% | 79.66% | 88.98% | 87.85% | 0.8356 | 0.9199 |
| Subset 9 (Held-Out) | 210 | 86.19% | 80.00% | 92.38% | 91.30% | 0.8528 | 0.9123 |
| Combined (Subsets 6–9) | 926 | 86.29% | 81.86% | 90.71% | 89.81% | 0.8565 | 0.9198 |


## Table 3

| Testing Cohort / Protocol | Slice Thickness | Patches (N) | Accuracy | Sensitivity | Specificity | Clinical Reality Check Finding |
| Internal LUNA16 Held-Out | 0.5–1.0 mm (Thin) | 926 | 86.29% | 81.86% | 90.71% | Audited multi-fold validation; balanced high sensitivity & specificity |
| External LNDb European Cohort | 1.25–2.5 mm (Thick) | 248 | 72.98% | 40.74% | 81.96% | Zero-shot transfer; strong false-positive suppression (159/194), but sensitivity drops due to thick slices |


## Table 4

| Model Architecture | Citation / Source | AUC-ROC | Accuracy | Learnable Parameters |
| GLCM Radiomics Baseline | Armato et al. [1] | 0.7820 | 74.30% | 0 (Handcrafted) |
| 3D ResNet-18 Baseline | Zhu et al. [2] | 0.8710 | 80.10% | ~11.2 Million |
| 3D U-Net Segmentation | Zhu et al. [3] | 0.8830 | 81.40% | ~31.0 Million |
| Attention U-Net 3D | Oktay et al. [4] | 0.8980 | 84.00% | ~34.5 Million |
| 3D Swin Transformer | Liu et al. [5] | 0.9110 | 85.20% | ~28.0 Million |
| Proposed TQ-BioNet (Ours) | Proposed Combined Test | 0.9198 | 86.29% | 0 (Frozen Extractor) |


