#!/bin/bash

# UCS vs CS Experiment - 環境デプロイメントスクリプト
# 用途: 開発環境または本番環境の選択的デプロイ

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

# 使用方法表示
show_usage() {
    echo "使用方法: $0 [environment]"
    echo ""
    echo "environment:"
    echo "  development - 開発環境をデプロイ"
    echo "  production  - 本番環境をデプロイ"
    echo "  status      - 現在のサービス状態を確認"
    echo "  stop        - すべてのサービスを停止"
    echo ""
    echo "例:"
    echo "  $0 development"
    echo "  $0 production"
    echo "  $0 status"
}

# サービス状態確認
check_service_status() {
    echo -e "${BLUE}=== サービス状態確認 ===${NC}"
    
    for service in experiment-development experiment-production; do
        if systemctl list-unit-files | grep -q "^$service.service"; then
            if systemctl is-active --quiet $service; then
                status="RUNNING"
                color=$GREEN
            else
                status="STOPPED"
                color=$YELLOW
            fi
            echo -e "${color}$service: $status${NC}"
            
            if [ "$status" == "RUNNING" ]; then
                echo "  PID: $(systemctl show --property MainPID --value $service)"
                echo "  Uptime: $(systemctl show --property ActiveEnterTimestamp --value $service)"
            fi
        else
            echo -e "${RED}$service: NOT INSTALLED${NC}"
        fi
    done
}

# すべてのサービス停止
stop_all_services() {
    echo -e "${BLUE}=== すべてのサービスを停止中 ===${NC}"
    
    for service in experiment-development experiment-production; do
        if systemctl list-unit-files | grep -q "^$service.service"; then
            if systemctl is-active --quiet $service; then
                log_info "$service を停止中..."
                systemctl stop $service
                log_success "$service 停止完了"
            else
                log_info "$service は既に停止しています"
            fi
        fi
    done
}

# 環境デプロイ
deploy_environment() {
    local env=$1
    local service_name="experiment-$env"
    
    echo -e "${BLUE}=== $env 環境デプロイ開始 ===${NC}"
    
    # 権限チェック
    if [ "$EUID" -ne 0 ]; then
        log_error "このスクリプトはroot権限で実行してください"
        echo "使用方法: sudo $0 $env"
        exit 1
    fi
    
    # 基本設定
    APP_DIR="/opt/ucs-vs-cs-experiment"
    DEPLOYMENT_DIR="$APP_DIR/deployment"
    ENV_DIR="$DEPLOYMENT_DIR/environments/$env"
    
    # 環境ディレクトリの確認
    if [ ! -d "$ENV_DIR" ]; then
        log_error "環境ディレクトリが見つかりません: $ENV_DIR"
        exit 1
    fi
    
    # 他の環境のサービスを停止
    log_info "既存サービスの停止..."
    stop_all_services
    
    # サービスファイルのコピー
    log_info "systemd サービスファイルをコピー中..."
    cp "$ENV_DIR/systemd.service" "/etc/systemd/system/$service_name.service"
    
    # 権限設定
    if [ "$env" == "production" ]; then
        log_info "本番環境用の権限を設定中..."
        chown -R www-data:www-data $APP_DIR/logs
        chown -R www-data:www-data $APP_DIR/data
        chown -R www-data:www-data $APP_DIR/tmp
    else
        log_info "開発環境用の権限を設定中..."
        chown -R ec2-user:ec2-user $APP_DIR/logs
        chown -R ec2-user:ec2-user $APP_DIR/data
        chown -R ec2-user:ec2-user $APP_DIR/tmp
    fi
    
    # systemd リロード
    log_info "systemd をリロード中..."
    systemctl daemon-reload
    
    # サービス有効化と開始
    log_info "$service_name サービスを有効化・開始中..."
    systemctl enable $service_name
    systemctl start $service_name
    
    # 起動確認
    sleep 3
    if systemctl is-active --quiet $service_name; then
        log_success "$env 環境のデプロイが完了しました"
        
        # サービス情報表示
        echo ""
        echo -e "${BLUE}=== サービス情報 ===${NC}"
        echo "サービス名: $service_name"
        echo "状態: $(systemctl is-active $service_name)"
        echo "PID: $(systemctl show --property MainPID --value $service_name)"
        echo "ログ確認: journalctl -u $service_name -f"
        
        # ヘルスチェック
        log_info "ヘルスチェック実行中..."
        sleep 5
        if curl -f http://127.0.0.1:9876/ >/dev/null 2>&1; then
            log_success "アプリケーションは正常に動作しています"
        else
            log_warning "アプリケーションへの接続に失敗しました"
            log_info "ログを確認してください: journalctl -u $service_name"
        fi
    else
        log_error "$env 環境のデプロイに失敗しました"
        log_info "詳細: journalctl -u $service_name"
        exit 1
    fi
}

# メイン処理
main() {
    case "${1:-}" in
        "development"|"dev")
            deploy_environment "development"
            ;;
        "production"|"prod")
            deploy_environment "production"
            ;;
        "status")
            check_service_status
            ;;
        "stop")
            # 権限チェック
            if [ "$EUID" -ne 0 ]; then
                log_error "このスクリプトはroot権限で実行してください"
                exit 1
            fi
            stop_all_services
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        "")
            log_error "環境を指定してください"
            echo ""
            show_usage
            exit 1
            ;;
        *)
            log_error "不明な環境: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
