"""
llama_core の決定事項解析・正規化ロジック。
Decision parsing and normalization helpers for llama_core.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.llama_core_constants import (
    DECISION_ALLOWED_KEYS_BY_MODE,
    DECISION_BULLET_PREFIX_RE,
    DECISION_DATE_LIKE_RE,
    DECISION_DEFAULT_MESSAGE,
    DECISION_FLEX_KEY_LIMIT,
    DECISION_IGNORED_LINES,
    DECISION_KEY_EXTRA_ALIASES_BY_MODE,
    DECISION_KEY_LABELS_BY_MODE,
    DECISION_KV_SEPARATOR_RE,
    DECISION_MAX_ITEMS,
    DECISION_MEMO_KEYS_BY_LANGUAGE,
    DECISION_PATCH_ALLOWED_KEYS,
    DECISION_SLOT_QUESTION_PATTERNS,
    DECISION_SLOT_VALUE_PATTERNS,
    DECISION_UNKNOWN_ANSWER_RE,
    DECISION_YES_NO_TOKENS,
    MAX_DECISION_CHARS,
)
from backend.llama_core_language import (
    _decision_default_message,
    _memo_key_for_language,
    _normalize_language_code,
    sanitize_llm_text,
)

# 決定事項テキストの解析・正規化
# Decision text parsing and normalization
def _normalize_decision_line(line: str) -> str:
    """
    箇条書き記号や余分な空白を除去して1行を正規化する
    Normalize one decision line by removing bullets and collapsing spaces.
    """
    cleaned = DECISION_BULLET_PREFIX_RE.sub("", line.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _split_decision_lines(text: Optional[str]) -> List[str]:
    """
    決定事項テキストを有効な行リストへ分解する
    Split raw decision text into cleaned, non-ignored lines.
    """
    if not text:
        return []
    lines: List[str] = []
    for raw in str(text).splitlines():
        cleaned = _normalize_decision_line(raw)
        if not cleaned or cleaned in DECISION_IGNORED_LINES:
            continue
        lines.append(cleaned)
    return lines


def _parse_decision_key_value(line: str) -> Optional[Tuple[str, str]]:
    """
    `項目: 値` 形式の1行をキーと値に分解する
    Parse a `key: value` style line into key/value components.
    """
    parts = DECISION_KV_SEPARATOR_RE.split(line, maxsplit=1)
    if len(parts) != 2:
        return None
    key, value = parts[0].strip(), parts[1].strip()
    if not key or not value:
        return None
    return key, value


def _normalize_user_value(text: Optional[str]) -> str:
    """
    ユーザー入力値の制御文字と余分な空白を除去する
    Normalize user-provided text by stripping control chars and extra spaces.
    """
    if not text:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str(text))
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def _is_date_like(text: str) -> bool:
    """
    文字列が日付・時期を示す表現かどうかを判定する
    Check whether a text looks like a date or time-period expression.
    """
    if not text:
        return False
    if DECISION_DATE_LIKE_RE.search(text):
        return True
    lowered = text.lower()
    return any(
        token in text
        for token in ("今日", "明日", "明後日", "あさって", "今週", "来週", "再来週", "来月", "週末", "平日")
    ) or any(
        token in lowered
        for token in ("today", "tomorrow", "this week", "next week", "weekend", "weekday", "next month")
    )


def _extract_kv_map(decision_text: Optional[str]) -> Dict[str, str]:
    """
    決定事項テキストから `キー -> 値` マップを抽出する
    Extract a `key -> value` map from decision text items.
    """
    items, _, _ = _parse_decision_items(decision_text)
    result: Dict[str, str] = {}
    for item in items:
        if item["type"] == "kv":
            result[item["key"]] = item["value"]
    return result


def _extract_slot_value(slot: str, text: str) -> Optional[str]:
    """
    スロット別の正規表現でユーザー文から値候補を抽出する
    Extract a slot value candidate from user text via slot-specific patterns.
    """
    if not text:
        return None
    pattern = DECISION_SLOT_VALUE_PATTERNS.get(slot)
    if not pattern:
        return None
    match = pattern.search(text)
    if not match:
        return None
    value = _normalize_user_value(match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1))
    return value or None


def _is_valid_slot_value(slot: str, text: str) -> bool:
    """
    スロットに対して値が有効か（曖昧/YesNo除外など）を判定する
    Validate whether a candidate value is usable for the given slot.
    """
    cleaned = _normalize_user_value(text)
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered in DECISION_YES_NO_TOKENS:
        return False
    if DECISION_UNKNOWN_ANSWER_RE.search(cleaned):
        return False
    if slot == "日程":
        return _is_date_like(cleaned)
    return not _is_date_like(cleaned)


def _derive_decision_patch_from_history(
    chat_history: List[Tuple[str, str]],
    previous_text: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    直近の会話履歴から add/update 差分パッチを推定する
    Infer an add/update decision patch from recent chat history.
    """
    if not chat_history:
        return None

    existing = _extract_kv_map(previous_text)
    decided: Dict[str, str] = dict(existing)

    recent_history = chat_history[-20:]
    pending_slot: Optional[str] = None
    for role, content in recent_history:
        if role == "assistant":
            pending_slot = None
            for slot, pattern in DECISION_SLOT_QUESTION_PATTERNS.items():
                if pattern.search(content):
                    pending_slot = slot
                    break
            continue

        user_text = _normalize_user_value(content)
        if not user_text:
            pending_slot = None
            continue

        handled = False
        for slot in DECISION_SLOT_VALUE_PATTERNS:
            value = _extract_slot_value(slot, user_text)
            if value and _is_valid_slot_value(slot, value):
                decided[slot] = value
                handled = True
                pending_slot = None
        if handled:
            continue

        if pending_slot and _is_valid_slot_value(pending_slot, user_text):
            decided[pending_slot] = user_text
        pending_slot = None

    add: Dict[str, str] = {}
    update: Dict[str, str] = {}
    for key, value in decided.items():
        if key not in existing:
            add[key] = value
        elif existing.get(key) != value:
            update[key] = value

    if not add and not update:
        return None
    return {"add": add, "update": update, "remove": []}


# JSON抽出とパッチ正規化
# JSON extraction and patch normalization
def _strip_code_fences(text: str) -> str:
    """
    ``` で囲まれたコードフェンスを除去する
    Remove surrounding triple-backtick code fences from text.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_json_object(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    文字列からJSONオブジェクトを抽出して返す
    Parse and return a JSON object from free-form response text.
    """
    if not text:
        return None
    cleaned = _strip_code_fences(str(text))
    cleaned = cleaned.strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                obj = json.loads(snippet)
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
    return None


def _normalize_decision_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    LLMが返したパッチJSONを許可形式へ正規化する
    Normalize an LLM patch object into the allowed patch schema.
    """
    if not patch or not isinstance(patch, dict):
        return None
    filtered = {k: v for k, v in patch.items() if k in DECISION_PATCH_ALLOWED_KEYS}

    def normalize_map(value: Any) -> Dict[str, str]:
        """
        add/update 用のマップを文字列キー/値へ整形する
        Normalize add/update maps into clean string key/value pairs.
        """
        if not isinstance(value, dict):
            return {}
        normalized: Dict[str, str] = {}
        for key, val in value.items():
            k = str(key).strip()
            v = str(val).strip()
            if k and v:
                normalized[k] = v
        return normalized

    def normalize_remove(value: Any) -> List[str]:
        """
        remove 指定をキー名リストへ正規化する
        Normalize remove targets into a list of non-empty keys.
        """
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = [value]
        else:
            return []
        result: List[str] = []
        for item in items:
            key = str(item).strip()
            if key:
                result.append(key)
        return result

    add = normalize_map(filtered.get("add"))
    update = normalize_map(filtered.get("update"))
    remove = normalize_remove(filtered.get("remove"))

    if not add and not update and not remove:
        return {}
    return {"add": add, "update": update, "remove": remove}


# 決定事項のアイテム化とキー正規化
# Decision itemization and key normalization
def _parse_decision_items(text: Optional[str]) -> Tuple[List[Dict[str, str]], Dict[str, int], set]:
    """
    決定事項テキストを kv/plain の内部アイテムへ変換する
    Convert decision text into internal `kv`/`plain` item structures.
    """
    items: List[Dict[str, str]] = []
    key_index: Dict[str, int] = {}
    plain_set: set = set()
    for line in _split_decision_lines(text):
        kv = _parse_decision_key_value(line)
        if kv:
            key, value = kv
            item = {"type": "kv", "key": key, "value": value}
            if key in key_index:
                items[key_index[key]] = item
            else:
                key_index[key] = len(items)
                items.append(item)
        else:
            if line not in plain_set:
                items.append({"type": "plain", "value": line})
                plain_set.add(line)
    return items, key_index, plain_set


def _normalize_key_alias(key: str) -> str:
    """
    キー比較用に記号・区切り・大文字小文字差を吸収する
    Normalize key aliases by removing separators and case differences.
    """
    cleaned = key.strip().lower()
    cleaned = re.sub(r"[\s_\-./]+", "", cleaned)
    cleaned = re.sub(r"[：:]", "", cleaned)
    return cleaned


_DECISION_ALIAS_CACHE: Dict[str, Dict[str, str]] = {}


def _get_decision_alias_lookup(mode: str) -> Dict[str, str]:
    """
    モード別の別名→正規キー変換表を構築・キャッシュする
    Build and cache alias-to-canonical-key lookup for each mode.
    """
    if mode in _DECISION_ALIAS_CACHE:
        return _DECISION_ALIAS_CACHE[mode]

    lookup: Dict[str, str] = {}
    labels_by_lang = DECISION_KEY_LABELS_BY_MODE.get(mode, {})
    for labels in labels_by_lang.values():
        for canonical, label in labels.items():
            lookup[_normalize_key_alias(label)] = canonical
    extras = DECISION_KEY_EXTRA_ALIASES_BY_MODE.get(mode, {})
    for canonical, aliases in extras.items():
        for alias in aliases:
            lookup[_normalize_key_alias(alias)] = canonical

    _DECISION_ALIAS_CACHE[mode] = lookup
    return lookup


def _canonicalize_decision_key(key: str, mode: str) -> Optional[str]:
    """
    入力キー名をモード定義の正規キーへ変換する
    Convert an input key label into the mode-specific canonical key.
    """
    if not key:
        return None
    lookup = _get_decision_alias_lookup(mode)
    return lookup.get(_normalize_key_alias(key))


def _label_for_canonical_key(mode: str, language: str, canonical: str) -> str:
    """
    正規キーに対応する表示ラベル（言語別）を返す
    Resolve the display label for a canonical key in the target language.
    """
    labels_by_lang = DECISION_KEY_LABELS_BY_MODE.get(mode, {})
    lang = _normalize_language_code(language)
    labels = labels_by_lang.get(lang) or labels_by_lang.get("ja") or {}
    return labels.get(canonical, canonical)


def _is_memo_key(key: str) -> bool:
    """
    キーがメモ項目（自由記述欄）かどうかを判定する
    Check whether a key represents the memo/free-notes field.
    """
    normalized = _normalize_key_alias(key)
    for memo_key in DECISION_MEMO_KEYS_BY_LANGUAGE.values():
        if normalized == _normalize_key_alias(memo_key):
            return True
    return False


def _build_memo_value(entries: List[str]) -> str:
    """
    メモ候補を整形して1つの連結文字列にまとめる
    Normalize memo entries and combine them into one memo string.
    """
    normalized: List[str] = []
    for entry in entries:
        cleaned = _normalize_decision_line(entry)
        if cleaned:
            normalized.append(cleaned)
    return " / ".join(normalized)


def _enforce_decision_policy(text: Optional[str], mode: str, language: str) -> str:
    """
    モード制約に沿って決定事項を整形・上限調整して返す
    Enforce mode policy on decisions (allowed keys, limits, memo handling).
    """
    items, _, _ = _parse_decision_items(text)
    if not items:
        return _decision_default_message(language)

    allowed_keys = set(DECISION_ALLOWED_KEYS_BY_MODE.get(mode, []))
    memo_entries: List[str] = []
    ordered_items: List[Dict[str, str]] = []
    fixed_index: Dict[str, int] = {}
    flex_index: Dict[str, int] = {}

    for item in items:
        if item["type"] == "kv":
            key = item["key"].strip()
            value = item["value"].strip()
            if _is_memo_key(key):
                if value:
                    memo_entries.append(value)
                continue
            canonical = _canonicalize_decision_key(key, mode)
            if canonical and canonical in allowed_keys:
                if canonical in fixed_index:
                    ordered_items[fixed_index[canonical]]["value"] = value
                else:
                    fixed_index[canonical] = len(ordered_items)
                    ordered_items.append({"kind": "fixed", "canonical": canonical, "value": value})
                continue

            if key in flex_index:
                ordered_items[flex_index[key]]["value"] = value
            else:
                flex_index[key] = len(ordered_items)
                ordered_items.append({"kind": "flex", "key": key, "value": value})
        else:
            if item.get("value"):
                memo_entries.append(item["value"])

    flex_limit = max(0, DECISION_FLEX_KEY_LIMIT)
    if flex_limit >= 0:
        flex_indices = [i for i, item in enumerate(ordered_items) if item["kind"] == "flex"]
        overflow = flex_indices[flex_limit:]
        for idx in overflow:
            removed = ordered_items[idx]
            memo_entries.append(f"{removed['key']}：{removed['value']}")
        for idx in reversed(overflow):
            del ordered_items[idx]

    if DECISION_MAX_ITEMS > 0:
        def total_items() -> int:
            """
            出力予定の総項目数を数える
            Count total output items including memo when present.
            """
            return len(ordered_items) + (1 if memo_entries else 0)

        while total_items() > DECISION_MAX_ITEMS and ordered_items:
            idx = None
            for i in range(len(ordered_items) - 1, -1, -1):
                if ordered_items[i]["kind"] == "flex":
                    idx = i
                    break
            if idx is None:
                idx = len(ordered_items) - 1
            removed = ordered_items.pop(idx)
            if removed["kind"] == "fixed":
                key_label = _label_for_canonical_key(mode, language, removed["canonical"])
                memo_entries.append(f"{key_label}：{removed['value']}")
            else:
                memo_entries.append(f"{removed['key']}：{removed['value']}")

    final_items: List[Dict[str, str]] = []
    for item in ordered_items:
        if item["kind"] == "fixed":
            key_label = _label_for_canonical_key(mode, language, item["canonical"])
        else:
            key_label = item["key"]
        final_items.append({"type": "kv", "key": key_label, "value": item["value"]})
    memo_value = _build_memo_value(memo_entries)
    if memo_value:
        final_items.append({"type": "kv", "key": _memo_key_for_language(language), "value": memo_value})

    if not final_items:
        return _decision_default_message(language)
    return sanitize_llm_text(_decision_items_to_text(final_items), max_length=MAX_DECISION_CHARS)


def _decision_items_to_text(items: List[Dict[str, str]]) -> str:
    """
    内部アイテム配列を表示用テキストへ変換する
    Convert internal decision items into user-facing text lines.
    """
    if not items:
        return DECISION_DEFAULT_MESSAGE
    lines: List[str] = []
    for item in items:
        if item["type"] == "kv":
            lines.append(f'{item["key"]}：{item["value"]}')
        else:
            lines.append(item["value"])
    return "\n".join(lines)


def _apply_decision_patch(prev_text: Optional[str], patch: Dict[str, Any]) -> str:
    """
    既存決定事項へ add/update/remove パッチを適用する
    Apply add/update/remove patch operations to existing decisions.
    """
    add = patch.get("add") or {}
    update = patch.get("update") or {}
    remove_list = patch.get("remove") or []

    if not add and not update and not remove_list:
        existing = "\n".join(_split_decision_lines(prev_text))
        return existing if existing else DECISION_DEFAULT_MESSAGE

    items, key_index, plain_set = _parse_decision_items(prev_text)

    remove_set = {key for key in remove_list if key}
    if remove_set:
        items = [
            item
            for item in items
            if not (item["type"] == "kv" and item["key"] in remove_set)
        ]
        key_index = {item["key"]: idx for idx, item in enumerate(items) if item["type"] == "kv"}

    def apply_map(value_map: Dict[str, str]) -> None:
        """
        マップ項目を既存リストへ上書きまたは追加する
        Upsert key/value entries into the current decision item list.
        """
        for key, value in value_map.items():
            if key in remove_set:
                continue
            item = {"type": "kv", "key": key, "value": value}
            if key in key_index:
                items[key_index[key]] = item
            else:
                key_index[key] = len(items)
                items.append(item)

    apply_map(add)
    apply_map(update)

    merged = _decision_items_to_text(items)
    return sanitize_llm_text(merged, max_length=MAX_DECISION_CHARS)


def _merge_decision_text(prev_text: Optional[str], new_text: Optional[str]) -> str:
    """
    新しい決定事項テキストを既存内容に重複なくマージする
    Merge new decision lines into previous text without duplicating items.
    """
    prev_lines = _split_decision_lines(prev_text)
    new_lines = _split_decision_lines(new_text)

    if not prev_lines and not new_lines:
        return DECISION_DEFAULT_MESSAGE
    if not new_lines:
        return "\n".join(prev_lines)

    result_lines = list(prev_lines)
    key_index: Dict[str, int] = {}
    for idx, line in enumerate(result_lines):
        kv = _parse_decision_key_value(line)
        if kv:
            key_index[kv[0]] = idx

    seen_plain = {line for line in result_lines if not _parse_decision_key_value(line)}

    for line in new_lines:
        kv = _parse_decision_key_value(line)
        if kv:
            key = kv[0]
            if key in key_index:
                result_lines[key_index[key]] = line
            else:
                key_index[key] = len(result_lines)
                result_lines.append(line)
        else:
            if line not in seen_plain:
                result_lines.append(line)
                seen_plain.add(line)

    merged = "\n".join(result_lines)
    return sanitize_llm_text(merged, max_length=MAX_DECISION_CHARS)
