from pydantic import BaseModel, EmailStr, SkipValidation
from uuid import UUID
from datetime import datetime
from typing import Literal, List


class DummyLoginRequest(BaseModel):
    role: SkipValidation[Literal["employee", "moderator"]]


class Error(BaseModel):
    message: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: SkipValidation[Literal["employee", "moderator"]]


class User(BaseModel):
    id: UUID
    email: EmailStr
    role: SkipValidation[Literal["employee", "moderator"]]


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    token: str


class PVZCreate(BaseModel):
    city: SkipValidation[Literal["Москва", "Санкт-Петербург", "Казань"]]


class PVZ(BaseModel):
    id: UUID
    registration_date: datetime
    city: SkipValidation[Literal["Москва", "Санкт-Петербург", "Казань"]]


class ReceptionCreate(BaseModel):
    pvz_id: UUID


class Reception(BaseModel):
    id: UUID
    date_time: datetime
    pvz_id: UUID
    status: SkipValidation[Literal["in_progress", "close"]]


class ProductCreate(BaseModel):
    type: SkipValidation[Literal["электроника", "одежда", "обувь"]]
    pvz_id: UUID


class Product(BaseModel):
    id: UUID
    date_time: datetime
    type: SkipValidation[Literal["электроника", "одежда", "обувь"]]
    reception_id: UUID


# Следующие 2 класса - для эндпоинта /pvz (GET)


class ReceptionNested(BaseModel):
    reception: Reception
    products: List[Product]


class PVZNested(BaseModel):
    pvz: PVZ
    receptions: List[ReceptionNested]
