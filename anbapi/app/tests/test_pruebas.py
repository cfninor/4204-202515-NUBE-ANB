from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.pruebas import benchmark_router


@pytest.fixture
def app():
    """Crea app de prueba con el router montado."""
    api = FastAPI()
    api.include_router(benchmark_router)
    return api


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_db():
    """DB mock que reemplaza la dependencia get_db."""
    db = MagicMock()
    yield db


@patch("routers.benchmark_router.benchmark_service")
def test_start_saturation_benchmark_success(mock_service, client):
    mock_service.run_saturation_test.return_value = "test_bench_123"

    resp = client.post(
        "/benchmark/saturation",
        json={"video_size_mb": 50, "num_workers": 1, "num_tasks": 5},
    )

    assert resp.status_code == 200
    data = resp.json()

    mock_service.run_saturation_test.assert_called_once()
    assert data["benchmark_id"] == "test_bench_123"
    assert data["parameters"]["video_size_mb"] == 50


def test_start_saturation_benchmark_invalid_size(client):
    resp = client.post(
        "/benchmark/saturation",
        json={
            "video_size_mb": 10,  # ❌ No permitido
            "num_workers": 1,
            "num_tasks": 5,
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Tamaño de video debe ser 50 o 100 MB"


@patch("routers.benchmark_router.get_db")
@patch("routers.benchmark_router.benchmark_service")
def test_get_benchmark_status_success(mock_service, mock_get_db, client, mock_db):
    mock_get_db.return_value = mock_db
    mock_service.get_benchmark_status.return_value = {
        "status": "completed",
        "video_ids": ["v1"],
    }

    resp = client.get("/benchmark/status/test123")

    assert resp.status_code == 200
    data = resp.json()

    mock_service.get_benchmark_status.assert_called_once()
    assert data["status"] == "completed"
    assert data["video_ids"] == ["v1"]


@patch("routers.benchmark_router.get_db")
@patch("routers.benchmark_router.benchmark_service")
def test_get_benchmark_status_not_found(mock_service, mock_get_db, client, mock_db):
    mock_get_db.return_value = mock_db
    mock_service.get_benchmark_status.return_value = None  # ❌ no encontrado

    resp = client.get("/benchmark/status/inexistente123")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Benchmark no encontrado"


@patch("routers.benchmark_router.get_db")
@patch("routers.benchmark_router.benchmark_service")
def test_get_capacity_table_success(mock_service, mock_get_db, client, mock_db):
    mock_get_db.return_value = mock_db
    mock_service.generate_capacity_table.return_value = {
        "capacity_table": [],
        "summary": {"total_benchmarks_analizados": 1},
    }

    resp = client.get("/benchmark/capacity-table")

    assert resp.status_code == 200
    data = resp.json()

    mock_service.generate_capacity_table.assert_called_once()
    assert "capacity_table" in data
    assert "summary" in data
