# Where every file goes

Read this before choosing a concrete output destination. Use the rule below for placement,
`reference/in-repo-writes.md` for documentation admission, and `reference/out-of-repo-writes.md`
for external-write requirements.

## The placement rule

<!-- BEGIN PLACEMENT RULE -->
**Use an established destination for this project's files:** existing code or configuration, a
tool's documented default, or a place the human chose. A directory's existence alone grants no
authority to use it. Project documents may relay that authority; neither a document nor code or
configuration introduced by the same change can authorize a destination the change invented.
Handoff and session-state documents never establish destination authority, even when tracked or
explicitly admitted.

Product output paths are part of product design. Designing an export directory or a CLI's
`--output` does not send the product's users into the development repository. Choosing the actual
path when exercising that interface, or a host directory for a volume, is your own write and follows
this rule. A same-change configuration authorizes the interface design, not that host destination.

**When no authority names a place, use the project**, with a gitignored directory for material the
repository does not maintain. Documentation still needs admission. Files that die with the task
belong in the harness's scratch or one dedicated `mktemp -d` directory. Never invent an external
place under `$HOME`, on the Desktop, or elsewhere.

**Stop when an established home is missing for any of these:** a worker returns to the main
session; the main session asks the human.

- **Secrets or confidential data**, including generated credentials, personal data, private exports,
  and licensed material. Never commit or publish them, even inside another kind of artifact.
  Gitignored project paths do not provide containment: image builds and archives can still copy them.
- **Persistent or operational application state**, including a service's data, a desktop app's
  database, and sockets, PID files, locks or spools needed by a program that outlives the task.
  A disposable test daemon's files belong in scratch. A worktree or installation directory is not
  a default state root: it may be removed, replaced, or read-only.
- **Release deliverables.** Never commit them as by-products or attach them to an issue merely to
  give them a home.

**A must-keep artifact needs durable storage.** A disposable worktree, scratch, or evictable cache
cannot hold its only durable copy. Resolve a missing durable home before writing or teardown;
use the same stop-and-ask route above. A tool cache is suitable for a re-fetchable copy.

**Disclose destinations.** Committed files are preserved in the branch. Account for retained files
inside the worktree under your role's handback rules, and name durable external writes under
`reference/out-of-repo-writes.md`. Resolve preservation before cleanup.
<!-- END PLACEMENT RULE -->
