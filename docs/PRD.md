# DevStandard-Antigravity Project Definition (PRD)

Approved for DevStandard-Antigravity; this document is the measuring stick for every structure in
this repository — see the existence criterion at the end.

## 1. Problem background

1. **The native harness provides a single agent.** Advancing several pieces of work in parallel
   forces the human into the scheduler-and-coordinator role; their time goes to coordination
   instead of direction.
2. **An unsupervised agent's completion claims are untrustworthy.** Observed in practice:
   completion claims with no evidence, tests weakened until they pass, code reaching the main
   branch unreviewed.
3. **Irreversible operations carry the highest risk.** Ordinary mistakes are acceptable;
   unrecoverable damage is not. A run-first-fix-later strategy is premised on things remaining
   fixable.
4. **Repeated revision erodes the core of the work.** An agent's first pass usually gets the core
   right, with defects concentrated in the periphery; after several review-and-fix rounds the
   periphery approaches perfection while the core is lost. Two causes: the multi-round mechanism
   itself induces goal drift, and the review prompt steers reviewers toward secondary issues.
5. **Agents lack the working conventions human developers assume.** Where files belong, when to
   ask before acting, what must not be touched — every fresh session violates them anew.
6. **The rules layer accretes incident by incident.** Preventive construction piles up until the
   layer is too large to read or maintain.

## 2. Structures reused as-is

1. **The GitHub collaboration flow** (issues / PRs / review / CI): the structure human software
   development has already validated; machines simply reuse it.
2. **git worktrees, OS-level sandboxes, branch protection**: parallel isolation and enforcement,
   natively available, requiring only configuration.
3. **The superpowers skill library**: mature working methods — test-driven development,
   systematic debugging, requirements clarification — bound into the workflow per role: the
   worker role binds execution skills, the orchestrator role binds requirements skills. Centralized
   binding points ensure that upgrading or replacing the library touches one place.

## 3. Vision

> **One person directs an agent team through development: the human owns direction, sets the
> acceptance criteria, and signs off on architecture-level changes and major releases; one
> Antigravity orchestrator converses, dispatches, gates quality against those criteria, and merges; N
> workers process N issues in parallel. Fast, without losing control.**

**Who this is for:** anyone carrying medium-to-large work through Antigravity — a solo developer
directing several parallel agent lanes, or a team where several humans each direct their own
orchestrator sessions. The team case is this same picture once per human, not a second design.

## 4. The solution: the target workflows

The substance of this product is the three workflows below; every rule, file, and mechanism exists
to make agents run by them.

**Workflow 1: the full lifecycle of one task**

```
Entry: the human raises a need, or the orchestrator finds a problem
  → Discussion pins down: the wanted result, and why        [human participates]
  → Human confirms the conclusion                          [human participates]
  → 1. Complete the issue: goal, bounds (weight and required finish), done-check
  → 2. Dispatch: branch + worktree + role injection
  → 3. Worker: implement → rebase onto current main → run the done-check on the
       final state, keep the evidence
       → open the PR (restating the goal, with evidence of fulfillment)
       → drive the checks green → deliver
  → 4. Orchestrator acceptance: one clean-context reviewer rules on
       "did this PR accomplish what the issue set out to accomplish"
       ├ Goal met     → peripheral issues recorded as notes; no re-review; pass
       ├ Goal not met → return for fixes → re-review (judging the goal only)
       └ Conflicts with main → dispatch a resolver → re-review
       (Ordinary tasks pass on this ruling alone. Architecture-level changes and
        major releases additionally wait for the human's sign-off before merge.)
  → 5. Worker drives CI green before handback → reviewer sees a green PR →
       review pass + CI green → merge → close the issue → remove the worktree
  → 6. Release (repos with a standing delegation) → one-line report to the human
```

**Workflow 2: the orchestrator's main loop**

The orchestrator is a single-threaded event handler running in Antigravity. Events — the human's
messages, worker deliveries, verdicts returning, CI state changes, monitor notifications — arrive at
any time. It handles one event at a time and then returns to what was in hand (usually the discussion
with the human). Priority: a request to authorize an irreversible action and a red main outrank
arrival order; everything else is handled in the order it arrives.

Nothing waits inside the loop: dispatch returns immediately or spawns a background executor task;
results come back as events (including native `send_message` wakeups). Concurrency lives in the
workers, not in the orchestrator, which has one conversation and one context; it carries N workers by
keeping each event's handling short.

```
loop {
  The human speaks        → discuss / create issues / adjust direction
  An irreversible action
  is needed               → stop; request the human's authorization;
                            proceed only after approval
  An architecture-level
  change or major release
  is ready to merge       → wait for the human's sign-off
  Ready issues await
  dispatch               → dispatch, N ways in parallel (Codex CLI, native subagents)
                            (cut scopes to minimize file overlap)
  A worker delivers       → acceptance → start the review
  A verdict returns       → met: merge, clean up, release
                            not met: return | conflict: dispatch a resolver
  Main goes red           → freeze new dispatch; revert first
  Idle                    → sweep leftovers; report progress
}
The orchestrator does by hand only: changes on the order of one or two lines,
and research. Everything else is dispatched.
```

**Workflow 3: the worker's one execution**

```
Receive the task (role context + the whole issue, freshly fetched: body and comments)
  → Check the task is specified: goal or done-check missing/vague → do not start;
    return it to the orchestrator
  → Take position: own branch + worktree; record a starting-state snapshot (baseline)
  → Implement, using the execution skills (TDD, systematic debugging); change only what
    is in the task's scope; trace wherever the cause leads
       On any of four events → stop, escalate to the orchestrator, wait:
         touching core architecture | an irreversible action needed |
         done-check wrong or unreachable | stuck on a direction call
  → Rebase onto current main; resolve own conflicts
  → Run the done-check on the final state; keep the evidence (commands, exit codes, output)
  → Open the PR: restate the goal — "done, evidence here"
  → Drive CI green: red caused by own diff → fix; red not one's own → escalate
  → Hand back to the orchestrator; leave the worktree in place (removed at merge)
  ← Returned (goal not met) → fix the named gap → repeat rebase → done-check →
    evidence → hand back
```

**The two roles.** Orchestrator — converse, discuss, relay between human and workers, gate and
merge; stays responsive. Worker — a fixed-role executor; one task maps to one branch and one
worktree; delivers evidence; never merges; stops and escalates on anything major. An action that is
irreversible (deleting data, force-pushing shared branches, publishing, writes leaving the repo)
always stops for the human's authorization before anyone performs it.

## 5. Implementation

Antigravity ships its own harness — sessions, subagent invocations, tool execution, permissions. On
the native harness alone, agents will not run the workflows of section 4: the native layer has no
notion of roles, no dispatch-and-acceptance protocol, and no concept of multi-agent parallel
collaboration.

This project provides a **supplementary harness** on top of Antigravity:

- **hooks** — `hooks.json` declares lifecycle hooks:
  - `SessionStart`: injects the orchestrator's self-contained role reference into context via
    Antigravity's `injectSteps` structure.
  - `PreToolUse`: dual-protocol word-guard inspecting commands before execution (supporting both
    Antigravity camelCase `toolCall` and Codex snake_case `tool_name`).
- **skills** — mature methods from superpowers invoked at matching workflow steps.
- **native subagents (`invoke_subagent`)** — Antigravity-native subagent workers and reviewers
  spawned with model selection (`pro` for workers and reviewers) and continuation via `send_message`.
- **external agent processes** — headless CLI workers and reviewers:
  - **Codex CLI (`--implementation codex`)**: OS-sandboxed worker execution with bubblewrap/AppArmor,
    and disposable pinned checkouts for reviewers.
- **scripts** — mechanical steps (`scripts/dispatch`, `scripts/review-packet`, `scripts/guard`)
  made deterministic and auditable.

**Context engineering.** The orchestrator's harness and the worker's harness are two separate sets,
designed and delivered separately. The orchestrator's set is built around communication and
decisions: requirements skills, dispatch, acceptance, merge, human interaction. The worker's set is
built around execution: implementation skills (TDD, systematic debugging), task boundaries, evidence
duties, and escalation rules. Each set is self-contained. The two sets share only the workflow
contract itself — the interface where the roles interlock.

## 6. Success criteria

Success is defined as: the problems of section 1 no longer occur:

1. **The human no longer schedules**: with several pieces of work in parallel, the human's actions
   reduce to giving direction, inspecting results, and authorizing irreversibles.
2. **Zero evidence-free completion claims pass acceptance.**
3. **Zero unauthorized irreversible operations occur.**
4. **The core is no longer lost**: after acceptance, a deliverable's core is still the goal its issue
   set; rework of the "periphery perfected, trunk lost" kind no longer appears.
5. **Fresh sessions no longer violate working conventions.**
6. **The rules layer stays readable end-to-end**: every rule traces to a problem above or a reuse
   decision in section 2; whatever cannot be traced has been deleted.

## 7. Boundaries

- **Never replaces the native harness; supplies only the difference.**
- **Zero errors is not the goal**: outside irreversible accidents, problems surface in running and
  are fixed once surfaced; acceptance rules on "goal met within declared bounds", not perfection.
- **No preventive construction**: rules are established by real incidents, structure is built by
  real need; anything constructed in advance for an imagined problem is presumed wrong.
- **Never rewrites the craft it reuses**: where superpowers already teaches a method, the flow points
  at it by name and never copies its content onto our pages.
- **Release is never automatic by default**: shipping is tag-triggered and the human decides when
  to tag (unless a standing delegation has been explicitly given for this repo).

**Existence criterion:** every rule, file, and mechanism in this supplementary harness must trace
back to a problem in section 1 or a reuse decision in section 2; whatever cannot be traced is to be
deleted.
