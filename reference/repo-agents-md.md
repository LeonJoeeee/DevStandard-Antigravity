# The repo-root `AGENTS.md`

Keep the project's first-principles core need and concise operational facts where every fresh-context
session reads them automatically: the repository's native `AGENTS.md`, respecting existing `AGENTS.md`
/ `GEMINI.md` instructions. Antigravity and Codex load these files before task work. Maintain each
fact at its established source; do not duplicate content across both files or install a managed method
block in `AGENTS.md`.

The file belongs to the repository owner. DevStandard recommends structure and soft prose guidance; it
does not gate changes on mechanical length or content rules. Shared system structure, decision history,
and task status have their own homes (`docs/architecture.md`, `docs/adr/`, and GitHub issues).

## `## Core need` (at the top)

Place `## Core need` first in `AGENTS.md` (or in the established root `GEMINI.md` of an adopted
repository, never duplicated across both), distilled after actively drilling down with the human across
turns to uncover first-principles needs and real-world pain points (`reference/orchestrator.md` §3):

- Write natural prose — suggested ~300–1000 CJK characters or ~200–700 English words (soft guidance,
  no mechanical length gate) — substantial enough that every orchestrator, worker, reviewer, and helper
  understands the concrete real-world pain points, failure modes, and constructive direction ("the real
  need is X rather than Y") and sees how its work serves that need.
- Avoid surface feature lists, absolutist product dogma ("non-negotiable guarantees", "must never"
  product bans that trigger LLM zealotry), and module, interface, or implementation details (which
  belong in `docs/architecture.md` and issues). Update `## Core need` in the same change when the human
  reshapes project direction.

## Operational sections (include only when real facts exist)

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

Founded projects create repo-root `AGENTS.md` at founding (`reference/architecture.md`) with
`## Core need`, adding operational sections (`Commands`, `Gotchas`, `New worktree`, `Record language`)
only when real operational facts exist — skip empty operational headings or a transcription of CI that
adds nothing, and record project-specific gotchas only after real trouble surfaces (`reference/in-repo-writes.md`).
In adopted repositories, add or reconcile `## Core need` and operational discoveries through ordinary
branch/PR changes, replacing stale guidance while respecting owner-chosen content. The orchestrator's
Cleanup and release section owns reconciliation at task or parent-effort closure, including manual
closure and cancellation.

## Example

```markdown
# <Project> — repo notes for agents

## Core need
<natural prose (~300–1000 CJK chars / ~200–700 English words): real-world pain points, why naive approaches fail, and constructive "the real need is X rather than Y" direction without module/interface detail>

## Commands
- install: <command>
- test: <command>
- run: <command>

## Gotchas
- <real local/CI difference or pitfall observed in practice>
- <cache or deploy root already assigned to this project or chosen by the human>

## New worktree: copy these untracked files
- <path; or omit operational sections until real operational facts exist>

Architecture: see docs/architecture.md. Decisions: docs/adr/ unless the architecture points elsewhere. Tasks: GitHub issues.
```
