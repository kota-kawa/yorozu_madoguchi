from database import SessionLocal
from models import ReservationPlan

def write_reservation_plan(destinations, departure, hotel, airlines, railway, taxi, start, end):
    db = SessionLocal()
    try:
        # 既存のプランを取得（常に1件のみ保持する運用と仮定）
        plan = db.query(ReservationPlan).first()
        
        if plan:
            # 更新
            plan.destinations = destinations
            plan.departure = departure
            plan.hotel = hotel
            plan.airlines = airlines
            plan.railway = railway
            plan.taxi = taxi
            plan.start_date = start
            plan.end_date = end
        else:
            # 新規作成
            plan = ReservationPlan(
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
