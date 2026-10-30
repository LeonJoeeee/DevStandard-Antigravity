# DevStandard-Antigravity — Collaboration-Model Architecture

> Shared baseline for all parallel work in DevStandard-Antigravity. Read before starting a task.
> Changes to this baseline require a public merge, human approval, and an ADR.

This document defines the supplementary harness implementing the three target workflows in
[PRD §4](PRD.md#4-the-solution-the-target-workflows). It specifies the roles, context boundaries,
delivery paths, mechanical guards, stateless review/merge gates, and concurrency behavior of
DevStandard-Antigravity (`devstandard-agy`). Every structure named here traces to a PRD §1 problem
or a PRD §2 reuse decision in §7.

Delivery and enforcement statements use two labels:
- **Verified**: the behavior was measured or tested directly against the shipped implementation.
- **Unverified**: the architecture requires the behavior without automated runtime verification here.

---

## 1. Scope and Configuration

The supported configuration is **one Antigravity orchestrator** session directing **N dispatched
executors**. Each dispatched executor serves one of two purposes: **worker** or **reviewer** (a
conflict resolver is a worker assigned a conflict task, not a third role). This is the smallest
structure that removes manual lane scheduling from the human while reusing the GitHub collaboration
flow, git worktrees, and OS/host isolation (PRD §1.1, §2.1, §2.2).

```
                      +-----------------------------+
                      |     Human Developer         |
                      +--------------+--------------+
                                     | Direction, Tradeoffs & Authorization
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
                       GitHub (Issue / PR / Review / CI / Merge)
```

DevStandard is a supplementary harness ([ADR 0001](adr/0001-antigravity-host-with-native-and-codex-executors.md),
[ADR 0003](adr/0003-harness-engineering-alignment-and-streamlined-gates.md)). Antigravity owns
sessions, native subagent execution, tools, and permissions; Codex CLI owns its OS-level sandbox
(`bubblewrap` / AppArmor on Linux). DevStandard supplies the collaboration layer above them: concise
single-reader role maps, isolated lane dispatch, independent code review, guarded merge, and
canonical file hygiene (`reference/in-repo-writes.md`, `reference/where-it-goes.md`).

**GitHub holds durable coordination state:** issues define `Goal` / `Bounds` / `Done-check` and
record `devstandard-dispatch-v1` lane receipts; branches and worktrees isolate edits; PRs carry
final-state proof; `## Code Review — round N` comments record verdicts; and CI plus branch
protection gate integration. Local scratch directories, process IDs, and subagent handles are
transient execution state, never a competing state machine.

---

## 2. Roles and Context Sets

Each role reads a single concise (~100–220 line), self-contained navigation map with internalized
engineering craft and zero external skill-plugin dependencies ([ADR 0003](adr/0003-harness-engineering-alignment-and-streamlined-gates.md)).

### 2.1 Orchestrator (`reference/orchestrator.md`)

The orchestrator converses with the human (`Restate before acting`), shapes feature design (gauging
input clarity and running concurrent non-blocking read-only research into existing repo capabilities
and mature open-source packages) and bug/audit decisions (tracing root causes, siblings, cost of
inaction, and fix-induced complexity before judging worthiness), compares viable options neutrally
before recommending, prepares proportional leaf issues, dispatches lanes, coordinates stateless
acceptance reviews, enforces the 2-round convergence rule, runs guarded merges, cleans up lanes, and
handles release-time versioning.

Its context set contains:
- authority boundaries (`Looking needs no permission; doing always does`, `hold` / `delegated`,
  mandatory `Restate before acting`, explicit human consent before irreversible actions or
  monkey-patching third-party internals);
- the non-blocking event loop and machine-parsed model-routing tables (`worker >= reviewer`:
  `gpt-6.1-sol` at `xhigh` / `high` on Codex, `inherit` on Antigravity; native task-local helper
  defaults);
- workflow triggers and pointers to `scripts/dispatch`, `scripts/review-packet`, `scripts/guard`,
  and trigger-loaded `reference/*.md` guides (`harness-codex.md`, `harness-antigravity.md`,
  `in-repo-writes.md`, `where-it-goes.md`, `prd.md`, `architecture.md`, `adr.md`, `design-spec.md`,
  `repo-agents-md.md`, `ci-pipelines.md`, `ci-cannot-run.md`, `red-check.md`, `deployments.md`).

### 2.2 Dispatched Executor: Purpose × Implementation

Purpose determines authority and role map; `--implementation` determines transport and isolation:

| Purpose | Codex CLI (`--implementation codex`, default) | Native Antigravity Subagent (`--implementation agy`) | Deliverable |
|---|---|---|---|
| **Worker** | `scripts/dispatch` feeds `reference/worker.md` + `# Task packet` (`Environment:`, `Helpers:`, `Commit trailer:`) to `codex exec` (`gpt-6.1-sol` at `xhigh`) in `workspace-write` sandbox rooted at the worktree with `--add-dir` grants for `--git-common-dir` and `--git-dir`. | `scripts/dispatch` writes `agent-spawn.json` (`Role="Issue <N> worker"`, `Model="inherit"` default) with `reference/worker.md` + `# Task packet`. Spawned via `invoke_subagent`, continued via `send_message`, and restored on compaction via `PreInvocation`. | A green, rebased PR linked to the issue with final-state `Done-check` evidence and an empty `git status --porcelain -uall`. |
| **Reviewer** | `scripts/review-packet start --wait` invokes `scripts/dispatch` (`gpt-6.1-sol` at `high`) in an independent disposable `--no-local` clone of `HEAD_SHA` (`--add-dir` only to the clone's separate Git dir), validates the returned verdict, and posts one `## Code Review — round N` comment. | `scripts/review-packet start --implementation agy` writes `packet.json`, `packet.txt`, `attempt.json`, and `agent-spawn.json` (`Role="Issue <N> reviewer"`, `Model="inherit"` default) pointing to `brief.txt` (9-slot `reference/reviewer.md` + 3-form `## Pinned Git evidence` + `# Task packet`). Caller publishes via `scripts/review-packet publish`. | A validated whole verdict (`Approve` or `Request changes`, `### Blocking`, `### Notes`) on the exact `HEAD_SHA`, with zero repository or remote mutations by the reviewer. |

### 2.3 Worker Context Set (`reference/worker.md`)

The worker receives `reference/worker.md` plus a dynamic `# Task packet` assembled by `scripts/dispatch`:
- **Static role (`reference/worker.md`):** `1 issue = 1 branch = 1 worktree = 1 green, evidence-bearing PR`;
  `### Never` boundaries; lane & baseline verification; internalized `## 3. Execution craft`
  (proportional scratch planning, fail-before-pass reproduction, root-cause and sibling tracing,
  public-API-first reuse, weighing fix-induced complexity); final-state rebase & clean-tree rules
  (no per-PR version bumps); and escalation / review-continuation / harness-limit rules.
- **Dynamic `# Task packet`:** `Issue`, `Branch`, `Worktree`, `Named base`, `Role references resolve from`,
  verbatim issue body and ordered non-dispatch comments, optional `PR` and `Inputs and expected output` /
  `Continuation brief`, `Executor`, `Record language`, `Commit trailer`, concise `Environment:` line,
  and machine-derived `Helpers:` routing line. No orchestrator harness pages are spliced in.

### 2.4 Reviewer Context Set (`reference/reviewer.md`)

`reference/reviewer.md` is a direct 9-slot Senior Code Reviewer prompt (no outer code fence or
orchestrator preamble):
- **Targeted active verification within three hard red lines:** beyond static reading, reviewers run
  focused commands and edge-case probes when needed to verify runtime behavior, callers, or claimed
  `Done-check` proofs, placing any temporary files strictly inside an isolated `mktemp -d` under
  `/tmp` (or session scratch / disposable CLI review clone) while obeying three hard red lines:
  (1) never touch repository worktrees or refs, (2) never write to GitHub or remotes, and (3) never
  trigger external or live side effects.
- **Two-tier verdict contract:** opens with `Reviewer: {REVIEWER_IDENTITY} — reviewed {HEAD_SHA}`,
  followed by `### Verdict` (`Approve | Request changes` with summary grounds), `### Blocking`
  (`None.` on `Approve`, or numbered concrete defects with `[Needs human decision]` when scope or
  irreversible authorization is implicated), and `### Notes` (non-blocking observations / `Nit:`
  items that never block merge or trigger re-review).

### 2.5 Resolver

A conflict resolver is a worker continued or dispatched to rebase a branch that conflicts with
current `main`. It resolves conflicts within the lane, reruns `Done-check` on the final state, and
hands back the updated head for fresh code review; it never merges.

---

## 3. Context Delivery

Static role prompts live at one canonical file per role:
- Orchestrator: `reference/orchestrator.md`
- Worker: `reference/worker.md`
- Reviewer: `reference/reviewer.md`

Orchestrator-only executor guides live separately in `reference/harness-codex.md` and
`reference/harness-antigravity.md`.

### 3.1 Antigravity Context Delivery Across Compactions (`hooks/session-start`)

Antigravity delivers and restores role context via `hooks.json` ([ADR 0002](adr/0002-post-compaction-orchestrator-context-re-injection.md)):

1. **`SessionStart` (`./hooks/session-start`):** fires at top-level session initialization and
   injects `reference/orchestrator.md` whole (with a plugin-root preamble) in a single
   `{"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}` step. All subagents (identified via
   `DEVSTANDARD_ROLE`, `agent_type`, `.system_generated/subagents/<conversationId>.json`, or
   `parentConversationId`) emit `{}` because `scripts/dispatch` delivers their initial prompt.
2. **`PreInvocation` (`./hooks/session-start --pre-invocation`):** runs before later turns and
   determines the target role via `target_role_relpath()`:
   - Main orchestrator session → `reference/orchestrator.md`.
   - Explicitly dispatched native `worker` subagent (`agent_type` in `('worker', 'devstandard:worker')`
     when `DEVSTANDARD_ROLE` is unset, or `subagent_role(event, strict=True) == 'worker'` from
     `.system_generated/subagents/<conversationId>.json`) → `reference/worker.md`, with a worker
     preamble instructing recovery of dynamic `# Task packet` fields from the issue's
     `devstandard-dispatch-v1` receipt or local transcript.
   - CLI roles (`DEVSTANDARD_ROLE`), reviewers, `research` subagents, untyped task-local helpers
     (`strict=True -> 'helper'`), and unrecognized `parentConversationId` sessions → suppressed (`{}`).
3. **Byte-safe reverse-tail transcript scan (`needs_context()`):** validates that `transcriptPath`
   is a regular file and scans backward from EOF in 64 KB chunks (`TRANSCRIPT_CHUNK_BYTES = 65536`),
   carrying partial leading line bytes across chunk boundaries before UTF-8 decoding. Inspecting
   valid JSON object records from newest to oldest, it returns `True` immediately on `CHECKPOINT`,
   `False` immediately on a `SYSTEM_MESSAGE` carrying `DevStandard operating context: <role_relpath>`
   or the missing-page stop warning, and `False` if BOF is reached without a `CHECKPOINT`.

### 3.2 Worker and Reviewer Packet Assembly (`scripts/dispatch` & `scripts/review-packet`)

- **Worker dispatch:** `scripts/dispatch` validates the target checkout, issue, explicit named base,
  and linked worktree (`.agents/worktrees/<issue>-<slug>`), writes `brief.txt` (`reference/worker.md`
  + `# Task packet`), records a `devstandard-dispatch-v1` receipt on the issue, and either runs
  sandboxed `codex exec` (`--wait`) or writes `agent-spawn.json` (`--implementation agy`).
- **Reviewer assembly & dispatch:** `scripts/review-packet` (`scripts/review_packet.py`) verifies
  all observed and required PR checks are green, fills the 9 slots of `reference/reviewer.md`,
  appends `## Packet integrity`, the quoted issue body, optional `rebase_result`, and verbatim
  `prior_verdicts`, and invokes `scripts/dispatch --purpose reviewer`. For `--implementation agy`,
  `scripts/dispatch` appends `## Pinned Git evidence` containing the three canonical diff forms
  (`--name-status`, `--stat`, and full `diff` across `REVIEW_BASE_SHA..HEAD_SHA`) without redundant
  per-file blob dumps.

---

## 4. Dual-Protocol PreToolUse Guard

`hooks/pre-tool-use` and `scripts/hard_edges.py` provide deterministic command-word refusals across
both Antigravity and Codex CLI tool protocols.

### 4.1 Protocol Normalization and Fail-Open Safety

- **Antigravity protocol:** camelCase JSON (`toolCall.name == "run_command"`, reading
  `toolCall.args.CommandLine` with fallback to `toolCall.arguments.CommandLine`), emitting
  `{"decision": "deny", "reason": ...}` or `{"decision": "allow"}`.
- **Codex protocol:** snake_case JSON (`tool_name` in `("Bash", "exec_command")`, reading
  `tool_input.command` or `tool_input.cmd`), emitting `hookSpecificOutput` `permissionDecision: "deny"`
  or `{}`.
- Non-shell tools (such as `write_file`, `edit_file`, `apply_patch`) are always admitted so prose
  containing guarded words never blocks file edits. Quoted strings and heredoc bodies are stripped
  via `command_only()` before whole-word scanning, and malformed hook events fail open to stderr
  rather than wedging lanes.

### 4.2 Role Resolution and Refusal Rules

`hooks/pre-tool-use` resolves the active role from `--role`, `DEVSTANDARD_ROLE`,
`subagent_role(event)` (`strict=False`, so untyped task-local helpers safely inherit `worker`
refusals while `research` children keep their parent role), `agent_type`, or untyped `agent_id`:

| Role | Refused Shell Patterns | Rationale & Redirect |
|---|---|---|
| **Worker** | Whole-word `merge`; `push` also naming `main` or `master` | Workers never integrate code or push to protected branches; they push their task branch and hand back the PR (`reference/worker.md`). |
| **Orchestrator** | `gh pr merge` | Direct merges bypass reviewed-head, rebase-proof, and `merged-result` verification; route through `<plugin>/scripts/guard merge` (`reference/orchestrator.md`). |
| **Reviewer** | `gh` commands carrying write flags (`-X`, `--method`, `-f`, `-F`, `--field`, `--input`) | Reviewers never write to GitHub or remotes; they return their whole verdict to the caller (`reference/reviewer.md`). |

---

## 5. Workflow Edges and Enforcement Tiers

Enforcement combines three tiers:
- **Hard:** Mechanical refusal by script, hook, OS sandbox, or GitHub branch protection.
- **Structural:** Context separation, worktree isolation, or deterministic packet/gate assembly.
- **Soft:** Engineering judgment guided by concise role principles.

### Workflow 1: Lifecycle of One Task

| Step / Edge | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Intake, Research & Option Shaping | **Structural:** `reference/orchestrator.md` mandates `Restate before acting`, feature vs. bug/audit intake, and neutral-first option comparison. **Soft:** Concurrent read-only subagent research into repo & mature OSS solutions; human confirms direction. | **Verified:** `reference/orchestrator.md` §1 & §3; `reference/adr.md`; `reference/design-spec.md`. |
| Issue → Isolated Lane Dispatch | **Hard:** `scripts/dispatch` enforces explicit base, linked `.agents/worktrees/<issue>-<slug>`, gitignore check, and Codex `workspace-write` sandbox. **Structural:** Unified `# Task packet` + `devstandard-dispatch-v1` receipt. | **Verified:** `scripts/dispatch`; `.github/test-dispatch.py`. |
| Implementation → Green PR | **Hard:** `hooks/pre-tool-use` blocks worker `merge` and `main`/`master` pushes; CI runs test suite and two-parent `merged-result` job. **Structural:** `reference/worker.md` internalizes craft and forbids per-PR version bumps. | **Verified:** `reference/worker.md`; `.github/workflows/ci.yml`; `.github/test-hard-edges.py`. |
| Green PR → Stateless Code Review | **Hard:** `scripts/review-packet` refuses red/pending/unreported checks, validates 9-slot `reference/reviewer.md`, isolates CLI reviewers in disposable clones, and blocks reviewer `gh` write flags. **Structural:** Stateless `start` / `publish` posts one `## Code Review — round N` comment on valid return. **Soft:** Reviewer runs targeted `/tmp` active verification within three hard red lines. | **Verified:** `scripts/review-packet`; `scripts/review_packet.py`; `.github/test-review-packet.py`. |
| Accepted Head → Guarded Merge & Cleanup | **Hard:** Branch protection blocks direct pushes; `scripts/guard merge` requires a valid `Approve` verdict (or human-authorized `merge-as-is` ruling), green `merged-result / BASE / HEAD`, and exact head or conflict-free git-tree equality (`compare_rebase`); `scripts/dispatch --cleanup` refuses dirty/unmerged lanes. | **Verified:** `scripts/guard`; `scripts/hard_edges.py`; `.github/test-hard-edges.py`; `.github/test-dispatch.py`. |
| Release-Time Versioning | **Structural:** Ordinary PRs leave version manifests untouched; releases bump versions in dedicated release PRs and tag after merge under human authorization or standing delegation. | **Verified:** `reference/orchestrator.md`; `reference/worker.md`; `scripts/guard`. |

### Workflow 2: Orchestrator Event Loop

| Event | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Human message arrives | **Soft:** Opens with `Restate before acting`; proposes before mutating state. | **Verified:** `reference/orchestrator.md` §1. |
| Irreversible action or monkey-patch | **Hard:** `PreToolUse` refuses `gh pr merge`. **Soft:** Stops for explicit human words before irreversible actions or private third-party monkey-patching. | **Verified:** `hooks/pre-tool-use`; `reference/orchestrator.md` §1 & §3. |
| Context compaction (`CHECKPOINT`) | **Hard:** `hooks/session-start --pre-invocation` reverse-scans `transcript.jsonl` and re-injects `reference/orchestrator.md` once per checkpoint. | **Verified:** `hooks/session-start`; `.github/test-session-start.py`. |
| Verdict returns (`Approve` / `Request changes`) | **Hard:** `scripts/review-packet` rejects malformed verdicts, blocks `Notes`-only re-reviews on accepted heads, warns at 2+ non-converging rounds, and requires `--human-authorization` for `merge-as-is`. | **Verified:** `scripts/review-packet`; `scripts/hard_edges.py`; `.github/test-review-packet.py`. |
| `main` goes red | **Structural:** Freezes new dispatch and prioritizes green restoration (`reference/red-check.md`, `reference/ci-pipelines.md`). | **Verified:** `reference/orchestrator.md` §2 & §4. |

### Workflow 3: Worker Execution

| Step | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Packet & lane validation | **Structural:** `# Task packet` supplies verbatim issue, ordered comments, base, branch, and worktree. **Soft:** Worker verifies lane git metadata and stops on missing/conflicting contracts or broken baselines. | **Verified:** `scripts/dispatch`; `reference/worker.md` §2. |
| Native worker compaction | **Hard:** `hooks/session-start --pre-invocation` restores `reference/worker.md` for dispatched native workers while keeping helpers/reviewers suppressed. | **Verified:** `hooks/session-start`; `.github/test-session-start.py`. |
| Craft, boundaries & hygiene | **Hard:** Codex OS sandbox + `PreToolUse` word-guard + CI canonical-doc assertions. **Structural:** `reference/in-repo-writes.md` and `reference/where-it-goes.md` prevent `SUMMARY.md` / `HANDOFF.md` junk and unauthorized host writes. | **Verified:** `reference/worker.md` §3; `reference/in-repo-writes.md`; `reference/where-it-goes.md`; `.github/workflows/ci.yml`. |
| Final rebase, proof & handback | **Hard:** `scripts/guard merge` requires current `main` ancestry and `merged-result` CI; `scripts/review-packet` gates on green PR checks. | **Verified:** `reference/worker.md` §4; `scripts/guard`; `scripts/review-packet`. |

---

## 6. Concurrency and Review Convergence

### 6.1 Conflict-Free Parallel Lanes

N parallel lanes execute across isolated `.agents/worktrees/<issue>-<slug>` checkouts under one
orchestrator. Release-time versioning eliminates artificial manifest/badge conflicts across
concurrent branches, allowing clean post-acceptance rebases verified mechanically by
`scripts/guard compare` (`replay^{tree} == new_head^{tree}`).

### 6.2 Non-Blocking Event Loop and Reactive Wakeup

CLI workers and reviewers run with `--wait` inside background harness tasks; native Antigravity
subagents run asynchronously via `invoke_subagent` and wake the orchestrator via `send_message`. The
orchestrator never polls in sleep loops.

### 6.3 Stateless Review Publication and 2-Round Convergence

To prevent PR comment noise, stranded reservations, and multi-round goal drift (PRD §1.4, §1.6):
- `scripts/review-packet start` posts zero pre-flight reservation comments; one canonical
  `## Code Review — round N` comment is published only when a valid `Approve | Request changes`
  verdict returns (failed CLI runs exit nonzero without polluting the PR). Historical
  `## Merge check 1 — round N` comments remain readable via `allow_legacy=True` for backward
  compatibility.
- `### Notes` are strictly advisory; re-reviewing an already `Approve`d head without an
  evidence-bearing recovery ruling is mechanically refused.
- After 2 review rounds without convergence (`CONVERGENCE_CAP = 2`), `scripts/review-packet` emits
  a convergence warning and `reference/reviewer.md` / `reference/orchestrator.md` direct escalation
  to the human rather than spinning further fix rounds; a human-authorized override records a
  `## Review ruling — round N` (`--decision merge-as-is --reason ... --human-authorization ...`).

---

## 7. Traceability Matrix

| Architectural Mechanism | PRD §1 Problem Addressed | PRD §2 Reuse Decision |
|---|---|---|
| Antigravity orchestrator + N dispatched executor lanes | §1.1 Single-agent scheduling bottleneck | §2.1 GitHub collaboration flow |
| Dedicated git worktrees, Codex `workspace-write` sandbox, and `in-repo-writes.md` / `where-it-goes.md` | §1.3 Irreversible/unauthorized writes; §1.5 Convention loss | §2.2 Git worktrees & OS sandboxes |
| `SessionStart` orchestrator delivery + `PreInvocation` reverse-tail restoration for orchestrator & native workers | §1.5 Context loss across sessions and compactions | §2.3 Antigravity lifecycle hooks (`injectSteps`) |
| Dual-protocol `PreToolUse` command word-guard (`hooks/pre-tool-use`) | §1.3 Catastrophic unreviewed merges & default-branch pushes | §2.3 Antigravity & Codex tool-use hooks |
| Concise single-reader role maps (`orchestrator.md`, `worker.md`, `reviewer.md`) with internalized craft | §1.2 Untrustworthy claims & silent monkey-patching; §1.6 Rule accretion | §2.3 Self-contained role maps without external skill plugins |
| Active-verification `Approve \| Request changes` review, stateless `review-packet`, and 2-round convergence rule | §1.2 Weak verification; §1.4 Multi-round drift & comment noise | §2.1 GitHub PR reviews |
| `scripts/guard merge`, `merged-result` CI binding, pure git-tree `compare_rebase`, and release-time versioning | §1.2 Unverified merges; §1.6 Per-PR version conflicts | §2.1 GitHub CI & §2.2 Branch protection |

Decisions and their reasons: `docs/adr/`.
