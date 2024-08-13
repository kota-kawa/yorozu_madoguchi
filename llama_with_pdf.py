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

def run_qa_chain(message, retriever):
    # Get Groq API key
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
        # contextにはRetriever、inputにはユーザーの質問を渡す
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    response = rag_chain.invoke(message)

    return response

def chain_main():
    # PDFファイルパスとメッセージを直接指定
    pdf_file = "frog.pdf"
    message = "坂柳はなぜ退学した？"

    text = process_pdf(pdf_file)
    retriever = create_faiss_index(text)
    output = run_qa_chain(message, retriever)

    print("Answer:", output)
    return output

if __name__ == "__main__":
    chain_main()
