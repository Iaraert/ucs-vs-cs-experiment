# UCS vs CS Experiment - デプロイメント設定

## 📁 ディレクトリ構造

```
deployment/
├── README.md                    # このファイル（デプロイメント説明書）
├── setup.sh                    # 初期セットアップスクリプト
├── deploy.sh                   # 環境デプロイメントスクリプト
├── common.conf                 # 共通設定ファイル
├── environments/              # 環境固有の設定
│   ├── development/          # 開発環境設定
│   │   ├── gunicorn.conf.py # 開発用Gunicorn設定
│   │   └── systemd.service  # 開発用systemdサービス
│   └── production/           # 本番環境設定
│       ├── gunicorn.conf.py # 本番用Gunicorn設定
│       └── systemd.service  # 本番用systemdサービス
└── systemd/                  # 旧形式（互換性のため保持）
    ├── experiment-development.service
    └── experiment-production.service
```

## 🚀 クイックスタート

### 1. 初期セットアップ
```bash
# 基本環境のセットアップ
cd /opt/ucs-vs-cs-experiment/deployment
chmod +x setup.sh deploy.sh
sudo ./setup.sh
```

### 2. 開発環境のデプロイ
```bash
# 開発環境を起動
sudo ./deploy.sh development

# または短縮形
sudo ./deploy.sh dev
```

### 3. 本番環境のデプロイ
```bash
# 本番環境を起動
sudo ./deploy.sh production

# または短縮形
sudo ./deploy.sh prod
```

## 🔧 運用コマンド

### サービス状態確認
```bash
# 全サービスの状態確認
sudo ./deploy.sh status

# 個別サービス確認
sudo systemctl status experiment-development
sudo systemctl status experiment-production
```

### サービス制御
```bash
# すべてのサービスを停止
sudo ./deploy.sh stop

# 個別サービス制御
sudo systemctl start experiment-development
sudo systemctl stop experiment-development
sudo systemctl restart experiment-development
```

### ログ確認
```bash
# リアルタイムログ確認
sudo journalctl -u experiment-development -f
sudo journalctl -u experiment-production -f

# アプリケーションログ
tail -f /opt/ucs-vs-cs-experiment/logs/gunicorn_access_dev.log
tail -f /opt/ucs-vs-cs-experiment/logs/gunicorn_error_dev.log
```

## 🏗️ 環境の違い

| 項目 | 開発環境 | 本番環境 |
|------|----------|----------|
| **実行ユーザー** | ec2-user | www-data |
| **Gunicornワーカー数** | 1 | CPU数 × 2 + 1 |
| **ログレベル** | debug | info |
| **自動リロード** | 有効 | 無効 |
| **プリロード** | 無効 | 有効 |
| **セキュリティ設定** | 緩和 | 強化 |
| **再起動間隔** | 30秒 | 10秒 |
| **ログファイル** | *_dev.log | *_prod.log |

## 📋 デプロイメント手順詳細

### setup.sh の機能
- 基本ディレクトリ作成
- 必要パッケージのインストール
- ユーザーアカウント作成（ec2-user, www-data）
- 権限設定
- 仮想環境の確認

### deploy.sh の機能
- 環境選択的デプロイ
- 既存サービスの自動停止
- systemdサービス設定
- 権限の環境別調整
- ヘルスチェック実行

## 🛠️ カスタマイズ

### 設定ファイルの編集
```bash
# 開発環境のGunicorn設定
nano environments/development/gunicorn.conf.py

# 本番環境のGunicorn設定
nano environments/production/gunicorn.conf.py

# 共通設定
nano common.conf
```

### ポート変更
デフォルトポート（9876）を変更する場合：
1. `common.conf` の `APP_PORT` を変更
2. 各環境の `gunicorn.conf.py` の `bind` を変更
3. 各環境の `systemd.service` の `PORT` 環境変数を変更

## 🐛 トラブルシューティング

### サービスが起動しない場合
```bash
# サービス状態の詳細確認
sudo systemctl status experiment-development -l

# ログの確認
sudo journalctl -u experiment-development -n 50

# 設定ファイルの構文チェック
sudo /opt/ucs-vs-cs-experiment/venv-aws/bin/gunicorn --check-config \
  -c environments/development/gunicorn.conf.py wsgi:app
```

### 権限エラーの場合
```bash
# 権限の再設定
sudo chown -R ec2-user:ec2-user /opt/ucs-vs-cs-experiment
sudo chmod -R 755 /opt/ucs-vs-cs-experiment
sudo chmod -R 775 /opt/ucs-vs-cs-experiment/logs
sudo chmod -R 775 /opt/ucs-vs-cs-experiment/tmp
```

### アプリケーションログの確認
```bash
# Gunicornログ
tail -f /opt/ucs-vs-cs-experiment/logs/gunicorn_error_dev.log

# アプリケーションログ
tail -f /opt/ucs-vs-cs-experiment/logs/experiment_app_$(date +%Y%m%d).log
```

## 🔄 環境切り替え

本番環境から開発環境への切り替え：
```bash
sudo ./deploy.sh stop
sudo ./deploy.sh development
```

開発環境から本番環境への切り替え：
```bash
sudo ./deploy.sh stop
sudo ./deploy.sh production
```

## 📝 メンテナンス

### ログローテーション
```bash
# ログファイルの手動ローテーション
sudo logrotate -f /etc/logrotate.d/experiment-app
```

### バックアップ
```bash
# 設定ファイルのバックアップ
tar -czf deployment-backup-$(date +%Y%m%d).tar.gz deployment/
```

## 🆘 サポート

問題が発生した場合：
1. このREADMEのトラブルシューティングセクションを確認
2. ログファイルを確認
3. サービス状態を確認
4. 必要に応じて `./deploy.sh status` で現在の状態を確認

## 🔄 移行ガイド（旧形式から新形式へ）

### 既存の旧形式を使用している場合

既存の設定ファイルがある場合の移行手順：

1. **現在のサービスを停止**
```bash
sudo systemctl stop experiment-development
sudo systemctl stop experiment-production
```

2. **新しいデプロイスクリプトを使用**
```bash
sudo ./deploy.sh development  # または production
```

3. **旧ファイルの削除（オプション）**
```bash
# 確認後、不要になった旧ファイルを削除
rm gunicorn_development.conf.py
rm gunicorn_production.conf.py
rm switch_to_development.sh
rm switch_to_production.sh
```

### 新旧対応表

| 旧ファイル | 新ファイル |
|-----------|-----------|
| `gunicorn_development.conf.py` | `environments/development/gunicorn.conf.py` |
| `gunicorn_production.conf.py` | `environments/production/gunicorn.conf.py` |
| `systemd/experiment-*.service` | `environments/*/systemd.service` |
| `switch_to_*.sh` | `deploy.sh [environment]` |

## 📊 変更点サマリー

✅ **追加された機能:**
- 統一されたデプロイスクリプト（`deploy.sh`）
- 環境別ディレクトリ構造
- カラー出力付きのログ表示
- 自動ヘルスチェック
- サービス状態確認機能
- 共通設定ファイル

✅ **改善された点:**
- より明確なファイル構造
- 簡単な環境切り替え
- エラーハンドリングの改善
- 包括的なドキュメント
- 設定の一元管理
