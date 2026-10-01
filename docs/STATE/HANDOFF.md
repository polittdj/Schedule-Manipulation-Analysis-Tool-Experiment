# Handoff — 2026-10-01 (LODESTAR 2.0 — the operator's "Console" design handoff built whole; the One-Pager's logic links drawn shortest-route BEHIND the items in both programs, ADR-0540's escalation retired — ADR-0543 · **v1.0.298**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** Branch `claude/wonderful-ptolemy-tl0xru` from `main` @
> `fac57735` (#729, ADR-0542, v1.0.297; 828 commits). The campaign's open disclosures are carried verbatim below; this
> session fixed none of them, and **A0923-IMP-005** and **A0923-DOC-003** stay strict-xfail.

- **T1 (latent, option-gated) — A0923-CPM-048:** a schedule saved with "Split in-progress tasks" OFF (`<SplitsInProgressTasks>0</SplitsInProgressTasks>`) has every out-of-sequence started task's remaining work split off its actual work and restarted at its predecessor's finish anyway — the element is never read — so that task's finish, its successors' dates and the served project finish (`/analysis`, `/path`) read later than the file's own, undisclosed (the hand file: 01/14/2026 for 01/13/2026). Since c18dcd24 (the tree's first commit; the current restart shape since 85f0c6ce, #702, v1.0.278, ADR-0513). Every committed file is saved with the option ON. Until fixed, check the option on an operator file before citing its finish.
- **T1 (latent, mode-gated) — A0923-CPM-049:** a STARTED manually scheduled task (`<Manual>1</Manual>` with actuals) is re-spanned by logic from its predecessor's finish and by the R-72 restart — MS Project keeps a manual task at its stored dates, and ADR-0034 / the served explainer promise the pin only for unstarted tasks — so its finish, its successors and the served project finish move, undisclosed. Since 7d893f6c (#91, v1.0.0, ADR-0034). No committed file carries a started manual task. Until fixed, read a started manual task's dates from the file's own Start / Finish.
- **T2 (latent, option-gated) — A0923-CPM-050 / 051:** "Calculate multiple critical paths" and the critical slack limit are never read: on a file declaring either, `/path`'s "What drives the date" chain and the DCMA-12 target set hold the single-terminus, slack ≤ 0 set (2 activities for the file's 4) while `/analysis` prints the stored count beside them, an independent network's end gets the project finish as its late finish and days of float, and no page names the option. Until fixed, read Critical from the file's own flag on such a file.
- **An instance of A0923-CPM-040 in the SHIPPED DEMO:** "Load example" then a posted target makes `/export/{xlsx,docx}/path` answer 500 (undated tasks only; every committed schedule file is 200). U57 widens.

Session 7's four lines and the earlier ones are carried unchanged in `docs/STATE/AUDIT-2026-09-23.md` (the session-7, -6 and -5 sections) and in the asks file; read them there.

STATUS (current) — **ADR-0543 MERGED** as `ad2cfa14` (#730, 2026-10-01 13:35Z; squash tree `d5683fec` identical to the
green PR head `e6d241c2`, all eight checks green). Highest ADR on disk **0543**. Version **1.0.298**; LODESTAR **2.0.0**
(`lodestar/LODESTAR.pyz` 841,464 bytes, **48 members**); the wheel and the nine installers rebuilt from a clean worktree
of `1d910711` (75 installer tests green there). The full suite and `-m parity` on the final tree are recorded in the
SESSION-LOG entry's gate line. QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0543 did (operator request 2026-10-01: "update the UI for the Lodestar stand alone program … create [any missing] functionality")

- **The studio** (`web/lodestar_studio.py`, `lodestar_actions.py`, `lodestar_history.py`; `static/lodestar_studio.js`,
  `lodestar_slide.js`): server-rendered regions swapped in place over a same-origin JSON API (`/api/state`,
  `/api/<action>`, `/api/preview` on a session COPY, `/api/undo|redo`); ONE dispatcher for the JSON and the v1 form
  routes (scripting off still works); undo/redo of 60 steps with a session log; Ctrl/⌘K palette; a 7-step tour; five
  Show-me demos; a data-date slider (linear feedback + throttled preview, ONE commit); drag-to-link; DATA drawer; full
  screen; Print/PDF of the slide alone on ONE page.
- **Its own design system:** the handoff's A1 tokens (`lodestar_tokens.css`, four views dark / bright / contrast /
  console, `lodestar_view.js`, key `lodestar-view`) — Bright's text tokens darkened for WCAG AA (93 failures → 0, every
  view and overlay swept); IBM Plex Sans / Mono + Space Grotesk vendored (`static/fonts/`, OFL; package-data now names
  `web/static/fonts/*`); a Lucide sprite (`lodestar_icons.py`, ISC). LODESTAR loads none of Polaris²'s sheets or scripts.
  The frame: 56-px header (nav links with `aria-current`, palette, Undo/Redo, views, marking, Tour, Quit), 320-px side
  panel, status bar, CUI bars, the ONE drawer copy, the credit top and bottom (launch page too).
- **The launch page** (`lodestar_launch.py/.js/.css`): its own hero, a six-stage star fix ending on a welcome panel, the
  v1 opt-out key kept, real tiles, the list→slide animation; no canvas, no sound.
- **Logic links, BOTH programs** (`reports/onepager_links.py`, `static/onepager_links.js` + the two page painters,
  `reports/pptx.py`): the handoff's shortest-route rule (anchors on the shape edge, ≤9 candidate columns scored
  `10·bars + 3·names + 0.002·distance`, go-round along the row boundary); the shaft UNDER the items, head + tag OVER;
  labels outside their bar haloed (a 1.5-pt glow in the .pptx); the .pptx paints "Logic link: …" (shaft) and "Logic link
  arrowhead: …" (head + tag) per link. ADR-0540's escalation (spacing, gutter, reorder, glyph shrink, dashed, footnotes)
  REMOVED — the slide is laid out once; links never move an item (measured three ways).
- **One copy of the pages' sentences** — `web/onepager.py` / `onepager_compare.py` builders read by both programs
  (52 renders byte-identical to the parent commit).
- **Bugs found by the test stream and fixed red → green:** the JSON gate read `{"title": true}` as a missing title and
  wiped it; the slider lost keyboard presses (12 keys → +2 days); contrast below AA; the launch page carried the credit
  once; print produced two identical pages.

## Open — for the operator

- **RULED 2026-10-01 by the operator: the head-over-label overlap stays — NO label nudge.** A 4.2-pt head entering an
  item on its LABEL's side covers ~1.2 pt of the label ("◂CDR"); the proposed fix (move labels, changing item geometry
  on every slide) is REJECTED. Do not re-propose it. Also recorded, unchanged: SS + FF on one pair share a row
  boundary; FS links into one start share a last leg.
- **Three pre-existing PowerPoint defects** (reproduced 2026-10-01, NOT fixed here): month lines hidden under the opaque
  lane fills; the UNCLASSIFIED marking text painted in CUI purple (`_CUI` 4B2E83); `_rels/.rels` names no docProps part.
- **Noted, not in scope:** `web/help.py`, `i18n.py`, `offload.py` and `system.py` are in no `LAYER_ORDER` row of
  `tests/web/test_monolith_split_contract.py`, so the downward-import guard never checks them (found by the test
  stream; pre-existing).
- **Carried unchanged:** the size-cap ruling (`LABEL_MAX` 14 / `GLYPH_MAX` 40 / `LANE_NAME_MAX` 12 PROVISIONAL).
- **UNVERIFIED:** PowerPoint itself (no Impress here); Firefox / WebKit; Windows / macOS; a physical printer; a blocked
  `www.google.com` CONNECT seen once during a lint run (LODESTAR's pages make no remote request — measured; the proxy log
  that would name the caller was not readable here).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
