import pandas as pd
import numpy as np

# データ読み込み
print("データを読み込み中...")
df = pd.read_csv("final_valid_updated.csv")

# 基本情報
print(f"元データ: {len(df):,} 行, {df['user_id'].nunique():,} 人")

# 各参加者のレコード数をカウント
user_counts = df['user_id'].value_counts().sort_values()

# 統計情報
print(f"\n=== 参加者ごとのレコード数の分布 ===")
count_distribution = user_counts.value_counts().sort_index()
total_users = len(user_counts)

for count, num_users in count_distribution.items():
    percentage = (num_users / total_users) * 100
    print(f"{count}回のレコード: {num_users:,} 人 ({percentage:.1f}%)")

# 6回の参加者
valid_users = user_counts[user_counts == 6].index
print(f"\n6回のレコードがある有効な参加者: {len(valid_users):,} 人")

# 6回でない参加者の詳細
invalid_users = user_counts[user_counts != 6]

if len(invalid_users) > 0:
    print(f"\n=== 6回ではない参加者の詳細一覧 ===")
    print(f"無効な参加者数: {len(invalid_users):,} 人")
    print()
    
    # ソートして表示
    invalid_sorted = invalid_users.sort_values()
    for i, (user_id, count) in enumerate(invalid_sorted.items()):
        print(f"{i+1:3d}. {user_id} : {count} 回")
    
    print(f"\n=== 回数別の詳細 ===")
    for count in sorted(invalid_users.unique()):
        users_with_count = invalid_users[invalid_users == count]
        print(f"\n{count}回の参加者 ({len(users_with_count)} 人):")
        for j, user_id in enumerate(users_with_count.index):
            print(f"  {j+1:2d}. {user_id}")
            
else:
    print("すべての参加者が6回のレコードを持っています。")

# サマリー
print(f"\n=== 最終サマリー ===")
print(f"総参加者数: {total_users:,} 人")
print(f"有効参加者数: {len(valid_users):,} 人")
print(f"無効参加者数: {len(invalid_users):,} 人")
print(f"除外率: {(len(invalid_users) / total_users) * 100:.1f}%")

# 有効データを保存
valid_df = df[df['user_id'].isin(valid_users)].copy()
print(f"\nフィルタ後データ: {len(valid_df):,} 行, {valid_df['user_id'].nunique():,} 人")
print(f"除外されたレコード数: {len(df) - len(valid_df):,}")

output_path = "final_valid_6_samples.csv"
valid_df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"\n有効なデータを保存: {output_path}")

# 詳細を別ファイルに保存
with open("invalid_participants_detail.txt", "w", encoding="utf-8") as f:
    f.write("6回ではない参加者の詳細一覧\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"総参加者数: {total_users:,} 人\n")
    f.write(f"無効参加者数: {len(invalid_users):,} 人\n")
    f.write(f"除外率: {(len(invalid_users) / total_users) * 100:.1f}%\n\n")
    
    if len(invalid_users) > 0:
        f.write("無効な参加者一覧:\n")
        f.write("-" * 40 + "\n")
        invalid_sorted = invalid_users.sort_values()
        for i, (user_id, count) in enumerate(invalid_sorted.items()):
            f.write(f"{i+1:3d}. {user_id} : {count} 回\n")
        
        f.write(f"\n回数別の詳細:\n")
        f.write("-" * 40 + "\n")
        for count in sorted(invalid_users.unique()):
            users_with_count = invalid_users[invalid_users == count]
            f.write(f"\n{count}回の参加者 ({len(users_with_count)} 人):\n")
            for j, user_id in enumerate(users_with_count.index):
                f.write(f"  {j+1:2d}. {user_id}\n")

print("詳細レポートを保存: invalid_participants_detail.txt")
