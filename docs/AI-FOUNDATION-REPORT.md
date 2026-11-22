# AI foundation report

Updated: 2026-11-23. The foundation setup was documentation and project-local skills; the current `develop` branch also contains the OCR backend implementation. The implementation and its evidence are tracked separately from the foundation package inventory below.

## Delivery and evidence

The per-document delivery list is [document-delivery.md](agents/document-delivery.md). The shared instructions preserve the original pstack rules, require focused commits and require a PR for each merge into `main`. The original instruction bytes and SHA-256 receipt are in `docs/history/agent-instructions/`; the staged Git blob was checked against the archive.

The five standard project skill packages contain 82 files: test-engineering 2, security-review 2, graphify 12, hook-management 2 and impeccable 64. Source and installed inventories, fingerprints, adaptations and individual paths are in [foundation.json](agents/foundation.json) and [skills-checklist.md](agents/skills-checklist.md). Package completeness is separate from runtime discovery: a fresh supported host session has not verified discovery or dispatch of the five project-local copies.

The user separately requested the Graphify CLI and Git `post-commit` update hook. `graphifyy==0.9.80` was installed into `.graphify-venv/`, and `graphify update` and the hook were observed during commits. This local hook is not transferred by Git. Its setup, scope and code-only update limitation are recorded in [graphify.md](agents/graphify.md). The separate Impeccable engine and host lifecycle hooks were not installed.

## Representative journey

Requirement: a user submits a printed Thai/English document, monitors page progress and can edit and download the result ([product](../PRODUCT.md), [spec](spec.md)). The backend implements the documented API and OCR adapter. Backend PR #13 is merged and its checks passed; issues #2–#6 and #10 are closed with evidence. Local evidence includes backend HTTP integration tests, CPU model smoke tests for a synthetic Thai image and two-page PDF, and a browser flow through the real loopback backend. Current commands and results are in [testing](TESTING.md). Frontend-dependent issues #7–#9 and parent issue #1 remain open; the API usage contract is available in [frontend-api.md](frontend-api.md).

## Verification and gaps

- Exact archived instruction hash checked, and `CLAUDE.md` is a one-line import. Host loading was not observed.
- Skill inventories and local links were checked separately from semantic review; see the checklist for counts and exact differences.
- Graphify CLI and the named local post-commit event ran; the graph does not prove OCR functionality or semantic document coverage.
- `graphify hook status` does not recognize the custom post-commit hook because it lacks the upstream installer marker. Git commit output independently confirmed the event ran. The upstream installer also changes other hook events, which were not requested.
- `git diff --check main` reports inherited CRLF and whitespace in copied skill resources and the byte-preserved instruction archive. These files retain the captured source bytes; no whitespace-clean result is claimed.
- Backend native checks pass locally: Ruff lint/format, mypy, pytest (37 passed, 3 skipped), and opt-in CPU model smoke (2 passed). Backend PR #13 and its GitHub checks passed before the workflow was removed at the user's request. Frontend checks were previously run locally, but frontend implementation is deferred in the current phase.
- Manual security reviews covered upload, temporary storage, job lifecycle, model loading, frontend proxy, rendering and export. No confirmed vulnerability was found; no automated security scanner, fuzzing or native dependency audit ran.
- OCR quality on a real-document corpus, performance benchmark, inference timeout, authentication and public deployment remain unverified or out of scope. Local limits are documented with reasons and tested boundaries, not claimed throughput guarantees.
- PR and focused-commit rules are instructions, not a configured branch-protection policy.
- Setup remains partial until a fresh host verifies discovery and dispatch of all five project-local skills.

## Independent review

A fresh independent agent reviewed the root instructions, product, domain, design, architecture, testing and security documents, plus all five skill entrypoints and their contracts. It found no substantive content contradictions, verified all 116 local Markdown links, compared the 82 installed file hashes against the recorded inventory and checked the original instruction archive. It identified unfinished manifest receipts, report/delivery paths and routing status; these were completed after review. Its review did not independently re-fetch upstream packages or exercise fresh-host skill dispatch.

A separate bounded manual security review covered the skill package changes against `main`, the local Git hook and Graphify configuration. It found no confirmed security issue in that scope. The review did not execute Impeccable or verify its absent engine: its launcher can download and execute that engine, and engine-side authorization and origin checks remain unreviewed. Root instructions require explicit authorization before downloading it. The review did not include an automated scan, dependency advisory sweep or a full audit of bundled browser code.
