# DevStandard's Antigravity executors (Native and CLI)

Antigravity hosts the method's main orchestrator session ([ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)). Dispatched workers and independent gating reviewers may execute on Antigravity in two distinct implementations:

- **Native Antigravity subagents (`--implementation agy`)**: Dispatched directly inside the orchestrator session via `invoke_subagent` and continued via `send_message`.
- **Antigravity CLI executor (`--implementation agy-cli`)**: Dispatched as an independent headless subprocess running the `agy` command with stream-json communication.

`reference/orchestrator.md` owns selection and role routing, and `reference/code-review-prompt.md` owns review authority.

## Native Antigravity subagents (`--implementation agy`)

Native subagents execute within the host Antigravity environment without spawning an external CLI process.

### Worker dispatch and continuation
- **Dispatch**: The orchestrator runs `scripts/dispatch <issue> --purpose worker --base origin/main --implementation agy`, which prepares `agent-spawn.json` in session scratch containing the assembled prompt and spawn parameters. The orchestrator invokes the subagent via:
  ```json
  invoke_subagent(TypeName="self", Model="flash", Prompt=<content-of-agent-spawn.json>)
  ```
  The worker anchor model is `flash` (`gemini-3.8-flash` at `max` effort). The orchestrator records the returned `conversationId` handle on the issue as durable dispatch evidence.
- **Continuation**: On a goal-gap or rebase continuation (`--continue --resume <conversationId>`), `scripts/dispatch` prepares the continuation prompt in session scratch. The orchestrator resumes the existing subagent in the same lane by calling:
  ```json
  send_message(Recipient="<conversationId>", Message=<continuation-prompt>)
  ```
  The reactive messaging system automatically wakes the orchestrator when the worker responds, eliminating the need for status polling.

### Gating review and verdict publication
- **Review dispatch**: Commissioned via `scripts/review-packet start <pr> --issue <issue> --implementation agy`. `start` prepares `agent-spawn.json` in session scratch. The orchestrator calls:
  ```json
  invoke_subagent(TypeName="self", Model="pro", Prompt=<content-of-agent-spawn.json>)
  ```
  The reviewer anchor model is `pro` (`gemini-4-argon` at `medium` effort).
- **Read-only contract**: Native reviewers inherit the caller's session directory / workspace. By written contract, the reviewer is strictly read-only toward the repository and remote: no file writes in the lane or main checkout, no remote writes, and no issue or PR edits. Antigravity's built-in file writers (`write_file`, `edit_file`) remain denied by role contract.
- **Verdict return**: The reviewer returns its whole verdict via `send_message` back to the caller. The orchestrator saves the verdict to `<session-scratch>/verdict.md` and publishes it to GitHub with:
  ```sh
  scripts/review-packet publish <pr> --issue <issue> --attempt <comment-id> --verdict <session-scratch>/verdict.md
  ```

## Antigravity CLI executor (`--implementation agy-cli`)

Dispatched as a headless CLI process executing `agy`.

### Prerequisites and permissions
- `agy` must be on PATH and authenticated (`~/.gemini/antigravity-cli/antigravity-oauth-token`). The normal host HOME must permit conversation and artifact persistence.
- Superpowers skills must be available in Antigravity's plugin roots.
- Both worker and reviewer roles run with `--dangerously-skip-permissions` (`permission_mode: always-proceed`). Every configured and enabled agy MCP server is callable; there is no admission layer. The operator must not configure a server a role must not reach.
- This represents host/tool permission access, not an OS sandbox restricting the worker to its lane.

### Headless stream-json input and output
- Worker anchor is `gemini-3.8-flash` at `max` effort; reviewer anchor is `gemini-4-argon` at `medium` effort. Dispatch passes `--model <model>-<effort>` (e.g. `gemini-3.8-flash-max` or `gemini-4-argon-medium`) and omits `--effort`.
- Full briefs and review packets use `--input-format stream-json --output-format stream-json` with one NDJSON message on stdin:
  ```json
  {"event":"user","message":{"content":"<whole brief or packet>"}}
  ```
- Events and exit: The `init` event names conversation and permission mode; the final `{"event":"result","result":{...}}` event carries `status`, `response`, `conversation_id`, and `usage`.
- Nonzero exit, any non-empty `denied_actions`, unsuccessful status, or missing result indicates harness failure.
- A CLI reviewer runs in an independent one-off checkout of the pinned head; caller publishes the whole verdict upon return.
- Continuation uses `--conversation <recorded-id>` in the same lane.
- Python dispatch supports macOS/Linux; Windows is not qualified.

<!-- BEGIN ANTIGRAVITY WORKER MECHANICS -->
## Worker mechanics

`scripts/dispatch` delivers this section with `reference/worker.md` to every Antigravity worker (both native subagents and CLI processes). That page carries the contract, including what a worker does when the packet cannot be recovered; this section describes the Antigravity harness beneath it.

### Native Antigravity subagent (`--implementation agy`)
- **Starting environment and lane boundary**: A native subagent begins in the caller's workspace or lane. The packet gives the assigned `Worktree` and `Branch`; the worker validates the lane (`git rev-parse --show-toplevel` equals the assigned worktree, `git-dir` differs from `git-common-dir`) and executes all file operations and commands within that worktree.
- **Task-local helpers**: Subagents spawned by a worker for its own task use Antigravity's native subagent tool (`invoke_subagent`), never another CLI process or orchestrator dispatch scripts. Helper models follow the role table: `pro` for decisions that directly decide a merge or design, `flash` for ordinary subagents, and `flash_lite` for mechanical scans.
- **Recovering the binding**: When dynamic context is lost to compaction, the native subagent recovers its binding from the latest matching `devstandard-dispatch-v1` receipt recorded on the issue or from its local conversation record in `<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`. A valid receipt must match the assigned branch and worktree exactly and contain all required packet fields.
- **Communication**: The subagent communicates progress and delivery back to the orchestrator via `send_message`.

### Antigravity CLI worker (`--implementation agy-cli`)
- **Starting environment**: The CLI process begins in its assigned lane worktree under host/tool permissions with `--dangerously-skip-permissions`. The assigned branch and worktree bound its authority; agy adds no independent OS sandbox.
- **Task-local helpers**: Task-local helpers use agy's native subagent facilities, never another CLI process or orchestrator dispatch scripts.
- **Recovering the binding**: A linked worktree on a matching `task/<issue>-...` branch uses `origin` to identify the repository. The latest matching `devstandard-dispatch-v1` process-run receipt on the issue names the lane and its absolute brief holds the packet in full. Branch and worktree must match exactly.
- **Continuation**: Continuation uses the completed receipt's `conversation_id` in the same lane.
<!-- END ANTIGRAVITY WORKER MECHANICS -->
