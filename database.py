from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 環境変数からデータベースURLを取得。デフォルトはローカル開発用（docker-compose外での実行用）
# docker-compose内では環境変数で上書きされる
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/yorozu")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
