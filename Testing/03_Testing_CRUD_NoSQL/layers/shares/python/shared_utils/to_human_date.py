"""SAST date formatting helper used by existing API Lambdas."""

from datetime import datetime, timedelta, timezone


def to_human_date(iso_string: str) -> str:
    """Convert an ISO 8601 timestamp string to a human-readable date in SAST."""
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")


def get_local_now() -> str:
    """Return the current SAST timestamp in ISO 8601 format."""
    tz = timezone(timedelta(hours=2))
    return datetime.now(tz).isoformat()
