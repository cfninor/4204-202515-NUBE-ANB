import os
import mimetypes
from typing import BinaryIO
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from .base import Storage 


class S3Storage(Storage):

    def __init__(self) -> None:
        self.bucket = os.getenv("S3_BUCKET")
        if not self.bucket:
            raise RuntimeError("S3_BUCKET no está definido en el entorno.")

        self.region = os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "us-east-1"
        self.base_prefix = (os.getenv("S3_BASE_PREFIX", "") or "").strip("/")
        self.presign_expires = int(os.getenv("S3_PRESIGN_EXPIRES", "3600"))

        self._s3 = boto3.client(
            "s3",
            region_name=self.region,
            config=BotoConfig(s3={"addressing_style": "virtual"}),
        )

    def save(self, key: str, stream: BinaryIO) -> str:
        full_key = self._full_key(key)
        content_type, _ = mimetypes.guess_type(full_key)
        extra = {"ContentType": content_type} if content_type else {}
        self._s3.upload_fileobj(stream, self.bucket, full_key, ExtraArgs=extra)
        return key

    def url(self, key: str) -> str:
        full_key = self._full_key(key)
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": full_key},
            ExpiresIn=self.presign_expires,
        )

    def exists(self, key: str) -> bool:
        full_key = self._full_key(key)
        try:
            self._s3.head_object(Bucket=self.bucket, Key=full_key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            return code not in ("404", "NoSuchKey", "NotFound")

    def delete(self, key: str) -> None:
        full_key = self._full_key(key)
        self._s3.delete_object(Bucket=self.bucket, Key=full_key)

    def _full_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self.base_prefix}/{key}" if self.base_prefix else key