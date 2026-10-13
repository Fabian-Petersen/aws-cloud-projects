Update `getStoreCostMetrics` to scope maintenance-cost data using authenticated Cognito claims.

Access rules:

- `admin`: include all maintenance actions across all locations.
- `maintenance`: include only actions linked to maintenance requests where `assign_to_sub == claims["sub"]`. Do not restrict technicians by their stored location and do not accept a technician sub from query parameters.
- `manager` / `user`: include only actions from the authenticated user’s stored location. Ignore client-supplied locations for authorization.

Maintenance actions contain the costs and `request_id`; maintenance requests contain `assign_to_sub`. Join them using `action.request_id == request.id`.

Preserve the existing cost formula:

total_cost_parts + total_cost_sundries + total_cost_contractor

Return the existing frontend-compatible shapes:

Top-level admin:
{
"2026": [
{ "name": "maitland", "code": "MAI", "value": 25000 }
]
}

Top-level maintenance and manager/user:
{
"2026": [
{ "name": "Jan", "value": 1000 },
{ "name": "Feb", "value": 1500 }
]
}

For technician month/job drilldowns, ignore `userLocation` and return only jobs assigned to `claims["sub"]`, including jobs across every location. Jobs assigned to other technicians must never contribute.

Preserve pagination, existing response schemas, CORS handling, and cost calculation. Add the maintenance-request table to the Lambda’s least-privilege DynamoDB permissions if required. Perform Python syntax validation after the change.
