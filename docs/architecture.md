# DevStandard-Antigravity — Collaboration-Model Architecture

> Shared baseline for all parallel work in DevStandard-Antigravity. Read before any task.
> Changing anything here touches the core: public merge + human approval + an ADR.

This document defines the supplementary harness required by the three target workflows in PRD §4. It
defines the roles, context boundaries, delivery paths, enforcement points, and concurrency behavior
from which DevStandard-Antigravity (`devstandard-agy`) is implemented. Every structure named here is
traced to a PRD §1 pain point or a PRD §2 reuse decision in the closing table.

Delivery and enforcement statements use two labels:
- **Verified**: the behavior was measured or the artifact was inspected, naming its source.
- **Unverified**: the architecture requires the behavior but has not demonstrated it on a given host.

---

## 1. Scope and Configuration

The supported configuration is **one Antigravity orchestrator** session with **N dispatched
executors**. A dispatched executor has one of two purposes: **worker** or **reviewer**. A conflict
resolver is a worker assigned a conflict task, not a third role. This is the smallest configuration
that removes scheduling from the human while retaining the GitHub flow and native isolation
mechanisms (PRD §1.1, §2.1, §2.2).

```
                      +-----------------------------+
                      |     Human Developer        |
                      +--------------+--------------+
                                     | Direction & Decisions
                                     v
                      +-----------------------------+
                      |   Antigravity Orchestrator  |
                      |   (Main Session: `agy`)     |
                      +--------------+--------------+
                                     | Dispatches N parallel lanes
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+------------------+                                    +------------------+
| Codex CLI        |                                    | Native Subagent  |
| Worker/Reviewer  |                                    | Worker/Reviewer  |
| (`workspace-     |                                    | (`invoke_        |
|  write` sandbox) |                                    |   subagent`)     |
+------------------+                                    +------------------+
         |                                                       |
         +---------------------------+---------------------------+
                                     |
                                     v
                       GitHub (Issue / PR / CI / Merge)
```

DevStandard is a supplementary harness. The host (Antigravity) owns its sessions, subagent
invocations, tools, and permissions. Dispatched Codex CLI processes also own their OS-level sandboxes
(`bubblewrap` on Linux). DevStandard supplies the missing collaboration protocol: role context,
dispatch, acceptance, and transitions between GitHub artifacts (PRD §1.1, §1.5).

**It governs one layer: collaboration with GitHub** — issue, lane, PR, review, merge — and nothing
below a role. What a dispatched role spawns beneath itself touches none of those artifacts; this
design requires only that one accountable author hands back one PR.

The durable coordination state is GitHub: issues declare work, branches and worktrees isolate it,
PRs deliver it, review records acceptance, and CI plus branch protection gate integration. Native
task handles, process IDs, and output files are transient observations, not a second state machine
(PRD §2.1, §2.2).

---

## 2. Roles and Context Sets

### 2.1 Orchestrator

The orchestrator converses with the human, completes an issue with settled results and bounds after
human confirmation, partitions concurrent work, dispatches executors, observes delivery, assembles
acceptance reviews, merges accepted work, and performs cleanup and delegated release.

Its context set contains:
- the workflow contract and the three events that wait on the human (irreversibles, architecture
  direction, major release);
- open-issue, open-PR, CI, branch, and worktree state needed to run the main loop;
- dispatch, acceptance, merge, cleanup, and reporting triggers with pointers to operative procedures;
- requirements-clarification skill bindings from superpowers; and
- the rule that implementation craft and worker task-local procedures are not loaded into the
  orchestrator context.

### 2.2 Dispatched Executor: Purpose × Implementation

There is one dispatched-executor construct. Purpose determines context and authority; implementation
determines how that context is delivered:

| Purpose | Codex CLI (`--implementation codex`, default) | Native Antigravity Subagent (`--implementation agy`) | Result |
|---|---|---|---|
| **Worker** | Dispatch supplies shared role plus `reference/harness-codex.md` worker section, task packet, explicit settings, and an OS sandbox (`workspace-write`) granting the worktree and linked git metadata. | Dispatched via `invoke_subagent` with `Role="Issue <N> worker"` and the prepared model (`inherit` by default). Brief contains shared worker role, `reference/harness-antigravity.md`, and task packet. Continuation via `send_message`. | A green PR linked to the issue, rebased on current `main`, with final-state evidence. |
| **Reviewer** | Dispatch supplies judging contract and packet in an independent one-off checkout of the pinned head, with `workspace-write`, network, and a grant only to the copy's Git metadata. | Dispatched via `invoke_subagent` with `Role="Issue <N> reviewer"` and the prepared model (`inherit` by default). Pinned judging contract, empty skills, read-only by written contract toward repository and remote. Returns verdict via `send_message`. | A verdict naming reviewer and reviewed head, published whole by the caller; reviewer never alters the repository or remote. |

### 2.3 Worker Context Set

The worker set consists of the static role plus one dynamic task packet:
- **Static role:** binds the worker to PRD §4 Workflow 3: one issue, branch, and worktree; write
  authority restricted to that lane; evidence and attribution duties; NEVER and escalation boundaries;
  and execution-skill triggers (TDD, systematic debugging).
- **Task packet:** supplies freshly fetched issue details (body and comments), named base, branch,
  worktree, required inputs, and expected output. It carries no merge, release, or orchestration
  procedures.

### 2.4 Reviewer Context Set

Reviewer is the read-only purpose of the dispatched-executor family:
- **Judging contract:** Goal verdict first, two-check Floor second, Notes last
  (`reference/code-review-prompt.md`). Only the Goal verdict and Floor decide readiness; Notes neither
  block nor trigger re-review.
- **Read-only authority:** no comments, PR/issue edits, pushes, or remote state changes. The caller
  publishes the unedited verdict.

### 2.5 Resolver

A resolver is a worker assigned to rebase a delivered branch that conflicts with current `main`. It
receives the ordinary worker set plus the delivered PR, old and new bases, conflicting paths, and the
original issue contract. It runs only in that lane, reruns done-checks on the resolved final state,
republishes evidence, and returns the head for fresh review. It never receives merge authority.

---

## 3. Context Delivery

Static role content has one operative source per role:
- Orchestrator: `reference/orchestrator.md`
- Worker: `reference/worker.md` plus host mechanics (`reference/harness-antigravity.md` or
  `reference/harness-codex.md`)
- Reviewer: `reference/code-review-prompt.md`

### 3.1 Antigravity Context Delivery Across Compactions

Antigravity loads the orchestrator context through its native plugin system:
1. `hooks.json` declares `SessionStart` pointing to `hooks/session-start` and `PreInvocation`
   pointing to `hooks/session-start --pre-invocation`.
2. Antigravity fires `SessionStart` at initialization of a new session
   (`InvocationNum == 0 && InitialNumSteps == 0`).
3. Before later invocations, `PreInvocation` reads `transcriptPath` (`transcript.jsonl`). It restores
   context only when the latest `CHECKPOINT` step is newer than the last DevStandard `SYSTEM_MESSAGE`
   step (identified by the orchestrator-context preamble or missing-page stop warning).
4. Both delivery paths inject `reference/orchestrator.md` whole, with a plugin-root preamble, in a single
   `injectSteps` step: `{"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}`.
5. If the page cannot be read when delivery is needed, the same structure delivers a stop warning
   naming the missing role context. A warning after the latest checkpoint also prevents duplicate delivery.
6. `PreInvocation` emits `{}` when the transcript is unavailable, contains no checkpoint, or already
   has DevStandard context after its latest checkpoint; blank or malformed JSONL records are ignored.
7. In both modes, `hooks/session-start` first identifies subagents via
   Antigravity's `.system_generated/subagents/<conversationId>.json` registry (or `DEVSTANDARD_ROLE` /
   `agent_type` / non-empty `parentConversationId`) and emits `{}` without injecting
   `reference/orchestrator.md`, preventing context pollution and duplicate competing roles.

[ADR 0002](adr/0002-post-compaction-orchestrator-context-re-injection.md) records why the full role
page is restored after each compaction instead of relying on a checkpoint summary or read notice.

### 3.2 Worker & Reviewer Delivery

- **Native Antigravity Subagent (`--implementation agy`)**: Orchestrator unpacks `agent-spawn.json`
  into `invoke_subagent(TypeName=spawn["type_name"], Role=spawn["role"], Model=spawn["model"], Prompt=spawn["prompt"])`
  (`reference/harness-antigravity.md`). The role is `Issue <N> worker` or `Issue <N> reviewer` for
  registry detection, and the model preserves dispatch overrides. The worker brief is injected into
  the initial prompt; the worker replies or escalates via `send_message`.
  Orchestrator receives wakeups reactively without polling.
- **Codex CLI (`--implementation codex`)**: `scripts/dispatch` passes the worker/reviewer brief on
  stdin. Worker operates within its assigned worktree under an OS sandbox.

---

## 4. Dual-Protocol PreToolUse Guard

To prevent catastrophic operations across heterogeneous executors, `hooks/pre-tool-use` serves as an
active command-line guard.

### 4.1 Protocol Normalization

Different harnesses deliver tool invocations in different JSON formats:

- **Antigravity protocol:** camelCase JSON:
  ```json
  {
    "toolCall": {
      "name": "run_command",
      "args": {
        "CommandLine": "git merge feature-branch"
      }
    }
  }
  ```
  The primary command field is `toolCall.args.CommandLine`; `toolCall.arguments` is accepted as a
  fallback when `toolCall.args` is absent or null, with the same `CommandLine` field.
- **Codex protocol:** snake_case JSON:
  ```json
  {
    "tool_name": "exec_command",
    "tool_input": {
      "cmd": "git merge feature-branch"
    }
  }
  ```

`hooks/pre-tool-use` parses both shapes transparently, extracting the raw command text regardless of
the caller's protocol.

### 4.2 Word-List Refusals

The guard evaluates command text against whole-word rules based on the active role (passed via
environment variable `DEVSTANDARD_ROLE`, detected from `agent_type`, or resolved for native Antigravity
subagents from Antigravity's `.system_generated/subagents/<conversationId>.json` registry):

| Role | Blocked Command Patterns | Rationale & Route |
|---|---|---|
| **Worker** | `merge`, `git merge`, direct push to default branch (`git push origin main`, `git push origin master`) | Workers must never integrate code directly or push to protected branches; they rebase and deliver PRs. |
| **Orchestrator** | `gh pr merge` | Direct PR merges bypass acceptance verification; orchestrator must route through `scripts/guard merge`. |
| **Reviewer** | `gh api` with write flags (`-X POST`, `-X PUT`, `-X PATCH`, `-X DELETE`, `--field`, `-f`, `-F`) | Reviewers are strictly read-only toward GitHub and the repository remote. |

When a command is refused, the hook exits `0` and emits structured JSON:

- **Antigravity:** `{"decision": "deny", "reason": ...}`; an admitted call emits `{"decision": "allow"}`.
- **Codex:** `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": ...}}`; an admitted call emits `{}`.

The refusal reason names the triggering word/pattern, the role's next step, and the reference page
explaining the rule.

---

## 5. Workflow Edges and Enforcement Tiers

Enforcement is categorized into three tiers:
- **Hard:** A native mechanism or script mechanically refuses the action (e.g. guard script, branch
  protection, OS sandbox).
- **Structural:** The harness places required context or a fixed transition at the act site (e.g.
  worktree creation, review packet assembly, prompt injection).
- **Soft:** The role instruction requires model judgment where decisions cannot be mechanized.

### Workflow 1: Lifecycle of One Task

| Step / Edge | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Discussion → Complete Issue | **Structural:** Orchestrator context supplies issue fields and superpowers requirements-skill trigger. **Soft:** Human confirms settled result and reason; orchestrator establishes scope and done-check. | **Verified:** PRD §4.1; triggers in `reference/orchestrator.md`. |
| Issue → Dispatch (Workflow 3) | **Hard:** `scripts/dispatch` refuses missing issue, base, branch, or worktree. **Structural:** Injected brief points to specification check. **Soft:** Worker evaluates whether goal or done-check is underspecified before starting. | **Verified:** `scripts/dispatch` lane validation; `.github/test-dispatch.py`. |
| Dispatch → Isolated Lane | **Hard:** Codex CLI bubblewrap sandbox (`workspace-write`). **Structural:** Dedicated git worktree per lane. **Soft:** Worker respects assigned worktree boundary. | **Verified:** Codex bubblewrap sandbox; git worktree isolation. |
| Implementation → Green PR | **Hard:** `scripts/review-packet` refuses acceptance if PR CI is red or unreported. **Structural:** Role brief binds TDD and systematic debugging. **Soft:** Implementation choices and proof evidence accuracy. | **Verified:** `scripts/review-packet` green-head admission; `.github/test-review-packet.py`. |
| Delivered PR → Acceptance | **Hard:** Assembler refuses unverified or red PRs; Codex CLI reviewer sandbox isolates writes to its disposable checkout and metadata; `PreToolUse` refuses reviewer `gh api` write flags on both executors. **Structural:** Independent pinned checkout for CLI reviewer; complete Goal/Floor/Notes packet. **Soft:** Native reviewer repository/remote read-only authority is a written role contract; reviewer judges goal fulfillment and evidence validity. | **Verified:** `scripts/review-packet`; `reference/harness-codex.md`; `hooks/pre-tool-use`; Goal/Floor/Notes contract. |
| Accepted Head → Merge & Cleanup | **Hard:** Branch protection blocks direct main pushes; `scripts/guard merge` verifies exact accepted head or content-unchanged rebase proof. **Structural:** Architecture-level flag in review packet. **Soft:** Human sign-off on architecture changes. | **Verified:** `scripts/guard merge`; `.github/test-hard-edges.py`. |
| Merged Result → Release | **Structural:** Standing repo release delegation; version lockstep in `plugin.json`. **Soft:** Human authorization for major releases. | **Verified:** Repo release delegation; `AGENTS.md`. |

### Workflow 2: Orchestrator Events

| Event | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Human speaks | **Soft:** Orchestrator converses, creates issues, adjusts direction. **Structural:** Role context supplies issue templates. | **Verified:** `reference/orchestrator.md`. |
| Irreversible action needed | **Hard:** `hooks/pre-tool-use` refuses `gh pr merge`; branch protection protects main. **Soft:** Orchestrator stops and requests human authorization for irreversible actions outside hook word lists. | **Verified:** `hooks/pre-tool-use`; `scripts/guard`. |
| Architecture direction / Major release ready | **Structural:** Role context forbids merging architecture changes without human approval. **Soft:** Orchestrator stops and requests human decision. | **Verified:** `reference/orchestrator.md`. |
| Ready issues await dispatch | **Hard:** Dispatcher creates isolated branches and worktrees. **Structural:** Orchestrator dispatches N parallel lanes. | **Verified:** `scripts/dispatch`. |
| Worker delivers | **Structural:** Orchestrator inspects PR and CI status; initiates review only on green PR. | **Verified:** `scripts/review-packet`. |
| Verdict returns | **Hard:** `scripts/guard merge` blocks unaccepted heads. **Structural:** Goal Yes advances toward merge; Goal No returns to worker with round accounting; conflict dispatches resolver. | **Verified:** `scripts/review-packet` round accounting; `scripts/guard merge`. |
| Main goes red | **Structural:** Role context freezes new dispatch; prioritizes revert-first. | **Verified:** `reference/orchestrator.md`. |
| Idle | **Structural:** Sweeps abandoned worktrees and reports status. | **Verified:** Main loop specification. |

### Workflow 3: Worker Execution

| Step | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Specification check | **Structural:** `scripts/dispatch` injects the freshly fetched issue body and comments. **Hard:** `scripts/review-packet` validates structured issue fields at review assembly. **Soft:** Worker checks that Goal, Bounds, and Done-check are specified before starting and returns a vague or incomplete task. | **Verified:** `scripts/dispatch`; `scripts/review-packet`; `reference/worker.md` specification check. |
| Taking position | **Hard:** Codex bubblewrap sandbox limits filesystem access. **Structural:** Dedicated worktree. | **Verified:** Worktree creation; sandbox configuration. |
| Implementation | **Structural:** Role binds TDD and systematic debugging skills. **Soft:** Worker focuses strictly on issue bounds. | **Verified:** Superpowers bindings in role brief. |
| Stop events (core architecture, irreversible, done-check invalid, direction call) | **Hard:** `hooks/pre-tool-use` blocks prohibited words. **Structural:** Worker stops and escalates to orchestrator via issue comment or output. | **Verified:** Worker stop triggers; `hooks/pre-tool-use`. |
| Rebase onto main | **Structural:** Worker rebases and resolves own conflicts before handback. **Hard:** `scripts/guard merge` enforces that merged head is rebased onto current main. | **Verified:** `scripts/guard merge` rebase check. |
| Final-state done-check | **Structural:** Worker runs done-check on final rebased state and records exit codes and outputs. **Hard:** CI verifies mechanical test assertions. | **Verified:** PR evidence template; CI test run. |
| PR & Green CI | **Hard:** `scripts/review-packet` refuses acceptance if CI checks are red. | **Verified:** `scripts/review-packet` admission gate. |
| Handback | **Hard:** Worker hook refuses `merge`. **Structural:** Worker hands back PR to orchestrator; leaves worktree for cleanup at merge. | **Verified:** Role hook; worktree cleanup lifecycle. |

---

## 6. Concurrency and Review Convergence

### 6.1 Parallel Lanes

N-way dispatch executes across N issue/branch/worktree lanes under one Antigravity orchestrator.
Scopes are partitioned to minimize file overlap. Worktrees physically isolate checkouts. Codex CLI
sandboxes isolate process writes; native subagents run in isolated tool-use frames. GitHub serves as
the queue and durable record (PRD §1.1, §2.1, §2.2).

### 6.2 Reactive Wakeup and Non-Blocking Loop

The Antigravity orchestrator operates as a non-blocking event handler:
- Dispatched CLI processes run as background tasks or subprocesses; completion notifications wake the
  orchestrator.
- Native subagents run asynchronously; completions trigger `send_message` wakeups.
- The orchestrator context does not poll in a sleep loop. It handles arriving events immediately and
  resumes conversation with the human.

### 6.3 Review Convergence and Round Accounting

To prevent multi-round goal drift (PRD §1.4):
- Reviewers rule strictly on **Goal** fulfillment, **Floor** checks (evidence and boundaries), and
  advisory **Notes**.
- Peripheral issues are recorded as Notes and never trigger a re-review round.
- If a goal is not met, the return packet isolates the specific missing outcome; the worker fixes only
  the named gap.
- Every round is recorded on the PR (`scripts/review-packet start`) before review execution begins,
  ensuring visible accounting.

---

## 7. Traceability Matrix

| Architectural Mechanism | PRD §1 Problem Addressed | PRD §2 Reuse Decision |
|---|---|---|
| Antigravity orchestrator + N dispatched workers | §1.1 Human scheduling bottleneck | §2.1 GitHub collaboration flow |
| Git worktrees & Codex OS sandbox (`workspace-write`) | §1.5 Missing conventions; write safety | §2.2 Git worktrees & OS sandboxes |
| SessionStart delivery + PreInvocation `injectSteps` restoration after a newer `CHECKPOINT` than the last DevStandard `SYSTEM_MESSAGE` | §1.5 Working conventions forgotten | Native Antigravity plugin architecture |
| Dual-protocol PreToolUse word-guard | §1.3 Irreversible operations | Antigravity & Codex tool-use hooks |
| Superpowers role-bound skills (TDD, Debugging) | §1.2 Untrustworthy claims; core quality | §2.3 Superpowers craft library |
| Goal/Floor/Notes review contract | §1.4 Multi-round goal drift & core erosion | GitHub PR reviews |
| `scripts/guard merge` reviewed-head & rebase proof | §1.2 Untrustworthy completion claims | §2.1 GitHub CI & branch protection |
| Two separate context sets (orchestrator vs worker) | §1.6 Rules accretion & context pollution | Context engineering separation |
