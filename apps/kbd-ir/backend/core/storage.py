"""S3 storage helper functions."""
from __future__ import annotations

import uuid
from typing import Dict

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional dependency during local dev
    boto3 = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore

from fastapi import HTTPException, status

from .config import settings


def _ensure_boto3_client():
    if boto3 is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 client unavailable",
        )
    return boto3.client("s3", region_name=settings.aws_region)


def build_submission_key(tournament_slug: str, song_id: str, user_id: str) -> str:
    """Build a deterministic S3 object key for score submissions."""

    return "/".join(
        [
            settings.s3_base_prefix.strip("/"),
            tournament_slug,
            song_id,
            user_id,
            f"{uuid.uuid4()}-raw",
        ]
    )


def generate_presigned_upload(key: str, content_type: str = "image/jpeg", expires_in: int = 900) -> Dict[str, str]:
    """Generate a presigned POST payload for uploading a photo."""

    client = _ensure_boto3_client()
    try:
        return client.generate_presigned_post(
            Bucket=settings.s3_bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[["starts-with", "$Content-Type", "image/"]],
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - network call
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate upload URL",
        ) from exc
