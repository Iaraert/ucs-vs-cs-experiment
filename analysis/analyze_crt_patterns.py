"""
analyze_crt_patterns.py

CRTの回答パターンを分析して正解を特定
"""
import pandas as pd
import numpy as np

def analyze_crt_patterns():
    """CRTの回答パターンを分析"""
    
    print("CRT回答パターン分析を開始...")
    
    # データ読み込み
    df_crt = pd.read_csv('honban/crt_data_exp3.csv')
    df_final = pd.read_csv('final_valid.csv')
    
    print(f"CRTデータ: {len(df_crt)}行")
    print(f"final_validデータ: {len(df_final)}行")
    
    # 既存のcrt_correct_cntとマージ
    merged = df_final.merge(df_crt, on='user_id', how='inner')
    merged = merged.dropna(subset=['crt_correct_cnt'])
    
    print(f"マージ後（CRT正答数が記録されているデータ）: {len(merged)}行")
    
    # 各問題の回答パターンを分析
    print(f"\n=== 各問題の回答分布 ===")
    
    for col in ['q1', 'q2', 'q3']:
        print(f"\n{col}の回答分布:")
        counts = merged[col].value_counts().sort_index()
        print(counts.head(10))
    
    # 正答数別の回答パターンを分析
    print(f"\n=== 正答数別の回答パターン ===")
    
    for score in sorted(merged['crt_correct_cnt'].unique()):
        if pd.notna(score):
            subset = merged[merged['crt_correct_cnt'] == score]
            print(f"\n正答数 {score} のグループ (n={len(subset)}):")
            
            for col in ['q1', 'q2', 'q3']:
                mode_value = subset[col].mode()
                if len(mode_value) > 0:
                    most_common = mode_value.iloc[0]
                    count = (subset[col] == most_common).sum()
                    print(f"  {col}: {most_common} ({count}/{len(subset)} = {count/len(subset):.1%})")
    
    # 正答推定: 正答数3の人たちの最頻値を見る
    perfect_scores = merged[merged['crt_correct_cnt'] == 3]
    if len(perfect_scores) > 0:
        print(f"\n=== 正答数3の人たちの回答パターン (n={len(perfect_scores)}) ===")
        estimated_answers = {}
        for col in ['q1', 'q2', 'q3']:
            mode_values = perfect_scores[col].mode()
            if len(mode_values) > 0:
                estimated_answers[col] = mode_values.iloc[0]
                count = (perfect_scores[col] == estimated_answers[col]).sum()
                print(f"{col}の推定正解: {estimated_answers[col]} ({count}/{len(perfect_scores)} = {count/len(perfect_scores):.1%})")
        
        # 推定正解で再計算
        print(f"\n=== 推定正解での再計算 ===")
        df_crt_recalc = df_crt.copy()
        
        for col in ['q1', 'q2', 'q3']:
            if col in estimated_answers:
                df_crt_recalc[f'{col}_correct_new'] = (df_crt_recalc[col] == estimated_answers[col]).astype(int)
        
        df_crt_recalc['crt_correct_total_new'] = (
            df_crt_recalc['q1_correct_new'] + 
            df_crt_recalc['q2_correct_new'] + 
            df_crt_recalc['q3_correct_new']
        )
        
        # 再検証
        merged_new = df_final.merge(
            df_crt_recalc[['user_id', 'crt_correct_total_new']], 
            on='user_id', how='inner'
        )
        merged_new = merged_new.dropna(subset=['crt_correct_cnt'])
        
        if len(merged_new) > 0:
            matches = (merged_new['crt_correct_cnt'] == merged_new['crt_correct_total_new']).sum()
            print(f"新しい正解での一致率: {matches}/{len(merged_new)} ({matches/len(merged_new):.1%})")
            
            # 推定正解を保存
            corrected_scores = df_crt_recalc[['user_id', 'q1', 'q2', 'q3', 
                                            'q1_correct_new', 'q2_correct_new', 'q3_correct_new',
                                            'crt_correct_total_new']].copy()
            corrected_scores.to_csv('crt_corrected_scores.csv', index=False, encoding='utf-8-sig')
            print(f"→ 修正済みCRTスコアを保存: crt_corrected_scores.csv")
            
            # 推定正解の情報を保存
            with open('crt_estimated_answers.txt', 'w', encoding='utf-8') as f:
                f.write("CRT推定正解:\n")
                for col, answer in estimated_answers.items():
                    f.write(f"{col}: {answer}\n")
            print(f"→ 推定正解を保存: crt_estimated_answers.txt")
    
    else:
        print("正答数3のデータが見つかりませんでした")

if __name__ == "__main__":
    analyze_crt_patterns()
    print("\n=== CRTパターン分析完了 ===")
