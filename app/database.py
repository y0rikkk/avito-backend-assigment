import psycopg2
from datetime import datetime
from typing import List
from app.config import settings


def get_db():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME,
    )
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME,
        )
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


def has_active_reception(connection, pvz_id: str) -> bool:
    """Проверяет, есть ли у ПВЗ активная приёмка (in_progress)."""
    conn = None
    try:
        conn = connection
        cur = conn.cursor()
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM receptions WHERE pvz_id = %s AND status = 'in_progress')",
            (pvz_id,),
        )
        return cur.fetchone()[0]
    except Exception as e:
        print(f"Ошибка при проверке активной приёмки: {e}")  # TODO поменять
        return True  # В случае ошибки считаем, что приёмка есть (для безопасности)


def get_active_reception_id(connection, pvz_id: str) -> str | None:
    """Возвращает ID активной приёмки (in_progress) для указанного ПВЗ или None."""
    conn = None
    try:
        conn = connection
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


def get_last_product_id(connection, pvz_id: str) -> str | None:
    """Возвращает ID последнего добавленного товара в активной приёмке ПВЗ или None."""
    conn = None
    try:
        conn = connection
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id 
            FROM products p
            JOIN receptions r ON p.reception_id = r.id
            WHERE r.pvz_id = %s AND r.status = 'in_progress'
            ORDER BY p.date_time DESC
            LIMIT 1
            """,
            (pvz_id,),
        )
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Ошибка при поиске последнего товара: {e}")
        return None


def get_pvz_list(
    connection,
    start_date: datetime = None,
    end_date: datetime = None,
    page: int = 1,
    limit: int = 10,
) -> List[dict]:
    """Возвращает список ПВЗ с приёмками и товарами, учитывая фильтры и пагинацию."""
    conn = None
    try:
        conn = connection
        cur = conn.cursor()

        # Базовый запрос
        query = """
        SELECT 
            pvz.id AS pvz_id,
            pvz.registration_date,
            pvz.city,
            r.id AS reception_id,
            r.date_time AS reception_date,
            r.status,
            pr.id AS product_id,
            pr.date_time AS product_date,
            pr.type
        FROM pvz
        LEFT JOIN receptions r ON pvz.id = r.pvz_id
        LEFT JOIN products pr ON r.id = pr.reception_id
        """

        # Условия фильтрации
        conditions = []
        params = []

        if start_date:
            conditions.append("r.date_time >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("r.date_time <= %s")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Сортировка и пагинация
        query += """
        ORDER BY pvz.registration_date DESC, r.date_time DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, (page - 1) * limit])

        cur.execute(query, params)
        rows = cur.fetchall()

        # Форматирование результата
        pvz_dict = {}
        for row in rows:
            pvz_id = row[0]
            if pvz_id not in pvz_dict:
                pvz_dict[pvz_id] = {
                    "id": pvz_id,
                    "registration_date": row[1],
                    "city": row[2],
                    "receptions": [],
                }

            if row[3]:  # Если есть приёмка
                reception = next(
                    (r for r in pvz_dict[pvz_id]["receptions"] if r["id"] == row[3]),
                    None,
                )
                if not reception:
                    reception = {
                        "id": row[3],
                        "date_time": row[4],
                        "status": row[5],
                        "products": [],
                    }
                    pvz_dict[pvz_id]["receptions"].append(reception)

                if row[6]:  # Если есть товар
                    reception["products"].append(
                        {"id": row[6], "date_time": row[7], "type": row[8]}
                    )

        return list(pvz_dict.values())

    except Exception as e:
        print(f"Ошибка при получении списка ПВЗ: {e}")
        return []
