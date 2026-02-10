# Gunicorn設定 - 開発環境

bind = "127.0.0.1:9876"
workers = 1  # 開発環境では1ワーカーで十分
worker_class = "sync"

wsgi_module = "wsgi:app"
chdir = "/opt/ucs-vs-cs-experiment"

daemon = False
user = "ec2-user"
group = "ec2-user"
umask = 0

accesslog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_access_dev.log"
errorlog = "/opt/ucs-vs-cs-experiment/logs/gunicorn_error_dev.log"
loglevel = "debug"  # 開発環境では詳細ログ

timeout = 120
keepalive = 2

reload = True  # コード変更時の自動リロード
preload_app = False  # デバッグのためプリロードしない

worker_tmp_dir = "/dev/shm"

raw_env = [
    'FLASK_ENV=development',
    'PYTHONPATH=/opt/ucs-vs-cs-experiment'
]
