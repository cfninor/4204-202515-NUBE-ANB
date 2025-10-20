import pytest
from faker import Faker
from models.user import User
from models.video import Video
from models.videoStatus import VideoStatus
from security import hash_password

fake = Faker()


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
def created_video(db_session, test_user):
    v = Video(
        user_id=test_user.id,
        title="video prueba",
        original_url="/fake.mp4",
        task_id="test-task",
        status=VideoStatus.UPLOADED,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


def test_vote_success(client, auth_user_override, created_video):
    resp = client.post(f"/api/public/videos/{created_video.id}/vote")
    assert resp.status_code == 201
    body = resp.json()
    assert body.get("message") == "Voto registrado exitosamente."


def test_vote_duplicate(client, auth_user_override, created_video):
    # first vote
    resp1 = client.post(f"/api/public/videos/{created_video.id}/vote")
    assert resp1.status_code == 201
    # duplicate
    resp2 = client.post(f"/api/public/videos/{created_video.id}/vote")
    assert resp2.status_code == 400
    assert "ya vot" in resp2.text.lower()


def test_vote_unauthenticated(client, created_video):
    resp = client.post(f"/api/public/videos/{created_video.id}/vote")
    assert resp.status_code == 401


def test_vote_not_found(client, auth_user_override):
    resp = client.post(f"/api/public/videos/9999999/vote")
    assert resp.status_code == 404
    assert "no encontrado" in resp.text.lower()
