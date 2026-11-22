# API contract for the frontend

Status: implemented by the backend. The frontend is a separate repository and should consume this contract through its Next.js BFF. JSON field names are snake_case. Timestamps use ISO 8601 with a timezone. Page numbering starts at 1. Job state and uploaded data are memory-only and temporary.

Base path: `/api/v1`

## Capabilities

`GET /api/v1/ocr/capabilities` returns the configured upload limits, supported media types, model revision and worker settings. Read it before accepting a file instead of hard-coding backend limits.

```json
{
  "supported_media_types": ["image/jpeg", "image/png", "application/pdf"],
  "max_upload_bytes": 20971520,
  "max_pages": 20,
  "pdf_dpi": 150,
  "max_page_pixels": 25000000,
  "max_total_pixels": 80000000,
  "max_pending_jobs": 2,
  "max_retained_jobs": 5,
  "worker_count": 1,
  "job_ttl_seconds": 3600,
  "model_id": "iapp/OpenThai2.1-OCR-Text-20261118",
  "model_revision": "v2.1.4"
}
```

`max_pending_jobs` is the waiting queue size. One additional job can be active. `max_retained_jobs` caps all jobs that still have temporary data, including completed jobs awaiting review. The API is intended to run as one process.

## Create a job

`POST /api/v1/ocr/jobs` accepts `multipart/form-data` with one field named `file`, containing one JPG, PNG or PDF. The backend identifies type from file bytes and decodes the document before adding it to the bounded queue. The client content type and filename extension do not establish file type.

Response: `202 Accepted`. The response also includes a `Location` header for the status resource and `Cache-Control: no-store`.

```json
{
  "id": "7a0d4c31-3281-4c37-895e-23a33be75946",
  "filename": "document.pdf",
  "media_type": "application/pdf",
  "status": "queued",
  "progress": {
    "total_pages": 2,
    "completed_pages": 0,
    "failed_pages": 0,
    "processing_pages": 0,
    "processed_pages": 0
  },
  "created_at": "2026-11-23T10:00:00Z",
  "expires_at": "2026-11-23T11:00:00Z"
}
```

The file is staged in an app-owned temporary directory. An accepted job may begin before the client receives the response.

## Capabilities and job status

`GET /api/v1/ocr/jobs/{job_id}` returns the same job shape as create. Poll while the status is `queued` or `processing`, then stop at a terminal status. `processed_pages` is completed plus failed pages; `processing_pages` is either zero or one with the current single worker.

| Status | Meaning |
| --- | --- |
| `queued` | Accepted and waiting, or no page has started yet |
| `processing` | A page is being rendered or recognized |
| `completed` | Every page completed, including pages with no detected text |
| `partially_completed` | All pages finished and at least one succeeded and one failed |
| `failed` | All pages failed |

The last three states are terminal. Progress and job status are derived from page states.

## List pages and read OCR output

`GET /api/v1/ocr/jobs/{job_id}/pages` returns all page results in document order. While work is in progress, some pages may still be `pending` or `processing`.

`GET /api/v1/ocr/jobs/{job_id}/pages/{page_number}` returns the same shape for one page:

```json
{
  "page_number": 1,
  "status": "completed",
  "has_text": true,
  "original_text": "หนังสือรับรอง",
  "lines": [
    {
      "text": "หนังสือรับรอง",
      "confidence": 0.98,
      "box": { "x1": 120.0, "y1": 180.0, "x2": 430.0, "y2": 222.0 }
    }
  ],
  "image_size": { "width": 1200, "height": 1800 },
  "error": null,
  "image_url": "/api/v1/ocr/jobs/7a0d4c31-3281-4c37-895e-23a33be75946/pages/1/image"
}
```

`original_text` and `lines` are the unedited output from OpenThai. A completed page with no text has `has_text: false`, `original_text: ""` and `lines: []`. Pending and processing pages have `has_text: null` and no result. Failed pages have `has_text: null`, no result, and an `error` object. An OCR failure may still have a rendered image available.

OpenThai returns a four-corner polygon for each line. The backend converts it to an axis-aligned rectangle by taking the minimum and maximum x/y coordinates. `box` coordinates are pixels from the top-left of the rendered image. `confidence` is in the 0–1 range. The rendered image is PNG, oriented for display and composited onto white when the uploaded image is transparent. For PDFs, each page is rendered at the `pdf_dpi` reported by capabilities. These rules were verified with the pinned model on a synthetic Thai image and PDF pages.

The image endpoint is `GET /api/v1/ocr/jobs/{job_id}/pages/{page_number}/image`. It returns `image/png` and `Cache-Control: no-store`. It returns `409 PAGE_IMAGE_NOT_READY` until rendering finishes, and `404 JOB_NOT_FOUND` if the job is deleted, expired, or the page number is invalid.

## Delete and retention

`DELETE /api/v1/ocr/jobs/{job_id}` removes the source document, rendered page images and OCR result from accessible job state, then returns `204 No Content`. A second delete returns `404 JOB_NOT_FOUND`.

The frontend should delete when the user starts over or finishes. The backend also expires jobs after the configured TTL. Deletion makes a job inaccessible immediately; if an OCR worker is still reading its file, physical cleanup waits until that worker returns. Late worker results are discarded. On API startup, leftover UUID job directories owned by this application are removed. API restart clears job state; there is no history or recovery.

## Frontend edits and downloads

Edited text is frontend-only state. Keep it separate from `original_text`, and restore only the current page from the original result after confirmation. Build TXT and JSON downloads in the frontend from all successful pages after fetching them. If any successful page cannot be fetched, stop the download and show the incomplete result. Include failed page details in partial-result downloads. The backend does not store edited text or expose download endpoints.

## Errors

Application errors use one shape:

```json
{
  "error": {
    "code": "JOB_QUEUE_FULL",
    "message": "ระบบกำลังประมวลผลงานเต็ม โปรดลองอีกครั้งภายหลัง",
    "retryable": true
  }
}
```

| HTTP | Code | Meaning |
| ---: | --- | --- |
| 409 | `PAGE_IMAGE_NOT_READY` | The page image has not been rendered yet |
| 409 | `JOB_STORAGE_LIMIT_REACHED` | The temporary job limit is reached; delete an old job before uploading |
| 413 | `FILE_TOO_LARGE` | Uploaded file exceeds the byte limit |
| 415 | `UNSUPPORTED_FILE_TYPE` | File contents are not JPG, PNG or PDF |
| 415 | `FILE_EXTENSION_MISMATCH` | Filename extension does not match the detected file contents |
| 422 | `EMPTY_FILE` | File is empty |
| 422 | `CORRUPT_IMAGE` / `CORRUPT_PDF` | The document cannot be decoded |
| 422 | `PDF_PASSWORD_PROTECTED` | Encrypted PDF files are not accepted |
| 422 | `PAGE_LIMIT_EXCEEDED` | Document has too many pages |
| 422 | `PAGE_DIMENSION_LIMIT_EXCEEDED` | A page dimension exceeds the limit |
| 422 | `PAGE_PIXEL_LIMIT_EXCEEDED` / `PDF_PIXEL_LIMIT_EXCEEDED` / `DOCUMENT_PIXEL_LIMIT_EXCEEDED` | Rendered pixel budget is exceeded |
| 422 | `INVALID_REQUEST` | Request parameters or multipart form are invalid |
| 404 | `JOB_NOT_FOUND` | Job is missing, deleted, expired, or page number is invalid |
| 503 | `JOB_QUEUE_FULL` | Waiting queue is full; response includes `Retry-After` |
| 500 | `INTERNAL_ERROR` | Unexpected server failure |

Every job and image response uses `Cache-Control: no-store`. This backend does not configure CORS; the frontend should call through its own same-origin BFF. The local demo has no authentication and is not approved for public deployment.
