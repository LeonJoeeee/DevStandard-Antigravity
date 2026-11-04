# How to write a design spec

A design spec (`docs/specs/YYYY-MM-DD-<kebab-title>.md`, or an adopted repository's established
location declared in `docs/architecture.md` under `reference/in-repo-writes.md`) pins a concrete
technical contract connecting `docs/architecture.md` to task-level interfaces, verification, and
rollback. Most work needs no spec file.

## When to write a spec

Reserve `docs/specs/YYYY-MM-DD-<kebab-title>.md` strictly for two cases:

1. **Multi-lane shared contracts:** multi-issue work whose shared interfaces, schemas, wire/storage
   formats, protocols, or step-ordered migrations are too detailed to hold cleanly in the parent
   tracking issue and must stay aligned across parallel or sequenced worker lanes.
2. **Human-confirmed standalone specs:** an effort where the human explicitly requests or confirms a
   committed spec during pre-work alignment (`reference/orchestrator.md` §3).

Otherwise, skip `docs/specs/`: single-issue work (including high-cost interface or schema changes,
which receive an internal pre-code challenge and inline issue contract), multi-issue splits whose
parent and leaf issues already state the contract clearly, refactors, bug fixes, and founding setup
(`reference/prd.md`) carry their contract directly on the issue.

**Do not duplicate ADRs:** a spec records *what* is built and *how* its interfaces, verification,
and rollback work — without lifecycle status headers, hash-pinning ceremony, or option-comparison
prose. Option comparisons happen in conversation (`reference/orchestrator.md` §3), and durable
architectural rationale and tradeoffs live in `docs/adr/` (`reference/adr.md`). When a change also
alters shared architecture or makes a costly-to-reverse decision, record the *why* in an ADR and
link the two.

## Content

Scale detail to the cost of mistakes; pin exact contracts and fragile step order while leaving
routine local implementation choices to each worker:

1. **Context and scope** — what changes, why, and linked parent/leaf issues (plus ADR link when applicable).
2. **Concrete interfaces and invariants** — exact signatures, schemas, on-disk/wire formats, touched
   modules, and required migration or rollout ordering. Note any mature open-source package reused
   via its public API (or cite the ADR justifying a custom build).
3. **Out of scope** — boundaries every implementation lane must respect.
4. **Verification** — deterministic end-to-end checks from which leaf `## Done-check` commands derive.
5. **Failure detection and rollback** — required for shared/public interfaces, schemas, migrations,
   and hard-to-reverse changes: how partial failure is detected and how to restore the prior state safely.

## Review, delivery, and maintenance

Under `reference/orchestrator.md` §2 and §3, the orchestrator drafts the contract and issue split
internally, runs a clean-context read-only `inherit` subagent challenge (`TypeName="self"`) checking
design soundness, mature open-source reuse, rollback safety, and cross-lane interface/`Bounds`
alignment, resolves routine engineering gaps internally, and confirms the polished contract and
split with the human before execution starts.

Deliver a confirmed spec through one of two paths:

- **Single implementation PR:** when a single implementation lane builds a human-confirmed spec,
  carry `docs/specs/YYYY-MM-DD-<kebab-title>.md` in that implementation PR.
- **Prerequisite spec leaf PR before parallel lanes:** when parallel implementation lanes depend on
  the shared contract, merge the spec first via its own prerequisite leaf issue and worker lane
  (`Parent: #<parent>`), then lift `hold` on the `after #<spec-leaf>` implementation leaves (each
  still inlining its leaf-specific contract alongside the spec path). Never dispatch a worker on the
  held parent tracking issue.

Specs carry no status header. Keep active specs synchronized while lanes build against them; when a
spec is superseded, obsolete, or cancelled, update or remove it through an ordinary reviewed PR
under `reference/in-repo-writes.md` (`reference/orchestrator.md` Cleanup and release), leaving
durable decision history in `docs/adr/`.

## Template

```markdown
# <Contract or change title>

## Context
<what changes and why; parent/leaf issue links; ADR link when applicable>

## Interfaces and invariants
<exact signatures, schemas, formats, touched modules, and required step/migration ordering>

## Out of scope
<explicit boundaries>

## Verification
<deterministic end-to-end check informing leaf Done-checks>

## Failure detection and rollback
<how partial failure is detected and safely rolled back; omit only for purely additive low-risk contracts>
```
