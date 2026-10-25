# DevStandard's Antigravity executor (Native subagents)

Antigravity hosts the method's main orchestrator session ([ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)). Dispatched workers and independent gating reviewers execute on Antigravity as native subagents (`--implementation agy`): dispatched directly inside the orchestrator session via `invoke_subagent` and continued via `send_message`.

`reference/orchestrator.md` owns selection and role routing, and `reference/code-review-prompt.md` owns review authority.

## Native Antigravity subagents (`--implementation agy`)

Native subagents execute within the host Antigravity environment without spawning an external CLI process. Antigravity registers native subagents at spawn under `.system_generated/subagents/<conversationId>.json`. DevStandard lifecycle hooks inspect this registry via `subagent_role(event)` in `scripts/hard_edges.py`: `SessionStart` and `PreInvocation` suppress `reference/orchestrator.md` injection for subagents, and `PreToolUse` enforces the role's command word list (`worker` or `reviewer`).

Load each prepared `agent-spawn.json` as `spawn` and unpack its `type_name`, `role`, `model`, and
`prompt` fields into `invoke_subagent`. Pass the prompt field rather than the raw JSON file, and
preserve `spawn["model"]` so explicit dispatch overrides take effect. The role labels below are
required: `subagent_role()` uses the registered role to distinguish native workers from reviewers.

### Worker dispatch and continuation
- **Dispatch**: The orchestrator runs `scripts/dispatch <issue> --purpose worker --base origin/main --implementation agy`, which prepares `agent-spawn.json` in session scratch containing the assembled prompt and spawn parameters. The orchestrator invokes the subagent via:
  ```python
  invoke_subagent(TypeName=spawn["type_name"], Role=spawn["role"], Model=spawn["model"], Prompt=spawn["prompt"])
  ```
  Pass `spawn["role"]` as `Role="Issue <N> worker"`. The worker anchor model is `inherit`. The orchestrator records the returned `conversationId` handle on the issue as durable dispatch evidence.
- **Continuation**: On a goal-gap or rebase continuation (`--continue --resume <conversationId>`), `scripts/dispatch` prepares the continuation prompt in session scratch. The orchestrator resumes the existing subagent in the same lane by calling:
  ```json
  send_message(Recipient="<conversationId>", Message=<continuation-prompt>)
  ```
  The reactive messaging system automatically wakes the orchestrator when the worker responds, eliminating the need for status polling.

### Gating review and verdict publication
- **Review dispatch**: Commissioned via `scripts/review-packet start <pr> --issue <issue> --architecture-level no --output <session-scratch> --implementation agy` (use `--architecture-level yes` for an architecture-level change). `start` prepares `agent-spawn.json` in session scratch. The orchestrator calls:
  ```python
  invoke_subagent(TypeName=spawn["type_name"], Role=spawn["role"], Model=spawn["model"], Prompt=spawn["prompt"])
  ```
  Pass `spawn["role"]` as `Role="Issue <N> reviewer"`. The reviewer anchor model is `inherit`.
- **Read-only contract**: Native reviewers inherit the caller's session directory / workspace. By written contract, the reviewer is strictly read-only toward the repository and remote: no file writes in the lane or main checkout, no remote writes, and no issue or PR edits. Antigravity's built-in file writers (`write_file`, `edit_file`) remain denied by role contract.
- **Verdict return**: The reviewer returns its whole verdict via `send_message` back to the caller. The orchestrator saves the verdict to `<session-scratch>/verdict.md` and publishes it to GitHub with:
  ```sh
  scripts/review-packet publish <pr> --issue <issue> --attempt <comment-id> --verdict <session-scratch>/verdict.md
  ```

<!-- BEGIN ANTIGRAVITY WORKER MECHANICS -->
## Worker mechanics

`scripts/dispatch` delivers this section with `reference/worker.md` to every Antigravity worker. That page carries the contract, including what a worker does when the packet cannot be recovered; this section describes the Antigravity harness beneath it.

### Native Antigravity subagent (`--implementation agy`)
- **Starting environment and lane boundary**: A native subagent begins in the caller's workspace or lane. The packet gives the assigned `Worktree` and `Branch`; the worker validates the lane (`git rev-parse --show-toplevel` equals the assigned worktree, `git-dir` differs from `git-common-dir`) and executes all file operations and commands within that worktree.
- **Task-local helpers**: Use Antigravity's native subagent tool (`invoke_subagent`) with the model the packet's `Helpers:` line gives: `inherit` for merge/design decisions and the default, `flash` for mechanical or very simple work. Default and mechanical helpers may instead run `claude -p --model "glm-5.3-flash-official[1m]" --effort max --dangerously-skip-permissions --no-session-persistence "<prompt>"`. Merge/design-deciding helpers use the native tool. Helpers never use `scripts/dispatch` or `scripts/review-packet`.
- **Recovering the binding**: When dynamic context is lost to compaction, the native subagent recovers its binding from the latest matching `devstandard-dispatch-v1` receipt recorded on the issue or from its local conversation record in `<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`. A valid receipt must match the assigned branch and worktree exactly and contain all required packet fields.
- **Communication**: The subagent communicates progress and delivery back to the orchestrator via `send_message`.
<!-- END ANTIGRAVITY WORKER MECHANICS -->
