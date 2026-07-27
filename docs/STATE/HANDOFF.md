# Handoff — 2026-07-27b (AXIS-TITLES batch 0: one caption convention; v1.0.104; highest ADR 0298)

> ## STATUS (current) — AXIS-TITLES batch 0 SHIPPED. Version **1.0.104**. Highest ADR **0298**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `3c0f098` after PR
> #443 / ADR-0297 squash-merged).
>
> - **ADR-0298 — `SFChartFrame.axisTitles` is now the ONE axis-caption implementation.** The tree
>   had TWO (`performance.js` local pair at 9px; `scatter.js` centred-X + **rotated** Y at 11px)
>   and 28 uncaptioned chart modules. Both are retired into the shared helper; `rotate(-90` is now
>   absent from every module. Size comes from **`--sf-fs-axis-title: 11px`** in `base.css` via
>   `.ch-at` — no chart sets a number, so the queued CRISPNESS floor moves ONE value.
> - **⚠️ THE SPEC HAD FIVE FALSE PREMISES — all verified before implementing. Do not trust
>   `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` unchecked:** (1) `SFChartFrame.text` **does not
>   exist** (chartframe exported `{frame, scan}` only); (2) **no type/font tokens existed** —
>   `var(--sf-fs-label)` / `var(--sf-font-mono)` would resolve to nothing (`sf-themes.css` is
>   colour-only); (3) **`scatter.js` already had an X caption** — the spec says "Y only … gains the
>   X caption it never had"; (4) **`gantt.js` renders HTML, not SVG**, so the spec's "a Gantt is not
>   exempt, both axes get captions" is impossible with an SVG `<text>` helper — and 11 further
>   modules in its §3 table render no SVG at all; (5) its §7 golden SHAs are stale (pre-ADR-0296)
>   and §6 points at `docs/UI-INVENTORY.md`, which lives in `00_REFERENCE_INTAKE/`.
> - **The guard is a LEDGER, not the spec's regex** (which under-detected by half — missed
>   `path.js`/`resources.js`, silent on every HTML visual). `tests/web/test_axis_titles.py` puts
>   every non-exempt module in exactly ONE bucket: captioned · **`PENDING` (16 real SVG charts left
>   — this list shrinking to empty IS the completion signal)** · `NO_SVG_AXES` (11 DOM visuals the
>   SVG helper cannot serve). A NEW unclassified module FAILS the test.
> - **The guard was PROVED to bite — 6 mutants, each caught by its intended assertion.** One is
>   worth remembering: an earlier, narrower size assertion sliced from `function axisTitles` and
>   **missed** a numeric `font-size` planted in the node builder just above it. Widened to the whole
>   caption block. Also: `git checkout --` to undo a mutant **wiped a legitimate uncommitted edit**
>   (performance.js) — use file backups for mutation testing, never git checkout.
> - **Visible change is exactly 5 captions** (3 perf: 9px→11px + uppercase; scatter X: centred→
>   right-aligned; scatter Y: rotated→horizontal). No plotted value, scale, domain, tick or payload
>   touched — the three dashboard golden SHAs are unchanged.
> - **Gate:** full suite **2,704 passed**; ruff/format/mypy-strict/bandit/node clean; wheel + 9
>   installers at **1.0.104**. `00_REFERENCE_INTAKE/UI-INVENTORY.md` corrected (3 rows + a
>   verified-corrections note).
> - **OWED, NOT CLAIMED:** the DESIGN-SYSTEM DoD's "renders correctly in all 4 themes + 90-125%
>   scale" needs a browser and this sandbox has no automation for it (prior Chromium checks were
>   manual). Structure/styling hooks are covered by the static + node layers; **the four-theme
>   visual pass is outstanding** — `text-transform` on SVG `<text>` is the property to eyeball.
> - **NEXT:** AXIS-TITLES batches 1-5 — drive `PENDING` (16) to empty, ~5 modules per PR, each
>   passing `xLabel`/`yLabel` per the spec's §3 table (its captions are sound; only its premises
>   were not). Then **CRISPNESS 11px floor** ONLY, no vendored fonts (⚠️ its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE) — note `--sf-fs-axis-title` is already the seam.
>   Then GUIDED-MODE (5 decisions) + VOICE-DECISION (4), parked on the operator. Also open: split
>   phases 2-3 (`web/chrome.py`, then per-page helper modules); a DOM caption mechanism for the 11
>   `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe's UI surface
>   (ADR-0293).
> - **DEPLOY NOTE:** the operator has **no local clone** — download `installer/install-tier2.ps1`
>   from the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
