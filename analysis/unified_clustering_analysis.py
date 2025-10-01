"""
unified_clustering_analysis.py

クラスタリング分析統合版
- 基本クラスタリング分析（clustering_analysis.py）
- ユーザーベースクラスタリング分析（user_based_cluster_analysis_filtered.py）
- CRT関連クラスタリング分析（crt_cluster_histogram_analysis.py）

統合機能:
1. サンプル数に基づくクラスタリング（K-means）
2. ユーザーベースクラスタリング（条件別フィルタリング）
3. CRT関連ヒストグラム・クラスタリング分析
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
matplotlib.rcParams['axes.unicode_minus'] = False


class UnifiedClusteringAnalyzer:
    """統合クラスタリング分析クラス"""
    
    def __init__(self, csv_path: str, max_k: int = 5, random_state: int = 42):
        self.csv_path = csv_path
        self.max_k = max_k
        self.random_state = random_state
        self.df = None
        self.results = {}
        
    def load_data(self):
        """データ読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        return self.df
        
    def find_optimal_k(self, X: np.ndarray, k_min: int = 2, k_max: int = None) -> int:
        """Silhouette scoreに基づいて最適k値を決定"""
        if k_max is None:
            k_max = self.max_k
        k_max = min(k_max, X.shape[0] - 1)
        
        best_k, best_score = k_min, -np.inf
        for k in range(k_min, k_max + 1):
            labels = KMeans(n_clusters=k, random_state=self.random_state).fit_predict(X)
            score = silhouette_score(X, labels)
            print(f"    → k={k}, silhouette={score:.3f}")
            if score > best_score:
                best_k, best_score = k, score
        print(f"  ★ Best k = {best_k} (silhouette={best_score:.3f})\n")
        return best_k
        
    def plot_table(self, df: pd.DataFrame, title: str, fname: str):
        """DataFrameを表画像として保存"""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.axis("off")
        tbl = ax.table(cellText=df.values,
                       rowLabels=df.index,
                       colLabels=df.columns,
                       cellLoc="center", loc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(10)
        tbl.scale(1.2, 1.5)
        plt.title(title, pad=20, fontsize=12)
        plt.tight_layout()
        plt.savefig(fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"→ Saved: {fname}")
        
    def create_cluster_table(self, df: pd.DataFrame, prefix: str):
        """クラスタリング&平均表作成"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        
        # ピボットテーブル作成
        mat = df.pivot(index="user_id", columns=num_col, values=est_col).dropna()
        if mat.empty:
            raise ValueError("ピボットテーブルが空です。フィルタ条件を確認してください。")
            
        # クラスタリング
        k = self.find_optimal_k(mat.values, k_max=self.max_k)
        original_labels = KMeans(n_clusters=k, random_state=self.random_state).fit_predict(mat.values)
        
        # 各クラスターの1~6の平均回答値の平均を計算してソート
        cluster_means = {}
        for i in range(k):
            cluster_data = mat.iloc[original_labels == i]
            available_cols = [col for col in cluster_data.columns if col in [1, 2, 3, 4, 5, 6]]
            if available_cols:
                cluster_mean = cluster_data[available_cols].mean().mean()
            else:
                cluster_mean = cluster_data.mean().mean()
            cluster_means[i] = cluster_mean
            
        # クラスターを平均値でソート（降順）
        sorted_clusters = sorted(cluster_means.keys(), key=lambda x: cluster_means[x], reverse=True)
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_clusters)}
        labels = np.array([label_mapping[label] for label in original_labels])
        
        mat["cluster"] = labels
        
        # 参加者数確認表示
        counts = pd.Series(labels).value_counts().sort_index()
        print("クラスターサイズ:", {f"Cluster{c+1}": int(n) for c, n in counts.items()})
        print("クラスター平均値（1~6の平均）:")
        for new_label in range(k):
            old_label = sorted_clusters[new_label]
            print(f"  Cluster{new_label+1}: {cluster_means[old_label]:.2f}")
            
        # 平均テーブル作成
        idx = mat.columns[:-1]
        table = pd.DataFrame(index=idx,
                             columns=["All"] + [f"Cluster {i+1}" for i in range(k)])
        table.index.name = "#"
        table["All"] = mat.drop(columns="cluster").mean().values
        for i in range(k):
            table[f"Cluster {i+1}"] = (
                mat[mat["cluster"] == i].drop(columns="cluster").mean().values
            )
        return table.round(1), mat, k
        
    def analyze_case(self, label: str, subset: pd.DataFrame, prefix: str):
        """個別ケース解析"""
        if subset.empty:
            print(f"\n{label}: データが空です → スキップ")
            return None, None, None
            
        print("\n" + "=" * 60)
        print(f"{label} の分析")
        print("=" * 60)
        
        try:
            cluster_tbl, mat, k = self.create_cluster_table(subset, prefix)
            print("\n-- Cluster Averages --\n", cluster_tbl)
            
            # 画像保存
            filename = f"{label}_avg.png"
            self.plot_table(cluster_tbl, f"{label}: {prefix.upper()}", filename)
            
            # クラスターサイズ情報を取得
            cluster_sizes = {}
            for i in range(k):
                cluster_sizes[i] = len(mat[mat["cluster"] == i])
                
            # 結果保存
            self.results[label] = {
                "cluster": cluster_tbl,
                "cluster_sizes": cluster_sizes,
                "mat": mat,
                "k": k
            }
            
            return cluster_tbl, mat, k
            
        except Exception as e:
            print(f"エラー: {e}")
            return None, None, None
            
    def basic_clustering_analysis(self):
        """基本クラスタリング分析（clustering_analysis.py相当）"""
        print("\n" + "="*80)
        print("基本クラスタリング分析")
        print("="*80)
        
        if self.df is None:
            self.load_data()
            
        # データ前処理
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        # Overall analysis (全体データのクラスタリング)
        print("\n--- Overall Analysis ---")
        
        # ex1 と ex2 のユーザー別平均を結合
        ex1_avg = ex1_first.groupby("user_id")["ex1_estimate"].mean().reset_index()
        ex2_avg = ex2_first.groupby("user_id")["ex2_estimate"].mean().reset_index()
        merged = pd.merge(ex1_avg, ex2_avg, on="user_id", how="inner")
        merged["overall_estimate"] = (merged["ex1_estimate"] + merged["ex2_estimate"]) / 2
        
        # ピボットテーブル作成（sample_number別の全体平均）
        overall_pivot = self.df.groupby(["user_id", "sample_number"])[["ex1_estimate", "ex2_estimate"]].mean()
        overall_pivot["overall_estimate"] = (overall_pivot["ex1_estimate"] + overall_pivot["ex2_estimate"]) / 2
        overall_pivot = overall_pivot.reset_index().pivot(index="user_id", columns="sample_number", values="overall_estimate").dropna()
        
        print(f"【Overall】クラスタリング (n_users={len(overall_pivot)})")
        k_overall = self.find_optimal_k(overall_pivot.values, k_max=self.max_k)
        
        original_labels = KMeans(n_clusters=k_overall, random_state=self.random_state).fit_predict(overall_pivot.values)
        
        # クラスターソート
        cluster_means = {}
        for i in range(k_overall):
            cluster_data = overall_pivot.iloc[original_labels == i]
            cluster_means[i] = cluster_data.mean().mean()
            
        sorted_clusters = sorted(cluster_means.keys(), key=lambda x: cluster_means[x], reverse=True)
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_clusters)}
        labels = np.array([label_mapping[label] for label in original_labels])
        overall_pivot["cluster"] = labels
        
        counts = pd.Series(labels).value_counts().sort_index()
        print("Overall cluster sizes:", counts.to_dict())
        print("Overall cluster means (1~6 average):")
        for new_label in range(k_overall):
            old_label = sorted_clusters[new_label]
            print(f"  Cluster{new_label+1}: {cluster_means[old_label]:.2f}")
            
        # 個別ケース分析
        cases = [
            ("All_ex1", ex1_first, "ex1"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("All_ex2", ex2_first, "ex2"),
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]
        
        for case_name, data, prefix in cases:
            self.analyze_case(case_name, data, prefix)
            
    def user_based_clustering_analysis(self):
        """ユーザーベースクラスタリング分析（user_based_cluster_analysis_filtered.py相当）"""
        print("\n" + "="*80)
        print("ユーザーベースクラスタリング分析")
        print("="*80)
        
        if self.df is None:
            self.load_data()
            
        # 全体平均クラスタリング
        print("\n--- 全体平均クラスタリング ---")
        grouped_combined = self.df.groupby('user_id')
        user_ids_combined = []
        features_combined = []
        for uid, group in grouped_combined:
            user_ids_combined.append(uid)
            ex1_mean = group['ex1_estimate'].mean()
            ex2_mean = group['ex2_estimate'].mean()
            combined_mean = (ex1_mean + ex2_mean) / 2
            features_combined.append(combined_mean)
        features_combined = np.array(features_combined).reshape(-1, 1)
        
        scaler_combined = StandardScaler()
        scaled_combined = scaler_combined.fit_transform(features_combined)
        kmeans_combined = KMeans(n_clusters=2, random_state=self.random_state)
        clusters_combined = kmeans_combined.fit_predict(scaled_combined)
        
        count_cluster0_combined = int(np.sum(clusters_combined == 0))
        count_cluster1_combined = int(np.sum(clusters_combined == 1))
        total_combined = len(clusters_combined)
        overall_avg_combined = np.mean(features_combined[:,0])
        cluster0_avg_combined = np.mean(features_combined[clusters_combined == 0, 0]) if np.any(clusters_combined == 0) else float('nan')
        cluster1_avg_combined = np.mean(features_combined[clusters_combined == 1, 0]) if np.any(clusters_combined == 1) else float('nan')
        
        # 回答値が大きいものをcluster1とする
        if cluster0_avg_combined > cluster1_avg_combined:
            clusters_combined = np.where(clusters_combined == 0, 1, 0)
            cluster0_avg_combined, cluster1_avg_combined = cluster1_avg_combined, cluster0_avg_combined
            count_cluster0_combined, count_cluster1_combined = count_cluster1_combined, count_cluster0_combined
            
        print("ex1_estimate, ex2_estimateの回答値を平均したもののクラスタ分布")
        print(f"全体: {count_cluster0_combined}, {count_cluster1_combined}, {total_combined}  平均: {overall_avg_combined:.2f} (cluster0: {cluster0_avg_combined:.2f}, cluster1: {cluster1_avg_combined:.2f})")
        
        # 条件別フィルタリング分析
        print("\n--- 条件別フィルタリング分析 ---")
        
        # フィルタリング条件定義
        conditions = {
            "非対称的/サマリー": {"cond_val": 0, "col": "ex1_estimate", "is_first_col": "ex1_is_first"},
            "非対称的/オンライン": {"cond_val": 0, "col": "ex2_estimate", "is_first_col": "ex2_is_first"},
            "対称的/サマリー": {"cond_val": 1, "col": "ex1_estimate", "is_first_col": "ex1_is_first"},
            "対称的/オンライン": {"cond_val": 1, "col": "ex2_estimate", "is_first_col": "ex2_is_first"}
        }
        
        final_results = []
        condition_distribution = {}
        
        # 各条件ごとにクラスタリング実行
        for label, details in conditions.items():
            subset = self.df[(self.df['Cond'] == details["cond_val"]) & 
                            (self.df[details["is_first_col"]] == 1)]
            
            print(f"\n{label} - フィルタ後のデータ行数: {len(subset)}")
            
            # ユーザーごとにグループ化
            grouped = subset.groupby('user_id')
            user_ids = []
            features = []
            for user_id, group in grouped:
                user_ids.append(user_id)
                features.append(group[details["col"]].mean())
                
            # 十分なデータがない場合はスキップ
            if len(features) < 2:
                print(f"{label}の条件でフィルタリングしたデータが不足しています（ユーザー数: {len(features)}）。スキップします。")
                continue
                
            features = np.array(features).reshape(-1, 1)
            
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)
            kmeans = KMeans(n_clusters=2, random_state=self.random_state)
            clusters = kmeans.fit_predict(scaled_features)
            
            count_cluster0 = np.sum(clusters == 0)
            count_cluster1 = np.sum(clusters == 1)
            total = len(clusters)
            
            overall_avg = np.mean(features[:,0])
            cluster0_avg = np.mean(features[clusters==0, 0]) if np.any(clusters==0) else float('nan')
            cluster1_avg = np.mean(features[clusters==1, 0]) if np.any(clusters==1) else float('nan')
            
            # 平均値に応じてクラスタ番号を一定の意味に揃える処理
            if cluster0_avg > cluster1_avg:
                clusters = np.where(clusters == 0, 1, 0)
                cluster0_avg, cluster1_avg = cluster1_avg, cluster0_avg
                count_cluster0, count_cluster1 = count_cluster1, count_cluster0
                
            condition_distribution[label] = {
                'cluster0': int(count_cluster0), 'cluster1': int(count_cluster1), 'total': total,
                'overall_avg': overall_avg, 'cluster0_avg': cluster0_avg, 'cluster1_avg': cluster1_avg
            }
            
            for uid, cl in zip(user_ids, clusters):
                final_results.append({
                    'user_id': uid,
                    'Cond': details["cond_val"],
                    'condition': label,
                    'cluster': cl
                })
                
        # 結果保存
        results_df = pd.DataFrame(final_results)
        
        print("\n条件別クラスタ分布（cluster0, cluster1, total）と平均回答値")
        for condition in conditions.keys():
            if condition in condition_distribution:
                dist = condition_distribution[condition]
                print(f"{condition}: {dist['cluster0']}, {dist['cluster1']}, {dist['total']}  平均: {dist['overall_avg']:.2f} (cluster0: {dist['cluster0_avg']:.2f}, cluster1: {dist['cluster1_avg']:.2f})")
            else:
                print(f"{condition}: 0, 0, 0  平均: N/A (cluster0: N/A, cluster1: N/A)")
                
        results_df.to_csv('user_cluster_results.csv', index=False)
        print("\n詳細な結果をuser_cluster_results.csvに保存しました。")
        
        self.results['user_based'] = {
            'results_df': results_df,
            'condition_distribution': condition_distribution
        }
        
    def crt_clustering_analysis(self, threshold: float = 1.0):
        """CRT関連クラスタリング分析（crt_cluster_histogram_analysis.py相当）"""
        print("\n" + "="*80)
        print("CRT関連クラスタリング分析")
        print("="*80)
        
        # CRT関連分析は別途実装が必要
        # 現在はプレースホルダー
        print(f"CRT閾値: {threshold}")
        print("※ CRT関連分析は今後実装予定")
        
    def save_results(self, output_dir: str = "clustering_results"):
        """結果保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 基本クラスタリング結果
        if 'basic' in self.results:
            for case_name, case_data in self.results.items():
                if case_name != 'user_based' and isinstance(case_data, dict) and 'cluster' in case_data:
                    filename = os.path.join(output_dir, f"{case_name}_cluster_table.csv")
                    case_data['cluster'].to_csv(filename)
                    print(f"保存: {filename}")
                    
        # ユーザーベース結果
        if 'user_based' in self.results:
            filename = os.path.join(output_dir, "user_cluster_results.csv")
            self.results['user_based']['results_df'].to_csv(filename, index=False)
            print(f"保存: {filename}")
            
        print(f"\n全結果を {output_dir} に保存しました。")


def main():
    parser = argparse.ArgumentParser(description="統合クラスタリング分析")
    parser.add_argument("--mode", choices=["basic", "user", "crt", "all"], default="all",
                        help="分析モード選択")
    parser.add_argument("--csv", default="final_valid.csv",
                        help="入力CSVファイル")
    parser.add_argument("--max_k", type=int, default=5,
                        help="最大クラスター数")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="CRT分析用閾値")
    parser.add_argument("--output_dir", default="clustering_results",
                        help="出力ディレクトリ")
                        
    args = parser.parse_args()
    
    analyzer = UnifiedClusteringAnalyzer(args.csv, args.max_k)
    
    if args.mode in ["basic", "all"]:
        analyzer.basic_clustering_analysis()
        
    if args.mode in ["user", "all"]:
        analyzer.user_based_clustering_analysis()
        
    if args.mode in ["crt", "all"]:
        analyzer.crt_clustering_analysis(args.threshold)
        
    # 結果保存
    analyzer.save_results(args.output_dir)
    
    print("\n統合クラスタリング分析完了！")


if __name__ == "__main__":
    main()