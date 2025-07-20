"""
scenario_effect_analysis.py

シナリオが各刺激の評定に与える影響を分析
sample_story_averages_by_condition.csvをもとに分析
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import f_oneway, ttest_rel
import warnings
warnings.filterwarnings('ignore')

class ScenarioEffectAnalyzer:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = None
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"Data loaded: {self.csv_path} (shape={self.df.shape})")
        
        # 条件を英語に変換
        condition_mapping = {
            "非対称否定_サマリー": "Asymmetric_Summary",
            "対称否定_サマリー": "Symmetric_Summary", 
            "非対称否定_オンライン": "Asymmetric_Online",
            "対称否定_オンライン": "Symmetric_Online"
        }
        self.df['condition_en'] = self.df['condition'].map(condition_mapping)
        
        print("Conditions mapped to English:")
        print(self.df['condition_en'].value_counts())
        
    def calculate_scenario_effects(self):
        """シナリオ効果を計算"""
        results = []
        
        for condition in self.df['condition_en'].unique():
            if pd.isna(condition):
                continue
                
            condition_data = self.df[self.df['condition_en'] == condition]
            
            for sample_num in range(1, 7):  # sample_number 1-6
                sample_data = condition_data[condition_data['sample_number'] == sample_num]
                
                if len(sample_data) == 0:
                    continue
                
                # シナリオ間の評定値（count > 0のもののみ）
                valid_data = sample_data[sample_data['count'] > 0]
                
                if len(valid_data) < 2:
                    # データが不十分な場合
                    results.append({
                        'condition': condition,
                        'sample_number': sample_num,
                        'n_scenarios': len(valid_data),
                        'mean_rating': np.nan,
                        'std_rating': np.nan,
                        'min_rating': np.nan,
                        'max_rating': np.nan,
                        'range_rating': np.nan,
                        'cv_rating': np.nan,
                        'scenario_effect_size': np.nan,
                        'anova_f': np.nan,
                        'anova_p': np.nan
                    })
                    continue
                
                ratings = valid_data['mean_estimate'].values
                
                # 基本統計量
                mean_rating = np.mean(ratings)
                std_rating = np.std(ratings, ddof=1) if len(ratings) > 1 else 0
                min_rating = np.min(ratings)
                max_rating = np.max(ratings)
                range_rating = max_rating - min_rating
                cv_rating = std_rating / mean_rating if mean_rating != 0 else np.nan
                
                # シナリオ効果サイズ（標準偏差 / 平均の絶対値）
                scenario_effect_size = std_rating / abs(mean_rating) if mean_rating != 0 else np.nan
                
                # 分散分析（シナリオ間で差があるか）
                if len(valid_data) >= 3:
                    scenario_groups = [valid_data[valid_data['cover_story'] == story]['mean_estimate'].values 
                                     for story in valid_data['cover_story'].unique()]
                    scenario_groups = [group for group in scenario_groups if len(group) > 0]
                    
                    if len(scenario_groups) >= 2:
                        try:
                            f_stat, p_value = f_oneway(*scenario_groups)
                        except:
                            f_stat, p_value = np.nan, np.nan
                    else:
                        f_stat, p_value = np.nan, np.nan
                else:
                    f_stat, p_value = np.nan, np.nan
                
                results.append({
                    'condition': condition,
                    'sample_number': sample_num,
                    'n_scenarios': len(valid_data),
                    'mean_rating': round(mean_rating, 3),
                    'std_rating': round(std_rating, 3),
                    'min_rating': round(min_rating, 3),
                    'max_rating': round(max_rating, 3),
                    'range_rating': round(range_rating, 3),
                    'cv_rating': round(cv_rating, 3) if not np.isnan(cv_rating) else np.nan,
                    'scenario_effect_size': round(scenario_effect_size, 3) if not np.isnan(scenario_effect_size) else np.nan,
                    'anova_f': round(f_stat, 3) if not np.isnan(f_stat) else np.nan,
                    'anova_p': round(p_value, 3) if not np.isnan(p_value) else np.nan
                })
        
        return pd.DataFrame(results)
    
    def visualize_scenario_effects(self, effects_df):
        """シナリオ効果を可視化"""
        # Set up the plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Scenario Effects on Stimulus Ratings by Condition', fontsize=16, y=0.98)
        
        # 1. Range of ratings by condition and sample
        ax1 = axes[0, 0]
        pivot_range = effects_df.pivot(index='sample_number', columns='condition', values='range_rating')
        sns.heatmap(pivot_range, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax1, cbar_kws={'label': 'Range'})
        ax1.set_title('Range of Ratings Across Scenarios')
        ax1.set_xlabel('Condition')
        ax1.set_ylabel('Sample Number')
        
        # 2. Coefficient of Variation by condition and sample
        ax2 = axes[0, 1]
        pivot_cv = effects_df.pivot(index='sample_number', columns='condition', values='cv_rating')
        sns.heatmap(pivot_cv, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax2, cbar_kws={'label': 'CV'})
        ax2.set_title('Coefficient of Variation Across Scenarios')
        ax2.set_xlabel('Condition')
        ax2.set_ylabel('Sample Number')
        
        # 3. Scenario Effect Size by condition and sample
        ax3 = axes[0, 2]
        pivot_effect = effects_df.pivot(index='sample_number', columns='condition', values='scenario_effect_size')
        sns.heatmap(pivot_effect, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax3, cbar_kws={'label': 'Effect Size'})
        ax3.set_title('Scenario Effect Size')
        ax3.set_xlabel('Condition')
        ax3.set_ylabel('Sample Number')
        
        # 4. ANOVA F-statistics
        ax4 = axes[1, 0]
        pivot_f = effects_df.pivot(index='sample_number', columns='condition', values='anova_f')
        sns.heatmap(pivot_f, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax4, cbar_kws={'label': 'F-statistic'})
        ax4.set_title('ANOVA F-statistics (Scenario Differences)')
        ax4.set_xlabel('Condition')
        ax4.set_ylabel('Sample Number')
        
        # 5. Box plot of scenario effect sizes by condition
        ax5 = axes[1, 1]
        valid_effects = effects_df.dropna(subset=['scenario_effect_size'])
        if len(valid_effects) > 0:
            sns.boxplot(data=valid_effects, x='condition', y='scenario_effect_size', ax=ax5)
            ax5.set_title('Distribution of Scenario Effect Sizes')
            ax5.set_xlabel('Condition')
            ax5.set_ylabel('Scenario Effect Size')
            ax5.tick_params(axis='x', rotation=45)
        
        # 6. Scatter plot: Mean rating vs Scenario effect size
        ax6 = axes[1, 2]
        valid_data = effects_df.dropna(subset=['mean_rating', 'scenario_effect_size'])
        if len(valid_data) > 0:
            for condition in valid_data['condition'].unique():
                cond_data = valid_data[valid_data['condition'] == condition]
                ax6.scatter(cond_data['mean_rating'], cond_data['scenario_effect_size'], 
                           label=condition, alpha=0.7, s=60)
            ax6.set_xlabel('Mean Rating')
            ax6.set_ylabel('Scenario Effect Size')
            ax6.set_title('Mean Rating vs Scenario Effect Size')
            ax6.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.savefig('scenario_effect_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def detailed_scenario_analysis(self):
        """詳細なシナリオ分析"""
        # データがあるもののみ抽出
        valid_data = self.df[self.df['count'] > 0]
        
        print("\n=== Detailed Scenario Analysis ===")
        
        # 条件別のシナリオ効果サマリー
        summary_results = []
        
        for condition in valid_data['condition_en'].unique():
            if pd.isna(condition):
                continue
                
            cond_data = valid_data[valid_data['condition_en'] == condition]
            
            # 各sample_numberでのシナリオ間変動
            sample_variations = []
            for sample_num in range(1, 7):
                sample_data = cond_data[cond_data['sample_number'] == sample_num]
                if len(sample_data) > 1:
                    std_variation = sample_data['mean_estimate'].std()
                    sample_variations.append(std_variation)
            
            avg_variation = np.mean(sample_variations) if sample_variations else 0
            
            # シナリオ間での一貫性（標準偏差の平均）
            scenario_consistency = []
            for story in range(1, 13):
                story_data = cond_data[cond_data['cover_story'] == story]
                if len(story_data) > 1:
                    story_std = story_data['mean_estimate'].std()
                    scenario_consistency.append(story_std)
            
            avg_consistency = np.mean(scenario_consistency) if scenario_consistency else 0
            
            summary_results.append({
                'condition': condition,
                'n_valid_datapoints': len(cond_data),
                'avg_scenario_variation': round(avg_variation, 3),
                'avg_scenario_consistency': round(avg_consistency, 3),
                'overall_mean': round(cond_data['mean_estimate'].mean(), 3),
                'overall_std': round(cond_data['mean_estimate'].std(), 3)
            })
        
        summary_df = pd.DataFrame(summary_results)
        
        print("\nCondition Summary:")
        print(summary_df.to_string(index=False))
        
        # 保存
        summary_df.to_csv('scenario_effect_summary.csv', index=False)
        print(f"\nSummary saved to: scenario_effect_summary.csv")
        
        return summary_df
    
    def statistical_tests(self):
        """統計的検定"""
        valid_data = self.df[self.df['count'] > 0]
        
        print("\n=== Statistical Tests ===")
        
        # 条件間でのシナリオ効果の違いを検定
        condition_effects = {}
        
        for condition in valid_data['condition_en'].unique():
            if pd.isna(condition):
                continue
                
            cond_data = valid_data[valid_data['condition_en'] == condition]
            
            # 各sample_numberでのシナリオ間変動を計算
            sample_variations = []
            for sample_num in range(1, 7):
                sample_data = cond_data[cond_data['sample_number'] == sample_num]
                if len(sample_data) > 1:
                    std_variation = sample_data['mean_estimate'].std()
                    sample_variations.append(std_variation)
            
            condition_effects[condition] = sample_variations
        
        # 条件間でのシナリオ効果の分散分析
        effect_values = [effects for effects in condition_effects.values() if len(effects) > 0]
        
        if len(effect_values) >= 2:
            try:
                f_stat, p_value = f_oneway(*effect_values)
                print(f"\nANOVA for scenario effects across conditions:")
                print(f"F-statistic: {f_stat:.3f}")
                print(f"p-value: {p_value:.3f}")
                
                if p_value < 0.05:
                    print("Significant difference in scenario effects between conditions")
                else:
                    print("No significant difference in scenario effects between conditions")
            except Exception as e:
                print(f"Error in ANOVA: {e}")
        
        # ペアワイズ比較
        conditions = list(condition_effects.keys())
        print(f"\nPairwise comparisons of scenario effects:")
        
        for i in range(len(conditions)):
            for j in range(i+1, len(conditions)):
                cond1, cond2 = conditions[i], conditions[j]
                effects1, effects2 = condition_effects[cond1], condition_effects[cond2]
                
                if len(effects1) > 0 and len(effects2) > 0:
                    try:
                        t_stat, p_value = stats.ttest_ind(effects1, effects2)
                        print(f"{cond1} vs {cond2}: t={t_stat:.3f}, p={p_value:.3f}")
                    except Exception as e:
                        print(f"{cond1} vs {cond2}: Error - {e}")
    
    def run_analysis(self):
        """全体の分析を実行"""
        print("=== Scenario Effect Analysis ===")
        print("Analyzing how scenarios affect stimulus ratings in each condition")
        print("=" * 60)
        
        # データ読み込み
        self.load_data()
        
        # シナリオ効果計算
        print("\nCalculating scenario effects...")
        effects_df = self.calculate_scenario_effects()
        
        # 結果保存
        effects_df.to_csv('scenario_effects_detailed.csv', index=False)
        print(f"Detailed results saved to: scenario_effects_detailed.csv")
        
        # 可視化
        print("\nCreating visualizations...")
        self.visualize_scenario_effects(effects_df)
        
        # 詳細分析
        summary_df = self.detailed_scenario_analysis()
        
        # 統計的検定
        self.statistical_tests()
        
        print("\n=== Analysis Complete ===")
        return effects_df, summary_df


if __name__ == "__main__":
    analyzer = ScenarioEffectAnalyzer("sample_story_averages_by_condition.csv")
    effects_df, summary_df = analyzer.run_analysis()