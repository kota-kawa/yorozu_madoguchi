"""
Groq/OpenAI互換クライアントの生成と再利用。
Factory for a Groq/OpenAI-compatible client with caching.
"""

import os
from typing import Optional

import openai

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_client: Optional[openai.OpenAI] = None


def get_groq_client() -> openai.OpenAI:
    """
    Groqクライアントを生成・再利用する
    Create and reuse a singleton Groq client.
    """
    global _client
    if _client is None:
        # 初回のみ環境変数を読み込み、クライアントを生成
        # Initialize the client only once
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY が設定されていないか、無効です。")
        base_url = os.environ.get("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL)
        _client = openai.OpenAI(base_url=base_url, api_key=api_key)
    return _client
