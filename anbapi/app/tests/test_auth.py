import pytest
from faker import Faker

fake = Faker()


def creacion_usuario():
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}"
    email = fake.unique.email()
    password = fake.password(length=12)
    city = fake.city()
    country = fake.country()
    return {
        "first_name": first,
        "last_name": last,
        "email": email,
        "username": username,
        "password": password,
        "password2": password,
        "city": city,
        "country": country,
    }


def test_registro_usuario(client):
    res = client.post("/api/auth/signup", json=creacion_usuario())
    assert res.status_code == 201, res.text
    assert "Usuario creado exitosamente" in res.json()["message"]


def test_registro_passwords_no_coinciden(client):
    data = creacion_usuario()
    data["password2"] = data["password"] + "x"
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "Constraseñas no coinciden"


def test_registro_email_duplicado(client):
    base = creacion_usuario()
    res1 = client.post("/api/auth/signup", json=base)
    assert res1.status_code == 201, res1.text
    otro = creacion_usuario()
    otro["email"] = base["email"]
    res2 = client.post("/api/auth/signup", json=otro)
    assert res2.status_code == 400, res2.text
    assert res2.json()["detail"] == "Email duplicado"


def test_login_exitoso(client):
    user = creacion_usuario()
    res_reg = client.post("/api/auth/signup", json=user)
    assert res_reg.status_code == 201, res_reg.text
    res_log = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert res_log.status_code == 200, res_log.text
    body = res_log.json()
    assert "access_token" in body and body["access_token"]
    assert "expires_in" in body and isinstance(body["expires_in"], int)
    assert body["expires_in"] > 0
    assert body["token_type"] == "bearer"


def test_login_credenciales_invalidas(client):
    user = creacion_usuario()
    res_reg = client.post("/api/auth/signup", json=user)
    assert res_reg.status_code == 201
    res = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": user["password"] + "!"},
    )
    assert res.status_code == 401, res.text
    assert res.json()["detail"] == "Credenciales inválidas"


def test_registro_email_invalido_422(client):
    data = creacion_usuario()
    data["email"] = "correo-invalido"
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 422, res.text


@pytest.mark.parametrize(
    "campo", ["email", "first_name", "last_name", "password", "password2", "username"]
)
def test_registro_campo_faltante_422(client, campo):
    data = creacion_usuario()
    data.pop(campo)
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 422, res.text
