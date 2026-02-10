from config.settings import active_config

# グローバル設定（config/settings.pyから読み込み）
DEBUG = active_config.DEBUG  # デバッグモード
TESTING = active_config.TESTING  # テストモード
SECRET_KEY = active_config.SECRET_KEY  # Flask セッション用秘密鍵
DATABASE_PATH = active_config.DATABASE_PATH  # データベースファイルパス
DATA_DIR = active_config.DATA_DIR  # データ保存ディレクトリ
LOG_LEVEL = active_config.LOG_LEVEL  # ログレベル（DEBUG/INFO/WARNING/ERROR）
LOG_DIR = active_config.LOG_DIR  # ログ保存ディレクトリ

# アプリケーション固有の設定
APPLICATION_NAME = "UCS vs CS Experiment"  # 実験名