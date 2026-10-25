# 0001 — Antigravity host with native and Codex executors

Status: Accepted (2026-10-21); Amended (2026-10-22); Amended by 0002 (2026-10-22); Amended (2026-10-25).

## Context

DevStandard originated on Claude Code (`DevStandard-ClaudeCode`). Across the project's history,
supporting multiple main-session hosts within a single repository proved to be a persistent source of
architectural friction:

1. **The dual-host anti-pattern (ADRs 0045, 0056, 0063):** ADR 0045 removed Codex host packaging to
   eliminate dead packaging and split delivery paths. ADR 0056 attempted to restore Codex host
   packaging within the same repository, introducing duplicate manifests (`.claude-plugin/` and
   `.codex-plugin/`), colliding marketplace definitions, complex conditional branches in lifecycle
   hooks, diverging size budgets, and fractured CI test matrices. ADR 0063 definitively resolved the
   churn by declaring Claude Code the sole main-session host in that repository and keeping Codex
   strictly as a dispatched executor.

2. **Distinct Antigravity runtime contracts:** Antigravity (`agy`) provides a distinct agent
   architecture:
   - Plugin manifest: root `plugin.json` declaring name, version, description, and hooks.
   - Hook declaration: `hooks.json` mapping events (`SessionStart`, `PreToolUse`) to scripts.
   - Context delivery: `SessionStart` requires structured JSON output declaring an `injectSteps` array
     (e.g., `{"injectSteps": [{"stepType": "instruction", "content": ...}]}`) rather than unstructured
     text concatenation.
   - Tool inspection: Antigravity tool invocations arrive as camelCase JSON (`toolCall.name`,
     `toolCall.arguments`) rather than snake_case JSON (`tool_name`, `tool_input`).
   - Native subagent harness: Antigravity provides `invoke_subagent` with distinct model tiers
     (`Model="flash"` / `gemini-3.8-flash` and `Model="pro"` / `gemini-4-argon`), continuation via
     `send_message`, and reactive wakeup without polling.

Attempting to force Antigravity host packaging into `DevStandard-ClaudeCode` would revive the exact
dual-host failure modes documented in ADRs 0045, 0056, and 0063.

## Decision

1. **Standalone repository:** Found `devstandard-agy` as an independent repository specifically
   tailored for Antigravity as the primary orchestrator session.
2. **Native Antigravity host:** Package DevStandard via Antigravity's native plugin architecture:
   - Root `plugin.json` and `hooks.json`.
   - `hooks/session-start` delivering `reference/orchestrator.md` inline into Antigravity context via
     the native `injectSteps` format, with multi-part reassembly ensuring byte-exact delivery.
3. **Dual-protocol PreToolUse guard:** Implement `hooks/pre-tool-use` to parse both Antigravity
   camelCase `toolCall` JSON and Codex snake_case `tool_name` JSON, providing uniform role word-list
   refusals across heterogeneous executors.
4. **Hybrid executor architecture:** Dispatches three executor implementations under the Antigravity
   orchestrator:
   - **Codex CLI (`--implementation codex`, default):** Runs in an OS-enforced sandbox
     (`workspace-write` with bubblewrap/AppArmor) for workers, and an independent disposable pinned
     checkout for reviewers. Provides hard OS filesystem protection.
   - **Native Antigravity Subagents (`--implementation agy`):** Dispatches directly within Antigravity
     using `invoke_subagent`. Uses `Model="flash"` (`gemini-3.8-flash`) at `max` effort for workers,
     and `Model="pro"` (`gemini-4-argon`) at `medium` effort for clean-context reviewers. Continuation
     and reports flow via `send_message` with reactive wakeup.
   - **Antigravity CLI (`--implementation agy-cli`):** Dispatches headless `agy` processes
     communicating over stream-json on stdin/stdout with `--dangerously-skip-permissions`.

## Consequences

- `DevStandard-ClaudeCode` and `devstandard-agy` remain completely decoupled, each optimized for its
  native host harness without compromises, conditional manifest branches, or split CI suites.
- Antigravity users obtain the full DevStandard discipline (one orchestrator, N parallel worker lanes,
  Goal/Floor/Notes review, green CI gate, and superpowers craft integration).
- The hybrid executor model combines the hard OS-level sandboxing of Codex CLI with the native speed
  and model flexibility of Antigravity subagents.

**Amendment (2026-10-22):** Simplify Antigravity execution to native subagents (`--implementation agy`) alongside Codex CLI (`--implementation codex`), removing the headless Antigravity CLI executor (`--implementation agy-cli`). Both native worker and reviewer roles are anchored to `pro` (because first-pass implementation quality in the worker matters at least as much as review, and `invoke_subagent` exposes only tier aliases without concrete model/effort controls). Antigravity task-local helpers are consolidated to a two-tier (`pro` / `flash`) routing table without unverified concrete-model mappings.

**Amendment (2026-10-22, issue #7):** Anchor native Antigravity subagents (`worker`, `reviewer`, arbitration, and non-mechanical task-local helpers) to `inherit` (`Model="inherit"`) instead of `pro`, while keeping `flash` for mechanical/very simple task-local helpers (with `pro` remaining an explicit tier option only when a lighter parent session needs to step up). In Antigravity (`agy`), session thinking effort is encoded directly into the parent session's active model variant (e.g., `Gemini 4 Argon (High)`); calling `invoke_subagent` with `Model="inherit"` (`tier == 1` in `modelutils.ResolveModelForTierFromConfig`) preserves the parent conversation's exact `(model, effort)` selection, whereas `Model="pro"` overrides the parent selection with the server's default `tiered_pro_experiences` preset.

**Amendment (2026-10-22, issue #11):** Correct the runtime facts in Context's Antigravity contracts
and Decision's context-delivery and tool-guard descriptions. Antigravity fires `SessionStart` at
new-session initialization (`InvocationNum == 0 && InitialNumSteps == 0`). The hook delivers
`reference/orchestrator.md` whole, with a plugin-root preamble, in a single step using
`{"injectSteps": [{"systemMessage": {"systemMessage": ...}}]}`; the original instruction/content
shape and multi-part splitting claims do not describe the runtime. Antigravity `PreToolUse`
delivers commands in `toolCall.args.CommandLine`; `toolCall.arguments` is accepted as a fallback
when `args` is absent or null. The hook exits `0` and emits JSON `{"decision": "deny", "reason": ...}`
for refusals or `{"decision": "allow"}` for admissions. These are factual corrections; the host and
executor decision stands.

**Amendment (2026-10-22, see 0002):** Extend the hook declaration and context-delivery descriptions
with post-compaction restoration. `hooks.json` registers `PreInvocation` alongside `SessionStart`,
calling `hooks/session-start --pre-invocation`. SessionStart still delivers the whole orchestrator
page at initialization. PreInvocation restores the same preamble and complete page in one
`injectSteps` `systemMessage` step when the transcript's latest `CHECKPOINT` is newer than its last
DevStandard `SYSTEM_MESSAGE`, including a missing-page stop warning as a delivery marker. Other
turns emit `{}`. Both context hooks suppress delivery for workers, reviewers, and helper subagents;
the host and executor decision stands.

**Amendment (2026-10-25):** Admit `claude -p` with `glm-5.3-flash-official[1m]` at `max`, using
`--dangerously-skip-permissions --no-session-persistence`, strictly as a task-local helper option
for the default and mechanical tiers in `reference/orchestrator.md`'s Model and effort table.
Both Codex and Antigravity roles may use it for those tiers; helpers whose conclusions directly
decide a merge or design continue to use their harness's native subagent tool. Claude is not a
dispatched worker or reviewer executor: `--implementation` remains `codex` or `agy`, and helpers
never go through `scripts/dispatch` or `scripts/review-packet`.

