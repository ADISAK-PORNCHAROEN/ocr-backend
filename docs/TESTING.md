# OCR Playground testing

## Native checks

Install the project and development tools with `uv sync --group dev`. The default suite uses synthetic files and a fake OCR adapter; it does not download the model.

```powershell
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy
uv run pytest
```

This repository intentionally has no GitHub Actions workflow. Run these commands locally before opening a pull request. Keep the optional model smoke separate from the default suite so a normal test run does not depend on model downloads or Hub availability. The checks on backend PR #13 passed before the user requested workflow removal.

## Behavior covered

| Boundary | Tests and observable behavior |
| --- | --- |
| Domain | Initial page states, derived job progress, blank success, all-failed status, invalid transitions, positive page numbers |
| File validation | Content signature and extension agreement, malformed image, encrypted PDF, upload-byte cap, page count, page dimensions and pixel budget, PDF total pixel budget, sanitized display filename |
| HTTP contract | Multipart upload, 202/Location, status polling, page list and OCR result, PNG page image, no-store headers, stable error envelope, capabilities and configured limits |
| Multi-page results | PDF page count, completed blank page, failed page, partial job state, page images for available outputs |
| Queue and lifecycle | Bounded queue and retained-job cap, delete while a worker is active, discard late results, expiry, inaccessible expired jobs and temporary-file cleanup |
| Model and renderer | Optional real OpenThai OCR on a synthetic Thai image and real two-page PDF rendering on CPU |

Unit tests exercise local domain and document rules. HTTP integration tests use synthetic inputs and an injected fake processor to control page results, failures and worker timing. These tests do not claim OCR accuracy or performance.

## Real model smoke

The model smoke uses the pinned `iapp/OpenThai2.1-OCR-Text-20261118` revision `v2.1.4`. The first run downloads its runtime and ONNX files from Hugging Face. On Windows, the Thai image fixture uses Tahoma by default; set `OCR_SMOKE_FONT` if another Thai-capable font should be used.

```powershell
$env:OCR_RUN_MODEL_SMOKE = "1"
uv run pytest tests/smoke/test_openthai_cpu.py -vv
Remove-Item Env:OCR_RUN_MODEL_SMOKE
```

The smoke verifies Thai text, line boxes within the displayed image, confidence range, and rendering every page of a synthetic two-page PDF. It does not compare a corpus score or establish speed. The most recent local run on 2026-11-23 passed both smoke tests on CPU.

## Live BFF integration

On 2026-11-23, a browser flow used the frontend BFF against the real backend on loopback with isolated temporary storage and synthetic inputs:

- A Thai PNG upload returned a completed OCR result with `สวัสดีครับ OCR 123`. The TXT download preserved the text. Deletion returned `204`, and a later job lookup returned `404`.
- A two-page PDF returned page 1 text `สวัสดีครับ OCR 123` and page 2 text `PAGE TWO 456`. Both page-image endpoints returned `200 image/png`. TXT contained both pages; JSON kept edited text separate from original OCR lines and coordinates. Deletion returned `204`, followed by `404` on lookup.

This verifies the frontend-to-backend contract and temporary job lifecycle for these synthetic examples. It does not establish accuracy on real documents, OCR throughput or performance under concurrent use. Frontend implementation remains outside the current backend phase.

## Fixtures and cleanup

Tests generate synthetic images and PDFs in pytest-owned temporary directories. No user documents or OCR results are committed. The API fixture uses an isolated temporary storage root and checks cleanup on delete, expiry and shutdown. Do not change it to point at a user documents directory.

## Runtime limits and measurements

The inspected local machine has Windows, Python 3.13, 8 logical processors and 31.8 GB RAM. The chosen defaults are 20 MiB per upload, 20 pages, PDF rendering at 150 DPI, 25 million pixels per page, 80 million total PDF pixels, 12,000 pixels per dimension, two waiting jobs plus one active job, five retained jobs, one OCR process with one inference thread, and a one-hour TTL. Unit tests exercise the byte, page, dimension and pixel boundaries; smoke tests verify the configured PDF raster path.

These are conservative local-demo safeguards, not benchmark-derived throughput guarantees. No latency, throughput, OCR quality or peak-memory claims are made. If optimizing, measure cold start separately from warm per-page inference, record CPU/RAM and runtime/model revisions, and verify output quality alongside speed.
