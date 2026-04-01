"""
データベース接続と初期化のユーティリティ。
Database connection and initialization utilities.
"""

from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError
import os
import time
import logging
from typing import Generator

# ロギング設定
# Configure logging
logger = logging.getLogger(__name__)
ALEMBIC_INI_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"
ALEMBIC_SCRIPT_PATH = ALEMBIC_INI_PATH.parent / "alembic"

# 環境変数からデータベースURLを取得
# Read database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _build_alembic_config() -> Config:
    """
    Alembic実行用の設定を組み立てる
    Build Alembic config used for migration execution.
    """
    if not ALEMBIC_INI_PATH.exists():
        raise FileNotFoundError(f"Alembic config file not found: {ALEMBIC_INI_PATH}")
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_PATH))
    return config


def _run_migrations(connection: Connection) -> None:
    """
    Alembicマイグレーションを最新まで適用する
    Apply Alembic migrations up to the latest revision.
    """
    config = _build_alembic_config()
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


def _is_postgresql(connection: Connection) -> bool:
    return connection.dialect.name == "postgresql"

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
    if not _is_postgresql(connection):
        return
    connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _db_init_lock_key()})

def _release_db_init_lock(connection) -> None:
    """
    DB初期化のアドバイザリロックを解放する
    Release advisory lock after DB initialization.
    """
    if not _is_postgresql(connection):
        return
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
    Alembicマイグレーションを実行してスキーマを最新にします。
    Retries on startup and applies Alembic migrations to the latest schema.
    """
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            with engine.connect() as connection:
                _acquire_db_init_lock(connection)
                try:
                    _run_migrations(connection)
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
