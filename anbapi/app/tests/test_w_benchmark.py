import os
from unittest.mock import MagicMock, patch

import pytest
from workers.benchmark import BenchmarkProducer


@pytest.fixture
def producer(tmp_path):
    """Producer usando directorio temporal para evitar escribir en disco real."""
    with patch("workers.benchmark.SessionLocal") as mock_db:
        mock_db.return_value = MagicMock()

        # storage.save mockeado
        with patch("workers.benchmark.storage") as mock_storage:
            mock_storage.save.return_value = "/fake/storage/path/video.mp4"

            # Mockear workers.tasks.process_video.delay
            with patch("workers.tasks.process_video") as mock_task:
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
    with patch("workers.benchmark.SessionLocal") as mock_db:
        db_instance = MagicMock()
        mock_db.return_value = db_instance

        with producer.get_db_session() as db:
            assert db is db_instance

        db_instance.commit.assert_called_once()
        db_instance.close.assert_called_once()


def test_get_db_session_rollback(producer):
    with patch("workers.benchmark.SessionLocal") as mock_db:
        db_instance = MagicMock()
        mock_db.return_value = db_instance

        with pytest.raises(Exception):
            with producer.get_db_session() as _db:
                raise Exception("Boom")

        db_instance.rollback.assert_called_once()
        db_instance.close.assert_called_once()


@patch("workers.benchmark.subprocess.run")
def test_create_real_dummy_video_ffmpeg_error(mock_run, producer):
    # Mock error de subprocess.run
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_run.return_value = mock_process

    # Mock process_video.delay
    with patch("workers.tasks.process_video.delay"):
        with patch.object(
            producer, "create_small_valid_video", return_value="fallback"
        ) as mock_fallback:
            result = producer.create_real_dummy_video(size_mb=5)
            mock_fallback.assert_called_once()
            assert result == "fallback"


def test_create_small_valid_video_small(producer, tmp_path):
    base_vid = tmp_path / "base.mp4"
    base_vid.write_bytes(b"fake video content" * 100)  # Crear archivo más grande

    with patch.object(producer, "get_base_test_video", return_value=str(base_vid)):
        # Mock subprocess.run para evitar ejecutar ffmpeg
        with patch("workers.benchmark.subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process
            
            output = producer.create_small_valid_video(str(tmp_path / "out.mp4"), 2)
            # Verificar que el archivo de salida se creó
            assert os.path.exists(output)


def test_create_small_valid_video_large_calls_expand(producer):
    with patch.object(producer, "get_base_test_video", return_value="/base/video.mp4"):
        with patch.object(producer, "expand_video_size") as mock_expand:
            # Mock subprocess.run
            with patch("workers.benchmark.subprocess.run"):
                producer.create_small_valid_video("/tmp/out.mp4", 20)
                mock_expand.assert_called_once()


@patch("workers.benchmark.subprocess.run")
def test_get_base_test_video_creates(mock_run, producer):
    # Mock exitoso de subprocess.run
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_run.return_value = mock_process

    base_path = producer.storage_dir / "base_test.mp4"
    
    # Asegurarse de que el archivo no existe inicialmente
    if base_path.exists():
        base_path.unlink()

    result = producer.get_base_test_video()

    # Verificar que se llamó a subprocess.run
    mock_run.assert_called_once()
    # Verificar que el método retorna una ruta
    assert result is not None
    assert isinstance(result, str)


@patch("workers.benchmark.subprocess.run")
def test_expand_video_size_success(mock_run, producer):
    # Mock exitoso con stdout
    mock_process = MagicMock()
    mock_process.stdout = "1.0"
    mock_process.returncode = 0
    mock_run.return_value = mock_process

    # Crear archivos de entrada y salida temporales
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
        input_file.write(b"fake video content")
        input_path = input_file.name

    try:
        output_path = input_path.replace('.mp4', '_out.mp4')
        producer.expand_video_size(input_path, output_path, 10)
        mock_run.assert_called()
    finally:
        # Limpiar
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


@patch("workers.benchmark.subprocess.run", side_effect=Exception("boom"))
def test_expand_video_size_fallback(mock_run, producer, tmp_path):
    input_file = tmp_path / "in.mp4"
    input_file.write_bytes(b"xxx")

    with patch.object(producer, "pad_file_to_size") as mock_pad:
        producer.expand_video_size(str(input_file), str(tmp_path / "out.mp4"), 10)
        mock_pad.assert_called_once()


def test_pad_file_to_size(producer, tmp_path):
    file = tmp_path / "file.mp4"
    file.write_bytes(b"xxxxx")  # 5 bytes

    producer.pad_file_to_size(str(file), target_size_mb=0.001)  # Usar tamaño más pequeño para测试

    assert os.path.getsize(file) > 5


def test_inject_messages_directly(producer):
    # Mockear create_real_dummy_video
    producer.create_real_dummy_video = MagicMock(return_value="video_id")

    # Mock process_video.delay
    with patch("workers.tasks.process_video.delay") as mock_delay:
        # Mock time.time para calcular duration
        with patch("workers.benchmark.time.time") as mock_time:
            mock_time.side_effect = [1000.0, 1001.0]  # 1 segundo de diferencia
            
            result = producer.inject_messages_directly(video_size_mb=50, num_messages=3)

            assert result["total_messages"] == 3
            assert len(result["video_ids"]) == 3
            assert mock_delay.call_count == 3
            assert result["injection_time_seconds"] == 1.0
            assert result["injection_rate_msg_per_sec"] == 3.0


def test_cleanup_benchmark_data(producer):
    mock_db = MagicMock()

    video = MagicMock()
    video.original_url = "/fake/file.mp4"
    video.processed_url = "/fake/out.mp4"

    # Fake DB select → retorna el video 2 veces, None al final
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [video, None]

    # Mock para remover archivos
    with patch("workers.benchmark.os.path.exists", return_value=True):
        with patch("workers.benchmark.os.remove") as mock_rm:
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


# Tests adicionales para casos edge
def test_create_small_valid_video_base_not_exists(producer, tmp_path):
    """Test cuando el video base no existe"""
    non_existent_base = tmp_path / "nonexistent.mp4"
    
    with patch.object(producer, "get_base_test_video", return_value=str(non_existent_base)):
        with patch("workers.benchmark.subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process
            
            # Debería fallar silenciosamente o manejar el error
            with pytest.raises(Exception):
                producer.create_small_valid_video(str(tmp_path / "out.mp4"), 2)


def test_pad_file_to_size_already_large(producer, tmp_path):
    """Test cuando el archivo ya es más grande que el tamaño objetivo"""
    file = tmp_path / "large_file.mp4"
    # Crear archivo de 2KB
    file.write_bytes(b"x" * 2048)
    
    original_size = os.path.getsize(file)
    
    # Intentar pad a 1KB (menor que el tamaño actual)
    producer.pad_file_to_size(str(file), target_size_mb=0.001)  # ~1KB
    
    # El archivo debería mantenerse igual o crecer, no reducirse
    assert os.path.getsize(file) >= original_size
