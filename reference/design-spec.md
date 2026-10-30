# How to write a design spec

A design spec settles how a substantial change will be built before implementation and gives a
fresh-context worker enough information to execute it. It connects the system view in
`docs/architecture.md` to the task's interfaces and verification.

## When a spec is required

Write one when the change affects a shared or public interface, including a schema or on-disk
format; when a feature has consequential design alternatives; or when a mistake is expensive to
undo. Significance of the change governs, regardless of project size or how detailed the issue is.

Otherwise, do not add specs for meaning-preserving refactors, objective improvements, changes
invisible to users, or work the issue already fully specifies. Founding uses the architecture
discussion as its design and challenge (`reference/prd.md`).

## Content

1. **Problem and context** — what changes and why; link the issue.
2. **Options considered** — describe all viable options neutrally before stating a choice. Give
   each option's benefits, drawbacks, carry costs, and the failure modes and complexity it introduces.
   For non-trivial capabilities, first survey mature open-source solutions: active maintenance,
   mainstream adoption, ergonomics, and capability fit. Consider composable libraries for the
   sub-problems, rather than comparing a custom build only with an oversized monolith.
3. **Decision** — the chosen design, why its tradeoffs fit, and the files and interfaces it touches.
   Explain any custom build where mature solutions could serve the need.
4. **Out of scope** — boundaries the implementation must respect.
5. **Verification** — a mechanically judgeable end-to-end check from which the done-check derives.
6. **Failure detection and rollback** — required for shared or public interfaces, schemas, and
   expensive-to-undo changes: how to detect partial failure and return safely to the previous state.

Scale detail to the cost of mistakes. Pin exact contracts and fragile step order; leave routine
implementation choices to the worker. Give alternatives enough space for a fair comparison.

## Review and handoff

The orchestrator settles the design direction under `reference/orchestrator.md` §3's feature and
design workflow and commissions the draft in the worker's assigned lane. Before authorizing
implementation, it runs an independent pre-code challenge under `reference/orchestrator.md` §2's
Model and effort section. The challenge checks the alternatives, unjustified
wheel-reinvention, and risks introduced by the proposed design itself.

Use `docs/specs/YYYY-MM-DD-<kebab-title>.md` by default, or an adopted repository's established
location declared in `docs/architecture.md` (`reference/in-repo-writes.md`). Put one of these statuses
under the title: `Status: draft`, `Status: accepted`, `Status: committed`, or `Status: abandoned`.

- Mark the draft `accepted` when the challenge has no blocking grounds. Before the implementation
  continuation, make the accepted blob reachable in the repository, publish its blob SHA on the
  issue, and link the spec in the worker's handoff.
- Carry the spec in the implementation PR and set it to `committed` before code review. This describes
  its state at merge and avoids a post-merge edit to protected main. A decision settled well before
  implementation may instead merge as a small `accepted` spec PR, with the implementation PR
  updating its status later.
- Keep abandoned specs and mark them `abandoned`; never delete them. For closure after an accepted
  spec has merged, use `reference/orchestrator.md`'s Cleanup and release section and a PR.

An architecture-touching change still needs its ADR. The ADR records the decision and why; the spec
records the design and verification. Link them.

## Template

```markdown
# <change>

Status: draft

## Problem and context
<what changes and why; issue link>

## Options considered
<mature solutions surveyed and all viable options, with benefits, drawbacks, carry costs,
introduced failure modes and complexity>

## Decision
<chosen design, rationale, files and interfaces>

## Out of scope
<boundaries>

## Verification
<end-to-end check>

## Failure detection and rollback (when required)
<detect partial failure and safely restore the previous state>
```
