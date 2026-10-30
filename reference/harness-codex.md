# DevStandard's Codex CLI executor

Codex does not host the method: the orchestrator is an Antigravity session
([ADR 0001](docs/adr/0001-antigravity-host-with-native-and-codex-executors.md)). It dispatches Codex
as a CLI process — `--implementation codex` for a worker or an independent gating reviewer — and this
page maps that executor's mechanics for the dispatching orchestrator. Method paths resolve from the
installed plugin root.

## Dispatching Codex

Dispatch a worker with `scripts/dispatch ... --implementation codex --wait`, and commission a gating
review through `scripts/review-packet start ... --implementation codex --wait`, which runs a fresh
Codex CLI process and publishes one `## Code Review — round N` comment upon a valid return. The CLI
must be installed and authenticated. `reference/orchestrator.md`'s Dispatching to an executor
section owns when Codex is chosen and its permission boundaries, while `# Task packet` delivers the
concise runtime environment, scratch, helper, and return notes directly to the dispatched process.

**Verified Codex mechanics.** Run Codex CLI as the dispatch process's child with `--wait` inside a
harness background task. A linked worktree requires explicit write grants (`--add-dir`) to both the
common `.git` directory and `.git/worktrees/<name>`; the first grant is not recursive. Codex's
`review` subcommand cannot take DevStandard's review contract and sandbox controls, so gating review
uses `codex exec`. Inspect actual output shape and exit status before treating a return as valid.

A CLI reviewer runs with `workspace-write` and network access inside an independent disposable clone
of the packet's pinned head under run scratch (`TMPDIR` or the system temporary directory). Its Git
metadata lives beside that clone, and the only extra write grant points to that copy's metadata so
probes or fetches never alter the lane's refs or objects. `scripts/dispatch` creates the clone,
restores the upstream `origin` URL, and removes the copy before returning, including on nonzero exit
or cancellation; setup failure returns an error without launching a reviewer.

Targeted verification probes stay inside that disposable clone or an isolated `mktemp -d`, and
verdicts always judge the pinned Git objects under the three hard red lines in
`reference/reviewer.md`. The caller publishes the verdict; the reviewer `gh` write-flag hook remains
a guardrail alongside the written contract.

For MCP access in a dispatched Codex process, see `mcp_tool_admission` in `scripts/dispatch`. Do not
attach an MCP server a worker must not reach to a session running workers; when a visible tool is
refused, the worker follows `reference/worker.md`'s harness-limit rule.

Codex CLI dispatch's hook-trust bypass is invocation-wide, so every hook source Codex has enabled
runs in the child (remove any legacy pre-2.0 DevStandard Codex plugin via `codex plugin remove`).
Retain run scratch until lane cleanup (`scripts/dispatch --help`). Python dispatch supports
macOS and Linux; Windows is not qualified.
