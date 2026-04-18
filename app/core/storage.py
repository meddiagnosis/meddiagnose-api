"""
Cloud storage abstraction layer.

Supports local filesystem (development) and Google Cloud Storage / AWS S3 (production).
Set STORAGE_BACKEND in .env: "local", "gcs", or "s3".
"""

import os
import uuid
import logging
from pathlib import Path
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        """Upload file and return the public/signed URL or path."""

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete a file. Returns True if successful."""

    @abstractmethod
    async def get_url(self, file_path: str) -> str:
        """Get a URL for the file (signed URL for cloud, local path otherwise)."""


class LocalStorage(StorageBackend):
    def __init__(self):
        self.base_dir = Path(get_settings().UPLOAD_DIR)

    async def upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        fpath = user_dir / safe_name
        with open(fpath, "wb") as f:
            f.write(file_bytes)
        return str(fpath)

    async def delete(self, file_path: str) -> bool:
        try:
            Path(file_path).unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False

    async def get_url(self, file_path: str) -> str:
        return f"/static/uploads/{Path(file_path).relative_to(self.base_dir)}"


class GCSStorage(StorageBackend):
    def __init__(self):
        settings = get_settings()
        self.bucket_name = settings.GCS_BUCKET or "meddiagnose-uploads"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client()
        return self._client

    async def upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob_name = f"uploads/{user_id}/{uuid.uuid4().hex}_{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_bytes, content_type="application/octet-stream")
        logger.info(f"Uploaded to GCS: gs://{self.bucket_name}/{blob_name}")
        return f"gs://{self.bucket_name}/{blob_name}"

    async def delete(self, file_path: str) -> bool:
        try:
            client = self._get_client()
            blob_name = file_path.replace(f"gs://{self.bucket_name}/", "")
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"GCS delete failed: {e}")
            return False

    async def get_url(self, file_path: str) -> str:
        from datetime import timedelta
        client = self._get_client()
        blob_name = file_path.replace(f"gs://{self.bucket_name}/", "")
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(expiration=timedelta(hours=1))


class S3Storage(StorageBackend):
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "meddiagnose-uploads")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    async def upload(self, file_bytes: bytes, filename: str, user_id: int) -> str:
        client = self._get_client()
        key = f"uploads/{user_id}/{uuid.uuid4().hex}_{filename}"
        client.put_object(Bucket=self.bucket_name, Key=key, Body=file_bytes)
        logger.info(f"Uploaded to S3: s3://{self.bucket_name}/{key}")
        return f"s3://{self.bucket_name}/{key}"

    async def delete(self, file_path: str) -> bool:
        try:
            client = self._get_client()
            key = file_path.replace(f"s3://{self.bucket_name}/", "")
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    async def get_url(self, file_path: str) -> str:
        client = self._get_client()
        key = file_path.replace(f"s3://{self.bucket_name}/", "")
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=3600,
        )


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        backend = os.getenv("STORAGE_BACKEND", "local").lower()
        if backend == "gcs":
            _storage = GCSStorage()
        elif backend == "s3":
            _storage = S3Storage()
        else:
            _storage = LocalStorage()
        logger.info(f"Storage backend: {backend}")
    return _storage
