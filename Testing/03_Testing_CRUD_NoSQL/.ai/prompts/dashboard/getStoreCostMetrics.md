Status = `Pending`

Update `getStoreCostMetrics` so technician cost drilldowns provide a clear hierarchy instead of jumping directly from a month to jobs.

Required technician hierarchy:

Maintenance Cost YTD
-> month
-> locations where the technician actioned assigned jobs
-> jobs/equipment at the selected location
-> frontend opens the selected job using `action_id`

Use authenticated Cognito claims for authorization:

- Identify technicians from the `maintenance` group.
- Filter maintenance requests using:
  `assign_to_sub == claims["sub"]`
- Join actions using:
  `maintenance_action.request_id == maintenance_request.id`
- Never filter technicians by their home location.
- Never accept a technician sub from query parameters.
- A selected location is only a drilldown filter after technician ownership has been enforced.

Technician response contracts:

1. Initial request — costs grouped by month:

{
"2026": [
{ "name": "Jan", "value": 2500 },
{ "name": "Feb", "value": 1800 }
]
}

2. Month selected — costs grouped by action location:

Request:
`?year=2026&month=Oct&location=all`

Response:
{
"scope": "locations",
"year": "2026",
"month": "Oct",
"data": [
{
"name": "central services",
"code": "CTS",
"value": 1500,
"job_count": 2
},
{
"name": "golden acre",
"code": "GAC",
"value": 3000,
"job_count": 1
}
]
}

Only include locations containing jobs assigned to the authenticated technician.

3. Location selected — return jobs and equipment:

Request:
`?year=2026&month=Oct&location=central services`

Response:
{
"scope": "jobs",
"location": "central services",
"year": "2026",
"month": "Oct",
"total_jobs": 2,
"total_cost": 1500,
"jobs": [
{
"request_id": "request-123",
"action_id": "action-123",
"jobcardNumber": "Job-CTS-202610-0001",
"assetID": "ASSET-001",
"equipment": "Bandsaw",
"assets": [
{
"assetID": "ASSET-001",
"equipment": "Bandsaw"
}
],
"date": "2026-10-10T08:00:00+02:00",
"costs": {
"parts": 500,
"sundries": 100,
"contractor": 0,
"total": 600
}
}
]
}

Equipment handling:

- Read equipment information from the maintenance request linked by `request_id`.
- Support both the legacy top-level `assetID` and the newer request `assets` array.
- Return available asset IDs, equipment names, and other existing identifying fields.
- If no asset ID exists, keep the job in the response and use `jobcardNumber` or `request_id` as its display fallback.
- Keep one cost total per job/action; do not duplicate the action cost for every asset.

Preserve existing scopes:

- Admin: all authorized costs and existing site/month/job drilldowns.
- Manager/user: authenticated assigned location only.
- Maintenance: assigned jobs across every location.

Preserve the existing formula:

`total_cost_parts + total_cost_sundries + total_cost_contractor`

Paginate all DynamoDB scans/queries and update schemas or lightweight validation for the new `scope`, location breakdown, and equipment-enriched job response.
