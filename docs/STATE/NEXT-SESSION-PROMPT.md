# Kickoff prompt for the next session

Paste the block below verbatim to start the next session.

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; POLARIS in the UI). **Read `docs/STATE/HANDOFF.md` first**, then the full
findings in **`docs/STATE/AUDIT-2026-07-13.md`** — a read-only, falsification-oriented audit (7 parallel
agents + re-validation; every finding validated ≥4 ways) was just completed. `main` is green at
**v1.0.18** (HEAD `2c55769`), highest ADR **0211**. **No fixes have been applied yet** — the audit only
wrote the report + refreshed the state docs.

**Your mandate:** work the audit's remediation backlog, **one PR per theme**, fully gated, most
value-per-risk first. Nothing found is a CRITICAL/egress defect — these are fidelity, presentation,
dead-defense-in-depth, test-false-confidence, and doc-drift fixes. Confirm each fix against the
evidence in the audit report before changing code; several findings include a "verify X first" caveat.

**Two non-negotiable laws (CLAUDE.md):** (1) **Data sovereignty** — no schedule content leaves the
machine; AI is loopback-only and fails closed; runtime I/O is std-lib only; never commit real
`.mpp/.xlsx/.aft/.xer/.docx`. (2) **Fidelity over speed** — numbers must match Acumen/SSI; never
fabricate; parity is gate-locked (`pytest -m parity`). Do **not** touch `engine/` for a
presentation-only fix.

**Recommended order (each = its own branch off latest `origin/main`, draft PR, full gate, ADR + HANDOFF
+ SESSION-LOG refresh with the new ADR number in both docs):**

1. **Docs-only sweep (cheapest, zero code risk, fixes a HIGH).** Fix H2 (USER-GUIDE default Q&A mode is
   **annotate**, not interpretive; describe all 3 modes), M9 (the `.aft`/intake is committed per
   ADR-0152 — correct CLAUDE.md's Bible section, README:108, and the `test_aft_formula_audit.py`
   docstring), M10 (add Metric Workbench / SRA Excel round-trip / 12-chapter nav / 4 themes to
   README + USER-GUIDE; stamp USER-GUIDE), M12 (FINAL-REPORT SSI → 108/108 UID 145; 4 themes), M13
   (batch cap → 100), L11 (M15 wording), L12 (four themes, not a toggle), L13 (DESIGN-SYSTEM rollout
   status), N3 (introduce the POLARIS name). No ADR needed (docs only) — but still refresh HANDOFF.

2. **Presentation-bug PR (UI, no engine math).** Fix M2 (replace the `"&mdash;"` KPI sentinel with the
   literal "—" char in the 7 affected headers — see AUDIT §M2 for the exact `app.py` lines), L1
   (workbench NA metric shows "0.00" — send `value: null` or an `applicable` flag for inapplicable
   checks so `fmt` renders "—", **without** breaking informational NA extras like logic_density), L2
   (`_what_changed_header` mixes active/inactive populations), L10 (chapter-01 Gantt legend hardcoded
   hexes → theme tokens). Add a rendering test that a missing-value KPI emits "—" and a NA workbench
   cell emits "—". Verify in all four themes (Chromium; `executable_path="/opt/pw-browsers/chromium"`).

3. **Chapter-01 Critical basis (M3).** Decide: make `_where_we_stand_header`'s "Critical (incomplete)"
   KPI + float bands use `effective_total_float`/`is_effective_critical` (align with ribbon + ch 11),
   OR correct the comment and accept pure-CPM — but reconcile so one file reports one Critical count
   across chapters. Presentation only; pin with a test on a progressed fixture.

4. **`sra_conclusions._wd` calendar fix (M1, engine fidelity).** Thread
   `sch.calendar.working_minutes_per_day` into `_wd` (480 fallback only for a 0-minute calendar),
   mirroring the `recommendations.py` D13 fix. Add a `TP2` (600 min/day) test asserting the contingency
   / predictability day-counts. Parity-safe (percentiles/dates already use the real calendar).

5. **24-hour calendar parse (H3, importer fidelity).** FIRST verify whether the `.mpp`/MPXJ path emits
   `00:00→00:00` or `00:00→24:00` for a 24h calendar (convert a 24h `.mpp` with
   `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in.mpp> <out.xml>` and inspect). If it
   emits `00:00`, fix `working_time_span` to treat `from==0 and to==0` as `(0,1440)` (a real non-working
   day is `DayWorking=0` with no `WorkingTime`). Add an MSPDI 24h-calendar fixture + test; re-run parity
   to confirm no regression. Consider the sibling XER fix (L8) in the same PR (shared `working_time_span`).

6. **AI figure-gate hardening (H1 + M4 + M5).** (a) Gate `_ai_translate` with
   `citations.preserves_figures(src, translated)` — fall back to source on mismatch (H1). (b) Extend
   the shared `figure_tokens` with a bounded number-word lexicon so introduced number-words are caught
   in every gate (M4). (c) Add the missing accusatory terms + stem matching to `_LOADED_TERMS` (M5).
   Add adversarial tests for each (a translated digit-flip is dropped; a "twenty" strict answer is
   discarded; a "fabricated" polish is rejected). This is the highest-care PR — it touches the Law-2
   guarantees; keep changes minimal and test-driven.

7. **Wire the dead CUI defenses (M6 + L3).** Call `configure_logging()` and `assert_local_only()` once
   at process start (`launcher.main()` + top of `create_app()`), so log redaction and the egress guard
   actually run in the shipped app. Add a startup-assertion test. Optionally extend the egress
   forbidden-set (L4) in the same PR.

8. **Test-coverage PRs (E/F + the smaller ones).** Add a `chartframe_harness.mjs` (M7) and a
   `workbench.js` node harness (M8) that execute the JS against a stub DOM and assert rendered
   call-out text / cell formatting / sort order — the repo already has the pattern
   (`tests/web/js/sra_derive_harness.mjs`). Then the low-severity test tightenings (metric_catalog
   NA-guard branch; sra_conclusions tier boundaries + idiom allowlist).

9. **Low/Nit cleanup, batched:** MSPDI decode ladder (L7), XER calendar `working_days` + baseline
   semantics (L8/L9 — L9 needs a P6 reference check + ADR), air-gap test route enumeration (L5),
   pre-commit archive extensions (L6), `xlsx_read` decompression cap (N1), stored-slack ROUND_HALF_UP
   (N2). Also add the durable guard M11 suggests: have the version-sync test assert the pyproject
   version string appears in HANDOFF.

**Do NOT re-report or re-fix** the audit's VERIFIED-CLEAN items or the dismissed pip-audit noise
(ambient container packages, not the `.[dev]` closure — see AUDIT "Dismissed after validation").

**Workflow:** `git fetch origin` → branch fresh from `origin/main` (squash-merges make stacked
branches conflict) → one PR per theme → full gate before every push (`ruff check src/ tests/`,
`ruff format --check .`, `python -m mypy src/`, `bandit -q -r src`, `python -m pytest -q`,
`node --check src/schedule_forensics/web/static/*.js`) → any UI change verified in all four themes in
Chromium → update `docs/STATE/HANDOFF.md` + append `docs/STATE/SESSION-LOG.md` with the new ADR number
in both (the drift guard `tests/test_state_docs.py` enforces it) → regenerate
`docs/METRIC-DICTIONARY.md` if `help.py` changed. After each squash-merge, restart the branch with
`git fetch --prune origin && git checkout -B <branch> origin/main`.

---

## Quick reference (entry points on `main`)

- **Engine:** `engine/cpm.py` (`compute_cpm`); `engine/metrics/` (one module per family; `_common.py`
  has `effective_total_float`/`is_effective_critical`); `engine/sra.py` + `engine/sra_conclusions.py`
  (ADR-0201); `engine/metric_catalog.py` (ADR-0204 Workbench library).
- **Importers:** `importers/mspdi.py` (rich path), `xer.py`, `json_schedule.py`; `.mpp` via vendored
  MPXJ (`tools/mpxj/`, Java) — see CLAUDE.md for the conversion command; `_common.py::working_time_span`
  is the calendar-span parser at the centre of H3/L8.
- **AI:** `ai/qa.py` (mode gate), `ai/citations.py` (`figure_tokens`/`preserves_figures`/`reattach`/
  `introduces_loaded_terms`), `ai/narrative.py`, `ai/briefing.py`; `ai/backend.py::route_backend`
  (loopback-only, falls closed to Null).
- **Web UI:** the whole app is `web/app.py` (E501-exempt); chapter headers are the `_*_header`
  functions; page-shell helpers `_stat_cards` (:6867) / `_status_stack` (:7203); `_e` (:1724) is the
  HTML escaper; vendored JS/CSS under `web/static/` (four themes in `sf-themes.css`).
- **Reports:** `reports/xlsx.py` (writer) + `reports/xlsx_read.py` (std-lib reader, ADR-0211);
  `reports/tables.py`; `reports/docx.py`.
- **Guards:** `net_guard.py` (egress), `logging_redaction.py` (CUI redaction) — both implemented +
  unit-tested but **not wired at runtime** (M6/L3); `.githooks/pre-commit` (CUI file block).
- **Docs/state:** `docs/STATE/AUDIT-2026-07-13.md` (this audit), `HANDOFF.md`, `SESSION-LOG.md`,
  `docs/adr/` (0000–0211), `docs/DESIGN-SYSTEM.md` (Mission Ops rulebook), `docs/METRIC-DICTIONARY.md`
  (generated from `web/help.py`).

## Files most likely to be touched (by step)
- Step 1: `docs/USER-GUIDE.md`, `README.md`, `CLAUDE.md`, `docs/FINAL-REPORT.md`,
  `tests/engine/test_aft_formula_audit.py` (docstring).
- Step 2: `src/schedule_forensics/web/app.py` (KPI sentinels + legend), `web/static/workbench.js` +
  `/api/workbench` serializer.
- Step 3: `src/schedule_forensics/web/app.py::_where_we_stand_header`.
- Step 4: `src/schedule_forensics/engine/sra_conclusions.py`.
- Step 5: `src/schedule_forensics/importers/_common.py` (`working_time_span`), `importers/mspdi.py`,
  a new MSPDI 24h fixture under `tests/fixtures/`.
- Step 6: `src/schedule_forensics/ai/citations.py`, `web/app.py::_ai_translate`.
- Step 7: `src/schedule_forensics/launcher.py`, `web/app.py::create_app`.
- Step 8: `tests/web/js/` (new harnesses).
