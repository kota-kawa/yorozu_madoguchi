from flask import Flask, render_template, request, jsonify
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

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

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

def run_qa_chain(message, retriever):
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

# Route to render the homepage
@app.route('/')
def home():
    return render_template('sock_test.html')  # Make sure you have an 'index.html' file in the templates folder

# Route to handle user message submission
@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')
    pdf_file = "gates.pdf"
    
    # Process PDF and create retriever
    text = process_pdf(pdf_file)
    retriever = create_faiss_index(text)
    
    # Run the QA chain
    output = run_qa_chain(user_message, retriever)

    return jsonify(response=output)

if __name__ == "__main__":
    app.run(debug=True)
