import pytest
import psycopg2
from app.logger import logger
from app.security import create_access_token, settings


@pytest.fixture(autouse=True)
def disable_app_logger():
    logger.disabled = True
    yield
    logger.disabled = False


@pytest.fixture
def moderator_token():
    return create_access_token(role="moderator")


@pytest.fixture
def employee_token():
    return create_access_token(role="employee")


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
