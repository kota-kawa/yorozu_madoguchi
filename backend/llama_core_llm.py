"""
llama_core の安全性チェックとLLM呼び出しヘルパー。
Output guardrails and LLM invocation helpers for llama_core.
"""

import json
import logging
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

import openai

from backend import guard

from backend.groq_openai_client import get_groq_client
from backend.llama_core_constants import (
    GROQ_API_TIMEOUT,
    GROQ_FALLBACK_MODEL_NAME,
    GROQ_MAX_RETRIES,
    GROQ_MODEL_NAME,
    OUTPUT_GUARD_ENABLED,
)

logger = logging.getLogger(__name__)

# 出力ガードとLLM呼び出し
# Output guardrails and LLM invocation
def output_is_safe(text: str) -> bool:
    """
    出力テキストの安全性をチェックする（Guard使用）
    Check output safety using the guard model.
    """
    if not OUTPUT_GUARD_ENABLED or not text:
        return True
    try:
        result = guard.content_checker(text)
        return "unsafe" not in result
    except Exception as e:
        logger.error(f"Output safety check failed: {e}")
        return False


def _build_messages(
    system_prompt: str,
    chat_history: List[Tuple[str, str]],
    user_input: str,
) -> List[Dict[str, str]]:
    """LLM呼び出し用のmessages配列を構築する / Build messages for LLM API calls."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for role, content in chat_history:
        if role == "assistant":
            messages.append({"role": "assistant", "content": content})
        else:
            messages.append({"role": "user", "content": content})
    messages.append({"role": "user", "content": user_input})
    return messages


def _is_transient_error(err: Exception) -> bool:
    """
    一時的なエラー（タイムアウト・接続エラー・レート制限・5xx）かどうかを判定する
    Return True for errors that are safe to retry (timeout, connection, rate-limit, 5xx).
    """
    if isinstance(err, (openai.APITimeoutError, openai.APIConnectionError)):
        return True
    if isinstance(err, openai.APIStatusError) and err.status_code in (429, 500, 502, 503, 504):
        return True
    return False


def _invoke_chat_completion(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    tool_choice: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    指定メッセージでチャット補完APIを呼び出して本文を返す。
    一時的なエラー時は指数バックオフで再試行する。
    Call the chat-completions API and return extracted assistant content.
    Retries with exponential backoff on transient errors.
    """
    client = get_groq_client()
    payload: Dict[str, Any] = {
        "model": model_name or GROQ_MODEL_NAME,
        "messages": messages,
        "timeout": GROQ_API_TIMEOUT,
    }
    if tool_choice:
        payload["tool_choice"] = tool_choice
    if tools is not None:
        payload["tools"] = tools
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            completion = client.chat.completions.create(**payload)
            return _extract_message_content(completion.choices[0].message)
        except Exception as e:
            if not _is_transient_error(e) or attempt == GROQ_MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            logger.warning(
                "Groq API transient error (attempt %d/%d): %s; retrying in %ds",
                attempt + 1, GROQ_MAX_RETRIES, e, wait,
            )
            time.sleep(wait)
    raise RuntimeError("Unreachable")


def _invoke_chat_completion_stream(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    tool_choice: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Iterator[str]:
    """
    指定メッセージでチャット補完APIをストリーミング呼び出しする。
    接続確立時の一時的なエラーは指数バックオフで再試行する。
    Call the chat-completions API in streaming mode and yield text deltas.
    Retries with exponential backoff on transient errors during connection setup.
    """
    client = get_groq_client()
    payload: Dict[str, Any] = {
        "model": model_name or GROQ_MODEL_NAME,
        "messages": messages,
        "stream": True,
        "timeout": GROQ_API_TIMEOUT,
    }
    if tool_choice:
        payload["tool_choice"] = tool_choice
    if tools is not None:
        payload["tools"] = tools
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            stream = client.chat.completions.create(**payload)
            for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if content:
                    yield str(content)
            return
        except Exception as e:
            if not _is_transient_error(e) or attempt == GROQ_MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            logger.warning(
                "Groq API transient error on stream (attempt %d/%d): %s; retrying in %ds",
                attempt + 1, GROQ_MAX_RETRIES, e, wait,
            )
            time.sleep(wait)


PASS_THROUGH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "assistant",
            "description": "Return assistant message content when the model tries to call a tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    }
]


def _extract_message_content(message: Any) -> str:
    """
    通常本文または tool_call 引数から応答テキストを取り出す
    Extract response text from message content or tool-call arguments.
    """
    content = getattr(message, "content", None) or ""
    if content:
        return content
    tool_calls = getattr(message, "tool_calls", None) or []
    for call in tool_calls:
        function = getattr(call, "function", None)
        if not function:
            continue
        name = getattr(function, "name", "")
        if name != "assistant":
            continue
        args = getattr(function, "arguments", None)
        parsed = None
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError:
                parsed = None
        elif isinstance(args, dict):
            parsed = args
        if isinstance(parsed, dict):
            content_value = parsed.get("content")
            if content_value:
                return str(content_value)
        if isinstance(args, str) and args:
            return args
    return ""


def _invoke_with_tool_retries(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> str:
    """
    tool_use_failed 発生時にフォールバック条件で再試行する
    Retry with fallback options when the model fails due to tool-use errors.
    """
    try:
        return _invoke_chat_completion(messages, model_name=model_name)
    except Exception as e:
        if not _is_tool_use_failed(e):
            raise

    if GROQ_FALLBACK_MODEL_NAME:
        logger.warning(
            "Groq tool_use_failed; retrying with fallback model: %s",
            GROQ_FALLBACK_MODEL_NAME,
        )
        try:
                return _invoke_chat_completion(messages, model_name=GROQ_FALLBACK_MODEL_NAME)
        except Exception as retry_err:
            if _is_tool_use_failed(retry_err):
                logger.warning("Groq tool_use_failed on fallback; retrying with tool_choice=auto")
                return _invoke_chat_completion(
                    messages,
                    model_name=GROQ_FALLBACK_MODEL_NAME,
                    tool_choice="auto",
                    tools=PASS_THROUGH_TOOLS,
                )
            raise

    logger.warning("Groq tool_use_failed; retrying with tool_choice=auto")
    return _invoke_chat_completion(
        messages,
        model_name=model_name,
        tool_choice="auto",
        tools=PASS_THROUGH_TOOLS,
    )


def _invoke_with_tool_retries_stream(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> Iterator[str]:
    """
    tool_use_failed 発生時にフォールバック条件で再試行しつつストリーミングする
    Stream responses with fallback retries when tool-use errors occur.
    """
    try:
        yield from _invoke_chat_completion_stream(messages, model_name=model_name)
        return
    except Exception as e:
        if not _is_tool_use_failed(e):
            raise

    if GROQ_FALLBACK_MODEL_NAME:
        logger.warning(
            "Groq tool_use_failed; retrying stream with fallback model: %s",
            GROQ_FALLBACK_MODEL_NAME,
        )
        try:
            yield from _invoke_chat_completion_stream(
                messages,
                model_name=GROQ_FALLBACK_MODEL_NAME,
            )
            return
        except Exception as retry_err:
            if _is_tool_use_failed(retry_err):
                logger.warning("Groq tool_use_failed on fallback stream; retrying with tool_choice=auto")
                yield from _invoke_chat_completion_stream(
                    messages,
                    model_name=GROQ_FALLBACK_MODEL_NAME,
                    tool_choice="auto",
                    tools=PASS_THROUGH_TOOLS,
                )
                return
            raise

    logger.warning("Groq tool_use_failed; retrying stream with tool_choice=auto")
    yield from _invoke_chat_completion_stream(
        messages,
        model_name=model_name,
        tool_choice="auto",
        tools=PASS_THROUGH_TOOLS,
    )

def _is_tool_use_failed(err: Exception) -> bool:
    """
    例外内容が tool_use_failed 系かどうかを判定する
    Detect whether an exception represents a tool-use failure case.
    """
    text = f"{err}"
    if "tool_use_failed" in text or "Tool choice is none" in text or "called a tool" in text:
        return True
    body = getattr(err, "body", None)
    if isinstance(body, dict):
        error = body.get("error") or {}
        if error.get("code") == "tool_use_failed":
            return True
        if "tool" in str(error.get("message", "")):
            return True
    return False
