# DevStandard for Antigravity

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version: 1.7.0](https://img.shields.io/badge/version-1.7.0-green.svg)](plugin.json)

**The GitHub flow, extended to agent teams on Antigravity.**

DevStandard is a self-contained development-method plugin for [Antigravity](https://github.com/google-deepmind) (`agy`) — delivered by native lifecycle hooks (see [Install](#install)) — that orchestrates parallel software engineering across isolated worker lanes using [Codex CLI](https://developers.openai.com/codex) or native Antigravity subagents. It adds the three things a raw agent harness does not supply by itself:

1. **First-principles engineering discipline + minimal hard guardrails** — drill down to underlying core needs before acting (clarifying ambiguous intent, referents, or non-obvious inferences without every-turn restatement ceremony), check what need existing logic served rather than shipping symptom-masking "green" fixes, compare viable options neutrally before recommending, prove completion on the final rebased state, and keep hard guardrails strictly on execution, authority, and safety boundaries;
2. **Canonical project memory** — predictable homes for first-principles core need and concise operational notes (`AGENTS.md` / `GEMINI.md`), shared system baseline (`docs/architecture.md`), architectural decisions (`docs/adr/`), and optional shared design specs (`docs/specs/`), with zero duplicate PRD bureaucracy or committed `SUMMARY.md` / `HANDOFF.md` process junk;
3. **Reliable role context across compactions** — `SessionStart` delivers the orchestrator's complete role map (`reference/orchestrator.md`) via Antigravity `injectSteps`, and `PreInvocation` restores `reference/orchestrator.md` for the main session and `reference/worker.md` for dispatched native workers after context compaction.

The bet behind it: directing agents is the same collaboration problem human teams already solved with the GitHub flow — issues, isolated branches, evidence-bearing PRs, independent code review, and green CI — rather than a bespoke multi-agent state machine.

## Supported Executors

The main session is an Antigravity orchestrator, which routes workers and independent gating reviewers across two executor implementations by task shape — with explicit human instructions always taking top precedence and `--implementation codex` remaining the CLI default when omitted (`reference/orchestrator.md`, [ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)):

- **Codex CLI (`--implementation codex`, CLI default — bounded code, bug-fix, test, and pipeline tasks)**: Runs workers (`gpt-6.1-sol` at `xhigh`) in an OS-enforced `workspace-write` sandbox (bubblewrap/AppArmor on Linux) rooted at the lane worktree, and runs gating reviewers (`gpt-6.1-sol` at `high`) in an independent disposable clone of the pinned PR head.
- **Native Antigravity Subagents (`--implementation agy` — skill/governance/ADR authoring, macro-architecture, and scientific research tasks)**: Spawns workers and clean-context reviewers directly inside Antigravity via `invoke_subagent` (`Model="inherit"` by default, preserving your active session model and thinking effort). Continuations and verdicts flow asynchronously via `send_message` with reactive wakeup (no polling loops).

## Requirements

- **Antigravity (`agy`)**, with native plugin, `SessionStart`, `PreInvocation`, and `PreToolUse` hook support (`plugin.json`, `hooks.json`).
- **git** and an authenticated **[`gh`](https://cli.github.com/) CLI** for issue, PR, review, branch-protection, and guarded-merge operations.
- **Python 3.10+** for the shipped stdlib scripts and verification gates.
- **For Codex CLI lanes:** an installed, authenticated `codex` CLI and, on Linux, its [sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing#prerequisites) (`bubblewrap` and scoped AppArmor profiles).
- **Zero external skill plugins required:** execution craft, workflow guidance, and review discipline are self-contained inside `reference/` ([ADR 0003](docs/adr/0003-harness-engineering-alignment-and-streamlined-gates.md)).

## Install

### Antigravity Plugin Installation

Install or link `devstandard` into your Antigravity plugin directory:

1. **User-level install:**
   ```bash
   mkdir -p ~/.gemini/config/plugins
   git clone https://github.com/LeonJoeeee/DevStandard-Antigravity.git ~/.gemini/config/plugins/devstandard
   ```
   Or register the directory in `~/.gemini/config/plugins.json`.

2. **Workspace-level install:**
   ```bash
   mkdir -p .agents/plugins
   git clone https://github.com/LeonJoeeee/DevStandard-Antigravity.git .agents/plugins/devstandard
   ```

3. **Verify installation:**
   Start a new Antigravity session and ask:
   > *"What does DevStandard tell you to do?"*

   The agent should state its orchestrator role, collaboration chain (ambiguity-driven `Restate before acting`), authority boundaries, and workflow triggers.

### For Codex CLI Lanes

No separate plugin installation inside Codex is needed: `scripts/dispatch` injects `reference/worker.md` or `reference/reviewer.md`, the unified `# Task packet`, helper model defaults, and `hooks/pre-tool-use` directly into each `codex exec` invocation.

## What You Get

- **Core-need-anchored direction & two-track design** — at founding and feature intake, the orchestrator checks both detailed designs and rough ideas against the project's underlying core need (`AGENTS.md` / `GEMINI.md`), runs concurrent non-blocking read-only research into existing repo capabilities and mature open-source packages, passes the core need in every helper brief and leaf `## Goal`, and follows a two-track design flow: single-issue work goes straight to one proportional leaf issue (running a lightweight clean-context read-only `inherit` pre-code challenge checking core-need fit, interfaces, and rollback only on high-cost interface, schema, or hard-to-reverse changes), while multi-issue or cross-component work drafts and internally challenges the overall design and child split before human confirmation. For bugs and audits, it traces root causes, what need existing logic served, siblings, cost of inaction, and fix-induced complexity *before* judging whether a fix is worth making — escalating rather than masking symptoms for green checks and leaving tolerable minor issues alone. Viable options on genuine tradeoff forks are compared neutrally before any recommendation.
- **Conflict-free parallel lanes & close-time reconciliation** — held parent tracking issues (`hold`, never dispatched) coordinate self-contained `Parent: #<parent>` leaf issues (`1 leaf issue = 1 branch = 1 worktree = 1 green PR`), immediate close-time maintenance reconciles parent progress and downstream `after #<id>` contracts before moving on, and release versions are bumped at release time rather than on ordinary PRs to keep concurrent lanes free of manifest conflicts.
- **Active-verification code review & 2-round convergence** — a clean-context Senior Code Reviewer (`reference/reviewer.md`) combines static diff analysis with targeted verification probes in isolated `/tmp` or scratch directories within three hard red lines, verifying genuine `Goal` and core-need fulfillment (flagging `[Needs human decision]` if `Goal` framing conflicts with the core need) and returning `Approve | Request changes` (`### Verdict`, `### Blocking`, `### Notes`). `Notes` never block or trigger rework; if 2 fix rounds fail to converge, the orchestrator stops looping and escalates to you.
- **Guarded integration** — `scripts/guard merge` verifies an `Approve` verdict (or human-authorized `merge-as-is` ruling), green two-parent `merged-result` CI, and exact head identity or pure conflict-free git-tree rebase equality.

## How You Use It

- **Day to day** — describe a feature, bug, or audit question. The orchestrator clarifies any ambiguous phrasing, referent, or non-obvious inference up front (skipping ceremonial restatement when your request is already clear), investigates or scopes proportionally, confirms the plan with you, dispatches isolated lanes, and returns reviewed, CI-green PRs with final-state command evidence.
- **Starting something new** — drill down to first-principles core needs in repo-root `AGENTS.md` (`## Core need`) and capture shared boundaries in `docs/architecture.md` when warranted (`reference/architecture.md`); small prototypes and 1–2 line fixes skip heavy ceremony.
- **Running parallel work** — direct one responsive Antigravity orchestrator while N workers build, rebase, verify, and drive checks green in parallel worktrees. You own direction, trade-offs, architecture sign-off, irreversible authorizations, and releases (or grant `delegated` merge / standing release authority where desired).

## What's Actually Installed

1. **SessionStart and Post-Compaction PreInvocation Delivery (`hooks/session-start`)**:
   Injects `reference/orchestrator.md` whole at new-session startup via `{"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}` while suppressing all subagents. On `PreInvocation`, reverse-scans `transcript.jsonl` from EOF in 64 KB chunks and restores `reference/orchestrator.md` for the main session — or `reference/worker.md` for explicitly dispatched native `worker` subagents — only after a new `CHECKPOINT`, keeping reviewers, `research` subagents, task-local helpers, and ordinary turns at `{}` ([ADR 0002](docs/adr/0002-post-compaction-orchestrator-context-re-injection.md)).

2. **Dual-Protocol PreToolUse Guard (`hooks/pre-tool-use`, `scripts/hard_edges.py`)**:
   Inspects shell tool commands across both Antigravity camelCase JSON (`toolCall.name`, `toolCall.args.CommandLine`) and Codex snake_case JSON (`tool_name`, `tool_input`):
   - **Worker:** refuses `merge` and direct `push` to `main` / `master`.
   - **Orchestrator:** refuses `gh pr merge` (redirecting to `scripts/guard merge`).
   - **Reviewer:** refuses `gh` write flags (`-X`, `--method`, `-f`, `-F`, `--field`, `--input`).

3. **Shipped Tooling (`scripts/`)**:
   - `scripts/dispatch`: Creates/adopts/cleans isolated worktree lanes and assembles unified `# Task packet` prompts across Codex CLI and native Antigravity subagents.
   - `scripts/review-packet`: Verifies green PR checks, assembles 9-slot reviewer packets, statelessly publishes `## Code Review — round N` comments, and tracks 2-round convergence and rulings.
   - `scripts/guard`: Audits branch protection, proves pure git-tree equality across rebases (`compare`), and executes verified squash merges (`merge`).

## Layout

```text
plugin.json      Antigravity plugin manifest (v1.7.0)
hooks.json       Lifecycle hook declarations (SessionStart, PreInvocation, PreToolUse)
hooks/           SessionStart & reverse-tail PreInvocation context delivery, dual-protocol PreToolUse guard
scripts/         Deterministic lane dispatcher, stateless review-packet publisher, and guarded merge CLI
reference/       Concise role maps (orchestrator.md, worker.md, reviewer.md), executor guides
                 (harness-codex.md, harness-antigravity.md), hygiene rules (in-repo-writes.md,
                 where-it-goes.md), and trigger-loaded guides (repo-agents-md, architecture, adr, design-spec, CI)
docs/            architecture.md and ADRs (0000–0004, covering host/executors, compaction, Harness Engineering, & core-need alignment)
```

## License

MIT.
