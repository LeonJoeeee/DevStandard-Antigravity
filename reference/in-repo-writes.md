# What documentation may be added to a repository

Read this before adding documentation. The delimited predicate is also carried into admission
review under `reference/code-review-prompt.md`'s Floor 2.

<!-- BEGIN IN-REPO-WRITES PREDICATE -->
This predicate governs prose for people or agents, including generated prose and session-state or
handoff files in any format. It excludes code, non-document build output, genuine product/runtime
configuration, fixtures, lockfiles, and `.gitignore`. Editing an existing tracked document at its
path is ordinary work, except for session-state or handoff artifacts, which never earn retention.
Adding a document requires one of three admissions:

1. **A method document whose trigger fired:** `docs/PRD.md` and `docs/architecture.md` (founding or
   architectural redefinition); `docs/architecture/<subsystem>.md` (subsystem outgrows the
   overview); `docs/adr/NNNN-*.md` (costly-to-reverse decision); `docs/specs/YYYY-MM-DD-*.md`
   (substantial change); repo-root `AGENTS.md` or `GEMINI.md` (operational memory update); and
   founding `README.md` named in the accepted setup design. Other admissions cannot waive these
   triggers. `docs/architecture.md` and repo-root `AGENTS.md` / `GEMINI.md` remain reserved entry
   points; an adopted repository's established path for other kinds follows admission 2.
2. **An established `{CONVENTION_BASE_SHA}` convention whose creation condition fired:** a
   maintained kind in the pre-work base sharing purpose, location, and naming (or maintained by a
   base tool) when its real trigger occurs, such as a release or generator run. A single incidental
   file is not a convention.
3. **Explicit written authority:** requested in the dispatched issue, the accepted spec whose
   reachable blob SHA was published on the issue before dispatch, or a pre-existing project
   document. Handoff artifacts and a worker's unapproved additions to its own issue or spec grant
   no authority.

Never create competing authorities at the same scope across `{REVIEW_BASE_SHA}`, the head, and
candidate additions (marked translations naming their canonical source and linked subsystem
children do not compete). Never invent session-summary, status, or handoff files; record handoffs
and status on the issue or PR.
<!-- END IN-REPO-WRITES PREDICATE (26 payload lines) -->

For file and external placement, use `reference/where-it-goes.md`. Your role page governs final
tree accounting and handback.
