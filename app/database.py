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


def has_active_reception(pvz_id: str) -> bool:
    """Проверяет, есть ли у ПВЗ активная приёмка (in_progress)."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM receptions WHERE pvz_id = %s AND status = 'in_progress')",
            (pvz_id,),
        )
        return cur.fetchone()[0]
    except Exception as e:
        print(f"Ошибка при проверке активной приёмки: {e}")
        return True  # В случае ошибки считаем, что приёмка есть (для безопасности)
    finally:
        if conn:
            conn.close()


def get_active_reception_id(pvz_id: str) -> str | None:
    """Возвращает ID активной приёмки (in_progress) для указанного ПВЗ или None."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM receptions WHERE pvz_id = %s AND status = 'in_progress' LIMIT 1",
            (pvz_id,),
        )
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Ошибка при поиске активной приёмки: {e}")
        return None
    finally:
        if conn:
            conn.close()
