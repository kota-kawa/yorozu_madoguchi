"""
ルートで共通利用するヘルパー関数。
Shared helper utilities for route modules.
"""

from flask import Response, jsonify, request
import os
from typing import Tuple, Union

from backend import redis_client

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def resolve_frontend_url(
    path: str = "",
    default_origin: str = "https://chat.project-kk.com",
) -> str:
    """
    フロントエンドのURLを動的に解決する。
    Resolve the frontend base URL dynamically.
    """
    host = request.headers.get("Host", "")
    if "chat.project-kk.com" in host:
        base_url = "https://chat.project-kk.com"
    elif "localhost" in host or "127.0.0.1" in host:
        base_url = "http://localhost:5173"
    else:
        base_url = os.getenv("FRONTEND_ORIGIN", default_origin)

    if path and not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"


def reset_session_data(session_id: str) -> None:
    """Redisのセッションデータをリセットする / Reset session data in Redis."""
    redis_client.reset_session(session_id)


def error_response(message: str, status: int = 400) -> ResponseOrTuple:
    """エラーレスポンスを返すヘルパー関数 / Helper to return JSON error responses."""
    return jsonify({"error": message, "response": message}), status
