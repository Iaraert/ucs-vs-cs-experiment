# Gunicorn設定ファイル - 開発環境用
# UCS vs CS 実験アプリケーション

import multiprocessing
import os

# 基本設定
bind = "127.0.0.1:9876"
workers = 1  # 開発環境では1ワーカーで十分
worker_class = "sync"
worker_connections = 1000

# アプリケーション設定
wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"
pythonpath = "/opt/ucs-vs-cs-experiment"

# プロセス設定
daemon = False
user = "ec2-user"
group = "ec2-user"
umask = 0
tmp_upload_dir = "/opt/ucs-vs-cs-experiment/tmp"

# ログ設定
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access_dev.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error_dev.log"
loglevel = "debug"  # 開発環境では詳細ログ
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# パフォーマンス設定
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# 開発環境特有の設定
reload = True  # コード変更時の自動リロード
preload_app = False  # デバッグのためプリロードしない

# セキュリティ設定（開発環境用）
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# ワーカープロセス管理
worker_tmp_dir = "/dev/shm"
enable_stdio_inheritance = True

# 環境変数の設定
raw_env = [
    'FLASK_ENV=development',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment',
    'TMPDIR=/opt/ucs-vs-cs-experiment/tmp'
]

# ヘルスチェック設定
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
