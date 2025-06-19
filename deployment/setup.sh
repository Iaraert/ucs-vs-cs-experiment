#!/bin/bash

# UCS vs CS Experiment - 統一デプロイメントスクリプト
# 用途: アプリケーションの初期セットアップと基本環境の構築

set -e

# カラー出力の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}=== UCS vs CS Experiment セットアップ ===${NC}"

# 権限チェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはroot権限で実行してください"
    echo "使用方法: sudo ./setup.sh"
    exit 1
fi

# 定数
APP_DIR="/opt/ucs-vs-cs-experiment"
DEPLOYMENT_DIR="$APP_DIR/deployment"

log_info "1. 基本ディレクトリの作成..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/tmp
mkdir -p $APP_DIR/config
log_success "ディレクトリ作成完了"

log_info "2. 必要なパッケージのインストール..."
if command -v yum &> /dev/null; then
    # Amazon Linux / CentOS / RHEL
    yum update -y
    yum install -y curl netcat-openbsd python3 python3-pip
    log_success "YUM パッケージインストール完了"
elif command -v apt &> /dev/null; then
    # Ubuntu / Debian
    apt update
    apt install -y curl netcat python3 python3-pip python3-venv
    log_success "APT パッケージインストール完了"
else
    log_warning "パッケージマネージャーを認識できませんでした"
fi

log_info "3. ユーザーアカウントの確認と作成..."

# ec2-userの確認・作成
if ! id "ec2-user" &>/dev/null; then
    log_info "ec2-userを作成中..."
    useradd --system --create-home --shell /bin/bash ec2-user
    log_success "ec2-user作成完了"
else
    log_info "ec2-user は既に存在します"
fi

# www-dataユーザーの確認・作成
if ! id "www-data" &>/dev/null; then
    log_info "www-dataユーザーを作成中..."
    useradd --system --no-create-home --shell /bin/bash www-data
    log_success "www-data作成完了"
else
    log_info "www-data は既に存在します"
fi

log_info "4. 権限の設定..."
chown -R ec2-user:ec2-user $APP_DIR
chmod -R 755 $APP_DIR

# ログディレクトリは両方のユーザーがアクセス可能に
chmod -R 775 $APP_DIR/logs
chmod -R 775 $APP_DIR/tmp
chmod -R 775 $APP_DIR/data

log_success "基本権限設定完了"

echo "6. スクリプトファイルに実行権限を設定..."
chmod +x $APP_DIR/deployment/switch_to_development.sh
chmod +x $APP_DIR/deployment/switch_to_production.sh

echo "7. systemdディレクトリの準備..."
systemctl daemon-reload

echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo ""
echo "【開発環境の場合】"
echo "1. sudo cp systemd/experiment-development.service /etc/systemd/system/"
echo "2. sudo systemctl daemon-reload"
echo "3. sudo systemctl enable experiment-development"
echo "4. sudo systemctl start experiment-development"
echo ""
echo "【本番環境の場合】"
echo "1. sudo chown -R www-data:www-data $APP_DIR"
echo "2. sudo cp systemd/experiment-production.service /etc/systemd/system/"
echo "3. sudo systemctl daemon-reload"
echo "4. sudo systemctl enable experiment-production"
echo "5. sudo systemctl start experiment-production"
echo ""
echo "ログ確認: sudo journalctl -u experiment-[development|production] -f"
echo "Gunicornログ: tail -f $APP_DIR/logs/gunicorn_*.log"
