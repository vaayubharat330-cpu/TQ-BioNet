import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import warnings
from xgboost import XGBClassifier

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ripser')

from tq_bionet.synthetic_data import generate_synthetic_dataset
from tq_bionet.pipeline import extract_tq_bio_features

def run_feature_analysis():
    print("======================================================================")
    print("            TQ-BioNet Feature Distribution & Importance Analysis       ")
    print("======================================================================\n")
    
    # 1. Generate dataset
    num_pos = 40
    X_raw, y = generate_synthetic_dataset(num_samples_per_class=num_pos)
    
    # 2. Extract features and map subclass names
    print("      Extracting features and mapping subclasses...")
    features_list = []
    
    # Helper to map index to subclass
    def get_subclass_name(idx):
        if idx >= 40:
            return "Vascular Crossing"
        sub_idx = idx % 4
        if sub_idx == 0:
            return "Benign Solid"
        elif sub_idx == 1:
            return "Faint GGO"
        elif sub_idx == 2:
            return "Spiculated"
        else:
            return "Juxta-Vascular"
            
    for i in range(len(X_raw)):
        f_dict, _ = extract_tq_bio_features(X_raw[i])
        f_dict['Subclass'] = get_subclass_name(i)
        f_dict['Label'] = y[i]
        features_list.append(f_dict)
        
    df = pd.DataFrame(features_list)
    # Exclude extra helper columns for statistical analysis
    feature_cols = [c for c in df.columns if c not in ['Subclass', 'Label', 'extraction_time_sec']]
    
    # 3. Print feature statistics by subclass
    print("\n[1/3] FEATURE DISTRIBUTION MEAN STATS BY CLINICAL SUBCLASS")
    print("-" * 105)
    print(f"{'Subclass':<20} | {'Quant Eigen 0':<15} | {'Fractal Dim (Df)':<18} | {'H0 Total Pers':<15} | {'H1 Total Pers':<15} | {'Lacunarity 4':<12}")
    print("-" * 105)
    
    grouped = df.groupby('Subclass')
    for name, group in grouped:
        e0 = group['quantum_eigenvalue_0'].mean()
        df_val = group['fractal_dimension'].mean()
        h0 = group['H0_total_persistence'].mean()
        h1 = group['H1_total_persistence'].mean()
        lac = group['lacunarity_4'].mean()
        print(f"{name:<20} | {e0:<15.4f} | {df_val:<18.4f} | {h0:<15.4f} | {h1:<15.4f} | {lac:<12.4f}")
    print("-" * 105)
    
    # 4. Generate & Save Box Plots
    print("\n[2/3] Generating and saving box plots for key features...")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Box plot for Quantum Eigenvalue 0
    df.boxplot(column='quantum_eigenvalue_0', by='Subclass', ax=axes[0], grid=False, rot=30)
    axes[0].set_title('Quantum Eigenvalue 0', fontweight='bold')
    axes[0].set_xlabel('')
    axes[0].set_ylabel('Eigenvalue Value')
    
    # Box plot for Fractal Dimension
    df.boxplot(column='fractal_dimension', by='Subclass', ax=axes[1], grid=False, rot=30)
    axes[1].set_title('3D Fractal Dimension (Df)', fontweight='bold')
    axes[1].set_xlabel('')
    axes[1].set_ylabel('Dimension Value')
    
    # Box plot for H1 Total Persistence
    df.boxplot(column='H1_total_persistence', by='Subclass', ax=axes[2], grid=False, rot=30)
    axes[2].set_title('H1 Total Persistence (Loops)', fontweight='bold')
    axes[2].set_xlabel('')
    axes[2].set_ylabel('Homology Persistence')
    
    plt.suptitle('') # Remove default subplots title
    plt.tight_layout()
    plot_path = "c:\\Users\\suraj\\Desktop\\4th yr project\\tq_bionet\\feature_distributions.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    # 5. Statistical Significance Tests & Effect Sizes (Mann-Whitney U with Cliff's Delta & Holm-Bonferroni correction)
    print("\n[2.5/3] Running Mann-Whitney U test with Cliff's Delta effect size...")
    from scipy.stats import mannwhitneyu
    
    def compute_cliffs_delta(pos_vals, neg_vals):
        n1 = len(pos_vals)
        n2 = len(neg_vals)
        greater = 0
        less = 0
        for x in pos_vals:
            for y in neg_vals:
                if x > y:
                    greater += 1
                elif x < y:
                    less += 1
        return (greater - less) / (n1 * n2)
        
    def interpret_cliffs_delta(d):
        ad = abs(d)
        if ad < 0.147:
            return "Negligible"
        elif ad < 0.33:
            return "Small"
        elif ad < 0.474:
            return "Medium"
        else:
            return "Large"
            
    positives = df[df['Label'] == 1]
    negatives = df[df['Label'] == 0]
    test_features = ['quantum_eigenvalue_0', 'fractal_dimension', 'H1_total_persistence', 'lacunarity_4']
    
    raw_p_vals = []
    u_stats = []
    deltas = []
    
    for feat in test_features:
        stat, p_val = mannwhitneyu(positives[feat], negatives[feat], alternative='two-sided')
        delta = compute_cliffs_delta(positives[feat].values, negatives[feat].values)
        raw_p_vals.append(p_val)
        u_stats.append(stat)
        deltas.append(delta)
        
    # Apply Holm-Bonferroni correction
    sorted_indices = np.argsort(raw_p_vals)
    k = len(test_features)
    corrected_p_vals = [0.0] * k
    prev_p = 0.0
    for rank, idx in enumerate(sorted_indices):
        raw_p = raw_p_vals[idx]
        adj_p = min(raw_p * (k - rank), 1.0)
        adj_p = max(adj_p, prev_p)
        corrected_p_vals[idx] = adj_p
        prev_p = adj_p
        
    print("-" * 115)
    print(f"{'Feature Name':<25} | {'U Stat':<10} | {'Raw p-value':<12} | {'Holm-Adj p-val':<15} | {'Cliff delta':<12} | {'Effect Size'}")
    print("-" * 115)
    for i, feat in enumerate(test_features):
        eff_str = interpret_cliffs_delta(deltas[i])
        print(f"{feat:<25} | {u_stats[i]:<10.1f} | {raw_p_vals[i]:<12.4e} | {corrected_p_vals[i]:<15.4e} | {deltas[i]:<12.4f} | {eff_str}")
    print("-" * 115)
    
    # 6. XGBoost Feature Importance
    print("\n[3/3] Training XGBoost for feature importance analysis...")
    X = df[feature_cols].values
    y = df['Label'].values
    
    xgb = XGBClassifier(eval_metric='logloss', random_state=42)
    xgb.fit(X, y)
    
    importances = xgb.feature_importances_
    importance_df = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False)
    
    print("\nXGBOOST FEATURE IMPORTANCE RANKING:")
    print("-" * 45)
    print(f"{'Feature Name':<30} | {'Importance Score':<15}")
    print("-" * 45)
    for idx, row in importance_df.head(10).iterrows():
        print(f"{row['Feature']:<30} | {row['Importance']:.4f}")
    print("-" * 45)
    print("======================================================================\n")

if __name__ == "__main__":
    run_feature_analysis()
