# ADR-0494 — Every page states the installed build: the Boot Screen first under the compliance chrome, and the header beside the brand on every chrome page (OR-18)

- **Status:** Accepted — 2026-09-15 (operator directives, the same day: *"add at the top of the launch page the version number of the installed program so that we don't have to go through so much effort to tell if the correct version has been uploaded to my computer"*, then *"I agree with your recommendation: the same chip in the global header so every page and every screenshot pins the build"*).
- **Version:** 1.0.262
- **Extends:** ADR-0493 (OR-17 had to establish the installed build from the WORDING of a screenshot because no page carried a version; AI Settings gained `tool version:` there), ADR-0426 (the Boot Screen), ADR-0195 (the design system: tokens only, the compliance chrome never displaced, four themes measured).
- **Shipped:** `web/chrome.py` (`tool_version()` — the accessor read at RENDER time; the `brand-ver` chip in `_LAYOUT`; `build_version` passed at render), `web/launch.py` (the `boot-version` line after the compliance chrome), `web/static/base.css` (`.brand-ver`, `--header-muted`), `web/static/launch.css` (`.boot-version`, `--boot-muted`), `web/app.py` (the `X as X` re-export the monolith-split contract requires), `tests/web/test_version_chip.py` (4, NEW), `tests/web/test_version_chip_browser.py` (4 themes × 2 widths, NEW).

## Context

"The launch page" is `/launch`, the Boot Screen the desktop icon opens on — OUTSIDE the story
chrome (no header, no nav), rendered by `web/launch.py::_launch_html`; its first elements are the
CUI bar and the compliance drawer (design system §6: never displaced). The header of every other
page is `chrome.py`'s `_LAYOUT`; its brand subtitle is hidden in three of the four themes, so a
version could not ride it. Red first: on the pristine tree the visible text of `/launch` and `/`
carries no version (`/settings` does, since ADR-0493).

## Decision

1. **The Boot Screen states the build as the first thing under the compliance chrome:** a
   server-rendered `<div class=boot-version data-tool-version data-no-i18n>` after the CUI bar
   and the drawer, before the boot stage — present even when the boot script never runs (the
   hero text is script-filled; this line is not). Monospace, `--boot-muted`, centred.
2. **Every chrome page states it in the header beside the brand:** `<span class=brand-ver
   data-tool-version data-no-i18n>` right after the wordmark's `</h1>`, `--header-muted`,
   `nowrap`, visible in all four themes. The header is hidden in print (base.css), so the chip
   does not print — exports keep their own marking (§6); a version on exports is not this unit.
3. **The element's TEXT is the bare version; the visible "BUILD" label is CSS-generated
   (`::before`)** — so every pin, every screenshot and the settings chip read the same digits,
   and `data-no-i18n` keeps the DOM translator off the number.
4. **Read at render time through `chrome.tool_version()`, never bound at import and never a
   literal** — a test monkeypatches the module constant to `9.9.9-probe` and both surfaces follow.
5. **What the chip means, stated to the operator:** it is the version the RUNNING process reports
   (the installed package's metadata; `dev` on a source-tree run). An older copy still serving the
   port shows its own, older, version — the truth, and exactly the case to catch. The installer's
   console banner is the only witness that an upload happened.

## Verification (QC-1)

- Red first: `/launch` and `/` RED (no version in the visible text), `/settings` GREEN — a probe on
  the pristine tree. After: `tests/web/test_version_chip.py` 4 passed (placement after the CUI bar
  and the drawer and before `<div id=sfBoot>`, exactly once; the header chip after `</h1>` on `/`,
  `/settings`, `/help`; the probe value flows to both surfaces; the CSS label and `data-no-i18n`);
  `tests/web/test_version_chip_browser.py` 8 passed — console / daylight / apollo / jarvis at
  1,440 and 900 px: both chips laid out with `w, h > 0`, the launch line's top at or below the CUI
  bar's bottom, the header chip inside the header's box and not left of the brand, the `::before`
  label rendered, and the document's scroll width IDENTICAL with the chip hidden (no sideways
  scroll added). One instrument fixed by its own red: the placement pin first anchored on
  `id=sfBoot`, which matches an earlier substring in the head; it anchors on `<div id=sfBoot>` now.
- **Mutation battery, 5 mutants on a shadowed copy — 5 / 5 RED by name** (control 4 passed): the
  launch line dropped · the header chip dropped · the version a literal `"1.0.262"` · the header
  chip translatable (`data-no-i18n` dropped) · the launch line moved below the boot stage.
- The monolith-split contract fired on the new public name (`chrome.py defines names web.app does
  not re-export: ['tool_version']`) — re-exported, 71 passed. Both ruff binaries, `ruff format
  --check`, mypy strict, bandit, `node --check` clean; installers 68 passed on the rebuilt wheel.
  The full suite and `-m parity` on the final head: the SESSION-LOG follow-up with the PR number.

## Deliberately NOT done

- A version on exports / print (the header never prints by design; §6's marking is the export's
  chrome) — its own unit if asked.
- A "what is installed on disk" probe (a second interpreter, the venv's metadata): the running
  process IS the installed program in the desktop-icon deployment; the nuance is stated, not built.
