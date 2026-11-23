# OCR Backend

A local FastAPI playground for extracting printed Thai and English text from one JPG, PNG or PDF file. OCR runs on CPU through the pinned OpenThai OCR Text v2.1.4 runtime. Jobs and uploads are temporary, in-memory jobs are lost on restart, and the app removes its own temporary files during shutdown or expiry.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Internet access on the first OCR request to download the pinned model files from Hugging Face

## Run locally

```powershell
uv sync --group dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --workers 1
```

Use one Uvicorn worker because job state is held in memory by one API process. The OCR process starts when the first job is processed. Swagger UI is available at `/docs`; check `/health` and `/api/v1/ocr/capabilities` before connecting a frontend.

Copy `.env.example` to `.env.local` to change local settings. Do not commit `.env.local`, model weights, uploads, or OCR results. `OCR_MODEL_CACHE_DIR` is optional; without it, Hugging Face's normal user cache is used.

## API flow

1. Read supported file types and limits from `GET /api/v1/ocr/capabilities`.
2. Upload one multipart field named `file` to `POST /api/v1/ocr/jobs`.
3. Poll `GET /api/v1/ocr/jobs/{job_id}` until the job is completed, partially completed, or failed.
4. Read all pages from `GET /api/v1/ocr/jobs/{job_id}/pages`; fetch each rendered page image from its `image_url`.
5. Delete the temporary job with `DELETE /api/v1/ocr/jobs/{job_id}` when finished.

Page text is the original OCR result. Edited text and TXT/JSON export are frontend state and are not written by this API. Errors use an `{ "error": { "code", "message", "retryable" } }` envelope. Job/page data is served with `Cache-Control: no-store`.

## Checks

```powershell
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy
uv run pytest
```

The default test suite uses a fake OCR adapter. Real-model smoke tests are opt-in and download the model on first use; see `docs/TESTING.md`.

This repository has no configured GitHub Actions workflow. Run the checks locally before opening a pull request.

## Runtime limits

Current local defaults are documented in `docs/runtime-limits.md`. Upload and pixel limits, the absence of a fixed page-count cap (`max_pages: null`), and the retained-job cap are exposed by the capabilities endpoint. Page responses include `ocr_duration_ms` for model inference only.
