"""API Gateway proxy response helper."""

import json

from shared_utils.decimal import decimal_serializer


def _response(status_code, body, headers):
    """Construct the JSON proxy response shape used by the API Lambdas."""
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer),
    }
