import os
import logging
import traceback
import json
import inspect
from logging.handlers import RotatingFileHandler
import datetime
import sys

# グローバル設定のデフォルト値
DEFAULT_CONFIG = {
    'LOG_LEVEL': 'INFO',
    'LOG_DIR': 'logs',
    'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    'INCLUDE_TRACE': True,
    'MAX_LOG_SIZE': 10 * 1024 * 1024,  # 10MB
    'BACKUP_COUNT': 5
}

# グローバル設定を保持する変数
config = DEFAULT_CONFIG.copy()

def configure_logging(config_dict=None):
    """
    ロギング設定を更新する

    Args:
        config_dict (dict): 更新する設定の辞書
    """
    if config_dict:
        config.update(config_dict)


def get_log_level(level_name):
    """
    文字列のログレベルを logging モジュールの定数に変換する

    Args:
        level_name (str): ログレベルの文字列表現

    Returns:
        int: logging モジュールのログレベル定数
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_name.upper(), logging.INFO)


def setup_logger(name, log_level=None, log_dir=None, log_format=None):
    """
    アプリケーション用のロガーをセットアップする

    Args:
        name (str): ロガーの名前
        log_level (str, optional): ログレベル（'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'）
        log_dir (str, optional): ログファイルを保存するディレクトリ
        log_format (str, optional): ログフォーマット

    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    # 設定からデフォルト値を取得
    log_level = log_level or config['LOG_LEVEL']
    log_dir = log_dir or config['LOG_DIR']
    log_format = log_format or config['LOG_FORMAT']
    max_bytes = config['MAX_LOG_SIZE']
    backup_count = config['BACKUP_COUNT']

    # ロギングレベルの数値を取得
    level_num = get_log_level(log_level)

    # ロガーの取得
    logger = logging.getLogger(name)
    logger.setLevel(level_num)

    # すでにハンドラが設定されている場合は追加しない
    if logger.handlers:
        return logger

    # ログディレクトリが存在しない場合は作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 日付を含むログファイル名を作成
    today = datetime.datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'{name}_{today}.log')

    # ファイルハンドラの設定
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level_num)

    # コンソールハンドラの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_num)

    # フォーマットの設定
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # ハンドラをロガーに追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class ErrorLogger:
    """
    エラーログ記録のためのユーティリティクラス
    """

    def __init__(self, logger=None):
        """初期化"""
        self.logger = logger or setup_logger('error_logger')

    def log_exception(self, exc, level='ERROR', context=None, include_traceback=None):
        """
        例外をログに記録する

        Args:
            exc (Exception): 発生した例外
            level (str): ログレベル
            context (dict): 追加のコンテキスト情報
            include_traceback (bool): トレースバックを含めるかどうか
        """
        if include_traceback is None:
            include_traceback = config['INCLUDE_TRACE']

        # 呼び出し元の情報を取得
        caller_frame = inspect.currentframe().f_back
        filename = caller_frame.f_code.co_filename
        lineno = caller_frame.f_lineno
        function_name = caller_frame.f_code.co_name

        # エラーメッセージを構築
        error_info = {
            'exception_type': exc.__class__.__name__,
            'exception_message': str(exc),
            'file': os.path.basename(filename),
            'line': lineno,
            'function': function_name,
        }

        if context:
            error_info['context'] = context

        if include_traceback:
            error_info['traceback'] = traceback.format_exc()

        # JSONに変換できるかチェック
        try:
            error_json = json.dumps(error_info, ensure_ascii=False)
        except (TypeError, ValueError):
            # JSONに変換できない場合はコンテキストを除外
            if 'context' in error_info:
                del error_info['context']
            error_json = json.dumps(error_info, ensure_ascii=False)

        # ログレベルに応じてログ記録
        log_method = getattr(self.logger, level.lower(), self.logger.error)
        log_method(f"エラーが発生しました: {error_json}")
        
        return error_info

    def log_api_error(self, request, exc, status_code=500):
        """
        API関連のエラーをログに記録する

        Args:
            request: リクエストオブジェクト
            exc (Exception): 発生した例外
            status_code (int): HTTPステータスコード

        Returns:
            dict: エラー情報
        """
        # リクエスト情報を収集
        try:
            request_data = {
                'url': request.path,
                'method': request.method,
                'headers': dict(request.headers),
                'args': dict(request.args)
            }

            # POSTリクエストのボディを追加
            if request.method == 'POST':
                if request.is_json:
                    request_data['body'] = request.json
                else:
                    request_data['form'] = request.form.to_dict()
        except Exception as e:
            request_data = {'error': f"リクエストデータの解析エラー: {str(e)}"}

        context = {
            'request': request_data,
            'status_code': status_code
        }

        return self.log_exception(exc, level='ERROR', context=context)


class UserFriendlyError(Exception):
    """
    ユーザーフレンドリーなエラーメッセージを含む例外クラス
    """

    def __init__(self, message, user_message=None, status_code=500, recovery_path=None, error_code=None):
        """
        初期化

        Args:
            message (str): 開発者向けの詳細なエラーメッセージ
            user_message (str): ユーザー向けの表示メッセージ
            status_code (int): HTTPステータスコード
            recovery_path (str): リカバリーパスのURL
            error_code (str): エラーコード
        """
        super().__init__(message)
        self.user_message = user_message or "システムエラーが発生しました。しばらく経ってからもう一度お試しください。"
        self.status_code = status_code
        self.recovery_path = recovery_path
        self.error_code = error_code or 'SYSTEM_ERROR'

    def to_dict(self):
        """
        エラー情報を辞書形式で返す

        Returns:
            dict: エラー情報
        """
        return {
            'error': True,
            'error_code': self.error_code,
            'message': self.user_message,
            'status_code': self.status_code,
            'recovery_path': self.recovery_path
        }


# シングルトン用インスタンス
error_logger = ErrorLogger()

# アプリケーションのメインロガー
app_logger = setup_logger('experiment_app')