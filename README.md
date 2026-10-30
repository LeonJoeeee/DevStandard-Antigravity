# DevStandard for Antigravity

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version: 1.5.0](https://img.shields.io/badge/version-1.5.0-green.svg)](plugin.json)

**The GitHub flow, extended to agent teams on Antigravity.**

DevStandard is a self-contained development-method plugin for [Antigravity](https://github.com/google-deepmind) (`agy`) — delivered by native lifecycle hooks (see [Install](#install)) — that orchestrates parallel software engineering across isolated worker lanes using [Codex CLI](https://developers.openai.com/codex) or native Antigravity subagents. It adds the three things a raw agent harness does not supply by itself:

1. **High-trust engineering discipline + minimal hard guardrails** — restate human intent before acting, investigate root causes and weigh fix-induced complexity before touching code, compare viable options neutrally before recommending, prove completion on the final rebased state, and stop for explicit human authorization before irreversible actions or monkey-patching third-party internals;
2. **Canonical project memory** — predictable homes for product definition (`docs/PRD.md`), shared baseline (`docs/architecture.md`), architectural decisions (`docs/adr/`), substantial design specs (`docs/specs/`), and concise operational notes (`AGENTS.md` / `GEMINI.md`), with zero committed `SUMMARY.md` / `HANDOFF.md` process junk;
3. **Reliable role context across compactions** — `SessionStart` delivers the orchestrator's complete role map (`reference/orchestrator.md`) via Antigravity `injectSteps`, and `PreInvocation` restores `reference/orchestrator.md` for the main session and `reference/worker.md` for dispatched native workers after context compaction.

The bet behind it: directing agents is the same collaboration problem human teams already solved with the GitHub flow — issues, isolated branches, evidence-bearing PRs, independent code review, and green CI — rather than a bespoke multi-agent state machine.

## Supported Executors

The main session is an Antigravity orchestrator, which dispatches workers and independent gating reviewers across two executor implementations ([ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)):

- **Codex CLI (`--implementation codex`, default)**: Runs workers (`gpt-6.1-sol` at `xhigh`) in an OS-enforced `workspace-write` sandbox (bubblewrap/AppArmor on Linux) rooted at the lane worktree, and runs gating reviewers (`gpt-6.1-sol` at `high`) in an independent disposable clone of the pinned PR head.
- **Native Antigravity Subagents (`--implementation agy`)**: Spawns workers and clean-context reviewers directly inside Antigravity via `invoke_subagent` (`Model="inherit"` by default, preserving your active session model and thinking effort). Continuations and verdicts flow asynchronously via `send_message` with reactive wakeup (no polling loops).

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

   The agent should state its orchestrator role, collaboration chain (`Restate before acting`), authority boundaries, and workflow triggers.

### For Codex CLI Lanes

No separate plugin installation inside Codex is needed: `scripts/dispatch` injects `reference/worker.md` or `reference/reviewer.md`, the unified `# Task packet`, helper model defaults, and `hooks/pre-tool-use` directly into each `codex exec` invocation.

## What You Get

- **Workflow-matched direction first** — for new features, the orchestrator gauges input clarity and runs concurrent non-blocking read-only research into existing repo capabilities and mature open-source packages; for bugs and audits, it traces root causes, siblings, cost of inaction, and fix-induced complexity *before* judging whether a fix is worth making (including leaving tolerable minor issues alone). Viable options are compared neutrally before any recommendation.
- **Conflict-free parallel lanes** — one leaf issue = one branch = one worktree (`.agents/worktrees/<issue>-<slug>`) = one green PR. Release versions are bumped at release time rather than on ordinary PRs, keeping concurrent lanes free of manifest conflicts.
- **Active-verification code review & 2-round convergence** — a clean-context Senior Code Reviewer (`reference/reviewer.md`) combines static diff analysis with targeted verification probes in isolated `/tmp` or scratch directories within three hard red lines, returning `Approve | Request changes` (`### Verdict`, `### Blocking`, `### Notes`). `Notes` never block or trigger rework; if 2 fix rounds fail to converge, the orchestrator stops looping and escalates to you.
- **Guarded integration** — `scripts/guard merge` verifies an `Approve` verdict (or human-authorized `merge-as-is` ruling), green two-parent `merged-result` CI, and exact head identity or pure conflict-free git-tree rebase equality.

## How You Use It

- **Day to day** — describe a feature, bug, or audit question. The orchestrator restates your intent, investigates or scopes proportionally, confirms the plan with you, dispatches isolated lanes, and returns reviewed, CI-green PRs with final-state command evidence.
- **Starting something new** — settle outcomes in `docs/PRD.md` and shared boundaries in `docs/architecture.md` when warranted; small prototypes and 1–2 line fixes skip heavy ceremony.
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
plugin.json      Antigravity plugin manifest (v1.5.0)
hooks.json       Lifecycle hook declarations (SessionStart, PreInvocation, PreToolUse)
hooks/           SessionStart & reverse-tail PreInvocation context delivery, dual-protocol PreToolUse guard
scripts/         Deterministic lane dispatcher, stateless review-packet publisher, and guarded merge CLI
reference/       Concise role maps (orchestrator.md, worker.md, reviewer.md), executor guides
                 (harness-codex.md, harness-antigravity.md), hygiene rules (in-repo-writes.md,
                 where-it-goes.md), and trigger-loaded templates (prd, architecture, adr, design-spec, CI)
docs/            PRD.md, architecture.md, and ADRs (0000–0003, including post-compaction & Harness Engineering alignment)
```

## License

MIT.
