# When CI cannot run at all (the check-2 fallback)

Check 2 is green CI on the merged result. Fallback is a declared, temporary loss of independent
execution, established only by the merging main session. A worker's done-check never substitutes.

## Wait first

Waiting preserves check 2 and is normally the right choice. Use fallback only after explaining why
waiting is ruled out. Prove both trigger conditions: the cause is outside this repository, and it
prevents the platform producing a run for any push. The qualifying causes are exhausted Actions
minutes on a private repo or a provider outage. Capture billing/usage proof or a public status-page
incident; for a self-hosted GitHub instance, use its admin or incident channel. Tell the human;
removing the cause belongs to them. An unproven outage grants no fallback.

| Not a trigger | Response |
|---|---|
| Slow, queued or flaky CI; a session deadline | Wait; a queued run is a run. |
| Offline self-hosted runner | Ask the human to check/restart it; see `reference/ci-pipelines.md` for ephemeral-runner diagnostics. |
| A run started and failed | Use `reference/red-check.md`; main follows the orchestrator's red-main recovery. |
| Invalid YAML, disabled workflow or mismatched triggers | Repair through a PR within authorized scope. |
| Actions disabled by the organization | Wait for the human or org admin to restore it. |
| No CI configured | Settle CI as a task using `reference/ci-pipelines.md`. |
| No auth, network or readable Actions state | Establish the state or wait. |

A job prevented from starting by exhausted billing quota belongs to the qualifying quota case.

## Materialize and run the exact merge

Only the merging main session, never a worker or helper, runs fallback. Fetch current main and the
PR head and check out their synthetic two-parent merge, rather than the branch as pushed:

    set -e
    REPO_ROOT=$(git rev-parse --show-toplevel)
    git fetch origin main
    BASE_SHA=$(git rev-parse FETCH_HEAD)
    git fetch origin "pull/<PR>/head"
    HEAD_SHA=$(git rev-parse FETCH_HEAD)
    MERGE_TREE=$(git merge-tree --write-tree "$BASE_SHA" "$HEAD_SHA")
    MERGE_COMMIT=$(printf 'CI fallback: merge %s into %s\n' "$HEAD_SHA" "$BASE_SHA" |
      git -c user.name=CI-Fallback -c user.email=ci-fallback@invalid \
        commit-tree "$MERGE_TREE" -p "$BASE_SHA" -p "$HEAD_SHA")
    FALLBACK_CHECKOUT=
    cleanup() {
      cd "$REPO_ROOT" || true
      git worktree remove --force "$FALLBACK_CHECKOUT" 2>/dev/null || true
      rm -rf "$FALLBACK_ROOT"
    }
    FALLBACK_ROOT=$(mktemp -d)
    trap cleanup EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    FALLBACK_CHECKOUT="$FALLBACK_ROOT/checkout"
    git worktree add --detach "$FALLBACK_CHECKOUT" "$MERGE_COMMIT"
    cd "$FALLBACK_CHECKOUT"

Run every CI job from this worktree, unfiltered and to completion. The traps remove the temporary
checkout and its root on success, failure or handled signals. Capture the merge commit, parent and
tree identities as shown below; labels and a clean branch checkout do not prove the merged state.
Any head move or rebase invalidates the materialization and run.

If any job needs unavailable secrets, a service, another OS or a GPU, there is no fallback for that
job. Wait, take it to the human, or make the job locally runnable in its own PR. A runnable subset
never satisfies check 2.

## Protection and review

Never drop required checks, enable bypasses, edit rulesets or push directly to main to unblock a
merge. Name the blocked PR to the human. They may restore the platform or waive the check; restore
protection in the same session as the merge. Where server-side protection is unavailable, the same
evidence and audit remain required. `reference/orchestrator.md`'s Branch protection section owns
plan-limit recognition and recording.

Publish evidence before check 1. Put the audit checklist and evidence block below in the same PR
comment, then commission review with `scripts/review-packet start --wait --ci-fallback <comment URL>`.
The assembler carries the whole comment into `reference/code-review-prompt.md`'s fallback slot,
which otherwise reads `NONE`. A clean independent reader audits the captured evidence, including
when the merging session authored the diff. If review returns the diff or the base/head changes,
materialize and run again; the final evidence must cover the state that merges.

    Audit the CI-fallback evidence above against all four items:
    - Is the stated cause outside this repo (minutes exhausted, platform
      outage) and proven — not "slow", "queued", "flaky", "red", or anything
      this repo or its org could fix?
    - Do the merging session's timestamped fetch/ref captures identify the
      current remote main tip and PR head, matching the published base/head
      and this packet's pins? Does its successful merge-tree capture use
      those exact SHAs and produce the published tree? Does the captured
      checkout identity show a commit whose first parent is that base,
      second parent is that head, and tree is that captured merge tree?
      Compare the supplied captures; do not execute commands. Missing or
      inconsistent captures cannot establish that the run tested their merge.
    - Is the run fresh (a UTC timestamp) and tracked state clean before it
      (`git diff --quiet` and `git diff --cached --quiet`)? Are permitted
      untracked inputs enumerated—only paths already on the pre-run baseline
      and named by the worktree copy-list, never an invented fixture? Do
      before/after `git status --porcelain -uall` snapshots match? Is every
      ignored input the run depends on named?
    - Is every CI job covered, unfiltered, with commands and exit codes shown?

## Evidence comment

Keep the literal `CI-FALLBACK` marker for the return sweep. Publish the following with the audit
checklist before merge so GitHub preserves the reason, exact state and complete results:

    CI-FALLBACK (check 2 degraded)
    Reason: minutes quota exhausted | provider outage
            + proof (billing/usage page or `gh api` output; status-page incident id)
    Merged state: base <SHA> = current remote main tip; head <SHA> = this PR's head
    Materialised merge: commit <SHA>; tree <TREE-ID>
    Run at: <UTC timestamp>
    Runner: main session — <OS, toolchain versions>
    Captured at: <UTC timestamp; fresh for this review's base/head>
    $ git fetch origin main              -> exit 0
    $ git rev-parse FETCH_HEAD            -> <base SHA>
    $ git fetch origin pull/<PR>/head     -> exit 0
    $ git rev-parse FETCH_HEAD            -> <head SHA>
    $ git merge-tree --write-tree <base SHA> <head SHA> -> exit 0
      <merge tree>
    $ git rev-parse HEAD HEAD^1 HEAD^2 'HEAD^{tree}'
      <synthetic merge commit>
      <base>
      <head>
      <tree>
    $ git diff --quiet                    -> exit 0
    $ git diff --cached --quiet           -> exit 0
    Permitted untracked inputs: <baseline + copy-list paths, or NONE>
    Ignored inputs used by the run: <paths, or NONE>
    $ git status --porcelain -uall (before) -> <snapshot>
    $ <command>          -> exit <code>
    <output tail>
    (one block per CI job; every job covered, none skipped or filtered)
    $ git status --porcelain -uall (after)  -> <identical snapshot>

## Return to CI

Hold releases until workflows return: a tag pushed during the outage can look shipped without a
release. Main is unverified rather than red, so dispatch continues; a failing run still invokes
red-main recovery.

Fallback ends as soon as a push can produce a run. The next merge requires ordinary check 2.
Trigger main's first restored CI run promptly and confirm protection is restored. Green covers all
fallback merges without re-review. On red, search closed PRs for `CI-FALLBACK` and apply red-main
recovery: revert first, fixing forward only when the fix is obvious and takes minutes. Repeated
fallback use calls for pipeline repair; see `reference/ci-pipelines.md`.
