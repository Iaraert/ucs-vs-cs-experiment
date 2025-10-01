"""
correlation_analysis_extended.py

相関分析専用コード - CSとUCSのthreshold値を0.1刻みで変更
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib_fontja
from matplotlib import rcParams
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr, spearmanr
from CS_UCS import CS, UCS, normalize_condition_value


NUMERIC_EPSILON = 1e-12

MODEL_METRIC_COLUMNS = [
    "P(E|C)",
    "P(C|E)",
    "ΔP",
    "CS",
    "UCS",
    "pARIs",
    "DFH",
    "Dice",
    "CS_diff",
    "UCS_diff",
    "CS_ratio",
    "UCS_ratio",
    "CS_single",
    "UCS_single",
]

CONDITION_DEPENDENT_METRICS = [
    "CS_diff",
    "UCS_diff",
    "CS_ratio",
    "UCS_ratio",
    "CS_single",
    "UCS_single",
]


class CorrelationAnalyzer:
    def __init__(self, csv_path: str, max_k: int = 5, debug: bool = False):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame = None
        self.debug = debug
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
    def safe_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        """安全な相関計算"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        valid_count = mask.sum()
        if valid_count < 2:
            return np.nan
        x_valid = x[mask]
        y_valid = y[mask]
        if np.nanstd(x_valid) == 0 or np.nanstd(y_valid) == 0:
            return 0.0
        try:
            corr, _ = pearsonr(x_valid, y_valid)
        except Exception as exc:
            if self.debug:
                print(f"[DEBUG] Pearson correlation failed (n={valid_count}): {exc}")
            return np.nan
        if self.debug:
            print(f"[DEBUG] Pearson correlation computed (n={valid_count}): {corr}")
        return corr

    def safe_spearman_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        """安全なスピアマン順位相関計算"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        valid_count = mask.sum()
        if valid_count < 2:
            return np.nan
        x_valid = x[mask]
        y_valid = y[mask]
        if np.nanstd(x_valid) == 0 or np.nanstd(y_valid) == 0:
            return 0.0
        try:
            corr, _ = spearmanr(x_valid, y_valid)
        except Exception as exc:
            if self.debug:
                print(f"[DEBUG] Spearman correlation failed (n={valid_count}): {exc}")
            return np.nan
        if self.debug:
            print(f"[DEBUG] Spearman correlation computed (n={valid_count}): {corr}")
        return corr

    def _safe_score(self, func, counts, threshold, is_gene, label: str, **kwargs) -> float:
        """CS/UCSの安全なスコア計算"""
        try:
            with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
                score = func(counts, threshold, is_gene, **kwargs)
        except Exception as exc:
            if self.debug:
                print(f"[DEBUG] {label} computation failed for counts={counts}: {exc}")
            return np.nan
        if not np.isfinite(score):
            if self.debug:
                print(f"[DEBUG] {label} produced non-finite value for counts={counts}: {score}")
            return np.nan
        return float(score)

    def _safe_ratio(self, numerator: float, denominator: float, label: str) -> float:
        """安全な比率計算（ゼロ除算を防止）"""
        if (denominator is None) or (not np.isfinite(denominator)):
            if self.debug:
                print(f"[DEBUG] {label} denominator is invalid: {denominator}")
            return np.nan
        if abs(denominator) < NUMERIC_EPSILON:
            if self.debug:
                print(f"[DEBUG] {label} denominator too small (|den|<{NUMERIC_EPSILON}): {denominator}")
            return np.nan
        if numerator is None or not np.isfinite(numerator):
            if self.debug:
                print(f"[DEBUG] {label} numerator is invalid: {numerator}")
            return np.nan
        return float(numerator / denominator)

    def _infer_cond_value_from_label(self, label: str):
        """ラベル文字列から条件値を推定 (Cond0 -> 0, Cond1 -> 1)"""
        if label is None:
            return None
        if "Cond0" in label:
            return 0
        if "Cond1" in label:
            return 1
        if self.debug:
            print(f"[DEBUG] Unable to infer condition value from label '{label}'.")
        return None
        
    def find_optimal_k(self, X: np.ndarray, k_min: int = 2, k_max: int = 5) -> int:
        """最適なクラスタ数を決定"""
        best_k, best_score = k_min, -np.inf
        for k in range(k_min, min(k_max, X.shape[0]) + 1):
            labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
            score = silhouette_score(X, labels)
            if score > best_score:
                best_k, best_score = k, score
        return best_k
        
    def metrics_from_abcd(
        self,
        a: int,
        b: int,
        c: int,
        d: int,
        cs_th: float = 1.0,
        ucs_th: float = 1.0,
        is_gene: bool = True,
        cond_value=None,
    ):
        """a,b,c,d からモデル指標を計算"""
        pe_c = a / (a + b) if (a + b) else np.nan
        pc_e = a / (a + c) if (a + c) else np.nan
        delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
        paris = a / (a + b + c) if (a + b + c) else np.nan
        dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
        cs_val = self._safe_score(CS, (a, b, c, d), cs_th, is_gene, "CS_total")
        ucs_val = self._safe_score(UCS, (a, b, c, d), ucs_th, is_gene, "UCS_total")
        cond_processed = normalize_condition_value(cond_value)
        if cond_value is not None and cond_processed is None and self.debug:
            print(
                f"[DEBUG] Invalid condition value '{cond_value}' treated as default (compute all metrics)."
            )

        cs_diff = ucs_diff = cs_ratio = ucs_ratio = cs_single = ucs_single = np.nan
        condition_metrics_computed = False

        if cond_processed == 0:
            if self.debug:
                print(
                    "[DEBUG] Condition value indicates asymmetric (0). "
                    "Condition-specific metrics set to np.nan."
                )
        else:
            cs_ab = self._safe_score(CS, (a, b, c, d), cs_th, is_gene, "CS_ab")
            cs_cd = self._safe_score(CS, (c, d, a, b), cs_th, not is_gene, "CS_cd")
            ucs_ab = self._safe_score(UCS, (a, b, c, d), ucs_th, is_gene, "UCS_ab")
            ucs_cd = self._safe_score(UCS, (c, d, a, b), ucs_th, not is_gene, "UCS_cd")

            cs_single = self._safe_score(CS, (a, b, 0, 0), cs_th, is_gene, "CS_single", conts_loglike0=(c, d, 0, 0))
            ucs_single = self._safe_score(UCS, (a, b, 0, 0), ucs_th, is_gene, "UCS_single", conts_loglike0=(c, d, 0, 0))

            cs_diff = (cs_ab - cs_cd) if np.isfinite(cs_ab) and np.isfinite(cs_cd) else np.nan
            ucs_diff = (ucs_ab - ucs_cd) if np.isfinite(ucs_ab) and np.isfinite(ucs_cd) else np.nan

            cs_ratio = self._safe_ratio(cs_ab, cs_cd, "CS_ratio")
            ucs_ratio = self._safe_ratio(ucs_ab, ucs_cd, "UCS_ratio")

            cs_single = cs_single if np.isfinite(cs_single) else np.nan
            ucs_single = ucs_single if np.isfinite(ucs_single) else np.nan
            condition_metrics_computed = True

        metrics_tuple = (
            pe_c,
            pc_e,
            delta_p,
            cs_val,
            ucs_val,
            paris,
            dfh,
            dice,
            cs_diff,
            ucs_diff,
            cs_ratio,
            ucs_ratio,
            cs_single,
            ucs_single,
        )

        if self.debug:
            cond_display = (
                "None(default)" if cond_processed is None and cond_value is None else cond_processed
            )
            metrics_map = dict(zip(MODEL_METRIC_COLUMNS, metrics_tuple))
            metrics_map["cond_value_original"] = cond_value
            metrics_map["cond_value_processed"] = cond_processed
            print("[DEBUG] metrics_from_abcd", metrics_map)
            if cond_processed == 0:
                print("[DEBUG] Condition-specific metrics are np.nan due to asymmetric condition.")
            elif condition_metrics_computed:
                computed_subset = {
                    metric: metrics_map[metric] for metric in CONDITION_DEPENDENT_METRICS
                }
                print(
                    "[DEBUG] Condition-specific metrics computed successfully for condition",
                    cond_display,
                    computed_subset,
                )

        return metrics_tuple
        
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
        
    def calculate_correlations(
        self,
        df_subset: pd.DataFrame,
        mat: pd.DataFrame,
        k: int,
        prefix: str,
        cs_th: float,
        ucs_th: float,
        default_cond_value=None,
    ):
        """相関を計算"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]

        # モデル指標を準備
        metric_columns = MODEL_METRIC_COLUMNS

        model_df = pd.DataFrame(
            index=sorted(df_subset[num_col].unique()),
            columns=metric_columns,
            dtype=float,
        )

        cond_column_available = "Cond" in df_subset.columns
        if not cond_column_available and self.debug:
            print(
                f"[DEBUG] 'Cond' column missing in subset for prefix '{prefix}'. "
                f"Using default condition value: {default_cond_value}"
            )

        for s in model_df.index:
            row = df_subset[df_subset[num_col] == s].iloc[0]
            a, b, c, d = row[abcd_cols].astype(int).values
            is_gene = df_subset[df_subset[num_col] == s][est_col].mean() >= 0
            cond_value = None
            if cond_column_available:
                cond_candidates = (
                    df_subset[df_subset[num_col] == s]["Cond"].dropna().unique()
                )
                if len(cond_candidates) == 1:
                    cond_value = cond_candidates[0]
                elif len(cond_candidates) > 1:
                    cond_value = cond_candidates[0]
                    if self.debug:
                        print(
                            f"[DEBUG] Multiple condition values found for sample_number={s}: "
                            f"{cond_candidates}. Using {cond_value}."
                        )
                else:
                    cond_value = default_cond_value
                    if self.debug:
                        print(
                            f"[DEBUG] No condition value available for sample_number={s}. "
                            f"Fallback to default: {default_cond_value}"
                        )
            else:
                cond_value = default_cond_value

            model_df.loc[s] = self.metrics_from_abcd(
                a,
                b,
                c,
                d,
                cs_th=cs_th,
                ucs_th=ucs_th,
                is_gene=is_gene,
                cond_value=cond_value,
            )

        # グループ定義
        groups = {"All": df_subset}
        for cl in range(k):
            ids = mat[mat["cluster"] == cl].index
            groups[f"Cluster{cl+1}"] = df_subset[df_subset["user_id"].isin(ids)]
        group_names = list(groups.keys())
        # 相関テーブル初期化
        corr_table_pearson = pd.DataFrame(index=group_names, columns=metric_columns, dtype=float)
        corr_table_spearman = pd.DataFrame(index=group_names, columns=metric_columns, dtype=float)
        # CRT平均テーブル初期化
        crt_table = pd.DataFrame(index=group_names, columns=["CRT_mean", "estimate_mean"])
        # 相関計算
        for g_name, g_df in groups.items():
            # 推定値の平均
            y = g_df.groupby(num_col)[est_col].mean().reindex(model_df.index).values
            
            # CRT平均スコア計算
            if len(g_df) > 0 and "crt_correct_cnt" in g_df.columns:
                crt_mean = g_df["crt_correct_cnt"].mean()
                if pd.notna(crt_mean):
                    crt_table.loc[g_name, "CRT_mean"] = round(crt_mean, 3)
                else:
                    crt_table.loc[g_name, "CRT_mean"] = np.nan
            else:
                crt_table.loc[g_name, "CRT_mean"] = np.nan
            
            # 評定値の平均
            if len(g_df) > 0:
                estimate_mean = g_df[est_col].mean()
                if pd.notna(estimate_mean):
                    crt_table.loc[g_name, "estimate_mean"] = round(estimate_mean, 3)
                else:
                    crt_table.loc[g_name, "estimate_mean"] = np.nan
            else:
                crt_table.loc[g_name, "estimate_mean"] = np.nan
            
            # 各指標との相関
            for metric in metric_columns:
                x = model_df[metric].values
                pearson_val = self.safe_corr(x, y)
                spearman_val = self.safe_spearman_corr(x, y)
                corr_table_pearson.loc[g_name, metric] = (
                    np.nan if np.isnan(pearson_val) else round(float(pearson_val), 3)
                )
                corr_table_spearman.loc[g_name, metric] = (
                    np.nan if np.isnan(spearman_val) else round(float(spearman_val), 3)
                )
                if self.debug:
                    print(
                        f"[DEBUG] Correlations group={g_name}, metric={metric}, "
                        f"pearson={pearson_val}, spearman={spearman_val}"
                    )

        return corr_table_pearson, corr_table_spearman, crt_table, model_df
        
    def get_cluster_sizes(self, mat: pd.DataFrame, k: int):
        """クラスターサイズを取得"""
        cluster_sizes = {}
        for i in range(k):
            cluster_sizes[i] = len(mat[mat["cluster"] == i])
        return cluster_sizes
        
    def analyze_case(
        self,
        label: str,
        df_subset: pd.DataFrame,
        prefix: str,
        cs_th: float,
        ucs_th: float,
        default_cond_value=None,
    ):
        """個別ケースの分析"""
        if df_subset.empty:
            return None, None, None, None, None

        mat, k, labels = self.create_cluster_data(df_subset, prefix)
        if mat is None:
            return None, None, None, None, None
        corr_table_pearson, corr_table_spearman, crt_table, model_df = self.calculate_correlations(
            df_subset,
            mat,
            k,
            prefix,
            cs_th,
            ucs_th,
            default_cond_value=default_cond_value,
        )
        cluster_sizes = self.get_cluster_sizes(mat, k)

        return corr_table_pearson, corr_table_spearman, crt_table, cluster_sizes, model_df
        
    def run_threshold_analysis(self, thresholds=None):
        """threshold値を変えながら分析実行（CSとUCSは同じ値）"""
        if thresholds is None:
            thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)]
            
        self.load_data()
          # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]
        
        all_results = []
        
        # threshold 値で実行（CSとUCSは同じ値）
        for th in thresholds:
            print(f"\n=== CS threshold = {th:.1f}, UCS threshold = {th:.1f} ===")
            
            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue
                    
                default_cond_value = self._infer_cond_value_from_label(label)
                (
                    corr_table_pearson,
                    corr_table_spearman,
                    crt_table,
                    cluster_sizes,
                    model_df,
                ) = self.analyze_case(
                    label,
                    df_sub,
                    prefix,
                    th,
                    th,
                    default_cond_value=default_cond_value,
                )

                if corr_table_pearson is None or corr_table_spearman is None:
                    continue

                # 結果をDataFrameに変換
                for cluster_name in corr_table_pearson.index:
                    if cluster_name == "All":
                        continue
                        
                    # 実験タイプと条件を抽出
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
                        "n": cluster_sizes.get(cluster_index, 0),  # 6で割った値を表示
                        "CRT_mean": crt_table.loc[cluster_name, "CRT_mean"],
                        "estimate_mean": crt_table.loc[cluster_name, "estimate_mean"],
                    }

                    for metric_name in model_df.columns:
                        pearson_key = f"{metric_name}_pearson"
                        spearman_key = f"{metric_name}_spearman"
                        result_row[pearson_key] = corr_table_pearson.loc[cluster_name, metric_name]
                        result_row[spearman_key] = corr_table_spearman.loc[cluster_name, metric_name]

                    if self.debug:
                        print(f"[DEBUG] Result row ({label}, {cluster_name}): {result_row}")

                    all_results.append(result_row)

        # 結果をDataFrameに変換して保存
        results_df = pd.DataFrame(all_results)

        # CSVファイルに保存
        filename = "extended_correlation_results_with_additional_metrics.csv"
        results_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n→ 結果を保存: {filename}")
          # プレビュー表示
        print(f"\n=== 結果プレビュー ===")
        print(f"総行数: {len(results_df)}")
        print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
        print(f"\n先頭5行:")
        print(results_df.head().to_string(index=False))

        cond_metric_cols = [
            f"{metric}_{suffix}"
            for metric in CONDITION_DEPENDENT_METRICS
            for suffix in ("pearson", "spearman")
        ]
        if not results_df.empty:
            print("\n=== 条件別新規指標サマリー ===")
            sym_mask = results_df["条件"] == "対称否定"
            asym_mask = results_df["条件"] == "非対称否定"
            if sym_mask.any():
                sample_vals = results_df.loc[sym_mask, cond_metric_cols].head(1).iloc[0]
                formatted_sample = {
                    col: (np.nan if pd.isna(val) else round(float(val), 3))
                    for col, val in sample_vals.items()
                }
                print("対称条件サンプル (初回行):", formatted_sample)
            else:
                print("対称条件の結果がありません。")

            if asym_mask.any():
                nan_ratios = (
                    results_df.loc[asym_mask, cond_metric_cols].isna().mean().fillna(0.0) * 100
                )
                formatted_nan = {
                    col: round(float(val), 1) for col, val in nan_ratios.to_dict().items()
                }
                print("非対称条件のNaN率(%)", formatted_nan)
            else:
                print("非対称条件の結果がありません。")

        return results_df
    
    def calculate_sample_averages(self):
        """4条件下でのsample_numberごとに12個のストーリー(ex1_cover_story, ex2_cover_story)での平均回答値を計算"""
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_オンライン", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("対称否定_オンライン", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("非対称否定_オンライン２", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("対称否定_オンライン２", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]
        
        all_sample_averages = []
        
        for condition_name, df_subset, prefix in conditions:
            if df_subset.empty:
                continue
                
            est_col = f"{prefix}_estimate"
            num_col = f"{prefix}_sample_number"
            cover_story_col = f"{prefix}_cover_story"
            
            # 全ての組み合わせを作成（sample_number: 1-6, cover_story: 1-12）
            all_combinations = []
            for sample_num in range(1, 7):  # 1-6
                for story_num in range(1, 13):  # 1-12
                    subset_data = df_subset[(df_subset[num_col] == sample_num) & (df_subset[cover_story_col] == story_num)]
                    
                    if len(subset_data) > 0:
                        mean_val = subset_data[est_col].mean()
                        std_val = subset_data[est_col].std()
                        count_val = len(subset_data)
                    else:
                        mean_val = 0.0
                        std_val = 0.0
                        count_val = 0
                    
                    all_combinations.append({
                        'sample_number': sample_num,
                        'cover_story': story_num,
                        'mean_estimate': round(mean_val, 3),
                        'std_estimate': round(std_val, 3) if pd.notna(std_val) else 0.0,
                        'count': count_val,
                        'condition': condition_name
                    })
            
            sample_averages = pd.DataFrame(all_combinations)
            all_sample_averages.append(sample_averages)
          # 全条件の結果を結合
        if all_sample_averages:
            combined_averages = pd.concat(all_sample_averages, ignore_index=True)
            
            # 条件、sample_number、cover_storyでソート
            combined_averages = combined_averages.sort_values(['condition', 'sample_number', 'cover_story'])
            
            # CSVファイルに保存
            filename = "sample_story_averages_by_condition.csv"
            combined_averages.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"→ sample_numberとcover_storyごとの平均回答値を保存: {filename}")
            
            # ピボットテーブル形式でも保存（sample_number × condition × cover_story）
            # まず、条件とcover_storyを組み合わせた新しいカラムを作成
            combined_averages['condition_story'] = combined_averages['condition'] + '_story' + combined_averages['cover_story'].astype(str)
            
            pivot_table = combined_averages.pivot(index='sample_number', 
                                                 columns='condition_story', 
                                                 values='mean_estimate')
            pivot_filename = "sample_story_averages_pivot.csv"
            pivot_table.to_csv(pivot_filename, encoding="utf-8-sig")
            print(f"→ ピボットテーブル形式でも保存: {pivot_filename}")
            
            # 条件別の平均（cover_storyをまとめた）も計算
            condition_averages = combined_averages.groupby(['condition', 'sample_number'])['mean_estimate'].mean().reset_index()
            condition_pivot = condition_averages.pivot(index='sample_number', 
                                                      columns='condition', 
                                                      values='mean_estimate')
            condition_filename = "sample_condition_averages_pivot.csv"
            condition_pivot.to_csv(condition_filename, encoding="utf-8-sig")
            print(f"→ 条件別平均ピボットテーブルも保存: {condition_filename}")
            
            # プレビュー表示
            print(f"\n=== sample_numberとcover_storyごとの平均回答値プレビュー ===")
            print(combined_averages.head(20).to_string(index=False))
            print(f"\n=== 条件別平均ピボットテーブルプレビュー ===")
            print(condition_pivot.to_string())
            
            return combined_averages
        
    def create_crt_cluster_histograms(self, thresholds=None):
        """繧ｯ繝ｩ繧ｹ繧ｿ縺斐→縺ｮCRT逕溘ョ繝ｼ繧ｿ繝偵せ繝医げ繝ｩ繝繧剃ｽ懈・"""
        if thresholds is None:
            # デフォルトは threshold = 1.0
            thresholds = [1.0]

        self.load_data()

        # データを分岐
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()

        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]

        for th in thresholds:
            print(f"\n=== threshold = {th:.1f} 縺ｧ縺ｮCRT繧ｯ繝ｩ繧ｹ繧ｿ繝ｼ繝偵せ繝医げ繝ｩ繝菴懈・ ===")

            valid_cases = []
            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue

                if "ex1" in label:
                    experiment_type = "繧ｵ繝槭Μ繝ｼ"
                elif "ex2" in label:
                    experiment_type = "繧ｪ繝ｳ繝ｩ繧､繝ｳ"
                else:
                    continue
                if "Cond0" in label:
                    condition = "髱槫ｯｾ遘ｰ蜷ｦ螳・"
                elif "Cond1" in label:
                    condition = "蟇ｾ遘ｰ蜷ｦ螳・"
                else:
                    continue

                condition_name = f"{condition}_{experiment_type}"
                default_cond_value = self._infer_cond_value_from_label(label)

                (
                    corr_table_pearson,
                    corr_table_spearman,
                    crt_table,
                    cluster_sizes,
                    model_df,
                ) = self.analyze_case(
                    label,
                    df_sub,
                    prefix,
                    th,
                    th,
                    default_cond_value=default_cond_value,
                )
                if corr_table_pearson is None or corr_table_spearman is None:
                    print(f"対象: {condition_name}")
                    print("  -> 解析に必要なデータが不足しているためスキップ")
                    continue

                valid_cases.append(
                    {
                        "condition_name": condition_name,
                        "df_subset": df_sub,
                        "prefix": prefix,
                        "model_df": model_df,
                        "threshold": th,
                    }
                )

            if not valid_cases:
                continue

            axis_limits = self._determine_scatter_axis_limits(valid_cases)

            for case in valid_cases:
                condition_name = case["condition_name"]
                df_subset = case["df_subset"]
                prefix = case["prefix"]
                model_df = case["model_df"]
                print(f"対象: {condition_name}")

                mat, k, labels = self.create_cluster_data(df_subset, prefix)
                if mat is None:
                    print(f"  -> {condition_name}: クラスターデータが不足しているためスキップ")
                    continue

                self._plot_crt_cluster_histogram(condition_name, df_subset, mat, k, prefix, th)
                self._plot_cs_ucs_scatter(
                    condition_name,
                    df_subset,
                    prefix,
                    model_df,
                    th,
                    axis_limits=axis_limits,
                )

    def _plot_crt_cluster_histogram(self, condition_name: str, df_subset: pd.DataFrame, 
                                   mat: pd.DataFrame, k: int, prefix: str, threshold: float):
        """個別条件のクラスター別CRTヒストグラム作成"""
        
        # CRTデータがない場合はスキップ
        if 'crt_correct_cnt' not in df_subset.columns:
            print(f"  -> {condition_name}: CRTデータなし")
            return
        
        # 図の設定 (クラスター数に応じて調整)
        fig, axes = plt.subplots(1, k, figsize=(4*k, 6))
        if k == 1:
            axes = [axes]
        
        colors = ['lightblue', 'lightcoral', 'lightgreen', 'lightyellow', 'lightgray']
        
        for cluster_idx in range(k):
            ax = axes[cluster_idx]
            
            # このクラスターに属するユーザーIDを取得
            cluster_users = mat[mat["cluster"] == cluster_idx].index
            # このクラスターのユーザーのCRTデータを取得 (ユニークなuser_idごとに一度だけ)
            cluster_df = df_subset[df_subset["user_id"].isin(cluster_users)]
            unique_crt_data = cluster_df.drop_duplicates(subset="user_id")['crt_correct_cnt'].dropna()
            
            if len(unique_crt_data) == 0:
                ax.text(0.5, 0.5, 'No CRT Data', transform=ax.transAxes, 
                        ha='center', va='center', fontsize=12)
                ax.set_title(f'クラスタ{cluster_idx+1}\n(n=0)', fontsize=12, fontweight='bold')
                continue
            
            # ヒストグラムを描画（CRTは0-3の整数値）
            bins = np.arange(-0.5, 4.5, 1)
            counts, _, patches = ax.hist(unique_crt_data, bins=bins, alpha=0.7, 
                                           edgecolor='black', color=colors[cluster_idx % len(colors)])
            # バーの上に人数を表示
            for i, count in enumerate(counts):
                if count > 0:
                    ax.text(i, count + 0.05, f'{int(count)}', ha='center', va='bottom', fontsize=10)
            
            # 統計情報を計算
            mean_crt = unique_crt_data.mean()
            std_crt = unique_crt_data.std()
            
            # タイトルと軸ラベル設定
            ax.set_title(f'クラスタ{cluster_idx+1}\n(n={len(unique_crt_data)}, 平均={mean_crt:.2f})', 
                         fontsize=12, fontweight='bold')
            ax.set_xlabel('CRTスコア（正答数）', fontsize=10)
            ax.set_ylabel('人数', fontsize=10)
            
            # x軸の目盛りを整数に設定
            ax.set_xticks([0, 1, 2, 3])
            ax.set_xlim(-0.5, 3.5)
            
            # y軸の最大値を設定（全クラスターで統一）
            max_count = max([max(df_subset[df_subset["user_id"].isin(
                mat[mat["cluster"] == i].index)].drop_duplicates(subset='user_id')['crt_correct_cnt']
                .dropna().value_counts().values, default=0) for i in range(k)], default=1)
            ax.set_ylim(0, max_count * 1.2)
            
            ax.grid(True, alpha=0.3)
        
        # 全体のタイトル
        fig.suptitle(f'CRTスコア分布（クラスター別）- {condition_name}', 
                    fontsize=14, fontweight='bold')
        
        # ファイル名を作成して保存
        filename = f"crt_cluster_histogram_{condition_name}_th{threshold:.1f}.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"  -> CRTクラスターヒストグラム保存: {filename}")
        plt.close()  # メモリ節約のためクローズ
        

    def _determine_scatter_axis_limits(self, cases):
        """条件ごとの散布図で共通の軸範囲を計算する"""
        if not cases:
            return None

        x_min = np.inf
        x_max = -np.inf
        y_bounds = {"CS": [np.inf, -np.inf], "UCS": [np.inf, -np.inf]}

        for case in cases:
            df_subset = case["df_subset"]
            prefix = case["prefix"]
            model_df = case["model_df"]

            est_col = f"{prefix}_estimate"
            if est_col in df_subset.columns:
                estimates = pd.to_numeric(df_subset[est_col], errors="coerce").dropna()
                if not estimates.empty:
                    x_min = min(x_min, float(estimates.min()))
                    x_max = max(x_max, float(estimates.max()))

            for metric in ("CS", "UCS"):
                if metric in model_df.columns:
                    series = (
                        pd.to_numeric(model_df[metric], errors="coerce")
                        .replace([np.inf, -np.inf], np.nan)
                        .dropna()
                    )
                    if not series.empty:
                        y_bounds[metric][0] = min(y_bounds[metric][0], float(series.min()))
                        y_bounds[metric][1] = max(y_bounds[metric][1], float(series.max()))

        axis_limits = {}

        if np.isfinite(x_min) and np.isfinite(x_max):
            if x_min == x_max:
                pad = max(1.0, abs(x_min) * 0.1)
            else:
                pad = max(1.0, (x_max - x_min) * 0.05)
            axis_limits["x"] = (x_min - pad, x_max + pad)
        else:
            axis_limits["x"] = (-100.0, 100.0)

        y_limits = {}
        for metric, (y_min, y_max) in y_bounds.items():
            if np.isfinite(y_min) and np.isfinite(y_max):
                if y_min == y_max:
                    pad = max(0.5, abs(y_min) * 0.1)
                else:
                    pad = max(0.5, (y_max - y_min) * 0.05)
                y_limits[metric] = (y_min - pad, y_max + pad)
            else:
                y_limits[metric] = (-2.5, 5.0)

        axis_limits["y"] = y_limits
        return axis_limits

    def _plot_cs_ucs_scatter(
        self,
        condition_name: str,
        df_subset: pd.DataFrame,
        prefix: str,
        model_df: pd.DataFrame,
        threshold: float,
        axis_limits=None,
    ):
        """譚｡莉ｶ蛻･縺ｫCS/UCS縺ｨ隧募ｮ壹・謨｣蟶・峙繧呈緒逕ｻ縺吶ｋ（逕ｻ蜒城↓豢ｻ譖ｿ）"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        required_cols = {est_col, num_col}
        if not required_cols.issubset(df_subset.columns):
            if self.debug:
                missing = sorted(required_cols.difference(set(df_subset.columns)))
                print(f"[DEBUG] CS/UCS謨｣蟶・峙繧偵せ繧ｭ繝・・ ({condition_name}): 谺謳榊・={missing}")
            return
        if "CS" not in model_df.columns or "UCS" not in model_df.columns:
            if self.debug:
                print(
                    f"[DEBUG] 繝｢繝・Ν謖・ｨ吶↓CS/UCS蛻励′蟄伜惠縺励↑縺・◆繧∵淵蟶・峙繧剃ｽ懈・縺ｧ縺阪∪縺帙ｓ ({condition_name})"
                )
            return

        subset = df_subset.dropna(subset=[est_col, num_col])
        if subset.empty:
            print(f"  -> {condition_name}: 隧募ｮ壹ョ繝ｼ繧ｿ縺ｪ縺・")
            return

        sample_estimates = subset.groupby(num_col)[est_col].mean()
        sample_counts = subset.groupby(num_col)[est_col].count()
        scatter_df = pd.DataFrame(
            {
                "estimate_mean": sample_estimates,
                "count": sample_counts,
            }
        ).join(model_df[["CS_diff", "UCS_diff"]], how="inner")
        scatter_df = scatter_df.dropna(subset=["estimate_mean", "CS_diff", "UCS_diff"])
        if scatter_df.empty:
            print(f"  -> {condition_name}: CS/UCS謨｣蟶・峙縺ｫ蠢・ｦ√↑繝・・繧ｿ縺御ｸ崎ｶｳ")
            return
        scatter_df = scatter_df.sort_index()

        def _auto_limits(values, fallback, min_padding):
            finite_values = np.asarray(values, dtype=float)
            finite_values = finite_values[np.isfinite(finite_values)]
            if finite_values.size == 0:
                return fallback
            v_min = float(finite_values.min())
            v_max = float(finite_values.max())
            if v_min == v_max:
                pad = max(min_padding, abs(v_min) * 0.1)
            else:
                pad = max(min_padding, (v_max - v_min) * 0.05)
            return (v_min - pad, v_max + pad)

        supplied_x_limits = axis_limits.get("x") if axis_limits else None
        supplied_y_limits = axis_limits.get("y") if axis_limits else {}

        x_limits = supplied_x_limits or _auto_limits(
            scatter_df["estimate_mean"].values, (-100.0, 100.0), 1.0
        )

        fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharex=True)
        axes = np.atleast_1d(axes)
        metrics = [("CS", "CS"), ("UCS", "UCS")]
        for ax, (metric_key, label) in zip(axes, metrics):
            x = scatter_df["estimate_mean"].values
            y = scatter_df[metric_key].values
            sizes = 30 + scatter_df["count"].astype(float).values * 8
            ax.scatter(x, y, s=sizes, alpha=0.7, edgecolors="black", linewidth=0.5)
            for sample_num, x_val, y_val in zip(scatter_df.index, x, y):
                ax.annotate(
                    str(sample_num),
                    (x_val, y_val),
                    textcoords="offset points",
                    xytext=(5, 5),
                    fontsize=9,
                )
            ax.set_title(f"{label}縺ｨ隧募ｮ・", fontsize=12)
            ax.set_xlabel("隧募ｮ壼､")
            ax.set_ylabel(f"{label}蛟､")
            ax.grid(True, alpha=0.3)

            y_limits = supplied_y_limits.get(metric_key)
            if y_limits is None:
                y_limits = _auto_limits(y, (-2.5, 5.0), 0.5)
            ax.set_xlim(x_limits)
            ax.set_ylim(y_limits)

        fig.suptitle(
            f"CS/UCS謨｣蟶・峙 - {condition_name} (髢ｾ蛟､ {threshold:.1f})",
            fontsize=14,
            fontweight="bold",
        )
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        safe_condition_name = "".join("_" if c in {"/", "\\", " "} else c for c in condition_name)
        filename = f"cs_ucs_scatter_{safe_condition_name}_th{threshold:.1f}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"  -> CS/UCS謨｣蟶・峙繧剃ｿ晏ｭ・ {filename}")
        plt.close(fig)

    def create_crt_cluster_summary_table(self, thresholds=None):
        """クラスタごとのCRT要約統計量テーブルを作成"""
        if thresholds is None:
            thresholds = [1.0]
        
        self.load_data()
        
        all_summary_data = []
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]
        
        for th in thresholds:
            print(f"\n=== threshold = {th:.1f} でのCRT要約統計量計算 ===")
            
            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue
                    
                # 実験タイプと条件を抽出
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
                
                condition_name = f"{condition}_{experiment_type}"
                
                # クラスタリング実行
                default_cond_value = self._infer_cond_value_from_label(label)
                (
                    corr_table_pearson,
                    corr_table_spearman,
                    crt_table,
                    cluster_sizes,
                    model_df,
                ) = self.analyze_case(
                    label,
                    df_sub,
                    prefix,
                    th,
                    th,
                    default_cond_value=default_cond_value,
                )

                if corr_table_pearson is None or corr_table_spearman is None:
                    continue
                
                # クラスタリング結果を取得
                mat, k, labels = self.create_cluster_data(df_sub, prefix)
                if mat is None:
                    continue
                
                # 各クラスターの統計量を計算
                for cluster_idx in range(k):
                    cluster_users = mat[mat["cluster"] == cluster_idx].index
                    cluster_df = df_sub[df_sub["user_id"].isin(cluster_users)]
                    crt_data = cluster_df['crt_correct_cnt'].dropna()
                    
                    if len(crt_data) > 0:
                        # スコア別の人数を計算
                        score_counts = crt_data.value_counts().sort_index()
                        
                        summary_row = {
                            'threshold': th,
                            '実験タイプ': experiment_type,
                            '条件': condition,
                            'クラスタ': f'クラスタ{cluster_idx+1}',
                            'n': len(crt_data),
                            'CRT平均': round(crt_data.mean(), 3),
                            'CRT標準偏差': round(crt_data.std(), 3),
                            'CRT最小値': int(crt_data.min()),
                            'CRT中央値': round(crt_data.median(), 3),
                            'CRT最大値': int(crt_data.max()),
                            'スコア0': score_counts.get(0, 0),
                            'スコア1': score_counts.get(1, 0),
                            'スコア2': score_counts.get(2, 0),
                            'スコア3': score_counts.get(3, 0),
                            'スコア0_%': round((score_counts.get(0, 0) / len(crt_data)) * 100, 1),
                            'スコア1_%': round((score_counts.get(1, 0) / len(crt_data)) * 100, 1),
                            'スコア2_%': round((score_counts.get(2, 0) / len(crt_data)) * 100, 1),
                            'スコア3_%': round((score_counts.get(3, 0) / len(crt_data)) * 100, 1),
                        }
                        
                        all_summary_data.append(summary_row)
        
        if all_summary_data:
            # DataFrameに変換
            summary_df = pd.DataFrame(all_summary_data)
            
            # CSVファイルに保存
            filename = "crt_cluster_summary_statistics.csv"
            summary_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n→ CRTクラスター要約統計量テーブル保存: {filename}")
            
            # プレビュー表示
            print(f"\n=== CRTクラスター要約統計量テーブル プレビュー ===")
            print(summary_df.head(20).to_string(index=False))
            
            return summary_df
        else:
            print("CRTクラスター要約統計量の計算でデータが見つかりませんでした")
            return None


if __name__ == "__main__":
    # CS と UCS の threshold 値を0.1刻みで設定（同じ値）
    thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]
    
    print("=== 拡張相関分析 ===")
    print(f"threshold値: {thresholds}")
    print(f"総パターン数: {len(thresholds)}")
    print("=" * 50)
    analyzer = CorrelationAnalyzer("final_valid_6_samples.csv", max_k=5, debug=True)

    print("\n=== デバッグ: 条件依存指標テスト ===")
    test_counts = (8, 2, 3, 7)
    metrics_sym = analyzer.metrics_from_abcd(
        *test_counts,
        cs_th=1.0,
        ucs_th=1.0,
        is_gene=True,
        cond_value=1,
    )
    metrics_asym = analyzer.metrics_from_abcd(
        *test_counts,
        cs_th=1.0,
        ucs_th=1.0,
        is_gene=True,
        cond_value=0,
    )
    sym_map = dict(zip(MODEL_METRIC_COLUMNS, metrics_sym))
    asym_map = dict(zip(MODEL_METRIC_COLUMNS, metrics_asym))
    condition_metrics_sym = {metric: sym_map[metric] for metric in CONDITION_DEPENDENT_METRICS}
    condition_metrics_asym = {metric: asym_map[metric] for metric in CONDITION_DEPENDENT_METRICS}
    nan_verification = {metric: pd.isna(condition_metrics_asym[metric]) for metric in CONDITION_DEPENDENT_METRICS}
    print("[DEBUG] cond=1 指標値:", condition_metrics_sym)
    print("[DEBUG] cond=0 指標値 (期待: NaN):", condition_metrics_asym)
    print("[DEBUG] cond=0 NaN検証:", nan_verification)

    print("\n=== デバッグ: 相関計算テスト ===")
    x_debug = np.array([0.1, 0.2, 0.4, 0.8])
    y_debug = np.array([0.15, 0.27, 0.36, 0.82])
    print(f"[DEBUG] テストPearson: {analyzer.safe_corr(x_debug, y_debug)}")
    print(f"[DEBUG] テストSpearman: {analyzer.safe_spearman_corr(x_debug, y_debug)}")

    # sample_numberごとの平均回答値を計算
    print("\n=== sample_numberとcover_storyごとの平均回答値計算 ===")
    analyzer.load_data()  # データを読み込み
    sample_averages = analyzer.calculate_sample_averages()
    
    # CRTクラスターヒストグラムを作成（threshold = 1.0 のみ）
    print("\n=== CRTクラスターヒストグラム作成 ===")
    analyzer.create_crt_cluster_histograms([1.0])
    
    # CRTクラスター要約統計量テーブル作成
    print("\n=== CRTクラスター要約統計量テーブル作成 ===")
    crt_cluster_summary = analyzer.create_crt_cluster_summary_table([1.0])
    
    # threshold分析を実行
    print("\n=== threshold分析開始 ===")
    results = analyzer.run_threshold_analysis(thresholds)
    
    print("\n=== 分析完了 ===")
