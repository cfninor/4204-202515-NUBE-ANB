import os

from config import config

from .base import Storage


class LocalStorage(Storage):
    def __init__(self, base_dir: str | None = None):
        self.base_upload = base_dir or config.UPLOAD_DIR

    def save(self, key: str, stream) -> str:
        os.makedirs(self.base_upload, exist_ok=True)
        path = os.path.join(self.base_upload, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(stream.read())
        return path

    def download_to_path(self, key: str, dest_path: str) -> None:
        src_path = os.path.join(self.base_upload, key)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(src_path, "rb") as src, open(dest_path, "wb") as dst:
            dst.write(src.read())

    def url(self, key: str) -> str:
        return os.path.join(self.base_upload, key)

    def exists(self, key: str) -> bool:
        return os.path.exists(os.path.join(self.base_upload, key))

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
