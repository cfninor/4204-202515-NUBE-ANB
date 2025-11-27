import threading
import time
from datetime import datetime, timezone

from models.video import Video
from models.videoStatus import VideoStatus
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from workers.benchmark import BenchmarkProducer
import numpy as np


class BenchmarkService:
    def __init__(self):
        self.producer = BenchmarkProducer()
        self.active_benchmarks = {}

    def run_saturation_test(self, video_size_mb: int, num_workers: int, num_tasks: int):
        """Ejecuta prueba de saturación"""
        benchmark_id = (
            f"saturation_{video_size_mb}mb_{num_workers}workers_{int(time.time())}"
        )

        # Iniciar benchmark en un hilo separado
        thread = threading.Thread(
            target=self._run_saturation_benchmark,
            args=(benchmark_id, video_size_mb, num_tasks),
        )
        thread.daemon = True
        thread.start()

        self.active_benchmarks[benchmark_id] = {
            "type": "saturation",
            "video_size_mb": video_size_mb,
            "num_workers": num_workers,
            "num_tasks": num_tasks,
            "start_time": datetime.now(timezone.utc),
            "status": "running",
            "video_ids": [],
            "configuration": f"{num_workers}worker",
        }

        return benchmark_id

    def _run_saturation_benchmark(
        self, benchmark_id: str, video_size_mb: int, num_tasks: int
    ):
        """Ejecuta el benchmark de saturación en segundo plano"""
        try:
            print(
                f"🎬 Iniciando benchmark {benchmark_id} con {num_tasks} tareas de {video_size_mb}MB"
            )

            # Inyectar mensajes
            result = self.producer.inject_messages_directly(video_size_mb, num_tasks)

            print(
                f"✅ Mensajes inyectados: {result['total_messages']} en {result['injection_time_seconds']:.2f}s"
            )
            print(
                f"📊 Tasa de inyección: {result['injection_rate_msg_per_sec']:.2f} mensajes/segundo"
            )

            # Esperar un poco para que empiecen a procesarse
            print("⏳ Esperando procesamiento inicial...")
            time.sleep(10)  # Esperar 10 segundos para que algunos videos se procesen

            self.active_benchmarks[benchmark_id].update(
                {
                    "video_ids": result["video_ids"],
                    "injection_info": result,
                    "status": "completed",
                    "completion_time": datetime.now(timezone.utc),
                }
            )

            print(f"🎉 Benchmark {benchmark_id} marcado como completado")

        except Exception as e:
            print(f"❌ Error en benchmark {benchmark_id}: {str(e)}")
            import traceback

            traceback.print_exc()

            self.active_benchmarks[benchmark_id].update(
                {
                    "status": "error",
                    "error": str(e),
                    "completion_time": datetime.now(timezone.utc),
                }
            )

    def run_sustained_test(
        self,
        video_size_mb: int,
        num_workers: int,
        queue_size: int,
        duration_seconds: int,
    ):
        """Ejecuta prueba sostenida"""
        benchmark_id = (
            f"sustained_{video_size_mb}mb_{num_workers}workers_{int(time.time())}"
        )

        thread = threading.Thread(
            target=self._run_sustained_benchmark,
            args=(benchmark_id, video_size_mb, queue_size, duration_seconds),
        )
        thread.daemon = True
        thread.start()

        self.active_benchmarks[benchmark_id] = {
            "type": "sustained",
            "video_size_mb": video_size_mb,
            "num_workers": num_workers,
            "queue_size": queue_size,
            "duration_seconds": duration_seconds,
            "start_time": datetime.now(timezone.utc),
            "status": "running",
            "video_ids": [],
            "configuration": f"{num_workers}worker",
        }

        return benchmark_id

    def _run_sustained_benchmark(
        self,
        benchmark_id: str,
        video_size_mb: int,
        queue_size: int,
        duration_seconds: int,
    ):
        """Ejecuta el benchmark sostenido en segundo plano"""
        try:
            start_time = time.time()
            all_video_ids = []

            print(f"🎬 Iniciando benchmark sostenido {benchmark_id}")
            print(
                f"   Duración: {duration_seconds}s, Tamaño cola: {queue_size}, Video: {video_size_mb}MB"
            )

            while time.time() - start_time < duration_seconds:
                # Usar sesión independiente para cada verificación
                with self.producer.get_db_session() as db:
                    current_pending = db.execute(
                        select(func.count(Video.id)).where(
                            Video.status == VideoStatus.UPLOADED
                        )
                    ).scalar()

                    tasks_to_add = max(0, queue_size - current_pending)
                    if tasks_to_add > 0:
                        # Inyectar mensajes (esto ya maneja su propia sesión)
                        result = self.producer.inject_messages_directly(
                            video_size_mb, tasks_to_add
                        )
                        all_video_ids.extend(result["video_ids"])
                        print(
                            f"➕ Añadidas {tasks_to_add} tareas, total acumulado: {len(all_video_ids)}"
                        )

                time.sleep(2)  # Verificar cada 2 segundos

            self.active_benchmarks[benchmark_id].update(
                {
                    "video_ids": all_video_ids,
                    "status": "completed",
                    "completion_time": datetime.now(timezone.utc),
                }
            )

            print(f"🎉 Benchmark sostenido {benchmark_id} completado")

        except Exception as e:
            print(f"❌ Error en benchmark sostenido {benchmark_id}: {str(e)}")
            import traceback

            traceback.print_exc()

            self.active_benchmarks[benchmark_id].update(
                {
                    "status": "error",
                    "error": str(e),
                    "completion_time": datetime.now(timezone.utc),
                }
            )

    def get_benchmark_status(self, benchmark_id: str, db: Session):
        """Obtiene el estado de un benchmark específico"""
        if benchmark_id not in self.active_benchmarks:
            return None

        benchmark = self.active_benchmarks[benchmark_id].copy()

        if benchmark["status"] == "completed":
            # Calcular métricas usando la sesión proporcionada
            video_ids = benchmark.get("video_ids")
            print(
                f"Calculando métricas para benchmark {benchmark_id} con {len(video_ids)} videos"
            )
            if video_ids:
                metrics = self._calculate_metrics(video_ids, db)
                benchmark["metrics"] = metrics

        return benchmark

    def _calculate_metrics(self, video_ids: list, db: Session):
        """Calcula métricas de rendimiento usando la sesión proporcionada"""
        try:
            if not video_ids:
                return {
                    "throughput_videos_per_min": 0,
                    "average_service_time_seconds": 0,
                    "success_rate": 0,
                    "processed_count": 0,
                    "processing_count": 0,
                    "failed_count": 0,
                    "total_count": 0,
                    "message": "No hay videos para calcular métricas",
                }

            # Obtener todos los videos por sus IDs
            videos = (
                db.execute(select(Video).where(Video.id.in_(video_ids))).scalars().all()
            )

            processed_count = 0
            processing_count = 0
            failed_count = 0
            processing_times = []
            mb_per_second = 0
            desviation = 0
            p90 = 0
            p95 = 0
            p50 = 0
            avg_service_time = 0
            throughput_per_min = 0

            for video in videos:
                if video.status == VideoStatus.PROCESSED:
                    processed_count += 1
                    # ✅ CORREGIDO: Usar processing_started_at en lugar de created_at
                    if video.processed_at and video.processing_started_at:
                        processing_time = (
                            video.processed_at - video.processing_started_at
                        ).total_seconds()
                        processing_times.append(processing_time)
                        print(
                            f"📊 Video {video.id}: Tiempo procesamiento real = {processing_time}".replace(
                                ".", ","
                            )
                        )
                elif video.status == VideoStatus.UPLOADED:
                    processing_count += 1
                elif video.status == VideoStatus.FAILED:
                    failed_count += 1

            total_count = len(videos)
            
            # Calcular métricas
            if processing_times:
                total_processing_time = sum(processing_times)

                mb_per_second = (len(total_count) / total_processing_time).second
                desviation= np.std(processing_times)
                p90=np.percentile(processing_times,90)
                p95=np.percentile(processing_times,95)
                p50=np.percentile(processing_times,50)
                avg_service_time = total_processing_time / len(processing_times)
                throughput_per_min = (
                    (processed_count / total_processing_time) * 60
                    if avg_service_time > 0
                    else 0
                )
                print(f"📊 throughput_per_min:{throughput_per_min}")
            else:
                avg_service_time = 0
                throughput_per_min = 0

            success_rate = (
                (processed_count / total_count * 100) if total_count > 0 else 0
            )

            return {
                "throughput_videos_per_min": round(throughput_per_min, 2),
                "average_service_time_seconds": round(avg_service_time, 2),
                "success_rate": round(success_rate, 2),
                "mb_per_second": round(mb_per_second, 2), 
                "desviation": round(desviation, 2),
                "p90": round(p90, 2),
                "p95": round(p95, 2),
                "p50": round(p50, 2),
                "processed_count": processed_count,
                "processing_count": processing_count,
                "failed_count": failed_count,
                "total_count": total_count,
                "processing_times_sample": [round(t, 2) for t in processing_times[:3]]
                if processing_times
                else [],
                "message": f"Procesados: {processed_count}, En proceso: {processing_count}, Fallados: {failed_count}",
            }

        except Exception as e:
            print(f"Error calculando métricas: {str(e)}")
            import traceback

            traceback.print_exc()

            return {
                "throughput_videos_per_min": 0,
                "average_service_time_seconds": 0,
                "success_rate": 0,
                "mb_per_second": 0,
                "desviation": 0,
                "p90": 0,
                "p95": 0,
                "p50": 0,
                "processed_count": 0,
                "processing_count": 0,
                "failed_count": 0,
                "total_count": len(video_ids),
                "error": str(e),
            }

    def generate_capacity_table(self, db: Session):
        """Genera tabla de capacidad basada en benchmarks históricos"""
        completed_benchmarks = []
        for benchmark_id, benchmark_data in self.active_benchmarks.items():
            if benchmark_data.get("status") == "completed":
                # Recalcular métricas con la sesión actual
                video_ids = benchmark_data.get("video_ids", [])
                if video_ids:
                    metrics = self._calculate_metrics(video_ids, db)
                    completed_benchmarks.append(
                        {
                            "benchmark_id": benchmark_id,
                            **benchmark_data,
                            "metrics": metrics,
                        }
                    )

        if not completed_benchmarks:
            return {
                "capacity_table": [],
                "message": "No hay datos de benchmarks completados disponibles",
            }

        # Organizar datos por configuración
        config_data = {}

        for benchmark in completed_benchmarks:
            benchmark_id = benchmark["benchmark_id"]

            if benchmark_id.startswith("saturation_"):
                parts = benchmark_id.split("_")
                video_size_mb = int(parts[1].replace("mb", ""))
                num_workers = int(parts[2].replace("workers", ""))

                config_key = f"{num_workers}worker"

                if config_key not in config_data:
                    config_data[config_key] = {"50MB": None, "100MB": None}

                # Almacenar el throughput para este tamaño de video
                throughput = benchmark["metrics"]["throughput_videos_per_min"]
                config_data[config_key][f"{video_size_mb}MB"] = throughput

        # Construir tabla de capacidad
        capacity_table = []

        target_configs = [
            {"workers": 1, "procesos": 1, "label": "1 worker × 1 proceso"},
            {"workers": 1, "procesos": 2, "label": "1 worker × 2 procesos"},
            {"workers": 1, "procesos": 4, "label": "1 worker × 4 procesos"},
        ]

        for config in target_configs:
            config_key = f"{config['workers']}worker"

            row = {"configuration": config["label"], "50MB": "N/A", "100MB": "N/A"}

            if config_key in config_data:
                data = config_data[config_key]

                if data["50MB"] is not None:
                    row["50MB"] = f"{data['50MB']:.1f} videos/min"

                if data["100MB"] is not None:
                    row["100MB"] = f"{data['100MB']:.1f} videos/min"

            capacity_table.append(row)

        return {
            "capacity_table": capacity_table,
            "summary": {
                "total_benchmarks_analizados": len(completed_benchmarks),
                "configuraciones_encontradas": list(config_data.keys()),
            },
        }

    def cleanup_benchmark(self, benchmark_id: str):
        """Limpia los datos de un benchmark"""
        if benchmark_id in self.active_benchmarks:
            video_ids = self.active_benchmarks[benchmark_id].get("video_ids", [])
            if video_ids:
                self.producer.cleanup_benchmark_data(video_ids)
            del self.active_benchmarks[benchmark_id]
            return True
        return False
