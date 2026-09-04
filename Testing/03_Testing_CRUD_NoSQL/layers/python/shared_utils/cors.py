"""CORS helpers matching the API Lambda response conventions."""

from shared_utils._response import _response


DEFAULT_ALLOWED_ORIGINS = [
    "https://www.crud-nosql.app.fabian-portfolio.net",
    "https://crud-nosql.app.fabian-portfolio.net",
    "http://localhost:5173",
]
DEFAULT_ALLOWED_HEADERS = (
    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
)


def handle_request_metadata(
    event,
    allowed_origins=DEFAULT_ALLOWED_ORIGINS,
    allowed_methods="GET,POST,OPTIONS",
):
    """Extract the HTTP method and construct CORS headers from request origin."""
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""
    allowed_origin = origin if origin in allowed_origins else ""

    response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": allowed_methods,
        "Access-Control-Allow-Headers": DEFAULT_ALLOWED_HEADERS,
        "Access-Control-Allow-Credentials": "true",
    }
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )
    return method, response_headers


def handle_options_request(method, headers):
    """Return the existing API preflight response, or None for other methods."""
    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, headers)
    return None
