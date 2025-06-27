from flask import Flask
from config.settings import active_config
from utils.logger import configure_logging, setup_logger, error_logger
from utils.logger import app_logger  # 追加

# 設定からロギング設定を読み込む
logging_config = {
    'LOG_LEVEL': active_config.LOG_LEVEL,
    'LOG_DIR': active_config.LOG_DIR,
    'LOG_FORMAT': active_config.LOG_FORMAT,
    'INCLUDE_TRACE': active_config.LOG_INCLUDE_TRACE,
    'MAX_LOG_SIZE': active_config.LOG_MAX_SIZE,
    'BACKUP_COUNT': active_config.LOG_BACKUP_COUNT
}

# ロギングシステムを設定
configure_logging(logging_config)

# アプリケーションロガーの設定
app_logger.info('アプリケーションを初期化しています')

# Flaskアプリケーションの作成
app = Flask(__name__)
app.config.from_object(active_config)

app_logger.info(f'Flaskアプリケーションが初期化されました (環境: {app.config.get("ENV", "development")})')

# ビューモジュールをインポート
from exp import error_handlers
from exp import views