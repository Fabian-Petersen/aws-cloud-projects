"""S3 presigned-upload helper used by API Lambda handlers."""


def generate_presigned_upload_url(
    s3,
    bucket_name: str,
    key: str,
    content_type: str = "application/octet-stream",
    expires_in: int = 3600,
) -> str:
    """Generate the same S3 v4 PUT URL shape used by upload-request handlers."""
    return s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
