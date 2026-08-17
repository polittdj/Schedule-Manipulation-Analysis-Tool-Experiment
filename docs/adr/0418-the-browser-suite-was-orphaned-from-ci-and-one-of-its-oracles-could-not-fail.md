# ADR-0418 — BROWSER-ORPHAN-01: 94 browser tests never ran, and one oracle could not fail

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** BROWSER-ORPHAN-01 (audit 2026-08-16) ·
**Extends:** ADR-0406 (runner-compatible chromium), ADR-0331 (the caption halo), ADR-0360 (the
fetch+blob export) · **Ships:** tests + `.github/workflows/ci.yml` only — **no runtime code
changed**, so no wheel/installer rebuild (ADR-0148) and no version bump.

## Context

ADR-0406 diagnosed a defect in `tests/web/test_r11_panel_contract.py`: pinning the dev container's
vendored chromium and skipping when it is absent is not a browser-availability check, it is a
*this-container* check. On a GitHub runner `playwright install chromium` writes to
`~/.cache/ms-playwright/…`, so the pinned `/opt/pw-browsers` was missing, every test in the module
SKIPPED, and the job went green in 59 seconds having proved nothing.

**That fix reached exactly one module.** The kickoff recorded the residue as "four browser test
modules never run in CI". That count was wrong, and the correction is the reason this ADR is large.

## What was actually true

A computed census — matching the LAUNCH call, not the word "playwright" — finds **24** modules that
drive a browser. **23** of them pinned `/opt/pw-browsers`; only ADR-0406's own module resolved
properly. Measured by bind-mounting an empty directory over `/opt/pw-browsers` inside a mount
namespace, which is a runner-shaped filesystem:

| filesystem | result |
| --- | --- |
| runner-shaped (`/opt/pw-browsers` empty) | 86 passed, **94 skipped** |
| this container (vendored chromium present) | 175 passed, **5 failed** |

So **94 browser tests never executed in either CI path** — the `test` matrix installs no browser
(`playwright` lives in the `browser` extra, not `dev`), and the `browser` job named a single module
by hand. Five had been failing the whole time, under a green badge.

## The five failures — two unrelated causes, neither one an "assertion to loosen"

### Four `⤓ EXCEL` download assertions were pinning a superseded mechanism

`assert expected_path in download.url` fails on a **working** button. ADR-0360 deliberately stopped
navigating to the export: the button now `fetch`es (so it can hold a PREPARING state through a
server-side re-run measured at 140 s, instead of reading as dead) and hands the browser a
same-origin blob via `URL.createObjectURL`. `download.url` is therefore
`blob:http://127.0.0.1:PORT/<uuid>` and can never contain the export path, while
`suggested_filename` is correct (`bow-wave-cei.xlsx`).

The tests' own docstring states the property they meant to hold — *"the ⤓ glyph is wired AND its
endpoint is live"* — so the repair asserts that, on the **network**, rather than deleting the check:
the export path was really requested. That is stronger than the string it replaces, and
mutation-measured: pointing the fetch at an unrelated URL still yields a `.xlsx`-named blob download
that the old shape would have been satisfied by in the pre-ADR-0360 world, and only the new
assertion notices.

The accompanying `status == 200` check is documented as **secondary, not load-bearing** — measured
against a deliberately dead (500) endpoint, the failure surfaces as the download wait timing out,
because a non-ok response throws before any blob is made. Recording that is the point: an assertion
that reads as load-bearing while being practically unreachable is the defect class this repo keeps
paying for.

### The histogram legibility oracle returned the same verdict in both worlds

This one is the opposite of a stale assertion, and it is why "loosen it" would have been wrong.

`test_the_degenerate_single_bin_histogram_is_still_legible` scored the `Finish date` caption at
**1.17:1** against a 3.0 floor — exactly the number its own docstring attributes to *"without the
halo"*. The obvious reading is that ADR-0331's halo had been lost. **It had not.** Measured:

- computed style on every caption is `paint-order: stroke`, `stroke: rgb(255,255,255)`, `3px`;
- rendered at true 1× and magnified losslessly, `FINISH DATE` is plainly legible, each glyph
  carrying a white halo over the blue bar;
- stashing the halo moves pure-white pixels in the clip from **17.6% to 1.3%**, so it is painting.

The defect was in the **oracle**. `_modal_color` takes the mode of the caption's whole box, on its
own stated premise that "glyph strokes are sparse relative to the box they sit in, so the mode is
what the eye reads the text against". That premise holds only while a caption sits on ONE surface.
This caption straddles a boundary — the degenerate one-bin bar fills ~65% of its box — so the mode
reports the box's dominant REGION, which is not the glyphs' backdrop.

The decisive measurement, and the reason this is a defect rather than a tuning quibble:

| oracle | halo painted | halo stashed | discriminates? |
| --- | --- | --- | --- |
| whole-box mode (old) | **1.17:1** | **1.17:1** | **no** |
| glyph backdrop, 1px ring (new) | **3.06:1** | **1.17:1** | yes |

The old check failed a correct render **and could not have detected a broken one**. It was not a
test that had gone stale; it was a test that had never been able to refute its own claim (QC-1).

A second, independent defect sat in the same test: `caps` came from a document-wide `text.ch-at`
sweep while `shots` came only from `#ssiCharts`, joined by caption **text** — which is not unique
(three captions read "Finish date"). Captions were therefore scored against another caption's
pixels, which is why one straddling caption reported as three failures. Probing and screenshotting
the same element handle makes that class unrepresentable rather than merely fixed.

## Decision

1. **One resolver, `tests/web/browser_chrome.py`.** Prefer a vendored binary (offline containers
   have no download), else return NO `executable_path` and let playwright resolve its own — the
   branch a runner takes, and the branch the 23 modules could not take. All 23 repointed; the
   `CHROME.exists()` skips are gone, so a missing browser now fails loudly instead of skipping.
   Import spelling is `from web.browser_chrome import …`, verified under **bare** `pytest` from two
   working directories, because `from tests.web.…` is what killed three CI jobs at once before.
   `tests/perf/` has no package parent and loads it by path.
2. **CI computes its browser population** via `tools/browser_modules.py` and feeds it to pytest, so
   a new browser module is covered the day it lands. A hand-listed set is what orphaned 23 modules.
3. **The skip-is-a-failure guard now covers the whole set**, not one module.
4. **`_glyph_backdrop`** replaces the whole-box mode for the straddling case, and the degenerate
   test pairs probe-to-screenshot by element handle. Its measured population is floored at 5 so the
   sweep cannot silently shrink.

## Verification

- **Red first.** The CI-coverage guard was written before the workflow changed and failed by name,
  listing all 23 orphaned modules.
- **Mutation, 7/7 by name**, each mutation confirmed to have LANDED before its verdict was believed:
  reintroduce a pinned path · CI stops computing the census · resolver pins instead of deferring ·
  the two censuses diverge · and three separate ways to break the skip guard (weaken its pattern,
  drop its `exit 1`, delete the step). An eighth "survived" verdict was a battery defect — a `sed`
  whose delimiter collided with the pattern, so the mutant never landed — and it exposed a genuinely
  weak assertion of mine (`or "SKIPPED" in ci`), which was replaced.
- **The repaired histogram test goes red when the halo is stashed** (1.17:1) and green when restored,
  with `git diff` confirming the CSS was returned to baseline. It now also catches a second caption
  the old oracle missed in both worlds.
- **Behaviour preservation:** the 23 migrated modules ran **175 passed / 5 failed** before the
  repoint and **175 passed / the same 5 failed** after it (measured as 200/5 with
  `test_r11_panel_contract.py`'s 25 tests added to the set), so the repoint changed no outcome. With
  both repairs in, the computed census is **210 passed, 0 failed, 0 skipped** — the first time this
  set has been green.

## The first CI run closed the runner leg — and surfaced two MORE orphans

The `browser` job's first run on this branch downloaded chromium 1234 into
`~/.cache/ms-playwright`, printed the 24-module census, and reported **203 passed, 0 skipped**.
That closes the UNVERIFIED leg above **positively**: `chrome_kwargs()` returned `{}`, playwright
resolved its own browser, and modules that had never executed on CI executed.

It also failed 2 tests — `test_float_tip_dismiss` and `test_float_tip_scroll`, both timing out
waiting for a focus-shown `.dcma-tip-float`. So the un-orphaning surfaced **seven** pre-existing
failures in total, not five. Same class, same cause of invisibility.

**A correction to this ADR's first reading of them.** They looked runner-specific — they passed in
this container and failed on the runner, and the obvious suspect was the chromium build (1194 vs
1234, unreproducible here because the egress proxy blocks `cdn.playwright.dev`). That was wrong.
Instrumented and re-run in a loop, the scroll test fails **8 times in 20 locally**. The local passes
were luck, and "it only fails on CI" was a conclusion drawn from a sample of one.

Three hypotheses were measured and **refuted** before the real one was found: the headless shell
(pointing the resolver at the vendored `headless_shell`: both still pass), a missing `tabindex`
(it is unconditional), and `focus()` scrolling into the document-level scroll-hide (`scrollY` moved
0px in all four in-view × `preventScroll` combinations).

**The actual mechanism, recorded rather than reasoned:** a probe logging scroll events and
tip-visibility transitions caught it in the act —

    TIP-SHOWN at 55ms → scroll at 57ms → tip-hidden at 67ms      (fails)
    scroll at 70ms → TIP-SHOWN at 85ms                            (passes)

`scroll_into_view_if_needed()` delivers its scroll event **asynchronously**, 57–70ms after the call
returns. The product hides tips on scroll *by design* — the scroll test's own docstring calls that
a FACT — so focusing immediately races the late scroll event, and when the focus-show wins the race
it is promptly wiped by the loser. Nothing about the product is wrong.

Fixed by settling: `settle_scroll()` waits for scroll quiescence before focusing, so the focus-show
always lands after the scroll. Quiescence rather than a flat sleep, because the delay is
machine-dependent and a constant tuned on this container is precisely the timing pin that fails on a
slower runner. Measured: **12/20 → 20/20**. The assertion is unchanged; only the setup race is gone.
`wait_for_tip()` also now reports the state at timeout (did focus land, does the row have a box,
what each tip's `display` says), because this failure had to be diagnosed on a machine no debugger
can reach — proven to fire by deleting the focus listener.

## Consequences

The `browser` job grows from one module to 24 (~6 min of tests). That is the cost of the requirement
being real. `src/` is untouched: this ADR ships tests and a workflow, so no wheel or installer is
rebuilt and the version stays v1.0.211.

**What this does NOT settle.** The runner branch is proven here only to the point of handoff —
`chrome_kwargs()` returns `{}` and playwright takes over. That playwright then finds a browser on a
GitHub runner is proven by CI's existing `browser` job, which has been green through exactly that
branch with a skip-is-a-failure guard; it is not re-proven locally, because this container's
`PLAYWRIGHT_BROWSERS_PATH` points at the vendored root and the vendored build (1194) does not match
the pip driver's expectation (1234). The first CI run of this branch is what closes that leg.
