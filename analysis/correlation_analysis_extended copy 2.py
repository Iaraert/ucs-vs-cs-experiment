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
    def __init__(self, csv_path: str, debug: bool = False):
        self.csv_path = csv_path
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
            cs_ab = self._safe_score(CS, (a, b, 0, 0), cs_th, is_gene, "CS_ab")
            cs_cd = self._safe_score(CS, (c, d, 0, 0), cs_th, is_gene, "CS_cd")
            ucs_ab = self._safe_score(UCS, (a, b, 0, 0), ucs_th, is_gene, "UCS_ab")
            ucs_cd = self._safe_score(UCS, (c, d, 0, 0), ucs_th, is_gene, "UCS_cd")

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
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
    
        mat = df_subset.pivot(index="user_id", columns=num_col, values=est_col).dropna()
        if mat.empty:
            return None
    
        return mat
    
    def calculate_correlations(
        self,
        df_subset: pd.DataFrame,
        prefix: str,
        cs_th: float,
        ucs_th: float,
        default_cond_value=None,
    ):
        """?????"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
    
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
    
        y = df_subset.groupby(num_col)[est_col].mean().reindex(model_df.index).values
    
        corr_table_pearson = pd.DataFrame(index=["All"], columns=metric_columns, dtype=float)
        corr_table_spearman = pd.DataFrame(index=["All"], columns=metric_columns, dtype=float)
        crt_table = pd.DataFrame(index=["All"], columns=["CRT_mean", "estimate_mean"])
    
        crt_mean = np.nan
        if len(df_subset) > 0 and "crt_correct_cnt" in df_subset.columns:
            crt_mean = df_subset["crt_correct_cnt"].mean()
        crt_table.loc["All", "CRT_mean"] = round(crt_mean, 3) if pd.notna(crt_mean) else np.nan
    
        estimate_mean = df_subset[est_col].mean() if len(df_subset) > 0 else np.nan
        crt_table.loc["All", "estimate_mean"] = (
            round(estimate_mean, 3) if pd.notna(estimate_mean) else np.nan
        )
    
        for metric in metric_columns:
            x = model_df[metric].values
            pearson_val = self.safe_corr(x, y)
            spearman_val = self.safe_spearman_corr(x, y)
            corr_table_pearson.loc["All", metric] = (
                np.nan if np.isnan(pearson_val) else round(float(pearson_val), 3)
            )
            corr_table_spearman.loc["All", metric] = (
                np.nan if np.isnan(spearman_val) else round(float(spearman_val), 3)
            )
            if self.debug:
                print(
                    f"[DEBUG] Correlations group=All, metric={metric}, "
                    f"pearson={pearson_val}, spearman={spearman_val}"
                )
    
        return corr_table_pearson, corr_table_spearman, crt_table, model_df
    
    def analyze_case(
        self,
        label: str,
        df_subset: pd.DataFrame,
        prefix: str,
        cs_th: float,
        ucs_th: float,
        default_cond_value=None,
    ):
        """????????"""
        if df_subset.empty:
            return None, None, None, None
    
        mat = self.create_cluster_data(df_subset, prefix)
        if mat is None:
            return None, None, None, None
    
        return self.calculate_correlations(
            df_subset,
            prefix,
            cs_th,
            ucs_th,
            default_cond_value=default_cond_value,
        )
    
    
    
    
    
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
            print()
            print(f"=== CS threshold = {th:.1f}, UCS threshold = {th:.1f} ===")
    
            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue
    
                default_cond_value = self._infer_cond_value_from_label(label)
                (
                    corr_table_pearson,
                    corr_table_spearman,
                    crt_table,
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
    
                if "All" not in corr_table_pearson.index:
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
    
                result_row = {
                    "CS_threshold": th,
                    "UCS_threshold": th,
                    "実験タイプ": experiment_type,
                    "条件": condition,
                    "CRT_mean": crt_table.loc["All", "CRT_mean"],
                    "estimate_mean": crt_table.loc["All", "estimate_mean"],
                }
    
                for metric_name in model_df.columns:
                    pearson_key = f"{metric_name}_pearson"
                    spearman_key = f"{metric_name}_spearman"
                    result_row[pearson_key] = corr_table_pearson.loc["All", metric_name]
                    result_row[spearman_key] = corr_table_spearman.loc["All", metric_name]
    
                if self.debug:
                    print(f"[DEBUG] Result row ({label}): {result_row}")
    
                all_results.append(result_row)
    
        results_df = pd.DataFrame(all_results)
    
        if not results_df.empty:
            filename = "extended_correlation_results_with_additional_metrics.csv"
            results_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print()
            print(f"→ 結果を保存: {filename}")
            print()
            print("=== 結果プレビュー ===")
            print(f"総行数: {len(results_df)}")
            print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
            print()
            print("先頭5行:")
            print(results_df.head().to_string(index=False))
        else:
            print("結果が得られませんでした。条件とthresholdを確認してください。")
    
        cond_metric_cols = [
            f"{metric}_{suffix}"
            for metric in CONDITION_DEPENDENT_METRICS
            for suffix in ("pearson", "spearman")
        ]
        if not results_df.empty:
            print()
            print("=== 条件別新規指標サマリー ===")
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
                print("非対称条件のNaN率(%):", formatted_nan)
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
        else:
            print("データが見つかりませんでした。")
            return pd.DataFrame()


if __name__ == "__main__":
    # CS と UCS の threshold 値を0.1刻みで設定（同じ値）
    thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]
    
    print("=== 拡張相関分析 ===")
    print(f"threshold値: {thresholds}")
    print(f"総パターン数: {len(thresholds)}")
    print("=" * 50)
    analyzer = CorrelationAnalyzer("final_valid_6_samples.csv", debug=True)

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

    # threshold分析を実行
    print("\n=== threshold分析開始 ===")
    results = analyzer.run_threshold_analysis(thresholds)
    
    print("\n=== 分析完了 ===")
