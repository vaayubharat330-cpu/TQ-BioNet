# TQ-BioNet: Candidate-Level Pulmonary Nodule Classification on 3D Thoracic CT

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Benchmarks: LUNA16](https://img.shields.io/badge/Benchmark-LUNA16%20%7C%20LNDb-orange.svg)]()
[![Research prototype](https://img.shields.io/badge/status-research%20prototype-orange.svg)]()

> **TQ-BioNet: Lung Nodule Classification on Thoracic CT Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry**  
> *Developed by: Department of Information Technology, MLR Institute of Technology, Hyderabad, Telangana, India.*

---

## 📌 Project Overview

**TQ-BioNet** is a research prototype for candidate-level pulmonary nodule classification on 3D thoracic CT. It combines hand-engineered numerical descriptors with a supervised classifier. Feature extraction has no learned weights; the classifier is trained from data.

Existing computer-aided detection (CAD) systems face two fundamental challenges:
1. **Black-box opacity and parameter bloat:** Deep 3D convolutional networks (3D ResNet, 3D Swin Transformers) employ tens of millions of learnable parameters ($11\text{M} - 86\text{M}$ weights), which overfit scanner-specific contrast noise and lack clinical explainability.
2. **Juxta-vascular false positives:** Spherical nodules physically attached to pulmonary vessels share identical Hounsfield Unit (HU) radiodensity ranges with blood vessels, creating excessive false alarms at vascular bifurcations.

The current implementation extracts 31 descriptors, with a 15-feature subset used by selected validation scripts. It uses a numerical finite-difference eigenproblem, point-cloud persistent homology, thresholded fractal summaries, and single-location Hessian descriptors. The ensemble averages model probabilities; it is not calibrated unless a separate calibration procedure is explicitly fitted and evaluated.

---

## 🌟 Key Technical Contributions

* **Zero-Trainable-Parameter Feature Extraction ($W = 0$):** Zero GPU backward propagation during feature extraction, eliminating the risk of memorizing scanner hardware noise.
* **Local Z-Score IQR Normalization:** $\hat{I} = \frac{I - \text{Median}(I)}{\text{IQR}(I) + 10^{-6}}$ standardizes local contrast and suppresses multi-vendor attenuation drift across scanner manufacturers (GE, Siemens, Philips).
* **Juxta-Vascular Separation:** Multi-scale Frangi vesselness filter ($\mathcal{V}_\sigma$) and 3D Blobness ratios ($R_B$) mathematically separate tubular vessels from spherical nodules.
* **3D Schrödinger Density Well:** Discretized 3D Hamiltonian eigenvalue equation solved via SciPy ARPACK Lanczos solver, extracting core density concentration states ($E_0, E_1, E_2$).
* **Sublevel Persistent Homology:** Captures microstructural tissue connectivity ($H_0$ persistent entropy, $\beta_1$ 1D loops).
* **Runtime:** Benchmark numbers must be regenerated on documented hardware and software versions before being treated as reproducible performance claims.

---

## ⚠️ Historical Results — Not Yet Revalidated

### 1. Primary Benchmark: LUNA16 Independent Validation Cohort (Subsets 6–9, $N = 926$)
Previously reported repository metrics are retained here as historical records only. The current audit found inconsistencies in validation scripts and split metadata. Subset separation / SeriesUID separation must not be described as patient-disjoint unless a verified patient mapping is supplied. Do not cite these values as independently reproduced v3.1 results:

| Metric | Score | 95% Confidence Interval (Bootstrap $B=1000$) |
| :--- | :---: | :---: |
| **Accuracy** | **86.29%** | $[83.91\% - 88.45\%]$ |
| **Specificity** | **90.71%** | $[88.02\% - 92.98\%]$ |
| **Precision** | **89.81%** | $[86.95\% - 92.21\%]$ |
| **Sensitivity** | **81.86%** | $[78.04\% - 85.23\%]$ |
| **F1-Score** | **0.8565** | $[0.8310 - 0.8800]$ |
| **AUC-ROC** | **0.9198** | $[0.9015 - 0.9387]$ |

#### Per-Subset Stability (Subsets 6–9):
* **Subset 6 ($N=258$):** Accuracy = 86.43%, Specificity = 89.92%, AUC-ROC = 0.9266
* **Subset 7 ($N=222$):** Accuracy = 88.29%, Specificity = 91.89%, AUC-ROC = 0.9208
* **Subset 8 ($N=236$):** Accuracy = 84.32%, Specificity = 88.98%, AUC-ROC = 0.9199
* **Subset 9 ($N=210$):** Accuracy = 86.19%, Specificity = 92.38%, AUC-ROC = 0.9123

### 2. LNDb external validation — currently blocked
Evaluated on external CT volumes from the University Hospital of São João with thicker slices ($1.25 - 2.5\,\text{mm}$) and different reconstruction kernels with **zero fine-tuning**:
* **Accuracy:** **72.98%**
* **Specificity:** **81.96%** (Successfully rejected 159 out of 194 non-nodule false alarms; $\text{TN} = 159, \text{FP} = 35$)
* **Sensitivity:** **40.74%** (Reflects expected real-world domain shift on thick slices)

---

## 📐 System Architecture

```
[3D Thoracic CT Volume (.mhd/.raw)]
               │
               ▼
 [1.0 mm³ Isotropic Spatial Resampling]
               │
               ▼
[32×32×32 mm³ Candidate Patch Extraction]
               │
               ▼
 [Local Z-Score IQR Contrast Normalization]
               │
 ┌─────────────┼─────────────┬─────────────┐
 ▼             ▼             ▼             ▼
[TDA Homology] [Schrödinger] [3D Hessian]  [3D Fractal]
 (H₀, β₁, Ptot) (E₀, E₁, E₂)  (V_σ, R_B, λᵢ)(D_F, Lac)
 └─────────────┼─────────────┴─────────────┘
               │
               ▼
 [15-Dimensional Frozen Feature Vector (x ∈ ℝ¹⁵)]
               │
               ▼
 [Soft-Voting Ensemble (SVM + XGBoost + RF)]
               │
               ▼
 [Mean Ensemble Probability & Prediction]
```

---

## 📂 Repository Directory Structure

```text
├── tq_bionet/                  # Core feature extraction & modeling package
│   ├── pipeline.py             # Master feature extraction pipeline
│   ├── quantum_module.py       # 3D Schrödinger finite-difference solver
│   ├── tda_module.py           # Topological persistent homology module
│   ├── hessian_module.py       # 3D Hessian vesselness & blobness filters
│   ├── fractal_module.py       # 3D box-counting dimension & lacunarity
│   ├── classifier.py          # Soft-Voting Ensemble (SVM, XGBoost, RF)
│   └── runtime_benchmark.py    # Latency benchmarking suite
│
├── outputs/                    # Output plots, confusion matrices, and ROC curves
│   ├── luna16_roc_curve.png    # Audited ROC curve on LUNA16 (AUC = 0.9198)
│   ├── validation_confusion_matrix.png
│   ├── feature_importance.png  # SHAP feature attribution ranking
│   └── subset_comparison.png   # Cross-subset performance stability
│
├── TQ_BioNet_IEEE_Conference_Paper.docx        # Final formatted IEEE Conference Paper
├── TQ_BioNet_Patent_Form2_Complete_Specification.docx # Indian Patent Form-2 Specification
├── Batch-13_PPT_Reviewed_Fixed.pptx           # Reviewed project defense presentation
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git exclusions for large CT volumes
└── README.md                   # Comprehensive project documentation
```

---

## 🚀 Quickstart & Reproduction

For the v3.1 audit/repair work, see `AUDIT_REPAIR_V3.1.md`. Do not reuse v3.0 caches after any feature-schema or preprocessing change; the v3.1 pipeline must regenerate caches and manifests. Full LUNA16/LNDb validation requires the corresponding datasets and is not claimed to have run in this repository audit.

### 1. Installation
Clone this repository and install dependencies in a clean virtual environment:
```bash
git clone https://github.com/vaayubharat330-cpu/TQ-BioNet.git
cd TQ-BioNet
pip install -r requirements.txt
```

### 2. Run Independent Validation on LUNA16
To evaluate the frozen voting ensemble on the held-out validation cohort:
```bash
python run_independent_validation.py
```

### 3. Run Benchmark Latency Suite
To benchmark the execution latency of each mathematical sub-engine:
```bash
python run_benchmarks.py
```

---

## 👥 Authors & Institutional Affiliation

* **Faculty Supervisor:**
  * **Ch. Upender Rao**, Assistant Professor, Department of Information Technology, MLR Institute of Technology, Hyderabad, India.
* **Student Researchers & Innovators:**
  * **Veludandi Suraj** (Roll No: `23R21A12J7`)
  * **Thatipalli Vijay Durga** (Roll No: `23R21A12J4`)
  * **Patnam Sathwik** (Roll No: `23R21A12H2`)
  * **Tanneru Koushal Kumar** (Roll No: `23R21A12J2`)

**Department of Information Technology**  
**MLR Institute of Technology (Autonomous)**  
Dundigal, Hyderabad – 500043, Telangana, India.

---

## 📜 Citation & License

This project is licensed under the [MIT License](LICENSE).

```bibtex
@article{tqbionet2026,
  title={TQ-BioNet: Lung Nodule Classification on Thoracic CT Integrating Topological Homology, Density Well Physics, and 3D Hessian Geometry},
  author={Rao, Ch. Upender and Suraj, Veludandi and Durga, Thatipalli Vijay and Sathwik, Patnam and Kumar, Tanneru Koushal},
  journal={Department of Information Technology, MLR Institute of Technology},
  year={2026}
}
```
