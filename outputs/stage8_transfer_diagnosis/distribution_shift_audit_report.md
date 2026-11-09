# TQ-BioNet Stage 8: LNDb Transfer Diagnosis — 15-Feature Distribution Shift Audit

**Audit Date**: November 9, 2026 (Revised Stage 8.0.1)  
**Cohorts Audited**:
- **LUNA16 Development (Reference)**: Subsets 0–5 ($N=1446$, Pos=723, Neg=723, Scans=365)
- **LUNA16 Validation (In-Domain Control)**: Subsets 6–9 ($N=926$, Pos=463, Neg=463, Scans=236)
- **LNDb Exploratory Cohort (Transfer Diagnosis)**: Folds 0–2 ($N=899$, Pos=577, Neg=322, Scans=171) across 171 annotated scans
- **Status of Fold 3**: **LNDb Fold 3 is excluded from this diagnostic study** ($N=320$ findings across 58 annotated scans). Fold 3 was previously evaluated during Stages 6E/6F and is deliberately excluded here to avoid cumulative tuning bias.

---

## 1. Executive Summary & Core Diagnostic Findings

This audit examines the feature-level shifts between LUNA16 and LNDb to diagnose why zero-shot performance dropped from **86.29% accuracy (0.9202 AUC)** on LUNA16 to **54.72% accuracy (0.5729 AUC)** on LNDb without training any new models.

### Key Observations:
1. **Elevated Cross-Cohort Drift vs Minimal In-Domain Drift**:
   - Across LUNA16 Subsets 0–5 vs 6–9 (in-domain control), the maximum normalized Wasserstein distance across all 15 features is only **0.063** (average: **0.038**), with all $\text{PSI} < 0.05$.
   - In contrast, between LUNA16 and LNDb Folds 0–2, the average normalized Wasserstein distance increases **8.3x to 0.281**, and **11 out of 15 features exhibit moderate distribution shift ($0.10 \le \text{PSI} < 0.25$)**; zero features cross the $\text{PSI} \ge 0.25$ threshold overall.

2. **Asymmetric Class-Conditional Divergence (Negative-Class Divergence)**:
   - **Positive Nodules** show their largest shifts in **Differential Geometry / Hessian eigenvalues** (`hessian_L2` $W_d = 0.444$, `hessian_L3` $W_d = 0.424$, `hessian_L1` $W_d = 0.397$).
   - **Negative Non-Nodules** exhibit much stronger shifts in **fractal dimension** ($W_d = 0.578$ vs $0.131$ in positives), **H0 entropy** ($W_d = 0.588$ vs $0.408$), and **quantum graph Laplacian eigenvalues** ($W_d \approx 0.51$ vs $0.12$ in positives). Within negatives specifically, 10 features exceed $\text{PSI}_{\text{neg}} \ge 0.25$.
   - *Diagnostic Hypothesis*: These descriptive measurements support the hypothesis that differences in negative candidate generation (CAD candidate false positives in LUNA16 vs radiologist-reviewed non-nodules in LNDb) alter the morphological baseline of the negative class, while scanner acquisition variations contribute to positive nodule curvature differences. These hypotheses will be directly tested against acquisition parameters in Stage 8.1.

3. **Topological and Fractal Sensitivity**:
   - Persistent homology ($H_0, H_1$) and fractal lacunarity show moderate shift across both classes, reflecting sensitivity to scanner noise floors and local slice interpolation.

---

## 2. 15-Feature Distribution Shift Ranking (Overall)

Features ranked by Normalized Wasserstein Distance (normalized to 1.0 $\sigma$ of LUNA16 Development):

| Rank | Feature | Family | Norm Wasserstein ($W_d$) | KS Stat ($D$) | Cohen's $d$ | PSI | Shift Level |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `H0_entropy` | Topological Persistence | 0.4819 | 0.1999 | -0.4819 | 0.2067 | *Moderate (0.10–0.25)* |
| 2 | `hessian_L2` | Differential Geometry / Hessian | 0.3660 | 0.1826 | -0.3652 | 0.2059 | *Moderate (0.10–0.25)* |
| 3 | `hessian_L3` | Differential Geometry / Hessian | 0.3657 | 0.1703 | -0.3655 | 0.2008 | *Moderate (0.10–0.25)* |
| 4 | `H0_total_persistence` | Topological Persistence | 0.3469 | 0.1914 | -0.3469 | 0.1901 | *Moderate (0.10–0.25)* |
| 5 | `H1_count` | Topological Persistence | 0.3411 | 0.2120 | -0.3411 | 0.2126 | *Moderate (0.10–0.25)* |
| 6 | `H1_total_persistence` | Topological Persistence | 0.3408 | 0.2120 | -0.3408 | 0.2126 | *Moderate (0.10–0.25)* |
| 7 | `fractal_dimension` | Fractal Complexity | 0.3161 | 0.1417 | -0.3161 | 0.1035 | *Moderate (0.10–0.25)* |
| 8 | `lacunarity_4` | Fractal Complexity | 0.2492 | 0.1423 | +0.2482 | 0.1001 | *Moderate (0.10–0.25)* |
| 9 | `quantum_eigenvalue_0` | Quantum Graph Laplacian | 0.2468 | 0.1596 | -0.2192 | 0.1485 | *Moderate (0.10–0.25)* |
| 10 | `quantum_eigenvalue_1` | Quantum Graph Laplacian | 0.2453 | 0.1543 | -0.2124 | 0.1612 | *Moderate (0.10–0.25)* |
| 11 | `quantum_eigenvalue_2` | Quantum Graph Laplacian | 0.2403 | 0.1504 | -0.2074 | 0.1538 | *Moderate (0.10–0.25)* |
| 12 | `blobness_ratio` | Differential Geometry / Hessian | 0.1838 | 0.1041 | +0.1836 | 0.0495 | Minimal (<0.10) |
| 13 | `hessian_L1` | Differential Geometry / Hessian | 0.1637 | 0.0769 | -0.1632 | 0.0875 | Minimal (<0.10) |
| 14 | `lacunarity_8` | Fractal Complexity | 0.1541 | 0.0823 | +0.1539 | 0.0772 | Minimal (<0.10) |
| 15 | `vesselness_ratio` | Differential Geometry / Hessian | 0.1119 | 0.0596 | -0.0575 | 0.0492 | Minimal (<0.10) |

---

## 3. Class-Conditional Shift Analysis (Positives vs Negatives)

| Feature | Family | Positives $W_d$ | Positives KS | Positives PSI | Negatives $W_d$ | Negatives KS | Negatives PSI | Dominant Drift Class |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `H0_entropy` | Topological Persistence | 0.4084 | 0.1750 | 0.1739 | 0.5881 | 0.2695 | 0.3601 | **Negatives** ($\Delta = +0.180$) |
| `fractal_dimension` | Fractal Complexity | 0.1313 | 0.0633 | 0.0357 | 0.5781 | 0.2724 | 0.3082 | **Negatives** ($\Delta = +0.447$) |
| `quantum_eigenvalue_0` | Quantum Graph Laplacian | 0.1230 | 0.1037 | 0.1412 | 0.5196 | 0.2826 | 0.4785 | **Negatives** ($\Delta = +0.397$) |
| `quantum_eigenvalue_1` | Quantum Graph Laplacian | 0.1237 | 0.1010 | 0.1532 | 0.5055 | 0.2803 | 0.4423 | **Negatives** ($\Delta = +0.382$) |
| `quantum_eigenvalue_2` | Quantum Graph Laplacian | 0.1190 | 0.0975 | 0.1407 | 0.4964 | 0.2820 | 0.4136 | **Negatives** ($\Delta = +0.377$) |
| `H0_total_persistence` | Topological Persistence | 0.2461 | 0.1603 | 0.1715 | 0.4805 | 0.2612 | 0.3408 | **Negatives** ($\Delta = +0.234$) |
| `H1_count` | Topological Persistence | 0.2420 | 0.1996 | 0.1811 | 0.4718 | 0.2736 | 0.4062 | **Negatives** ($\Delta = +0.230$) |
| `H1_total_persistence` | Topological Persistence | 0.2419 | 0.2002 | 0.1803 | 0.4714 | 0.2750 | 0.4063 | **Negatives** ($\Delta = +0.230$) |
| `blobness_ratio` | Differential Geometry / Hessian | 0.1194 | 0.0630 | 0.0537 | 0.4513 | 0.1505 | 0.1540 | **Negatives** ($\Delta = +0.332$) |
| `hessian_L2` | Differential Geometry / Hessian | 0.4444 | 0.1946 | 0.3788 | 0.4068 | 0.2498 | 0.3877 | Balanced |
| `hessian_L3` | Differential Geometry / Hessian | 0.4240 | 0.1880 | 0.3351 | 0.3826 | 0.2329 | 0.3030 | Balanced |
| `lacunarity_4` | Fractal Complexity | 0.2771 | 0.1673 | 0.1272 | 0.2539 | 0.1429 | 0.1458 | Balanced |
| `vesselness_ratio` | Differential Geometry / Hessian | 0.1957 | 0.0991 | 0.0966 | 0.1754 | 0.0929 | 0.0811 | Balanced |
| `hessian_L1` | Differential Geometry / Hessian | 0.3973 | 0.1792 | 0.2771 | 0.1620 | 0.0814 | 0.0784 | **Positives** ($\Delta = +0.235$) |
| `lacunarity_8` | Fractal Complexity | 0.2179 | 0.1419 | 0.2189 | 0.1277 | 0.0553 | 0.0972 | Balanced |

---

## 4. Agreement-Level Stratification (`AgrLevel` 0 to 3)

Features compared against corresponding LUNA16 Development class:

| Agreement Tier | Clinical Meaning | Findings ($N$) | Avg Feature $W_d$ | Max Shifting Feature ($W_d$) | Top Shift Family |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `AgrLevel 0` | Non-nodule consensus | 322 | 0.4047 | `H0_entropy` (0.5881) | Topological Persistence |
| `AgrLevel 1` | Solitary radiologist positive | 414 | 0.2767 | `hessian_L2` (0.5113) | Differential Geometry / Hessian |
| `AgrLevel 2` | Two radiologists positive | 130 | 0.2298 | `H0_entropy` (0.3995) | Topological Persistence |
| `AgrLevel 3` | Three+ consensus positive | 33 | 0.2251 | `blobness_ratio` (0.3782) | Differential Geometry / Hessian |

---

## 5. In-Domain Baseline Control (LUNA16 Dev vs LUNA16 Val)

To confirm that the LUNA16 validation cohort did not suffer from similar distribution drift, we compare Subsets 0–5 vs Subsets 6–9:

| Feature | Norm Wasserstein ($W_d$) | KS Stat ($D$) | Cohen's $d$ | PSI |
| :--- | :---: | :---: | :---: | :---: |
| `H0_entropy` | 0.0565 | 0.0438 | +0.0276 | 0.0242 |
| `hessian_L1` | 0.0552 | 0.0475 | +0.0483 | 0.0241 |
| `blobness_ratio` | 0.0532 | 0.0382 | +0.0518 | 0.0080 |
| `H0_total_persistence` | 0.0490 | 0.0396 | +0.0127 | 0.0226 |
| `vesselness_ratio` | 0.0485 | 0.0313 | -0.0397 | 0.0314 |

> **Takeaway**: In-domain drift within LUNA16 is negligible ($W_d \le 0.063$, $\text{PSI} < 0.05$), validating that the v3.1 feature extractor is mathematically consistent across scans when the acquisition distribution and candidate generation mechanisms are matched.

---

## 6. Actionable Diagnostic Roadmap for Stage 8.1

Based on these empirical distributions, the transfer diagnosis roadmap proceeds as follows:
1. **Scanner & Acquisition Parameter Correlation (Stage 8.1)**: Join LNDb Folds 0–2 findings with `LNDbAcqParams.csv` to test whether Hessian curvature shifts or topological shifts track reconstruction kernels, slice spacing, or scanner models.
2. **Negative Definition Investigation**: Evaluate how radiologist non-nodules differ geometrically from CAD candidates, using scan-level clustered observations.
3. **Exclusion of Fold 3**: LNDb Fold 3 ($N=320$) remains excluded from exploratory correlation analyses to prevent repetitive tuning exposure.
