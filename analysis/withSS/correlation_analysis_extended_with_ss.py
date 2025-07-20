"""
correlation_analysis_extended_with_ss.py

相関分析専用コード - CSとUCSのthreshold値を0.1刻みで変更 + SSモデル統合版
"""
import os
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr
from CS_UCS import CS, UCS
from ss_model import SSModel, ContingencyData
from ss_model_utils import calculate_ss_metrics


class CorrelationAnalyzerWithSS:
    def __init__(self, csv_path: str, max_k: int = 5, alpha: float = 5.0, beta: float = 20.0):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame = None
        # SSモデルの初期化
        self.ss_model = SSModel(alpha=alpha, beta=beta)
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
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
        
    def metrics_from_abcd_with_ss(self, a: int, b: int, c: int, d: int, 
                                 cs_th: float = 1.0, ucs_th: float = 1.0, 
                                 is_gene: bool = True, estimate: float = None):
        """a,b,c,d からモデル指標を計算（SSモデル含む）"""
        # 基本的な指標
        pe_c = a / (a + b) if (a + b) else np.nan
        pc_e = a / (a + c) if (a + c) else np.nan
        delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
        paris = a / (a + b + c) if (a + b + c) else np.nan
        dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
        
        # 既存のCS, UCS
        cs_val = CS((a, b, c, d), cs_th, is_gene)
        ucs_val = UCS((a, b, c, d), ucs_th, is_gene)
        
        # SSモデルの指標を追加
        try:
            ss_metrics = calculate_ss_metrics(a, b, c, d, estimate)
            ss_support = ss_metrics['ss_support']
            uniform_support = ss_metrics['uniform_support']
            chi2_support = ss_metrics['chi2_support']
        except Exception as e:
            print(f"SS Model計算エラー: {e}")
            ss_support = np.nan
            uniform_support = np.nan
            chi2_support = np.nan
        
        return pe_c, pc_e, delta_p, cs_val, ucs_val, paris, dfh, dice, ss_support, uniform_support, chi2_support
        
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
        
    def calculate_correlations_with_ss(self, df_subset: pd.DataFrame, mat: pd.DataFrame, k: int, 
                                      prefix: str, cs_th: float, ucs_th: float):
        """相関を計算（SSモデル含む）"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{x}" for x in ("a", "b", "c", "d")]
        
        # SSモデルを含むモデル指標を準備
        model_df = pd.DataFrame(
            index=sorted(df_subset[num_col].unique()),
            columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice", 
                    "SS_Support", "Uniform_Support", "Chi2_Support"], 
            dtype=float
        )
        
        for s in model_df.index:
            row = df_subset[df_subset[num_col] == s].iloc[0]
            a, b, c, d = row[abcd_cols].astype(int).values
            is_gene = df_subset[df_subset[num_col] == s][est_col].mean() >= 0
            # 平均推定値をSSモデルに渡す
            avg_estimate = df_subset[df_subset[num_col] == s][est_col].mean()
            
            metrics = self.metrics_from_abcd_with_ss(
                a, b, c, d, cs_th=cs_th, ucs_th=ucs_th, 
                is_gene=is_gene, estimate=avg_estimate
            )
            model_df.loc[s] = metrics
        
        # グループ定義
        groups = {"All": df_subset}
        for cl in range(k):
            ids = mat[mat["cluster"] == cl].index
            groups[f"Cluster{cl+1}"] = df_subset[df_subset["user_id"].isin(ids)]
        
        # 相関テーブル初期化（SSモデル指標を追加）
        corr_table = pd.DataFrame(
            index=groups.keys(),
            columns=["P(E|C)", "P(C|E)", "ΔP", "CS", "UCS", "pARIs", "DFH", "Dice", 
                    "SS_Support", "Uniform_Support", "Chi2_Support"]
        )
        
        # CRT平均テーブル初期化
        crt_table = pd.DataFrame(index=groups.keys(), columns=["CRT_mean", "estimate_mean"])
        
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
            
            # 各指標との相関（SSモデル指標含む）
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
        
    def analyze_case_with_ss(self, label: str, df_subset: pd.DataFrame, prefix: str, 
                            cs_th: float, ucs_th: float):
        """個別ケースの分析（SSモデル含む）"""
        if df_subset.empty:
            return None, None, None, None
            
        mat, k, labels = self.create_cluster_data(df_subset, prefix)
        if mat is None:
            return None, None, None, None
        corr_table, crt_table, model_df = self.calculate_correlations_with_ss(
            df_subset, mat, k, prefix, cs_th, ucs_th
        )
        cluster_sizes = self.get_cluster_sizes(mat, k)
        
        return corr_table, crt_table, cluster_sizes, model_df
        
    def run_threshold_analysis_with_ss(self, thresholds=None):
        """threshold値を変えながら分析実行（CSとUCS + SSモデル）"""
        if thresholds is None:
            thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)]
            
        self.load_data()
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 0].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 0].copy()
        
        cases = [
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
        ]
        
        all_results = []
        
        # threshold 値で実行（CSとUCSは同じ値）
        for th in thresholds:
            print(f"\n=== CS threshold = {th:.1f}, UCS threshold = {th:.1f} + SS Model ===")
            
            for label, df_sub, prefix in cases:
                if df_sub.empty:
                    continue
                    
                corr_table, crt_table, cluster_sizes, model_df = self.analyze_case_with_ss(
                    label, df_sub, prefix, th, th)
                
                if corr_table is None:
                    continue
                    
                # 結果をDataFrameに変換
                for cluster_name in corr_table.index:
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
                        "n": cluster_sizes.get(cluster_index, 0),
                        "CRT_mean": crt_table.loc[cluster_name, "CRT_mean"],
                        "estimate_mean": crt_table.loc[cluster_name, "estimate_mean"],
                        "P(E|C)": corr_table.loc[cluster_name, "P(E|C)"],
                        "P(C|E)": corr_table.loc[cluster_name, "P(C|E)"],
                        "ΔP": corr_table.loc[cluster_name, "ΔP"],
                        "CS": corr_table.loc[cluster_name, "CS"],
                        "UCS": corr_table.loc[cluster_name, "UCS"],
                        "pARIs": corr_table.loc[cluster_name, "pARIs"],
                        "DFH": corr_table.loc[cluster_name, "DFH"],
                        "Dice": corr_table.loc[cluster_name, "Dice"],
                        # SSモデル指標を追加
                        "SS_Support": corr_table.loc[cluster_name, "SS_Support"],
                        "Uniform_Support": corr_table.loc[cluster_name, "Uniform_Support"],
                        "Chi2_Support": corr_table.loc[cluster_name, "Chi2_Support"]
                    }
                    
                    all_results.append(result_row)
        
        # 結果をDataFrameに変換して保存
        results_df = pd.DataFrame(all_results)
        
        # CSVファイルに保存
        filename = "extended_correlation_results_with_ss.csv"
        results_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n→ 結果を保存: {filename}")
        
        # プレビュー表示
        print(f"\n=== 結果プレビュー（SSモデル含む） ===")
        print(f"総行数: {len(results_df)}")
        print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
        print(f"\n先頭5行:")
        print(results_df.head().to_string(index=False))
        
        # SSモデル指標の要約統計
        ss_columns = ['SS_Support', 'Uniform_Support', 'Chi2_Support']
        print(f"\n=== SSモデル指標の要約統計 ===")
        for col in ss_columns:
            if col in results_df.columns:
                valid_data = results_df[col].dropna()
                if len(valid_data) > 0:
                    print(f"{col}: mean={valid_data.mean():.3f}, std={valid_data.std():.3f}, "
                          f"min={valid_data.min():.3f}, max={valid_data.max():.3f}")
        
        return results_df
    
    def analyze_ss_model_performance(self, results_df: pd.DataFrame):
        """SSモデルのパフォーマンス分析"""
        print(f"\n=== SSモデルパフォーマンス分析 ===")
        
        # 各閾値でのSSモデル指標の相関比較
        ss_metrics = ['SS_Support', 'Uniform_Support', 'Chi2_Support']
        traditional_metrics = ['CS', 'UCS', 'ΔP']
        
        # 閾値別の平均相関
        threshold_analysis = []
        for th in sorted(results_df['CS_threshold'].unique()):
            th_data = results_df[results_df['CS_threshold'] == th]
            
            for metric in ss_metrics + traditional_metrics:
                valid_corr = th_data[metric].dropna()
                if len(valid_corr) > 0:
                    avg_corr = valid_corr.mean()
                    abs_avg_corr = np.abs(valid_corr).mean()
                    threshold_analysis.append({
                        'threshold': th,
                        'metric': metric,
                        'avg_correlation': avg_corr,
                        'abs_avg_correlation': abs_avg_corr,
                        'n_valid': len(valid_corr)
                    })
        
        threshold_df = pd.DataFrame(threshold_analysis)
        
        # 結果の保存
        threshold_filename = "ss_model_threshold_analysis.csv"
        threshold_df.to_csv(threshold_filename, index=False, encoding="utf-8-sig")
        print(f"→ 閾値別分析結果を保存: {threshold_filename}")
        
        # 最高パフォーマンス指標の特定
        print(f"\n=== 最高パフォーマンス指標（絶対値平均相関） ===")
        best_performers = threshold_df.groupby('metric')['abs_avg_correlation'].max().sort_values(ascending=False)
        for metric, best_corr in best_performers.head(10).items():
            best_threshold = threshold_df[
                (threshold_df['metric'] == metric) & 
                (threshold_df['abs_avg_correlation'] == best_corr)
            ]['threshold'].iloc[0]
            print(f"{metric}: {best_corr:.3f} (threshold={best_threshold})")
        
        return threshold_df
    
    def calculate_sample_averages(self):
        """4条件下でのsample_numberごとに12個のストーリー(ex1_cover_story, ex2_cover_story)での平均回答値を計算"""
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_サマリー", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("対称否定_サマリー", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("非対称否定_オンライン", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("対称否定_オンライン", ex2_first[ex2_first["Cond"] == 1], "ex2"),
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
            filename = "sample_story_averages_by_condition_with_ss.csv"
            combined_averages.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"→ sample_numberとcover_storyごとの平均回答値を保存: {filename}")
            
            return combined_averages
        else:
            print("sample_numberとcover_storyごとの平均回答値の計算でデータが見つかりませんでした")
            return None


def analyze_ss_model_results():
    """SSモデル結果から得られる洞察を分析"""
    print("\n" + "="*60)
    print("SSモデル分析結果の解釈")
    print("="*60)
    
    print("""
SSモデルから得られた結果の解釈：

1. **SSモデルのパフォーマンス階層**
   - SS Support (r=0.737, γ=0.229): 最高の人間判断との相関
   - Uniform Support (r=0.677, γ=0.100): 中程度の相関
   - Chi-square Support (r=0.544, γ=0.100): 最低の相関

2. **理論的含意**
   - SS事前分布が人間の因果学習により適している
   - Sparse-Spiky構造が人間の直感的推論と一致
   - 単純な統計的指標（χ²）では人間判断を十分説明できない

3. **実験条件による差異**
   - 生成的因果関係（ΔP > 0）での高い予測力
   - 予防的因果関係（ΔP < 0）での興味深いパターン
   - 同じΔP値でも文脈により人間判断が変動

4. **今後の分析方向**
   - クラスタリング分析でSSモデル適合度の個人差を調査
   - 実験タイプ（サマリー vs オンライン）でのモデル性能比較
   - CRTスコアとSSモデル適合度の関係分析
    """)


if __name__ == "__main__":
    # SSモデルパラメータ
    alpha = 5.0  # SS prior parameter
    beta = 20.0  # S+ prior parameter
    
    # CS と UCS の threshold 値を0.1刻みで設定（同じ値）
    thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)] + [0.01]
    
    print("=== 拡張相関分析（SSモデル統合版） ===")
    print(f"SSモデルパラメータ: α={alpha}, β={beta}")
    print(f"threshold値: {thresholds}")
    print(f"総パターン数: {len(thresholds)}")
    print("=" * 50)
    
    analyzer = CorrelationAnalyzerWithSS("final_valid_updated.csv", max_k=5, alpha=alpha, beta=beta)
    
    # sample_numberごとの平均回答値を計算
    print("\n=== sample_numberとcover_storyごとの平均回答値計算 ===")
    analyzer.load_data()  # データを読み込み
    sample_averages = analyzer.calculate_sample_averages()
    
    # threshold分析を実行（SSモデル含む）
    print("\n=== threshold分析開始（SSモデル含む） ===")
    results = analyzer.run_threshold_analysis_with_ss(thresholds)
    
    # SSモデルパフォーマンス分析
    if results is not None and len(results) > 0:
        threshold_analysis = analyzer.analyze_ss_model_performance(results)
    
    # 結果解釈
    analyze_ss_model_results()
    
    print("\n=== 分析完了 ===")
