# 0002 — Post-compaction orchestrator context re-injection

Status: Accepted (2026-10-22); Amends 0001 (post-compaction orchestrator context delivery via PreInvocation).

## Context

SessionStart delivers `reference/orchestrator.md` at initialization, but later context compaction
can truncate that DevStandard `SYSTEM_MESSAGE`. The main Antigravity orchestrator still needs its
complete operating instructions in the active context across successive compactions. A checkpoint
summary can omit operative rules; a one-line notice to read the page leaves delivery dependent on
the model choosing to follow it.

## Decision

Register `PreInvocation` in `hooks.json`, calling `hooks/session-start --pre-invocation`. Keep the
existing SessionStart delivery path and use the same single `injectSteps` `systemMessage` step to
restore the plugin-root preamble and whole page after compaction, rather than a summary or read notice.

The PreInvocation path scans the JSONL file named by `transcriptPath`, ignoring blank or malformed
records. Delivery is needed only when a `CHECKPOINT` exists and no later `SYSTEM_MESSAGE` contains
the DevStandard orchestrator-context marker or missing-page stop-warning marker. This transcript
ordering provides duplicate suppression between compactions and restores delivery after each new
checkpoint without a separate state file. Missing or unreadable transcripts produce `{}`; an
unreadable role page produces the existing stop warning when delivery is needed.

Role and subagent suppression runs before this decision in both modes: workers, reviewers, and
helpers must receive their own assigned context without an additional orchestrator role.

## Consequences

The orchestrator's full operating context is restored on the next invocation after compaction,
while ordinary turns add no duplicate payload. Each PreInvocation scans the transcript, and each
restoration consumes context for the whole page. Delivery depends on the host supplying a readable
transcript with `CHECKPOINT` and marked `SYSTEM_MESSAGE` records; unavailable transcripts are a
no-op rather than a reason to inject on every turn.
