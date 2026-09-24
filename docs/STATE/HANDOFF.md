# Handoff — 2026-09-24 (b) (five §3 rows worked in order — R-18 / R-39 (ADR-0529), R-22 / R-32 / R-21 re-priced (ADR-0530), R-71's RECORD limbs (ADR-0531) — **v1.0.292**)

STATUS (current) — branch **`claude/polaris-smat-continue-4cmkc2`**, draft PR opened this session (the operator merges; never marked ready here). Based on `main` @ **`a65e1b21`** (#715, ADR-0527, v1.0.290). §0's anti-foreign-prompt block was RUN and the tree agreed on every point (a65e1b21, 814 commits after `--unshallow`, `src` present / `app` absent, both workflows, 1.0.290, highest ADR 0527 on main — 0528 lives only on PR #716's branch). **PR #716 (R-13 / ADR-0528, v1.0.291, `claude/tender-ptolemy-ua1y6k`) is still a DRAFT** — read to conclusion this session: **all EIGHT checks green** (cui-guard · browser · floor · test (3.11) · test (3.13) · check · linux · windows; `check` posted 09:38 UTC); its local suite was never finished (61 %), CI was its gate and it passed. `main`'s own CI + installer-smoke runs for a65e1b21 were read from their JOBS: **all green**. This PR and #716 both touch the state docs, `pyproject.toml` and the nine installers — **whichever merges second needs a merge-resolve** (this one takes v1.0.292 and ADR-0529–0531 so nothing collides by number). `src/` changed (`engine/cpm.py`, `web/app.py`, `web/static/wbs.js`): wheel + nine installers rebuilt LAST, so **EIGHT checks**. Highest ADR **0531**. Version **1.0.292**. Schema **2.17.0** (unchanged). QC-1 / QC-2 / QC-3 bind every session.

## What landed — §3 worked in order, each row's premise re-read first

**R-18 / NUM-01 CLOSED (ADR-0529).** `tests/guards/parity_tolerance_ledger.tsv` (41 rows: 29 `tolerance` in 10 families, 12 `exact`) + `test_parity_tolerance_ledger.py`: tree ↔ ledger both ways (an AST census of `abs(...) <=` and `pytest.approx` sites over the CI parity population, plus two `text` rows for the shapes the walker cannot see), and ledger → `docs/PARITY-REPORT.md` (every banded family named under **Tolerance-accepted families** as "within documented tolerance", never "exact"). Red on the pristine report with 16 named findings — the SPI / TCPI "✅ exact" beside a `<= 0.0101` gate by name; that gate is now the 2-dp equality the same file already held. 6 / 6 mutants red.

**R-39 CLOSED (ADR-0529).** `/export/{fmt}/workbench` answers 422; the RC-02 pin is `== 422` on all six (red on exactly the two workbench cases first).

**R-22 CLOSED (ADR-0530).** The row's premise was half wrong: the pivots are server-rendered (`wbs.py`) and only `wbs.js`'s axis-title call at line 133 is pinned — the file is NOT byte-frozen (the layout test's docstring said so; corrected). Every body row of BOTH pivots now `SFDrill.mark`s its branch below that call (neither pin moved); `test_wbs_row_drill_browser.py` red-first (0 of 44), census drill floor 8 → 38, mutant 2 / 2 red.

**R-32 / CI-04 CLOSED (ADR-0530).** The race is a FRAME chain, measured in-page: the header paints at 137 characters with the pane overflowing by 10 px; two frames later the data-date seat scrolls to that edge, the edge-extend adds 60 days, the header is 216 characters — 50–110 ms after the paint, both pages, every load. A held asset (no web fonts exist; `app.css`) and CPU throttling × 20 reproduce nothing. The oracle reads both pages SETTLED; the induced-delay proof holds `/driving-path`'s animation frames 400 ms per hop with teeth; the dropped-wait mutant red. **Product finding registered, not fixed:** the whole-schedule view opens with its timescale extended by 60 days whenever the pane overflows by under an inch.

**R-21 re-priced, OPEN (ADR-0530).** ADR-0458's probe is committed (`tools/analysis_scroll_probe.py`). On this box the wheel sequences read p95 17–50 ms UNCHANGED and the re-aim-forcing programmatic steps 150 (ADR-0458's 150) → 86–115 ms with every sticky cell stripped (67–100 links off): the "p95 ≤ 50" criterion is met where it cannot discriminate and unreachable where it can. No frozen pane built blind.

**R-71's RECORD limbs CLOSED (ADR-0531).** Corpus rebuilt (44 files, 22,105 activities, keyed on PATH). A finished activity's late start / finish ARE its actuals with zero total and zero free float (8,644 / 8,644; the engine read 0 / 8,644 and non-zero free on 8,079 before); a started activity's late start is its actual start (1,159 / 1,159) with its total slack the FINISH slack alone — the file itself says so: StartSlack 0 and TotalSlack == FinishSlack on 1,159 / 1,159. Nothing else moved: unstarted late dates 10,829 / 10,332 and started slacks 1,012 exact before and after. **The clamp is REFUTED as a rule:** 23 started activities carry a negative FinishSlack, 22 store LF = EF, and UID 187 on the logic-reestablished Hard_File stores LF 3.5 days BELOW EF — residual named, unfloored figure kept. **Consequence raised to the operator:** the pure `is_critical` (kept pure by ADR-0527's ruling) reads True on finished work (0 ≤ 0); every product Critical figure goes through `is_effective_critical` or scores incomplete work so nothing reported moved; the stored-dates oracle's raw-flag census is re-scoped to incomplete work (110 / 103 / 76 / 68 / 19 · 106 / 99 · 1 024 / 998 — each the old figure less its file's finished count) with the record pinned exactly on every finished activity. If the raw flag should stay False on finished work, that is one clause — not decided here.

## How it was verified

QC-3 attacked 20 assumptions across the three ADRs; **7 fell** (R-22's premise ×2; a substring row locator that clicked the wrong branch; R-32's prescribed asset hold and CPU throttling; R-21's own settle premise; the clamp rule). Red-first on every row; mutants: R-18 6 / 6, R-22 2 / 2, R-32 1 / 1, R-71 3 / 3 (9 / 6 / 12 pins red by name). Engine 1,316 / 1,316 after nine dated re-baselines; stored-dates oracle 15 / 15. Gate figures (parity, full suite) are in the session log entry for this session.

## Deliberate re-baselines (all dated in the tests)

SPI / TCPI gate `<= 0.0101` → `== round(x, 2)` · RC-02 `in (400, 422)` → `== 422` · census drill floor 8 → 38 · `test_float_analysis` raw critical 41 → 61 / 4 → 31 (incomplete counts unchanged) · `test_free_float_bounded_by_total` 427 → 423 · the DCMA-12 rig −DAY → 0 · five started-work pins from the need to the record · the wall-field sentinel allows the record's late walls · the oracle's Critical floors re-scoped to incomplete work.

## Not done (measured, left) · carried forward

R-71's clamp (UID 187 counter-witness) · R-21's pane (criterion re-priced) · R-22's encodings (verbatim table) and the pivots' `scope=col` row headers · R-32's product finding (the 60-day extension on open) · DCMA-13's pure-branch min over ALL timings (unmoved on the four progressed goldens; would read 0 on a file whose incomplete work all has positive float) · the eleven other exports answering 400 · the AST walker's blind shapes (text rows). **UNVERIFIED:** nothing in this handoff — every figure above was re-read from a run. **Next:** R-68 waits on the operator; the raw-flag question (ADR-0531); then the register's remaining OPEN rows by tier.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
