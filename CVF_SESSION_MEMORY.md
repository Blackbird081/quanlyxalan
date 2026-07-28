# Project Session Memory

Memory class: POINTER_RECORD

This is the project continuity front door. It is CVF-governed project state,
not provider-specific memory and not a chat transcript.

## Startup Order

1. Read `.cvf/manifest.json` and `.cvf/policy.json`.
2. Read `CVF_SESSION/ACTIVE_SESSION_STATE.json`.
3. Read the active handoff named by that state file.
4. Read `IMPLEMENTATION_STATUS.json` and `docs/INDEX.md`.
5. State current mode, active handoff, next allowed move, parked checkpoint,
   and active role before material work.

## Mandatory Continuity Rehydration

Repeat the startup order before material work at every new or resumed
chat/session, after context loss or compaction, at the start of every new
tranche or work order, and whenever responsibility or the active handoff
changes. Read current files again; do not rely on chat history,
provider-local memory, or a declaration from a previous session.

Emit a fresh `CVF Agent Declaration` before the first material action. At a
tranche transition, also record the acknowledgment in the active handoff
before BUILD. If continuity surfaces disagree, stop and report
`BLOCKED_CONTINUITY_DRIFT`.

Active state: `CVF_SESSION/ACTIVE_SESSION_STATE.json`

Initial active handoff: `CVF_SESSION/handoffs/AGENT_HANDOFF_V1_2026-07-27.md`

Provider-local files may assist execution but are not project source authority.
