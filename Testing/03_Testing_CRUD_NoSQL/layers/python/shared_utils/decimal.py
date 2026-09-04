"""DynamoDB Decimal JSON serialization helper."""

from decimal import Decimal


def decimal_serializer(obj):
    """Convert DynamoDB Decimal values to JSON-compatible integers or floats."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError
