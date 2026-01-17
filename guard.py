from groq import Groq
from dotenv import load_dotenv
import os
import logging

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

# Groqクライアントの初期化
client = Groq(
    # This is the default and can be omitted
    api_key = groq_api_key,
)

def content_checker(prompt: str) -> str:
    """
    入力または出力テキストの安全性をチェックする
    
    Llama Guardモデルを使用して、コンテンツが安全かどうか（暴力、ヘイトスピーチなどを含まないか）を判定します。
    """
    # 短すぎるテキストはチェックをスキップ（誤検知防止や効率化のため）
    if len(prompt) <= 5:
        return "safe"
        
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="meta-llama/llama-guard-4-12b",
    )
    result = chat_completion.choices[0].message.content
    logging.getLogger(__name__).info("Content check result: %s", result)
    return result
