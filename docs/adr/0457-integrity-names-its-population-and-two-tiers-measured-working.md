# ADR-0457 — /integrity names the population it compared (Project + reduce filter); the "two tiers" report measured working and pinned

- **Status:** Accepted — 2026-09-03 (operator evening batch: I-01 · T-01)
- **Version:** 1.0.234
- **Extends:** ADR-0258 (active-Project scoping), ADR-0450 (field roles — an unmapped role name matches nothing), ADR-0370/0371 (pair scope), ADR-0440/0452/0453 (the Timescale dialog and its ladder)
- **Shipped:** `web/app.py` (`/integrity`: the Project-population note, the raw-size counts under a reduce filter), `web/integrity.py` (`_integrity_population_note`, `_scope_phrase`, `_integrity_header(scope=…)`, `_integrity_body(raw_sizes=…)`), `tests/web/test_integrity_population_disclosure.py` (6), `tests/web/test_timescale_dialog_browser.py` (+2 T-01 pins)

## Context — measured before believed

**I-01** — "The schedule integrity page is not picking up the same findings that it once did and it's not
working correctly now." The instrument was a DIFFERENTIAL: the SAME inputs (the golden trio
Hard_File → Hard_File_updated → Project5, the Project2 → Project5 pair, the five-version TP4 corpus —
byte-identical across the three trees, checked by `git diff --stat`) through `/integrity?a=&b=` for
every pair AND through `detect_manipulation` directly, on `git worktree` checkouts at v1.0.221
(`dfa09ac`) and v1.0.229 (`cc21cb5`) and on this tree, diffing detector rows BY NAME.

| corpus · pair | v1.0.221 | v1.0.229 | v1.0.233 | rows by name |
|---|---|---|---|---|
| golden trio 0→1 / 0→2 / 1→2 | 4 / 7 / 9 | 4 / 7 / 9 | 4 / 7 / 9 | identical |
| Project2 → Project5 | 5 | 5 | 5 | identical |
| TP4, all ten pairs | 0·0·1·1·0·2·2·2·2·0 | same | same | identical |

`engine/manipulation.py`, `change_effects.py`, `cpm.py`, the importers and the model are byte-identical
between v1.0.221 and this tree; `state.py` changed only for field roles and the One-Pager. So every
code-side hypothesis the ledger named (ADR-0450 narrowing the detector population by itself, ADR-0421/0422
raw-vs-scoped pairing, ADR-0371 truncation, ADR-0424 all-N pairing) is **REFUTED for a clean session**.
The page itself renders with zero page errors, the A/B picker, the drill, the logic diagram and the
xlsx export all work (chromium, golden trio).

What DOES make the page "not pick up" findings is **session state**, measured on this tree:

| session | /integrity said |
|---|---|
| clean, 3 files one folder | 9 findings, Hard_File_updated → Project5 |
| two folders (2 + 1), the 1-file folder active (ADR-0258 heals to the last-loaded file) | **"Load at least two versions of the schedule"** — while two versions sit loaded in the other Project |
| loose files: two share a document Title, the third differs | same message — three loose files became TWO Projects |
| reduce filter `WBS = 1` | 1 finding (a real narrowing, no counts stated) |
| reduce filter on the role name `Cost Account` with NO mapping (ADR-0450: matches nothing) | **"No manipulation-pattern findings between Hard_File_updated.mpp.xml and Project5.mpp.xml"** — an affirmative negative over an EMPTY population |

The filter banner is on every page and the Project strip names the active Project, so neither state is
hidden — but the page's own sentences were wrong for them: "load two versions" when two are loaded, and
"no findings" when nothing was compared. On a testimony surface a wrong sentence is the defect.

**T-01** — "when I tell it I want two tiers it doesn't work correctly." Driven in chromium on this tree:
the dialog's Show menu set to *Two tiers (Middle, Bottom)* and committed with OK on /analysis (five TP4
versions and TP5), /path, /driving-path, /evolution and /sra, then three zoom-in steps, six zoom-out
steps, Fit / View entire project, and a reload. Every scale rendered **exactly two** `.g-tier` rows,
each `position: absolute` at `y` 0/18 (18/36 under a caption row), the scale 36 px tall (`g-scale-rows-2`),
`config().show === 2` before and after the reload, localStorage `{"show":2,…}`, zero page errors; one
and three tiers again through the same menu. The three hypotheses — the promotion ladder re-adding a
row, a string `show` rejected by the ADR-0440 sanitizer, Fit re-applying its own set — are **REFUTED**
on this tree. The static assets are served `Cache-Control: no-cache` with an ETag, so a stale
`timescale.js` after an upgrade is refuted too. **NOT REPRODUCED**; the operator is asked for the page,
the zoom and a screenshot of the dialog beside the header.

## Decisions

1. **/integrity names its Project population whenever more than one Project is loaded**
   (`_integrity_population_note`): *"Project X holds k of the N loaded files — this page compares
   versions inside ONE Project. Other Projects loaded: A (2 versions) · B (1 version). Switch: [select]"*,
   with the switch form's `next_url` set to `/integrity` (the app strips Referer). The empty state under a
   one-version active Project now says that Project has one solvable version and points at the switch
   and at Portfolio's combine — never "load at least two versions" while two are loaded.
2. **Under a reduce filter the page states the in-scope counts** ("a of A activities in P and b of B in C
   are in scope of the active filter") in the takeaway, and **an empty side is "nothing to compare",
   never "no findings"**: the takeaway, the findings panel's take-line and its empty paragraph all say the
   filter left nothing; no detector ran. Highlight mode and no filter carry no counts (nothing is scoped).
3. **T-01 is pinned, not fixed**: two M2 drivers measure Show = 2 on /path (zoom slider, Fit, reload,
   then 1 and 3) and on /analysis (three zoom-in, six zoom-out, Fit) by computed position and rendered
   `y` — never by config or inline styles.

## Verification (QC-1)

- Red-first: the four disclosure tests observed **RED on a pristine worktree at `0f098cce`** (the
  empty state carried no Project name and no switch; the empty-filter page read "No manipulation-pattern
  findings"); the two guards (single Project; highlight/no filter) green before and after.
- Green: 40 across the six /integrity TestClient modules; the two T-01 pins green on the tree.
- Mutation (T-01 pins, scratch copy): `visibleTiers` made to return three tiers for `show === 2` →
  **both pins red by name** (2/2), the rest of M2 untouched.

## Deliberately NOT done

- No engine change — the detectors were proven unchanged; Law 2 is untouched.
- The active-Project default (heal to the most recently loaded file) stays as ADR-0258 decided; this ADR
  discloses it on the page rather than re-deciding it.
- The Timescale dialog is untouched: nothing measured wrong. If the operator's screenshot shows a third
  row on ≥ v1.0.234 it is a NEW defect with a named page and zoom.

## Operator asks carried forward

For I-01: which finding disappeared, and on which two files — and whether the two files were dropped
as separate folders or carry different document Titles (the page now says so itself). For T-01: which
page, which zoom, and a screenshot of the dialog beside the header.
