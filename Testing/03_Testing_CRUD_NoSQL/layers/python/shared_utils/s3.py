"""S3 helpers used by API Lambda handlers."""


def delete_prefix(s3, bucket_name: str, prefix: str) -> int:
    """Delete every object below an S3 prefix and return the object count.

    ``list_objects_v2`` pages contain at most 1,000 objects. Using the
    paginator ensures large request folders are completely removed while each
    ``delete_objects`` call remains within S3's 1,000-key batch limit.

    Raises:
        RuntimeError: If S3 reports that any object in a batch was not deleted.
    """
    deleted_count = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if not objects:
            continue

        response = s3.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": objects, "Quiet": True},
        )
        errors = response.get("Errors", [])
        if errors:
            failed_keys = ", ".join(error.get("Key", "unknown") for error in errors)
            raise RuntimeError(f"Failed to delete S3 objects: {failed_keys}")
        deleted_count += len(objects)

    return deleted_count


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
