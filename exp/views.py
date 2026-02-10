import datetime
import json
import os
from flask import render_template, request, Response, redirect, jsonify, current_app, Blueprint, session, abort
from flask import Flask, make_response
import hashlib
import time
from threading import Lock

from exp import app
from exp.config import LOG_LEVEL, LOG_DIR
from utils.logger import setup_logger, error_logger, UserFriendlyError
from utils.logger import app_logger  # 追加

# データベースとデータ処理用のクラスをインポート
from models.database import Database
from utils.data_handler import DataHandler

# セキュリティ機能のインポート
from exp.security_handlers import security_bp, analyze_security_patterns
from exp.utils import requires_step, require_exact_step

# インスタンスを初期化
db = Database()
data_handler = DataHandler()

# セキュリティBlueprint登録
app.register_blueprint(security_bp)

# ロガーをセットアップ
logger = setup_logger('views', log_level=LOG_LEVEL, log_dir=LOG_DIR)

# アプリケーション起動時にデータベースを初期化
try:
    db.init_db()
    logger.info("データベースが初期化されました")
except Exception as e:
    error_logger.log_exception(e, level='CRITICAL', context={'module': 'views', 'action': 'init_db'})
    logger.critical("データベースの初期化に失敗しました：%s", str(e))

# --- 重複参加防止機構 ---
# CookieとIP+UserAgentハッシュで同一人物の再参加をブロック
BLOCK_DUPLICATE_PARTICIPATION = True  # Falseにすると無効化
_ip_hash_set = set()  # ブロック対象のIP+UAハッシュを保持
_ip_hash_expiry = dict()  # {hash: [timestamp1, timestamp2, ...]} アクセス履歴を記録
_ip_hash_lock = Lock()
_IP_HASH_TTL = 3600  # 1時間（秒）- アクセス履歴の有効期限
_IP_HASH_THRESHOLD = 3  # 1時間内に3回以上同一IPからアクセスでブロック（複数デバイスでの再参加防止）


def is_duplicate_participant():
    # 管理者解除用パラメータ
    if request.args.get('force_participate') == '1':
        return False
    if not BLOCK_DUPLICATE_PARTICIPATION:
        return False
    # 1. Cookie判定
    if request.cookies.get('simple_flag') != 'true':
        # Cookieがなければ未参加扱い
        return False
    # 2. LocalStorage判定（クライアント側でJSがalready_participatedを持っていなければ未参加扱い）
    # サーバー側では判定できないため、クライアント側で必ず参加ボタンを表示すること
    # 3. IP+UserAgentハッシュ判定
    ip = request.remote_addr or ''
    user_agent = request.headers.get('User-Agent', '')
    hash_input = ip + '|' + user_agent
    ip_ua_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    now = time.time()
    with _ip_hash_lock:
        # 期限切れハッシュを削除
        expired = [h for h, ts_list in _ip_hash_expiry.items() if all(t < now for t in ts_list)]
        for h in expired:
            _ip_hash_set.discard(h)
            _ip_hash_expiry.pop(h, None)
        # アクセス履歴を記録
        ts_list = _ip_hash_expiry.get(ip_ua_hash, [])
        # 有効なタイムスタンプのみ残す
        ts_list = [t for t in ts_list if t >= now - _IP_HASH_TTL]
        ts_list.append(now)
        _ip_hash_expiry[ip_ua_hash] = ts_list
        # 1時間以内に3回以上同一IP+UAからアクセスがあればブロック
        if len(ts_list) >= _IP_HASH_THRESHOLD:
            _ip_hash_set.add(ip_ua_hash)
            return True
    return False


@app.route('/')
def index():
    """ルート: トップページへリダイレクト"""
    logger.debug("トップページにリダイレクトします")
    return redirect('/t0P1')


@app.route('/t0P1')
def top1():
    """ルート: 実験説明ページ（初回訪問者用）"""
    logger.debug("top1ページが表示されました")
    return render_template('exp/top1.html')


@app.route('/t0P12', methods=['GET'])
def top1_2():
    """ルート: 実験説明ページ（条件割り当て後）"""
    return render_template('exp/top1_2.html')


@app.route('/eXaMinE1')
def examine1():
    """ルート: 実験1（因果判断課題）"""
    user_id = request.args.get("id")
    if not user_id:
        return redirect('/')
    logger.debug("examine1ページが表示されました")
    return render_template('exp/examine1.html', user_id=user_id)


@app.route('/eXaM1nE_2')
def examine1_2():
    """ルート: 実験1_2（因果判断課題・別バージョン）"""
    user_id = request.args.get("id")
    if not user_id:
        return redirect('/t0P12')
    logger.debug("examine1_2ページが表示されました")
    return render_template('exp/examine1_2.html', user_id=user_id)


@app.route('/Ex2')
def examine2():
    """ルート: 実験2（IMC課題）"""
    user_id = request.args.get("id")
    if not user_id:
        return redirect('/')
    logger.debug("examine2ページが表示されました")
    return render_template('exp/examine2.html', user_id=user_id)


@app.route('/CRT3')
def examine3():
    """ルート: 実験3（CRT課題）"""
    user_id = request.args.get("id")
    if not user_id:
        return redirect('/')
    logger.debug("examine3ページが表示されました")
    return render_template('exp/examine3.html', user_id=user_id)


@app.route('/end')
def end():
    """ルート: 実験終了ページ（重複参加チェック有り）"""
    # 重複参加をチェックし、ブロック
    if is_duplicate_participant():
        return render_template('exp/already_participated.html'), 403
    
    logger.debug("endページが表示されました")
    resp = make_response(render_template('exp/end.html'))
    # 参加済みフラグをCookieにセット（30日間有効）
    resp.set_cookie('simple_flag', 'true', max_age=60*60*24*30, httponly=True, samesite='Lax')
    return resp


@app.route('/getSampleType', methods=['GET'])
def get_sample_type():
    try:
        user_id = request.args.get('user_id', str(datetime.datetime.now().timestamp()))
        app_logger.info(f"/getSampleType APIリクエスト受信: user_id={user_id}")  # ログ追加
        logger.info(f"条件割り当てリクエスト: user_id={user_id}")
        
        if not user_id:
            raise UserFriendlyError(
                message="ユーザーIDが指定されていません",
                user_message="ユーザー識別情報が不足しています。もう一度最初からお試しください。",
                status_code=400,
                error_code="MISSING_USER_ID",
                recovery_path="/"
            )
        
        result = db.get_condition_assignment(user_id)
        app_logger.info(f"/getSampleType 割り当て結果: {result}")  # ログ追加
        logger.info(f"条件割り当て結果: {result}")
        
        if not result:
            raise UserFriendlyError(
                message=f"条件割り当てに失敗しました: user_id={user_id}",
                user_message="条件の割り当てに失敗しました。もう一度お試しください。",
                status_code=500,
                error_code="CONDITION_ASSIGNMENT_FAILED",
                recovery_path="/"
            )
        
        return jsonify(result)
    
    except UserFriendlyError as e:
        app_logger.error(f"/getSampleType UserFriendlyError: {e}")  # ログ追加
        error_logger.log_api_error(request, e, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        app_logger.error(f"/getSampleType 例外発生: {e}", exc_info=True)  # ログ追加
        error_info = error_logger.log_api_error(request, e)
        return jsonify({
            "error": True,
            "message": current_app.config.get('DEFAULT_ERROR_MESSAGE', "エラーが発生しました。もう一度お試しください。"),
            "error_code": "SYSTEM_ERROR",
            "status_code": 500,
            "recovery_path": "/"
        }), 500

@app.route('/send', methods=['POST'])
def send():
    try:
        app_logger.info("/send APIリクエスト受信")  # ログ追加
        raw_data = request.form.to_dict()
        suffix = raw_data.get("file_name_suffix", "exp")
        user_id = raw_data.get("user_id")
        page = None
        if suffix == "exp1":
            page = "examine1"
        elif suffix == "exp1_2":
            page = "examine1_2"
        
        logger.info(f"実験データの保存リクエスト: suffix={suffix}")
        
        if not raw_data:
            raise UserFriendlyError(
                message="データが空です",
                user_message="送信データが空です。必要な情報を入力してください。",
                status_code=400,
                error_code="EMPTY_DATA",
                recovery_path="/examine1"
            )
        
        # DataHandlerクラスを使用してデータを保存
        results = data_handler.save_experiment_data(raw_data, suffix)
        app_logger.info(f"/send データ保存結果: {results}")  # ログ追加
        logger.info(f"データ保存結果: {results}")
        
        return Response(status=200)
    
    except UserFriendlyError as e:
        app_logger.error(f"/send UserFriendlyError: {e}")  # ログ追加
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        app_logger.error(f"/send 例外発生: {e}", exc_info=True)  # ログ追加
        error_info = error_logger.log_api_error(request, e)
        logger.error(f"/send エンドポイントでのエラー: {e}", exc_info=True)
        return jsonify({
            "error": True,
            "message": "データの保存中にエラーが発生しました。もう一度お試しください。",
            "error_code": "DATA_SAVE_ERROR",
            "status_code": 500
        }), 500

@app.route('/send_imc', methods=['POST'])
def send_imc():
    try:
        app_logger.info("/send_imc APIリクエスト受信")  # ログ追加
        raw_data = request.form.to_dict()
        suffix = raw_data.get("file_name_suffix", "default")
        
        logger.info(f"IMC/CRTデータの保存リクエスト: suffix={suffix}")
        
        if not raw_data:
            raise UserFriendlyError(
                message="IMC/CRTデータが空です",
                user_message="送信データが空です。必要な情報を入力してください。",
                status_code=400,
                error_code="EMPTY_IMC_DATA",
                recovery_path="/examine2"
            )
        
        # examine2, examine3で送信済みか判定
        if suffix in ["exp2", "exp3"]:
            # 必須データが1件以上あるか
            key = "user_data" if suffix == "exp2" else "crt_data"
            import json
            try:
                datalist = json.loads(raw_data.get(key, "[]"))
            except Exception:
                datalist = []
            if not isinstance(datalist, list) or len(datalist) == 0:
                logger.warning(f"進捗違反: {suffix} でデータ未送信")
                return jsonify({
                    "error": True,
                    "message": "進捗条件を満たしていません（データが必要です）。",
                    "error_code": "PROGRESS_VIOLATION",
                    "status_code": 400
                }), 400

        # DataHandlerクラスを使用してデータを保存
        results = data_handler.save_imc_data(raw_data, suffix)
        app_logger.info(f"/send_imc データ保存結果: {results}")  # ログ追加
        logger.info(f"データ保存結果: {results}")
        
        return jsonify({"status": "success"})
    
    except UserFriendlyError as e:
        app_logger.error(f"/send_imc UserFriendlyError: {e}")  # ログ追加
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        app_logger.error(f"/send_imc 例外発生: {e}", exc_info=True)  # ログ追加
        error_info = error_logger.log_api_error(request, e)
        logger.error(f"/send_imc エンドポイントでのエラー: {e}", exc_info=True)
        return jsonify({
            "error": True,
            "message": "IMC/CRTデータの保存中にエラーが発生しました。もう一度お試しください。",
            "error_code": "IMC_DATA_SAVE_ERROR",
            "status_code": 500
        }), 500

@app.route('/setSampleType', methods=['GET'])
def set_sample_type():
    try:
        app_logger.info("/setSampleType APIリクエスト受信")  # ログ追加
        user_id = request.args.get('user_id')
        sample_type = request.args.get('sampleType')
        
        if not user_id or not sample_type:
            raise UserFriendlyError(
                message="ユーザーIDまたはサンプルタイプが指定されていません",
                user_message="必要な情報が不足しています。もう一度お試しください。",
                status_code=400,
                error_code="MISSING_PARAMETERS",
                recovery_path="/"
            )
        
        logger.info(f"サンプルタイプを設定: user_id={user_id}, sampleType={sample_type}")
        app_logger.info(f"/setSampleType 設定: user_id={user_id}, sampleType={sample_type}")  # ログ追加
        return jsonify({"status": "success", "sample_type": sample_type})
    
    except UserFriendlyError as e:
        app_logger.error(f"/setSampleType UserFriendlyError: {e}")  # ログ追加
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        app_logger.error(f"/setSampleType 例外発生: {e}", exc_info=True)  # ログ追加
        error_info = error_logger.log_api_error(request, e)
        return jsonify({
            "error": True,
            "message": "サンプルタイプの設定中にエラーが発生しました。",
            "error_code": "SAMPLE_TYPE_ERROR",
            "status_code": 500
        }), 500

@app.route('/getExperimentPath', methods=['GET'])
def get_experiment_path():
    try:
        user_id = request.args.get('user_id', str(datetime.datetime.now().timestamp()))
        reallocate = request.args.get('reallocate', 'false').lower() == 'true'
        # 運用監視用: 重要なAPIリクエストのみapp_logger
        app_logger.info(f"/getExperimentPath APIリクエスト受信: user_id={user_id}, reallocate={reallocate}")

        if not user_id:
            raise UserFriendlyError(
                message="ユーザーIDが指定されていません",
                user_message="ユーザー識別情報が不足しています。もう一度最初からお試しください。",
                status_code=400,
                error_code="MISSING_USER_ID",
                recovery_path="/"
            )

        # クライアントからのreallocateパラメータを使用
        result = db.get_experiment_path_assignment(user_id, reallocate)
        # 割り当て結果はlogger(INFO)のみ
        logger.info(f"実験経路割り当て結果: {result}")

        if not result:
            raise UserFriendlyError(
                message=f"実験経路割り当てに失敗しました: user_id={user_id}",
                user_message="実験経路の割り当てに失敗しました。もう一度お試しください。",
                status_code=500,
                error_code="PATH_ASSIGNMENT_FAILED",
                recovery_path="/"
            )

        return jsonify(result)

    except UserFriendlyError as e:
        app_logger.error(f"/getExperimentPath UserFriendlyError: {e}")  # ログ追加
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code

    except Exception as e:
        app_logger.error(f"/getExperimentPath 例外発生: {e}", exc_info=True)  # ログ追加
        error_info = error_logger.log_api_error(request, e)
        return jsonify({
            "error": True,
            "message": current_app.config.get('DEFAULT_ERROR_MESSAGE', "エラーが発生しました。もう一度お試しください。"),
            "error_code": "SYSTEM_ERROR",
            "status_code": 500,
            "recovery_path": "/"
        }), 500

@app.route('/health')
def health_check():
    """
    ヘルスチェックエンドポイント - systemdの起動確認用
    """
    try:
        app_logger.info("/health APIリクエスト受信")  # ログ追加
        # 基本的なシステム状態をチェック
        status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'UCS vs CS Experiment',
            'version': '1.0.0'
        }
        
        # データベース接続の確認
        try:
            db.get_connection()
            status['database'] = 'connected'
        except Exception as db_error:
            status['database'] = 'error'
            status['status'] = 'degraded'
            logger.warning(f"ヘルスチェック - データベース接続エラー: {db_error}")
        
        # ログディレクトリの書き込み権限確認
        try:
            test_log_path = os.path.join(LOG_DIR, 'health_check_test.tmp')
            with open(test_log_path, 'w') as f:
                f.write('test')
            os.remove(test_log_path)
            status['log_directory'] = 'writable'
        except Exception as log_error:
            status['log_directory'] = 'error'
            status['status'] = 'degraded'
            logger.warning(f"ヘルスチェック - ログディレクトリエラー: {log_error}")
        
        http_status = 200 if status['status'] == 'healthy' else 503
        return jsonify(status), http_status
        
    except Exception as e:
        app_logger.error(f"/health 例外発生: {e}", exc_info=True)  # ログ追加
        error_logger.log_exception(e, level='ERROR', context={'endpoint': 'health_check'})
        return jsonify({
            'status': 'error',
            'message': 'ヘルスチェックでエラーが発生しました',
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# /api/validate-progressは不要なため削除

# --- ステップ順序制御付きルーティング ---
@app.route('/step/<int:n>', methods=['POST'])
@require_exact_step  # デコレータは引数付きで使うため、下で明示的に呼ぶ

def step_page(n):
    # --- ステップ順序チェック ---
    check = require_exact_step(n)
    resp = check(lambda: None)()
    if resp is not None:
        return resp
    # --- ページ表示・データ保存処理 ---
    raw_data = request.form.to_dict()
    suffix = raw_data.get("file_name_suffix", "exp")
    user_id = raw_data.get("user_id")
    page = None
    if suffix == "exp1":
        page = "examine1"
    elif suffix == "exp1_2":
        page = "examine1_2"
    logger.info(f"実験データの保存リクエスト: suffix={suffix}")
    if not raw_data:
        raise UserFriendlyError(
            message="データが空です",
            user_message="送信データが空です。必要な情報を入力してください。",
            status_code=400,
            error_code="EMPTY_DATA",
            recovery_path="/examine1"
        )
    # DataHandlerクラスを使用してデータを保存
    results = data_handler.save_experiment_data(raw_data, suffix)
    logger.info(f"データ保存結果: {results}")
    # ステップ進行
    exp_id = session.get('exp_id')
    if exp_id:
        # 単調増加でcurrent_stepを更新
        rows = db.update_experiment_session(exp_id, current_step=n+1, expected=n)
        if rows == 0:
            raise RuntimeError("step desync")
    # 次のステップ番号を hidden で受け取る
    next_step = raw_data.get('next_step')
    if next_step is not None:
        try:
            next_step = int(next_step)
            return redirect(f'/step/{next_step}')
        except Exception:
            pass
    # デフォルトはendへ
    return redirect('/end')

@app.route('/step/<int:n>', methods=['GET'])
def step_page_get(n):
    abort(405)

@app.route('/reset_participation')
def reset_participation():
    """
    管理者・開発用: 参加済みフラグのリセットページ
    """
    return render_template('exp/reset_participation.html')

@app.route('/reset_participation/exec')
def reset_participation_exec():
    """
    管理者・開発用: 参加済みフラグのリセット実行
    CookieとIPハッシュをリセット
    """
    # Cookie削除
    resp = make_response(render_template('exp/reset_participation.html', reset_done=True))
    resp.set_cookie('simple_flag', '', expires=0)
    # IP+UAハッシュもリセット
    global _ip_hash_set, _ip_hash_expiry
    with _ip_hash_lock:
        _ip_hash_set.clear()
        _ip_hash_expiry.clear()
    return resp

@app.route('/api/save_crt_experience', methods=['POST'])
def save_crt_experience():
    """
    CRT受験歴アンケートの回答を保存するエンドポイント
    """
    try:
        app_logger.info("/api/save_crt_experience APIリクエスト受信")
        
        # JSON形式でリクエストを受け取る
        request_data = request.get_json()
        
        if not request_data:
            raise UserFriendlyError(
                message="CRT受験歴データが空です",
                user_message="送信データが空です。もう一度お試しください。",
                status_code=400,
                error_code="EMPTY_CRT_EXPERIENCE_DATA",
                recovery_path="/end"
            )
        
        user_id = request_data.get('user_id')
        experience = request_data.get('experience')
        timestamp = request_data.get('timestamp')
        
        if not user_id or not experience:
            raise UserFriendlyError(
                message="必要なデータが不足しています",
                user_message="必要な情報が不足しています。もう一度お試しください。",
                status_code=400,
                error_code="MISSING_CRT_EXPERIENCE_DATA",
                recovery_path="/end"
            )
        
        # experienceの値が有効かチェック
        valid_experiences = ['yes', 'no', 'unknown']
        if experience not in valid_experiences:
            raise UserFriendlyError(
                message=f"無効な回答値: {experience}",
                user_message="無効な回答です。もう一度お試しください。",
                status_code=400,
                error_code="INVALID_CRT_EXPERIENCE_VALUE",
                recovery_path="/end"
            )
        
        logger.info(f"CRT受験歴データの保存リクエスト: user_id={user_id}, experience={experience}")
        
        # データベースに保存
        result = db.save_crt_experience(user_id, experience, timestamp)
        
        app_logger.info(f"/api/save_crt_experience データ保存結果: {result}")
        logger.info(f"CRT受験歴データ保存結果: {result}")
        
        return jsonify({
            "status": "success",
            "message": "CRT受験歴データが正常に保存されました"
        })
    
    except UserFriendlyError as e:
        app_logger.error(f"/api/save_crt_experience UserFriendlyError: {e}")
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        app_logger.error(f"/api/save_crt_experience 例外発生: {e}", exc_info=True)
        error_info = error_logger.log_api_error(request, e)
        logger.error(f"/api/save_crt_experience エンドポイントでのエラー: {e}", exc_info=True)
        return jsonify({
            "error": True,
            "message": "CRT受験歴データの保存中にエラーが発生しました。もう一度お試しください。",
            "error_code": "CRT_EXPERIENCE_SAVE_ERROR",
            "status_code": 500
        }), 500