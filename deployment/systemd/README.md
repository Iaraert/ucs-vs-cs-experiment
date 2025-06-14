# UCS vs CS Experiment - 本番環境用Systemdサービス

## 概要
本番環境向けの安全で信頼性の高いsystemdサービス設定です。ループ状態やクラッシュからの自動復旧を重視した堅牢な設定になっています。

## 特徴
- **ループ防止**: 30秒の再起動間隔、10分間に3回までの制限
- **ヘルスチェック**: 起動時の正常性確認とポート待機
- **グレースフルシャットダウン**: 適切なシグナル処理
- **セキュリティ強化**: ProtectSystem、ReadWritePaths制御
- **エラーコード制御**: 特定の終了コードでは再起動を抑制

## 主な改善点
### 1. 再起動制御の最適化
- `RestartSec=30`: 再起動間隔を30秒に延長（ループ防止）
- `StartLimitInterval=600`: 監視期間を10分に延長
- `RestartPreventExitStatus=1 2 3`: 特定の終了コードでは再起動しない

### 2. ヘルスチェック機能
- `/health`エンドポイントによる正常性確認
- データベース接続とログディレクトリの書き込み権限チェック
- 起動後5秒待機 + ポート待機確認

### 3. セキュリティ強化
- `ProtectSystem=strict`: システムディレクトリを読み取り専用に
- `ReadWritePaths`: 必要な書き込みパスのみ許可
- `ProtectHome=yes`: ホームディレクトリを保護

## ファイル構成
- `experiment-simple.service` - 本番環境用systemdサービス定義
- `setup.sh` - 本番環境用セットアップスクリプト

## 前提条件
- Ubuntu/Debian系Linuxサーバー
- Python 3.6以上
- root権限

## インストール手順

### 1. セットアップの実行
```bash
# systemdディレクトリに移動
cd deployment/systemd

# セットアップスクリプトを実行可能にする
chmod +x setup.sh

# セットアップを実行（root権限が必要）
sudo ./setup.sh
```

### 2. アプリケーションのデプロイ
```bash
# アプリケーションファイルをコピー
sudo cp -r /path/to/your/app/* /opt/experiment/

# 仮想環境を作成
sudo python3 -m venv /opt/experiment/venv

# 依存関係をインストール
sudo /opt/experiment/venv/bin/pip install -r /opt/experiment/requirements.txt

# 権限を設定
sudo chown -R www-data:www-data /opt/experiment
```

### 3. サービスの起動
```bash
# サービスを有効化
sudo systemctl enable experiment-simple

# サービスを開始
sudo systemctl start experiment-simple

# サービスの状態を確認
sudo systemctl status experiment-simple
```

## サービス管理コマンド

### 基本操作
```bash
# 開始
sudo systemctl start experiment-simple

# 停止
sudo systemctl stop experiment-simple

# 再起動
sudo systemctl restart experiment-simple

# 状態確認
sudo systemctl status experiment-simple

# 有効化/無効化
sudo systemctl enable experiment-simple
sudo systemctl disable experiment-simple

# ヘルスチェック確認
curl http://127.0.0.1:9876/health
```

### ログ確認
```bash
# リアルタイムログ
sudo journalctl -u experiment-simple -f

# 最新ログ
sudo journalctl -u experiment-simple -n 50

# エラーログのみ
sudo journalctl -u experiment-simple -p err

# 起動ログのみ
sudo journalctl -u experiment-simple --since "10 minutes ago"
```

### 再起動制限の確認・リセット
```bash
# 再起動制限の状態確認
sudo systemctl show experiment-simple | grep -E "(NRestarts|RestartUSec)"

# 再起動制限をリセット（緊急時）
sudo systemctl reset-failed experiment-simple
```

## 本番環境での注意事項

### セキュリティ
- サービスは`www-data`ユーザーで実行されます
- `NoNewPrivileges=yes`でセキュリティが強化されています
- 一時ディレクトリが隔離されています

### 監視
- アプリケーションは`127.0.0.1:9876`でリッスンします
- ログは`journalctl`で確認できます
- 5分間に3回以上失敗した場合、再起動が停止されます

### 環境変数
- `FLASK_ENV=production`
- `PORT=9876`
- `HOST=127.0.0.1`

## トラブルシューティング

### サービスが開始しない場合
```bash
# 詳細な状態確認
sudo systemctl status experiment-simple -l

# ログ確認
sudo journalctl -u experiment-simple --no-pager

# ヘルスチェックの確認
curl -v http://127.0.0.1:9876/health
```

### よくある問題と対処法
1. **サービスがループ再起動している**
   - 10分間に3回失敗すると自動的に停止します
   - `sudo systemctl reset-failed experiment-simple`でリセット
   - アプリケーションログで根本原因を確認

2. **Python仮想環境のパスが間違っている**
   - `/opt/experiment/venv/bin/python`が存在するか確認
   - `sudo -u www-data /opt/experiment/venv/bin/python --version`でテスト

3. **権限エラー**
   - `sudo chown -R www-data:www-data /opt/experiment`を実行
   - ログディレクトリとデータディレクトリの書き込み権限を確認

4. **ポートが使用中**
   - `sudo netstat -tlnp | grep 9876`でポート使用状況を確認
   - `sudo lsof -i :9876`で使用中のプロセスを特定

5. **データベース接続エラー**
   - `/opt/experiment/data/`ディレクトリの権限を確認
   - ヘルスチェックでデータベース状態を確認

### 緊急時の手動リセット
```bash
# サービスを完全停止
sudo systemctl stop experiment-simple

# 再起動制限をリセット
sudo systemctl reset-failed experiment-simple

# プロセスが残っている場合は手動で終了
sudo pkill -f "experiment"

# サービスを再開
sudo systemctl start experiment-simple
```

### 安全な削除方法
```bash
# サービスを停止・無効化
sudo systemctl stop experiment-simple
sudo systemctl disable experiment-simple

# サービスファイルを削除
sudo rm /etc/systemd/system/experiment-simple.service
sudo systemctl daemon-reload

# アプリケーションディレクトリを削除（必要に応じて）
sudo rm -rf /opt/experiment
```

## パフォーマンス監視
```bash
# CPU・メモリ使用率
sudo systemctl show experiment-simple --property=MainPID
ps -p <PID> -o pid,ppid,cmd,%mem,%cpu

# サービス起動時間
sudo systemd-analyze blame | grep experiment-simple
```