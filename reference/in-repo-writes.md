# Repository documentation and canonical paths

Keep repository documentation lean, current, and in predictable locations so humans and fresh
agent sessions find one clear source of truth:

- **Canonical document paths:** founding `README.md`; operational memory in repo-root `AGENTS.md`
  or `GEMINI.md` (`reference/repo-agents-md.md`); product definition in `docs/PRD.md`
  (`reference/prd.md`); shared system baseline in `docs/architecture.md` and extracted subsystem
  children in `docs/architecture/<subsystem>.md` (`reference/architecture.md`); architectural
  decisions in `docs/adr/NNNN-*.md` (`reference/adr.md`); and pre-implementation design specs in
  `docs/specs/YYYY-MM-DD-*.md` (`reference/design-spec.md`).
- **Adopted repositories:** `docs/architecture.md` and repo-root `AGENTS.md` / `GEMINI.md` remain
  reserved entry points; other documentation kinds follow established repository conventions
  declared in `docs/architecture.md` or paths explicitly authorized in `## Bounds`.
- **Keep docs synchronized and free of process junk:** update any document within `## Bounds` that
  your code change invalidates in the same diff. Never create competing authority documents at the
  same scope (marked translations naming their canonical source and linked subsystem docs do not
  compete). Never commit `SUMMARY.md`, `HANDOFF.md`, scratch plans, or session-status files — keep
  working notes in task scratch and publish durable task state on the GitHub issue or PR.

For file and external output destinations, follow `reference/where-it-goes.md`.
