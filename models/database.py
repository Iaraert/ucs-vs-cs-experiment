import os
import sqlite3
import threading
import datetime

class Database:
    """
    データベース操作をカプセル化するクラス
    条件割り当てとその履歴を管理
    """
    
    def __init__(self, db_path=None):
        """
        データベースクラスの初期化
        
        Args:
            db_path (str, optional): データベースファイルのパス。
            指定がない場合はデフォルトパスを使用。
        """
        self.db_path = db_path or os.path.join('.', 'data', 'participant_allocation.db')
        # SQLite接続用のロックを作成（スレッドセーフにするため）
        self.db_lock = threading.Lock()

    def init_db(self):
        """データベースの初期化と必要なテーブルの作成"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 条件割り当てカウンターのテーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS condition_counters (
            condition_name TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
        ''')

        # 割り当て履歴のテーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS allocation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            condition_name TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 実験経路カウンターのテーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_path_counters (
            path_type TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
        ''')

        # 経路割り当て履歴のテーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_path_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            path_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 初期データが存在しない場合は挿入
        cursor.execute("SELECT count(*) FROM condition_counters WHERE condition_name = 'asymmetric'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO condition_counters (condition_name, count) VALUES ('asymmetric', 0)")
            cursor.execute("INSERT INTO condition_counters (condition_name, count) VALUES ('symmetric', 0)")

        # 実験経路カウンターの初期データが存在しない場合は挿入
        cursor.execute("SELECT count(*) FROM experiment_path_counters WHERE path_type = 'order1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO experiment_path_counters (path_type, count) VALUES ('order1', 0)")
            cursor.execute("INSERT INTO experiment_path_counters (path_type, count) VALUES ('order2', 0)")

        conn.commit()
        conn.close()

    def get_condition_assignment(self, user_id):
        """
        ユーザーIDに基づいて実験条件を割り当てる

        Args:
            user_id (str): ユーザーID

        Returns:
            dict: 割り当てられた条件と関連情報を含む辞書
        """
        try:
            with self.db_lock:  # スレッドセーフに処理
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # トランザクション開始
                conn.execute("BEGIN TRANSACTION")

                # まず、このユーザーIDに既存の割り当てがあるか確認
                cursor.execute(
                    "SELECT condition_name FROM allocation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (user_id,)
                )
                existing_allocation = cursor.fetchone()

                if existing_allocation:
                    # 既存の割り当てがある場合はそれを使用（カウンターは更新しない）
                    selected_condition = existing_allocation[0]
                    print(f"既存の条件を使用: ユーザーID {user_id} -> {selected_condition}")
                else:
                    # 新規ユーザーの場合は割り当てを行う
                    # 現在の各条件の参加者数を取得
                    cursor.execute("SELECT condition_name, count FROM condition_counters")
                    counters = {row[0]: row[1] for row in cursor.fetchall()}

                    # 少ない方の条件を選択、同じ場合はランダムに決定
                    if counters.get('asymmetric', 0) < counters.get('symmetric', 0):
                        selected_condition = 'asymmetric'
                    elif counters.get('asymmetric', 0) > counters.get('symmetric', 0):
                        selected_condition = 'symmetric'
                    else:
                        # 均等の場合はランダムに割り当て
                        import random
                        selected_condition = random.choice(['asymmetric', 'symmetric'])

                    # カウンターを更新
                    cursor.execute(
                        "UPDATE condition_counters SET count = count + 1 WHERE condition_name = ?",
                        (selected_condition,)
                    )

                    # 割り当て履歴に記録
                    cursor.execute(
                        "INSERT INTO allocation_history (user_id, condition_name) VALUES (?, ?)",
                        (user_id, selected_condition)
                    )

                    print(f"新規条件割り当て: ユーザーID {user_id} -> {selected_condition}")

                # トランザクションをコミット
                conn.commit()
                conn.close()

                return {"sampleType": selected_condition, "userId": user_id}

        except Exception as e:
            print(f"条件割り当てエラー: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()  # エラー時はロールバック
                conn.close()
            # エラー時のデフォルト条件
            return {"sampleType": "asymmetric", "error": str(e), "userId": user_id}

    def get_allocation_stats(self):
        """
        条件割り当ての統計情報を取得

        Returns:
            dict: 各条件の割り当て数と割合
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT condition_name, count FROM condition_counters")
                counters = {row[0]: row[1] for row in cursor.fetchall()}

                # 総参加者数
                total = sum(counters.values())

                # 割合を計算
                percentages = {
                    condition: (count / total * 100 if total > 0 else 0)
                    for condition, count in counters.items()
                }

                conn.close()

                return {
                    "counts": counters,
                    "percentages": percentages,
                    "total": total
                }

        except Exception as e:
            print(f"統計情報取得エラー: {e}")
            return {
                "counts": {"symmetric": 0, "asymmetric": 0},
                "percentages": {"symmetric": 0, "asymmetric": 0},
                "total": 0,
                "error": str(e)
            }

    def get_db_info(self):
        """
        データベース内のすべてのテーブル情報を取得する

        Returns:
            list: テーブル情報を含む辞書のリスト
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # テーブル一覧の取得
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                table_info_list = []

                # 各テーブルの情報を取得
                for table_name in [row[0] for row in tables]:
                    # カラム構造の取得
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]

                    # データの取得
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()

                    # サンプルデータ（最大5件）
                    sample_data = rows[:5]

                    table_info = {
                        "name": table_name,
                        "columns": columns,
                        "row_count": len(rows),
                        "sample_data": sample_data
                    }

                    table_info_list.append(table_info)

                conn.close()

                return table_info_list

        except Exception as e:
            print(f"データベース情報取得エラー: {e}")
            return {"error": str(e)}

    def get_experiment_path_assignment(self, user_id, reallocate=True):
        """
        ユーザーIDに基づいて実験経路を割り当てる
        order1: examine1 → examine1_2 → examine2
        order2: examine1_2 → examine1 → examine2

        Args:
            user_id (str): ユーザーID
            reallocate (bool): Trueの場合、既存の割り当てがあっても再割り当てを行う

        Returns:
            dict: 割り当てられた経路と関連情報を含む辞書
        """
        try:
            with self.db_lock:  # スレッドセーフに処理
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # トランザクション開始
                conn.execute("BEGIN TRANSACTION")

                # まず、このユーザーIDに既存の経路割り当てがあるか確認
                cursor.execute(
                    "SELECT path_type FROM experiment_path_history WHERE user_id = ?",
                    (user_id,)
                )
                existing_path = cursor.fetchone()

                if existing_path and not reallocate:
                    # 既存の割り当てがある場合はそれを使用（カウンターは更新しない）
                    selected_path = existing_path[0]
                    print(f"既存の経路を使用: ユーザーID {user_id} -> {selected_path}")
                else:
                    # 新規ユーザーまたは再割り当ての場合
                    # 現在の各経路の参加者数を取得
                    cursor.execute("SELECT path_type, count FROM experiment_path_counters")
                    counters = {row[0]: row[1] for row in cursor.fetchall()}

                    # 少ない方の経路を選択、同じ場合はorder1を優先
                    if counters.get('order1', 0) <= counters.get('order2', 0):
                        selected_path = 'order1'
                    else:
                        selected_path = 'order2'

                    # カウンターを更新
                    cursor.execute(
                        "UPDATE experiment_path_counters SET count = count + 1 WHERE path_type = ?",
                        (selected_path,)
                    )

                    # 既存ユーザーの場合は履歴を更新、新規ユーザーの場合は挿入
                    if existing_path:
                        print(f"経路再割り当て: ユーザーID {user_id} -> {selected_path}")
                        cursor.execute(
                            "UPDATE experiment_path_history SET path_type = ? WHERE user_id = ?",
                            (selected_path, user_id)
                        )
                    else:
                        print(f"新規経路割り当て: ユーザーID {user_id} -> {selected_path}")
                        cursor.execute(
                            "INSERT OR REPLACE INTO experiment_path_history (user_id, path_type) VALUES (?, ?)",
                            (user_id, selected_path)
                        )

                # トランザクションをコミット
                conn.commit()
                conn.close()

                return {"pathType": selected_path, "userId": user_id}

        except Exception as e:
            print(f"経路割り当てエラー: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()  # エラー時はロールバック
                conn.close()
            # エラー時のデフォルト経路
            return {"pathType": "order1", "error": str(e), "userId": user_id}

    def get_experiment_path_stats(self):
        """
        実験経路割り当ての統計情報を取得

        Returns:
            dict: 各経路の割り当て数と割合
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT path_type, count FROM experiment_path_counters")
                counters = {row[0]: row[1] for row in cursor.fetchall()}

                # 総参加者数
                total = sum(counters.values())

                # 割合を計算
                percentages = {
                    path_type: (count / total * 100 if total > 0 else 0)
                    for path_type, count in counters.items()
                }

                conn.close()

                return {
                    "counts": counters,
                    "percentages": percentages,
                    "total": total
                }

        except Exception as e:
            print(f"経路統計情報取得エラー: {e}")
            return {
                "counts": {"order1": 0, "order2": 0},
                "percentages": {"order1": 0, "order2": 0},
                "total": 0,
                "error": str(e)
            }