from config.settings import active_config

# 設定をconfig/settings.pyから読み込み
DEBUG = active_config.DEBUG
TESTING = active_config.TESTING
SECRET_KEY = active_config.SECRET_KEY
DATABASE_PATH = active_config.DATABASE_PATH
DATA_DIR = active_config.DATA_DIR
LOG_LEVEL = active_config.LOG_LEVEL
LOG_DIR = active_config.LOG_DIR

# アプリケーション固有の設定
APPLICATION_NAME = "UCS vs CS Experiment"