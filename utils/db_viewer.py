import sys
import os

# プロジェクトルートへのパスを追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.database import Database

def display_database_info():
    """データベースの情報を表示する"""
    db = Database()
    table_info = db.get_db_info()

    if "error" in table_info:
        print(f"エラーが発生しました: {table_info['error']}")
        return

    print("データベース内のテーブル一覧:")
    for table_data in table_info:
        print(f"- {table_data['name']}")

        print(f"\n{table_data['name']}テーブルの内容:")
        print(f"カラム構造: {table_data['columns']}")
        print(f"レコード数: {table_data['row_count']}")

        for i, row in enumerate(table_data['sample_data']):
            print(f"  {i+1}. {row}")

        if table_data['row_count'] > 5:
            print(f"  ...他に{table_data['row_count']-5}件のレコードがあります")
        print()

if __name__ == "__main__":
    display_database_info()