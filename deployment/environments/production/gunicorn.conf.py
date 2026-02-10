# Gunicorn設定 - 本番環境

bind = "127.0.0.1:9876"
workers = 2  # t3.mediumは2vCPUなので2ワーカー（CPU数*2+1は過剰）
worker_class = "sync"

wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"

daemon = False
user = "www-data"  # 本番環境ではwww-data
group = "www-data"
umask = 0

accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access_prod.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error_prod.log"
loglevel = "info"

timeout = 120
keepalive = 2
max_requests = 2000  # 安定性重視
max_requests_jitter = 500

reload = False  # 本番では自動リロード無効
preload_app = True  # パフォーマンス向上のためプリロード

worker_tmp_dir = "/dev/shm"

raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment'
]
