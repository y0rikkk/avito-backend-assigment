from pydantic import BaseModel
from datetime import datetime


class PVZCreate(BaseModel):
    city: str  # "Москва", "Санкт-Петербург" или "Казань"


class PVZResponse(BaseModel):
    id: str  # UUID в виде строки
    registration_date: datetime
    city: str
