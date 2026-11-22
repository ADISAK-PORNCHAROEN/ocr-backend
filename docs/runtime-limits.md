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
