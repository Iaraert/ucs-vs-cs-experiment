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
│   ├── res_user_data_exp1.csv     # 実験1のユーザーデータ
│   ├── res_estimations_exp1.csv   # 実験1の回答データ
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
│       │   ├── data-manager.js# データ管理クラス
│       │   ├── event-bus.js   # イベント通知システム
│       │   ├── event-handler.js# イベントハンドラー
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

## データ収集

以下のデータが収集されます:
- **ユーザーデータ**: 参加者情報、ブラウザ情報、実験所要時間
- **実験回答データ**: 実験課題への回答と評価値
- **IMC結果**: 指示操作確認課題の結果（実験の有効性確認用）
- **CRTデータ**: 認知反射テストの回答と所要時間（認知傾向測定用）

## データ分析

収集したデータの分析手順:

1. **データの前処理**
```python
from utils.data_handler import DataHandler
handler = DataHandler()
processed_data = handler.preprocess_data("res_user_data_exp1.csv", "res_estimations_exp1.csv")
```

2. **実験結果の可視化**
```python
import pandas as pd
import matplotlib.pyplot as plt

# データ読み込み
df = pd.read_csv("data/res_estimations_exp1.csv")

# 条件ごとの結果集計
results = df.groupby(['stimuli', 'number']).mean()
results.plot(kind='bar')
plt.show()
```

3. **統計分析**
```python
import scipy.stats as stats

# 条件間の差の検定
condition1 = df[df['sample_type'] == 'matched']['estimation']
condition2 = df[df['sample_type'] == 'unmatched']['estimation']
t_stat, p_value = stats.ttest_ind(condition1, condition2)
print(f"t統計量: {t_stat}, p値: {p_value}")
```

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

- examine1:   ICOOON MONO(https://icooon-mono.com/)
- examine1_2: いらすとや

## 参考にしたサイト
- SQLite の基礎 #Database - Qiita: https://qiita.com/shikuno_dev/items/13de104aa2c2adf8aead
- SQLite3を用いたSQL入門: https://www.aise.ics.saitama-u.ac.jp/~gotoh/Lectures/TUS_IP/IntroSQLBySQLite3.html
- 【Python】sqlite3.connect() の使い方と実行結果 — シラベルノート: https://pyex.srbrnote.work/library/sqlite3/sqlite3.connect.html

- threading --- スレッドベースの並列処理 — Python 3.10.17 ドキュメント: https://docs.python.org/ja/3.10/library/threading.html
- Pythonの「threading.Lock」とは？ | プログラミング単語帳: https://programming-tango.jp/vocabulary/7151/
- pythonでマルチスレッドについて勉強してみる: https://qiita.com/jabberwocky3376/items/60b8b133eb9151147c7e

- RESTful API: https://zenn.dev/mstng/articles/1c2e0fecbab103
- 実践：はじめてのWebAPI設計: https://qiita.com/kazuki_tachikawa/items/7dab01ac2ea08b85fb15
- RESTful API 設計の極意：実践ガイド: https://qiita.com/Leapcell/items/d57e5e180c1812d88f8b

- 動的SQLの使用方法: https://docs.oracle.com/cd/E16338_01/appdev.112/b61344/ch_ten.htm
- 7.1 動的SQLの概念: https://software.fujitsu.com/jp/manual/manualfiles/M070075/J2X01638/01Z200/sqlbg07/sqlbg069.html
- 動的SQLの使用方法 https://docs.oracle.com/cd/F82042_01/zzpre/using-dynamic-SQL.html#GUID-09DE3FA0-C622-466A-9A2E-A7735A970271

- Javaでデザインパターンを学ぶ：Observerパターン - 土日の勉強ノート: https://daisuke20240310.hatenablog.com/entry/observer
- JavaScriptでObserverパターンの理解: https://viblo.asia/p/javascript%E3%81%A7observer%E3%83%91%E3%82%BF%E3%83%BC%E3%83%B3%E3%81%AE%E7%90%86%E8%A7%A3-E1XVOXlp4Mz