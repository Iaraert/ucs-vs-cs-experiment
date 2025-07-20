import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def find_optimal_k(X, k_min=2, k_max=5, random_state=0):
    best_k, best_score = k_min, -1
    for k in range(k_min, k_max+1):
        km = KMeans(n_clusters=k, random_state=random_state).fit(X)
        score = silhouette_score(X, km.labels_)
        print(f"  → k={k}, silhouette={score:.3f}")
        if score > best_score:
            best_k, best_score = k, score
    print(f"★ Best k = {best_k} (silhouette={best_score:.3f})\n")
    return best_k

def cluster_and_table(df, prefix, max_k=5):
    est = f"{prefix}_estimate"
    num = f"{prefix}_sample_number"

    # pivot: user × sample#
    pivot = df.pivot(index='user_id', columns=num, values=est)
    pivot = pivot.dropna()            # drop users with any missing sample
    X = pivot.values

    print(f"=== {prefix} クラスタリング（all users in df）===")
    k = find_optimal_k(X, k_max=max_k)
    labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
    pivot['cluster'] = labels

    # build mean table
    table = pd.DataFrame(index=pivot.columns[:-1])
    table.index.name = '#'
    table['All'] = pivot.drop(columns='cluster').mean()
    for c in range(k):
        table[f'Cluster {c+1}'] = pivot[pivot['cluster']==c].drop(columns='cluster').mean()

    print(table.round(2), '\n')
    return pivot

def cluster_and_table_both(df, max_k=5):
    # pivot ex1 and ex2 across ALL users
    p1 = df.pivot(index='user_id', columns='ex1_sample_number', values='ex1_estimate')
    p2 = df.pivot(index='user_id', columns='ex2_sample_number', values='ex2_estimate')
    p1.columns = [f"ex1_{c}" for c in p1.columns]
    p2.columns = [f"ex2_{c}" for c in p2.columns]

    merged = p1.join(p2, how='inner').dropna()
    X = merged.values

    print("=== No‐condition（ex1＋ex2）クラスタリング ===")
    k = find_optimal_k(X, k_max=max_k)
    labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
    merged['cluster'] = labels

    # ex1 table
    ex1_cols = [c for c in merged.columns if c.startswith('ex1_')]
    tbl1 = pd.DataFrame(index=[int(c.split('_')[1]) for c in ex1_cols])
    tbl1.index.name = '#'
    tbl1['All'] = merged[ex1_cols].mean()
    for c in range(k):
        tbl1[f'Cluster {c+1}'] = merged[merged['cluster']==c][ex1_cols].mean()
    print("\n-- Ex1 Table --")
    print(tbl1.round(2))

    # ex2 table
    ex2_cols = [c for c in merged.columns if c.startswith('ex2_')]
    tbl2 = pd.DataFrame(index=[int(c.split('_')[1]) for c in ex2_cols])
    tbl2.index.name = '#'
    tbl2['All'] = merged[ex2_cols].mean()
    for c in range(k):
        tbl2[f'Cluster {c+1}'] = merged[merged['cluster']==c][ex2_cols].mean()
    print("\n-- Ex2 Table --\n")
    print(tbl2.round(2), '\n')

    return merged

if __name__ == "__main__":
    # 1) load all data
    df = pd.read_csv("final_valid.csv")

    # 2) No‐condition: uses both ex1 & ex2
    cluster_and_table_both(df, max_k=5)

        # 3) Cond=0 × ex1
    df0_ex1 = df[df['Cond']==0]
    cluster_and_table(df0_ex1, 'ex1', max_k=5)

    # 4) Cond=0 × ex2
    df0_ex2 = df[df['Cond']==0]
    cluster_and_table(df0_ex2, 'ex2', max_k=5)

    # 5) Cond=1 × ex1
    df1_ex1 = df[df['Cond']==1]
    cluster_and_table(df1_ex1, 'ex1', max_k=5)

    # 6) Cond=1 × ex2
    df1_ex2 = df[df['Cond']==1]
    cluster_and_table(df1_ex2, 'ex2', max_k=5)