# DevStandard's Antigravity executor (Native subagents)

Antigravity hosts the method's main orchestrator session
([ADR 0001](../docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)). Dispatched workers
and independent gating reviewers can execute on Antigravity as native subagents
(`--implementation agy`): spawned inside the orchestrator session via `invoke_subagent` and
continued via `send_message`.

`reference/orchestrator.md` owns executor selection and model routing; `reference/reviewer.md` owns
the review contract and three hard red lines; and `# Task packet` delivers the runtime lane, scratch,
helper, and return instructions directly to each subagent.

## Native Antigravity subagents (`--implementation agy`)

Native subagents execute inside the host Antigravity environment without spawning an external CLI
process. Antigravity registers native subagents at spawn under
`.system_generated/subagents/<conversationId>.json`. DevStandard lifecycle hooks inspect this
registry via `scripts/hard_edges.py`: `SessionStart` suppresses `reference/orchestrator.md`
injection for all subagents, `PreInvocation` restores `reference/worker.md` after compaction only for
explicitly dispatched native workers while keeping reviewers, `research` subagents, and task-local
helpers suppressed, and `PreToolUse` enforces each role's command word list (`worker` or `reviewer`).

Load each prepared `agent-spawn.json` as `spawn` and unpack its `type_name`, `role`, `model`, and
`prompt` fields into `invoke_subagent`. Pass `spawn["prompt"]` (never the raw JSON file) and
preserve `spawn["model"]` so explicit dispatch overrides take effect. Keep `spawn["role"]` intact so
the registry hooks distinguish dispatched native workers (`"Issue <N> worker"`) from reviewers and
task-local helpers.

### Worker dispatch and continuation

- **Dispatch:** run `scripts/dispatch <issue> --purpose worker --base origin/main --implementation agy`,
  which prepares `agent-spawn.json` in scratch. Spawn the worker via:
  ```python
  invoke_subagent(TypeName=spawn["type_name"], Role=spawn["role"], Model=spawn["model"], Prompt=spawn["prompt"])
  ```
  `spawn["role"]` is `"Issue <N> worker"` and default `model` is `inherit`. Record the returned
  `conversationId` on the issue as durable dispatch evidence.
- **Continuation:** on a fix or rebase continuation (`--continue --resume <conversationId> --brief <file>`),
  `scripts/dispatch` prepares the continuation prompt; resume the same worker via:
  ```python
  send_message(Recipient="<conversationId>", Message=spawn["prompt"])
  ```
  Reactive wakeup resumes the orchestrator automatically when the worker replies.
- **Compaction recovery:** if a dispatched native worker's context compacts, `hooks/session-start --pre-invocation`
  automatically restores `reference/worker.md` after the transcript `CHECKPOINT`; the worker recovers
  dynamic `# Task packet` fields from the issue's `devstandard-dispatch-v1` receipt or local
  transcript (`reference/worker.md`).

### Stateless gating review and verdict publication

- **Review preparation:** run `scripts/review-packet start <pr> --issue <issue> --output <session-scratch> --implementation agy`.
  `start` verifies green checks, writes `packet.json`, `packet.txt`, and `attempt.json` in
  `<session-scratch>`, and prepares `agent-spawn.json` with zero pre-flight PR comment noise. Spawn
  the fresh reviewer via:
  ```python
  invoke_subagent(TypeName=spawn["type_name"], Role=spawn["role"], Model=spawn["model"], Prompt=spawn["prompt"])
  ```
  `spawn["role"]` is `"Issue <N> reviewer"` and default `model` is `inherit`.
- **Reviewer boundaries:** native reviewers inherit the host workspace; under `reference/reviewer.md`,
  they never modify repository worktrees or refs, never run `gh` writes, and place any temporary
  verification probe files strictly inside an isolated `mktemp -d` under `/tmp` or session scratch.
- **Publication:** when the reviewer returns its verdict via `send_message`, save it whole to
  `<session-scratch>/verdict.md` and publish one `## Code Review — round N` comment with:
  ```sh
  <plugin>/scripts/review-packet publish <pr> --issue <issue> --output <session-scratch> --verdict <session-scratch>/verdict.md
  ```
