import os
from unittest.mock import MagicMock, patch

import pytest
from workers.benchmark import BenchmarkProducer


@pytest.fixture
def producer(tmp_path):
    """Producer usando directorio temporal para evitar escribir en disco real."""
    with patch("services.benchmark_producer.SessionLocal") as mock_db:
        mock_db.return_value = MagicMock()

        # storage.save mockeado
        with patch("services.benchmark_producer.storage") as mock_storage:
            mock_storage.save.return_value = "/fake/storage/path/video.mp4"

            # Mockear workers.tasks.process_video.delay
            with patch("services.benchmark_producer.process_video") as mock_task:
                mock_task.delay = MagicMock()

                # Crear instancia real del Producer pero con mocks
                p = BenchmarkProducer()
                p.storage_dir = tmp_path / "benchmark_videos"
                os.makedirs(p.storage_dir, exist_ok=True)

                return p


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


def test_get_db_session_commit(producer):
    with patch("services.benchmark_producer.SessionLocal") as mock_db:
        db_instance = MagicMock()
        mock_db.return_value = db_instance

        with producer.get_db_session() as db:
            assert db is db_instance

        db_instance.commit.assert_called_once()
        db_instance.close.assert_called_once()


def test_get_db_session_rollback(producer):
    with patch("services.benchmark_producer.SessionLocal") as mock_db:
        db_instance = MagicMock()
        mock_db.return_value = db_instance

        with pytest.raises(Exception):
            with producer.get_db_session() as _db:
                raise Exception("Boom")

        db_instance.rollback.assert_called_once()
        db_instance.close.assert_called_once()


@patch("services.benchmark_producer.subprocess.run")
def test_create_real_dummy_video_success(mock_run, producer):
    mock_run.return_value.returncode = 0

    # mock DB add/commit/refresh
    producer.db.add = MagicMock()
    producer.db.commit = MagicMock()
    producer.db.refresh = MagicMock()

    video_id = producer.create_real_dummy_video(size_mb=5)

    assert producer.db.add.called
    assert producer.db.commit.called
    assert producer.db.refresh.called

    # El ID retornado debe ser string
    assert isinstance(video_id, str)


@patch("services.benchmark_producer.subprocess.run")
def test_create_real_dummy_video_ffmpeg_error(mock_run, producer):
    mock_run.return_value.returncode = 1

    with patch.object(
        producer, "create_small_valid_video", return_value="fallback"
    ) as mock_fallback:
        result = producer.create_real_dummy_video(size_mb=5)
        mock_fallback.assert_called_once()
        assert result == "fallback"


def test_create_small_valid_video_small(producer, tmp_path):
    base_vid = tmp_path / "base.mp4"

    with patch.object(producer, "get_base_test_video", return_value=str(base_vid)):
        base_vid.write_bytes(b"xxxx")  # base pequeño

        output = producer.create_small_valid_video(str(tmp_path / "out.mp4"), 2)
        assert os.path.exists(output)


def test_create_small_valid_video_large_calls_expand(producer):
    with patch.object(producer, "get_base_test_video", return_value="/base/video.mp4"):
        with patch.object(producer, "expand_video_size") as mock_expand:
            producer.create_small_valid_video("/tmp/out.mp4", 20)
            mock_expand.assert_called_once()


@patch("services.benchmark_producer.subprocess.run")
def test_get_base_test_video_creates(mock_run, producer):
    base_path = producer.storage_dir / "base_test.mp4"
    if os.path.exists(base_path):
        os.remove(base_path)

    result = producer.get_base_test_video()

    assert os.path.exists(result)
    mock_run.assert_called_once()


@patch("services.benchmark_producer.subprocess.run")
def test_expand_video_size_success(mock_run, producer):
    mock_run.return_value.stdout = "1.0"

    producer.expand_video_size("/input.mp4", "/output.mp4", 10)

    mock_run.assert_called()


@patch("services.benchmark_producer.subprocess.run", side_effect=Exception("boom"))
def test_expand_video_size_fallback(mock_run, producer, tmp_path):
    input_file = tmp_path / "in.mp4"
    input_file.write_bytes(b"xxx")

    with patch.object(producer, "pad_file_to_size") as mock_pad:
        producer.expand_video_size(str(input_file), str(tmp_path / "out.mp4"), 10)
        mock_pad.assert_called_once()


def test_pad_file_to_size(producer, tmp_path):
    file = tmp_path / "file.mp4"
    file.write_bytes(b"xxxxx")  # 5 bytes

    producer.pad_file_to_size(str(file), target_size_mb=1)

    assert os.path.getsize(file) > 5


def test_inject_messages_directly(producer):
    # Mockear create_real_dummy_video
    producer.create_real_dummy_video = MagicMock(return_value="video_id")

    from workers.tasks import process_video

    process_video.delay = MagicMock()

    result = producer.inject_messages_directly(video_size_mb=50, num_messages=3)

    assert result["total_messages"] == 3
    assert len(result["video_ids"]) == 3
    assert process_video.delay.call_count == 3


def test_cleanup_benchmark_data(producer):
    mock_db = MagicMock()

    video = MagicMock()
    video.original_url = "/fake/file.mp4"
    video.processed_url = "/fake/out.mp4"

    # Fake DB select → retorna el video 2 veces, None al final
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [video, None]

    # Mock para remover archivos
    with patch("services.benchmark_producer.os.path.exists", return_value=True):
        with patch("services.benchmark_producer.os.remove") as mock_rm:
            with patch.object(
                producer,
                "get_db_session",
                return_value=MagicMock(
                    __enter__=lambda *a: mock_db, __exit__=lambda *a: None
                ),
            ):
                producer.cleanup_benchmark_data(["1", "2"])

                assert mock_rm.call_count == 2
                assert mock_db.delete.called
                assert mock_db.commit.called
