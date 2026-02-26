"""
llama_core の安全性チェックとLLM呼び出しヘルパー。
Output guardrails and LLM invocation helpers for llama_core.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import guard

from groq_openai_client import get_groq_client
from llama_core_constants import (
    GROQ_FALLBACK_MODEL_NAME,
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


def _invoke_chat_completion(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    tool_choice: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    EN: Execute invoke chat completion processing.
    JP: _invoke_chat_completion の処理を実行する。
    """
    client = get_groq_client()
    payload: Dict[str, Any] = {
        "model": model_name or GROQ_MODEL_NAME,
        "messages": messages,
    }
    if tool_choice:
        payload["tool_choice"] = tool_choice
    if tools is not None:
        payload["tools"] = tools
    completion = client.chat.completions.create(**payload)
    return _extract_message_content(completion.choices[0].message)


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
    EN: Execute extract message content processing.
    JP: _extract_message_content の処理を実行する。
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
    EN: Execute invoke with tool retries processing.
    JP: _invoke_with_tool_retries の処理を実行する。
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

def _is_tool_use_failed(err: Exception) -> bool:
    """
    EN: Execute is tool use failed processing.
    JP: _is_tool_use_failed の処理を実行する。
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
