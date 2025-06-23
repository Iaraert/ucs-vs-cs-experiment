#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースをリセットするスクリプト
すべてのテーブルの内容をクリアし、カウンターを0にリセットします
"""

import os
import sys
import sqlite3
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database

def reset_database(db_path=None):
    """
    データベースをリセットする
    
    Args:
        db_path (str, optional): データベースファイルのパス
    """
    try:
        # データベースインスタンスを作成
        db = Database(db_path)
        
        print(f"データベースのリセットを開始します...")
        print(f"対象ファイル: {db.db_path}")
        
        # データベース接続
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # トランザクション開始
        conn.execute("BEGIN TRANSACTION")
        
        # 1. allocation_historyテーブルをクリア
        cursor.execute("DELETE FROM allocation_history")
        deleted_allocation = cursor.rowcount
        print(f"- allocation_history: {deleted_allocation}件のレコードを削除")
        
        # 2. experiment_path_historyテーブルをクリア
        cursor.execute("DELETE FROM experiment_path_history")
        deleted_path = cursor.rowcount
        print(f"- experiment_path_history: {deleted_path}件のレコードを削除")
        
        # 3. condition_countersをリセット
        cursor.execute("UPDATE condition_counters SET count = 0")
        updated_conditions = cursor.rowcount
        print(f"- condition_counters: {updated_conditions}件のカウンターをリセット")
        
        # 4. experiment_path_countersをリセット
        cursor.execute("UPDATE experiment_path_counters SET count = 0")
        updated_paths = cursor.rowcount
        print(f"- experiment_path_counters: {updated_paths}件のカウンターをリセット")
        
        # 5. sqlite_sequenceテーブルをリセット（AUTO_INCREMENTカウンターをリセット）
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name IN ('allocation_history', 'experiment_path_history')")
        updated_sequences = cursor.rowcount
        print(f"- sqlite_sequence: {updated_sequences}件のシーケンスをリセット")
        
        # コミット
        conn.commit()
        
        print(f"\n✅ データベースリセットが完了しました！")
        print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # リセット後の状態を確認
        print("\n--- リセット後の状態確認 ---")
        cursor.execute("SELECT condition_name, count FROM condition_counters")
        conditions = cursor.fetchall()
        print("condition_counters:")
        for condition in conditions:
            print(f"  - {condition[0]}: {condition[1]}")
            
        cursor.execute("SELECT path_type, count FROM experiment_path_counters")
        paths = cursor.fetchall()
        print("experiment_path_counters:")
        for path in paths:
            print(f"  - {path[0]}: {path[1]}")
            
        cursor.execute("SELECT COUNT(*) FROM allocation_history")
        alloc_count = cursor.fetchone()[0]
        print(f"allocation_history: {alloc_count}件")
        
        cursor.execute("SELECT COUNT(*) FROM experiment_path_history")
        path_count = cursor.fetchone()[0]
        print(f"experiment_path_history: {path_count}件")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

def confirm_reset():
    """リセットの確認を行う"""
    print("⚠️  データベースのリセットを実行します")
    print("この操作により、以下のデータがすべて削除されます:")
    print("  - すべての条件割り当て履歴")
    print("  - すべての実験経路割り当て履歴")
    print("  - すべてのカウンター値")
    print()
    
    response = input("本当にリセットしますか？ (yes/no): ").strip().lower()
    return response in ['yes', 'y']

def main():
    """メイン関数"""
    print("=" * 50)
    print("データベースリセットツール")
    print("=" * 50)
    
    # 確認
    if not confirm_reset():
        print("リセットがキャンセルされました。")
        return
    
    # リセット実行
    reset_database()

if __name__ == "__main__":
    main()
