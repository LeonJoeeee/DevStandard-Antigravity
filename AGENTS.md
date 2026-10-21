# Working on DevStandard-Antigravity itself

This file is **repo ops for this repository only**. It is not part of the method: nothing in
`reference/` points at it, and no seeded project receives it. Antigravity loads a
*project's* `AGENTS.md`, never a plugin's. Everything here is a practice we follow *while
building DevStandard-Antigravity*, not a rule DevStandard states.

**Never write the page total.** An ADR or a PR description may state what a change *cost* —
because that is history and stays true forever. It may not state what the page *measures afterwards*
(`total 4,560 of 5,000`): that is a snapshot, it is stale by the next change that moves anything,
and the CI-enforced ceiling is the only current figure a reader needs. Every such total written is
wrong within a week — and the ones already in `docs/adr/` stay exactly as written; an immutable body
is not a defect to clean up.

Two carve-outs. **A gate's own output quoted as evidence** — `<artifact> N bytes (cap <gate>)`
in a PR's evidence block — is the run's words, dated by the run, and is what a reviewer verifies
gate 2 against; quote it there and restate it nowhere else (including here, which is why this
example is a placeholder). And **an argument that turns on headroom** may state the distance to
the ceiling, because a delta cannot express it — but it states it once, in the ADR that makes the
argument.

**The line that decides what belongs here:** a method DevStandard *ships* goes in the shipped
pages; a practice useful only for maintaining *this* project goes here. When the two get
confused, repo-ops material ends up on a page every project pays to read every session.

## Auditing our own pages (ADR 0032)

Our pages are the product, so their length is a cost every reader pays. Four rules, and when they
disagree the first one wins.

**1. Weight is earned by frequency × cost-of-getting-it-wrong *in a target project*** — never by
how vivid the incident was here. The question that finds the defect is not "is this rule true for
someone else?" (it usually is, which is why two audits passed it) but **"is its weight proportional
to how often a normal project hits it — or to how memorably we hit it?"** `reference/adr.md` failed
it hardest: 314 words on claiming a free ADR number, a collision we hit because our product is
decisions, sitting beside 66 words for the irreversible one. `reference/orchestrator.md`'s Worktree
lifecycle section is the standard — long exactly where the failure cannot be undone.

**2. A rule is stated in full in exactly one place *within the set of files one reader receives*;
every other site carries the trigger and a pointer.** Measure it per reader, never across the
library: whether a reader needs to know something is decided by that reader's function, not by what
another reader already knows. So the same rule on the orchestrator's page and the worker's page is
**delivery, not duplication** — they are two prompts delivered whole to two different agents, and
the reviewer is a third. The defect is one reader's own set saying the same thing twice. Prefer a
small file sized to what the pointer asks for over pointing at a large file that happens to contain
the answer; `reference/red-check.md` exists for exactly that reason.

**3. Give the common cases, then a closing default — never chase an exhaustive enumeration of an
open-ended set.** (A genuinely closed set — a status vocabulary, an absolute NEVER list — is a
contract, not an enumeration, and rule 3 does not touch it.) Name explicitly the few cases where
taking the default is expensive, and let the default carry the rest. The signal that you are
enumerating: **round after round finds a new case the page does not decide, and the answer each
time is another rule.** The count alone proves nothing — a round whose findings are consequences
of the last round's fixes, or gaps in its verification, is the review working, however many there
are. Two things it never licenses dismissing: **a site whose statement has staled** (rule 2 and
*search twice*) and **a safety regression**. The review-side counterpart is operative in
`reference/code-review-prompt.md`'s Goal verdict — the open-ended-goal and stop-signal clauses,
which tell the reviewer to report non-convergence instead of writing another round's rule.

**4. Before a page gains another rule, ask what could be removed instead — and whether the problem
is worth solving at all (ADR 0053).** Alone among these four it also ships: `reference/orchestrator.md`
and `reference/code-review-prompt.md` carry the operative wordings.

**The trigger always stays resident.** A reader who does not recognise the situation never follows
the pointer, so rule 2 never applies to the sentence that makes someone *look*. Sinking a trigger is
not compression; it is deletion with extra steps.

## Commands

Any change here is done-checked by verification commands runnable from the repo root:

```sh
# 1. Dispatcher integration checks (real git/processes; GitHub, Codex, and Antigravity executor doubles)
python3 .github/test-dispatch.py

# 2. Review-packet assembly, green-head admission, publication, and round accounting
python3 .github/test-review-packet.py

# 3. Guard, authorization, reviewed-head and constructed-rebase probes (dual-protocol Antigravity + Codex hook checks)
python3 .github/test-hard-edges.py

# 4. SessionStart hook delivery: injectSteps structure, multi-part reconstruction, degraded read, unsupported environments
python3 .github/test-session-start.py

# 5. ADR index consistency and amendment block validation
python3 .github/check-adr-index.py

# 6. Release manifest version check
python3 -c 'import json; p=json.load(open("plugin.json"))["version"]; print("plugin.json version:", p)'

# 7. Pre-merge check — verify published review verdict on the PR before merging:
PR=<number>
test "$(gh api "repos/LeonJoeeee/DevStandard-Antigravity/issues/$PR/comments" \
  --jq '[.[] | select(.body | test("[Mm]erge check 1"))] | length')" -ge 1
```

**The verdict is posted when it arrives, not when you remember.** Knowing the rule is never the
safeguard, and command 7 above catches omissions before merge. What replaced remembering is the
machinery: `scripts/review-packet start` reserves the round as a PR comment *before* the reviewer
runs, so an unpublished verdict is a visible reservation rather than nothing at all. On the Codex
path, `start --wait` waits for dispatch to return, then replaces that reservation with
`## Merge check 1 — round N` and the unedited verdict itself; a process that exits returning no
verdict is recorded as a failed attempt, not a returned one. On the native Antigravity path,
the orchestrator receives the subagent result via `send_message` and publishes the verdict with
`scripts/review-packet publish --attempt ID --verdict FILE`. Check 1 always runs read-only.
**The safeguard is the assembler's round accounting, not anyone reproducing a prompt correctly** —
which is why `reference/orchestrator.md` forbids a bespoke review prompt outright.

## Rewording a rule: search twice

Our product is prose, so nothing mechanical catches a stale statement. Rename a function and
the compiler finds every caller; reword a rule and **nothing responds**.

When you change the wording of a rule that exists in more than one place, **search twice**:

1. **Every other statement of the clause** — the `reference/` files, `docs/architecture.md`, and
   the ADR that recorded it.
2. **Every site that cites or paraphrases it**, found by *its pointer to the rule* — the file
   it names, the rule's subject — and **never by the words you just added.** Searching for the
   word you added finds every site that already has it, and by construction cannot find the sites
   that should now carry it.

Reconcile each in the same diff, or say in the PR description why it needs none — a site simply
absent from the sweep is a silent omission, not a clearing.

**Cite the rule, not the line.** A pointer to a specific line number is stale the moment anything
above it moves. Name the rule or its section instead; that survives an edit, and it is what a reader
searches for anyway. The one place a line number belongs is an amendment recording a move.

**Record the ruling, not the tally.** Do not close a sweep with "N sites". A count is a snapshot
that becomes incorrect when another commit moves anything. State which sites are reconciled and which
are cleared and why.

Two sites take a specific form:

- **An ADR** is reconciled by appending a dated `**Amendment (YYYY-MM-DD, see NNNN):**` block,
  never by a rewritten body (`reference/adr.md`). Ask: **would a reader *act* on the sentence, or
  only read it?** A statement they would follow (where a rule lives now) is a live instruction and is
  reconciled. A statement recording history is left untouched.
- **A historical record** — a merged PR description, a released tag's notes — is not a site.

## The release delegation

The role pages' two-checks paragraph states that releasing is normally the human's call. For this
repository, the human has granted a standing delegation: the agent releases right after each
merge — tag, push — with `plugin.json` updated, without asking per release. The goal is that merged
improvements reach users' active sessions immediately.

Withdrawing the delegation is the human's to do, and takes saying so rather than editing a file.
**Target projects are unaffected:** there, release go/no-go stays on the human's ask-axes and
`reference/ci-pipelines.md` tag-triggered default governs.

**Version bumps:** fold the version bump into the change PR and put the semver call in its
description. If a bare bump PR is unavoidable and has no Floor-2 failure, it needs no issue or
check-1 reviewer: CI is its review. It still merges through `scripts/guard merge`.

## ADRs in this repo

`docs/adr/` ships inside the repository. Consequence: **an ADR that decides how we operate, rather
than what the method says, must say so in its own title and text** — otherwise a reader in a target
project takes it for an instruction.

**Two amendment blocks of the same date share one status entry**, and that is correct: the status line
is a set of dates, and one `Amended (YYYY-MM-DD)` announces every block carrying it.

**Claiming a number here is a real collision risk.** Decisions are written at a high rate and multiple
branches may be open. Check these four locations before claiming the next sequential number:

```sh
# 1. the merged log
git ls-tree --name-only origin/main docs/adr/
# 2. every remote branch
git fetch --all && git log --all --diff-filter=AR --no-renames --name-only --pretty=format: -- 'docs/adr/*' | sort -u | grep .
# 3. every open PR
gh pr list --state open
# 4. open issues that may have reserved a number
```
Record which number you took and what you checked it against in the PR description.
