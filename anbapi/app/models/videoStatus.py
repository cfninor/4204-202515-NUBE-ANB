import enum


class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
