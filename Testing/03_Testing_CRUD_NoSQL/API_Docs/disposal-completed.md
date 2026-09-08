# Complete a disposal

`POST /api/disposals/{id}/completed` requires authenticated Cognito claims with
`sub`. The path ID is queried against `disposalId`; the returned `disposalCreated`
is used with it for the update. The existing Terraform route is unchanged.

```json
{
  "disposalMethod": "Scrapped",
  "disposalCost": 500,
  "disposalNotes": "Testing disposal",
  "disposalImages": [{"filename": "photo.jpg", "content_type": "image/jpeg"}],
  "disposalDocuments": [{"filename": "receipt.pdf", "content_type": "application/pdf"}]
}
```

`disposalMethod` must be a non-empty string. `disposalCost` must be a finite,
non-negative JSON number (zero is accepted). Notes default to an empty string;
upload arrays default to `[]`. Supplied file descriptors require a non-empty
filename without path separators and a non-empty content type. Use `[]` when
there are no files; empty placeholder descriptors are invalid.

An approved disposal transitions conditionally from `approved` to `disposed`.
The handler records the submitted fields, backend timestamp, and Cognito-derived
`disposedBy`/`disposedBySub` in `disposed`, and updates `dateUpdated`.
It returns HTTP 200 with `message`, the updated record in `data`, and
the flat array `presigned_urls` (empty when no files are supplied). Each entry
contains `type`, `filename`, `content_type`, `key`, and `url`. Images have
`type: "images"`; disposal documents have `type: "invoices"` so the shared
frontend hook selects them from `rawInvoices`.

PUT each file to its URL with the returned `content_type` as `Content-Type` within
one hour. Keys follow `disposals/{id}/disposal/images/{filename}` and
`disposals/{id}/disposal/documents/{filename}`. The existing S3 consumer appends
uploaded metadata to `disposed.disposalImages` / `disposed.disposalDocuments`;
these lists start empty. Completion commits before the frontend uploads files.

Responses: 400 invalid payload/path, 401 missing identity, 404 missing disposal,
409 disposal not approved or changed concurrently, 500 AWS/internal failure.
OPTIONS and all responses use shared CORS helpers. This endpoint updates the
disposal record; it does not directly update registered asset records.
