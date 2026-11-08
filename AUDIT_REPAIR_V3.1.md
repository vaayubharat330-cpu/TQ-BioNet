# TQ-BioNet v3.1 Audit and Repair Notes

## Scope and status

This branch contains targeted correctness, numerical-safety, dependency, and scientific-reporting repairs based on source inspection. It is not a claim that the full LUNA16 or LNDb experiments have been rerun. The datasets are not part of the repository, and fresh cache generation plus full validation must be performed by the project owner.

The v3.0 freeze document and historical outputs are retained. v3.1 is a separate repair line; do not overwrite historical v3.0 metrics or describe them as reproduced v3.1 results.

## Changes made

- Hardened the Schrödinger-inspired sparse eigensolver: validates cubic finite inputs, parameter ranges and eigenvalue count; caps sparse eigenvalue requests below matrix dimension; handles partial ARPACK convergence explicitly; and handles fewer than three returned states without indexing errors.
- Hardened the feature pipeline and Hessian input validation; invalid/non-finite feature vectors now fail explicitly instead of entering model training silently.
- Hardened fractal descriptors for malformed, empty, and small masks. Lacunarity uses a padded single window when the requested box is larger than the volume rather than taking the mean of an empty array.
- Hardened point-cloud persistence inputs. Infinite-death essential classes are no longer assigned an arbitrary fabricated finite death; finite-bar summaries explicitly exclude them.
- Added missing direct dependencies used by imports: scikit-image, ripser, persim, and pydicom.
- Fixed the subset-6 audit SVM scaling inconsistency: SVM training and prediction now both use development-fitted StandardScaler parameters, including the seed sensitivity run.
- Removed hard-coded PASS claims from the subset-6 audit report. SeriesUID separation is labelled accurately and is not represented as proof of patient-level independence.
- Disabled the legacy LNDb validation entry point pending a valid frozen-model external pipeline. The old script used mismatched preprocessing, native-spacing patches, a different model configuration, and a non-empirical ROC curve. Continuing to emit those metrics would be misleading.
- Updated README claims to describe the implemented algorithms accurately and labelled historical metrics as not yet revalidated.

## Critical remaining scientific / data requirements

1. **Patient identity:** current cached `groups` are SeriesUID values. Patient-level independence cannot be claimed without a verified SeriesUID-to-patient mapping.
2. **LNDb external test:** implement a single shared resampling, patch extraction, normalization, 15-feature schema, and model artifact path. Validate LNDb annotation semantics and units before defining labels. Do not fit or tune on LNDb.
3. **Model scaling contract:** training and inference must load the same development-fitted scaler artifact for SVM. Tree models must use their documented raw-feature path. Persist and validate feature names/order with every model artifact.
4. **Cache integrity:** cache manifests should hash X, y, groups, coordinates, feature-name schema, preprocessing config and code/feature version. Validate shapes, dtypes, labels, finite values, subset ID, and hashes before concatenation.
5. **Subset orchestration:** processing must fail-fast if any required development subset fails; never retrain on a partial 0–5 cohort and label it complete.
6. **Coordinate geometry:** verify all world-to-voxel transforms use image direction cosines as well as origin and spacing, especially for oblique scans.
7. **Confidence intervals:** use scan/cluster-level resampling where multiple candidate patches come from the same scan; ordinary candidate-level bootstrap can understate uncertainty.
8. **Calibration:** probability averaging is not calibration. If calibrated probabilities are required, fit calibration using development-only cross-validation and report Brier score / calibration curves on held-out data.
9. **Feature semantics:** the Hessian descriptor is a center-voxel, single-scale Hessian eigenvalue summary, not multi-scale Frangi vesselness. The persistence descriptor is point-cloud Vietoris–Rips persistence, not voxel sublevel persistence.
10. **Clinical interpretation:** candidate-level classification is not a patient-level diagnosis and is not a clinical device validation.

## Required owner-side validation before using results

- Install dependencies in a clean environment.
- Run unit tests and static checks.
- Remove only versioned v3.0 feature caches after backing up the original manifests/results.
- Regenerate all required caches using one consistent pipeline.
- Verify all six development subsets are present and valid before fitting.
- Re-run independent validation on subsets 6–9 with frozen development-only artifacts and a verified split manifest.
- Keep LNDb blocked until the external pipeline requirements above are satisfied.
- Recompute every reported metric and figure from saved predictions; do not manually construct ROC/PR curves.
