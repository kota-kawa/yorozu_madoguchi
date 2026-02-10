"""
学習アシスタント機能のBlueprint実装。
Blueprint for the study assistant feature.
"""

from flask import Blueprint, request, jsonify, redirect, make_response, Response
import logging
import os
import uuid
from typing import Tuple, Union

import llama_core
import limit_manager
import redis_client
import security

logger = logging.getLogger(__name__)

# Blueprintの定義：学習アシスタント機能に関連するルートをまとめる
# Blueprint definition for study assistant routes
study_bp = Blueprint('study', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def resolve_frontend_url(path: str = "") -> str:
    """
    フロントエンドのURLを動的に解決する
    Resolve the frontend base URL dynamically.

    環境に応じて適切なベースURLを返します。
    Returns the appropriate base URL depending on the environment.
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
    """Redisのセッションデータをリセットする / Reset session data in Redis."""
    redis_client.reset_session(session_id)


def error_response(message: str, status: int = 400) -> ResponseOrTuple:
    """エラーレスポンスを返すヘルパー関数 / Helper to return JSON error responses."""
    return jsonify({"error": message, "response": message}), status


@study_bp.route('/study')
def study_home() -> Response:
    """
    学習アシスタントの初期化エンドポイント
    Initialize study assistant feature and start a new session.

    新規セッションを作成し、フロントエンドの学習画面へリダイレクトします。
    Creates a new session and redirects to the UI.
    """
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url('/study')
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response


@study_bp.route('/study_send_message', methods=['POST'])
def study_send_message() -> ResponseOrTuple:
    """
    学習アシスタントのメッセージ処理エンドポイント
    Handle study assistant chat messages.
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
        # Check rate limits
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

        stored_language = redis_client.get_user_language(session_id)
        language = llama_core.resolve_user_language(
            prompt,
            fallback=stored_language,
            accept_language=request.headers.get("Accept-Language"),
        )
        redis_client.save_user_language(session_id, language)

        response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text = (
            llama_core.chat_with_llama(session_id, prompt, mode="study", language=language)
        )
        return jsonify({
            'response': response,
            'current_plan': current_plan,
            'yes_no_phrase': yes_no_phrase,
            'choices': choices,
            'is_date_select': is_date_select,
            'remaining_text': remaining_text
        })
    except Exception as e:
        logger.error(f"Error in study_send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)
