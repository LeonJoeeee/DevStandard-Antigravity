# How to write the architecture document and found a project

Once first-principles core needs are uncovered with the human (`reference/orchestrator.md` §3) and
captured in repo-root `AGENTS.md` (`reference/repo-agents-md.md`), `docs/architecture.md` describes the
shared structure and project baseline that parallel sessions build against when project scale or
multi-lane work warrants one. Keep the overview readable and focused on boundaries that change slowly;
decision history belongs in ADRs (`reference/adr.md`) and implementation detail in code.

## Content and maintenance

- State that this is the shared baseline to read before task work, and that structural, scope, or
  costly-to-reverse changes to this baseline require a public merge, human approval, and an ADR
  (`reference/adr.md`). The wording may fit the project.
- Explain broader project context, scope and explicit non-goals, main components, ownership, and
  interfaces. Add a diagram when it clarifies those boundaries.
- Name the quality goals, checkable release criteria (from which task `Done-check`s derive on larger
  projects), and hard constraints — compatibility, performance, budget, deadlines, or open release
  questions when applicable — constructively without absolutist product dogma.
- End with the decision-log location, normally `docs/adr/`, and any established mappings for method
  documents kept off their default paths. This footer is the common pointer for path consumers.

Describe the system as it exists. Keep active task plans on GitHub issues, optional shared interface or
migration contracts in `docs/specs/` (`reference/design-spec.md`), and historical decision reasoning in
ADRs (`reference/adr.md`); update `docs/architecture.md` in the same change that alters shared
structure, scope, or costly-to-reverse baseline choices, accompanied by an ADR. Avoid detail that would
make routine implementation changes stale the shared baseline.

## Founding setup

Founding is the orchestrator's work. After actively drilling down with the human across turns to
uncover first-principles core needs and real-world pain points (`reference/orchestrator.md` §3):

1. Ask the human for the repository name and whether it is public or private, then create it.
2. Push the founding commits directly to `main`: `README.md`, repo-root `AGENTS.md` with `## Core need`
   (including operational sections only when real operational facts exist; `reference/repo-agents-md.md`),
   `docs/architecture.md` (and `docs/adr/0000-record-architecture-decisions.md` under `reference/adr.md`)
   when warranted, a minimal code skeleton, CI and Dependabot files from `reference/ci-pipelines.md`,
   and `/.agents/worktrees/` in `.gitignore`.
3. Apply branch protection last with `guard protection --apply --check NAME`, naming the check reported
   by that CI (`scripts/guard protection --help`; `reference/orchestrator.md` Branch protection and
   Guarded operations sections). Subsequent changes use PRs, independent code review, green CI, and
   `scripts/guard merge`.

The baseline settled with the human (with a clean-context `inherit` pre-code challenge when interfaces
or schemas are high-cost) supplies the skeleton's design; founding needs no separate `docs/specs/`
contract. Use real interfaces and boundaries in the minimal skeleton so parallel tasks know where they
connect. The guard has no settings file to configure.

## Split on zoom

When a subsystem needs more explanation than the overview can give legibly, extract that subsystem to
`docs/architecture/<subsystem>.md`, or the adopted repository's established equivalent. Keep a summary
and link in the overview, and give the child the same approval boundary within its scope. Split along
domain boundaries where deeper explanation helps; stop above class and file detail.

## Template

```markdown
# <Project> — Architecture

> Shared baseline for parallel work; read alongside repo-root `AGENTS.md` before starting a task.
> Structural, scope, or costly-to-reverse changes to this baseline require a public merge, human approval, and an ADR.

## Context and scope
<what this system is, what it talks to, and explicit non-goals when applicable>

## Structure
<components, ownership, interfaces, and boundaries>

## Quality goals, release criteria, and constraints
- <key property, checkable release criterion, or hard constraint when applicable>

Decisions and their reasons: `<decision-log-path>` (default: `docs/adr/`).
Other established method-document locations: `<kind>: <path>` (omit if defaults apply).
```

The entry point remains canonical `docs/architecture.md`, including in an adopted repository: it
declares any established off-canonical locations (`reference/in-repo-writes.md`).
