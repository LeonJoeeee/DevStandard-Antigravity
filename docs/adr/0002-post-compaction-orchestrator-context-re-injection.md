# 0002 — Post-compaction orchestrator context re-injection

Status: Accepted (2026-10-22); Amends 0001 (post-compaction orchestrator context delivery via PreInvocation); Amended (2026-10-30).

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

**Amendment (2026-10-30):** Extend `PreInvocation` post-compaction context restoration to
explicitly dispatched native Antigravity `worker` subagents while keeping `SessionStart`
orchestrator-only and replacing full-transcript scans with a reverse-tail scan:

1. **Dispatched native worker restoration:** `SessionStart` continues to suppress all subagents
   because `scripts/dispatch` already delivers `reference/worker.md` and `# Task packet` in the
   initial prompt. On `PreInvocation`, `target_role_relpath()` restores `reference/worker.md` after
   a newer `CHECKPOINT` when `DEVSTANDARD_ROLE` is unset and either `agent_type` is `worker` /
   `devstandard:worker` or `subagent_role(event, strict=True)` resolves `'worker'` from
   `.system_generated/subagents/<conversationId>.json` (even when `parentConversationId` is
   present). The worker preamble directs the compacted subagent to recover dynamic `# Task packet`
   fields (`Issue`, `Branch`, `Worktree`, `Bounds`, `Done-check`) from the issue's
   `devstandard-dispatch-v1` receipt or local transcript. Reviewers, `research` subagents, untyped
   task-local helpers (`strict=True` returning `'helper'`), CLI runs (`DEVSTANDARD_ROLE`), and
   unrecognized `parentConversationId` sessions remain suppressed (`{}`). `hooks/pre-tool-use`
   keeps `subagent_role(event)` with `strict=False` so untyped helpers still inherit the `worker`
   command refusal list.
2. **Byte-safe reverse-tail transcript scan:** `needs_context()` verifies `transcriptPath` is a
   regular file (`stat.S_ISREG`) and reads backward from EOF in fixed-size byte chunks
   (`TRANSCRIPT_CHUNK_BYTES`), carrying leading partial-line bytes across chunk boundaries before
   UTF-8 decoding. Inspecting valid JSON object records from newest to oldest returns `True`
   immediately on `CHECKPOINT`, `False` immediately on a `SYSTEM_MESSAGE` carrying
   `DevStandard operating context: <role_relpath>` or the missing-page stop warning, and `False`
   at BOF without a `CHECKPOINT`, bounding per-turn latency regardless of total transcript length.
