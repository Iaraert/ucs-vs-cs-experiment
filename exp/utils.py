# exp/utils.py
# ページ順序制御とバリデーション用のユーティリティ
from functools import wraps
from flask import session, redirect, abort, make_response
from models.database import Database, ExperimentSession

# 実験ページの順序定義（order1/order2で順序が異なる）
ORDER1 = ['t0P12', 'eXaMinE1', 'eXaM1nE_2', 'Ex2', 'CRT3', 'end']
ORDER2 = ['t0P12', 'eXaM1nE_2', 'eXaMinE1', 'Ex2', 'CRT3', 'end']

# ページ名からステップ番号への変換辞書
ORDER1_STEP = {name: i for i, name in enumerate(ORDER1)}
ORDER2_STEP = {name: i for i, name in enumerate(ORDER2)}

# データベースインスタンス
_db = Database()


def requires_step(expected: int):
    """
    指定されたステップ番号でのみアクセスを許可するデコレータ
    現在のステップと一致しない場合は、正しいページへリダイレクトまたは403エラー
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exp_id = session.get('exp_id')
            if not exp_id:
                return abort(403)
            
            # セッション情報を取得
            sess = _db.get_experiment_session(exp_id)
            if not sess:
                return abort(403)
            
            # ステップが一致しない場合、正しいページにリダイレクト
            if sess.current_step != expected:
                order = sess.order
                if order == 'order1':
                    page = ORDER1[sess.current_step] if 0 <= sess.current_step < len(ORDER1) else None
                elif order == 'order2':
                    page = ORDER2[sess.current_step] if 0 <= sess.current_step < len(ORDER2) else None
                else:
                    page = None
                
                if page:
                    return redirect(f'/{page}')
                return abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_exact_step(expected: int):
    """
    より厳格なステップ制御デコレータ
    - current_step == expected: 通過
    - current_step < expected: 403（先のページへの飛ばしを防止）
    - current_step > expected: 410（逆走を防止）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exp_id = session.get('exp_id')
            if not exp_id:
                resp = make_response("セッションがありません (403)", 403)
                resp.mimetype = "text/plain"
                return resp
            
            sess = _db.get_experiment_session(exp_id)
            if not sess:
                resp = make_response("セッションが無効です (403)", 403)
                resp.mimetype = "text/plain"
                return resp
            
            # ステップの一致を厳密にチェック
            if sess.current_step == expected:
                return func(*args, **kwargs)
            elif sess.current_step < expected:
                # 先のページへの不正アクセスを防止
                resp = make_response("順序違反: 先のページへは進めません (403)", 403)
                resp.mimetype = "text/plain"
                return resp
            else:
                # 戻り操作を防止
                resp = make_response("逆走禁止: 古いページには戻れません (410)", 410)
                resp.mimetype = "text/plain"
                return resp
        return wrapper
    return decorator
