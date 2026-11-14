# 0004 — First-principles core-need alignment and PRD retirement across DevStandard and devstandard-agy

Status: Accepted (2026-11-14)

## Context

Dogfooding DevStandard across parallel Antigravity and Codex CLI lanes surfaced two coupled gaps — one
in the collaboration method DevStandard prescribes to target projects, and one in how both target
projects and this repository (`devstandard-agy`) split top-level project definition across files:

1. **Missing first-principles core-need spine across roles and helpers:** While DevStandard enforced
   worktree isolation, command/sandbox safety boundaries, and final-state `Done-check` verification,
   it lacked an explicit thread connecting day-to-day execution back to the user's underlying core
   need:
   - At project founding and feature intake, detailed or solution-shaped requests fast-tracked
     straight to codebase scoping without checking whether the proposed mechanism actually served
     the user's real need or whether a simpler, better-aligned approach existed.
   - Isolated worker lanes and subagent helpers received narrow task slices without consistently
     carrying the project's core need and how their slice served it.
   - During bug investigation, implementation, and review, narrow `Done-check` gates could turn green
     on fixes that masked symptoms, silenced errors, or degraded real behavior because existing
     logic's original purpose was not checked against the core need.
   - Conversely, phrasing product requirements as absolutist bans ("non-negotiable guarantees",
     "must never" product dogma) triggers rigid LLM zealotry on ordinary engineering tradeoffs where
     constructive direction ("the real need is X rather than Y") is needed, diluting the true hard
     red lines reserved for execution, authority, and safety boundaries.

2. **Duplicate, out-of-path `docs/PRD.md` ceremony:** DevStandard prescribed a separate
   `docs/PRD.md` (`reference/prd.md`) alongside repo-root `AGENTS.md` and `docs/architecture.md`.
   In practice, Antigravity and Codex automatically load repo-root `AGENTS.md` / `GEMINI.md` into
   fresh sessions, whereas `docs/PRD.md` was neither auto-loaded nor distinct enough from
   `AGENTS.md` (where concise first-principles `## Core need` prose belongs) and
   `docs/architecture.md` (where shared system context, scope/non-goals, founding order, constraints,
   checkable release criteria, and traceability belong). In `devstandard-agy` itself, `docs/PRD.md`
   duplicated workflow sequences and role summaries already maintained in `docs/architecture.md`.

Because `docs/adr/` ships inside `devstandard-agy`, this ADR explicitly distinguishes changes to the
**target-project method** (`reference/` and `scripts/`) from changes to **`devstandard-agy`'s own
repository baseline** (`docs/`, `.github/`, and `README.md`).

## Options considered

1. **Option 1: Keep `reference/prd.md` and `docs/PRD.md`, and layer core-need reminders onto role
   pages.**
    Retain `docs/PRD.md` as a canonical artifact in target projects and in `devstandard-agy`, instruct
   workers and reviewers to read `docs/PRD.md` alongside `AGENTS.md` and `docs/architecture.md`, and
   append core-need check bullets to `reference/orchestrator.md`, `reference/worker.md`, and
   `reference/reviewer.md`.
   - *Benefits:* Avoids deleting `reference/prd.md` and `docs/PRD.md` or updating canonical-path CI
     contracts; keeps product framing in a separate file from `AGENTS.md` and `docs/architecture.md`.
   - *Drawbacks, carry costs, and failure modes:* Keeps core project purpose out of the native
     `AGENTS.md` / `GEMINI.md` file that hosts load automatically; forces every session and PR to
     read and synchronize an extra top-level authority document (`docs/PRD.md` vs.
     `docs/architecture.md`); leaves helper packets without macro purpose unless separately wired;
     and preserves duplicate workflow/role prose inside `devstandard-agy`.

2. **Option 2: Embed non-dogmatic first-principles core-need alignment end-to-end across roles and
   helpers, and retire `PRD` (`reference/prd.md` and `docs/PRD.md`) into `AGENTS.md` +
   `docs/architecture.md`.**
   Anchor founding, `Restate before acting`, detailed-and-rough intake, pre-code challenges, leaf
   `## Goal`s, orchestrator and dispatched `Helpers:` briefs, bug root-cause/existing-purpose
   craft, worker escalation, and active-verification review on constructive first-principles core
   needs (keeping hard red lines strictly on execution, authority, and safety boundaries). Retire
   `reference/prd.md` and `docs/PRD.md`: place `## Core need` as soft-guided natural prose at the top
   of repo-root `AGENTS.md` (or established `GEMINI.md` in adopted repos), move `Founding setup` and
   project-baseline scope/criteria/constraints into `reference/architecture.md`, and consolidate
   `devstandard-agy`'s own `docs/PRD.md` single-sitedly into `docs/architecture.md`.
   - *Benefits:* Puts the project's core need in the native repo-root file every fresh session loads;
     eliminates a redundant authority document and template; aligns every role and subagent helper on
     why its task exists; catches solution-disguised requests at intake and symptom-masking "green"
     fixes during implementation and review without introducing absolutist product dogma; and removes
     duplicated workflow/role prose in `devstandard-agy`.
   - *Drawbacks, carry costs, and failure modes:* Requires coordinated reconciliation across role
     maps, supporting `reference/` guides, `scripts/hard_edges.py` helper lines, CI canonical-path
     assertions, `docs/architecture.md`, and `README.md` within role-map conciseness caps; relies on
     Soft/Structural engineering judgment rather than mechanical length or content gates for
     `## Core need` prose quality and core-need alignment.

3. **Option 3: Enforce rigid mechanical core-need schemas and mandatory product-invariant checklists
   in `scripts/dispatch` and `scripts/review-packet`.**
   Retire `docs/PRD.md`, require structured `Core-need:` headers in `AGENTS.md` and every issue
   `## Goal` validated by regex in `scripts/dispatch`, and add a separate mandatory reviewer verdict
   section for product invariants.
   - *Benefits:* Mechanically guarantees every issue and review carries a `Core-need` token.
   - *Drawbacks, carry costs, and failure modes:* Turns genuine first-principles thinking into
     boilerplate form-filling; breaks single-issue lightness on small tasks and adopted repositories;
     reintroduces brittle rubric parsing in `scripts/review-packet`; and encourages LLM zealotry over
     invariant wording rather than constructive judgment.

## Decision

Adopt **Option 2**, separating what DevStandard prescribes to target projects from how
`devstandard-agy` maintains its own repository baseline:

### 1. Target-project method (`reference/` and `scripts/hard_edges.py`)

- **Constructive, non-dogmatic core-need orientation:** Keep hard red lines (`Never` in
  `reference/worker.md`, the three hard red lines in `reference/reviewer.md`, and authority gates in
  `reference/orchestrator.md`) strictly on execution, authority, and safety boundaries. Frame
  product/engineering direction constructively ("the real need is X rather than Y"), avoid absolutist
  product bans ("non-negotiable guarantees", "must never" product dogma), and record specific
  gotchas in `AGENTS.md` only after real trouble surfaces.
- **Founding, restatement, and intake (`reference/orchestrator.md`, `reference/repo-agents-md.md`,
  `reference/architecture.md`, `reference/design-spec.md`):**
  - Before creating a repository or scoping a new project or major direction, actively drill down
    with the human across turns to uncover first-principles core needs and real-world pain points
    rather than transcribing surface feature wishes.
  - Include the inferred underlying core need (marked as inference) alongside literal/shorthand
    meaning in `Restate before acting`.
  - Check both detailed human specs/designs and rough ideas against the project's core need before
    scoping — surfacing drift and comparing better-aligned alternatives neutrally when a
    solution-shaped request diverges from the core need — and include core-need fit in clean-context
    read-only `inherit` pre-code challenges.
- **Shared direction across leaf issues and helpers (`reference/orchestrator.md`,
  `reference/worker.md`, `scripts/hard_edges.py`):**
  - Leaf `## Goal` states the project's core need, how the issue's target outcome connects to serving
    it, the intended boundary, and `Parent: #<parent>` plus inlined contracts when split from a
    parent.
  - Orchestrator helper briefs and dispatched worker/reviewer task-local helper briefs
    (`codex_helper_line` and `antigravity_helper_line` in `scripts/hard_edges.py`, kept single-line
    ahead of the `' — '` table separator) pass the project's core need and how the helper's task
    serves it.
- **Bug investigation, worker escalation, and review (`reference/orchestrator.md`,
  `reference/worker.md`, `reference/reviewer.md`):**
  - Check what need existing logic served before changing it, and ensure candidate fixes genuinely
    satisfy the core need rather than masking symptoms, silencing errors, or trading away real
    purpose for green checks.
  - Workers read repo-root `AGENTS.md` / `GEMINI.md` (when present, including `## Core need`) and
    `docs/architecture.md` (when present) alongside `## Goal`, and stop/escalate under `worker.md`
    `§5` when literal task framing or every in-`Bounds` fix that passes checks would undermine the
    core need.
  - Reviewers (`reference/reviewer.md` `What to evaluate` item 1 and `Output format`) verify that the
    change genuinely serves both `Goal` and the underlying core need rather than masking symptoms,
    and prefix `[Needs human decision]` under `### Blocking` when the issue's own `Goal` framing
    conflicts with the project's core need.
- **Retire `reference/prd.md` into `reference/repo-agents-md.md` + `reference/architecture.md`:**
  - Delete `reference/prd.md` and reconcile canonical path references across
    `reference/in-repo-writes.md`, `reference/ci-pipelines.md`, `reference/design-spec.md`, and
    `reference/orchestrator.md`.
  - `reference/repo-agents-md.md` places `## Core need` first in `AGENTS.md` (or established
    `GEMINI.md` in adopted repositories without duplicating across both) as natural, un-gated prose
    explaining concrete pain points and "X rather than Y" direction without module/interface detail;
    founded projects create `AGENTS.md` with `## Core need` and include operational sections only
    when real operational facts exist.
  - `reference/architecture.md` absorbs `Founding setup` plus broader project context, scope and
    non-goals, checkable release criteria, and constraints for larger projects, with ADRs
    accompanying structural, scope, or costly-to-reverse baseline changes (`reference/adr.md`).

### 2. `devstandard-agy` repository baseline (`docs/`, `.github/`, and `README.md`)

- Delete `docs/PRD.md` and fold Vision and Core Need, Problem Background (including core-need drift,
  symptom-masking completions, and avoiding absolutist requirement dogma), Reuse Baseline,
  Boundaries, Success Criteria, and the Existence Criterion single-sitedly into
  `docs/architecture.md`, updating internal section pointers and the Traceability Matrix without
  duplicating the workflow tables or role sections.
- Update `.github/workflows/ci.yml` canonical-path assertions (removing `docs/PRD.md` and `prd.md`
  from `contracts` and asserting both retired paths stay absent) and `.github/test-hard-edges.py` /
  `.github/test-dispatch.py` helper-line assertions, and reconcile `README.md`. Leave historical ADRs
  `0000`–`0003` untouched.

## Consequences

- **Improves:** Fresh orchestrator, worker, reviewer, and helper sessions share one clear first-principles
  core-need anchor without an extra `docs/PRD.md` document to maintain; solution-shaped requests that
  miss the underlying need are caught calmly before code is written; symptom-masking "green" bug fixes
  are surfaced for escalation rather than merged; and `devstandard-agy` maintains a single shared
  baseline in `docs/architecture.md` alongside its local `AGENTS.md`.
- **Costs:** `codex_helper_line` and `antigravity_helper_line` carry one additional clause in every
  dispatched `# Task packet`, and `docs/architecture.md` holds both problem/reuse framing and
  collaboration-architecture structure in one file.
- **Watch:** Keep `## Core need` prose grounded in real user pain points and constructive tradeoffs
  rather than drifting into module/implementation detail or absolutist "must never" dogma, and ensure
  reviewers reserve `[Needs human decision]` core-need blocks for genuine purpose conflicts rather
  than subjective preferences.
