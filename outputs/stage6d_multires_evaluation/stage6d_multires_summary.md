# TQ-BioNet Stage 6D: Multi-Resolution Resampling Comparison

This experiment evaluates the frozen v3.1 model bundle (trained on LUNA16 Subsets 0–5) across five isotropic resampling resolutions while holding the physical field of view constant at ~32 mm.

| Spacing | Patch Size | Physical FOV | Accuracy [95% CI] | Sensitivity | Specificity | F1-Score | AUC-ROC [95% CI] | 3-Reader Acc |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.8mm** | 40^3 | 32.0 mm | 0.5168 [0.487-0.547] | 0.4635 | 0.6075 | 0.5473 | 0.5499 [0.511-0.587] | 0.8409 |
| **1.0mm** | 32^3 | 32.0 mm | 0.5472 [0.515-0.580] | 0.5104 | 0.6098 | 0.5868 | 0.5729 [0.535-0.609] | 0.8182 |
| **1.25mm** | 26^3 | 32.5 mm | 0.5414 [0.513-0.573] | 0.5130 | 0.5898 | 0.5850 | 0.5658 [0.530-0.600] | 0.8636 |
