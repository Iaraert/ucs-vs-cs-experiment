#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import ast
import pandas as pd

def transform_stimuli_data(input_file='data/estimations_exp1.csv', output_file='data/estimations_exp1.csv'):
    """
    estimations_exp1.csvファイルのstimuli列（辞書形式）をa_value, b_value, c_value, d_value列に変換する
    元のファイルを上書きして新しい形式に変更する
    
    Args:
        input_file (str): 入力ファイルのパス
        output_file (str): 出力ファイルのパス（デフォルトは入力ファイルと同じ）
    
    Returns:
        bool: 変換が成功したかどうか
    """
    try:
        # プロジェクトルートからの相対パスを解決
        input_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), input_file)
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_file)
        
        # CSVファイルの読み込み
        df = pd.read_csv(input_path)
        
        # 新しいデータフレームを作成
        new_df = pd.DataFrame()
        new_df['user_id'] = df['user_id']
        new_df['number'] = df['number']
        
        # 各行を処理
        for idx, row in df.iterrows():
            # 辞書文字列をPythonの辞書に変換
            try:
                stimuli_dict = ast.literal_eval(row['stimuli'])
                
                # 辞書から値を抽出して新しい列に格納
                new_df.at[idx, 'a_value'] = stimuli_dict.get('a')
                new_df.at[idx, 'b_value'] = stimuli_dict.get('b')
                new_df.at[idx, 'c_value'] = stimuli_dict.get('c')
                new_df.at[idx, 'd_value'] = stimuli_dict.get('d')
                new_df.at[idx, 'estimation'] = row['estimation']
                new_df.at[idx, 'sample_type'] = stimuli_dict.get('sample_type')
                
                # タイムスタンプがあれば追加
                if len(df.columns) >= 6 and df.columns[5] != '':
                    new_df.at[idx, 'timestamp'] = row[df.columns[5]]
            except (SyntaxError, ValueError) as e:
                print(f"行 {idx} の刺激データの解析に失敗しました: {e}")
                continue
        
        # 変換結果を保存
        new_df.to_csv(output_path, index=False)
        print(f"データを {output_path} に正常に保存しました。")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    transform_stimuli_data()