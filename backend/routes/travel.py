"""
旅行計画機能のBlueprint実装。
Blueprint for the travel planning feature.
"""

from flask import Blueprint, request, jsonify, redirect, make_response, Response
import logging
import uuid
from typing import List, Tuple, Union

from backend import llama_core
from backend import reservation
from backend.database import SessionLocal
from backend.models import ReservationPlan
from backend import limit_manager
from backend import redis_client
from backend import security
from backend.routes.common import (
    error_response,
    handle_chat_send_message,
    handle_submit_plan,
    reset_session_data,
    resolve_frontend_url,
    submit_plan_error_response,
)

logger = logging.getLogger(__name__)

# Blueprintの定義: 旅行計画機能（travel）のルートを管理
# Blueprint definition for travel routes
travel_bp = Blueprint('travel', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def load_reservation_data(session_id: str) -> List[dict]:
    """
    セッション単位で最新の予約プランを読み込む
    Load the latest reservation plan for a session.
    
    データベースから該当セッションの最新の旅行計画を取得し、辞書のリストとして返します。
    Fetches the most recent plan and returns a list of dicts.
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
    Initialize travel feature and start a new session.
    
    （ルートパス '/' に割り当てられているため、デフォルトのエントリーポイントとなります）
    新規セッション発行後、フロントエンドへリダイレクトします。
    Issues a new session ID and redirects to the frontend.
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
    Completion screen endpoint.
    
    予約プランデータを取得して返します。
    Returns reservation plan data.
    """
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        reservation_data = load_reservation_data(session_id)
        accepts_json = request.accept_mimetypes.get('application/json', 0)
        accepts_html = request.accept_mimetypes.get('text/html', 0)
        # JSON要求の場合はデータを返す
        # Return JSON when requested
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
    Message handling endpoint for travel feature.
    
    ユーザーからのメッセージを受け取り、旅行コンシェルジュとしての応答を生成します。
    Receives user input and generates concierge responses.
    """
    try:
        return handle_chat_send_message(
            request,
            mode="travel",
            error_responder=error_response,
            check_and_increment_limit=limit_manager.check_and_increment_limit,
            resolve_user_language=llama_core.resolve_user_language,
            get_user_language=redis_client.get_user_language,
            save_user_language=redis_client.save_user_language,
            chat_with_llama=llama_core.chat_with_llama,
            stream_chat_with_llama=lambda *args, **kwargs: llama_core.stream_chat_with_llama(
                *args, **kwargs
            ),
        )
    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)


@travel_bp.route('/travel_submit_plan', methods=['POST'])
def submit_plan() -> ResponseOrTuple:
    """
    プラン確定処理エンドポイント
    Finalize plan endpoint.
    
    現在のセッションでの旅行計画を解析し、データベースに保存します。
    Parses session decisions and stores the plan in DB.
    """
    try:
        return handle_submit_plan(
            request,
            complete_plan=reservation.complete_plan,
            error_responder=lambda message, status: (
                error_response(message, status)
                if status == 403
                else submit_plan_error_response(message, status)
            ),
        )
    except Exception as e:
        logger.error(f"Error in submit_plan: {e}", exc_info=True)
        return jsonify({'error': 'プランの保存に失敗しました。'}), 500
