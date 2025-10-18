from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from anbapi.app.database import get_db
from anbapi.app.models import User
from anbapi.app.schemas import (
    LogInRequestSchema,
    LogInResponseSchema,
    SignUpRequestSchema,
)
from anbapi.app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def sign_up(user: SignUpRequestSchema, db: Session = Depends(get_db)):
    if user.password != user.password2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Constraseñas no coinciden"
        )

    existing_user = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email duplicado"
        )

    hashed_pwd = hash_password(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        user_name=user.username,
        hashed_password=hashed_pwd,
        city=user.city,
        country=user.country,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Usuario creado exitosamente"}


@router.post(
    "/login", response_model=LogInResponseSchema, status_code=status.HTTP_200_OK
)
def login(credentials: LogInRequestSchema, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.email == credentials.email)
    ).scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    token_data = {"sub": str(user.id)}
    access_token, expires_in = create_access_token(token_data)

    return LogInResponseSchema(access_token=access_token, expires_in=expires_in)
