from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt
import uuid
from datetime import datetime, timezone
from app.config import settings
from app.database import (
    init_db,
    get_db_connection,
    has_active_reception,
    get_active_reception_id,
    get_last_product_id,
)
from app.security import create_access_token
from app.schemas import *

app = FastAPI()

security = HTTPBearer()


# TODO переделать
@app.on_event("startup")
def startup_event():
    init_db()


def get_current_role(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload["role"]
    except:
        raise HTTPException(status_code=403, detail="Доступ запрещён")


@app.get("/")
async def home():
    return "hello world"


class DummyLoginRequest(BaseModel):
    role: str


@app.post("/dummyLogin")
def dummy_login(request: DummyLoginRequest):
    if request.role not in ["employee", "moderator"]:
        raise HTTPException(
            status_code=400,
            detail="Недопустимая роль. Допустимые значения: 'employee', 'moderator'",
        )

    token = create_access_token(role=request.role)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/pvz", response_model=PVZResponse)
def create_pvz(
    pvz_data: PVZCreate,
    role: str = Depends(get_current_role),
):
    if role != "moderator":
        raise HTTPException(status_code=403, detail="Только для модераторов")

    allowed_cities = ["Москва", "Санкт-Петербург", "Казань"]
    if pvz_data.city not in allowed_cities:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый город. Допустимые значения: {', '.join(allowed_cities)}",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        pvz_id = str(uuid.uuid4())
        registration_date = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO pvz (id, registration_date, city)
            VALUES (%s, %s, %s)
            RETURNING id, registration_date, city
            """,
            (pvz_id, registration_date, pvz_data.city),
        )
        result = cur.fetchone()
        conn.commit()

        return {"id": result[0], "registration_date": result[1], "city": result[2]}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.post("/receptions", response_model=ReceptionResponse)
def create_reception(
    reception_data: ReceptionCreate,
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    if has_active_reception(reception_data.pvz_id):
        raise HTTPException(
            status_code=400,
            detail="В этом ПВЗ уже есть активная приёмка. Закройте её перед созданием новой.",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        reception_id = str(uuid.uuid4())
        date_time = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO receptions (id, date_time, pvz_id, status)
            VALUES (%s, %s, %s, 'in_progress')
            RETURNING id, date_time, pvz_id, status
            """,
            (reception_id, date_time, reception_data.pvz_id),
        )
        result = cur.fetchone()
        conn.commit()

        return {
            "id": result[0],
            "date_time": result[1],
            "pvz_id": result[2],
            "status": result[3],
        }

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Ошибка при создании приёмки: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


@app.post("/products", response_model=ProductResponse)
def add_product(
    product_data: ProductCreate,
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    reception_id = get_active_reception_id(product_data.pvz_id)
    if not reception_id:
        raise HTTPException(
            status_code=400,
            detail="В этом ПВЗ нет активной приёмки. Сначала создайте её.",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        product_id = str(uuid.uuid4())
        date_time = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO products (id, date_time, type, reception_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, date_time, type, reception_id
            """,
            (product_id, date_time, product_data.type, reception_id),
        )
        result = cur.fetchone()
        conn.commit()

        return {
            "id": result[0],
            "date_time": result[1],
            "type": result[2],
            "reception_id": result[3],
        }

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Ошибка при добавлении товара: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


@app.post("/pvz/{pvz_id}/delete_last_product")
def delete_last_product(
    pvz_id: str,
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    product_id = get_last_product_id(pvz_id)
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Нет товаров для удаления или отсутствует активная приёмка",
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s RETURNING id", (product_id,))
        deleted = cur.fetchone()
        conn.commit()

        # if not deleted:
        #     raise HTTPException(status_code=404, detail="Товар не найден")

        return {"message": f"Товар {deleted[0]} удалён"}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Ошибка при удалении товара: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
