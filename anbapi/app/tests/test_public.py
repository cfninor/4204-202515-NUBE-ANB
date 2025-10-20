
import pytest
from faker import Faker
from models import User, Video, VideoStatus
from security import hash_password

fake = Faker()


@pytest.fixture()
def test_user(db_session):
    """Fixture para crear un usuario de prueba en la BD."""
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
def seed_videos(db_session, test_user):
    """Fixture para crear videos de prueba con diferentes estados."""
    videos_data = [
        {"title": "Video Procesado 1", "status": VideoStatus.PROCESSED},
        {"title": "Video Subido", "status": VideoStatus.UPLOADED},
        {"title": "Video Procesado 2", "status": VideoStatus.PROCESSED},
        {"title": "Video Fallido", "status": VideoStatus.FAILED},
    ]

    for data in videos_data:
        video = Video(
            user_id=test_user.id,
            title=data["title"],
            original_url=f"/fake/{fake.uuid4()}.mp4",
            processed_url=f"/fake/processed/{fake.uuid4()}.mp4",
            status=data["status"],
            task_id=fake.uuid4(),
        )
        db_session.add(video)
    db_session.commit()


def test_list_public_videos_returns_processed_videos(client, seed_videos):
    """Prueba que el endpoint devuelve solo los videos con estado 'PROCESSED'."""
    response = client.get("/api/public/videos")

    assert response.status_code == 200
    data = response.json()

    # Deben haber 2 videos procesados
    assert len(data) == 2

    # Verificar que todos los videos devueltos tienen el estado correcto
    for video in data:
        assert video["status"] == VideoStatus.PROCESSED

    # Verificar que los títulos son los correctos
    titles = {v["title"] for v in data}
    assert "Video Procesado 1" in titles
    assert "Video Procesado 2" in titles
    assert "Video Subido" not in titles


def test_list_public_videos_returns_message_when_no_videos(client):
    """Prueba que el endpoint devuelve un mensaje cuando no hay videos procesados."""
    response = client.get("/api/public/videos")

    assert response.status_code == 200
    data = response.json()

    assert data == {"message": "No hay videos disponibles para votación."}
