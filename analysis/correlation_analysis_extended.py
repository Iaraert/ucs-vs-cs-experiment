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
from scipy.stats import pearsonr
from CS_UCS import CS, UCS


class CorrelationAnalyzer:
    def __init__(self, csv_path: str, max_k: int = 5):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame = None
        
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
                    
                corr_table, crt_table, cluster_sizes, model_df = self.analyze_case(
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
                        "n": cluster_sizes.get(cluster_index, 0),  # 6で割った値を表示
                        "CRT_mean": crt_table.loc[cluster_name, "CRT_mean"],
                        "estimate_mean": crt_table.loc[cluster_name, "estimate_mean"],
                        "P(E|C)": corr_table.loc[cluster_name, "P(E|C)"],
                        "P(C|E)": corr_table.loc[cluster_name, "P(C|E)"],
                        "ΔP": corr_table.loc[cluster_name, "ΔP"],
                        "CS": corr_table.loc[cluster_name, "CS"],
                        "UCS": corr_table.loc[cluster_name, "UCS"],
                        "pARIs": corr_table.loc[cluster_name, "pARIs"],
                        "DFH": corr_table.loc[cluster_name, "DFH"],
                        "Dice": corr_table.loc[cluster_name, "Dice"]
                    }
                    
                    all_results.append(result_row)
        
        # 結果をDataFrameに変換して保存
        results_df = pd.DataFrame(all_results)
        
        # CSVファイルに保存
        filename = "extended_correlation_results.csv"
        results_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n→ 結果を保存: {filename}")
          # プレビュー表示
        print(f"\n=== 結果プレビュー ===")
        print(f"総行数: {len(results_df)}")
        print(f"threshold値: {sorted(results_df['CS_threshold'].unique())}")
        print(f"\n先頭5行:")
        print(results_df.head().to_string(index=False))
        
        return results_df
    
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
        """クラスタごとのCRT生データヒストグラムを作成（特定のthreshold値で）"""
        if thresholds is None:
            # デフォルトは threshold = 1.0 のみ
            thresholds = [1.0]
        
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
        
        for th in thresholds:
            print(f"\n=== threshold = {th:.1f} でのCRTクラスターヒストグラム作成 ===")
            
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
                print(f"条件: {condition_name}")
                
                # クラスタリング実行
                corr_table, crt_table, cluster_sizes, model_df = self.analyze_case(
                    label, df_sub, prefix, th, th)
                
                if corr_table is None:
                    print(f"  -> クラスタリングデータなし")
                    continue
                
                # クラスタリング結果を取得
                mat, k, labels = self.create_cluster_data(df_sub, prefix)
                if mat is None:
                    continue
                
                # クラスターごとのCRTヒストグラムを作成
                self._plot_crt_cluster_histogram(condition_name, df_sub, mat, k, prefix, th)
    
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
                corr_table, crt_table, cluster_sizes, model_df = self.analyze_case(
                    label, df_sub, prefix, th, th)
                
                if corr_table is None:
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
    analyzer = CorrelationAnalyzer("final_valid_updated.csv", max_k=5)
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
