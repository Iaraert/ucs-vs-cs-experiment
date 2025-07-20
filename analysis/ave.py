import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

def find_optimal_k(X, k_min=2, k_max=5, random_state=0):
    best_k, best_score = k_min, -1
    for k in range(k_min, k_max+1):
        labels = KMeans(n_clusters=k, random_state=random_state).fit_predict(X)
        score = silhouette_score(X, labels)
        print(f"    → k={k}, silhouette={score:.3f}")
        if score > best_score:
            best_k, best_score = k, score
    print(f"  ★ Best k = {best_k} (silhouette={best_score:.3f})\n")
    return best_k

def cluster_table(df, prefix, max_k=5):
    est_col = f"{prefix}_estimate"
    num_col = f"{prefix}_sample_number"
    # pivot: user_id × sample_number
    mat = df.pivot(index='user_id', columns=num_col, values=est_col).dropna()
    X = mat.values

    print(f"【{prefix}】クラスタリング (n_users={len(mat)})")
    k = find_optimal_k(X, k_max=max_k)

    labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
    mat['cluster'] = labels

    # 平均テーブル
    idx = mat.columns[:-1]
    table = pd.DataFrame(index=idx, 
                         columns=['All'] + [f'Cluster {i+1}' for i in range(k)])
    table.index.name = '#'
    table['All'] = mat.drop(columns='cluster').mean().values
    for i in range(k):
        table[f'Cluster {i+1}'] = mat[mat['cluster']==i].drop(columns='cluster').mean().values

    return table.round(1)

def plot_table(df_table, title, filename):
    fig, ax = plt.subplots(figsize=(4,2))
    ax.axis('off')
    tbl = ax.table(
        cellText=df_table.values,
        rowLabels=df_table.index,
        colLabels=df_table.columns,
        cellLoc='center',
        loc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1, 1.5)
    plt.title(title, pad=20)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)

def cluster_overall_data(df, max_k=5):
    """全体データのクラスタリング（サンプルナンバーごとのex1_estimate と ex2_estimate の平均）"""
    # ex1とex2の各サンプルナンバーでの平均を計算
    df_ex1_avg = df.groupby(['user_id', 'ex1_sample_number'])['ex1_estimate'].mean().reset_index()
    df_ex2_avg = df.groupby(['user_id', 'ex2_sample_number'])['ex2_estimate'].mean().reset_index()
    
    # サンプルナンバーを統一（ex1_sample_numberとex2_sample_numberは共通）
    df_ex1_avg = df_ex1_avg.rename(columns={'ex1_sample_number': 'sample_number'})
    df_ex2_avg = df_ex2_avg.rename(columns={'ex2_sample_number': 'sample_number'})
    
    # マージしてex1とex2の平均を計算
    merged = pd.merge(df_ex1_avg, df_ex2_avg, on=['user_id', 'sample_number'], how='inner')
    merged['overall_estimate'] = (merged['ex1_estimate'] + merged['ex2_estimate']) / 2
    
    # pivot: user_id × sample_number
    mat = merged.pivot(index='user_id', columns='sample_number', values='overall_estimate').dropna()
    X = mat.values
    
    print(f"【Overall】クラスタリング (n_users={len(mat)})")
    k = find_optimal_k(X, k_max=max_k)
    
    labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
    mat['cluster'] = labels
    
    # 平均テーブル作成
    idx = mat.columns[:-1]
    table = pd.DataFrame(index=idx, 
                         columns=['All'] + [f'Cluster {i+1}' for i in range(k)])
    table.index.name = '#'
    table['All'] = mat.drop(columns='cluster').mean().values
    for i in range(k):
        table[f'Cluster {i+1}'] = mat[mat['cluster']==i].drop(columns='cluster').mean().values
    
    return table.round(1)

if __name__ == "__main__":
    # データ読み込み
    df = pd.read_csv("final_valid.csv")
    
    # 全体データのクラスタリング
    overall_table = cluster_overall_data(df, max_k=5)
    print(f"\n— Overall Data —\n", overall_table, "\n")
    plot_table(
        overall_table,
        title="Overall Data: Average of EX1 & EX2 vs Cluster",
        filename="Overall_data.png"
    )
    print(f"→ Saved: Overall_data.png")

    # 「first」のみで分ける
    df_ex1 = df[df['ex1_is_first']==1].copy()
    df_ex2 = df[df['ex2_is_first']==1].copy()

    # ケース定義
    cases = [
        ("All_ex1",   df_ex1,               "ex1"),
        ("Cond0_ex1", df_ex1[df_ex1["Cond"]==0], "ex1"),
        ("Cond1_ex1", df_ex1[df_ex1["Cond"]==1], "ex1"),
        ("All_ex2",   df_ex2,               "ex2"),
        ("Cond0_ex2", df_ex2[df_ex2["Cond"]==0], "ex2"),
        ("Cond1_ex2", df_ex2[df_ex2["Cond"]==1], "ex2"),
    ]

    for name, subdf, prefix in cases:
        tbl = cluster_table(subdf, prefix, max_k=5)
        print(f"\n— {name} —\n", tbl, "\n")
        plot_table(
            tbl,
            title=f"{name}: {prefix.upper()} Sample vs Cluster",
            filename=f"{name}.png"
        )
        print(f"→ Saved: {name}.png")