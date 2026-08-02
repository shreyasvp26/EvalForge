"""S3-compatible object storage via boto3 (MinIO, R2, AWS, …)."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from agent_eval_infrastructure.storage.protocol import ObjectMetadata


class S3CompatibleObjectStorage:
    """ObjectStorage backed by any S3-compatible API (endpoint_url configurable)."""

    def __init__(
        self,
        client: Any,
        *,
        bucket: str,
    ) -> None:
        self._client = client
        self._bucket = bucket

    def put(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        response = self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        etag = response.get("ETag")
        if isinstance(etag, str):
            etag = etag.strip('"')
        else:
            etag = None
        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size_bytes=len(data),
            etag=etag,
        )

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise LookupError(f"Object not found: {key}") from exc
            raise
        body = response["Body"].read()
        return bytes(body)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def head(self, key: str) -> ObjectMetadata | None:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {
                "404",
                "NoSuchKey",
                "404 Not Found",
                "NotFound",
            }:
                return None
            raise
        etag = response.get("ETag")
        if isinstance(etag, str):
            etag = etag.strip('"')
        else:
            etag = None
        content_type = str(response.get("ContentType") or "application/octet-stream")
        size = int(response.get("ContentLength") or 0)
        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size_bytes=size,
            etag=etag,
        )


def create_s3_client(
    *,
    endpoint_url: str | None,
    access_key: str,
    secret_key: str,
    region: str,
    force_path_style: bool = True,
) -> Any:
    """Build a boto3 S3 client without hardcoding a single cloud vendor."""
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(s3={"addressing_style": "path" if force_path_style else "auto"}),
    )
