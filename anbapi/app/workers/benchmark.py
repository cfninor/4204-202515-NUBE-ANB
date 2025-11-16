import os
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from database import SessionLocal
from models.video import Video
from models.videoStatus import VideoStatus
from sqlalchemy import select
from storage_a.factory import get_storage

storage = get_storage()


class BenchmarkProducer:
    def __init__(self):
        self.storage_dir = "benchmark_videos"
        self.db = SessionLocal()
        os.makedirs(self.storage_dir, exist_ok=True)

    @contextmanager
    def get_db_session(self):
        """Context manager para manejar sesiones de BD de forma segura"""
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_real_dummy_video(self, size_mb: int, duration: int = 10) -> str:
        """Crea un video dummy real usando FFmpeg"""
        video_filename = f"benchmark_{size_mb}mb_{uuid.uuid4()}.mp4"
        video_path = os.path.join(self.storage_dir, video_filename)
        video = os.path.abspath(video_path)

        try:
            # Crear video de prueba con FFmpeg (color sólido + audio silencio)
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=red:size=640x360:rate=30:d={duration}",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "30",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-t",
                str(duration),
                video,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            path = storage.save(video_filename, open(video, "rb"))

            if result.returncode != 0:
                print(f"⚠️ Error creando video dummy: {result.stderr}")
                # Fallback: crear archivo pequeño válido
                return self.create_small_valid_video(video_path, size_mb)
            video = Video(
                user_id=1,  # ID de usuario por defecto para benchmarks
                title=video_filename,
                original_url=path,
                uploaded_at=datetime.now(timezone.utc),
                status=VideoStatus.UPLOADED,
                task_id="benchmark",
            )

            self.db.add(video)
            self.db.commit()
            self.db.refresh(video)
            print(f"✅ Video dummy creado: {video_path}")
            return video.id

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            print(f"❌ Error con FFmpeg: {e}")
            # Fallback a video mínimo
            return self.create_small_valid_video(video_path, size_mb)

    def create_small_valid_video(self, video_path: str, size_mb: int) -> str:
        """Crea un video mínimo válido como fallback"""
        # Crear un video muy pequeño y luego expandirlo si es necesario
        base_video = self.get_base_test_video()

        if size_mb > 5:  # Si necesita ser más grande
            self.expand_video_size(base_video, video_path, size_mb)
        else:
            shutil.copy2(base_video, video_path)

        return video_path

    def get_base_test_video(self) -> str:
        """Obtiene o crea un video de prueba base"""
        base_path = os.path.join(self.storage_dir, "base_test.mp4")

        if not os.path.exists(base_path):
            # Crear video base mínimo (1 segundo, color rojo)
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=red:size=640x360:rate=1:d=1",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "30",
                "-t",
                "1",
                base_path,
            ]
            subprocess.run(cmd, capture_output=True)

        return base_path

    def expand_video_size(self, input_path: str, output_path: str, target_size_mb: int):
        """Expande un video para que tenga el tamaño objetivo"""
        try:
            # Primero obtener duración actual
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                input_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            _duration = float(result.stdout.strip())

            # Calcular nueva duración para alcanzar el tamaño
            # Estimación: 1MB ≈ 3 segundos en calidad baja
            target_duration = max(1, int(target_size_mb * 3))

            # Crear video looped
            cmd = [
                "ffmpeg",
                "-y",
                "-stream_loop",
                str(target_duration - 1),  # Loop para alcanzar duración
                "-i",
                input_path,
                "-c",
                "copy",
                "-t",
                str(target_duration),
                output_path,
            ]
            subprocess.run(cmd, capture_output=True)

        except Exception as e:
            print(f"❌ Error expandiendo video: {e}")
            # Fallback: copiar y rellenar con datos
            shutil.copy2(input_path, output_path)
            self.pad_file_to_size(output_path, target_size_mb)

    def pad_file_to_size(self, file_path: str, target_size_mb: int):
        """Rellena un archivo con datos para alcanzar el tamaño objetivo"""
        current_size = os.path.getsize(file_path) / (1024 * 1024)  # MB

        if current_size < target_size_mb:
            padding_size = int((target_size_mb - current_size) * 1024 * 1024)

            # Agregar datos de relleno al final del archivo
            with open(file_path, "ab") as f:
                f.write(b"\0" * padding_size)

    def inject_messages_directly(self, video_size_mb: int, num_messages: int):
        """Inyecta mensajes directamente en la cola"""
        video_ids = []
        start_time = time.time()

        for i in range(num_messages):
            # Solo obtenemos el ID, no el objeto Video completo
            video_id = self.create_real_dummy_video(video_size_mb)
            video_ids.append(video_id)

            # Inyectar directamente en la cola Celery usando solo el ID
            from workers.tasks import process_video

            process_video.delay(str(video_id))

        end_time = time.time()
        injection_rate = num_messages / (end_time - start_time)

        return {
            "video_ids": video_ids,  # Solo IDs, no objetos
            "total_messages": num_messages,
            "injection_time_seconds": end_time - start_time,
            "injection_rate_msg_per_sec": injection_rate,
        }

    def cleanup_benchmark_data(self, video_ids: list):
        """Limpia los datos generados durante el benchmark"""
        with self.get_db_session() as db:
            for video_id in video_ids:
                # Buscar el video usando solo el ID en la sesión actual
                video = db.execute(
                    select(Video).where(Video.id == video_id)
                ).scalar_one_or_none()

                if video:
                    # Eliminar archivo dummy
                    if os.path.exists(video.original_url):
                        try:
                            os.remove(video.original_url)
                        except OSError:
                            print(f"⚠️ No se pudo eliminar {video.original_url}")

                    # Eliminar archivo procesado si existe
                    if video.processed_url and os.path.exists(video.processed_url):
                        try:
                            os.remove(video.processed_url)
                        except OSError:
                            print(f"⚠️ No se pudo eliminar {video.processed_url}")

                    # Eliminar registro de la base de datos
                    db.delete(video)

            db.commit()
