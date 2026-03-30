"""
フィットネス相談機能のBlueprint実装。
Blueprint for the fitness consultation feature.
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

# Blueprintの定義：フィットネス機能に関連するルートをまとめる
# Blueprint definition for fitness routes
fitness_bp = Blueprint('fitness', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


@fitness_bp.route('/fitness')
def fitness_home() -> Response:
    """
    フィットネス機能の初期化エンドポイント
    Initialize fitness feature and start a new session.
    
    新しいセッションIDを発行し、セッションデータをリセットした後、
    フロントエンドのフィットネス画面へリダイレクトします。
    Issues a new session ID, resets data, and redirects to the UI.
    """
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url('/fitness')
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response


@fitness_bp.route('/fitness_send_message', methods=['POST'])
def fitness_send_message() -> ResponseOrTuple:
    """
    フィットネスチャットのメッセージ処理エンドポイント
    Handle fitness chat messages.
    
    1. CSRFチェックとセッション検証
    2. 利用制限（レートリミット）の確認とカウント更新
    3. 入力メッセージの検証（空文字、文字数制限）
    4. LLM（llama_core）への問い合わせと応答の生成
    1) CSRF and session validation
    2) Rate-limit check and increment
    3) Input validation (empty/length)
    4) LLM call and response generation
    """
    try:
        return handle_chat_send_message(
            request,
            mode="fitness",
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
        logger.error(f"Error in fitness_send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)
