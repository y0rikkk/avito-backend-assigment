from pydantic import BaseModel, EmailStr, SkipValidation
from datetime import datetime
from typing import Literal, List


class DummyLoginRequest(BaseModel):
    role: SkipValidation[Literal["employee", "moderator"]]


class Error(BaseModel):
    message: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str  # "employee" или "moderator"


class User(BaseModel):
    id: str
    email: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    token: str


class PVZCreate(BaseModel):
    city: str  # "Москва", "Санкт-Петербург" или "Казань"


class PVZ(BaseModel):
    id: str  # UUID в виде строки
    registration_date: datetime
    city: str


class ReceptionCreate(BaseModel):
    pvz_id: str  # UUID ПВЗ в виде строки


class Reception(BaseModel):
    id: str
    date_time: datetime
    pvz_id: str
    status: str  # "in_progress" или "close"


class ProductCreate(BaseModel):
    type: Literal["электроника", "одежда", "обувь"]
    pvz_id: str  # UUID ПВЗ в виде строки


class Product(BaseModel):
    id: str
    date_time: datetime
    type: str
    reception_id: str


# Следующие 3 класса - для эндпоинта /pvz (GET)


class ReceptionNested(BaseModel):
    reception: Reception
    products: List[Product]


class PVZNested(BaseModel):
    pvz: PVZ
    receptions: List[ReceptionNested]
