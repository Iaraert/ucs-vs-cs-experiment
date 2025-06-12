import os
from exp import app
from exp.config import DEBUG

PORT = int(os.environ.get('PORT', 9876))
HOST = os.environ.get('HOST', '0.0.0.0' if not DEBUG else '127.0.0.1')

if __name__ == '__main__':
    print(f"サーバーを開始します: {HOST}:{PORT} (Debug: {DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)