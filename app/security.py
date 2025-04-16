from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
from app.config import settings


def create_access_token(role: str) -> str:
    payload = {
        "sub": "dummy_user",  # Условный идентификатор пользователя
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def hash_password(password):
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        password=plain_password.encode("utf-8"),
        hashed_password=hashed_password.encode("utf-8"),
    )
