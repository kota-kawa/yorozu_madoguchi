import logging
import os
import guard
import redis_client
import re
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
import warnings

# ロギング設定
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

groq_api_key = os.getenv("GROQ_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "2000"))
OUTPUT_GUARD_ENABLED = os.getenv("OUTPUT_GUARD_ENABLED", "true").lower() in ("1", "true", "yes")

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
        - 質問: 一度のメッセージで一つの質問。
        - Yes/No形式: ユーザーに決めてほしい場合は「Yes/No:〇〇にしますか？」という形式を使用。
        - 選択肢形式: ユーザーに複数の選択肢から選んでほしい場合は「Select: [選択肢1, 選択肢2, ..., その他]」という形式を使用（※必ず半角括弧 [] と半角カンマを使用、最大6つ、最後に「その他」を含める）。
        - 日付選択形式: ユーザーに日付を選択してほしい場合は「DateSelect: true」という形式を使用。
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている旅行項目（目的地、出発地、日程など）を抽出し、簡潔な箇条書きリストを作成するアシスタントです。
        - 説明や挨拶は不要です。
        - 「項目名：内容」の形式で出力してください。
        - 各項目は改行で区切ってください。
        """
    },
    "reply": {
        "system": """
        # 命令書
        あなたは、親しみやすく丁寧なメッセージ返答アシスタントです。
        ユーザーからのメッセージに対し、簡潔かつ分かりやすい日本語で応答してください。

        ## あなたの役割
        - ユーザーからの問いかけに対して、親しみやすく回答する。
        - 必要に応じてユーザーの意向を確認し、決定を促す。

        # 制約条件
        - 言語: 日本語。
        - トーン: 親しみやすく、丁寧な「です・ます」調。
        - 応答の長さ: 200文字以内目安。
        - 質問: 一度のメッセージで一つの質問。

        # 特殊形式（ユーザーのアクションを促す場合に使用）
        - Yes/No形式: ユーザーに決めてほしい場合は「Yes/No:〇〇にしますか？」という形式を使用。
        - 選択肢形式: ユーザーに複数の選択肢から選んでほしい場合は「Select: [選択肢1, 選択肢2, ..., その他]」という形式を使用（※必ず半角括弧 [] と半角カンマを使用、最大6つ、最後に「その他」を含める）。
        - 日付選択形式: ユーザーに日付を選択してほしい場合は「DateSelect: true」という形式を使用。
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている項目（返信内容の方針など）を抽出し、簡潔な箇条書きリストを作成するアシスタントです。
        - 説明や挨拶は不要です。
        - 「項目名：内容」の形式で出力してください。
        - 各項目は改行で区切ってください。
        """
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
        - 選択肢形式: ユーザーに複数の選択肢から選んでほしい場合は「Select: [選択肢1, 選択肢2, ..., その他]」という形式を使用（※必ず半角括弧 [] と半角カンマを使用、最大6つ、最後に「その他」を含める）。
        - 日付選択形式: ユーザーに日付を選択してほしい場合は「DateSelect: true」という形式を使用。
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている筋トレ・健康の項目（目標、頻度、制約、食事方針など）を抽出し、簡潔な箇条書きリストを作成するアシスタントです。
        - 説明や挨拶は不要です。
        - 「項目名：内容」の形式で出力してください。
        - 各項目は改行で区切ってください。
        """
    }
}

def current_datetime_jp_line():
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    now = datetime.now()
    weekday = weekday_map[now.weekday()]
    return f"現在日時: {now.year}年{now.month}月{now.day}日（{weekday}） {now.hour:02d}:{now.minute:02d}"


def sanitize_llm_text(text, max_length=MAX_OUTPUT_CHARS):
    if text is None:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str(text))
    cleaned = cleaned.strip()
    if max_length and len(cleaned) > max_length:
        cleaned = f"{cleaned[:max_length]}..."
    return cleaned


def output_is_safe(text):
    if not OUTPUT_GUARD_ENABLED or not text:
        return True
    try:
        result = guard.content_checker(text)
        return "unsafe" not in result
    except Exception as e:
        logger.error(f"Output safety check failed: {e}")
        return False

def run_qa_chain(message, chat_history, mode="travel"):
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="openai/gpt-oss-20b")
    
    system_prompt = PROMPTS.get(mode, PROMPTS["travel"])["system"] + "\n" + current_datetime_jp_line()
    
    prompt_messages = [("system", system_prompt)] + chat_history + [("human", "{input}")]
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    chain = prompt | groq_chat | StrOutputParser()
    response = chain.invoke({"input": message})
    response = sanitize_llm_text(response)

    if not output_is_safe(response):
        safe_message = "安全性の理由で表示できません。"
        return safe_message, None, None, False, safe_message

    # Yes/No形式の抽出ロジック
    yes_no_phrase = None
    choices = None
    is_date_select = False
    remaining_text = response

    # Select: [...] 形式の抽出 (正規表現)
    select_match = re.search(r'Select:\s*\[(.*?)\]', response, re.DOTALL)
    if select_match:
        choices_str = select_match.group(1)
        # カンマ区切りでリスト化し、引用符などを除去
        choices = [c.strip().strip('"\'') for c in choices_str.split(',') if c.strip()]
        # Select部分を除去してremaining_textを更新
        remaining_text = remaining_text.replace(select_match.group(0), "").strip()

    # DateSelect: true 形式の抽出
    date_match = re.search(r'DateSelect:\s*true', remaining_text, re.IGNORECASE)
    if date_match:
        is_date_select = True
        remaining_text = remaining_text.replace(date_match.group(0), "").strip()

    # Yes/No形式の抽出 (Selectが見つからなかった場合、または共存する場合)
    if not choices and not is_date_select and "Yes/No" in remaining_text:
        start = remaining_text.find('Yes/No:')
        if start != -1:
            q_full = remaining_text.find('？', start)
            q_half = remaining_text.find('?', start)
            q_pos = q_full if q_full != -1 else q_half
            
            if q_pos != -1:
                yes_no_phrase = remaining_text[start + len('Yes/No:'):q_pos + 1]
                remaining_text = remaining_text[:start] + remaining_text[q_pos + 1:]
                
    remaining_text = sanitize_llm_text(remaining_text)
    if not remaining_text.strip():
        remaining_text = "Empty"

    return response, yes_no_phrase, choices, is_date_select, remaining_text

def write_decision(session_id, chat_history, mode="travel"):
    default_message = "決定している項目がありません。"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"
    
    try:
        content = redis_client.get_decision(session_id) or default_message
        groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="openai/gpt-oss-20b")
        
        system_prompt = PROMPTS.get(mode, PROMPTS["travel"])["decision_system"] + "\n" + current_datetime_jp_line() + f"\n以前の決定事項:\n{content}\n"
        
        prompt_messages = [("system", system_prompt)] + chat_history + [("human", "{input}")]
        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        
        chain = prompt | groq_chat | StrOutputParser()
        response = chain.invoke({"input": message})
        response = sanitize_llm_text(response, max_length=int(os.getenv("MAX_DECISION_CHARS", "2000")))

        redis_client.save_decision(session_id, response)
        return response
    except Exception as e:
        logger.error(f"Error in write_decision: {e}")
        return "決定事項の更新中にエラーが発生しました。"

def chat_with_llama(session_id, prompt, mode="travel"):
    result = guard.content_checker(prompt)
    if 'unsafe' in result:
        return None, redis_client.get_decision(session_id) or "安全性の問題で表示できません", None, None, False, "それには答えられません"
    
    chat_history = redis_client.get_chat_history(session_id)
    chat_history.append(("human", prompt))
    
    response, yes_no_phrase, choices, is_date_select, remaining_text = run_qa_chain(prompt, chat_history, mode=mode)
    response = sanitize_llm_text(response)
    remaining_text = sanitize_llm_text(remaining_text)
    
    chat_history.append(("assistant", response))
    redis_client.save_chat_history(session_id, chat_history)
    current_plan = write_decision(session_id, chat_history, mode=mode)
    
    return response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text
