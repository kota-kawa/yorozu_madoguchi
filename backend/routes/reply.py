"""
返信サポート機能のBlueprint実装。
Blueprint for the reply support feature.
"""

from flask import Blueprint, request, jsonify, redirect, Response
from backend import llama_core
from backend import reservation
from backend.database import SessionLocal
from backend.models import ReservationPlan
from backend import redis_client
import logging
from typing import Tuple, Union

from backend import limit_manager
from backend.errors import SessionError, classify_backend_exception
from backend.routes.common import (
    error_response,
    make_chat_send_message_route,
    make_session_init_route,
    make_submit_plan_route,
    resolve_frontend_url,
    rich_chat_error_response,
    submit_plan_error_response,
)

ResponseOrTuple = Union[Response, Tuple[Response, int]]

logger = logging.getLogger(__name__)

# Blueprintの定義: メッセージ返信機能（reply）のルートを管理
# Blueprint definition for reply routes
reply_bp = Blueprint("reply", __name__)

reply_home = make_session_init_route(
    blueprint=reply_bp,
    route_path="/reply",
    frontend_path="/reply",
    default_frontend_origin="http://localhost:5173",
    endpoint_name="reply_home",
    reset_session=lambda session_id: redis_client.reset_session(session_id),
    on_reset_error=lambda session_id, error: logger.error(
        f"Failed to reset session for {session_id}: {error}"
    ),
)


# 予約完了画面
# Reservation completion screen
@reply_bp.route("/reply_complete")
def reply_complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    Completion screen endpoint.

    データベースから最新の予約プラン情報を取得し、
    JSONデータとして返すか、フロントエンドの完了画面へリダイレクトします。
    Loads the latest plan and returns JSON or redirects to the completion UI.
    """
    reservation_data = []
    session_id = request.cookies.get("session_id")
    try:
        if not session_id:
            raise SessionError("セッションが無効です。ページをリロードしてください。")

        db = SessionLocal()
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
                ("目的地", plan.destinations),
                ("出発地", plan.departure),
                ("ホテル", plan.hotel),
                ("航空会社", plan.airlines),
                ("鉄道会社", plan.railway),
                ("タクシー会社", plan.taxi),
                ("滞在開始日", plan.start_date),
                ("滞在終了日", plan.end_date),
            ]
            for key, value in fields:
                if value:
                    reservation_data.append(f"{key}：{value}")
    except Exception as error:
        backend_error = classify_backend_exception(
            error,
            default_message="完了画面データの取得に失敗しました。",
        )
        logger.error(
            "Error loading reservation data (%s): %s",
            backend_error.error_type,
            backend_error,
            exc_info=True,
        )
        return error_response(
            backend_error.message,
            status=backend_error.status_code,
            error_type=backend_error.error_type,
        )
    finally:
        if "db" in locals():
            db.close()

    accepts_json = request.accept_mimetypes.get("application/json", 0)
    accepts_html = request.accept_mimetypes.get("text/html", 0)
    # JSONを要求されている場合はデータを返す
    # Return JSON when requested
    if accepts_json >= accepts_html:
        return jsonify({"reservation_data": reservation_data})

    # 結果をログ出力
    # Log results for diagnostics
    for item in reservation_data:
        logger.info(f"Reservation Data: {item}")
    return redirect(resolve_frontend_url("/complete", default_origin="http://localhost:5173"))


reply_send_message = make_chat_send_message_route(
    blueprint=reply_bp,
    route_path="/reply_send_message",
    mode="reply",
    error_responder=rich_chat_error_response,
    endpoint_name="reply_send_message",
    check_and_increment_limit=lambda *args, **kwargs: limit_manager.check_and_increment_limit(
        *args, **kwargs
    ),
    resolve_user_language=lambda *args, **kwargs: llama_core.resolve_user_language(*args, **kwargs),
    get_user_language=lambda *args, **kwargs: redis_client.get_user_language(*args, **kwargs),
    save_user_language=lambda *args, **kwargs: redis_client.save_user_language(*args, **kwargs),
    chat_with_llama=lambda *args, **kwargs: llama_core.chat_with_llama(*args, **kwargs),
    stream_chat_with_llama=lambda *args, **kwargs: llama_core.stream_chat_with_llama(*args, **kwargs),
    logger=logger,
    limit_exceeded_message_builder=lambda limit: (
        f"申し訳ありませんが、本日の利用制限（{limit}回）に達しました。明日またご利用ください。"
    ),
)

reply_submit_plan = make_submit_plan_route(
    blueprint=reply_bp,
    route_path="/reply_submit_plan",
    complete_plan=lambda session_id: reservation.complete_plan(session_id),
    logger=logger,
    endpoint_name="reply_submit_plan",
    error_responder=submit_plan_error_response,
)
