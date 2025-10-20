import os

from config import config

from .base import Storage


class LocalStorage(Storage):
    base_upload = config.UPLOAD_DIR

    def save(self, key: str, stream) -> str:
        os.makedirs(self.base_upload, exist_ok=True)
        path = os.path.join(self.base_upload, key)
        with open(path, "wb") as f:
            f.write(stream.read())
        return path

    def url(self, key: str) -> str:
        return f"/files/{key}"

    def exists(self, key: str) -> bool:
        return os.path.exists(os.path.join(self.base_upload, key))

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
