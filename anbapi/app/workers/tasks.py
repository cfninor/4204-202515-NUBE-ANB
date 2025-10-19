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
FAST = "+faststart"


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


def x264_video_args():
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


def build_vf_main():
    return (
        "scale=w=1280:h=720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,format=rgba"
    )


def render_main_clip(src: str, duration: float, logo: str | None, out_path: str):
    if logo and os.path.isfile(logo):
        run(
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
                "[0:v]" + build_vf_main() + "[v0];"
                "[1:v]scale=180:-1,format=rgba[wm];"
                "[v0][wm]overlay=W-w-30:30:format=auto:eval=init[v]",
                "-map",
                "[v]",
                *x264_video_args(),
                "-an",  # SIN AUDIO
                out_path,
            ]
        )
    else:
        run(
            [
                FFMPEG,
                "-y",
                "-i",
                src,
                "-t",
                f"{duration}",
                "-vf",
                build_vf_main(),
                *x264_video_args(),
                "-an",  # SIN AUDIO
                out_path,
            ]
        )


def render_color_clip(duration: float, out_path: str):
    run(
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
            *x264_video_args(),
            "-an",
            out_path,
        ]
    )


def render_logo_clip(duration: float, logo: str, out_path: str):
    run(
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
            "[0:v]scale='min(720,iw)':'min(300,ih)':"
            "force_original_aspect_ratio=decrease,"
            "format=rgba,fade=t=in:st=0:d=0.5,fade=t=out:st="
            + str(max(0.0, duration - 0.5))
            + ":d=0.5[lg];"
            "[1:v][lg]overlay=(W-w)/2:(H-h)/2[v]",
            "-map",
            "[v]",
            *x264_video_args(),
            "-an",
            out_path,
        ]
    )


def render_stub_one_frame(out_path: str):
    run(
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
            *x264_video_args(),
            "-an",
            out_path,
        ]
    )


def concat_three(intro: str, main_: str, outro: str, dest: str):
    run(
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
            *x264_video_args(),
            dest,
        ]
    )


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
        total_target = 35.0
        main_len = max(0.0, total_target - (intro_len + outro_len))

        with tempfile.TemporaryDirectory() as tmp:
            main_720 = os.path.join(tmp, "main_720.mp4")
            intro = os.path.join(tmp, "intro.mp4")
            outro = os.path.join(tmp, "outro.mp4")

            render_main_clip(src, main_len, logo if has_logo else None, main_720)

            if intro_len > 0.0:
                if has_logo:
                    render_logo_clip(intro_len, logo, intro)
                else:
                    render_color_clip(intro_len, intro)
            else:
                render_stub_one_frame(intro)

            if outro_len > 0.0:
                if has_logo:
                    render_logo_clip(outro_len, logo, outro)
                else:
                    render_color_clip(outro_len, outro)
            else:
                render_stub_one_frame(outro)

            concat_three(intro, main_720, outro, dest)

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
