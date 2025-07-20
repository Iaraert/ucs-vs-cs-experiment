"""
SS Model (Sparse-Spiky Model) Implementation in Python

This is a Python implementation of the Bayesian causal learning model 
from Lu, Yuille, Liljeholm, Cheng & Holyoak (2008).

The model implements:
1. Bayesian model with SS (Sparse-Spiky) prior
2. Bayesian model with Uniform prior  
3. Chi-square model

Based on the MATLAB code in the SSmodel directory.
"""

import numpy as np
import pandas as pd
from scipy import stats, optimize, integrate
from scipy.special import comb
from dataclasses import dataclass
from typing import Tuple, List, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class ContingencyData:
    """Contingency table data structure"""
    a: int  # N(e+,c+): trials where both e and c are present
    b: int  # N(e-,c+): trials where e is not present but c is
    c: int  # N(e+,c-): trials where e is present but c is not  
    d: int  # N(e-,c-): trials where neither e nor c is present
    causal_direction: int  # 1: generative, -1: preventive, 0: unknown
    
    @property
    def total_trials(self) -> int:
        return self.a + self.b + self.c + self.d
    
    @property
    def p_e_given_c(self) -> float:
        """P(E|C)"""
        if self.a + self.b == 0:
            return 0.0
        return self.a / (self.a + self.b)
    
    @property
    def p_e_given_not_c(self) -> float:
        """P(E|¬C)"""
        if self.c + self.d == 0:
            return 0.0
        return self.c / (self.c + self.d)
    
    @property
    def delta_p(self) -> float:
        """ΔP = P(E|C) - P(E|¬C)"""
        return self.p_e_given_c - self.p_e_given_not_c


class SSModel:
    """SS Model implementation"""
    
    def __init__(self, alpha: float = 5.0, beta: float = 20.0, 
                 integration_precision: float = 1e-10):
        """
        Initialize SS Model
        
        Args:
            alpha: Parameter for SS prior (default: 5.0)
            beta: Parameter for S+ prior (default: 20.0)  
            integration_precision: Precision for numerical integration
        """
        self.alpha = alpha
        self.beta = beta
        self.integration_precision = integration_precision
        
    def nchoosek(self, n: int, k: int) -> float:
        """Binomial coefficient: n choose k"""
        if k > n or k < 0:
            return 0.0
        return comb(n, k, exact=False)
    
    def ss_prior(self, w0: float, w1: float, alpha: float, beta: float) -> float:
        """
        SS+ prior distribution
        
        Args:
            w0: Background cause strength
            w1: Focal cause strength  
            alpha: SS prior parameter
            beta: S+ prior parameter
            
        Returns:
            Prior probability density
        """
        # SS prior: spike at (0,1) and (1,0) for generative
        # or spike at (1,1) for preventive
        term1 = np.exp(-alpha * (1 - w0) - alpha * w1)
        term2 = np.exp(-alpha * w0 - alpha * (1 - w1))
        if beta > 0:
            # S+ component
            term3 = np.exp(-beta * w1)
            return term1 + term2 + term3
        else:
            return term1 + term2
    
    def uniform_prior(self, w0: float, w1: float) -> float:
        """Uniform prior over [0,1] x [0,1]"""
        return 1.0
    
    def likelihood(self, contingency: ContingencyData, w0: float, w1: float) -> float:
        """
        Likelihood function based on noisy-OR or noisy-AND-NOT model
        
        Args:
            contingency: Contingency table data
            w0: Background cause strength
            w1: Focal cause strength
            
        Returns:
            Likelihood value
        """
        a, b, c, d = contingency.a, contingency.b, contingency.c, contingency.d
        direction = contingency.causal_direction
        
        # Total trials for each cell type
        n_ec = a + b  # trials with cause present
        n_e_not_c = c + d  # trials with cause absent
        
        if direction == 1:  # Generative case (noisy-OR)
            # P(E|C) = 1 - (1-w0)(1-w1)
            # P(E|¬C) = w0
            p_e_given_c = 1 - (1 - w0) * (1 - w1)
            p_e_given_not_c = w0
        elif direction == -1:  # Preventive case (noisy-AND-NOT)
            # P(E|C) = w0 * (1-w1)  
            # P(E|¬C) = w0
            p_e_given_c = w0 * (1 - w1)
            p_e_given_not_c = w0
        else:  # Unknown direction
            # Average over both possibilities
            p_e_given_c_gen = 1 - (1 - w0) * (1 - w1)
            p_e_given_c_prev = w0 * (1 - w1)
            p_e_given_c = 0.5 * (p_e_given_c_gen + p_e_given_c_prev)
            p_e_given_not_c = w0
        
        # Binomial likelihoods
        if n_ec > 0:
            like_ec = self.nchoosek(n_ec, a) * (p_e_given_c ** a) * ((1 - p_e_given_c) ** b)
        else:
            like_ec = 1.0
            
        if n_e_not_c > 0:
            like_e_not_c = self.nchoosek(n_e_not_c, c) * (p_e_given_not_c ** c) * ((1 - p_e_given_not_c) ** d)
        else:
            like_e_not_c = 1.0
        
        return like_ec * like_e_not_c
    
    def posterior_support(self, contingency: ContingencyData, 
                         use_uniform_prior: bool = False) -> float:
        """
        Calculate Bayesian causal support (log likelihood ratio)
        
        Args:
            contingency: Contingency table data
            use_uniform_prior: Whether to use uniform instead of SS prior
            
        Returns:
            Log support value
        """
        prior_func = self.uniform_prior if use_uniform_prior else self.ss_prior
        
        # Define integration bounds
        bounds = [(0, 1), (0, 1)]  # w0, w1 both in [0,1]
        
        # Marginal likelihood under causal model (H1)
        def integrand_h1(params):
            w0, w1 = params
            if use_uniform_prior:
                prior = self.uniform_prior(w0, w1)
            else:
                prior = self.ss_prior(w0, w1, self.alpha, self.beta)
            like = self.likelihood(contingency, w0, w1)
            return prior * like
        
        # Marginal likelihood under independence model (H0: w1 = 0)
        def integrand_h0(w0):
            if use_uniform_prior:
                prior = self.uniform_prior(w0, 0)
            else:
                prior = self.ss_prior(w0, 0, self.alpha, self.beta)
            like = self.likelihood(contingency, w0, 0)
            return prior * like
        
        try:
            # Numerical integration
            result_h1, _ = integrate.dblquad(
                lambda w1, w0: integrand_h1([w0, w1]),
                0, 1,  # w0 bounds
                lambda w0: 0, lambda w0: 1,  # w1 bounds
                epsabs=self.integration_precision
            )
            
            result_h0, _ = integrate.quad(
                integrand_h0, 0, 1,
                epsabs=self.integration_precision
            )
            
            if result_h1 <= 0 or result_h0 <= 0:
                return 0.0
                
            support = np.log(result_h1 / result_h0)
            return support
            
        except Exception as e:
            print(f"Integration error: {e}")
            return 0.0
    
    def chi_square_support(self, contingency: ContingencyData) -> float:
        """
        Chi-square model for causal support
        
        Args:
            contingency: Contingency table data
            
        Returns:
            Chi-square statistic
        """
        a, b, c, d = contingency.a, contingency.b, contingency.c, contingency.d
        
        # Create 2x2 contingency table
        observed = np.array([[a, b], [c, d]])
        
        # Calculate expected frequencies under independence
        row_totals = observed.sum(axis=1)
        col_totals = observed.sum(axis=0)
        total = observed.sum()
        
        if total == 0:
            return 0.0
        
        expected = np.outer(row_totals, col_totals) / total
        
        # Avoid division by zero
        expected = np.maximum(expected, 1e-10)
        
        # Calculate chi-square statistic
        chi2 = np.sum((observed - expected) ** 2 / expected)
        
        return chi2
    
    def power_transform(self, predictions: np.ndarray, human_data: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Power transformation to optimize model fit to human data
        
        Args:
            predictions: Model predictions
            human_data: Human judgments
            
        Returns:
            Tuple of (optimal_gamma, transformed_predictions)
        """
        def objective(gamma):
            transformed = np.sign(predictions) * np.abs(predictions) ** gamma
            correlation = np.corrcoef(transformed, human_data)[0, 1]
            return -correlation  # Minimize negative correlation
        
        try:
            result = optimize.minimize_scalar(objective, bounds=(0.1, 5.0), method='bounded')
            optimal_gamma = result.x
            transformed = np.sign(predictions) * np.abs(predictions) ** optimal_gamma
            return optimal_gamma, transformed
        except:
            return 1.0, predictions
    
    def analyze_contingencies(self, contingencies: List[ContingencyData], 
                            human_data: Optional[np.ndarray] = None) -> pd.DataFrame:
        """
        Analyze multiple contingency tables
        
        Args:
            contingencies: List of contingency data
            human_data: Optional human judgment data for comparison
            
        Returns:
            DataFrame with analysis results
        """
        results = []
        
        for i, cont in enumerate(contingencies):
            # Calculate different model predictions
            ss_support = self.posterior_support(cont, use_uniform_prior=False)
            uniform_support = self.posterior_support(cont, use_uniform_prior=True)
            chi2_support = self.chi_square_support(cont)
            
            result = {
                'condition': i + 1,
                'a': cont.a, 'b': cont.b, 'c': cont.c, 'd': cont.d,
                'causal_direction': cont.causal_direction,
                'delta_p': cont.delta_p,
                'p_e_given_c': cont.p_e_given_c,
                'p_e_given_not_c': cont.p_e_given_not_c,
                'ss_support': ss_support,
                'uniform_support': uniform_support,
                'chi2_support': chi2_support,
            }
            
            if human_data is not None and i < len(human_data):
                result['human_judgment'] = human_data[i]
            
            results.append(result)
        
        df = pd.DataFrame(results)
        
        # If human data available, calculate correlations and transformations
        if human_data is not None:
            for model in ['ss_support', 'uniform_support', 'chi2_support']:
                predictions = df[model].values
                gamma, transformed = self.power_transform(predictions, human_data)
                df[f'{model}_transformed'] = transformed
                df[f'{model}_gamma'] = gamma
                
                # Calculate correlation
                correlation = np.corrcoef(transformed, human_data)[0, 1]
                print(f"{model}: γ={gamma:.3f}, r={correlation:.3f}")
        
        return df
    
    def plot_results(self, results_df: pd.DataFrame, 
                    human_data: Optional[np.ndarray] = None):
        """
        Plot model results
        
        Args:
            results_df: Results from analyze_contingencies
            human_data: Optional human data for comparison
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        models = ['ss_support', 'uniform_support', 'chi2_support']
        model_names = ['SS Prior', 'Uniform Prior', 'Chi-square']
        
        # Plot 1: Model predictions comparison
        ax = axes[0, 0]
        x = np.arange(len(results_df))
        width = 0.25
        
        for i, (model, name) in enumerate(zip(models, model_names)):
            ax.bar(x + i*width, results_df[model], width, label=name, alpha=0.8)
        
        ax.set_xlabel('Condition')
        ax.set_ylabel('Support')
        ax.set_title('Model Predictions')
        ax.legend()
        ax.set_xticks(x + width)
        ax.set_xticklabels([f'C{i+1}' for i in range(len(results_df))])
        
        # Plot 2: ΔP vs Support
        ax = axes[0, 1]
        for model, name in zip(models, model_names):
            ax.scatter(results_df['delta_p'], results_df[model], label=name, alpha=0.7)
        ax.set_xlabel('ΔP')
        ax.set_ylabel('Support')
        ax.set_title('ΔP vs Support')
        ax.legend()
        
        # Plot 3: Human vs Model (if human data available)
        if human_data is not None:
            ax = axes[1, 0]
            for model, name in zip(models, model_names):
                if f'{model}_transformed' in results_df.columns:
                    ax.scatter(human_data, results_df[f'{model}_transformed'], 
                             label=name, alpha=0.7)
            ax.plot([human_data.min(), human_data.max()], 
                   [human_data.min(), human_data.max()], 'k--', alpha=0.5)
            ax.set_xlabel('Human Judgments')
            ax.set_ylabel('Model Predictions (transformed)')
            ax.set_title('Human vs Model')
            ax.legend()
        
        # Plot 4: Contingency table heatmap
        ax = axes[1, 1]
        contingency_matrix = results_df[['a', 'b', 'c', 'd']].values
        im = ax.imshow(contingency_matrix.T, cmap='Blues', aspect='auto')
        ax.set_xlabel('Condition')
        ax.set_ylabel('Cell (a, b, c, d)')
        ax.set_title('Contingency Tables')
        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels(['a (E,C)', 'b (¬E,C)', 'c (E,¬C)', 'd (¬E,¬C)'])
        plt.colorbar(im, ax=ax)
        
        plt.tight_layout()
        return fig


def example_usage():
    """Example usage of the SS Model"""
    
    # Example data from exp1data.m
    contingencies = [
        ContingencyData(8, 0, 0, 8, 1),   # Strong generative
        ContingencyData(8, 0, 2, 6, 1),   # Moderate generative  
        ContingencyData(16, 48, 0, 64, 1), # Weak generative
        ContingencyData(12, 4, 16, 0, -1), # Strong preventive
        ContingencyData(0, 16, 4, 12, -1), # Moderate preventive
        ContingencyData(4, 12, 16, 0, -1), # Weak preventive
    ]
    
    # Human judgments (converted to 0-100 scale)
    human_data = np.array([84.58, 69.26, 43.55, 29.2, 62.5, 91.7])
    
    # Create and run model
    model = SSModel(alpha=5.0, beta=20.0)
    
    print("SS Model Analysis")
    print("=" * 50)
    
    results = model.analyze_contingencies(contingencies, human_data)
    
    print("\nResults Summary:")
    print(results[['condition', 'delta_p', 'ss_support', 'uniform_support', 
                  'chi2_support', 'human_judgment']].round(3))
    
    # Plot results
    fig = model.plot_results(results, human_data)
    plt.show()
    
    return results


if __name__ == "__main__":
    # Run example
    results = example_usage()
