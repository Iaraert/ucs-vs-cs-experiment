# exp/utils.py
# 共通ユーティリティ・デコレータ置き場
from functools import wraps
from flask import session, redirect, abort, make_response
from models.database import Database, ExperimentSession

# ページ名リスト（order1/order2で順序が異なる）
ORDER1 = ['top1_2', 'examine1', 'examine1_2', 'examine2', 'examine3', 'end']
ORDER2 = ['top1_2', 'examine1_2', 'examine1', 'examine2', 'examine3', 'end']

# ページ名→step番号辞書
ORDER1_STEP = {name: i for i, name in enumerate(ORDER1)}
ORDER2_STEP = {name: i for i, name in enumerate(ORDER2)}

# ExperimentSession取得用
_db = Database()

def requires_step(expected: int):
    """
    Flaskビュー用: セッションのcurrent_stepがexpectedと一致しない場合リダイレクト/403。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exp_id = session.get('exp_id')
            if not exp_id:
                return abort(403)
            sess = _db.get_experiment_session(exp_id)
            if not sess:
                return abort(403)
            if sess.current_step != expected:
                # 正しいページ名を推定
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
    current_stepがexpectedと一致: 通過
    current_step < expected: abort(403)（先のページへ飛ばし防止）
    current_step > expected: abort(410)（逆走禁止）
    abort時はプレーンテキストで理由を返す
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
            if sess.current_step == expected:
                return func(*args, **kwargs)
            elif sess.current_step < expected:
                resp = make_response("順序違反: 先のページへは進めません (403)", 403)
                resp.mimetype = "text/plain"
                return resp
            else:
                resp = make_response("逆走禁止: 古いページには戻れません (410)", 410)
                resp.mimetype = "text/plain"
                return resp
        return wrapper
    return decorator
