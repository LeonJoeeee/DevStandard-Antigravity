# Where every file goes

Read this before choosing any concrete output destination inside or outside the repository.
Repository documentation admission follows `reference/in-repo-writes.md`; final working-tree
accounting follows your role page.

## The placement rule

**Use an established destination for this project's files:** existing project code or
configuration, a tool's documented default or cache, or a path the human chose. A directory's mere
existence or an invented hidden directory grants no authority. Project documents (`AGENTS.md`,
`GEMINI.md`, `docs/architecture.md`) may relay existing or human-chosen authority, never originate
a destination; code, configuration, or docs introduced by the same change cannot authorize an
external destination the change invented; and handoff or session-state artifacts never establish
destination authority.

Product output paths (a CLI's `--output`, an export directory, or a service's configured data root)
are part of product design rather than destinations inside the development repository. Choosing the
actual host path when exercising that interface or mounting a volume during work is your own write
and follows this rule.

**When no authority names a place, stay inside the project or task scratch:** use a gitignored
project directory for unmaintained project material (documentation still requires admission), or
task scratch for ephemeral files. Never invent external drop targets under `$HOME`, on the Desktop,
or at arbitrary host paths unless the human names one.

**Stop when an established home is missing for any of these** — a worker returns to the main
session; the main session asks the human:

- **Secrets or confidential data** (credentials, generated tokens, personal data, private exports,
  licensed corpora). Never commit or publish them, even inside another artifact; `.gitignore` does
  not prevent image builds or archives from copying them.
- **Persistent or operational application state** (service data, app databases, and runtime
  sockets, PID files, locks, or spools that outlive the task; disposable test-daemon files belong
  in scratch). Worktrees and replaceable or read-only install directories are not state roots.
- **Release deliverables.** Follow the release pipeline; never commit them as by-products or attach
  them to an issue merely to store them.

## External destinations and disclosure

- **Downloads, environments, and tool clones:** use the tool's documented cache when available,
  whether serving one task or many; otherwise put task-ephemeral material in scratch. Must-keep
  material needs a durable project-authorized root (which `AGENTS.md` or `GEMINI.md` may relay
  under `reference/repo-agents-md.md`). A disposable worktree, scratch, or evictable tool cache is
  suitable for re-fetchable copies, never for the sole copy of must-keep material — resolve a
  missing durable home via the stop-and-ask route before writing or teardown.
- **Deploy roots and runtime state:** establish authority under the placement rule, then document
  the root and retention policy (including rollback releases kept under `reference/deployments.md`)
  in `AGENTS.md`, `GEMINI.md`, or `docs/architecture.md` before writing there.
- **Scratch and dispatcher output:** use the harness-named scratch (`<appDataDir>/brain/<conversation-id>/scratch`
  on Antigravity) or one dedicated `mktemp -d` per task; process workers follow `reference/worker.md`
  without assuming caller scratch is writable, and dispatcher scratch stays until lane cleanup
  (`reference/orchestrator.md`). Publish durable task results on the issue or PR.
- **Disclose durable writes:** committed files live in the branch, and retained worktree files are
  accounted for at handback. Name every durable external write in the PR description (or at
  handback when there is no PR) — path, admitting rule, and why — including writes performed by
  session commands that `git diff` cannot show.
