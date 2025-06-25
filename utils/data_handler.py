import os
import csv
import json

class DataHandler:
    """実験データの保存と取得を担当するクラス"""

    def __init__(self, data_dir='data'):
        """データ処理の初期化"""
        self.data_dir = data_dir
        # データディレクトリが存在しない場合は作成
        os.makedirs(self.data_dir, exist_ok=True)

    def save_experiment_data(self, raw_data, suffix="exp"):
        """実験データ（user_data, estimations）を保存する"""
        results = {}

        for data_name in ["user_data", "estimations"]:
            if data_name not in raw_data:
                continue

            data = json.loads(raw_data[data_name])
            file_name = f"{data_name}_{suffix}.csv"
            filepath = os.path.join(self.data_dir, file_name)  # dataディレクトリに保存

            # ファイルが存在しない場合はヘッダーを追加
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, data[0].keys())
                    writer.writeheader()

            # データを追記
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, data[0].keys())
                writer.writerows(data)

            results[data_name] = len(data)

        return results

    def save_imc_data(self, raw_data, suffix="default"):
        """IMCと認知反射テスト(CRT)のデータを保存する"""
        results = {}

        # IMCデータの保存
        if "user_data" in raw_data:
            user_data = json.loads(raw_data["user_data"])
            file_name = f"imc_data_{suffix}.csv"
            filepath = os.path.join(self.data_dir, file_name)

            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, user_data[0].keys())
                    writer.writeheader()

            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, user_data[0].keys())
                writer.writerows(user_data)

            results["imc_data"] = len(user_data)

        # CRTデータの保存
        if "crt_data" in raw_data:
            crt_data = json.loads(raw_data["crt_data"])
            file_name = f"crt_data_{suffix}.csv"
            filepath = os.path.join(self.data_dir, file_name)

            fieldnames = [
                "user_id",          # ユーザーID
                "q1", "q2", "q3",   # 回答内容
                "q1_correct", "q2_correct", "q3_correct",  # 正誤判定
                "total_correct",    # 総正解数
                "time_q1", "time_q2", "time_q3",  # 各問題の所要時間
                "total_time"        # 全体の所要時間
            ]

            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(crt_data)

            results["crt_data"] = len(crt_data)

        return results

    def backup_data(self, suffix="exp"):
        """
        データのバックアップを作成する

        Args:
            suffix (str): ファイル名の接尾辞

        Returns:
            dict: バックアップしたファイルの情報
        """
        import datetime
        import shutil

        backup_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.data_dir, f"backup_{backup_time}")
        os.makedirs(backup_dir, exist_ok=True)

        backup_files = {}

        # ユーザーデータとエスティメーションのバックアップ
        for data_name in ["user_data", "estimations", "imc_data", "crt_data"]:
            file_name = f"{data_name}_{suffix}.csv"
            src_path = os.path.join(self.data_dir, file_name)

            if os.path.exists(src_path):
                dst_path = os.path.join(backup_dir, file_name)
                shutil.copy2(src_path, dst_path)
                backup_files[data_name] = dst_path

        return {
            "backup_time": backup_time,
            "backup_dir": backup_dir,
            "files": backup_files
        }

    def get_progress_counts(self, user_id):
        """
        各ページ（examine1, examine1_2, examine2, examine3）の送信済み件数を返す。
        戻り値: dict { 'examine1': int, 'examine1_2': int, 'examine2': int, 'examine3': int }
        """
        import sqlite3
        db_path = "experiment.db"  # 実際のDBパスに合わせて修正
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        result = {}
        try:
            # examine1
            cursor.execute(
                "SELECT COUNT(*) FROM estimations WHERE user_id=? AND file_name_suffix='exp1'", (user_id,))
            result['examine1'] = cursor.fetchone()[0]
            # examine1_2
            cursor.execute(
                "SELECT COUNT(*) FROM estimations WHERE user_id=? AND file_name_suffix='exp1_2'", (user_id,))
            result['examine1_2'] = cursor.fetchone()[0]
            # examine2
            cursor.execute(
                "SELECT COUNT(*) FROM user_data WHERE user_id=? AND file_name_suffix='exp2'", (user_id,))
            result['examine2'] = cursor.fetchone()[0]
            # examine3
            cursor.execute(
                "SELECT COUNT(*) FROM user_data WHERE user_id=? AND file_name_suffix='exp3'", (user_id,))
            result['examine3'] = cursor.fetchone()[0]
        except Exception as e:
            # 必要に応じてロギング
            result = {'examine1': 0, 'examine1_2': 0, 'examine2': 0, 'examine3': 0}
        finally:
            conn.close()
        return result