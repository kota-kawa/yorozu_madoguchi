from pypdf import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

#.envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

def process_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()
    return text

def create_faiss_index(text):
    # チャンク間でoverlappingさせながらテキストを分割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
    )
    # テキストを分割
    splited_text = text_splitter.split_text(text)

    # 軽量な英語専用モデルを使用
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # テキストを埋め込みベクトルに変換
    index = FAISS.from_texts(splited_text, embedding=embeddings)
    # FaissのRetrieverを取得
    retriever = index.as_retriever(search_kwargs={"k": 1})

    return retriever

def run_qa_chain(message, retriever, chat_history):
    # Get Groq API key
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")

    system_prompt = (
        "あなたは便利なアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "マニュアルの内容から回答してください。"
        "\n\n"
        "{context}"
    )

    # チャット履歴を組み込む
    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
        ("human", "{input}")
    ]

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    rag_chain = (
        # contextにはRetriever、inputにはユーザーの質問を渡す
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    response = rag_chain.invoke(message)

    return response

def chat_with_pdf(pdf_file):
    text = process_pdf(pdf_file)
    retriever = create_faiss_index(text)
    chat_history = []

    while True:
        message = input("質問を入力してください（終了するには 'exit' と入力）：")
        if message.lower() == 'exit':
            break

        chat_history.append(("human", message))
        response = run_qa_chain(message, retriever, chat_history)
        chat_history.append(("assistant", response))

        print("回答:", response)

if __name__ == "__main__":
    pdf_file = "frog.pdf"
    chat_with_pdf(pdf_file)
