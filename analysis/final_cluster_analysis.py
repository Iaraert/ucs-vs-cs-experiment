import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

try:
    df = pd.read_csv('final_valid.csv')
    print(f"データ読み込み成功: {df.shape[0]}行, {df.shape[1]}列")
    
    print(f"user_id: {df['user_id'].nunique()}")
    print(f"Cond分布:\n{df['Cond'].value_counts()}")
    
    # 各参加者の平均estimate値
    user_means = df.groupby(['user_id', 'Cond']).agg({
        'ex1_estimate': 'mean',
        'ex2_estimate': 'mean'
    }).reset_index()
    
    print(f"参加者データ: {len(user_means)}人")
    
    # 各条件ごとに、サマリーとオンラインで個別にクラスタリング
    clustering_results = {}
    for cond in [0, 1]:
        subset = user_means[user_means['Cond'] == cond]
        label = "非対称的" if cond == 0 else "対称的"
        
        # サマリー
        X_summary = subset[['ex1_estimate']].values
        kmeans_summary = KMeans(n_clusters=2, random_state=42)
        clusters_summary = kmeans_summary.fit_predict(X_summary)
        count_summary0 = int((clusters_summary == 0).sum())
        count_summary1 = int((clusters_summary == 1).sum())
        
        # オンライン
        X_online = subset[['ex2_estimate']].values
        kmeans_online = KMeans(n_clusters=2, random_state=42)
        clusters_online = kmeans_online.fit_predict(X_online)
        count_online0 = int((clusters_online == 0).sum())
        count_online1 = int((clusters_online == 1).sum())
        
        clustering_results[label] = {
            'summary': {'cluster0': count_summary0, 'cluster1': count_summary1},
            'online': {'cluster0': count_online0, 'cluster1': count_online1}
        }
        
        # ユーザーデータに各クラスタの割当も反映
        user_means.loc[subset.index, 'cluster_summary'] = clusters_summary
        user_means.loc[subset.index, 'cluster_online'] = clusters_online

    print("\nクラスタリング結果:")
    print(f"非対称的/サマリー {clustering_results['非対称的']['summary']['cluster0']} {clustering_results['非対称的']['summary']['cluster1']}")
    print(f"非対称的/オンライン  {clustering_results['非対称的']['online']['cluster0']} {clustering_results['非対称的']['online']['cluster1']}")
    print(f"対称的/サマリー {clustering_results['対称的']['summary']['cluster0']} {clustering_results['対称的']['summary']['cluster1']}")
    print(f"対称的/オンライン  {clustering_results['対称的']['online']['cluster0']} {clustering_results['対称的']['online']['cluster1']}")
    
    user_means.to_csv('final_cluster_results.csv', index=False)
    print("\n結果をfinal_cluster_results.csvに保存しました")
    
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
