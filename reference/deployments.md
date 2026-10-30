# Deploying a self-hosted service

Deploy only under the human's words or standing release delegation. This page grants no authority;
a merge does not authorize a deploy. Record the deploy separately.

Run on the service's host from a local checkout of the merged commit. Cut the release archive from
that commit, for example with `git archive`, rather than from working-tree contents. Keep separate
the development checkout, release snapshot, running instance and project data. Never develop in the
running directory; the repository remains the source of truth.

Use immutable release directories with an atomically switched `current` pointer by default:

1. Stop the service, switch the pointer, start the service, then probe health.
2. After health succeeds, verify the deployed fix with a direct check or bug reproduction when
   applicable.
3. If either verification fails, restore the previous release with the same stop / switch / start /
   probe sequence. Rollback changes the pointer, not the code.

Keep a per-deploy receipt with the authorization, merged commit, previous and new release
identities, time, health and applicable fix-verification results, and any rollback.

A deploy never implicitly migrates or resets state. Data, secrets, configuration, and declared
deploy roots with rollback retention follow `reference/where-it-goes.md`.

Use containers or orchestration when coordination across hosts or services justifies them. A
trivial stateless tool may run from a checkout whose deployed contents exactly match the merged
commit; never develop there. Otherwise use immutable releases. Keep service commands and health
probes in the project's own docs.
