import re
from groq import Groq
from dotenv import load_dotenv
import os

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

# Groqクライアントの初期化
client = Groq(
    api_key = groq_api_key,  # 必要に応じてAPIキーを設定
)

# チャットコンプリーションの生成
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": """この問題の答えを導くためにpythonコードを生成して。pythonの標準ライブラリのみを使って。 問題「ある袋の中に赤いボールが5個、青いボールが3個、緑のボールが2個入っています。この袋からボールを1個ずつ無作為に取り出し、取り出したボールは元に戻さないとします。

最初の2回の取り出しで、赤いボールと青いボールがそれぞれ1個ずつ出る確率を求めてください。
最初の3回の取り出しで、少なくとも1個の緑のボールが出る確率を求めてください。」""",
        }
    ],
    model="llama3-70b-8192",
)

# 生成されたコンテンツの表示
generated_content = chat_completion.choices[0].message.content
print("Generated Content:")
print(generated_content)

# 正規表現を使ってPythonコード部分を抽出
code_match = re.search(r'```(.*?)```', generated_content, re.DOTALL)
if code_match:
    extracted_code = code_match.group(1).strip()
    
    # "python"文字列を削除
    if extracted_code.startswith("python"):
        extracted_code = extracted_code[len("python"):].strip()
    
    print("抽出されたコード:")
    print(extracted_code)
    
    # 生成されたコードの実行
    exec(extracted_code)

 
else:
    print("No Python code found in the generated content.")


