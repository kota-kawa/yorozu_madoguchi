"""
就活アシスタント機能のBlueprint実装。
Blueprint for the job-hunting assistant feature.
"""

from flask import Blueprint, request, redirect, make_response, Response
import logging
import uuid
from typing import Tuple, Union

from backend import llama_core
from backend import limit_manager
from backend import redis_client
from backend import security
from backend.routes.common import (
    error_response,
    handle_chat_send_message,
    reset_session_data,
    resolve_frontend_url,
)

logger = logging.getLogger(__name__)

# Blueprintの定義：就活アシスタント機能に関連するルートをまとめる
# Blueprint definition for job assistant routes
job_bp = Blueprint('job', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


@job_bp.route('/job')
def job_home() -> Response:
    """
    就活アシスタントの初期化エンドポイント
    Initialize job assistant feature and start a new session.

    新規セッションを作成し、フロントエンドの就活画面へリダイレクトします。
    Creates a new session and redirects to the UI.
    """
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url('/job')
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response


@job_bp.route('/job_send_message', methods=['POST'])
def job_send_message() -> ResponseOrTuple:
    """
    就活チャットのメッセージ処理エンドポイント
    Handle job assistant chat messages.
    """
    try:
        return handle_chat_send_message(
            request,
            mode="job",
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
        logger.error(f"Error in job_send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)
