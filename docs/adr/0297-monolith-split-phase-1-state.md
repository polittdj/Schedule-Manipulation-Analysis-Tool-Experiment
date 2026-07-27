# ADR-0297 — Monolith split, phase 1: the session-state machinery moves to `web/state.py`

- **Status:** Accepted
- **Date:** 2026-07-27
- **Closes:** perf backlog item 7 of 7 — *phase 1* (opened by ADR-0281; the backlog is now clear)
- **Related:** ADR-0195 (never big-bang — integrate in phases), ADR-0263/0281/0292 (the state
  machinery this ADR relocates), ADR-0249 (the tests are the measure)

## Context

`web/app.py` had grown to **19,211 lines**: the session state + caches, a ~4,900-line `create_app`
holding every route, ~11k lines of presentation helpers, and the server lifecycle — one file, one
E501 exemption, one namespace. The perf backlog's final item is the split, and the house rule
(ADR-0195) is explicit: **phases, never big-bang**.

The riskiest coupling is not imports — it is **tests**. 126 test imports of `SessionState`, and a
family of tests that monkeypatch engine callables *through the app module's namespace*
(`monkeypatch.setattr(app_mod, "_compute_analysis", …)`). Python resolves a callee in the
namespace of the module that *calls* it, so moving a call site silently disconnects any patch
aimed at the old module — a test that still passes while spying nothing would be worse than a
loud failure.

## Decision

**Phase 1 extracts the state machinery — verbatim — into `web/state.py` (1,616 lines):**
`_LRUCache` + the cache caps, `_Flash`, `_Analysis` / `_DashCore` / `_dash_core`,
`_compute_analysis` (the single CPM pass every view reuses), `UnifiedRisk`, the `_Role` data
table, `SessionState`, and `_iso_date` / `_activity_rows` (the grid rows `_Analysis` carries).
`app.py` drops to **18,050 lines** and re-exports every moved name with the explicit
`X as X` idiom (mypy-strict `attr-defined` clean, ruff F401 clean), so **every existing import
path keeps working** — including `web/__init__`'s.

Rules applied, and to reuse in phases 2–3:

1. **Patch where the call site lives.** Tests spying `_compute_analysis`, `compute_cpm`,
   `compute_summary`, `audit_schedule`, `compute_float_bands`, `compute_baseline_compliance`,
   `recommend` (called from `state.py`) now patch `web.state`; tests spying
   `work_to_go_census` / `_parse_upload` / `_MAX_UPLOAD_BYTES` (called from `app.py` —
   `_perf_version_block`, the upload route) stay on `web.app`. Eleven sites moved across four
   files; two first-pass mistakes (both directions) were caught by the tests failing loudly —
   the perf-contract suite is precisely the harness that makes this refactor safe.
2. **The moved block is verbatim except line-wrapping.** `app.py` is E501-exempt (HTML
   f-strings); `state.py` has no HTML and earns no exemption, so 32 over-long comment/docstring
   lines were re-wrapped — comment and docstring whitespace only, no statement changed.
3. **`_OAT_MAX_ACTIVITIES` deliberately stayed in `app.py`** — its only caller is the SRA route,
   and a test patches it through the app namespace.

## Why this is the right phase-1 boundary

- It is the piece every other page depends on and the piece hardest to review inside a 19k-line
  file: the caches (ADR-0263/0281/0292), the epoch keying, the single-flight locks, and the
  analysis chokepoint are now one readable module with no HTML in it.
- It is cycle-free: `state.py` imports engine/ai/model only; `app.py` imports `state`. Nothing
  in `state.py` references route code or presentation helpers (verified by grep before the cut,
  and one miss — `_ROLE_BY_ID` in `set_role` — was caught by ruff F821 and resolved by moving
  the `_Role` data table too).

## Proof of behaviour-freedom

- Full suite **2,670 passed** (only the wheel-lockstep guard tripped, cleared by regenerating).
- The three **dashboard payload golden SHAs passed untouched** — the strongest oracle available:
  byte-identical payloads across the split, in both DCMA modes, with an unsolvable card.
- `pytest -m parity` 44 passed; ruff / ruff-format / mypy-strict / bandit / node all clean.

## Consequences

- Phases 2–3 remain, in this order, each its own behaviour-free PR: **(2)** the page chrome
  (`_LAYOUT`, nav/banner/page shell) → `web/chrome.py`; **(3)** the ~11k lines of
  `_*_body` / `_*_panel` / `_*_data` presentation helpers → per-page modules (these carry the
  HTML f-strings and take the E501 exemption with them). `create_app`'s routes stay in `app.py`
  until the helpers are out; splitting routes first would drag the whole helper tail with them.
- `CLAUDE.md`'s architecture note is updated (it declared "the entire UI in one (large) file").
- The perf backlog opened by ADR-0281 is **closed**: items 1–4 shipped (ADR-0288/0289/0291/0292),
  5 shipped (ADR-0293), 6 closed as a decision (ADR-0294), 7 phase 1 shipped here with phases
  2–3 queued as ordinary follow-on work, plus the two bonus items the backlog surfaced
  (ADR-0295's correctness fix, ADR-0296's dashboard trim).
