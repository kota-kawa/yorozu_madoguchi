from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
import re
import make_csv

import warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")


# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

def execute_reservation(response):
    # 正規表現を使ってPythonコード部分を抽出
    code_match = re.search(r'```(.*?)```', response, re.DOTALL)
    if code_match:
        extracted_code = code_match.group(1).strip()
        # "python"文字列を削除
        if extracted_code.startswith("python"):
            extracted_code = extracted_code[len("python"):].strip()
        print("抽出されたコード:")
        print(extracted_code)
        # 生成されたコードの実行
        exec(extracted_code)

def complete_plan():
    file_path = "decision.txt"
    message = "この決定している項目からコードを生成してください。"
    # ファイルを読み込む
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
    # システムプロンプトを定義する
    system_prompt = (
        "あなたは、渡された文章からプログラムを作成するアシスタントです。あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "以下の形式で目的地やタクシー会社のような部分を、適切な要素に変更してpythonのプログラムを生成して。空白の項目があっても構わないが、空白ならNoneを挿入して。"
        "目的地やタクシー会社のような部分に挿入する要素はテキスト形式にして。リスト形式などは一切使わずに。もしも複数の要素があった場合には、「、」で区切って単語をつなげて。"
        "ここで示されている要素以外は一切作成しないで。"
        f"{text}\n"
        "\n\n"
        """
        import make_csv

        destinations = 目的地
        departure = 出発地
        hotel = ホテル
        airlines = 航空会社
        railway = 鉄道会社
        taxi = タクシー会社
        start = 滞在開始日
        end = 滞在終了日
        set_reservation = make_csv.write_reservation_plan(destinations, departure, hotel, airlines, railway, taxi, start, end)
        """
    )
    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] +  [
        ("human", "{input}")
    ]
    # プロンプトテンプレートを作成する
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    # チェーンを構築する
    chain = (
        prompt
        | groq_chat
        | StrOutputParser()
    )
    response = chain.invoke({"input": message})
    execute_reservation(response)
    return 'Complete!'