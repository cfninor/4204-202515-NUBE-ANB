import uuid

from database import get_db
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import HTTPBearer
from models import User, Video, VideoStatus
from security import get_current_user
from sqlalchemy.orm import Session
from storage_a.local import LocalStorage
from workers.tasks import process_video

router = APIRouter(prefix="/api/videos", tags=["videos"])
bearer = HTTPBearer()
storage = LocalStorage()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    request: Request,
    title: str = Form(...),
    video_file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if video_file.content_type not in {"video/mp4", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Solo se permite MP4")

    vid = f"{uuid.uuid4()}.mp4"
    path = storage.save(vid, video_file.file)

    video = Video(
        user_id=user.id,
        title=title,
        original_url=path,
        status=VideoStatus.UPLOADED,
        task_id=VideoStatus.UPLOADED,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    task = process_video.delay(video.id)
    video.task_id = task.id
    db.commit()
    return {
        "message": "Video subido correctamente, procesamiento en curso",
        "task_id": video.id,
    }
