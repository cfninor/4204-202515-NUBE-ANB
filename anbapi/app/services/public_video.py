from database import get_db

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from models import User, Video, VideoVote
from security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/public/videos", tags=["public_videos"])
bearer = HTTPBearer()


@router.post("/{video_id}/vote", status_code=status.HTTP_201_CREATED)
def vote_video(
	video_id: int,
	user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
):
	video = db.get(Video, video_id)
	if not video:
		raise HTTPException(status_code=404, detail="Video no encontrado.")

	vote = VideoVote(user_id=user.id, video_id=video_id)
	db.add(vote)
	try:
		db.commit()
	except IntegrityError:
		db.rollback()
		# unique constraint violation -> user already voted
		raise HTTPException(status_code=400, detail="El usuario ya votó este video.")

	return {"message": "Voto registrado exitosamente."}



