# 0003 — Harness Engineering alignment and streamlined collaboration gates

Status: Accepted (2026-10-30).

## Context

Across early dogfooding on Antigravity and Codex CLI, four structural frictions surfaced in
DevStandard's collaboration layer:

1. **Incident-accreted prompt bloat and cross-file splicing:** Role and supporting `reference/*.md`
   pages had accumulated incident anecdotes, banned-word catalogs, rigid counting predicates, and
   worker-mechanics blocks spliced out of orchestrator harness files. Every session paid to read
   ceremony that crowded out engineering judgment.
2. **External skill-plugin lock-in (`superpowers`):** Requiring an external craft plugin across both
   Antigravity and Codex CLI installations added setup friction and brittle skill-name coupling for
   foundational habits (proportional scratch planning, fail-before-pass reproduction, root-cause and
   sibling tracing, public-API-first reuse) that frontier models execute cleanly when stated
   concisely inside their own role map.
3. **Undifferentiated intake and premature fixing:** Feature work and bug/audit work used a single
   rigid ceremony instead of matching real engineering judgment — exploratory features needed
   concurrent non-blocking survey of existing repository capabilities and mature open-source
   packages (plus explicit human consent before monkey-patching private library internals), bug and
   audit findings needed root-cause, cost-of-inaction, and fix-induced-complexity evaluation before
   deciding whether a fix is even warranted, and multi-option discussions needed neutral trade-off
   comparisons before stating a recommendation.
4. **Stateful review noise and per-PR version conflicts:** Pre-flight PR reservation comments
   (`reserved` / `dispatched` / `fail`), four-line `Goal verdict` / `Floor` / `Ready to merge`
   rubrics, open-ended rework loops, and per-PR version-manifest bumps produced PR comment clutter,
   stranded lanes on transient CLI failures, and artificial merge conflicts across parallel
   worktrees that required special-case manifest exemptions in rebase checks.

## Options considered

1. **Option 1: Holistic Harness Engineering simplification and internalized craft.**
   Consolidate roles into three concise single-reader navigation maps (`reference/orchestrator.md`,
   `reference/worker.md`, `reference/reviewer.md`) with internalized craft and zero external skill
   dependencies; split orchestrator intake into clarity-sensitive feature discovery (with concurrent
   read-only OSS/repo research and public-API-first discipline) and deep-first bug/audit judgment
   (including leaving tolerable issues alone when fixes add worse complexity), backed by
   neutral-first option comparison; upgrade `reference/reviewer.md` to targeted active verification
   in isolated scratch within three hard red lines and a two-tier `Approve | Request changes`
   (`### Verdict`, `### Blocking`, `### Notes`) output; make `scripts/review-packet` stateless with
   a 2-round non-convergence human escalation rule while retaining read compatibility for historical
   PR verdicts; and pair release-time versioning with pure git-tree equality in `scripts/guard`
   rebase proofs and streamlined canonical path norms (`reference/in-repo-writes.md`,
   `reference/where-it-goes.md`).
   - *Pros:* Removes external plugin setup on both Antigravity and Codex; keeps per-session context
     lean and single-sited per reader; empowers reviewers to verify runtime edge cases safely;
     eliminates pre-flight PR comment spam, stranded reservations, and parallel version-bump merge
     conflicts; deletes manifest-exemption complexity from `scripts/guard`.
   - *Cons:* Requires coordinated updates across role pages, dispatcher/review/guard scripts, CI
     contract tests, and top-level documentation. Native Antigravity reviewers share the host
     filesystem and therefore rely on explicit red lines, isolated `/tmp` probe rules, and
     `PreToolUse` `gh` write-flag refusals rather than a separate OS mount namespace.
   - *Carry costs and new risks:* Maintaining `allow_legacy=True` parsing so historical PR review
     comments remain verifiable; keeping role maps within CI conciseness caps without losing hard
     safety boundaries.

2. **Option 2: Incremental patching onto external skill bindings, multi-part rubrics, and stateful
   reservations.**
   Keep the `superpowers` dependency, spliced worker-mechanics blocks, `Goal verdict` / `Floor` /
   `Ready to merge` rubric, pre-flight PR reservation state machine, HTML-counted doc predicates,
   and per-PR version-bump rebase exemptions, while layering new feature/audit and active-review
   guidance onto existing pages.
   - *Pros:* Smaller immediate diff to scripts and historical test fixtures; single review comment
     schema across old and new PRs.
   - *Cons:* Retains dual-host external plugin installation requirements; increases prompt size and
     cross-file coupling; preserves PR reservation failure modes and parallel version-manifest
     conflicts.
   - *Carry costs and new risks:* Permanent upkeep of custom reservation-recovery subcommands,
     manifest-hunk stripping in rebase proofs, and sprawling prompt prose that dilutes high-cost
     safety rules.

## Decision

Adopt **Option 1**:

1. **Concise single-reader role maps without external craft plugins:** Ship self-contained role maps
   in `reference/orchestrator.md`, `reference/worker.md`, and `reference/reviewer.md` under CI line
   caps, internalizing proportional planning, fail-before-pass verification, root-cause/sibling
   tracing, public-API-first reuse, and fix-complexity judgment while removing `superpowers` and
   orchestrator-to-worker text splicing (`scripts/dispatch` delivers runtime lane/helper context
   directly in `# Task packet`).
2. **Real-workflow orchestration and human alignment:** Preserve `Looking needs no permission; doing
   always does`, `hold` / `delegated` controls, and mandatory `Restate before acting`; separate §3
   into clarity-sensitive feature/design intake (with concurrent non-blocking read-only subagent
   surveys of existing capabilities and mature open-source solutions, and explicit prior human
   consent required for monkey-patching private library internals) and deep-first bug/audit
   evaluation; and require neutral-first option presentation with recommendations strictly at the end.
3. **Targeted active-verification review and stateless 2-round convergence:** Replace the passive
   rubric page with `reference/reviewer.md` (9 clean slots, isolated `/tmp` or scratch active
   verification within three hard red lines, and `Approve | Request changes` + `### Blocking` +
   `### Notes`). Make `scripts/review-packet` stateless (`## Code Review — round N` posted only on
   valid return, `allow_legacy=True` retained for historical PR comments) and enforce a 2-round
   convergence rule escalating repeated blockers to the human (`--human-authorization` required on
   `merge-as-is`).
4. **Streamlined hygiene and conflict-free release-time versioning:** Simplify
   `reference/in-repo-writes.md` and `reference/where-it-goes.md` around canonical document paths
   and explicit bans on committed `SUMMARY.md` / `HANDOFF.md` junk, defer version bumps to release
   time, and verify post-acceptance rebases in `scripts/guard` via pure conflict-free git-tree
   equality (`replay^{tree} == new_head^{tree}`).

## Consequences

- **Improves:** Onboarding requires only DevStandard, Antigravity, `git`, `gh`, Python, and optional
  Codex CLI; orchestrator, worker, and reviewer sessions receive crisp, role-pure instructions; PR
  threads stay clean; reviewers catch runtime edge cases early without mutating lanes; and parallel
  worktrees rebase cleanly without version-bump collisions.
- **Costs:** `scripts/review_packet.py` carries a small read-only legacy parser (`allow_legacy=True`)
  for historical `## Merge check 1 — round N` comments, and `.github/workflows/ci.yml` enforces
  canonical documentation paths and role-map conciseness caps on every PR.
- **Watch:** Keep future additions to `reference/*.md` subject to the same proportional-weight test —
  prefer deleting machinery or sharpening principles before adding new rules, and verify native
  reviewer probes stay strictly inside isolated temporary directories.
