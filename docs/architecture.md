# DevStandard-Antigravity — Collaboration-Model Architecture

> Shared baseline for all parallel work in DevStandard-Antigravity. Read alongside repo-root
> `AGENTS.md` before starting a task. Structural, scope, or costly-to-reverse changes to this
> baseline require a public merge, human approval, and an ADR.

This document defines the collaboration baseline and supplementary harness of DevStandard-Antigravity
(`devstandard-agy`). It specifies the project's core need, problem background, reused foundations,
roles, context boundaries, delivery paths, mechanical guards, stateless review/merge gates,
concurrency behavior, boundaries, checkable success criteria, and end-to-end traceability (`§8.3`).

Delivery and enforcement statements use two labels:
- **Verified**: the behavior was measured or tested directly against the shipped implementation.
- **Unverified**: the architecture requires the behavior without automated runtime verification here.

---

## 1. Core Need, Problem Background, and Reuse Baseline

### 1.1 Vision and Core Need

> **One person directs an agent team through development: the human uncovers first-principles core
> needs, weighs real product and architectural tradeoffs, sets acceptance criteria, and authorizes
> irreversible actions, baseline changes, and releases; one Antigravity orchestrator converses,
> researches, dispatches, coordinates independent code review, and integrates; N workers build and
> verify N issues in parallel — anchored end-to-end to the user's true underlying need without
> process ceremony.**

**Who this is for:** anyone carrying non-trivial software engineering work through Antigravity — a
solo developer directing parallel agent lanes, or a team where each human directs their own
orchestrator session over a shared GitHub repository.

### 1.2 Problem Background

1. **The native harness provides a single agent.** Advancing several pieces of work in parallel
   forces the human into manual scheduling and coordination instead of direction and judgment.
2. **Core-need drift and surface-level or untrustworthy completions.** Solution-shaped requests,
   speech-transcription shorthand, and narrow slice context cause isolated lanes or subagent helpers
   to build surface mechanisms that miss what the user genuinely needs, or to "fix" bugs by masking
   symptoms, silencing errors, degrading real behavior, weakening assertions, silently monkey-patching
   private third-party internals, or claiming completion without final-state proof so checks turn
   green while real purpose is undermined.
3. **Irreversible operations carry disproportionate risk.** Ordinary mistakes in an isolated branch
   are cheap to recover; deleting unintegrated work, force-pushing shared branches, mutating live
   services, or writing to unauthorized host paths is not.
4. **Unguided review loops erode the core of the work.** Without active runtime verification, a clear
   blocker boundary, and a convergence stop, multi-round review drifts into secondary churn while
   losing sight of whether the change genuinely serves its goal and underlying core need.
5. **Agents lose purpose and conventions across sessions and compactions.** Core project needs,
   canonical document homes, scratch boundaries, speech-transcription restatement, and role limits
   vanish in fresh sessions or after context compaction unless the harness delivers and restores them
   reliably where sessions actually look.
6. **Incident-driven rules and absolutist requirement dogma accrete into brittle ceremony.**
   Preventive micro-prescriptions, absolutist product bans ("non-negotiable guarantees", "must never"
   product dogma that triggers LLM zealotry), duplicate authority documents, external skill-plugin
   lock-in, per-PR version-bump rituals, and stateful PR comment machinery crowd out engineering
   judgment and manufacture avoidable merge conflicts.

### 1.3 Reuse Baseline (Structures Reused As-Is)

1. **The GitHub collaboration flow** (issues / branches / PRs / code review / CI): the durable
   coordination state machine human software teams have already validated.
2. **git worktrees, OS-level sandboxes, and server-side branch protection**: parallel filesystem
   isolation and mechanical branch enforcement natively available on the host and GitHub.
3. **Antigravity lifecycle hooks, native subagents, and native `AGENTS.md` loading, paired with
   self-contained engineering craft**: Antigravity's `SessionStart`, `PreInvocation`, `PreToolUse`,
   `invoke_subagent`, and `send_message` primitives combined with always-loaded repo-root `AGENTS.md`
   (`## Core need`), concise single-reader role maps (`orchestrator`, `worker`, `reviewer`), and zero
   external skill-library dependencies.

---

## 2. Scope and Configuration

The supported configuration is **one Antigravity orchestrator** session directing **N dispatched
executors**. Each dispatched executor serves one of two purposes: **worker** or **reviewer** (a
conflict resolver is a worker assigned a conflict task, not a third role). This is the smallest
structure that removes manual lane scheduling from the human while reusing the GitHub collaboration
flow, git worktrees, and OS/host isolation (`§1.2`, `§1.3`).

```
                      +-----------------------------+
                      |     Human Developer         |
                      +--------------+--------------+
                                     | Core Needs, Tradeoffs & Authorization
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
[ADR 0003](adr/0003-harness-engineering-alignment-and-streamlined-gates.md),
[ADR 0004](adr/0004-first-principles-core-need-alignment-and-prd-retirement.md)). Antigravity owns
sessions, native subagent execution, tools, and permissions; Codex CLI owns its OS-level sandbox
(`bubblewrap` / AppArmor on Linux). DevStandard supplies the collaboration layer above them:
first-principles core-need alignment, concise single-reader role maps, isolated lane dispatch,
independent code review, guarded merge, and canonical file hygiene (`reference/in-repo-writes.md`,
`reference/where-it-goes.md`).

**GitHub and canonical repo docs hold durable state:** repo-root `AGENTS.md` (or established
`GEMINI.md`) holds `## Core need` and concise operational facts; `docs/architecture.md` holds shared
system structure; `docs/adr/` records architectural decisions; issues define `Goal` (connecting the
task outcome to the project's core need), `Bounds`, and `Done-check` plus `devstandard-dispatch-v1`
lane receipts; branches and worktrees isolate edits; PRs carry final-state proof;
`## Code Review — round N` comments record verdicts; and CI plus branch protection gate integration.
Local scratch directories, process IDs, and subagent handles are transient execution state, never a
competing state machine.

---

## 3. Roles and Context Sets

Each role reads a single concise (~100–240 line), self-contained navigation map with internalized
engineering craft, non-dogmatic core-need orientation, and zero external skill-plugin dependencies
([ADR 0003](adr/0003-harness-engineering-alignment-and-streamlined-gates.md),
[ADR 0004](adr/0004-first-principles-core-need-alignment-and-prd-retirement.md)).

### 3.1 Orchestrator (`reference/orchestrator.md`)

The orchestrator converses with the human (`Restate before acting`, restating both literal/shorthand
meaning and the inferred underlying core need), drills down across turns at project founding or major
direction shifts to uncover first-principles core needs rather than transcribing surface feature
wishes, checks both detailed human designs/specs and rough exploratory requests against the core need
(with concurrent non-blocking read-only OSS/repo research), shapes feature work through a two-track
flow — going straight to one proportional leaf issue by default (running a lightweight clean-context
read-only `inherit` pre-code challenge checking core-need fit, interface soundness, and rollback on
high-cost public/shared interface, schema, or hard-to-reverse changes), or drafting and internally
challenging an overall design + child-issue split before human confirmation on multi-issue or
cross-component work — evaluates bugs and audits (tracing root causes, what need existing logic
served, siblings, cost of inaction, genuine core-need satisfaction vs. symptom-masking, and
fix-induced complexity before judging worthiness), compares viable options neutrally on genuine
tradeoff forks before recommending, manages held parent tracking issues (`hold`, never dispatched)
and self-contained `Parent: #N` leaf issues, dispatches lanes, coordinates stateless acceptance
reviews, enforces the 2-round convergence rule, runs guarded merges, executes immediate close-time
issue/parent/dependent reconciliation and lane teardown, and handles release-time versioning.

Its context set contains:
- authority boundaries (`Looking needs no permission; doing always does`, `hold` / `delegated`,
  mandatory `Restate before acting` with inferred core need, explicit human consent before
  irreversible actions or monkey-patching third-party internals, and keeping hard red lines strictly
  on execution, authority, and safety boundaries rather than absolutist product bans);
- the non-blocking event loop, task-shape executor routing (Codex CLI for bounded code, bug-fix,
  test, and pipeline lanes; native Antigravity `inherit` for skill/governance/ADR authoring,
  macro-architecture, and scientific research lanes, with explicit human instructions always taking
  top precedence), orchestrator helper split (passing the project's core need and how the helper's
  task serves it in every brief: native `inherit` via `TypeName="self"` with an explicit read-only
  prompt boundary for top-level judgment/arbitration, pre-code design/decomposition challenges, and
  research/information synthesis; Codex for bounded execution helpers), and machine-parsed role and
  task-local helper routing tables (`worker >= reviewer`: `gpt-6.1-sol` at `xhigh` / `high` on Codex,
  `inherit` on Antigravity);
- workflow triggers and pointers to `scripts/dispatch`, `scripts/review-packet`, `scripts/guard`,
  and trigger-loaded `reference/*.md` guides (`harness-codex.md`, `harness-antigravity.md`,
  `in-repo-writes.md`, `where-it-goes.md`, `repo-agents-md.md`, `architecture.md`, `adr.md`,
  `design-spec.md`, `ci-pipelines.md`, `ci-cannot-run.md`, `red-check.md`, `deployments.md`).

### 3.2 Dispatched Executor: Purpose × Implementation

Purpose determines authority and role map; `--implementation` determines transport and isolation
(`reference/orchestrator.md` routes `worker` and `reviewer` lanes by task shape unless the human
specifies otherwise, while `--implementation codex` remains the CLI flag default when omitted):

| Purpose | Codex CLI (`--implementation codex`, CLI default) | Native Antigravity Subagent (`--implementation agy`) | Deliverable |
|---|---|---|---|
| **Worker** | `scripts/dispatch` feeds `reference/worker.md` + `# Task packet` (`Environment:`, `Helpers:`, `Commit trailer:`) to `codex exec` (`gpt-6.1-sol` at `xhigh`) in `workspace-write` sandbox rooted at the worktree with `--add-dir` grants for `--git-common-dir` and `--git-dir`. | `scripts/dispatch` writes `agent-spawn.json` (`Role="Issue <N> worker"`, `Model="inherit"` default) with `reference/worker.md` + `# Task packet`. Spawned via `invoke_subagent`, continued via `send_message`, and restored on compaction via `PreInvocation`. | A green, rebased PR linked to the issue with final-state `Done-check` evidence and an empty `git status --porcelain -uall`. |
| **Reviewer** | `scripts/review-packet start --wait` invokes `scripts/dispatch` (`gpt-6.1-sol` at `high`) in an independent disposable `--no-local` clone of `HEAD_SHA` (`--add-dir` only to the clone's separate Git dir), validates the returned verdict, and posts one `## Code Review — round N` comment. | `scripts/review-packet start --implementation agy` writes `packet.json`, `packet.txt`, `attempt.json`, and `agent-spawn.json` (`Role="Issue <N> reviewer"`, `Model="inherit"` default) pointing to `brief.txt` (9-slot `reference/reviewer.md` + `# Task packet` + 3-form `## Pinned Git evidence`). Caller publishes via `scripts/review-packet publish`. | A validated whole verdict (`Approve` or `Request changes`, `### Blocking`, `### Notes`) on the exact `HEAD_SHA`, with zero repository or remote mutations by the reviewer. |

### 3.3 Worker Context Set (`reference/worker.md`)

The worker receives `reference/worker.md` plus a dynamic `# Task packet` assembled by `scripts/dispatch`:
- **Static role (`reference/worker.md`):** `1 issue = 1 branch = 1 worktree = 1 green, evidence-bearing PR`;
  `### Never` execution/authority/safety boundaries; task-local helper rule passing the project's
  core need and how the helper's task serves it in every brief; lane & baseline verification
  (reading repo-root `AGENTS.md` / `GEMINI.md` and `docs/architecture.md` when present alongside
  `## Goal`); internalized `## 3. Execution craft` (proportional scratch planning, fail-before-pass
  reproduction, checking what need existing logic served and tracing root causes/siblings without
  symptom-masking, public-API-first reuse, weighing fix-induced complexity); final-state rebase &
  clean-tree rules (no per-PR version bumps); and escalation / review-continuation / harness-limit
  rules (stopping when literal task framing or every in-`Bounds` fix passing checks would undermine
  the core need).
- **Dynamic `# Task packet`:** `Issue`, `Branch`, `Worktree`, `Named base`, `Role references resolve from`,
  verbatim issue body and ordered non-dispatch comments, optional `PR` and `Inputs and expected output` /
  `Continuation brief`, `Executor`, `Record language`, `Commit trailer`, concise `Environment:` line,
  and single-line machine-derived `Helpers:` routing line (`codex_helper_line` /
  `antigravity_helper_line`, including the core-need brief requirement). No orchestrator harness
  pages are spliced in.

### 3.4 Reviewer Context Set (`reference/reviewer.md`)

`reference/reviewer.md` is a direct 9-slot Senior Code Reviewer prompt (no outer code fence or
orchestrator preamble):
- **Targeted active verification within three hard red lines:** beyond static reading, reviewers run
  focused commands and edge-case probes when needed to verify runtime behavior, callers, or claimed
  `Done-check` proofs, placing any temporary files strictly inside an isolated `mktemp -d` under
  `/tmp` (or session scratch / disposable CLI review clone) while obeying three hard red lines:
  (1) never touch repository worktrees or refs, (2) never write to GitHub or remotes, and (3) never
  trigger external or live side effects.
- **Core-need evaluation and two-tier verdict contract:** verifies that the change genuinely serves
  the stated `Goal` and underlying core need (checking what need existing logic served before it was
  changed rather than accepting symptom-masking green checks). Opens with
  `Reviewer: {REVIEWER_IDENTITY} — reviewed {HEAD_SHA}`, followed by `### Verdict`
  (`Approve | Request changes` with summary grounds), `### Blocking` (`None.` on `Approve`, or
  numbered concrete defects prefixed with `[Needs human decision]` when an unauthorized irreversible
  action, a conflict between the issue's `Goal` framing and the project's core need, or a
  scope/direction change is implicated), and `### Notes` (non-blocking observations / `Nit:` items
  that never block merge or trigger re-review).

### 3.5 Resolver

A conflict resolver is a worker continued or dispatched to rebase a branch that conflicts with
current `main`. It resolves conflicts within the lane, reruns `Done-check` on the final state, and
hands back the updated head for fresh code review; it never merges.

---

## 4. Context Delivery

Static role prompts live at one canonical file per role:
- Orchestrator: `reference/orchestrator.md`
- Worker: `reference/worker.md`
- Reviewer: `reference/reviewer.md`

Orchestrator-only executor guides live separately in `reference/harness-codex.md` and
`reference/harness-antigravity.md`.

### 4.1 Antigravity Context Delivery Across Compactions (`hooks/session-start`)

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

### 4.2 Worker and Reviewer Packet Assembly (`scripts/dispatch` & `scripts/review-packet`)

- **Worker dispatch:** `scripts/dispatch` validates the target checkout, issue, explicit named base,
  and linked worktree (`.agents/worktrees/<issue>-<slug>`), writes `brief.txt` (`reference/worker.md`
  + `# Task packet` including `codex_helper_line` or `antigravity_helper_line`), records a
  `devstandard-dispatch-v1` receipt on the issue, and either runs sandboxed `codex exec` (`--wait`)
  or writes `agent-spawn.json` (`--implementation agy`).
- **Reviewer assembly & dispatch:** `scripts/review-packet` (`scripts/review_packet.py`) verifies
  all observed and required PR checks are green, fills the 9 slots of `reference/reviewer.md`,
  appends `## Packet integrity`, the quoted issue body, optional `rebase_result`, and verbatim
  `prior_verdicts`, and invokes `scripts/dispatch --purpose reviewer`. For `--implementation agy`,
  `scripts/dispatch` appends `## Pinned Git evidence` containing the three canonical diff forms
  (`--name-status`, `--stat`, and full `diff` across `REVIEW_BASE_SHA..HEAD_SHA`) without redundant
  per-file blob dumps.

---

## 5. Dual-Protocol PreToolUse Guard

`hooks/pre-tool-use` and `scripts/hard_edges.py` provide deterministic command-word refusals across
both Antigravity and Codex CLI tool protocols.

### 5.1 Protocol Normalization and Fail-Open Safety

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

### 5.2 Role Resolution and Refusal Rules

`hooks/pre-tool-use` resolves the active role from `--role`, `DEVSTANDARD_ROLE`,
`subagent_role(event)` (`strict=False`, so untyped task-local helpers safely inherit `worker`
refusals while `research` children keep their parent role), `agent_type`, or untyped `agent_id`:

| Role | Refused Shell Patterns | Rationale & Redirect |
|---|---|---|
| **Worker** | Whole-word `merge`; `push` also naming `main` or `master` | Workers never integrate code or push to protected branches; they push their task branch and hand back the PR (`reference/worker.md`). |
| **Orchestrator** | `gh pr merge` | Direct merges bypass reviewed-head, rebase-proof, and `merged-result` verification; route through `<plugin>/scripts/guard merge` (`reference/orchestrator.md`). |
| **Reviewer** | `gh` commands carrying write flags (`-X`, `--method`, `-f`, `-F`, `--field`, `--input`) | Reviewers never write to GitHub or remotes; they return their whole verdict to the caller (`reference/reviewer.md`). |

---

## 6. Workflow Edges and Enforcement Tiers

Enforcement combines three tiers:
- **Hard:** Mechanical refusal by script, hook, OS sandbox, or GitHub branch protection.
- **Structural:** Context separation, worktree isolation, or deterministic packet/gate assembly.
- **Soft:** Engineering judgment guided by concise role principles.

### Workflow 1: Lifecycle of One Task

| Step / Edge | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Intake, Core-Need Alignment, Two-Track Design & Decomposition | **Structural:** `reference/orchestrator.md` mandates `Restate before acting` (with inferred core need), first-principles core-need drill-down on founding/major directions (`reference/repo-agents-md.md`, `reference/architecture.md`), core-need checks on both detailed specs and rough ideas, deep-first bug/audit investigation (checking what need existing logic served and rejecting symptom-masking fixes), neutral-first option comparison on tradeoff forks, two-track scoping (single-issue default vs. upfront multi-issue design + split), held parent tracking issues (`hold`, never dispatched) with self-contained leaf issues (`## Goal` naming core need + task connection, `Parent: #N`, inlined contracts, `after #N` + `hold`), and optional status-free `docs/specs/` contracts (`reference/design-spec.md`). **Soft:** Concurrent read-only subagent research into repo & mature OSS solutions; clean-context read-only `inherit` pre-code challenge (`TypeName="self"`) checking core-need fit, interfaces, and rollback before dispatch/confirmation; core need passed in every helper brief. | **Verified:** `reference/orchestrator.md` §1–§3; `reference/repo-agents-md.md`; `reference/architecture.md`; `reference/adr.md`; `reference/design-spec.md`; `.github/workflows/ci.yml`. |
| Leaf Issue → Isolated Lane Dispatch | **Hard:** `scripts/dispatch` enforces explicit base, linked `.agents/worktrees/<issue>-<slug>`, gitignore check, and Codex `workspace-write` sandbox. **Structural / Soft:** Unified `# Task packet` (including `Helpers:` core-need brief requirement) + `devstandard-dispatch-v1` receipt on leaf issues; respecting `hold`, `Parent: #N`, and `after #N` prerequisites before calling `scripts/dispatch` is an orchestrator Structural/Soft convention rather than a CLI hard refusal. | **Verified:** `scripts/dispatch`; `scripts/hard_edges.py`; `reference/orchestrator.md` §3; `.github/test-dispatch.py`; `.github/test-hard-edges.py`. |
| Implementation → Green PR | **Hard:** `hooks/pre-tool-use` blocks worker `merge` and `main`/`master` pushes; CI runs test suite and two-parent `merged-result` job. **Structural / Soft:** `reference/worker.md` reads `AGENTS.md` / `GEMINI.md` and `docs/architecture.md` when present, internalizes root-cause/existing-purpose craft, forbids per-PR version bumps, and escalates when literal task framing or in-`Bounds` fixes would undermine the core need. | **Verified:** `reference/worker.md`; `.github/workflows/ci.yml`; `.github/test-hard-edges.py`. |
| Green PR → Stateless Code Review | **Hard:** `scripts/review-packet` refuses red/pending/unreported checks, validates 9-slot `reference/reviewer.md`, isolates CLI reviewers in disposable clones, and blocks reviewer `gh` write flags. **Structural:** Stateless `start` / `publish` posts one `## Code Review — round N` comment on valid return. **Soft:** Reviewer runs targeted `/tmp` active verification within three hard red lines, checks genuine `Goal` + core-need fulfillment (vs. symptom-masking), and flags `[Needs human decision]` when `Goal` conflicts with the core need. | **Verified:** `scripts/review-packet`; `scripts/review_packet.py`; `reference/reviewer.md`; `.github/test-review-packet.py`. |
| Accepted Head → Guarded Merge & Close-Time Maintenance | **Hard:** Branch protection blocks direct pushes; `scripts/guard merge` requires a valid `Approve` verdict (or human-authorized `merge-as-is` ruling), green `merged-result / BASE / HEAD`, and exact head or conflict-free git-tree equality (`compare_rebase`); `scripts/dispatch --cleanup` requires a merged `--pr` or explicit `--discard` and refuses dirty/switched lanes. **Structural / Soft:** Immediate close-time reconciliation — updating/closing `Parent: #N` issues upward, posting contract updates on `after #N` / sibling issues, lifting satisfied `hold`s, dispatching newly ready leaves, and syncing `AGENTS.md` / `GEMINI.md` and obsolete `docs/specs/` via PRs — is guided by `reference/orchestrator.md` §3. | **Verified:** `scripts/guard`; `scripts/hard_edges.py`; `scripts/dispatch`; `reference/orchestrator.md` §3; `.github/test-hard-edges.py`; `.github/test-dispatch.py`. |
| Release-Time Versioning | **Structural:** Ordinary PRs leave version manifests untouched; releases bump versions in dedicated release PRs and tag after merge under human authorization or standing delegation. | **Verified:** `reference/orchestrator.md`; `reference/worker.md`; `scripts/guard`. |

### Workflow 2: Orchestrator Event Loop

| Event | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Human message arrives | **Soft:** Opens with `Restate before acting` (including inferred core need); checks designs/requests against the core need, runs two-track scoping, and proposes before mutating state. | **Verified:** `reference/orchestrator.md` §1 & §3. |
| Irreversible action or monkey-patch | **Hard:** `PreToolUse` refuses `gh pr merge`. **Soft:** Stops for explicit human words before irreversible actions or private third-party monkey-patching. | **Verified:** `hooks/pre-tool-use`; `reference/orchestrator.md` §1 & §3. |
| Context compaction (`CHECKPOINT`) | **Hard:** `hooks/session-start --pre-invocation` reverse-scans `transcript.jsonl` and re-injects `reference/orchestrator.md` once per checkpoint. | **Verified:** `hooks/session-start`; `.github/test-session-start.py`. |
| Verdict returns (`Approve` / `Request changes`) | **Hard:** `scripts/review-packet` rejects malformed verdicts, blocks `Notes`-only re-reviews on accepted heads, warns at 2+ non-converging rounds, and requires `--human-authorization` for `merge-as-is`. | **Verified:** `scripts/review-packet`; `scripts/hard_edges.py`; `.github/test-review-packet.py`. |
| Issue closes (merge or authorized cancellation) | **Hard:** `scripts/dispatch --cleanup` requires merged `--pr` or explicit `--discard` and a clean lane tree. **Structural / Soft:** Reconciles `Parent: #N` progress/closure, `after #N` / sibling contracts, `hold` labels, `AGENTS.md` / `GEMINI.md`, and obsolete `docs/specs/` before moving on. | **Verified:** `scripts/dispatch`; `reference/orchestrator.md` §3; `.github/test-dispatch.py`. |
| `main` goes red | **Structural:** Freezes new dispatch and prioritizes green restoration (`reference/red-check.md`, `reference/ci-pipelines.md`). | **Verified:** `reference/orchestrator.md` §2 & §4. |

### Workflow 3: Worker Execution

| Step | Enforcement Tier & Mechanism | Evidence State |
|---|---|---|
| Packet, core-need & lane validation | **Structural:** `# Task packet` supplies verbatim issue (`## Goal` naming core need + task connection), ordered comments, base, branch, worktree, and `Helpers:` core-need brief line. **Soft:** Worker reads `AGENTS.md` / `GEMINI.md` and `docs/architecture.md` when present, verifies lane git metadata, and stops on missing/conflicting contracts, core-need conflicts, or broken baselines. | **Verified:** `scripts/dispatch`; `scripts/hard_edges.py`; `reference/worker.md` §1–§2 & §5. |
| Native worker compaction | **Hard:** `hooks/session-start --pre-invocation` restores `reference/worker.md` for dispatched native workers while keeping helpers/reviewers suppressed. | **Verified:** `hooks/session-start`; `.github/test-session-start.py`. |
| Craft, boundaries & hygiene | **Hard:** Codex OS sandbox + `PreToolUse` word-guard + CI canonical-doc assertions. **Structural / Soft:** `reference/worker.md` checks what need existing logic served rather than masking symptoms, and `reference/in-repo-writes.md` / `reference/where-it-goes.md` prevent `SUMMARY.md` / `HANDOFF.md` junk and unauthorized host writes. | **Verified:** `reference/worker.md` §3; `reference/in-repo-writes.md`; `reference/where-it-goes.md`; `.github/workflows/ci.yml`. |
| Final rebase, proof & handback | **Hard:** `scripts/guard merge` requires current `main` ancestry and `merged-result` CI; `scripts/review-packet` gates on green PR checks. | **Verified:** `reference/worker.md` §4; `scripts/guard`; `scripts/review-packet`. |

---

## 7. Concurrency and Review Convergence

### 7.1 Conflict-Free Parallel Lanes

N parallel lanes execute across isolated `.agents/worktrees/<issue>-<slug>` checkouts under one
orchestrator. Release-time versioning eliminates artificial manifest/badge conflicts across
concurrent branches, allowing clean post-acceptance rebases verified mechanically by
`scripts/guard compare` (`replay^{tree} == new_head^{tree}`).

### 7.2 Non-Blocking Event Loop and Reactive Wakeup

CLI workers and reviewers run with `--wait` inside background harness tasks; native Antigravity
subagents run asynchronously via `invoke_subagent` and wake the orchestrator via `send_message`. The
orchestrator never polls in sleep loops.

### 7.3 Stateless Review Publication and 2-Round Convergence

To prevent PR comment noise, stranded reservations, and multi-round goal drift (`§1.2`):
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

## 8. Boundaries, Success Criteria, and Traceability

### 8.1 Boundaries and Non-Goals

- **Supplies only the collaboration layer** above the host harness, git, and GitHub — never a
  competing runtime, custom issue tracker, or bespoke multi-agent state machine.
- **Pragmatic engineering over perfectionism or requirement dogma:** acceptance requires sound,
  proportional fulfillment of `Goal` and the project's core need within `Bounds`; hard red lines stay
  strictly on execution, authority, and safety boundaries rather than absolutist product bans, and
  audits explicitly leave tolerable minor issues alone when a fix would introduce heavier complexity
  or risk than the defect itself.
- **High-trust principles + minimal hard guardrails:** mechanical enforcement is reserved for
  high-cost execution boundaries; everyday engineering judgment uses constructive first-principles
  clarity ("the real need is X rather than Y") rather than incident-accreted word bans or ceremony.
- **Self-contained without external skill-plugin lock-in:** core engineering habits live concisely
  inside the role maps rather than binding external skill libraries.
- **Release is human-gated and versioned at release time:** ordinary PRs do not bump version
  manifests; shipping tags wait for explicit human authorization (unless standing release delegation
  is granted for a specific repository).

### 8.2 Success Criteria

Success means the problems of `§1.2` no longer occur:

1. **The human directs rather than schedules:** parallel lanes advance concurrently while human
   attention stays on uncovering core needs, weighing real tradeoffs, approving baseline changes,
   and authorizing irreversible actions.
2. **Every role and helper stays anchored to the true underlying need:** solution-shaped requests are
   checked against `## Core need`, leaf `## Goal`s and helper briefs carry macro purpose, and workers
   and reviewers escalate rather than shipping symptom-masking "green" completions.
3. **Every merged change carries final-state proof and independent verification:** completion claims
   are backed by rebased `Done-check` outputs, green `merged-result` CI, and an active `Approve`
   review on the exact head (or pure conflict-free rebase tree match).
4. **Zero unauthorized irreversible actions or silent monkey-patches occur.**
5. **Reviews protect the core and converge quickly:** `Notes` never force rework, `Blocking` items
   isolate real defects or `[Needs human decision]` alignment conflicts, and non-converging lanes
   escalate after 2 rounds instead of drifting.
6. **Purpose, conventions, and role boundaries survive fresh sessions and compactions** for both the
   orchestrator and long-running native workers, without duplicate authority files, committed
   `SUMMARY.md` / `HANDOFF.md` junk, or per-PR version conflicts.
7. **The method stays readable end-to-end:** every page, hook, and script traces directly to `§1.2`
   or `§1.3`.

### 8.3 Traceability Matrix and Existence Criterion

| Architectural Mechanism | §1.2 Problem Addressed | §1.3 Reuse Decision |
|---|---|---|
| Antigravity orchestrator + N dispatched executor lanes | §1.2.1 Single-agent scheduling bottleneck | §1.3.1 GitHub collaboration flow |
| `AGENTS.md` `## Core need`, inferred-need restatement, core-need intake/challenge checks, leaf `## Goal` & `Helpers:` core-need briefs, and retired standalone PRD | §1.2.2 Core-need drift & symptom-masking completions; §1.2.5 Purpose loss; §1.2.6 Duplicate-doc & dogma ceremony | §1.3.3 Native `AGENTS.md` loading & self-contained role maps |
| Dedicated git worktrees, Codex `workspace-write` sandbox, and `in-repo-writes.md` / `where-it-goes.md` | §1.2.3 Irreversible/unauthorized writes; §1.2.5 Convention loss | §1.3.2 Git worktrees & OS sandboxes |
| `SessionStart` orchestrator delivery + `PreInvocation` reverse-tail restoration for orchestrator & native workers | §1.2.5 Context loss across sessions and compactions | §1.3.3 Antigravity lifecycle hooks (`injectSteps`) |
| Dual-protocol `PreToolUse` command word-guard (`hooks/pre-tool-use`) | §1.2.3 Catastrophic unreviewed merges & default-branch pushes | §1.3.3 Antigravity & Codex tool-use hooks |
| Concise single-reader role maps (`orchestrator.md`, `worker.md`, `reviewer.md`) with internalized root-cause & existing-purpose craft | §1.2.2 Symptom-masking & silent monkey-patching; §1.2.6 Rule accretion | §1.3.3 Self-contained role maps without external skill plugins |
| Active-verification `Approve \| Request changes` review, `[Needs human decision]` core-need escalation, stateless `review-packet`, and 2-round convergence rule | §1.2.2 Surface "green" fixes; §1.2.4 Multi-round drift & comment noise | §1.3.1 GitHub PR reviews |
| `scripts/guard merge`, `merged-result` CI binding, pure git-tree `compare_rebase`, and release-time versioning | §1.2.2 Unverified merges; §1.2.6 Per-PR version conflicts | §1.3.1 GitHub CI & §1.3.2 Branch protection |

**Existence criterion:** every rule, file, and mechanism in this supplementary harness must trace
back to a problem in `§1.2` or a reuse decision in `§1.3`; whatever cannot be traced is to be
deleted.

Decisions and their reasons: `docs/adr/`.
