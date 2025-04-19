from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.config import settings
import psycopg2
import pytest


def override_get_db():
    conn = psycopg2.connect(
        host=settings.TEST_DB_HOST,
        port=settings.TEST_DB_PORT,
        user=settings.TEST_DB_USER,
        password=settings.TEST_DB_PASSWORD,
        dbname=settings.TEST_DB_NAME,
    )
    try:
        yield conn
    finally:
        conn.close()


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


def test_dummy_login_success():
    # Проверка успешного входа через dummy login
    response = client.post("/dummyLogin", json={"role": "moderator"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_dummy_login_invalid_role():
    # Проверка недопустимой роли при входе через dummy login
    response = client.post("/dummyLogin", json={"role": "admin"})
    assert response.status_code == 400


def test_create_pvz():
    # Получаем токен модератора
    login_response = client.post("/dummyLogin", json={"role": "moderator"})
    token = login_response.json()["access_token"]

    # Успешное создание ПВЗ
    response = client.post(
        "/pvz", json={"city": "Москва"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "id" in response.json()

    # Попытка создать ПВЗ с недопустимым городом
    response = client.post(
        "/pvz",
        json={"city": "Владивосток"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400

    # Попытка создать ПВЗ без прав (employee)
    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]
    response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_create_reception():
    # Создаём ПВЗ (от имени модератора)
    moderator_token = client.post("/dummyLogin", json={"role": "moderator"}).json()[
        "access_token"
    ]
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    pvz_id = pvz_response.json()["id"]

    # Получаем токен сотрудника
    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]

    # Успешное создание приёмки
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Попытка создать вторую приёмку (должна быть ошибка)
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400

    # Попытка создать приёмку без прав (модератором)
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 403


def test_add_product():
    # Создаём ПВЗ и приёмку
    moderator_token = client.post("/dummyLogin", json={"role": "moderator"}).json()[
        "access_token"
    ]
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    pvz_id = pvz_response.json()["id"]

    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]
    reception_response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )

    # Успешное добавление товара
    response = client.post(
        "/products",
        json={"type": "одежда", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["type"] == "одежда"

    # Попытка добавить товар без активной приёмки (закроем приёмку)
    client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = client.post(
        "/products",
        json={"type": "электроника", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_delete_last_product():
    # Создаём ПВЗ, приёмку и добавляем товары
    moderator_token = client.post("/dummyLogin", json={"role": "moderator"}).json()[
        "access_token"
    ]
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    pvz_id = pvz_response.json()["id"]

    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]
    client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )

    # Добавляем 2 товара
    client.post(
        "/products",
        json={"type": "одежда", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    client.post(
        "/products",
        json={"type": "электроника", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )

    # Удаляем последний товар (электроника)
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert "электроника" not in response.text  # Проверяем, что удалён последний

    # Попытка удалить из закрытой приёмки
    client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_close_last_reception():
    # Создаём ПВЗ и приёмку
    moderator_token = client.post("/dummyLogin", json={"role": "moderator"}).json()[
        "access_token"
    ]
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    pvz_id = pvz_response.json()["id"]

    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]
    reception_response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    reception_id = reception_response.json()["id"]

    # Успешное закрытие приёмки
    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "close"

    # Попытка закрыть уже закрытую приёмку
    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_get_pvz_list():
    # Создаём тестовые данные
    moderator_token = client.post("/dummyLogin", json={"role": "moderator"}).json()[
        "access_token"
    ]
    pvz_response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    pvz_id = pvz_response.json()["id"]

    employee_token = client.post("/dummyLogin", json={"role": "employee"}).json()[
        "access_token"
    ]
    reception_response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    client.post(
        "/products",
        json={"type": "электроника", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )

    # Запрос списка
    response = client.get(
        "/pvz", headers={"Authorization": f"Bearer {moderator_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert response.json()[0]["id"] == pvz_id


def test_register_and_login():
    # Регистрация
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "test123", "role": "moderator"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

    # Логин с правильным паролем
    response = client.post(
        "/login", json={"email": "test@example.com", "password": "test123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Логин с неверным паролем
    response = client.post(
        "/login", json={"email": "test@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
