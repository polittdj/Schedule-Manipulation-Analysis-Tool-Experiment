# ADR-0440 — The Timescale config loaded from localStorage unvalidated: a persisted garbage Size zoomed every Gantt 0.01×–6000× with zero errors, and a garbage tier unit crashed the render

- **Status:** Accepted
- **Date:** 2026-08-27
- **Context:** POLARIS² audit campaign WP0 (docs/STATE/AUDIT-2026-08-27.md, Phase 0) — the
  operator's live-defect report on installed v1.0.221: /path, /driving-path, /evolution,
  "controls do nothing" + "renders wrong".
- **Extends/relates:** ADR-0186/0332 (persist.js deliberately exempts the Timescale key from
  Reset-view and the launch wipe — preferences survive; that exemption is what lets a poisoned
  config outlive every reset the operator can reach) · ADR-0304 (the measured-box standard the
  new suite drives under).

## Context

The MS-Project Timescale dialog (`static/timescale.js`) persists its config per browser in
`localStorage["sf.timescale.v1"]`. Three facts combined into the defect surface:

1. **The load path merged persisted values with only a null-check** (pre-fix `:60-77`): any
   type, any range, any enum value entered `CFG` verbatim.
2. **The 25–1000 Size clamp existed only on dialog EDITS** (`numberInput`'s input listener) —
   never on load. `sizeFactor()` is `(Number(CFG.size)||100)/100`, and every consumer
   (`app.js:477-480`, `path.js:158-160`, `driving_path.js:65-67`, `path_evolution.js:158-160`,
   `sra_grid.js:27`) guards only non-positive factors.
3. **persist.js exempts the key from every wipe by design** — so the state is durable, invisible
   to a fresh-profile probe, and unreachable by Reset view.

A 13-cell × 3-page reproduction matrix (Playwright, real Chromium, state seeded via
`context.add_init_script` because timescale.js reads storage at script PARSE time; TP4
five-version corpus, target 26; oracles: pageerror count, sane geometry, and a Tier-2 measured
control effect; the A0 baseline row passed all three pages before any hostile cell was trusted)
measured, pre-fix:

| seed | measured effect (all with **zero** console/page errors) |
| --- | --- |
| `{"size": 1}` | factor 0.01 — /path track collapses to its 120px floor, every task bar at the 2px floor; doubling the Zoom slider moves the widest bar 2→8px; /evolution zoom 2→3px. **Both reported symptoms.** |
| `{"size": 100000}` | factor 1000 — tracks measure 476,000–1,056,000px; the viewport shows one giant band; zoom clicks change nothing perceptible |
| `{"size": "600000"}` (string) | Number() coerces downstream → factor 6000, tracks 2.85M–6.34M px |
| `{"size": 24}` | factor 0.24 — degraded (track floors), mild: the 25 floor is the right clamp bound |
| `{"top": {"units": "bogus", …}}` | **crash**: `Cannot read properties of undefined (reading 'fn')` in `tierBands` — /path and /driving-path lose the whole Gantt; /evolution's `.catch` (`path_evolution.js:515`) swallows it into a misleading "Failed to load the path-evolution data." |

The crash has a distinct mechanism worth naming: `tierBands` guards units with
`UNITS[tier.units] || UNITS.months`, but `labelDef` indexed `LABELS[units] || []` and returned
`defs[0]` → `undefined` → `.fn` throws. Two lookup tables, one fallback.

Corrupt JSON, garbage `show`, persist.js replay extremes, and the single-version/no-target data
states were all probed and did **not** reproduce (see the audit ledger's full matrix).

Whether the operator's machine actually holds such a persisted state is **unverifiable from this
side**; the ledger carries the three-line operator ask (screenshot · console errors ·
`localStorage.getItem("sf.timescale.v1")`). The unclamped load path is a confirmed defect in its
own right regardless — the dialog's own floor/ceiling, applied only sometimes, is a broken
invariant.

## Decision

Sanitize on the load path (`loadPersisted()` in timescale.js, moved below the UNITS/LABELS
tables it validates against — nothing reads `CFG` before they exist):

- **Ranges coerce-then-clamp**: `size` → [25, 1000] (the dialog's own bounds; a wild number
  keeps its direction and lands on the nearest legal bound); tier `count` → [1, 999], floored.
  Empty strings and non-finite values keep the default (Number("") is 0, not a choice).
- **Enums must be members or the field keeps its default**: `show` ∈ {1,2,3} (coerced first, so
  a stringified legal value still loads), `fyStartMonth` ∈ integers 0–11 (a month INDEX outside
  the calendar identifies nothing — it rejects rather than clamping to an arbitrary December),
  tier `units`/`label`/`align`, nonworking `draw`/`pattern`; nonworking `color` must match the
  dialog's own `#rrggbb(aa)` shape before it reaches CSS gradient/background strings.
- **Healing is in-memory** — idempotent per load; the stored value heals on the operator's next
  OK. No write-on-load churn.
- **`labelDef` gets the same months-fallback `tierBands` already had**, so the crash class is
  dead even for a future unvalidated path (two tables, one fallback, now actually true).

New suite `tests/web/test_timescale_dialog_browser.py` (M2, 16 tests, ~37s, auto-joins CI's
browser job via `tools/browser_modules.py`): the dialog's first-ever behavioral coverage
(open/tabs/preview, OK-commits-measured-on-the-page-behind, Cancel-discards, Reset-restores,
Escape, persistence + cross-page) plus the load-path hardening pins, including the A1/A2 matrix
cells committed as FAIL-side tests.

## Verification (QC-1)

- **Red first**: all 8 hardening tests observed to fail on the pre-fix tree, each on the defect
  it names (`assert 1 == 25` · `assert 100000 == 1000` · `'600000' == 1000` · `'bogus' ==
  'years'` · `assert 0 == 3` · "bars still at the floor: 2" · track `670000`).
- **Green**: 16/16 post-fix.
- **Mutation battery, red by name**: size clamp removed → 6 tests red; tier sanitize bypassed →
  hostile-tier test red on the units assert *while the labelDef belt still prevented the crash*;
  belt ALSO reverted → red on the crash channel with the exact original pageerror text; show/fy
  passthrough → its test red. Seed vacuity is excluded by the pre-fix reds (a vacuous seed
  cannot produce `assert 0 == 3`).
- **End-to-end**: the matrix probe re-run on the fixed tree — catastrophic cells heal on all
  three pages (A2: tracks 4,750–10,560px, live controls); A1/A3 heal to size 25, whose measured
  geometry equals the dialog's own legal 25% (track 120, factor 0.25, measured separately).

## Consequences

- An operator with a poisoned persisted config gets a working tool again on first load of this
  build, with no manual storage surgery.
- The dialog opens showing the healed value (the Size input reads 25/1000, not the garbage), so
  the state is visible and correctable.
- The load-path contract is now pinned by a browser suite that did not exist before; the
  Timescale dialog moves from zero behavioral coverage to 16 driven behaviors.

## Deliberately NOT done

- **The legal 25% floor look** (/path track floors at 120px at Size 25) — the dialog's own
  smallest choice renders identically; a defect row would be wrong. Logged in the audit ledger
  as a UI-map observation for WP1.
- **`path_evolution.js:515`'s misattributing catch** ("Failed to load…" for a RENDER crash) —
  with B2 fixed there is no known way to reach it; reported in the ledger, unrepaired (the
  `citations.reattach`-pin shape: measured unreachable, latent).
- **Write-back healing on load** — rejected to avoid a storage write on every page parse; the
  next OK persists the healed config.
- **/driving-path's empty-corridor opening on TP4** (v5 has no corridor for 11→26; the page
  offers no "step back" hint) — correct data, UI-map candidate, not a defect.
