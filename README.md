# UCS vs CS 実験システム

## 概要
因果判断課題（UCS vs CS）のオンライン実験システム。Flask + Gunicorn で構成されたWebアプリケーション。開発は `server.py`、本番は `wsgi.py` を利用する。

## クイックスタート（開発）
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python server.py
```
- デフォルトはポート5000で起動する。

## デプロイ（本番）
デプロイ手順は `deployment/README.md` を参照。

## ディレクトリ概要
```
cs_vs_ising_tomita/
├── server.py                # 開発用サーバー起動
├── wsgi.py                  # 本番用WSGIエントリーポイント
├── requirements.txt         # 本番依存
├── requirements-dev.txt     # 開発依存
├── exp/                     # 実験アプリ本体（ルーティング/静的ファイル/テンプレート）
├── models/                  # DB操作
├── utils/                   # 解析・運用補助スクリプト
├── config/                  # アプリ設定
├── deployment/              # デプロイ設定
└── data/                    # 実験データ（CSV/DB）
```

## 実験フロー（主要ルート）
1. `/t0P1` : 説明・同意
2. `/t0P12` : 詳細説明
3. `/eXaMinE1` : 実験1（リスト形式）
4. `/eXaM1nE_2` : 実験1.2（オンライン形式）
5. `/Ex2` : 実験2（IMC）
6. `/CRT3` : 実験3（CRT）
7. `/end` : 終了

## データと注意事項
- `data/participant_allocation.db` は自動生成される。
- 個人情報は Git 管理対象から除外する（`.gitignore` を確認）。
- ログは `logs/` に出力されるため、必要に応じてバックアップを取得する。

## トラブルシューティング（最小）
```bash
# DB初期化
python -c "from models.database import Database; db = Database(); db.init_db()"

# ポート5000の使用状況
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows
```

## 使用された画像

- examine1, examine1_2:   ICOOON MONO(https://icooon-mono.com/)

## 参考にしたサイト
### SQLite
- SQLite の基礎 #Database - Qiita: https://qiita.com/shikuno_dev/items/13de104aa2c2adf8aead
- SQLite3を用いたSQL入門: https://www.aise.ics.saitama-u.ac.jp/~gotoh/Lectures/TUS_IP/IntroSQLBySQLite3.html
- 【Python】sqlite3.connect() の使い方と実行結果 — シラベルノート: https://pyex.srbrnote.work/library/sqlite3/sqlite3.connect.html

### threading
- threading --- スレッドベースの並列処理 — Python 3.10.17 ドキュメント: https://docs.python.org/ja/3.10/library/threading.html
- Pythonの「threading.Lock」とは？ | プログラミング単語帳: https://programming-tango.jp/vocabulary/7151/
- pythonでマルチスレッドについて勉強してみる: https://qiita.com/jabberwocky3376/items/60b8b133eb9151147c7e

### RESTful API
- RESTful API: https://zenn.dev/mstng/articles/1c2e0fecbab103
- 実践：はじめてのWebAPI設計: https://qiita.com/kazuki_tachikawa/items/7dab01ac2ea08b85fb15
- RESTful API 設計の極意：実践ガイド: https://qiita.com/Leapcell/items/d57e5e180c1812d88f8b

### 動的SQL
- 動的SQLの使用方法: https://docs.oracle.com/cd/E16338_01/appdev.112/b61344/ch_ten.htm
- 7.1 動的SQLの概念: https://software.fujitsu.com/jp/manual/manualfiles/M070075/J2X01638/01Z200/sqlbg07/sqlbg069.html
- 動的SQLの使用方法 https://docs.oracle.com/cd/F82042_01/zzpre/using-dynamic-SQL.html#GUID-09DE3FA0-C622-466A-9A2E-A7735A970271

### Observerパターン
- Javaでデザインパターンを学ぶ：Observerパターン - 土日の勉強ノート: https://daisuke20240310.hatenablog.com/entry/observer
- JavaScriptでObserverパターンの理解: https://viblo.asia/p/javascript%E3%81%A7observer%E3%83%91%E3%82%BF%E3%83%BC%E3%83%B3%E3%81%AE%E7%90%86%E8%A7%A3-E1XVOXlp4Mz

### Gunicorn
- Gunicornってなんだろう？WSGIってなんだろう？｜Fuji: https://note.com/shirotabistudy/n/n99fcb1586fd1

### Nginx
- EC2のAmazon LinuxにNginxを入れてFlaskを動かす方法: https://zenn.dev/century/articles/6b7d6ad29605f8
- 【AWS EC2】Amazon Linux2にnginxをインストールする方法: https://qiita.com/tamorieeeen/items/07743216a3662cfca890


### Systemd
- man systemd.service 日本語訳 #Linux - Qiita: https://qiita.com/JhonnyBravo/items/a28074c20fa9adf02be3
- これからSystemd入門する: https://qiita.com/bluesDD/items/eaf14408d635ffd55a18
- Oracle Linux 9 Managing the System With systemd: https://docs.oracle.com/en/operating-systems/oracle-linux/9/systemd/index.html
- Linux女子部　systemd徹底入門: https://www.slideshare.net/slideshow/linux-27872553/27872553