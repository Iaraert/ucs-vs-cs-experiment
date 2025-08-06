import os
import sqlite3
import threading
import datetime
import re

from utils.logger import app_logger  # 追加

class ExperimentSession:
    def __init__(self, id, current_step=0, finished=False, order=None):
        self.id = id
        self.current_step = current_step
        self.finished = finished
        self.order = order  # order1/order2 など

    def __repr__(self):
        return f'<ExperimentSession id={self.id} step={self.current_step} finished={self.finished} order={self.order}>'

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

    def validate_user_id(self, user_id):
        """
        ユーザーIDの妥当性を検証
        
        Args:
            user_id (str): 検証するユーザーID
            
        Returns:
            bool: IDが有効かどうか
        """
        if not user_id or not isinstance(user_id, str):
            return False
        
        # 基本的な長さチェック（最小3文字、最大50文字）
        if len(user_id) < 3 or len(user_id) > 50:
            return False
        
        # 危険な文字の除外（SQLインジェクション、XSS対策）
        dangerous_chars = re.compile(r'[<>\'"&=;()|]')
        if dangerous_chars.search(user_id):
            return False
        
        # 制御文字の除外
        if re.search(r'[\x00-\x1F\x7F]', user_id):
            return False
        
        return True

    def sanitize_user_id(self, user_id):
        """
        ユーザーIDをサニタイズ
        
        Args:
            user_id (str): サニタイズするユーザーID
            
        Returns:
            str: サニタイズされたユーザーID
        """
        if not user_id:
            return ''
        
        # 文字列に変換し、基本的なサニタイズ
        sanitized = str(user_id).strip()[:50]  # 最大長制限
        sanitized = re.sub(r'[<>\'"&=;()|]', '', sanitized)  # 危険な文字を削除
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)  # 制御文字を削除
        
        return sanitized

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

        # 実験セッション管理テーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_step INTEGER NOT NULL DEFAULT 0,
            finished BOOLEAN NOT NULL DEFAULT 0
        )
        ''')

        # CRT受験歴アンケートのテーブルを作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crt_experience_survey (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            experience TEXT NOT NULL CHECK (experience IN ('yes', 'no', 'unknown')),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

                # ユーザーIDのサニタイズ
                user_id = self.sanitize_user_id(user_id)

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
                    app_logger.info(f"既存の条件を使用: ユーザーID {user_id} -> {selected_condition}")  # ログ追加
                    # print(f"既存の条件を使用: ユーザーID {user_id} -> {selected_condition}")
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

                    # JSTタイムスタンプを生成
                    JST = datetime.timezone(datetime.timedelta(hours=9), 'Asia/Tokyo')
                    now_jst = datetime.datetime.now(JST)
                    timestamp_jst = now_jst.strftime("%Y-%m-%d %H:%M:%S")

                    # 割り当て履歴に記録（JSTでtimestampを明示的に指定）
                    cursor.execute(
                        "INSERT INTO allocation_history (user_id, condition_name, timestamp) VALUES (?, ?, ?)",
                        (user_id, selected_condition, timestamp_jst)
                    )

                    app_logger.info(f"新規条件割り当て: ユーザーID {user_id} -> {selected_condition}")  # ログ追加
                    # print(f"新規条件割り当て: ユーザーID {user_id} -> {selected_condition}")

                # トランザクションをコミット
                conn.commit()
                conn.close()

                return {"sampleType": selected_condition, "userId": user_id}
        except Exception as e:
            app_logger.error(f"条件割り当てエラー: {e}", exc_info=True)  # ログ追加
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

    def get_experiment_path_assignment(self, user_id, reallocate=False):
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
        # ユーザーIDの検証とサニタイズ
        if not self.validate_user_id(user_id):
            app_logger.warning(f"無効なユーザーID: {user_id}")  # ログ追加
            return {"pathType": "order1", "error": "Invalid user ID", "userId": user_id}
        try:
            with self.db_lock:  # スレッドセーフに処理
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # ユーザーIDのサニタイズ
                sanitized_user_id = self.sanitize_user_id(user_id)
                # トランザクション開始
                conn.execute("BEGIN TRANSACTION")
                # まず、このユーザーIDに既存の経路割り当てがあるか確認
                cursor.execute(
                    "SELECT path_type FROM experiment_path_history WHERE user_id = ?",
                    (sanitized_user_id,)
                )
                existing_path = cursor.fetchone()

                if existing_path and not reallocate:
                    # 既存の割り当てがある場合はそれを使用（カウンターは更新しない）
                    selected_path = existing_path[0]
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
                    # JSTタイムスタンプを生成
                    JST = datetime.timezone(datetime.timedelta(hours=9), 'Asia/Tokyo')
                    now_jst = datetime.datetime.now(JST)
                    timestamp_jst = now_jst.strftime("%Y-%m-%d %H:%M:%S")
                    # 既存ユーザーの場合は履歴を更新、新規ユーザーの場合は挿入
                    update_query = "UPDATE experiment_path_history SET path_type = ?, timestamp = ? WHERE user_id = ?"
                    if existing_path:
                        cursor.execute(update_query, (selected_path, timestamp_jst, sanitized_user_id))
                    else:
                        insert_query = "INSERT INTO experiment_path_history (user_id, path_type, timestamp) VALUES (?, ?, ?)"
                        try:
                            cursor.execute(insert_query, (sanitized_user_id, selected_path, timestamp_jst))
                        except sqlite3.IntegrityError:
                            cursor.execute(update_query, (selected_path, timestamp_jst, sanitized_user_id))

                # トランザクションをコミット
                conn.commit()
                conn.close()

                return {"pathType": selected_path, "userId": sanitized_user_id}
        except Exception as e:
            app_logger.error(f"経路割り当てエラー: {e}", exc_info=True)  # ログ追加
            if 'conn' in locals() and conn:
                conn.rollback()  # エラー時はロールバック
                conn.close()
            # エラー時のデフォルト経路
            return {"pathType": "order1", "error": str(e), "userId": user_id}

    def get_connection(self):
        """ヘルスチェック用のデータベース接続テスト"""
        try:
            conn = sqlite3.connect(self.db_path)
            # 簡単なクエリでテスト
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True
        except Exception as e:
            raise Exception(f"Database connection failed: {e}")

    def get_progress_counts(self, user_id):
        from utils.data_handler import DataHandler
        handler = DataHandler()
        return handler.get_progress_counts(user_id)

    def get_experiment_session(self, exp_id):
        """
        experiment_session テーブルからセッション情報を取得
        Args:
            exp_id (int): セッションID
        Returns:
            ExperimentSession or None
        """
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, current_step, finished FROM experiment_session WHERE id = ?", (exp_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            # order情報も取得（experiment_path_historyから）
            cursor.execute("SELECT path_type FROM experiment_path_history WHERE id = ?", (exp_id,))
            order_row = cursor.fetchone()
            order = order_row[0] if order_row else None
            conn.close()
            return ExperimentSession(id=row[0], current_step=row[1], finished=bool(row[2]), order=order)

    def update_experiment_session(self, exp_id, current_step=None, finished=None, expected=None):
        """
        experiment_session テーブルの current_step/finished を更新
        current_stepはexpected一致時のみ進める（単調増加）
        """
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            rows = 0
            if current_step is not None:
                if expected is not None:
                    # current_stepがexpectedのときのみ進める
                    cursor.execute("UPDATE experiment_session SET current_step = ? WHERE id = ? AND current_step = ?", (current_step, exp_id, expected))
                    rows = cursor.rowcount
                else:
                    cursor.execute("UPDATE experiment_session SET current_step = ? WHERE id = ?", (current_step, exp_id))
                    rows = cursor.rowcount
            if finished is not None:
                cursor.execute("UPDATE experiment_session SET finished = ? WHERE id = ?", (int(bool(finished)), exp_id))
            conn.commit()
            conn.close()
            return rows

    def save_crt_experience(self, user_id, experience, timestamp=None):
        """
        CRT受験歴アンケートの回答をデータベースに保存
        
        Args:
            user_id (str): ユーザーID
            experience (str): 受験歴回答 ('yes', 'no', 'unknown')
            timestamp (str, optional): タイムスタンプ（指定がない場合は現在時刻）
            
        Returns:
            dict: 保存結果
        """
        # ユーザーIDの検証とサニタイズ
        if not self.validate_user_id(user_id):
            app_logger.warning(f"無効なユーザーID: {user_id}")
            return {"error": "Invalid user ID", "userId": user_id}
        
        sanitized_user_id = self.sanitize_user_id(user_id)
        
        # experienceの値が有効かチェック
        valid_experiences = ['yes', 'no', 'unknown']
        if experience not in valid_experiences:
            app_logger.warning(f"無効なCRT受験歴回答: {experience}")
            return {"error": "Invalid experience value", "experience": experience}
        
        try:
            with self.db_lock:  # スレッドセーフに処理
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # トランザクション開始
                conn.execute("BEGIN TRANSACTION")
                
                # JSTタイムスタンプを生成（timestampが指定されていない場合）
                if not timestamp:
                    JST = datetime.timezone(datetime.timedelta(hours=9), 'Asia/Tokyo')
                    now_jst = datetime.datetime.now(JST)
                    timestamp = now_jst.strftime("%Y-%m-%d %H:%M:%S")
                
                # 既存のレコードがあるかチェック
                cursor.execute(
                    "SELECT id FROM crt_experience_survey WHERE user_id = ?",
                    (sanitized_user_id,)
                )
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # 既存レコードを更新
                    cursor.execute(
                        "UPDATE crt_experience_survey SET experience = ?, timestamp = ? WHERE user_id = ?",
                        (experience, timestamp, sanitized_user_id)
                    )
                    action = "updated"
                    app_logger.info(f"CRT受験歴データ更新: ユーザーID {sanitized_user_id} -> {experience}")
                else:
                    # 新規レコードを挿入
                    cursor.execute(
                        "INSERT INTO crt_experience_survey (user_id, experience, timestamp) VALUES (?, ?, ?)",
                        (sanitized_user_id, experience, timestamp)
                    )
                    action = "created"
                    app_logger.info(f"CRT受験歴データ新規作成: ユーザーID {sanitized_user_id} -> {experience}")
                
                # トランザクションをコミット
                conn.commit()
                conn.close()
                
                return {
                    "status": "success",
                    "action": action,
                    "userId": sanitized_user_id,
                    "experience": experience,
                    "timestamp": timestamp
                }
                
        except Exception as e:
            app_logger.error(f"CRT受験歴データ保存エラー: {e}", exc_info=True)
            if 'conn' in locals() and conn:
                conn.rollback()  # エラー時はロールバック
                conn.close()
            return {"error": str(e), "userId": user_id}