# -*- coding: utf-8 -*-
"""
UCS vs CS 実験アプリ用 負荷テストスクリプト（Locust）

- 実験参加者の同時接続・ピーク・長時間・SQLite競合を再現しやすい設計
- GET→POSTの1セットを1タスクでループ（実験フローに近い）
- user_idはセッションごとに一意生成し全タスクで共通利用
- パラメータは実データ・CSV・条件名などをバリエーション化
- エラー判定はstatus_code, レスポンステキスト, タイムアウト, ヘッダー多角的
- 結果CSVやログは日付付きディレクトリ（例: loadtest_results/20250627/）に保存推奨

【推奨実行例】
# 通常シナリオ（30ユーザー, 5/sec, 15分）
locust -f locustfile.py -u 30 -r 5 --run-time 15m --csv loadtest_results/20250627/result_exp1
# ピーク負荷（100ユーザー, 30/sec, 10分）
locust -f locustfile.py -u 100 -r 30 --run-time 10m --csv loadtest_results/20250627/result_peak
# 超ピーク（300ユーザー, 50/sec, 10分）
locust -f locustfile.py -u 300 -r 50 --run-time 10m --csv loadtest_results/20250627/result_superpeak

【分析例】
- --csv で出力されたCSVを pandas/Excel で可視化・集計
- 長時間運用（10分以上）でメモリリークやDBロックも確認
- SQLite競合やtimeout発生時はワーカー数・timeout値も調整

"""
import os
import random
import string
import time
from locust import HttpUser, task, between, events
from requests.exceptions import RequestException, Timeout

HOST = os.environ.get("LOCUST_HOST", "http://127.0.0.1:9876")

# 実データに近いパラメータ例
CHOICE_LABELS = ["treated_positive", "treated_negative", "non_treated_positive", "non_treated_negative"]
CSV_PATHS = ["/static/material1.json", "/static/material2.json"]
FILE_NAME_SUFFIXES = ["exp1", "exp1_2"]
SAMPLE_TYPES = ["asymmetric", "symmetric"]

class ExperimentUser(HttpUser):
    # 人間の回答間隔に近いthink time
    wait_time = between(5, 15)
    host = HOST

    def on_start(self):
        # セッションごとに一意なuser_idを生成
        self.user_id = self.random_user_id()
        self.n_trials = 6  # 1セッションでのトライアル数（実験1相当）
        self.sample_type = random.choice(SAMPLE_TYPES)
        self.user_agent = self.random_user_agent()

    def random_user_id(self):
        # 実験本番のID生成に近い方式
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

    def random_user_agent(self):
        # 代表的なUAをランダムに
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
        ]
        return random.choice(ua_list)

    @task
    def experiment_flow(self):
        headers = {"User-Agent": self.user_agent}
        for trial in range(self.n_trials):
            choice_label = random.choice(CHOICE_LABELS)
            csv_path = random.choice(CSV_PATHS)
            trial_count = trial + 1
            file_name_suffix = random.choice(FILE_NAME_SUFFIXES)

            # GET: /getSampleType?user_id=xxx
            try:
                with self.client.get(f"/getSampleType?user_id={self.user_id}", headers=headers, timeout=10, catch_response=True) as response:
                    if response.status_code != 200 or "error" in response.text.lower() or response.headers.get("X-Error-Code"):
                        response.failure(f"Status code: {response.status_code}, body: {response.text[:100]}")
                    else:
                        response.success()
            except Timeout as e:
                events.request_failure.fire(
                    request_type="GET",
                    name="/getSampleType",
                    response_time=10000,
                    exception=e
                )
                break
            except RequestException as e:
                events.request_failure.fire(
                    request_type="GET",
                    name="/getSampleType",
                    response_time=0,
                    exception=e
                )
                break

            time.sleep(random.uniform(5, 15))  # GET→POST間のthink time

            # POST: /send
            post_data = {
                "user_id": self.user_id,
                "choice_label": choice_label,
                "csv_path": csv_path,
                "trial_count": trial_count,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "file_name_suffix": file_name_suffix,
                "sample_type": self.sample_type
            }
            try:
                with self.client.post("/send", data=post_data, headers=headers, timeout=10, catch_response=True) as response:
                    if response.status_code != 200 or "error" in response.text.lower() or response.headers.get("X-Error-Code"):
                        response.failure(f"Status code: {response.status_code}, body: {response.text[:100]}")
                    else:
                        response.success()
            except Timeout as e:
                events.request_failure.fire(
                    request_type="POST",
                    name="/send",
                    response_time=10000,
                    exception=e
                )
                break
            except RequestException as e:
                events.request_failure.fire(
                    request_type="POST",
                    name="/send",
                    response_time=0,
                    exception=e
                )
                break

            time.sleep(random.uniform(5, 15))  # POST→次トライアル間のthink time

    # ファイルアップロード負荷テスト例（必要なら有効化）
    # @task(0)
    # def upload_file(self):
    #     files = {"file": ("dummy.csv", "a,b,c\n1,2,3\n" * 1000)}
    #     try:
    #         with self.client.post("/upload", files=files, timeout=20, catch_response=True) as response:
    #             if response.status_code != 200:
    #                 response.failure(f"Status code: {response.status_code}")
    #             else:
    #                 response.success()
    #     except Exception as e:
    #         events.request_failure.fire(
    #             request_type="POST",
    #             name="/upload",
    #             response_time=0,
    #             exception=e
    #         )
