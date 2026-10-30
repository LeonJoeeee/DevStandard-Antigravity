# DevStandard-Antigravity Project Definition (PRD)

Approved for DevStandard-Antigravity; this document is the measuring stick for every structure in
this repository — see the existence criterion at the end.

## 1. Problem background

1. **The native harness provides a single agent.** Advancing several pieces of work in parallel
   forces the human into the scheduler-and-coordinator role; their time goes to coordination
   instead of direction.
2. **An unsupervised agent's completion claims are untrustworthy.** Observed in practice:
   completion claims with no final-state evidence, tests weakened until they pass, private
   third-party internals silently monkey-patched, and unreviewed changes reaching `main`.
3. **Irreversible operations carry the highest risk.** Ordinary mistakes in an isolated branch are
   recoverable; deleting data, force-pushing shared branches, mutating live services, or writing to
   unauthorized host paths is not.
4. **Unguided review loops erode the core of the work.** Without a clear blocker boundary and a
   convergence stop, multi-round review drifts into secondary churn or endless back-and-forth while
   losing sight of whether the change soundly and proportionally solved its goal.
5. **Agents lose working conventions across sessions and compactions.** Canonical document homes,
   scratch boundaries, speech-transcription restatement, and role limits vanish in fresh sessions
   or after context compaction unless the harness delivers and restores them reliably.
6. **Incident-driven rules accrete into brittle ceremony.** Preventive micro-prescriptions, external
   skill-plugin dependencies, per-PR version-bump rituals, and stateful comment machinery pile up
   until prompts crowd out engineering judgment and manufacture avoidable merge conflicts.

## 2. Structures reused as-is

1. **The GitHub collaboration flow** (issues / branches / PRs / code review / CI): the durable
   state machine human software teams have already validated.
2. **git worktrees, OS-level sandboxes, and server-side branch protection**: parallel filesystem
   isolation and mechanical branch enforcement, natively available.
3. **Antigravity lifecycle hooks and native subagents, paired with self-contained engineering
   craft**: Antigravity's `SessionStart`, `PreInvocation`, `PreToolUse`, `invoke_subagent`, and
   `send_message` primitives combined with concise single-reader role maps (`orchestrator`,
   `worker`, `reviewer`) and zero external skill-library dependencies.

## 3. Vision

> **One person directs an agent team through development: the human owns direction, sets
> acceptance criteria, and authorizes irreversible actions, architecture-level changes, and
> releases; one Antigravity orchestrator converses, researches, dispatches, coordinates independent
> code review, and integrates; N workers build and verify N issues in parallel. Fast, high-trust,
> and under control.**

**Who this is for:** anyone carrying medium-to-large software engineering work through Antigravity —
a solo developer directing parallel agent lanes, or a team where each human directs their own
orchestrator session over the shared GitHub repository.

## 4. The solution: the target workflows

Every rule, reference page, hook, and script in this repository exists to run these three workflows.

**Workflow 1: the full lifecycle of one task**

```
Entry: the human raises a need, or an audit/bug surfaces a candidate problem
  → Restate before acting: organize what the human meant, mark inferences, catch
     shorthand or speech-transcription slips before mutating state        [human participates]
  → Shape the direction by work type:
     ├ Features, new capabilities, and design:
     │  gauge input clarity first — clear specs proceed straight to scoping;
     │  rough ideas align on intent while a concurrent non-blocking read-only
     │  subagent surveys existing repo capabilities & mature open-source solutions
     │  (maintenance, adoption, ergonomics, reputation, composable fit);
     │  enforce public-API-first usage (monkey-patching requires compelling
     │  technical justification + explicit prior human consent)
     └ Bugs, problems, and codebase audits:
        trace root cause, sibling occurrences, and cost of inaction BEFORE judging
        worthiness; weigh fix-induced complexity, new failure modes, and carry cost,
        recommending leaving tolerable issues alone when fixes create a bigger mess
  → Compare viable options neutrally first (pros, cons, new risks, carry costs),
     place recommendation strictly at the end, and confirm with human     [human participates]
  → 1. Prepare leaf issue proportionally: Goal, Bounds, deterministic Done-check
  → 2. Dispatch isolated lane: 1 issue = 1 branch = 1 worktree = 1 writer
  → 3. Worker: plan in scratch → fail-before-pass / root-cause implementation →
        rebase onto current main (no per-PR version bump) → run Done-check on final
        state → verify empty git status → open PR & drive CI/bot checks green
  → 4. Independent code review (`reference/reviewer.md`): clean-context reviewer
        reads pinned diff and runs targeted active verification probes in isolated
        scratch within three hard red lines, returning `Approve | Request changes`
        with `Blocking` items and non-blocking `Notes`, published statelessly as one
        `## Code Review — round N` comment:
        ├ Approve          → `Notes` never block or trigger re-review; ready to merge
        ├ Request changes  → continue worker on `Blocking` items (if 2 rounds fail to
        │                     converge on the same problem, stop and escalate to human)
        └ Base advanced    → pure rebase + git-tree equality proof (no extra review round),
                              or conflict resolution + fresh review
  → 5. Guarded merge (`scripts/guard merge`) under human or `delegated` merge
        authority → reconcile parent/dependent issues & docs → clean up lane
  → 6. Release-time versioning: bump version manifests only when cutting a human-
        authorized (or standing-delegated) release, keeping parallel lanes conflict-free
```

**Workflow 2: the orchestrator's main loop**

The orchestrator is a single-threaded, non-blocking event handler in the main Antigravity session.
Background CLI dispatches (`--wait` in a background task) and native Antigravity subagents
(`invoke_subagent` + reactive `send_message` wakeups) run asynchronously while the orchestrator
remains reachable to the human. Requests to authorize irreversible actions and red-`main` recovery
outrank new dispatch; GitHub issues and PRs hold durable state.

```
loop {
  The human speaks        → open with `Restate before acting`; research freely;
                             compare options neutrally before recommending; confirm doing
  Irreversible action or
  monkey-patch needed     → stop; explain impact/justification; wait for explicit human words
  Main goes red           → freeze new dispatch; restore green first (normally via revert)
  Ready leaf issues wait  → partition scopes to avoid overlap; dispatch N lanes in parallel
                             (Codex CLI default, or native Antigravity subagents)
  A worker hands back     → verify clean tree & green CI; start stateless code review
  A verdict returns       → `Approve` + green CI: merge via `scripts/guard merge` when
                             authorized (human sign-off always required for architecture
                             changes and major releases), then clean up lane
                             `Request changes`: continue worker on `Blocking` items, or
                             escalate to human on `[Needs human decision]` or 2 non-
                             converging rounds
  Release authorized      → bump version at release time, merge through review + CI, tag/deploy
}
The orchestrator edits directly only for tiny 1–2 line changes; substantive work goes to lanes.
```

**Workflow 3: the worker's one execution**

```
Receive `# Task packet` + `reference/worker.md`
  → Verify packet fields, `Goal`, `Bounds`, `Done-check`, ordered comments, and isolated worktree
    (if underspecified, conflicting, or baseline-broken → stop and return immediately)
  → Plan proportionally in task scratch (never commit `SUMMARY.md` / `HANDOFF.md` junk)
  → Implement within `Bounds`:
      reproduce / fail-before-pass where testable | trace root causes & siblings |
      reuse existing modules & declared packages via official public APIs |
      weigh fix-induced complexity and delete dead code left by edits
      On scope/architecture expansion, out-of-`Bounds` root cause, monkey-patching need,
      irreversible action, invalid `Done-check`, or hook/sandbox refusal → stop and escalate
  → Fetch `origin`, rebase onto current `main` (never bump release versions unless asked)
  → Run complete `Done-check` on final rebased state; remove scratch so `git status` is empty
  → Push branch, open PR with goal restatement & final-state evidence, drive CI & bots green
  → Return PR and evidence to orchestrator; leave worktree intact for orchestrator cleanup
```

**The three roles.**
- **Orchestrator (`reference/orchestrator.md`):** converses (`Restate before acting`), investigates
  and compares options neutrally, scopes issues proportionally, dispatches lanes, commissions
  stateless reviews, enforces the 2-round convergence rule, and runs guarded merges and cleanup.
- **Worker (`reference/worker.md`):** accountable single-lane builder (`1 issue = 1 branch =
  1 worktree = 1 green PR`); internalizes execution craft; never merges, pushes to `main`, or
  bypasses hooks/sandboxes.
- **Reviewer (`reference/reviewer.md`):** independent Senior Code Reviewer combining static diff
  inspection with targeted active verification in isolated scratch under three hard red lines
  (never touch repo worktrees/refs, never write to GitHub/remotes, never trigger live side effects),
  returning `Approve | Request changes` with `Blocking` and `Notes`.

## 5. Implementation

DevStandard supplies a lightweight **supplementary harness** on top of Antigravity:

- **Lifecycle and guard hooks (`hooks.json`, `hooks/`):**
  - `SessionStart` (`hooks/session-start`): injects `reference/orchestrator.md` whole via
    `injectSteps` at top-level session start while suppressing all subagents.
  - `PreInvocation` (`hooks/session-start --pre-invocation`): scans `transcript.jsonl` backward from
    EOF in 64 KB chunks and restores `reference/orchestrator.md` for the main orchestrator — or
    `reference/worker.md` for explicitly dispatched native `worker` subagents — when a `CHECKPOINT`
    is newer than the last matching DevStandard `SYSTEM_MESSAGE`, while keeping reviewers,
    `research` subagents, task-local helpers, and ordinary turns at `{}`.
  - `PreToolUse` (`hooks/pre-tool-use`, `scripts/hard_edges.py`): dual-protocol command word-guard
    parsing both Antigravity camelCase `toolCall` JSON and Codex snake_case `tool_name` JSON.
- **Concise role maps and hygiene guides (`reference/`):** single-reader role maps
  (`orchestrator.md`, `worker.md`, `reviewer.md`), executor guides (`harness-codex.md`,
  `harness-antigravity.md`), canonical repository documentation norms (`in-repo-writes.md`), file
  placement rules (`where-it-goes.md`), and trigger-loaded templates (`prd.md`, `architecture.md`,
  `adr.md`, `design-spec.md`, `repo-agents-md.md`, `ci-pipelines.md`, `ci-cannot-run.md`,
  `red-check.md`, `deployments.md`).
- **Dual executor implementations:** OS-sandboxed **Codex CLI (`--implementation codex`)** processes
  and **native Antigravity subagents (`--implementation agy`)** via `invoke_subagent` and
  `send_message`.
- **Deterministic scripts (`scripts/`):** `scripts/dispatch` (lane lifecycle and unified
  `# Task packet` assembly), `scripts/review-packet` (stateless green-PR review assembly,
  publication of `## Code Review — round N`, and 2-round convergence warnings), and `scripts/guard`
  (branch-protection audit, pure git-tree rebase equality proof, and reviewed-head squash merge).

**Context engineering.** Each role receives one concise (~100–220 line), self-contained navigation
map tailored to its authority. Orchestrator harness mechanics never pollute worker or reviewer
prompts, external craft plugins are unnecessary, and supporting reference pages load only when
their specific trigger fires.

## 6. Success criteria

Success means the problems of section 1 no longer occur:

1. **The human directs rather than schedules:** parallel lanes advance concurrently while human
   attention stays on intent, option tradeoffs, architecture calls, and irreversible authorizations.
2. **Every merged change carries final-state proof and independent verification:** completion
   claims are backed by rebased `Done-check` outputs, green `merged-result` CI, and an active
   `Approve` review on the exact head (or pure conflict-free rebase tree match).
3. **Zero unauthorized irreversible actions or silent monkey-patches occur.**
4. **Reviews protect the core and converge quickly:** `Notes` never force rework, `Blocking` items
   isolate real defects, and non-converging lanes escalate after 2 rounds instead of drifting.
5. **Conventions and role boundaries survive fresh sessions and compactions** for both the
   orchestrator and long-running native workers, without committed `SUMMARY.md` / `HANDOFF.md` junk
   or per-PR version conflicts.
6. **The method stays readable end-to-end:** every page and script traces directly to §1 or §2.

## 7. Boundaries

- **Supplies only the collaboration layer** above the host harness, git, and GitHub.
- **Pragmatic engineering over perfectionism:** acceptance requires sound, proportional goal
   fulfillment within `Bounds`, and audits explicitly leave tolerable minor issues alone when a fix
   would introduce heavier complexity or risk than the defect itself.
- **High-trust principles + minimal hard guardrails:** mechanical enforcement is reserved for
   high-cost boundaries; everyday engineering judgment uses directional principles rather than
   incident-accreted word bans or ceremony.
- **Self-contained without external skill-plugin lock-in:** core engineering habits live concisely
   inside the role maps rather than binding external skill libraries.
- **Release is human-gated and versioned at release time:** ordinary PRs do not bump version
   manifests; shipping tags wait for explicit human authorization (unless standing release
   delegation is granted for a specific repository).

**Existence criterion:** every rule, file, and mechanism in this supplementary harness must trace
back to a problem in section 1 or a reuse decision in section 2; whatever cannot be traced is to be
deleted.
