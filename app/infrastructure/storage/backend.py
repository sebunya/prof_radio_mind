"""Storage backend abstraction — local filesystem or S3-compatible (Hetzner Object Storage).

At startup the correct backend is selected based on settings:
  - S3_ENDPOINT_URL set → S3Backend (Hetzner Object Storage, AWS S3, etc.)
  - S3_ENDPOINT_URL empty → LocalBackend (writes to raw_payload_storage_path)

Both backends share the same interface so callers are backend-agnostic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def write(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Persist bytes and return the canonical storage path/key."""
        ...

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """Read and return raw bytes for the given key."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if the key exists in storage."""
        ...


class LocalBackend(StorageBackend):
    """Writes files to the local filesystem under storage_root."""

    def __init__(self, storage_root: str) -> None:
        self._root = Path(storage_root)

    async def write(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def read(self, key: str) -> bytes:
        return (self._root / key).read_bytes()

    async def exists(self, key: str) -> bool:
        return (self._root / key).exists()


class S3Backend(StorageBackend):
    """Writes objects to any S3-compatible store (Hetzner Object Storage, AWS S3)."""

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "eu-central-1",
    ) -> None:
        self._endpoint = endpoint_url
        self._access_key = access_key_id
        self._secret_key = secret_access_key
        self._bucket = bucket_name
        self._region = region

    def _client_kwargs(self) -> dict:
        return {
            "endpoint_url": self._endpoint,
            "aws_access_key_id": self._access_key,
            "aws_secret_access_key": self._secret_key,
            "region_name": self._region,
        }

    async def write(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        import aioboto3

        session = aioboto3.Session()
        async with session.client("s3", **self._client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        path = f"s3://{self._bucket}/{key}"
        logger.debug("s3_write key=%s bucket=%s", key, self._bucket)
        return path

    async def read(self, key: str) -> bytes:
        import aioboto3

        session = aioboto3.Session()
        async with session.client("s3", **self._client_kwargs()) as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=key)
            return await response["Body"].read()

    async def exists(self, key: str) -> bool:
        import aioboto3
        from botocore.exceptions import ClientError

        session = aioboto3.Session()
        async with session.client("s3", **self._client_kwargs()) as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError:
                return False


def get_storage_backend() -> StorageBackend:
    """Return the configured backend based on settings."""
    from app.core.settings import settings

    if settings.s3_endpoint_url:
        return S3Backend(
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
        )
    return LocalBackend(settings.raw_payload_storage_path)
