from dotenv import load_dotenv
import json
import logging
import os
from typing import Any, Dict, Optional

from groq_openai_client import get_groq_client

# .envファイルの読み込み
load_dotenv()

client = get_groq_client()
GROQ_GUARD_MODEL_NAME = os.getenv("GROQ_GUARD_MODEL_NAME", "openai/gpt-oss-safeguard-20b")

DEFAULT_GUARD_POLICY = """
You are a safety classifier. Determine whether the input should be blocked.
Classify as "unsafe" if it contains or requests:
- Violence, threats, or weapon instructions
- Hate/harassment targeting protected groups
- Self-harm or suicide
- Sexual content involving minors or non-consensual acts
- Instructions for illegal wrongdoing (fraud, theft, evasion)
- Malware, hacking, or cyber abuse
Otherwise classify as "safe".

Return JSON only, exactly with these keys:
{"verdict": "safe|unsafe", "categories": ["..."], "reason": "short"}
"""


def _load_guard_policy() -> str:
    policy_path = os.getenv("GROQ_GUARD_POLICY_PATH")
    if policy_path:
        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                policy = f.read().strip()
            if policy:
                return policy
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Failed to read GROQ_GUARD_POLICY_PATH=%s: %s", policy_path, e
            )
    inline = os.getenv("GROQ_GUARD_POLICY")
    if inline:
        return inline.strip()
    return DEFAULT_GUARD_POLICY.strip()


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None
    return None


def _normalize_guard_result(raw: str) -> str:
    parsed = _try_parse_json(raw)
    if isinstance(parsed, dict):
        verdict = str(parsed.get("verdict", "")).strip().lower()
        if verdict in ("safe", "unsafe"):
            return verdict
    lowered = (raw or "").lower()
    if "unsafe" in lowered:
        return "unsafe"
    if "safe" in lowered:
        return "safe"
    return "unsafe"


def content_checker(prompt: str) -> str:
    """
    入力または出力テキストの安全性をチェックする

    Safety GPT OSS 20B を使用して、安全かどうかを判定します。
    """
    # 短すぎるテキストはチェックをスキップ（誤検知防止や効率化のため）
    if len(prompt) <= 5:
        return "safe"

    policy = _load_guard_policy()
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": policy,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model=GROQ_GUARD_MODEL_NAME,
            temperature=0,
        )
    except Exception as e:
        logging.getLogger(__name__).error("Content check failed: %s", e)
        return "unsafe"

    raw = chat_completion.choices[0].message.content or ""
    result = _normalize_guard_result(raw)
    logging.getLogger(__name__).info("Content check result: %s", result)
    return result
