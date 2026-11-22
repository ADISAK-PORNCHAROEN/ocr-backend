# OCR issue run plan

## Scope and completion check

The issue set captured at kickoff is `#1` through `#10` in `ADISAK-PORNCHAROEN/ocr-backend`. Issue #1 is the parent product specification. Issues #2 through #10 contain implementation work.

The task is complete when each implementation issue meets its acceptance criteria with recorded evidence, the parent specification is satisfied, the backend and frontend checks pass, both pull requests from `develop` to `main` are merged, and the related backend issues are closed with links to the delivered changes.

The backend and frontend are separate repositories under the accepted project design. Backend issues #7 through #9 require code in `ADISAK-PORNCHAROEN/ocr-frontend`.

## Implementation order

1. **Backend structure, issue #10.** Add the FastAPI and uv application, accepted layer boundaries, native checks, and a health route. Verify install, type checking, tests, and startup.
2. **Single-image OCR, issue #2.** Pin OpenThai OCR Text v2.1.4, verify its output on CPU, and return original text, line boxes, confidence, and the matching page image. Verify the HTTP behavior with a fake adapter and a real-model smoke run.
3. **Job progress, issue #3.** Add a bounded queue, asynchronous processing, derived progress, and polling. Verify queued, processing, terminal, blank-page, and failure states through HTTP.
4. **PDF and partial results, issue #4.** Render every page at a bounded resolution and preserve completed pages when another page fails. Verify a multi-page PDF through HTTP.
5. **Upload checks, issue #5.** Reject unsupported, corrupt, encrypted, oversized, and over-page-limit files. Measure representative image and PDF processing on the target machine before finalizing defaults.
6. **Deletion and expiry, issue #6.** Remove jobs from readable state immediately, defer file cleanup while a worker uses a file, expire old jobs, and clear stale job directories at startup. Verify deletion during inference and restart cleanup.
7. **Frontend review and editing, issue #7.** Implement the selected Paperflow design in the separate frontend project. Verify blank, failed, edited, restored, copied, keyboard, and mobile states against a controlled backend.
8. **Frontend downloads, issue #8.** Build TXT and JSON from every successful page, keep edited text separate from OCR output, and stop when any successful page cannot be fetched. Verify complete and partial results.
9. **Integrated flow, issue #9.** Connect upload, polling, review, download, and restart to the real backend. Verify the complete browser flow and cleanup.
10. **Close the parent, issue #1.** Reconcile implemented behavior and remaining limitations with the product specification. Close the parent only after its child work is merged.

## Architecture decisions

Keep one FastAPI process as the only writer of job state and artifacts. Use an in-memory job repository, a bounded asyncio queue, one coordinator, and one OCR process worker. The worker handles one page at a time and returns data to the API process. The API process stores page results and ignores late results after deletion or expiry.

Represent page states as pending, processing, completed, or failed. A completed page with no text remains a success. Derive job progress from page states. Keep HTTP schemas out of entities and OCR policy out of repositories.

Keep the frontend's edits in memory and separate from original OCR data. The frontend calls the backend through its Next.js BFF and downloads only after it has fetched every successful page.

## Baseline and gates

At kickoff, `develop` was clean at `3374e72`. The backend had no application code, dependency manifest, test runner, or CI baseline. The frontend repository had design documents and an open design pull request, but no application source or test runner.

Run focused checks after each implementation unit. Run the full backend and frontend suites once after the final changes. Run a separate real-model CPU smoke test and a browser end-to-end flow. Review both diffs against the issue criteria and project security models before merging.

Make focused commits on `develop`. Merge through pull requests. Do not push commits directly to `main`.
