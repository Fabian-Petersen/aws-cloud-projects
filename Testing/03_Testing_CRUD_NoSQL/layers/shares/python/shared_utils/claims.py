"""Cognito claims helpers used by API Lambda handlers."""

import json


def get_user_claims(event):
    """Extract REST API Cognito authorizer claims from an API Gateway event."""
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )


def parse_groups(groups_claim):
    """Parse Cognito group claims in list, JSON-list, or comma-separated form."""
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
