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
accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error.log"
loglevel = "debug"  # 開発環境では詳細ログ
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# パフォーマンス設定
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = False  # 開発環境では無効（再読み込み対応）
timeout = 30
worker_tmp_dir = "/opt/ucs-vs-cs-experiment/tmp"

# プロセス管理
pidfile = "/opt/ucs-vs-cs-experiment/logs/gunicorn.pid"
proc_name = "ucs_vs_cs_experiment_dev"

# セキュリティ設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 環境変数
raw_env = [
    'FLASK_ENV=development',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment',
    'TMPDIR=/opt/ucs-vs-cs-experiment/tmp',
]

# 開発用設定
reload = True  # コード変更時の自動再読み込み
reload_extra_files = [
    "/opt/ucs-vs-cs-experiment/exp/views.py",
    "/opt/ucs-vs-cs-experiment/exp/templates/",
    "/opt/ucs-vs-cs-experiment/exp/static/",
]
capture_output = True
enable_stdio_inheritance = True
