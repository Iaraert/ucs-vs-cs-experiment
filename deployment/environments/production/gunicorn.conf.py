# Gunicorn設定ファイル - 本番環境用
# UCS vs CS 実験アプリケーション

import multiprocessing
import os

# 基本設定
bind = "127.0.0.1:9876"
workers = multiprocessing.cpu_count() * 2 + 1  # 本番環境では最適化
worker_class = "sync"
worker_connections = 1000

# アプリケーション設定
wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"
pythonpath = "/opt/ucs-vs-cs-experiment"

# プロセス設定
daemon = False
user = "www-data"  # 本番環境ではwww-data
group = "www-data"
umask = 0
tmp_upload_dir = "/opt/ucs-vs-cs-experiment/tmp"

# ログ設定
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access_prod.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error_prod.log"
loglevel = "info"  # 本番環境では標準ログレベル
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# パフォーマンス設定
timeout = 120
keepalive = 2
max_requests = 5000  # 本番環境では多めに設定
max_requests_jitter = 500

# 本番環境特有の設定
reload = False  # 本番では自動リロード無効
preload_app = True  # パフォーマンス向上のためプリロード

# セキュリティ設定（本番環境用）
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# ワーカープロセス管理
worker_tmp_dir = "/dev/shm"
enable_stdio_inheritance = False

# 環境変数の設定
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment',
    'TMPDIR=/opt/ucs-vs-cs-experiment/tmp'
]

# プロセス管理とモニタリング
def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")

# メモリ使用量の最適化
def max_requests_reached(worker):
    worker.log.info("Max requests reached, recycling worker")

# 本番環境用のヘルスチェック設定
def on_starting(server):
    server.log.info("Server is starting")

def on_reload(server):
    server.log.info("Server is reloading")

def on_exit(server):
    server.log.info("Server is shutting down")
