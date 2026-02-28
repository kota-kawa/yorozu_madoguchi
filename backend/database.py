"""
データベース接続と初期化のユーティリティ。
Database connection and initialization utilities.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError
import os
import time
import logging
from typing import Generator

# ロギング設定
# Configure logging
logger = logging.getLogger(__name__)

# 環境変数からデータベースURLを取得
# Read database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def _db_init_lock_key() -> int:
    """
    DB初期化用のアドバイザリロックキーを取得する
    Get advisory lock key used for DB initialization.
    """
    raw = os.getenv("DB_INIT_LOCK_KEY", "834221").strip()
    try:
        return int(raw)
    except ValueError:
        return 834221

def _acquire_db_init_lock(connection) -> None:
    """
    DB初期化の同時実行を防ぐためのアドバイザリロックを取得する
    Acquire advisory lock to prevent concurrent DB initialization.
    """
    connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _db_init_lock_key()})

def _release_db_init_lock(connection) -> None:
    """
    DB初期化のアドバイザリロックを解放する
    Release advisory lock after DB initialization.
    """
    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _db_init_lock_key()})

def get_db() -> Generator[Session, None, None]:
    """
    データベースセッションを取得する依存関係関数
    Dependency provider that yields a DB session.
    
    リクエストごとに新しいセッションを作成し、処理終了後に必ずクローズします。
    Creates a new session per request and always closes it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    データベースの初期化を行う関数
    Initialize the database schema with retries.
    
    コンテナ起動直後など、DBが準備できていない場合を考慮し、リトライロジックを実装しています。
    テーブルの作成と、必要なスキーマ変更（マイグレーション的処理）を実行します。
    Retries on startup, creates tables, and applies minimal schema updates.
    """
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            with engine.begin() as connection:
                _acquire_db_init_lock(connection)
                try:
                    # テーブル作成（存在しない場合）
                    Base.metadata.create_all(bind=connection)
                    # スキーマの確認と更新
                    _ensure_reservation_schema(connection)
                finally:
                    _release_db_init_lock(connection)
            logger.info("Database initialized successfully.")
            return
        except OperationalError as e:
            if i < max_retries - 1:
                logger.warning(f"Database not ready yet, retrying in {retry_interval} seconds... (Attempt {i+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                logger.error("Could not connect to database after multiple attempts.")
                raise e

def _ensure_reservation_schema(connection) -> None:
    """
    reservation_plansテーブルのスキーマを確認し、必要なカラムを追加する
    Ensure reservation_plans schema has required columns and indexes.
    
    既存のテーブルに対して、session_idカラムやインデックスが不足している場合に追加します。
    簡易的なマイグレーション機能として動作します。
    Adds missing columns/indexes as a lightweight migration step.
    """
    inspector = inspect(connection)
    if "reservation_plans" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("reservation_plans")}
    if "session_id" in columns:
        return

    # 複数ワーカー起動時の競合でDuplicateColumnが発生しないようにガード
    # Guard against DuplicateColumn when multiple workers start
    connection.execute(text("ALTER TABLE reservation_plans ADD COLUMN IF NOT EXISTS session_id VARCHAR(64)"))
    connection.execute(
        text("CREATE INDEX IF NOT EXISTS ix_reservation_plans_session_id ON reservation_plans (session_id)")
    )
