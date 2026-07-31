# 0320 — The /evolution exports honor the page state (and say what they applied)

Date: 2026-07-31
Status: accepted

## Context

The trace-options banner (`_optioned_versions`) promises that "every date and path on this
page (**including the Excel exports**) comes from the re-solved pure-logic network" — but
`/export/{fmt}/evolution` ignored every page parameter: no trace options, no `tier`, and not
even the page's own `?target=` focus (it read only the session-wide `SessionState.target_uid`).
The ⤓ export bar linked the bare route, so nothing the operator had set on the page reached
the workbook. Two page forms compounded it by DROPPING state on submit: the Focus form (and
its auto-submitting tier select) lost the active `ignore_*` options — silently flipping a
counterfactual view back to the stored basis — and the counterfactual "Run what-if" picker
reloaded with ONLY `cf_a`/`cf_b`, losing focus, tier and options. The clear-focus link did the
same. PR-6 of the approved queue (`docs/STATE/PLAN-20260730.md`), scoped to `web/app.py`.

## Decision

**One rule — the export mirrors the page, and headings state only what was applied.**

- The ⤓ bar carries the LIVE page state: `_evolution_state_qs` (urlencode; only non-default
  values emitted) appends `target`/`tier`/`ignore_constraints`/`ignore_leveling` to both
  links; a stateless render keeps the bare path byte-identical. Precedent: the `/resources`
  bucket link.
- `export_evolution` gains the SAME Query params as `/api/evolution` (ADR-0265's route),
  resolves the focus with the page's exact rule (`_parse_uid(target)` when the URL carries
  one, else the session target), and routes through `_optioned_versions`. Defaults reproduce
  the pre-0320 workbook byte-for-byte.
- **Applied-scope headings, two carriers** (the xlsx renderer never shows a TableSet title;
  the docx uses it as the H0): the TableSet title gains a suffix listing the APPLIED items
  ("driving path to UID N"; the option names from `_trace_option_names`, the new ONE source
  the banner also reads), and the workbook gains its own prepended "Applied scope" sheet.
- **`tier` is disclosed, never implied.** The tier stepper is an on-screen lens; these tables
  keep the path basis. A recognized tier (`_EVO_TIER_SELECT` membership — also the injection
  gate) adds the note "the on-screen tier view (X) is not applied - these tables keep the
  path basis" and NO title suffix. A wrong scope line would be worse than none.
- **Drop-nothing forms:** `_keep_hidden` (extracted verbatim from `_trace_options_form`) adds
  the missing state as hidden inputs — the Focus form keeps `ignore_*`; the what-if picker
  keeps `target`/`tier`/`ignore_*`; the clear-focus link keeps tier + options while emitting
  the explicit empty `target=` (which must override a session-wide target — an absent
  parameter would not). Defaults emit nothing, so default pages render byte-identically.

**A finding worth the record:** the session target and a URL `?target=` are NOT synonyms.
`SessionState.scope()` truncates the POPULATION of every version to the target's driving
subtree (`subschedule_to_target`, inside `_solvable_versions`), while `?target=` is a view
focus on the full population — the page renders those two states differently (e.g. the
truncated network's project finish is the target chain's finish). The export now mirrors the
page in BOTH states; a draft test asserting their equivalence was wrong and was replaced by
the mirror pin (`test_export_session_focus_applies_the_sessions_own_rule`).

## Consequences

- The export's strictness now matches the page's: a non-integer `ignore_*` value 422s where
  the parameterless handler used to ignore it (read this session: page 422 / export 422 —
  parity; no shipped link emits such a URL). Garbage `target` text means "no focus" and
  `tier=critical` (API vocabulary, not offered by the page select) stays a recognized tier —
  both 200, mirroring the page.
- Out of the approved scope, recorded not chased: the Focus form still drops `cf_a`/`cf_b`
  (the what-if pair resets to its two-most-recent default on refocus), and the trace-options
  form's pre-existing `tier=off` keep stays as-is.
- `reports/` untouched: the inner Table titles (pinned by `tests/test_coverage_misc.py`) and
  every other export are unchanged.

## Verification (all read from runs this session)

`tests/web/test_evolution_export_options.py` — 14 tests: bar query string live + bare default;
options change the workbook to the pure-logic dates (fixture oracle from the ADR-0265 suite:
stored `2025-01-2x` finishes vanish, `2025-01-08` appears); URL focus honored and
session-focus mirror pinned; scope sheet + docx H0 suffix present when scoped, absent by
default; tier disclosed not applied (and unknown tier ⇒ no disclosure); both forms + clear
link carry state; explicit-default URLs byte-identical to bare. **Proved able to fail:**
`app.py` stashed → 9 of 14 fail (the 5 passers are the deliberate non-regression pins) → pop.
Neighboring suites (evolution view / family-B unify / path options / coverage app + extra /
mission ×2 / coverage misc + the new file): **127 passed**. Statics: `ruff` 0.16.1 + format +
`mypy --strict` (117 files) + `bandit` exit 0 + `node --check` all clean.

**One freeze pin re-baselined, per its own prescribed path:** the r11 form-freeze
(`test_r11_panel_contract.py::PAGE_FORMS[EVO]`) pins the what-if picker byte-for-byte; the
drop-nothing rule legitimately grew it by one hidden input carrying the page's RESOLVED focus
(that fixture's session target 26). Refreshed deliberately with this ADR named — old
`25dd6f16300d15519223ee9df9738355`/803 → new `3b6af0bf329283581a407b90b7c70192`/847, computed
from a live fixture-identical render (never retyped) — while the two untouched `/evolution`
form pins (802 / 743) prove the round's other bytes did not move.

Full suite on this tree: **3157 passed, 1 skipped, 1 failed in 837 s** — the one failure is
`test_float_tip_dismiss` (the ADR-0314 browser suite for the `/analysis` DCMA callout, a page
this diff never touches) timing out its 4-second tip-SHOW wait under full-suite load. Triaged,
not hand-waved: it passed **18/18 rerun alone** and **54/54 in a 3× parallel probe on the
PRISTINE (stashed) tree** — a load-dependent sensitivity independent of this change, visible
only at full-suite concurrency on this session's restart-prone container. CI is the enforced
arbiter; if CI reproduces it, the timing posture gets its own fix.
