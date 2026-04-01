"""
ルートで共通利用するヘルパー関数。
Shared helper utilities for route modules.
"""

from dataclasses import dataclass
import logging
import os
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
import uuid

from flask import (
    Blueprint,
    Request,
    Response,
    jsonify,
    make_response,
    redirect,
    request,
    stream_with_context,
)

from backend import security
from backend import redis_client
from backend.session_request_lock import (
    acquire_session_lock,
    release_session_lock,
    session_request_lock,
)

ResponseOrTuple = Union[Response, Tuple[Response, int]]
LimitCheckResult = Tuple[bool, int, int, str, bool, Optional[str]]


@dataclass(frozen=True)
class ChatRequestContext:
    """send_message 共通前処理の結果。/ Parsed and validated chat request context."""

    session_id: str
    data: Dict[str, Any]
    prompt: str
    language: str


ChatErrorResponder = Callable[[str, int], ResponseOrTuple]
LimitChecker = Callable[[str, Optional[str]], LimitCheckResult]
LanguageResolver = Callable[..., str]
LanguageGetter = Callable[[str], str]
LanguageSaver = Callable[[str, str], None]
LimitExceededMessageBuilder = Callable[[int], str]
ChatResult = Tuple[Optional[str], str, Optional[str], Optional[List[str]], bool, str, bool]
ChatRunner = Callable[..., ChatResult]
StreamChatRunner = Callable[..., Generator[str, None, None]]
PlanCompleter = Callable[[str], str]
ExceptionResponder = Callable[[Exception], ResponseOrTuple]
SessionResetter = Callable[[str], None]
SessionResetErrorHandler = Callable[[str, Exception], None]


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


def rich_chat_error_response(message: str, status: int = 400) -> ResponseOrTuple:
    """
    チャットUI向けの詳細エラーペイロードを返す。
    Return rich chat error payload consumed by the generic chat UI.
    """
    return jsonify({
        "error": message,
        "response": message,
        "current_plan": "",
        "yes_no_phrase": "",
        "choices": None,
        "is_date_select": False,
        "remaining_text": "",
        "used_web_search": False,
    }), status


def submit_plan_error_response(message: str, status: int = 400) -> ResponseOrTuple:
    """submit_plan 向けの最小エラーレスポンス。/ Minimal error response for submit_plan."""
    return jsonify({"error": message}), status


def prepare_chat_request(
    req: Request,
    *,
    error_responder: ChatErrorResponder,
    check_and_increment_limit: LimitChecker,
    resolve_user_language: LanguageResolver,
    get_user_language: LanguageGetter,
    save_user_language: LanguageSaver,
    limit_exceeded_message_builder: Optional[LimitExceededMessageBuilder] = None,
) -> Union[ChatRequestContext, ResponseOrTuple]:
    """
    send_message の共通前処理を実行する。
    Execute shared pre-processing for send_message.
    """
    if not security.is_csrf_valid(req):
        return error_responder("不正なリクエストです。", status=403)

    session_id = req.cookies.get("session_id")
    if not session_id:
        return error_responder("セッションが無効です。ページをリロードしてください。", status=400)

    data = req.get_json(silent=True)
    if not isinstance(data, dict):
        return error_responder(
            "リクエストの形式が正しくありません（JSONを送信してください）。",
            status=400,
        )

    is_allowed, _count, limit, user_type, total_exceeded, error_code = (
        check_and_increment_limit(session_id, user_type=data.get("user_type"))
    )
    if error_code == "redis_unavailable":
        return error_responder(
            "利用状況を確認できません。しばらく待ってから再試行してください。",
            status=503,
        )
    if not user_type:
        return error_responder("ユーザー種別を選択してください。", status=400)
    if total_exceeded:
        return error_responder("今日の上限に達しました。明日またご利用ください。", status=429)
    if not is_allowed:
        message = (
            limit_exceeded_message_builder(limit)
            if limit_exceeded_message_builder
            else f"本日の利用制限（{limit}回）に達しました。明日またご利用ください。"
        )
        return error_responder(
            message,
            status=429,
        )

    prompt = data.get("message", "")
    if not isinstance(prompt, str) or not prompt:
        return error_responder("メッセージを入力してください。", status=400)
    if len(prompt) > 3000:
        return error_responder(
            "入力された文字数が3000文字を超えています。短くして再度お試しください。",
            status=400,
        )

    stored_language = get_user_language(session_id)
    language = resolve_user_language(
        prompt,
        fallback=stored_language,
        accept_language=req.headers.get("Accept-Language"),
    )
    save_user_language(session_id, language)

    return ChatRequestContext(
        session_id=session_id,
        data=data,
        prompt=prompt,
        language=language,
    )


def wants_stream_response(req: Request, data: Dict[str, Any]) -> bool:
    """ストリーミング応答を希望しているか判定する / Check whether SSE stream is requested."""
    accept_mimetypes = req.accept_mimetypes
    if hasattr(accept_mimetypes, "get"):
        sse_quality = accept_mimetypes.get("text/event-stream", 0)  # type: ignore[attr-defined]
        json_quality = accept_mimetypes.get("application/json", 0)  # type: ignore[attr-defined]
    else:
        sse_quality = accept_mimetypes["text/event-stream"]
        json_quality = accept_mimetypes["application/json"]

    return bool(data.get("stream")) or (
        sse_quality > json_quality
    )


def build_stream_chat_response(
    *,
    session_id: str,
    prompt: str,
    mode: str,
    language: str,
    error_responder: ChatErrorResponder,
    stream_chat_with_llama: StreamChatRunner,
) -> ResponseOrTuple:
    """
    ストリーミング応答を生成する。
    Build an SSE response with per-session lock handling.
    """
    lock_acquired = acquire_session_lock(session_id)
    if not lock_acquired:
        return error_responder(
            "前のメッセージを処理中です。応答が返るまでお待ちください。",
            status=409,
        )

    def generate() -> Generator[str, None, None]:
        try:
            for chunk in stream_chat_with_llama(
                session_id,
                prompt,
                mode=mode,
                language=language,
            ):
                yield chunk
        finally:
            release_session_lock(session_id)

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def build_json_chat_response(
    *,
    session_id: str,
    prompt: str,
    mode: str,
    language: str,
    error_responder: ChatErrorResponder,
    chat_with_llama: ChatRunner,
) -> ResponseOrTuple:
    """
    非ストリーミング応答を生成する。
    Build a non-streaming JSON response with per-session lock handling.
    """
    with session_request_lock(session_id) as lock_acquired:
        if not lock_acquired:
            return error_responder(
                "前のメッセージを処理中です。応答が返るまでお待ちください。",
                status=409,
            )

        (
            response_text,
            current_plan,
            yes_no_phrase,
            choices,
            is_date_select,
            remaining_text,
            used_web_search,
        ) = chat_with_llama(
            session_id,
            prompt,
            mode=mode,
            language=language,
        )
        return jsonify({
            "response": response_text,
            "current_plan": current_plan,
            "yes_no_phrase": yes_no_phrase,
            "choices": choices,
            "is_date_select": is_date_select,
            "remaining_text": remaining_text,
            "used_web_search": used_web_search,
        })


def handle_chat_send_message(
    req: Request,
    *,
    mode: str,
    error_responder: ChatErrorResponder,
    check_and_increment_limit: LimitChecker,
    resolve_user_language: LanguageResolver,
    get_user_language: LanguageGetter,
    save_user_language: LanguageSaver,
    chat_with_llama: ChatRunner,
    stream_chat_with_llama: StreamChatRunner,
    limit_exceeded_message_builder: Optional[LimitExceededMessageBuilder] = None,
) -> ResponseOrTuple:
    """
    send_message の共通処理フローを実行する。
    Execute the shared end-to-end send_message workflow.
    """
    context_or_error = prepare_chat_request(
        req,
        error_responder=error_responder,
        check_and_increment_limit=check_and_increment_limit,
        resolve_user_language=resolve_user_language,
        get_user_language=get_user_language,
        save_user_language=save_user_language,
        limit_exceeded_message_builder=limit_exceeded_message_builder,
    )
    if not isinstance(context_or_error, ChatRequestContext):
        return context_or_error

    context = context_or_error
    if wants_stream_response(req, context.data):
        return build_stream_chat_response(
            session_id=context.session_id,
            prompt=context.prompt,
            mode=mode,
            language=context.language,
            error_responder=error_responder,
            stream_chat_with_llama=stream_chat_with_llama,
        )

    return build_json_chat_response(
        session_id=context.session_id,
        prompt=context.prompt,
        mode=mode,
        language=context.language,
        error_responder=error_responder,
        chat_with_llama=chat_with_llama,
    )


def handle_submit_plan(
    req: Request,
    *,
    complete_plan: PlanCompleter,
    error_responder: ChatErrorResponder = submit_plan_error_response,
) -> ResponseOrTuple:
    """
    submit_plan の共通処理を実行する。
    Execute the shared submit_plan workflow.
    """
    if not security.is_csrf_valid(req):
        return error_responder("不正なリクエストです。", status=403)

    session_id = req.cookies.get("session_id")
    if not session_id:
        return error_responder("セッションが無効です。", status=400)

    result = complete_plan(session_id)
    return jsonify({"compile": result})


def make_session_init_route(
    *,
    blueprint: Blueprint,
    route_path: str,
    frontend_path: str,
    default_frontend_origin: str = "https://chat.project-kk.com",
    endpoint_name: Optional[str] = None,
    reset_session: SessionResetter = reset_session_data,
    on_reset_error: Optional[SessionResetErrorHandler] = None,
) -> Callable[[], Response]:
    """
    初期化＋リダイレクト用の home ルートを生成して Blueprint に登録する。
    Create and register a home route that initializes session and redirects.
    """

    @blueprint.route(route_path, endpoint=endpoint_name)
    def home() -> Response:
        session_id = str(uuid.uuid4())
        try:
            reset_session(session_id)
        except Exception as error:
            if on_reset_error:
                on_reset_error(session_id, error)
            else:
                raise
        redirect_url = resolve_frontend_url(frontend_path, default_origin=default_frontend_origin)
        response = make_response(redirect(redirect_url))
        response.set_cookie("session_id", session_id, **security.cookie_settings(request))
        return response

    return home


def make_chat_send_message_route(
    *,
    blueprint: Blueprint,
    route_path: str,
    mode: str,
    error_responder: ChatErrorResponder,
    endpoint_name: Optional[str] = None,
    catch_exceptions: bool = True,
    check_and_increment_limit: LimitChecker,
    resolve_user_language: LanguageResolver,
    get_user_language: LanguageGetter,
    save_user_language: LanguageSaver,
    chat_with_llama: ChatRunner,
    stream_chat_with_llama: StreamChatRunner,
    logger: logging.Logger,
    limit_exceeded_message_builder: Optional[LimitExceededMessageBuilder] = None,
    exception_responder: Optional[ExceptionResponder] = None,
) -> Callable[[], ResponseOrTuple]:
    """
    send_message ルートを生成して Blueprint に登録する。
    Create and register a send_message route for a feature mode.
    """

    @blueprint.route(route_path, methods=["POST"], endpoint=endpoint_name)
    def send_message() -> ResponseOrTuple:
        def _run() -> ResponseOrTuple:
            return handle_chat_send_message(
                request,
                mode=mode,
                error_responder=error_responder,
                check_and_increment_limit=check_and_increment_limit,
                resolve_user_language=resolve_user_language,
                get_user_language=get_user_language,
                save_user_language=save_user_language,
                chat_with_llama=chat_with_llama,
                stream_chat_with_llama=stream_chat_with_llama,
                limit_exceeded_message_builder=limit_exceeded_message_builder,
            )

        if not catch_exceptions:
            return _run()

        try:
            return _run()
        except Exception as error:
            logger.error(f"Error in {mode}_send_message: {error}", exc_info=True)
            if exception_responder:
                return exception_responder(error)
            return error_responder(
                "サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。",
                status=500,
            )

    return send_message


def make_submit_plan_route(
    *,
    blueprint: Blueprint,
    route_path: str,
    complete_plan: PlanCompleter,
    logger: logging.Logger,
    endpoint_name: Optional[str] = None,
    catch_exceptions: bool = True,
    error_responder: ChatErrorResponder = submit_plan_error_response,
    exception_responder: Optional[ExceptionResponder] = None,
) -> Callable[[], ResponseOrTuple]:
    """
    submit_plan ルートを生成して Blueprint に登録する。
    Create and register a submit_plan route.
    """

    @blueprint.route(route_path, methods=["POST"], endpoint=endpoint_name)
    def submit_plan() -> ResponseOrTuple:
        def _run() -> ResponseOrTuple:
            return handle_submit_plan(
                request,
                complete_plan=complete_plan,
                error_responder=error_responder,
            )

        if not catch_exceptions:
            return _run()

        try:
            return _run()
        except Exception as error:
            logger.error(f"Error in {route_path.strip('/')}: {error}", exc_info=True)
            if exception_responder:
                return exception_responder(error)
            return submit_plan_error_response("プランの保存に失敗しました。", status=500)

    return submit_plan
