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

@pytest.fixture()
def mock_storage_delete(monkeypatch):
    def _fake_delete(path):
        print(f"Faking delete for {path}")
        return

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
