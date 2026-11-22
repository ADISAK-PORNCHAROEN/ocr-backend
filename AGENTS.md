# OCR Backend Agent Guide

This project is a local FastAPI OCR playground. The accepted design uses OpenThai OCR Text on CPU; implementation is not yet present.

## Working agreements

- Work on a branch; open a pull request for every merge into `main`. Do not push commits directly to `main`.
- Split work into focused, reviewable commits by coherent change. Do not combine unrelated work into one commit. Preserve the user's changes.
- Use Python, FastAPI and uv. Follow the accepted layer boundaries in `docs/folder-structure.md`; each feature owns its own files in each applicable layer.
- Keep uploaded documents, OCR output, credentials and local environments out of Git.
- For pstack role assignments, read `C:/Users/Fluke/.agents/pstack-models.md`. When spawning an agent, use only `gpt-6-luna` with `xhigh` (or `max` for the hardest tasks), or `gpt-6.1-sol` with `medium`. If the assigned combination is unavailable, report the limitation instead of selecting another.

## Find the source

- The implementation is not yet present; distinguish the accepted design from implemented behavior.
- For codebase discovery, read `.agents/skills/graphify/SKILL.md` when useful, verify graph freshness and confirm results against source. The Graphify CLI is not installed by this setup; if unavailable, use targeted search.

## Read by task

| Task | Read first |
| --- | --- |
| Product behavior | `PRODUCT.md`, `CONTEXT.md` and `docs/project-scope.md` |
| Architecture or API | `docs/architecture.md`, `docs/folder-structure.md` and `docs/frontend-api.md` |
| Behavior or test change | `docs/TESTING.md` and `.agents/skills/test-engineering/SKILL.md` |
| Application, dependency, executable configuration or CI change | `.agents/skills/security-review/SKILL.md` and `docs/SECURITY-MODEL.md` |
| UI design | `DESIGN.md` and `.agents/skills/impeccable/SKILL.md`; its separate engine is not installed by setup and must not be downloaded without explicit request |
| Hook changes | `.agents/skills/hook-management/SKILL.md`; only for an explicit request and after establishing host, scope, event and behavior |
| Workflow readiness | `docs/agents/skills-checklist.md` and `docs/AI-FOUNDATION-REPORT.md` |

## Completion

Review the actual change against the applicable task skills. Run existing project checks when applicable and report their results and any gaps; do not claim commands or runtime behavior that were not verified. Report the PR and focused commits when created.
