"""
create_crt_scores.py

参加者IDごとのCRTの正答数を計算して別ファイルに保存
"""
import pandas as pd
import numpy as np

def calculate_crt_scores():
    """CRTデータから正答数を計算"""
    
    # CRTの正解
    CORRECT_ANSWERS = {
        'q1': 5,   # バットとボール問題
        'q2': 5,   # 機械の問題  
        'q3': 47   # 池の問題
    }
    
    print("CRTスコア計算を開始...")
    
    # CRTデータの読み込み
    try:
        df_crt = pd.read_csv('honban/crt_data_exp3.csv')
        print(f"CRTデータ読み込み完了: {len(df_crt)}行")
    except FileNotFoundError:
        print("エラー: honban/crt_data_exp3.csvが見つかりません")
        return
    
    # 各問題の正答数を計算
    df_crt['q1_correct'] = (df_crt['q1'] == CORRECT_ANSWERS['q1']).astype(int)
    df_crt['q2_correct'] = (df_crt['q2'] == CORRECT_ANSWERS['q2']).astype(int)
    df_crt['q3_correct'] = (df_crt['q3'] == CORRECT_ANSWERS['q3']).astype(int)
    
    # 総正答数を計算
    df_crt['crt_correct_total'] = (
        df_crt['q1_correct'] + df_crt['q2_correct'] + df_crt['q3_correct']
    )
    
    # 結果の統計
    print(f"\n=== CRT正答数の統計 ===")
    print(f"参加者数: {len(df_crt)}")
    print(f"平均正答数: {df_crt['crt_correct_total'].mean():.2f}")
    print(f"正答数の分布:")
    print(df_crt['crt_correct_total'].value_counts().sort_index())
    
    # 各問題の正答率
    print(f"\n=== 各問題の正答率 ===")
    print(f"Q1 (バットとボール): {df_crt['q1_correct'].mean():.1%}")
    print(f"Q2 (機械): {df_crt['q2_correct'].mean():.1%}")
    print(f"Q3 (池): {df_crt['q3_correct'].mean():.1%}")
    
    # 詳細データの保存
    detailed_output = df_crt[['user_id', 'q1', 'q2', 'q3', 'q1_correct', 
                             'q2_correct', 'q3_correct', 'crt_correct_total']].copy()
    detailed_output.to_csv('crt_detailed_scores.csv', index=False, encoding='utf-8-sig')
    print(f"\n→ 詳細データを保存: crt_detailed_scores.csv")
    
    # IDごとの正答数のみの簡潔版
    summary_output = df_crt[['user_id', 'crt_correct_total']].copy()
    summary_output.to_csv('crt_scores_by_user.csv', index=False, encoding='utf-8-sig')
    print(f"→ 正答数のみを保存: crt_scores_by_user.csv")
    
    # final_valid.csvとの突合確認
    try:
        df_final = pd.read_csv('final_valid.csv')
        print(f"\n=== final_valid.csvとの突合 ===")
        print(f"final_valid.csvの参加者数: {len(df_final['user_id'].unique())}")
        
        # CRTデータがある参加者
        crt_users = set(df_crt['user_id'])
        final_users = set(df_final['user_id'].unique())
        
        print(f"CRTデータがある参加者: {len(crt_users)}")
        print(f"両方にある参加者: {len(crt_users & final_users)}")
        print(f"final_valid.csvにのみある参加者: {len(final_users - crt_users)}")
        print(f"CRTデータにのみある参加者: {len(crt_users - final_users)}")
        
        # final_valid.csvのcrt_correct_cntと比較
        if 'crt_correct_cnt' in df_final.columns:
            # CRTデータとマージ
            merged = df_final.merge(summary_output, on='user_id', how='left')
            
            # 既存のcrt_correct_cntと新しい計算結果を比較
            matched_users = merged.dropna(subset=['crt_correct_cnt', 'crt_correct_total'])
            if len(matched_users) > 0:
                matches = (matched_users['crt_correct_cnt'] == matched_users['crt_correct_total']).sum()
                print(f"\n既存データとの一致: {matches}/{len(matched_users)} ({matches/len(matched_users):.1%})")
                
                # 不一致の詳細
                mismatches = matched_users[
                    matched_users['crt_correct_cnt'] != matched_users['crt_correct_total']
                ]
                if len(mismatches) > 0:
                    print(f"不一致データ数: {len(mismatches)}")
                    print("不一致例（最初の5件）:")
                    print(mismatches[['user_id', 'crt_correct_cnt', 'crt_correct_total']].head())
        
    except FileNotFoundError:
        print("final_valid.csvが見つかりませんでした")
    
    return df_crt

if __name__ == "__main__":
    calculate_crt_scores()
    print("\n=== CRTスコア計算完了 ===")
