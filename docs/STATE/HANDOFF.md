# Handoff — 2026-09-02 (session close: PR #621 MERGED — the header root cause (ADR-0445, v1.0.227) and the One-Pager (ADR-0446, v1.0.228) are on `main` @ `74e98d99`; WP3 is next)

> ## STATUS (current) — **PR #621 squash-merged to `main` @ `74e98d99` (2026-09-02 12:31Z, all seven CI checks green on its head `de56a557`). Branch `claude/polaris2-audit-resume-3xg50n` was restarted from that `origin/main` (GitHub deleted the merged head); NO open PR at close. WP0/WP1/WP2 MERGED; the two operator items on top MERGED. QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0446**; version **1.0.228**; wheel + nine installers in lockstep on `main` — the operator re-downloads from `main` once (banner must read **v1.0.228**). Campaign queue: **WP3 (M4, the SRA grid)** is next — branch fresh from `origin/main`, open a new draft PR.
>
> ## What is on `main` now (both merged in #621; full narrative in the archived 2026-09-01 handoff)
> **ADR-0445 (v1.0.227) — the operator's diagonal timeline header, ROOT-CAUSED.** `hud.css`'s tooltip
> anchor `[data-sf-hint]{position:relative}` out-cascaded `.g-band{position:absolute}` on every titled
> band, bar and milestone (in the tree since 2026-07-11, all four themes, one file or two). Fixed with
> `:where([data-sf-hint]){position:relative}` — zero specificity — and mutation-proved both ways (plain
> selector → staircase; rule deleted → 206 of 215 tooltip hosts static). Second layer: ADR-0442's UI-01
> (`sizeGrip`) was this same hijack misdiagnosed as a Chromium quirk — DELETED; CSS alone seats the grip
> at `[47,0,7,58]` and the drag driver now asserts absolute · flush-right · full-height · reachable.
> **ADR-0446 (v1.0.228) — the One-Pager.** `/onepager` (LIBRARY rail): a three-column Excel list
> (swimlane · task or milestone · date) → ONE 16:9 swimlane slide previewed as an SVG → the SAME slide
> as native, editable PowerPoint shapes (`/export/pptx/onepager`) + the parsed list to Excel/Word
> (`/export/{fmt}/onepager`) + a template (`/export/{fmt}/onepager-template`). **One layout, two
> painters:** `reports/onepager.py` computes every coordinate in slide points (960×540, 1 pt = 12,700
> EMU); `static/onepager.js` and `reports/pptx.py` only paint. Every parser decision is on the page by
> row number; density steps the label floors down AND says so; a list that cannot fit is told to split.
> 43 reports + 13 page + 4 Playwright tests; python-pptx and LibreOffice Impress renders viewed.
> **Still UNVERIFIED in PowerPoint itself — ASK the operator what their first open showed before
> touching it.** The third commit (`de56a557`) was test-only: `from tests.web.…` collects under
> `python -m pytest` and dies under CI's plain `pytest`.
>
> ## Carried forward — observed, deliberately NOT fixed (ask before acting)
> - The sticky controls bar (`#pathControls`, z6) overlays the sticky header (z3/4) at the top scroll
>   position — a cross-page z-order design question (ledger row; drivers scroll to viewport centre).
> - The Word/Excel writers always stamp the CUI banner regardless of the session's classification
>   mode; the One-Pager slide follows `_cui_marking` instead — a pre-existing inconsistency (ADR-0446).
> - The One-Pager in PowerPoint (above) — the operator's first open settles it.
>
> ## Gate at close
> Docs-only close: no `src/` change, no rebuild, nothing to re-measure. On the merged head: full suite
> **4658 passed / 5 skipped / 1 failed in 47:31** (the one red the installer lockstep, whose wheel
> predated the last route rename — rebuilt after, lockstep 68 passed); CI green on `de56a557` (all
> seven); drift guards 17 passed on this close.
>
> ## Traps paid for this session, by name (the kickoff carries the full list)
> RENDERED `y` + COMPUTED `position` measure a positioning claim, never inline styles or widths · a
> global `[attr]{position:relative}` hijacks every positioned element that gains the attribute — use
> `:where()` · ask the engine which rule won (CDP `CSS.getMatchedStylesForNode`) · a workaround written
> against a hijacked state becomes the bug once the hijack is fixed · one layout, two painters · read the
> operator's file cell by cell before writing a parser · bisect the environment before the artifact ·
> `TestClient` follows a 303 · `panelkit.js` is a per-page include · `TIME_RE` is singular · compute
> fixture serials · `python -m pytest` vs plain `pytest` differ in `sys.path` — never `from tests.…`.
>
> ## Next — campaign queue (unchanged)
> **WP3** (M4 SRA grid edit / paste-from-Excel / save round-trip) → **WP4** (route-coverage
> instrument + the 08-26 `startup_failure` root-cause) → **WP5** (BOTH folder builds) → **WP6**
> (ledger highs: CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** (thin dims,
> `ai/txlog.py` first) → **WP8** (consolidated report + roadmap by testimony risk).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
