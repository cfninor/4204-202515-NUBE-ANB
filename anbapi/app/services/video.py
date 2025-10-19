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

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

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
    return {
        "message": "Video subido correctamente, procesamiento en curso",
        "task_id": video.id,
    }
