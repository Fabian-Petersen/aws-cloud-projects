"""Cognito claims helpers used by API Lambda handlers."""

import json


def get_user_claims(event):
    """Return Cognito claims from a REST API Gateway proxy event.

    Missing request-context fields produce an empty dictionary rather than an
    exception, allowing the handler to return its normal unauthorized response.
    """
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )


def get_requestor_identity(event):
    """Build canonical requestor fields from authenticated Cognito claims.

    Returns:
        dict: ``requestorSub``, ``requestorEmail``, ``requestedBy``, and
        ``requestorName``. ``requestedBy`` combines ``name`` and
        ``family_name`` in the same way as existing post-request handlers.
    """
    claims = get_user_claims(event)
    requestor_name = claims.get("name", "")
    requested_by = " ".join(
        part
        for part in [requestor_name, claims.get("family_name", "")]
        if part
    ).strip()
    return {
        "requestorSub": claims.get("sub"),
        "requestorEmail": claims.get("email", ""),
        "requestedBy": requested_by,
        "requestorName": requestor_name,
    }


def parse_groups(groups_claim):
    """Return lowercase groups from supported Cognito claim representations.

    Examples:
        ``parse_groups('["Admin", "User"]')`` and
        ``parse_groups("Admin,User")`` both return ``["admin", "user"]``.
    """
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(group).lower() for group in groups_claim]

    if isinstance(groups_claim, str):
        try:
            parsed = json.loads(groups_claim)
            if isinstance(parsed, list):
                return [str(group).lower() for group in parsed]
        except Exception:
            pass

        return [group.strip().lower() for group in groups_claim.split(",")]

    return []
