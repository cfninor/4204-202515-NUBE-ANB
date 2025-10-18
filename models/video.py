from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Sequence, String
from sqlalchemy.orm import relationship

from database import Base

from .videoStatus import VideoStatus

video_id_seq = Sequence("video_id_seq", start=10000, increment=1)


class Video(Base):
    __tablename__ = "videos"

    id = Column(
        Integer,
        video_id_seq,
        primary_key=True,
        server_default=video_id_seq.next_value(),
        index=True,
    )
    title = Column(String, nullable=False)
    status = Column(Enum(VideoStatus), default=VideoStatus.UPLOADED, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    original_url = Column(String, nullable=False)
    processed_url = Column(String, nullable=True)
    votes = Column(Integer, default=0)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner = relationship("User", back_populates="videos")
