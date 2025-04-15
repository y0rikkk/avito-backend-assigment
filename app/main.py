from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import init_db, get_db_connection
from app.security import create_access_token

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


from jose import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings


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
