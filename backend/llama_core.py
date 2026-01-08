from pypdf import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import guard

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


# PDFファイルを読み込み、全ページのテキストを抽出する
def process_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()
    return text

#　RAGに渡せるように文章の形式にする
def create_faiss_index(text):
    # テキストをチャンクに分割する
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,  # 各チャンクのサイズ
        chunk_overlap=50,  # チャンク間の重なり
    )
    splited_text = text_splitter.split_text(text)
    # テキストチャンクの埋め込みを生成する
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    # FAISSインデックスを作成し、レトリーバーとして設定する
    index = FAISS.from_texts(splited_text, embedding=embeddings)
    retriever = index.as_retriever(search_kwargs={"k": 1})
    return retriever

# PDFファイルを処理してテキストを抽出する
#pdf_file = "./travel_choice.pdf"
#text = process_pdf(pdf_file)
# テキストからFAISSインデックスを作成する
#retriever = create_faiss_index(text)

# 既存のFAISSインデックスを読み込む
def load_faiss_index(index_path):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    index = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    retriever = index.as_retriever(search_kwargs={"k": 1})
    return retriever


# 既存のFAISSインデックスのパス
index_path = "./travel_choice"

# テキストからFAISSインデックスを読み込む
retriever = load_faiss_index(index_path)

#　旅行計画の相談チャットのプロンプト
def run_qa_chain(message, retriever, chat_history):
    yes_no_phrase, remaining_text = None, None
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")

    """
    system_prompt = (
        "あなたは旅行の予定を立てるアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。回答は150文字以内にして。"
        "会話例を参考にしながら、ユーザーの要求に合うように計画を立てて。"
        "出発地、目的地、滞在開始日、滞在終了日はユーザに決めさせて。（おすすめを聞かれたときには答えていいよ）"
        "ユーザーに質問するときには、１回で１つの項目についてだけにして。"

        "出発地、目的地、滞在開始日、滞在終了日は確実に決めて。"
        "出発地、目的地は駅か空港名にして。"
        "\n\n"
        "もしも会話の状況を見て、ユーザーに対して「はい/いいえ」で回答してもらいたい場合には、「Yes/No:〇〇にしますか？」と全く同じ形式で出力して。"
        "{context}"
    )"""

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

    {context}
    """

    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
        ("human", "{input}")
    ]
    # プロンプトテンプレートを作成する
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    # RAG（Retrieval-Augmented Generation）チェーンを構築する
    rag_chain = (
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    #　チャット履歴とプロンプトを元に、回答を生成
    response = rag_chain.invoke(message)

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

#　決定している事項をテキストファイルに書き込む
def write_decision_txt(chat_history, session_id):
    file_path = f"./decision_{session_id}.txt"
    default_message = "決定している項目がありません。"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"

    # Check if file exists, if not create empty
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("")

    # ファイルを読み込む
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # ファイルが空の場合は、デフォルトメッセージを書き込む
    if not content.strip():
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(default_message)
            return default_message

    decision_index = create_faiss_index(content)
    # Groqのチャットモデルを初期化する llama3-70b-8192
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
    # システムプロンプトを定義する
    system_prompt = (
        "あなたは、渡された文章から決定されている項目を抽出するアシスタントです。あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "\n\n"
    )
    # プロンプトメッセージを作成する
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
        ("human", "{input}")
    ]
    # プロンプトテンプレートを作成する
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    # RAG（Retrieval-Augmented Generation）チェーンを構築する
    rag_chain = (
        {"context": decision_index, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    response = rag_chain.invoke(message)
    # 決定事項をファイルに保存する
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(response)

    return response

# チャット履歴をファイルから読み込む
def load_chat_history(file_path):
    chat_history = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            current_role = None
            current_text = []
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("human:") or stripped_line.startswith("assistant:"):
                    if current_role is not None:
                        chat_history.append((current_role, "\n".join(current_text).strip()))
                    current_role, current_text = stripped_line.split(":", 1)
                    current_text = [current_text.strip()]
                else:
                    current_text.append(stripped_line)
            if current_role is not None:
                chat_history.append((current_role, "\n".join(current_text).strip()))
    return chat_history

# チャット履歴をファイルに保存する
def save_chat_history(file_path, chat_history):
    with open(file_path, "w", encoding="utf-8") as f:
        for role, text in chat_history:
            f.write(f"{role}:{text}\n")

# メインのプログラムにLLMの結果を返す
def chat_with_llama(prompt, session_id):
    result = guard.content_checker(prompt)

    #　悪意のあるプロンプトだった場合
    if 'unsafe' in result:
        remaining_text = "それには答えられません"
        yes_no_phrase, response = None, None

        file_path = f"./decision_{session_id}.txt"
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("決定している項目がありません。")

        # ファイルを読み込む
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        current_plan = content
    #　通常の返答
    else:
        # チャット履歴を読み込む
        chat_history_file = f"./chat_history_{session_id}.txt"
        chat_history = load_chat_history(chat_history_file)
        # 入力メッセージを追加してQAチェーンを実行する
        message = prompt
        chat_history.append(("human", message))
        response, yes_no_phrase, remaining_text = run_qa_chain(message, retriever, chat_history)
        chat_history.append(("assistant", response))
        # チャット履歴を保存する
        save_chat_history(chat_history_file, chat_history)
        # 決定している項目を保存する
        chat_history = load_chat_history(chat_history_file)
        current_plan = write_decision_txt(chat_history, session_id)
        print("回答：", response)

    return response, current_plan, yes_no_phrase, remaining_text
