"""
Brave Search API クライアント。
Brave Search API client.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend import limit_manager

logger = logging.getLogger(__name__)

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
MAX_RESULT_COUNT = 20


def is_configured() -> bool:
    """BRAVE_SEARCH_API が設定されているかを返す / Return whether BRAVE_SEARCH_API is configured."""
    return bool(os.getenv("BRAVE_SEARCH_API", "").strip())


def search_web(query: str, count: int | None = None) -> List[Dict[str, str]]:
    """
    Brave Search API でWeb検索を行い、整形済み結果を返す。
    Perform a Brave web search and return normalized results.
    """
    normalized_query = (query or "").strip()
    token = os.getenv("BRAVE_SEARCH_API", "").strip()
    if not token or not normalized_query:
        return []

    allowed, current_count, limit, error_code = limit_manager.check_and_increment_web_search_limit()
    if not allowed:
        if error_code:
            logger.warning(
                "Skipping Brave search because monthly-limit check failed: %s",
                error_code,
            )
        else:
            logger.info(
                "Skipping Brave search because monthly limit reached: %s/%s",
                current_count,
                limit,
            )
        return []

    result_count = _resolve_result_count(count)
    timeout_seconds = _resolve_timeout_seconds()
    params = urlencode({"q": normalized_query, "count": str(result_count)})
    url = f"{BRAVE_SEARCH_ENDPOINT}?{params}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": token,
            "User-Agent": "yorozu-madoguchi/1.0",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            error_body = ""
        logger.warning(
            "Brave search failed with status=%s body=%s",
            e.code,
            error_body[:300],
        )
        return []
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning("Brave search request failed: %s", e)
        return []
    except Exception as e:
        logger.error("Unexpected Brave search error: %s", e)
        return []

    return _normalize_results(payload)


def _resolve_result_count(count: int | None) -> int:
    """検索件数を安全な範囲で決定する / Resolve count within API-safe bounds."""
    if count is None:
        raw_default = os.getenv("BRAVE_SEARCH_RESULT_COUNT", "5").strip()
        try:
            count = int(raw_default)
        except ValueError:
            count = 5
    return max(1, min(MAX_RESULT_COUNT, count))


def _resolve_timeout_seconds() -> float:
    """タイムアウト秒数を取得する / Resolve request timeout in seconds."""
    raw_timeout = os.getenv("BRAVE_SEARCH_TIMEOUT_SECONDS", "8").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError:
        timeout = 8.0
    return max(1.0, timeout)


def _normalize_results(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    APIレスポンスを `title/url/description` 形式へ正規化する。
    Normalize API payload into `title/url/description` entries.
    """
    web_payload = payload.get("web")
    if not isinstance(web_payload, dict):
        return []

    results = web_payload.get("results")
    if not isinstance(results, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        normalized.append(
            {
                "title": str(item.get("title", "")).strip(),
                "url": url,
                "description": str(item.get("description", "")).strip(),
            }
        )
    return normalized
