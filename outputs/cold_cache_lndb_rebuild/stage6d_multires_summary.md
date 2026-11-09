# TQ-BioNet Stage 6D: Multi-Resolution Resampling Comparison

This experiment evaluates the frozen v3.1 model bundle (trained on LUNA16 Subsets 0–5) across five isotropic resampling resolutions while holding the physical field of view constant at ~32 mm.

| Spacing | Patch Size | Physical FOV | Accuracy [95% CI] | Sensitivity | Specificity | F1-Score | AUC-ROC [95% CI] | 3-Reader Acc |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1.0mm** | 32^3 | 32.0 mm | 0.5472 [0.515-0.580] | 0.5104 | 0.6098 | 0.5868 | 0.5729 [0.535-0.609] | 0.8182 |
