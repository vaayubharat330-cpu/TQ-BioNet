import matplotlib.pyplot as plt
import numpy as np

def make_enhanced_charts():
    # Chart 1: Per-Subset and External Slice-Thickness Evaluation
    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=300)
    
    cohorts = [
        'Subset 6\n(N=258, Thin)', 
        'Subset 7\n(N=222, Thin)', 
        'Subset 8\n(N=236, Thin)', 
        'Subset 9\n(N=210, Thin)', 
        'Combined LUNA16\n(N=926, Thin)', 
        'External Cohort\n(N=248, Thick Slice)'
    ]
    accuracies = [86.43, 88.29, 84.32, 86.19, 86.29, 72.98]
    specificities = [89.92, 91.89, 88.98, 92.38, 90.71, 81.96]

    x = np.arange(len(cohorts))
    width = 0.35

    rects1 = ax.bar(x - width/2, accuracies, width, label='Accuracy (%)', color='#1E88E5', edgecolor='black', linewidth=0.8)
    rects2 = ax.bar(x + width/2, specificities, width, label='Specificity (%)', color='#43A047', edgecolor='black', linewidth=0.8)

    ax.set_ylabel('Performance Score (%)', fontsize=10, fontweight='bold')
    ax.set_title('Empirical Classification Accuracy & Specificity Across Tested Cohorts & Slice Thicknesses', fontsize=11, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(cohorts, fontsize=8.5, fontweight='bold')
    ax.set_ylim(50, 105)
    ax.legend(loc='lower left', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

    plt.tight_layout()
    out_path = r'c:\Users\suraj\Desktop\4th yr project\fig4_accuracy_comparison.png'
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Enhanced comparison chart generated at:", out_path)

if __name__ == '__main__':
    make_enhanced_charts()
