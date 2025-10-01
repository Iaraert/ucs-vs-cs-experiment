# -*- coding: utf-8 -*-
"""
unified_phase_analysis.py

Phase分析の統合版
以下の機能を統合:
1. Phase間平均値差分析 (phase/phase_homogeneity_analysis.py)
2. Phase間相関等質性分析 (phase/phase_correlation_homogeneity_analysis.py)

使用方法:
    python unified_phase_analysis.py --mode homogeneity
    python unified_phase_analysis.py --mode correlation
    python unified_phase_analysis.py --mode both
"""

import argparse
import pandas as pd
import numpy as np
import scipy.stats as stats
from scipy.stats import shapiro, levene, ttest_ind, mannwhitneyu, pearsonr
from sklearn.covariance import EmpiricalCovariance
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

from CS_UCS import CS, UCS

# 日本語フォント設定
try:
    import matplotlib_fontja
    matplotlib_fontja.japanize()
except:
    pass

sns.set_theme(style="whitegrid")

class UnifiedPhaseAnalyzer:
    def __init__(self, data_path='final_valid_updated.csv', max_k=5):
        self.data_path = data_path
        self.max_k = max_k
        self.df = None
        self.homogeneity_results = []
        self.correlation_results = []
    
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.data_path)
        print(f"データ読み込み完了: {self.data_path} (shape={self.df.shape})")
        print(f"ユニーク参加者数: {self.df['user_id'].nunique()}")
        
        # Phase分布の確認
        print(f"\nPhase分布:")
        print(f"EX1 - First (is_first=1): {(self.df['ex1_is_first'] == 1).sum()}行")
        print(f"EX1 - Second (is_first=0): {(self.df['ex1_is_first'] == 0).sum()}行")
        print(f"EX2 - First (is_first=1): {(self.df['ex2_is_first'] == 1).sum()}行")
        print(f"EX2 - Second (is_first=0): {(self.df['ex2_is_first'] == 0).sum()}行")
    
    def prepare_data(self):
        """データの前処理"""
        self.df['condition'] = self.df['Cond'].apply(lambda x: f"Condition_{x}")
        self.df['ex1_phase'] = np.where(self.df['ex1_is_first'] == 1, 'First', 'Second')
        self.df['ex2_phase'] = np.where(self.df['ex2_is_first'] == 1, 'First', 'Second')
        
        print(f"条件: {sorted(self.df['condition'].unique())}")
        print(f"刺激番号範囲: EX1={sorted(self.df['ex1_sample_number'].unique())}, "
              f"EX2={sorted(self.df['ex2_sample_number'].unique())}")
    
    # ==================== 共通ユーティリティ ====================
    def interpret_cohens_d(self, d):
        """Cohen's dの効果量を解釈"""
        if d is None or np.isnan(d):
            return 'unknown'
        abs_d = abs(d)
        if abs_d < 0.2:
            return 'negligible'
        elif abs_d < 0.5:
            return 'small'
        elif abs_d < 0.8:
            return 'medium'
        else:
            return 'large'
    
    def fisher_z_transform(self, r):
        """Fisherのz変換"""
        if r is None or np.isnan(r) or abs(r) >= 1:
            return np.nan
        return 0.5 * np.log((1 + r) / (1 - r))
    
    def correlation_homogeneity_test(self, r1, n1, r2, n2):
        """2つの相関係数の等質性検定（Fisherのz変換を使用）"""
        if any([np.isnan(r1), np.isnan(r2)]) or n1 < 4 or n2 < 4:
            return np.nan, np.nan
        
        z1 = self.fisher_z_transform(r1)
        z2 = self.fisher_z_transform(r2)
        
        if np.isnan(z1) or np.isnan(z2):
            return np.nan, np.nan
        
        se_diff = np.sqrt(1/(n1-3) + 1/(n2-3))
        if se_diff == 0:
            return np.nan, np.nan
        
        z_stat = (z1 - z2) / se_diff
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        return z_stat, p_value
    
    def safe_corr(self, x, y):
        """安全な相関計算"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        if mask.sum() < 2:
            return np.nan
        if np.nanstd(x[mask]) == 0 or np.nanstd(y[mask]) == 0:
            return 0.0
        return pearsonr(x[mask], y[mask])[0]
    
    # ==================== Phase平均値差分析 ====================
    def perform_t_test_analysis(self, condition, stimulus_num):
        """指定された条件と刺激番号でのPhase間t検定分析"""
        condition_data = self.df[self.df['condition'] == condition].copy()
        
        results = {
            'condition': condition,
            'stimulus_number': stimulus_num,
            'n_participants': 0,
            'ex1_tests': {},
            'ex2_tests': {}
        }
        
        # EX1の分析
        ex1_stimulus_data = condition_data[condition_data['ex1_sample_number'] == stimulus_num]
        if len(ex1_stimulus_data) > 0:
            ex1_first = ex1_stimulus_data[ex1_stimulus_data['ex1_is_first'] == 1]['ex1_estimate']
            ex1_second = ex1_stimulus_data[ex1_stimulus_data['ex1_is_first'] == 0]['ex1_estimate']
            
            if len(ex1_first) > 2 and len(ex1_second) > 2:
                # 正規性検定
                try:
                    _, ex1_first_normal = shapiro(ex1_first) if len(ex1_first) >= 3 else (np.nan, np.nan)
                    _, ex1_second_normal = shapiro(ex1_second) if len(ex1_second) >= 3 else (np.nan, np.nan)
                except:
                    ex1_first_normal = ex1_second_normal = np.nan
                
                # 等分散性検定
                try:
                    _, ex1_levene_p = levene(ex1_first, ex1_second)
                except:
                    ex1_levene_p = np.nan
                
                # T検定
                equal_var = ex1_levene_p > 0.05 if not np.isnan(ex1_levene_p) else True
                t_stat, p_value = ttest_ind(ex1_first, ex1_second, equal_var=equal_var)
                
                # Cohen's d効果量
                pooled_std = np.sqrt(((len(ex1_first)-1)*ex1_first.var(ddof=1) + 
                                     (len(ex1_second)-1)*ex1_second.var(ddof=1)) / 
                                    (len(ex1_first) + len(ex1_second) - 2)) if len(ex1_first) + len(ex1_second) - 2 > 0 else np.nan
                
                cohens_d = (ex1_first.mean() - ex1_second.mean()) / pooled_std if pooled_std > 0 else np.nan
                
                results['ex1_tests'] = {
                    'first_mean': ex1_first.mean(),
                    'first_std': ex1_first.std(ddof=1),
                    'first_n': len(ex1_first),
                    'second_mean': ex1_second.mean(),
                    'second_std': ex1_second.std(ddof=1),
                    'second_n': len(ex1_second),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'effect_size': self.interpret_cohens_d(cohens_d),
                    'equal_variance': equal_var,
                    'levene_p': ex1_levene_p,
                    'first_normal_p': ex1_first_normal,
                    'second_normal_p': ex1_second_normal
                }
        
        # EX2の分析（同様の処理）
        ex2_stimulus_data = condition_data[condition_data['ex2_sample_number'] == stimulus_num]
        if len(ex2_stimulus_data) > 0:
            ex2_first = ex2_stimulus_data[ex2_stimulus_data['ex2_is_first'] == 1]['ex2_estimate']
            ex2_second = ex2_stimulus_data[ex2_stimulus_data['ex2_is_first'] == 0]['ex2_estimate']
            
            if len(ex2_first) > 2 and len(ex2_second) > 2:
                # 正規性検定
                try:
                    _, ex2_first_normal = shapiro(ex2_first) if len(ex2_first) >= 3 else (np.nan, np.nan)
                    _, ex2_second_normal = shapiro(ex2_second) if len(ex2_second) >= 3 else (np.nan, np.nan)
                except:
                    ex2_first_normal = ex2_second_normal = np.nan
                
                # 等分散性検定
                try:
                    _, ex2_levene_p = levene(ex2_first, ex2_second)
                except:
                    ex2_levene_p = np.nan
                
                # T検定
                equal_var = ex2_levene_p > 0.05 if not np.isnan(ex2_levene_p) else True
                t_stat, p_value = ttest_ind(ex2_first, ex2_second, equal_var=equal_var)
                
                # Cohen's d効果量
                pooled_std = np.sqrt(((len(ex2_first)-1)*ex2_first.var(ddof=1) + 
                                     (len(ex2_second)-1)*ex2_second.var(ddof=1)) / 
                                    (len(ex2_first) + len(ex2_second) - 2)) if len(ex2_first) + len(ex2_second) - 2 > 0 else np.nan
                
                cohens_d = (ex2_first.mean() - ex2_second.mean()) / pooled_std if pooled_std > 0 else np.nan
                
                results['ex2_tests'] = {
                    'first_mean': ex2_first.mean(),
                    'first_std': ex2_first.std(ddof=1),
                    'first_n': len(ex2_first),
                    'second_mean': ex2_second.mean(),
                    'second_std': ex2_second.std(ddof=1),
                    'second_n': len(ex2_second),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'effect_size': self.interpret_cohens_d(cohens_d),
                    'equal_variance': equal_var,
                    'levene_p': ex2_levene_p,
                    'first_normal_p': ex2_first_normal,
                    'second_normal_p': ex2_second_normal
                }
        
        # 参加者数の更新
        ex1_users = set(ex1_stimulus_data['user_id'].unique()) if len(ex1_stimulus_data) > 0 else set()
        ex2_users = set(ex2_stimulus_data['user_id'].unique()) if len(ex2_stimulus_data) > 0 else set()
        results['n_participants'] = len(ex1_users.union(ex2_users))
        
        return results
    
    def run_homogeneity_analysis(self):
        """Phase間等質性分析を実行"""
        print("\n=== Phase間等質性分析（刺激別）を開始 ===")
        
        self.load_data()
        self.prepare_data()
        
        conditions = sorted(self.df['condition'].unique())
        stimulus_numbers = sorted(self.df['ex1_sample_number'].unique())
        
        self.homogeneity_results = []
        
        for condition in conditions:
            print(f"\n条件: {condition}")
            
            for stimulus_num in stimulus_numbers:
                result = self.perform_t_test_analysis(condition, stimulus_num)
                
                # データが十分にある場合のみ結果を保存
                if (result['ex1_tests'] or result['ex2_tests']) and result['n_participants'] > 0:
                    self.homogeneity_results.append(result)
                    print(f"  刺激{stimulus_num}: 参加者{result['n_participants']}名")
        
        print(f"\n分析完了: {len(self.homogeneity_results)}件の結果")
        return self.homogeneity_results
    
    def create_homogeneity_summary(self):
        """等質性分析結果のサマリーテーブルを作成"""
        if not self.homogeneity_results:
            return pd.DataFrame()
        
        t_test_summary = []
        
        for result in self.homogeneity_results:
            condition = result['condition']
            stimulus_num = result['stimulus_number']
            
            # EX1の結果
            if 'ex1_tests' in result and result['ex1_tests']:
                ex1 = result['ex1_tests']
                t_test_summary.append({
                    'condition': condition,
                    'stimulus_number': stimulus_num,
                    'experiment': 'EX1',
                    'first_mean': ex1['first_mean'],
                    'first_std': ex1['first_std'],
                    'first_n': ex1['first_n'],
                    'second_mean': ex1['second_mean'],
                    'second_std': ex1['second_std'],
                    'second_n': ex1['second_n'],
                    't_statistic': ex1['t_statistic'],
                    'p_value': ex1['p_value'],
                    'significant': ex1['p_value'] < 0.05,
                    'cohens_d': ex1['cohens_d'],
                    'effect_size': ex1['effect_size'],
                    'equal_variance': ex1['equal_variance'],
                    'levene_p': ex1['levene_p']
                })
            
            # EX2の結果
            if 'ex2_tests' in result and result['ex2_tests']:
                ex2 = result['ex2_tests']
                t_test_summary.append({
                    'condition': condition,
                    'stimulus_number': stimulus_num,
                    'experiment': 'EX2',
                    'first_mean': ex2['first_mean'],
                    'first_std': ex2['first_std'],
                    'first_n': ex2['first_n'],
                    'second_mean': ex2['second_mean'],
                    'second_std': ex2['second_std'],
                    'second_n': ex2['second_n'],
                    't_statistic': ex2['t_statistic'],
                    'p_value': ex2['p_value'],
                    'significant': ex2['p_value'] < 0.05,
                    'cohens_d': ex2['cohens_d'],
                    'effect_size': ex2['effect_size'],
                    'equal_variance': ex2['equal_variance'],
                    'levene_p': ex2['levene_p']
                })
        
        df_t_test = pd.DataFrame(t_test_summary)
        
        if not df_t_test.empty:
            df_t_test.to_csv('unified_phase_homogeneity_t_tests.csv', index=False, encoding='utf-8-sig')
            print("保存: unified_phase_homogeneity_t_tests.csv")
        
        return df_t_test
    
    # ==================== Phase相関等質性分析 ====================
    def find_optimal_k(self, X, k_min=2, k_max=5):
        """最適なクラスタ数を決定"""
        best_k = k_min
        best_score = -np.inf
        
        for k in range(k_min, min(k_max, X.shape[0]) + 1):
            try:
                labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_k = k
                    best_score = score
            except:
                continue
        
        return best_k
    
    def create_cluster_data(self, df_subset, prefix):
        """クラスタリングデータを作成"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        
        # ピボットテーブル作成
        mat = df_subset.pivot(index="user_id", columns=num_col, values=est_col).dropna()
        if mat.empty:
            return None, 0, None
        
        # クラスタリング
        k = self.find_optimal_k(mat.values, k_max=self.max_k)
        original_labels = KMeans(n_clusters=k, random_state=0).fit_predict(mat.values)
        
        # クラスターを平均値でソート
        cluster_means = {}
        for i in range(k):
            cluster_data = mat.iloc[original_labels == i]
            available_cols = [col for col in cluster_data.columns if col in [1, 2, 3, 4, 5, 6]]
            if available_cols:
                cluster_mean = cluster_data[available_cols].mean().mean()
            else:
                cluster_mean = cluster_data.mean().mean()
            cluster_means[i] = cluster_mean
        
        sorted_clusters = sorted(cluster_means.keys(), key=lambda x: cluster_means[x], reverse=True)
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_clusters)}
        labels = np.array([label_mapping[label] for label in original_labels])
        
        mat["cluster"] = labels
        
        return mat, k, labels
    
    def metrics_from_abcd(self, a, b, c, d, cs_th, ucs_th, is_gene):
        """a,b,c,dからモデル指標を計算"""
        pe_c = a / (a + b) if (a + b) else np.nan
        pc_e = a / (a + c) if (a + c) else np.nan
        delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
        paris = a / (a + b + c) if (a + b + c) else np.nan
        dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
        cs_val = CS((a, b, c, d), cs_th, is_gene)
        ucs_val = UCS((a, b, c, d), ucs_th, is_gene)
        
        return pe_c, pc_e, delta_p, cs_val, ucs_val, paris, dfh, dice
    
    def calculate_phase_correlations(self, df_subset, prefix, cs_th=1.0, ucs_th=1.0):
        """各Phaseでの相関係数を計算"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
        
        # Phase別にデータを分割
        phase1_data = df_subset[df_subset[f"{prefix}_is_first"] == 1]
        phase2_data = df_subset[df_subset[f"{prefix}_is_first"] == 0]
        
        results = {}
        
        for phase_name, phase_data in [("Phase1", phase1_data), ("Phase2", phase2_data)]:
            if len(phase_data) == 0:
                continue
            
            # モデル指標を準備
            model_df = pd.DataFrame(
                index=sorted(phase_data[num_col].unique()),
                columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"], 
                dtype=float
            )
            
            for s in model_df.index:
                row = phase_data[phase_data[num_col] == s].iloc[0]
                a, b, c, d = row[abcd_cols].astype(int).values
                is_gene = phase_data[phase_data[num_col] == s][est_col].mean() >= 0
                model_df.loc[s] = self.metrics_from_abcd(a, b, c, d, cs_th, ucs_th, is_gene)
            
            # クラスタリング
            mat, k, labels = self.create_cluster_data(phase_data, prefix)
            if mat is None:
                continue
            
            # 各クラスターでの相関を計算
            correlations = {}
            cluster_sizes = {}
            
            for cl in range(k):
                ids = mat[mat["cluster"] == cl].index
                cl_data = phase_data[phase_data["user_id"].isin(ids)]
                if cl_data.empty:
                    continue
                
                y = cl_data.groupby(num_col)[est_col].mean().reindex(model_df.index).values
                
                cluster_correlations = {}
                for metric in ['CS', 'UCS']:
                    x = model_df[metric].values
                    corr = self.safe_corr(x, y)
                    cluster_correlations[metric] = corr
                
                correlations[f'Cluster{cl+1}'] = {
                    'correlations': cluster_correlations,
                    'n_participants': len(ids),
                    'n_samples': len(model_df.index)
                }
                cluster_sizes[cl] = len(ids)
            
            results[phase_name] = correlations
        
        return results
    
    def test_correlation_homogeneity_detailed(self, phase1_corr_results, phase2_corr_results,
                                           condition_name, experiment, threshold):
        """Phase間での相関係数の等質性検定"""
        homogeneity_results = []
        
        # 共通するクラスターを特定
        phase1_clusters = set(phase1_corr_results.keys())
        phase2_clusters = set(phase2_corr_results.keys())
        common_clusters = phase1_clusters.intersection(phase2_clusters)
        
        for cluster in common_clusters:
            phase1_data = phase1_corr_results[cluster]
            phase2_data = phase2_corr_results[cluster]
            
            for metric in ['CS', 'UCS']:
                r1 = phase1_data['correlations'][metric]
                r2 = phase2_data['correlations'][metric]
                n1 = phase1_data['n_samples']
                n2 = phase2_data['n_samples']
                
                z_stat, p_val = self.correlation_homogeneity_test(r1, n1, r2, n2)
                
                result = {
                    'condition': condition_name,
                    'experiment': experiment,
                    'threshold': threshold,
                    'cluster': cluster,
                    'metric': metric,
                    'phase1_correlation': r1,
                    'phase2_correlation': r2,
                    'phase1_n_participants': phase1_data['n_participants'],
                    'phase2_n_participants': phase2_data['n_participants'],
                    'phase1_n_samples': n1,
                    'phase2_n_samples': n2,
                    'phase1_fisher_z': self.fisher_z_transform(r1),
                    'phase2_fisher_z': self.fisher_z_transform(r2),
                    'z_statistic': z_stat,
                    'p_value': p_val,
                    'significant': (p_val < 0.05) if not np.isnan(p_val) else False,
                    'correlation_difference': (abs(r1 - r2) if not (np.isnan(r1) or np.isnan(r2)) else np.nan)
                }
                
                homogeneity_results.append(result)
        
        return homogeneity_results
    
    def run_correlation_analysis(self, thresholds=[1.0, 0.7, 0.5, 0.2, 0.1]):
        """CS/UCS相関のPhase間等質性検定を実行"""
        print("\n=== CS・UCS相関係数のPhase間等質性検定を開始 ===")
        
        if self.df is None:
            self.load_data()
            self.prepare_data()
        
        # 条件定義
        conditions = [
            ("非対称否定_サマリー", "ex1", 0),
            ("対称否定_サマリー", "ex1", 1),
            ("非対称否定_オンライン", "ex2", 0),
            ("対称否定_オンライン", "ex2", 1),
        ]
        
        all_correlation_results = []
        
        for condition_name, experiment, cond_value in conditions:
            print(f"\n条件: {condition_name}")
            
            base_data = self.df[self.df["Cond"] == cond_value].copy()
            
            print(f"総データ数: {len(base_data)}行")
            print(f"Phase1 (is_first=1): {len(base_data[base_data[f'{experiment}_is_first'] == 1])}行")
            print(f"Phase2 (is_first=0): {len(base_data[base_data[f'{experiment}_is_first'] == 0])}行")
            
            if len(base_data) == 0:
                print("データが不足しているためスキップします")
                continue
            
            # 各thresholdで分析
            for th in thresholds:
                print(f"  Threshold {th}:")
                
                # Phase別相関係数を計算
                phase_correlations = self.calculate_phase_correlations(base_data, experiment, th, th)
                
                if 'Phase1' not in phase_correlations or 'Phase2' not in phase_correlations:
                    print(f"    データが不足しているためthreshold {th}をスキップします")
                    continue
                
                # 等質性検定
                homogeneity_results = self.test_correlation_homogeneity_detailed(
                    phase_correlations['Phase1'], 
                    phase_correlations['Phase2'],
                    condition_name, experiment, th
                )
                
                # 結果を表示
                for result in homogeneity_results:
                    cluster = result['cluster']
                    metric = result['metric']
                    r1 = result['phase1_correlation']
                    r2 = result['phase2_correlation']
                    p_val = result['p_value']
                    print(f"    {cluster} {metric}: r1={r1:.3f}, r2={r2:.3f}, p={p_val:.4f}" +
                          (" *" if result['significant'] else ""))
                
                all_correlation_results.extend(homogeneity_results)
        
        self.correlation_results = all_correlation_results
        return all_correlation_results
    
    def create_correlation_summary(self):
        """相関等質性分析結果のサマリーを作成"""
        if not self.correlation_results:
            return pd.DataFrame()
        
        correlation_df = pd.DataFrame(self.correlation_results)
        
        if not correlation_df.empty:
            correlation_df.to_csv("unified_correlation_homogeneity_results.csv", index=False, encoding="utf-8-sig")
            print("保存: unified_correlation_homogeneity_results.csv")
        
        return correlation_df
    
    # ==================== 可視化 ====================
    def create_homogeneity_visualizations(self, df_summary):
        """等質性分析の可視化"""
        if df_summary.empty:
            print('等質性可視化スキップ (データなし)')
            return
        
        # p値ヒートマップ EX1 / EX2
        for exp in ['EX1', 'EX2']:
            exp_data = df_summary[df_summary['experiment'] == exp]
            if exp_data.empty:
                continue
            
            pivot = exp_data.pivot(index='condition', columns='stimulus_number', values='p_value')
            if pivot.empty:
                continue
            
            plt.figure(figsize=(12, 6))
            sns.heatmap(pivot, annot=True, cmap='RdYlBu_r', vmin=0, vmax=1, center=0.05, 
                       fmt='.3f', cbar_kws={'label': 'p-value'})
            plt.title(f'{exp}: Phase差 p値 (刺激別)')
            plt.tight_layout()
            
            filename = f'unified_phase_homogeneity_{exp.lower()}_pvalues.png'
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            print(f'保存: {filename}')
        
        # 効果量ヒートマップ
        for exp in ['EX1', 'EX2']:
            exp_data = df_summary[df_summary['experiment'] == exp]
            if exp_data.empty:
                continue
            
            pivot = exp_data.pivot(index='condition', columns='stimulus_number', values='cohens_d')
            if pivot.empty:
                continue
            
            plt.figure(figsize=(12, 6))
            sns.heatmap(pivot, annot=True, cmap='RdBu_r', center=0, fmt='.2f', 
                       cbar_kws={'label': "Cohen's d"})
            plt.title(f'{exp}: Phase差 効果量 Cohen d (刺激別)')
            plt.tight_layout()
            
            filename = f'unified_phase_homogeneity_{exp.lower()}_effect_size.png'
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            print(f'保存: {filename}')
    
    def create_correlation_visualizations(self, correlation_df):
        """相関等質性分析の可視化"""
        if correlation_df.empty:
            print('相関可視化スキップ (データなし)')
            return
        
        # 相関係数等質性のヒートマップ
        plt.figure(figsize=(16, 11))
        
        # CS p-value
        plt.subplot(2, 3, 1)
        cs_data = correlation_df[correlation_df['metric'] == 'CS']
        if not cs_data.empty:
            pivot = cs_data.pivot_table(index=['condition', 'cluster'], columns='threshold', 
                                      values='p_value', aggfunc='mean')
            sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlBu_r', vmin=0, vmax=0.1, 
                       cbar_kws={'label': 'p'})
            plt.title('CS 相関 等質性 p値')
        
        # UCS p-value
        plt.subplot(2, 3, 2)
        ucs_data = correlation_df[correlation_df['metric'] == 'UCS']
        if not ucs_data.empty:
            pivot = ucs_data.pivot_table(index=['condition', 'cluster'], columns='threshold', 
                                       values='p_value', aggfunc='mean')
            sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlBu_r', vmin=0, vmax=0.1, 
                       cbar_kws={'label': 'p'})
            plt.title('UCS 相関 等質性 p値')
        
        # 相関差ヒートマップ
        plt.subplot(2, 3, 3)
        if not cs_data.empty:
            pivot = cs_data.pivot_table(index=['condition', 'cluster'], columns='threshold', 
                                      values='correlation_difference', aggfunc='mean')
            sns.heatmap(pivot, annot=True, fmt='.3f', cmap='Reds', cbar_kws={'label': '|Δr|'})
            plt.title('CS Phase間 相関差')
        
        plt.subplot(2, 3, 4)
        if not ucs_data.empty:
            pivot = ucs_data.pivot_table(index=['condition', 'cluster'], columns='threshold', 
                                       values='correlation_difference', aggfunc='mean')
            sns.heatmap(pivot, annot=True, fmt='.3f', cmap='Reds', cbar_kws={'label': '|Δr|'})
            plt.title('UCS Phase間 相関差')
        
        # 有意差の分布
        plt.subplot(2, 3, 5)
        sig_counts = correlation_df.groupby(['condition', 'metric'])['significant'].sum().unstack(fill_value=0)
        if not sig_counts.empty:
            sig_counts.plot(kind='bar', ax=plt.gca())
            plt.title('条件別 有意差数')
            plt.ylabel('count')
            plt.xticks(rotation=45)
        
        # 相関係数の散布図
        plt.subplot(2, 3, 6)
        colors = correlation_df['significant'].map({True: 'red', False: 'blue'})
        plt.scatter(correlation_df['phase1_correlation'], 
                   correlation_df['phase2_correlation'], 
                   c=colors, alpha=0.6)
        
        # 対角線
        corr_min = min(correlation_df[['phase1_correlation', 'phase2_correlation']].min())
        corr_max = max(correlation_df[['phase1_correlation', 'phase2_correlation']].max())
        plt.plot([corr_min, corr_max], [corr_min, corr_max], 'k--', alpha=0.5)
        
        plt.xlabel('Phase1 r')
        plt.ylabel('Phase2 r')
        plt.title('相関比較 (赤=有意差)')
        
        plt.tight_layout()
        plt.savefig('unified_correlation_homogeneity_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        print('保存: unified_correlation_homogeneity_analysis.png')
    
    # ==================== レポート生成 ====================
    def generate_homogeneity_report(self, df_summary):
        """等質性分析レポート生成"""
        if df_summary.empty:
            return
        
        significant_tests = df_summary[df_summary['significant'] == True]
        
        with open('unified_phase_homogeneity_report.txt', 'w', encoding='utf-8') as f:
            f.write('統合Phase間等質性レポート (刺激別)\n')
            f.write('=' * 60 + '\n\n')
            
            # 全体サマリー
            f.write('1. 分析概要\n')
            f.write('-' * 30 + '\n')
            f.write(f'総検定数: {len(df_summary)}\n')
            f.write(f'有意差あり: {len(significant_tests)} ({len(significant_tests)/len(df_summary):.1%})\n\n')
            
            # 有意差一覧
            f.write('2. 有意差のある検定\n')
            f.write('-' * 30 + '\n')
            for _, row in significant_tests.iterrows():
                f.write(f"{row['condition']} 刺激{row['stimulus_number']} {row['experiment']}: "
                       f"p={row['p_value']:.4f} d={row['cohens_d']:.2f} {row['effect_size']}\n")
            
            # 条件別サマリー
            f.write(f'\n3. 条件別サマリー\n')
            f.write('-' * 30 + '\n')
            for condition in sorted(df_summary['condition'].unique()):
                cond_data = df_summary[df_summary['condition'] == condition]
                cond_significant = cond_data[cond_data['significant'] == True]
                f.write(f'{condition}:\n')
                f.write(f'  総検定数: {len(cond_data)}件\n')
                f.write(f'  有意差あり: {len(cond_significant)}件\n\n')
        
        print('保存: unified_phase_homogeneity_report.txt')
    
    def generate_correlation_report(self, correlation_df):
        """相関等質性分析レポート生成"""
        if correlation_df.empty:
            return
        
        significant_tests = correlation_df[correlation_df['significant'] == True]
        
        with open('unified_correlation_homogeneity_report.txt', 'w', encoding='utf-8') as f:
            f.write('統合CS・UCS相関係数Phase間等質性レポート\n')
            f.write('=' * 60 + '\n\n')
            
            # 全体サマリー
            f.write('1. 分析概要\n')
            f.write('-' * 30 + '\n')
            f.write(f'総検定数: {len(correlation_df)}\n')
            f.write(f'有意差あり: {len(significant_tests)} ({len(significant_tests)/len(correlation_df):.1%})\n\n')
            
            # 条件別要約
            f.write('2. 条件別要約\n')
            f.write('-' * 30 + '\n')
            for condition in correlation_df['condition'].unique():
                cond_data = correlation_df[correlation_df['condition'] == condition]
                cond_significant = cond_data[cond_data['significant'] == True]
                f.write(f'{condition}:\n')
                f.write(f'  総検定数: {len(cond_data)}件\n')
                f.write(f'  有意差あり: {len(cond_significant)}件 ({len(cond_significant)/len(cond_data)*100:.1f}%)\n\n')
            
            # CS vs UCS比較
            f.write('3. CS vs UCS比較\n')
            f.write('-' * 30 + '\n')
            cs_data = correlation_df[correlation_df['metric'] == 'CS']
            ucs_data = correlation_df[correlation_df['metric'] == 'UCS']
            
            cs_sig = len(cs_data[cs_data['significant'] == True])
            ucs_sig = len(ucs_data[ucs_data['significant'] == True])
            
            f.write(f'CS有意差: {cs_sig}/{len(cs_data)} ({cs_sig/len(cs_data)*100:.1f}%)\n')
            f.write(f'UCS有意差: {ucs_sig}/{len(ucs_data)} ({ucs_sig/len(ucs_data)*100:.1f}%)\n')
        
        print('保存: unified_correlation_homogeneity_report.txt')

def main():
    parser = argparse.ArgumentParser(description="統合Phase分析")
    parser.add_argument("--mode", choices=["homogeneity", "correlation", "both"], 
                       default="both", help="分析モード選択")
    parser.add_argument("--data", default="final_valid_updated.csv", 
                       help="データファイルパス")
    parser.add_argument("--max-k", type=int, default=5, 
                       help="最大クラスタ数（相関分析用）")
    
    args = parser.parse_args()
    
    print("=== 統合Phase分析 ===")
    print(f"データ: {args.data}")
    print(f"モード: {args.mode}")
    print("=" * 50)
    
    analyzer = UnifiedPhaseAnalyzer(data_path=args.data, max_k=args.max_k)
    
    homogeneity_df = None
    correlation_df = None
    
    if args.mode in ["homogeneity", "both"]:
        print("\n--- Phase間等質性分析 ---")
        analyzer.run_homogeneity_analysis()
        homogeneity_df = analyzer.create_homogeneity_summary()
        analyzer.create_homogeneity_visualizations(homogeneity_df)
        analyzer.generate_homogeneity_report(homogeneity_df)
    
    if args.mode in ["correlation", "both"]:
        print("\n--- Phase間相関等質性分析 ---")
        thresholds = [1.0, 0.7, 0.5, 0.2, 0.1]
        analyzer.run_correlation_analysis(thresholds)
        correlation_df = analyzer.create_correlation_summary()
        analyzer.create_correlation_visualizations(correlation_df)
        analyzer.generate_correlation_report(correlation_df)
    
    print("\n=== 分析完了 ===")

if __name__ == "__main__":
    main()
