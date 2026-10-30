# How to write the architecture document

After the PRD, describe the shared structure that parallel sessions build against. Use
`reference/orchestrator.md`'s requirements binding to settle it with the human. Keep the overview
readable and focused on boundaries that change slowly; decision history belongs in ADRs and
implementation detail in code.

## Content and maintenance

- State that this is the shared baseline to read before task work, and that changing it requires
  a public merge, human approval, and an ADR. The wording may fit the project.
- Explain the system's context, main components, ownership, and interfaces. Add a diagram when it
  clarifies those boundaries.
- Name the quality goals that drive structural choices and help resolve future tradeoffs.
- End with the decision-log location, normally `docs/adr/`, and any established mappings for method
  documents kept off their default paths. This footer is the common pointer for path consumers.

Describe the system as it exists. Keep plans and historical reasoning in the appropriate spec or
ADR, and update the architecture in the same change that alters its structure, together with the
ADR. Avoid detail that would make routine implementation changes stale the shared baseline.

## Split on zoom

When a subsystem needs more explanation than the overview can give legibly, extract that subsystem
to `docs/architecture/<subsystem>.md`, or the adopted repository's established equivalent. Keep a
summary and link in the overview, and give the child the same approval boundary within its scope.
Split along domain boundaries where deeper explanation helps; stop above class and file detail.

## Template

```markdown
# <Project> — Architecture

> Shared baseline for parallel work; read before starting a task.
> Changes to this baseline require a public merge, human approval, and an ADR.

## Context
<what this system is and what it talks to>

## Structure
<components, ownership, interfaces and boundaries>

## Key quality goals
- <property and why it matters here>

Decisions and their reasons: `<decision-log-path>` (default: `docs/adr/`).
Other established method-document locations: `<kind>: <path>` (omit if defaults apply).
```

The entry point remains canonical `docs/architecture.md`, including in an adopted repository:
it declares any established off-canonical locations (`reference/in-repo-writes.md`).
