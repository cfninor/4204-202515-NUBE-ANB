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
FFPROBE = "ffprobe"
COLOR = "color=size=1280x720:rate=30:color=black"
FAST = "+faststart"


def _storage():
    return get_storage()


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _ensure_file(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(b"")


def _x264_args() -> list[str]:
    return [
        "-r",
        "30",
        "-fps_mode",
        "cfr",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        FAST,
    ]


def _build_vf_main() -> str:
    return (
        "scale=w=1280:h=720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,format=rgba"
    )


def _render_main(src: str, duration: float, logo: str | None, out_path: str):
    vf_logo = (
        "[0:v]" + _build_vf_main() + "[v0];"
        "[1:v]scale=180:-1,format=rgba[wm];"
        "[v0][wm]overlay=W-w-30:30:format=auto:eval=init[v]"
    )
    if logo and os.path.isfile(logo):
        _run(
            [
                FFMPEG,
                "-y",
                "-i",
                src,
                "-i",
                logo,
                "-t",
                f"{duration}",
                "-filter_complex",
                vf_logo,
                "-map",
                "[v]",
                *_x264_args(),
                "-an",
                out_path,
            ]
        )
    else:
        _run(
            [
                FFMPEG,
                "-y",
                "-i",
                src,
                "-t",
                f"{duration}",
                "-vf",
                _build_vf_main(),
                *_x264_args(),
                "-an",
                out_path,
            ]
        )
    _ensure_file(out_path)


def _render_color(duration: float, out_path: str):
    _run(
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-t",
            f"{duration}",
            "-i",
            COLOR,
            "-map",
            "0:v",
            *_x264_args(),
            "-an",
            out_path,
        ]
    )
    _ensure_file(out_path)


def _render_logo(duration: float, logo: str, out_path: str):
    fade_out = max(0.0, duration - 0.5)
    _run(
        [
            FFMPEG,
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration}",
            "-i",
            logo,
            "-f",
            "lavfi",
            "-t",
            f"{duration}",
            "-i",
            COLOR,
            "-filter_complex",
            "[0:v]scale='min(720,iw)':'min(300,ih)':force_original_aspect_ratio=decrease,"
            f"format=rgba,fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out}:d=0.5[lg];"
            "[1:v][lg]overlay=(W-w)/2:(H-h)/2[v]",
            "-map",
            "[v]",
            *_x264_args(),
            "-an",
            out_path,
        ]
    )
    _ensure_file(out_path)


def _render_stub(out_path: str):
    _run(
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-t",
            "0.033",
            "-i",
            COLOR,
            "-map",
            "0:v",
            *_x264_args(),
            "-an",
            out_path,
        ]
    )
    _ensure_file(out_path)


def _concat_segments(intro: str, main_: str, outro: str, dest: str):
    _run(
        [
            FFMPEG,
            "-y",
            "-i",
            intro,
            "-i",
            main_,
            "-i",
            outro,
            "-filter_complex",
            "[0:v]setpts=PTS-STARTPTS[v0];"
            "[1:v]setpts=PTS-STARTPTS[v1];"
            "[2:v]setpts=PTS-STARTPTS[v2];"
            "[v0][v1][v2]concat=n=3:v=1:a=0[v]",
            "-map",
            "[v]",
            *_x264_args(),
            dest,
        ]
    )
    _ensure_file(dest)


def _calc_main_len(intro_len: float, outro_len: float, total: float = 35.0) -> float:
    return max(0.0, total - (intro_len + outro_len))


def _render_segment(duration: float, has_logo: bool, logo: str, out_path: str) -> None:
    if duration <= 0.0:
        _render_stub(out_path)
    elif has_logo:
        _render_logo(duration, logo, out_path)
    else:
        _render_color(duration, out_path)


def _paths(tmp: str, video_id: int) -> tuple[str, str, str, str, str]:
    return (
        os.path.join(tmp, "src.mp4"),
        os.path.join(tmp, "main_720.mp4"),
        os.path.join(tmp, "intro.mp4"),
        os.path.join(tmp, "outro.mp4"),
        os.path.join(tmp, f"{video_id}.mp4"),
    )


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
        main_len = _calc_main_len(intro_len, outro_len)
        logo = os.path.join(config.ASSETS_DIR, "logo.jpg")
        has_logo = os.path.isfile(logo)

        with tempfile.TemporaryDirectory() as tmp:
            src_path, main_720, intro, outro, final_local = _paths(tmp, vid)
            if not os.path.isfile(src_key):
                storage.download_to_path(src_key, src_path)
            else:
                src_path = src_key

            _render_main(src_path, main_len, logo if has_logo else None, main_720)
            _render_segment(intro_len, has_logo, logo, intro)
            _render_segment(outro_len, has_logo, logo, outro)

            _concat_segments(intro, main_720, outro, final_local)

            out_key = os.path.join(os.fspath(config.PROCESSED_DIR), f"{vid}.mp4")
            with open(final_local, "rb") as f:
                storage.save(out_key, f)
        video.status = VideoStatus.PROCESSED
        processed_url_fn = getattr(storage, "url", None)
        video.processed_url = (
            processed_url_fn(out_key) if callable(processed_url_fn) else out_key
        )
        video.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ok"

    except Exception:
        if video is not None:
            video.status = VideoStatus.FAILED
            db.commit()
        return "error"
    finally:
        db.close()
