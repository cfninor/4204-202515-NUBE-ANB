import uuid
from datetime import timezone
from typing import List, Optional

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
from models import User, Video, VideoStatus
from security import get_current_user
from sqlalchemy.orm import Session
from storage_a.factory import get_storage
from workers.tasks import process_video

router = APIRouter(prefix="/api/videos", tags=["videos"])
storage = get_storage()

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def to_iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def status_str(s) -> str:
    # Enum('UPLOADED','PROCESSED','FAILED') -> 'uploaded'/'processed'/'failed'
    if isinstance(s, VideoStatus):
        return (getattr(s, "name", None) or getattr(s, "value", str(s))).lower()
    return str(s).lower()


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
        raise HTTPException(
            status_code=400, detail="Error en el archivo (tipo inválido)."
        )

    video_file.file.seek(0, 2)
    size = video_file.file.tell()
    video_file.file.seek(0)
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400, detail="Error en el archivo (tamaño inválido)."
        )

    vid = f"{uuid.uuid4()}.mp4"
    storage.save(vid, video_file.file)
    original_url = getattr(storage, "url", None)
    public_url = original_url(f"uploads/{vid}") if callable(original_url) else vid

    video = Video(
        user_id=user.id,
        title=title,
        original_url=public_url,
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


# ---------------------- GET /api/videos ----------------------
@router.get("", status_code=status.HTTP_200_OK)
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    videos: List[Video] = (
        db.query(Video)
        .filter(Video.user_id == user.id)
        .order_by(Video.uploaded_at.desc())
        .all()
    )
    response = []
    for v in videos:
        s = status_str(v.status)
        item = {
            "video_id": str(v.id),
            "title": v.title,
            "status": s,
            "uploaded_at": to_iso(v.uploaded_at),
            "processed_at": to_iso(v.processed_at),
        }
        if s == "processed" and v.processed_url:
            item["processed_url"] = v.processed_url
        response.append(item)
    return response


@router.get("/{video_id}", status_code=status.HTTP_200_OK)
def get_video_detail(
    video_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v_exists = db.query(Video).filter(Video.id == video_id).first()
    if v_exists and v_exists.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="El usuario autenticado no tiene permisos para acceder a este video (no es el propietario).",
        )

    video: Optional[Video] = (
        db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    )
    if not video:
        raise HTTPException(
            status_code=404,
            detail="El video con el video_id especificado no existe o no pertenece al usuario.",
        )

    s = status_str(video.status)
    body = {
        "video_id": str(video.id),
        "title": video.title,
        "status": s,
        "uploaded_at": to_iso(video.uploaded_at),
        "processed_at": to_iso(video.processed_at),
        "original_url": video.original_url,
        "votes": len(video.votes) if hasattr(video, "votes") else 0,
    }
    if s == "processed" and video.processed_url:
        body["processed_url"] = video.processed_url
    return body


@router.delete("/{video_id}", status_code=status.HTTP_200_OK)
async def delete_video(
    video_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        video_id_int = int(video_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="El video no existe.")

    video = (
        db.query(Video)
        .filter(Video.id == video_id_int, Video.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=404, detail="El video no existe o no pertenece al usuario."
        )

    try:
        storage.delete(video.original_url)
        if video.processed_url:
            storage.delete(video.processed_url)
    except Exception as e:
        print(f"Advertencia: no se pudo eliminar el archivo. Detalle: {e}")

    db.delete(video)
    db.commit()
    return {"message": "El video ha sido eliminado exitosamente.", "video_id": video_id}
