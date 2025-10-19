import os
import subprocess
import tempfile
from datetime import datetime, timezone

from celery_app import celery
from config import config
from database import SessionLocal
from models import Video, VideoStatus
from sqlalchemy import select

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
COLOR = "color=size=1280x720:rate=30:color=black"
ANULL = "anullsrc=channel_layout=stereo:sample_rate=48000"


def run(cmd):
    subprocess.run(cmd, check=True)


def has_audio_stream(path: str) -> bool:
    try:
        out = (
            subprocess.check_output(
                [
                    FFPROBE,
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    path,
                ],
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )
        return out != ""
    except subprocess.CalledProcessError:
        return False


@celery.task(name="process_video")
def process_video(video_id: str):
    db = SessionLocal()
    try:
        video_id = int(video_id)
        video = db.execute(
            select(Video).where(Video.id == video_id)
        ).scalar_one_or_none()
        if not video:
            return "not-found"

        src = video.original_url
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)
        dest = os.path.join(config.PROCESSED_DIR, f"{video_id}.mp4")

        logo = os.path.join(config.ASSETS_DIR, "logo.jpg")
        has_logo = os.path.isfile(logo)

        outro_len = config.OUTRO_SECONDS
        intro_len = config.INTRO_SECONDS
        total_target = 30.0
        main_len = max(0.0, total_target - (intro_len + outro_len))

        vf_main = (
            "scale=w=1280:h=720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black"
        )

        with tempfile.TemporaryDirectory() as tmp:
            main_720 = os.path.join(tmp, "main_720.mp4")
            intro = os.path.join(tmp, "intro.mp4")
            outro = os.path.join(tmp, "outro.mp4")

            if has_audio_stream(src):
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-i",
                        src,
                        "-t",
                        f"{main_len}",
                        "-vf",
                        vf_main,
                        "-r",
                        "30",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-shortest",
                        main_720,
                    ]
                )
            else:
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-i",
                        src,  # [0]
                        "-f",
                        "lavfi",
                        "-t",
                        f"{main_len}",
                        "-i",
                        ANULL,  # [1]
                        "-t",
                        f"{main_len}",
                        "-vf",
                        vf_main,
                        "-r",
                        "30",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-shortest",
                        main_720,
                    ]
                )

            if has_logo:
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-loop",
                        "1",
                        "-t",
                        f"{intro_len}",
                        "-i",
                        logo,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{intro_len}",
                        "-i",
                        COLOR,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{intro_len}",
                        "-i",
                        ANULL,
                        "-filter_complex",
                        "[0:v]scale='min(720,iw)':'min(300,ih)':force_original_aspect_ratio=decrease,"
                        "format=rgba,fade=t=in:st=0:d=0.5,fade=t=out:st="
                        + str(max(0.0, intro_len - 0.5))
                        + ":d=0.5[lg];"
                        "[1:v][lg]overlay=(W-w)/2:(H-h)/2[v]",
                        "-map",
                        "[v]",
                        "-map",
                        "2:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-shortest",
                        intro,
                    ]
                )
            else:
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-f",
                        "lavfi",
                        "-t",
                        f"{intro_len}",
                        "-i",
                        COLOR,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{intro_len}",
                        "-i",
                        ANULL,
                        "-map",
                        "0:v",
                        "-map",
                        "1:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-shortest",
                        intro,
                    ]
                )

            if has_logo:
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-loop",
                        "1",
                        "-t",
                        f"{outro_len}",
                        "-i",
                        logo,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{outro_len}",
                        "-i",
                        COLOR,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{outro_len}",
                        "-i",
                        ANULL,
                        "-filter_complex",
                        "[0:v]scale='min(720,iw)':'min(300,ih)':force_original_aspect_ratio=decrease,"
                        "format=rgba,fade=t=in:st=0:d=0.5,fade=t=out:st="
                        + str(max(0.0, outro_len - 0.5))
                        + ":d=0.5[lg];"
                        "[1:v][lg]overlay=(W-w)/2:(H-h)/2[v]",
                        "-map",
                        "[v]",
                        "-map",
                        "2:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-shortest",
                        outro,
                    ]
                )
            else:
                run(
                    [
                        FFMPEG,
                        "-y",
                        "-f",
                        "lavfi",
                        "-t",
                        f"{outro_len}",
                        "-i",
                        COLOR,
                        "-f",
                        "lavfi",
                        "-t",
                        f"{outro_len}",
                        "-i",
                        ANULL,
                        "-map",
                        "0:v",
                        "-map",
                        "1:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-ar",
                        "48000",
                        "-shortest",
                        outro,
                    ]
                )

            run(
                [
                    FFMPEG,
                    "-y",
                    "-i",
                    intro,
                    "-i",
                    main_720,
                    "-i",
                    outro,
                    "-filter_complex",
                    "[0:v]setpts=PTS-STARTPTS[v0];"
                    "[0:a]asetpts=PTS-STARTPTS, aformat=channel_layouts=stereo,aresample=48000[a0];"
                    "[1:v]setpts=PTS-STARTPTS[v1];"
                    "[1:a]asetpts=PTS-STARTPTS, aformat=channel_layouts=stereo,aresample=48000[a1];"
                    "[2:v]setpts=PTS-STARTPTS[v2];"
                    "[2:a]asetpts=PTS-STARTPTS, aformat=channel_layouts=stereo,aresample=48000[a2];"
                    "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
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
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-movflags",
                    "+faststart",
                    dest,
                ]
            )

        video.status = VideoStatus.PROCESSED
        video.processed_url = dest
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
