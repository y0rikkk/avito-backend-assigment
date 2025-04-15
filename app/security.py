from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import settings


def create_access_token(role: str) -> str:
    payload = {
        "sub": "dummy_user",  # Условный идентификатор пользователя
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
