import argparse
import boto3
import os
from botocore.exceptions import ClientError


def upload_file(bucket: str, local_path: str, s3_key: str, region: str | None = None) -> None:
    session_kwargs = {}
    if region:
        session_kwargs["region_name"] = region

    session = boto3.Session(**session_kwargs)
    s3 = session.client("s3")

    try:
        s3.upload_file(local_path, bucket, s3_key)
        print(f"Uploaded {local_path} to s3://{bucket}/{s3_key}")
    except ClientError as exc:
        raise SystemExit(f"Failed to upload to S3: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload attendance.db to S3")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--key", default="attendance.db", help="Object key in the bucket")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION"),
        help="AWS region (optional, falls back to environment)",
    )
    parser.add_argument(
        "--db",
        default=os.path.join(os.path.dirname(__file__), "attendance.db"),
        help="Path to SQLite database file",
    )

    args = parser.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"Database file not found: {args.db}")

    upload_file(bucket=args.bucket, local_path=args.db, s3_key=args.key, region=args.region)


if __name__ == "__main__":
    main()
