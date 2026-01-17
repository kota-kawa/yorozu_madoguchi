from flask import Blueprint, request, jsonify, redirect, make_response, Response
import llama_core
import reservation
from database import SessionLocal
from models import ReservationPlan
import uuid
import redis_client
import logging
import os
import security
from typing import Tuple, Union

ResponseOrTuple = Union[Response, Tuple[Response, int]]
import limit_manager

logger = logging.getLogger(__name__)

# Blueprintの定義: メッセージ返信機能（reply）のルートを管理
reply_bp = Blueprint('reply', __name__)

def resolve_frontend_url(path: str = "") -> str:
    """
    フロントエンドのURLを動的に解決する
    
    環境（本番、ローカル、Dockerなど）に応じて適切なベースURLを決定し、
    リダイレクト先やリンク生成に使用します。
    """
    host = request.headers.get('Host', '')
    if 'chat.project-kk.com' in host:
        base_url = "https://chat.project-kk.com"
    elif 'localhost' in host or '127.0.0.1' in host:
        base_url = "http://localhost:5173"
    else:
        base_url = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    if path and not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"

# ホームのチャット画面
@reply_bp.route('/reply')
def reply_home() -> Response:
    """
    返信機能の初期化エンドポイント
    
    新規セッションを作成し、Redis上のデータをクリアしてから
    フロントエンドのチャット画面へリダイレクトします。
    """
    session_id = str(uuid.uuid4())
    try:
        redis_client.reset_session(session_id)
    except Exception as e:
        logger.error(f"Failed to reset session for {session_id}: {e}")
        
    response = make_response(redirect(resolve_frontend_url('/reply')))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response

# 予約完了画面
@reply_bp.route('/reply_complete')
def reply_complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    
    データベースから最新の予約プラン情報を取得し、
    JSONデータとして返すか、フロントエンドの完了画面へリダイレクトします。
    """
    reservation_data = []
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。ページをリロードしてください。'}), 400

    db = SessionLocal()
    try:
        # DBから最新の計画を取得
        plan = (
            db.query(ReservationPlan)
            .filter(ReservationPlan.session_id == session_id)
            .order_by(ReservationPlan.id.desc())
            .first()
        )
        if plan:
            fields = [
                ('目的地', plan.destinations),
                ('出発地', plan.departure),
                ('ホテル', plan.hotel),
                ('航空会社', plan.airlines),
                ('鉄道会社', plan.railway),
                ('タクシー会社', plan.taxi),
                ('滞在開始日', plan.start_date),
                ('滞在終了日', plan.end_date)
            ]
            for key, value in fields:
                if value:
                    reservation_data.append(f"{key}：{value}")
    except Exception as e:
        logger.error(f"Error loading reservation data: {e}")
    finally:
        db.close()

    accepts_json = request.accept_mimetypes.get('application/json', 0)
    accepts_html = request.accept_mimetypes.get('text/html', 0)
    # JSONを要求されている場合はデータを返す
    if accepts_json >= accepts_html:
        return jsonify({"reservation_data": reservation_data})

    # 結果をログ出力
    for item in reservation_data:
        logger.info(f"Reservation Data: {item}")
    return redirect(resolve_frontend_url('/complete'))


# メッセージを受け取り、レスポンスを返すエンドポイント
@reply_bp.route('/reply_send_message', methods=['POST'])
def reply_send_message() -> ResponseOrTuple:
    """
    メッセージ送信処理エンドポイント
    
    ユーザーからのメッセージを受け取り、LLMを使用して応答を生成します。
    CSRFチェック、セッション検証、利用制限チェックを含みます。
    """
    if not security.is_csrf_valid(request):
        return jsonify({'error': '不正なリクエストです。', 'response': '不正なリクエストです。'}), 403

    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。ページをリロードしてください。'}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            'error': 'リクエストの形式が正しくありません（JSONを送信してください）。',
            'response': 'リクエストの形式が正しくありません（JSONを送信してください）。',
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 400

    # 利用制限のチェック
    is_allowed, count, limit, user_type, total_exceeded, error_code = (
        limit_manager.check_and_increment_limit(session_id, user_type=data.get("user_type"))
    )
    if error_code == "redis_unavailable":
        return jsonify({
            'error': "利用状況を確認できません。しばらく待ってから再試行してください。",
            'response': "利用状況を確認できません。しばらく待ってから再試行してください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 503
    if not user_type:
        return jsonify({
            'error': "ユーザー種別を選択してください。",
            'response': "ユーザー種別を選択してください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 400
    if total_exceeded:
        return jsonify({
            'response': "今日の上限に達しました。明日またご利用ください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 429
    if not is_allowed:
        return jsonify({
            'response': f"申し訳ありませんが、本日の利用制限（{limit}回）に達しました。明日またご利用ください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 429

    prompt = data.get('message')

    # 文字数制限のチェック
    if not prompt:
        return jsonify({
            'response': "メッセージを入力してください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 400
    if len(prompt) > 3000:
        return jsonify({
            'response': "入力された文字数が3000文字を超えています。短くして再度お試しください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 400

    # LLMとの対話実行 (mode="reply")
    response, current_plan, yes_no_phrase, _choices, _is_date_select, remaining_text = (
        llama_core.chat_with_llama(session_id, prompt, mode="reply")
    )
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@reply_bp.route('/reply_submit_plan', methods=['POST'])
def reply_submit_plan() -> ResponseOrTuple:
    """
    プラン確定処理エンドポイント
    
    現在のセッションでの決定事項を解析し、データベースに保存します。
    """
    if not security.is_csrf_valid(request):
        return jsonify({'error': '不正なリクエストです。'}), 403

    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。'}), 400
        
    compile = reservation.complete_plan(session_id)
    return jsonify({'compile': compile})
