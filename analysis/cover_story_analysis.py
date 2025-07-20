"""
cover_story_analysis.py

カバーストーリーの特性を分析するコード
ex1_cover_storyとex2_cover_storyは共通の値を持つため、統合的に分析
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr, spearmanr, chi2_contingency
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
import japanize_matplotlib
sns.set_style("whitegrid")


class CoverStoryAnalyzer:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df: pd.DataFrame = None
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
        # カバーストーリーの一致確認
        ex1_stories = set(self.df['ex1_cover_story'].unique())
        ex2_stories = set(self.df['ex2_cover_story'].unique())
        print(f"ex1_cover_story値: {sorted(ex1_stories)}")
        print(f"ex2_cover_story値: {sorted(ex2_stories)}")
        print(f"カバーストーリー一致確認: {ex1_stories == ex2_stories}")
        
    def safe_corr(self, x: np.ndarray, y: np.ndarray, method='pearson') -> float:
        """安全な相関計算"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        if mask.sum() < 2:
            return np.nan
        if np.nanstd(x[mask]) == 0 or np.nanstd(y[mask]) == 0:
            return 0.0
        
        if method == 'pearson':
            return pearsonr(x[mask], y[mask])[0]
        elif method == 'spearman':
            return spearmanr(x[mask], y[mask])[0]
        
    def analyze_cover_story_basic_stats(self):
        """カバーストーリーの基本統計"""
        print("\n=== カバーストーリー基本統計 ===")
        
        # ex1のみ使用（ex2と同じなので）
        story_stats = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            # ex1でのこのストーリーのデータ
            ex1_data = self.df[self.df['ex1_cover_story'] == story]
            # ex2でのこのストーリーのデータ
            ex2_data = self.df[self.df['ex2_cover_story'] == story]
            
            # 各実験での統計
            ex1_stats = {
                'story': story,
                'experiment': 'ex1',
                'n_participants': len(ex1_data),
                'mean_estimate': ex1_data['ex1_estimate'].mean(),
                'std_estimate': ex1_data['ex1_estimate'].std(),
                'cond0_ratio': (ex1_data['Cond'] == 0).mean(),
                'mean_crt': ex1_data['crt_correct_cnt'].mean() if 'crt_correct_cnt' in ex1_data.columns else np.nan
            }
            
            ex2_stats = {
                'story': story,
                'experiment': 'ex2',
                'n_participants': len(ex2_data),
                'mean_estimate': ex2_data['ex2_estimate'].mean(),
                'std_estimate': ex2_data['ex2_estimate'].std(),
                'cond0_ratio': (ex2_data['Cond'] == 0).mean(),
                'mean_crt': ex2_data['crt_correct_cnt'].mean() if 'crt_correct_cnt' in ex2_data.columns else np.nan
            }
            
            story_stats.extend([ex1_stats, ex2_stats])
        
        stats_df = pd.DataFrame(story_stats)
        
        # 保存
        stats_df.to_csv('cover_story_basic_stats.csv', index=False, encoding='utf-8-sig')
        print("→ 基本統計を保存: cover_story_basic_stats.csv")
        
        return stats_df
    
    def analyze_story_difficulty(self):
        """ストーリー別の難易度分析"""
        print("\n=== ストーリー難易度分析 ===")
        
        difficulty_results = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            # 各実験でのこのストーリーのデータ
            ex1_data = self.df[self.df['ex1_cover_story'] == story]
            ex2_data = self.df[self.df['ex2_cover_story'] == story]
            
            # 推定値の分散（難易度の指標として）
            ex1_var = ex1_data['ex1_estimate'].var()
            ex2_var = ex2_data['ex2_estimate'].var()
            
            # 極端な値（-100, 100）の割合
            ex1_extreme = ((ex1_data['ex1_estimate'] == -100) | (ex1_data['ex1_estimate'] == 100)).mean()
            ex2_extreme = ((ex2_data['ex2_estimate'] == -100) | (ex2_data['ex2_estimate'] == 100)).mean()
            
            # 中央値からの乖離
            ex1_median_dev = np.abs(ex1_data['ex1_estimate'] - ex1_data['ex1_estimate'].median()).mean()
            ex2_median_dev = np.abs(ex2_data['ex2_estimate'] - ex2_data['ex2_estimate'].median()).mean()
            
            difficulty_results.append({
                'story': story,
                'ex1_variance': ex1_var,
                'ex2_variance': ex2_var,
                'ex1_extreme_ratio': ex1_extreme,
                'ex2_extreme_ratio': ex2_extreme,
                'ex1_median_deviation': ex1_median_dev,
                'ex2_median_deviation': ex2_median_dev,
                'ex1_n': len(ex1_data),
                'ex2_n': len(ex2_data)
            })
        
        difficulty_df = pd.DataFrame(difficulty_results)
        
        # 保存
        difficulty_df.to_csv('cover_story_difficulty_analysis.csv', index=False, encoding='utf-8-sig')
        print("→ 難易度分析を保存: cover_story_difficulty_analysis.csv")
        
        return difficulty_df
    
    def analyze_story_consistency(self):
        """ストーリー間の一貫性分析"""
        print("\n=== ストーリー間一貫性分析 ===")
        
        consistency_results = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            # 同じ参加者が同じストーリーをex1とex2で体験した場合の分析
            same_story_participants = self.df[
                (self.df['ex1_cover_story'] == story) & 
                (self.df['ex2_cover_story'] == story)
            ]
            
            if len(same_story_participants) > 0:
                # ex1とex2の推定値の相関
                corr_estimate = self.safe_corr(
                    same_story_participants['ex1_estimate'].values,
                    same_story_participants['ex2_estimate'].values
                )
                
                # 推定値の差
                estimate_diff = same_story_participants['ex2_estimate'] - same_story_participants['ex1_estimate']
                mean_diff = estimate_diff.mean()
                std_diff = estimate_diff.std()
                
                consistency_results.append({
                    'story': story,
                    'n_same_story_participants': len(same_story_participants),
                    'ex1_ex2_correlation': corr_estimate,
                    'mean_estimate_difference': mean_diff,
                    'std_estimate_difference': std_diff,
                    'ex1_mean': same_story_participants['ex1_estimate'].mean(),
                    'ex2_mean': same_story_participants['ex2_estimate'].mean()
                })
        
        consistency_df = pd.DataFrame(consistency_results)
        
        # 保存
        consistency_df.to_csv('cover_story_consistency_analysis.csv', index=False, encoding='utf-8-sig')
        print("→ 一貫性分析を保存: cover_story_consistency_analysis.csv")
        
        return consistency_df
    
    def analyze_story_condition_interaction(self):
        """ストーリーと条件の交互作用分析"""
        print("\n=== ストーリー×条件交互作用分析 ===")
        
        interaction_results = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            for exp in ['ex1', 'ex2']:
                story_col = f'{exp}_cover_story'
                estimate_col = f'{exp}_estimate'
                
                story_data = self.df[self.df[story_col] == story]
                
                if len(story_data) == 0:
                    continue
                
                # 条件別の統計
                cond0_data = story_data[story_data['Cond'] == 0][estimate_col]
                cond1_data = story_data[story_data['Cond'] == 1][estimate_col]
                
                # t検定
                if len(cond0_data) > 1 and len(cond1_data) > 1:
                    t_stat, p_value = stats.ttest_ind(cond0_data, cond1_data)
                else:
                    t_stat, p_value = np.nan, np.nan
                
                # 効果サイズ（Cohen's d）
                if len(cond0_data) > 0 and len(cond1_data) > 0:
                    pooled_std = np.sqrt(((len(cond0_data) - 1) * cond0_data.var() + 
                                        (len(cond1_data) - 1) * cond1_data.var()) / 
                                       (len(cond0_data) + len(cond1_data) - 2))
                    cohens_d = (cond0_data.mean() - cond1_data.mean()) / pooled_std if pooled_std > 0 else 0
                else:
                    cohens_d = np.nan
                
                interaction_results.append({
                    'story': story,
                    'experiment': exp,
                    'cond0_n': len(cond0_data),
                    'cond1_n': len(cond1_data),
                    'cond0_mean': cond0_data.mean() if len(cond0_data) > 0 else np.nan,
                    'cond1_mean': cond1_data.mean() if len(cond1_data) > 0 else np.nan,
                    'cond0_std': cond0_data.std() if len(cond0_data) > 0 else np.nan,
                    'cond1_std': cond1_data.std() if len(cond1_data) > 0 else np.nan,
                    'condition_difference': (cond0_data.mean() - cond1_data.mean()) if len(cond0_data) > 0 and len(cond1_data) > 0 else np.nan,
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d
                })
        
        interaction_df = pd.DataFrame(interaction_results)
        
        # 保存
        interaction_df.to_csv('cover_story_condition_interaction.csv', index=False, encoding='utf-8-sig')
        print("→ 交互作用分析を保存: cover_story_condition_interaction.csv")
        
        return interaction_df
    
    def analyze_story_crt_relationship(self):
        """ストーリーとCRTスコアの関係分析"""
        print("\n=== ストーリー×CRT関係分析 ===")
        
        if 'crt_correct_cnt' not in self.df.columns:
            print("CRTスコアが見つかりません")
            return None
        
        crt_results = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            for exp in ['ex1', 'ex2']:
                story_col = f'{exp}_cover_story'
                estimate_col = f'{exp}_estimate'
                
                story_data = self.df[self.df[story_col] == story]
                
                if len(story_data) == 0:
                    continue
                
                # CRTスコアと推定値の相関
                corr_crt = self.safe_corr(
                    story_data['crt_correct_cnt'].values,
                    story_data[estimate_col].values
                )
                
                # CRTスコア別の推定値統計
                crt_stats = story_data.groupby('crt_correct_cnt')[estimate_col].agg(['count', 'mean', 'std']).reset_index()
                
                crt_results.append({
                    'story': story,
                    'experiment': exp,
                    'n_participants': len(story_data),
                    'crt_estimate_correlation': corr_crt,
                    'mean_crt_score': story_data['crt_correct_cnt'].mean(),
                    'std_crt_score': story_data['crt_correct_cnt'].std(),
                    'mean_estimate': story_data[estimate_col].mean(),
                    'std_estimate': story_data[estimate_col].std()
                })
        
        crt_df = pd.DataFrame(crt_results)
        
        # 保存
        crt_df.to_csv('cover_story_crt_relationship.csv', index=False, encoding='utf-8-sig')
        print("→ CRT関係分析を保存: cover_story_crt_relationship.csv")
        
        return crt_df
    
    def create_story_visualization(self):
        """ストーリー分析の可視化"""
        print("\n=== ストーリー分析可視化 ===")
        
        # 図のセットアップ
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Cover Story Analysis', fontsize=16)
        
        # 1. ストーリー別推定値分布（ex1）
        story_estimates_ex1 = []
        story_labels = []
        for story in sorted(self.df['ex1_cover_story'].unique()):
            estimates = self.df[self.df['ex1_cover_story'] == story]['ex1_estimate']
            story_estimates_ex1.append(estimates)
            story_labels.append(f'Story {story}')
        
        axes[0,0].boxplot(story_estimates_ex1, labels=story_labels)
        axes[0,0].set_title('Ex1: Estimate Distribution by Story')
        axes[0,0].set_ylabel('Estimate')
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # 2. ストーリー別推定値分布（ex2）
        story_estimates_ex2 = []
        for story in sorted(self.df['ex2_cover_story'].unique()):
            estimates = self.df[self.df['ex2_cover_story'] == story]['ex2_estimate']
            story_estimates_ex2.append(estimates)
        
        axes[0,1].boxplot(story_estimates_ex2, labels=story_labels)
        axes[0,1].set_title('Ex2: Estimate Distribution by Story')
        axes[0,1].set_ylabel('Estimate')
        axes[0,1].tick_params(axis='x', rotation=45)
        
        # 3. ストーリー別参加者数
        story_counts = []
        for story in sorted(self.df['ex1_cover_story'].unique()):
            count_ex1 = len(self.df[self.df['ex1_cover_story'] == story])
            count_ex2 = len(self.df[self.df['ex2_cover_story'] == story])
            story_counts.append([count_ex1, count_ex2])
        
        story_counts = np.array(story_counts)
        x = np.arange(len(story_labels))
        width = 0.35
        
        axes[0,2].bar(x - width/2, story_counts[:,0], width, label='Ex1', alpha=0.8)
        axes[0,2].bar(x + width/2, story_counts[:,1], width, label='Ex2', alpha=0.8)
        axes[0,2].set_title('Participants per Story')
        axes[0,2].set_ylabel('Number of Participants')
        axes[0,2].set_xticks(x)
        axes[0,2].set_xticklabels(story_labels, rotation=45)
        axes[0,2].legend()
        
        # 4. ストーリー別推定値平均値の比較
        story_means_ex1 = [self.df[self.df['ex1_cover_story'] == story]['ex1_estimate'].mean() 
                          for story in sorted(self.df['ex1_cover_story'].unique())]
        story_means_ex2 = [self.df[self.df['ex2_cover_story'] == story]['ex2_estimate'].mean() 
                          for story in sorted(self.df['ex2_cover_story'].unique())]
        
        axes[1,0].scatter(story_means_ex1, story_means_ex2, alpha=0.7)
        axes[1,0].plot([-100, 100], [-100, 100], 'r--', alpha=0.5)
        axes[1,0].set_xlabel('Ex1 Mean Estimate')
        axes[1,0].set_ylabel('Ex2 Mean Estimate')
        axes[1,0].set_title('Story Mean Estimates: Ex1 vs Ex2')
        
        # ストーリーラベルを追加
        for i, story in enumerate(sorted(self.df['ex1_cover_story'].unique())):
            axes[1,0].annotate(f'S{story}', (story_means_ex1[i], story_means_ex2[i]))
        
        # 5. 条件別効果サイズ（ストーリー別）
        effect_sizes_ex1 = []
        effect_sizes_ex2 = []
        
        for story in sorted(self.df['ex1_cover_story'].unique()):
            # Ex1
            cond0_ex1 = self.df[(self.df['ex1_cover_story'] == story) & (self.df['Cond'] == 0)]['ex1_estimate']
            cond1_ex1 = self.df[(self.df['ex1_cover_story'] == story) & (self.df['Cond'] == 1)]['ex1_estimate']
            
            if len(cond0_ex1) > 0 and len(cond1_ex1) > 0:
                pooled_std = np.sqrt(((len(cond0_ex1) - 1) * cond0_ex1.var() + 
                                    (len(cond1_ex1) - 1) * cond1_ex1.var()) / 
                                   (len(cond0_ex1) + len(cond1_ex1) - 2))
                effect_size = (cond0_ex1.mean() - cond1_ex1.mean()) / pooled_std if pooled_std > 0 else 0
            else:
                effect_size = np.nan
            effect_sizes_ex1.append(effect_size)
            
            # Ex2
            cond0_ex2 = self.df[(self.df['ex2_cover_story'] == story) & (self.df['Cond'] == 0)]['ex2_estimate']
            cond1_ex2 = self.df[(self.df['ex2_cover_story'] == story) & (self.df['Cond'] == 1)]['ex2_estimate']
            
            if len(cond0_ex2) > 0 and len(cond1_ex2) > 0:
                pooled_std = np.sqrt(((len(cond0_ex2) - 1) * cond0_ex2.var() + 
                                    (len(cond1_ex2) - 1) * cond1_ex2.var()) / 
                                   (len(cond0_ex2) + len(cond1_ex2) - 2))
                effect_size = (cond0_ex2.mean() - cond1_ex2.mean()) / pooled_std if pooled_std > 0 else 0
            else:
                effect_size = np.nan
            effect_sizes_ex2.append(effect_size)
        
        x = np.arange(len(story_labels))
        axes[1,1].bar(x - width/2, effect_sizes_ex1, width, label='Ex1', alpha=0.8)
        axes[1,1].bar(x + width/2, effect_sizes_ex2, width, label='Ex2', alpha=0.8)
        axes[1,1].set_title('Condition Effect Size by Story (Cohen\'s d)')
        axes[1,1].set_ylabel('Effect Size')
        axes[1,1].set_xticks(x)
        axes[1,1].set_xticklabels(story_labels, rotation=45)
        axes[1,1].legend()
        axes[1,1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        
        # 6. CRTスコアとの相関（ストーリー別）
        if 'crt_correct_cnt' in self.df.columns:
            crt_corr_ex1 = []
            crt_corr_ex2 = []
            
            for story in sorted(self.df['ex1_cover_story'].unique()):
                # Ex1
                story_data_ex1 = self.df[self.df['ex1_cover_story'] == story]
                corr_ex1 = self.safe_corr(story_data_ex1['crt_correct_cnt'].values, 
                                        story_data_ex1['ex1_estimate'].values)
                crt_corr_ex1.append(corr_ex1)
                
                # Ex2
                story_data_ex2 = self.df[self.df['ex2_cover_story'] == story]
                corr_ex2 = self.safe_corr(story_data_ex2['crt_correct_cnt'].values, 
                                        story_data_ex2['ex2_estimate'].values)
                crt_corr_ex2.append(corr_ex2)
            
            axes[1,2].bar(x - width/2, crt_corr_ex1, width, label='Ex1', alpha=0.8)
            axes[1,2].bar(x + width/2, crt_corr_ex2, width, label='Ex2', alpha=0.8)
            axes[1,2].set_title('CRT-Estimate Correlation by Story')
            axes[1,2].set_ylabel('Correlation')
            axes[1,2].set_xticks(x)
            axes[1,2].set_xticklabels(story_labels, rotation=45)
            axes[1,2].legend()
            axes[1,2].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        else:
            axes[1,2].text(0.5, 0.5, 'CRT data not available', 
                          ha='center', va='center', transform=axes[1,2].transAxes)
            axes[1,2].set_title('CRT Analysis (No Data)')
        
        plt.tight_layout()
        plt.savefig('cover_story_analysis_visualization.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("→ 可視化を保存: cover_story_analysis_visualization.png")
    
    def run_comprehensive_analysis(self):
        """包括的なカバーストーリー分析を実行"""
        print("=== カバーストーリー包括分析開始 ===")
        
        self.load_data()
        
        # 各種分析を実行
        basic_stats = self.analyze_cover_story_basic_stats()
        difficulty_analysis = self.analyze_story_difficulty()
        consistency_analysis = self.analyze_story_consistency()
        interaction_analysis = self.analyze_story_condition_interaction()
        crt_analysis = self.analyze_story_crt_relationship()
        
        # 可視化
        self.create_story_visualization()
        
        # サマリーレポート作成
        self.create_summary_report(basic_stats, difficulty_analysis, consistency_analysis, 
                                 interaction_analysis, crt_analysis)
        
        print("\n=== カバーストーリー分析完了 ===")
        
        return {
            'basic_stats': basic_stats,
            'difficulty': difficulty_analysis,
            'consistency': consistency_analysis,
            'interaction': interaction_analysis,
            'crt_relationship': crt_analysis
        }
    
    def create_summary_report(self, basic_stats, difficulty_analysis, consistency_analysis, 
                            interaction_analysis, crt_analysis):
        """サマリーレポートを作成"""
        report_lines = []
        report_lines.append("=== カバーストーリー分析サマリーレポート ===\n")
        
        # 基本統計サマリー
        report_lines.append("## 基本統計")
        report_lines.append(f"総ストーリー数: {len(basic_stats['story'].unique())}")
        report_lines.append(f"総参加者数: {basic_stats['n_participants'].sum() // 2}")  # ex1とex2で重複を除く
        report_lines.append("")
        
        # 難易度分析サマリー
        if difficulty_analysis is not None:
            report_lines.append("## 難易度分析")
            high_var_stories = difficulty_analysis.nlargest(3, 'ex1_variance')['story'].tolist()
            low_var_stories = difficulty_analysis.nsmallest(3, 'ex1_variance')['story'].tolist()
            report_lines.append(f"高分散ストーリー（判断が困難）: {high_var_stories}")
            report_lines.append(f"低分散ストーリー（判断が容易）: {low_var_stories}")
            report_lines.append("")
        
        # 一貫性分析サマリー
        if consistency_analysis is not None and len(consistency_analysis) > 0:
            report_lines.append("## 一貫性分析")
            high_corr_stories = consistency_analysis.nlargest(3, 'ex1_ex2_correlation')['story'].tolist()
            low_corr_stories = consistency_analysis.nsmallest(3, 'ex1_ex2_correlation')['story'].tolist()
            report_lines.append(f"高一貫性ストーリー: {high_corr_stories}")
            report_lines.append(f"低一貫性ストーリー: {low_corr_stories}")
            report_lines.append("")
        
        # 条件効果サマリー
        if interaction_analysis is not None:
            report_lines.append("## 条件効果分析")
            strong_effect_stories = interaction_analysis[
                interaction_analysis['cohens_d'].abs() > 0.5
            ]['story'].unique().tolist()
            report_lines.append(f"強い条件効果のあるストーリー（|d| > 0.5）: {strong_effect_stories}")
            report_lines.append("")
        
        # CRT関係サマリー
        if crt_analysis is not None:
            report_lines.append("## CRT関係分析")
            high_crt_corr = crt_analysis[
                crt_analysis['crt_estimate_correlation'].abs() > 0.3
            ]['story'].unique().tolist()
            report_lines.append(f"CRTと強い相関のあるストーリー（|r| > 0.3）: {high_crt_corr}")
            report_lines.append("")
        
        # レポート保存
        with open('cover_story_analysis_summary.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print("→ サマリーレポートを保存: cover_story_analysis_summary.txt")


if __name__ == "__main__":
    print("=== カバーストーリー特性分析 ===")
    
    analyzer = CoverStoryAnalyzer("final_valid_updated.csv")
    results = analyzer.run_comprehensive_analysis()
    
    print("\n=== 分析完了 ===")
    print("作成されたファイル:")
    print("- cover_story_basic_stats.csv")
    print("- cover_story_difficulty_analysis.csv")
    print("- cover_story_consistency_analysis.csv")
    print("- cover_story_condition_interaction.csv")
    print("- cover_story_crt_relationship.csv")
    print("- cover_story_analysis_visualization.png")
    print("- cover_story_analysis_summary.txt")
