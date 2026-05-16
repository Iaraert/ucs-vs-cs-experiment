# Deployment Configuration

UCS vs CS 実験システムのデプロイ用設定と運用手順。開発環境と本番環境の両方を対象とする。

## ファイル構成（要点）
```
deployment/
├── common.conf
├── setup.sh
├── deploy.sh
├── environments/
│   ├── development/
│   └── production/
└── systemd/
```

## 前提条件

### EC2インスタンス
- AMI: Amazon Linux 2023（`ec2-user`を使用）
- キーペア: `.pem`形式、`~/.ssh/`に保存し`chmod 400`を設定

### SSHアクセス
```bash
chmod 400 ~/.ssh/my-ec2-key.pem
ssh -i ~/.ssh/my-ec2-key.pem ec2-user@<パブリックIP>
```

VS CodeのRemote-SSHを使う場合は`~/.ssh/config`に以下を追記：
```
Host my-ec2
    HostName <EC2のパブリックIP>
    User ec2-user
    IdentityFile ~/.ssh/my-ec2-key.pem
```

### セキュリティグループ（インバウンドルール）
| タイプ | ポート | ソース | 用途 |
|--------|--------|--------|------|
| SSH | 22 | 自分のIP/32 | SSH接続 |
| HTTP | 80 | 0.0.0.0/0 | ブラウザアクセス |
| カスタムTCP | 9876 | 0.0.0.0/0 | Gunicorn直接アクセス（開発時） |

> **注意**: ソースを特定IPに絞る場合（例: `60.149.136.25/32`）、プロバイダやルーター再起動でIPが変わると接続できなくなる。`curl ifconfig.me`で現在のIPを確認すること。

---

## 初回セットアップ

### リポジトリの配置
```bash
cd /opt
sudo git clone https://github.com/your-user/ucs-vs-cs-experiment.git
sudo chown -R ec2-user:ec2-user /opt/ucs-vs-cs-experiment
```

### セットアップスクリプトの実行
```bash
cd /opt/ucs-vs-cs-experiment
sudo ./deployment/setup.sh
```
- アプリ配置: `/opt/ucs-vs-cs-experiment`
- 必要なパッケージと仮想環境を準備する

> **注意**: スクリプトに実行権限がない場合は`chmod +x`を付与するか`sudo bash ./deployment/setup.sh`で実行する。

### Python仮想環境とGunicornのインストール
```bash
cd /opt/ucs-vs-cs-experiment
python3 -m venv venv-aws
source venv-aws/bin/activate
pip install -r requirements.txt
deactivate
```

### Nginxのインストール
```bash
# Amazon Linux
sudo yum install nginx -y

# Nginxの設定をリポジトリからコピー
sudo cp /opt/ucs-vs-cs-experiment/config/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## デプロイ
```bash
sudo bash /opt/ucs-vs-cs-experiment/deployment/deploy.sh development
sudo bash /opt/ucs-vs-cs-experiment/deployment/deploy.sh production
sudo bash /opt/ucs-vs-cs-experiment/deployment/deploy.sh status
sudo bash /opt/ucs-vs-cs-experiment/deployment/deploy.sh stop
```

> **注意**: deploy.shはアプリのパスを`/opt/ucs-vs-cs-experiment`にハードコードしている。ローカル環境（`~/projects/`など）から実行しても動作しない。必ずEC2上で実行すること。

---

## 主要設定（common.conf）
- `APP_DIR=/opt/ucs-vs-cs-experiment`
- `APP_PORT=9876`
- `APP_HOST=127.0.0.1`
- `DEFAULT_TIMEOUT=120`
- `WORKER_TMP_DIR=/dev/shm`

---

## 環境差分（要点）
- 開発: `workers=1`, `reload=True`, `loglevel=debug`, `user=ec2-user`
- 本番: `workers=2`, `preload_app=True`, `loglevel=info`, `user=ec2-user`（※`www-data`はAmazon Linuxに存在しないため`ec2-user`を使用）, `max_requests=2000`

---

## OS固有の注意事項（Amazon Linux）

### www-dataユーザーについて
`www-data`はUbuntu/Debian固有のWebサーバーユーザー。Amazon Linuxには存在しない。

| OS | Webサーバーユーザー |
|----|----------------------|
| Ubuntu / Debian | `www-data` |
| Amazon Linux / CentOS | `nginx` または `ec2-user` |

deploy.shの`www-data`を`ec2-user`に変更する場合：
```bash
sudo sed -i 's/www-data:www-data/ec2-user:ec2-user/g' \
  /opt/ucs-vs-cs-experiment/deployment/deploy.sh
```

### Gunicornのバインドアドレス
`common.conf`の`APP_HOST=127.0.0.1`はローカルホストのみのアクセスになる。Nginxを使わず直接外部アクセスしたい場合は`0.0.0.0`に変更する：
```bash
sudo sed -i 's/127.0.0.1/0.0.0.0/g' \
  /opt/ucs-vs-cs-experiment/deployment/gunicorn_development.conf.py
```

変更後はサービスを再起動し確認：
```bash
sudo systemctl restart experiment-development
sudo ss -tlnp | grep 9876
# 0.0.0.0:9876 になっていればOK
```

---

## 運用コマンド
```bash
# systemd
sudo systemctl start experiment-production
sudo systemctl stop experiment-production
sudo systemctl status experiment-production

# Gunicorn logs
tail -f /opt/ucs-vs-cs-experiment/logs/gunicorn_error_prod.log
```

---

## トラブルシューティング

### 起動失敗時のログ確認
```bash
journalctl -u experiment-production -n 100
journalctl -xeu experiment-development.service --no-pager
```

### ポート競合・リッスン確認
```bash
sudo ss -tlnp | grep 9876
sudo lsof -i :9876
```

### SSH接続が遅い・繋がらない
```bash
# デバッグモードで接続（どのステップで止まるか確認）
ssh -v -i ~/.ssh/my-ec2-key.pem ec2-user@<IP>

# 自分の現在のIPを確認（セキュリティグループのIP制限と照合）
curl ifconfig.me
```

### Nginxの設定をリポジトリから復元
```bash
cd /opt/ucs-vs-cs-experiment
sudo git checkout config/nginx.conf
```

### exit code 203
`ExecStart`に指定されたコマンドが見つからない。仮想環境が作成されていないか、パスが間違っている。

### exit code 1 / conf.pyが見つからない
Gunicornの設定ファイルが存在しない。`git pull`またはSCPでファイルを取得する：
```bash
scp -i ~/.ssh/my-ec2-key.pem \
  ~/projects/ucs-vs-cs-experiment/deployment/gunicorn_development.conf.py \
  ec2-user@<IP>:/opt/ucs-vs-cs-experiment/deployment/
```

---

**最終更新**: 2026年5月16日