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

def process_comment_text(comment_text):
    """コメントからテキストを処理"""
    return comment_text

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
        "あなたは渡されたHTMLコードとユーザーからの指示によってJavascriptコードを生成するアシスタントです。 また、あなたは日本人なので、日本語で回答してください。必ず日本語で。"
        ""
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
    # コメントでテキストを指定
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

    message = "フォームに情報を入力して" # 質問を設定

    # コメントからテキストを取得
    text = process_comment_text(comment_text)
    retriever = create_faiss_index(text)
    output = run_qa_chain(message, retriever)

    print("Answer:", output)
    return output

if __name__ == "__main__":
    chain_main()
