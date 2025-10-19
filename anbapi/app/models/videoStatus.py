from enum import Enum


class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    PUBLISHED = "published"
    VOTING = "voting"
    FAILED = "failed"
