import os
import shutil
import time
from datetime import datetime, timezone

from celery_app import celery
from config import config
from database import SessionLocal
from models import Video, VideoStatus
from sqlalchemy import select


@celery.task(name="process_video")
def process_video(video_id: str):
    db = SessionLocal()
    try:
        video = db.execute(
            select(Video).where(Video.id == video_id)
        ).scalar_one_or_none()
        if not video:
            print("not -found")
            return "not-found"
        video.status = VideoStatus.PROCESSED
        db.commit()

        src = video.original_url
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)
        dest = os.path.join(config.PROCESSED_DIR, f"{video_id}.mp4")

        time.sleep(2)
        shutil.copyfile(src, dest)

        video.status = VideoStatus.PROCESSED
        video.processed_url = dest
        video.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ok"
    except Exception:
        video.status = VideoStatus.FAILED
        db.commit()
        return "error"
    finally:
        db.close()
