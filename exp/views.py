import datetime
import json
import os
from flask import render_template, request, Response, redirect, jsonify, current_app, Blueprint
from exp import app
from exp.config import LOG_LEVEL, LOG_DIR
from utils.logger import setup_logger, error_logger, UserFriendlyError

# データベースとデータ処理用のクラスをインポート
from models.database import Database
from utils.data_handler import DataHandler

# セキュリティ機能のインポート
from exp.security_handlers import security_bp, analyze_security_patterns

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

@app.route('/')
def index():
    logger.debug("トップページにリダイレクトします")
    return redirect('/top1')

@app.route('/top1')
def top1():
    logger.debug("top1ページが表示されました")
    return render_template('exp/top1.html')

@app.route('/top1_2')
def top1_2():
    logger.debug("top1_2ページが表示されました")
    return render_template('exp/top1_2.html')

@app.route('/examine1')
def examine1():
    logger.debug("examine1ページが表示されました")
    return render_template('exp/examine1.html')

@app.route('/examine1_2')
def examine1_2():
    logger.debug("examine1_2ページが表示されました")
    return render_template('exp/examine1_2.html')

@app.route('/examine2')
def examine2():
    logger.debug("examine2ページが表示されました")
    return render_template('exp/examine2.html')

@app.route('/examine3')
def examine3():
    logger.debug("examine3ページが表示されました")
    return render_template('exp/examine3.html')

@app.route('/end')
def end():
    logger.debug("endページが表示されました")
    return render_template('exp/end.html')

@app.route('/getSampleType', methods=['GET'])
def get_sample_type():
    try:
        user_id = request.args.get('user_id', str(datetime.datetime.now().timestamp()))
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
        error_logger.log_api_error(request, e, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
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
        raw_data = request.form.to_dict()
        suffix = raw_data.get("file_name_suffix", "exp")
        
        logger.info(f"実験データの保存リクエスト: suffix={suffix}")
        
        if not raw_data:
            raise UserFriendlyError(
                message="データが空です",
                user_message="送信データが空です。必要な情報を入力してください。",
                status_code=400,
                error_code="EMPTY_DATA",
                recovery_path="/examine1"
            )
        
        # examine1, examine1_2で6件送信済みか判定
        if suffix in ["exp1", "exp1_2"]:
            estimations = raw_data.get("estimations")
            import json
            try:
                est_list = json.loads(estimations) if estimations else []
            except Exception:
                est_list = []
            if not isinstance(est_list, list) or len(est_list) != 6:
                logger.warning(f"進捗違反: {suffix} で6件未満のデータ送信: {len(est_list)}件")
                return jsonify({
                    "error": True,
                    "message": "進捗条件を満たしていません（6件のデータが必要です）。",
                    "error_code": "PROGRESS_VIOLATION",
                    "status_code": 400
                }), 400

        # DataHandlerクラスを使用してデータを保存
        results = data_handler.save_experiment_data(raw_data, suffix)
        logger.info(f"データ保存結果: {results}")
        
        return Response(status=200)
    
    except UserFriendlyError as e:
        error_logger.log_api_error(request, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
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
        logger.info(f"データ保存結果: {results}")
        
        return jsonify({"status": "success"})
    
    except UserFriendlyError as e:
        error_logger.log_api_error(request, e, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
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
        return jsonify({"status": "success", "sample_type": sample_type})
    
    except UserFriendlyError as e:
        error_logger.log_api_error(request, e, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
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
        logger.debug(f"パラメータ - user_id={user_id}, reallocate={reallocate}, type={type(reallocate)}")
        logger.info(f"実験経路割り当てリクエスト: user_id={user_id}, reallocate={reallocate}")
        
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
        logger.debug(f"実験経路割り当て結果: {result}")
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
        error_logger.log_api_error(request, e, e.status_code)
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
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
        error_logger.log_exception(e, level='ERROR', context={'endpoint': 'health_check'})
        return jsonify({
            'status': 'error',
            'message': 'ヘルスチェックでエラーが発生しました',
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# 進捗API
@app.route('/api/progress')
def api_progress():
    """
    examine1, examine1_2, examine2, examine3 の進捗/order検証API
    """
    try:
        user_id = request.args.get('user_id')
        page = request.args.get('page')
        progress_token = request.args.get('progress_token')
        if not user_id or not page:
            return jsonify({
                "allowed": False,
                "redirectPage": "/",
                "error": "missing_parameters"
            }), 400

        path_info = db.get_experiment_path_assignment(user_id, reallocate=False)
        path_type = path_info.get('pathType', 'order1')  # 'order1' or 'order2'

        allowed = True
        redirect_page = None

        examine1_count = 0
        examine1_2_count = 0
        try:
            progress_info = data_handler.get_progress_counts(user_id)
            examine1_count = progress_info.get('examine1', 0)
            examine1_2_count = progress_info.get('examine1_2', 0)
        except Exception as e:
            logger.warning(f"進捗情報取得失敗: {e}")

        logger.debug(f"進捗判定: user_id={user_id}, page={page}, path_type={path_type}, examine1_count={examine1_count}, examine1_2_count={examine1_2_count}")

        # --- 進入許可ロジック（order1/order2で統一, 0件時は必ず進入可） ---
        if path_type == 'order1':
            if page == 'examine1':
                if examine1_count == 0:
                    allowed = True
                    redirect_page = None
                elif examine1_count >= 6:
                    allowed = False
                    redirect_page = '/examine1_2'
            elif page == 'examine1_2':
                if examine1_2_count == 0:
                    allowed = True
                    redirect_page = None
                elif examine1_count < 6:
                    allowed = False
                    redirect_page = '/examine1'
                elif examine1_2_count >= 6:
                    allowed = False
                    redirect_page = '/examine2'
        elif path_type == 'order2':
            if page == 'examine1_2':
                if examine1_2_count == 0:
                    allowed = True
                    redirect_page = None
                elif examine1_2_count >= 6:
                    allowed = False
                    redirect_page = '/examine1'
            elif page == 'examine1':
                if examine1_count == 0:
                    allowed = True
                    redirect_page = None
                elif examine1_2_count < 6:
                    allowed = False
                    redirect_page = '/examine1_2'
                elif examine1_count >= 6:
                    allowed = False
                    redirect_page = '/examine2'
        # 他ページは特に制限しない

        return jsonify({
            "allowed": allowed,
            "redirectPage": redirect_page,
            "progressToken": progress_token or "",
            "order": path_type
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "allowed": False,
            "redirectPage": "/",
            "error": str(e)
        }), 500

@app.route('/api/validate-progress', methods=['POST'])
def api_validate_progress():
    """
    データ送信時の進捗/order検証API（ダミー実装: 常にOKを返す）
    """
    data = request.get_json(force=True)
    user_id = data.get('user_id')
    page = data.get('page')
    progress_token = data.get('progress_token')
    # 必要ならここで進捗/orderチェックのロジックを追加
    return jsonify({
        "allowed": True
    })