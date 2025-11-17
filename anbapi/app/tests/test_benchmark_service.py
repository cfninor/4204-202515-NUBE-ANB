from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from services.benchmark_service import BenchmarkService


@pytest.fixture
def service():
    return BenchmarkService()


@pytest.fixture
def mock_producer():
    """Mock del BenchmarkProducer"""
    mock = MagicMock()
    mock.inject_messages_directly.return_value = {
        "total_messages": 5,
        "injection_time_seconds": 1.0,
        "injection_rate_msg_per_sec": 5,
        "video_ids": ["v1", "v2", "v3", "v4", "v5"],
    }
    return mock


@patch("threading.Thread")
def test_run_saturation_test_starts_thread(mock_thread, service, mock_producer):
    service.producer = mock_producer

    benchmark_id = service.run_saturation_test(50, 1, 5)

    # Verificar que un thread fue disparado
    mock_thread.assert_called_once()
    assert benchmark_id in service.active_benchmarks

    data = service.active_benchmarks[benchmark_id]
    assert data["status"] == "running"
    assert data["video_size_mb"] == 50


def test_run_saturation_benchmark_logic(service, mock_producer):
    service.producer = mock_producer

    benchmark_id = "test_bench_123"
    service.active_benchmarks[benchmark_id] = {"status": "running", "video_ids": []}

    service._run_saturation_benchmark(benchmark_id, 50, 5)

    data = service.active_benchmarks[benchmark_id]
    assert data["status"] == "completed"
    assert len(data["video_ids"]) == 5


@patch("threading.Thread")
def test_run_sustained_test_start_thread(mock_thread, service, mock_producer):
    service.producer = mock_producer

    benchmark_id = service.run_sustained_test(50, 1, 3, 10)

    mock_thread.assert_called_once()
    assert benchmark_id in service.active_benchmarks
    assert service.active_benchmarks[benchmark_id]["status"] == "running"


def test_run_sustained_benchmark(service, mock_producer):
    service.producer = mock_producer

    # Mock de DB session
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = False

    # Simular count de videos pendientes
    mock_session.execute.return_value.scalar.return_value = 0

    mock_producer.get_db_session.return_value = mock_session

    service.active_benchmarks["bench123"] = {"status": "running"}

    # Reducir tiempo de benchmark para que no tarde
    with patch("time.time", side_effect=[0, 1]):
        service._run_sustained_benchmark("bench123", 50, 3, 1)

    data = service.active_benchmarks["bench123"]
    assert data["status"] == "completed"
    assert len(data["video_ids"]) == 5  # 5 que retorna el mock


def test_get_benchmark_status_completed(service, mock_producer):
    service.producer = mock_producer

    mock_db = MagicMock()

    service.active_benchmarks["b1"] = {"status": "completed", "video_ids": ["v1", "v2"]}

    # Forzar cálculo de métricas
    service._calculate_metrics = MagicMock(return_value={"processed_count": 2})

    result = service.get_benchmark_status("b1", mock_db)
    assert result["metrics"]["processed_count"] == 2


def test_get_benchmark_status_not_found(service):
    result = service.get_benchmark_status("nope", MagicMock())
    assert result is None


class FakeVideo:
    def __init__(self, id, status, start, end):
        self.id = id
        self.status = status
        self.processing_started_at = start
        self.processed_at = end


class FakeStatus:
    PROCESSED = "PROCESSED"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"


def test_calculate_metrics(service):
    # Sobrescribir VideoStatus para pruebas
    service.VideoStatus = FakeStatus

    start = datetime.now(timezone.utc) - timedelta(seconds=10)
    end = datetime.now(timezone.utc)

    video1 = FakeVideo("1", FakeStatus.PROCESSED, start, end)
    video2 = FakeVideo("2", FakeStatus.UPLOADED, None, None)
    video3 = FakeVideo("3", FakeStatus.FAILED, None, None)

    fake_db = MagicMock()
    fake_db.execute.return_value.scalars.return_value.all.return_value = [
        video1,
        video2,
        video3,
    ]

    metrics = service._calculate_metrics(["1", "2", "3"], fake_db)

    assert metrics["processed_count"] == 1
    assert metrics["processing_count"] == 1
    assert metrics["failed_count"] == 1
    assert metrics["average_service_time_seconds"] > 0


def test_generate_capacity_table(service):
    service.active_benchmarks = {
        "saturation_50mb_1workers_123": {"status": "completed", "video_ids": ["x1"]},
        "saturation_100mb_1workers_555": {"status": "completed", "video_ids": ["x2"]},
    }

    fake_db = MagicMock()
    service._calculate_metrics = MagicMock(
        return_value={"throughput_videos_per_min": 12.5}
    )

    result = service.generate_capacity_table(fake_db)

    assert len(result["capacity_table"]) == 3
    assert "50MB" in result["capacity_table"][0]
    assert "100MB" in result["capacity_table"][0]


def test_cleanup_benchmark(service, mock_producer):
    service.producer = mock_producer

    service.active_benchmarks["b1"] = {"video_ids": ["1", "2", "3"]}

    assert service.cleanup_benchmark("b1") is True
    mock_producer.cleanup_benchmark_data.assert_called_once()


def test_cleanup_benchmark_not_found(service):
    assert service.cleanup_benchmark("xxx") is False
