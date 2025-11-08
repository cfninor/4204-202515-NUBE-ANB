import os

from .local import LocalStorage
from .s3 import S3Storage


def get_storage():
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        return S3Storage()
    base_dir = os.getenv("UPLOAD_DIR")
    return LocalStorage(base_dir=base_dir)
