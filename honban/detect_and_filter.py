import pandas as pd
import numpy as np
from collections import defaultdict
import time

# =========================================================
#  パラメータ設定（必要に応じて変更）
# =========================================================
SIMILAR_THD          = 3   # 類似判定幅 (±3)
MIN_REPEATS          = 5   # 類似値がこの回数以上 → similar_answers

# =========================================================
#  ユーティリティ関数
# =========================================================
def check_similar_answers(grp: pd.DataFrame,
                          similar_thd: int = SIMILAR_THD,
                          min_repeats: int = MIN_REPEATS) -> bool:
    """同一/類似回答が min_repeats 回以上あるか判定"""
    est = grp['estimation'].to_numpy()
    for v in est:
        n_similar = ((est >= v - similar_thd) & (est <= v + similar_thd)).sum()
        if n_similar >= min_repeats:
            return True
    return False

def check_short_duration(grp: pd.DataFrame, duration_threshold_sec: int) -> bool:
    """1 回目から 6 回目までの総回答時間 < threshold なら True"""
    t_min = pd.to_datetime(grp['timestamp']).min()
    t_max = pd.to_datetime(grp['timestamp']).max()
    duration = (t_max - t_min).total_seconds()
    return duration < duration_threshold_sec

def pivot_estimation(df_phase: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """6 行回答を wide 形式に変換 (est1..est6, ts1..ts6)"""
    df_phase = df_phase.sort_values(['user_id', 'timestamp']).copy()
    df_phase['order'] = df_phase.groupby('user_id').cumcount() + 1  # 1..6
    est_wide = df_phase.pivot(index='user_id', columns='order', values='estimation')
    est_wide = est_wide.add_prefix(f'{prefix}_est')
    dur = (
        df_phase.groupby('user_id')['timestamp']
        .apply(lambda s: (pd.to_datetime(s.max()) - pd.to_datetime(s.min())).total_seconds())
        .rename(f'{prefix}_duration_sec')
    )
    return pd.concat([est_wide, dur], axis=1)

# =========================================================
#  メイン処理
# =========================================================
if __name__ == '__main__':
    print("final.csvベースのデータ処理を開始します...")
    
    # === final.csvの読み込み ===
    df_final = pd.read_csv('final.csv')
    print(f"final.csv読み込み完了: {len(df_final)}行")
    
    # === participant_id.csvの読み込みとフィルタリング ===
    df_participants = pd.read_csv('honban/participant_id.csv')
    valid_ids = set(df_participants['user_id'])
    df_final = df_final[df_final['user_id'].isin(valid_ids)]
    print(f"participant_id.csvに基づくフィルタリング完了: {len(df_final)}行")
    
    # === 関連データの読み込み ===
    df_imc = pd.read_csv('honban/imc_data_exp2.csv')
    df_crt = pd.read_csv('honban/crt_data_exp3.csv')
    
    # IMC合格フラグ
    df_imc['imc_pass'] = df_imc.get('result', 1).astype(int)
    
    # final.csvの欠損データを補完
    # IMCデータをマージ
    df_final = df_final.merge(
        df_imc[['user_id', 'imc_pass']], 
        on='user_id', how='left', suffixes=('', '_new')
    )
    
    # 欠損値を新しいデータで補完
    df_final['imc_pass'] = df_final['imc_pass'].fillna(df_final.get('imc_pass_new', 0))
    
    # 不要な列を削除
    cols_to_drop = [c for c in df_final.columns if c.endswith('_new')]
    df_final = df_final.drop(columns=cols_to_drop)
    
    print("IMCデータの補完完了")
    
    # === 除外基準の適用 ===
    excluded_ids = set()
    exclusion_reasons = defaultdict(list)
    
    # 1. IMC不合格
    imc_fail = df_final[df_final['imc_pass'] == 0]['user_id'].unique()
    excluded_ids.update(imc_fail)
    for uid in imc_fail:
        exclusion_reasons[uid].append('IMC_fail')
    
    # 2. is_first=1の初回回答からCRT回答までの時間による除外
    # CRTタイムスタンプをユーザーごとに取得
    df_crt['timestamp'] = pd.to_datetime(df_crt['timestamp'], errors='coerce')
    crt_times = df_crt.groupby('user_id')['timestamp'].first()
    
    # is_first=1の初回回答時刻をユーザーごとに取得
    df_final['ex1_timestamp'] = pd.to_datetime(df_final['ex1_timestamp'], errors='coerce')
    df_final['ex2_timestamp'] = pd.to_datetime(df_final['ex2_timestamp'], errors='coerce')
    
    # 各ユーザーのis_first=1の初回回答時刻を取得
    first_response_times = {}
    for user_id, group in df_final.groupby('user_id'):
        # ex1とex2でis_first=1の最初の回答を見つける
        ex1_first = group[group['ex1_is_first'] == 1]['ex1_timestamp'].min()
        ex2_first = group[group['ex2_is_first'] == 1]['ex2_timestamp'].min()
        
        # 両方ともNaNでない場合は早い方、片方がNaNの場合はもう片方を使用
        if pd.notna(ex1_first) and pd.notna(ex2_first):
            first_response_times[user_id] = min(ex1_first, ex2_first)
        elif pd.notna(ex1_first):
            first_response_times[user_id] = ex1_first
        elif pd.notna(ex2_first):
            first_response_times[user_id] = ex2_first
    
    # 初回回答からCRT回答までの時間を計算し、外れ値を検出
    total_durations = []
    for user_id in first_response_times.keys():
        if user_id in crt_times.index:
            first_time = first_response_times[user_id]
            crt_time = crt_times[user_id]
            if pd.notna(first_time) and pd.notna(crt_time):
                duration = (crt_time - first_time).total_seconds()
                total_durations.append((user_id, duration))
    
    if total_durations:
        # 時間の外れ値を検出（5%ile未満、95%ile超過）
        durations_series = pd.Series([d[1] for d in total_durations])
        duration_q = durations_series.quantile([0.05, 0.95])
        
        for user_id, duration in total_durations:
            if duration < duration_q[0.05] or duration > duration_q[0.95]:
                excluded_ids.add(user_id)
                exclusion_reasons[user_id].append('time_outlier')
        
        print(f"時間外れ値除外: {duration_q[0.05]:.1f}秒未満または{duration_q[0.95]:.1f}秒超過")
    
    # 3. 各参加者のデータ行数チェック（12行でないもの）
    user_counts = df_final['user_id'].value_counts()
    incomplete_users = user_counts[user_counts != 6].index
    excluded_ids.update(incomplete_users)
    for uid in incomplete_users:
        exclusion_reasons[uid].append('incomplete_data')
    
    # 4. 推定値一定ユーザー
    estimation_var = df_final.groupby('user_id')[['ex1_estimate', 'ex2_estimate']].apply(
        lambda x: x.nunique().sum()
    )
    const_users = estimation_var[estimation_var <= 2].index
    excluded_ids.update(const_users)
    for uid in const_users:
        exclusion_reasons[uid].append('constant_estimation')    
    print(f"除外対象ユーザー数: {len(excluded_ids)}")
    
    # === データ分割 ===
    df_valid = df_final[~df_final['user_id'].isin(excluded_ids)].copy()
    df_excluded = df_final[df_final['user_id'].isin(excluded_ids)].copy()
    
    print(f"有効ユーザー数: {len(df_valid['user_id'].unique())}")
    print(f"除外ユーザー数: {len(df_excluded['user_id'].unique())}")
    
    # === 結果保存（final.csvと同じデータ構造で保存） ===
    df_valid.to_csv('honban/final_valid.csv', index=False, encoding='utf-8')
    df_excluded.to_csv('honban/final_excluded.csv', index=False, encoding='utf-8')
    
    # 除外理由の保存
    exclusion_log = []
    for uid, reasons in exclusion_reasons.items():
        exclusion_log.append({
            'user_id': uid,
            'exclusion_reasons': ';'.join(reasons)
        })
    pd.DataFrame(exclusion_log).to_csv('honban/exclusion_reasons.csv', index=False)
    
    print("処理完了:")
    print(f"  有効データ: honban/final_valid.csv ({len(df_valid)}行)")
    print(f"  除外データ: honban/final_excluded.csv ({len(df_excluded)}行)")
    print(f"  除外理由: honban/exclusion_reasons.csv ({len(exclusion_log)}ユーザー)")
