# Local runtime limits

These defaults make the first local version predictable on the inspected development machine: Windows, Python 3.13, 8 logical processors and 31.8 GB RAM. They are configurable through `OCR_*` environment variables and returned by `GET /api/v1/ocr/capabilities`.

| Limit | Default | Reason |
| --- | ---: | --- |
| Upload size | 20 MiB | Bounds temporary disk use and request staging |
| Pages per document | No fixed page-count ceiling (`max_pages: null`) | Upload bytes and per-page/cumulative pixel limits remain; they bound raster work but do not fully bound page metadata or per-page OCR overhead |
| PDF render resolution | 150 DPI | A4 is about 2.1 megapixels at this setting |
| Pixels per page | 25 million | Bounds decode/render memory for unusually large pages |
| Pixels across document | 80 million | Bounds cumulative work across all PDF pages |
| Maximum image dimension | 12,000 px | Rejects extremely wide or tall inputs before inference |
| Waiting jobs | 2, plus one active job | Keeps the single model worker's backlog bounded |
| Retained jobs | 5 | Bounds completed and active documents kept for review until deletion or expiry |
| API processes / OCR workers / model threads | 1 / 1 / 1 | Avoids duplicate in-memory state and unpredictable CPU oversubscription |
| Job retention | 1 hour | Cleans abandoned local documents while leaving time to review results |

The model card reports roughly 450 MB of model memory per worker. The service starts only one worker and reads pages sequentially. With no page-count ceiling, a PDF containing many very small pages can still consume CPU time and in-memory page state while remaining under the pixel budget. Keep this service on loopback; do not treat these limits as protection for a public or multi-user deployment. This is a conservative local configuration, not a throughput benchmark or a production capacity claim. Revisit values after testing representative scanned PDFs, large images, and concurrent uploads on the target machine.

Uploads are copied from the framework's spooled multipart file to an app-owned UUID directory with a byte cap. File type is identified from the file contents and decoded before queuing. The API deletes the directory on explicit deletion, expiry, shutdown, or a later startup cleanup. The retained-job cap includes active jobs and jobs awaiting deletion/expiry. OCR job state is memory-only, so restarting the API discards prior jobs.

## Historical page-cap experiment

Before removal of the fixed page cap, the byte, page-count and PDF pixel limits were exercised on 2026-11-23 using synthetic inputs. The machine was Windows 11, Python 3.13.0, an Intel Core i5-10300H with 8 logical CPUs and 31.8 GiB RAM.

| Experiment | Result |
| --- | --- |
| Stage a valid PNG padded to exactly 20 MiB | Accepted at the configured byte limit; staging took 0.018 s |
| Validate a synthetic blank 20-page A4 PDF (595.28 × 841.89 points) | Accepted; validation took 0.041 s |
| Render all 20 pages at 150 DPI | 1,241 × 1,754 px per page; 43,534,280 total pixels; 0.237 s for all pages, below the 80 million pixel cap |
| Validate an otherwise identical 21-page A4 PDF | Rejected with the former `PAGE_LIMIT_EXCEEDED` rule; this behavior has since been removed |

The historical timings describe validation and PDF rendering only; they do not measure OCR inference, peak memory, concurrent uploads, real scanned documents, throughput or OCR quality. The current implementation accepts PDFs above 20 pages when the active byte, dimensions and total-pixel safeguards pass. See the current benchmark below for inference timing evidence.

## CPU OCR timing benchmark

`ocr_duration_ms` measures only the elapsed time inside the pinned model's `read(image)` inference call. It excludes upload, queue wait, PDF rendering, image encoding, process-pool transfer and worker/model initialization. The first request's wall time is therefore not directly comparable with this per-page metric.

Measured on 2026-11-23 on Windows 11, Python 3.13.0, Intel Core i5-10300H, 8 logical processors and 31.8 GiB RAM. The input was a synthetic 10-page PDF, each page containing the same 1800 × 320 px Tahoma-rendered Thai greeting and `OCR 123` at 150 DPI. One page was used for warm-up; pages 2–10 supplied nine inference samples. All 10 pages returned text containing `สวัสดี`.

| Measurement | Result |
| --- | ---: |
| Model | `iapp/OpenThai2.1-OCR-Text-20261118`, revision `v2.1.4` |
| First-page wall time | 1,720.05 ms, including worker/model initialization, PDF rendering and process-pool transfer |
| Warm per-page inference | Median 104.92 ms; range 100.85–137.74 ms across 9 pages |
| CPU load before run | 17.8–22.4% over three one-second samples; this was not an isolated machine |

Reproduce with `uv run python scripts/benchmark_ocr.py --warmup-pages 1 --sample-pages 9`. The script fails if any page does not return the expected Thai text. The benchmark is a small synthetic input on one Windows laptop; it does not establish document accuracy, end-to-end latency for real scans, sustained throughput, peak memory or performance on another machine. The reported per-page values are the model inference call only.
