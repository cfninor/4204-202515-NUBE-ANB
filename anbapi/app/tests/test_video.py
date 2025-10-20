import io
import uuid

import pytest
from faker import Faker
from models.user import User
from security import hash_password
from services import video

fake = Faker()


class DummyTask:
    def __init__(self):
        self.id = str(uuid.uuid4())


@pytest.fixture()
def test_user(db_session):
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}"
    email = fake.unique.email()
    password = fake.password(length=12)
    city = fake.city()
    country = fake.country()
    hashed_pwd = hash_password(password)
    u = User(
        first_name=first,
        last_name=last,
        email=email,
        user_name=username,
        hashed_password=hashed_pwd,
        city=city,
        country=country,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def auth_user_override(app, test_user):
    from security import get_current_user

    def _override():
        return test_user

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def mock_storage_save(monkeypatch, tmp_path):
    def _fake_save(name, fileobj):
        fileobj.read()
        return f"/fake/storage/{name}"

    monkeypatch.setattr(video.storage, "save", _fake_save)
    return _fake_save


@pytest.fixture()
def mock_celery_delay(monkeypatch):
    def _fake_delay(*args, **kwargs):
        return DummyTask()

    monkeypatch.setattr(video.process_video, "delay", _fake_delay)
    return _fake_delay


def _multipart_mp4(size_bytes: int):
    data = b"\x00" * size_bytes
    file = ("video.mp4", io.BytesIO(data), "video/mp4")
    return file


def test_upload_ok(
    client,
    auth_user_override,
    test_user,
    mock_storage_save,
    mock_celery_delay,
    db_session,
):
    files = {"video_file": _multipart_mp4(1024)}
    data = {"title": "mi video"}

    resp = client.post("/api/videos/upload", files=files, data=data)

    assert resp.status_code == 201
    body = resp.json()
    assert "message" in body and "procesamiento en curso" in body["message"]
    assert "task_id" in body
    from models import Video

    saved = db_session.query(Video).order_by(Video.id.desc()).first()
    assert saved is not None
    assert saved.user_id == test_user.id
    assert saved.title == "mi video"
    assert saved.original_url.startswith("/fake/storage/")
    from models import VideoStatus

    assert saved.status == VideoStatus.UPLOADED
    assert saved.id == body["task_id"]


def test_upload_tipo_invalido(client, auth_user_override):
    files = {
        "video_file": ("mal.txt", io.BytesIO(b"hola"), "text/plain"),
    }
    data = {"title": "malo"}
    resp = client.post("/api/videos/upload", files=files, data=data)
    assert resp.status_code == 400
    assert "tipo" in resp.text.lower()


def test_upload_tamano_excedido(client, auth_user_override, monkeypatch):
    monkeypatch.setattr(video, "MAX_FILE_SIZE_BYTES", 10)
    files = {"video_file": _multipart_mp4(20)}
    data = {"title": "grande"}

    resp = client.post("/api/videos/upload", files=files, data=data)
    assert resp.status_code == 400
    assert "tamaño" in resp.text.lower()


def test_upload_sin_auth(client):
    files = {"video_file": _multipart_mp4(100)}
    data = {"title": "x"}
    resp = client.post("/api/videos/upload", files=files, data=data)
    assert resp.status_code == 401

# --------------------------- /api/videos & /api/videos/id  ---------------------------
from fastapi.testclient import TestClient # noqa: E402

# app (ajusta el import si tu módulo es distinto)
try:
    from main import app  # p.ej. si tu asgi está en main.py (raíz)
except ImportError:
    from app.main import app  # p.ej. si está en app/main.py

from database import SessionLocal # noqa: E402
from models import Video, VideoStatus # noqa: E402
from security import get_current_user # noqa: E402

class _DummyUser:
    id = 1
    email = "demo@acme.com"

def _override_get_current_user():
    return _DummyUser()

client = TestClient(app)

def _seed_data():
    db = SessionLocal()
    u1 = db.query(User).filter(User.id == 1).first()
    if not u1:
        u1 = User(
            id=1,
            first_name="Demo",
            last_name="User",
            email="demo@acme.com",
            user_name="demo",
            hashed_password="x",
            is_active=True,
        )
        db.add(u1)
    u2 = db.query(User).filter(User.id == 2).first()
    if not u2:
        u2 = User(
            id=2,
            first_name="Other",
            last_name="User",
            email="other@acme.com",
            user_name="other",
            hashed_password="x",
            is_active=True,
        )
        db.add(u2)
    db.commit()
    db.query(Video).delete()
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    v1 = Video(
        user_id=1,
        title="Video subido",
        status=VideoStatus.UPLOADED,
        uploaded_at=now - timedelta(days=1),
        processed_at=None,
        original_url="http://localhost/media/originals/v1.mp4",
        processed_url=None,
        task_id="task-1",
    )
    v2 = Video(
        user_id=1,
        title="Video procesado",
        status=VideoStatus.PROCESSED,
        uploaded_at=now - timedelta(days=2),
        processed_at=now - timedelta(days=2, hours=-1),
        original_url="http://localhost/media/originals/v2.mp4",
        processed_url="http://localhost/media/processed/v2.mp4",
        task_id="task-2",
    )
    v3 = Video(
        user_id=2,
        title="De otro usuario",
        status=VideoStatus.PROCESSED,
        uploaded_at=now - timedelta(days=3),
        processed_at=now - timedelta(days=3, hours=-1),
        original_url="http://localhost/media/originals/v3.mp4",
        processed_url="http://localhost/media/processed/v3.mp4",
        task_id="task-3",
    )
    db.add_all([v1, v2, v3])
    db.commit()
    db.refresh(v1)
    db.refresh(v2)
    db.refresh(v3)
    db.close()
    return v1.id, v2.id, v3.id

def _is_iso_z(s):
    if s is None:
        return True
    return isinstance(s, str) and s.endswith("Z")

def test_get_videos_ok_y_reglas_processed_url():
    app.dependency_overrides[get_current_user] = _override_get_current_user
    v1_id, v2_id, _ = _seed_data()

    r = client.get("/api/videos")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) >= 2

    # Chequea nombres de campos del anexo
    sample = body[0]
    for key in ("video_id", "title", "status", "uploaded_at", "processed_at"):
        assert key in sample

    # processed_url solo si status == "processed"
    by_id = {int(item["video_id"]): item for item in body}
    assert by_id[v1_id]["status"] in ("uploaded", "processed")
    assert by_id[v2_id]["status"] == "processed"

    assert by_id[v1_id].get("processed_url") in (None, None)  # explícitamente ausente o null
    assert isinstance(by_id[v2_id].get("processed_url"), str)

    # formato ISO con Z
    assert _is_iso_z(by_id[v1_id]["uploaded_at"])
    assert _is_iso_z(by_id[v1_id]["processed_at"])

def test_get_video_detail_ok_campos_y_urls():
    app.dependency_overrides[get_current_user] = _override_get_current_user
    _, v2_id, _ = _seed_data()

    r = client.get(f"/api/videos/{v2_id}")
    assert r.status_code == 200
    v = r.json()

    # Campos del anexo
    for key in ("video_id", "title", "status", "uploaded_at", "processed_at", "original_url"):
        assert key in v

    # processed -> debe venir processed_url
    if v["status"] == "processed":
        assert isinstance(v.get("processed_url"), str)

    # votos puede existir (si tu modelo lo trae)
    assert "votes" in v

    # formato ISO con Z
    assert _is_iso_z(v["uploaded_at"])
    assert _is_iso_z(v["processed_at"])

def test_get_video_detail_403_no_propietario():
    app.dependency_overrides[get_current_user] = _override_get_current_user
    _, _, other_user_video_id = _seed_data()

    # El video pertenece al user_id=2 -> actual (user_id=1) debe recibir 403
    r = client.get(f"/api/videos/{other_user_video_id}")
    assert r.status_code == 403
    assert "no tiene permisos" in r.json()["detail"].lower()

def test_get_video_detail_404_inexistente():
    app.dependency_overrides[get_current_user] = _override_get_current_user
    _seed_data()

    r = client.get("/api/videos/99999999")
    assert r.status_code == 404
    assert "no existe" in r.json()["detail"].lower() or "no pertenece" in r.json()["detail"].lower()

def test_get_videos_401_sin_autenticacion():
    # Quita override para probar 401 real
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    _seed_data()

    r = client.get("/api/videos")  # sin Authorization
    assert r.status_code == 401  # mensaje exacto depende de tu get_current_user

def test_get_video_detail_401_sin_autenticacion():
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    _seed_data()

    r = client.get("/api/videos/1")  # sin Authorization
    assert r.status_code == 401
    
@pytest.fixture()
def mock_storage_delete(monkeypatch):
    def _fake_delete(path):
        print(f"Faking delete for {path}")
        return ""

    monkeypatch.setattr(video.storage, "delete", _fake_delete)
    return _fake_delete

@pytest.fixture()
def test_video(db_session, test_user):
    from models import Video, VideoStatus
    v = Video(
        user_id=test_user.id,
        title="video de prueba",
        original_url="/fake/storage/video.mp4",
        status=VideoStatus.PROCESSED,
        task_id="fake_task_id"
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v

def test_delete_video_ok(client, auth_user_override, test_video, mock_storage_delete, db_session):
    video_id = test_video.id
    resp = client.delete(f"/api/videos/{video_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body
    assert "eliminado exitosamente" in body["message"]
    assert body["video_id"] == str(video_id)

    from models import Video
    deleted_video = db_session.query(Video).filter(Video.id == video_id).first()
    assert deleted_video is None

def test_delete_video_not_found(client, auth_user_override, mock_storage_delete):
    video_id = 999999  # Use a non-existent integer ID
    resp = client.delete(f"/api/videos/{video_id}")
    assert resp.status_code == 404

def test_delete_video_unauthorized(client, test_video):
    video_id = test_video.id
    resp = client.delete(f"/api/videos/{video_id}")
    assert resp.status_code == 401

@pytest.fixture()
def other_user(db_session):
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}"
    email = fake.unique.email()
    password = fake.password(length=12)
    hashed_pwd = hash_password(password)
    u = User(
        first_name=first,
        last_name=last,
        email=email,
        user_name=username,
        hashed_password=hashed_pwd,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u

@pytest.fixture()
def other_video(db_session, other_user):
    from models import Video, VideoStatus
    v = Video(
        user_id=other_user.id,
        title="video ajeno",
        original_url="/fake/storage/video_ajeno.mp4",
        status=VideoStatus.PROCESSED,
        task_id="fake_task_id_other"
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v

def test_delete_video_not_owned(client, auth_user_override, other_video, mock_storage_delete):
    video_id = other_video.id
    resp = client.delete(f"/api/videos/{video_id}")
    assert resp.status_code == 404 # The service returns 404 in this case