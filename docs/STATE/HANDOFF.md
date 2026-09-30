# Handoff — 2026-09-29 (c) (One-Pager: the slide fills the page at every list size, every logic link is fitted — more space, a gutter lane, a reorder within the swimlane, then drawn dashed and NAMED — and the installers put the tool's own Desktop icon on the machine — ADR-0540 · **v1.0.296**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** This session took **ADR-0540** after ADR-0539 landed;
> **ADR-0538 is held by AUDIT session 7's draft PR #726** (`claude/modest-cori-iit4zh` @ `3a177864`, opened 2026-09-29
> 23:09Z — the branch did not exist on the remote when this session started; base `996b28b2`, `src/` unchanged, no version
> bump) — **squash-merged by the operator as `5c6622fd` (2026-09-30) while this PR was open**, so this branch merged
> `main` (a merge commit; the state docs conflicted as predicted), moved session 7's handoff section to the top of
> `HANDOFF-ARCHIVE.md` demoted and kept its LESSONS entry beside this one. The campaign's disclosures below are session
> 7's four, VERBATIM; per session 7 the earlier ones now live in `docs/STATE/AUDIT-2026-09-23.md` (the three-way merge
> took that move). This session fixed none of them, and **A0923-IMP-005** and **A0923-DOC-003** stay strict-xfail.

- **T1 — A0923-CPM-042 (in committed corpus):** an ELAPSED activity's "Remaining duration" is served over the project's 480-minute working day, three times its own duration on an 8-hour day: on the committed Hard_File_updated3 / Hard_File_updated4_24h goldens UID 146 reads 6.0 d beside its Duration 2.0 (elapsed) — Acumen Fuse's Remaining Duration shows 2 — and Jacked_Up_Schedule_1's UID 20 reads 96.0 for 32; the figure reaches the Task Information dialog, the unrestricted Ask table and the activities exports that name the column (`web/state.py:1775`). Since 7eb8708a (#314, v1.0.4, 2026-07-10, ADR-0183). Until fixed, read an elapsed activity's remaining work from its Duration line, never from "Remaining duration".
- **T1 (option-gated) — A0923-CPM-036 / 038 (family B — the counterfactual pages; in committed corpus):** with a trace option on ("Ignore constraints" / "Ignore leveling delay" on /driving-path, /evolution and their exports), the pages do not show the re-solve their banner promises: with no focus UID /evolution's critical path, its entered / left counts and its docx / xlsx exports are the source file's STORED Critical flags drawn at the re-solved dates (CPM-036 — the drawn set moves on 0 of 44 corpus files where the re-solved set differs on 24), and "Ignore constraints" ticked ALONE changes nothing on a fully-dated file — the tiers, driving slack and focus path are the stored schedule's (CPM-038 — inert on 44 of 44; Hard_File target 411's 88 rows unchanged). Since 140aed3a (#292, v1.0.4, 2026-07-08, ADR-0155). Until fixed, do not cite a family-B page's path, tiers or counts as a counterfactual; tick both options together and read the re-solved FINISH only.
- **T1 (latent — no committed file exercises them) — A0923-CPM-043 / 044 / 046 / 047:** CPM dates and floats are wrong on an operator file that carries a task on a calendar with non-working weekdays (e.g. a 24-hour Monday–Friday crew calendar) whose late finish falls at its week's end — negative total float and a late start before the project start (CPM-043); a lagged FF or SF link from a 24-hour-calendar or elapsed activity — that activity shown with negative float, critical (CPM-044); a lagged SS or SF link into an activity on its own calendar — that activity and the project finish up to 15 hours later than the equivalent FS / FF link (CPM-046); or a lag-0 SS / SF link from a project-calendar task that starts after a mid-day break into a 24-hour or elapsed activity — scheduled up to an hour before its predecessor starts, float an hour high (CPM-047). Since afb8e729 (#497, v1.0.140, 2026-07-31). Check an operator file for these shapes before citing its CPM figures.
- **T1 (data-gated) — A0923-IMP-011:** a hand-written or third-party `.json` schedule whose calendar repeats a holiday, lists its day blocks out of order, or declares blocks that contradict its day length is accepted with no error and no note and computed wrong (a repeated holiday costs one working day per extra listing: a 3-day task finishes 01/09/2026 for 01/08). Since e5a67518 (#70, v1.0.0, 2026-06-11). Only the tool's own JSON format reaches it (0 committed files); check such a calendar before citing the file's dates.

Session 6's seven lines and the eight earlier ones are carried unchanged in `docs/STATE/AUDIT-2026-09-23.md` (the session-6 and session-5 sections) and in the asks file; read them there.

STATUS (current) — **ADR-0539 is on `main`**: draft PR #725 was squash-merged by the operator as **`996b28b2`**
(2026-09-29 21:45Z; CI run #2019 green). The 2026-09-29 (b) handoff, SESSION-LOG entry and NEXT-SESSION-PROMPT said it
waited on the operator — it no longer does, and this section corrects that. **The ADR-0540 feature is COMPLETE on draft
PR** on branch `claude/gracious-lovelace-8hwycm` (from `main` @ `996b28b2`; the PR number is in the branch's pull request) — the
operator marks it ready and squash-merges; a session never does. Highest ADR on disk **0540**. Version **1.0.296**;
the wheel, the nine installers (MPXJ ref `163d1942`, fetched `--depth=2`) and `lodestar/LODESTAR.pyz` (707,568
bytes, 34 members) are rebuilt from a clean worktree of the final source. QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0540 did (the operator's asks, 2026-09-29)

- **Full-page fill, always** (`reports/onepager.py::fit_rows`, both pages, both .pptx, LODESTAR): the rows, bars,
  diamonds and labels scale to the whole lane area at every list size — a 3-item slide filled 13.7 % of it before
  (rows capped at 13 pt, labels at 8 pt) and fills 100 % now, as do 10 / 40 / 144 items (measured both pages). The
  ROWS are never capped; the TEXT is (`LABEL_MAX` 14 pt, swimlane names 12 pt) — **provisional until the operator
  rules** (below). The row pitch and the glyph height are returned apart, so the fit has a fixed point (40 items
  cycled 16 ↔ 17 rows and filled 94 % before that).
- **Every logic link fitted** (`fit_links` / `Attempt` / `Fit`; the router's `route_all`): in the operator's order —
  (1) the bars, diamonds and labels shrink (100 → 80 → 65 %) to open space between the rows; (2) a 12-pt gutter lane
  at the slide's right edge carries the links no channel can; (3) items are reordered WITHIN their swimlane (never
  across; `_swap_ok`, 12 trials) — never a second slide; every step is disclosed on the page ("How the logic links
  were fitted") and in the Excel Notes. Bounded: `WORK_BUDGET` 24,000 judged routes over ALL attempts; deterministic
  (two runs of 144 items × 200 links identical, 15.7 s, 200 of 200 drawn).
- **The last resort draws** (ruling (c)): a link no route clears is drawn along the route with the LEAST overlap,
  DASHED, flagged in its tooltip, listed on the page ("Logic links drawn dashed over other ink — N of M"), and named in
  the slide's own footnote — one text box painted by the page's SVG AND the .pptx (`_footnote`; "Caution — N logic
  link(s) drawn dashed over other ink, no clear route existing: …", `FOOT_CHAR_W` 0.66 so LibreOffice keeps it on the
  slide). ADR-0539's "refuse and name" rule is superseded. Property pinned: every erasure by a flagged link names its
  victim (independent generator; seed 15 caught the force path judging a COPY of the route).
- **The router got faster with an identical answer** (`onepager_links.py`: axis-gap reject, per-leg strips,
  precomputed vertical legs, a y-band index): 6.7 → 3.8 s on the stress slide, the output digest identical over 1,250
  links of the review's generator. Two more tag spots (above / below the channel line) so a 3-item slide with three
  links is no longer "crowded".
- **Excel keeps the sheet's own order** (decided; the Notes table says the slide reordered); **one layout per state per
  session** (`onepager_common.cached_layout` — GET, PowerPoint and Excel share it; keyed on the list, the window, the
  title, today and the links).
- **The Desktop icon is the tool's own** (`schedule_forensics.desktop_icon`: `.ico` / `.png` / `.icns` from the shipped
  favicon's five PNG frames): Windows `.lnk` `IconLocation`; Linux `.desktop` `Icon=` plus a trusted Desktop copy; macOS
  a `Polaris².app` bundle on the Desktop. Written by reading and by the generated-installer tests — **no Windows or
  macOS host here (UNVERIFIED)**.
- **The three rulings are recorded** in DESIGN-SYSTEM §7c and ADR-0540: (a) the marking switch does NOT reach the
  Excel exports; (b) the slide's 7.8 px SS / FF / SF tag IS exempt from §1's 8 px floor; (c) unavoidable collisions are
  drawn and disclosed, never refused.
- **Three adversarial reviews, 17 findings, each re-reproduced red, fixed and pinned** (ADR-0540's third table): among them `GLYPH_MAX` 40 with a per-diamond clamp (a 2-item diamond had left the slide), the footnote's four compact lines with whole entries counted past them, the reserve guards (`fit_links`), the cache's one-instant snapshot (`OnePagerSnapshot`), the icon writer's CRC walk, the Linux Desktop entry's `Name=Polaris²`, the gutter ledger (`RouteReport.points`), `_WARN` in print, LODESTAR 1.0.1.

## Measured at close (Python 3.11, a clean worktree of the final commit)

Static gate green at the PINNED ruff 0.16.9 (`ruff check .`, `ruff format --check .` 1,387 files), `mypy src/` 178 files, `bandit` exit 0, `node --check` per file; `build_lodestar.py --check` current (707,568 bytes, 34 members). **The FULL suite on a clean worktree of the source commit `26128a81` with the rebuilt artifacts in it: 6,583 passed, 5 skipped, 83 xfailed, 1 failed, exit 1 in 58 min 20 s** — the one failure the axis-caption ledger (`test_r11_panel_contract`, both One-Pager painters' caption call sites moved on purpose to `L.h - 3`), re-derived in the second commit and its module re-run green on the final tree (25 passed); no XPASS (A0923-IMP-005 and A0923-DOC-003 still strict-xfail). **`-m parity` 271 passed, exit 0 (11 min 43 s).** On the final tree: `tests/installer` + the LODESTAR lockstep + `tests/test_state_docs.py` 113 passed. The browser census (Chromium, LibreOffice Impress) ran inside the full suite. PR #726's own reproducers run against this tree: 62 xfailed, 0 XPASS, 0 failed.

## Decision for the operator (ASK, do not assume)

**The readable size cap for tiny lists.** Shipped: rows uncapped (3 items: 134.7-pt rows, 91.6-pt bars), text capped at
`LABEL_MAX` 14 pt / swimlane names 12 pt. The renders at 3 / 10 / 40 / 144 items (both pages, four views; the before
and after) were delivered to the operator with this session — **rule on the cap before anyone changes the constant.**

**UNVERIFIED, stated:** Windows / macOS launching and the icon on those hosts (the `.lnk`, the `.app` bundle,
`gio set … trusted`); PowerPoint itself (LibreOffice Impress rendered the .pptx here); Firefox / WebKit; the
2026-09-29 (b) session's UNVERIFIED items stand.

## Next

1. The operator reviews draft PR of `claude/gracious-lovelace-8hwycm`, marks it ready and squash-merges; then `git fetch --prune origin` and
   restart the branch per CLAUDE.md. #726 (ADR-0538) merged first (`5c6622fd`); this PR merged `main` and keeps BOTH
   sessions' state-doc sections (session 7's at the top of the archive) — nothing rebuilt (#726 changed no `src/`).
2. The cap ruling above.
3. Follow-ups (out of scope, recorded only — ADR-0539 / ADR-0540): the NEW / REMOVED badge text is wider than its badge
   (UIP-3); a 500 on a Polaris² route carries no CSP / nosniff (ROUTES-5); an empty workbook says "1 row(s) skipped";
   reading Excel's percent format; the pre-commit hook cannot see into a shebang-prefixed ZIP (`.pyz`) — the LODESTAR
   lockstep test guards it until then.
4. **Answered by the operator (2026-09-29) — do not ask again:** rulings (a) / (b) / (c) above; column E of the real
   lists holds the WORD "Complete"; how LODESTAR is released or shared is OUT of scope — do not raise NPR 2210.1.

The AUDIT-2026-09-23 campaign's own Next is session 7's — the top `(prior)` section of `HANDOFF-ARCHIVE.md` — and
its resume line in `NEXT-SESSION-PROMPT.md`.

## Traps this session paid for, by name

**An editable install shadows a worktree** — `PYTHONPATH=<tree>/src`. · **The container's ruff is not CI's** (pin
`ruff>=0.16.1,<0.17` in a venv). · **A shallow clone refuses the installer build** — `SF_MPXJ_REF=163d1942…`, fetched
`--depth=2` (a `--depth=1` fetch makes the ref a graft boundary). · **The container's git identity env overrides git
config** — set `GIT_AUTHOR_*` / `GIT_COMMITTER_*` = Claude <noreply@anthropic.com> on each commit. · **Build the .pyz,
the wheel and the installers from a CLEAN worktree of the commit.** · **Every push cancels CI's run in flight** — one
validated push. · **A fit loop needs a fixed point** — a glyph sized from the row count changes the row count; return the
pitch and the glyph apart. · **A forced route judged as a COPY reserves nothing** — judge the route itself. · **A budget
that counts only the last step is no budget** — count every attempt. · **Playwright's locator click is stricter than a
pointer** — a label at the shape's centre (a sibling in the item's group) makes it refuse a click the operator's pointer
delivers; click by coordinates. · **`rsync` is absent here and `2>/dev/null` hid it** — `cp -r`, and read stderr.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
