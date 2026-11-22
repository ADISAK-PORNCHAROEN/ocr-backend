# Local runtime limits

These defaults make the first local version predictable on the inspected development machine: Windows, Python 3.13, 8 logical processors and 31.8 GB RAM. They are configurable through `OCR_*` environment variables and returned by `GET /api/v1/ocr/capabilities`.

| Limit | Default | Reason |
| --- | ---: | --- |
| Upload size | 20 MiB | Bounds temporary disk use and request staging |
| Pages per document | 20 | Bounds a single job and gives progress a useful scale |
| PDF render resolution | 150 DPI | A4 is about 2.1 megapixels at this setting |
| Pixels per page | 25 million | Bounds decode/render memory for unusually large pages |
| Pixels across document | 80 million | Bounds cumulative work, including a 20-page A4 PDF at 150 DPI |
| Maximum image dimension | 12,000 px | Rejects extremely wide or tall inputs before inference |
| Waiting jobs | 2, plus one active job | Keeps the single model worker's backlog bounded |
| Retained jobs | 5 | Bounds completed and active documents kept for review until deletion or expiry |
| API processes / OCR workers / model threads | 1 / 1 / 1 | Avoids duplicate in-memory state and unpredictable CPU oversubscription |
| Job retention | 1 hour | Cleans abandoned local documents while leaving time to review results |

The model card reports roughly 450 MB of model memory per worker. The service starts only one worker and reads pages sequentially. This is a conservative local configuration, not a throughput benchmark or a production capacity claim. Revisit values after testing representative scanned PDFs, large images, and concurrent uploads on the target machine.

Uploads are copied from the framework's spooled multipart file to an app-owned UUID directory with a byte cap. File type is identified from the file contents and decoded before queuing. The API deletes the directory on explicit deletion, expiry, shutdown, or a later startup cleanup. The retained-job cap includes active jobs and jobs awaiting deletion/expiry. OCR job state is memory-only, so restarting the API discards prior jobs.

## Local boundary experiment

On 2026-11-23, the configured byte, page-count and PDF pixel limits were exercised on the target machine using synthetic inputs. The machine was Windows 11, Python 3.13.0, an Intel Core i5-10300H with 8 logical CPUs and 31.8 GiB RAM.

| Experiment | Result |
| --- | --- |
| Stage a valid PNG padded to exactly 20 MiB | Accepted at the configured byte limit; staging took 0.018 s |
| Validate a synthetic blank 20-page A4 PDF (595.28 × 841.89 points) | Accepted; validation took 0.041 s |
| Render all 20 pages at 150 DPI | 1,241 × 1,754 px per page; 43,534,280 total pixels; 0.237 s for all pages, below the 80 million pixel cap |
| Validate an otherwise identical 21-page A4 PDF | Rejected with `PAGE_LIMIT_EXCEEDED` |

This confirms the selected byte and page-count boundaries and the 20-page PDF raster size on this machine. The image and PDF were synthetic and blank; the timings describe file validation and PDF rendering only. They do not measure OCR inference, peak memory, concurrent uploads, real scanned documents, throughput or OCR quality. The separate CPU model smoke verifies a synthetic Thai image and two-page PDF. Re-measure before changing defaults or using the service beyond the local demo.
