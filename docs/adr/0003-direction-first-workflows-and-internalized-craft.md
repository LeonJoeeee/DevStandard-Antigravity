# 0003 — Direction-first workflows and internalized craft

Status: Accepted (2026-10-30); Amends 0001 (external craft integration only).

## Context

DevStandard's core role pages had accumulated detailed command instructions and execution-skill
bindings alongside their authority rules. Those bindings required a separate craft plugin in each
executor, although dispatched workers already receive a complete role brief. Repeated mechanics
also competed with the engineering judgment the orchestrator needs in daily work: discovering how
to build a capability and deciding what to do about a thoroughly investigated problem.

Issue #30, under parent #29, accepts a direction-first role layer with self-contained craft. This
decision changes what DevStandard prescribes to target projects; it is not a local maintenance
convention for this repository. ADR 0001's host, executor, and safety decisions remain in force;
its historical body is unchanged.

## Decision

Keep hard guardrails for safety and authority, and use light, principle-based guidance for
engineering craft. Preserve mandatory human-message restatement without an acknowledgement
exception, human authorization for irreversibles and architecture-level merges, `hold` and
`delegated`, isolated worker lanes, independent Goal/Floor review, and guarded integration with
green CI for the actual merged result.

Put the two daily engineering workflows directly in the orchestrator role. Gauge feature-request
detail; research detailed specifications directly, and briefly align on rough intent before
launching asynchronous read-only research into existing code and mature open-source building
blocks while continuing the conversation. For bugs and audits, establish root cause, sibling
occurrences, and impact over time before judging whether to act. Compare the problem with each
fix's new failure modes, edge cases, complexity, and carry costs, including leaving tolerable
findings alone. Describe all viable options neutrally before the final assessment and
recommendation.

Put concise planning, reproduction, verification, root-cause tracing, and reuse habits in the
worker brief. Remove the external `superpowers` prerequisite instead of retaining a binding whose
availability can stop a dispatched task. Use public library APIs and extension points; inspect
docs and source before assuming they are inadequate. Missing public extension points or needed
libraries outside Bounds return to the orchestrator. Private-internal coupling and monkey-patching
require compelling justification and explicit prior human consent.

Keep operative decisions and core commands in the role pages; scripts' `--help` and harness pages
own detailed command and executor mechanics. Express lane ownership and a clean handback directly,
without requiring pasted status snapshots. Retaining long external skill tutorials or copying
them into the role pages would preserve the context burden this decision removes.

## Consequences

Each executor receives the craft guidance it needs without resolving another plugin's skills.
The orchestrator remains available during discovery, package reuse can shape task Bounds, and
problem investigation can justify doing less. Guidance depends on engineering judgment rather
than rigid evaluation checklists; future changes must keep it concise and aligned across roles.

Mechanical guards, hooks, CI, model routing, and the fenced reviewer contract do not change. The
reviewer's MIT attribution remains. Supporting topic/template pages are handled separately by
issue #31. This capability change ships as plugin version 1.5.0; architecture-level integration
still waits for explicit human sign-off on the reviewed green PR.
