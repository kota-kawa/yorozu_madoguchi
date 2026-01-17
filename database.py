from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os
import time
import logging

# ロギング設定
logger = logging.getLogger(__name__)

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
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_reservation_schema()
            logger.info("Database initialized successfully.")
            return
        except OperationalError as e:
            if i < max_retries - 1:
                logger.warning(f"Database not ready yet, retrying in {retry_interval} seconds... (Attempt {i+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                logger.error("Could not connect to database after multiple attempts.")
                raise e


def _ensure_reservation_schema():
    inspector = inspect(engine)
    if "reservation_plans" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("reservation_plans")}
    if "session_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE reservation_plans ADD COLUMN session_id VARCHAR(64)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_reservation_plans_session_id ON reservation_plans (session_id)")
        )
