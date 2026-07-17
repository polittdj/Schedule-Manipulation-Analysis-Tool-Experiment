# ADR-0255 — role-selection front page: five audience roles as curated entry points (v4 F4)

## Status

Accepted. Closes standing queue item **F4 / v4 "roles front-end"**. No committed spec existed
(searched all docs + the Thursday directive), so this session proposed the design and the
operator approved it before build: **the 5-role list** (Scheduler/Planner, Program/Project
Manager, Forensic Analyst, Auditor (DCMA/IG), Counsel/Testifying Expert) **with
emphasis + role landing** behavior (the operator picked the deeper of the two offered depths).

## Decision

A role is a **curated entry point, never a mode**. Selecting one changes three things and
nothing else:

1. **Home "Start here" strip** — the role's 4–5 primary pages as cards with a one-line why
   each, drawn from the committed Mission-Ops spine (`_SPINE`); a card whose route cannot
   resolve yet (`@analysis` with nothing loaded) is skipped, never a dead link.
2. **Nav emphasis** — the role's pages get a `role-hl` accent highlight in the left nav.
   Every chapter stays rendered and reachable under every role (a test walks pages outside
   the active role's set and asserts they still render in the nav).
3. **Post-upload landing** — a CLEAN ingest lands on the role's primary page (Scheduler →
   `/ribbon`, PM → `/portfolio`, Auditor → `/standards`, Counsel → `/briefing`; Analyst
   inherits the default). Any ingest with errors/skips still lands on the dashboard so the
   manifest is seen — **disclosure outranks the role landing**.

Law-2/CUI safety by construction: the role can never hide a page, change a computation, a
default parameter, or a number — the mapping is a static committed table (`_ROLES`) of
existing routes; no engine import, no AI involvement. "Show everything" (no role, the
default) reproduces the pre-F4 behavior exactly — the upload-destination logic is
byte-compatible when `role is None` (pinned by test). `SessionState.role` is fail-soft
(unknown ids ignored), cleared on wipe, set via `POST /role`.

## Consequences

- `web/app.py`: `_Role` + `_ROLES` + `_ROLE_BY_ID` (by the spine), `_role_strip` (picker +
  Start-here cards), `SessionState.role` + `set_role` + wipe clear, `POST /role`, the
  `role-hl` nav class, and the role-aware upload destination. `base.css`: `.role-strip` /
  `.role-card(.active)` / `.start-card` / `.nav-chapter.role-hl` — theme tokens only,
  verified in all four themes (the active pill carries a doubled accent ring so it stays
  distinct even where a theme outlines every button).
- Tests (`tests/web/test_roles_front_end.py`): picker renders all five + "Show everything"
  with the contract stated on-page; persistence + fail-soft + wipe; Start-here strip + nav
  highlight with everything still reachable; `@analysis` card gating; the three landing pins
  (role landing / no-role default preserved / analyst inherits); errors-outrank-landing.
- Engine, metrics, parity: untouched (no engine file in the diff).
- Future: per-role default exports or briefing templates would be separate ADRs; the role
  list itself is operator-editable only through code (deliberate — the mapping is part of
  the reviewed, testimony-safe surface).
