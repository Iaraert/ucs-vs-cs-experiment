#!/bin/bash

# 本番環境向けシンプルセットアップスクリプト
# UCS vs CS 実験アプリケーション用

set -e  # エラー時に終了

echo "=== UCS vs CS Experiment Production Setup ==="

# 基本的なチェック
if [ "$EUID" -ne 0 ]; then
    echo "エラー: このスクリプトはroot権限で実行してください"
    exit 1
fi

# 現在のディレクトリを確認
if [ ! -f "experiment-simple.service" ]; then
    echo "エラー: experiment-simple.service ファイルが見つかりません"
    echo "systemdディレクトリで実行してください"
    exit 1
fi

# 1. アプリケーションディレクトリの作成
APP_DIR="/opt/ucs-vs-cs-experiment"
echo "アプリケーションディレクトリを作成中: $APP_DIR"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/data

# 2. www-dataユーザーの存在確認
if ! id "www-data" &>/dev/null; then
    echo "www-dataユーザーを作成中..."
    useradd --system --no-create-home --shell /bin/false www-data
fi

# 3. サービスファイルをコピー
echo "systemdサービスファイルをコピー中..."
cp experiment-simple.service /etc/systemd/system/

# 4. systemdをリロード
echo "systemdをリロード中..."
systemctl daemon-reload

# 5. 基本的な権限設定
echo "基本的な権限を設定中..."
chown -R www-data:www-data $APP_DIR

echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo "1. アプリケーションファイルを $APP_DIR にコピー"
echo "2. 仮想環境を $APP_DIR/venv に作成"
echo "3. 依存関係をインストール"
echo "4. sudo systemctl enable experiment-simple"
echo "5. sudo systemctl start experiment-simple"
echo ""
echo "ログ確認: sudo journalctl -u experiment-simple -f"