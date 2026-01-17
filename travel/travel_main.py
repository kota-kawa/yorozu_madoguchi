from flask import Blueprint, request, jsonify, redirect, make_response, Response
import logging
import os
import uuid
from typing import List, Tuple, Union

import llama_core
import reservation
from database import SessionLocal
from models import ReservationPlan
import limit_manager
import redis_client
import security

logger = logging.getLogger(__name__)

# Blueprintの定義: 旅行計画機能（travel）のルートを管理
travel_bp = Blueprint('travel', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def resolve_frontend_url(path: str = "") -> str:
    """
    フロントエンドのURLを動的に解決する
    
    環境に応じて適切なベースURLを返します。
    """
    host = request.headers.get('Host', '')
    if 'chat.project-kk.com' in host:
        base_url = "https://chat.project-kk.com"
    elif 'localhost' in host or '127.0.0.1' in host:
        base_url = "http://localhost:5173"
    else:
        base_url = os.getenv("FRONTEND_ORIGIN", "https://chat.project-kk.com")

    if path and not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"


def reset_session_data(session_id: str) -> None:
    """Redisのセッションデータをリセットする"""
    redis_client.reset_session(session_id)


def error_response(message: str, status: int = 400) -> ResponseOrTuple:
    """エラーレスポンスを返すヘルパー関数"""
    return jsonify({"error": message, "response": message}), status


def load_reservation_data(session_id: str) -> List[dict]:
    """
    セッション単位で最新の予約プランを読み込む
    
    データベースから該当セッションの最新の旅行計画を取得し、辞書のリストとして返します。
    """
    if not session_id:
        return []

    db = SessionLocal()
    try:
        plan = (
            db.query(ReservationPlan)
            .filter(ReservationPlan.session_id == session_id)
            .order_by(ReservationPlan.id.desc())
            .first()
        )
        if plan:
            return [{
                "id": plan.id,
                "session_id": plan.session_id,
                "destinations": plan.destinations,
                "departure": plan.departure,
                "hotel": plan.hotel,
                "airlines": plan.airlines,
                "railway": plan.railway,
                "taxi": plan.taxi,
                "start_date": plan.start_date,
                "end_date": plan.end_date
            }]
        return []
    finally:
        db.close()


@travel_bp.route('/')
def home() -> Response:
    """
    旅行計画機能の初期化エンドポイント
    
    （ルートパス '/' に割り当てられているため、デフォルトのエントリーポイントとなります）
    新規セッション発行後、フロントエンドへリダイレクトします。
    """
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url()
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response


@travel_bp.route('/complete')
def complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    
    予約プランデータを取得して返します。
    """
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        reservation_data = load_reservation_data(session_id)
        accepts_json = request.accept_mimetypes.get('application/json', 0)
        accepts_html = request.accept_mimetypes.get('text/html', 0)
        # JSON要求の場合はデータを返す
        if accepts_json >= accepts_html:
            return jsonify({"reservation_data": reservation_data})

        for item in reservation_data:
            logger.info(f"Reservation Data: {item}")
        return redirect(resolve_frontend_url('/complete'))
    except Exception as e:
        logger.error(f"Complete endpoint failed: {e}")
        return "サーバー内部エラーが発生しました。", 500


@travel_bp.route('/travel_send_message', methods=['POST'])
def send_message() -> ResponseOrTuple:
    """
    メッセージ送信処理エンドポイント
    
    ユーザーからのメッセージを受け取り、旅行コンシェルジュとしての応答を生成します。
    """
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        data = request.get_json(silent=True)
        if data is None:
            return error_response("リクエストの形式が正しくありません（JSONを送信してください）。", status=400)

        # 利用制限のチェック
        is_allowed, count, limit, user_type, total_exceeded, error_code = (
            limit_manager.check_and_increment_limit(session_id, user_type=data.get("user_type"))
        )
        if error_code == "redis_unavailable":
            return error_response("利用状況を確認できません。しばらく待ってから再試行してください。", status=503)
        if not user_type:
            return error_response("ユーザー種別を選択してください。", status=400)
        if total_exceeded:
            return error_response("今日の上限に達しました。明日またご利用ください。", status=429)
        if not is_allowed:
            return error_response(
                f"本日の利用制限（{limit}回）に達しました。明日またご利用ください。",
                status=429
            )

        prompt = data.get('message', '')

        if not prompt:
            return error_response("メッセージを入力してください。", status=400)

        if len(prompt) > 3000:
            return error_response("入力された文字数が3000文字を超えています。短くして再度お試しください。", status=400)

        # LLMとの対話実行（デフォルトモード=travel）
        response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text = llama_core.chat_with_llama(session_id, prompt)
        return jsonify({
            'response': response,
            'current_plan': current_plan,
            'yes_no_phrase': yes_no_phrase,
            'choices': choices,
            'is_date_select': is_date_select,
            'remaining_text': remaining_text
        })

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)


@travel_bp.route('/travel_submit_plan', methods=['POST'])
def submit_plan() -> ResponseOrTuple:
    """
    プラン確定処理エンドポイント
    
    現在のセッションでの旅行計画を解析し、データベースに保存します。
    """
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'error': 'セッションが無効です。'}), 400

        result = reservation.complete_plan(session_id)
        return jsonify({'compile': result})
    except Exception as e:
        logger.error(f"Error in submit_plan: {e}", exc_info=True)
        return jsonify({'error': 'プランの保存に失敗しました。'}), 500
