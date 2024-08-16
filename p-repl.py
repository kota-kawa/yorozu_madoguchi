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
            "content": """この問題の答えを導くためにpythonコードを生成して。pythonの標準ライブラリのみを使って。 問題「ある関数 f(x)=x3−3x2+2x
 があります。この関数の極値（最大値と最小値）を求めてください。また、関数の定積分 ∫0~2​f(x)dx
 を計算してください。」""",
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


