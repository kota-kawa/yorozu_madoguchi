"""
LLM対話ロジックと決定事項管理のコア実装。
Core logic for LLM chat flows and decision tracking.
"""

import json
import logging
import re
import warnings
from typing import Any, Dict, Generator, List, Optional, Tuple

from backend import brave_search
from backend import guard
from backend import redis_client

from backend.llama_core_constants import (
    DECISION_ALLOWED_KEYS_BY_MODE,
    DECISION_BULLET_PREFIX_RE,
    DECISION_DATE_LIKE_RE,
    DECISION_DEFAULT_MESSAGE,
    DECISION_DEFAULT_MESSAGES,
    DECISION_ERROR_MESSAGES,
    DECISION_FLEX_KEY_LIMIT,
    DECISION_GUARD_BLOCKED_MESSAGES,
    DECISION_IGNORED_LINES,
    DECISION_KEY_EXTRA_ALIASES_BY_MODE,
    DECISION_KEY_LABELS_BY_MODE,
    DECISION_KV_SEPARATOR_RE,
    DECISION_MAX_ITEMS,
    DECISION_MEMO_KEYS_BY_LANGUAGE,
    DECISION_PATCH_ALLOWED_KEYS,
    DECISION_SAFETY_MESSAGES,
    DECISION_SLOT_QUESTION_PATTERNS,
    DECISION_SLOT_VALUE_PATTERNS,
    DECISION_UNKNOWN_ANSWER_RE,
    DECISION_YES_NO_TOKENS,
    DEFAULT_LANGUAGE,
    GROQ_FALLBACK_MODEL_NAME,
    GROQ_MODEL_NAME,
    LANGUAGE_JA_RE,
    LANGUAGE_LATIN_RE,
    LANGUAGE_NAMES,
    MAX_DECISION_CHARS,
    MAX_OUTPUT_CHARS,
    OUTPUT_GUARD_ENABLED,
    SUPPORTED_LANGUAGES,
    groq_api_key,
)
from backend.llama_core_decision import (
    _DECISION_ALIAS_CACHE,
    _apply_decision_patch,
    _build_memo_value,
    _canonicalize_decision_key,
    _derive_decision_patch_from_history,
    _decision_items_to_text,
    _enforce_decision_policy,
    _extract_json_object,
    _extract_kv_map,
    _extract_slot_value,
    _get_decision_alias_lookup,
    _is_date_like,
    _is_memo_key,
    _is_valid_slot_value,
    _label_for_canonical_key,
    _merge_decision_text,
    _normalize_decision_line,
    _normalize_decision_patch,
    _normalize_key_alias,
    _normalize_user_value,
    _parse_decision_items,
    _parse_decision_key_value,
    _split_decision_lines,
    _strip_code_fences,
)
from backend.llama_core_language import (
    _decision_default_message,
    _decision_error_message,
    _decision_guard_blocked_message,
    _decision_language_instruction,
    _decision_safety_message,
    _detect_language,
    _language_instruction,
    _memo_key_for_language,
    _normalize_language_code,
    _parse_accept_language,
    current_datetime_jp_line,
    current_datetime_line,
    resolve_user_language,
    sanitize_llm_text,
)
from backend.llama_core_llm import (
    PASS_THROUGH_TOOLS,
    _build_messages,
    _extract_message_content,
    _invoke_chat_completion,
    _invoke_with_tool_retries_stream,
    _invoke_with_tool_retries,
    _is_tool_use_failed,
    output_is_safe,
)
from backend.llama_core_prompts import PROMPTS

# ロギング設定
# Configure logging
logger = logging.getLogger(__name__)
# 特定の警告を抑制
# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")


def _parse_web_search_decision(raw_text: str) -> Dict[str, Any]:
    """
    検索判定レスポンスをJSONとして解析する
    Parse web-search decision JSON from model output.
    """
    parsed = _extract_json_object(raw_text)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _needs_web_search(
    message: str,
    chat_history: List[Tuple[str, str]],
    mode: str,
    language: str,
) -> Tuple[bool, str]:
    """
    LLMでWeb検索要否を判定する
    Decide whether to trigger web search using LLM judgment.
    """
    if not brave_search.is_configured():
        return False, ""

    user_input = (message or "").strip()
    if not user_input:
        return False, ""

    if language == "en":
        system_prompt = (
            "You are a search router. Decide whether web search is necessary before answering.\n"
            "Use a conservative policy: search only when timeliness/factual verification matters.\n"
            "Search if the user asks for latest/recent/current/price/news/law/rules/schedule/company or person facts,\n"
            "or explicitly asks to look things up.\n"
            "Do not search for casual chat, brainstorming, creative writing, translation, or personal advice.\n"
            f"Current mode: {mode}\n"
            "Return strict JSON only:\n"
            '{"should_search": boolean, "query": string, "reason": string}\n'
            "When should_search is false, query must be empty."
        )
    else:
        system_prompt = (
            "あなたは検索ルーターです。回答前にWeb検索が必要かを判断してください。\n"
            "方針は保守的です。最新性や事実確認が必要な場合だけ検索します。\n"
            "最新・最近・現在・価格・ニュース・法律/ルール・日程・企業/人物の事実確認、"
            "またはユーザーが明示的に検索を要求した場合は検索します。\n"
            "雑談、ブレスト、創作、翻訳、個人的な助言では検索しません。\n"
            f"現在のモード: {mode}\n"
            "次のJSONのみを返してください:\n"
            '{"should_search": boolean, "query": string, "reason": string}\n'
            "should_search が false の場合、query は空文字にしてください。"
        )

    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    messages = _build_messages(system_prompt, recent_history, user_input)
    try:
        decision_raw = _invoke_with_tool_retries(messages)
    except Exception as e:
        logger.warning("Web-search routing failed, fallback to no-search: %s", e)
        return False, ""

    decision = _parse_web_search_decision(decision_raw)
    should_search = bool(decision.get("should_search"))
    query = sanitize_llm_text(str(decision.get("query", "")), max_length=200).strip()
    if not should_search or not query:
        return False, ""
    return True, query


def _build_web_context(results: List[Dict[str, str]], language: str) -> str:
    """
    Web検索結果をプロンプト用コンテキストへ整形する
    Format web results as prompt context.
    """
    if not results:
        return ""

    lines: List[str] = []
    for index, item in enumerate(results[:5], start=1):
        url = (item.get("url") or "").strip()
        if not url:
            continue
        title = (item.get("title") or "").strip() or url
        description = (item.get("description") or "").strip()
        if language == "en":
            block = f"{index}. {title}\nURL: {url}"
            if description:
                block += f"\nSummary: {description}"
        else:
            block = f"{index}. {title}\nURL: {url}"
            if description:
                block += f"\n概要: {description}"
        lines.append(block)

    if not lines:
        return ""

    header = "## Web Search Results" if language == "en" else "## Web検索結果"
    return f"{header}\n" + "\n\n".join(lines)


def _append_sources(text: str, results: List[Dict[str, str]], language: str) -> str:
    """
    回答末尾に出典URLを付与する
    Append source URLs to the end of assistant text.
    """
    normalized_text = sanitize_llm_text(text).strip()
    if not normalized_text or normalized_text == "Empty" or not results:
        return normalized_text

    header = "Sources" if language == "en" else "参考URL"
    if f"{header}:" in normalized_text:
        return normalized_text

    urls: List[str] = []
    for item in results:
        url = (item.get("url") or "").strip()
        if not url or url in urls:
            continue
        urls.append(url)

    if not urls:
        return normalized_text

    source_lines = "\n".join(f"- {url}" for url in urls)
    return f"{normalized_text}\n\n{header}:\n{source_lines}"


def _run_web_search_if_needed(
    message: str,
    chat_history: List[Tuple[str, str]],
    mode: str,
    language: str,
) -> Tuple[bool, List[Dict[str, str]]]:
    """
    必要時のみWeb検索を実行する
    Execute web search only when LLM decides it is required.
    """
    should_search, query = _needs_web_search(message, chat_history, mode, language)
    if not should_search:
        return False, []

    results = brave_search.search_web(query)
    return True, results

def run_qa_chain(
    message: str,
    chat_history: List[Tuple[str, str]],
    mode: str = "travel",
    decision_text: Optional[str] = None,
    language: Optional[str] = None,
    web_context: Optional[str] = None,
) -> Tuple[str, Optional[str], Optional[List[str]], bool, str]:
    """
    ユーザーのメッセージに対してLLMで応答を生成する
    Generate an LLM response for a user message.
    
    1. プロンプトの構築（システムプロンプト + 履歴 + ユーザー入力）
    2. LLMの呼び出し
    3. レスポンスのサニタイズと安全性チェック
    4. 特殊形式（Select, Yes/No, DateSelect）の抽出と解析
    1) Build prompt (system + history + user input)
    2) Call LLM
    3) Sanitize response and run safety checks
    4) Extract special formats (Select, Yes/No, DateSelect)
    """
    lang = _normalize_language_code(language)
    system_prompt = (
        _language_instruction(lang)
        + "\n"
        + PROMPTS.get(mode, PROMPTS["travel"])["system"]
        + "\n"
        + current_datetime_line(lang)
    )
    decision_text = (decision_text or "").strip()
    if decision_text in DECISION_IGNORED_LINES:
        decision_text = ""
    if decision_text:
        if lang == "en":
            system_prompt += (
                "\n\n## Decisions so far\n"
                f"{decision_text}\n"
                "- Do not ask again about already decided items. Ask for the next missing info."
            )
        else:
            system_prompt += (
                "\n\n## 既に決定している情報\n"
                f"{decision_text}\n"
                "- 既に決定している内容は繰り返し質問せず、次に必要な情報を確認してください。"
            )

    if web_context:
        if lang == "en":
            system_prompt += (
                "\n\nUse the web context only for factual support and avoid fabricating facts.\n"
                "Do not mention internal reasoning.\n"
                f"{web_context}"
            )
        else:
            system_prompt += (
                "\n\nWeb検索コンテキストは事実確認にのみ使い、推測で事実を作らないでください。\n"
                "内部推論は出力しないでください。\n"
                f"{web_context}"
            )
    
    messages = _build_messages(system_prompt, chat_history, message)
    response = _invoke_with_tool_retries(messages)
    return _parse_response_output(response, lang)


def _parse_response_output(
    raw_response: str,
    language: Optional[str],
) -> Tuple[str, Optional[str], Optional[List[str]], bool, str]:
    """
    LLMの生テキストを整形し、特殊フォーマットを抽出する
    Sanitize raw output and extract Select/Yes-No/DateSelect directives.
    """
    lang = _normalize_language_code(language)
    response = sanitize_llm_text(raw_response)

    if not output_is_safe(response):
        safe_message = _decision_safety_message(lang)
        return safe_message, None, None, False, safe_message

    yes_no_phrase = None
    choices = None
    is_date_select = False
    remaining_text = response

    select_match = re.search(r'Select\s*[:：]\s*[\[\［](.*?)[\]\］]', response, re.DOTALL)
    if select_match:
        choices_str = select_match.group(1)
        parts = re.split(r'[,、，]', choices_str)
        choices = [c.strip().strip('"\'') for c in parts if c.strip()]
        remaining_text = remaining_text.replace(select_match.group(0), "").strip()

    date_match = re.search(r'DateSelect\s*[:：]\s*true', remaining_text, re.IGNORECASE)
    if date_match:
        is_date_select = True
        remaining_text = remaining_text.replace(date_match.group(0), "").strip()

    if not choices and not is_date_select and "Yes/No" in remaining_text:
        start = remaining_text.find('Yes/No:')
        if start != -1:
            q_full = remaining_text.find('？', start)
            q_half = remaining_text.find('?', start)
            q_pos = q_full if q_full != -1 else q_half
            if q_pos != -1:
                yes_no_phrase = remaining_text[start + len('Yes/No:'):q_pos + 1]
                remaining_text = remaining_text[:start] + remaining_text[q_pos + 1:]

    remaining_text = sanitize_llm_text(remaining_text)
    if not remaining_text.strip():
        remaining_text = "Empty"

    return response, yes_no_phrase, choices, is_date_select, remaining_text

def write_decision(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    mode: str = "travel",
    language: Optional[str] = None,
) -> str:
    """
    チャット履歴から決定事項を抽出し、Redisに保存する
    Extract decisions from chat history and store them in Redis.
    
    LLMを使用して、会話の内容から「目的地」や「日程」などの確定事項を要約させます。
    Uses the LLM to summarize confirmed items (destination, dates, etc.).
    """
    lang = _normalize_language_code(language)
    default_message = _decision_default_message(lang)
    if lang == "en":
        message = (
            "If there are new or updated decisions, output only those items as JSON. "
            "Do not include uncertain or inferred information. No explanations or greetings."
        )
    else:
        message = (
            "これまでの決定事項に新しく追加・変更された内容があれば、その項目だけをJSONで出力してください。"
            "未確定や推測は書かず、説明や挨拶は一切不要です。"
        )
    
    try:
        previous_text = redis_client.get_decision(session_id) or ""
        previous_text = _enforce_decision_policy(previous_text, mode, lang)
        derived_patch = _derive_decision_patch_from_history(chat_history, previous_text)
        if derived_patch:
            previous_text = _apply_decision_patch(previous_text, derived_patch)
            previous_text = _enforce_decision_policy(previous_text, mode, lang)
        previous_lines = _split_decision_lines(previous_text)
        content = "\n".join(previous_lines) if previous_lines else default_message
        previous_label = "Previous decisions:" if lang == "en" else "以前の決定事項:"
        system_prompt = (
            PROMPTS.get(mode, PROMPTS["travel"])["decision_system"]
            + "\n"
            + _decision_language_instruction(lang)
            + "\n"
            + current_datetime_line(lang)
            + f"\n{previous_label}\n{content}\n"
        )
        messages = _build_messages(system_prompt, chat_history, message)
        response = _invoke_with_tool_retries(messages)
        response = sanitize_llm_text(response, max_length=MAX_DECISION_CHARS)
        if not output_is_safe(response):
            safe_text = "\n".join(previous_lines) if previous_lines else default_message
            safe_text = _enforce_decision_policy(safe_text, mode, lang)
            redis_client.save_decision(session_id, safe_text)
            return safe_text

        patch = _normalize_decision_patch(_extract_json_object(response))
        if patch is not None:
            merged = _apply_decision_patch(previous_text, patch)
        else:
            merged = _merge_decision_text(previous_text, response)

        merged = _enforce_decision_policy(merged, mode, lang)
        redis_client.save_decision(session_id, merged)
        return merged
    except Exception as e:
        logger.error(f"Error in write_decision: {e}")
        return _decision_error_message(lang)

def chat_with_llama(
    session_id: str,
    prompt: str,
    mode: str = "travel",
    language: Optional[str] = None,
) -> Tuple[Optional[str], str, Optional[str], Optional[List[str]], bool, str, bool]:
    """
    LLMとの対話を行うメイン関数
    Main entry point for LLM chat handling.
    
    1. 入力の安全性チェック
    2. チャット履歴の取得
    3. LLM応答の生成（run_qa_chain）
    4. 履歴と決定事項の保存
    1) Input safety check
    2) Load chat history
    3) Generate LLM response (run_qa_chain)
    4) Persist history and decisions
    """
    lang = _normalize_language_code(language or redis_client.get_user_language(session_id))
    result = guard.content_checker(prompt)
    if 'unsafe' in result:
        fallback_decision = redis_client.get_decision(session_id) or _decision_safety_message(lang)
        return None, fallback_decision, None, None, False, _decision_guard_blocked_message(lang), False
    
    chat_history = redis_client.get_chat_history(session_id)
    decision_text = redis_client.get_decision(session_id)
    decision_text = _enforce_decision_policy(decision_text, mode, lang)

    used_web_search, web_results = _run_web_search_if_needed(
        prompt,
        chat_history,
        mode=mode,
        language=lang,
    )
    web_context = _build_web_context(web_results, lang) if web_results else None

    response, yes_no_phrase, choices, is_date_select, remaining_text = run_qa_chain(
        prompt,
        chat_history,
        mode=mode,
        decision_text=decision_text,
        language=lang,
        web_context=web_context,
    )
    response = sanitize_llm_text(response)
    remaining_text = sanitize_llm_text(remaining_text)

    if web_results and remaining_text != "Empty":
        response = _append_sources(response, web_results, lang)
        remaining_text = _append_sources(remaining_text, web_results, lang)
    
    chat_history.append(("human", prompt))
    chat_history.append(("assistant", response))
    redis_client.save_chat_history(session_id, chat_history)
    current_plan = write_decision(session_id, chat_history, mode=mode, language=lang)
    
    return response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text, used_web_search


def stream_chat_with_llama(
    session_id: str,
    prompt: str,
    mode: str = "travel",
    language: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    LLM応答をストリーミングしつつ、終了時に決定事項まで更新する
    Stream LLM response chunks and persist chat/decision state at completion.
    """
    lang = _normalize_language_code(language or redis_client.get_user_language(session_id))
    result = guard.content_checker(prompt)
    if "unsafe" in result:
        fallback_decision = redis_client.get_decision(session_id) or _decision_safety_message(lang)
        payload = {
            "type": "final",
            "response": None,
            "current_plan": fallback_decision,
            "yes_no_phrase": None,
            "choices": None,
            "is_date_select": False,
            "remaining_text": _decision_guard_blocked_message(lang),
            "used_web_search": False,
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return

    chat_history = redis_client.get_chat_history(session_id)
    decision_text = redis_client.get_decision(session_id)
    decision_text = _enforce_decision_policy(decision_text, mode, lang)

    should_search, query = _needs_web_search(prompt, chat_history, mode=mode, language=lang)
    if should_search:
        yield f"data: {json.dumps({'type': 'search_start'}, ensure_ascii=False)}\n\n"
        web_results = brave_search.search_web(query)
        used_web_search = True
    else:
        web_results = []
        used_web_search = False
    yield f"data: {json.dumps({'type': 'meta', 'used_web_search': used_web_search}, ensure_ascii=False)}\n\n"

    system_prompt = (
        _language_instruction(lang)
        + "\n"
        + PROMPTS.get(mode, PROMPTS["travel"])["system"]
        + "\n"
        + current_datetime_line(lang)
    )
    if decision_text:
        if lang == "en":
            system_prompt += (
                "\n\n## Decisions so far\n"
                f"{decision_text}\n"
                "- Do not ask again about already decided items. Ask for the next missing info."
            )
        else:
            system_prompt += (
                "\n\n## 既に決定している情報\n"
                f"{decision_text}\n"
                "- 既に決定している内容は繰り返し質問せず、次に必要な情報を確認してください。"
            )
    web_context = _build_web_context(web_results, lang) if web_results else None
    if web_context:
        if lang == "en":
            system_prompt += (
                "\n\nUse the web context only for factual support and avoid fabricating facts.\n"
                "Do not mention internal reasoning.\n"
                f"{web_context}"
            )
        else:
            system_prompt += (
                "\n\nWeb検索コンテキストは事実確認にのみ使い、推測で事実を作らないでください。\n"
                "内部推論は出力しないでください。\n"
                f"{web_context}"
            )

    messages = _build_messages(system_prompt, chat_history, prompt)
    chunks: List[str] = []

    for delta in _invoke_with_tool_retries_stream(messages):
        if not delta:
            continue
        chunks.append(delta)
        payload = {"type": "delta", "content": delta}
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    raw_response = "".join(chunks)
    response, yes_no_phrase, choices, is_date_select, remaining_text = _parse_response_output(raw_response, lang)

    if web_results and remaining_text != "Empty":
        response = _append_sources(response, web_results, lang)
        remaining_text = _append_sources(remaining_text, web_results, lang)

    chat_history.append(("human", prompt))
    chat_history.append(("assistant", response))
    redis_client.save_chat_history(session_id, chat_history)
    current_plan = write_decision(session_id, chat_history, mode=mode, language=lang)

    payload = {
        "type": "final",
        "response": response,
        "current_plan": current_plan,
        "yes_no_phrase": yes_no_phrase,
        "choices": choices,
        "is_date_select": is_date_select,
        "remaining_text": remaining_text,
        "used_web_search": used_web_search,
    }
    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
