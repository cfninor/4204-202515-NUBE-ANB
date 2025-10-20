import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import func

from models.video import Video
from models.videoVote import VideoVote
from models.user import User
from models.videoStatus import VideoStatus


@pytest.fixture()
def user_with_videos_and_votes(db_session):
    """Crea un usuario con videos y votos simulados."""
    u = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        user_name="test.user",
        hashed_password="hashed",
        city="Bogotá",
        country="Colombia",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    v = Video(
        user_id=u.id,
        title="video ranking test",
        original_url="/test.mp4",
        task_id="test-task",
        status=VideoStatus.UPLOADED,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)

    # Crea algunos votos
    vote1 = VideoVote(video_id=v.id, user_id=u.id)
    db_session.add(vote1)
    db_session.commit()

    return u, v


def test_ranking_success(client, user_with_videos_and_votes):
    resp = client.get("/api/public/ranking?page=1&size=10")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "position" in first
    assert "username" in first
    assert "city" in first
    assert "votes" in first


@patch("services.public_ranking.get_redis_client")
def test_ranking_uses_cache(mock_redis_client, client):
    """Debe devolver los datos desde cache si están almacenados en Redis."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps([
        {"position": 1, "username": "cached_user", "city": "Cali", "votes": 5}
    ])
    mock_redis_client.return_value = mock_redis

    resp = client.get("/api/public/ranking?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["username"] == "cached_user"

    # Redis.get fue llamado
    mock_redis.get.assert_called_once()


@patch("services.public_ranking.get_redis_client")
def test_ranking_redis_fails(mock_redis_client, client, user_with_videos_and_votes):
    """Si Redis falla, debe seguir funcionando usando la BD."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis down")
    mock_redis.setex.side_effect = Exception("Redis set fail")
    mock_redis_client.return_value = mock_redis

    resp = client.get("/api/public/ranking?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0  # sigue devolviendo datos desde DB

