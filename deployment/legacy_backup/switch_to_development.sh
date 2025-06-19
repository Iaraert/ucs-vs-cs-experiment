#!/bin/bash

# 現在のec2-user環境で開発環境設定を適用するスクリプト

echo "=== EC2ユーザー開発環境への切り替え ==="

APP_DIR="/opt/ucs-vs-cs-experiment"

# 1. 既存のサービスを停止
echo "既存のサービスを停止中..."
sudo systemctl stop experiment-production || true
sudo systemctl disable experiment-production || true
sudo systemctl reset-failed experiment-production || true

# 2. 既存のGunicornプロセスを停止
echo "Gunicornプロセスを停止中..."
sudo pkill -f "gunicorn" || true

# 3. 権限をec2-userに設定
echo "権限をec2-userに設定中..."
sudo chown -R ec2-user:ec2-user $APP_DIR
sudo chmod -R 755 $APP_DIR

# 4. 必要なディレクトリを作成
echo "必要なディレクトリを作成中..."
sudo mkdir -p $APP_DIR/tmp
sudo chown -R ec2-user:ec2-user $APP_DIR/tmp
sudo chmod -R 755 $APP_DIR/tmp

# 5. 開発環境サービスを設定
echo "開発環境サービスを設定中..."
sudo cp $APP_DIR/deployment/systemd/experiment-development.service /etc/systemd/system/
sudo systemctl daemon-reload

# 6. 開発環境サービスを開始
echo "開発環境サービスを開始中..."
sudo systemctl enable experiment-development
sudo systemctl start experiment-development

echo "=== 切り替え完了 ==="
echo ""
echo "サービス状態確認:"
echo "sudo systemctl status experiment-development"
echo ""
echo "ログ確認:"
echo "sudo journalctl -u experiment-development -f"
