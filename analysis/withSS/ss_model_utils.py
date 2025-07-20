"""
SS Model Utilities

Utility functions to integrate SS Model with existing project scripts.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from ss_model import SSModel, ContingencyData


def calculate_ss_metrics(a: int, b: int, c: int, d: int, 
                        estimate: Optional[float] = None,
                        alpha: float = 5.0, beta: float = 20.0) -> Dict[str, float]:
    """
    Calculate all SS Model metrics for a single contingency table
    
    Args:
        a, b, c, d: Contingency table cells (a=E&C, b=¬E&C, c=E&¬C, d=¬E&¬C)
        estimate: Human estimate (optional, used to infer causal direction)
        alpha: SS prior parameter
        beta: S+ prior parameter
        
    Returns:
        Dictionary with all calculated metrics
    """
    # Infer causal direction
    if estimate is not None:
        if estimate > 0:
            causal_direction = 1  # Generative
        elif estimate < 0:
            causal_direction = -1  # Preventive
        else:
            causal_direction = 0  # Unknown
    else:
        # Default to generative if no estimate provided
        causal_direction = 1
    
    # Create contingency data
    contingency = ContingencyData(a, b, c, d, causal_direction)
    
    # Initialize model
    model = SSModel(alpha=alpha, beta=beta)
    
    # Calculate basic metrics
    delta_p = contingency.delta_p
    p_e_given_c = contingency.p_e_given_c
    p_e_given_not_c = contingency.p_e_given_not_c
    
    # Calculate model predictions
    try:
        ss_support = model.posterior_support(contingency, use_uniform_prior=False)
    except:
        ss_support = np.nan
        
    try:
        uniform_support = model.posterior_support(contingency, use_uniform_prior=True)
    except:
        uniform_support = np.nan
        
    try:
        chi2_support = model.chi_square_support(contingency)
    except:
        chi2_support = np.nan
    
    return {
        'delta_p': delta_p,
        'p_e_given_c': p_e_given_c,
        'p_e_given_not_c': p_e_given_not_c,
        'causal_direction': causal_direction,
        'ss_support': ss_support,
        'uniform_support': uniform_support,
        'chi2_support': chi2_support,
        'total_n': a + b + c + d
    }


def add_ss_metrics_to_dataframe(df: pd.DataFrame, 
                               a_col: str = 'a', b_col: str = 'b',
                               c_col: str = 'c', d_col: str = 'd',
                               estimate_col: Optional[str] = None,
                               prefix: str = 'ss_') -> pd.DataFrame:
    """
    Add SS Model metrics to an existing DataFrame
    
    Args:
        df: Input DataFrame
        a_col, b_col, c_col, d_col: Column names for contingency table
        estimate_col: Column name for human estimates (optional)
        prefix: Prefix for new column names
        
    Returns:
        DataFrame with added SS metrics
    """
    df_copy = df.copy()
    
    # Initialize new columns
    ss_metrics = [
        'delta_p', 'p_e_given_c', 'p_e_given_not_c', 'causal_direction',
        'ss_support', 'uniform_support', 'chi2_support', 'total_n'
    ]
    
    for metric in ss_metrics:
        df_copy[f'{prefix}{metric}'] = np.nan
    
    # Calculate metrics for each row
    for idx, row in df_copy.iterrows():
        try:
            a = int(row[a_col])
            b = int(row[b_col])
            c = int(row[c_col])
            d = int(row[d_col])
            
            estimate = None
            if estimate_col and estimate_col in row:
                estimate = row[estimate_col]
                if pd.isna(estimate):
                    estimate = None
            
            metrics = calculate_ss_metrics(a, b, c, d, estimate)
            
            for metric, value in metrics.items():
                df_copy.loc[idx, f'{prefix}{metric}'] = value
                
        except Exception as e:
            print(f"Error calculating SS metrics for row {idx}: {e}")
            continue
    
    return df_copy


def compare_metrics(df: pd.DataFrame, 
                   human_col: str,
                   model_cols: List[str],
                   method: str = 'pearson') -> Dict[str, float]:
    """
    Compare model metrics with human judgments
    
    Args:
        df: DataFrame with human and model data
        human_col: Column name for human judgments
        model_cols: List of model column names
        method: Correlation method ('pearson', 'spearman')
        
    Returns:
        Dictionary of correlations
    """
    correlations = {}
    
    for model_col in model_cols:
        if model_col in df.columns and human_col in df.columns:
            # Remove NaN values
            valid_data = df[[human_col, model_col]].dropna()
            
            if len(valid_data) > 1:
                if method == 'pearson':
                    corr = valid_data[human_col].corr(valid_data[model_col])
                elif method == 'spearman':
                    corr = valid_data[human_col].corr(valid_data[model_col], method='spearman')
                else:
                    corr = np.nan
                
                correlations[model_col] = corr
            else:
                correlations[model_col] = np.nan
        else:
            correlations[model_col] = np.nan
    
    return correlations


def metrics_from_abcd(a: int, b: int, c: int, d: int, 
                     is_gene: bool = True) -> Dict[str, float]:
    """
    Calculate various causal learning metrics from contingency table
    (Compatible with existing project functions)
    
    Args:
        a, b, c, d: Contingency table cells
        is_gene: Whether to assume generative causal direction
        
    Returns:
        Dictionary with metrics including SS Model predictions
    """
    # Basic probability calculations
    n_total = a + b + c + d
    if n_total == 0:
        return {metric: np.nan for metric in ['P(E|C)', 'P(C|E)', 'ΔP', 'CS', 'UCS', 'pARIs', 'DFH', 'Dice']}
    
    # Conditional probabilities
    p_e_given_c = a / (a + b) if (a + b) > 0 else 0
    p_e_given_not_c = c / (c + d) if (c + d) > 0 else 0
    p_c_given_e = a / (a + c) if (a + c) > 0 else 0
    p_c_given_not_e = b / (b + d) if (b + d) > 0 else 0
    
    # ΔP
    delta_p = p_e_given_c - p_e_given_not_c
    
    # CS (Causal Support) - using Chi-square
    observed = np.array([[a, b], [c, d]])
    row_totals = observed.sum(axis=1)
    col_totals = observed.sum(axis=0)
    expected = np.outer(row_totals, col_totals) / n_total
    expected = np.maximum(expected, 1e-10)  # Avoid division by zero
    cs = np.sum((observed - expected) ** 2 / expected)
    
    # UCS (Unbiased Causal Support) - using log likelihood ratio
    if p_e_given_c > 0 and p_e_given_not_c > 0 and p_e_given_c != p_e_given_not_c:
        ucs = 2 * (a * np.log(p_e_given_c) + b * np.log(1 - p_e_given_c) +
                  c * np.log(p_e_given_not_c) + d * np.log(1 - p_e_given_not_c) -
                  (a + c) * np.log((a + c) / n_total) - 
                  (b + d) * np.log((b + d) / n_total))
    else:
        ucs = 0
    
    # pARIs (probably should be properly defined, using placeholder)
    paris = abs(delta_p)
    
    # DFH (Δf statistic)
    dfh = delta_p
    
    # Dice coefficient
    dice = 2 * a / (2 * a + b + c) if (2 * a + b + c) > 0 else 0
    
    # Add SS Model metrics
    estimate = delta_p * 100  # Convert to 0-100 scale like human estimates
    ss_metrics = calculate_ss_metrics(a, b, c, d, estimate)
    
    return {
        'P(E|C)': p_e_given_c,
        'P(C|E)': p_c_given_e,
        'ΔP': delta_p,
        'CS': cs,
        'UCS': ucs,
        'pARIs': paris,
        'DFH': dfh,
        'Dice': dice,
        'SS_Support': ss_metrics['ss_support'],
        'Uniform_Support': ss_metrics['uniform_support'],
        'Chi2_Support': ss_metrics['chi2_support']
    }


def analyze_experiment_with_ss_model(data_path: str, 
                                   output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Analyze experiment data with SS Model
    
    Args:
        data_path: Path to experiment data (CSV or database)
        output_path: Optional path to save results
        
    Returns:
        DataFrame with SS Model analysis
    """
    # Load data
    if data_path.endswith('.csv'):
        df = pd.read_csv(data_path)
    else:
        # Assume it's a database or other format
        raise NotImplementedError("Only CSV files supported in this utility")
    
    # Add SS metrics for both experiments
    for exp in ['ex1', 'ex2']:
        if all(col in df.columns for col in [f'{exp}_a', f'{exp}_b', f'{exp}_c', f'{exp}_d']):
            df = add_ss_metrics_to_dataframe(
                df, 
                a_col=f'{exp}_a', b_col=f'{exp}_b',
                c_col=f'{exp}_c', d_col=f'{exp}_d',
                estimate_col=f'{exp}_estimate',
                prefix=f'{exp}_ss_'
            )
    
    # Calculate correlations if human estimates available
    if 'ex1_estimate' in df.columns:
        ex1_corr = compare_metrics(
            df, 'ex1_estimate',
            ['ex1_ss_ss_support', 'ex1_ss_uniform_support', 'ex1_ss_chi2_support']
        )
        print("Ex1 correlations with human estimates:")
        for model, corr in ex1_corr.items():
            print(f"  {model}: r = {corr:.3f}")
    
    if 'ex2_estimate' in df.columns:
        ex2_corr = compare_metrics(
            df, 'ex2_estimate', 
            ['ex2_ss_ss_support', 'ex2_ss_uniform_support', 'ex2_ss_chi2_support']
        )
        print("Ex2 correlations with human estimates:")
        for model, corr in ex2_corr.items():
            print(f"  {model}: r = {corr:.3f}")
    
    # Save results if requested
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
    
    return df


def create_ss_model_summary(df: pd.DataFrame) -> Dict:
    """
    Create summary statistics for SS Model analysis
    
    Args:
        df: DataFrame with SS Model results
        
    Returns:
        Dictionary with summary statistics
    """
    summary = {}
    
    # Find SS model columns
    ss_cols = [col for col in df.columns if 'ss_' in col and any(metric in col for metric in ['support', 'delta_p'])]
    
    if ss_cols:
        summary['ss_model_summary'] = df[ss_cols].describe()
        
        # Correlation matrix
        numeric_ss_cols = [col for col in ss_cols if df[col].dtype in ['float64', 'int64']]
        if len(numeric_ss_cols) > 1:
            summary['ss_correlation_matrix'] = df[numeric_ss_cols].corr()
    
    # Human estimate correlations
    estimate_cols = [col for col in df.columns if 'estimate' in col and col.endswith('estimate')]
    support_cols = [col for col in df.columns if 'support' in col]
    
    if estimate_cols and support_cols:
        summary['human_model_correlations'] = {}
        for est_col in estimate_cols:
            for sup_col in support_cols:
                corr = df[est_col].corr(df[sup_col])
                summary['human_model_correlations'][f'{est_col}_vs_{sup_col}'] = corr
    
    return summary


# Example usage function
def example_ss_integration():
    """Example of how to integrate SS Model with existing project"""
    
    print("SS Model Integration Example")
    print("=" * 40)
    
    # Example contingency data
    example_data = pd.DataFrame({
        'condition': [1, 2, 3, 4],
        'a': [8, 12, 16, 4],
        'b': [0, 4, 48, 12],
        'c': [0, 16, 0, 16],
        'd': [8, 0, 64, 0],
        'estimate': [80, 30, 40, -60]  # Human estimates
    })
    
    print("Example data:")
    print(example_data)
    
    # Add SS metrics
    result_df = add_ss_metrics_to_dataframe(
        example_data,
        a_col='a', b_col='b', c_col='c', d_col='d',
        estimate_col='estimate'
    )
    
    print("\nWith SS Model metrics:")
    ss_columns = [col for col in result_df.columns if col.startswith('ss_')]
    print(result_df[['condition'] + ss_columns].round(3))
    
    # Calculate correlations
    correlations = compare_metrics(
        result_df, 'estimate',
        ['ss_ss_support', 'ss_uniform_support', 'ss_chi2_support']
    )
    
    print("\nCorrelations with human estimates:")
    for model, corr in correlations.items():
        print(f"  {model}: r = {corr:.3f}")
    
    return result_df


if __name__ == "__main__":
    # Run example
    result = example_ss_integration()
