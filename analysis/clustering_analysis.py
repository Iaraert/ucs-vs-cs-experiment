"""
clustering_analysis.py

クラスタリング分析専用コード - 相関分析部分を分離
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# 日本語フォント設定
import japanize_matplotlib


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


def plot_table(df: pd.DataFrame, title: str, fname: str):
    """DataFrame をシンプルな表画像として保存"""
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.axis("off")
    tbl = ax.table(cellText=df.values,
                   rowLabels=df.index,
                   colLabels=df.columns,
                   cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.4)
    plt.title(title, pad=18)
    plt.tight_layout()
    plt.savefig(fname, dpi=300)
    plt.close(fig)
    print(f"→ Saved: {fname}")


class ClusteringAnalysis:
    def __init__(self, csv_path: str, max_k: int = 5):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df: pd.DataFrame = None
        self.results: dict[str, dict] = {}

    def load(self):
        """データロード"""
        self.df = pd.read_csv(self.csv_path)
        print(f"読み込み完了: {self.csv_path}  (shape={self.df.shape})")

    def _cluster_table(self, df: pd.DataFrame, prefix: str):
        """クラスタリング & 平均表作成"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        mat = df.pivot(index="user_id", columns=num_col, values=est_col).dropna()
        if mat.empty:
            raise ValueError("Pivot テーブルが空です。フィルタ条件を確認してください。")

        # クラスタリング
        k = find_optimal_k(mat.values, k_max=self.max_k)
        original_labels = KMeans(n_clusters=k, random_state=0).fit_predict(mat.values)
        
        # 各クラスターの1~6の平均回答値の平均を計算してソート
        cluster_means = {}
        for i in range(k):
            cluster_data = mat.iloc[original_labels == i, :-1] if 'cluster' in mat.columns else mat.iloc[original_labels == i]
            # 1~6の列を取得（sample_number 1~6に対応）
            available_cols = [col for col in cluster_data.columns if col in [1, 2, 3, 4, 5, 6]]
            if available_cols:
                cluster_mean = cluster_data[available_cols].mean().mean()
            else:
                cluster_mean = cluster_data.mean().mean()
            cluster_means[i] = cluster_mean
        
        # 平均値の大きい順にクラスターをソート
        sorted_clusters = sorted(cluster_means.keys(), key=lambda x: cluster_means[x], reverse=True)
        
        # ラベルを再マッピング（平均値が大きい方がCluster1になる）
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_clusters)}
        labels = np.array([label_mapping[label] for label in original_labels])
        
        mat["cluster"] = labels

        # 参加者数の確認表示（再マッピング後）
        counts = pd.Series(labels).value_counts().sort_index()
        print("クラスタサイズ:", {f"Cluster{c+1}": int(n) for c, n in counts.items()})
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

        cluster_tbl, mat, k = self._cluster_table(subset, prefix)
        print("\n-- Cluster Averages --\n", cluster_tbl)
        plot_table(cluster_tbl, f"{label}: {prefix.upper()}", f"{label}_avg.png")

        # クラスターサイズ情報を取得
        cluster_sizes = {}
        for i in range(k):
            cluster_sizes[i] = len(mat[mat["cluster"] == i])

        # 保存
        self.results[label] = {"cluster": cluster_tbl,
                               "cluster_sizes": cluster_sizes,
                               "mat": mat,
                               "k": k}
        
        return cluster_tbl, mat, k

    def run(self):
        """全体実行"""
        self.load()

        # first ブロック
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        # 総合クラスタリング
        overall = pd.concat([
            ex1_first.rename(columns={"ex1_estimate": "estimate", "ex1_sample_number": "sn"})[["user_id", "sn", "estimate"]],
            ex2_first.rename(columns={"ex2_estimate": "estimate", "ex2_sample_number": "sn"})[["user_id", "sn", "estimate"]]
        ])
        overall = overall.groupby(["user_id", "sn"]).mean().reset_index()
        overall_pivot = overall.pivot(index="user_id", columns="sn", values="estimate").dropna()
        print("\n総合クラスタリング")
        k_overall = find_optimal_k(overall_pivot.values)
        original_labels = KMeans(n_clusters=k_overall, random_state=0).fit_predict(overall_pivot.values)
        
        # 全体でも1~6の平均値でクラスターをソート
        cluster_means = {}
        for i in range(k_overall):
            cluster_data = overall_pivot.iloc[original_labels == i]
            available_cols = [col for col in cluster_data.columns if col in [1, 2, 3, 4, 5, 6]]
            if available_cols:
                cluster_mean = cluster_data[available_cols].mean().mean()
            else:
                cluster_mean = cluster_data.mean().mean()
            cluster_means[i] = cluster_mean
        
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

        # 個別ケース
        cases = [
            ("All_ex1", ex1_first, "ex1"),
            ("Cond0_ex1", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("Cond1_ex1", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("All_ex2", ex2_first, "ex2"),
            ("Cond0_ex2", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("Cond1_ex2", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]

        # 各ケースの分析
        for lbl, df_sub, pre in cases:
            self.analyze_case(lbl, df_sub, pre)

        print("\nクラスタリング分析終了")
        return self.results


if __name__ == "__main__":
    analysis = ClusteringAnalysis("final_valid.csv", max_k=5)
    results = analysis.run()
