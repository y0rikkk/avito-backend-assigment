import pytest
import psycopg2
import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.config import settings
from tests.conftest import moderator_token, employee_token, override_get_db


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Фикстура для очистки всех таблиц после теста."""
    conn = psycopg2.connect(
        host=settings.TEST_DB_HOST,
        port=settings.TEST_DB_PORT,
        user=settings.TEST_DB_USER,
        password=settings.TEST_DB_PASSWORD,
        dbname=settings.TEST_DB_NAME,
    )
    cur = conn.cursor()

    with open("tests/init_test_db.sql", "r") as f:
        sql_script = f.read()

    cur.execute(sql_script)
    conn.commit()
    conn.close()


def test_full_reception_flow(moderator_token, employee_token):
    # Создаём ПВЗ
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert pvz_response.status_code == 201
    pvz_id = pvz_response.json()["id"]

    # Создаём приёмку
    reception_response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert reception_response.status_code == 201

    # Добавляем 50 товаров
    for i in range(50):
        # product_type = "электроника" if i % 2 == 0 else "одежда"
        product_type = ["электроника", "одежда", "обувь"][i % 3]
        response = client.post(
            "/products",
            json={"type": product_type, "pvz_id": pvz_id},
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert response.status_code == 201

    # Закрываем приёмку
    close_response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "close"

    # Проверяем, что приёмка закрыта
    date = datetime.date.today()
    url = f"/pvz?start_date={date}&page=1&limit=30"
    db_response = client.get(
        url,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert db_response.status_code == 200
    assert db_response.json()[0]["receptions"][0]["reception"]["status"] == "close"
    assert len(db_response.json()[0]["receptions"][0]["products"]) == 30

    url = f"/pvz?start_date={date}&page=2&limit=30"
    db_response = client.get(
        url,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert db_response.status_code == 200
    assert db_response.json()[0]["receptions"][0]["reception"]["status"] == "close"
    assert len(db_response.json()[0]["receptions"][0]["products"]) == 20
