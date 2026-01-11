from groq import Groq
from dotenv import load_dotenv
import os

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

client = Groq(
    # This is the default and can be omitted
    api_key = groq_api_key,
)

def content_checker(prompt):
    if len(prompt) <= 5:
        return "safe"
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-guard-3-8b",
    )
    result = chat_completion.choices[0].message.content
    print(result)
    return result
