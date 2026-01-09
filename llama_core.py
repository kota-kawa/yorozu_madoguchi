import logging
import os
import guard
import redis_client

# ロギング設定
logger = logging.getLogger(__name__)

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser

import warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

groq_api_key = os.getenv("GROQ_API_KEY")

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# API キーが設定されていない、または .env に誤りがある場合はここで明示的にエラーを出す
if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY が設定されていないか、無効です。"
        ".env ファイルを確認し、正しい API キーを指定してください。"
    )

#　旅行計画の相談チャットのプロンプト
def run_qa_chain(message, chat_history):
    yes_no_phrase, remaining_text = None, None
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
    
    # 修正後のシステムプロンプト
    system_prompt = """
    # 命令書

    あなたは、優秀で親切な旅行計画のプロフェッショナル・コンシェルジュです。
    ユーザー一人ひとりに寄り添い、最高の旅行プランを作成するのを手伝ってください。

    ## あなたの役割
    - ユーザーとの対話を通じて、旅行の必須情報（目的地、日程など）と、潜在的な要望（興味、予算、雰囲気など）を引き出します。
    - 提供されたユーザーとの会話とあなたの知識を基に、ユーザーに最適な旅行プランを提案します。
    - 明るく、丁寧で、共感的な対話スタイルで、ユーザーが楽しく計画を立てられるようにサポートしてください。

    ## 実行ステップ
    あなたは以下のステップに沿って、ユーザーとの対話を進めてください。

    ### Step 1: 基本情報のヒアリング
    まず、旅行の土台となる以下の必須項目を一つずつ、順番に質問して確認してください。
    1.  **目的地**: どこへ行きたいですか？（都道府県、都市名など）
    2.  **出発地**: どこから出発しますか？（駅名や空港名を推奨）
    3.  **日程**: いつからいつまで旅行しますか？（具体的な日付）

    ### Step 2: 好みや要望のヒアリング
    基本情報が固まったら、よりパーソナルなプランにするために、ユーザーの好みや要望をヒアリングします。
    例：
    - どんなことに興味がありますか？（グルメ、自然、歴史、アート、アクティビティなど）
    - 旅行の予算はどのくらいですか？
    - どんな雰囲気の旅行にしたいですか？（のんびり、アクティブ、豪華など）

    ### Step 3: 具体的な提案
    ヒアリングした内容と、ユーザーとの会話を基に、具体的な旅行プランの選択肢を提案してください。
    - 提案には、なぜそれがおすすめなのか、具体的な理由を必ず添えてください。

    ### Step 4: プランの確定
    ユーザーが選択肢の中から決定したら、その内容を要約して確認します。
    全ての項目が決まったら、最終的な旅行プランをまとめて提示してください。

    # 制約条件
    - **言語**: 回答は全て流暢な日本語で行ってください。
    - **応答の長さ**: 簡潔さを心がけ、一度の回答は200文字以内を目安にしてください。ただし、ユーザーに有益な情報を提供することを最優先とし、必要であれば少し超えても構いません。
    - **質問の仕方**: ユーザーを混乱させないよう、一度のメッセージでは一つの質問だけにしてください。
    - **Yes/No形式の質問**: ユーザーに二者択一で決めてほしい場合は、必ず「Yes/No:〇〇にしますか？」という形式で質問してください。この形式は、提案を絞り込む際に効果的です。
    - **必須項目の扱い**: 出発地、目的地、日程は、ユーザーに決めてもらいます。もしユーザーが「おまかせ」や「おすすめは？」と尋ねてきた場合にのみ、ユーザーとの会話の情報を基に提案してください。
    - **地名の扱い**: 出発地と目的地は、交通手段の検索を考慮し、駅名または空港名で確定するように促してください。
    """
    
    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
        ("human", "{input}")
    ]
    # プロンプトテンプレートを作成する
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    # チェーンを構築する (RAGなし)
    chain = (
        prompt
        | groq_chat
        | StrOutputParser()
    )
    #　チャット履歴とプロンプトを元に、回答を生成
    response = chain.invoke({"input": message})

    # Yes/No形式の文章の整形
    def extract_and_split_text(text):
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
            remaining_text = "Empty"
    else:
        remaining_text = response

    return response, yes_no_phrase, remaining_text

#　決定している事項をRedisに書き込む
def write_decision(session_id, chat_history):
    default_message = "決定している項目がありません。"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"
    
    try:
        # Redisから読み込む
        content = redis_client.get_decision(session_id)
        
        # コンテンツが空の場合は、デフォルトメッセージを使用
        if not content.strip():
            content = default_message

        # Groqのチャットモデルを初期化する
        groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
        # システムプロンプトを定義する
        system_prompt = (
            "あなたは、渡されたチャット履歴と以前の決定事項から、現在決定されている項目を抽出するアシスタントです。\n"
            "あなたは日本人なので、日本語で回答してください。必ず日本語で。\n"
            f"以前の決定事項:\n{content}\n\n"
        )
        # プロンプトメッセージを作成する
        prompt_messages = [
            ("system", system_prompt),
        ] + chat_history + [
            ("human", "{input}")
        ]
        # プロンプトテンプレートを作成する
        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        
        # チェーンを構築する (RAGなし)
        chain = (
            prompt
            | groq_chat
            | StrOutputParser()
        )
        response = chain.invoke({"input": message})
        
        # 決定事項をRedisに保存する
        redis_client.save_decision(session_id, response)

        return response
    except Exception as e:
        logger.error(f"Error in write_decision: {e}")
        return "決定事項の更新中にエラーが発生しました。"

# メインのプログラムにLLMの結果を返す
def chat_with_llama(session_id, prompt):
    result = guard.content_checker(prompt)

    #　悪意のあるプロンプトだった場合
    if 'unsafe' in result:
        remaining_text = "それには答えられません"
        yes_no_phrase, response = None, None
        
        try:
            current_plan = redis_client.get_decision(session_id)
            if not current_plan:
                current_plan = "情報を読み取れませんでした。"
        except Exception:
            current_plan = "情報を読み取れませんでした。"
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
        # ここで再読み込みは不要。メモリ上のchat_historyを使う。
        current_plan = write_decision(session_id, chat_history)
        # print("回答：", response) # 不要なprintは削除

    return response, current_plan, yes_no_phrase, remaining_text
