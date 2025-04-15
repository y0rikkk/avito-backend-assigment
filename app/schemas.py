from pydantic import BaseModel
from datetime import datetime
from typing import Literal, List


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


class ProductCreate(BaseModel):
    type: Literal["электроника", "одежда", "обувь"]
    pvz_id: str  # UUID ПВЗ в виде строки


class ProductResponse(BaseModel):
    id: str
    date_time: datetime
    type: str
    reception_id: str


# Следующие 3 класса - для эндпоинта /pvz (GET)


class ProductResponseData(BaseModel):
    id: str
    date_time: datetime
    type: str


class ReceptionResponseData(BaseModel):
    id: str
    date_time: datetime
    status: str
    products: List[ProductResponseData]


class PVZResponseData(PVZResponse):
    receptions: List[ReceptionResponseData]
