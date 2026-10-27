# DevStandard for Antigravity

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version: 1.3.3](https://img.shields.io/badge/version-1.3.3-green.svg)](plugin.json)

**The GitHub flow, extended to agent teams on Antigravity.**

DevStandard is a development-method plugin for [Antigravity](https://github.com/google-deepmind) (`agy`) — delivered by native session hooks (see [Install](#install)) — that orchestrates development across isolated worker lanes and can dispatch [Codex](https://developers.openai.com/codex) or native subagents. It adds the three things an agent harness doesn't do by itself:

1. **Discipline** — rules an agent won't impose on itself: settle what "done" means before starting, get designs torn apart before writing code, prove completion with concrete evidence, know when to stop and ask you;
2. **Project memory** — a PRD, an architecture doc, a decision log (ADRs), design specs for substantial changes, and a repo `AGENTS.md` (or `GEMINI.md`) only when it has commands, gotchas, a worktree copy-list, or record-language declaration to hold, so parallel sessions (and human teammates) stay aligned on *what*, *how*, and *why*;
3. **Reliable delivery of both** — `SessionStart` delivers the orchestrator's complete role reference via Antigravity hooks (`injectSteps`), and `PreInvocation` restores it after each context compaction. Dispatched workers receive their own complete role context.

The bet behind it: directing agents is the same collaboration problem humans already solved with the GitHub flow — so agents follow the **same** branches / PRs / CI / review process your team already uses, instead of an unproven agent-coordination scheme.

## Supported Executors

DevStandard separates the coordinating conversation from parallel implementation work. The main session is an Antigravity orchestrator, which dispatches workers and reviewers across two supported executor implementations:

- **Codex CLI (`--implementation codex`, default)**: Runs in an OS-sandboxed lane (`workspace-write` with bubblewrap/AppArmor) for workers, and an independent disposable one-off checkout of the pinned head for read-only gating reviewers. Provides hard OS-level write boundaries.
- **Native Antigravity Subagents (`--implementation agy`)**: Dispatches directly inside the active Antigravity environment via `invoke_subagent`. Uses `Model="inherit"` for workers and clean-context reviewers. Communication and continuation flow through `send_message` with reactive wakeup (no polling needed).

## Requirements

- **Antigravity (`agy`)**, with native plugin, SessionStart, and PreInvocation-hook support (`plugin.json`, `hooks.json`). Antigravity serves as the primary main orchestrator session ([ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)).
- **[superpowers](https://github.com/obra/superpowers)** — the craft layer. Install it alongside DevStandard (and into Codex if you dispatch Codex lanes). The role pages bind its requirements, debugging, TDD, and planning skills.
- **git** and an authenticated **[`gh`](https://cli.github.com/) CLI** for the shipped commands — the dispatcher, review packets, and guarded merge interact with GitHub through `gh`.
- **Python 3.10+** for the shipped scripts and verification gates.
- **For Codex lanes:** an installed, authenticated Codex CLI with superpowers installed into it, and, on Linux, its [sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing#prerequisites) (`bubblewrap` and scoped AppArmor profiles).

## Install

### Antigravity Plugin Installation

Install or link the `devstandard` plugin into your Antigravity plugin directory:

1. **User-level install:**
   ```bash
   mkdir -p ~/.gemini/config/plugins
   git clone https://github.com/LeonJoeeee/DevStandard-Antigravity.git ~/.gemini/config/plugins/devstandard
   ```
   Or register the path in `~/.gemini/config/plugins.json`.

2. **Workspace-level install:**
   Link or clone into your workspace:
   ```bash
   mkdir -p .agents/plugins
   git clone https://github.com/LeonJoeeee/DevStandard-Antigravity.git .agents/plugins/devstandard
   ```

3. **Install superpowers:**
   Ensure `superpowers` is installed and available in Antigravity's plugin roots so craft skills resolve.

4. **Verify installation:**
   Start a new Antigravity session and ask:
   > *"What does DevStandard tell you to do?"*

   The agent should recite the trigger rule, the core discipline, and the orchestrator workflow.

### For Codex Lanes

DevStandard does not need to be installed as a plugin inside Codex; the dispatcher injects the worker or reviewer role brief directly into the execution prompt. However, superpowers must be installed in Codex so the worker's craft bindings resolve:

```bash
codex plugin marketplace add https://github.com/obra/superpowers.git
codex plugin add superpowers@superpowers-dev
```

## What You Get

- **Set the result and why** — the orchestrator turns them into GitHub issues with explicit bounds and observable done-checks. Weight belongs to each task; a small demo earns no heavy setup ceremony.
- **Keep one responsive orchestrator** — Antigravity discusses, dispatches, accepts, and integrates. Direct edits stay small enough not to block conversation; substantive work goes to worker lanes.
- **Run workers in parallel lanes** — one task, branch, and worktree each. Codex CLI runs in an OS-enforced sandbox; native Antigravity subagents run with defined model tiers (`inherit` / `flash`) and communicate asynchronously. Workers implement, rebase, prove the final state, and deliver a green PR.
- **Accept against the goal** — a clean reviewer judges a green PR under the Goal/Floor/Notes contract. Both review and CI guard integration; architecture direction and major releases remain human-owned.
- **Automatic context delivery** — the whole orchestrator role reference arrives at session start and is restored after compaction via `hooks/session-start` (`injectSteps`). Ordinary turns between compactions add no duplicate context. Dispatched workers receive their role brief and execution craft at dispatch.

## How You Use It

**Day to day** — ask for a bug fix or a feature in an existing repo. The agent settles what "done" looks like first and closes with verifiable evidence rather than "should work now".

**Starting something new** — say what you want to build and why. The orchestrator clarifies the outcome and chooses task bounds with you. A durable project definition, shared architecture, or ADR triggers its template; a prototype does not inherit enterprise process merely because it is new.

**Working a big project in parallel** — discuss direction with one Antigravity orchestrator. It creates issues, cuts independent scopes, and dispatches N lanes through `scripts/dispatch`. Workers return evidence-bearing PRs, drive CI green, and leave their worktrees for the orchestrator. A clean reviewer judges acceptance, the guarded merge verifies the result, and the orchestrator closes the issue and cleans up the worktree. You own direction, irreversible authorization, architecture decisions, and major releases.

## What's Actually Installed

1. **SessionStart and PreInvocation Context Delivery (`hooks/session-start`)**:
   Delivers the orchestrator's self-contained page (`reference/orchestrator.md`) whole, with a plugin-root preamble, at new-session initialization in a single step: `{"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}`. Before later invocations, restores the same payload only when `transcript.jsonl` contains a `CHECKPOINT` newer than its last DevStandard `SYSTEM_MESSAGE`. Both modes suppress injection for worker, reviewer, and helper subagents ([ADR 0002](docs/adr/0002-post-compaction-orchestrator-context-re-injection.md)).

2. **Dual-Protocol PreToolUse Guard (`hooks/pre-tool-use`)**:
   Runs before tool invocations and inspects command text. It supports both:
   - Antigravity camelCase JSON (`toolCall.name`, `toolCall.args.CommandLine`, with `toolCall.arguments` as a fallback when `args` is absent or null)
   - Codex snake_case JSON (`tool_name`, `tool_input`)
   
   It enforces whole-word refusals:
   - Worker: refuses `merge` and direct pushes to default branches.
   - Orchestrator: refuses `gh pr merge` (routing to `scripts/guard merge`).
   - Reviewer: refuses `gh api` write flags.
   
   Every refusal is a helpful reminder naming the word, what the role should do instead, and which reference page to read.

3. **Shipped Tooling (`scripts/`)**:
   - `scripts/dispatch`: Prepares and dispatches workers/reviewers across Codex CLI or native Antigravity subagents.
   - `scripts/review-packet`: Assembles review packets from live Git/PR state, enforces green CI admission, and tracks review rounds.
   - `scripts/guard`: Enforces reviewed-head identity, content-unchanged rebase proofs, and clean merge operations.

## Layout

```
plugin.json      Antigravity plugin manifest
hooks.json       Hook definitions (SessionStart, PreInvocation, PreToolUse)
hooks/           Initial and post-compaction context delivery (injectSteps), dual-protocol PreToolUse guard
scripts/         Shipped machinery — fixed dispatcher, review packets, guarded merge
reference/       Self-contained orchestrator and worker role pages, harness mechanics, templates
docs/            PRD, architecture document, and architectural decision records (ADRs)
```

## License

MIT.
