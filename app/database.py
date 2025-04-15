import psycopg2
from psycopg2 import sql
from app.config import settings


def get_db_connection():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME,
    )
    return conn


def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        with open("app/init_db.sql", "r") as f:
            sql_script = f.read()

        cur.execute(sql_script)
        conn.commit()
        print("Таблицы успешно созданы!")

    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
    finally:
        if conn:
            conn.close()
