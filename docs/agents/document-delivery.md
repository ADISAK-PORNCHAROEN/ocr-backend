# Foundation document delivery

This project has accepted product and API design documents but no OCR application, dependency manifest, application tests, database, or CI configuration. Each row records the canonical owner and source evidence; planned behavior is not implemented behavior.

| Document | Applicability and content evidence | Review / remaining decision |
| --- | --- | --- |
| `AGENTS.md` | Required; owner rules, accepted layering and project routes | Original preserved in `docs/history/agent-instructions/`; host loading unverified |
| `CLAUDE.md` | Required; one-line import | Claude host loading unverified |
| `PRODUCT.md` | Required; owner-approved `docs/project-scope.md` and `docs/spec.md` | Implementation pending |
| `CONTEXT.md` | Required; confirmed OCR terms | Revisit as domain terms are agreed |
| `DESIGN.md` | Required; accepted flow in `docs/frontend-guide.md` | Visual system and UI implementation not established |
| `SECURITY.md` | Required; security model pointer | Reporting contact and policy not established |
| `docs/architecture.md` | Applicable; accepted design and `docs/folder-structure.md` | Worker and model behavior unverified |
| `docs/frontend-api.md` | Applicable; agreed proposed API | Endpoints and model mapping unimplemented |
| `docs/TESTING.md` | Applicable; planned API and OCR behavior from spec | No native test runner or tests yet |
| `docs/SECURITY-MODEL.md` | Applicable; planned upload, model and temporary-file boundaries | Controls are design requirements, not verified behavior |
| `docs/SCHEMA.md` | Not applicable: no persistent schema or database exists or is planned for v1 | Revisit if persistence is introduced |
| `docs/adr/` | Not required by setup; design rationale is in `docs/architecture.md` | Create an ADR when the documented criteria apply |
| `docs/agents/skills-checklist.md` | Required; inventory and discovery status | Runtime skill discovery unverified |
| `.agents/skills/test-engineering/SKILL.md` and its `references/testing-contract.md` | Required; project test workflow | Inspect actual source and tests for each future change |
| `.agents/skills/security-review/SKILL.md` and its `references/review-contract.md` | Required; change-scoped security review | No application diff to review in setup |
| `.agents/skills/graphify/SKILL.md` | Required; source discovery | Local CLI and post-commit are documented in `docs/agents/graphify.md` |
| `.agents/skills/hook-management/SKILL.md` and its `references/hook-change-contract.md` | Required; explicitly requested hook changes | Local post-commit configured; host lifecycle hooks not configured |
| `.agents/skills/impeccable/SKILL.md`, `agents/openai.yaml` and `reference/hooks.md` | Required; UI design workflow | Separate engine and runtime discovery unverified |
| `docs/AI-FOUNDATION-REPORT.md` | Required; evidence, limitations and continuation | Update as capabilities change |
