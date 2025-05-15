import sqlite3
import os

def check_database():
    try:
        # データベースファイルへのパス
        db_path = os.path.join('.', 'data', 'participant_allocation.db')

        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # テーブル一覧の取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print("データベース内のテーブル一覧:")
        for table in tables:
            print(f"- {table[0]}")

        # 各テーブルの内容を表示
        for table_name in [row[0] for row in tables]:
            print(f"\n{table_name}テーブルの内容:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("カラム構造:", [col[1] for col in columns])

            # データ取得
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            print(f"レコード数: {len(rows)}")

            # 最大5件まで表示
            for i, row in enumerate(rows[:5]):
                print(f"  {i+1}. {row}")

            if len(rows) > 5:
                print(f"  ...他に{len(rows)-5}件のレコードがあります")

        conn.close()

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    check_database()