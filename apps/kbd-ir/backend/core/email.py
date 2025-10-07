"""SES email helper utilities."""
from __future__ import annotations

import logging
from typing import Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional dependency during local dev
    boto3 = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore

from .config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, reset_link: str) -> None:
    """Send a password reset email via Amazon SES.

    Falls back to logging when boto3 is unavailable or credentials are missing.
    """

    subject = "【KBD-IR】パスワードリセットのご案内"
    body = f"""{recipient} 様\n\nKBD-IR にてパスワード再設定のリクエストを受け付けました。\n下記のリンクをクリックし、パスワードの再設定を完了してください。\n\nリセットリンク: {reset_link}\n有効期限: 発行から{settings.password_reset_expiration_minutes}分\n\n※心当たりがない場合は、このメールを破棄してください。\n※本メールは送信専用です。ご不明な点がありましたら、管理者までご連絡ください。\n\n--\nKBD-IR 運営\n"""

    if boto3 is None:
        logger.warning("boto3 not installed; email to %s would be: %s", recipient, body)
        return

    client = boto3.client("ses", region_name=settings.aws_region)
    try:
        client.send_email(
            Source=settings.ses_sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - network call
        logger.error("Failed to send password reset email: %s", exc)
        raise
