"""
返信サポート機能のBlueprint実装。
Blueprint for the reply support feature.
"""

from flask import Blueprint, Response
from backend import llama_core
from backend import reservation
from backend import redis_client
import logging
from typing import Any, Dict, List, Tuple, Union

from backend import limit_manager
from backend.routes.common import (
    make_complete_route,
    make_chat_send_message_route,
    load_latest_reservation_data,
    make_session_init_route,
    make_submit_plan_route,
    rich_chat_error_response,
    submit_plan_error_response,
)

ResponseOrTuple = Union[Response, Tuple[Response, int]]

logger = logging.getLogger(__name__)

# Blueprintの定義: メッセージ返信機能（reply）のルートを管理
# Blueprint definition for reply routes
reply_bp = Blueprint("reply", __name__)

REPLY_COMPLETE_FIELDS = (
    ("目的地", "destinations"),
    ("出発地", "departure"),
    ("ホテル", "hotel"),
    ("航空会社", "airlines"),
    ("鉄道会社", "railway"),
    ("タクシー会社", "taxi"),
    ("滞在開始日", "start_date"),
    ("滞在終了日", "end_date"),
)

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


def _format_reply_complete_data(reservation_data: List[Dict[str, Any]]) -> List[str]:
    if not reservation_data:
        return []

    latest_plan = reservation_data[0]
    formatted: List[str] = []
    for label, key in REPLY_COMPLETE_FIELDS:
        value = latest_plan.get(key)
        if isinstance(value, str) and value.strip():
            formatted.append(f"{label}：{value.strip()}")
    return formatted


reply_complete = make_complete_route(
    blueprint=reply_bp,
    route_path="/reply_complete",
    mode="reply",
    load_reservation_data=load_latest_reservation_data,
    formatter=_format_reply_complete_data,
    logger=logger,
    endpoint_name="reply_complete",
    frontend_path="/complete",
    default_frontend_origin="http://localhost:5173",
)


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
)

reply_submit_plan = make_submit_plan_route(
    blueprint=reply_bp,
    route_path="/reply_submit_plan",
    complete_plan=lambda session_id: reservation.complete_plan(session_id),
    logger=logger,
    endpoint_name="reply_submit_plan",
    error_responder=submit_plan_error_response,
)
