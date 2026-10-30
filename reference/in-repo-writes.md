# What documentation may be added to a repository

Read this before adding documentation. The delimited predicate is also carried into admission
review under `reference/code-review-prompt.md`'s Floor 2.

<!-- BEGIN IN-REPO-WRITES PREDICATE -->
This predicate governs prose for people or agents, including generated prose. It excludes code,
non-document build output, genuine product/runtime configuration, fixtures, lockfiles and
`.gitignore`. Handoff or session-state artifacts remain documentation regardless of file format.

A new document must pass one admission below. Editing an existing tracked path is ordinary work;
that path does not license another document. A handoff or session-state document must qualify on
every edit; inheriting it grants no permission to keep it.

1. **A method document whose trigger fired:** `docs/PRD.md` and `docs/architecture.md` for founding
   or task-scoped architectural redefinition; `docs/architecture/<subsystem>.md` when the overview
   cannot explain that subsystem legibly; `docs/adr/NNNN-*.md` when ADR admission fires;
   `docs/specs/YYYY-MM-DD-*.md` for a substantial change; repo-root `AGENTS.md` (or `GEMINI.md`)
   when operational memory needs updating. Other admissions cannot waive these triggers.
   Paths are canonical relative to the scope whose lifecycle ran; an adopted repository's
   established convention may supply a location under admission 2. `docs/architecture.md` and
   repo-root `AGENTS.md` (or `GEMINI.md`) remain reserved entry points. `README.md` is admitted
   only as founding-scaffolder output named in the accepted setup design; adding a scaffolder
   later grants no admission.

2. **An established base-tree convention whose creation condition fired.** Pin the pre-work base
   as `{CONVENTION_BASE_SHA}`: `origin/main`, local `main` or `HEAD` without a remote, or the empty
   tree for founding. The base must show a maintained kind sharing purpose, location and naming,
   or a tool already in that base maintaining it. Its real creation condition must occur, such as
   a release or generator run. One incidental file or matching shape is insufficient.

3. **A written authority request.** Authority is the human, main session, or pre-work record: the
   issue as dispatched; the accepted spec version whose reachable blob SHA was published on the
   issue before dispatch; or a pre-existing document. Handoff and session-state artifacts never
   grant authority. A doer's additions to its own issue or implementing spec are escalation until
   approved there by the main session. With neither an issue nor a remote, a human's instruction
   may authorize a document if disclosed at handback.

Never create competing authorities at the same scope. A marked translation naming its canonical
source or a scoped child linked from its overview does not compete. Check against the prospective merge:
`{REVIEW_BASE_SHA}`, the head and other candidate documents. `{CONVENTION_BASE_SHA}` establishes
only whether a convention admitted the addition.

A document passing no admission is invented. Session endings and handoffs never suffice under any
admission or format. Put summaries, handoffs and status on the issue, PR description or comments.
<!-- END IN-REPO-WRITES PREDICATE (39 payload lines) -->

For external placement use `reference/out-of-repo-writes.md`. Your role page governs final tree
accounting and handback.
