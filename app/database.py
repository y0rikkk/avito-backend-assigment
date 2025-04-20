import psycopg2
from datetime import datetime
from typing import List
from app.config import settings
from app.logger import logger

import psycopg2.extras

psycopg2.extras.register_uuid()


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
        logger.info("БД инициализирована")

    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
    finally:
        if conn:
            conn.close()


def has_active_reception(connection, pvz_id) -> bool:
    """Проверяет, есть ли у ПВЗ активная приёмка (in_progress)."""
    conn = None
    try:
        conn = connection
        cur = conn.cursor()
        cur.execute(
            "(SELECT 1 FROM receptions WHERE pvz_id = %s AND status = 'in_progress')",
            (pvz_id,),
        )
        if cur.fetchone():
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке активной приёмки: {e}")
        raise


def get_active_reception_id(connection, pvz_id) -> str | None:
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
        logger.error(f"Ошибка при поиске активной приёмки: {e}")
        raise


def get_last_product_id(connection, pvz_id) -> str | None:
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
        logger.error(f"Ошибка при поиске последнего товара: {e}")
        raise


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

        # Группировка данных
        result = []
        current_pvz = None
        current_reception = None

        for row in rows:
            (
                pvz_id,
                reg_date,
                city,
                reception_id,
                reception_date,
                status,
                product_id,
                product_date,
                product_type,
            ) = row

            # Если это новый ПВЗ
            if not current_pvz or current_pvz["pvz"]["id"] != pvz_id:
                current_pvz = {
                    "pvz": {
                        "id": pvz_id,
                        "registration_date": reg_date.isoformat(),
                        "city": city,
                    },
                    "receptions": [],
                }
                result.append(current_pvz)

            # Если есть приёмка и она новая
            if reception_id and (
                not current_reception
                or current_reception["reception"]["id"] != reception_id
            ):
                current_reception = {
                    "reception": {
                        "id": reception_id,
                        "date_time": reception_date.isoformat(),
                        "pvz_id": current_pvz["pvz"]["id"],
                        "status": status,
                    },
                    "products": [],
                }
                current_pvz["receptions"].append(current_reception)

            # Если есть товар
            if product_id:
                current_reception["products"].append(
                    {
                        "id": product_id,
                        "date_time": product_date.isoformat(),
                        "type": product_type,
                        "reception_id": current_reception["reception"]["id"],
                    }
                )

        return result

    except Exception as e:
        logger.error(f"Ошибка при получении списка ПВЗ: {e}")
        raise
