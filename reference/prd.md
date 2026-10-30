# How to write the PRD

At project start, settle with the human what to build, why it matters, and what counts as done.
Use `reference/orchestrator.md`'s requirements binding for that dialogue. Keep the PRD focused on
user outcomes; put system structure in the architecture document.

## Content

- **Purpose and audience** — what this is and whom it serves.
- **Problem** — why it is worth building and what happens without it.
- **Features as user value** — what users can do, with explicit non-goals.
- **Definition of done** — concrete, mechanically checkable release criteria from which task
  done-checks derive.
- **Constraints**, when applicable — compatibility, performance, budget, deadlines, or other hard
  limits.

Keep it concise and update it in the same change when the human changes direction.

## Founding setup

Founding is the orchestrator's work. Follow this order:

1. Ask the human for the repository name and whether it is public or private, then create it.
2. Push the founding commits directly to main: the PRD, architecture, minimal code skeleton, CI and
   Dependabot files from `reference/ci-pipelines.md`, `/.agents/worktrees/` in `.gitignore`, and a
   repo-root `AGENTS.md` when there are operational facts to record.
3. Apply branch protection last with `guard protection --apply --check NAME`, naming the check
   reported by that CI. Use `scripts/guard protection --help` for provisioning; this belongs to the
   human or main session. Subsequent changes use PRs, both checks, and `scripts/guard merge`.

The architecture settled with the human supplies the skeleton's design and pre-code challenge;
founding needs no separate spec. Use real interfaces and boundaries in the minimal skeleton so
parallel tasks know where they connect. The guard has no settings file to configure; see
`reference/orchestrator.md`'s Guarded operations section.

## Template

```markdown
# <Project> — PRD

## Purpose and audience
<what this is, for whom>

## Problem
<why build it; why now>

## Features (as user value)
- <user can ...>

## Non-goals
- <what this deliberately leaves out>

## Definition of done
1. <checkable release criterion>

## Constraints
- <hard limit; omit this section if none apply>
```

The default location is `docs/PRD.md`. An adopted repository's established convention may supply
another path under `reference/in-repo-writes.md`.
