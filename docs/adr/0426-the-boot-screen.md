# ADR-0426 — The Boot Screen: the prototype's launch sequence, with real numbers on it

**Status:** Accepted · **Date:** 2026-08-17 · **Amends:** ADR-0328 (Boot Audio Hum), ADR-0349
(chrome split) · **Ships:** `web/launch.py`, `web/static/launch.js`, `web/static/launch.css`,
`web/chrome.py`, `web/app.py`, `launcher.py`

## Context

The Mission Ops v2 prototype (the MERLIN deck) opens on a full-bleed particle lightshow: four hero
scenes that morph into one another, a **BEGIN LAUNCH SEQUENCE** control, a staged transit with
telemetry, and a welcome panel that hands the operator into the deck.

The repo shipped **`static/launch_audio.js` and nothing else** — ADR-0328's synthesized Boot Audio
Hum, which rides the *load overlay*. That is the sound of a boot sequence with no boot sequence
attached. `DESIGN-GAP-2026-08-17.md` filed it as gap #9:

> **Boot / launch sequence** — The repo ships only `static/launch_audio.js` (the ADR-0328
> generative hum). The deck's particle canvas, Hohmann transit, telemetry and welcome screen are
> absent.

The operator's report was blunter: *"there is no launch screen with the animations."*

**A naming collision to keep straight.** ADR-0328 calls the load overlay "the Launch Sequence".
This ADR's subject is the **startup screen**. They now share one audio module and nothing else.

## Decision

Serve the boot screen at **`GET /launch`**, and point the launcher's browser-open at it.

### It is deliberately not a `_page`

Every other route returns through the story chrome — header, nav rail, chapter kicker, Continue
footer. All four are wrong here: a startup screen that renders a nav rail is a dashboard with a
picture on it. `/launch` is the **only** route that builds its own document.

That is also precisely where compliance chrome silently stops rendering, so the two pieces §6
requires are kept and are **provably the same ones**:

- both CUI marking bars, from the same `_cui_marking(state)` derivation `_page` now uses;
- the compliance drawer, from a new `_compliance_drawer(state)`.

`_LAYOUT` previously carried the drawer's ~20 lines of regulatory prose inline. It now renders
`{{ drawer }}` from that same function, so there is **one** copy of the CUI/ITAR/EAR notice in the
tree. `test_the_drawer_on_the_boot_screen_is_byte_identical_to_the_shell` asserts equality of
bytes, not presence — a presence check passes forever while two copies drift apart.

### Nothing on the screen is a fabricated number

The prototype's telemetry tiles count `225.4 M km` down to zero and tick off `0 / 14 COMPLETE`.
Nothing computes either. The design system's numbers rule — *every displayed number traces to the
engine payload; missing values show `—`, never a fabricated figure* — has no cinematic exemption,
so the tiles were re-cut to three facts the session can actually supply:

| tile | source | empty session |
|---|---|---|
| SCHEDULES ABOARD | `len(state.schedules)` + summed `len(sch.tasks)` | `— nothing aboard` |
| NEWEST DATA DATE | `max(status_date)` across loaded files | `—` |
| SEQUENCE | the stage LABEL | `PRE-FLIGHT` |

The stage labels (`IGNITION`, `CRUISE`, …) stay, because a label claims nothing. A count that is
unknown renders the em dash and never `0` — "nothing loaded" is unknown, not zero.

The route reads only what is already in memory. **No CPM pass**: a boot screen that solves seven
networks before it can paint is not a boot screen.

### Four ports where the prototype could not be copied

1. **No inline handlers.** The deck wires everything with `onClick=`; the strict `script-src
   'self'` CSP (ADR-0268) forbids it. Every control is bound in `launch.js` by id or
   `data-sf-boot-*`, and the session facts arrive as a non-executable
   `<script type="application/json">` block.
2. **Reduced motion is a STILL frame, not a BLANK one.** `prefers-reduced-motion` composes exactly
   one frame and never re-arms the loop; BEGIN lands straight on the welcome panel instead of
   holding the operator for seven seconds. "Honours reduced motion" is usually implemented as
   "renders nothing", which is a different and worse product — the chromium test asserts both
   halves (`> 5000` lit pixels **and** a frozen `requestAnimationFrame` counter).
3. **The ground stays dark in every theme — the one deliberate departure from the theme.** The
   lightshow is an **additive** particle field: it works by adding light to a dark ground. On
   daylight there is no equivalent. The first daylight render was measured, not guessed, and it
   was a grey smear with the theme's dark ink unreadable on top of it. So the boot stage carries
   its own surface (`--boot-ground` / `--boot-ink` / `--boot-muted` / `--boot-line`), declared in
   `launch.css`, which only `/launch` loads. The four themes still differentiate: the particles
   are coloured from `--boot-accent` / `--boot-warm`, which resolve to the theme's `--accent` /
   `--warn` for the three dark views. daylight alone re-points them, because its accent is a deep
   blue chosen for white paper and reads as nothing at all as emitted light.
4. **The particle budget scales with the surface.** The prototype's 15,600 is treated as a ceiling
   (`area / 78`, floor 4,200), so a laptop pane and a wall display both hold frame rate. The
   prototype's bucketed draw is kept verbatim and is the reason this is viable at all: particles
   are binned by quantized colour into preallocated flat arrays and counting-sorted, so the loop
   emits one `fillStyle` per non-empty bucket instead of ~15,600 rgba string allocations a frame.

### The opt-out never flashes

`sf-boot-skip` is read **at parse time** in the head-loaded module, before the canvas is laid out,
and the page `location.replace("/")`s. A boot screen the operator dismissed must never appear for
a frame on the way to being dismissed. `?replay=1` reopens it — an opt-out must not be a one-way
door.

The launcher opens `{url}/launch`; every other link, bookmark and printed URL still points at the
deck root. The boot screen is reachable once per launch and never gets between the operator and a
page.

## Verification

`tests/web/test_boot_screen.py` (15, content) + `tests/web/test_boot_screen_chromium.py` (16,
behavioural). The content guards were mutation-proven in a sandbox copy at
`/home/claude/sandbox` — the tree under measurement was never mutated, and the sandbox was
sha256-verified back to its pristine state after the run.

| mutant | expected red | result |
|---|---|---|
| M1 drop the bottom CUI bar | marking guard | red |
| M2 hand-edit a second drawer copy | byte-identity guard | red |
| M3 print `0 files · 0 activities` instead of the em dash | numbers-rule guard | red |
| M4 point a quick action at a route that does not exist | route-exists guard | red |
| M5 hard-code the prototype's cyan ramp | palette guard | red |
| M6 re-arm the frame loop under reduced motion | reduced-motion guard | red |
| M7 launcher opens the deck root again | launcher guard | red |
| M8 drop the compliance drawer | `test_hud_layer` drawer sweep | red |
| M9 render the story nav on the boot screen | story-chrome guard | red |
| M10 defeat the skip short-circuit | opt-out guard | red |
| M11 paint one frame and freeze the loop | animation guard (chromium) | red |

**The first run of that battery reported 6 of 10 SURVIVED, and the harness was the defect.** The
sandbox's tests were importing the *installed* package from the real tree, so every Python
mutation landed on a file nothing under test was reading; the four JS/launcher mutants passed only
because those guards read files by path. The harness now probes
`schedule_forensics.web.launch.__file__` and refuses to run unless the subject resolves inside the
sandbox. This is the repo's own standing lesson — *a mutant that misses its subject proves
nothing* — reproduced in the instrument rather than in the guard, which is the harder place to
notice it. It is also why "6 survivors" was not reported as a finding: an unverified instrument
produces testimony, not evidence.

**`ruff` caught a no-op assertion I wrote.** The first version of the "the scene keeps moving"
check ended `assert frame_b == frame_a2 or True` — always true, incapable of failing, and sitting
inside a test whose name promised the opposite. SIM222 flagged it. It is now a real claim (two
canvas samples ~900 ms apart must DIFFER) and M11 proves it goes red when the loop is frozen.
Worth recording because it is this repo's single most-repeated defect class appearing in the very
commit whose ADR describes guarding against it — and because the linter, not the reasoning, is
what found it.

**ADR-0418's brand-new guard caught this ADR's own test file.** `test_boot_screen_chromium.py`
was first written pinning `/opt/pw-browsers` with a `skipif` — which is precisely the defect
ADR-0418 had just removed from 24 modules holding 94 never-executed browser tests. This branch was
cut before that landed, so the pattern was copied from a module that still had it.
`tests/guards/test_browser_resolver.py` went red on the rebase and the file now uses the shared
`web.browser_chrome.chrome_kwargs()`. Worth recording as evidence for the guard rather than
against the author: a computed census caught a regression written by someone who had not yet read
the ADR that forbade it, which is the only kind of enforcement that actually scales.

Three defects were found by the tools rather than by reading:

- **The bottom CUI marking bar fell off a 720px viewport on apollo** (measured at 1180×720, where
  the uppercase mono type is tallest). `min-height: 100vh` let the stage grow past the fold and
  push the marking off-screen. Now `height: 100vh` with the stage absorbing overflow, so the bars
  are laid out rather than overlaid and cannot move. The chromium guard measures
  `getBoundingClientRect()` for both bars against the canvas in **all four themes at two
  viewports** — a class read-back would have proven nothing (ADR-0305's lesson).
- **`page.wait_for_function` throws `EvalError` against this app**, because its predicate is
  injected as a string and the CSP refuses `unsafe-eval`. The test polls through `evaluate()`
  instead. The CSP biting an instrument is the air-gap working; the test bent, not the policy.

## What this does NOT do

**The MERLIN wordmark is not applied.** The deck's welcome panel reads "Hello and welcome back to
Merlin" and carries the falcon etymology; this screen says "Welcome back." and the document title
stays `— POLARIS`. Renaming the product is an operator-level decision touching an ADR-0175
wordmark and every page in the tree, and it does not belong smuggled into a launch-screen commit.
Gap #10 stays open.

The deck's Hohmann-transfer orbital diagram is also not ported: the transit renders as the warp of
the existing particle field plus the stage ledger, not as a second illustrated scene.
