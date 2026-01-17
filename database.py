from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError
import os
import time
import logging
from typing import Generator

# ロギング設定
logger = logging.getLogger(__name__)

# 環境変数からデータベースURLを取得。デフォルトはローカル開発用（docker-compose外での実行用）
# docker-compose内では環境変数で上書きされる
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/yorozu")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    データベースセッションを取得する依存関係関数
    
    リクエストごとに新しいセッションを作成し、処理終了後に必ずクローズします。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    データベースの初期化を行う関数
    
    コンテナ起動直後など、DBが準備できていない場合を考慮し、リトライロジックを実装しています。
    テーブルの作成と、必要なスキーマ変更（マイグレーション的処理）を実行します。
    """
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            # テーブル作成（存在しない場合）
            Base.metadata.create_all(bind=engine)
            # スキーマの確認と更新
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


def _ensure_reservation_schema() -> None:
    """
    reservation_plansテーブルのスキーマを確認し、必要なカラムを追加する
    
    既存のテーブルに対して、session_idカラムやインデックスが不足している場合に追加します。
    簡易的なマイグレーション機能として動作します。
    """
    inspector = inspect(engine)
    if "reservation_plans" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("reservation_plans")}
    if "session_id" in columns:
        return

    with engine.begin() as connection:
        # 複数ワーカー起動時の競合でDuplicateColumnが発生しないようにガード
        connection.execute(text("ALTER TABLE reservation_plans ADD COLUMN IF NOT EXISTS session_id VARCHAR(64)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_reservation_plans_session_id ON reservation_plans (session_id)")
        )
