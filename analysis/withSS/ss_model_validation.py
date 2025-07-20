"""
SS Model Validation and Testing

This script provides validation tests and examples for the SS Model implementation.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ss_model import SSModel, ContingencyData, example_usage
from ss_model_integration import SSModelAnalyzer


def validate_ss_model():
    """Validate SS Model implementation against known test cases"""
    
    print("SS Model Validation Tests")
    print("=" * 40)
    
    model = SSModel(alpha=5.0, beta=20.0)
    
    # Test 1: Perfect generative relationship
    print("\nTest 1: Perfect generative relationship")
    perfect_gen = ContingencyData(16, 0, 0, 16, 1)  # a=16, b=0, c=0, d=16
    print(f"  Contingency: a={perfect_gen.a}, b={perfect_gen.b}, c={perfect_gen.c}, d={perfect_gen.d}")
    print(f"  ΔP = {perfect_gen.delta_p:.3f}")
    
    ss_support = model.posterior_support(perfect_gen, use_uniform_prior=False)
    uniform_support = model.posterior_support(perfect_gen, use_uniform_prior=True)
    chi2_support = model.chi_square_support(perfect_gen)
    
    print(f"  SS Support: {ss_support:.3f}")
    print(f"  Uniform Support: {uniform_support:.3f}")
    print(f"  Chi-square: {chi2_support:.3f}")
    
    # Test 2: Perfect preventive relationship
    print("\nTest 2: Perfect preventive relationship")
    perfect_prev = ContingencyData(0, 16, 16, 0, -1)  # a=0, b=16, c=16, d=0
    print(f"  Contingency: a={perfect_prev.a}, b={perfect_prev.b}, c={perfect_prev.c}, d={perfect_prev.d}")
    print(f"  ΔP = {perfect_prev.delta_p:.3f}")
    
    ss_support = model.posterior_support(perfect_prev, use_uniform_prior=False)
    uniform_support = model.posterior_support(perfect_prev, use_uniform_prior=True)
    chi2_support = model.chi_square_support(perfect_prev)
    
    print(f"  SS Support: {ss_support:.3f}")
    print(f"  Uniform Support: {uniform_support:.3f}")
    print(f"  Chi-square: {chi2_support:.3f}")
    
    # Test 3: No relationship (independence)
    print("\nTest 3: No relationship (independence)")
    no_rel = ContingencyData(8, 8, 8, 8, 0)  # a=8, b=8, c=8, d=8
    print(f"  Contingency: a={no_rel.a}, b={no_rel.b}, c={no_rel.c}, d={no_rel.d}")
    print(f"  ΔP = {no_rel.delta_p:.3f}")
    
    ss_support = model.posterior_support(no_rel, use_uniform_prior=False)
    uniform_support = model.posterior_support(no_rel, use_uniform_prior=True)
    chi2_support = model.chi_square_support(no_rel)
    
    print(f"  SS Support: {ss_support:.3f}")
    print(f"  Uniform Support: {uniform_support:.3f}")
    print(f"  Chi-square: {chi2_support:.3f}")
    
    # Test 4: Compare with original MATLAB data
    print("\nTest 4: Original experiment data comparison")
    
    # Data from exp1data.m
    matlab_contingencies = [
        ContingencyData(8, 0, 0, 8, 1),
        ContingencyData(8, 0, 2, 6, 1),
        ContingencyData(16, 48, 0, 64, 1),
        ContingencyData(12, 4, 16, 0, -1),
        ContingencyData(0, 16, 4, 12, -1),
        ContingencyData(4, 12, 16, 0, -1),
    ]
    
    human_judgments = np.array([84.58, 69.26, 43.55, 29.2, 62.5, 91.7])
    
    results = model.analyze_contingencies(matlab_contingencies, human_judgments)
    
    print("\nComparison with MATLAB implementation:")
    print(results[['condition', 'delta_p', 'ss_support', 'uniform_support', 
                  'chi2_support', 'human_judgment']].round(3))
    
    return results


def test_different_parameters():
    """Test SS Model with different parameter values"""
    
    print("\nParameter Sensitivity Analysis")
    print("=" * 40)
    
    # Test contingency
    test_cont = ContingencyData(12, 4, 4, 12, 1)  # Moderate generative
    
    # Test different alpha values
    alphas = [1.0, 2.0, 5.0, 10.0, 20.0]
    betas = [0.0, 5.0, 10.0, 20.0]
    
    results = []
    
    for alpha in alphas:
        for beta in betas:
            model = SSModel(alpha=alpha, beta=beta)
            ss_support = model.posterior_support(test_cont, use_uniform_prior=False)
            
            results.append({
                'alpha': alpha,
                'beta': beta,
                'ss_support': ss_support
            })
    
    param_df = pd.DataFrame(results)
    
    # Plot parameter sensitivity
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    
    for beta in betas:
        subset = param_df[param_df['beta'] == beta]
        ax.plot(subset['alpha'], subset['ss_support'], 
               marker='o', label=f'β = {beta}')
    
    ax.set_xlabel('Alpha (α)')
    ax.set_ylabel('SS Support')
    ax.set_title('Parameter Sensitivity Analysis')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig, param_df


def create_sample_data_analysis():
    """Create analysis of current project sample data"""
    
    print("\nSample Data Analysis")
    print("=" * 40)
    
    try:
        analyzer = SSModelAnalyzer()
        
        # Try to analyze existing data
        sample_results = analyzer.analyze_sample_conditions()
        print(f"Analyzed {len(sample_results)} conditions")
        
        # Show summary
        print("\nSample Analysis Summary:")
        summary = sample_results.groupby('experiment_type')[
            ['delta_p', 'ss_support', 'uniform_support', 'chi2_support', 'human_estimate_mean']
        ].agg(['mean', 'std']).round(3)
        
        print(summary)
        
        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Plot 1: ΔP distribution
        axes[0, 0].hist(sample_results[sample_results['experiment_type'] == 'ex1']['delta_p'], 
                       alpha=0.7, label='Ex1', bins=10)
        axes[0, 0].hist(sample_results[sample_results['experiment_type'] == 'ex2']['delta_p'], 
                       alpha=0.7, label='Ex2', bins=10)
        axes[0, 0].set_xlabel('ΔP')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('ΔP Distribution')
        axes[0, 0].legend()
        
        # Plot 2: SS Support vs Human Estimates
        for exp_type, color in [('ex1', 'blue'), ('ex2', 'red')]:
            subset = sample_results[sample_results['experiment_type'] == exp_type]
            axes[0, 1].scatter(subset['human_estimate_mean'], subset['ss_support'], 
                             c=color, alpha=0.6, label=exp_type)
        axes[0, 1].set_xlabel('Human Estimate Mean')
        axes[0, 1].set_ylabel('SS Support')
        axes[0, 1].set_title('SS Support vs Human Estimates')
        axes[0, 1].legend()
        
        # Plot 3: Model comparison
        models = ['ss_support', 'uniform_support', 'chi2_support']
        model_names = ['SS', 'Uniform', 'Chi2']
        
        x = np.arange(len(sample_results))
        width = 0.25
        
        for i, (model, name) in enumerate(zip(models, model_names)):
            axes[1, 0].bar(x + i*width, sample_results[model], width, 
                          label=name, alpha=0.8)
        
        axes[1, 0].set_xlabel('Condition')
        axes[1, 0].set_ylabel('Support')
        axes[1, 0].set_title('Model Predictions Comparison')
        axes[1, 0].legend()
        
        # Plot 4: Causal Direction Distribution
        direction_counts = sample_results['causal_direction'].value_counts()
        axes[1, 1].bar(['Preventive', 'Unknown', 'Generative'], 
                      [direction_counts.get(-1, 0), direction_counts.get(0, 0), direction_counts.get(1, 0)])
        axes[1, 1].set_ylabel('Count')
        axes[1, 1].set_title('Causal Direction Distribution')
        
        plt.tight_layout()
        return fig, sample_results
        
    except Exception as e:
        print(f"Could not analyze sample data: {e}")
        print("This is expected if the experiment database/CSV files are not available")
        return None, None


def run_all_tests():
    """Run all validation tests"""
    
    print("Running SS Model Validation and Testing")
    print("=" * 50)
    
    # Basic validation
    validation_results = validate_ss_model()
    
    # Parameter sensitivity
    param_fig, param_df = test_different_parameters()
    
    # Sample data analysis (if available)
    sample_fig, sample_results = create_sample_data_analysis()
    
    # Show plots
    plt.show()
    
    print("\nAll tests completed!")
    
    return {
        'validation_results': validation_results,
        'parameter_analysis': param_df,
        'sample_results': sample_results
    }


if __name__ == "__main__":
    # Run all tests
    test_results = run_all_tests()
