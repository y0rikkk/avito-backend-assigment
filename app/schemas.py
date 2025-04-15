from pydantic import BaseModel
from datetime import datetime


class PVZCreate(BaseModel):
    city: str  # "Москва", "Санкт-Петербург" или "Казань"


class PVZResponse(BaseModel):
    id: str  # UUID в виде строки
    registration_date: datetime
    city: str


class ReceptionCreate(BaseModel):
    pvz_id: str  # UUID ПВЗ в виде строки


class ReceptionResponse(BaseModel):
    id: str
    date_time: datetime
    pvz_id: str
    status: str  # "in_progress" или "close"
