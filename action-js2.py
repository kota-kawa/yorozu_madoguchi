from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Get environment variables
groq_api_key = os.getenv("GROQ_API_KEY")

def process_comment_text(comment_text):
    """Process the comment text"""
    return comment_text

def create_faiss_index(text):
    # Split text into overlapping chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
    )
    # Split the text
    splited_text = text_splitter.split_text(text)
    
    # Return the split text (no embedding conversion)
    return splited_text

def run_qa_chain(message, context):
    # Get Groq API key
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")

    # System prompt with context directly used
    system_prompt = (
        "あなたは渡されたHTMLコードとユーザーからの指示によってJavascriptコードを生成するアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "\n\n"
        f"{context}"  # Use context directly in the prompt
    )

    # Create prompt template with system and human messages
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # Create the chain without retriever, only input
    rag_chain = (
        {"input": RunnablePassthrough()}  # Only pass user input (message)
        | prompt
        | groq_chat
        | StrOutputParser()
    )

    # Get response
    response = rag_chain.invoke(message)

    return response

def chain_main():
    # Comment with user data and form HTML
    comment_text = """ 名前:こうた メールアドレス:kouta@gmail.com メッセージ:おはよう！
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>お問い合わせフォーム</title>
        <link rel="stylesheet" href="styles.css">
    </head>
    <body>
        <div class="contact-form">
            <h1>お問い合わせフォーム</h1>
            <form action="/submit_form" method="post">
                <label for="name">名前:</label>
                <input type="text" id="name" name="name" placeholder="お名前を入力してください" required>

                <label for="email">メールアドレス:</label>
                <input type="email" id="email" name="email" placeholder="メールアドレスを入力してください" required>

                <label for="message">メッセージ:</label>
                <textarea id="message" name="message" placeholder="メッセージを入力してください" required></textarea>

                <button type="submit">送信</button>
            </form>
        </div>
    </body>
    </html>
    """

    # User's message (question)
    message = "フォームに情報を入力して"

    # Process comment text
    text = process_comment_text(comment_text)

    # Directly run the QA chain with text
    output = run_qa_chain(message, text)

    print("Answer:", output)
    return output

if __name__ == "__main__":
    chain_main()
