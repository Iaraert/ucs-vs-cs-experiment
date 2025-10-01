# -*- coding: utf-8 -*-
"""
unified_correlation_analysis.py

相関分析の統合版
以下の機能を統合:
1. 基本相関分析 (correlation_analysis_extended.py)
2. SSモデル統合相関分析 (withSS/correlation_analysis_extended_with_ss.py)

使用方法:
    python unified_correlation_analysis.py --mode basic
    python unified_correlation_analysis.py --mode ss --alpha 5.0 --beta 20.0
    python unified_correlation_analysis.py --mode both
"""

import argparse
import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import spearmanr, pearsonr
from CS_UCS import CS, UCS

# SSモデル関連のインポート (利用可能な場合)
# try:
#     from ss_model import SSModel, ContingencyData
#     from ss_model_utils import calculate_ss_metrics
#     SS_AVAILABLE = True
# except ImportError:
#     SS_AVAILABLE = False
#     print("警告: SSモデルが利用できません。基本分析のみ実行されます。")
SS_AVAILABLE = False

# 日本語フォント設定
try:
    import matplotlib_fontja
    matplotlib_fontja.japanize()
except:
    pass

class UnifiedCorrelationAnalyzer:
    CORRELATION_METHODS = ("spearman", "pearson")
    BASE_METRICS = ["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"]
    SS_METRICS = ["SS_Support", "Uniform_Support", "Chi2_Support"]

    def __init__(self, csv_path="final_valid_6_samples.csv", max_k=5, alpha=5.0, beta=20.0):
        self.csv_path = csv_path
        self.max_k = max_k
        self.alpha = alpha  # SSモデルパラメータ
        self.beta = beta    # SSモデルパラメータ
        self.df = None
        self.basic_sample_metrics_df = None
        self.ss_sample_metrics_df = None
        self.sample_records = []
          # SSモデル初期化
        # if SS_AVAILABLE:
        #     self.ss_model = SSModel(alpha=alpha, beta=beta)
        # else:
        #     self.ss_model = None
        self.ss_model = None
    
    def load_data(self):
        """データ読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        print(f"ユニーク参加者数: {self.df['user_id'].nunique()}")
    
    def _metric_columns(self, include_ss=False):
        metrics = list(self.BASE_METRICS)
        if include_ss and SS_AVAILABLE:
            metrics += self.SS_METRICS
        return metrics

    def _corr_column(self, metric, method):
        return f"{metric}_{method}"

    def _correlation_columns(self, metrics):
        return [self._corr_column(metric, method) for metric in metrics for method in self.CORRELATION_METHODS]

    def _assign_correlation_values(self, container, correlations, include_ss):
        for metric in self._metric_columns(include_ss):
            for method in self.CORRELATION_METHODS:
                key = self._corr_column(metric, method)
                container[key] = correlations.get(key, np.nan)

    def _append_sample_metrics(self, df_subset, model_df, label, prefix, cs_th, ucs_th):
        """Keep sample-level metrics for CSV export"""
        if model_df is None or model_df.empty:
            return
        sample_df = model_df.copy().reset_index()
        if "sample_number" not in sample_df.columns and "index" in sample_df.columns:
            sample_df = sample_df.rename(columns={"index": "sample_number"})
        if "estimate_mean" not in sample_df.columns and df_subset is not None:
            num_col = f"{prefix}_sample_number"
            est_col = f"{prefix}_estimate"
            if num_col in df_subset.columns and est_col in df_subset.columns:
                ratings = df_subset.groupby(num_col)[est_col].mean()
                sample_df["estimate_mean"] = sample_df["sample_number"].map(ratings)
        if "condition" not in sample_df.columns:
            if df_subset is not None and not df_subset.empty and "Cond" in df_subset.columns:
                sample_df["condition"] = df_subset["Cond"].iloc[0]
            else:
                sample_df["condition"] = np.nan
        sample_df["case_label"] = label
        sample_df["prefix"] = prefix
        sample_df["cs_threshold"] = cs_th
        sample_df["ucs_threshold"] = ucs_th
        self.sample_records.append(sample_df)


    def compute_correlations(self, x, y):
        """安全にピアソン/スピアマン相関を計算"""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        mask = (~np.isnan(x)) & (~np.isnan(y)) & np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 2:
            return {method: np.nan for method in self.CORRELATION_METHODS}

        x_clean = x[mask]
        y_clean = y[mask]

        if np.any(np.abs(x_clean) > 1e10) or np.any(np.abs(y_clean) > 1e10):
            return {method: np.nan for method in self.CORRELATION_METHODS}

        if np.std(x_clean) == 0 or np.std(y_clean) == 0:
            return {method: 0.0 for method in self.CORRELATION_METHODS}

        computations = {
            "spearman": lambda: spearmanr(x_clean, y_clean)[0],
            "pearson": lambda: pearsonr(x_clean, y_clean)[0],
        }

        results = {}
        for method, func in computations.items():
            try:
                corr = func()
            except Exception as exc:
                print(f"{method.title()}相関計算エラー: {exc}")
                corr = np.nan
            if not np.isfinite(corr):
                corr = np.nan
            results[method] = corr

        return {method: results.get(method, np.nan) for method in self.CORRELATION_METHODS}
    
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
    
    def metrics_from_abcd(self, a, b, c, d, cs_th, ucs_th, is_gene, is_sym):
        """a,b,c,dからモデル指標を計算"""
        # 基本指標
        pe_c = a / (a + b) if (a + b) else np.nan
        pc_e = a / (a + c) if (a + c) else np.nan
        delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
        paris = a / (a + b + c) if (a + b + c) else np.nan
        dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
        
        # CS/UCS計算（例外処理付き）
        try:
            cs_val = CS((a, b, c, d), cs_th, is_gene)
            if not np.isfinite(cs_val):
                cs_val = np.nan
        except:
            cs_val = np.nan
            
        try:
            ucs_val = UCS((a, b, c, d), ucs_th, is_gene)
            if not np.isfinite(ucs_val):
                ucs_val = np.nan
        except:
            ucs_val = np.nan

        if is_sym == 1:
            try:
                cs_pos = CS((a, b, 0, 0), cs_th, is_gene)
                cs_neg = CS((c, d, 0, 0), cs_th, is_gene)
                if np.isfinite(cs_pos) and np.isfinite(cs_neg):
                    cs_val = cs_pos - cs_neg
                else:
                    cs_val = np.nan
            except:
                cs_val = np.nan

            try:
                ucs_pos = UCS((a, b, 0, 0), ucs_th, is_gene)
                ucs_neg = UCS((c, d, 0, 0), ucs_th, is_gene)
                if np.isfinite(ucs_pos) and np.isfinite(ucs_neg):
                    ucs_val = ucs_pos - ucs_neg
                else:
                    ucs_val = np.nan
            except:
                ucs_val = np.nan

        # 全ての値を有限数に制限
        metrics = [pe_c, pc_e, delta_p, cs_val, ucs_val, paris, dfh, dice]
        safe_metrics = []
        for val in metrics:
            if np.isfinite(val):
                safe_metrics.append(val)
            else:
                safe_metrics.append(np.nan)
        
        return tuple(safe_metrics)
    
    def ss_metrics_from_abcd(self, a, b, c, d):
        """SSモデル指標を計算"""
        # if not SS_AVAILABLE:
        #     return np.nan, np.nan, np.nan
        
        # try:
        #     # 値が有finite数であることを確認
        #     if not all(np.isfinite([a, b, c, d])):
        #         return np.nan, np.nan, np.nan
        #     
        #     # 整数に変換
        #     a, b, c, d = int(a), int(b), int(c), int(d)
        #     
        #     # calculate_ss_metricsを正しく呼び出し
        #     metrics = calculate_ss_metrics(a, b, c, d)
        #     
        #     ss_support = metrics.get('ss_support', np.nan)
        #     uniform_support = metrics.get('uniform_support', np.nan)
        #     chi2_support = metrics.get('chi2_support', np.nan)
        #     
        #     # 有限数チェック
        #     if not np.isfinite(ss_support):
        #         ss_support = np.nan
        #     if not np.isfinite(uniform_support):
        #         uniform_support = np.nan
        #     if not np.isfinite(chi2_support):
        #         chi2_support = np.nan
        #         
        #     return ss_support, uniform_support, chi2_support
        # except Exception as e:
        #     print(f"SSモデル計算エラー: {e}")
        #     return np.nan, np.nan, np.nan
        
        return np.nan, np.nan, np.nan
    
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
    
    def calculate_correlations_basic(self, df_subset, mat, k, prefix, cs_th, ucs_th):
        """基本モデルの相関を計算"""
        return self._calculate_correlations(df_subset, mat, k, prefix, cs_th, ucs_th, include_ss=False)

    def calculate_correlations_with_ss(self, df_subset, mat, k, prefix, cs_th, ucs_th):
        """SSモデルを含む相関を計算"""
        if not SS_AVAILABLE:
            return self.calculate_correlations_basic(df_subset, mat, k, prefix, cs_th, ucs_th)
        return self._calculate_correlations(df_subset, mat, k, prefix, cs_th, ucs_th, include_ss=True)

    def _calculate_correlations(self, df_subset, mat, k, prefix, cs_th, ucs_th, include_ss):
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]

        metric_columns = self._metric_columns(include_ss)
        model_df = pd.DataFrame(
            index=sorted(df_subset[num_col].unique()),
            columns=metric_columns,
            dtype=float,
        )
        model_df.index.name = "sample_number"

        for sample_idx in model_df.index:
            sample_rows = df_subset[df_subset[num_col] == sample_idx]
            if sample_rows.empty:
                continue

            a, b, c, d = sample_rows.iloc[0][abcd_cols].astype(int).values
            is_gene = sample_rows[est_col].mean() >= 0
            is_sym = sample_rows["Cond"].iloc[0] if "Cond" in sample_rows.columns else 0

            basic_metrics = self.metrics_from_abcd(a, b, c, d, cs_th, ucs_th, is_gene, is_sym)
            values = list(basic_metrics)

            if include_ss and SS_AVAILABLE:
                values += list(self.ss_metrics_from_abcd(a, b, c, d))

            model_df.loc[sample_idx] = values

        sample_ratings = df_subset.groupby(num_col)[est_col].mean().reindex(model_df.index)
        model_df["estimate_mean"] = sample_ratings.values
        if "Cond" in df_subset.columns and not df_subset.empty:
            model_df["condition"] = df_subset["Cond"].iloc[0]
        else:
            model_df["condition"] = np.nan

        groups = {"All": df_subset}
        for cl in range(k):
            ids = mat[mat["cluster"] == cl].index
            groups[f"Cluster{cl+1}"] = df_subset[df_subset["user_id"].isin(ids)]

        corr_columns = self._correlation_columns(metric_columns)
        corr_table = pd.DataFrame(index=groups.keys(), columns=corr_columns, dtype=float)
        crt_table = pd.DataFrame(index=groups.keys(), columns=["CRT_mean", "estimate_mean"], dtype=float)

        metric_values = {metric: model_df[metric].values for metric in metric_columns}

        for g_name, g_df in groups.items():
            if g_df.empty:
                crt_table.loc[g_name] = [np.nan, np.nan]
                continue

            y = g_df.groupby(num_col)[est_col].mean().reindex(model_df.index).values

            crt_mean = g_df["crt_correct_cnt"].mean() if "crt_correct_cnt" in g_df.columns else np.nan
            estimate_mean = g_df[est_col].mean()
            crt_table.loc[g_name] = [crt_mean, estimate_mean]

            for metric in metric_columns:
                correlations = self.compute_correlations(metric_values[metric], y)
                for method, corr in correlations.items():
                    corr_table.loc[g_name, self._corr_column(metric, method)] = corr

        return corr_table, crt_table, model_df

    def get_cluster_sizes(self, mat, k):
        """クラスターサイズを取得"""
        cluster_sizes = {}
        for i in range(k):
            cluster_sizes[i] = len(mat[mat["cluster"] == i])
        return cluster_sizes
    
    def analyze_case(self, label, df_subset, prefix, cs_th, ucs_th, use_ss=False):
        """個別ケースの分析"""
        if df_subset.empty:
            return None, None, None, None
        
        mat, k, labels = self.create_cluster_data(df_subset, prefix)
        if mat is None:
            return None, None, None, None
        
        if use_ss:
            corr_table, crt_table, model_df = self.calculate_correlations_with_ss(df_subset, mat, k, prefix, cs_th, ucs_th)
        else:
            corr_table, crt_table, model_df = self.calculate_correlations_basic(df_subset, mat, k, prefix, cs_th, ucs_th)
        
        cluster_sizes = self.get_cluster_sizes(mat, k)
        
        return corr_table, crt_table, cluster_sizes, model_df
    
    def analyze_condition_only(self, label, df_subset, prefix, cs_th, ucs_th, use_ss=False):
        """条件ごとの分析（クラスタリングなし）"""
        if df_subset.empty:
            return None

        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]

        include_ss = use_ss and SS_AVAILABLE
        metric_columns = self._metric_columns(include_ss)

        model_df = pd.DataFrame(
            index=sorted(df_subset[num_col].unique()),
            columns=metric_columns,
            dtype=float,
        )

        for sample_idx in model_df.index:
            sample_rows = df_subset[df_subset[num_col] == sample_idx]
            if sample_rows.empty:
                continue

            a, b, c, d = sample_rows.iloc[0][abcd_cols].astype(int).values
            is_gene = sample_rows[est_col].mean() >= 0
            is_sym = sample_rows["Cond"].iloc[0] if "Cond" in sample_rows.columns else 0

            values = list(self.metrics_from_abcd(a, b, c, d, cs_th, ucs_th, is_gene, is_sym))
            if include_ss:
                values += list(self.ss_metrics_from_abcd(a, b, c, d))

            model_df.loc[sample_idx] = values

        y = df_subset.groupby(num_col)[est_col].mean().reindex(model_df.index).values

        correlations = {}
        for metric in metric_columns:
            metric_values = model_df[metric].values
            for method, corr in self.compute_correlations(metric_values, y).items():
                correlations[self._corr_column(metric, method)] = corr

        crt_mean = df_subset["crt_correct_cnt"].mean() if "crt_correct_cnt" in df_subset.columns else np.nan
        estimate_mean = df_subset[est_col].mean()

        return correlations, crt_mean, estimate_mean, len(df_subset)

    def run_condition_correlation_analysis(self, thresholds=None, use_ss=False):
        """条件ごと（クラスタリングなし）相関分析実行"""
        if thresholds is None:
            thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]

        if not hasattr(self, 'df') or self.df is None:
            self.load_data()

        include_ss = use_ss and SS_AVAILABLE
        analysis_label = "SSモデル統合" if include_ss else "基本"
        print(f"=== {analysis_label}条件別相関分析を実行 ===")

        if use_ss and not SS_AVAILABLE:
            print("SSモデルが利用できないため、基本指標のみで分析します")
        if include_ss:
            print(f"SSモデルパラメータ: α={self.alpha}, β={self.beta}")

        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()

        self.sample_records = []
        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]

        all_results = []

        for th in thresholds:
            print(f"\n=== CS threshold = {th:.1f}, UCS threshold = {th:.1f} ===")

            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue

                result = self.analyze_condition_only(label, df_sub, prefix, th, th, use_ss=include_ss)
                if result is None:
                    continue

                correlations, crt_mean, estimate_mean, n_participants = result

                if "ex1" in label:
                    experiment_type = "サマリー"
                elif "ex2" in label:
                    experiment_type = "オンライン"
                else:
                    continue

                if "Cond0" in label:
                    condition = "非対称否定"
                elif "Cond1" in label:
                    condition = "対称否定"
                else:
                    continue

                result_row = {
                    "CS_threshold": th,
                    "UCS_threshold": th,
                    "実験タイプ": experiment_type,
                    "条件": condition,
                    "n": n_participants,
                    "CRT_mean": crt_mean,
                    "estimate_mean": estimate_mean,
                }
                self._assign_correlation_values(result_row, correlations, include_ss)

                all_results.append(result_row)

        results_df = pd.DataFrame(all_results)

        if not results_df.empty:
            meta_columns = [
                "CS_threshold",
                "UCS_threshold",
                "実験タイプ",
                "条件",
                "n",
                "CRT_mean",
                "estimate_mean",
            ]
            corr_columns = self._correlation_columns(self._metric_columns(include_ss))
            ordered_columns = meta_columns + corr_columns
            results_df = results_df.reindex(columns=ordered_columns)

        if not results_df.empty:
            filename = "condition_ss_correlation_results.csv" if include_ss else "condition_basic_correlation_results.csv"
            results_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n→ {analysis_label}条件別分析結果を保存: {filename}")

            print(f"\n=== {analysis_label}条件別分析結果プレビュー ===")
            print(f"総行数: {len(results_df)}")
            print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
            print("\n先頭5行:")
            print(results_df.head().to_string(index=False))

            print("\n=== CS/UCS 相関係数の要約統計 ===")
            for method in self.CORRELATION_METHODS:
                for metric in ["CS", "UCS"]:
                    col = self._corr_column(metric, method)
                    if col not in results_df:
                        continue
                    valid_data = results_df[col].dropna()
                    if len(valid_data) > 0:
                        print(
                            f"{metric} ({method.title()}): mean={valid_data.mean():.3f}, "
                            f"std={valid_data.std():.3f}, min={valid_data.min():.3f}, max={valid_data.max():.3f}"
                        )

            if include_ss:
                ss_metrics = ["SS_Support", "Uniform_Support", "Chi2_Support"]
                print("\n=== SSモデル指標の相関要約統計 ===")
                for method in self.CORRELATION_METHODS:
                    for metric in ss_metrics:
                        col = self._corr_column(metric, method)
                        if col not in results_df:
                            continue
                        valid_data = results_df[col].dropna()
                        if len(valid_data) > 0:
                            print(
                                f"{metric} ({method.title()}): mean={valid_data.mean():.3f}, "
                                f"std={valid_data.std():.3f}, min={valid_data.min():.3f}, max={valid_data.max():.3f}"
                            )

        return results_df

    def run_basic_analysis(self, thresholds=None):
        """基本相関分析実行"""
        return self._run_cluster_analysis(thresholds, include_ss=False)

    def run_ss_analysis(self, thresholds=None):
        """SSモデル指標を含む相関分析実行"""
        if not SS_AVAILABLE:
            print("SSモデルが利用できないため、基本分析を実行します")
            return self._run_cluster_analysis(thresholds, include_ss=False)
        return self._run_cluster_analysis(thresholds, include_ss=True)

    def _run_cluster_analysis(self, thresholds, include_ss):
        if thresholds is None:
            thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]

        if not hasattr(self, 'df') or self.df is None:
            self.load_data()

        include_ss = bool(include_ss and SS_AVAILABLE)
        analysis_label = "SSモデル統合" if include_ss else "基本"
        print(f"=== {analysis_label}相関分析実行 ===")
        if include_ss:
            print(f"SSモデルパラメータ: α={self.alpha}, β={self.beta}")

        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()

        self.sample_records = []
        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]

        all_results = []

        for th in thresholds:
            header = f"CS threshold = {th:.1f}, UCS threshold = {th:.1f}"
            if include_ss:
                header += " + SS Model"
            print(f"\n=== {header} ===")

            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue

                corr_table, crt_table, cluster_sizes, model_df = self.analyze_case(
                    label, df_sub, prefix, th, th, use_ss=include_ss)

                if corr_table is None:
                    continue
                self._append_sample_metrics(df_sub, model_df, label, prefix, th, th)

                for cluster_name in corr_table.index:
                    if cluster_name == "All":
                        continue

                    if "ex1" in label:
                        experiment_type = "サマリー"
                    elif "ex2" in label:
                        experiment_type = "オンライン"
                    else:
                        continue

                    if "Cond0" in label:
                        condition = "非対称否定"
                    elif "Cond1" in label:
                        condition = "対称否定"
                    else:
                        continue

                    cluster_num = cluster_name.replace("Cluster", "")
                    cluster_index = int(cluster_num) - 1

                    result_row = {
                        "CS_threshold": th,
                        "UCS_threshold": th,
                        "実験タイプ": experiment_type,
                        "条件": condition,
                        "クラスタ": f"クラスタ{cluster_num}",
                        "n": cluster_sizes.get(cluster_index, 0),
                        "CRT_mean": crt_table.loc[cluster_name, "CRT_mean"],
                        "estimate_mean": crt_table.loc[cluster_name, "estimate_mean"],
                    }

                    correlations = corr_table.loc[cluster_name].to_dict()
                    self._assign_correlation_values(result_row, correlations, include_ss)

                    all_results.append(result_row)

        results_df = pd.DataFrame(all_results)

        if not results_df.empty:
            meta_columns = [
                "CS_threshold",
                "UCS_threshold",
                "実験タイプ",
                "条件",
                "クラスタ",
                "n",
                "CRT_mean",
                "estimate_mean",
            ]
            corr_columns = self._correlation_columns(self._metric_columns(include_ss))
            ordered_columns = meta_columns + corr_columns
            results_df = results_df.reindex(columns=ordered_columns)

        if not results_df.empty:
            filename = "unified_ss_correlation_results.csv" if include_ss else "unified_basic_correlation_results.csv"
            results_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n→ {analysis_label}分析結果を保存: {filename}")

            print(f"\n=== {analysis_label}分析結果プレビュー ===")
            print(f"総行数: {len(results_df)}")
            print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
            print("\n先頭5行:")
            print(results_df.head().to_string(index=False))

            print("\n=== CS/UCS 相関係数の要約統計 ===")
            for method in self.CORRELATION_METHODS:
                for metric in ["CS", "UCS"]:
                    col = self._corr_column(metric, method)
                    if col not in results_df:
                        continue
                    valid_data = results_df[col].dropna()
                    if len(valid_data) > 0:
                        print(
                            f"{metric} ({method.title()}): mean={valid_data.mean():.3f}, "
                            f"std={valid_data.std():.3f}, min={valid_data.min():.3f}, max={valid_data.max():.3f}"
                        )

            if include_ss:
                print("\n=== SSモデル指標の相関要約統計 ===")
                for method in self.CORRELATION_METHODS:
                    for metric in self.SS_METRICS:
                        col = self._corr_column(metric, method)
                        if col not in results_df:
                            continue
                        valid_data = results_df[col].dropna()
                        if len(valid_data) > 0:
                            print(
                                f"{metric} ({method.title()}): mean={valid_data.mean():.3f}, "
                                f"std={valid_data.std():.3f}, min={valid_data.min():.3f}, max={valid_data.max():.3f}"
                            )

        sample_metrics_df = pd.concat(self.sample_records, ignore_index=True) if getattr(self, "sample_records", None) else pd.DataFrame()
        meta_columns = ["case_label", "prefix", "condition", "cs_threshold", "ucs_threshold", "sample_number", "estimate_mean"]
        if not sample_metrics_df.empty:
            for col in meta_columns:
                if col not in sample_metrics_df.columns:
                    sample_metrics_df[col] = np.nan
            metric_columns = [col for col in sample_metrics_df.columns if col not in meta_columns]
            ordered_columns = meta_columns + metric_columns
            sample_metrics_df = sample_metrics_df[ordered_columns]
            filename = "unified_ss_sample_metrics.csv" if include_ss else "unified_basic_sample_metrics.csv"
            sample_metrics_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\nSaved sample-level metrics to {filename}")
        else:
            print("\nNo sample-level metrics were generated for export.")
        if include_ss:
            self.ss_sample_metrics_df = sample_metrics_df
        else:
            self.basic_sample_metrics_df = sample_metrics_df
        return results_df

    def create_visualizations(self, basic_df=None, ss_df=None):
        """可視化作成"""
        if basic_df is None and ss_df is None:
            return

        # 基本分析の可視化
        if basic_df is not None and not basic_df.empty:
            self._create_basic_visualization(basic_df)
        
        # SSモデル分析の可視化
        if ss_df is not None and not ss_df.empty and SS_AVAILABLE:
            self._create_ss_visualization(ss_df)
    
        sample_basic = getattr(self, "basic_sample_metrics_df", None)
        if sample_basic is not None and not sample_basic.empty:
            self._create_rating_metric_scatter(sample_basic, include_ss=False)

        sample_ss = getattr(self, "ss_sample_metrics_df", None)
        if SS_AVAILABLE and sample_ss is not None and not sample_ss.empty:
            self._create_rating_metric_scatter(sample_ss, include_ss=True)

    def _create_rating_metric_scatter(self, sample_metrics_df, include_ss=False):
        """Create scatter plots of rating vs CS/UCS values."""
        if sample_metrics_df is None or sample_metrics_df.empty:
            return
        output_dir = "results"
        os.makedirs(output_dir, exist_ok=True)
        metrics = ["CS", "UCS"]
        fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 5))
        if len(metrics) == 1:
            axes = [axes]
        else:
            axes = np.atleast_1d(axes)
        case_labels_series = sample_metrics_df.get("case_label", pd.Series(dtype=str)).fillna("Unknown")
        case_labels = list(pd.unique(case_labels_series))
        palette = plt.cm.get_cmap('tab10', len(case_labels) or 1)
        label_colors = {label: palette(i) for i, label in enumerate(case_labels)}
        for idx_ax, metric in enumerate(metrics):
            ax = axes[idx_ax]
            if metric not in sample_metrics_df.columns:
                ax.axis('off')
                continue
            subset = sample_metrics_df[["estimate_mean", metric, "case_label"]].dropna(subset=["estimate_mean", metric]).copy()
            subset['case_label'] = subset['case_label'].fillna('Unknown')
            if subset.empty:
                ax.axis('off')
                continue
            seen_labels = set()
            for label, group in subset.groupby('case_label'):
                color = label_colors.get(label, 'gray')
                legend_label = label if label not in seen_labels else None
                seen_labels.add(label)
                ax.scatter(group['estimate_mean'], group[metric], s=35, alpha=0.7, color=color, edgecolors='none', label=legend_label)
            corr_vals = self.compute_correlations(subset[metric].values, subset['estimate_mean'].values)
            pear = corr_vals.get('pearson', np.nan)
            spear = corr_vals.get('spearman', np.nan)
            if len(subset) >= 2 and np.std(subset['estimate_mean'].values) > 0:
                coeffs = np.polyfit(subset['estimate_mean'].values, subset[metric].values, 1)
                x_vals = np.linspace(subset['estimate_mean'].min(), subset['estimate_mean'].max(), 100)
                ax.plot(x_vals, coeffs[0] * x_vals + coeffs[1], color='black', linewidth=1, linestyle='--', alpha=0.6)
            ax.set_xlabel('Rating (mean)')
            ax.set_ylabel(metric)
            ax.set_title(f'{metric} vs Rating (r={pear:.2f}, rho={spear:.2f})')
            ax.grid(True, alpha=0.3)
            if seen_labels:
                ax.legend(frameon=False)
        title = 'Rating vs CS/UCS (SS)' if include_ss else 'Rating vs CS/UCS (Basic)'
        fig.suptitle(title, fontsize=14)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        filename = os.path.join(output_dir, 'rating_vs_cs_ucs_ss.png' if include_ss else 'rating_vs_cs_ucs_basic.png')
        fig.savefig(filename, dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f'Saved rating vs CS/UCS scatter to {filename}')

    def _create_basic_visualization(self, df):
        """基本分析の可視化"""
        metrics = ['CS', 'UCS', 'ΔP', 'DFH']

        for method in self.CORRELATION_METHODS:
            n_metrics = len(metrics)
            n_cols = 2
            n_rows = math.ceil(n_metrics / n_cols)
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 6 * n_rows))
            axes = np.array(axes).reshape(-1)
            has_data = False

            for i, metric in enumerate(metrics):
                column = self._corr_column(metric, method)
                if column not in df.columns:
                    axes[i].axis('off')
                    continue

                pivot = df.pivot_table(
                    index=['実験タイプ', '条件'],
                    columns='CS_threshold',
                    values=column,
                    aggfunc='mean',
                )

                if pivot.empty:
                    axes[i].axis('off')
                    continue

                has_data = True
                im = axes[i].imshow(pivot.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
                axes[i].set_title(f'{metric} {method.title()}相関係数 (threshold別)')
                axes[i].set_xlabel('Threshold')
                axes[i].set_ylabel('実験タイプ・条件')
                axes[i].set_xticks(range(len(pivot.columns)))
                axes[i].set_xticklabels([f'{x:.1f}' for x in pivot.columns], rotation=45)
                axes[i].set_yticks(range(len(pivot.index)))
                axes[i].set_yticklabels([f'{x[0]}-{x[1]}' for x in pivot.index])
                plt.colorbar(im, ax=axes[i])

            for ax in axes[n_metrics:]:
                ax.axis('off')

            filename = f'unified_basic_{method}_correlation_heatmaps.png'
            if has_data:
                plt.tight_layout()
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                print(f'保存: {filename}')
            plt.close(fig)

    def _create_ss_visualization(self, df):
        """SSモデル分析の可視化"""
        metrics = ['CS', 'UCS'] + self.SS_METRICS

        for method in self.CORRELATION_METHODS:
            n_metrics = len(metrics)
            n_cols = 2
            n_rows = math.ceil(n_metrics / n_cols)
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 6 * n_rows))
            axes = np.array(axes).reshape(-1)
            has_data = False

            for i, metric in enumerate(metrics):
                column = self._corr_column(metric, method)
                if column not in df.columns:
                    axes[i].axis('off')
                    continue

                pivot = df.pivot_table(
                    index=['実験タイプ', '条件'],
                    columns='CS_threshold',
                    values=column,
                    aggfunc='mean',
                )

                if pivot.empty:
                    axes[i].axis('off')
                    continue

                has_data = True
                im = axes[i].imshow(pivot.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
                axes[i].set_title(f'{metric} {method.title()}相関係数 (threshold別)')
                axes[i].set_xlabel('Threshold')
                axes[i].set_ylabel('実験タイプ・条件')
                axes[i].set_xticks(range(len(pivot.columns)))
                axes[i].set_xticklabels([f'{x:.1f}' for x in pivot.columns], rotation=45)
                axes[i].set_yticks(range(len(pivot.index)))
                axes[i].set_yticklabels([f'{x[0]}-{x[1]}' for x in pivot.index])
                plt.colorbar(im, ax=axes[i])

            for ax in axes[n_metrics:]:
                ax.axis('off')

            filename = f'unified_ss_{method}_correlation_heatmaps.png'
            if has_data:
                plt.tight_layout()
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                print(f'保存: {filename}')
            plt.close(fig)

    def create_interaction_visualizations(self, interaction_df):
        #交互作用分析の可視化
        # if interaction_df is None or interaction_df.empty:
        #     return
        #
        # # 1. 相関差のヒートマップ
        # fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        #
        # for i, metric in enumerate(['CS', 'UCS']):
        #     metric_data = interaction_df[interaction_df['指標'] == metric]
        #     if metric_data.empty:
        #         continue
        #     
        #     pivot = metric_data.pivot_table(
        #         index='実験タイプ', 
        #         columns='CS_threshold', 
        #         values='相関差',
        #         aggfunc='mean'
        #     )
        #     
        #     if not pivot.empty:
        #         im = axes[i].imshow(pivot.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
        #         axes[i].set_title(f'{metric} スピアマン相関差 (非対称否定 - 対称否定)')
        #         axes[i].set_xlabel('Threshold')
        #         axes[i].set_ylabel('実験タイプ')
        #         axes[i].set_xticks(range(len(pivot.columns)))
        #         axes[i].set_xticklabels([f'{x:.1f}' for x in pivot.columns], rotation=45)
        #         axes[i].set_yticks(range(len(pivot.index)))
        #         axes[i].set_yticklabels(pivot.index)
        #         
        #         # 値を表示
        #         for row in range(len(pivot.index)):
        #             for col in range(len(pivot.columns)):
        #                 value = pivot.iloc[row, col]
        #                 if not np.isnan(value):
        #                     axes[i].text(col, row, f'{value:.3f}', ha='center', va='center',
        #                                color='white' if abs(value) > 0.5 else 'black')
        #         
        #         plt.colorbar(im, ax=axes[i])
        # plt.tight_layout()
        # filename = 'interaction_spearman_correlation_differences.png'
        # plt.savefig(filename, dpi=300, bbox_inches='tight')
        # plt.close()
        # print(f"保存: {filename}")
        # 
        # # 2. p値のヒートマップ
        # fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        # 
        # for i, metric in enumerate(['CS', 'UCS']):
        #     metric_data = interaction_df[interaction_df['指標'] == metric]
        #     if metric_data.empty:
        #         continue
        #     
        #     pivot = metric_data.pivot_table(
        #         index='実験タイプ', 
        #         columns='CS_threshold', 
        #         values='p値',
        #         aggfunc='mean'
        #     )
        #     
        #     if not pivot.empty:                # -log10(p値)で色付け
        #         log_p = -np.log10(pivot.values + 1e-10)  # ゼロ除算回避
        #         im = axes[i].imshow(log_p, cmap='Reds', aspect='auto')
        #         axes[i].set_title(f'{metric} スピアマン相関交互作用 -log10(p値)')
        #         axes[i].set_xlabel('Threshold')
        #         axes[i].set_ylabel('実験タイプ')
        #         axes[i].set_xticks(range(len(pivot.columns)))
        #         axes[i].set_xticklabels([f'{x:.1f}' for x in pivot.columns], rotation=45)
        #         axes[i].set_yticks(range(len(pivot.index)))
        #         axes[i].set_yticklabels(pivot.index)
        #         
        #         # 有意水準の線を追加
        #         axes[i].axhline(y=-0.5, color='blue', linestyle='--', alpha=0.7, label='p=0.05')
        #         axes[i].axhline(y=-0.5, color='red', linestyle='--', alpha=0.7, label='p=0.01')
        #         
        #         # 値を表示
        #         for row in range(len(pivot.index)):
        #             for col in range(len(pivot.columns)):
        #                 value = pivot.iloc[row, col]
        #                 if not np.isnan(value):
        #                     axes[i].text(col, row, f'{value:.3f}', ha='center', va='center',
        #                                color='white' if log_p[row, col] > 1 else 'black')
        #         
        #         plt.colorbar(im, ax=axes[i])
        # plt.tight_layout()
        # filename = 'interaction_spearman_p_values.png'
        # plt.savefig(filename, dpi=300, bbox_inches='tight')
        # plt.close()
        # print(f"保存: {filename}")
        # 
        # # 3. 効果サイズの分布
        # valid_effects = interaction_df['効果サイズ'].dropna()
        # if len(valid_effects) > 0:
        #     plt.figure(figsize=(10, 6))
        #     plt.hist(valid_effects, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        #     plt.axvline(valid_effects.mean(), color='red', linestyle='--', label=f'平均: {valid_effects.mean():.3f}')
        #     plt.axvline(0.1, color='orange', linestyle=':', label='小効果: 0.1')
        #     plt.axvline(0.3, color='green', linestyle=':', label='中効果: 0.3')
        #     plt.axvline(0.5, color='purple', linestyle=':', label='大効果: 0.5')            
        #     plt.xlabel('効果サイズ (Cohen\'s q)')
        #     plt.ylabel('頻度')
        #     plt.title('スピアマン相関交互作用効果サイズの分布')
        #     plt.legend()
        #     plt.grid(True, alpha=0.3)
        #     filename = 'interaction_spearman_effect_sizes.png'
        #     plt.savefig(filename, dpi=300, bbox_inches='tight')
        #     plt.close()
        #     print(f"保存: {filename}")
        return
    
    def analyze_interaction_effects(self, thresholds=None, use_ss=False):
        """条件（Cond, experiment_type）の交互作用を検証"""
        # from scipy import stats
        # try:
        #     from scipy.stats import f_oneway
        #     from sklearn.metrics import r2_score
        # except ImportError:
        #     print("警告: scipy.statsまたはsklearnが利用できません")
        #     return None
        # 
        # if thresholds is None:
        #     thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]
        # 
        # if not hasattr(self, 'df') or self.df is None:
        #     self.load_data()
        # 
        # # データ準備
        # ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        # ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        # 
        # cases = [
        #     ("ex1", ex1_first, "サマリー"),
        #     ("ex2", ex2_first, "オンライン")
        # ]
        # 
        # interaction_results = []
        # print(f"=== 条件交互作用分析実行（スピアマン相関） ===")
        # if use_ss:
        #     print(f"SSモデルパラメータ: α={self.alpha}, β={self.beta}")
        # 
        # # threshold値で実行
        # for th in thresholds:
        #     print(f"\n=== CS threshold = {th:.1f}, UCS threshold = {th:.1f} ===")
        #     
        #     for prefix, df_exp, exp_type in cases:
        #         if df_exp.empty:
        #             continue
        #         
        #         est_col = f"{prefix}_estimate"
        #         num_col = f"{prefix}_sample_number"
        #         abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
        #         
        #         # モデル指標を計算
        #         model_columns = ["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice"]
        #         if use_ss and SS_AVAILABLE:
        #             model_columns.extend(["SS_Support", "Uniform_Support", "Chi2_Support"])
        #         
        #         model_df = pd.DataFrame(
        #             index=sorted(df_exp[num_col].unique()),
        #             columns=model_columns,
        #             dtype=float
        #         )
        #         
        #         for s in model_df.index:
        #             row = df_exp[df_exp[num_col] == s].iloc[0]
        #             a, b, c, d = row[abcd_cols].astype(int).values
        #             is_gene = df_exp[df_exp[num_col] == s][est_col].mean() >= 0
        #             is_sym = df_exp[df_exp[num_col] == s]["Cond"].iloc[0] if "Cond" in df_exp.columns else 0
        #             
        #             # 基本指標
        #             metrics = self.metrics_from_abcd(a, b, c, d, th, th, is_gene, is_sym)
        #             
        #             if use_ss and SS_AVAILABLE:
        #                 # SSモデル指標
        #                 ss_metrics = self.ss_metrics_from_abcd(a, b, c, d)
        #                 all_metrics = list(metrics) + list(ss_metrics)
        #             else:
        #                 all_metrics = list(metrics)
        #             
        #             model_df.loc[s] = all_metrics
        #         
        #         # 条件別のグループを作成
        #         cond0_data = df_exp[df_exp["Cond"] == 0]  # 非対称否定
        #         cond1_data = df_exp[df_exp["Cond"] == 1]  # 対称否定
        #         
        #         for metric in ["CS", "UCS"]:
        #             if metric not in model_df.columns:
        #                 continue
        #             
        #             # 各条件での相関係数を計算
        #             cond0_corr = np.nan
        #             cond1_corr = np.nan
        #             
        #             if not cond0_data.empty:
        #                 y0 = cond0_data.groupby(num_col)[est_col].mean().reindex(model_df.index).values
        #                 x = model_df[metric].values
        #                 cond0_corr = self.safe_corr(x, y0)
        #             
        #             if not cond1_data.empty:
        #                 y1 = cond1_data.groupby(num_col)[est_col].mean().reindex(model_df.index).values
        #                 x = model_df[metric].values
        #                 cond1_corr = self.safe_corr(x, y1)
        #             
        #             # 交互作用効果の検定
        #             interaction_p_value = np.nan
        #             f_statistic = np.nan
        #             effect_size = np.nan
        #             
        #             try:
        #                 # 2要因ANOVAのための準備
        #                 if not cond0_data.empty and not cond1_data.empty:
        #                     # データを再構成
        #                     all_data = []
        #                     for s_num in model_df.index:
        #                         if s_num in cond0_data[num_col].values:
        #                             y0_vals = cond0_data[cond0_data[num_col] == s_num][est_col].values
        #                             for val in y0_vals:
        #                                 all_data.append({
        #                                     'estimate': val,
        #                                     'cond': 0,
        #                                     'sample_num': s_num,
        #                                     'metric_value': model_df.loc[s_num, metric]
        #                                 })
        #                         
        #                         if s_num in cond1_data[num_col].values:
        #                             y1_vals = cond1_data[cond1_data[num_col] == s_num][est_col].values
        #                             for val in y1_vals:
        #                                 all_data.append({
        #                                     'estimate': val,
        #                                     'cond': 1,
        #                                     'sample_num': s_num,
        #                                     'metric_value': model_df.loc[s_num, metric]
        #                                 })
        #                     
        #                     if len(all_data) > 10:  # 最低限のサンプルサイズ
        #                         test_df = pd.DataFrame(all_data)
        #                           # スピアマン相関の差の検定 (Fisher's z-transformation近似)
        #                         if not np.isnan(cond0_corr) and not np.isnan(cond1_corr):
        #                             n0 = len(cond0_data)
        #                             n1 = len(cond1_data)
        #                             
        #                             if n0 > 3 and n1 > 3:
        #                                 # Fisher's z変換（スピアマン相関の近似）
        #                                 z0 = 0.5 * np.log((1 + cond0_corr) / (1 - cond0_corr))
        #                                 z1 = 0.5 * np.log((1 + cond1_corr) / (1 - cond1_corr))
        #                                 
        #                                 # 標準誤差
        #                                 se_diff = np.sqrt(1/(n0-3) + 1/(n1-3))
        #                                 
        #                                 # z統計量
        #                                 z_stat = (z0 - z1) / se_diff
        #                                 
        #                                 # p値（両側検定）
        #                                 interaction_p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        #                                 f_statistic = z_stat ** 2
        #                                 
        #                                 # 効果サイズ (Cohen's q)
        #                                 effect_size = abs(z0 - z1)
        #             
        #             except Exception as e:
        #                 print(f"交互作用検定エラー: {e}")
        #             
        #             # 結果を保存
        #             result_row = {
        #                 "CS_threshold": th,
        #                 "UCS_threshold": th,
        #                 "実験タイプ": exp_type,
        #                 "指標": metric,
        #                 "非対称否定_相関": cond0_corr,
        #                 "対称否定_相関": cond1_corr,
        #                 "相関差": cond0_corr - cond1_corr if not np.isnan(cond0_corr) and not np.isnan(cond1_corr) else np.nan,
        #                 "F統計量": f_statistic,
        #                 "p値": interaction_p_value,
        #                 "効果サイズ": effect_size,
        #                 "有意": "**" if interaction_p_value < 0.01 else "*" if interaction_p_value < 0.05 else "n.s." if not np.isnan(interaction_p_value) else "N/A",
        #                 "非対称否定_n": len(cond0_data),
        #                 "対称否定_n": len(cond1_data)
        #             }
        #             
        #             interaction_results.append(result_row)
        # 
        # # 結果をDataFrameに変換して保存
        # results_df = pd.DataFrame(interaction_results)
        # if not results_df.empty:
        #     if use_ss:
        #         filename = "interaction_effects_ss_spearman_analysis.csv"
        #     else:
        #         filename = "interaction_effects_basic_spearman_analysis.csv"
        #     
        #     results_df.to_csv(filename, index=False, encoding="utf-8-sig")
        #     print(f"\n→ 交互作用分析結果を保存: {filename}")
        #     
        #     # プレビュー表示
        #     print(f"\n=== 交互作用分析結果プレビュー ===")
        #     print(f"総行数: {len(results_df)}")
        #     print(f"\n先頭5行:")
        #     print(results_df.head().to_string(index=False))
        #     
        #     # 有意な交互作用の要約
        #     significant_results = results_df[results_df["有意"].isin(["*", "**"])]
        #     if not significant_results.empty:
        #         print(f"\n=== 有意な交互作用効果 ===")
        #         print(f"有意な結果: {len(significant_results)}件")
        #         print(significant_results[["実験タイプ", "指標", "CS_threshold", "相関差", "p値", "有意"]].to_string(index=False))
        #     else:
        #         print("\n有意な交互作用効果は検出されませんでした。")
        #     
        #     # 効果サイズの要約
        #     valid_effect_sizes = results_df["効果サイズ"].dropna()
        #     if len(valid_effect_sizes) > 0:
        #         print(f"\n=== 効果サイズの要約統計 ===")
        #         print(f"平均効果サイズ: {valid_effect_sizes.mean():.3f}")
        #         print(f"最大効果サイズ: {valid_effect_sizes.max():.3f}")
        #         print(f"最小効果サイズ: {valid_effect_sizes.min():.3f}")
        # 
        # return results_df
        return None
        
def main():
    parser = argparse.ArgumentParser(description="統合相関分析")
    parser.add_argument("--mode", choices=["basic", "ss", "both"], default="basic", 
                       help="分析モード選択")
    parser.add_argument("--data", default="final_valid_6_samples.csv", 
                       help="データファイルパス")
    parser.add_argument("--alpha", type=float, default=5.0, 
                       help="SSモデル α パラメータ")
    parser.add_argument("--beta", type=float, default=20.0, 
                       help="SSモデル β パラメータ")
    parser.add_argument("--max-k", type=int, default=5, 
                       help="最大クラスタ数")
    
    args = parser.parse_args()
    
    # threshold値設定
    thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]
    print("=== 統合相関分析 (Spearman & Pearson) ===")
    print(f"データ: {args.data}")
    print(f"モード: {args.mode}")
    if args.mode in ["ss", "both"]:
        print(f"SSモデルパラメータ: α={args.alpha}, β={args.beta}")
    print(f"threshold値: {len(thresholds)}個")
    print("=" * 50)
    
    analyzer = UnifiedCorrelationAnalyzer(
        csv_path=args.data, 
        max_k=args.max_k, 
        alpha=args.alpha, 
        beta=args.beta
    )
    
    basic_df = None
    ss_df = None
    
    if args.mode in ["basic", "both"]:
        basic_df = analyzer.run_basic_analysis(thresholds)
    if args.mode in ["ss", "both"]:
        ss_df = analyzer.run_ss_analysis(thresholds)
    
    # 条件別相関分析の実行
    print("\n=== 条件別相関分析実行 ===")
    
    if args.mode in ["basic", "both"]:
        condition_basic_df = analyzer.run_condition_correlation_analysis(thresholds, use_ss=False)
    if args.mode in ["ss", "both"]:
        condition_ss_df = analyzer.run_condition_correlation_analysis(thresholds, use_ss=True)
      # 交互作用分析の実行
    print("\n=== 交互作用分析実行 ===")
    
    # if args.mode in ["basic", "both"]:
    #     interaction_basic_df = analyzer.analyze_interaction_effects(thresholds, use_ss=False)
    # 
    # if args.mode in ["ss", "both"]:
    #     interaction_ss_df = analyzer.analyze_interaction_effects(thresholds, use_ss=True)
      # 可視化
    analyzer.create_visualizations(basic_df, ss_df)
    
    # 交互作用分析の可視化
    # if args.mode in ["basic", "both"]:
    #     analyzer.create_interaction_visualizations(interaction_basic_df)
    # if args.mode in ["ss", "both"]:
    #     analyzer.create_interaction_visualizations(interaction_ss_df)
    
    print("\n=== 分析完了 ===")

if __name__ == "__main__":
    main()
