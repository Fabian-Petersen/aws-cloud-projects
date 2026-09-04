"""DynamoDB pagination and value helpers."""


def scan_all(table, **kwargs):
    """Return every item from a paginated DynamoDB ``scan`` operation.

    Keyword arguments such as ``FilterExpression`` are retained on every page.
    """
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
    """Return every item from a paginated DynamoDB ``query`` operation.

    Keyword arguments such as ``IndexName`` and ``KeyConditionExpression`` are
    retained on every page.
    """
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


def query_first(table, **kwargs):
    """Return the first item matching a DynamoDB query, or ``None``.

    The helper supplies ``Limit=1``. Callers provide the index and key condition,
    for example ``query_first(table, IndexName="AssetIDIndex", ...)``.
    """
    response = table.query(Limit=1, **kwargs)
    items = response.get("Items", [])
    return items[0] if items else None


def normalize_string(value: str | None) -> str:
    """Convert a value to a stripped lowercase string.

    ``None`` becomes ``""``; for example, ``" Pending "`` becomes
    ``"pending"``.
    """
    return str(value or "").strip().lower()
