import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from celery_app import celery
from config import config
from database import SessionLocal
from models import Video, VideoStatus
from sqlalchemy import select
from storage_a.factory import get_storage

FFMPEG = "ffmpeg"
FAST = "+faststart"
logger = logging.getLogger(__name__)


def _storage():
    return get_storage()


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg falló: {e.stderr.decode(errors='ignore')[:300]}")
        raise
    except FileNotFoundError:
        logger.error("FFmpeg no está instalado o no está en PATH.")
        raise


def _ensure_file(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(b"")


def get_duration(path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return float(result.stdout.decode().strip())
    except Exception:
        return 0.0


def _build_filter(intro_len: float, outro_len: float, main_len: float) -> str:
    fade_in_intro = min(intro_len, 0.5)
    fade_out_intro = max(intro_len - 0.5, 0)
    fade_in_outro = min(outro_len, 0.5)
    fade_out_outro = max(outro_len - 0.5, 0)

    return f"""
    [0:v]scale=1280:720:force_original_aspect_ratio=decrease,
        pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,
        fps=30,format=yuv420p,setsar=1,
        trim=0:{intro_len},
        fade=t=in:st=0:d={fade_in_intro},
        fade=t=out:st={fade_out_intro}:d=0.5,
        setpts=PTS-STARTPTS[intro];

    [1:v]scale=1280:720:force_original_aspect_ratio=decrease,
        pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,
        fps=30,format=yuv420p,setsar=1,
        trim=0:{main_len},
        setpts=PTS-STARTPTS[main_base];

    [3:v]scale=120:-1[wm];
    [main_base][wm]overlay=W-w-10:10[main];

    [2:v]scale=1280:720:force_original_aspect_ratio=decrease,
        pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,
        fps=30,format=yuv420p,setsar=1,
        trim=0:{outro_len},
        fade=t=in:st=0:d={fade_in_outro},
        fade=t=out:st={fade_out_outro}:d=0.5,
        setpts=PTS-STARTPTS[outro];

    [intro][main][outro]concat=n=3:v=1:a=0[v]
    """


def _render_final_video(
    src: str,
    logo: str,
    out_path: str,
    intro_len: float,
    outro_len: float,
) -> None:
    real_dur = get_duration(src)
    main_len = min(real_dur, 30.0)

    filters = _build_filter(intro_len, outro_len, main_len)

    watermark = os.path.join(config.ASSETS_DIR, "watermark.png")

    cmd = [
        FFMPEG,
        "-y",
        "-loop",
        "1",
        "-t",
        str(intro_len),
        "-i",
        logo,
        "-i",
        src,
        "-loop",
        "1",
        "-t",
        str(outro_len),
        "-i",
        logo,
        "-i",
        watermark,
        "-filter_complex",
        filters,
        "-map",
        "[v]",
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        FAST,
        "-r",
        "30",
        "-an",
        out_path,
    ]

    _run(cmd)
    _ensure_file(out_path)


def _render_simple(src: str, out_path: str) -> None:
    vf = (
        "scale=1280:720:flags=fast_bilinear:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        src,
        "-vf",
        vf,
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        FAST,
        "-an",
        out_path,
    ]
    _run(cmd)
    _ensure_file(out_path)


@celery.task(name="process_video")
def process_video(video_id: str) -> Literal["not-found", "ok", "error"]:
    db = SessionLocal()
    storage = _storage()
    video = None

    try:
        vid = int(video_id)
        video = db.execute(select(Video).where(Video.id == vid)).scalar_one_or_none()

        if not video:
            return "not-found"

        src_key = video.original_url
        intro_len = float(config.INTRO_SECONDS or 0.0)
        outro_len = float(config.OUTRO_SECONDS or 0.0)
        logo = os.path.join(config.ASSETS_DIR, "logo.jpg")
        has_logo = os.path.isfile(logo)
        if intro_len + outro_len > 5:
            raise ValueError("Las cortinillas no pueden exceder 5 segundos en total.")

        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, "src.mp4")
            final_local = os.path.join(tmp, f"{vid}.mp4")

            if not os.path.isfile(src_key):
                storage.download_to_path(src_key, src_path)
            else:
                src_path = src_key

            real_dur = get_duration(src_path)

            if real_dur < 20:
                raise ValueError(
                    f"Video demasiado corto: {real_dur:.2f}s (mínimo 20s)."
                )

            if real_dur > 60:
                raise ValueError(
                    f"Video demasiado largo: {real_dur:.2f}s (máximo 60s)."
                )

            if has_logo:
                _render_final_video(src_path, logo, final_local, intro_len, outro_len)
            else:
                _render_simple(src_path, final_local)

            out_key = f"{str(config.PROCESSED_DIR).strip('/')}/{vid}.mp4"
            with open(final_local, "rb") as f:
                storage.save(out_key, f)

        video.status = VideoStatus.PROCESSED
        processed_url = getattr(storage, "url", None)
        video.processed_url = (
            processed_url(out_key) if callable(processed_url) else out_key
        )
        video.processed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Video {vid} procesado correctamente.")
        return "ok"

    except Exception as e:
        logger.error(f"Error procesando video {video_id}: {e}")
        if video is not None:
            video.status = VideoStatus.FAILED
            db.commit()
        return "error"

    finally:
        db.close()
