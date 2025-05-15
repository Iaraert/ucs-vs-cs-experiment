import os

class Config:
    """アプリケーションの基本設定"""
    
    # アプリケーション設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-development')
    DEBUG = False
    TESTING = False
    
    # データベース設定
    DATABASE_PATH = os.path.join('.', 'data', 'participant_allocation.db')
    
    # データストレージ設定
    DATA_DIR = os.path.join('.', 'data')
    
    # ロギング設定
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join('.', 'logs')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    LOG_INCLUDE_TRACE = True
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # エラー処理設定
    DEFAULT_ERROR_MESSAGE = 'システムエラーが発生しました。しばらく経ってからもう一度お試しください。'
    ERROR_TEMPLATES = {
        '404': 'error/404.html',
        '500': 'error/500.html',
        'default': 'error/500.html'
    }
    # リカバリーパス設定
    DEFAULT_RECOVERY_PATH = '/'

class DevelopmentConfig(Config):
    """開発環境の設定"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    LOG_INCLUDE_TRACE = True
    # 開発環境では詳細なエラーメッセージを表示
    DEFAULT_ERROR_MESSAGE = None  # Noneの場合、実際のエラーメッセージが表示される

class TestingConfig(Config):
    """テスト環境の設定"""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = os.path.join('.', 'data', 'test_database.db')
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """本番環境の設定"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key'
    LOG_LEVEL = 'ERROR'
    LOG_INCLUDE_TRACE = False  # 本番環境ではトレースバックを含めない

# 環境に基づいて適切な設定を選択
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# 現在の環境設定を取得（デフォルトは開発環境）
active_config = config_by_name.get(os.environ.get('FLASK_ENV', 'development'))
