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
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
    )
    splited_text = text_splitter.split_text(text)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    index = FAISS.from_texts(splited_text, embedding=embeddings)
    retriever = index.as_retriever(search_kwargs={"k": 1})

    return retriever

def run_qa_chain(message, retriever, chat_history):
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")

    system_prompt = (
        "あなたは便利なアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "マニュアルの内容から回答してください。"
        "\n\n"
        "{context}"
    )

    prompt_messages = [
        ("system", system_prompt),
    ] + chat_history + [
        ("human", "{input}")
    ]

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    rag_chain = (
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | groq_chat
        | StrOutputParser()
    )
    response = rag_chain.invoke(message)

    return response

def load_chat_history(file_path):
    chat_history = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                role, text = line.strip().split(":", 1)
                chat_history.append((role, text.strip()))
    return chat_history

def save_chat_history(file_path, chat_history):
    with open(file_path, "w", encoding="utf-8") as f:
        for role, text in chat_history:
            f.write(f"{role}:{text}\n")

def chat_with_llama(prompt):
    pdf_file = "frog.pdf"
    text = process_pdf(pdf_file)
    retriever = create_faiss_index(text)
    chat_history_file = "chat_history.txt"
    chat_history = load_chat_history(chat_history_file)

    message = prompt
    chat_history.append(("human", message))
    response = run_qa_chain(message, retriever, chat_history)
    chat_history.append(("assistant", response))
    save_chat_history(chat_history_file, chat_history)
    print("回答：", response)
    return response

