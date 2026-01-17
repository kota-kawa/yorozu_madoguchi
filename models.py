from sqlalchemy import Column, Integer, String
from database import Base

class ReservationPlan(Base):
    """
    旅行計画の予約情報を管理するモデル
    
    ユーザーごとに作成された旅行プランの詳細（目的地、移動手段、日程など）を保持します。
    """
    __tablename__ = "reservation_plans"

    id = Column(Integer, primary_key=True, index=True)
    # セッションID: ユーザーを一意に識別するためのID（CookieやRedisと連携）
    session_id = Column(String(64), index=True, nullable=False)
    
    # 以下、旅行プランの構成要素
    destinations = Column(String, nullable=True)  # 目的地
    departure = Column(String, nullable=True)     # 出発地
    hotel = Column(String, nullable=True)         # 宿泊施設
    airlines = Column(String, nullable=True)      # 航空会社
    railway = Column(String, nullable=True)       # 鉄道
    taxi = Column(String, nullable=True)          # タクシー・送迎
    start_date = Column(String, nullable=True)    # 旅行開始日
    end_date = Column(String, nullable=True)      # 旅行終了日
