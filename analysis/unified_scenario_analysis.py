"""
unified_scenario_analysis.py

シナリオ分析統合版
- シナリオ効果分析（scenario_effect_analysis.py）
- シナリオ特性分析（scenario_characteristics_analysis.py）

統合機能:
1. シナリオが各刺激の評定に与える影響分析
2. シナリオ特性の条件別分析
3. シナリオ間の統計的比較
4. 難易度・効果サイズ分析
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import f_oneway, ttest_rel, pearsonr
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
import japanize_matplotlib
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
matplotlib.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")


class UnifiedScenarioAnalyzer:
    """統合シナリオ分析クラス"""
    
    def __init__(self):
        self.df = None
        self.analysis_df = None
        self.results = {}
        
    def load_scenario_effect_data(self, csv_path: str):
        """シナリオ効果分析用データ読み込み"""
        self.df = pd.read_csv(csv_path)
        print(f"シナリオ効果データ読み込み完了: {csv_path} (shape={self.df.shape})")
        
        # 条件を英語に変換
        condition_mapping = {
            "非対称否定_サマリー": "Asymmetric_Summary",
            "対称否定_サマリー": "Symmetric_Summary", 
            "非対称否定_オンライン": "Asymmetric_Online",
            "対称否定_オンライン": "Symmetric_Online"
        }
        self.df['condition_en'] = self.df['condition'].map(condition_mapping)
        
        print("条件マッピング完了:")
        print(self.df['condition_en'].value_counts())
        return self.df
        
    def load_scenario_characteristics_data(self, csv_path: str):
        """シナリオ特性分析用データ読み込み"""
        self.analysis_df = pd.read_csv(csv_path)
        print(f"シナリオ特性データ読み込み完了: {csv_path} (shape={self.analysis_df.shape})")
        
        print(f"\n=== データ概要 ===")
        if '実験タイプ' in self.analysis_df.columns:
            print(f"実験タイプ: {list(self.analysis_df['実験タイプ'].unique())}")
        if '条件' in self.analysis_df.columns:
            print(f"条件: {list(self.analysis_df['条件'].unique())}")
        if 'CS_threshold' in self.analysis_df.columns:
            print(f"CS閾値: {sorted(self.analysis_df['CS_threshold'].unique())}")
        if 'ストーリー' in self.analysis_df.columns:
            print(f"ストーリー数: {len(self.analysis_df['ストーリー'].unique())}")
        if 'グループ' in self.analysis_df.columns:
            print(f"グループ: {list(self.analysis_df['グループ'].unique())}")
            
        # threshold=1.0かつ全体グループのデータで分析
        if 'CS_threshold' in self.analysis_df.columns and 'グループ' in self.analysis_df.columns:
            self.analysis_df = self.analysis_df[
                (self.analysis_df['CS_threshold'] == 1.0) & 
                (self.analysis_df['グループ'] == '全体')
            ].copy()
            print(f"\n分析対象データ: {self.analysis_df.shape}")
            
        return self.analysis_df
        
    def calculate_scenario_effects(self):
        """シナリオ効果を計算"""
        print("\n" + "="*80)
        print("シナリオ効果分析")
        print("="*80)
        
        if self.df is None:
            raise ValueError("シナリオ効果データが読み込まれていません。load_scenario_effect_data()を実行してください。")
            
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
                valid_data = sample_data[sample_data['count'] > 0] if 'count' in sample_data.columns else sample_data
                
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
                
                ratings = valid_data['mean_estimate'].values if 'mean_estimate' in valid_data.columns else valid_data['estimate'].values
                
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
                    story_col = 'cover_story' if 'cover_story' in valid_data.columns else 'story'
                    if story_col in valid_data.columns:
                        scenario_groups = [valid_data[valid_data[story_col] == story]['mean_estimate'].values 
                                         for story in valid_data[story_col].unique()]
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
                else:
                    f_stat, p_value = np.nan, np.nan
                
                results.append({
                    'condition': condition,
                    'sample_number': sample_num,
                    'n_scenarios': len(valid_data),
                    'mean_rating': mean_rating,
                    'std_rating': std_rating,
                    'min_rating': min_rating,
                    'max_rating': max_rating,
                    'range_rating': range_rating,
                    'cv_rating': cv_rating,
                    'scenario_effect_size': scenario_effect_size,
                    'anova_f': f_stat,
                    'anova_p': p_value
                })
                
        scenario_effects_df = pd.DataFrame(results)
        self.results['scenario_effects'] = scenario_effects_df
        
        # 結果表示
        print("\n--- シナリオ効果サマリー ---")
        for condition in scenario_effects_df['condition'].unique():
            if pd.isna(condition):
                continue
            cond_data = scenario_effects_df[scenario_effects_df['condition'] == condition]
            mean_effect = cond_data['scenario_effect_size'].mean()
            mean_range = cond_data['range_rating'].mean()
            significant_count = len(cond_data[cond_data['anova_p'] < 0.05])
            
            print(f"{condition}:")
            print(f"  平均効果サイズ: {mean_effect:.3f}")
            print(f"  平均レンジ: {mean_range:.3f}")
            print(f"  有意なシナリオ効果: {significant_count}/{len(cond_data)}")
            
        return scenario_effects_df
        
    def analyze_scenario_characteristics(self):
        """シナリオ特性分析"""
        print("\n" + "="*80)
        print("シナリオ特性分析")
        print("="*80)
        
        if self.analysis_df is None:
            raise ValueError("シナリオ特性データが読み込まれていません。load_scenario_characteristics_data()を実行してください。")
            
        # メトリクス列
        metrics = ['CS', 'UCS', 'P(E|C)', 'P(C|E)', 'ΔP', 'pARIs', 'DFH', 'Dice', 'CRT_mean']
        available_metrics = [m for m in metrics if m in self.analysis_df.columns]
        
        results = {}
        
        print(f"\n=== 条件別基本統計量 ===")
        print(f"利用可能メトリクス: {available_metrics}")
        
        # 実験タイプ × 条件での統計
        exp_types = self.analysis_df['実験タイプ'].unique() if '実験タイプ' in self.analysis_df.columns else ['全体']
        conditions = self.analysis_df['条件'].unique() if '条件' in self.analysis_df.columns else ['全体']
        
        for exp_type in exp_types:
            for condition in conditions:
                if '実験タイプ' in self.analysis_df.columns and '条件' in self.analysis_df.columns:
                    subset = self.analysis_df[
                        (self.analysis_df['実験タイプ'] == exp_type) & 
                        (self.analysis_df['条件'] == condition)
                    ]
                else:
                    subset = self.analysis_df
                
                if subset.empty:
                    continue
                
                key = f"{exp_type}_{condition}"
                results[key] = {}
                
                print(f"\n{exp_type} - {condition} (n={len(subset)})")
                
                for metric in available_metrics:
                    values = subset[metric].dropna()
                    if len(values) > 0:
                        mean_val = values.mean()
                        std_val = values.std()
                        min_val = values.min()
                        max_val = values.max()
                        
                        results[key][metric] = {
                            'mean': mean_val,
                            'std': std_val,
                            'min': min_val,
                            'max': max_val,
                            'count': len(values)
                        }
                        
                        print(f"  {metric}: M={mean_val:.3f}, SD={std_val:.3f}, Range=[{min_val:.3f}, {max_val:.3f}]")
        
        self.results['characteristics'] = results
        return results
        
    def scenario_difficulty_analysis(self):
        """シナリオ難易度分析"""
        print("\n" + "="*80)
        print("シナリオ難易度分析")
        print("="*80)
        
        if self.analysis_df is None:
            return None
            
        # CRT平均値による難易度分類
        if 'CRT_mean' in self.analysis_df.columns:
            crt_values = self.analysis_df['CRT_mean'].dropna()
            if len(crt_values) > 0:
                crt_median = crt_values.median()
                self.analysis_df['difficulty'] = self.analysis_df['CRT_mean'].apply(
                    lambda x: 'High' if x > crt_median else 'Low' if pd.notna(x) else 'Unknown'
                )
                
                print(f"CRT中央値による難易度分類 (中央値: {crt_median:.3f})")
                difficulty_counts = self.analysis_df['difficulty'].value_counts()
                print(difficulty_counts)
                
                # 難易度別の特性比較
                if 'CS' in self.analysis_df.columns and 'UCS' in self.analysis_df.columns:
                    for difficulty in ['High', 'Low']:
                        subset = self.analysis_df[self.analysis_df['difficulty'] == difficulty]
                        if len(subset) > 0:
                            cs_mean = subset['CS'].mean()
                            ucs_mean = subset['UCS'].mean()
                            print(f"{difficulty} Difficulty: CS={cs_mean:.3f}, UCS={ucs_mean:.3f}")
        
        return self.analysis_df
        
    def correlation_analysis(self):
        """メトリクス間相関分析"""
        print("\n" + "="*80)
        print("メトリクス間相関分析")
        print("="*80)
        
        if self.analysis_df is None:
            return None
            
        metrics = ['CS', 'UCS', 'P(E|C)', 'P(C|E)', 'ΔP', 'pARIs', 'DFH', 'Dice', 'CRT_mean']
        available_metrics = [m for m in metrics if m in self.analysis_df.columns]
        
        if len(available_metrics) < 2:
            print("相関分析に必要な数値メトリクスが不足しています。")
            return None
            
        # 相関行列計算
        corr_data = self.analysis_df[available_metrics].corr()
        
        print("相関行列:")
        print(corr_data.round(3))
        
        # 高い相関（|r| > 0.7）の組み合わせ
        high_corr_pairs = []
        for i in range(len(available_metrics)):
            for j in range(i+1, len(available_metrics)):
                corr_val = corr_data.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corr_pairs.append((available_metrics[i], available_metrics[j], corr_val))
                    
        print(f"\n高相関ペア (|r| > 0.7):")
        for metric1, metric2, corr_val in high_corr_pairs:
            print(f"  {metric1} - {metric2}: r = {corr_val:.3f}")
            
        self.results['correlation'] = corr_data
        return corr_data
        
    def create_visualization(self, output_dir: str = "scenario_analysis"):
        """可視化作成"""
        os.makedirs(output_dir, exist_ok=True)
        
        # シナリオ効果可視化
        if 'scenario_effects' in self.results:
            df_effects = self.results['scenario_effects']
            
            # 効果サイズの条件別比較
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=df_effects, x='condition', y='scenario_effect_size')
            plt.title('シナリオ効果サイズの条件別分布')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'scenario_effect_sizes.png'), dpi=300)
            plt.close()
            
            # レンジの条件別比較
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=df_effects, x='condition', y='range_rating')
            plt.title('シナリオ評定レンジの条件別分布')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'scenario_ranges.png'), dpi=300)
            plt.close()
            
        # 相関ヒートマップ
        if 'correlation' in self.results:
            plt.figure(figsize=(10, 8))
            sns.heatmap(self.results['correlation'], annot=True, cmap='coolwarm', center=0,
                       square=True, fmt='.3f')
            plt.title('メトリクス間相関行列')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'correlation_heatmap.png'), dpi=300)
            plt.close()
            
        print(f"可視化ファイルを {output_dir} に保存しました。")
        
    def save_results(self, output_dir: str = "scenario_analysis"):
        """結果保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        # シナリオ効果結果
        if 'scenario_effects' in self.results:
            filename = os.path.join(output_dir, "scenario_effects_analysis.csv")
            self.results['scenario_effects'].to_csv(filename, index=False)
            print(f"保存: {filename}")
            
        # 特性分析結果
        if 'characteristics' in self.results:
            # 辞書形式のデータをDataFrameに変換
            char_rows = []
            for key, metrics in self.results['characteristics'].items():
                for metric, stats in metrics.items():
                    char_rows.append({
                        'condition': key,
                        'metric': metric,
                        'mean': stats['mean'],
                        'std': stats['std'],
                        'min': stats['min'],
                        'max': stats['max'],
                        'count': stats['count']
                    })
            char_df = pd.DataFrame(char_rows)
            filename = os.path.join(output_dir, "scenario_characteristics_analysis.csv")
            char_df.to_csv(filename, index=False)
            print(f"保存: {filename}")
            
        # 相関分析結果
        if 'correlation' in self.results:
            filename = os.path.join(output_dir, "scenario_correlation_analysis.csv")
            self.results['correlation'].to_csv(filename)
            print(f"保存: {filename}")
            
        print(f"\n全結果を {output_dir} に保存しました。")


def main():
    parser = argparse.ArgumentParser(description="統合シナリオ分析")
    parser.add_argument("--mode", choices=["effect", "characteristics", "all"], default="all",
                        help="分析モード選択")
    parser.add_argument("--effect_csv", default="sample_story_averages_by_condition.csv",
                        help="シナリオ効果分析用CSVファイル")
    parser.add_argument("--char_csv", default="cover_story_cs_ucs_correlation_results.csv",
                        help="シナリオ特性分析用CSVファイル")
    parser.add_argument("--output_dir", default="scenario_analysis",
                        help="出力ディレクトリ")
    parser.add_argument("--visualize", action="store_true",
                        help="可視化を作成")
                        
    args = parser.parse_args()
    
    analyzer = UnifiedScenarioAnalyzer()
    
    try:
        if args.mode in ["effect", "all"]:
            if os.path.exists(args.effect_csv):
                analyzer.load_scenario_effect_data(args.effect_csv)
                analyzer.calculate_scenario_effects()
            else:
                print(f"シナリオ効果データファイルが見つかりません: {args.effect_csv}")
                
        if args.mode in ["characteristics", "all"]:
            if os.path.exists(args.char_csv):
                analyzer.load_scenario_characteristics_data(args.char_csv)
                analyzer.analyze_scenario_characteristics()
                analyzer.scenario_difficulty_analysis()
                analyzer.correlation_analysis()
            else:
                print(f"シナリオ特性データファイルが見つかりません: {args.char_csv}")
                
        # 結果保存
        analyzer.save_results(args.output_dir)
        
        # 可視化作成
        if args.visualize:
            analyzer.create_visualization(args.output_dir)
            
        print("\n統合シナリオ分析完了！")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
