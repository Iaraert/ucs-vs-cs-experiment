# UCS vs CS Experiment - 本番環境用Systemdサービス

## 概要
本番環境向けの安全で最小限のsystemdサービス設定です。セキュリティとパフォーマンスを重視した設定になっています。

## 特徴
- セキュリティ強化（NoNewPrivileges、PrivateTmp）
- 安全な再起動制限（300秒間に3回まで）
- 適切なログ管理
- 本番環境用の環境変数設定

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
```

### ログ確認
```bash
# リアルタイムログ
sudo journalctl -u experiment-simple -f

# 最新ログ
sudo journalctl -u experiment-simple -n 50

# エラーログのみ
sudo journalctl -u experiment-simple -p err
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
```

### よくある問題
1. **Python仮想環境のパスが間違っている**
   - `/opt/experiment/venv/bin/python`が存在するか確認

2. **権限エラー**
   - `sudo chown -R www-data:www-data /opt/experiment`を実行

3. **ポートが使用中**
   - `sudo netstat -tlnp | grep 9876`でポート使用状況を確認

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