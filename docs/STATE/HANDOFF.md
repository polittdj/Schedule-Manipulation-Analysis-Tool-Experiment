# Handoff — 2026-07-17 (v4 F4: role-selection front page; v1.0.64; highest ADR 0255)

> ## STATUS (current) — ADR-0255: the ROLE-SELECTION FRONT PAGE is live — five audience roles (Scheduler/Planner, Program/Project Manager, Forensic Analyst, Auditor DCMA/IG, Counsel/Testifying Expert) as CURATED ENTRY POINTS, operator-approved design (5 roles + emphasis + role landing). A role is never a mode: it can't hide a page or change a number. Version 1.0.63 → 1.0.64 (wheel + 9 installers in lockstep). Full gate green incl. `parity`.
>
> - **What a role does (exactly three things).** (1) A home **"Start here" strip** — the role's
>   4–5 primary pages as cards with one-line whys, from the committed `_SPINE` (an unresolvable
>   `@analysis` card is skipped until a schedule loads — never a dead link). (2) **Nav emphasis** —
>   `role-hl` accent on the role's chapters; EVERY chapter stays rendered under every role
>   (pinned). (3) **Post-upload landing** — a CLEAN ingest lands on the role's page (Scheduler →
>   /ribbon, PM → /portfolio, Auditor → /standards, Counsel → /briefing; Analyst inherits the
>   default); any errors/skips still land on the dashboard — disclosure outranks the landing
>   (pinned). "Show everything" (default) is byte-compatible with pre-F4 behavior (pinned).
> - **Wiring.** `_Role`/`_ROLES` static table by the spine; `_role_strip`; `SessionState.role`
>   (fail-soft `set_role`, cleared on wipe); `POST /role`; role-aware upload dest; `.role-card` /
>   `.start-card` / `.nav-chapter.role-hl` CSS — theme tokens only, 4-theme verified (active pill
>   carries a doubled accent ring so it reads in JARVIS where every button is outlined). No
>   engine file touched — parity untouched by construction.
> - **Verified.** `tests/web/test_roles_front_end.py` (6): picker renders all 5 + Show everything
>   with the contract stated on-page; persist/fail-soft/wipe; strip + nav highlight with
>   everything still reachable; @analysis gating; the three landing pins; errors-outrank-landing.
>   4-theme Chromium green (console/daylight/apollo/jarvis).
> - **State:** v1.0.64; **ADR-0255**; wheel + 9 installers in lockstep; full gate green.
> - **NEXT — the standing queue:** **#13** XER per-task calendars (still PARKED — the operator's
>   owed `.xer` files) → the ADR-0251 family-B option-plumbing unify PRs (forward toggles to
>   /api/evolution; full-trace export basis; drill field columns — each needs golden
>   re-validation) → the zero-margin SRA toggle (Fig 7-43 fidelity, via the existing three-point
>   surface, ADR-0254's documented follow-up) → deferred perf (ADR-0249 harness). Operator-side
>   (no code): the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map + the §4 root-vs-mpp
>   `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
