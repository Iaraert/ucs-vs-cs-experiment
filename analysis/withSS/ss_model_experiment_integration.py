"""
SS Model Integration with Current Experiment Analysis

This script integrates the SS Model results with the existing experimental analysis
to provide deeper insights into human causal learning patterns.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from ss_model_utils import add_ss_metrics_to_dataframe, compare_metrics
from pathlib import Path

def analyze_ss_model_performance():
    """
    Analyze SS Model performance based on the example results
    """
    
    # Example results from the validation
    example_results = {
        'condition': [1, 2, 3, 4, 5, 6],
        'delta_p': [1.00, 0.75, 0.25, -0.25, -0.25, -0.75],
        'ss_support': [None, None, None, None, None, None],  # Will calculate
        'uniform_support': [None, None, None, None, None, None],
        'chi2_support': [16.000, 9.600, 18.286, 4.571, 4.571, 19.200],
        'human_judgment': [84.58, 69.26, 43.55, 29.20, 62.50, 91.70],
        'causal_direction': [1, 1, 1, -1, -1, -1]  # generative=1, preventive=-1
    }
    
    df_example = pd.DataFrame(example_results)
    
    print("SS Model Performance Analysis")
    print("=" * 50)
    
    # Model correlations from the results
    correlations = {
        'SS Support': {'r': 0.737, 'gamma': 0.229},
        'Uniform Support': {'r': 0.677, 'gamma': 0.100}, 
        'Chi-square Support': {'r': 0.544, 'gamma': 0.100}
    }
    
    print("\n1. Model Performance Ranking:")
    for i, (model, stats) in enumerate(sorted(correlations.items(), 
                                            key=lambda x: x[1]['r'], reverse=True), 1):
        print(f"   {i}. {model}: r = {stats['r']:.3f} (γ = {stats['gamma']:.3f})")
    
    # Analyze patterns
    print("\n2. Causal Pattern Analysis:")
    
    # Generative conditions (positive ΔP)
    gen_conditions = df_example[df_example['delta_p'] > 0]
    print(f"\n   Generative Conditions (n={len(gen_conditions)}):")
    print(f"   ΔP range: {gen_conditions['delta_p'].min():.2f} to {gen_conditions['delta_p'].max():.2f}")
    print(f"   Human judgment range: {gen_conditions['human_judgment'].min():.2f} to {gen_conditions['human_judgment'].max():.2f}")
    
    # Preventive conditions (negative ΔP)  
    prev_conditions = df_example[df_example['delta_p'] < 0]
    print(f"\n   Preventive Conditions (n={len(prev_conditions)}):")
    print(f"   ΔP range: {prev_conditions['delta_p'].min():.2f} to {prev_conditions['delta_p'].max():.2f}")
    print(f"   Human judgment range: {prev_conditions['human_judgment'].min():.2f} to {prev_conditions['human_judgment'].max():.2f}")
    
    # Interesting case: Same ΔP, different judgments
    same_deltap = df_example[df_example['delta_p'] == -0.25]
    if len(same_deltap) > 1:
        print(f"\n3. Same ΔP (-0.25), Different Judgments:")
        for _, row in same_deltap.iterrows():
            print(f"   Condition {int(row['condition'])}: Human judgment = {row['human_judgment']:.2f}")
        
        judgment_diff = same_deltap['human_judgment'].max() - same_deltap['human_judgment'].min()
        print(f"   Judgment difference: {judgment_diff:.2f} points")
        print("   → This suggests factors beyond ΔP influence human causal judgments")
    
    return df_example, correlations


def integrate_with_experiment_data():
    """
    Integrate SS Model with actual experiment data
    """
    
    print("\n4. Integration with Experiment Data:")
    print("-" * 40)
    
    # Try to load experiment data
    data_files = [
        'final_valid.csv',
        'final_valid_6_samples.csv', 
        'merged.csv'
    ]
    
    df = None
    for file_path in data_files:
        if Path(file_path).exists():
            try:
                df = pd.read_csv(file_path)
                print(f"   Loaded data from: {file_path}")
                print(f"   Data shape: {df.shape}")
                break
            except Exception as e:
                print(f"   Failed to load {file_path}: {e}")
    
    if df is None:
        print("   No experiment data found. Using example data for demonstration.")
        return None
    
    # Check for required columns
    required_cols = ['ex1_a', 'ex1_b', 'ex1_c', 'ex1_d', 'ex1_estimate']
    if not all(col in df.columns for col in required_cols):
        print(f"   Missing required columns. Available: {list(df.columns)}")
        return None
    
    # Add SS metrics to experiment data
    print("   Adding SS Model metrics...")
    df_with_ss = add_ss_metrics_to_dataframe(
        df,
        a_col='ex1_a', b_col='ex1_b', 
        c_col='ex1_c', d_col='ex1_d',
        estimate_col='ex1_estimate',
        prefix='ex1_ss_'
    )
    
    # Calculate correlations
    ss_metrics = ['ex1_ss_ss_support', 'ex1_ss_uniform_support', 'ex1_ss_chi2_support']
    correlations_exp = compare_metrics(df_with_ss, 'ex1_estimate', ss_metrics)
    
    print("\n   Correlations with human estimates (Ex1):")
    for metric, corr in correlations_exp.items():
        print(f"   {metric}: r = {corr:.3f}")
    
    return df_with_ss


def compare_with_existing_metrics():
    """
    Compare SS Model with existing project metrics (CS, UCS, etc.)
    """
    
    print("\n5. Comparison with Existing Metrics:")
    print("-" * 40)
    
    # Load basic stats if available
    stats_path = Path('results/basic_stats.csv')
    if stats_path.exists():
        try:
            basic_stats = pd.read_csv(stats_path)
            print(f"   Loaded basic stats: {basic_stats.shape}")
            
            # Show CS and UCS statistics
            cs_stats = basic_stats[basic_stats.iloc[:, 2] == 'CS']
            ucs_stats = basic_stats[basic_stats.iloc[:, 2] == 'UCS']
            
            if not cs_stats.empty:
                print(f"\n   CS metric range: {cs_stats['mean'].min():.3f} to {cs_stats['mean'].max():.3f}")
            if not ucs_stats.empty:
                print(f"   UCS metric range: {ucs_stats['mean'].min():.3f} to {ucs_stats['mean'].max():.3f}")
            
            print("\n   SS Model adds Bayesian perspective to complement existing metrics:")
            print("   - CS/UCS: Frequentist approach")
            print("   - SS Model: Bayesian approach with structured priors")
            print("   - Both capture different aspects of causal reasoning")
            
        except Exception as e:
            print(f"   Error loading basic stats: {e}")
    else:
        print("   Basic stats file not found")


def recommendations_for_further_analysis():
    """
    Provide recommendations for further analysis
    """
    
    print("\n6. Recommendations for Further Analysis:")
    print("-" * 40)
    
    recommendations = [
        "1. Apply SS Model to all experimental conditions in the dataset",
        "2. Compare SS Model predictions across different story contexts",
        "3. Analyze individual differences in alignment with SS vs other models",
        "4. Investigate the role of CRT scores in model fits",
        "5. Examine Phase 1 vs Phase 2 differences using SS Model framework",
        "6. Use SS Model to understand CS vs UCS correlation patterns",
        "7. Apply to cluster analysis to identify distinct reasoning strategies"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print(f"\n   Next steps:")
    print(f"   - Run: python ss_model_integration.py")
    print(f"   - Analyze: python ss_model_validation.py") 
    print(f"   - Integrate with existing analyses using ss_model_utils.py")


def create_ss_integration_visualization():
    """
    Create visualization comparing SS Model with human judgments
    """
    
    # Example data from the results
    conditions = [1, 2, 3, 4, 5, 6]
    delta_p = [1.00, 0.75, 0.25, -0.25, -0.25, -0.75]
    human_judgment = [84.58, 69.26, 43.55, 29.20, 62.50, 91.70]
    chi2_support = [16.000, 9.600, 18.286, 4.571, 4.571, 19.200]
    causal_direction = ['Gen', 'Gen', 'Gen', 'Prev', 'Prev', 'Prev']
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Plot 1: ΔP vs Human Judgment
    ax1 = axes[0, 0]
    colors = ['blue' if d > 0 else 'red' for d in delta_p]
    ax1.scatter(delta_p, human_judgment, c=colors, s=100, alpha=0.7)
    for i, cond in enumerate(conditions):
        ax1.annotate(f'C{cond}', (delta_p[i], human_judgment[i]), 
                    xytext=(5, 5), textcoords='offset points')
    ax1.set_xlabel('ΔP')
    ax1.set_ylabel('Human Judgment')
    ax1.set_title('ΔP vs Human Judgment')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Chi-square vs Human Judgment
    ax2 = axes[0, 1]
    ax2.scatter(chi2_support, human_judgment, c=colors, s=100, alpha=0.7)
    for i, cond in enumerate(conditions):
        ax2.annotate(f'C{cond}', (chi2_support[i], human_judgment[i]),
                    xytext=(5, 5), textcoords='offset points')
    ax2.set_xlabel('Chi-square Support')
    ax2.set_ylabel('Human Judgment')
    ax2.set_title('Chi-square vs Human Judgment')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Model Performance Comparison
    ax3 = axes[1, 0]
    models = ['SS Support', 'Uniform Support', 'Chi-square Support']
    correlations = [0.737, 0.677, 0.544]
    gammas = [0.229, 0.100, 0.100]
    
    bars = ax3.bar(models, correlations, color=['darkblue', 'lightblue', 'gray'], alpha=0.7)
    ax3.set_ylabel('Correlation with Human Judgment')
    ax3.set_title('Model Performance Comparison')
    ax3.set_ylim(0, 1)
    
    # Add gamma values on bars
    for bar, gamma in zip(bars, gammas):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'γ={gamma:.3f}', ha='center', va='bottom', fontsize=9)
    
    plt.xticks(rotation=45)
    
    # Plot 4: Causal Direction Analysis
    ax4 = axes[1, 1]
    gen_judgments = [hj for i, hj in enumerate(human_judgment) if delta_p[i] > 0]
    prev_judgments = [hj for i, hj in enumerate(human_judgment) if delta_p[i] < 0]
    
    ax4.boxplot([gen_judgments, prev_judgments], labels=['Generative', 'Preventive'])
    ax4.set_ylabel('Human Judgment')
    ax4.set_title('Judgment by Causal Direction')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ss_model_integration_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n   Visualization saved: ss_model_integration_analysis.png")
    
    return fig


def main():
    """
    Main analysis function
    """
    
    print("SS Model Integration Analysis")
    print("=" * 60)
    
    # Analyze SS model performance
    example_df, correlations = analyze_ss_model_performance()
    
    # Try to integrate with experiment data
    exp_df = integrate_with_experiment_data()
    
    # Compare with existing metrics
    compare_with_existing_metrics()
    
    # Provide recommendations
    recommendations_for_further_analysis()
    
    # Create visualization
    fig = create_ss_integration_visualization()
    
    print(f"\n" + "=" * 60)
    print("Analysis complete! Key insights:")
    print("- SS Model shows strong predictive power for human causal judgments")
    print("- Structured priors (SS) outperform uniform priors") 
    print("- Same ΔP can lead to different judgments, suggesting complex reasoning")
    print("- Integration with existing project metrics recommended")
    
    return example_df, exp_df, fig


if __name__ == "__main__":
    example_df, exp_df, fig = main()
    plt.show()
