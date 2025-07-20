"""
overall_average_analysis.py

ex1_estimate と ex2_estimate の平均値 (ex1_estimate + ex2_estimate) / 2 を使って、
全体のクラスタリングと相関係数分析を実行する。

ex1_is_first と ex2_is_first は補完的な役割を果たしており、
sample_number は ex1 と ex2 で共通である。
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr
from CS_UCS import CS, UCS  # ユーザ提供モジュール

# 日本語フォント設定
import japanize_matplotlib

def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    """x, y のピアソン相関を計算。
    - サンプル数 < 2 あるいは分散 0 の場合は 0.0 を返す。
    - NaN は除外。
    """
    mask = ~np.isnan(x) & ~np.isnan(y)
    if mask.sum() < 2:
        return np.nan  # 本質的に計算不能
    if np.nanstd(x[mask]) == 0 or np.nanstd(y[mask]) == 0:
        return 0.0  # 変動が無い → 相関を 0 とみなす
    return pearsonr(x[mask], y[mask])[0]

def find_optimal_k(X: np.ndarray, k_min: int = 2, k_max: int = 5) -> int:
    """Silhouette score に基づいて最適 k を決定"""
    best_k, best_score = k_min, -np.inf
    for k in range(k_min, min(k_max, X.shape[0]) + 1):
        labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
        score = silhouette_score(X, labels)
        print(f"    → k={k}, silhouette={score:.3f}")
        if score > best_score:
            best_k, best_score = k, score
    print(f"  ★ Best k = {best_k} (silhouette={best_score:.3f})\n")
    return best_k

def metrics_from_abcd(a: int, b: int, c: int, d: int, *, th: float = 0.8, is_gene: bool = True):
    """a,b,c,d → モデル指標 8 種類"""
    pe_c = a / (a + b) if (a + b) else np.nan
    pc_e = a / (a + c) if (a + c) else np.nan
    delta_p = pe_c - (c / (c + d) if (c + d) else np.nan)
    paris = a / (a + b + c) if (a + b + c) else np.nan
    dfh = a / np.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
    dice = (2 * a) / (2 * a + b + c) if (2 * a + b + c) else np.nan
    cs_val = CS((a, b, c, d), 1.0, is_gene)
    ucs_val = UCS((a, b, c, d), 0.01, is_gene)
    return pe_c, pc_e, delta_p, cs_val, ucs_val, paris, dfh, dice

def plot_table(df: pd.DataFrame, title: str, fname: str):
    """DataFrame をシンプルな表画像として保存"""
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    tbl = ax.table(cellText=df.values,
                   rowLabels=df.index,
                   colLabels=df.columns,
                   cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.5)
    plt.title(title, pad=20)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"→ Saved: {fname}")

class OverallAverageAnalysis:
    def __init__(self, csv_path: str, max_k: int = 5):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame | None = None
        
    def load_data(self):
        """データを読み込み、平均値を計算"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
        # 平均estimate値を計算 (ex1_estimate + ex2_estimate) / 2
        self.df['avg_estimate'] = (self.df['ex1_estimate'] + self.df['ex2_estimate']) / 2
        
        # sample_numberはex1とex2で共通なので、ex1_sample_numberを使用
        self.df['sample_number'] = self.df['ex1_sample_number']
        
        print(f"平均estimate値を計算しました")
        print(f"Sample number範囲: {self.df['sample_number'].min()} - {self.df['sample_number'].max()}")
        print(f"ユニークなsample_number: {sorted(self.df['sample_number'].unique())}")
        
    def create_pivot_for_clustering(self):
        """クラスタリング用のピボットテーブルを作成"""
        pivot_df = self.df.pivot(index='user_id', columns='sample_number', values='avg_estimate')
        pivot_df = pivot_df.dropna()
        
        print(f"ピボットテーブル作成完了: {pivot_df.shape}")
        print(f"使用するsample_number: {list(pivot_df.columns)}")
        
        return pivot_df
        
    def perform_clustering(self, pivot_df: pd.DataFrame):
        """クラスタリングを実行"""
        print("\n=== クラスタリング分析 ===")
        
        # 最適なクラスタ数を決定
        k = find_optimal_k(pivot_df.values, k_max=self.max_k)
        
        # K-meansクラスタリング実行
        kmeans = KMeans(n_clusters=k, random_state=0)
        labels = kmeans.fit_predict(pivot_df.values)
        pivot_df['cluster'] = labels
        
        # クラスタサイズの表示
        cluster_counts = pivot_df['cluster'].value_counts().sort_index()
        print("クラスタサイズ:")
        for cluster_id, count in cluster_counts.items():
            print(f"  Cluster {cluster_id + 1}: {count}人")
            
        return pivot_df, k
        
    def create_average_table(self, pivot_df: pd.DataFrame, k: int):
        """クラスタごとの平均値テーブルを作成"""
        sample_columns = [col for col in pivot_df.columns if col != 'cluster']
        
        # 平均値テーブル作成
        avg_table = pd.DataFrame(
            index=sample_columns,
            columns=['All'] + [f'Cluster {i+1}' for i in range(k)]
        )
        avg_table.index.name = 'Sample#'
        
        # 全体平均
        avg_table['All'] = pivot_df[sample_columns].mean().values
        
        # クラスタごとの平均
        for i in range(k):
            cluster_data = pivot_df[pivot_df['cluster'] == i][sample_columns]
            avg_table[f'Cluster {i+1}'] = cluster_data.mean().values
            
        avg_table = avg_table.round(2)
        
        print("\n=== クラスタ平均値テーブル ===")
        print(avg_table.to_string())
        
        # テーブルを画像として保存
        plot_table(avg_table, "Overall Average Analysis: Cluster Averages", "overall_avg_table.png")
        
        return avg_table
        
    def calculate_model_metrics(self):
        """各sample_numberに対してモデル指標を計算"""
        sample_numbers = sorted(self.df['sample_number'].unique())
        
        model_df = pd.DataFrame(
            index=sample_numbers,
            columns=['P(E|C)', 'P(C|E)', 'ΔP', 'CS', 'UCS', 'pARIs', 'DFH', 'Dice'],
            dtype=float
        )
        
        for sn in sample_numbers:
            # 該当するsample_numberの最初の行から a,b,c,d を取得
            # ex1とex2で a,b,c,d は同じなので、ex1の値を使用
            row = self.df[self.df['sample_number'] == sn].iloc[0]
            a, b, c, d = int(row['ex1_a']), int(row['ex1_b']), int(row['ex1_c']), int(row['ex1_d'])
            
            # 平均estimate値が正かどうかでis_geneを判定
            avg_est = self.df[self.df['sample_number'] == sn]['avg_estimate'].mean()
            is_gene = avg_est >= 0
            
            # モデル指標を計算
            model_df.loc[sn] = metrics_from_abcd(a, b, c, d, is_gene=is_gene)
            
        print("\n=== モデル指標テーブル ===")
        print(model_df.round(3).to_string())
        
        return model_df
        
    def calculate_correlations(self, pivot_df: pd.DataFrame, model_df: pd.DataFrame, k: int):
        """相関係数を計算"""
        print("\n=== 相関分析 ===")
        
        # グループ定義
        groups = {'All': self.df}
        for cl in range(k):
            cluster_users = pivot_df[pivot_df['cluster'] == cl].index
            groups[f'Cluster{cl+1}'] = self.df[self.df['user_id'].isin(cluster_users)]
            
        # 相関テーブル初期化
        corr_table1 = pd.DataFrame(
            index=groups.keys(),
            columns=['P(E|C)', 'P(C|E)', 'ΔP', 'CS']
        )
        corr_table2 = pd.DataFrame(
            index=groups.keys(),
            columns=['UCS', 'pARIs', 'DFH', 'Dice']
        )
        
        # 各グループに対して相関を計算
        for group_name, group_df in groups.items():
            print(f"\n{group_name} の相関計算 (n={len(group_df)}人)")
            
            # sample_numberごとの平均estimate値を取得
            y_values = (
                group_df.groupby('sample_number')['avg_estimate']
                .mean()
                .reindex(model_df.index)
                .values
            )
            
            # 各モデル指標との相関を計算
            for metric in model_df.columns:
                x_values = model_df[metric].values
                corr = safe_corr(x_values, y_values)
                
                # 適切なテーブルに結果を格納
                if metric in corr_table1.columns:
                    corr_table1.loc[group_name, metric] = np.nan if np.isnan(corr) else round(corr, 3)
                else:
                    corr_table2.loc[group_name, metric] = np.nan if np.isnan(corr) else round(corr, 3)
                    
                print(f"  {metric}: r = {corr:.3f}" if not np.isnan(corr) else f"  {metric}: r = NaN")
        
        print("\n=== 相関係数テーブル1 (P(E|C), P(C|E), ΔP, CS) ===")
        print(corr_table1.to_string())
        
        print("\n=== 相関係数テーブル2 (UCS, pARIs, DFH, Dice) ===")
        print(corr_table2.to_string())
        
        return corr_table1, corr_table2
        
    def save_results(self, avg_table, model_df, corr_table1, corr_table2):
        """結果をCSVファイルに保存"""
        avg_table.to_csv('overall_avg_cluster_table.csv')
        model_df.to_csv('overall_model_metrics.csv')
        corr_table1.to_csv('overall_correlation_table1.csv')
        corr_table2.to_csv('overall_correlation_table2.csv')
        
        print(f"\n結果ファイルを保存しました:")
        print(f"  - overall_avg_cluster_table.csv")
        print(f"  - overall_model_metrics.csv") 
        print(f"  - overall_correlation_table1.csv")
        print(f"  - overall_correlation_table2.csv")
        
    def run(self):
        """全体の分析を実行"""
        print("=" * 70)
        print("Overall Average Analysis: (ex1_estimate + ex2_estimate) / 2")
        print("=" * 70)
        
        # データ読み込みと前処理
        self.load_data()
        
        # ピボットテーブル作成
        pivot_df = self.create_pivot_for_clustering()
        
        # クラスタリング実行
        pivot_df, k = self.perform_clustering(pivot_df)
        
        # 平均値テーブル作成
        avg_table = self.create_average_table(pivot_df, k)
        
        # モデル指標計算
        model_df = self.calculate_model_metrics()
        
        # 相関係数計算
        corr_table1, corr_table2 = self.calculate_correlations(pivot_df, model_df, k)
        
        # 結果保存
        self.save_results(avg_table, model_df, corr_table1, corr_table2)
        
        print("\n分析完了!")
        
        return {
            'pivot_df': pivot_df,
            'avg_table': avg_table,
            'model_df': model_df,
            'corr_table1': corr_table1,
            'corr_table2': corr_table2
        }

if __name__ == "__main__":
    analysis = OverallAverageAnalysis("final_valid.csv", max_k=5)
    results = analysis.run()
