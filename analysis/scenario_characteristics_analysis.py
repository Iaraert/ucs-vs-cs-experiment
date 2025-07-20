"""
scenario_characteristics_analysis.py

cover_story_cs_ucs_correlation_results.csvを元に
シナリオ特性を条件（サマリー, オンライン, 対称的, 非対称的）下で分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
import japanize_matplotlib
import matplotlib
import matplotlib.font_manager as fm

# 確実な日本語フォント設定
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
matplotlib.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

class ScenarioCharacteristicsAnalyzer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None
        
    def load_and_prepare_data(self):
        """データを読み込み、前処理"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.df.shape}")
        
        # 基本情報表示
        print(f"\n=== データ概要 ===")
        print(f"実験タイプ: {list(self.df['実験タイプ'].unique())}")
        print(f"条件: {list(self.df['条件'].unique())}")
        print(f"CS閾値: {sorted(self.df['CS_threshold'].unique())}")
        print(f"ストーリー数: {len(self.df['ストーリー'].unique())}")
        print(f"グループ: {list(self.df['グループ'].unique())}")
        
        # threshold=1.0かつ全体グループのデータで分析
        self.analysis_df = self.df[
            (self.df['CS_threshold'] == 1.0) & 
            (self.df['グループ'] == '全体')
        ].copy()
        
        print(f"\n分析対象データ: {self.analysis_df.shape}")
        return self.analysis_df
    
    def basic_statistics_by_condition(self):
        """条件別の基本統計量"""
        print(f"\n=== 条件別基本統計量 ===")
        
        # メトリクス列
        metrics = ['CS', 'UCS', 'P(E|C)', 'P(C|E)', 'ΔP', 'pARIs', 'DFH', 'Dice', 'CRT_mean']
        
        results = {}
        
        # 実験タイプ × 条件での統計
        for exp_type in self.analysis_df['実験タイプ'].unique():
            for condition in self.analysis_df['条件'].unique():
                subset = self.analysis_df[
                    (self.analysis_df['実験タイプ'] == exp_type) & 
                    (self.analysis_df['条件'] == condition)
                ]
                
                if subset.empty:
                    continue
                
                key = f"{exp_type}_{condition}"
                results[key] = {}
                
                print(f"\n{exp_type} - {condition} (n={len(subset)})")
                
                for metric in metrics:
                    if metric in subset.columns:
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
        
        return results
    
    def scenario_difficulty_analysis(self):
        """シナリオ難易度分析"""
        print(f"\n=== シナリオ難易度分析 ===")
        
        # CRT平均スコアによる難易度分類
        story_stats = self.analysis_df.groupby(['ストーリー', '実験タイプ', '条件']).agg({
            'CRT_mean': 'first',
            'CS': 'first',
            'UCS': 'first',
            'n': 'first'
        }).reset_index()
        
        # CRT平均による難易度分類
        crt_overall_mean = story_stats['CRT_mean'].mean()
        story_stats['難易度'] = story_stats['CRT_mean'].apply(
            lambda x: '高' if x >= crt_overall_mean else '低'
        )
        
        print(f"CRT全体平均: {crt_overall_mean:.3f}")
        print(f"高難易度ストーリー: {len(story_stats[story_stats['難易度'] == '高'])}")
        print(f"低難易度ストーリー: {len(story_stats[story_stats['難易度'] == '低'])}")
        
        # 難易度別のCS/UCS分析
        difficulty_analysis = story_stats.groupby(['実験タイプ', '条件', '難易度']).agg({
            'CS': ['mean', 'std', 'count'],
            'UCS': ['mean', 'std', 'count'],
            'CRT_mean': ['mean', 'std']
        }).round(3)
        
        print(f"\n=== 難易度別CS/UCS分析 ===")
        print(difficulty_analysis)
        
        return story_stats, difficulty_analysis
    
    def correlation_pattern_analysis(self):
        """相関パターン分析"""
        print(f"\n=== 相関パターン分析 ===")
        
        # CS/UCS強度による分類
        def classify_correlation(cs_val, ucs_val, threshold=0.3):
            cs_strong = abs(cs_val) >= threshold
            ucs_strong = abs(ucs_val) >= threshold
            
            if cs_strong and ucs_strong:
                return 'CS+UCS強'
            elif cs_strong:
                return 'CS強'
            elif ucs_strong:
                return 'UCS強'
            else:
                return '弱相関'
        
        self.analysis_df['相関パターン'] = self.analysis_df.apply(
            lambda row: classify_correlation(row['CS'], row['UCS']), axis=1
        )
        
        # パターン別集計
        pattern_counts = self.analysis_df.groupby(['実験タイプ', '条件', '相関パターン']).size().unstack(fill_value=0)
        print(f"\n相関パターン分布:")
        print(pattern_counts)
        
        # パターン別の特徴分析
        pattern_stats = self.analysis_df.groupby('相関パターン').agg({
            'CS': ['mean', 'std'],
            'UCS': ['mean', 'std'],
            'CRT_mean': ['mean', 'std'],
            'n': 'sum'
        }).round(3)
        
        print(f"\n相関パターン別統計:")
        print(pattern_stats)
        
        return pattern_counts, pattern_stats
    
    def statistical_tests(self):
        """統計検定"""
        print(f"\n=== 統計検定 ===")
        
        results = {}
        
        # 1. 実験タイプ間比較（サマリー vs オンライン）
        summary_data = self.analysis_df[self.analysis_df['実験タイプ'] == 'サマリー']
        online_data = self.analysis_df[self.analysis_df['実験タイプ'] == 'オンライン']
        
        for metric in ['CS', 'UCS', 'CRT_mean']:
            if metric in self.analysis_df.columns:
                summary_vals = summary_data[metric].dropna()
                online_vals = online_data[metric].dropna()
                
                if len(summary_vals) > 0 and len(online_vals) > 0:
                    # t検定
                    t_stat, p_val = stats.ttest_ind(summary_vals, online_vals)
                    # Mann-Whitney U検定
                    u_stat, u_p_val = stats.mannwhitneyu(summary_vals, online_vals, alternative='two-sided')
                    
                    results[f'実験タイプ_{metric}'] = {
                        't_test': {'statistic': t_stat, 'p_value': p_val},
                        'mann_whitney': {'statistic': u_stat, 'p_value': u_p_val},
                        'summary_mean': summary_vals.mean(),
                        'online_mean': online_vals.mean()
                    }
                    
                    print(f"\n{metric} - 実験タイプ比較:")
                    print(f"  サマリー: M={summary_vals.mean():.3f}, SD={summary_vals.std():.3f}")
                    print(f"  オンライン: M={online_vals.mean():.3f}, SD={online_vals.std():.3f}")
                    print(f"  t検定: t={t_stat:.3f}, p={p_val:.3f}")
                    print(f"  Mann-Whitney: U={u_stat:.3f}, p={u_p_val:.3f}")
        
        # 2. 条件間比較（対称否定 vs 非対称否定）
        symmetric_data = self.analysis_df[self.analysis_df['条件'] == '対称否定']
        asymmetric_data = self.analysis_df[self.analysis_df['条件'] == '非対称否定']
        
        for metric in ['CS', 'UCS', 'CRT_mean']:
            if metric in self.analysis_df.columns:
                sym_vals = symmetric_data[metric].dropna()
                asym_vals = asymmetric_data[metric].dropna()
                
                if len(sym_vals) > 0 and len(asym_vals) > 0:
                    # t検定
                    t_stat, p_val = stats.ttest_ind(sym_vals, asym_vals)
                    # Mann-Whitney U検定
                    u_stat, u_p_val = stats.mannwhitneyu(sym_vals, asym_vals, alternative='two-sided')
                    
                    results[f'条件_{metric}'] = {
                        't_test': {'statistic': t_stat, 'p_value': p_val},
                        'mann_whitney': {'statistic': u_stat, 'p_value': u_p_val},
                        'symmetric_mean': sym_vals.mean(),
                        'asymmetric_mean': asym_vals.mean()
                    }
                    
                    print(f"\n{metric} - 条件比較:")
                    print(f"  対称否定: M={sym_vals.mean():.3f}, SD={sym_vals.std():.3f}")
                    print(f"  非対称否定: M={asym_vals.mean():.3f}, SD={asym_vals.std():.3f}")
                    print(f"  t検定: t={t_stat:.3f}, p={p_val:.3f}")
                    print(f"  Mann-Whitney: U={u_stat:.3f}, p={u_p_val:.3f}")
        
        return results
    
    def create_visualizations(self):
        """可視化作成"""
        print(f"\n=== 可視化作成 ===")
        
        # フォント設定の確実な適用
        try:
            # japanize_matplotlibの設定を再適用
            import japanize_matplotlib
            plt.rcParams['axes.unicode_minus'] = False
            print("japanize_matplotlib設定完了")
        except Exception as e:
            print(f"フォント設定警告: {e}")
            # フォールバック設定
            plt.rcParams['font.family'] = ['DejaVu Sans']
        
        # 図のセットアップ
        fig, axes = plt.subplots(3, 2, figsize=(15, 18))
        fig.suptitle('Scenario Characteristics Analysis (シナリオ特性分析)', fontsize=16)
        
        # 1. 実験タイプ・条件別CS/UCS平均値
        condition_means = self.analysis_df.groupby(['実験タイプ', '条件'])[['CS', 'UCS']].mean()
        
        # 日本語ラベルを英語に変換
        exp_type_map = {'サマリー': 'Summary', 'オンライン': 'Online'}
        condition_map = {'対称否定': 'Symmetric', '非対称否定': 'Asymmetric'}
        
        x_labels = []
        for exp, cond in condition_means.index:
            exp_en = exp_type_map.get(exp, exp)
            cond_en = condition_map.get(cond, cond)
            x_labels.append(f"{exp_en}\n{cond_en}")
            
        x_pos = np.arange(len(x_labels))
        width = 0.35
        axes[0,0].bar(x_pos - width/2, condition_means['CS'], width, label='CS', alpha=0.8)
        axes[0,0].bar(x_pos + width/2, condition_means['UCS'], width, label='UCS', alpha=0.8)
        axes[0,0].set_title('CS/UCS by Experiment Type and Condition\n(実験タイプ・条件別 CS/UCS 平均値)')
        axes[0,0].set_ylabel('Correlation (相関係数)')
        axes[0,0].set_xticks(x_pos)
        axes[0,0].set_xticklabels(x_labels, rotation=45)
        axes[0,0].legend()
        axes[0,0].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        # 2. CRT平均スコア分布
        for i, exp_type in enumerate(self.analysis_df['実験タイプ'].unique()):
            for j, condition in enumerate(self.analysis_df['条件'].unique()):
                subset = self.analysis_df[
                    (self.analysis_df['実験タイプ'] == exp_type) & 
                    (self.analysis_df['条件'] == condition)
                ]
                if not subset.empty:
                    exp_en = exp_type_map.get(exp_type, exp_type)
                    cond_en = condition_map.get(condition, condition)
                    label = f"{exp_en}-{cond_en}"
                    axes[0,1].hist(subset['CRT_mean'].dropna(), alpha=0.6, label=label, bins=10)
                    axes[0,1].set_title('CRT Score Distribution by Conditions\n(条件別CRTスコア分布)')
                    axes[0,1].set_xlabel('CRT Mean Score (CRT平均スコア)')
                    axes[0,1].set_ylabel('Frequency (頻度)')
                    axes[0,1].legend()
        
        # 3. CS vs UCS散布図（条件別）
        colors = ['red', 'blue', 'green', 'orange']
        markers = ['o', 's', '^', 'D']
        
        i = 0
        for exp_type in self.analysis_df['実験タイプ'].unique():
            for condition in self.analysis_df['条件'].unique():
                subset = self.analysis_df[
                    (self.analysis_df['実験タイプ'] == exp_type) & 
                    (self.analysis_df['条件'] == condition)
                ]
                if not subset.empty:
                    exp_en = exp_type_map.get(exp_type, exp_type)
                    cond_en = condition_map.get(condition, condition)
                    axes[1,0].scatter(subset['CS'], subset['UCS'], 
                                    c=colors[i % len(colors)], 
                                    marker=markers[i % len(markers)],
                                    label=f"{exp_en}-{cond_en}", 
                                    alpha=0.7, s=60)
                    i += 1
        
        axes[1,0].set_xlabel('CS Correlation (CS相関)')
        axes[1,0].set_ylabel('UCS Correlation (UCS相関)')
        axes[1,0].set_title('CS vs UCS Correlation by Conditions\n(条件別 CS vs UCS 相関)')
        axes[1,0].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        axes[1,0].axvline(x=0, color='k', linestyle='-', alpha=0.3)
        axes[1,0].legend()
          # 4. ストーリー別CS相関（条件別色分け）
        story_cs = self.analysis_df.pivot_table(
            index='ストーリー', 
            columns=['実験タイプ', '条件'], 
            values='CS', 
            aggfunc='first'
        )
        
        # ヒートマップ
        im = axes[1,1].imshow(story_cs.T.values, cmap='RdBu_r', aspect='auto')
        axes[1,1].set_title('ストーリー・条件別CS相関ヒートマップ\n(CS Correlation Heatmap by Story and Condition)')
        axes[1,1].set_xlabel('ストーリー番号 (Story Number)')
        axes[1,1].set_ylabel('条件 (Condition)')
        axes[1,1].set_xticks(range(len(story_cs.index)))
        axes[1,1].set_xticklabels(story_cs.index)
        axes[1,1].set_yticks(range(len(story_cs.columns)))
        
        # Y軸ラベルを英語に変換
        y_labels = []
        for exp, cond in story_cs.columns:
            exp_en = exp_type_map.get(exp, exp)
            cond_en = condition_map.get(cond, cond)
            y_labels.append(f"{exp_en}-{cond_en}")
        axes[1,1].set_yticklabels(y_labels, rotation=0)
        
        # カラーバー
        plt.colorbar(im, ax=axes[1,1])
        
        # 5. 相関強度分布
        cs_abs = self.analysis_df['CS'].abs()
        ucs_abs = self.analysis_df['UCS'].abs()
        
        axes[2,0].hist(cs_abs, alpha=0.6, label='|CS|', bins=15, color='blue')
        axes[2,0].hist(ucs_abs, alpha=0.6, label='|UCS|', bins=15, color='red')
        axes[2,0].set_title('相関強度分布\n(Distribution of Correlation Magnitudes)')
        axes[2,0].set_xlabel('|相関係数| (|Correlation|)')
        axes[2,0].set_ylabel('頻度 (Frequency)')
        axes[2,0].legend()
        axes[2,0].axvline(x=0.3, color='k', linestyle='--', alpha=0.5, label='閾値=0.3')
        
        # 6. CRT vs CS/UCS関係
        axes[2,1].scatter(self.analysis_df['CRT_mean'], self.analysis_df['CS'], 
                         alpha=0.6, label='CS', color='blue')
        axes[2,1].scatter(self.analysis_df['CRT_mean'], self.analysis_df['UCS'], 
                         alpha=0.6, label='UCS', color='red')
        axes[2,1].set_xlabel('CRTスコア (CRT Mean Score)')
        axes[2,1].set_ylabel('相関係数 (Correlation)')
        axes[2,1].set_title('CRTスコア vs CS/UCS相関\n(CRT Score vs CS/UCS Correlation)')
        axes[2,1].legend()
        axes[2,1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('scenario_characteristics_analysis.png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.show()
        
        print("→ 可視化を保存: scenario_characteristics_analysis.png")
    
    def save_detailed_results(self, basic_stats, story_stats, difficulty_analysis, 
                            pattern_counts, pattern_stats, test_results):
        """詳細結果をCSVファイルに保存"""
        print(f"\n=== 結果保存 ===")
        
        # 1. 基本統計をDataFrameに変換
        basic_stats_rows = []
        for condition, metrics in basic_stats.items():
            for metric, stats in metrics.items():
                basic_stats_rows.append({
                    '条件': condition,
                    'メトリクス': metric,
                    '平均': stats['mean'],
                    '標準偏差': stats['std'],
                    '最小値': stats['min'],
                    '最大値': stats['max'],
                    'サンプル数': stats['count']
                })
        
        basic_stats_df = pd.DataFrame(basic_stats_rows)
        basic_stats_df.to_csv('scenario_basic_statistics.csv', index=False, encoding='utf-8-sig')
        
        # 2. ストーリー統計保存
        story_stats.to_csv('scenario_story_statistics.csv', index=False, encoding='utf-8-sig')
        
        # 3. 難易度分析保存
        difficulty_analysis.to_csv('scenario_difficulty_analysis.csv', encoding='utf-8-sig')
        
        # 4. 相関パターン保存
        pattern_counts.to_csv('scenario_correlation_patterns.csv', encoding='utf-8-sig')
        pattern_stats.to_csv('scenario_pattern_statistics.csv', encoding='utf-8-sig')
        
        # 5. 統計検定結果保存
        test_results_rows = []
        for test_name, results in test_results.items():
            test_results_rows.append({
                '検定': test_name,
                't統計量': results.get('t_test', {}).get('statistic', None),
                't検定p値': results.get('t_test', {}).get('p_value', None),
                'U統計量': results.get('mann_whitney', {}).get('statistic', None),
                'Mann-Whitney p値': results.get('mann_whitney', {}).get('p_value', None),
                'グループ1平均': list(results.values())[2] if len(results) > 2 else None,
                'グループ2平均': list(results.values())[3] if len(results) > 3 else None
            })
        
        test_results_df = pd.DataFrame(test_results_rows)
        test_results_df.to_csv('scenario_statistical_tests.csv', index=False, encoding='utf-8-sig')
        
        print("→ 保存されたファイル:")
        print("  - scenario_basic_statistics.csv")
        print("  - scenario_story_statistics.csv")
        print("  - scenario_difficulty_analysis.csv")
        print("  - scenario_correlation_patterns.csv")
        print("  - scenario_pattern_statistics.csv")
        print("  - scenario_statistical_tests.csv")
    
    def generate_summary_report(self, basic_stats, story_stats, difficulty_analysis, 
                              pattern_counts, pattern_stats, test_results):
        """サマリーレポート生成"""
        report = []
        report.append("=" * 60)
        report.append("シナリオ特性分析サマリーレポート")
        report.append("=" * 60)
        report.append("")
        
        # 基本情報
        report.append("## 1. データ概要")
        report.append(f"分析対象データ数: {len(self.analysis_df)}")
        report.append(f"実験タイプ: {list(self.analysis_df['実験タイプ'].unique())}")
        report.append(f"条件: {list(self.analysis_df['条件'].unique())}")
        report.append(f"ストーリー数: {len(self.analysis_df['ストーリー'].unique())}")
        report.append("")
        
        # 主要な発見
        report.append("## 2. 主要な発見")
        
        # CS/UCS平均値
        overall_cs_mean = self.analysis_df['CS'].mean()
        overall_ucs_mean = self.analysis_df['UCS'].mean()
        report.append(f"全体CS平均: {overall_cs_mean:.3f}")
        report.append(f"全体UCS平均: {overall_ucs_mean:.3f}")
        
        # 条件別差異
        summary_cs = self.analysis_df[self.analysis_df['実験タイプ'] == 'サマリー']['CS'].mean()
        online_cs = self.analysis_df[self.analysis_df['実験タイプ'] == 'オンライン']['CS'].mean()
        
        if not np.isnan(summary_cs) and not np.isnan(online_cs):
            report.append(f"サマリー実験CS平均: {summary_cs:.3f}")
            report.append(f"オンライン実験CS平均: {online_cs:.3f}")
            report.append(f"実験タイプ間CS差: {abs(summary_cs - online_cs):.3f}")
        
        # 強相関ストーリー
        strong_cs_stories = self.analysis_df[self.analysis_df['CS'].abs() >= 0.5]['ストーリー'].unique()
        strong_ucs_stories = self.analysis_df[self.analysis_df['UCS'].abs() >= 0.5]['ストーリー'].unique()
        
        if len(strong_cs_stories) > 0:
            report.append(f"CS強相関ストーリー (|r|≥0.5): {list(strong_cs_stories)}")
        if len(strong_ucs_stories) > 0:
            report.append(f"UCS強相関ストーリー (|r|≥0.5): {list(strong_ucs_stories)}")
        
        report.append("")
        
        # 統計的有意差
        report.append("## 3. 統計的有意差")
        for test_name, results in test_results.items():
            t_p = results.get('t_test', {}).get('p_value', 1)
            mw_p = results.get('mann_whitney', {}).get('p_value', 1)
            
            if t_p < 0.05 or mw_p < 0.05:
                report.append(f"{test_name}: 有意差あり (t検定p={t_p:.3f}, MW検定p={mw_p:.3f})")
        
        report.append("")
        
        # 相関パターン
        report.append("## 4. 相関パターン分析")
        for pattern in pattern_stats.index:
            count = pattern_stats.loc[pattern, ('n', 'sum')]
            cs_mean = pattern_stats.loc[pattern, ('CS', 'mean')]
            ucs_mean = pattern_stats.loc[pattern, ('UCS', 'mean')]
            report.append(f"{pattern}: {count}件 (CS平均={cs_mean:.3f}, UCS平均={ucs_mean:.3f})")
        
        report.append("")
        report.append("=" * 60)
        
        # ファイル保存
        with open('scenario_characteristics_summary_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print("→ サマリーレポートを保存: scenario_characteristics_summary_report.txt")
        
        return report
    
    def run_comprehensive_analysis(self):
        """包括的な分析実行"""
        print("=" * 60)
        print("シナリオ特性分析開始")
        print("=" * 60)
        
        # データ準備
        self.load_and_prepare_data()
        
        # 基本統計
        basic_stats = self.basic_statistics_by_condition()
        
        # シナリオ難易度分析
        story_stats, difficulty_analysis = self.scenario_difficulty_analysis()
        
        # 相関パターン分析
        pattern_counts, pattern_stats = self.correlation_pattern_analysis()
        
        # 統計検定
        test_results = self.statistical_tests()
        
        # 可視化
        self.create_visualizations()
        
        # 結果保存
        self.save_detailed_results(basic_stats, story_stats, difficulty_analysis, 
                                 pattern_counts, pattern_stats, test_results)
        
        # サマリーレポート
        report = self.generate_summary_report(basic_stats, story_stats, difficulty_analysis, 
                                            pattern_counts, pattern_stats, test_results)
        
        print("\n" + "=" * 60)
        print("シナリオ特性分析完了")
        print("=" * 60)
        
        return {
            'basic_stats': basic_stats,
            'story_stats': story_stats,
            'difficulty_analysis': difficulty_analysis,
            'pattern_counts': pattern_counts,
            'pattern_stats': pattern_stats,
            'test_results': test_results,
            'report': report
        }


if __name__ == "__main__":
    analyzer = ScenarioCharacteristicsAnalyzer("cover_story_cs_ucs_correlation_results.csv")
    results = analyzer.run_comprehensive_analysis()
