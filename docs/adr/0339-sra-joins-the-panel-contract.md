# ADR-0339 — `/sra` joins the panel contract

Status: accepted (2026-08-02) — Phase 3 (UI), third and final Act III conversion PR

## Context

ADR-0337 converted chapter 12 (`/briefing` + `/brief`); ADR-0338 converted `/risks`, chapter 11's
sub-page. `/sra` — chapter 11 proper — was the last Act III route outside the contract, and the
largest. Measured on the pristine tree by rendering the page, not by grep:

| route | panels | heads | tools | ⛶ | takes | chips | panelkit | takeaway h1 | lede |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/sra` before | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | **0** |
| `/sra` after | 15 | **12** | **12** | **12** | **12** | **12** | **1** | 1 | **1** |

Two carried figures were wrong and are corrected here:

* the long-carried estimate of **13 panels** was already known to be wrong (ADR-0338 measured 15);
  15 is confirmed again on this tree.
* the carried line-count attributed ≈295 of `/sra`'s ≈550 rendering lines to `_sra_report_blocks`.
  **`_sra_report_blocks` does not render this page at all** — it builds the `.docx` SRA report for
  `@app.get("/export/{fmt}/sra")`. The page's 15 panels come from `_sra_body`, `_sra_explainers`,
  `_sra_overrides_table`, `_ssi_panel`, `_correlation_matrix_panel`, `_jcl_panel` and
  `_what_could_go_wrong_header`. The conversion is correspondingly smaller than budgeted.

## Decision

### 1. Twelve panels convert; three stay bare

Of the 15, three are out of scope by the standing ADR-0337/0338 scope note and stay bare: the two
`.panel.status-stack` header bars (`_status_stack` is shared by several chapter headers — giving it
the contract here would be a cross-cutting change wearing a chapter-11 label) and the global Ask
panel that `_page` adds to every route. The remaining **12** convert.

### 2. The chip is the SINGLE-file chip — the mirror image of ADR-0338

Every model on this page — SSI, OAT, JCL and the legacy Monte-Carlo — resolves its schedule through
`_sra_selected`, and the top panel exists purely to say which file that is. So the chip is
`_prov_chip(scoped)` for that one version.

This is deliberately the opposite call from `/risks`, and for the same reason: the chip must
describe where the panel's figures actually came from. `/risks` computes `recommend(current, prior)`
so its chip names a pair; `/sra` computes everything against one file, so a series chip would render
`v1→v2` and claim versions no figure on the page was derived from.

### 3. ⤓ EXCEL is short by two — the first route where rank 3 costs something

Rank 3 is "never a dead **or lying** link". On the three previously converted routes every panel's
data rides the page's workbook, so ⤓-count trivially equalled tool-strip count. `/sra` is the first
route where it does not:

* **the "Which risk model should I use?" explainer** is guidance prose. No workbook carries a figure
  from it, so a ⤓ would open a file without its content.
* **the JCL panel on a duration-only file.** Its sheets ride `/export/xlsx/sra` *only once the file
  is cost-loaded* (ADR-0269) — the same gate the panel's own body honours by refusing to render a
  number. The ⤓ is gated on that same `loaded` flag.

Both keep the head, the ⛶ and the chip; they lose only the glyph that would lie. 12 strips, **10**
⤓. `tests/web/test_act3_panel_contract.py` asserts the **shortfall**, so a later round that hands
every strip a ⤓ "for consistency" fails.

A **third** case came out of the audit pass: when NO loaded version solves, `_sra_selected` returns
None and `/export/xlsx/sra` answers **400** — so on that page every ⤓ would be a dead button. The
export attribute, the ⤓ and the provenance chip therefore degrade together (`solvable`); the head
and the ⛶ stay, because enlarging a panel needs no data.

The shared hover title is also deliberately weaker than `/analysis`'s and `/risks`'s. Those say
"this panel's data is one of its sheets". The SRA workbook holds the **SSI** run's setup,
focus-finish results, OAT sensitivity and risk register — so for the three LEGACY Monte-Carlo chart
panels it carries the equivalent SSI-model sheet, not that panel's own series. Naming the workbook
is true for all ten panels; claiming per-panel sheet identity would not be.

### 4. The takes hold before any simulation has run

Four of these panels are empty chart hosts at render time: `sra.js` fetches `/api/sra` on demand
because running 1000× CPM during the page render would hang the page on a large schedule. A take on
one of those panels therefore cannot quote a P50, a mean finish or a sensitivity — the server has
not computed one, and inventing one is a Law-2 violation. Those four takes state what the panel will
draw and from what. The remaining eight quote figures the panel itself renders (the ranked-task
counts, the correlation entries, the global triangular, the registered-risk count), each worded to
read correctly at **zero**.

### 5. `/sra` gains the DoD's context line

`/sra` already had a takeaway h1 (`_what_could_go_wrong_header` rendered one inline) but **no**
`page-lede` — half of the DoD's "takeaway h1, context line" rule. The header now routes through
`_utility_takeaway`, which renders the same h1 byte-for-byte and adds the missing lede.

Measured, not assumed: the lede is the majority pattern (`/evm`, `/scurve`, `/margin`, `/groups`,
`/integrity` all carry one). `/briefing`, `/path` and `/compare` still render a bare h1 — recorded
as a carried gap, not fixed here, because each is another page's PR.

One limit stays: when nothing solves, `_what_could_go_wrong_header` returns `""` and the page has no
takeaway at all. That is pre-existing empty-state behaviour, not introduced here, and is recorded
rather than widened into this PR.

## Consequences

* Act III's census is **complete**: every route in it is inside
  `tests/web/test_act3_panel_contract.py` and `tests/web/test_act3_themes_chromium.py`.
* `_jcl_panel` and `_sra_explainers` build their own tool strip rather than taking the page's,
  because theirs is a different shape. That shape — ⛶ with no ⤓ — is new, and is rendered-tested in
  all four themes on its own.
* No `engine/` change; no calculation touched. The conversion decorates panels that were already
  `.panel`, and the panel count is unchanged at 15.

## The gate that was vacuous, and how it was found

`test_the_sra_takeaway_quotes_figures_the_page_renders_below_it` **could not fail** as first
written. It searched the KPI strip for "the label, then the number" using `.*?` under `re.DOTALL`,
which spans the entire six-card strip — so any card's digit satisfied any label. Rewriting the
headline to quote two figures the page never renders (`incomplete`, `neg`) left it green.

It was caught by running the revert (W7), not by reading the test. The fix parses the strip into
`label -> value` pairs and compares each figure against **its own** card.

This is the fourth consecutive PR in which the revert pass found an assertion that could not fail,
and the third of the three named shapes: *a rule whose assertion is looser than the rule*.

## Verification

14 reverts, every one confirmed to change the **rendered page** before the module was run, and every
module run **whole** (a `-k` filter can silently deselect the test being targeted):

| # | revert | gate that failed |
| --- | --- | --- |
| W1 | the page mints an extra panel | panel count |
| W2 | one panel loses its head strip | contract vocabulary (+ excel, + chip) |
| W3 | `panelkit.js` include dropped | panelkit-once |
| W4 | the explainer is given a ⤓ "for consistency" | ⤓ shortfall |
| W4b | same, in the browser | ⛶-only strip, four themes |
| W5a | the chip names the wrong loaded file | single-file chip |
| W5b | the chip becomes a series chip (`v1→v2`) | single-file chip |
| W6a | the DoD context line is dropped | takeaway loop |
| W7 | the headline quotes unrendered figures | **was vacuous — fixed, then failed** |
| W8 | a deferred panel's take quotes a fabricated P50 | no-simulation-figure |
| W9 | `panelkit.js` dropped (browser) | panelkit drives `/sra` |
| W10 | `/sra`'s head strips removed | panelkit drives `/sra`, ⛶-only strip |
| C1 | jarvis hides `.sf-tools` | all four theme rows **incl. `/sra`** + ⛶-only |
| C2 | apollo renders `.prov-chip` transparent | all four theme rows **incl. `/sra`** + ⛶-only |

W10 also recorded a real limit worth carrying: `test_the_head_strip_survives_all_four_themes` probes
only the **first** `.panel-head` on a page, so it cannot tell whether 1 or 12 panels carry one. The
markup census covers the count; C1/C2 prove the style probe discriminates on `/sra`.

## The adversarial audit pass (ADR-0240), and what it changed

A four-lens audit (vacuous gates · Law-2 fidelity · render correctness across session states ·
consistency with the converted routes) was run over the diff, and every finding was re-verified by
the lead against the actual code before anything was touched. Six were **confirmed and fixed**:

1. **The ⤓ was a dead link whenever no version solves** — `/export/xlsx/sra` answers 400 in that
   state. Fixed by degrading the export attribute, the ⤓ and the chip together.
2. **The JCL take asserted "No budgeted cost on this file" when the real reason was that nothing
   solved** — a false statement about a file that may well be cost-loaded. Now a third branch.
3. **The JCL "loaded" take read a target SETTING as a computed result.** `st.jcl_confidence` is the
   confidence the frontier is drawn at, not a JCL the panel computed. Reworded.
4. **"N versions loaded" counted every loaded file** (`len(st.schedules)`), which spans other
   Projects and operator-EXCLUDED versions, while the picker beside it is built from
   `ordered_versions()`. Now counts the selector's own population.
5. **The takeaway gate bound only the first two figures** — the headline appends ", with N risks
   registered", so a fabricated third figure passed. Now every figure in the h1 is bound.
6. **The ⤓ test asserted only the negative half of rank 3** — a ⤓ on a panel with no `data-export`
   is an inert button and would have passed. The glyph and the export are now paired per panel.

Three were **refuted** by the lead and deliberately not acted on: the "Risk inputs" take was said to
misreport overrides (it mirrors the panel's own semantics — `st.sra_overrides` IS the legacy
per-activity override set, app.py's own comment: "An explicit legacy per-activity override still
wins"); the correlation take's "drives the run" phrasing was said to overstate (it reuses the
panel's pre-existing wording verbatim — re-litigating the semantics is not a UI conversion's job);
and two constant-vs-constant assertions were flagged as tautological — which was **right**, so they
were removed rather than defended: in a file whose purpose is "no vacuous gates", an assert that no
app change can move reads as coverage and is worse than a comment.

Six further reverts prove the audit-driven fixes: **A1** the export attr stops degrading · **A2**
the ⤓ stops degrading · **A3** the JCL take reverts to the false claim · **A4** the version count
reverts to `len(st.schedules)` (which needed an EXCLUDED version to discriminate — the two counts
are identical on the goldens) · **A5** the headline appends an unbound figure · **A6** a fabricated
mean-finish **date** in a deferred take, which the guard's original pattern missed. Plus **J1/J2**
on the cost-loaded JCL branch: J2 is the lying-link regression itself — the panel keeps its ⤓ while
the export stops carrying the JCL sheets.
