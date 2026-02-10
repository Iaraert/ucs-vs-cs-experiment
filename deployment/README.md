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

## 初回セットアップ
```bash
sudo ./setup.sh
```
- アプリ配置: `/opt/ucs-vs-cs-experiment`
- 必要なパッケージと仮想環境を準備する。

## デプロイ
```bash
./deploy.sh development
./deploy.sh production
./deploy.sh status
./deploy.sh stop
```

## 主要設定（common.conf）
- `APP_DIR=/opt/ucs-vs-cs-experiment`
- `APP_PORT=9876`
- `APP_HOST=127.0.0.1`
- `DEFAULT_TIMEOUT=120`
- `WORKER_TMP_DIR=/dev/shm`

## 環境差分（要点）
- 開発: `workers=1`, `reload=True`, `loglevel=debug`, `user=ec2-user`
- 本番: `workers=2`, `preload_app=True`, `loglevel=info`, `user=www-data`, `max_requests=2000`

## 運用コマンド
```bash
# systemd
sudo systemctl start experiment-production
sudo systemctl stop experiment-production
sudo systemctl status experiment-production

# Gunicorn logs
tail -f /opt/ucs-vs-cs-experiment/logs/gunicorn_error_prod.log
```

## トラブルシューティング（最小）
```bash
# 起動失敗時のログ確認
journalctl -u experiment-production -n 100

# ポート競合
sudo lsof -i :9876
```

**最終更新**: 2026年1月28日
