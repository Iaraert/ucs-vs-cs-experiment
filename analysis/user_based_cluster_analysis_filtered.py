import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


df = pd.read_csv('final_valid.csv')

# 一番最初に、ex1_estimate, ex2_estimateの回答値を平均したもののクラスタリング
grouped_combined = df.groupby('user_id')
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
kmeans_combined = KMeans(n_clusters=2, random_state=42)
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

# サマリー形式のデータはex1_is_first=1, オンライン形式のデータはex2_is_first=1のみが使えるという条件をフィルタリング
df_summary = df[df['ex1_is_first'] == 1]  # サマリー形式のフィルタリング
df_online = df[df['ex2_is_first'] == 1]   # オンライン形式のフィルタリング

# サマリーとオンラインを分ける前の全体データのクラスタリング
# 各ユーザーについて、ex1_is_first=1のデータからex1_estimate平均、ex2_is_first=1のデータからex2_estimate平均を計算し、それらを平均
user_ids_combined_filtered = []
features_combined_filtered = []

# デバッグ情報
total_users = len(df['user_id'].unique())
users_with_ex1_first = len(df[df['ex1_is_first'] == 1]['user_id'].unique())
users_with_ex2_first = len(df[df['ex2_is_first'] == 1]['user_id'].unique())

print(f"\nデバッグ情報:")
print(f"総ユーザー数: {total_users}")
print(f"ex1_is_first=1のユーザー数: {users_with_ex1_first}")
print(f"ex2_is_first=1のユーザー数: {users_with_ex2_first}")

for uid in df['user_id'].unique():
    user_data = df[df['user_id'] == uid]
    
    # ex1_is_first=1のデータからex1_estimate平均を計算
    ex1_filtered = user_data[user_data['ex1_is_first'] == 1]
    ex1_avg = ex1_filtered['ex1_estimate'].mean() if len(ex1_filtered) > 0 else np.nan
    
    # ex2_is_first=1のデータからex2_estimate平均を計算
    ex2_filtered = user_data[user_data['ex2_is_first'] == 1]
    ex2_avg = ex2_filtered['ex2_estimate'].mean() if len(ex2_filtered) > 0 else np.nan
    
    # 両方のデータが存在する場合のみ使用
    if not np.isnan(ex1_avg) and not np.isnan(ex2_avg):
        user_ids_combined_filtered.append(uid)
        combined_avg = (ex1_avg + ex2_avg) / 2
        features_combined_filtered.append(combined_avg)

print(f"ex1_is_first=1とex2_is_first=1の両方を持つユーザー数: {len(user_ids_combined_filtered)}")

if len(features_combined_filtered) == 0:
    print("警告: ex1_is_first=1とex2_is_first=1の両方の条件を満たすユーザーが存在しません。")
    print("このクラスタリングをスキップします。")
else:
    features_combined_filtered = np.array(features_combined_filtered).reshape(-1, 1)

    scaler_combined_filtered = StandardScaler()
    scaled_combined_filtered = scaler_combined_filtered.fit_transform(features_combined_filtered)
    kmeans_combined_filtered = KMeans(n_clusters=2, random_state=42)
    clusters_combined_filtered = kmeans_combined_filtered.fit_predict(scaled_combined_filtered)

    count_cluster0_combined_filtered = int(np.sum(clusters_combined_filtered == 0))
    count_cluster1_combined_filtered = int(np.sum(clusters_combined_filtered == 1))
    total_combined_filtered = len(clusters_combined_filtered)
    overall_avg_combined_filtered = np.mean(features_combined_filtered[:,0])
    cluster0_avg_combined_filtered = np.mean(features_combined_filtered[clusters_combined_filtered == 0, 0]) if np.any(clusters_combined_filtered == 0) else float('nan')
    cluster1_avg_combined_filtered = np.mean(features_combined_filtered[clusters_combined_filtered == 1, 0]) if np.any(clusters_combined_filtered == 1) else float('nan')

    # 回答値が大きいものをcluster1とする
    if cluster0_avg_combined_filtered > cluster1_avg_combined_filtered:
        clusters_combined_filtered = np.where(clusters_combined_filtered == 0, 1, 0)
        cluster0_avg_combined_filtered, cluster1_avg_combined_filtered = cluster1_avg_combined_filtered, cluster0_avg_combined_filtered
        count_cluster0_combined_filtered, count_cluster1_combined_filtered = count_cluster1_combined_filtered, count_cluster0_combined_filtered

    print("\n全体データのクラスタ分布（ex1_is_first=1のex1_estimateとex2_is_first=1のex2_estimateの平均）")
    print(f"全体: {count_cluster0_combined_filtered}, {count_cluster1_combined_filtered}, {total_combined_filtered}  平均: {overall_avg_combined_filtered:.2f} (cluster0: {cluster0_avg_combined_filtered:.2f}, cluster1: {cluster1_avg_combined_filtered:.2f})")

# サマリー形式（ex1_estimate）のクラスタリング（ex1_is_first=1のみ使用）
grouped_summary = df_summary.groupby('user_id')
user_ids_summary = []
features_summary = []
for uid, group in grouped_summary:
    user_ids_summary.append(uid)
    features_summary.append(group['ex1_estimate'].mean())
features_summary = np.array(features_summary).reshape(-1, 1)

scaler_summary = StandardScaler()
scaled_summary = scaler_summary.fit_transform(features_summary)
kmeans_summary = KMeans(n_clusters=2, random_state=42)
clusters_summary = kmeans_summary.fit_predict(scaled_summary)

count_cluster0_summary = int(np.sum(clusters_summary == 0))
count_cluster1_summary = int(np.sum(clusters_summary == 1))
total_summary = len(clusters_summary)
overall_avg_summary = np.mean(features_summary[:,0])
cluster0_avg_summary = np.mean(features_summary[clusters_summary == 0, 0]) if np.any(clusters_summary == 0) else float('nan')
cluster1_avg_summary = np.mean(features_summary[clusters_summary == 1, 0]) if np.any(clusters_summary == 1) else float('nan')

# 回答値が大きいものをcluster1とする
if cluster0_avg_summary > cluster1_avg_summary:
    clusters_summary = np.where(clusters_summary == 0, 1, 0)
    cluster0_avg_summary, cluster1_avg_summary = cluster1_avg_summary, cluster0_avg_summary
    count_cluster0_summary, count_cluster1_summary = count_cluster1_summary, count_cluster0_summary

print("\nサマリー形式データのクラスタ分布（ex1_is_first=1のみ使用）")
print(f"全体: {count_cluster0_summary}, {count_cluster1_summary}, {total_summary}  平均: {overall_avg_summary:.2f} (cluster0: {cluster0_avg_summary:.2f}, cluster1: {cluster1_avg_summary:.2f})")

# オンライン形式（ex2_estimate）のクラスタリング
grouped_online = df_online.groupby('user_id')
user_ids_online = []
features_online = []
for uid, group in grouped_online:
    user_ids_online.append(uid)
    features_online.append(group['ex2_estimate'].mean())
features_online = np.array(features_online).reshape(-1, 1)

scaler_online = StandardScaler()
scaled_online = scaler_online.fit_transform(features_online)
kmeans_online = KMeans(n_clusters=2, random_state=42)
clusters_online = kmeans_online.fit_predict(scaled_online)

count_cluster0_online = int(np.sum(clusters_online == 0))
count_cluster1_online = int(np.sum(clusters_online == 1))
total_online = len(clusters_online)
overall_avg_online = np.mean(features_online[:,0])
cluster0_avg_online = np.mean(features_online[clusters_online == 0, 0]) if np.any(clusters_online == 0) else float('nan')
cluster1_avg_online = np.mean(features_online[clusters_online == 1, 0]) if np.any(clusters_online == 1) else float('nan')

# 回答値が大きいものをcluster1とする
if cluster0_avg_online > cluster1_avg_online:
    clusters_online = np.where(clusters_online == 0, 1, 0)
    cluster0_avg_online, cluster1_avg_online = cluster1_avg_online, cluster0_avg_online
    count_cluster0_online, count_cluster1_online = count_cluster1_online, count_cluster0_online

print("\nオンライン形式データのクラスタ分布（ex2_is_first=1のみ使用）")
print(f"全体: {count_cluster0_online}, {count_cluster1_online}, {total_online}  平均: {overall_avg_online:.2f} (cluster0: {cluster0_avg_online:.2f}, cluster1: {cluster1_avg_online:.2f})")

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
    # 条件に合致するサブセットを抽出（Condと表示順序の条件）
    subset = df[(df['Cond'] == details["cond_val"]) & (df[details["is_first_col"]] == 1)]
    
    print(f"\nデバッグ: {label} - フィルタ後のデータ行数: {len(subset)}")
    
    # ユーザーごとにグループ化
    grouped = subset.groupby('user_id')
    user_ids = []
    features = []
    for user_id, group in grouped:
        user_ids.append(user_id)
        features.append(group[details["col"]].mean())
    
    print(f"デバッグ: {label} - ユーザー数: {len(user_ids)}")
    
    # 十分なデータがない場合はスキップ
    if len(features) < 2:
        print(f"{label}の条件でフィルタリングしたデータが不足しています（ユーザー数: {len(features)}）。スキップします。")
        continue
        
    features = np.array(features).reshape(-1, 1)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    kmeans = KMeans(n_clusters=2, random_state=42)
    clusters = kmeans.fit_predict(scaled_features)

    count_cluster0 = np.sum(clusters == 0)
    count_cluster1 = np.sum(clusters == 1)
    total = len(clusters)

    overall_avg = np.mean(features[:,0])
    cluster0_avg = np.mean(features[clusters==0, 0]) if np.any(clusters==0) else float('nan')
    cluster1_avg = np.mean(features[clusters==1, 0]) if np.any(clusters==1) else float('nan')
    
    # 平均値に応じてクラスタ番号を一定の意味に揃える処理を追加
    if cluster0_avg > cluster1_avg:
        clusters = np.where(clusters == 0, 1, 0)
        cluster0_avg, cluster1_avg = cluster1_avg, cluster0_avg
        count_cluster0, count_cluster1 = count_cluster1, count_cluster0
        
    condition_distribution[label] = {'cluster0': int(count_cluster0), 'cluster1': int(count_cluster1), 'total': total,
                                     'overall_avg': overall_avg, 'cluster0_avg': cluster0_avg, 'cluster1_avg': cluster1_avg}

    for uid, cl in zip(user_ids, clusters):
        final_results.append({
            'user_id': uid,
            'Cond': details["cond_val"],
            'condition': label,
            'cluster': cl
        })

results_df = pd.DataFrame(final_results)

print("\n条件別クラスタ分布（cluster0, cluster1, total）と平均回答値")
for condition in conditions.keys():
    if condition in condition_distribution:
        dist = condition_distribution[condition]
        print(f"{condition}: {dist['cluster0']}, {dist['cluster1']}, {dist['total']}  平均: {dist['overall_avg']:.2f} (cluster0: {dist['cluster0_avg']:.2f}, cluster1: {dist['cluster1_avg']:.2f})")
    else:
        print(f"{condition}: 0, 0, 0  平均: N/A (cluster0: N/A, cluster1: N/A)")

results_df.to_csv('user_cluster_results_filtered.csv', index=False)
print("\n詳細な結果をuser_cluster_results_filtered.csvに保存しました。")

print(f"\n総クラスタリング実施件数: {len(results_df)}")
for condition in conditions.keys():
    cond_count = len(results_df[results_df['condition'] == condition])
    print(f"{condition} の参加者数: {cond_count}")
