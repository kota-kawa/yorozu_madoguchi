from pypdf import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

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
pdf_file = "travel_choice.pdf"
text = process_pdf(pdf_file)
# テキストからFAISSインデックスを作成する
retriever = create_faiss_index(text)

#　旅行計画の相談チャットのプロンプト
def run_qa_chain(message, retriever, chat_history):
    yes_no_phrase, remaining_text = None, None
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")
    # システムプロンプトを定義する
    system_prompt = (
        "あなたは旅行の予定を立てるアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        #"マニュアルの選択肢の内容を元に、ユーザーの要求に合うように計画を立ててください。"
        "目的地、出発地、滞在開始日、滞在終了日は確実に決めて。目的地、出発地、滞在開始日、滞在終了日の提案はせずに、ユーザに入力させて。"
        "\n\n"
        "もしも会話の状況を見て、ユーザーに対して「はい/いいえ」で回答してもらいたい場合には、「Yes/No:〇〇にしますか？」と全く同じ形式で出力して。Yes/No形式の質問の頻度は2回に1回まで!絶対!"
        "{context}"
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
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    #　チャット履歴とプロンプトを元に、回答を生成
    response = rag_chain.invoke(message)

    # Yes/No形式の文章の整形
    def extract_and_split_text(text):
        # "Yes/No:"と"？"の位置を見つける
        yes_no_start = text.find('Yes/No:')
        if yes_no_start == -1:
            return None, text  # "Yes/No:"が見つからない場合は全体を返す

        question_end = text.find('？', yes_no_start)
        question_end_half = text.find('?', yes_no_start)
            # 有効な位置を選択
        if question_end == -1 and question_end_half == -1:
            return None, text  # 両方の"？"が見つからない場合は全体を返す

        # "Yes/No:"部分の抽出
        yes_no_phrase = text[yes_no_start + len('Yes/No:'):question_end + 1]

        # "Yes/No:"部分を除いた残りの文章
        remaining_text = text[:yes_no_start] + text[question_end + 1:]

        return response, yes_no_phrase, remaining_text

    # Yas/No形式の質問だった場合
    if "Yes/No" in response:
        # 関数を使って抽出
        response, yes_no_phrase, remaining_text = extract_and_split_text(response)
    else:
        remaining_text = response

    return response, yes_no_phrase, remaining_text

#　決定している事項をテキストファイルに書き込む
def write_decision_txt(chat_history):
    file_path = "decision.txt"
    message = "決定している項目のみを抽出してください、説明などは一切必要ありません"
    # ファイルを読み込む
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    decision_index = create_faiss_index(content)
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")
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
def chat_with_llama(prompt):
    # チャット履歴を読み込む
    chat_history_file = "chat_history.txt"
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
    current_plan = write_decision_txt(chat_history)
    print("回答：", response)

    return response, current_plan, yes_no_phrase, remaining_text