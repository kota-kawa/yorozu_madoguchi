"""
旅行計画機能のBlueprint実装。
Blueprint for the travel planning feature.
"""

from flask import Blueprint, request, jsonify, redirect, Response
import logging
from typing import List, TYPE_CHECKING, Tuple, Union

from backend import llama_core
from backend import reservation
from backend.database import SessionLocal
from backend.models import ReservationPlan
from backend import limit_manager
from backend import redis_client
from backend.errors import SessionError, classify_backend_exception
from backend.routes.common import (
    error_response,
    make_chat_send_message_route,
    make_session_init_route,
    make_submit_plan_route,
    resolve_frontend_url,
    submit_plan_error_response,
)

if TYPE_CHECKING:
    from backend.reservation import ReservationRecord

logger = logging.getLogger(__name__)

# Blueprintの定義: 旅行計画機能（travel）のルートを管理
# Blueprint definition for travel routes
travel_bp = Blueprint("travel", __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def load_reservation_data(session_id: str) -> List["ReservationRecord"]:
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
            return [reservation.serialize_reservation_plan(plan)]
        return []
    finally:
        db.close()


home = make_session_init_route(
    blueprint=travel_bp,
    route_path="/",
    frontend_path="",
    endpoint_name="home",
)


@travel_bp.route("/complete")
def complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    Completion screen endpoint.

    予約プランデータを取得して返します。
    Returns reservation plan data.
    """
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise SessionError("セッションが無効です。ページをリロードしてください。")

        reservation_data = load_reservation_data(session_id)
        accepts_json = request.accept_mimetypes.get("application/json", 0)
        accepts_html = request.accept_mimetypes.get("text/html", 0)
        # JSON要求の場合はデータを返す
        # Return JSON when requested
        if accepts_json >= accepts_html:
            return jsonify({"reservation_data": reservation_data})

        for item in reservation_data:
            logger.info(f"Reservation Data: {item}")
        return redirect(resolve_frontend_url("/complete"))
    except Exception as error:
        backend_error = classify_backend_exception(
            error,
            default_message="完了画面データの取得に失敗しました。",
        )
        logger.error(
            "Complete endpoint failed (%s): %s",
            backend_error.error_type,
            backend_error,
            exc_info=True,
        )
        return error_response(
            backend_error.message,
            status=backend_error.status_code,
            error_type=backend_error.error_type,
        )


send_message = make_chat_send_message_route(
    blueprint=travel_bp,
    route_path="/travel_send_message",
    mode="travel",
    error_responder=error_response,
    endpoint_name="send_message",
    check_and_increment_limit=lambda *args, **kwargs: limit_manager.check_and_increment_limit(
        *args, **kwargs
    ),
    resolve_user_language=lambda *args, **kwargs: llama_core.resolve_user_language(*args, **kwargs),
    get_user_language=lambda *args, **kwargs: redis_client.get_user_language(*args, **kwargs),
    save_user_language=lambda *args, **kwargs: redis_client.save_user_language(*args, **kwargs),
    chat_with_llama=lambda *args, **kwargs: llama_core.chat_with_llama(*args, **kwargs),
    stream_chat_with_llama=lambda *args, **kwargs: llama_core.stream_chat_with_llama(*args, **kwargs),
    logger=logger,
)

submit_plan = make_submit_plan_route(
    blueprint=travel_bp,
    route_path="/travel_submit_plan",
    complete_plan=lambda session_id: reservation.complete_plan(session_id),
    logger=logger,
    endpoint_name="submit_plan",
    error_responder=lambda message, status, error_type=None: (
        error_response(message, status, error_type=error_type)
        if status == 403
        else submit_plan_error_response(message, status, error_type=error_type)
    ),
    exception_responder=lambda error: submit_plan_error_response(
        error.message,
        status=error.status_code,
        error_type=error.error_type,
    ),
)
