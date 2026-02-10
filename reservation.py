"""
旅行予約プランの抽出と保存を行うモジュール。
Module for extracting and storing travel reservation plans.
"""

from dotenv import load_dotenv
import os
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import redis_client
from database import SessionLocal
from models import ReservationPlan
import re
import json
import logging

from groq_openai_client import get_groq_client

import warnings
# 不要な警告を抑制
# Suppress noisy warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

# .envファイルの読み込み
# Load variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

def current_datetime_jp_line() -> str:
    """現在日時を日本語フォーマットで返すヘルパー関数 / Return current datetime in JP format."""
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    now = datetime.now()
    weekday = weekday_map[now.weekday()]
    return f"現在日時: {now.year}年{now.month}月{now.day}日（{weekday}） {now.hour:02d}:{now.minute:02d}"

class ReservationData(BaseModel):
    """
    LLMからの構造化出力のためのPydanticモデル
    Pydantic model for structured LLM output.
    
    旅行計画の各要素を定義します。
    Defines fields for a travel plan.
    """
    destinations: Optional[str] = Field(description="目的地", default=None)
    departure: Optional[str] = Field(description="出発地", default=None)
    hotel: Optional[str] = Field(description="ホテル", default=None)
    airlines: Optional[str] = Field(description="航空会社", default=None)
    railway: Optional[str] = Field(description="鉄道会社", default=None)
    taxi: Optional[str] = Field(description="タクシー会社", default=None)
    start_date: Optional[str] = Field(description="滞在開始日", default=None)
    end_date: Optional[str] = Field(description="滞在終了日", default=None)

MAX_FIELD_LENGTH = 200
MAX_DATE_LENGTH = 32


def sanitize_field(value: Optional[str], max_length: int = MAX_FIELD_LENGTH) -> Optional[str]:
    """
    入力フィールドのサニタイズを行う
    Sanitize input fields.
    
    制御文字の除去、空白の正規化、最大長の制限を行います。
    Removes control chars, normalizes whitespace, and enforces max length.
    """
    if value is None:
        return None
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    text = " ".join(text.split())
    text = text.strip()
    if not text:
        return None
    if len(text) > max_length:
        text = text[:max_length]
    return text


def normalize_date(value: Optional[str]) -> Optional[str]:
    """
    日付文字列を正規化する（YYYY-MM-DD形式）
    Normalize date strings to YYYY-MM-DD.
    """
    text = sanitize_field(value, max_length=MAX_DATE_LENGTH)
    if not text:
        return None

    patterns = [
        r"(?P<year>\d{4})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})",
        r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    return text


def write_reservation_plan(
    session_id: str,
    destinations: Optional[str],
    departure: Optional[str],
    hotel: Optional[str],
    airlines: Optional[str],
    railway: Optional[str],
    taxi: Optional[str],
    start: Optional[str],
    end: Optional[str],
) -> str:
    """
    予約プラン情報をデータベースに保存（作成または更新）する
    Persist a reservation plan (create or update).
    """
    if not session_id:
        raise ValueError("session_id is required")

    destinations = sanitize_field(destinations)
    departure = sanitize_field(departure)
    hotel = sanitize_field(hotel)
    airlines = sanitize_field(airlines)
    railway = sanitize_field(railway)
    taxi = sanitize_field(taxi)
    start = normalize_date(start)
    end = normalize_date(end)

    db = SessionLocal()
    try:
        # セッション単位で最新のプランを取得
        # Fetch latest plan for the session
        plan = (
            db.query(ReservationPlan)
            .filter(ReservationPlan.session_id == session_id)
            .order_by(ReservationPlan.id.desc())
            .first()
        )
        
        if plan:
            # 更新処理
            # Update existing plan
            plan.destinations = destinations
            plan.departure = departure
            plan.hotel = hotel
            plan.airlines = airlines
            plan.railway = railway
            plan.taxi = taxi
            plan.start_date = start
            plan.end_date = end
        else:
            # 新規作成処理
            # Create new plan
            plan = ReservationPlan(
                session_id=session_id,
                destinations=destinations,
                departure=departure,
                hotel=hotel,
                airlines=airlines,
                railway=railway,
                taxi=taxi,
                start_date=start,
                end_date=end
            )
            db.add(plan)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return 'finish!'

def complete_plan(session_id: str) -> str:
    """
    Redis上の決定事項テキストから構造化データを抽出し、DBへ保存する
    Extract structured data from Redis decision text and save to DB.
    
    1. Redisから非構造化テキスト（決定事項）を取得
    2. Groq (LLM) を使用して ReservationData モデルに構造化
    3. write_reservation_plan を呼び出してDBに保存
    1) Load unstructured text from Redis
    2) Use Groq (LLM) to structure into ReservationData
    3) Save via write_reservation_plan
    """
    # Redisから読み込む
    # Load from Redis
    text = redis_client.get_decision(session_id)
    
    # プロンプトメッセージを作成する
    # Build prompt for the LLM
    system_prompt = (
        "あなたは旅行計画のアシスタントです。提供されたテキストから予約に関する情報を抽出してください。"
        "値がない場合はnullとしてください。"
        "出力は次のキーを持つJSONのみで返してください: "
        "destinations, departure, hotel, airlines, railway, taxi, start_date, end_date."
    ) + "\n" + current_datetime_jp_line()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text or ""},
    ]

    client = get_groq_client()
    completion = client.chat.completions.create(
        model=os.getenv("GROQ_RESERVATION_MODEL_NAME", "openai/gpt-oss-20b"),
        messages=messages,
    )
    content = completion.choices[0].message.content or "{}"
    result = _parse_reservation_json(content)

    # 抽出されたデータでDB保存処理を実行
    # Persist extracted data
    write_reservation_plan(
        session_id=session_id,
        destinations=result.destinations,
        departure=result.departure,
        hotel=result.hotel,
        airlines=result.airlines,
        railway=result.railway,
        taxi=result.taxi,
        start=result.start_date,
        end=result.end_date
    )

    return 'Complete!'


def _parse_reservation_json(content: str) -> ReservationData:
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("JSON object is required")
    except Exception:
        data = _extract_json_object(content)
    try:
        return ReservationData(**data)
    except Exception as err:
        logger.warning("Reservation JSON parse failed: %s", err)
        return ReservationData()


def _extract_json_object(content: str) -> Dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    snippet = content[start : end + 1]
    try:
        data = json.loads(snippet)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
