import numpy as np
import time
import warnings
from sklearn.svm import SVC
from xgboost import XGBClassifier

# Suppress ripser column-to-row warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.synthetic_data import make_ggo_nodule
from tq_bionet.quantum_module import solve_schrodinger_equation
from tq_bionet.topological_module import extract_point_cloud, compute_persistence_features
from tq_bionet.fractal_module import extract_fractal_features
from tq_bionet.pipeline import extract_tq_bio_features

def run_benchmark(num_iterations=50):
    print("======================================================================")
    print("               TQ-BioNet Component Runtime Benchmark                  ")
    print("======================================================================\n")
    
    # 1. Generate a test patch
    print("Generating standard GGO Nodule test patch...")
    patch = make_ggo_nodule()
    
    # Pre-extract once to compile/warm up caches
    print("Warming up components...")
    # Downsample once (all pipeline operations run on downsampled coordinates)
    from skimage.transform import resize
    working_patch = resize(patch, (16, 16, 16), mode='reflect', anti_aliasing=True)
    
    # Schrödinger
    _, _, prob_density = solve_schrodinger_equation(working_patch)
    # TDA
    pc = extract_point_cloud(prob_density)
    compute_persistence_features(pc)
    # Fractal
    extract_fractal_features(prob_density)
    
    # 2. Benchmark individual modules
    # Component A: Quantum Wave Mechanics
    wave_times = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        solve_schrodinger_equation(working_patch, mass_coef=1.0, potential_scale=100.0)
        wave_times.append(time.perf_counter() - t0)
        
    # Pre-calculate probability density for TDA and Fractal benchmarks
    _, _, prob_density = solve_schrodinger_equation(working_patch)
    
    # Component B: Persistent Homology (TDA)
    topo_times = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        pc = extract_point_cloud(prob_density, max_points=400)
        compute_persistence_features(pc)
        topo_times.append(time.perf_counter() - t0)
        
    # Component C: Fractal Analysis
    fractal_times = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        extract_fractal_features(prob_density)
        fractal_times.append(time.perf_counter() - t0)
        
    # Component D: Complete Pipeline extraction
    total_extract_times = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        extract_tq_bio_features(patch)
        total_extract_times.append(time.perf_counter() - t0)
        
    # Component E: Classifier Inference
    # Mock feature vector
    f_vec = np.random.randn(1, 26)
    
    # Train mock models
    X_mock = np.random.randn(100, 26)
    y_mock = np.random.randint(0, 2, size=100)
    
    svm = SVC(probability=True)
    svm.fit(X_mock, y_mock)
    
    xgb = XGBClassifier(eval_metric='logloss')
    xgb.fit(X_mock, y_mock)
    
    svm_times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        svm.predict_proba(f_vec)
        svm_times.append(time.perf_counter() - t0)
        
    xgb_times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        xgb.predict_proba(f_vec)
        xgb_times.append(time.perf_counter() - t0)
        
    # Calculate stats
    def calc_stats(t_list):
        arr = np.array(t_list) * 1000 # Convert to milliseconds
        return np.mean(arr), np.std(arr)
        
    wave_mean, wave_std = calc_stats(wave_times)
    topo_mean, topo_std = calc_stats(topo_times)
    frac_mean, frac_std = calc_stats(fractal_times)
    tot_mean, tot_std = calc_stats(total_extract_times)
    svm_mean, svm_std = calc_stats(svm_times)
    xgb_mean, xgb_std = calc_stats(xgb_times)
    
    print("\n======================================================================")
    # Print Markdown table ready for the report
    print("| Component / Operation | Mean Time (ms) | Std Dev (ms) | Description |")
    print("| :--- | :---: | :---: | :--- |")
    print(f"| **Wave Mechanics (Schrödinger)** | {wave_mean:.2f} ms | {wave_std:.2f} ms | Downsampled (16x16x16) eigenvalue solver |")
    print(f"| **Persistent Homology (TDA)** | {topo_mean:.2f} ms | {topo_std:.2f} ms | Sublevel filtration of top 400 coordinates |")
    print(f"| **Fractal Analysis (Df & Lac)** | {frac_mean:.2f} ms | {frac_std:.2f} ms | 3D box-counting and multiscale lacunarity |")
    print(f"| **Total Feature Extraction** | {tot_mean:.2f} ms | {tot_std:.2f} ms | Combined extraction pipeline |")
    print(f"| **SVM Classifier Inference** | {svm_mean:.4f} ms | {svm_std:.4f} ms | Prediction probability mapping |")
    print(f"| **XGBoost Classifier Inference** | {xgb_mean:.4f} ms | {xgb_std:.4f} ms | Forest ensemble decision trees prediction |")
    print("======================================================================\n")

if __name__ == "__main__":
    run_benchmark()
