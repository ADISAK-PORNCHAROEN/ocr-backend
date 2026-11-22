# Security standards and project mapping

Read before selecting risks, verification requirements or abuse cases for a diff.
During foundation setup/repair, adapt this contract to actual source, assets,
trust boundaries and policy. Retain every source below with its role, version
and local application. Link the project security model and SECURITY.md as the
owners of observed boundaries/invariants and reporting policy.

## Sources and application

| Source / edition | Principle to apply | Project mapping and evidence to establish |
| --- | --- | --- |
| [OWASP Top 10:2025](https://top10.owasp.org/2025/0x00_2025-Introduction/) | Identify applicable risk categories from changed boundaries | Map actual inputs, controls and sinks to relevant categories with justified exclusions |
| [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS/tree/v5.0.0/5.0) | Select concrete, testable security requirements | Read selected requirement text and record version-prefixed IDs, applicability, source control and actual verification outcome |
| [OWASP WSTG v4.2](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/) | Select applicable verification scenarios | Record versioned scenario, authorized local target, prerequisites, procedure and outcome |
| [OWASP Secure Code Review Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html) | Incremental diff review, data flow and validation of candidate issues | Trace attacker-controlled input through checks/transformations to reachable sinks in the reviewed patch |
| [OWASP Secure Coding with AI Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html) | Review AI-generated code, test changes and tooling provenance | Inspect dependency/tool changes, altered assertions, negative/recovery cases and preserved native gates |
| [OpenAI Codex Security](https://help.openai.com/en/articles/20001107-codex-security) | Contextual investigation and isolated validation | Use the installed host diff workflow's actual preflight, artifact and recovery rules and record capability gaps |

Keep versioned editions stable until an authorized workflow update reviews the
new edition and mappings. Read exact selected requirement/scenario text before
recording IDs. Recheck evolving cheat sheets or host documentation when a decision
depends on them; preserve unavailable links and report failed reads honestly.
Top 10 categories alone do not prove complete coverage or OWASP compliance.

## Map and review actual boundaries

For each affected asset/boundary, identify the source/caller, attacker control,
validation, transformation, sink, accepted invariant and relevant tests. Follow
the real diff, including new executable files, into supporting callers. Examine
authorization, hostile input, output, secrets, dependencies, exceptional paths
and logging where reachable. Explain excluded web/session scenarios from the
actual application; revisit them when a change introduces those boundaries.

Use the installed diff-review capability for patches. Repository/scoped baseline
audits and multi-pass scans require their explicit task scope. Preserve the same
durable scan identity and its recovery rules. If the capability is unavailable,
record the blocker and identify the bounded manual review actually performed.

Before confirming a candidate, establish reachability, prerequisites, protections
and concrete impact. Keep confirmed issues, candidates and unreviewed scope
distinct. A correctness defect alone does not establish exploitable impact.

## Connect the workflow and evidence

The generated SKILL.md routes here directly and connects to the project-local
test-engineering skill for relevant negative/regression checks. A host diff
scanner is optional; the local manual method remains complete without it.
Inherit the native quality profile, reporting policy, evidence owner and
isolated fixture rules. Keep custom hooks, disabled controls and action
authorization consistent with the existing harness. Report patch identity,
paths, actual tool/mode (or manual review), selected requirements/cases,
findings/candidates, exclusions and coverage gaps. A clean result applies only
to the reviewed snapshot.

## OCR Playground mapping (2026-11-22)

Run from the repository root. [Architecture](../../../../docs/architecture.md), [scope](../../../../docs/project-scope.md) and the [draft API](../../../../docs/frontend-api.md) describe a planned loopback-only OCR backend, not a running implementation. [Security policy](../../../../SECURITY.md) owns reporting decisions; [security model](../../../../docs/SECURITY-MODEL.md) owns assets, proposed controls and unresolved choices. No implemented control or completed security scan is evidenced by these design documents.

For a future executable diff, trace uploaded JPG/PNG/PDF bytes through content validation, decoding/rasterization, the native OCR adapter, temporary storage and returned text/images. Inspect file/path handling, parser/runtime dependencies, bounded upload/page/pixel/queue resources, sensitive logs and cleanup after failure/restart. Deletion/expiry must reject late worker results and prevent restored access to deleted work. These are planned invariants to verify once source exists.

OWASP's Secure Code Review source was read on 2026-11-22; its incremental/data-flow method applies to those changed boundaries. The other retained sources were not individually fetched in this packaging pass. Select precise ASVS 5.0.0 or WSTG v4.2 requirements only after reading their text for the implemented change; no unverified requirement IDs or compliance claim are recorded here. Top 10 categories are a relevance aid, not proof.

Account/session, payment and persistent-database scenarios are excluded by the current documented scope; revisit them if implementation introduces those boundaries. Absence of accounts does not prove job identifiers or loopback deployment are safe. Public deployment and cross-user access policy remain outside the approved local demo scope. Review actual binding, origins, resource limits and response behavior when code exists.

No host scanner is required for the manual diff method; report availability/use separately. This setup performs no application scan. Record exact patch identity, paths, attacker control, sink, protections, candidate status and coverage gaps. Connect negative/recovery cases to the [test-engineering skill](../../test-engineering/SKILL.md). On unavailable tools or uncertain reachability, preserve evidence and report the gap instead of confirming a finding. No external publication or fix is implied by review authority.
