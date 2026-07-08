# ADR-0162 — Per-change counterfactual effect on the target (fix the "zero effect" AI answer)

## Status

Accepted. Operator 2026-07-08: "On the Schedule Integrity Page I want you to calculate what the
effect would have been for each change to either the target UID if the user has chosen one or the
last task on the critical path if these changes were not made. … I reestablished … the relationship
between UID 188 and UID 187 to see what the effect would have been on UID 155 … Fix this in the
Schedule Integrity Page and the Ask the AI page." The operator asked the AI "If the schedule logic
on UID 187 had not been changed what would the effect have been on UID 155…" and was told the effect
"would be zero" — which is wrong.

## Context

Between `Hard_File` and `Hard_File_updated` the FS link **188→187** was removed. UID 155's finish is
2026-11-27 in the later file. Restore *only* that one link and re-run CPM and UID 155 moves to
2026-12-31 — a **+23 working-day (33 calendar-day)** slip the removal hid. The tool was answering
"zero effect" for two related reasons:

1. The existing **path counterfactual** (`engine/path_counterfactual.py`) only reverts activities
   that *left* the critical/driving set after their own change. UID 187 stayed critical, so the
   removed 188→187 link was never reverted and its effect never measured. The AI fact base carried
   no fact about it, so the model — correctly, given its evidence — could not find a non-zero number
   and defaulted to "zero."
2. Nothing on the Integrity page computed a **per-change** effect on a chosen target at all; it
   showed findings + the (incomplete) path counterfactual.

## Decisions

1. **New engine module `engine/change_effects.py`.** `compute_change_effects(prior, current,
   current_cpm=None, *, target_uid=None)` reverts **each detected change one at a time** on a copy
   of the later version, re-runs CPM, and reports the working-day movement of a chosen target's
   finish and of the project finish — plus one aggregate with every change reverted together. It
   covers all four structural change kinds from `diff_versions`: removed logic links (restore),
   added logic links (drop), duration changes (restore prior), and constraint changes (restore
   prior). Unlike the path counterfactual it does **not** gate on critical-set membership, so a
   change whose endpoints stay critical (the 188→187 case) is still measured.
2. **Target resolution matches the operator's words.** When a target UID is set it is used; when not,
   the target is the **last task on the critical path** — the effective-critical activity with the
   latest early finish (`_last_critical_uid`, via `path_evolution.effective_critical_set`), falling
   back to the max-early-finish scheduled task when no critical set exists.
3. **Sign convention matches the path counterfactual.** `finish_delta_days > 0` means the reverted
   (un-made) change would finish LATER — i.e. the change pulled the finish in and **hid** that much
   slip; `< 0` means the change pushed the finish out.
4. **Wired into both surfaces the operator named.** The Integrity page (`web/app.py::_integrity_body`)
   renders an "Effect of each change on <target>" table (per-change effect on the target finish + on
   the project finish + citations, sorted by magnitude, plus the aggregate). The Ask-the-AI fact base
   (`ai/qa.py::manipulation_forensics_facts`) emits one cited `CitedStatement` per change ("…reverting
   it … moves the finish +23 working day(s) LATER — the change hid that much slip…") plus an aggregate
   fact, so the model now has the engine-computed figure and can no longer answer "zero."
5. **Chrome shipped alongside (same operator message).** (a) Nav active-page highlight is now a
   high-contrast **yellow pill outlined in black** (`#ffd400`, `app.css`) instead of accent-blue on
   the blue ribbon, and picks a **single** winner — exact match else the single longest path-prefix
   with a segment boundary (`hints.js`) — so `/briefing` no longer also lit `/brief` (the
   "Diagnostic Brief shows when I choose Executive Summary" bug). (b) The AI **Generation timeout**
   default is raised to the form maximum **3600 s** (`ai/backend.py::AIConfig.gen_timeout`) so a slow
   local model can finish a full answer ("make the default the max").

## Consequences

- The 188→187 regression is fixed at the source: the Integrity page shows "restore removed FS link
  188→187 | +23 wd | +23 wd | UID 188, UID 187", and the AI fact base carries the same +23-working-day
  cited fact, so neither surface can report "zero effect." Verified end-to-end via TestClient against
  the `Hard_File` / `Hard_File_updated` golden pair.
- The engine number (+23 wd / +33 cal on UID 155) is well-founded from CPM; cross-validation against
  the operator's reestablished-logic SSI export (`UID_155_Directional_Path_Analysis…xlsx`) remains a
  pin-when-it-lands follow-up (it is not yet on `main`).
- Law 2 upheld: every displayed number is engine-computed by reverting a real change and re-running
  the deterministic CPM — no curve-fit, no fabricated "probably zero." Law 1 untouched (pure
  in-memory recomputation, no new I/O). Parity untouched (golden tests assert counts/values, not
  these counterfactual deltas). New tests: `tests/engine/test_change_effects.py` (4) +
  `tests/web/test_change_effects_integration.py` (4, incl. the +23-wd fact and the chrome fixes).
