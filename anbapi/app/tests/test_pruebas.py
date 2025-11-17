from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.pruebas import benchmark_router  # Cambiado a services.pruebas


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


@patch("services.pruebas.benchmark_service")  # CORREGIDO: services.pruebas
def test_start_saturation_benchmark_success(mock_service, client):
    mock_service.run_saturation_test.return_value = "test_bench_123"

    # CORREGIDO: Usar parámetros de query, no JSON
    resp = client.post(
        "/benchmark/saturation",
        params={  # Cambiado de json= a params=
            "video_size_mb": 50, 
            "num_workers": 1, 
            "num_tasks": 5
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    mock_service.run_saturation_test.assert_called_once_with(50, 1, 5)
    assert data["benchmark_id"] == "test_bench_123"
    assert data["parameters"]["video_size_mb"] == 50


def test_start_saturation_benchmark_invalid_size(client):
    # CORREGIDO: Usar parámetros de query
    resp = client.post(
        "/benchmark/saturation",
        params={  # Cambiado de json= a params=
            "video_size_mb": 10,  # ❌ No permitido
            "num_workers": 1,
            "num_tasks": 5,
        },
    )

    assert resp.status_code == 400
    assert "Tamaño de video debe ser 50 o 100 MB" in resp.json()["detail"]


@patch("services.pruebas.get_db")  # CORREGIDO: services.pruebas
@patch("services.pruebas.benchmark_service")  # CORREGIDO: services.pruebas
def test_get_benchmark_status_not_found(mock_service, mock_get_db, client, mock_db):
    mock_get_db.return_value = mock_db
    mock_service.get_benchmark_status.return_value = None  # ❌ no encontrado

    resp = client.get("/benchmark/status/inexistente123")

    assert resp.status_code == 404
    assert "Benchmark no encontrado" in resp.json()["detail"]

# Tests adicionales para cubrir más casos
@patch("services.pruebas.benchmark_service")
def test_start_saturation_benchmark_default_values(mock_service, client):
    """Test que los valores por defecto funcionan"""
    mock_service.run_saturation_test.return_value = "test_default_123"

    # Llamar sin parámetros (debería usar valores por defecto)
    resp = client.post("/benchmark/saturation")

    assert resp.status_code == 200
    data = resp.json()
    
    # Verificar que se usaron los valores por defecto: 50, 1, 10
    mock_service.run_saturation_test.assert_called_once_with(50, 1, 10)
    assert data["benchmark_id"] == "test_default_123"


@patch("services.pruebas.benchmark_service")
def test_start_saturation_benchmark_100mb(mock_service, client):
    """Test con tamaño de video 100MB"""
    mock_service.run_saturation_test.return_value = "test_100mb_123"

    resp = client.post(
        "/benchmark/saturation",
        params={
            "video_size_mb": 100,  # ✅ Permitido
            "num_workers": 2,
            "num_tasks": 8,
        },
    )

    assert resp.status_code == 200
    mock_service.run_saturation_test.assert_called_once_with(100, 2, 8)


@patch("services.pruebas.get_db")
@patch("services.pruebas.benchmark_service")
def test_get_benchmark_status_running(mock_service, mock_get_db, client, mock_db):
    """Test para benchmark en estado 'running'"""
    mock_get_db.return_value = mock_db
    mock_service.get_benchmark_status.return_value = {
        "status": "running",
        "progress": 50,
        "start_time": "2024-01-01T10:00:00Z"
    }

    resp = client.get("/benchmark/status/running123")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["progress"] == 50


@patch("services.pruebas.get_db")
@patch("services.pruebas.benchmark_service")
def test_get_capacity_table_empty(mock_service, mock_get_db, client, mock_db):
    """Test para tabla de capacidad vacía"""
    mock_get_db.return_value = mock_db
    mock_service.generate_capacity_table.return_value = {
        "capacity_table": [],
        "message": "No hay datos de benchmarks completados disponibles"
    }

    resp = client.get("/benchmark/capacity-table")

    assert resp.status_code == 200
    data = resp.json()
    assert data["capacity_table"] == []
    assert "message" in data