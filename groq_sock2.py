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
import time

# .envファイルの読み込み
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

def run_qa_chain(message, retriever):
    # Groq APIを使用したQAチェーン
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")

    system_prompt = (
        "あなたは便利なアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "マニュアルの内容から回答してください。"
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    rag_chain = (
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    response = rag_chain.invoke(message)

    return response

# 文字を1つずつ表示する関数
def display_text_character_by_character(text):
    for char in text:
        print(char, end='', flush=True)  # 改行なしで文字を表示し、出力を即座に反映
        time.sleep(0.05)  # 文字ごとに少しの遅延を追加

def chain_main():
    # PDFファイルパスとメッセージを指定
    pdf_file = "gates.pdf"
    message = "ビルゲイツはどのようにAIを活用している？"

    text = process_pdf(pdf_file)
    retriever = create_faiss_index(text)
    output = run_qa_chain(message, retriever)

    # 出力を1文字ずつ表示
    print("Answer: ", end='')
    display_text_character_by_character(output)

    return output

if __name__ == "__main__":
    chain_main()
