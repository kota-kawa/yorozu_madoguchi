"""
バックエンド共通の例外階層とエラーレスポンス生成。
Shared backend exception hierarchy and unified error response helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Tuple

from flask import Response, jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

GENERIC_SERVER_ERROR_MESSAGE = "サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。"
GENERIC_DATABASE_ERROR_MESSAGE = "データベース処理に失敗しました。しばらく待ってから再試行してください。"
GENERIC_REDIS_ERROR_MESSAGE = "利用状況を確認できません。しばらく待ってから再試行してください。"
GENERIC_LLM_TIMEOUT_MESSAGE = "応答の生成がタイムアウトしました。しばらく待ってから再試行してください。"
GENERIC_LLM_SERVICE_MESSAGE = "応答生成サービスで一時的なエラーが発生しました。しばらく待ってから再試行してください。"


@dataclass
class BackendError(Exception):
    """
    アプリケーション内で明示的に扱う業務例外の基底クラス。
    Base class for typed backend errors.
    """

    message: str
    status_code: int
    error_type: str
    cause: Optional[Exception] = None

    def __str__(self) -> str:
        return self.message


class ValidationError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=400, error_type="validation_error", cause=cause)


class SessionError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=400, error_type="session_error", cause=cause)


class ForbiddenError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=403, error_type="forbidden", cause=cause)


class ConflictError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=409, error_type="conflict", cause=cause)


class PayloadTooLargeError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=413, error_type="payload_too_large", cause=cause)


class RateLimitError(BackendError):
    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message=message, status_code=429, error_type="rate_limit_exceeded", cause=cause)


class RedisUnavailableError(BackendError):
    def __init__(
        self,
        message: str = GENERIC_REDIS_ERROR_MESSAGE,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, status_code=503, error_type="redis_unavailable", cause=cause)


class DatabaseError(BackendError):
    def __init__(
        self,
        message: str = GENERIC_DATABASE_ERROR_MESSAGE,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, status_code=503, error_type="database_error", cause=cause)


class LLMTimeoutError(BackendError):
    def __init__(
        self,
        message: str = GENERIC_LLM_TIMEOUT_MESSAGE,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, status_code=504, error_type="llm_timeout", cause=cause)


class LLMServiceError(BackendError):
    def __init__(
        self,
        message: str = GENERIC_LLM_SERVICE_MESSAGE,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, status_code=502, error_type="llm_service_error", cause=cause)


class InternalServerError(BackendError):
    def __init__(
        self,
        message: str = GENERIC_SERVER_ERROR_MESSAGE,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, status_code=500, error_type="internal_error", cause=cause)


def _iter_exception_chain(error: BaseException) -> Iterator[BaseException]:
    current: Optional[BaseException] = error
    while current is not None:
        yield current
        current = current.__cause__ or current.__context__


def _status_error_type(status: int) -> str:
    if status == 400:
        return "validation_error"
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    if status == 413:
        return "payload_too_large"
    if status == 429:
        return "rate_limit_exceeded"
    if 400 <= status < 500:
        return "request_error"
    if status == 503:
        return "service_unavailable"
    if status == 504:
        return "gateway_timeout"
    return "internal_error"


def _has_module_prefix(error: BaseException, module_prefix: str) -> bool:
    return error.__class__.__module__.startswith(module_prefix)


def _has_class_name(error: BaseException, names: set[str]) -> bool:
    return error.__class__.__name__ in names


def _is_redis_error(error: Exception) -> bool:
    redis_error_names = {
        "RedisError",
        "ConnectionError",
        "TimeoutError",
        "AuthenticationError",
        "BusyLoadingError",
    }
    for candidate in _iter_exception_chain(error):
        if _has_module_prefix(candidate, "redis") and _has_class_name(candidate, redis_error_names):
            return True
    return False


def _is_database_error(error: Exception) -> bool:
    if isinstance(error, SQLAlchemyError):
        return True
    for candidate in _iter_exception_chain(error):
        if isinstance(candidate, SQLAlchemyError):
            return True
        if _has_module_prefix(candidate, "sqlalchemy"):
            return True
    return False


def _is_llm_timeout_error(error: Exception) -> bool:
    timeout_names = {"APITimeoutError", "ReadTimeout", "ConnectTimeout"}
    for candidate in _iter_exception_chain(error):
        if _has_class_name(candidate, timeout_names):
            return True
        if _has_module_prefix(candidate, "openai") and "timeout" in candidate.__class__.__name__.lower():
            return True
        if _has_module_prefix(candidate, "httpx") and "timeout" in candidate.__class__.__name__.lower():
            return True
    if isinstance(error, TimeoutError):
        return True
    return False


def _is_llm_service_error(error: Exception) -> bool:
    llm_service_error_names = {
        "APIConnectionError",
        "APIError",
        "APIStatusError",
        "RateLimitError",
        "AuthenticationError",
        "PermissionDeniedError",
        "BadRequestError",
    }
    for candidate in _iter_exception_chain(error):
        if _has_module_prefix(candidate, "openai") and _has_class_name(candidate, llm_service_error_names):
            return True
    return False


def classify_backend_exception(
    error: Exception,
    *,
    default_message: str = GENERIC_SERVER_ERROR_MESSAGE,
) -> BackendError:
    """
    未分類例外を共通のBackendErrorへ分類する。
    Classify arbitrary exceptions into a typed BackendError.
    """
    if isinstance(error, BackendError):
        return error

    if isinstance(error, HTTPException):
        status = int(error.code or 500)
        description = str(error.description) if error.description else default_message
        return BackendError(
            message=description,
            status_code=status,
            error_type=_status_error_type(status),
            cause=error,
        )

    if _is_redis_error(error):
        return RedisUnavailableError(cause=error)
    if _is_database_error(error):
        return DatabaseError(cause=error)
    if _is_llm_timeout_error(error):
        return LLMTimeoutError(cause=error)
    if _is_llm_service_error(error):
        return LLMServiceError(cause=error)
    return InternalServerError(message=default_message, cause=error)


def build_error_payload(
    message: str,
    status: int,
    *,
    error_type: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    統一形式のエラーペイロードを組み立てる。
    Build a unified error payload.
    """
    resolved_error_type = error_type or _status_error_type(status)
    payload: Dict[str, Any] = {
        "error": message,
        "response": message,
        "error_type": resolved_error_type,
        "error_code": resolved_error_type,
    }
    if extra:
        payload.update(extra)
    return payload


def json_error_response(
    message: str,
    status: int = 400,
    *,
    error_type: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """
    統一形式のJSONエラーレスポンスを返す。
    Return a unified JSON error response tuple.
    """
    payload = build_error_payload(message, status, error_type=error_type, extra=extra)
    return jsonify(payload), status

