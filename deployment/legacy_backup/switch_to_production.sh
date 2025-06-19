#!/bin/bash

# 本番環境への切り替えスクリプト

echo "=== 本番環境への切り替え ==="

APP_DIR="/opt/ucs-vs-cs-experiment"

# 1. 既存の開発環境サービスを停止
echo "開発環境サービスを停止中..."
sudo systemctl stop experiment-development || true
sudo systemctl disable experiment-development || true
sudo systemctl reset-failed experiment-development || true

# 2. 既存のGunicornプロセスを停止
echo "Gunicornプロセスを停止中..."
sudo pkill -f "gunicorn" || true

# 3. www-dataユーザーの存在確認
echo "www-dataユーザーの確認..."
if ! id "www-data" &>/dev/null; then
    echo "www-dataユーザーを作成中..."
    sudo useradd --system --no-create-home --shell /bin/bash www-data
fi

# 4. 権限をwww-dataに設定
echo "権限をwww-dataに設定中..."
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 755 $APP_DIR

# 5. 必要なディレクトリを作成
echo "必要なディレクトリを作成中..."
sudo mkdir -p $APP_DIR/tmp
sudo chown -R www-data:www-data $APP_DIR/tmp
sudo chmod -R 755 $APP_DIR/tmp

# 6. 本番環境サービスを設定
echo "本番環境サービスを設定中..."
sudo cp $APP_DIR/deployment/systemd/experiment-production.service /etc/systemd/system/
sudo systemctl daemon-reload

# 7. 本番環境サービスを開始
echo "本番環境サービスを開始中..."
sudo systemctl enable experiment-production
sudo systemctl start experiment-production

echo "=== 切り替え完了 ==="
echo ""
echo "サービス状態確認:"
echo "sudo systemctl status experiment-production"
echo ""
echo "ログ確認:"
echo "sudo journalctl -u experiment-production -f"
