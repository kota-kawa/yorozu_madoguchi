"""
llama_core の言語判定・日時整形・テキストサニタイズヘルパー。
Language helpers for llama_core.
"""

from datetime import datetime
import re
from typing import Optional

from llama_core_constants import (
    DECISION_DEFAULT_MESSAGES,
    DECISION_ERROR_MESSAGES,
    DECISION_GUARD_BLOCKED_MESSAGES,
    DECISION_MEMO_KEYS_BY_LANGUAGE,
    DECISION_SAFETY_MESSAGES,
    DEFAULT_LANGUAGE,
    LANGUAGE_JA_RE,
    LANGUAGE_LATIN_RE,
    MAX_OUTPUT_CHARS,
    SUPPORTED_LANGUAGES,
)

# 言語判定・正規化のヘルパー
# Language detection and normalization helpers
def _normalize_language_code(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = language.strip().lower().replace("_", "-")
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    if normalized.startswith("ja"):
        return "ja"
    if normalized.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def _detect_language(text: str) -> Optional[str]:
    if not text:
        return None
    if LANGUAGE_JA_RE.search(text):
        return "ja"
    if LANGUAGE_LATIN_RE.search(text):
        return "en"
    return None


def _parse_accept_language(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    parts = [part.strip() for part in header_value.split(",") if part.strip()]
    for part in parts:
        code = part.split(";")[0].strip().lower()
        if code.startswith("ja"):
            return "ja"
        if code.startswith("en"):
            return "en"
    return None


def resolve_user_language(
    message: str,
    fallback: Optional[str] = None,
    accept_language: Optional[str] = None,
) -> str:
    detected = _detect_language(message)
    if detected:
        return detected
    normalized_fallback = _normalize_language_code(fallback) if fallback else None
    if normalized_fallback:
        return normalized_fallback
    header_lang = _parse_accept_language(accept_language)
    if header_lang:
        return header_lang
    return DEFAULT_LANGUAGE


def _language_instruction(language: str) -> str:
    lang = _normalize_language_code(language)
    if lang == "en":
        return "Language: English. Respond only in English."
    return "言語: 日本語。日本語のみで返答してください。"


def _decision_language_instruction(language: str) -> str:
    lang = _normalize_language_code(language)
    if lang == "en":
        return "All item names and values must be in English. Do not mix languages."
    return "項目名と内容は日本語で統一し、言語を混在させないでください。"


def _memo_key_for_language(language: str) -> str:
    lang = _normalize_language_code(language)
    return DECISION_MEMO_KEYS_BY_LANGUAGE.get(lang, DECISION_MEMO_KEYS_BY_LANGUAGE["ja"])


def _decision_default_message(language: str) -> str:
    lang = _normalize_language_code(language)
    return DECISION_DEFAULT_MESSAGES.get(lang, DECISION_DEFAULT_MESSAGES["ja"])


def _decision_error_message(language: str) -> str:
    lang = _normalize_language_code(language)
    return DECISION_ERROR_MESSAGES.get(lang, DECISION_ERROR_MESSAGES["ja"])


def _decision_safety_message(language: str) -> str:
    lang = _normalize_language_code(language)
    return DECISION_SAFETY_MESSAGES.get(lang, DECISION_SAFETY_MESSAGES["ja"])


def _decision_guard_blocked_message(language: str) -> str:
    lang = _normalize_language_code(language)
    return DECISION_GUARD_BLOCKED_MESSAGES.get(lang, DECISION_GUARD_BLOCKED_MESSAGES["ja"])


def current_datetime_line(language: str) -> str:
    """現在日時を言語に合わせて返すヘルパー関数
    Return the current datetime formatted for the given language.
    """
    now = datetime.now()
    if _normalize_language_code(language) == "en":
        weekday_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday = weekday_map[now.weekday()]
        return (
            f"Current datetime: {now.year}-{now.month:02d}-{now.day:02d} "
            f"({weekday}) {now.hour:02d}:{now.minute:02d}"
        )
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekday_map[now.weekday()]
    return f"現在日時: {now.year}年{now.month}月{now.day}日（{weekday}） {now.hour:02d}:{now.minute:02d}"


def current_datetime_jp_line() -> str:
    """現在日時を日本語フォーマットで返すヘルパー関数
    Return the current datetime in Japanese format.
    """
    return current_datetime_line("ja")


def sanitize_llm_text(text: Optional[str], max_length: int = MAX_OUTPUT_CHARS) -> str:
    """
    LLMからの出力テキストをサニタイズ（制御文字除去、長さ制限）する
    Sanitize LLM output (remove control chars, enforce length).
    """
    if text is None:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str(text))
    cleaned = cleaned.strip()
    if max_length and len(cleaned) > max_length:
        cleaned = f"{cleaned[:max_length]}..."
    return cleaned
