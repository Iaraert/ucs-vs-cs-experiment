# Gunicorn 高性能設定ファイル
# UCS vs CS 実験アプリケーション用

import multiprocessing
import os

# サーバー設定
bind = "127.0.0.1:9876"
backlog = 2048

# ワーカー設定
workers = max(1, (multiprocessing.cpu_count() * 2) + 1)
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# アプリケーション設定
wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"
pythonpath = "/opt/ucs-vs-cs-experiment"

# プロセス設定
daemon = False
user = "www-data"
group = "www-data"
umask = 0

# ログ設定
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error.log"
loglevel = "info"
capture_output = True
logger_class = "gunicorn.glogging.Logger"

# アクセスログ形式（詳細）
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s %(p)s'

# パフォーマンス設定
keepalive = 2
timeout = 30
graceful_timeout = 30
preload_app = True
worker_tmp_dir = "/dev/shm"

# プロセス管理
pidfile = "/opt/ucs-vs-cs-experiment/logs/gunicorn.pid"
proc_name = "ucs_vs_cs_experiment"

# セキュリティ設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 環境変数
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment',
]

# 実験環境特化設定
def when_ready(server):
    """サーバー起動時の処理"""
    server.log.info("UCS vs CS Experiment server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """ワーカープロセス中断時の処理"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """ワーカープロセス開始前の処理"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """ワーカープロセス開始後の処理"""
    server.log.info("Worker started (pid: %s)", worker.pid)
    # 実験データベースの接続チェック
    try:
        from models.database import DatabaseManager
        db = DatabaseManager()
        db.check_connection()
        server.log.info("Database connection verified for worker %s", worker.pid)
    except Exception as e:
        server.log.error("Database connection failed for worker %s: %s", worker.pid, e)

def worker_abort(worker):
    """ワーカープロセス異常終了時の処理"""
    worker.log.info("Worker aborted (pid: %s)", worker.pid)
