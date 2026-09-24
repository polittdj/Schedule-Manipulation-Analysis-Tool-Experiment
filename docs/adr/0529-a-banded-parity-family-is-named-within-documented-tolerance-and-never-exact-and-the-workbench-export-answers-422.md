# ADR-0529 — A parity family a gate accepts inside a band is named "within documented tolerance" and never "exact" (R-18 / NUM-01 CLOSED); the workbench export answers 422 like its five siblings (R-39 CLOSED)

**Status:** Accepted · **Date:** 2026-09-24 · **Extends:** ADR-0472 (WP8, the register), ADR-0469 (RC-02, the export population), ADR-0511 / ADR-0492 (the SPI / TCPI pins), ADR-0515 (the round-site ledger — the instrument pattern reused here) · **Closes:** R-18, R-39

## Context

### R-18 — NUM-01: "parity" covered three different claims and the report called a banded one exact

The 2026-08-13 audit (NUM-01, P6) found "parity" used for an exact pin, a transcribed oracle, and
agreement inside a band, without the report saying which. The WP8 register carried it as R-18
("NOT re-read this session (UNVERIFIED)") with a doc-lint as its first step. This session read it.

Measured on the tree (an AST census of every `Compare` whose `<` / `<=` side is an `abs(...)`
call and every `pytest.approx(...)` comparison, over the CI parity step's population — verbatim
from `.github/workflows/ci.yml:85`: `tests/parity/`, `tests/engine/test_ssi_leveled_uid152.py`,
`tests/importers/test_msp_views.py`):

| Measure | Value |
| --- | --- |
| tolerance-shaped assertions the walker sees | **39** (+2 shapes it cannot see, below) |
| … classed `tolerance` (a real band) | **29** in 10 families |
| … classed `exact` (a zero band, a float epsilon, a bare `approx` at rel 1e-6) | **12** |
| occurrences of the word "tolerance" in `docs/PARITY-REPORT.md` | **0** |
| families banded in a test and ABSENT from the report | **9** of 10 (SEM, SSI 24h UID 155, SSI leveled UID 152, both SRA oracles, the stored finish within a day, the UID 188 chain, R-57, R-65) |
| a report row saying "✅ exact" beside a banded gate | **SPI (cost)** and **TCPI** (report :210–211) against `abs(...) <= 0.0101` (`test_fuse_metric_history_oracle.py:327–328`) — while the SAME file already pinned the same figures EXACTLY at 2 dp (:575–576, `test_hard_file_ev_and_acwp_equal_the_fuse_ribbon_from_the_bookings_records`) |

So the defect NUM-01 named was real and still on the page: a testimony reader of the SPI row
would cite "exact" for a gate that accepted a hundredth either way.

### R-39 — one status code among six

RC-02's six never-adverse exports (`evm` · `scurve` · `risks` · `mission` · `ribbon` ·
`workbench`) answered an empty session with 422 / 422 / 422 / a valid one-row workbook (ADR-0268)
/ 422 / **400**. The pin accepted `in (400, 422)`, so the split was invisible to the gate.

## Decision

### R-18 — the wording is linted against the tests, not against itself

1. **`tests/guards/parity_tolerance_ledger.tsv`** — every tolerance-shaped assertion in the CI
   parity population, one row per occurrence: `file · class · seen · site · anchor`. An `ast`
   row's site is the comparison's normalized source (the round-site ledger's key, ADR-0515); a
   `text` row's site must still occur in its file (the two shapes the walker cannot see: the
   leveled UID 152 battery's `d < 0.02` / `>= 775` / `worst <= 1.01`, where the `abs()` sits
   upstream of the compared name, and R-57's two-sided `0 < … <= 120`).
2. **`tests/guards/test_parity_tolerance_ledger.py`** — ties the ledger to the tree in both
   directions (a new, moved or reworded banded site is unclassified by name; a stale row is
   stale by name), requires every class to be one of two stated ones, and lints the report: every
   `tolerance` row's anchor must sit in `docs/PARITY-REPORT.md` on a line that says "within
   documented tolerance" and carries no "exact". Two negative controls prove both instruments
   can fail.
3. **`docs/PARITY-REPORT.md`** — a new section, **Tolerance-accepted families**, one row per
   family with its gate, its band and why it is a band; the headline tempered ("exact at the
   precision Fuse prints … the families a gate accepts inside a stated band are listed by name …
   and are never called exact here"); the SPI / TCPI rows say "exact at the 2 dp the ribbon
   prints".
4. **The SPI / TCPI gate tightened** (`test_fuse_metric_history_oracle.py:327–328`): the
   `<= 0.0101` band became the 2-dp equality the same file already holds on the same figures
   (`== round(float(rec["SPI"]), 2)`). A loose check beside an exact one on the same numbers was
   a wider gate than the tree already proved — tightening it is the honest fix, not relabelling
   an exact figure as banded.

### R-39

`/export/{fmt}/workbench` answers **422** on an empty session; the RC-02 pin is `== 422` on all
six (the `mission` case keeps its ADR-0268 workbook).

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| A1 | The CI parity population is `tests/parity/` + two named files | read `ci.yml:85–86` (both jobs) | **held** — the ledger names it verbatim |
| A2 | The tightened SPI / TCPI check passes on the pristine engine | ran the one test after the edit | **held** (the 2-dp pin at :575 already passed on the same figures) |
| A3 | The AST walker sees every banded assertion | compared the census with a read of every parity file | **FELL** — two shapes are invisible by construction (an `abs()` upstream of the compared name; a two-sided range); ledgered as `text` rows whose site must still occur in the file |
| A4 | Each family's anchor is unique to the tolerance table | the lint reads every line carrying the anchor | **held** — 0 stray lines after the doc edit; before it, "TCPI" hit three report lines (the NOT_APPLICABLE note, the CPI row, the TCPI row) — which is why the anchors are the table's own labels |
| A5 | The lint is red on the pristine report | ran it with the ledger built and the report untouched | **held** — 16 findings, the SPI / TCPI "'exact' sits beside a tolerance family" by name among them |

## Verification

* **Red-first.** The doc lint on the pristine report: 1 failed with 16 named findings (9 families
  not named, SPI / TCPI named without the phrase and with "exact" beside them). R-39: the
  tightened pin on the pristine tree — exactly `[xlsx-workbench]` and `[docx-workbench]` red, the
  ten sibling cases green.
* **Green.** `tests/guards/test_parity_tolerance_ledger.py` 7 / 7; `tests/test_parity_report_sync.py`
  + `tests/web/test_docs.py` 16 / 16 with it; `tests/web/test_rc02_adverse_paths.py` 64 / 64.
* **Mutation, 6 of 6 red by name:** "exact" inserted into the SEM row · the phrase dropped from the
  R-57 row · a new `pytest.approx(expected, abs=0.5)` in a parity test (unledgered, by name) · the SEM
  ledger row deleted (the tree's site unclassified, by name) · the leveled battery's `worst <= 1.01`
  reworded (the text row no longer in its file, by name) · the tightened SPI pin nudged a hundredth
  (`1.05 == 1.06`).

## Deliberately NOT done

* The AST walker reads shape, not value: a band carried in a NAME (`days` — 0 on every stored-dates
  row, `bcws_tol` 0.0, `_TOL_DAYS`, `tol`) is classified by the value the test binds at ledgering.
  A silent change of that value is caught by review of the test, not by the ledger; the guard's
  docstring says so.
* The eleven other exports that answer 400 on an empty or insufficient session (`trend`, `cei`,
  `evolution`, `forecast`, `curves`, `compare`, `sra`, `sra-registry`, the two risk templates,
  `brief`, `briefing`) and `/api/workbench`'s own 400 are outside R-39's six (the RC-02
  population) and are left as they are — named here so the split is a decision, not a drift.
* No i18n or help text names an export's status code; none was added.
