from datetime import datetime, timedelta, timezone

from config import config
from database import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from models import User
from passlib.context import CryptContext
from sqlalchemy.orm import Session

AUTH_ERROR_MSG = "Falta de autenticación."

pwd = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, str]) -> tuple[str, int]:
    minutes = config.ACCESS_TOKEN_EXPIRE_MINUTES
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    token = jwt.encode({"exp": exp, **data}, config.SECRET_KEY, algorithm="HS256")
    return token, minutes


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR_MSG
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR_MSG
            )
        user_id = int(sub)
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR_MSG
        )
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR_MSG
        )
    return user
