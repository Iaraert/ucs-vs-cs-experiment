import pandas as pd
import numpy as np

# データ読み込み
df = pd.read_csv("final_valid_updated.csv")
print(f"元データ: {len(df)} 行, {df['user_id'].nunique()} 人")

# 各参加者のレコード数をカウント
user_counts = df['user_id'].value_counts().sort_index()
print(f"\n=== 参加者ごとのレコード数の分布 ===")
count_distribution = user_counts.value_counts().sort_index()
for count, num_users in count_distribution.items():
    print(f"{count}回のレコード: {num_users} 人")

# 6回ちょうどの参加者のみを抽出
valid_users = user_counts[user_counts == 6].index
print(f"\n6回のレコードがある有効な参加者: {len(valid_users)} 人")

# 有効でない参加者の詳細
invalid_users = user_counts[user_counts != 6]
if len(invalid_users) > 0:
    print(f"\n=== 無効な参加者の詳細 ===")
    for user_id, count in invalid_users.items():
        print(f"  {user_id}: {count} 回")

# 有効な参加者のデータのみを抽出
valid_df = df[df['user_id'].isin(valid_users)].copy()
print(f"\nフィルタ後データ: {len(valid_df)} 行, {valid_df['user_id'].nunique()} 人")

# サンプル：各参加者のサンプル番号をチェック
print(f"\n=== サンプル番号の完全性チェック（最初の3人） ===")
sample_users = valid_users[:3]
for user_id in sample_users:
    user_data = valid_df[valid_df['user_id'] == user_id]
    ex1_samples = sorted(user_data[user_data['ex1_is_first'] == 1]['ex1_sample_number'].unique())
    ex2_samples = sorted(user_data[user_data['ex2_is_first'] == 1]['ex2_sample_number'].unique())
    print(f"  {user_id[:15]}... ex1: {ex1_samples}, ex2: {ex2_samples}")

# 有効なデータを新しいファイルに保存
output_path = "final_valid_6_samples.csv"
valid_df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"\n有効なデータを保存: {output_path}")
print(f"除外された参加者数: {df['user_id'].nunique() - len(valid_users)}")
