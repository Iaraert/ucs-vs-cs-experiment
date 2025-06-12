import os
import logging
from exp import app

# 本番環境用の設定
if __name__ != "__main__":
    # Gunicorn経由での実行時
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    # 本番環境用の設定適用
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False

# 開発環境での直接実行
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)