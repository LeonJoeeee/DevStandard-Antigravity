# How to write ADRs

An ADR preserves a significant decision and its reasons so later sessions can understand the choice.
Record it at decision time from the actual discussion, with one decision per file.

## Admission

The test is cost of change. Write an ADR when a decision touches top-level structure, interfaces,
dependencies, or a key quality goal; has effects across components; or is costly to reverse.
Adopting a core external dependency and choosing custom infrastructure over mature open-source
solutions both qualify under this trigger.

Skip trivial local choices, temporary workarounds and spikes, and decisions already explained by an
ADR or the architecture. Ask whether a future session would spend real effort reconstructing why.
When human approval settles a top-level design choice, include the ADR in the same merge.

## Reasoning

For non-trivial capabilities, survey mature open-source solutions before proposing custom builds.
Assess maintenance, mainstream adoption, ergonomics, capability fit, and libraries that compose to
solve sub-problems. Describe all viable options completely and neutrally, with their pros, cons,
carry costs, and new failure modes and complexity, before stating the decision. Explain why any
custom infrastructure is justified. If the actual alternatives cannot be recovered, say so;
do not invent a discussion.

## Mechanics

- Use `docs/adr/NNNN-kebab-title.md` by default, or the adopted repository's established location
  declared in `docs/architecture.md` (`reference/in-repo-writes.md`). Seed the log at founding with
  `0000-record-architecture-decisions.md`, including these admission rules.
- Claim a four-digit, zero-padded sequential number when writing: the next above the highest
  claimed anywhere, never the lowest free. Never reuse numbers. Filenames serve as the index.
- A changed decision gets a new ADR stating `Supersedes NNNN`; change the old status to
  `Superseded by MMMM` and preserve its original body.
- For partial supersession or factual correction, append a dated amendment without rewriting the
  body. Use `**Amendment (YYYY-MM-DD, see NNNN):**` for an amending ADR, or
  `**Amendment (YYYY-MM-DD, <cause>):**` / `**Amendment (YYYY-MM-DD):**` otherwise.
- Statuses are `Accepted`, `Superseded by NNNN`, `Amended by NNNN (<date>)`, and `Amended (<date>)`;
  amendment entries accompany `Accepted`. A new ADR states `Supersedes NNNN` or
  `Amends NNNN (<what it amends>)` in its own status line.
- Announce every amendment in the amended ADR's status line. A block citing `see NNNN` requires
  `Amended by NNNN (<date>)` (legacy undated `Amended by NNNN` also qualifies). Other blocks require
  `Amended (<date>)`, even if they cite an issue, PR, commit, or merely causal ADR. One date entry
  covers matching blocks of that date.

## Template

```markdown
# NNNN — <decision>

Status: Accepted (<date>)

## Context
<situation, constraints and forces>

## Options considered
<actual viable options, mature solutions surveyed, benefits, drawbacks, carry costs and new risks>

## Decision
<choice and why its tradeoffs fit>

## Consequences
<what improves, what it costs, and what to watch>
```
