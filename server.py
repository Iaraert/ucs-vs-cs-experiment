import os
import sys
import signal
from exp import app
from exp.config import DEBUG
from utils.logger import setup_logger, error_logger

# ロガーをセットアップ
logger = setup_logger('server')

PORT = int(os.environ.get('PORT', 9876))
HOST = os.environ.get('HOST', '0.0.0.0' if not DEBUG else '127.0.0.1')

def signal_handler(signum, frame):
    """
    グレースフルシャットダウン用のシグナルハンドラー
    """
    logger.info(f"シグナル {signum} を受信しました。サーバーを正常終了します...")
    sys.exit(0)

def validate_environment():
    """
    起動前の環境チェック
    """
    try:
        # ポート番号の妥当性チェック
        if not (1 <= PORT <= 65535):
            raise ValueError(f"無効なポート番号: {PORT}")
        
        # 必要なディレクトリの存在確認
        required_dirs = ['logs', 'data']
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                logger.warning(f"ディレクトリが見つかりません: {dir_name}")
        
        logger.info("環境チェック完了")
        return True
        
    except Exception as e:
        error_logger.log_exception(e, level='CRITICAL', context={'function': 'validate_environment'})
        return False

if __name__ == '__main__':
    try:
        # シグナルハンドラーを設定
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # 環境チェック
        if not validate_environment():
            logger.critical("環境チェックに失敗しました。サーバーを起動できません。")
            sys.exit(1)
        
        logger.info(f"サーバーを開始します: {HOST}:{PORT} (Debug: {DEBUG})")
        
        # アプリケーションを起動
        app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
        
    except Exception as e:
        error_logger.log_exception(e, level='CRITICAL', context={'function': 'main'})
        logger.critical(f"サーバー起動中にエラーが発生しました: {e}")
        sys.exit(1)