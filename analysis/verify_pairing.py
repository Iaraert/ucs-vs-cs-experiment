import pandas as pd

# 修正後のデータを確認
df_final = pd.read_csv('final_valid_all_experiments.csv')

# サンプルユーザーで確認
sample_user = df_final['user_id'].iloc[0]
print(f"サンプルユーザー: {sample_user}")

user_data = df_final[df_final['user_id'] == sample_user]
print(f"\nデータ数: {len(user_data)}")

print("\ncover_storyとsample_numberの対応:")
for idx, row in user_data.iterrows():
    ex1_cs = row['ex1_cover_story']
    ex2_cs = row['ex2_cover_story']
    ex1_sn = row['ex1_sample_number']
    ex2_sn = row['ex2_sample_number']
    match = "✓" if ex1_cs == ex2_cs else "✗"
    print(f"  ex1: CS={ex1_cs:2} SN={ex1_sn} | ex2: CS={ex2_cs:2} SN={ex2_sn} | {match}")

# 全データでcover_storyの一致を確認
df_final['cs_match'] = (df_final['ex1_cover_story'] == df_final['ex2_cover_story'])
match_rate = df_final['cs_match'].mean() * 100
print(f"\n全データでのcover_story一致率: {match_rate:.1f}%")
print(f"一致するペア数: {df_final['cs_match'].sum()} / {len(df_final)}")

# sample_numberの一致も確認
df_final['sn_match'] = (df_final['ex1_sample_number'] == df_final['ex2_sample_number'])
sn_match_rate = df_final['sn_match'].mean() * 100
print(f"\nsample_numberの一致率: {sn_match_rate:.1f}%")
print(f"一致するペア数: {df_final['sn_match'].sum()} / {len(df_final)}")
