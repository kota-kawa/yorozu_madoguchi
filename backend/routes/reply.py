"""
返信サポート機能のBlueprint実装。
Blueprint for the reply support feature.
"""

from flask import Blueprint, request, jsonify, redirect, make_response, Response
from backend import llama_core
from backend import reservation
from backend.database import SessionLocal
from backend.models import ReservationPlan
import uuid
from backend import redis_client
import logging
from backend import security
from typing import Tuple, Union

from backend import limit_manager
from backend.routes.common import (
    handle_chat_send_message,
    handle_submit_plan,
    resolve_frontend_url,
    rich_chat_error_response,
    submit_plan_error_response,
)

ResponseOrTuple = Union[Response, Tuple[Response, int]]

logger = logging.getLogger(__name__)

# Blueprintの定義: メッセージ返信機能（reply）のルートを管理
# Blueprint definition for reply routes
reply_bp = Blueprint('reply', __name__)

# ホームのチャット画面
# Home chat screen
@reply_bp.route('/reply')
def reply_home() -> Response:
    """
    返信機能の初期化エンドポイント
    Initialize reply feature and start a new session.
    
    新規セッションを作成し、Redis上のデータをクリアしてから
    フロントエンドのチャット画面へリダイレクトします。
    Creates a new session, clears Redis data, and redirects to the chat UI.
    """
    session_id = str(uuid.uuid4())
    try:
        redis_client.reset_session(session_id)
    except Exception as e:
        logger.error(f"Failed to reset session for {session_id}: {e}")
        
    response = make_response(
        redirect(resolve_frontend_url('/reply', default_origin="http://localhost:5173"))
    )
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response

# 予約完了画面
# Reservation completion screen
@reply_bp.route('/reply_complete')
def reply_complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    Completion screen endpoint.
    
    データベースから最新の予約プラン情報を取得し、
    JSONデータとして返すか、フロントエンドの完了画面へリダイレクトします。
    Loads the latest plan and returns JSON or redirects to the completion UI.
    """
    reservation_data = []
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。ページをリロードしてください。'}), 400

    db = SessionLocal()
    try:
        # DBから最新の計画を取得
        # Fetch the latest plan from DB
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
    # Return JSON when requested
    if accepts_json >= accepts_html:
        return jsonify({"reservation_data": reservation_data})

    # 結果をログ出力
    # Log results for diagnostics
    for item in reservation_data:
        logger.info(f"Reservation Data: {item}")
    return redirect(resolve_frontend_url('/complete', default_origin="http://localhost:5173"))


# メッセージを受け取り、レスポンスを返すエンドポイント
# Receive a message and return an LLM response
@reply_bp.route('/reply_send_message', methods=['POST'])
def reply_send_message() -> ResponseOrTuple:
    """
    メッセージ送信処理エンドポイント
    Message handling endpoint for reply feature.
    
    ユーザーからのメッセージを受け取り、LLMを使用して応答を生成します。
    CSRFチェック、セッション検証、利用制限チェックを含みます。
    Includes CSRF, session, and rate-limit checks.
    """
    return handle_chat_send_message(
        request,
        mode="reply",
        error_responder=rich_chat_error_response,
        check_and_increment_limit=limit_manager.check_and_increment_limit,
        resolve_user_language=llama_core.resolve_user_language,
        get_user_language=redis_client.get_user_language,
        save_user_language=redis_client.save_user_language,
        chat_with_llama=llama_core.chat_with_llama,
        stream_chat_with_llama=lambda *args, **kwargs: llama_core.stream_chat_with_llama(
            *args, **kwargs
        ),
        limit_exceeded_message_builder=lambda limit: (
            f"申し訳ありませんが、本日の利用制限（{limit}回）に達しました。明日またご利用ください。"
        ),
    )

@reply_bp.route('/reply_submit_plan', methods=['POST'])
def reply_submit_plan() -> ResponseOrTuple:
    """
    プラン確定処理エンドポイント
    Finalize plan endpoint.
    
    現在のセッションでの決定事項を解析し、データベースに保存します。
    Parses decisions for the session and persists to the database.
    """
    return handle_submit_plan(
        request,
        complete_plan=reservation.complete_plan,
        error_responder=submit_plan_error_response,
    )
