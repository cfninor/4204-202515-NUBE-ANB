from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class VideoListItem(BaseModel):
    id: int
    title: str
    status: str                  
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    processed_url: Optional[str] = None

    class Config:
        from_attributes = True  

class VideoDetail(BaseModel):
    id: int
    title: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    original_url: Optional[str] = None
    processed_url: Optional[str] = None

    class Config:
        from_attributes = True
