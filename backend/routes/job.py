"""
就活アシスタント機能のBlueprint実装。
Blueprint for the job-hunting assistant feature.
"""

from flask import Blueprint, Response
import logging
from typing import Tuple, Union

from backend import llama_core
from backend import limit_manager
from backend import redis_client
from backend.routes.common import (
    make_chat_send_message_route,
    make_session_init_route,
    rich_chat_error_response,
)

logger = logging.getLogger(__name__)

# Blueprintの定義：就活アシスタント機能に関連するルートをまとめる
# Blueprint definition for job assistant routes
job_bp = Blueprint("job", __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]

job_home = make_session_init_route(
    blueprint=job_bp,
    route_path="/job",
    frontend_path="/job",
    endpoint_name="job_home",
    reset_session=lambda session_id: redis_client.reset_session(session_id),
)

job_send_message = make_chat_send_message_route(
    blueprint=job_bp,
    route_path="/job_send_message",
    mode="job",
    error_responder=rich_chat_error_response,
    endpoint_name="job_send_message",
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
