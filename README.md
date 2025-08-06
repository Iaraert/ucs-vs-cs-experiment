# UCS vs CS 実験アプリケーション

このプロジェクトは、実験参加者を条件間（asymmetric条件とsymmetric条件）にバランス良く割り当て、実験刺激を表示し、回答データを収集するためのWebアプリケーションです。クラウドワークスを通じた実験参加者の募集と謝金支払いに対応しています。

## 機能概要

- **参加者管理**: ユーザーIDに基づいて参加者を追跡し、実験条件を割り当て
- **条件割り当て**: asymmetric/symmetric条件に参加者を均等に振り分け
- **実験プロセス**: 複数ステップの実験画面を順に提示
  - 注意事項確認（top1.html）
  - 実験条件説明（top1_2.html）
  - 実験タスク画面（examine1.html, examine1_2.html, examine2.html）
  - 認知反射テスト（CRT）の実施（examine3.html）
- **パフォーマンス最適化**: 画像の遅延読み込みとプリロード機能によるスムーズな表示
- **データ収集**: 実験回答、認知的傾向測定結果の保存
- **完了処理**: 謝金支払いのための完了コード発行（end.html）
- **ブラウザ対応**: Chrome, Firefox, Edge, Safariなど主要ブラウザに対応
- **モジュラー設計**: ES6モジュール、Observerパターン、イベント駆動アーキテクチャ
- **エラーハンドリング**: 包括的なエラー処理とリトライ機能
- **データ整合性**: SQLiteデータベースによる参加者管理と条件割り当ての追跡

## プロジェクト構造

```
ucs_vs_cs_experiment-summary/
├── README.md              # プロジェクト説明書（本ファイル）
├── requirements.txt       # 本番環境用の依存パッケージ
├── requirements-dev.txt   # 開発環境用の依存パッケージ
├── server.py              # 開発用サーバー起動スクリプト
├── wsgi.py                # 本番環境用WSGIアプリケーション
│
├── config/                # 設定管理
│   ├── settings.py        # アプリケーション設定（環境別）
│   └── nginx.conf         # Nginxサーバー設定
│
├── data/                  # データ保存ディレクトリ
│   ├── participant_allocation.db  # 参加者割り当て用データベース
│   ├── res_user_data_exp1.csv     # 実験1のユーザーデータ（過去データ）
│   ├── res_estimations_exp1.csv   # 実験1の回答データ（過去データ）
│   ├── user_data_exp1.csv         # 実験1の現在のユーザーデータ（43名）
│   ├── estimations_exp1.csv       # 実験1の現在の回答データ（204件）
│   ├── imc_data_exp2.csv          # 実験2（IMC）のデータ
│   ├── crt_data_exp3.csv          # 実験3（CRT）のデータ
│   └── *.csv              # その他のデータファイル
│
├── exp/                   # Flaskアプリケーションのメインパッケージ
│   ├── __init__.py        # アプリケーション初期化
│   ├── config.py          # アプリケーション固有の設定
│   ├── views.py           # ルーティングとビュー関数
│   ├── error_handlers.py  # エラーハンドリング処理
│   ├── templates/         # HTMLテンプレート
│   │   ├── exp/           # 実験画面テンプレート
│   │   │   ├── top1.html      # 注意事項画面
│   │   │   ├── top1_2.html    # 実験説明画面
│   │   │   ├── examine1.html  # 実験画面1
│   │   │   ├── examine1_2.html# 拡張実験画面1.2
│   │   │   ├── examine2.html  # 実験画面2（IMC含む）
│   │   │   ├── examine3.html  # 認知反射テスト画面
│   │   │   └── end.html       # 完了・謝金コード画面
│   │   └── error/         # エラーページテンプレート
│   │       ├── 404.html       # Not Foundエラー
│   │       └── 500.html       # サーバーエラー
│   └── static/            # 静的ファイル（CSS, JavaScript）
│       ├── material1.json     # 実験1のシナリオデータ
│       ├── material1_2.json   # 実験1.2のシナリオデータ
│       ├── css/           # スタイルシート
│       │   ├── examine1.css   # 実験1用CSS
│       │   ├── examine1_2.css # 実験1.2用CSS
│       │   ├── examine2.css   # 実験2用CSS
│       │   ├── examine3.css   # 実験3用CSS
│       │   ├── top1.css       # トップページ用CSS
│       │   └── end.css        # 完了ページ用CSS
│       ├── javascript/    # クライアント側スクリプト
│       │   ├── config.js      # 設定管理
│       │   ├── data-manager.js# データ管理クラス（ES6モジュール）
│       │   ├── event-bus.js   # イベント通知システム（Observerパターン）
│       │   ├── event-handler.js# イベントハンドラー
│       │   ├── ajax-utils.js  # Ajax通信ユーティリティ
│       │   ├── ui-manager.js  # UI管理クラス
│       │   ├── utilities.js   # ユーティリティ関数
│       │   ├── examine1.js    # 実験1のロジック
│       │   ├── examine1_2.js  # 実験1.2のロジック
│       │   ├── examine2.js    # 実験2（IMC）のロジック
│       │   └── examine3.js    # 実験3（CRT）のロジック
│       └── images/        # 実験に使用する画像
│           ├── cause/        # 原因を表す画像
│           ├── effect/       # 結果を表す画像
│           └── scenarios/    # シナリオ別の画像
│
├── logs/                  # ログファイル保存ディレクトリ
│   ├── experiment_app_*.log  # アプリケーションログ
│   ├── views_*.log           # ビュー関数のログ
│   └── error_logger_*.log    # エラーログ
│
├── models/                # データモデル
│   └── database.py        # データベース操作クラス
│
├── pre_experiment_data/   # 実験前準備データ
│   ├── res_user_data_exp1.csv   # 予備実験のユーザーデータ
│   └── res_estimations_exp1.csv # 予備実験の回答データ
│
└── utils/                 # ユーティリティ機能
    ├── data_handler.py    # データ処理クラス
    ├── logger.py          # ロギングユーティリティ
    ├── db_viewer.py       # データベース閲覧ツール
    └── check_db.py        # データベースチェックツール
```

## セットアップ手順

### 前提条件
- Python 3.8以上
- pip（Pythonパッケージマネージャー）
- モダンブラウザ（Chrome, Firefox, Edge, Safari最新版推奨）

### インストール

1. リポジトリをクローンまたはダウンロード
```
git clone <リポジトリURL>
cd ucs_vs_cs_experiment-summary
```

2. 仮想環境を作成して有効化
```
python -m venv venv
# Windowsの場合
venv\Scripts\activate
# Linuxの場合
source venv/bin/activate
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt
```

### サーバー起動

開発環境での起動:
```
python server.py
```

デフォルトでは http://127.0.0.1:5000 でアクセス可能。

## 実験フロー

1. **参加者の訪問**: 参加者がトップページにアクセス（/）
2. **注意事項確認**: 実験の注意事項を説明（top1.html）
3. **実験説明**: 実験内容の詳細説明（top1_2.html）
4. **条件割り当て**: ユーザーIDに基づいてasymmetric/symmetric条件を割り当て
5. **実験課題1**: 最初の実験課題を実施（examine1.html/examine1_2.html）
   - 画像のプリロード機能によるスムーズな表示
   - Intersection Observerによる遅延読み込み対応
6. **IMCチェック**: 指示操作確認課題でアテンションを確認（examine2.html）
7. **認知反射テスト**: CRTによる認知的傾向の測定（examine3.html）
8. **完了**: 謝金コード生成と実験終了（end.html）

## データベース構造

実験の条件割り当て、実験パス管理、ユーザー追跡には SQLite データベース（`data/participant_allocation.db`）を使用しています。

### テーブル構造

#### 1. condition_counters テーブル

実験条件の使用回数を管理するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| condition_name | TEXT | 実験条件の名前（asymmetric, symmetric） |
| count | INTEGER | その条件が割り当てられた回数 |

このテーブルは実験条件の均等な割り当てを実現するために使用されます。新しい参加者が実験にアクセスすると、最も割り当て回数の少ない条件が選択されます。

#### 2. allocation_history テーブル

参加者への実験条件の割り当て履歴を記録するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | INTEGER | レコードの自動増加識別子（主キー） |
| user_id | TEXT | 参加者の一意識別子 |
| condition_name | TEXT | 割り当てられた実験条件名（asymmetric, symmetric） |
| timestamp | DATETIME | 条件が割り当てられた日時 |

このテーブルは、どの参加者がどの実験条件に割り当てられたかの完全な履歴を保持します。同じ参加者が再度実験に参加した場合に同じ条件に割り当てるために参照されます。

#### 3. experiment_path_counters テーブル

実験実施順序の使用回数を管理するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| path_type | TEXT | 実験順序の種類（order1, order2） |
| count | INTEGER | その順序が割り当てられた回数 |

このテーブルは実験の実施順序を均等に割り当てるために使用されます。参加者ごとに異なる実験順序を割り当てることで、順序効果をコントロールします。

#### 4. experiment_path_history テーブル

参加者への実験順序の割り当て履歴を記録するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | INTEGER | レコードの自動増加識別子（主キー） |
| user_id | TEXT | 参加者の一意識別子 |
| path_type | TEXT | 割り当てられた実験順序（order1, order2） |
| timestamp | DATETIME | 順序が割り当てられた日時 |

このテーブルは、どの参加者がどの実験順序に割り当てられたかの履歴を保持します。

#### 5. sqlite_sequence テーブル

SQLiteが自動的に管理する、AUTO_INCREMENT列の現在値を記録するシステムテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| name | TEXT | テーブル名 |
| seq | INTEGER | 次に使用される自動増分値 |

## 技術仕様とアーキテクチャ

### フロントエンド技術
- **ES6モジュール**: JavaScriptコードのモジュール化
- **Observerパターン**: イベント駆動アーキテクチャによる疎結合な設計
- **非同期処理**: Promise/async-awaitによる効率的な通信
- **エラーハンドリング**: 包括的なエラー処理とリトライ機能
- **レスポンシブデザイン**: 複数デバイス対応のUI

### バックエンド技術
- **Flask**: 軽量Webフレームワーク
- **SQLite**: 条件割り当て管理用データベース
- **CSV**: 実験データ保存形式
- **ロギング**: 詳細なアプリケーションログ
- **WSGI**: 本番環境対応（Gunicorn）

### データ管理
- **DataManager**: 実験データの一元管理クラス
- **条件バランシング**: 自動的な実験条件の均等配布
- **セッション管理**: ユーザーIDベースの状態管理
- **データ整合性**: トランザクション制御による安全なデータ操作

### パフォーマンス最適化
- **画像プリロード**: 実験画像の事前読み込み
- **Intersection Observer**: 効率的な遅延読み込み
- **イベントバス**: メモリ効率的なイベント通知
- **Ajax最適化**: タイムアウトとリトライ機能付きHTTP通信

## データ収集

以下のデータが収集されます:
- **ユーザーデータ**: 参加者情報、ブラウザ情報、実験所要時間
- **実験回答データ**: 実験課題への回答と評価値
- **IMC結果**: 指示操作確認課題の結果（実験の有効性確認用）
- **CRTデータ**: 認知反射テストの回答と所要時間（認知傾向測定用）

### 現在のデータ収集状況（2025年6月10日時点）

#### 実験1（examine1）
- **参加者数**: 43名
- **回答データ**: 204件の推定値データ
- **ファイルサイズ**: 17.6KB（estimations_exp1.csv）
- **最終更新**: 2025年6月10日 15:10

#### 実験2（IMC - Instructional Manipulation Check）
- **参加者数**: 少数（テスト段階）
- **ファイルサイズ**: 206B（imc_data_exp2.csv）
- **最終更新**: 2025年5月29日 01:23

#### 実験3（CRT - Cognitive Reflection Test）
- **参加者数**: 少数（テスト段階）
- **ファイルサイズ**: 373B（crt_data_exp3.csv）
- **最終更新**: 2025年5月29日 01:23

#### システムログ
- **アプリケーションログ**: 継続的に記録（最新：2025年6月10日）
- **エラーログ**: 問題発生時の詳細記録
- **ビューログ**: ユーザーアクセスパターンの追跡

## 環境変数

アプリケーション設定に以下の環境変数を使用できます:
- `FLASK_ENV`: 実行環境（development, testing, production）
- `PORT`: サーバーのポート番号
- `HOST`: サーバーのホスト設定
- `SECRET_KEY`: セッション暗号化用の秘密鍵
- `LOG_LEVEL`: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

## データバックアップ

実験データのバックアップには以下のコマンドを使用します:

```python
from utils.data_handler import DataHandler
handler = DataHandler()
backup_info = handler.backup_data(suffix="exp1")
print(f"バックアップ作成: {backup_info['backup_dir']}")
```

定期バックアップのためのcronジョブ設定（Linux/Unix）:
```
# 毎日深夜2時にバックアップを実行
0 2 * * * cd /path/to/project && /path/to/venv/bin/python -c 'from utils.data_handler import DataHandler; DataHandler().backup_data()'
```

## 管理ユーティリティ

データベース閲覧:
```
python -m utils.db_viewer
```

データベース整合性チェック:
```
python -m utils.check_db
```

## 本番環境での実行

Gunicornを使用した本番環境での実行:
```
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

Nginxとの連携設定は `config/nginx.conf` を参照してください。

## 開発履歴と最新機能

### 最新の改善点（2025年6月版）
- **ES6モジュール化**: JavaScriptコードの完全なモジュール化
- **Observerパターンの導入**: イベント駆動アーキテクチャによる保守性向上
- **Ajax通信の最適化**: エラーハンドリングとリトライ機能の強化
- **データ整合性の向上**: トランザクション制御の実装
- **パフォーマンス改善**: 画像プリロードとメモリ使用量の最適化

### 技術的な改善点
- **共通サンプルデータ**: `samples_common.json`による効率的なデータ管理
- **条件割り当ての自動化**: SQLiteベースの均等配布システム
- **ログ管理の強化**: 詳細なアプリケーション監視
- **エラー処理の包括化**: ユーザビリティを重視したエラーハンドリング

### 実験デザインの特徴
- **カウンターバランス**: 実験条件と順序の均等配布
- **参加者追跡**: ユーザーIDベースの一意識別
- **データ品質管理**: IMCによるアテンション確認
- **認知測定**: CRTによる個人差の測定

## ブラウザ互換性

本アプリケーションは以下のブラウザで動作確認済みです:
- Google Chrome 109.0以上

## トラブルシューティング

1. **画像が表示されない**
   - ブラウザのキャッシュをクリアしてリロード
   - 開発者ツールでネットワークエラーを確認

2. **データが保存されない**
   - ログファイル（logs/）でエラーを確認
   - データディレクトリ（data/）の書き込み権限を確認

3. **サーバー起動エラー**
   - Pythonバージョンの確認（3.8以上必須）
   - 依存パッケージの再インストール: `pip install -r requirements.txt`

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