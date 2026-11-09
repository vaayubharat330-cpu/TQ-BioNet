# IEEE Manuscript Revision Summary: TQ_BioNet_IEEE_Conference_Paper.docx

**Revision Date**: 2026-11-09  
**Target Document**: `TQ_BioNet_IEEE_Conference_Paper.docx`  
**Working Branch**: `audit/repair-v3.1`  
**Verification**: Preserved IEEE two-column paper structure, author block, figures, and formatting while aligning all textual claims, mathematical formulations, and experimental tables with the audited code and results.

---

## 1. Summary of Corrections Across Manuscript Sections

### 1.1 Title & Abstract
- **Title**: Updated to explicitly specify candidate classification:
  *`TQ-BioNet: Lung Nodule Candidate Classification on Thoracic CT Integrating Topological Homology, Quantum Density Physics, and 3D Hessian Geometry`*
- **Candidate-Level & Balanced Benchmark Clarification**:
  - Replaced "patient-disjoint held-out validation patches" with **"scan-level (SeriesUID) disjoint held-out validation candidates from the LUNA16 benchmark (Subsets 6–9, balanced 1:1 across 236 CT scans)"**.
  - Clarified that high accuracy and precision reflect candidate-level discrimination on an artificially balanced benchmark rather than clinical screening positive predictive value (PPV).
- **Accurate In-Domain Metrics**:
  - Updated ROC-AUC from $0.9198$ to audited **$0.9202$ [95% CI: $0.9022–0.9353$]**, with accuracy of **$86.29\%$ [83.98%–88.33%]**, sensitivity of **$81.86\%$**, and specificity of **$90.71\%$**.
- **Ensemble Calibration Framing**:
  - Replaced "calibrated Soft-Voting Ensemble" with **"unweighted Soft-Voting Ensemble (SVM, Random Forest, and XGBoost)"**, reflecting that while Platt-scaled SVM achieves $\text{ECE}=0.0450$, the unweighted soft voting ensemble achieves $\text{ECE}=0.1057$.
- **LNDb External Reality Check Replacement**:
  - Removed old unverified exploratory numbers ($72.98\%$ accuracy, $81.96\%$ specificity on 248 patches).
  - Replaced with the complete audited cohort findings ($229$ annotated scans, $1,219$ consensus findings):
    - **Zero-Shot Transfer**: Marked domain sensitivity with **$54.72\%$ accuracy and $0.5729$ ROC-AUC** at the $1.0\text{ mm}$ baseline, with multi-resolution resampling ($0.8\text{ mm}$, $1.25\text{ mm}$) confirming that voxel resampling alone does not overcome hardware and protocol drift.
    - **Domain Adaptation**: Scan-grouped adaptation on official consensus folds recovered discrimination to **$68.75\%$ accuracy and $0.6934$ ROC-AUC** on held-out Fold 3 ($N=320$ findings), achieving a statistically significant paired scan-cluster bootstrap improvement of **$+9.06\%$ [95% CI: $+2.27\%, +16.37\%$]** over the always-positive majority baseline ($59.69\%$).

---

### 1.2 Mathematical & Feature Extraction Methodology
- **Audit-Accurate 15-Feature Schema**:
  - **Topological Homology (4 features)**: $H_0$ persistent entropy, $H_0$ total persistence, $H_1$ count (loop count), and $H_1$ total persistence.
  - **3D Hessian Differential Geometry (5 features)**: Principal eigenvalues $|\lambda_1| \le |\lambda_2| \le |\lambda_3|$, Frangi vesselness ratio $V$, and 3D blobness ratio $R_B = |\lambda_1| / \sqrt{|\lambda_2 \lambda_3|}$ evaluated at single-scale $\sigma = 1.0\text{ mm}$ (corrected from multi-scale claim).
  - **Quantum Graph Laplacian (3 features)**: Lowest three non-trivial eigenvalues $\mu_0, \mu_1, \mu_2$ of the normalized graph Laplacian ($L_{\text{sym}} \psi = \mu \psi$) constructed from localized voxel patch adjacency (corrected from continuous Schrödinger potential well claim).
  - **Fractal Complexity (3 features)**: 3D box-counting fractal dimension $D_F$, lacunarity at radius 4 ($\text{Lac}_4$), and lacunarity at radius 8 ($\text{Lac}_8$).
- **Scaling Contract & Decision Policy**:
  - Explicitly specified that SVM is strictly fit on `StandardScaler` normalized features, whereas XGBoost and Random Forest strictly process unscaled features.
  - Soft-voting ensemble: $P(Y=1|x) = [P_{\text{SVM}}(x_{\text{scaled}}) + P_{\text{XGB}}(x) + P_{\text{RF}}(x)] / 3$.
  - Fixed decision threshold: $\hat{y} = 1 \iff P(Y=1|x) \ge 0.50$.

---

### 1.3 Dataset Descriptions & Scan-Level Split Integrity
- **LUNA16 (Primary Benchmark)**:
  - Documented exact scan counts: $888$ scans total; Development cohort (Subsets 0–5) contains $365$ scans and $1,446$ candidates ($723$ nodules, $723$ non-nodules); Validation cohort (Subsets 6–9) contains $236$ scans and $926$ candidates ($463$ nodules, $463$ non-nodules).
  - Strictly framed as **scan-level (SeriesUID) disjoint** ($\text{SeriesUID}_{\text{dev}} \cap \text{SeriesUID}_{\text{val}} = \emptyset$). Noted that patient-level independence is not claimed without external LIDC-IDRI mapping.
- **LNDb (External Reality-Check Cohort)**:
  - Documented clinical cohort from University Hospital of São João, Portugal: $294$ scans total, $229$ annotated scans containing $1,219$ consensus findings partitioned across 4 official consensus folds.
  - Documented physical geometry differences: median through-plane Z-spacing of $1.00\text{ mm}$ (vs. $1.25\text{ mm}$ in LUNA16) and diverse reconstruction kernels.

---

### 1.4 Tables & Results Alignment

#### Table I: Direct Empirical Performance Across Independent Test Subsets (LUNA16)
Updated with audited per-subset values and exact confidence intervals:
| Evaluation Subset | Candidates (N) | Accuracy | Sensitivity | Specificity | Precision | F1-Score | AUC-ROC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Subset 6 (Held-Out)** | 258 | 86.43% | 82.95% | 89.92% | 89.17% | 0.8594 | 0.9270 |
| **Subset 7 (Held-Out)** | 222 | 88.29% | 84.68% | 91.89% | 91.26% | 0.8785 | 0.9208 |
| **Subset 8 (Held-Out)** | 236 | 84.32% | 79.66% | 88.98% | 87.85% | 0.8356 | 0.9192 |
| **Subset 9 (Held-Out)** | 210 | 86.19% | 80.00% | 92.38% | 91.30% | 0.8528 | 0.9135 |
| **Combined (Subsets 6–9)** | **926** | **86.29%** | **81.86%** | **90.71%** | **89.81%** | **0.8565** | **0.9202** |

*Note: Combined metrics include audited 95% CIs: Accuracy [83.98%–88.33%], Sensitivity [78.09%–85.10%], Specificity [87.72%–93.03%], Precision [86.56%–92.35%], F1 [83.11%–87.91%], ROC-AUC [0.9022–0.9353], Brier score 0.1178, and ECE 0.1057.*

#### Table II: Cross-Center & Domain Adaptation Reality Check (LNDb)
Replaced the single exploratory row with the complete audited experimental evaluation:
| Testing Cohort / Protocol | Slice Sampling | Candidates (N) | Accuracy | Sensitivity | Specificity | Scientific & Clinical Reality Check Finding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Internal LUNA16 Held-Out** | 0.5–1.0 mm (Thin) | 926 | 86.29% | 81.86% | 90.71% | Audited scan-level held-out validation; strong in-domain candidate discrimination (AUC = 0.9202 [0.902–0.935]) |
| **External LNDb Zero-Shot (Baseline 1.0 mm)** | 1.0–2.0 mm (Thick) | 1,219 | 54.72% | 51.04% | 60.98% | Zero-shot transfer collapse (AUC = 0.5729); multi-resolution resampling (0.8–1.25 mm) does not overcome protocol shift |
| **External LNDb Domain-Adapted (Fold 3)** | 1.0–2.0 mm (Thick) | 320 | 68.75% | 83.25% | 46.72% | Scan-grouped adaptation recovers AUC = 0.6934; paired scan-cluster bootstrap gain of +9.06% [95% CI: +2.27%, +16.37%] over majority baseline |

#### Table III: Benchmark Comparison with Published Literature (LUNA16)
- Updated Proposed TQ-BioNet AUC to **$0.9202$** and Accuracy to **$86.29\%$**.
- Clarified in text that comparisons reflect candidate-level classification benchmarks on balanced or semi-balanced candidate sets rather than full screening detection.

---

### 1.5 Discussion, Limitations, & Conclusion
- **Scientific Integrity of the Cross-Cohort Contrast**:
  The paper now presents the honest contrast between strong in-domain candidate discrimination on LUNA16 ($0.9202$ AUC) and substantial zero-shot performance drop on LNDb ($0.5729$ AUC). It explains that voxel resampling alone ($0.8\text{ mm}, 1.0\text{ mm}, 1.25\text{ mm}$) did not solve the domain gap, and that while domain adaptation improves discrimination to $0.6934$ AUC (+9.06% over baseline), false-positive suppression remains challenging due to probability overlap between true nodules and non-nodular findings.
- **Explicit Scope Boundaries**:
  Clearly framed as a candidate classification component within CAD pipelines, not as a standalone clinically validated screening system.
