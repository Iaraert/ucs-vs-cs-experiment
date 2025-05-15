from flask import render_template, jsonify, request
from exp import app
from utils.logger import error_logger, UserFriendlyError

# カスタムエラーハンドラーの登録
@app.errorhandler(404)
def page_not_found(e):
    """
    404 Not Found エラーハンドラー
    """
    error_logger.logger.warning(f"404エラー: {request.path}")
    
    # APIリクエストとHTMLリクエストで応答を分ける
    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({
            'error': True,
            'message': 'リクエストされたリソースが見つかりません',
            'status_code': 404,
            'recovery_path': app.config.get('DEFAULT_RECOVERY_PATH', '/')
        }), 404
    
    return render_template(app.config.get('ERROR_TEMPLATES', {}).get('404', 'error/404.html')), 404


@app.errorhandler(500)
def internal_server_error(e):
    """
    500 Internal Server Error ハンドラー
    """
    # エラーのログ記録
    if isinstance(e, UserFriendlyError):
        error_info = error_logger.log_exception(e, level='ERROR')
        user_message = e.user_message
        recovery_path = e.recovery_path or app.config.get('DEFAULT_RECOVERY_PATH', '/')
        status_code = e.status_code
    else:
        error_info = error_logger.log_exception(e, level='ERROR')
        user_message = app.config.get('DEFAULT_ERROR_MESSAGE', 'システムエラーが発生しました。')
        recovery_path = app.config.get('DEFAULT_RECOVERY_PATH', '/')
        status_code = 500
    
    # APIリクエストとHTMLリクエストで応答を分ける
    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({
            'error': True,
            'message': user_message,
            'status_code': status_code,
            'recovery_path': recovery_path
        }), status_code
    
    return render_template(
        app.config.get('ERROR_TEMPLATES', {}).get('500', 'error/500.html'),
        error_message=user_message,
        recovery_path=recovery_path
    ), status_code


@app.errorhandler(UserFriendlyError)
def handle_user_friendly_error(e):
    """
    カスタムエラークラスのハンドラー
    """
    error_logger.log_exception(e, level='ERROR')
    
    # APIリクエストとHTMLリクエストで応答を分ける
    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify(e.to_dict()), e.status_code
    
    return render_template(
        app.config.get('ERROR_TEMPLATES', {}).get('default', 'error/500.html'),
        error_message=e.user_message,
        recovery_path=e.recovery_path or app.config.get('DEFAULT_RECOVERY_PATH', '/')
    ), e.status_code


# すべての未処理の例外を捕捉するためのエラーハンドラー
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """
    未処理の例外をキャッチするフォールバックハンドラー
    """
    error_info = error_logger.log_exception(e, level='ERROR')
    
    # APIリクエストとHTMLリクエストで応答を分ける
    if request.path.startswith('/api/') or request.is_json or request.headers.get('Accept') == 'application/json':
        return jsonify({
            'error': True,
            'message': app.config.get('DEFAULT_ERROR_MESSAGE', 'システムエラーが発生しました。'),
            'status_code': 500,
            'recovery_path': app.config.get('DEFAULT_RECOVERY_PATH', '/')
        }), 500
    
    return render_template(
        app.config.get('ERROR_TEMPLATES', {}).get('default', 'error/500.html'),
        error_message=app.config.get('DEFAULT_ERROR_MESSAGE', 'システムエラーが発生しました。'),
        recovery_path=app.config.get('DEFAULT_RECOVERY_PATH', '/')
    ), 500


# フロントエンドからのエラーレポートを受け取るエンドポイント
@app.route('/api/report-error', methods=['POST'])
def report_client_error():
    """
    フロントエンドからのエラー報告を受け取り、ログに記録する
    """
    try:
        data = request.get_json() or {}
        
        error_message = data.get('message', 'Unknown client error')
        error_type = data.get('type', 'ClientError')
        error_stack = data.get('stack', '')
        error_context = data.get('context', {})
        
        # 構造化されたエラー情報をログに記録
        error_logger.logger.error(f"フロントエンドエラー ({error_type}): {error_message}", extra={
            'client_error': {
                'type': error_type,
                'message': error_message,
                'stack': error_stack,
                'context': error_context,
                'user_agent': request.headers.get('User-Agent'),
                'referrer': request.headers.get('Referer'),
                'url': data.get('url', request.headers.get('Referer', '')),
            }
        })
        
        return jsonify({
            'status': 'success', 
            'message': 'エラーが正常に記録されました'
        })
        
    except Exception as e:
        error_logger.log_exception(e, level='ERROR')
        return jsonify({
            'status': 'error',
            'message': 'エラーの記録中に問題が発生しました'
        }), 500