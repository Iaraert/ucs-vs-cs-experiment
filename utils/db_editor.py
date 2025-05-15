#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import argparse
from datetime import datetime

# データベースファイルへのパス
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                     'data', 'participant_allocation.db')

def connect_to_db():
    """データベースに接続"""
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"データベース接続エラー: {e}")
        sys.exit(1)

def list_tables(conn):
    """データベース内のテーブル一覧を表示"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("データベース内のテーブル一覧:")
    for table in tables:
        print(f"- {table[0]}")
    return [table[0] for table in tables]

def show_table_structure(conn, table_name):
    """テーブルの構造を表示"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n{table_name}テーブルの構造:")
        print("ID  | 名前          | 型      | NOT NULL | デフォルト値 | プライマリキー")
        print("-" * 70)
        for col in columns:
            print(f"{col[0]:3d} | {col[1]:<13} | {col[2]:<7} | {col[3]:^8} | {col[4] if col[4] else 'なし':^11} | {col[5]:^12}")
    except sqlite3.Error as e:
        print(f"エラー: {e}")

def show_table_content(conn, table_name, limit=None):
    """テーブルの内容を表示"""
    cursor = conn.cursor()
    try:
        if limit:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        else:
            cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # カラム名を取得
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\n{table_name}テーブルの内容:")
        print(" | ".join(columns))
        print("-" * (sum(len(col) for col in columns) + 3 * len(columns)))
        
        for row in rows:
            print(" | ".join(str(cell) for cell in row))
        
        print(f"合計 {len(rows)} 件のレコード")
    except sqlite3.Error as e:
        print(f"エラー: {e}")

def execute_query(conn, query):
    """SQLクエリを実行"""
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        if query.strip().lower().startswith(('select', 'pragma')):
            rows = cursor.fetchall()
            if rows:
                # カラム名を取得（可能であれば）
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    print(" | ".join(columns))
                    print("-" * (sum(len(col) for col in columns) + 3 * len(columns)))
                
                for row in rows:
                    print(" | ".join(str(cell) for cell in row))
                print(f"合計 {len(rows)} 件のレコード")
            else:
                print("結果なし")
        else:
            conn.commit()
            print(f"クエリ実行成功: {cursor.rowcount} 行が影響を受けました")
    except sqlite3.Error as e:
        print(f"クエリ実行エラー: {e}")

def add_condition_counter(conn, condition_name, count):
    """条件カウンターを追加または更新"""
    cursor = conn.cursor()
    try:
        # まず存在チェック
        cursor.execute("SELECT count FROM condition_counters WHERE condition_name=?", (condition_name,))
        result = cursor.fetchone()
        
        if result is None:
            # 新規追加
            cursor.execute("INSERT INTO condition_counters (condition_name, count) VALUES (?, ?)", 
                         (condition_name, count))
            print(f"条件 '{condition_name}' をカウント {count} で追加しました")
        else:
            # 更新
            cursor.execute("UPDATE condition_counters SET count=? WHERE condition_name=?", 
                         (count, condition_name))
            print(f"条件 '{condition_name}' のカウントを {count} に更新しました")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"エラー: {e}")

def add_allocation_record(conn, user_id, condition_name):
    """割り当て履歴を追加"""
    cursor = conn.cursor()
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO allocation_history (user_id, condition_name, timestamp) VALUES (?, ?, ?)", 
                     (user_id, condition_name, timestamp))
        conn.commit()
        print(f"ユーザー '{user_id}' に条件 '{condition_name}' を割り当てました")
    except sqlite3.Error as e:
        print(f"エラー: {e}")

def reset_counters(conn):
    """すべての条件カウンターをリセット"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE condition_counters SET count=0")
        conn.commit()
        print("すべての条件カウンターをリセットしました")
    except sqlite3.Error as e:
        print(f"エラー: {e}")

def interactive_mode():
    """対話モード"""
    conn = connect_to_db()
    print(f"データベース '{DB_PATH}' に接続しました")
    list_tables(conn)
    
    while True:
        print("\n=== データベースエディタ ===")
        print("1: テーブル一覧を表示")
        print("2: テーブル構造を表示")
        print("3: テーブル内容を表示")
        print("4: SQLクエリを実行")
        print("5: 条件カウンターを追加/更新")
        print("6: 割り当て履歴を追加")
        print("7: 条件カウンターをリセット")
        print("q: 終了")
        
        choice = input("\n選択してください: ")
        
        if choice == '1':
            list_tables(conn)
        
        elif choice == '2':
            table_name = input("テーブル名を入力: ")
            show_table_structure(conn, table_name)
        
        elif choice == '3':
            table_name = input("テーブル名を入力: ")
            limit_input = input("表示する行数（すべて表示する場合は空白）: ")
            limit = int(limit_input) if limit_input.strip() else None
            show_table_content(conn, table_name, limit)
        
        elif choice == '4':
            query = input("SQLクエリを入力: ")
            execute_query(conn, query)
        
        elif choice == '5':
            condition_name = input("条件名: ")
            count = input("カウント値: ")
            try:
                count_value = int(count)
                add_condition_counter(conn, condition_name, count_value)
            except ValueError:
                print("カウント値は整数である必要があります")
        
        elif choice == '6':
            user_id = input("ユーザーID: ")
            condition_name = input("条件名: ")
            add_allocation_record(conn, user_id, condition_name)
        
        elif choice == '7':
            confirm = input("すべての条件カウンターをリセットしますか？(y/n): ")
            if confirm.lower() == 'y':
                reset_counters(conn)
        
        elif choice.lower() == 'q':
            break
        
        else:
            print("無効な選択です")
    
    conn.close()
    print("データベース接続を閉じました")

def main():
    parser = argparse.ArgumentParser(description='SQLiteデータベースエディタ')
    parser.add_argument('--list-tables', action='store_true', help='テーブル一覧を表示')
    parser.add_argument('--table-structure', type=str, help='指定したテーブルの構造を表示')
    parser.add_argument('--table-content', type=str, help='指定したテーブルの内容を表示')
    parser.add_argument('--limit', type=int, help='表示する行数を制限')
    parser.add_argument('--query', type=str, help='SQLクエリを実行')
    parser.add_argument('--reset-counters', action='store_true', help='条件カウンターをリセット')
    
    args = parser.parse_args()
    
    # 引数がない場合は対話モード
    if len(sys.argv) == 1:
        interactive_mode()
        return
    
    conn = connect_to_db()
    
    if args.list_tables:
        list_tables(conn)
    
    if args.table_structure:
        show_table_structure(conn, args.table_structure)
    
    if args.table_content:
        show_table_content(conn, args.table_content, args.limit)
    
    if args.query:
        execute_query(conn, args.query)
    
    if args.reset_counters:
        confirm = input("すべての条件カウンターをリセットしますか？(y/n): ")
        if confirm.lower() == 'y':
            reset_counters(conn)
    
    conn.close()

if __name__ == '__main__':
    main()