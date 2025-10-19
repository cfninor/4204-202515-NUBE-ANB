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
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Video, VideoStatus
from security import get_current_user
from storage_a.local import LocalStorage
from workers.tasks import process_video

router = APIRouter(prefix="/api/videos", tags=["videos"])
storage = LocalStorage()

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ---------------------- POST /api/videos/upload ----------------------
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    request: Request,
    title: str = Form(...),
    video_file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if video_file.content_type not in {"video/mp4", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Error en el archivo (tipo inválido).")
    
    video_file.file.seek(0, 2)  
    size = video_file.file.tell()
    video_file.file.seek(0)     
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Error en el archivo (tamaño inválido)."
        )


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
    return {"message": "Video subido correctamente, procesamiento en curso", "task_id": video.id}

# ---------------------- GET /api/videos ----------------------
@router.get("", status_code=status.HTTP_200_OK)
def list_videos(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    videos: List[Video] = (
        db.query(Video)
        .filter(Video.user_id == user.id)
        .order_by(Video.uploaded_at.desc())
        .all()
    )

    def to_item(v: Video):
        status_value = v.status.value if isinstance(v.status, VideoStatus) else str(v.status)
        return {
            "id": v.id,
            "title": v.title,
            "status": status_value,
            "uploaded_at": v.uploaded_at,
            "processed_at": v.processed_at,
            "processed_url": v.processed_url if status_value.lower() == "processed" else None,
        }

    return [to_item(v) for v in videos]

# ---------------------- GET /api/videos/{video_id} ----------------------
@router.get("/{video_id}", status_code=status.HTTP_200_OK)
def get_video_detail(
    video_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    v_exists = db.query(Video).filter(Video.id == video_id).first()
    if v_exists and v_exists.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este video")

    video: Optional[Video] = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado")

    status_value = video.status.value if isinstance(video.status, VideoStatus) else str(video.status)
    return {
        "id": video.id,
        "title": video.title,
        "status": status_value,
        "uploaded_at": video.uploaded_at,
        "processed_at": video.processed_at,
        "original_url": video.original_url,
        "processed_url": video.processed_url if status_value.lower() == "processed" else None,
    }