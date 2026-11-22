# Project skills checklist

The Foundation standard bundle contains **5 standard skills**. The installer and host/global skills are excluded from these totals.

- Standard project skills: **5**
- Selected project skills: **5**
- Complete package installations: **5/5**
- Incomplete or missing installations: **0/5**
- Runtime discovery verified: **0/5**

All 82 source files were copied before two documented contract adaptations. Package integrity, metadata/resource presence and root-guide routing are verified. Runtime discovery and fresh-session dispatch are **not verified**; disk presence is not evidence of host loading. Destination-specific testing/security mappings were added from the existing OCR specification, architecture and draft API.

| Complete | Skill | Authoritative source revision | Project path | Source → installed entries | Source → installed SHA-256 | Missing / changed / added | Manifest / route | Runtime discovery |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `test-engineering` | Captured Foundation package snapshot `sha256:48ab7a5135418971cc6e79b2bdc61e35008cde8c4fe7d1b99d7f5a57c0dd4bb5` | `.agents/skills/test-engineering` | 2 → 2 | `48ab7a5135418971cc6e79b2bdc61e35008cde8c4fe7d1b99d7f5a57c0dd4bb5` → `d9b4d01286139d27007f6beadca0ab7c534e9bdda65c4aeb6fec74e8ead2bb89` | none / `references/testing-contract.md` / none | manifest and root route aligned | not verified |
| [x] | `security-review` | Captured Foundation package snapshot `sha256:fd361917704ead6725794dea94fc08def2916ca5c8a561a9517192f7a4821d8a` | `.agents/skills/security-review` | 2 → 2 | `fd361917704ead6725794dea94fc08def2916ca5c8a561a9517192f7a4821d8a` → `7a11cdb03a8bb35777eb32e9730b7a752de7ba808acfbd19ab37e8d17ae6036f` | none / `references/review-contract.md` / none | manifest and root route aligned | not verified |
| [x] | `graphify` | Captured Foundation package snapshot `sha256:aab00021382bf9fa662577f3db7605d38269edc8aa9f690d80a47176cd34ccd7` | `.agents/skills/graphify` | 12 → 12 | `aab00021382bf9fa662577f3db7605d38269edc8aa9f690d80a47176cd34ccd7` → `aab00021382bf9fa662577f3db7605d38269edc8aa9f690d80a47176cd34ccd7` | none / none / none | manifest and root route aligned | not verified |
| [x] | `hook-management` | Captured Foundation package snapshot `sha256:01e66efa463c5fff70ccf3b1eee3cfc741b693de6de574d9c2dc2f91a18fd10b` | `.agents/skills/hook-management` | 2 → 2 | `01e66efa463c5fff70ccf3b1eee3cfc741b693de6de574d9c2dc2f91a18fd10b` → `01e66efa463c5fff70ccf3b1eee3cfc741b693de6de574d9c2dc2f91a18fd10b` | none / none / none | manifest and root route aligned | not verified |
| [x] | `impeccable` | Captured Foundation package snapshot `sha256:dc55eb3bcfc827aaa51f06bdda6bd88e21f6a75eaee261039095e98057c39cd0` | `.agents/skills/impeccable` | 64 → 64 | `dc55eb3bcfc827aaa51f06bdda6bd88e21f6a75eaee261039095e98057c39cd0` → `dc55eb3bcfc827aaa51f06bdda6bd88e21f6a75eaee261039095e98057c39cd0` | none / none / none | manifest and root route aligned | not verified |

## Provenance and preservation

Each source was inventoried before copying from the bundled `ai-project-foundation/assets/project-skills/<name>` folder. The immutable revision for this installation is the captured package fingerprint; per-file path/hash records are retained in [foundation.json](foundation.json). This receipt records the bytes present in the source snapshot, including its line endings. It does not claim the canonical upstream LF-byte fingerprints from a Git checkout.

Graphify retains all 12 files (entrypoint, eight references and three license/notice files), based on upstream v0.9.80 commit `6478eb71237c86ee5fb6a35c702835e987ca445d` with the Foundation adaptations already present in the bundled source. Impeccable retains all 64 files from its v4.7.0 package, based on upstream commit `aeeb3d8c30b5f95aeeb3e893b0f1a308af8fdb8f`, including `LICENSE`, `NOTICE.md`, route metadata and all five upstream JavaScript support files. Destination adaptations are exactly `test-engineering/references/testing-contract.md` and `security-review/references/review-contract.md`: appended OCR-specific boundaries, evidence owners, exclusions, missing native commands and recovery/completion criteria. Every source file and all source URLs are retained; no files were added inside a package.

The exact destination skill directory did not exist before copying; no sibling, host/global skill or setting was modified. The user separately requested the project-local Graphify CLI and Git post-commit hook; their installation and observed execution are recorded in [graphify.md](graphify.md). The Impeccable engine was not installed or launched. Hook management remains explicit-only.

## Review evidence

- Checked: 2026-11-22. Scope: the five project-local skill packages and this manifest/checklist; no application implementation is present in the assigned setup scope.
- Inventory: recursive paths including hidden files, symlink handling and SHA-256 of every file; records use normalized `/` paths, ordinal sorting, UTF-8, LF and a final newline. All source paths are retained; three packages match byte-for-byte and two differ only at the approved contract paths listed above.
- Metadata: all five entrypoint names/descriptions and required bundled resources exist; Impeccable `agents/openai.yaml` preserves its interface metadata and declares no invocation restrictions or dependencies.
- Direct local resource links: all 116 Markdown links in the installed packages resolved with no missing target after adaptations and creation of canonical project documents. This checks file targets; it does not establish fresh-session host discovery or dispatch.
- Runtime discovery next action: start a fresh supported host session in this repository and confirm the five names and their invocation policies in the host catalog. No global settings change is needed or authorized by this setup.
- Source-principle mappings: source-derived project context is appended to both contracts. Google test-review and OWASP secure-code-review pages were read on 2026-11-22; other retained source pages were not fetched during this pass. No native application test or security scan ran.
