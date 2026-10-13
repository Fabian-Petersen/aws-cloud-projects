# Fix Maintenance Cost YTD Backend Response for Technician

## Objective

Update the backend Maintenance Cost YTD logic so that users in the `maintenance` / technician group receive the **same response structure and drilldown hierarchy as Admin**.

The only difference must be the data scope:

```text
Admin
    -> all maintenance jobs

Technician / maintenance
    -> only jobs where assign_to_sub == authenticated Cognito claims["sub"]
```

Do not scope technician data by `userLocation`.

Do not change the frontend response contract.

---

## Current working Admin behaviour

Admin currently returns the correct top-level structure grouped by location:

```json
[
  {
    "name": "middestad mall",
    "code": "MSM",
    "value": 0
  },
  {
    "name": "distribution centre",
    "code": "DCN",
    "value": 7095
  },
  {
    "name": "central services",
    "code": "CTS",
    "value": 5000
  },
  {
    "name": "maitland",
    "code": "VTR",
    "value": 55296
  },
  {
    "name": "khayelitsha",
    "code": "IKH",
    "value": 0
  },
  {
    "name": "golden acre",
    "code": "GAC",
    "value": 1950
  },
  {
    "name": "bellville",
    "code": "BTX",
    "value": 13165
  },
  {
    "name": "wynberg",
    "code": "WBG",
    "value": 0
  },
  {
    "name": "phillipi",
    "code": "PHP",
    "value": 0
  },
  {
    "name": "atlantic meat store",
    "code": "AMS",
    "value": 0
  }
]
```

Admin drilldown then returns months for the selected location:

```json
[
  {
    "name": "Jan",
    "value": 0
  },
  {
    "name": "Feb",
    "value": 0
  },
  {
    "name": "Mar",
    "value": 0
  },
  {
    "name": "Apr",
    "value": 0
  },
  {
    "name": "May",
    "value": 34325
  },
  {
    "name": "Jun",
    "value": 1595
  },
  {
    "name": "Jul",
    "value": 0
  },
  {
    "name": "Aug",
    "value": 3056
  },
  {
    "name": "Sep",
    "value": 8540
  },
  {
    "name": "Oct",
    "value": 7780
  },
  {
    "name": "Nov",
    "value": 0
  },
  {
    "name": "Dec",
    "value": 0
  }
]
```

The next drilldown returns individual jobs:

```json
{
  "May": [
    {
      "name": "RT-0006",
      "value": 3795
    },
    {
      "name": "RT-0208",
      "value": 4795
    },
    {
      "name": "RT-0036",
      "value": 3295
    }
  ]
}
```

This Admin implementation is the reference.

Do not change its response structure.

---

## Current incorrect Technician behaviour

Technician currently receives months as the top-level response:

```json
[
  {
    "name": "Jan",
    "value": 0
  },
  {
    "name": "Feb",
    "value": 0
  },
  {
    "name": "Mar",
    "value": 0
  },
  {
    "name": "Apr",
    "value": 0
  },
  {
    "name": "May",
    "value": 0
  },
  {
    "name": "Jun",
    "value": 0
  },
  {
    "name": "Jul",
    "value": 0
  },
  {
    "name": "Aug",
    "value": 0
  },
  {
    "name": "Sep",
    "value": 0
  },
  {
    "name": "Oct",
    "value": 5000
  },
  {
    "name": "Nov",
    "value": 0
  },
  {
    "name": "Dec",
    "value": 0
  }
]
```

The next technician drilldown returns:

```json
[
  {
    "name": null,
    "value": 5000
  }
]
```

This is wrong.

The technician path is using a different aggregation structure from Admin.

---

# Required Technician behaviour

Technician must follow exactly the same hierarchy as Admin:

```text
Location
    -> Month
        -> Job
```

The only difference is that the source jobs must first be restricted to those assigned to the authenticated technician.

Use:

```python
claims["sub"]
```

and match it against:

```python
assign_to_sub
```

or the confirmed equivalent field in the repository.

Conceptually:

```python
technician_sub = claims["sub"]

authorised_jobs = [
    job
    for job in jobs
    if job.get("assign_to_sub") == technician_sub
]
```

Then pass `authorised_jobs` through the same aggregation logic used for Admin.

---

# Required top-level Technician response

Suppose the authenticated technician has jobs at:

```text
Distribution Centre -> R2,000
Central Services    -> R5,000
Golden Acre         -> R1,500
Maitland            -> R4,000
```

The technician response must look like:

```json
[
  {
    "name": "distribution centre",
    "code": "DCN",
    "value": 2000
  },
  {
    "name": "central services",
    "code": "CTS",
    "value": 5000
  },
  {
    "name": "golden acre",
    "code": "GAC",
    "value": 1500
  },
  {
    "name": "maitland",
    "code": "VTR",
    "value": 4000
  }
]
```

If the Admin endpoint intentionally includes zero-value locations, preserve that same behaviour for technician as well.

The important requirement is that the response schema is identical:

```json
{
  "name": "location name",
  "code": "LOCATION_CODE",
  "value": 1234
}
```

Technician must not receive month objects at the initial level.

---

# Required location drilldown for Technician

When the technician selects a location such as:

```text
CTS
```

return the month breakdown for only that technician's jobs at that location.

Example:

```json
[
  {
    "name": "Jan",
    "value": 0
  },
  {
    "name": "Feb",
    "value": 0
  },
  {
    "name": "Mar",
    "value": 0
  },
  {
    "name": "Apr",
    "value": 0
  },
  {
    "name": "May",
    "value": 0
  },
  {
    "name": "Jun",
    "value": 0
  },
  {
    "name": "Jul",
    "value": 0
  },
  {
    "name": "Aug",
    "value": 0
  },
  {
    "name": "Sep",
    "value": 0
  },
  {
    "name": "Oct",
    "value": 5000
  },
  {
    "name": "Nov",
    "value": 0
  },
  {
    "name": "Dec",
    "value": 0
  }
]
```

The backend filter at this level should conceptually be:

```python
job.get("assign_to_sub") == claims["sub"]
and job location == selected location
```

Use the existing repository fields and comparison conventions.

---

# Required month drilldown for Technician

When the technician selects a month, return the individual jobs contributing to the total.

Example:

```json
{
  "Oct": [
    {
      "name": "RT-0123",
      "value": 2000
    },
    {
      "name": "RT-0145",
      "value": 3000
    }
  ]
}
```

The job identifier and response format must be identical to Admin.

There must never be:

```json
{
  "name": null
}
```

for a valid job drilldown.

Find the actual cause of `name: null` rather than replacing it with a fallback string.

---

# Access model

Preserve this access behaviour:

```text
admin
    -> all jobs

maintenance
    -> jobs where assign_to_sub == claims["sub"]

manager / user
    -> jobs belonging to the authenticated user's assigned location
```

Technician must not be filtered by:

```text
userLocation
home location
base branch
frontend-supplied sub
```

A technician may complete work at multiple branches.

---

# Important implementation requirement

Do not maintain a separate technician aggregation path if Admin already has the correct implementation.

Prefer this pattern:

```python
if group == "admin":
    scoped_jobs = all_jobs

elif group == "maintenance":
    scoped_jobs = [
        job
        for job in all_jobs
        if job.get("assign_to_sub") == claims["sub"]
    ]

else:
    scoped_jobs = location_scoped_jobs
```

After that, use the same functions for:

```text
group by location
    -> group selected location by month
        -> return selected month's jobs
```

The access scope should differ.

The aggregation contract should not.

---

# Investigate before modifying

Trace the current Maintenance Cost backend logic and identify:

1. Where Admin gets its location-level response.
2. Where technician branches into a month-level response instead.
3. Whether technician logic currently uses `userLocation`.
4. Whether `assign_to_sub` exists on the maintenance request rather than maintenance action.
5. How request records are linked to action/cost records.
6. Where location `name` and `code` are obtained.
7. Why technician job drilldown produces `"name": null`.
8. Whether technician uses a different mapping/helper from Admin.

If assignment and cost are stored in separate tables, resolve technician ownership from the request/job record first and then aggregate the linked action cost.

Do not assume the cost/action table contains `assign_to_sub`.

---

# Preserve cost calculation

Do not change how maintenance cost is calculated.

Continue using the same fields and helpers currently used by Admin.

This task is about:

```text
which jobs are authorised
+
how those authorised jobs are grouped
```

It is not about redefining maintenance cost.

---

# Security

The backend must derive technician identity from the authenticated Cognito claims:

```python
claims["sub"]
```

Do not accept the technician `sub` from:

```text
query string
path parameter
request body
frontend
```

A technician must not be able to manipulate a request to retrieve another technician's cost data.

Location and month may be supplied for drilldown, but those parameters must only narrow the already-authorised technician dataset.

---

# Acceptance criteria

The implementation is complete only when all of the following pass.

## Admin

Admin still returns:

```text
Location -> Month -> Job
```

with no regression.

## Technician initial request

Technician returns location objects:

```json
{
  "name": "...",
  "code": "...",
  "value": 0
}
```

not months.

## Technician location drilldown

Selecting a location returns:

```text
Jan -> Dec
```

for the authenticated technician's jobs at that location.

## Technician month drilldown

Selecting a month returns individual technician jobs using the same structure as Admin.

## Technician scope

Only records where:

```python
assign_to_sub == claims["sub"]
```

contribute to technician totals.

## Multi-location

A technician with jobs at multiple locations sees all those locations.

Their stored/home location does not restrict the result.

## Other technicians

Jobs assigned to another technician do not contribute, even when they occur at the same location.

## Response shape

Technician and Admin use the same response contract at each drilldown level.

## Null labels

No valid technician drilldown returns:

```json
{
  "name": null
}
```

---

# Constraints

- Follow `AGENTS.md`.
- Backend repository only.
- Do not modify frontend code.
- Do not create a new API endpoint unless absolutely necessary.
- Reuse the working Admin aggregation implementation.
- Do not duplicate cost-calculation logic.
- Do not change Manager/User access behaviour.
- Do not change unrelated dashboard metrics.
- Do not add dependencies.
- Do not refactor unrelated code.
- Do not expose unrestricted Admin data to technicians.
- Use Cognito claims as the source of truth.

---

# Final response

After implementing the fix, report:

1. Root cause of technician returning months at the top level.
2. Root cause of `"name": null`.
3. Files changed.
4. Where Admin and Technician now share aggregation logic.
5. How `claims["sub"]` is used to restrict technician jobs.
6. Confirmation that `userLocation` is no longer used for technician Maintenance Cost scope.
7. Confirmation that Manager/User behaviour was not changed.
8. Confirmation that the cost formula was not changed.
9. Example Admin response after the change.
10. Example Technician response after the change.
11. Validation performed and results.

Task 2:
Investigate why the database query was changed, the admin user receive no data and lambda logs indicate

```py
Skipping store 'middestad mall': An error occurred (ValidationException) when calling the Query operation: Invalid ProjectionExpression: Attribute name is a reserved keyword; reserved keyword: location
```

and data

```py
data: {}
```

Correct this issue for the admin user, od not change the logic to introduce new errors. Do not perform extensive tests, i will test the lambda in the console
