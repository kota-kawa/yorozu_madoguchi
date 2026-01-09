from sqlalchemy import Column, Integer, String
from database import Base

class ReservationPlan(Base):
    __tablename__ = "reservation_plans"

    id = Column(Integer, primary_key=True, index=True)
    destinations = Column(String, nullable=True)
    departure = Column(String, nullable=True)
    hotel = Column(String, nullable=True)
    airlines = Column(String, nullable=True)
    railway = Column(String, nullable=True)
    taxi = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
