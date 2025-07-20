"""
SS Model Integration with UCS vs CS Experiment Data

This module integrates the SS Model with the existing experimental data
and provides analysis functions compatible with the current project structure.
"""

import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

from ss_model import SSModel, ContingencyData


class SSModelAnalyzer:
    """Integrate SS Model with experimental data"""
    
    def __init__(self, db_path: str = "experiment.db", 
                 alpha: float = 5.0, beta: float = 20.0):
        """
        Initialize SS Model Analyzer
        
        Args:
            db_path: Path to experiment database
            alpha: SS prior parameter
            beta: S+ prior parameter
        """
        self.db_path = Path(db_path)
        self.model = SSModel(alpha=alpha, beta=beta)
        self.df = None
        
    def load_experiment_data(self) -> pd.DataFrame:
        """Load experiment data from database or CSV files"""
        
        # Try to load from database first
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                query = """
                SELECT user_id, sample_number, story,
                       ex1_a, ex1_b, ex1_c, ex1_d, ex1_estimate,
                       ex2_a, ex2_b, ex2_c, ex2_d, ex2_estimate,
                       condition, crt_mean
                FROM experiment_data
                """
                self.df = pd.read_sql_query(query, conn)
                conn.close()
                print(f"Loaded {len(self.df)} records from database")
                return self.df
            except Exception as e:
                print(f"Database loading failed: {e}")
        
        # Fallback to CSV files
        csv_files = [
            "final_valid.csv", 
            "final_valid_6_samples.csv",
            "merged.csv"
        ]
        
        for csv_file in csv_files:
            csv_path = Path(csv_file)
            if csv_path.exists():
                try:
                    self.df = pd.read_csv(csv_path)
                    print(f"Loaded {len(self.df)} records from {csv_file}")
                    return self.df
                except Exception as e:
                    print(f"Failed to load {csv_file}: {e}")
        
        raise FileNotFoundError("No valid data source found")
    
    def create_contingency_from_abcd(self, a: int, b: int, c: int, d: int, 
                                   estimate: float) -> ContingencyData:
        """
        Create ContingencyData from a,b,c,d values
        
        Args:
            a, b, c, d: Contingency table cells
            estimate: Human estimate (used to infer causal direction)
            
        Returns:
            ContingencyData object
        """
        # Infer causal direction from estimate
        if estimate > 0:
            causal_direction = 1  # Generative
        elif estimate < 0:
            causal_direction = -1  # Preventive
        else:
            causal_direction = 0  # Unknown
            
        return ContingencyData(a, b, c, d, causal_direction)
    
    def analyze_sample_conditions(self) -> pd.DataFrame:
        """
        Analyze each sample condition using SS Model
        
        Returns:
            DataFrame with SS Model predictions for each sample
        """
        if self.df is None:
            self.load_experiment_data()
        
        results = []
        
        # Group by sample_number to get unique contingency conditions
        for sample_num in sorted(self.df['sample_number'].unique()):
            sample_data = self.df[self.df['sample_number'] == sample_num]
            
            # Get contingency data (should be same for all participants in this sample)
            first_row = sample_data.iloc[0]
            
            # Analyze both experiments
            for exp_type in ['ex1', 'ex2']:
                a = int(first_row[f'{exp_type}_a'])
                b = int(first_row[f'{exp_type}_b']) 
                c = int(first_row[f'{exp_type}_c'])
                d = int(first_row[f'{exp_type}_d'])
                
                # Get average human estimate for this condition
                human_estimates = sample_data[f'{exp_type}_estimate'].dropna()
                avg_human_estimate = human_estimates.mean()
                
                # Create contingency data
                contingency = self.create_contingency_from_abcd(a, b, c, d, avg_human_estimate)
                
                # Calculate SS Model predictions
                ss_support = self.model.posterior_support(contingency, use_uniform_prior=False)
                uniform_support = self.model.posterior_support(contingency, use_uniform_prior=True)
                chi2_support = self.model.chi_square_support(contingency)
                
                result = {
                    'sample_number': sample_num,
                    'experiment_type': exp_type,
                    'a': a, 'b': b, 'c': c, 'd': d,
                    'delta_p': contingency.delta_p,
                    'p_e_given_c': contingency.p_e_given_c,
                    'p_e_given_not_c': contingency.p_e_given_not_c,
                    'causal_direction': contingency.causal_direction,
                    'human_estimate_mean': avg_human_estimate,
                    'human_estimate_std': human_estimates.std(),
                    'n_participants': len(human_estimates),
                    'ss_support': ss_support,
                    'uniform_support': uniform_support,
                    'chi2_support': chi2_support,
                }
                
                results.append(result)
        
        return pd.DataFrame(results)
    
    def compare_models_to_human_data(self, condition_filter: Optional[Dict] = None) -> pd.DataFrame:
        """
        Compare SS Model predictions to human judgments
        
        Args:
            condition_filter: Optional filter for specific conditions
            
        Returns:
            DataFrame with model comparisons
        """
        if self.df is None:
            self.load_experiment_data()
        
        # Get sample analysis
        sample_results = self.analyze_sample_conditions()
        
        # Apply filters if provided
        if condition_filter:
            for key, value in condition_filter.items():
                if key in sample_results.columns:
                    sample_results = sample_results[sample_results[key] == value]
        
        # Calculate correlations between models and human data
        models = ['ss_support', 'uniform_support', 'chi2_support']
        human_col = 'human_estimate_mean'
        
        correlations = {}
        for model in models:
            corr = np.corrcoef(sample_results[model], sample_results[human_col])[0, 1]
            correlations[model] = corr
        
        print("Model-Human Correlations:")
        for model, corr in correlations.items():
            print(f"  {model}: r = {corr:.3f}")
        
        # Power transformation to optimize fit
        for model in models:
            predictions = sample_results[model].values
            human_data = sample_results[human_col].values
            
            gamma, transformed = self.model.power_transform(predictions, human_data)
            sample_results[f'{model}_transformed'] = transformed
            sample_results[f'{model}_gamma'] = gamma
            
            # Correlation after transformation
            corr_transformed = np.corrcoef(transformed, human_data)[0, 1]
            print(f"  {model} (transformed, γ={gamma:.3f}): r = {corr_transformed:.3f}")
        
        return sample_results
    
    def analyze_by_story_condition(self) -> pd.DataFrame:
        """
        Analyze SS Model predictions by story and condition
        
        Returns:
            DataFrame with story-level analysis
        """
        if self.df is None:
            self.load_experiment_data()
        
        results = []
        
        # Group by story and condition
        for story in sorted(self.df['story'].unique()):
            for condition in sorted(self.df['condition'].unique()):
                story_cond_data = self.df[
                    (self.df['story'] == story) & 
                    (self.df['condition'] == condition)
                ]
                
                if len(story_cond_data) == 0:
                    continue
                
                # Analyze both experiments
                for exp_type in ['ex1', 'ex2']:
                    exp_data = story_cond_data[f'{exp_type}_estimate'].dropna()
                    
                    if len(exp_data) == 0:
                        continue
                    
                    # Get contingency data
                    first_row = story_cond_data.iloc[0]
                    a = int(first_row[f'{exp_type}_a'])
                    b = int(first_row[f'{exp_type}_b'])
                    c = int(first_row[f'{exp_type}_c'])
                    d = int(first_row[f'{exp_type}_d'])
                    
                    avg_estimate = exp_data.mean()
                    contingency = self.create_contingency_from_abcd(a, b, c, d, avg_estimate)
                    
                    # Calculate model predictions
                    ss_support = self.model.posterior_support(contingency, use_uniform_prior=False)
                    uniform_support = self.model.posterior_support(contingency, use_uniform_prior=True)
                    chi2_support = self.model.chi_square_support(contingency)
                    
                    result = {
                        'story': story,
                        'condition': condition,
                        'experiment_type': exp_type,
                        'sample_number': first_row['sample_number'],
                        'n_participants': len(exp_data),
                        'human_estimate_mean': avg_estimate,
                        'human_estimate_std': exp_data.std(),
                        'ss_support': ss_support,
                        'uniform_support': uniform_support,
                        'chi2_support': chi2_support,
                        'delta_p': contingency.delta_p,
                        'causal_direction': contingency.causal_direction,
                    }
                    
                    results.append(result)
        
        return pd.DataFrame(results)
    
    def plot_model_comparison(self, comparison_df: pd.DataFrame, 
                            save_path: Optional[str] = None):
        """
        Plot SS Model vs human judgments
        
        Args:
            comparison_df: Results from compare_models_to_human_data
            save_path: Optional path to save the plot
        """
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        models = ['ss_support', 'uniform_support', 'chi2_support']
        model_names = ['SS Prior', 'Uniform Prior', 'Chi-square']
        
        human_col = 'human_estimate_mean'
        
        # Plot untransformed correlations
        for i, (model, name) in enumerate(zip(models, model_names)):
            ax = axes[0, i]
            
            x = comparison_df[human_col]
            y = comparison_df[model]
            
            ax.scatter(x, y, alpha=0.6, c=comparison_df['experiment_type'].map({'ex1': 'blue', 'ex2': 'red'}))
            
            # Add trend line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), "k--", alpha=0.8)
            
            # Calculate correlation
            corr = np.corrcoef(x, y)[0, 1]
            ax.set_title(f'{name}\nr = {corr:.3f}')
            ax.set_xlabel('Human Judgments')
            ax.set_ylabel('Model Predictions')
        
        # Plot transformed correlations  
        for i, (model, name) in enumerate(zip(models, model_names)):
            ax = axes[1, i]
            
            transformed_col = f'{model}_transformed'
            if transformed_col in comparison_df.columns:
                x = comparison_df[human_col]
                y = comparison_df[transformed_col]
                
                ax.scatter(x, y, alpha=0.6, c=comparison_df['experiment_type'].map({'ex1': 'blue', 'ex2': 'red'}))
                
                # Add trend line
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                ax.plot(x, p(x), "k--", alpha=0.8)
                
                # Calculate correlation and gamma
                corr = np.corrcoef(x, y)[0, 1]
                gamma = comparison_df[f'{model}_gamma'].iloc[0]
                ax.set_title(f'{name} (transformed)\nr = {corr:.3f}, γ = {gamma:.3f}')
                ax.set_xlabel('Human Judgments')
                ax.set_ylabel('Transformed Predictions')
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=8, label='Ex1 (Summary)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=8, label='Ex2 (Online)')
        ]
        fig.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        return fig
    
    def export_results(self, results_df: pd.DataFrame, 
                      filename: str = "ss_model_results.csv"):
        """
        Export SS Model results to CSV
        
        Args:
            results_df: Results DataFrame
            filename: Output filename
        """
        output_path = Path(filename)
        results_df.to_csv(output_path, index=False)
        print(f"Results exported to: {output_path}")
        
        # Create summary statistics
        summary_stats = results_df.groupby('experiment_type')[
            ['human_estimate_mean', 'ss_support', 'uniform_support', 'chi2_support']
        ].agg(['mean', 'std', 'min', 'max'])
        
        summary_path = output_path.with_suffix('.summary.csv')
        summary_stats.to_csv(summary_path)
        print(f"Summary statistics exported to: {summary_path}")


def run_ss_model_analysis():
    """Main function to run SS Model analysis"""
    
    print("SS Model Analysis for UCS vs CS Experiment")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = SSModelAnalyzer(alpha=5.0, beta=20.0)
    
    try:
        # Load data
        df = analyzer.load_experiment_data()
        print(f"Data shape: {df.shape}")
        
        # Analyze sample conditions
        print("\n1. Analyzing sample conditions...")
        sample_results = analyzer.analyze_sample_conditions()
        print(f"Analyzed {len(sample_results)} sample conditions")
        
        # Compare models to human data
        print("\n2. Comparing models to human judgments...")
        comparison_results = analyzer.compare_models_to_human_data()
        
        # Plot comparisons
        print("\n3. Creating visualizations...")
        fig = analyzer.plot_model_comparison(comparison_results, 
                                           save_path="ss_model_comparison.png")
        plt.show()
        
        # Export results
        print("\n4. Exporting results...")
        analyzer.export_results(comparison_results, "ss_model_analysis_results.csv")
        
        # Analyze by story and condition
        print("\n5. Analyzing by story and condition...")
        story_results = analyzer.analyze_by_story_condition()
        analyzer.export_results(story_results, "ss_model_story_analysis.csv")
        
        print("\nAnalysis complete!")
        return comparison_results, story_results
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None, None


if __name__ == "__main__":
    # Run the analysis
    comparison_results, story_results = run_ss_model_analysis()
