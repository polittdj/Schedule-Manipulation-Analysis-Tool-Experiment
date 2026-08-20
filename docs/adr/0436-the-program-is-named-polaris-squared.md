# 0436 — the program is named Polaris² (and what a rename deliberately does not touch)

- **Status:** accepted (operator directive 2026-08-20: "Change the name of the program to be
  Polaris (squared) - like to the exponent or power of 2")
- **Date:** 2026-08-20
- **Scope:** every DISPLAYED product name; no internal identity

## Decision

The product's displayed name is **POLARIS²** — the existing POLARIS brand with a Unicode
superscript-two (U+00B2). The character form was chosen over markup (`<sup>2</sup>`) because
the name must survive every medium the program writes it into: window `<title>`s, terminal
banners, Word/Excel export headings, `.lnk`/`.command` file names, and plain-text READMEs.
`²` renders in all of them; markup renders in one.

Where the name IS the hand-set SVG wordmark (ADR-0175 — stroke letterforms, no webfont), the
² is a new hand-set glyph in the same NASA-worm vocabulary: a single stroke path
(`class=brand-sup2`, stroke-width 8 vs the letters' 13, top-aligned to the caps) between the
S and the trailing north star; the star shifts right and the viewBox widens 344 → 382 (the
`.brand-mark` aspect-ratio follows). Verified by RENDER, not inspection — the masthead was
screenshotted in chromium before landing (QC-1; the glyph's geometry is hand-guessed
coordinates that no unit test can judge).

## Renamed surfaces

masthead wordmark + `aria-label`/`title` backronym prefix (`web/chrome.py`, `static/app.css`)
· every page `<title>` suffix · the boot screen title (`web/launch.py`) · the FastAPI app
title · the launcher's three console lines (`launcher.py`; `²` exists in cp437/cp1252, so
legacy Windows consoles render it) · the Word/Excel export titles ("POLARIS² — Executive
Briefing" / "— Diagnostic Brief" / "— Ask the AI" / per-schedule) and the export provenance
lines ("Generated locally by POLARIS²…") · the nine installers' banner ("Polaris² (Schedule
Forensics) installer — vX.Y.Z — Tier …"), step lines, first-run README, uninstaller strings,
and the user-facing shortcut names — Windows desktop/Start-Menu **Polaris²** (`.lnk`), Linux
app-menu entries "Start/Stop Polaris²", macOS Desktop "Start/Stop Polaris².command" · the
distributable README · the wheel's `description`.

**Upgrade hygiene:** a renamed shortcut would otherwise leave the old icon behind, so the
Windows installer removes the legacy `Schedule Forensics.lnk` and the old Start-Menu folder,
the macOS installer removes the legacy Desktop `.command` pair, and the uninstallers remove
BOTH generations of names.

## Deliberately NOT renamed

The `schedule_forensics` package, wheel/dist name, CLI entry point, venv path, install
directory (`ScheduleForensics`), the in-folder troubleshooting scripts' file names, and the
Linux `.desktop`/symlink file names. Renaming filesystem/import identities buys no operator
value and breaks upgrades-in-place. Two bounded exceptions to the display rule, both
constraints: the Windows `Start/Stop-ScheduleForensics.cmd` INTERNALS keep the old wording
(they are written `-Encoding ASCII`, which cannot carry `²`), and the docs/repo continue to
say "POLARIS/SMAT" as the project codename. "(Schedule Forensics)" stays as the descriptor
in the installer banner and README titles so existing users recognize the artifact.

## Pins

`tests/web/test_polaris_squared_brand.py` (wordmark glyph + widened viewBox + titles + app
title + template banners) · retargeted pins in `test_app.py` (title, viewBox 382),
`test_briefing.py`, `test_trend_views.py` · the rendered-banner locator in
`tests/installer/test_installers.py` now finds the Polaris² banner line, keeping its
embedded-version assertion. All were observed RED against the pre-rename tree.
