import logging
import os
import guard
import redis_client
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
import warnings

# ロギング設定
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

groq_api_key = os.getenv("GROQ_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY が設定されていないか、無効です。")

# プロンプトの定義
PROMPTS = {
    "travel": {
        "system": """
        # 命令書
        あなたは、優秀で親切な旅行計画のプロフェッショナル・コンシェルジュです。
        ユーザー一人ひとりに寄り添い、最高の旅行プランを作成するのを手伝ってください。

        ## あなたの役割
        - ユーザーとの対話を通じて、旅行の必須情報（目的地、日程など）と要望を引き出します。
        - 最適な旅行プランを提案し、丁寧で共感的な対話スタイルを保ってください。

        ## 実行ステップ
        1. 基本情報（目的地、出発地、日程）を一つずつ確認。
        2. 好みや要望をヒアリング。
        3. 具体的な提案と理由の提示。
        4. プランの要約と確定。

        # 制約条件
        - 言語: 日本語。
        - 応答の長さ: 200文字以内目安。
        - 質問: 一度のメッセージで一つの質問。
        - Yes/No形式: ユーザーに決めてほしい場合は「Yes/No:〇〇にしますか？」という形式を使用。
        """,
        "decision_system": "あなたは渡されたチャット履歴から、現在決定されている旅行項目（目的地、出発地、日程など）を抽出するアシスタントです。日本語で回答してください。"
    },
    "reply": {
        "system": """
        あなたはメッセージへの返答を考えるアシスタントです。日本語で回答してください。
        - 質問への回答は、簡潔に分かりやすくまとめて下さい。
        - 親しみやすさが大切です。
        - ユーザーに対して「はい/いいえ」で回答してもらいたい場合には、「Yes/No:〇〇にしますか？」と出力してください。
        """,
        "decision_system": "あなたは渡された文章から決定されている項目（返信内容の方針など）を抽出するアシスタントです。日本語で回答してください。"
    },
    "fitness": {
        "system": """
        # 命令書
        あなたは、筋トレ・フィットネス（健康全般）のアシスタントです。
        ユーザーの目的・体力・生活習慣に合わせて、安全で実践的な提案を行ってください。

        ## あなたの役割
        - 目標（筋肥大、減量、姿勢改善など）や経験、頻度、設備、制限（怪我・疾患）を確認。
        - 具体的で続けやすいメニューや習慣を提案し、丁寧で共感的な対話を保つ。
        - 医療判断は行わず、痛みや持病がある場合は医師相談を促す。

        ## 実行ステップ
        1. 目的と現状（経験・頻度・環境）を確認。
        2. 制約（時間、怪我、器具）を確認。
        3. 具体的な提案と理由を提示。
        4. 次回アクションの要約と確認。

        # 制約条件
        - 言語: 日本語。
        - 応答の長さ: 200文字以内目安。
        - 質問: 一度のメッセージで一つの質問。
        - Yes/No形式: ユーザーに決めてほしい場合は「Yes/No:〇〇にしますか？」という形式を使用。
        """,
        "decision_system": "あなたは渡されたチャット履歴から、現在決定されている筋トレ・健康の項目（目標、頻度、制約、食事方針など）を抽出するアシスタントです。日本語で回答してください。"
    }
}

def run_qa_chain(message, chat_history, mode="travel"):
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
    
    system_prompt = PROMPTS.get(mode, PROMPTS["travel"])["system"]
    
    prompt_messages = [("system", system_prompt)] + chat_history + [("human", "{input}")]
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    chain = prompt | groq_chat | StrOutputParser()
    response = chain.invoke({"input": message})

    # Yes/No形式の抽出ロジック
    yes_no_phrase, remaining_text = None, response
    if "Yes/No" in response:
        start = response.find('Yes/No:')
        if start != -1:
            q_full = response.find('？', start)
            q_half = response.find('?', start)
            q_pos = q_full if q_full != -1 else q_half
            
            if q_pos != -1:
                yes_no_phrase = response[start + len('Yes/No:'):q_pos + 1]
                remaining_text = response[:start] + response[q_pos + 1:]
                if not remaining_text.strip():
                    remaining_text = "Empty"

    return response, yes_no_phrase, remaining_text

def write_decision(session_id, chat_history, mode="travel"):
    default_message = "決定している項目がありません。"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"
    
    try:
        content = redis_client.get_decision(session_id) or default_message
        groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
        
        system_prompt = PROMPTS.get(mode, PROMPTS["travel"])["decision_system"] + f"\n以前の決定事項:\n{content}\n"
        
        prompt_messages = [("system", system_prompt)] + chat_history + [("human", "{input}")]
        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        
        chain = prompt | groq_chat | StrOutputParser()
        response = chain.invoke({"input": message})
        
        redis_client.save_decision(session_id, response)
        return response
    except Exception as e:
        logger.error(f"Error in write_decision: {e}")
        return "決定事項の更新中にエラーが発生しました。"

def chat_with_llama(session_id, prompt, mode="travel"):
    result = guard.content_checker(prompt)
    if 'unsafe' in result:
        return None, redis_client.get_decision(session_id) or "安全性の問題で表示できません", None, "それには答えられません"
    
    chat_history = redis_client.get_chat_history(session_id)
    chat_history.append(("human", prompt))
    
    response, yes_no_phrase, remaining_text = run_qa_chain(prompt, chat_history, mode=mode)
    
    chat_history.append(("assistant", response))
    redis_client.save_chat_history(session_id, chat_history)
    current_plan = write_decision(session_id, chat_history, mode=mode)
    
    return response, current_plan, yes_no_phrase, remaining_text
