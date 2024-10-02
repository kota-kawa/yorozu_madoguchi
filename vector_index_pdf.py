import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS

# ファイルパスを絶対パスで指定
file_path = "./static/rag2.pdf"

# ファイルが存在するか確認
if not os.path.exists(file_path):
    raise ValueError(f"File path {file_path} is not a valid file or does not exist")

# PDFファイルからテキストを読み込む
pdf_loader = PyPDFLoader(file_path)
documents = pdf_loader.load()

# テキストデータをベクトル化
embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
texts = [doc.page_content for doc in documents]
text_embeddings = embedding_model.embed_documents(texts)

# ベクトルデータをFAISSベクトルデータベースに保存
faiss_db = FAISS.from_texts(texts, embedding_model)

# FAISSベクトルデータベースを保存（任意）
faiss_db.save_local("rag_love2")

print("FAISSベクトルデータベースの作成が完了しました。")
