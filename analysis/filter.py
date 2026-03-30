#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全実験（exp1, exp1_2, exp2, exp3）のデータを統合し、
以下の基準で除外する：
1. すべての実験（exp1とexp1_2）に参加していない
2. IMCでresult=Falseの参加者
3. 回答時間の極端値（上位・下位5%）

final_valid_6_samples.csvのような形式で出力する
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# ex1_2 sample_number remap (24,18,12,26,20,14 -> 1..6)
EX2_SAMPLE_REMAP = {24: 1, 18: 2, 12: 3, 26: 4, 20: 5, 14: 6}

def remap_ex2_sample_number(value):
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return value
    return EX2_SAMPLE_REMAP.get(ivalue, value)

# =========================================================
#  パス設定
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HONBAN_DIR = BASE_DIR / "honban"
ANALYSIS_DIR = BASE_DIR / "analysis"

# 入力ファイル（honbanディレクトリから読み込む）
EST1_FILE = HONBAN_DIR / "estimations_exp1.csv"
EST2_FILE = HONBAN_DIR / "保存" / "estimations_exp1_2.csv"
USER1_FILE = HONBAN_DIR / "user_data_exp1.csv"
USER2_FILE = HONBAN_DIR / "user_data_exp1_2.csv"
IMC_FILE = HONBAN_DIR / "imc_data_exp2.csv"
CRT_FILE = HONBAN_DIR / "保存" / "crt_data_exp3.csv"
PARTICIPANT_FILE = HONBAN_DIR / "participant_id.csv"  # 有効な参加者リスト

# 出力ファイル
OUTPUT_FILE = ANALYSIS_DIR / "final_valid_all_experiments.csv"
REPORT_FILE = ANALYSIS_DIR / "filtering_report.txt"

print("=" * 80)
print("全実験データの統合とフィルタリング")
print("=" * 80)

# =========================================================
#  1. データ読み込み
# =========================================================
print("\n[1] データ読み込み中...")

# Estimations データ
df_est1 = pd.read_csv(EST1_FILE)
df_est2 = pd.read_csv(EST2_FILE)
print(f"  - estimations_exp1.csv: {len(df_est1)} 行")
print(f"  - estimations_exp1_2.csv: {len(df_est2)} 行")

# User データ
df_user1 = pd.read_csv(USER1_FILE)
df_user2 = pd.read_csv(USER2_FILE)
print(f"  - user_data_exp1.csv: {len(df_user1)} 行")
print(f"  - user_data_exp1_2.csv: {len(df_user2)} 行")

# IMC データ
df_imc = pd.read_csv(IMC_FILE)
print(f"  - imc_data_exp2.csv: {len(df_imc)} 行")

# CRT データ
df_crt = pd.read_csv(CRT_FILE)
print(f"  - crt_data_exp3.csv: {len(df_crt)} 行")

# 有効な参加者リスト
df_participants = pd.read_csv(PARTICIPANT_FILE)
valid_participant_ids = set(df_participants['user_id'].dropna().astype(str).unique())
print(f"  - participant_id.csv: {len(valid_participant_ids)} 人")

# =========================================================
#  2. 実験データの統合と参加者フィルタリング
# =========================================================
print("\n[2] 実験データの統合と参加者フィルタリング中...")

# exp1のデータ準備
df_exp1 = df_est1.copy()
df_exp1['experiment'] = 'exp1'
df_exp1['block'] = 'examine1'

# exp1_2のデータ準備
df_exp2 = df_est2.copy()
df_exp2['experiment'] = 'exp1_2'
df_exp2['block'] = 'examine1_2'

# 列名を統一
common_cols = ['user_id', 'cover_story', 'a_value', 'b_value', 'c_value', 
               'd_value', 'estimation', 'is_first', 'is_symmetric', 
               'sample_number', 'timestamp', 'experiment', 'block']

# 存在する列のみ選択
df_exp1_cols = [col for col in common_cols if col in df_exp1.columns]
df_exp2_cols = [col for col in common_cols if col in df_exp2.columns]

df_exp1 = df_exp1[df_exp1_cols]
df_exp2 = df_exp2[df_exp2_cols]

# データ統合
df_all = pd.concat([df_exp1, df_exp2], ignore_index=True)

# user_idを文字列型に統一
df_all['user_id'] = df_all['user_id'].astype(str)

# participant_id.csvに記載されている参加者のみをフィルタリング
df_all = df_all[df_all['user_id'].isin(valid_participant_ids)].copy()

print(f"  - 統合後のデータ: {len(df_all)} 行")
print(f"  - participant_id.csvに基づくフィルタリング後: {df_all['user_id'].nunique()} 人")

# =========================================================
#  3. 各参加者の回答時間を計算（is_first=1の実験開始からexp3送信まで）
# =========================================================
print("\n[3] 各参加者の回答時間を計算中（is_first=1の実験開始からexp3送信まで）...")

# timestampを日時型に変換
df_all['timestamp'] = pd.to_datetime(df_all['timestamp'], errors='coerce')
df_crt['timestamp'] = pd.to_datetime(df_crt['timestamp'], errors='coerce')

# CRTデータのuser_idを文字列型に統一
df_crt['user_id'] = df_crt['user_id'].astype(str)

# 各ユーザーのis_first=1の開始時刻とexp3の送信時刻を取得
user_durations = []

for user_id, user_data in df_all.groupby('user_id'):
    # is_first=1のデータ（最初の実験）
    first_1_data = user_data[user_data['is_first'] == 1]
    
    # exp3（CRT）のデータを取得
    crt_data = df_crt[df_crt['user_id'] == user_id]
    
    # is_first=1とexp3の両方が存在する場合のみ計算
    if len(first_1_data) > 0 and len(crt_data) > 0:
        # is_first=1の最初の回答時刻
        start_time = first_1_data['timestamp'].min()
        # exp3の送信時刻
        end_time = crt_data['timestamp'].iloc[0]  # CRTは1回のみ
        
        duration = (end_time - start_time).total_seconds()
        
        user_durations.append({
            'user_id': user_id,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration
        })

user_duration = pd.DataFrame(user_durations)

print(f"  - 回答時間を計算できたユーザー数: {len(user_duration)} 人")
print(f"  - 回答時間の統計:")
print(f"    平均: {user_duration['duration_seconds'].mean():.1f} 秒")
print(f"    中央値: {user_duration['duration_seconds'].median():.1f} 秒")
print(f"    最小: {user_duration['duration_seconds'].min():.1f} 秒")
print(f"    最大: {user_duration['duration_seconds'].max():.1f} 秒")

# =========================================================
#  4. 除外基準の適用
# =========================================================
print("\n[4] 除外基準の適用中...")

excluded_users = set()
exclusion_reasons = {}

# --- 4.1 exp1とexp1_2の両方に参加していない参加者を除外 ---
user_exp1 = set(df_all[df_all['block'] == 'examine1']['user_id'].unique())
user_exp2 = set(df_all[df_all['block'] == 'examine1_2']['user_id'].unique())
users_with_both = user_exp1 & user_exp2
users_without_both = (user_exp1 | user_exp2) - users_with_both

print(f"  - exp1とexp1_2の両方に参加: {len(users_with_both)} 人")
print(f"  - どちらか片方のみ: {len(users_without_both)} 人")

for user in users_without_both:
    excluded_users.add(user)
    if user in user_exp1 and user not in user_exp2:
        exclusion_reasons[user] = "exp1_2に参加していない"
    else:
        exclusion_reasons[user] = "exp1に参加していない"

# --- 4.2 IMC不合格（result=False）の除外 ---
df_imc['user_id'] = df_imc['user_id'].astype(str)

# result列がFalseまたは0の参加者を除外
# bool型、int型、str型に対応
imc_fail_users = []
for idx, row in df_imc.iterrows():
    result = row['result']
    # Falseと判定されるべき値
    if result == False or result == 0 or result == '0' or result == 'False' or str(result).lower() == 'false':
        imc_fail_users.append(row['user_id'])

imc_fail_users = list(set(imc_fail_users))
print(f"  - IMC不合格（result=False）: {len(imc_fail_users)} 人")

for user in imc_fail_users:
    if user not in excluded_users:
        excluded_users.add(user)
        exclusion_reasons[user] = "IMC不合格"

# IMC合格者のリストを作成
imc_pass_users = set(df_imc['user_id'].unique()) - set(imc_fail_users)
print(f"  - IMC合格（result=True）: {len(imc_pass_users)} 人")

# IMCデータがない参加者も除外
users_without_imc = users_with_both - set(df_imc['user_id'].unique())
print(f"  - IMCデータなし: {len(users_without_imc)} 人")
for user in users_without_imc:
    if user not in excluded_users:
        excluded_users.add(user)
        exclusion_reasons[user] = "IMCデータがない"

# --- 4.3 回答時間の極端値（上位・下位5%）の除外 ---
lower_bound = user_duration['duration_seconds'].quantile(0.05)
upper_bound = user_duration['duration_seconds'].quantile(0.95)

print(f"  - 回答時間の除外閾値:")
print(f"    下位5%: {lower_bound:.1f} 秒以下")
print(f"    上位5%: {upper_bound:.1f} 秒以上")

duration_outliers = user_duration[
    (user_duration['duration_seconds'] < lower_bound) |
    (user_duration['duration_seconds'] > upper_bound)
]['user_id'].unique()

print(f"  - 回答時間の極端値: {len(duration_outliers)} 人")
for user in duration_outliers:
    if user not in excluded_users:
        excluded_users.add(user)
        duration = user_duration[user_duration['user_id'] == user]['duration_seconds'].values[0]
        if duration < lower_bound:
            exclusion_reasons[user] = f"回答時間が短すぎる ({duration:.1f}秒)"
        else:
            exclusion_reasons[user] = f"回答時間が長すぎる ({duration:.1f}秒)"

# --- 4.4 定数回答（全て同じ値）を除外 ---
constant_answer_users = df_all.groupby('user_id')['estimation'].nunique()
constant_answer_users = constant_answer_users[constant_answer_users <= 1].index.tolist()
print(f"  - 定数回答の参加者: {len(constant_answer_users)} 人")
for user in constant_answer_users:
    if user not in excluded_users:
        excluded_users.add(user)
        exclusion_reasons[user] = "全回答が同じ値"

print(f"\n  合計除外人数: {len(excluded_users)} 人")

# =========================================================
#  5. フィルタリング後のデータ作成
# =========================================================
print("\n[5] フィルタリング後のデータ作成中...")

df_valid = df_all[~df_all['user_id'].isin(excluded_users)].copy()

print(f"  - フィルタリング後のデータ: {len(df_valid)} 行")
print(f"  - 有効な参加者数: {df_valid['user_id'].nunique()} 人")

# =========================================================
#  6. Wide形式への変換（final_valid_6_samples.csv形式）
# =========================================================
print("\n[6] Wide形式への変換中...")

# まずデータの状態を確認
print(f"  - 有効データのuser_id数: {df_valid['user_id'].nunique()}")
print(f"  - examine1のデータ数: {len(df_valid[df_valid['block'] == 'examine1'])}")
print(f"  - examine1_2のデータ数: {len(df_valid[df_valid['block'] == 'examine1_2'])}")

# IMCデータをマージ
df_imc_merge = df_imc[['user_id', 'result']].copy()
df_imc_merge['user_id'] = df_imc_merge['user_id'].astype(str)
df_imc_merge.columns = ['user_id', 'imc_pass']
df_imc_merge['imc_pass'] = df_imc_merge['imc_pass'].astype(int)
df_imc_merge = df_imc_merge.drop_duplicates(subset='user_id')

# CRTデータをマージ
df_crt_merge = df_crt[['user_id', 'q1', 'q2', 'q3']].copy()
df_crt_merge['user_id'] = df_crt_merge['user_id'].astype(str)

# CRTの正解を判定（正解: q1=50, q2=5, q3=47）
df_crt_merge['crt_q1_correct'] = (df_crt_merge['q1'] == 50).astype(int)
df_crt_merge['crt_q2_correct'] = (df_crt_merge['q2'] == 5).astype(int)
df_crt_merge['crt_q3_correct'] = (df_crt_merge['q3'] == 47).astype(int)
df_crt_merge['crt_correct_cnt'] = (
    df_crt_merge['crt_q1_correct'] + 
    df_crt_merge['crt_q2_correct'] + 
    df_crt_merge['crt_q3_correct']
)
df_crt_merge = df_crt_merge[['user_id', 'crt_correct_cnt']].drop_duplicates(subset='user_id')

# 各ユーザーについて行を作成
result_rows = []

for user_id in df_valid['user_id'].unique():
    user_data_exp1 = df_valid[(df_valid['user_id'] == user_id) & (df_valid['block'] == 'examine1')].copy()
    user_data_exp2 = df_valid[(df_valid['user_id'] == user_id) & (df_valid['block'] == 'examine1_2')].copy()
    
    # データが両方存在しない場合はスキップ
    if len(user_data_exp1) == 0 or len(user_data_exp2) == 0:
        continue
    
    # exp2のsample_numberをリマップ
    user_data_exp2['sample_number_remapped'] = user_data_exp2['sample_number'].apply(remap_ex2_sample_number)
    
    # Cond（is_symmetricから判定）
    cond = user_data_exp1['is_symmetric'].iloc[0] if 'is_symmetric' in user_data_exp1.columns else None
    
    # IMC情報を取得
    imc_info = df_imc_merge[df_imc_merge['user_id'] == user_id]
    imc_pass = imc_info['imc_pass'].iloc[0] if len(imc_info) > 0 else 1
    
    # CRT情報を取得
    crt_info = df_crt_merge[df_crt_merge['user_id'] == user_id]
    crt_correct_cnt = crt_info['crt_correct_cnt'].iloc[0] if len(crt_info) > 0 else 0
    
    # sample_numberでマッチングしてペアを作成
    for _, exp1_row in user_data_exp1.iterrows():
        exp1_sample = exp1_row['sample_number']
        
        # exp2から対応するsample_number（リマップ後）を探す
        exp2_matched = user_data_exp2[user_data_exp2['sample_number_remapped'] == exp1_sample]
        
        if len(exp2_matched) == 0:
            continue  # マッチするデータがない場合はスキップ
        
        exp2_row = exp2_matched.iloc[0]
        
        new_row = {
            'user_id': user_id,
            'Cond': cond,
            'ex1_cover_story': exp1_row['cover_story'],
            'ex1_a': exp1_row['a_value'],
            'ex1_b': exp1_row['b_value'],
            'ex1_c': exp1_row['c_value'],
            'ex1_d': exp1_row['d_value'],
            'ex1_estimate': exp1_row['estimation'],
            'ex1_is_first': exp1_row['is_first'],
            'ex1_sample_number': exp1_row['sample_number'],
            'ex1_timestamp': exp1_row['timestamp'],
            'ex2_cover_story': exp2_row['cover_story'],
            'ex2_a': exp2_row['a_value'],
            'ex2_b': exp2_row['b_value'],
            'ex2_c': exp2_row['c_value'],
            'ex2_d': exp2_row['d_value'],
            'ex2_estimate': exp2_row['estimation'],
            'ex2_is_first': exp2_row['is_first'],
            'ex2_is_symmetric': exp2_row['is_symmetric'],
            'ex2_sample_number': exp2_row['sample_number_remapped'],
            'ex2_timestamp': exp2_row['timestamp'],
            'imc_pass': imc_pass,
            'crt_correct_cnt': crt_correct_cnt
        }
        result_rows.append(new_row)

df_final = pd.DataFrame(result_rows)

if len(df_final) > 0:
    print(f"  - Wide形式データ: {len(df_final)} 行")
    print(f"  - 参加者数: {df_final['user_id'].nunique()} 人")
else:
    print("  - Wide形式データ: 0 行（警告: データが作成されませんでした）")

# =========================================================
#  7. 出力
# =========================================================
print("\n[7] ファイル出力中...")

if len(df_final) > 0:
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"  - {OUTPUT_FILE.name} を保存しました")
else:
    # 空の場合でも最低限のファイルを作成
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"  - {OUTPUT_FILE.name} を保存しました（警告: データが0行です）")

# レポート出力
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("全実験データのフィルタリングレポート\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("[1] データ読み込み\n")
    f.write(f"  - estimations_exp1.csv: {len(df_est1)} 行\n")
    f.write(f"  - estimations_exp1_2.csv: {len(df_est2)} 行\n")
    f.write(f"  - 統合後: {len(df_all)} 行, {df_all['user_id'].nunique()} 人\n\n")
    
    f.write("[2] 回答時間の統計\n")
    f.write(f"  - 平均: {user_duration['duration_seconds'].mean():.1f} 秒\n")
    f.write(f"  - 中央値: {user_duration['duration_seconds'].median():.1f} 秒\n")
    f.write(f"  - 最小: {user_duration['duration_seconds'].min():.1f} 秒\n")
    f.write(f"  - 最大: {user_duration['duration_seconds'].max():.1f} 秒\n")
    f.write(f"  - 下位5%閾値: {lower_bound:.1f} 秒\n")
    f.write(f"  - 上位5%閾値: {upper_bound:.1f} 秒\n\n")
    
    f.write("[3] 除外基準\n")
    f.write(f"  - すべての実験に参加していない: {len(users_without_both)} 人\n")
    f.write(f"  - IMC不合格（result=False）: {len(imc_fail_users)} 人\n")
    f.write(f"  - IMCデータなし: {len(users_without_imc)} 人\n")
    f.write(f"  - 回答時間の極端値: {len(duration_outliers)} 人\n")
    f.write(f"  - 定数回答: {len(constant_answer_users)} 人\n")
    f.write(f"  - 合計除外: {len(excluded_users)} 人\n\n")
    
    f.write("[4] 除外された参加者の詳細\n")
    for user_id in sorted(excluded_users):
        reason = exclusion_reasons.get(user_id, "不明")
        f.write(f"  - {user_id}: {reason}\n")
    f.write("\n")
    
    f.write("[5] フィルタリング後のデータ\n")
    if len(df_final) > 0:
        f.write(f"  - データ行数: {len(df_final)} 行\n")
        f.write(f"  - 有効な参加者数: {df_final['user_id'].nunique()} 人\n")
        f.write(f"  - IMC合格率: {df_final['imc_pass'].mean()*100:.1f}%\n")
        f.write(f"  - CRT平均正解数: {df_final['crt_correct_cnt'].mean():.2f}\n")
    else:
        f.write(f"  - データ行数: 0 行（警告: データが作成されませんでした）\n")
    
print(f"  - {REPORT_FILE.name} を保存しました")

print("\n" + "=" * 80)
print("処理完了！")
print("=" * 80)
print(f"\n出力ファイル:")
print(f"  - データ: {OUTPUT_FILE}")
print(f"  - レポート: {REPORT_FILE}")
