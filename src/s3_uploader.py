"""Optional S3 upload for generated reports."""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def s3_configured() -> bool:
    """Check whether S3 upload environment variables are set."""
    return all(
        os.environ.get(k)
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET")
    )


def upload_directory(output_dir: Path) -> None:
    """Upload the entire output directory to S3."""
    import boto3

    bucket = os.environ["S3_BUCKET"]
    prefix = os.environ.get("S3_PREFIX", "detection-reports/").rstrip("/")
    region = os.environ.get("AWS_REGION", "us-east-1")

    s3 = boto3.client("s3", region_name=region)

    skip = {".DS_Store", "Thumbs.db", ".gitkeep"}

    uploaded = 0
    for file_path in output_dir.rglob("*"):
        if not file_path.is_file() or file_path.name in skip:
            continue
        relative = file_path.relative_to(output_dir)
        key = f"{prefix}/{relative}"
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

        s3.upload_file(
            str(file_path),
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        uploaded += 1
        logger.debug("Uploaded s3://%s/%s", bucket, key)

    logger.info("Uploaded %d files to s3://%s/%s/", uploaded, bucket, prefix)

    # Optional CloudFront invalidation
    distribution_id = os.environ.get("CLOUDFRONT_DISTRIBUTION_ID")
    if distribution_id:
        _invalidate_cloudfront(distribution_id, prefix)


def _invalidate_cloudfront(distribution_id: str, prefix: str) -> None:
    import boto3
    from datetime import datetime, timezone

    cf = boto3.client("cloudfront")
    caller_ref = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    cf.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": [f"/{prefix}/*"]},
            "CallerReference": caller_ref,
        },
    )
    logger.info("Created CloudFront invalidation for /%s/*", prefix)
