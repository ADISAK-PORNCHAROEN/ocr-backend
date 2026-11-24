# OCR Backend

A local FastAPI playground for extracting printed Thai and English text from JPG, PNG, and PDF files with the pinned OpenThai OCR Text v2.1.4 model on CPU. The backend accepts one document per job, processes pages asynchronously, and keeps results temporarily for review. It is intended for local development and frontend integration, not public or multi-user deployment.

## Swagger walkthrough

[Watch the Swagger UI demo](docs/assets/ocr-backend-swagger-demo.webm). The clip uses a synthetic, one-page Thai and English PDF with no personal data. It shows the live capabilities response, upload, job polling, OCR text and per-page inference timing, and job deletion. The `pdf_dpi` displayed in the recording comes from that local runtime; `.env.example` defaults to 150 DPI.

## Requirements and setup

- Python 3.13 (or let uv install its managed Python)
- [uv](https://docs.astral.sh/uv/)
- Internet access when the pinned model is first needed and is not already cached

From a fresh checkout on Windows:

~~~powershell
uv python install 3.13
Copy-Item .env.example .env.local
uv sync --group dev
~~~

`.env.local` is optional and ignored by Git. Start with `.env.example`; change only the local `OCR_*` values needed for your machine. `OCR_MODEL_CACHE_DIR` is optional; without it, Hugging Face uses its normal user cache.

## Run locally

~~~powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --workers 1
~~~

Keep one Uvicorn worker because job state belongs to one API process. The OCR worker starts when the first job is processed. If the pinned model is not cached, that first OCR job downloads it from Hugging Face and initializes the CPU runtime; subsequent jobs can use the cache. The local API listens on loopback:

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>
- Capabilities: <http://127.0.0.1:8000/api/v1/ocr/capabilities>

Read capabilities before accepting an upload: supported media types and limits come from the running backend configuration. The model is `iapp/OpenThai2.1-OCR-Text-20261118`, revision `v2.1.4`.

## API walkthrough

The backend accepts one multipart field named `file`. Use the `id` returned by the upload response in the following requests. Keep polling while the job is `queued` or `processing`; page results are ready when the job reaches a terminal status.

~~~powershell
$base = "http://127.0.0.1:8000"

# Check readiness and read the backend's current limits.
curl.exe "$base/health"
curl.exe "$base/api/v1/ocr/capabilities"

# Upload one JPG, PNG, or PDF; copy the returned id for the requests below.
curl.exe -X POST "$base/api/v1/ocr/jobs" -F "file=@.\document.pdf"

# Replace <job-id> with the id from the 202 Accepted response.
curl.exe "$base/api/v1/ocr/jobs/<job-id>"
curl.exe "$base/api/v1/ocr/jobs/<job-id>/pages"
curl.exe "$base/api/v1/ocr/jobs/<job-id>/pages/1"
curl.exe "$base/api/v1/ocr/jobs/<job-id>/pages/1/image" --output page-1.png
curl.exe -X DELETE "$base/api/v1/ocr/jobs/<job-id>"
~~~

`GET /pages` returns page results in document order. The per-page endpoint returns `original_text`, recognized `lines`, and `ocr_duration_ms`; use the image endpoint or each page's `image_url` to retrieve the rendered page. The browser frontend should call this API through its same-origin BFF, as described in the [frontend integration guide](docs/frontend-guide.md) and [API contract](docs/frontend-api.md).

`original_text` and `lines` are the unedited OCR output. Edited text and TXT/JSON downloads are frontend state; the backend does not store them or expose download endpoints.

## Job lifecycle and errors

Job statuses are `queued`, `processing`, `completed`, `partially_completed`, and `failed`. The last three are terminal. Page results have their own `pending`, `processing`, `completed`, or `failed` status.

Application errors use an `error` object with `code`, `message`, and `retryable` fields. Examples include `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`, `JOB_QUEUE_FULL`, `JOB_STORAGE_LIMIT_REACHED`, and `JOB_NOT_FOUND`; the [API contract](docs/frontend-api.md) lists HTTP codes and details. Job and image responses use `Cache-Control: no-store`.

`ocr_duration_ms` is the elapsed time inside the OpenThai inference call for one page. It excludes queue wait, PDF rendering, image encoding, worker transfer, and model download or initialization, so it is not end-to-end job time. The first OCR job may take longer while the worker starts.

Jobs and OCR state are temporary. Job metadata is held in memory; source files, rendered page images, and OCR results live in the app's temporary storage. Explicit deletion, expiry, shutdown, or startup cleanup removes the data. The default TTL is one hour; restarting the API discards job state, with no history or recovery.

## Runtime limits

`max_pages` is `null`, so there is no fixed page-count ceiling. This does not mean unlimited uploads or work: the `.env.example` defaults still cap file size at 20 MiB, pixels at 25 million per page and 80 million across a PDF, and each image dimension at 12,000 pixels. The waiting queue and retained-job count are bounded as well. Limits are configurable and exposed by the capabilities endpoint; many small pages can still increase memory use and processing time.

See [runtime limits and measured OCR timings](docs/runtime-limits.md) for the full defaults and their limits as local safeguards.

## Project structure

~~~text
app/
├── main.py                     # FastAPI app, lifespan, router setup
├── core/                       # Settings, errors, and middleware
├── entities/                   # Job and page state
├── repositories/               # Temporary job and artifact storage
├── services/                   # Queue, OCR lifecycle, progress, expiry, deletion
├── api/
│   ├── controllers/            # HTTP endpoints: health and OCR jobs
│   └── schemas/                # HTTP request and response models
├── documents/                  # File validation and page reading/rendering
└── ocr/                        # OpenThai runtime adapter and result mapping

tests/
├── integration/                # HTTP contract and job lifecycle
├── unit/                       # Domain, document, service, and adapter behavior
└── smoke/                      # Optional real-model CPU checks
scripts/                         # Local benchmark utility
docs/                            # Architecture, API, limits, and contributor guides
~~~

The main call direction is `controller → service → repository`. The jobs service also calls the document reader and OCR adapter; entities hold domain state without HTTP types. The repository stores temporary state and files; there is no persistent database. Each layer keeps OCR-related responsibilities in its own files, following the [accepted folder structure](docs/folder-structure.md). For repository exploration, see the optional [Graphify setup](docs/agents/graphify.md).

## Quality checks

Install development dependencies with `uv sync --group dev`, then run:

~~~powershell
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy
uv run pytest
~~~

The default test suite uses a fake OCR adapter and does not download the model. Real-model smoke checks are opt-in; see [testing](docs/TESTING.md).

## Contribution workflow

Use `develop` as the working branch. Make focused commits by coherent change, run the relevant local checks, then open a pull request from `develop` into `main`. Merge through the pull request; do not commit directly to `main`. This repository has no configured GitHub Actions workflow, so run the checks locally before requesting review.

## Further documentation

- [Frontend API contract](docs/frontend-api.md)
- [Frontend integration guide](docs/frontend-guide.md)
- [Architecture](docs/architecture.md)
- [Folder structure](docs/folder-structure.md)
- [Runtime limits and benchmark notes](docs/runtime-limits.md)
- [Testing](docs/TESTING.md)
- [Graphify setup](docs/agents/graphify.md)
