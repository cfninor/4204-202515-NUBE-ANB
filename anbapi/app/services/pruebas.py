from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from services.benchmark_service import BenchmarkService
from sqlalchemy.orm import Session

benchmark_router = APIRouter(prefix="/benchmark", tags=["benchmark"])

# Instancia global del servicio de benchmark
benchmark_service = BenchmarkService()


@benchmark_router.post("/saturation")
async def start_saturation_benchmark(
    video_size_mb: int = 50, num_workers: int = 1, num_tasks: int = 10
):
    """Inicia una prueba de saturación"""
    if video_size_mb not in [50, 100]:
        raise HTTPException(400, "Tamaño de video debe ser 50 o 100 MB")

    benchmark_id = benchmark_service.run_saturation_test(
        video_size_mb, num_workers, num_tasks
    )

    return {
        "benchmark_id": benchmark_id,
        "message": "Benchmark de saturación iniciado",
        "parameters": {
            "video_size_mb": video_size_mb,
            "num_workers": num_workers,
            "num_tasks": num_tasks,
        },
    }


@benchmark_router.get("/status/{benchmark_id}")
async def get_benchmark_status(
    benchmark_id: str,
    db: Session = Depends(get_db),  # Inyectar sesión aquí
):
    """Obtiene el estado de un benchmark"""
    status = benchmark_service.get_benchmark_status(benchmark_id, db)  # Pasar db
    if not status:
        raise HTTPException(404, "Benchmark no encontrado")

    return status


@benchmark_router.get("/capacity-table")
async def get_capacity_table(
    db: Session = Depends(get_db),  # Inyectar sesión aquí
):
    """Genera tabla de capacidad basada en benchmarks históricos"""
    capacity_data = benchmark_service.generate_capacity_table(db)  # Pasar db
    return capacity_data
