from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.config import settings
import psycopg2
import pytest
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

    with open("tests/init_test_db.sql", "r", encoding="CP1251") as f:
        sql_script = f.read()

    cur.execute(sql_script)
    conn.commit()
    conn.close()


def test_dummy_login_success():
    # Проверка успешного входа через dummy login
    response = client.post("/dummyLogin", json={"role": "moderator"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_dummy_login_invalid_role():
    # Проверка недопустимой роли при входе через dummy login
    response = client.post("/dummyLogin", json={"role": "admin"})
    assert response.status_code == 400


def test_create_pvz_success(moderator_token):
    # Успешное создание ПВЗ
    response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 201
    assert "id" in response.json()


def test_create_pvz_invalid_city(moderator_token):
    # Попытка создать ПВЗ с недопустимым городом
    response = client.post(
        "/pvz",
        json={"city": "Владивосток"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 400


def test_create_pvz_invalid_role(employee_token):
    # Попытка создать ПВЗ без прав (employee)
    response = client.post(
        "/pvz",
        json={"city": "Москва"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_create_reception_success(employee_token):
    # Успешное создание приёмки
    pvz_id = "44444444-4444-4444-4444-444444444444"
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "in_progress"


def test_create_second_reception(employee_token):
    # Попытка создать вторую приёмку (должна быть ошибка)
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_create_reception_invalid_role(moderator_token):
    pvz_id = "44444444-4444-4444-4444-444444444444"
    # Попытка создать приёмку без прав (модератором)
    response = client.post(
        "/receptions",
        json={"pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 403


def test_add_product_success(employee_token):
    # Успешное добавление товара
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        "/products",
        json={"type": "одежда", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 201
    assert response.json()["type"] == "одежда"


def test_add_product_invalid_type(employee_token):
    # Попытка добавить товар с неправильной категорией
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        "/products",
        json={"type": "еда", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_add_product_invalid_type(moderator_token):
    # Попытка добавить товар с неправильной ролью (модератор)
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        "/products",
        json={"type": "одежда", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 403


def test_add_product_in_closed_reception(employee_token):
    # Попытка добавить товар без активной приёмки
    pvz_id = "44444444-4444-4444-4444-444444444444"
    response = client.post(
        "/products",
        json={"type": "электроника", "pvz_id": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_delete_last_product_success(employee_token):
    # Удаляем последний товар
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert "cccccccc-cccc-cccc-cccc-cccccccccccc" in response.text


def test_delete_last_product_no_product_available(employee_token):
    # Попытка удалить последний товар из пустой приемки
    pvz_id = "66666666-6666-6666-6666-666666666666"
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_delete_last_product_invalid_role(moderator_token):
    # Попытка удалить последний товар с неправильной ролью (модератор)
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 403


def test_delete_last_product_reception_closed(employee_token):
    # Попытка удалить из закрытой приёмки
    pvz_id = "44444444-4444-4444-4444-444444444444"
    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_close_last_reception_success(employee_token):
    # Успешное закрытие приёмки
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "close"


def test_close_last_reception_invalid_role(moderator_token):
    # Попытка закрыть приёмку с неправильной ролью (модератор)
    pvz_id = "55555555-5555-5555-5555-555555555555"
    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 403


def test_close_last_reception_already_closed(employee_token):
    # Попытка закрыть уже закрытую приёмку
    pvz_id = "44444444-4444-4444-4444-444444444444"
    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_get_pvz_list_success(moderator_token):
    # Запрос списка пвз
    response = client.get(
        "/pvz", headers={"Authorization": f"Bearer {moderator_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_pvz_list_unauthorized():
    # Запрос списка пвз без авторизации
    response = client.get("/pvz")
    assert response.status_code == 403


def test_register_success():
    # Успешная регистрация
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "test123", "role": "moderator"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


def test_register_invalid_role():
    # Попытка регистарции с неправильной ролью
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "test123", "role": "client"},
    )
    assert response.status_code == 400


def test_register_email_already_taken():
    # Попытка регистарции уже занятого email
    response = client.post(
        "/register",
        json={
            "email": "moderator@example.com",
            "password": "test123",
            "role": "moderator",
        },
    )
    assert response.status_code == 400


def test_login_success():
    # Логин с правильным паролем
    response = client.post(
        "/login", json={"email": "moderator@example.com", "password": "123456"}
    )
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_invalid_password():
    # Логин с неверным паролем
    response = client.post(
        "/login", json={"email": "moderator@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_login_invalid_email():
    response = client.post(
        "/login", json={"email": "employee3@example.com", "password": "123456"}
    )
    assert response.status_code == 401
