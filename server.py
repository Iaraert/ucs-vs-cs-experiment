import os
from exp import app
from exp.config import DEBUG

# 環境変数から設定を取得するか、デフォルト値を使用
PORT = int(os.environ.get('PORT', 5000))
HOST = os.environ.get('HOST', '0.0.0.0' if not DEBUG else '127.0.0.1')

if __name__ == '__main__':
    print(f"サーバーを開始します: {HOST}:{PORT} (Debug: {DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)