from datetime import datetime, timezone

from database import Base
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Sequence, String
from sqlalchemy.orm import relationship

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
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    original_url = Column(String, nullable=False)
    processed_url = Column(String, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id = Column(String, nullable=False)
    owner = relationship("User", back_populates="videos")
    votes = relationship(
        "VideoVote", back_populates="video", cascade="all, delete-orphan"
    )
