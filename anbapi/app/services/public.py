
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import Video, VideoStatus

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/videos", status_code=status.HTTP_200_OK)
async def list_public_videos(db: Session = Depends(get_db)):
    """
    Lista todos los videos públicos disponibles para votación.
    Solo se muestran los que tienen estado 'processed'.
    """
    videos = (
        db.query(Video)
        .filter(Video.status == VideoStatus.PROCESSED)
        .all()
    )

    if not videos:
        return {"message": "No hay videos disponibles para votación."}

    return [
        {
            "video_id": v.id,
            "title": v.title,
            "user_id": v.user_id,
            "processed_url": v.processed_url,
            "votes": getattr(v, "votes", 0),
            "status": v.status,
        }
        for v in videos
    ]