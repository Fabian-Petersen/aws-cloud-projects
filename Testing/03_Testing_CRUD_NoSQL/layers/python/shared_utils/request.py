"""API Gateway request parsing and validation helpers."""

import json


def parse_json_body(event):
    """Parse an API Gateway body into a JSON object.

    A dictionary body is returned unchanged, which is useful for direct tests.

    Example:
        ``parse_json_body({"body": "{\"name\": \"Asset\"}"})`` returns
        ``{"name": "Asset"}``.

    Raises:
        ValueError: If the body is absent, malformed, or not a JSON object.
    """
    body = event.get("body")
    if not body:
        raise ValueError("Missing request body")
    if isinstance(body, dict):
        return body

    try:
        data = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed request body") from exc

    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    return data


def require_fields(data, fields):
    """Require every named field to contain a truthy value.

    Example:
        ``require_fields(payload, ["location", "assets"])``.

    Raises:
        ValueError: Naming the first missing or empty field.
    """
    for field in fields:
        if not data.get(field):
            raise ValueError(f"Missing or empty field: {field}")


def require_non_empty_list(data, field, message=None):
    """Return ``data[field]`` after verifying it is a non-empty list.

    Args:
        data: Request object containing the list.
        field: Name of the list field.
        message: Optional client-facing validation message.

    Raises:
        ValueError: If the value is absent, empty, or not a list.
    """
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(message or f"{field} must contain at least one item")
    return value
