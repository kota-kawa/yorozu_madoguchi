from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
import guard
import redis_client

import warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")


# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

#　旅行計画の相談チャットのプロンプト
def run_qa_chain(message, chat_history):
    yes_no_phrase, remaining_text = None, None
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")

    # システムプロンプトを定義する Yes/No形式の質問の頻度は2回に1回まで!絶対!
    system_prompt = (
        "あなたはメッセージへの返答を考えるアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "質問への回答は、できるだけ簡潔に分かりやすくまとめて下さい。"
        "近い間柄ならば、丁寧になりすぎない（ですます調は年齢が近い人には使わない）親しみやすさが大切。"
        "\n\n"
        "もしも会話の状況を見て、ユーザーに対して「はい/いいえ」で回答してもらいたい場合には、「Yes/No:〇〇にしますか？」と全く同じ形式で出力して。"
    )
    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
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
    #　チャット履歴とプロンプトを元に、回答を生成
    response = chain.invoke({"input": message})

    # Yes/No形式の文章の整形
    def extract_and_split_text(text):
        # 関数を使って抽出
        print("Yes/No!!!")
        # "Yes/No:"と"？"の位置を見つける
        yes_no_start = text.find('Yes/No:')
        if yes_no_start == -1:
            return text, None, None  # "Yes/No:"が見つからない場合は全体を返す
        #?が全角の場合
        question_full = text.find('？', yes_no_start)
        #?が半角の場合
        question_half = text.find('?', yes_no_start)
            # 有効な位置を選択
        if question_full == -1 and question_half == -1:
            return text, None, None  # 両方の"？"が見つからない場合は全体を返す
        print("Yes/No???")
        # "Yes/No:"部分の抽出
        yes_no_phrase = text[yes_no_start + len('Yes/No:'):question_full + 1]

        # "Yes/No:"部分を除いた残りの文章
        remaining_text = text[:yes_no_start] + text[question_full + 1:]

        return response, yes_no_phrase, remaining_text

    # Yes/No形式の質問ではなかった場合
    if "Yes/No" in response:
        # 関数を使って抽出
        response, yes_no_phrase, remaining_text = extract_and_split_text(response)
        # remaining_textが空だったとき
        if remaining_text == None or remaining_text == "":
            # remaining_textが空または空白文字のみの場合の処理
            print("残りのテキストがありません。デフォルト値を設定します。")
            remaining_text = "Empty"
    else:
        remaining_text = response

    return response, yes_no_phrase, remaining_text

#　決定している事項をRedisに書き込む
def write_decision(session_id, chat_history):
    default_message = "決定している項目がありません。"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"
    
    # Redisから読み込む
    content = redis_client.get_decision(session_id)
    
    # ファイルが空の場合は、デフォルトメッセージを書き込む
    if not content.strip():
        content = default_message

    # Groqのチャットモデルを初期化する llama3-70b-8192
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
    # システムプロンプトを定義する
    system_prompt = (
        "あなたは、渡された文章から決定されている項目を抽出するアシスタントです。あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        f"\n\n前回の決定事項:\n{content}\n\n"
    )
    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
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
    # 決定事項をRedisに保存する
    redis_client.save_decision(session_id, response)

    return response

# メインのプログラムにLLMの結果を返す
def chat_with_llama(session_id, prompt):
    result = guard.content_checker(prompt)
    #　悪意のあるプロンプトだった場合
    if 'unsafe' in result:
        remaining_text = "それには答えられません"
        yes_no_phrase, response = None, None

        content = redis_client.get_decision(session_id)
        current_plan = content
    #　通常の返答
    else:
        # チャット履歴を読み込む
        chat_history = redis_client.get_chat_history(session_id)
        # 入力メッセージを追加してQAチェーンを実行する
        message = prompt
        chat_history.append(("human", message))
        
        # RAG用のretriever引数を削除
        response, yes_no_phrase, remaining_text = run_qa_chain(message, chat_history)
        
        chat_history.append(("assistant", response))
        # チャット履歴を保存する
        redis_client.save_chat_history(session_id, chat_history)
        # 決定している項目を保存する
        # メモリ上のhistoryを使う
        current_plan = write_decision(session_id, chat_history)
        print("回答：", response)

    return response, current_plan, yes_no_phrase, remaining_text
