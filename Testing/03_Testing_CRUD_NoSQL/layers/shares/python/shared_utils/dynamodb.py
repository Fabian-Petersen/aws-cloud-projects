"""DynamoDB pagination and value helpers."""


def scan_all(table, **kwargs):
    """Scan every page while retaining the table access pattern supplied by caller."""
    items = []
    response = table.scan(**kwargs)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            **kwargs,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return items


def query_all(table, **kwargs):
    """Query every page while retaining the key/index expression supplied by caller."""
    items = []
    response = table.query(**kwargs)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            **kwargs,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return items


def normalize_string(value: str | None) -> str:
    """Normalize status and other string comparisons used by transfer handlers."""
    return str(value or "").strip().lower()
