import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve, auc
from scipy.stats import binom, chi2

def compute_wilson_ci(successes, total, confidence=0.95):
    """
    Computes the Wilson Score Interval for a binary proportion metric
    (Accuracy, Sensitivity, Specificity, Precision).
    """
    if total <= 0:
        return 0.0, 0.0
    p = float(successes) / float(total)
    
    # 95% confidence -> z = 1.96; 99% -> z = 2.576
    if confidence == 0.95:
        z = 1.96
    elif confidence == 0.99:
        z = 2.576
    else:
        # standard normal distribution lookup approximation
        from scipy.stats import norm
        z = norm.ppf(1 - (1 - confidence) / 2)
        
    denominator = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denominator
    spread = z * np.sqrt((p * (1.0 - p)) / total + (z**2) / (4.0 * total**2)) / denominator
    low = max(0.0, center - spread)
    high = min(1.0, center + spread)
    return low, high

def compute_bootstrap_ci(y_true, y_val, metric_func, num_resamples=1000, confidence=0.95, random_seed=42):
    """
    Computes the non-parametric Bootstrap confidence interval for a metric
    (F1-score, ROC AUC) using percentile method.
    """
    y_true = np.array(y_true)
    y_val = np.array(y_val)
    n = len(y_true)
    if n <= 0:
        return 0.0, 0.0
        
    rng = np.random.default_rng(seed=random_seed)
    scores = []
    
    for _ in range(num_resamples):
        boot_idx = rng.choice(n, n, replace=True)
        # Ensure bootstrap sample contains both classes if metric is ROC AUC
        if len(np.unique(y_true[boot_idx])) > 1 or metric_func.__name__ != "roc_auc_score":
            try:
                score = metric_func(y_true[boot_idx], y_val[boot_idx])
                scores.append(score)
            except Exception:
                pass
                
    if len(scores) == 0:
        return 0.0, 0.0
        
    alpha = 1.0 - confidence
    low_pct = 100 * (alpha / 2.0)
    high_pct = 100 * (1.0 - alpha / 2.0)
    
    low = np.percentile(scores, low_pct)
    high = np.percentile(scores, high_pct)
    return low, high

def run_mcnemars_test(y_true, y_pred1, y_pred2):
    """
    Performs McNemar's Test to compare two classifiers.
    If the number of discordant pairs (b + c) is less than 25, it automatically
    applies the Exact Binomial Test (McNemar's Exact Test). Otherwise, it uses the
    asymptotic chi-squared approximation with Yates's continuity correction.
    """
    y_true = np.array(y_true)
    y_pred1 = np.array(y_pred1)
    y_pred2 = np.array(y_pred2)
    
    m1_correct = (y_pred1 == y_true)
    m2_correct = (y_pred2 == y_true)
    
    # b: M1 correct, M2 incorrect
    b = int(np.sum(m1_correct & ~m2_correct))
    # c: M1 incorrect, M2 correct
    c = int(np.sum(~m1_correct & m2_correct))
    
    total_discordant = b + c
    
    if total_discordant == 0:
        stat_name = "Exact Binomial"
        stat_val = 0.0
        p_value = 1.0
    elif total_discordant < 25:
        # McNemar's Exact Test (using cumulative binomial distribution)
        stat_name = "Exact Binomial"
        stat_val = float(min(b, c))
        # Cumulative probability of getting min(b,c) or fewer discordant outcomes out of b+c trials under null hypothesis (p=0.5)
        p_value = 2.0 * binom.cdf(min(b, c), total_discordant, 0.5)
        # Cap p-value at 1.0 (can exceed if min(b,c) is close to half of total)
        p_value = min(1.0, p_value)
    else:
        # McNemar's Asymptotic Test with Yates's correction
        stat_name = "Chi2 (with Yates's correction)"
        stat_val = float(((abs(b - c) - 1.0) ** 2) / total_discordant)
        p_value = float(chi2.sf(stat_val, 1))
        
    return {
        'b_discordant': b,
        'c_discordant': c,
        'total_discordant': total_discordant,
        'test_type': stat_name,
        'statistic': stat_val,
        'p_value': p_value,
        'statistically_significant': bool(p_value < 0.05)
    }

def plot_roc_pr_curves(y_test, svm_probs, xgb_probs, save_path_roc, save_path_pr):
    """
    Generates and saves the ROC and Precision-Recall curves comparing SVM and XGBoost.
    """
    # 1. Plot ROC Curve
    plt.figure(figsize=(7, 6))
    
    # SVM ROC
    fpr_svm, tpr_svm, _ = roc_curve(y_test, svm_probs)
    auc_svm = auc(fpr_svm, tpr_svm)
    plt.plot(fpr_svm, tpr_svm, label=f'SVM (AUC = {auc_svm:.4f})', color='darkorange', lw=2)
    
    # XGBoost ROC
    fpr_xgb, tpr_xgb, _ = roc_curve(y_test, xgb_probs)
    auc_xgb = auc(fpr_xgb, tpr_xgb)
    plt.plot(fpr_xgb, tpr_xgb, label=f'XGBoost (AUC = {auc_xgb:.4f})', color='navy', lw=2)
    
    # Diagonal baseline
    plt.plot([0, 1], [0, 1], color='gray', lw=1.5, linestyle='--')
    
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate (1 - Specificity)', fontsize=11)
    plt.ylabel('True Positive Rate (Sensitivity)', fontsize=11)
    plt.title('Receiver Operating Characteristic (ROC) Curve', fontsize=12, fontweight='bold')
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path_roc, dpi=300)
    plt.close()
    
    # 2. Plot Precision-Recall Curve
    plt.figure(figsize=(7, 6))
    
    # SVM PR
    precision_svm, recall_svm, _ = precision_recall_curve(y_test, svm_probs)
    pr_auc_svm = auc(recall_svm, precision_svm)
    plt.plot(recall_svm, precision_svm, label=f'SVM (PR-AUC = {pr_auc_svm:.4f})', color='darkorange', lw=2)
    
    # XGBoost PR
    precision_xgb, recall_xgb, _ = precision_recall_curve(y_test, xgb_probs)
    pr_auc_xgb = auc(recall_xgb, precision_xgb)
    plt.plot(recall_xgb, precision_xgb, label=f'XGBoost (PR-AUC = {pr_auc_xgb:.4f})', color='navy', lw=2)
    
    # Horizontal baseline representing the positive class ratio
    pos_ratio = np.sum(y_test == 1) / len(y_test)
    plt.plot([0, 1], [pos_ratio, pos_ratio], color='gray', lw=1.5, linestyle='--', label=f'Baseline ({pos_ratio:.2f})')
    
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('Recall (Sensitivity)', fontsize=11)
    plt.ylabel('Precision', fontsize=11)
    plt.title('Precision-Recall (PR) Curve', fontsize=12, fontweight='bold')
    plt.legend(loc="lower left")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path_pr, dpi=300)
    plt.close()
    
    print(f"      Successfully saved ROC curve plot to: {save_path_roc}")
    print(f"      Successfully saved Precision-Recall curve plot to: {save_path_pr}")
