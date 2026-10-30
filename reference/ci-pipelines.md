# CI, the release pipeline, and keeping them current

At project setup, generate CI and settle what shipping means: deploy a service under
[deployment discipline](deployments.md#deploying-a-self-hosted-service), publish a package, or
publish a plugin. Releases default to a version tag chosen by the human; release-on-merge requires
project opt-in. Adapt the templates' toolchain commands to the project.

## CI template (`.github/workflows/ci.yml`)

```yaml
name: CI
permissions:
  contents: read
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - name: Bind this checkout to the advertised PR merge result
        if: github.event_name == 'pull_request'
        env:
          EXPECTED_BASE: ${{ github.event.pull_request.base.sha }}
          EXPECTED_HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          test "$(git rev-parse HEAD^1)" = "$EXPECTED_BASE"
          test "$(git rev-parse HEAD^2)" = "$EXPECTED_HEAD"
      # <language setup step here, e.g. actions/setup-node / setup-python>
      - name: Install
        run: <install command>
      - name: Test
        run: <test command>

  merged-result:
    name: merged-result / ${{ github.event.pull_request.base.sha }} / ${{ github.event.pull_request.head.sha }}
    if: github.event_name == 'pull_request'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "this exact merge of base and head passed the test job"
```

Copy the checkout-binding step and `merged-result` job exactly for guarded integration. They bind
success to the advertised base/head merge under `scripts/hard_edges.py`'s `MERGED_RESULT` and
`merge_check` contract. Use `reference/orchestrator.md`'s Guarded operations section for invocation.
The CI token needs only read access; grant write access per job where required.

Pin third-party actions to full commit SHAs. First-party `actions/*` version tags are allowed.
Generate Dependabot alongside CI so the pins remain current.

## Resource controls and runners

Upload artifacts only for a real consumer and set `retention-days:`. Release deliverables use the
release pipeline; retained reports follow `reference/where-it-goes.md`. CI storage is not an archive.

Exhausted minutes on a private repo can prevent workflows from running, including release and
Dependabot workflows. Reduce spend with appropriate triggers, bounded matrices, dependency caches,
path filters, cancellation of superseded runs via `concurrency:`, and job `timeout-minutes:`. The
minimal template leaves these project-specific controls to setup. Tell the human when allowance is
exhausted; paying for more or making the repo public is their decision. The temporary fallback in
`reference/ci-cannot-run.md` does not repair the pipeline.

A self-hosted runner moves compute while preserving both merge gates. Provisioning is the human's
call; consider it before fallback when minutes are the constraint. **Use ephemeral runners only:**
one job, then deregister and exit, so jobs do not inherit prior workspaces. **Never use them on
public repositories.** Keep only needed toolchains on the host and provide required secrets through
workflow `secrets:` for that job alone.

The host must be available when jobs arrive. An empty ephemeral-runner list is normal while idle;
a job queued beyond five minutes with no runner registering indicates a stopped provisioning loop.
Ask the human to check or restart it. Queuing behind an offline runner is not a platform outage or
fallback trigger.

## Protection and setup

Apply branch protection last at founding with `guard protection --apply --check test`;
`reference/prd.md` owns the order. Use `scripts/guard protection --help` and
`reference/orchestrator.md`'s Branch protection section for settings, plan limits and provisioning.
Protection enforces the server-side CI gate; independent code review, pure rebase comparison, and the
guarded merge route (`scripts/guard merge`) still apply — including for release-time version bumps.
Protection creates no exceptions.

## Pipeline pin upkeep (`.github/dependabot.yml`, generated in the same setup step)

Generate this file with CI so workflow action updates arrive as PRs through code review and green CI.
This covers pipeline actions; project dependency management remains outside the method's scope.

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

## Release template (`.github/workflows/release.yml`)

```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      # <language setup + install + build steps>
      - name: Test
        run: <test command>          # green tests gate the release too
      - name: Publish
        run: <publish/deploy step>   # gh release create / npm publish / deploy ...
```

If the project has no release form yet, generate CI only and record the open release question in
the PRD's constraints. Workflow files land in `.github/workflows/`; Dependabot uses the path above.
Founding also records useful operational facts under `reference/repo-agents-md.md` and adds
`/.agents/worktrees/` to `.gitignore` for later lane creation.

## When CI goes red with no change of yours

Inspect the failure under `reference/red-check.md`. Vendor runtime deprecations can break unchanged
pipelines; inspect warnings and action versions. If the task already touches that workflow, update
pins the run flags as deprecated in the same diff. Otherwise return an out-of-bounds failure rather
than expanding the task. Protection checks and provisioning remain with the orchestrator.
