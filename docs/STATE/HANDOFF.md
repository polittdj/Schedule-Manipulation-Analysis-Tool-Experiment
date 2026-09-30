# Handoff — 2026-09-30 (One-Pager: the operator picks the DATA DATE; LODESTAR opens on a launch page of its own and writes its Desktop shortcut on its first run; ADR-0540's three loose ends closed — ADR-0541 · **v1.0.297**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** Branch `claude/focused-ride-4u3cpl` from `main` @
> `40cca07c` (#727, ADR-0540, v1.0.296; CI run #2027 — cui-guard and browser green, the three test jobs still running when
> this session started; re-checked before the push). The campaign's four T1 disclosures (session 7) are carried verbatim in
> the 2026-09-29 (c) section at the top of `HANDOFF-ARCHIVE.md` and in `docs/STATE/AUDIT-2026-09-23.md`; this session fixed
> none of them, and **A0923-IMP-005** and **A0923-DOC-003** stay strict-xfail.

STATUS (current) — **ADR-0541 is on draft PR** of `claude/focused-ride-4u3cpl` (the operator marks it ready and
squash-merges; a session never does). Highest ADR on disk **0541**. Version **1.0.297**; LODESTAR **1.0.2**
(`lodestar/LODESTAR.pyz` 816,775 bytes, **42 members**); the wheel and the nine installers rebuilt from a clean worktree of
the source commit. QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0541 did (the operator's kickoff, 2026-09-30)

- **The size cap ruling (item 4) was an unfilled template** (`[KEEP AS SHIPPED / RAISE TO … / LOWER TO …]`): **KEEP AS
  SHIPPED assumed** — `LABEL_MAX` 14 / `LANE_NAME_MAX` 12 / `GLYPH_MAX` 40 untouched, nothing re-derived for it; the
  3 / 10 / 40 / 144-item renders in four views at 1440 and 390 px on both pages were delivered as contact sheets with this
  session (`timeline_1440.png`, `timeline_390.png`, `compare_1440.png`, `compare_390.png`, plus LODESTAR's launch page and
  the Polaris² / LODESTAR side-by-side). **The ruling proper is still the operator's.**
- **The data date (item 11)** — `onepager_today` IS the operator's data date (one setting for both pages, `None` the
  computer's date); a **Data date** control on both pages in Polaris² and LODESTAR (`set_today`, `POST …/today`); the red
  line, its caption (`DATA DATE m/d/yy`), the legend, `plot_window`'s notes and the chip follow it and never say "today";
  **"Prepared" / "generated" stay the computer's date** and the subtitle names the data date beside it when they differ
  (`subtitle_for(..., prepared)`, `_onepager_dates` / `_Handler._dates`); the layout cache keys on both dates.
- **LODESTAR's launch page (item 12)** — `web/lodestar_launch.py` at LODESTAR's `/launch` (the program opens on it):
  Polaris²'s boot screen, the SAME `launch.js` / `launch.css` / hum, made LODESTAR's by what the page supplies through the
  boot JSON (`heroes`, `stages`, `home` — Polaris²'s tables are the script's defaults, its 29 boot tests unchanged), the ✦
  mark, the lodestar's gold accent in every view (`lodestar_launch.css`), its own icon (`lodestar.ico`, drawn by
  `desktop_icon.lodestar_ico_bytes`, its favicon too), real facts in the tiles. §7a's rules hold; Chromium pins at 1440
  and 390 px in four views.
- **The first-run Desktop shortcut (item 13)** — `lodestar/shortcut.py`: once per archive (a marker in LODESTAR's per-user
  data folder), best-effort, LODESTAR's own icon; `--shortcut` / `--no-shortcut`; Windows `.lnk` via PowerShell COM
  (`py -3` when present), macOS `.app`, Linux `.desktop` — **Linux run for real through the committed archive; Windows and
  macOS by reading, UNVERIFIED**. Every archive launch in the pyz tests passes `--no-shortcut` (they would have planted one
  on a developer's Desktop).
- **ADR-0540's follow-ups:** (1) `TODAY_CAPTION_DY` 5.5 — the caption's box clears the last band (Chromium-measured, a
  mutant at 4.5); (2) **the "2 of 600 gutter" premise FELL**: 0 gutter cases in 1,800 slides, but a clean-judged head on an
  earlier PLAIN horizontal leg on 66 / 34 / 22 of 100 seeds of three generators — heads are judged against every leg now
  (`_head_legs`), measured in-process before choosing (+1.4 % dashed links at most, the class gone) — and the
  escalation no longer buys a drawn link with a clean leg laid on a label (`RouteReport.touches`; the densest sweep
  slide had traded one undrawn link for six such legs once the reorder step re-packed it 0.15 pt tighter); (3) **decided: the
  legend's spare row carries a one-line footnote** when the list fills the slide and the legend uses one row
  (`spare_row_footnote`), on the page and in the .pptx.
- Pins re-derived with their reasons: the pristine digest (two reasons, once); the deck's `Today` shape names; the frozen
  "generated" date (a shape, not a value); review seed 105 (F3) → the mechanism; the gutter-ledger seeds 12 / 13 → 103 /
  110; the pyz member pin 34 → 42, named.

## Measured at close (Python 3.11, a clean worktree of the final commit)

_Filled in by the artifact commit: the static gate at the pinned ruff 0.16.9, mypy, bandit, node; the FULL suite and
`-m parity` on the clean worktree; the browser census; the LibreOffice interop gate is SKIPPED here (the container's
soffice has no Impress — CI installs it)._

## Decision for the operator (ASK, do not assume)

**The readable size cap for tiny lists** — still open: the shipped provisional caps stand; the renders are with this
session. **Rule before anyone changes a constant.**

**UNVERIFIED, stated:** the Windows `.lnk` and the macOS `.app` the first run writes (and Gatekeeper's view of a bundle
written by the user's own Python); Windows / macOS launching and the installers' icon on those hosts (ADR-0540); PowerPoint
itself; Firefox / WebKit.

## Next

1. The operator reviews the draft PR, marks it ready and squash-merges; then `git fetch --prune origin && git remote
   set-head origin -a && git checkout -B <branch> origin/main`.
2. The cap ruling; a real Windows and a real macOS run of `LODESTAR.pyz` (the shortcut and the launch page).
3. Follow-ups still out of scope (record only): UIP-3, ROUTES-5, the empty-workbook "1 row(s) skipped", Excel percent
   formats, the pre-commit hook and a shebang-prefixed ZIP; LODESTAR's release channel.
4. **Answered by the operator (2026-09-29) — do not ask again:** rulings (a) / (b) / (c) of ADR-0540; column E holds the
   WORD "Complete"; LODESTAR's release channel is out of scope.

The AUDIT-2026-09-23 campaign's own Next is session 7's — in `HANDOFF-ARCHIVE.md` — and its resume line in
`NEXT-SESSION-PROMPT.md`.

## Traps this session paid for, by name

**A kickoff can carry an unfilled ruling** — assume the no-change reading, say so, deliver the evidence. · **A
box-based collision probe over-counts** — judge the triangle. · **A frozen "today" seam that becomes a feature changes the
meaning of every test that used it** — re-derive the pins to the shape of a date. · **A pyz test that launches the
archive plants whatever the archive does on first run** — `--no-shortcut` everywhere, a HOME of its own for the shortcut
tests. · **`deck_shapes` never lists a connector.** · **mypy enters a Windows-only branch unless the function returns
first on other platforms.** · **A JS comment is text a text pin reads.** · The container's traps of 2026-09-29 (c) stand
(editable install, pinned ruff, `--depth=2`, git identity env, clean worktree, one push, coordinate clicks, no rsync).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
