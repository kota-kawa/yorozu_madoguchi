"""
SQLAlchemyモデル定義。
SQLAlchemy model definitions.
"""

from sqlalchemy import Column, Integer, String
from backend.database import Base

class ReservationPlan(Base):
    """
    旅行計画の予約情報を管理するモデル
    Model to store travel reservation plans.
    
    ユーザーごとに作成された旅行プランの詳細（目的地、移動手段、日程など）を保持します。
    Holds per-user plan details (destination, transport, dates, etc.).
    """
    __tablename__ = "reservation_plans"

    id: Column = Column(Integer, primary_key=True, index=True)
    # セッションID: ユーザーを一意に識別するためのID（CookieやRedisと連携）
    # Session ID: unique user identifier (cookie/Redis linkage)
    session_id: Column = Column(String(64), index=True, nullable=False)
    
    # 以下、旅行プランの構成要素
    # Fields composing the travel plan
    destinations: Column = Column(String, nullable=True)  # 目的地
    departure: Column = Column(String, nullable=True)     # 出発地
    hotel: Column = Column(String, nullable=True)         # 宿泊施設
    airlines: Column = Column(String, nullable=True)      # 航空会社
    railway: Column = Column(String, nullable=True)       # 鉄道
    taxi: Column = Column(String, nullable=True)          # タクシー・送迎
    start_date: Column = Column(String, nullable=True)    # 旅行開始日
    end_date: Column = Column(String, nullable=True)      # 旅行終了日
