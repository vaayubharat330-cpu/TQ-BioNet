import numpy as np
import warnings

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.synthetic_data import generate_synthetic_dataset
from tq_bionet.pipeline import extract_tq_bio_features

def run_robustness_study():
    print("======================================================================")
    print("                TQ-BioNet Biophysical Robustness Study                ")
    print("======================================================================\n")
    
    # 1. Generate clean dataset (20 samples for faster study execution)
    print("Generating clean baseline patches...")
    X_raw, _ = generate_synthetic_dataset(num_samples_per_class=10)
    
    # 2. Extract baseline features
    print("Extracting baseline features...")
    baseline_features = []
    for patch in X_raw:
        _, f_vec = extract_tq_bio_features(patch)
        baseline_features.append(f_vec)
    baseline_features = np.array(baseline_features)
    
    # Noise levels to evaluate (standard deviation of Gaussian noise added to raw voxels [0, 1])
    noise_levels = [0.01, 0.05, 0.10]
    
    print("\nStress-testing biophysical features under Gaussian noise:")
    print("-" * 74)
    print(f"{'Noise Level (Std Dev)':<25} | {'Mean Absolute Percentage Error (MAPE) on Features'}")
    print("-" * 74)
    
    rng = np.random.default_rng(seed=42)
    
    for noise in noise_levels:
        noise_features = []
        for patch in X_raw:
            # Add Gaussian noise and clip to keep in HU bounds [0, 1]
            noisy_patch = np.clip(patch + rng.normal(0, noise, size=patch.shape), 0.0, 1.0)
            _, f_vec = extract_tq_bio_features(noisy_patch)
            noise_features.append(f_vec)
            
        noise_features = np.array(noise_features)
        
        # Calculate MAPE (Mean Absolute Percentage Error) relative to baseline
        # Add epsilon to prevent division by zero for features close to 0
        eps = 1e-5
        percentage_errors = np.abs((noise_features - baseline_features) / (np.abs(baseline_features) + eps))
        
        # Average over all samples and features
        mean_mape = np.mean(percentage_errors) * 100
        
        print(f"Gaussian std = {noise:<12.2f} | {mean_mape:.2f}% MAPE")
    print("-" * 74)
    
    # 3. Analyze component-wise stability under heavy noise (std = 0.05)
    print("\nStability Analysis by Feature Group under Medium Noise (std = 0.05):")
    print("-" * 60)
    print(f"{'Feature Group':<25} | {'Group MAPE (%)':<15}")
    print("-" * 60)
    
    # Formulate noisy data for std = 0.05
    noisy_patch_list = [np.clip(p + rng.normal(0, 0.05, size=p.shape), 0.0, 1.0) for p in X_raw]
    noise_features_05 = []
    for np_patch in noisy_patch_list:
        _, f_vec = extract_tq_bio_features(np_patch)
        noise_features_05.append(f_vec)
    noise_features_05 = np.array(noise_features_05)
    
    # Extract keys list to get boundaries
    dummy_dict, _ = extract_tq_bio_features(X_raw[0])
    feature_keys = sorted([k for k in dummy_dict.keys() if k != 'extraction_time_sec'])
    
    group_indices = {
        "Wave Eigenvalues (10)": [i for i, k in enumerate(feature_keys) if 'quantum' in k],
        "Topological Homology (12)": [i for i, k in enumerate(feature_keys) if 'H0_' in k or 'H1_' in k],
        "Fractal Complexity (4)": [i for i, k in enumerate(feature_keys) if 'fractal' in k or 'lacunarity' in k]
    }
    
    eps = 1e-5
    for group_name, indices in group_indices.items():
        base_grp = baseline_features[:, indices]
        noise_grp = noise_features_05[:, indices]
        
        grp_mape = np.mean(np.abs((noise_grp - base_grp) / (np.abs(base_grp) + eps))) * 100
        print(f"{group_name:<25} | {grp_mape:.2f}% MAPE")
    print("-" * 60)
    print("======================================================================\n")

if __name__ == "__main__":
    run_robustness_study()
