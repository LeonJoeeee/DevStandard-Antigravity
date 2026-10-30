# The repo-root `AGENTS.md`

Keep concise operational facts where a fresh-context session reads them: the repository's native
`AGENTS.md`, respecting existing `AGENTS.md` / `GEMINI.md` instructions. Antigravity and Codex use
these files before task work. Maintain each fact at its established source; do not duplicate memory
across both files or install a managed method block in `AGENTS.md`.

The file belongs to the repository owner. DevStandard recommends useful notes and pointers; it
does not gate changes on the file's content or length. Architecture, decisions and task status
already have their own homes.

## Useful content

- **Commands** — install, test and run commands a session needs, consistent with CI.
- **Environment gotchas** — ports, required services, local/CI differences, and established cache
  or deploy roots. A root must already be authorized for this project's files or chosen by the
  human; recording it relays that authority (`reference/where-it-goes.md`).
- **Untracked worktree inputs** — the explicit allowlist of files a new worktree must copy, such
  as local configuration, under `reference/orchestrator.md`'s Worktree lifecycle section.
- **Record language**, when the durable record is not English. A repo-wide declaration in root
  `AGENTS.md` or `GEMINI.md` governs the whole record. Without one, English applies. Declare and
  follow an established non-English record rather than starting a mixed record. Translations are
  marked mirrors naming their canonical source and updated in the same diff.

Create the file only when useful operational content exists, under `reference/in-repo-writes.md`.
Skip an empty template or a transcription of CI that adds nothing. Write discoveries back through
ordinary branch/PR changes, replacing stale guidance while respecting owner-chosen content. The
orchestrator's Cleanup and release section owns reconciliation at task or parent-effort closure,
including manual closure and cancellation.

## Example

```markdown
# <Project> — repo notes for agents

## Commands
- install: <command>
- test: <command>
- run: <command>

## Gotchas
- <service or local/CI difference>
- <cache or deploy root already assigned to this project or chosen by the human>

## New worktree: copy these untracked files
- <path; or state that all load-bearing inputs are tracked>

Architecture: see docs/architecture.md. Decisions: docs/adr/ unless the architecture points elsewhere. Tasks: GitHub issues.
```
