# Gunicorn 設定ファイル
# UCS vs CS 実験アプリケーション用

import multiprocessing
import os

# 基本設定
bind = "127.0.0.1:9876"
workers = multiprocessing.cpu_count() * 2 + 1  # CPU数 × 2 + 1
worker_class = "sync"
worker_connections = 1000

# アプリケーション設定
wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"
pythonpath = "/opt/ucs-vs-cs-experiment"

# プロセス設定
daemon = False
user = "www-data"
group = "www-data"
umask = 0
tmp_upload_dir = None

# ログ設定
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# パフォーマンス設定
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 30
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
