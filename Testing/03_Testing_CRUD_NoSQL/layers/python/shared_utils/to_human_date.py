"""SAST date formatting helper used by existing API Lambdas."""

from datetime import datetime, timedelta, timezone


def to_human_date(iso_string: str) -> str:
    """Convert an ISO 8601 timestamp string to a human-readable date in SAST."""
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")


def to_human_date_only(iso_string: str) -> str:
    """Convert an ISO 8601 date or timestamp to a date-only display value.

    No timezone conversion is applied because a date-only field must not move
    to the previous or following day. For example, ``"2026-08-31"`` becomes
    ``"31 Aug 2026"``.
    """
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y")


def format_dates(data, date_time_fields=None, date_fields=None):
    """Format selected date fields recursively in a dictionary or list.

    The supplied object is updated in place and also returned for convenience.
    Fields in ``date_time_fields`` use SAST date-time formatting, while fields
    in ``date_fields`` use date-only formatting. Empty values are left intact.

    Example:
        ``format_dates(item, {"createdAt"}, {"expectedDate"})``
    """
    date_time_fields = set(date_time_fields or [])
    date_fields = set(date_fields or [])

    if isinstance(data, dict):
        for key, value in data.items():
            if not value:
                continue
            if key in date_time_fields:
                data[key] = to_human_date(value)
            elif key in date_fields:
                data[key] = to_human_date_only(value)
            else:
                format_dates(value, date_time_fields, date_fields)
    elif isinstance(data, list):
        for item in data:
            format_dates(item, date_time_fields, date_fields)

    return data


def get_local_now() -> str:
    """Return the current SAST timestamp in ISO 8601 format."""
    tz = timezone(timedelta(hours=2))
    return datetime.now(tz).isoformat()
