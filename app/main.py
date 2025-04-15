from fastapi import FastAPI, HTTPException
from app.database import init_db, get_db_connection

app = FastAPI()


@app.on_event("startup")
def startup_event():
    init_db()


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
