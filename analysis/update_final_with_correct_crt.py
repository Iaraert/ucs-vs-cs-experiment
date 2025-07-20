"""
update_final_with_correct_crt.py

正しいCRTスコアでfinal_valid.csvを更新
"""
import pandas as pd
import numpy as np

def update_final_with_correct_crt():
    """正しいCRTスコアでfinal_valid.csvを更新"""
    
    print("final_valid.csvのCRTスコア更新を開始...")
    
    # データ読み込み
    df_final = pd.read_csv('final_valid.csv')
    df_crt_corrected = pd.read_csv('crt_corrected_scores.csv')
    
    print(f"final_valid.csv: {len(df_final)}行, {len(df_final['user_id'].unique())}ユーザー")
    print(f"CRT修正データ: {len(df_crt_corrected)}行")
    
    # 現在のCRTスコアの統計
    print(f"\n=== 更新前のCRTスコア統計 ===")
    if 'crt_correct_cnt' in df_final.columns:
        print("既存のcrt_correct_cnt分布:")
        print(df_final['crt_correct_cnt'].value_counts().sort_index())
        print(f"平均: {df_final['crt_correct_cnt'].mean():.2f}")
    
    # CRTスコアをマージ
    # まず古いCRTスコアをバックアップ
    if 'crt_correct_cnt' in df_final.columns:
        df_final['crt_correct_cnt_old'] = df_final['crt_correct_cnt']
    
    # 新しいCRTスコアをマージ
    df_final = df_final.drop(columns=['crt_correct_cnt'], errors='ignore')
    df_final = df_final.merge(
        df_crt_corrected[['user_id', 'crt_correct_total_new']],
        on='user_id',
        how='left'
    )
    df_final = df_final.rename(columns={'crt_correct_total_new': 'crt_correct_cnt'})
    
    # 更新後の統計
    print(f"\n=== 更新後のCRTスコア統計 ===")
    print("新しいcrt_correct_cnt分布:")
    crt_counts = df_final['crt_correct_cnt'].value_counts().sort_index()
    print(crt_counts)
    print(f"平均: {df_final['crt_correct_cnt'].mean():.2f}")
    print(f"CRTデータがある参加者: {df_final['crt_correct_cnt'].notna().sum()}")
    print(f"CRTデータがない参加者: {df_final['crt_correct_cnt'].isna().sum()}")
    
    # 比較（古いデータがある場合）
    if 'crt_correct_cnt_old' in df_final.columns:
        comparison = df_final[['user_id', 'crt_correct_cnt_old', 'crt_correct_cnt']].dropna()
        if len(comparison) > 0:
            matches = (comparison['crt_correct_cnt_old'] == comparison['crt_correct_cnt']).sum()
            print(f"\n古いスコアとの一致: {matches}/{len(comparison)} ({matches/len(comparison):.1%})")
    
    # 更新されたファイルを保存
    df_final_output = df_final.drop(columns=['crt_correct_cnt_old'], errors='ignore')
    df_final_output.to_csv('final_valid_updated.csv', index=False, encoding='utf-8-sig')
    print(f"\n→ 更新されたファイルを保存: final_valid_updated.csv")
    
    # 元のファイルもバックアップ
    df_final_original = pd.read_csv('final_valid.csv')
    df_final_original.to_csv('final_valid_backup.csv', index=False, encoding='utf-8-sig')
    print(f"→ 元ファイルをバックアップ: final_valid_backup.csv")
    
    # 簡潔なCRTスコアファイルも作成（相関分析用）
    crt_summary = df_crt_corrected[['user_id', 'crt_correct_total_new']].copy()
    crt_summary = crt_summary.rename(columns={'crt_correct_total_new': 'crt_score'})
    crt_summary.to_csv('user_crt_scores_final.csv', index=False, encoding='utf-8-sig')
    print(f"→ 最終CRTスコアファイル: user_crt_scores_final.csv")
    
    return df_final_output

if __name__ == "__main__":
    updated_df = update_final_with_correct_crt()
    print("\n=== CRTスコア更新完了 ===")
