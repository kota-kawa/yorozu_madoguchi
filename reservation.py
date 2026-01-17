from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
import redis_client
from database import SessionLocal
from models import ReservationPlan
import re

import warnings
# 不要な警告を抑制
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

def current_datetime_jp_line() -> str:
    """現在日時を日本語フォーマットで返すヘルパー関数"""
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    now = datetime.now()
    weekday = weekday_map[now.weekday()]
    return f"現在日時: {now.year}年{now.month}月{now.day}日（{weekday}） {now.hour:02d}:{now.minute:02d}"

class ReservationData(BaseModel):
    """
    LLMからの構造化出力のためのPydanticモデル
    
    旅行計画の各要素を定義します。
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
    
    制御文字の除去、空白の正規化、最大長の制限を行います。
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
        plan = (
            db.query(ReservationPlan)
            .filter(ReservationPlan.session_id == session_id)
            .order_by(ReservationPlan.id.desc())
            .first()
        )
        
        if plan:
            # 更新処理
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
    
    1. Redisから非構造化テキスト（決定事項）を取得
    2. Groq (LLM) を使用して ReservationData モデルに構造化
    3. write_reservation_plan を呼び出してDBに保存
    """
    # Redisから読み込む
    text = redis_client.get_decision(session_id)
    
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="openai/gpt-oss-20b")
    
    # 構造化出力用にモデルを設定
    structured_llm = groq_chat.with_structured_output(ReservationData)

    # プロンプトメッセージを作成する
    system_prompt = (
        "あなたは旅行計画のアシスタントです。提供されたテキストから予約に関する情報を抽出してください。"
        "値がない場合はNoneとしてください。"
    ) + "\n" + current_datetime_jp_line()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])
    
    # チェーンを実行
    chain = prompt | structured_llm
    result = chain.invoke({"text": text})

    # 抽出されたデータでDB保存処理を実行
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
