# -*- coding: utf-8 -*-
"""
phase_correlation_homogeneity_analysis.py

is_first=1とis_first=0の両方の場合で相関分析を行い、
CS、UCSの値の等質性検定を行うコード
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr, levene, bartlett, ttest_ind, wilcoxon, mannwhitneyu
from scipy.stats import shapiro, normaltest, fisher_exact
import warnings
from CS_UCS import CS, UCS

warnings.filterwarnings('ignore')

# 日本語フォント設定（必要に応じて）
try:
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
except:
    pass

def fisher_z_transform(r):
    """Fisherのz変換"""
    if abs(r) >= 1:
        return np.nan
    return 0.5 * np.log((1 + r) / (1 - r))


def correlation_homogeneity_test(r1, n1, r2, n2):
    """
    2つの相関係数の等質性検定（Fisherのz変換を使用）
    
    Parameters:
    -----------
    r1, r2 : float
        比較する相関係数
    n1, n2 : int
        各相関係数のサンプルサイズ
        
    Returns:
    --------
    z_stat : float
        z統計量
    p_value : float
        p値
    """
    if np.isnan(r1) or np.isnan(r2) or n1 < 3 or n2 < 3:
        return np.nan, np.nan
    
    # Fisherのz変換
    z1 = fisher_z_transform(r1)
    z2 = fisher_z_transform(r2)
    
    if np.isnan(z1) or np.isnan(z2):
        return np.nan, np.nan
    
    # 標準誤差
    se_diff = np.sqrt(1/(n1-3) + 1/(n2-3))
    
    # z統計量
    z_stat = (z1 - z2) / se_diff
    
    # p値（両側検定）
    from scipy.stats import norm
    p_value = 2 * (1 - norm.cdf(abs(z_stat)))
    
    return z_stat, p_value

class PhaseCorrelationHomogeneityAnalyzer:
    def __init__(self, csv_path: str, max_k: int = 5):
        """
        初期化
        
        Parameters:
        -----------
        csv_path : str
            データファイルのパス
        max_k : int
            クラスタリングの最大クラスタ数
        """
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame = None
        self.results = {}
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        print(f"ユニーク参加者数: {self.df['user_id'].nunique()}")
        
        # Phase分布の確認
        print(f"\nPhase分布:")
        print(f"EX1 - First (is_first=1): {(self.df['ex1_is_first'] == 1).sum()}行")
        print(f"EX1 - Second (is_first=0): {(self.df['ex1_is_first'] == 0).sum()}行")
        print(f"EX2 - First (is_first=1): {(self.df['ex2_is_first'] == 1).sum()}行")
        print(f"EX2 - Second (is_first=0): {(self.df['ex2_is_first'] == 0).sum()}行")
        
    def safe_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        """安全な相関計算"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        if mask.sum() < 2:
            return np.nan
        if np.nanstd(x[mask]) == 0 or np.nanstd(y[mask]) == 0:
            return 0.0
        return pearsonr(x[mask], y[mask])[0]
        
    def find_optimal_k(self, X: np.ndarray, k_min: int = 2, k_max: int = 5) -> int:
        """最適なクラスタ数を決定"""
        best_k, best_score = k_min, -np.inf
        for k in range(k_min, min(k_max, X.shape[0]) + 1):
            labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
            score = silhouette_score(X, labels)
            if score > best_score:
                best_k, best_score = k, score
        return best_k
        
    def metrics_from_abcd(self, a: int, b: int, c: int, d: int, 
                         cs_th: float = 1.0, ucs_th: float = 1.0, is_gene: bool = True):
        """a,b,c,d からモデル指標を計算"""
        pe_c = a / (a + b) if (a + b) else np.nan
        pc_e = a / (a + c) if (a + c) else np.nan
        delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
        paris = a / (a + b + c) if (a + b + c) else np.nan
        dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
        cs_val = CS((a, b, c, d), cs_th, is_gene)
        ucs_val = UCS((a, b, c, d), ucs_th, is_gene)
        return pe_c, pc_e, delta_p, cs_val, ucs_val, paris, dfh, dice
        
    def create_cluster_data(self, df_subset: pd.DataFrame, prefix: str):
        """クラスタリングデータを作成"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        
        # ピボットテーブル作成
        mat = df_subset.pivot(index="user_id", columns=num_col, values=est_col).dropna()
        if mat.empty:
            return None, None, None
            
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
        
    def calculate_correlations(self, df_subset: pd.DataFrame, mat: pd.DataFrame, k: int, 
                             prefix: str, cs_th: float, ucs_th: float):
        """相関を計算"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
        
        # モデル指標を準備
        model_df = pd.DataFrame(index=sorted(df_subset[num_col].unique()),
                               columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"], 
                               dtype=float)
        
        for s in model_df.index:
            row = df_subset[df_subset[num_col] == s].iloc[0]
            a, b, c, d = row[abcd_cols].astype(int).values
            is_gene = df_subset[df_subset[num_col] == s][est_col].mean() >= 0
            model_df.loc[s] = self.metrics_from_abcd(a, b, c, d, cs_th=cs_th, ucs_th=ucs_th, is_gene=is_gene)
        
        # グループ定義
        groups = {"All": df_subset}
        for cl in range(k):
            ids = mat[mat["cluster"] == cl].index
            groups[f"Cluster{cl+1}"] = df_subset[df_subset["user_id"].isin(ids)]
        
        # 相関テーブル初期化
        corr_table = pd.DataFrame(index=groups.keys(),
                                 columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"])
        
        # CRT平均テーブル初期化
        crt_table = pd.DataFrame(index=groups.keys(), columns=["CRT_mean", "estimate_mean"])
        
        # 相関計算
        for g_name, g_df in groups.items():
            # 推定値の平均
            y = g_df.groupby(num_col)[est_col].mean().reindex(model_df.index).values
            
            # CRT平均スコア計算
            if len(g_df) > 0 and "crt_correct_cnt" in g_df.columns:
                crt_mean = g_df["crt_correct_cnt"].mean()
                crt_table.loc[g_name, "CRT_mean"] = round(crt_mean, 3) if pd.notna(crt_mean) else np.nan
            else:
                crt_table.loc[g_name, "CRT_mean"] = np.nan
            
            # 評定値の平均
            if len(g_df) > 0:
                estimate_mean = g_df[est_col].mean()
                crt_table.loc[g_name, "estimate_mean"] = round(estimate_mean, 3) if pd.notna(estimate_mean) else np.nan
            else:
                crt_table.loc[g_name, "estimate_mean"] = np.nan
            
            # 各指標との相関
            for metric in corr_table.columns:
                x = model_df[metric].values
                r = self.safe_corr(x, y)
                corr_table.loc[g_name, metric] = (np.nan if np.isnan(r) else round(r, 3))
        
        return corr_table, crt_table, model_df
        
    def get_cluster_sizes(self, mat: pd.DataFrame, k: int):
        """クラスターサイズを取得"""
        cluster_sizes = {}
        for i in range(k):
            cluster_sizes[i] = len(mat[mat["cluster"] == i])
        return cluster_sizes
        
    def analyze_case(self, label: str, df_subset: pd.DataFrame, prefix: str, 
                    cs_th: float, ucs_th: float):
        """個別ケースの分析"""
        if df_subset.empty:
            return None, None, None, None
            
        mat, k, labels = self.create_cluster_data(df_subset, prefix)
        if mat is None:
            return None, None, None, None
        corr_table, crt_table, model_df = self.calculate_correlations(df_subset, mat, k, prefix, cs_th, ucs_th)
        cluster_sizes = self.get_cluster_sizes(mat, k)
        
        return corr_table, crt_table, cluster_sizes, model_df
        
    def calculate_cs_ucs_values(self, df_subset: pd.DataFrame, prefix: str, 
                               thresholds: list = [1.0, 0.7, 0.5, 0.2, 0.1]):
        """CS、UCSの値を複数のthresholdで計算"""
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        
        results = []
        
        # 各sample_numberについて計算
        for sample_num in sorted(df_subset[num_col].unique()):
            sample_data = df_subset[df_subset[num_col] == sample_num]
            if len(sample_data) == 0:
                continue
                
            # a,b,c,d値を取得
            row = sample_data.iloc[0]
            a, b, c, d = row[abcd_cols].astype(int).values
            
            # 推定値の平均が正かどうかでis_geneを決定
            is_gene = sample_data[est_col].mean() >= 0
            
            # 各thresholdでCS、UCSを計算
            sample_result = {
                'sample_number': sample_num,
                'a': a, 'b': b, 'c': c, 'd': d,
                'is_gene': is_gene,
                'n_responses': len(sample_data),
                'mean_estimate': sample_data[est_col].mean()
            }
            
            for th in thresholds:
                cs_val = CS((a, b, c, d), th, is_gene)
                ucs_val = UCS((a, b, c, d), th, is_gene)
                sample_result[f'CS_{th}'] = cs_val
                sample_result[f'UCS_{th}'] = ucs_val
                
            results.append(sample_result)
            
        return pd.DataFrame(results)
        
    def test_cs_ucs_homogeneity(self, phase1_values: pd.DataFrame, phase2_values: pd.DataFrame,
                               thresholds: list = [1.0, 0.7, 0.5, 0.2, 0.1]):
        """Phase間でのCS、UCS値の等質性検定"""
        results = {}
        
        for th in thresholds:
            cs_col = f'CS_{th}'
            ucs_col = f'UCS_{th}'
            
            # 共通のsample_numberのみを対象とする
            common_samples = set(phase1_values['sample_number']).intersection(
                set(phase2_values['sample_number']))
            
            if len(common_samples) < 2:
                continue
                
            # データの準備
            phase1_cs = phase1_values[phase1_values['sample_number'].isin(common_samples)][cs_col].values
            phase2_cs = phase2_values[phase2_values['sample_number'].isin(common_samples)][cs_col].values
            phase1_ucs = phase1_values[phase1_values['sample_number'].isin(common_samples)][ucs_col].values
            phase2_ucs = phase2_values[phase2_values['sample_number'].isin(common_samples)][ucs_col].values
            
            # 正規性検定
            _, cs_phase1_normal = shapiro(phase1_cs) if len(phase1_cs) >= 3 else (np.nan, np.nan)
            _, cs_phase2_normal = shapiro(phase2_cs) if len(phase2_cs) >= 3 else (np.nan, np.nan)
            _, ucs_phase1_normal = shapiro(phase1_ucs) if len(phase1_ucs) >= 3 else (np.nan, np.nan)
            _, ucs_phase2_normal = shapiro(phase2_ucs) if len(phase2_ucs) >= 3 else (np.nan, np.nan)
            
            # 等分散性検定
            _, cs_levene_p = levene(phase1_cs, phase2_cs) if len(phase1_cs) > 1 and len(phase2_cs) > 1 else (np.nan, np.nan)
            _, ucs_levene_p = levene(phase1_ucs, phase2_ucs) if len(phase1_ucs) > 1 and len(phase2_ucs) > 1 else (np.nan, np.nan)
            
            # t検定（CS）
            cs_equal_var = cs_levene_p > 0.05 if not np.isnan(cs_levene_p) else True
            cs_t_stat, cs_t_pval = ttest_ind(phase1_cs, phase2_cs, equal_var=cs_equal_var)
            
            # t検定（UCS）
            ucs_equal_var = ucs_levene_p > 0.05 if not np.isnan(ucs_levene_p) else True
            ucs_t_stat, ucs_t_pval = ttest_ind(phase1_ucs, phase2_ucs, equal_var=ucs_equal_var)
            
            # Mann-Whitney U検定（ノンパラメトリック）
            cs_u_stat, cs_u_pval = mannwhitneyu(phase1_cs, phase2_cs, alternative='two-sided')
            ucs_u_stat, ucs_u_pval = mannwhitneyu(phase1_ucs, phase2_ucs, alternative='two-sided')
            
            # 効果量（Cohen's d）
            cs_pooled_std = np.sqrt(((len(phase1_cs)-1)*np.var(phase1_cs, ddof=1) + 
                                   (len(phase2_cs)-1)*np.var(phase2_cs, ddof=1)) / 
                                  (len(phase1_cs) + len(phase2_cs) - 2))
            cs_cohens_d = (np.mean(phase1_cs) - np.mean(phase2_cs)) / cs_pooled_std if cs_pooled_std > 0 else np.nan
            
            ucs_pooled_std = np.sqrt(((len(phase1_ucs)-1)*np.var(phase1_ucs, ddof=1) + 
                                    (len(phase2_ucs)-1)*np.var(phase2_ucs, ddof=1)) / 
                                   (len(phase1_ucs) + len(phase2_ucs) - 2))
            ucs_cohens_d = (np.mean(phase1_ucs) - np.mean(phase2_ucs)) / ucs_pooled_std if ucs_pooled_std > 0 else np.nan
            
            results[f'threshold_{th}'] = {
                'common_samples': len(common_samples),
                'CS': {
                    'phase1_mean': np.mean(phase1_cs),
                    'phase1_std': np.std(phase1_cs, ddof=1),
                    'phase2_mean': np.mean(phase2_cs),
                    'phase2_std': np.std(phase2_cs, ddof=1),
                    'phase1_normal_p': cs_phase1_normal,
                    'phase2_normal_p': cs_phase2_normal,
                    'levene_p': cs_levene_p,
                    't_statistic': cs_t_stat,
                    't_pvalue': cs_t_pval,
                    'mann_whitney_u': cs_u_stat,
                    'mann_whitney_p': cs_u_pval,
                    'cohens_d': cs_cohens_d,
                    'effect_size': self._interpret_cohens_d(cs_cohens_d)
                },
                'UCS': {
                    'phase1_mean': np.mean(phase1_ucs),
                    'phase1_std': np.std(phase1_ucs, ddof=1),
                    'phase2_mean': np.mean(phase2_ucs),
                    'phase2_std': np.std(phase2_ucs, ddof=1),
                    'phase1_normal_p': ucs_phase1_normal,
                    'phase2_normal_p': ucs_phase2_normal,
                    'levene_p': ucs_levene_p,
                    't_statistic': ucs_t_stat,
                    't_pvalue': ucs_t_pval,
                    'mann_whitney_u': ucs_u_stat,
                    'mann_whitney_p': ucs_u_pval,
                    'cohens_d': ucs_cohens_d,
                    'effect_size': self._interpret_cohens_d(ucs_cohens_d)
                }
            }
            
        return results
        
    def _interpret_cohens_d(self, d):
        """Cohen's dの効果量を解釈"""
        if np.isnan(d):
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

    def calculate_phase_correlations(self, df_subset: pd.DataFrame, prefix: str, 
                                   cs_th: float = 1.0, ucs_th: float = 1.0):
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
            model_df = pd.DataFrame(index=sorted(phase_data[num_col].unique()),
                                   columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"], 
                                   dtype=float)
            
            for s in model_df.index:
                sample_data = phase_data[phase_data[num_col] == s]
                if len(sample_data) == 0:
                    continue
                row = sample_data.iloc[0]
                a, b, c, d = row[abcd_cols].astype(int).values
                is_gene = sample_data[est_col].mean() >= 0
                model_df.loc[s] = self.metrics_from_abcd(a, b, c, d, cs_th=cs_th, ucs_th=ucs_th, is_gene=is_gene)
            
            # クラスタリング
            mat, k, labels = self.create_cluster_data(phase_data, prefix)
            if mat is None:
                continue
                
            # 各クラスターでの相関を計算
            correlations = {}
            cluster_sizes = {}
            
            for cl in range(k):
                cluster_ids = mat[mat["cluster"] == cl].index
                cluster_data = phase_data[phase_data["user_id"].isin(cluster_ids)]
                cluster_sizes[cl] = len(cluster_data)
                
                if len(cluster_data) == 0:
                    continue
                    
                # 推定値の平均
                y = cluster_data.groupby(num_col)[est_col].mean().reindex(model_df.index).values
                
                # 各指標との相関
                cluster_corrs = {}
                for metric in ["CS", "UCS"]:
                    x = model_df[metric].values
                    r = self.safe_corr(x, y)
                    cluster_corrs[metric] = r
                    
                correlations[f"Cluster{cl+1}"] = {
                    'correlations': cluster_corrs,
                    'n_participants': len(cluster_data),
                    'n_samples': len([s for s in model_df.index if not np.isnan(model_df.loc[s, 'CS'])])
                }
            
            results[phase_name] = correlations
            
        return results

    def test_correlation_homogeneity(self, phase1_corr_results: dict, phase2_corr_results: dict,
                                   condition_name: str, experiment: str, threshold: float):
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
                
                # 相関係数の等質性検定
                z_stat, p_value = correlation_homogeneity_test(r1, n1, r2, n2)
                
                # Fisherのz変換値
                z1 = fisher_z_transform(r1) if not np.isnan(r1) else np.nan
                z2 = fisher_z_transform(r2) if not np.isnan(r2) else np.nan
                
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
                    'phase1_fisher_z': z1,
                    'phase2_fisher_z': z2,
                    'z_statistic': z_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05 if not np.isnan(p_value) else False,
                    'correlation_difference': abs(r1 - r2) if not (np.isnan(r1) or np.isnan(r2)) else np.nan
                }
                
                homogeneity_results.append(result)
                
        return homogeneity_results

    def run_correlation_homogeneity_analysis(self, thresholds=[1.0, 0.7, 0.5, 0.2, 0.1]):
        """4条件下でのCS、UCSの相関係数のPhase間等質性検定を実行"""
        self.load_data()
        
        # 条件定義
        conditions = [
            ("非対称否定_サマリー", "ex1", 0),
            ("対称否定_サマリー", "ex1", 1),
            ("非対称否定_オンライン", "ex2", 0),
            ("対称否定_オンライン", "ex2", 1),
        ]
        
        all_homogeneity_results = []
        
        print("CS・UCS相関係数のPhase間等質性検定を開始...")
        print("=" * 80)
        
        for condition_name, experiment, cond_value in conditions:
            print(f"\n条件: {condition_name}")
            print("=" * 60)
            
            # データの準備
            base_data = self.df[self.df["Cond"] == cond_value].copy()
            
            print(f"総データ数: {len(base_data)}行")
            print(f"Phase1 (is_first=1): {len(base_data[base_data[f'{experiment}_is_first'] == 1])}行")
            print(f"Phase2 (is_first=0): {len(base_data[base_data[f'{experiment}_is_first'] == 0])}行")
            
            if len(base_data) == 0:
                print("データが不足しているためスキップします")
                continue
            
            # 各thresholdで分析
            for th in thresholds:
                print(f"\n  Threshold {th}:")
                
                # Phase別相関係数を計算
                phase_correlations = self.calculate_phase_correlations(base_data, experiment, th, th)
                
                if 'Phase1' not in phase_correlations or 'Phase2' not in phase_correlations:
                    print(f"    データが不足しているためthreshold {th}をスキップします")
                    continue
                
                # 等質性検定
                homogeneity_results = self.test_correlation_homogeneity(
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
                
                all_homogeneity_results.extend(homogeneity_results)
        
        # 結果をDataFrameに変換
        homogeneity_df = pd.DataFrame(all_homogeneity_results)
        
        # CSVファイルに保存
        homogeneity_df.to_csv("correlation_homogeneity_results.csv", index=False, encoding="utf-8-sig")
        
        print(f"\n結果を保存:")
        print(f"- correlation_homogeneity_results.csv ({len(homogeneity_df)}行)")
        
        # 結果の要約
        self.summarize_correlation_homogeneity_results(homogeneity_df)
        
        return homogeneity_df

    def summarize_correlation_homogeneity_results(self, homogeneity_df: pd.DataFrame):
        """相関係数等質性検定結果を要約"""
        print(f"\n" + "="*80)
        print("CS・UCS相関係数のPhase間等質性検定結果要約")
        print("="*80)
        
        # 全体サマリー
        print(f"\n1. 全体サマリー:")
        print(f"   - 総検定数: {len(homogeneity_df)}件")
        print(f"   - 条件数: {homogeneity_df['condition'].nunique()}")
        print(f"   - Threshold数: {homogeneity_df['threshold'].nunique()}")
        print(f"   - クラスター数: {homogeneity_df['cluster'].nunique()}")
        
        # 有意差のある検定の割合
        significant_tests = homogeneity_df[homogeneity_df['significant'] == True]
        total_tests = len(homogeneity_df)
        significant_rate = len(significant_tests) / total_tests if total_tests > 0 else 0
        
        print(f"   - 有意差あり: {len(significant_tests)}/{total_tests} ({significant_rate*100:.1f}%)")
        
        # 条件別要約
        print(f"\n2. 条件別要約:")
        for condition in homogeneity_df['condition'].unique():
            cond_data = homogeneity_df[homogeneity_df['condition'] == condition]
            cond_significant = cond_data[cond_data['significant'] == True]
            print(f"   {condition}:")
            print(f"     - 総検定数: {len(cond_data)}件")
            print(f"     - 有意差あり: {len(cond_significant)}件 ({len(cond_significant)/len(cond_data)*100:.1f}%)")
        
        # CS vs UCS比較
        print(f"\n3. CS vs UCS比較:")
        cs_data = homogeneity_df[homogeneity_df['metric'] == 'CS']
        ucs_data = homogeneity_df[homogeneity_df['metric'] == 'UCS']
        
        cs_sig = len(cs_data[cs_data['significant'] == True])
        ucs_sig = len(ucs_data[ucs_data['significant'] == True])
        
        print(f"   CS有意差: {cs_sig}/{len(cs_data)} ({cs_sig/len(cs_data)*100:.1f}%)")
        print(f"   UCS有意差: {ucs_sig}/{len(ucs_data)} ({ucs_sig/len(ucs_data)*100:.1f}%)")
        
        # Threshold別要約
        print(f"\n4. Threshold別要約:")
        for th in sorted(homogeneity_df['threshold'].unique()):
            th_data = homogeneity_df[homogeneity_df['threshold'] == th]
            th_sig = len(th_data[th_data['significant'] == True])
            print(f"   Threshold {th}: {th_sig}/{len(th_data)} ({th_sig/len(th_data)*100:.1f}%)")
        
        # 最も差の大きい相関係数ペア
        print(f"\n5. 相関係数差の大きいケース（上位5件）:")
        top_differences = homogeneity_df.nlargest(5, 'correlation_difference')
        for _, row in top_differences.iterrows():
            print(f"   {row['condition']} {row['cluster']} {row['metric']} (th={row['threshold']}):")
            print(f"     Phase1: {row['phase1_correlation']:.3f}, Phase2: {row['phase2_correlation']:.3f}")
            print(f"     差: {row['correlation_difference']:.3f}, p値: {row['p_value']:.4f}")

    def create_correlation_homogeneity_visualizations(self, homogeneity_df: pd.DataFrame):
        """相関係数等質性検定結果の可視化"""
        # p値のヒートマップ
        plt.figure(figsize=(16, 12))
        
        # CS結果のヒートマップ
        plt.subplot(2, 3, 1)
        cs_data = homogeneity_df[homogeneity_df['metric'] == 'CS']
        if len(cs_data) > 0:
            cs_pivot = cs_data.pivot_table(
                index=['condition', 'cluster'], 
                columns='threshold', 
                values='p_value', 
                aggfunc='mean'
            )
            sns.heatmap(cs_pivot, annot=True, fmt='.3f', cmap='RdYlBu_r', 
                       cbar_kws={'label': 'p-value'}, vmin=0, vmax=0.1)
            plt.title('CS相関係数等質性検定 p値')
            plt.ylabel('条件・クラスター')
        
        # UCS結果のヒートマップ
        plt.subplot(2, 3, 2)
        ucs_data = homogeneity_df[homogeneity_df['metric'] == 'UCS']
        if len(ucs_data) > 0:
            ucs_pivot = ucs_data.pivot_table(
                index=['condition', 'cluster'], 
                columns='threshold', 
                values='p_value', 
                aggfunc='mean'
            )
            sns.heatmap(ucs_pivot, annot=True, fmt='.3f', cmap='RdYlBu_r',
                       cbar_kws={'label': 'p-value'}, vmin=0, vmax=0.1)
            plt.title('UCS相関係数等質性検定 p値')
            plt.ylabel('条件・クラスター')
        
        # 相関係数差のヒートマップ（CS）
        plt.subplot(2, 3, 3)
        if len(cs_data) > 0:
            cs_diff_pivot = cs_data.pivot_table(
                index=['condition', 'cluster'], 
                columns='threshold', 
                values='correlation_difference', 
                aggfunc='mean'
            )
            sns.heatmap(cs_diff_pivot, annot=True, fmt='.3f', cmap='Reds',
                       cbar_kws={'label': '相関係数差'})
            plt.title('CS相関係数のPhase間差')
            plt.ylabel('条件・クラスター')
        
        # 相関係数差のヒートマップ（UCS）
        plt.subplot(2, 3, 4)
        if len(ucs_data) > 0:
            ucs_diff_pivot = ucs_data.pivot_table(
                index=['condition', 'cluster'], 
                columns='threshold', 
                values='correlation_difference', 
                aggfunc='mean'
            )
            sns.heatmap(ucs_diff_pivot, annot=True, fmt='.3f', cmap='Reds',
                       cbar_kws={'label': '相関係数差'})
            plt.title('UCS相関係数のPhase間差')
            plt.ylabel('条件・クラスター')
        
        # 有意差の分布
        plt.subplot(2, 3, 5)
        sig_counts = homogeneity_df.groupby(['condition', 'metric'])['significant'].sum().unstack()
        if not sig_counts.empty:
            sig_counts.plot(kind='bar', ax=plt.gca())
            plt.title('条件別有意差数')
            plt.ylabel('有意差数')
            plt.xticks(rotation=45)
            plt.legend(title='Metric')
        
        # 相関係数の散布図（Phase1 vs Phase2）
        plt.subplot(2, 3, 6)
        plt.scatter(homogeneity_df['phase1_correlation'], 
                   homogeneity_df['phase2_correlation'],
                   c=homogeneity_df['significant'].map({True: 'red', False: 'blue'}),
                   alpha=0.6)
        
        # 対角線
        min_corr = min(homogeneity_df['phase1_correlation'].min(), 
                      homogeneity_df['phase2_correlation'].min())
        max_corr = max(homogeneity_df['phase1_correlation'].max(), 
                      homogeneity_df['phase2_correlation'].max())
        plt.plot([min_corr, max_corr], [min_corr, max_corr], 'k--', alpha=0.5)
        
        plt.xlabel('Phase1 相関係数')
        plt.ylabel('Phase2 相関係数')
        plt.title('Phase間相関係数の比較')
        plt.legend(['等しい相関', '有意差なし', '有意差あり'])
        
        plt.tight_layout()
        plt.savefig('correlation_homogeneity_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("可視化ファイルを保存:")
        print("- correlation_homogeneity_analysis.png")


def main():
    """メイン実行関数"""
    print("CS・UCS相関係数のPhase間等質性検定を開始します...")
    
    # 分析器の初期化
    analyzer = PhaseCorrelationHomogeneityAnalyzer('final_valid_updated.csv', max_k=5)
    
    # threshold値の設定
    thresholds = [1.0, 0.7, 0.5, 0.2, 0.1]
    
    # 相関係数等質性検定の実行
    homogeneity_df = analyzer.run_correlation_homogeneity_analysis(thresholds)
    
    # 可視化
    analyzer.create_correlation_homogeneity_visualizations(homogeneity_df)
    
    print("\n分析完了! 以下のファイルが生成されました:")
    print("- correlation_homogeneity_results.csv")
    print("- correlation_homogeneity_analysis.png")


if __name__ == "__main__":
    main()
