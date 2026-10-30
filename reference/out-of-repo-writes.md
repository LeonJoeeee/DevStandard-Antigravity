# Where a write goes when it is not in the repo

Start with `reference/where-it-goes.md` to establish destination authority. A tool's documented
cache is an established destination; an invented hidden directory is still invented. This page
adds the requirements for external writes. Repository documentation admission belongs to
`reference/in-repo-writes.md`; final tree accounting belongs to your role page.

## Three kinds of write, one rule each

**1. Downloads, environments, tool clones** — use the tool's documented cache when available,
whether the material serves one task or many. Otherwise put task-ephemeral material in scratch.
For material to keep, use a cache root already authorized for this project, which its `AGENTS.md`
or `GEMINI.md` may relay (`reference/repo-agents-md.md`). An evictable cache cannot hold the only
durable copy of must-keep material. If no established external home qualifies, a worker stops and
returns to the main session; the main session asks the human.

**2. A deploy root or runtime state** — establish the project's destination under the placement
rule, then document it in the repo's `AGENTS.md`, `GEMINI.md` or architecture before writing there.
Declare retention too: which copies stay, which are removed, and when. Keep the previous releases
needed for rollback under `reference/deployments.md`. A new line in a document relays existing or
human-chosen authority; it cannot authorize a root the change invented.

**3. Scratch, drops, and task-local deliverables** — use the scratch named by the harness. On
Antigravity this is `<appDataDir>/brain/<conversation-id>/scratch` or the named scratch directory;
without a harness-named location, use one dedicated `mktemp -d` directory per task. A process worker
follows `reference/worker.md` and does not assume the invoking session's scratch is writable.
Dispatcher lifecycle scratch stays until lane cleanup under `reference/orchestrator.md`'s
Dispatching to an executor section. A Codex `-o` result is ephemeral output written by the CLI,
outside the agent sandbox, into dispatcher scratch under that section.

Publish durable results to the issue, PR or established destination. Release deliverables follow
the placement rule and release pipeline. The Desktop and `$HOME` are never drop targets unless the
human names one. Resolve any must-keep artifact's durable home before its scratch, worktree or cache
can disappear.

## Say where you wrote

Name every durable external write in the PR description, or at handback when there is no PR:
the path, the rule that admitted it, and why. This includes writes performed by session commands,
which a diff cannot show. A reviewer asks for the disclosure when the task plainly needed external
storage but the report names none.
