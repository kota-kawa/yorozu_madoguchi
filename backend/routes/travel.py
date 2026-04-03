"""
旅行計画機能のBlueprint実装。
Blueprint for the travel planning feature.
"""

from flask import Blueprint, Response
import logging
from typing import Tuple, Union

from backend import llama_core
from backend import reservation
from backend import limit_manager
from backend import redis_client
from backend.routes.common import (
    error_response,
    make_complete_route,
    make_chat_send_message_route,
    load_latest_reservation_data,
    make_session_init_route,
    make_submit_plan_route,
    rich_chat_error_response,
    submit_plan_error_response,
)

logger = logging.getLogger(__name__)

# Blueprintの定義: 旅行計画機能（travel）のルートを管理
# Blueprint definition for travel routes
travel_bp = Blueprint("travel", __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


home = make_session_init_route(
    blueprint=travel_bp,
    route_path="/",
    frontend_path="",
    endpoint_name="home",
)


complete = make_complete_route(
    blueprint=travel_bp,
    route_path="/complete",
    mode="travel",
    load_reservation_data=load_latest_reservation_data,
    formatter=lambda reservation_data: reservation_data,
    logger=logger,
    endpoint_name="complete",
)


send_message = make_chat_send_message_route(
    blueprint=travel_bp,
    route_path="/travel_send_message",
    mode="travel",
    error_responder=rich_chat_error_response,
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
