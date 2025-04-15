from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt
import uuid
from datetime import datetime, timezone
from app.config import settings
from app.database import init_db, get_db_connection
from app.security import create_access_token
from app.schemas import PVZCreate, PVZResponse

app = FastAPI()

security = HTTPBearer()


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


@app.get("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        conn.close()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/check-token")
def check_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return {"role": payload["role"], "expires": payload["exp"]}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Неверный токен")


@app.post("/pvz", response_model=PVZResponse)
def create_pvz(
    pvz_data: PVZCreate,
    role: str = Depends(get_current_role),
):
    if role != "moderator":
        raise HTTPException(status_code=403, detail="Только для модераторов")

    allowed_cities = ["Moscow", "Saint Petersburg", "Kazan"]
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
