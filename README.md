# UCS vs CS 実験アプリケーション

このプロジェクトは、実験参加者を条件間（matched条件とunmatched条件）にバランス良く割り当て、実験刺激を表示し、回答データを収集するためのWebアプリケーションです。クラウドワークスを通じた実験参加者の募集と謝金支払いに対応しています。

## 機能概要

- **参加者管理**: ユーザーIDに基づいて参加者を追跡し、実験条件を割り当て
- **条件割り当て**: matched/unmatched条件に参加者を均等に振り分け
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
4. **条件割り当て**: ユーザーIDに基づいてmatched/unmatched条件を割り当て
5. **実験課題1**: 最初の実験課題を実施（examine1.html/examine1_2.html）
   - 画像のプリロード機能によるスムーズな表示
   - Intersection Observerによる遅延読み込み対応
6. **IMCチェック**: 指示操作確認課題でアテンションを確認（examine2.html）
7. **認知反射テスト**: CRTによる認知的傾向の測定（examine3.html）
8. **完了**: 謝金コード生成と実験終了（end.html）

## データベース構造

実験の条件割り当てとユーザー追跡には SQLite データベース（`data/participant_allocation.db`）を使用しています。

### テーブル構造

#### 1. condition_counters テーブル

実験条件の使用回数を管理するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| condition_name | TEXT | 実験条件の名前（matched, unmatched, asymmetric, symmetric） |
| count | INTEGER | その条件が割り当てられた回数 |

このテーブルは実験条件の均等な割り当てを実現するために使用されます。新しい参加者が実験にアクセスすると、最も割り当て回数の少ない条件が選択されます。

#### 2. allocation_history テーブル

参加者への実験条件の割り当て履歴を記録するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | INTEGER | レコードの自動増加識別子（主キー） |
| user_id | TEXT | 参加者の一意識別子 |
| condition_name | TEXT | 割り当てられた実験条件名 |
| timestamp | DATETIME | 条件が割り当てられた日時 |

このテーブルは、どの参加者がどの実験条件に割り当てられたかの完全な履歴を保持します。同じ参加者が再度実験に参加した場合に同じ条件に割り当てるために参照されます。

### データベース操作

データベースの閲覧と編集には以下のユーティリティが用意されています：

#### データベース閲覧

```bash
python -m utils.db_viewer
```

実行すると、各テーブルの構造と内容が表示されます。

#### データベース編集

```bash
python -m utils.db_editor
```

対話式インターフェースで以下の操作が可能です：
- テーブル一覧の表示
- テーブル構造の確認
- テーブル内容の表示
- SQLクエリの実行
- 条件カウンターの追加・更新
- 割り当て履歴の追加
- 条件カウンターのリセット

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

- examine1: ICOOON MONO(https://icooon-mono.com/)
- 薬剤画像: いらすと屋