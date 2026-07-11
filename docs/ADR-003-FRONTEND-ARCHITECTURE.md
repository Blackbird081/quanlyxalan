# ADR-003: Frontend Architecture for the Local Pilot

- **Status:** ACCEPTED
- **Date:** 2026-07-11
- **Scope:** T5 product professionalization, local/pilot deployment

## Context

The application is a single FastAPI-served interface with a bounded operational
scope: declarations, vessels, crew, imports, reports and an ADMIN operational
summary. The existing frontend is modular plain JavaScript with a small API
wrapper and no build pipeline. A framework migration would add a compiler,
package supply-chain, new test/tooling ownership and a parallel rewrite risk.

## Decision

Continue with modular Vanilla JavaScript for the local pilot. Improve it in
place through explicit rendering boundaries, accessible semantic HTML, loading
and recovery states, and static/regression checks. The API remains the sole
authority for authorization and workflow decisions; UI visibility is not a
security control.

## Guardrails

- Keep API calls centralized in `frontend/app.js`; do not place role authority
  or workflow enforcement in the browser.
- Preserve server responses as the source for role-scoped queues and actions.
- Any new dialog must use native dialog semantics and be keyboard tested.
- Add a static assertion for each material accessibility contract that can be
  checked without a browser, and execute manual keyboard checks before Gate 5.

## Revisit criteria

Create a separately approved framework-migration plan only if one or more of
the following is sustained: more than three independently owned frontend
modules, repeated state synchronization defects, a required offline workflow,
or measurable performance/accessibility constraints that the current approach
cannot meet. The plan must include migration scope, dependency security review,
browser regression strategy and rollback path.

## Consequences

This avoids a premature rewrite and keeps local installation simple. It does
not close Gate 5: representative-user testing, an accessibility review,
responsive browser checks and agreed performance budgets remain required.
