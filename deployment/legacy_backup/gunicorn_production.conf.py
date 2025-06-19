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
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error.log"
loglevel = "info"  # 本番環境では標準ログレベル
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# パフォーマンス設定
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True  # 本番環境では有効
timeout = 30
worker_tmp_dir = "/opt/ucs-vs-cs-experiment/tmp"

# プロセス管理
pidfile = "/opt/ucs-vs-cs-experiment/logs/gunicorn.pid"
proc_name = "ucs_vs_cs_experiment_prod"

# セキュリティ設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 環境変数
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment',
    'TMPDIR=/opt/ucs-vs-cs-experiment/tmp',
]

# 本番用設定
reload = False  # 本番環境では無効
capture_output = False
enable_stdio_inheritance = False
