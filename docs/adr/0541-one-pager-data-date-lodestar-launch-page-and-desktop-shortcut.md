# ADR-0541 — The One-Pager draws the operator's DATA DATE, LODESTAR opens on a launch page of its own and writes its Desktop shortcut on its first run; ADR-0540's loose ends closed

**Status:** Accepted · **Date:** 2026-09-30 · **Extends:** ADR-0540 (full-page fill, every link
fitted, the installers' icon), ADR-0539 (LODESTAR), ADR-0426 (the Boot Screen), ADR-0446 / 0465
(the One-Pager pages), ADR-0527 (the date window) · **Operator:** David Politte

## Context

The operator's kickoff (2026-09-30) carried four things beside ADR-0540's recorded follow-ups:

| Ask | Decision |
| --- | --- |
| **The size cap ruling** (item 4) — the kickoff's ruling field read `[KEEP AS SHIPPED / RAISE TO … / LOWER TO …]`, an unfilled template | **KEEP AS SHIPPED, assumed** — `LABEL_MAX` 14 pt, `LANE_NAME_MAX` 12 pt, `GLYPH_MAX` 40 unchanged; the 3 / 10 / 40 / 144-item renders in four views at 1440 and 390 px on both pages are delivered with this session (contact sheets in the session's deliverables) for the ruling proper. No constant moved, so no pin the constants touch was re-derived for it |
| **Pick the DD** (item 11) — "I want the user to be able to pick the DD (Data Date) and the change be reflected in the One-Pager" | `onepager_today` IS the operator's data date (one setting for both pages; `None` the computer's date); a **Data date** control on both pages, in Polaris² and LODESTAR; the red line, its caption, the legend and the page's chip follow it and say **DATA DATE**, never "today"; "Prepared" / "generated" stay the computer's date and name the data date beside it when the two differ |
| **A launch page** (item 12) — "very similar to that of Polaris² but different enough so that the user can easily identify the tool" | LODESTAR's `/launch`: Polaris²'s boot screen — the SAME `launch.js` / `launch.css` / hum — made LODESTAR's by what the page supplies (its own heroes, stage words, home route), its ✦ mark and name, the lodestar's gold accent in every view, its own icon, real facts in the tiles; the program opens on it |
| **A Desktop shortcut on the first run** (item 13) — "if possible" | `lodestar/shortcut.py`: written once per archive (a marker in LODESTAR's per-user data folder), best-effort, with LODESTAR's own icon; `--shortcut` / `--no-shortcut`; Windows `.lnk` (PowerShell COM), macOS `.app`, Linux `.desktop` — Linux run for real, the other two by reading (UNVERIFIED) |
| ADR-0540 follow-up (1): the data-date caption's box 0.66 pt into the last band | `TODAY_CAPTION_DY` 5.5 (was 4.5), render-verified in Chromium on both pages: the box clears the band by 0.34 pt, the ink by 1.09; the ink stays 0.5 pt above the legend rule (the box crosses that rule by 0.36) |
| ADR-0540 follow-up (2): `_conflicts` checked heads against vertical legs only ("2 of 600 gutter slides") | heads are judged against EVERY leg (`_head_legs`) — the premise fell, below |
| ADR-0540 follow-up (3): a list that fills the slide to its last row has no footnote in the .pptx | **Decided: the legend's spare row carries it** — when the legend uses one of its two rows, ONE line (the count and the entries that fit) at the second row's baseline, painted by the page and the .pptx alike (`spare_row_footnote`); when the legend needs both rows the corner stands and the note says so |

Recorded, still out of scope: UIP-3, ROUTES-5, the empty-workbook "1 row(s) skipped", Excel percent
formats, the pre-commit hook's blindness to a shebang-prefixed ZIP; LODESTAR's release channel.
Answers already given by the operator (2026-09-29) were not asked again.

## The plan was attacked before the first edit (QC-3) — what fell

| Premise | Check (pristine tree `40cca07c`) | Verdict |
| --- | --- | --- |
| The caption's text box sits 0.66 pt into the last lane band | `probes/p_caption_box.py`: Chromium `getBBox` of `.op-today` vs the last band's `y1`, both pages, 3 and 40 items | **HELD**: 0.661 pt into the band on all four renders; the box's bottom 0.64 pt above the legend rule. After +1 pt: −0.339 (clear) and +0.36 (the box crosses the rule; the ink does not) |
| "2 of 600 review slides carry a later head's base on an earlier GUTTER leg" | `probes/p_head_v2.py`: a triangle-exact leg-to-head distance (no router code) over 600 seeds each of the review generator (40–140 items, 10–60 links), the same at DENSE (30–110, 8–40), and this module's generator at DENSE | **REFUTED as stated, and worse than stated**: 0 gutter cases in 1,800 slides (gutter slides are rare: 12 of 678 at the first count); but a CLEAN-judged head on an earlier PLAIN horizontal leg on 66 / 34 / 22 of 100 seeds — the leg runs through the head's base (distance 0 on most) — the same mis-join the vertical check exists for. A first, box-based probe over-counted (300 of 484 seeds): heads at adjacent attachment points sit within a box's reach of a neighbour's leg without the leg entering the triangle |
| The fix (check every leg) is affordable | `probes/p_head_v3.py`: the fix monkeypatched in-process over 100 seeds of each population, the tree untouched | **HELD**: the class vanishes (66 → 0, 34 → 0, 22 → 0); links drawn dashed 124 → 174 of 3,523 (+1.4 %), 52 → 62 of 2,421, 37 → 37 of 2,489; gutter slides 3 → 7, 1 → 3, 0 → 0; time 261 → 235 s, 83 → 102 s, 91 → 100 s |
| `onepager_today` is read by everything through one seam | grep: `app.py` (`_onepager_today`) and `server.py` (`_today`) are the only clock reads on the One-Pager path | HELD — it became the data date; the routes derive `(data date, prepared)` in one helper each (`_onepager_dates`, `_Handler._dates`) |
| "Prepared" may stay the data date | the subtitle and the deck's "generated" line read `today` | **REFUTED**: a slide prepared on 9/30 with a data date of 8/31 would say "Prepared 2026-08-31" — false. `subtitle_for` / `compare_subtitle` / both `*_pptx` actions take `prepared`; the subtitle names both dates when they differ; a mutant route that passes the data date as prepared is caught by name |
| The pristine-digest pin stays green | `test_onepager_window.py` | REFUTED as expected — the caption text and its baseline moved on purpose; re-pinned once, both reasons in the comment |
| ADR-0540's seed pins survive the router change | the fill-and-fit module after the fix | Two fell: review seed 105 (F3's "forced, then clean") now carries a flagged link and no review seed in 100–699 shows the shape — the mechanism is pinned directly (`disclose_fit` / `footnote_lines` with nothing to say); the gutter-ledger seeds 12 and 13 no longer reach the gutter — 103 and 110 do (searched) |
| `launch.js` can be shared without forking | `tests/web/test_boot_screen.py` pins its text | HELD after one re-derivation: the skip check must precede a literal `var boot = null;` — kept as a literal, the tables read after it; Polaris²'s tables are the defaults and its boot tests pass unchanged (29 of 29) |
| LODESTAR's static allowlist and member list can grow | `test_lodestar_pyz.py` pins 34 members by an independent literal | HELD by design: re-pinned to 42, on purpose, with the eight named |
| A subprocess in LODESTAR passes the windowless guard | `tests/test_windowless_subprocess.py` (AST) | HELD once `stdin=DEVNULL` and `creationflags=CREATE_NO_WINDOW` were on both calls (PowerShell, `gio`) |
| The pyz e2e tests can run on a developer's real machine without planting a shortcut | reading `_launch` | REFUTED — they would have: every archive launch in the tests now passes `--no-shortcut`, and the shortcut tests run under a HOME of their own |

## The build was attacked after it was written (QC-1) — what fell, and what replaced it

| Finding | Measured | Replaced by |
| --- | --- | --- |
| The deck's legend mark for the data date was asserted through `deck_shapes` | it is a connector, never listed there (nor was "Today" before) | the slide XML is read for the connector names (`Data date`, `Legend: data date`) |
| The launch page's fixture froze the data date to fix the clock | the tiles said "set by you" | the server's own clock seam (`LodestarServer(port, state, today)`) fixes the clock; the state holds no data date |
| The drawer prose check split on `{locality}` | the frame formats `{where}` first | the prose before the first placeholder is the shared copy checked |
| A comment in `launch.js` named LODESTAR | the "no identity in the script" pin read the comment | the pin names the identity WORDS (`STUDIO OPEN`, `One-Pager Studio`, `STAR FIX`) |
| The `entries` name in `build_layout` was reused for the footnote entries | mypy: the legend's tuples vs the footnote's strings | `foot_entries` |
| `winreg` on a non-Windows checker | mypy: no such attributes | the function returns first on any other platform, so the checker never enters the Windows branch |
| **The densest sweep slide lost its "no leg crosses a glyph" invariant** (`test_onepager_links`, row pitch 5.76) | with every leg checked, the base attempt left ONE link no route clears; the reorder step — the footnote band reserved — re-packed the slide 0.15 pt tighter, past the point where adjacent labels overlap, and `_better` (collisions only) accepted six clean legs through labels for one drawn link; the reserved last resort did the same | `RouteReport.touches` (clean links with a horizontal leg on a glyph, `_touches`); `_better` refuses a step that adds one, and a reserved last resort that adds one runs without the reserve (the F2 path — the link is drawn dashed and named, the spare legend row carries the count when it has one); a mutant that blinds the count fails the sweep pin by name |

**UNVERIFIED, stated:** the Windows `.lnk` (PowerShell `WScript.Shell`, `py -3`), the macOS `.app`
bundle and Gatekeeper's view of a bundle written by the user's own Python — no such host here;
the writers are held to the formats' own rules and Linux is run for real through the committed
archive. PowerPoint itself (LibreOffice Impress is the renderer here). Firefox / WebKit.

## Decision

1. **The data date** (`web/onepager_actions.set_today`, `POST /onepager/today` and
   `/onepager-compare/today` in both servers, `today_form` on both pages): `onepager_today` is the
   operator's data date, one setting for both One-Pager pages, `None` the computer's date; a date the
   One-Pager itself reads is taken, anything else refused by name and the setting kept; "clear"
   returns to the computer's date. The slide's red line, caption (`DATA DATE m/d/yy`), legend
   (`Data date (m/d/yy)`), `plot_window`'s notes and the page's chip follow it; the deck's connector
   names say `Data date`. `subtitle_for` / `compare_subtitle` take `prepared` and say
   `Prepared <clock> · data date <dd>` when they differ; the deck's "generated" line is the clock.
   The layout caches key on both dates.
2. **The caption** sits `TODAY_CAPTION_DY` = 5.5 pt below the last band on both pages; a Chromium
   pin measures the box against the band and the baseline against the legend rule, with a mutant
   at 4.5.
3. **The router** judges a new head against every leg of every earlier link (`_head_legs`), so a
   later head never sits on an earlier horizontal leg, and the escalation never buys a drawn link
   with a clean leg laid on a glyph (`RouteReport.touches`, `_better`, the last resort's reserve); a property over the module's 60 dense
   slides with an independent triangle-exact oracle, review seed 1 as the named case, and the
   vertical-only rule as the mutant that fails it by name.
4. **The spare-row footnote** (`spare_row_footnote`, `disclose_fit(spare_row=)`): a list that fills
   the slide to its last row with links drawn dashed carries ONE footnote line in the legend's spare
   row when the legend uses one row — on the page and in the .pptx — and the note says so; with a
   two-row legend the corner stands, the note saying where the links are named.
5. **LODESTAR's launch page** (`web/lodestar_launch.py`, `static/lodestar_launch.css`, `/launch`;
   `launch.js` reads `heroes` / `stages` / `home` from the page's boot JSON with Polaris²'s tables as
   the defaults; `__main__` opens `/launch`; `/favicon.ico` and the frame's icon are
   `lodestar.ico`). §7a's four rules hold.
6. **LODESTAR's own icon** (`desktop_icon.lodestar_ico_bytes`): the ✦ lodestar in gold on a dark
   rounded square, rasterised at 256 / 128 / 64 / 32 / 16 with 16× supersampling, packed as a
   Windows icon of PNG frames, committed as `web/static/lodestar.ico`; `lodestar-ico` / `-png` /
   `-icns` on the command line; a test decodes the committed file and holds its pixels to a fresh
   render (deflate is not byte-pinned; pixels are).
7. **The first-run Desktop shortcut** (`lodestar/shortcut.py`): `ensure(force, skip)` → an
   `Outcome` the console prints; the marker `shortcut-made.txt` and the icon files in LODESTAR's
   per-user data folder; a deleted shortcut stays deleted; `--shortcut` / `--no-shortcut`.
8. **LODESTAR 1.0.2** (42 members); the README says what the launch page and the shortcut do.

## Consequences

* `Layout` / `CompareLayout` carry no new field: the footnote's `footnote_y` may now lie inside the
  legend band (the spare row); both painters read it as before.
* `OnePagerSession.onepager_today` changed meaning: tests that froze the clock through it now
  freeze the data date, and "Prepared" in those pages is the real clock — the two pins that read
  a frozen "generated" / "Prepared" date were re-derived to the shape of a date.
* The escalation tallies ADR-0540 recorded on the module's DENSE generator move with the router
  change (more collisions are found, so more slides escalate); the counts in the ADR-0540 text
  are that ADR's measurement, not this tree's.
* The wheel and the nine installers are rebuilt at v1.0.297 from a clean worktree of the source
  commit; `lodestar/LODESTAR.pyz` at 814,888 bytes, 42 members.
* **Open for the operator:** the size cap ruling proper (the renders are delivered; the shipped
  provisional caps stand until ruled on); an icon for LODESTAR's launchers on the machine that
  cannot write a shortcut (out of scope).
