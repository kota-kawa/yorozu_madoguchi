from flask import Blueprint, request, jsonify, redirect, make_response
import logging
import os
import uuid

import llama_core
import limit_manager
import redis_client

logger = logging.getLogger(__name__)

fitness_bp = Blueprint('fitness', __name__)


def resolve_frontend_url(path=""):
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


def reset_session_data(session_id):
    """Redisのセッションデータをリセットする"""
    redis_client.reset_session(session_id)


def error_response(message, status=400):
    """エラーレスポンスを返すヘルパー関数"""
    return jsonify({"error": message, "response": message}), status


@fitness_bp.route('/fitness')
def fitness_home():
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url('/fitness')
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
    return response


@fitness_bp.route('/fitness_send_message', methods=['POST'])
def fitness_send_message():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        is_allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(session_id)
        if not user_type:
            return error_response("ユーザー種別を選択してください。", status=400)
        if total_exceeded:
            return error_response("今日の上限に達しました。明日またご利用ください。", status=429)
        if not is_allowed:
            return error_response(
                f"本日の利用制限（{limit}回）に達しました。明日またご利用ください。",
                status=429
            )

        data = request.get_json(silent=True)
        if data is None:
            return error_response("リクエストの形式が正しくありません（JSONを送信してください）。", status=400)

        prompt = data.get('message', '')
        if not prompt:
            return error_response("メッセージを入力してください。", status=400)

        if len(prompt) > 3000:
            return error_response("入力された文字数が3000文字を超えています。短くして再度お試しください。", status=400)

        response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text = llama_core.chat_with_llama(
            session_id,
            prompt,
            mode="fitness",
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
        logger.error(f"Error in fitness_send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)
