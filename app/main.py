from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from jose import jwt
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import make_asgi_app, start_http_server
import uuid
import json
import multiprocessing
from datetime import datetime, timezone
from typing import Optional
from app.config import settings
from app.database import (
    init_db,
    has_active_reception,
    get_active_reception_id,
    get_last_product_id,
    get_pvz_list,
    get_db,
)
from app.security import *
from app.schemas import *
from app.metrics import *
from app.logger import logger
from app.grpc.grpc_server import serve as run_grpc_server


security = HTTPBearer()


def save_openapi_spec():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    with open("openapi.json", "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        logger.info("Документация openapi.json обновлена")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    save_openapi_spec()
    grpc_process = multiprocessing.Process(target=run_grpc_server)
    grpc_process.start()
    logger.info("Приложение запущено")
    yield
    logger.info("Приложение остановлено")


app = FastAPI(lifespan=lifespan)

instrumentator = Instrumentator()
instrumentator.add(
    metrics.requests(
        should_include_handler=False,
        should_include_method=False,
        should_include_status=False,
        metric_doc="Total number of requests",
    )
)
instrumentator.add(
    metrics.latency(
        should_include_handler=False,
        should_include_method=False,
        should_include_status=False,
    )
)
instrumentator.instrument(app)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
start_http_server(9000)


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


@app.post(
    "/dummyLogin",
    responses={
        200: {"model": Token, "description": "Успешная авторизация"},
        400: {"model": Error, "description": "Неверный запрос"},
    },
    response_model=Token,
)
def dummy_login(request: DummyLoginRequest):
    if request.role not in ["employee", "moderator"]:
        raise HTTPException(
            status_code=400,
            detail="Недопустимая роль. Допустимые значения: 'employee', 'moderator'",
        )

    token = create_access_token(role=request.role)
    return {"token": token}


@app.post(
    "/pvz",
    response_model=PVZ,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "ПВЗ создан"},
        400: {"model": Error, "description": "Неверный запрос"},
        403: {"model": Error, "description": "Доступ запрещен"},
    },
)
def create_pvz(
    pvz_data: PVZCreate,
    connection=Depends(get_db),
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
        conn = connection
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

        PVZ_CREATED.inc()
        return {"id": result[0], "registration_date": result[1], "city": result[2]}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/receptions",
    response_model=Reception,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Приемка создана"},
        400: {
            "model": Error,
            "description": "Неверный запрос или есть незакрытая приемка",
        },
        403: {"model": Error, "description": "Доступ запрещен"},
    },
)
def create_reception(
    reception_data: ReceptionCreate,
    connection=Depends(get_db),
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    if has_active_reception(connection, reception_data.pvz_id):
        raise HTTPException(
            status_code=400,
            detail="В этом ПВЗ уже есть активная приёмка. Закройте её перед созданием новой.",
        )

    conn = None
    try:
        conn = connection
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

        RECEPTIONS_CREATED.inc()
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


@app.post(
    "/products",
    response_model=Product,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Товар добавлен"},
        400: {
            "model": Error,
            "description": "Неверный запрос или нет активной приемки",
        },
        403: {"model": Error, "description": "Доступ запрещен"},
    },
)
def add_product(
    product_data: ProductCreate,
    connection=Depends(get_db),
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    reception_id = get_active_reception_id(connection, product_data.pvz_id)
    if not reception_id:
        raise HTTPException(
            status_code=400,
            detail="В этом ПВЗ нет активной приёмки. Сначала создайте её.",
        )

    conn = None
    try:
        conn = connection
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

        PRODUCTS_ADDED.inc()
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


@app.post(
    "/pvz/{pvz_id}/delete_last_product",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Товар удален"},
        400: {
            "model": Error,
            "description": "Неверный запрос, нет активной приемки или нет товаров для удаления",
        },
        403: {"model": Error, "description": "Доступ запрещен"},
    },
)
def delete_last_product(
    pvz_id: str,
    connection=Depends(get_db),
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    product_id = get_last_product_id(connection, pvz_id)
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Нет товаров для удаления или отсутствует активная приёмка",
        )

    conn = None
    try:
        conn = connection
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


@app.post(
    "/pvz/{pvz_id}/close_last_reception",
    response_model=Reception,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Приемка закрыта"},
        400: {"model": Error, "description": "Неверный запрос или приемка уже закрыта"},
        403: {"model": Error, "description": "Доступ запрещен"},
    },
)
def close_last_reception(
    pvz_id: str,
    connection=Depends(get_db),
    role: str = Depends(get_current_role),
):
    if role != "employee":
        raise HTTPException(status_code=403, detail="Только для сотрудников ПВЗ")

    reception_id = get_active_reception_id(connection, pvz_id)
    if not reception_id:
        raise HTTPException(status_code=400, detail="Нет активной приёмки для закрытия")

    conn = None
    try:
        conn = connection
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE receptions
            SET status = 'close'
            WHERE id = %s
            RETURNING id, date_time, pvz_id, status
            """,
            (reception_id,),
        )
        result = cur.fetchone()
        conn.commit()

        # if not result:
        #     raise HTTPException(status_code=404, detail="Приёмка не найдена")

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
            status_code=500, detail=f"Ошибка при закрытии приёмки: {str(e)}"
        )


@app.get(
    "/pvz",
    response_model=List[PVZNested],
    status_code=status.HTTP_200_OK,
)
def list_pvz(
    connection=Depends(get_db),
    start_date: Optional[datetime] = Query(
        None, description="Начальная дата диапазона"
    ),
    end_date: Optional[datetime] = Query(None, description="Конечная дата диапазона"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=30, description="Количество элементов на странице"),
    role: str = Depends(get_current_role),  # Проверка авторизации
):

    if role != "moderator" and role != "employee":
        raise HTTPException(
            status_code=403, detail="Только для модераторов и сотрудников"
        )

    pvz_data = get_pvz_list(connection, start_date, end_date, page, limit)
    return pvz_data


@app.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Пользователь создан"},
        400: {"model": Error, "description": "Неверный запрос"},
    },
)
def register_user(user_data: UserRegister, connection=Depends(get_db)):
    conn = None
    try:
        logger.info(f"Register attempt: email={user_data.email}, role={user_data.role}")
        conn = connection
        cur = conn.cursor()

        # Проверяем, что email уникален
        cur.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        if user_data.role not in ["employee", "moderator"]:
            raise HTTPException(
                status_code=400,
                detail="Недопустимая роль. Допустимые значения: 'employee', 'moderator'",
            )

        # Хешируем пароль
        hashed_password = hash_password(user_data.password)

        # Сохраняем пользователя
        user_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO users (id, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, role
            """,
            (user_id, user_data.email, hashed_password, user_data.role),
        )
        result = cur.fetchone()
        conn.commit()

        logger.info(f"User registered: id={result[0]}")
        return {"id": result[0], "email": result[1], "role": result[2]}

    except HTTPException as e:
        logger.warning(f"Register failed: {e.detail}")
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Register error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации: {str(e)}")


@app.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Успешная авторизация"},
        401: {"model": Error, "description": "Неверные учетные данные"},
    },
)
def login_user(user_data: UserLogin, connection=Depends(get_db)):
    conn = None
    try:
        logger.info(f"Login attempt: email={user_data.email}")
        conn = connection
        cur = conn.cursor()

        # Ищем пользователя по email
        cur.execute(
            "SELECT id, email, password_hash, role FROM users WHERE email = %s",
            (user_data.email,),
        )
        user = cur.fetchone()

        if not user or not verify_password(user_data.password, user[2]):
            raise HTTPException(status_code=401, detail="Неверный email или пароль")

        # Генерируем JWT-токен
        token_data = {
            "sub": user[0],  # user_id
            "role": user[3],  # role
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(
            token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

        logger.info(f"User logged in: email={user_data.email}")
        # return {"access_token": token, "token_type": "bearer"}
        return {"token": token}

    except HTTPException as e:
        logger.warning(f"Login failed: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при авторизации: {str(e)}")
