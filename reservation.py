from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import make_csv
from pydantic import BaseModel, Field
from typing import Optional
import redis_client

import warnings
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

# .envファイルの読み込み
load_dotenv()

# 環境変数の値を取得
groq_api_key = os.getenv("GROQ_API_KEY")

class ReservationData(BaseModel):
    destinations: Optional[str] = Field(description="目的地", default=None)
    departure: Optional[str] = Field(description="出発地", default=None)
    hotel: Optional[str] = Field(description="ホテル", default=None)
    airlines: Optional[str] = Field(description="航空会社", default=None)
    railway: Optional[str] = Field(description="鉄道会社", default=None)
    taxi: Optional[str] = Field(description="タクシー会社", default=None)
    start_date: Optional[str] = Field(description="滞在開始日", default=None)
    end_date: Optional[str] = Field(description="滞在終了日", default=None)

def complete_plan(session_id):
    # Redisから読み込む
    text = redis_client.get_decision(session_id)
    
    # Groqのチャットモデルを初期化する
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
    
    # 構造化出力用にモデルを設定
    structured_llm = groq_chat.with_structured_output(ReservationData)

    # プロンプトメッセージを作成する
    system_prompt = (
        "あなたは旅行計画のアシスタントです。提供されたテキストから予約に関する情報を抽出してください。"
        "値がない場合はNoneとしてください。"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])
    
    # チェーンを実行
    chain = prompt | structured_llm
    result = chain.invoke({"text": text})

    # 抽出されたデータでDB保存処理を実行
    make_csv.write_reservation_plan(
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