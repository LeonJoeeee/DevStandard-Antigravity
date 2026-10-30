# When CI cannot run at all (the check-2 fallback)

Check 2 is green CI on the merged result. Fallback is a temporary loss of independent execution,
declared only by the merging main session. A worker's local done-check never substitutes.

## Wait first

Waiting preserves check 2 and is the default. Use fallback only when waiting is ruled out and both
conditions are proven: the cause is outside this repository, and it prevents the platform from
running workflows for any push — specifically exhausted Actions quota on a private repo or a
confirmed provider outage. Capture billing/usage proof or a status-page/admin incident and notify
the human, who owns resolving the cause.

| Not a trigger | Response |
|---|---|
| Slow, queued, or flaky CI; a session deadline | Wait; a queued run is a run. |
| Offline self-hosted runner | Ask the human to check or restart it (`reference/ci-pipelines.md`). |
| A run started and failed | Follow `reference/red-check.md` (or red-main recovery on `main`). |
| Invalid YAML, disabled workflow, or mismatched triggers | Repair via a PR within authorized scope. |
| Actions disabled by the organization | Wait for the human or org admin to restore it. |
| No CI configured | Settle CI as a task under `reference/ci-pipelines.md`. |
| Missing auth, network, or readable Actions state | Restore access or wait. |

## Materialize and run the exact merge

Only the merging main session, never a worker or helper, runs fallback. Fetch current `origin/main`
and `pull/<PR>/head`, synthesize their two-parent merge commit (`git merge-tree --write-tree
"$BASE_SHA" "$HEAD_SHA"` and `git commit-tree "$MERGE_TREE" -p "$BASE_SHA" -p "$HEAD_SHA"`), check
it out in a temporary detached worktree, run **every** CI job unfiltered to completion, and remove
the temporary worktree afterward. A plain branch checkout does not test the integrated result, and
any base or head movement invalidates the run.

If any job requires unavailable secrets, external services, another OS, or a GPU, stop — there is
no fallback for that PR. Wait, escalate to the human, or make the job locally runnable in its own
PR; a runnable subset never satisfies check 2.

## Protection, `CI-FALLBACK` evidence, and review

Never drop required checks, enable bypasses, edit rulesets, or push directly to `main` without the
human's decision. If the human waives a required check to unblock a merge, restore branch
protection in the same session (`reference/orchestrator.md`).

Before commissioning code review (`reference/reviewer.md`), publish one PR comment headed
`CI-FALLBACK` and pass its URL to `scripts/review-packet start ... --ci-fallback <comment URL>` so
an independent reviewer audits it (even when the merging session wrote the diff). Include both the
evidence and this audit checklist in that comment:

- **External cause proven:** private-repo quota exhaustion or provider outage with captured proof.
- **Exact synthetic merge:** UTC timestamp, `origin/main` base SHA, PR head SHA, synthetic
  two-parent merge commit SHA, and merge-tree SHA matching the review packet's pins.
- **Clean environment:** clean tracked checkout and only baseline copy-list untracked inputs (no
  invented fixtures).
- **Complete unfiltered jobs:** every CI job's command, exit code, and output summary.

Re-materialize and re-run whenever the diff, base, or head changes before merge.

## Return to CI

Hold releases until CI workflows return, so tags do not appear shipped without a release run. End
fallback as soon as pushes produce runs again, trigger `main`'s first restored CI run promptly, and
confirm branch protection is restored. If restored `main` fails, search closed PRs for
`CI-FALLBACK` and apply red-main recovery (revert first). Repeated fallback use calls for pipeline
repair under `reference/ci-pipelines.md`.
