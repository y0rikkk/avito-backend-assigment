from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dummy_login_success():
    # Проверка успешного входа через dummy login
    response = client.post("/dummyLogin", json={"role": "moderator"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_dummy_login_invalid_role():
    # Проверка недопустимой роли при входе через dummy login
    response = client.post("/dummyLogin", json={"role": "admin"})
    assert response.status_code == 400
