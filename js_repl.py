from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableSequence
from dotenv import load_dotenv
import os
import re

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

def escape_curly_braces(text):
    """Escape curly braces in the text."""
    return text.replace("{", "{{").replace("}", "}}")

def run_qa_chain(message, context):
    # Escape curly braces in the context
    escaped_context = escape_curly_braces(context)
    # Get Groq API key
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-70b-8192")

    # System prompt with context directly used
    system_prompt = (
        "あなたは渡されたHTMLコードとユーザーからの指示によってJavascriptコードを生成するアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        "Javascriptコードはeval()関数に入れてそのまま実行できるようにしてほしい。"
        "プロフィール情報 名前:こうた メールアドレス:kouta@gmail.com メッセージ:おはよう！"
        "\n\n"
        f"{escaped_context}"  # Use context directly in the prompt
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

def chain_main(message, html_code):
    # Comment with user data and form HTML
    """html_code = <div class="contact-form">
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
    </div>"""
    comment_text = str(html_code)

    # User's message (question)
    #message = "フォームに情報を入力して"

    # Process comment text
    text = process_comment_text(comment_text)

    # Directly run the QA chain with text
    output = run_qa_chain(message, text)

    # 正規表現を使ってjavascriptコード部分を抽出
    code_match = re.search(r'```(.*?)```', output, re.DOTALL)
    if code_match:
        extracted_code = code_match.group(1).strip()
        
        # "javascript"文字列を削除
        if extracted_code.startswith("javascript"):
            extracted_code = extracted_code[len("javascript"):].strip()
        
        print("抽出されたコード:")
        print(extracted_code)
        
        # 残りのテキストを表示
        remaining_text = re.sub(r'```(.*?)```', '', output, flags=re.DOTALL).strip()
        print("残りのテキスト:")
        print(remaining_text)
        return extracted_code, remaining_text
    
    else:
        print("Javascriptコードが見つかりませんでした。")

#if __name__ == "__main__":
    #chain_main()
