from datetime import datetime, timedelta, timezone

import pytest
from config import config
from faker import Faker
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from models.user import User
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

fake = Faker()


def _make_user(db_session, **overrides):
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}"
    email = fake.unique.email()
    password = fake.password(length=12)
    city = fake.city()
    country = fake.country()
    hashed_pwd = hash_password(password)
    data = {
        "first_name": first,
        "last_name": last,
        "email": email,
        "user_name": username,
        "hashed_password": hashed_pwd,
        "city": city,
        "country": country,
    }
    data.update(overrides)
    u = User(**data)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_hash_and_verify_ok():
    hp = hash_password("abc123")
    assert hp != "abc123"
    assert verify_password("abc123", hp) is True


def test_verify_password_fail():
    hp = hash_password("abc123")
    assert verify_password("wrong", hp) is False


def test_create_access_token_structure(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN_EXPIRE_MINUTES", 1)
    token, minutes = create_access_token({"sub": "1"})
    assert isinstance(token, str)
    assert minutes == 1
    payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "1"
    assert "exp" in payload


def test_get_current_user_no_credentials_401(db_session):
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=None, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_wrong_scheme_401(db_session):
    creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="whatever")
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=creds, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_invalid_token_401(db_session):
    creds = _bearer("not-a-jwt")
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=creds, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_token_without_sub_401(db_session):
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode({"exp": exp}, config.SECRET_KEY, algorithm="HS256")
    creds = _bearer(token)
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=creds, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_user_not_found_401(db_session):
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"exp": exp, "sub": "999999"}, config.SECRET_KEY, algorithm="HS256"
    )
    creds = _bearer(token)
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=creds, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_inactive_401(db_session):
    u = _make_user(db_session, is_active=False)
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"exp": exp, "sub": str(u.id)}, config.SECRET_KEY, algorithm="HS256"
    )
    creds = _bearer(token)
    with pytest.raises(Exception) as exc:
        get_current_user(credentials=creds, db=db_session)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_ok(db_session):
    u = _make_user(db_session, is_active=True)
    token, _ = create_access_token({"sub": str(u.id)})
    user = get_current_user(credentials=_bearer(token), db=db_session)
    assert user.id == u.id
    assert user.is_active is True
