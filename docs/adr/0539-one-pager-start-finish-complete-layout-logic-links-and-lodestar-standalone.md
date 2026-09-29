# ADR-0539 — The One-Pager reads C start · D finish · E complete, draws the operator's own logic links, and ships on its own as LODESTAR

**Status:** Accepted · **Date:** 2026-09-29 · **Extends:** ADR-0446 (One-Pager), ADR-0465 (Compare),
ADR-0524 / ADR-0526 (status column), ADR-0527 (date window), ADR-0264 / ADR-0268 (SEC-2/SEC-3) ·
**Operator:** David Politte

## Context

The operator asked (2026-09-29) for three changes to the One-Pager Timeline and One-Pager Compare:

1. "The MS Excel format … will have the start date in column C and the Finish Date in Column D and
   Complete in Column E from now on."
2. "Select two tasks or milestones at a time and then click a button that creates … an arrow that
   shows the logic between those two tasks … multiple pairs … only that logic … then export the
   One-Pager to MS PowerPoint."
3. "Keep [both pages] as a part of Polaris2 but … make just these two pages a separate program of
   their own that I can share with others … no Ask the AI … call it something cool and cite on it
   … created by David Politte … david.j.politte@nasa.gov."

Four rulings were asked and given before any code (2026-09-29):

| Question | Ruling |
| --- | --- |
| How the standalone program is packaged | **A single Python file** (`.pyz`) running the SAME modules — std-lib only, no pip, no internet; recipients need Python 3.10+ |
| Workbooks in the old layout (C date/range, D status) | **Auto-detect both**, the new layout the standard; the page says which layout it read |
| Link types | **Finish-to-Start by default, plus SS / FF / SF** |
| The program's name | **LODESTAR** ("One-Pager Studio") — Polaris is the lodestar |

## The plan was attacked before the first edit (QC-3) — what fell

A five-lens red team (intake, routing, security, packaging, UX; `scratchpad/redteam/*` probes, the
repo never mutated) tried to refute PLAN v1. What fell, and what replaced it:

| Plan v1 assumption | Verdict | Replaced by |
| --- | --- | --- |
| Header decides on a start in C, a finish in D (substring) or anything in E | **Refuted (blocker)**: a legacy "Comments" column in E, a "Start - Finish" C header, and D headers "Pend**ing**" / "Tr**end**" / "Over**due**" each flipped a legacy sheet and skipped its rows | ONLY column D's header decides, whole words; C and E headers never decide alone |
| Content: any date in D or anything in E means the new layout | **Refuted (blocker)**: one completion date typed in an old status column flipped the sheet (ADR-0526's own UNREAD fixture); owner names in E did too; 631/2000 fuzzed legacy sheets drew wrongly | Column D classified cell by cell (date · status word · placeholder · other); unanimous → that layout; mixed → the majority, with a note; a tie or nothing readable → the older reading plus a NAMED problem carrying the remedy; an Auto / C-D-E / older choice on both upload forms |
| "When no signal fires both readings agree" | **Refuted**: an unreadable D ("Sept 30, 2027", an MS Project paste "Mon 9/1/26") read old-style drew a milestone on the START | The claim deleted; the date reader learns MS Project's pasted forms — a weekday is CHECKED against the date (a contradiction is unreadable), a time of day is dropped, "Sept" and "Nov." read |
| Reuse `_is_header` | **Refuted**: a finish-only first row ("Milestones · Program Start · · 9/1/2026") was eaten as a header | A header has no date in C **or** D |
| Occurrence-number item keys survive a re-upload | **Refuted (blocker)**: a rolling monthly list silently re-attached a link to a different month's review | Unique swimlane+name → keyed by name alone (a link survives a slip); a repeated name → keyed with its exact dates (ADR-0524's identity rule); anything else is unresolved and NAMED |
| Horizontal legs on row boundaries (`cy ± row_h/2`) clear every glyph | **Refuted (blocker on Compare)**: the move arrow above every moved bar, and NEW/REMOVED tags, cross the boundary below row_h 12.5 | An obstacle model (every bar, diamond, ghost, move arrow, label, tag and check) and a channel chosen by MEASURING the free band over each leg's x-range; parallel legs stacked on tracks; a crowding note when the rows are too dense |
| Links painted beneath the items | **Refuted**: a middle bar hid a vertical leg and read as two links that do not exist | Links painted ABOVE the items over a halo in the canvas colour, below the red data-date line |
| PPTX line-end arrowheads | **Refuted**: LibreOffice drew `tailEnd` heads 5.95 pt — 3× the page's | The layout owns the head polygon; the .pptx paints it as a closed shape, the shaft as an open freeform, the whole link as ONE named group |
| The FastAPI routes' logic can be copied into a std-lib server | Risk of drift | `web/onepager_actions.py`: every route's behaviour, framework-free, called by BOTH servers |
| A std-lib server can reuse the policy as-is | **Refuted (blocker)**: on HTTP/1.1 a refused request's unread body was parsed as the next request, past both gates | HTTP/1.0, every refusal closes, chunked bodies refused, Content-Length checked BEFORE reading, a fixed static allowlist (a joined path served `../` from a filesystem package), silenced logging, a generic 500 |
| The upload cap bounds memory | **Refuted**: `rfile.read(n)` allocates `n` up front; a 773-byte workbook with a `ZZZZZZZ` column asked the SHARED reader for a billions-wide row (a pre-existing Polaris² DoS) | LODESTAR caps uploads at 20 MB before reading; `xlsx_read` refuses references past XFD / row 1,048,576 and holds a padded-cell budget; the One-Pager reads columns A–E only |
| Exports can stay as they are | **Refuted**: a slide title "Ωmega" or "日程" 500'd both PowerPoint exports (a non-Latin-1 header) | An ASCII-safe `filename` plus RFC 5987 `filename*` |
| The selects are a plain form | **Refuted**: persist.js restored the pair just added (a second Add = a duplicate) | `data-sf-nopersist`; the result shows INSIDE the links block, where the browser lands |

Assumptions that **held**, measured: the curated modules import under `python -I -S` on 3.10–3.13
with no third-party module; `importlib.resources` reads package data from inside a zipapp; the
std-lib email parser round-trips binary workbooks byte-exact (300 fuzzed uploads, 91 real intake
workbooks); a committed `.pyz` passes the pre-commit hook and CI's cui-guard; a stored,
fixed-header zip builds byte-identically on every interpreter here; every existing One-Pager row
set parses identically (102 captured calls, 49 row sets). **UNVERIFIED, stated:** PowerPoint itself
(no PowerPoint here — LibreOffice Impress renders the freeform links and heads correctly);
double-clicking a `.pyz` on Windows (no Windows host — `LODESTAR.bat` is the documented path);
Firefox/WebKit rendering of the pick rings (Chromium only).

## The build was attacked again after it was written (QC-1) — what fell, and what replaced it

Independent test writers (intake, links, pages, LODESTAR) and a four-lens review (intake, links,
LODESTAR, UI + docs — every finding sent to a refuting skeptic) attacked the built tree; the lead
re-reproduced every finding below on the built tree (RED) before fixing it in a sandbox copy
(GREEN), and each is now pinned in `tests/reports/test_onepager_review_findings.py` (18 of its 20
tests fail on the built tree; the other two are guards on behaviour that never broke).

| Finding | Measured on the built tree | Replaced by |
| --- | --- | --- |
| A typed TRUE in column E (and a checkbox) read as not complete | Excel stores it as a BOOLEAN cell, `t="b"` `<v>1</v>`; the reader returned `"1"`, named as an unread word on every row — the plan's "reads TRUE" held only for text | `read_xlsx_numbered(..., booleans_as_text=True)` for the One-Pager only: the word Excel SHOWS; the shared reader's default (the SRA imports) unchanged |
| A header-less sheet's dateless first row whose D or E says "Complete" / "Done" vanished unnamed | a regression: the pristine parser named it | a D / E header word that is ALSO a status value is no evidence of a header |
| INTAKE-1: one date among words the reader cannot read flipped an older sheet | 295 of 2,000 fuzzed older sheets drew differently, 1,386 rows lost | in the current layout D must be a FINISH date, so a status word, anything else, AND a date that cannot be the row's finish (before C, or not the end of C's range) all count against it: 0 of 2,000 differ; 995 of 1,000 fuzzed current sheets read current (was 911), 0 rows lost |
| INTAKE-2: "the layout could not be decided" was filed as a skipped row | the page said "1 row(s) skipped" when none was | a note about the sheet (`layout_note`), never a problem |
| INTAKE-3: D's header overruled a column whose content said the opposite | "Complete By" over dates collapsed every activity to a milestone; "Past Due" over Yes / No skipped every row | a date word ("by", "date", "target", "planned", …) makes a header say BOTH, so the content decides; a header is overruled only by POSITIVE unanimous content (≥ 2 dates, or ≥ 2 status words, and nothing else) — never by words the reader cannot read — and the page says so |
| INTAKE-5: "1/0000" in column D answered HTTP 500 | the month / year branch built a date in year 0 | not a date (and the same crash in column C, pre-existing, is gone with it) |
| INTAKE-6: column E dropped unsaid when D is empty and E holds words the reader does not know | read as the older layout, E ignored | nothing in D + anything in E → the current layout (E's words are then named) |
| INTAKE-7: a note typed alone in D above the header, or a status column headed by its status date, turned the header row into a skipped row | — | the header is looked for on the first row with content in A to C; a date in D keeps a header a header when C itself is a column title |
| Parallel legs of two links 0.4 pt apart read as one line | 7 undisclosed pairs at 36–64 items; the router compared track OFFSETS, but each leg's centre is measured over its own x-range | tracks judged by the height they DRAW at; a link falls back to the next free gap between its items before the slide is "crowded" (the note now fires at 60+ Compare / 144+ Timeline items, not on a 6-item Compare) |
| LINKS-1: a chain through a milestone lost the head INTO the milestone | the link out started exactly where the head in sat, and its halo erased it: 315 of 600 fuzzed two-link chains lost a head or a tag | every side of every end of an item has ATTACHMENT POINTS `_SLOT` apart (a milestone's start and finish are one point); heads and tags are reserved in their channel: 0 of 600 |
| LINKS-2: another link's halo erased half an SS / FF / SF tag | 45 % of the tag's ink on the review's pair | the tag takes the first clear spot (beside the head, else beside the predecessor's end) and is reserved; a later leg crosses it only when its channel has no other room — and then the slide says it is crowded |
| LINKS-4: a link was lost, with a false reason, when its item's name started or stopped repeating | the key changes FORM (name alone ↔ name and dates); the page said "is no longer in the list" of an item still on the slide | each link keeps both ends' identity (swimlane, name, start, finish) and is re-bound on upload to the ONE item with exactly that identity — never to another month's copy (a name-only matcher, tried as a mutant, re-attaches it); an end still unresolved is named truly |
| LINKS-5 / LINKS-6 | a hidden item in a refused loop printed "?"; the Excel table said "see the note below" with no note when the window left no slide | the label the link keeps; the one note |
| A 120-character name with no spaces in the link message scrolled the page sideways | 1,611 px in a 1,440 px viewport | `overflow-wrap:anywhere` on the links block's notices and list |
| LODESTAR LS-03 / LS-04: one client stalling its body froze every page; a body of many empty parts cost ~11 s of CPU per MB | the body was read and parsed under the state lock | the body is read and parsed BEFORE the lock, against a whole-body deadline; a multipart body is pre-scanned (at most 8 parts, 8 KB of headers each) before the email parser sees it |
| LS-05: Quit could lose its own "has stopped" page (8 of 30 runs), and that page always rendered unstyled | shutdown began before the reply was written; the page asked the stopped server for its stylesheets | the server stops only after the page is written; the page is self-contained, in the SYSTEM colours (no hex, no request) |
| LS-06: the standard library's own error pages (an unknown method, a long URI, too many headers) carried no CSP / nosniff / frame-deny | they bypass the one send path | every response's headers are completed before they end; PUT / DELETE / PATCH / OPTIONS are LODESTAR's own 405 |
| LS-07: LODESTAR's Word exports were titled "POLARIS² — One-Pager" | the table sets' titles | LODESTAR serves no Word export (no page offered one); `docx.py` left the archive (34 members) |
| LS-08: a CRLF checkout (Git for Windows' autocrlf) built a different archive | members packed as read | text members (.py / .js / .css) read as LF — a CRLF copy of the tree builds the IDENTICAL file |
| LS-09: without Sec-Fetch-Site an Origin from ANY loopback port could flip the marking | Polaris²'s gate, reused | `_same_origin`: LODESTAR's origin is exact, as its Host gate is |
| LS-10 – LS-13 | `--help` served and opened a browser; a 64 KB cap said "1 MB"; a folder named "… site-packages …" could not start it; the banner crashed an ASCII console | argparse (`--no-browser`, `--port`, `--version`; an unknown flag exits 2); the right unit; the archive is always kept on the path and ONLY the standard library's own directories join it (an editable install's `.pth` directory no longer does); the banner falls back to ASCII |
| LS-01: the lockstep test the ADR named did not exist yet | — | `tests/lodestar/test_lodestar_pyz.py` (byte-identical to a fresh build, members exactly the allowlist). The pre-commit hook still cannot see into a shebang-prefixed ZIP — recorded as a follow-up; the lockstep test is the guard |

## Decision

### 1. The intake (`reports/onepager.py`)

`read_sheet` → `SheetRead` (items, problems, notes, completion notes, layout, status column,
layout note); `parse_sheet` keeps its four-part contract. `detect_layout` as the table above;
`_row_span` the new layout's row rules (C start, D finish; either alone is the item's one date; both
give C's first day to D's last; a range in one cell agrees only when its end matches the other cell;
a status word in C or D is refused naming column E; a lone month is named). `OnePagerDoc` gains
`layout`, `status_column` (E / D / "" none) and `layout_note`; every sentence about completion names
the column the sheet used (`status_label`, `complete_legend`). `read_completion` reads TRUE (FALSE
already read). The template ships Swimlane · Task · Start · Finish · Complete.

### 2. Logic links (`reports/onepager_links.py`)

`Link(pred, succ, kind)` by item KEY (`item_keys`, above) with the labels at creation kept for
naming; `check_link` refuses the same item twice, an item not on the slide, a duplicate, a LOOP
(naming the chain) and more than 200. `route_links` over a `Grid` of row centres and glyph `Box`es:
FS leaves the predecessor's finish and enters the successor's start (SS / FF / SF likewise, a
milestone's centre for either end); a link whose end DATE is off the date window, whose item is not
on the slide, or whose item runs off an overflowing slide is not drawn and is NAMED. Both layouts
carry `links`, `link_notes` and `status_label`; the legend gains "Logic link" only when one is
drawn. The Excel exports gain a "Logic links" table. The page's form sits above the slide (From /
To / Type / Add — the no-JS and keyboard path), the list with a Remove per link below it;
`static/onepager_links.js` paints the links and lets a click pick From then To (rings + FROM / TO
tags). Links live in the session, survive a re-uploaded list, are cleared with the list and by a
session wipe.

### 3. LODESTAR (`lodestar/LODESTAR.pyz`)

Leaves cut so the One-Pager imports no engine: `reports/tableset.py` (Cell / Table / TableSet),
`web/htmlkit.py` (`_e`, `_utility_takeaway`, `_panel_head`, `_shell_tools`, the marking sentences
and the compliance drawer's ONE copy of the CUI / ITAR / EAR prose), `web/security.py` (CSP,
headers, Host allowlist, CSRF gate), `web/onepager_common.py` (the `OnePagerSession` protocol and the
Compare explainer) — each re-exported with the `X as X` idiom and registered in the split contract.
`web/onepager_actions.py` holds every route's behaviour; `app.py`'s One-Pager routes are thin
adapters over it (behaviour unchanged, the strict-xfail A0923-IMP-005 still xfail — only
`XlsxError` is caught). `web/lodestar_shell.py` is the frame (brand, two tabs, the four views, the
marking switch — CUI by default — Quit, and **"Created by David Politte · questions or issues:
david.j.politte@nasa.gov"** in the header and footer of every page; never on the slide or in the
deck's author field). `lodestar/server.py` is the std-lib server with the hardening above;
`tools/lodestar/build_lodestar.py` packs the allowlisted files VERBATIM (stored, sorted, fixed
headers, behind a shebang) — the only two renamed members are themselves files of `src/`
(`_pyz_main.py` → the archive's `__main__.py`, which refuses Python < 3.10, takes site-packages off
the path and refuses to start if anything non-std-lib was imported; `_pyz_web_init.py` → the web
package's `__init__`). Exports from LODESTAR say LODESTAR (a `product` parameter), never POLARIS².
`lodestar/` also holds `LODESTAR.bat` (CRLF), `LODESTAR.command`, `lodestar.sh` and a plain-English
README. `tests/lodestar/` holds the file byte-identical to a fresh build.

### What is N/A in the LODESTAR frame (DESIGN-SYSTEM §7c)

The chapter kicker, the Continue segue and the nav rail / story spine — LODESTAR has two pages and
no story. Its tabs are `cd-chip` links with `aria-current=page`.

## Consequences

* A NEW recurring cost: editing any file LODESTAR carries turns `tests/lodestar/test_lodestar_pyz.py`
  red until `python tools/lodestar/build_lodestar.py` is run (named in CLAUDE.md, the full-gate and
  session-close skills, and the test's own failure message).
* The shipped static asset count is 72 (+`onepager_links.js`, `lodestar.css`); LODESTAR.pyz carries 34 members.
* Sharing LODESTAR outside the operator's organization may fall under that organization's software
  release rules (for NASA, NPR 2210.1) — the operator's decision, flagged, not the build's.
* Follow-up, out of scope and recorded: a shebang-prefixed ZIP evades the pre-commit container
  detector even under a `.zip` name (its check keys on the first four bytes); the `.pyz` lockstep
  test is what guards this container instead.
