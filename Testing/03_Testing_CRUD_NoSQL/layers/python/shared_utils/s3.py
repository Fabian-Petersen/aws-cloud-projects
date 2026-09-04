"""S3 presigned-upload helper used by API Lambda handlers."""


def validate_upload_metadata(files, owner_label="item"):
    """Validate frontend upload descriptors and return the original list.

    Each descriptor must be a dictionary with a non-empty ``filename``. The
    optional ``owner_label`` is included in client-facing validation messages.

    Example:
        ``validate_upload_metadata([{"filename": "asset.webp"}], "asset 0")``.

    Raises:
        ValueError: If the collection is not a list or a filename is missing.
    """
    if files is None:
        return []
    if not isinstance(files, list):
        raise ValueError(f"Uploads for {owner_label} must be a list")
    for file_info in files:
        if not isinstance(file_info, dict) or not file_info.get("filename"):
            raise ValueError(f"Every upload for {owner_label} requires a filename")
    return files


def generate_presigned_upload_url(
    s3,
    bucket_name: str,
    key: str,
    content_type: str = "application/octet-stream",
    expires_in: int = 3600,
) -> str:
    """Generate an S3 v4 presigned PUT URL with a required content type.

    The caller must send the same ``Content-Type`` value when uploading or S3
    will reject the signed request. URLs expire after one hour by default.
    """
    return s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
