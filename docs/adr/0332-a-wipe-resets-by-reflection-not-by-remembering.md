# ADR-0332 — A wipe resets by reflection, not by remembering

Status: accepted (2026-08-01)
Implements: the approved completion plan, Phase 1 (session hygiene) — the half that needs no
deployed-box data
Builds on: ADR-0263 (the wipe generation gates late stores), ADR-0186 / ADR-0324 (page memory and
the launch token), ADR-0315 (the Ollama record-use hook)

## Context

The plan's Phase 1 began with a reflection sweep of `SessionState` against the `/session/wipe`
handler. The handler reset fields by **naming** them, and the list had fallen behind the dataclass:
of 72 declared fields, 36 were untouched, and after subtracting the six cleared indirectly through
`set_filter(())` / `set_saved_group(None)` and three internals, **27 fields of real operator state
survived a wipe.**

What survived is not cosmetic:

* the entire SRA setup — `sra_factor_rows`, `sra_factors` (per-UID Risk Ranking Factors),
  `sra_bcwc` (per-UID Best/Worst duration pairs), `sra_corr_pairs` / `sra_corr_groups` (the
  correlation matrix), `sra_criticality` (the cached per-activity Criticality Index), plus the run
  configuration and `sra_file`;
* the **whole JCL cost configuration** (all seven `jcl_*` fields);
* `margin_rate` — while `margin_band_dates` / `margin_band_rates` / `margin_risk_pcts` *were*
  reset, an inconsistency nobody had noticed;
* `translations` — AI translations of **imported activity names**, i.e. schedule-derived text;
* and `dcma_acumen_parity` — a **metric-MODE flag** consumed as `acumen_parity=` by the scope
  signature and the DCMA audit.

**Why this is Law 2, not housekeeping.** `sra_factors`, `sra_bcwc` and `sra_criticality` are keyed
by **UniqueID**. Load project A, set its risk inputs, wipe, load an unrelated project B, and B
silently inherits A's Risk Ranking Factors and Best/Worst pairs wherever the UIDs collide — with
nothing on screen saying so. A wiped session that still carries a metric-mode flag is the same
class of defect: the next file is analysed under a basis chosen for the previous one.

The client side had a matching hole. ADR-0324's launch guard sweeps `sf-qs:` / `sf-ui:` plus a
hardcoded per-page column-picker list, so `sf-story-visited` — which `story.js` fills with each
visited chapter's `data-route`, and the analysis chapter's route resolves to
`/analysis/<the operator's filename>` — outlived every launch **and** every wipe.

## Decision

1. **Reset by reflection.** `SessionState.reset()` returns every field to its constructed default
   except a small, named `WIPE_PRESERVED` set. The default is now RESET; preserving something
   requires naming it with a reason. This is the property that matters: the *next* field added is
   wiped without anyone remembering to add a line.

2. **`WIPE_PRESERVED` holds seven entries, each justified in the source:** `language` and
   `ram_warn_bytes` (operator preferences — a wipe clears what was *analysed*, not how the tool is
   displayed); `ai_config` (bespoke — the classification is carried across and the backend forced
   back to `null`); `wipe_gen` (a monotonic guard — bumped, never rewound, or ADR-0263's late-store
   window re-opens); `ai_use_hook` (application wiring installed by `create_app`, not session
   data); `_lock` and `_stripes` (concurrency primitives — replacing a lock another thread may hold
   is a data race).

3. **The handler keeps only what needs ordering.** `/session/wipe` now calls `st.reset()`, then
   bumps `wipe_gen` and clears the on-disk cache under the same lock (ADR-0263's ordering is
   unchanged), then rebuilds `ai_config`. Every default the old enumeration set was verified
   identical to the dataclass default before the swap, so the change is behaviour-preserving for
   the 36 fields it already handled and behaviour-fixing for the 27 it did not.

4. **The launch guard gains `GLOBAL_KEYS`**, a list for cross-page keys holding schedule-derived
   data — currently `sf-story-visited`. Preferences (`sf-theme`, `sf-scale`, `sf-sysmon`,
   `sf-hum-mute`, `sf-hum-vol`, hint dismissals) are deliberately **not** swept: a blanket
   prefix sweep would un-mute the ADR-0328 boot hum and reset the theme on every launch, which is
   a regression dressed as a fix.

5. **Scope note — what this ADR does NOT claim to fix.** The operator's "information from a
   previous session" report has a second, larger cause: on the deployed install the shortcut pins
   port 8321 and `launcher.py` has no instance detection, so a relaunch can land on the *surviving
   previous process*. That is Phase 1's other half and is blocked on one measurement from the
   deployed box (whether a second bind fails or succeeds — the answer differs on Windows). Nothing
   here depends on that answer.

## Consequences

* A wipe is now provably total, and the proof is mechanical rather than clerical.
* `tests/web/test_session_wipe_is_total.py` enumerates the dataclass and requires every field to be
  classified — reset by default, deliberately preserved, or incomparable (`_lock`, `_stripes`,
  `ai_use_hook`). A field added without a decision fails the last test in that file. The preserved
  set is capped at 8 entries so it cannot quietly become the new leak.
* `dcma_acumen_parity` returns to its default (`True`) on wipe. Anyone who had toggled it off for a
  file must re-toggle it after a wipe — correct, since the flag chose a basis for schedules that no
  longer exist.
* A within-session `sf-story-visited` still records the current chapter's route, filename included.
  That is not narrowed here: inside a session the name is already in the URL and on the page, so
  hiding it in storage buys nothing. What is fixed is its *persistence across* sessions.

## Verification (all read from runs this session)

New suite `tests/web/test_session_wipe_is_total.py`: **5 passed** — including a control that
asserts the fixture actually dirtied ≥40 fields, so the sweep cannot pass vacuously. Session
neighbours (`test_launch_invalidation`, `test_session_consistency`, `test_saved_filter_session`,
`test_sra_view`, `test_jcl_web`, `test_ai_wiring`): **81 passed** together with the new file.

**Proved able to fail, watched.** Reverting *only* the handler (keeping the new API, so the failure
is behavioural rather than an import error) fails the route test with
`assert {7: 3} == {}` — the per-UID Risk Ranking Factor still resident after a wipe, exactly the
value that would have leaked into the next project. Reverting `persist.js` fails the browser test
with `'["/analysis/SecretProject.mpp","/"]'` still in `sf-story-visited`.

**A test bug this caught, recorded because the fix was right and the test was wrong.** The first
browser assertion required `sf-story-visited` to be *absent* after the sweep. It is not: the guard
clears it and `story.js`, running on the same load, immediately re-records the chapter being viewed
now. The assertion was corrected to test the property that matters — that nothing from the previous
project remains — rather than a stricter condition the design never promised.

Statics foreground: ruff "All checks passed!" · format clean (838 files) · mypy --strict "no issues
in 117 source files" · `node --check` clean. Full-suite + installer-lockstep results: SESSION-LOG.
