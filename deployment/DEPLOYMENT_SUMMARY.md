# Deployment Structure Summary

## 📁 整理後のディレクトリ構造

```
deployment/
├── README.md                    # メインドキュメント
├── setup.sh                    # 初期セットアップスクリプト
├── deploy.sh                   # 統一デプロイメントスクリプト
├── common.conf                 # 共通設定値
├── environments/              # 環境別設定ディレクトリ
│   ├── development/          # 開発環境
│   │   ├── gunicorn.conf.py # Gunicorn設定
│   │   └── systemd.service  # systemdサービス定義
│   └── production/           # 本番環境
│       ├── gunicorn.conf.py # Gunicorn設定
│       └── systemd.service  # systemdサービス定義
├── systemd/                  # 旧形式（互換性維持）
│   ├── experiment-development.service
│   └── experiment-production.service
└── legacy_backup/            # 旧ファイルのバックアップ
    ├── gunicorn_development.conf.py
    ├── gunicorn_production.conf.py
    ├── switch_to_development.sh
    └── switch_to_production.sh
```

## 🔄 主な変更点

### ✅ 追加されたファイル
- `deploy.sh` - 統一デプロイメントスクリプト
- `common.conf` - 共通設定ファイル
- `environments/` - 環境別設定ディレクトリ
- `legacy_backup/` - 旧ファイルバックアップ

### 🔧 改善されたファイル
- `setup.sh` - カラー出力とエラーハンドリング追加
- `README.md` - 包括的なドキュメントに更新

### 📦 移動されたファイル
- 旧gunicorn設定ファイル → `legacy_backup/`
- 旧切り替えスクリプト → `legacy_backup/`

## 🚀 新しいワークフロー

### 従来の方法
```bash
# 旧方式（手動）
sudo cp systemd/experiment-development.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable experiment-development
sudo systemctl start experiment-development
```

### 新しい方法
```bash
# 新方式（自動化）
sudo ./deploy.sh development
```

## 📋 利用可能なコマンド

```bash
# 初期セットアップ
sudo ./setup.sh

# 開発環境デプロイ
sudo ./deploy.sh development
sudo ./deploy.sh dev

# 本番環境デプロイ
sudo ./deploy.sh production
sudo ./deploy.sh prod

# サービス状態確認
sudo ./deploy.sh status

# 全サービス停止
sudo ./deploy.sh stop

# ヘルプ表示
./deploy.sh help
```

## 🔐 権限とセキュリティ

### 開発環境
- 実行ユーザー: `ec2-user`
- ログレベル: `debug`
- 自動リロード: 有効
- セキュリティ: 開発向け緩和設定

### 本番環境
- 実行ユーザー: `www-data`
- ログレベル: `info`
- 自動リロード: 無効
- セキュリティ: 本番向け強化設定

## 📝 移行の利点

1. **統一されたデプロイ体験** - 一つのスクリプトで全環境対応
2. **設定の整理** - 環境別にディレクトリを分離
3. **エラーハンドリング改善** - 詳細なログとエラー処理
4. **自動ヘルスチェック** - デプロイ後の動作確認
5. **バックワード互換性** - 旧ファイルは保持
6. **包括的なドキュメント** - 詳細な使用方法とトラブルシューティング

## 🔄 今後の保守

- `environments/` 内の設定ファイルを編集
- `common.conf` で共通設定を管理
- `legacy_backup/` は必要に応じて削除可能
- 新機能は `deploy.sh` に追加
