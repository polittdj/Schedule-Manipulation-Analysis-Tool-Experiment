# ADR-0443 — WP2 (M3 + M5): the steppers and page chrome are DRIVEN, and five controls that were dead, racing or misrouted are fixed

- **Status:** Accepted
- **Date:** 2026-08-31
- **Version:** 1.0.225
- **Supersedes / extends:** ADR-0442 (WP1 census — this discharges every `WP2:M3` deferral it
  carried and settles the `/mission` design question it logged), ADR-0275 (the Play-all
  coordinator, which this ADR found was registered on exactly one of the three pages that use it),
  ADR-0268 (`data-sf-nexturl-submit`, the idiom the language form was never moved onto).

## Context

WP1 censused every interactive control the app serves and proved each one **exists**. Forty-seven
id'd steppers/autoplay controls plus 138 id-less `sf-frame` trio buttons were censused with an
explicit `WP2:M3` deferral, and the wall's 30-chart-hosts-against-9-chartframe-bars gap was logged
as a `WP2:M5` design question. WP1's own headline lesson was that presence is not function: its
first driver run found column-resize grips that had been **7×0px** for months under passing
byte-pins, and a sticky scrollbar that tracked content only when a fetch happened to win a race.

The steppers were in exactly that position. `tests/web/test_trends_animation.py` pins them by
BYTES — it greps the served JS for `sf-frame-prev` and for the string `prefers-reduced-motion` —
which certifies that the source contains those characters and nothing about whether a click moves
a chart. Nothing had ever driven them.

## Decision

Two new browser modules drive every one of those controls and measure the effect, and the five
defects the first runs found are fixed.

**The clock is driven, never slept on.** Autoplay runs on 1100–1800 ms timers; a wall-time wait
would make the module a multi-minute race, and this repo has already paid for a test that passed
at 1500 ms and failed at 1200 ms. Every autoplay assertion advances Playwright's fake clock by
exactly one interval. The instrument is pinned not to perturb the artifact:
`test_the_fake_clock_does_not_perturb_the_page` renders `/cei` with and without fake timers and
requires the two digests to be identical.

**Two oracles per control, and both are required** — the label the stepper rewrites AND a digest
of the chart it repaints. A control that flips its own caption while the visual behind it stands
still is the WP0 defect class, and a label-only assertion would certify it. The digest is
deliberately DOM-shape-agnostic: `/evolution` and `/driving-path` paint HTML-table Gantts and
`/trend`'s quality drill paints into `#qualBars`, so an SVG-only digest reported three false
"chart did not move" rows on the first probe — a wrong oracle, not a defect, and recorded here as
such. `test_chart_digest_is_stable_and_sensitive` pins that the digest holds still across a no-op
and moves on a real step; without that, every "chart moved" assertion is unfalsifiable.

### The five defects (all CONFIRMED-FIXED, red-first)

| row | verdict | measurement |
| --- | --- | --- |
| **M3-01** `/mission`'s wall master was never registered with the ADR-0275 coordinator | **CONFIRMED-FIXED** | The layout emits `chartframe.js` (which defines `window.SFPlayAll`) AFTER `<main>`; measured DOM script indices put `mission.js` at **20** and `chartframe.js` at **24**, so `mission.js:76`'s `if (window.SFPlayAll)` guard was always false and skipped registration in silence. Asked of the registry directly, `SFPlayAll.stopAll()` did nothing; driven by hand, a real click on a chart's own control left the wall playing — the exact "hit stop, it kept playing" symptom ADR-0275 was written to eliminate. Registration is now order-independent: early callers queue their `stop()` on a stub and `chartframe.js` adopts `_pending`. |
| **M3-02** `/curves`'s `#sfPlayAll` never called `register()` at all | **CONFIRMED-FIXED** | Zero occurrences of `SFPlayAll` in `curves.js`. Same measured symptom as M3-01. `/trend` was the only page where the coordinator worked, and only by accident — it registers from inside a post-`fetch` callback, by which time `chartframe.js` has loaded. It now uses the same order-independent idiom, so the accident is not load-bearing. |
| **M3-03** `driving_path.js` ignored `prefers-reduced-motion` | **CONFIRMED-FIXED** | The ONLY animated module of twelve with zero `prefers-reduced-motion` handling. Under reduced motion its Play rewound to 1/5 and a 1100 ms timer carried the corridor back to 5/5. Now advances one version and starts no timer, matching its nine siblings. |
| **M5-01** the Mission wall framed 9 of its 30 chart tiles | **CONFIRMED-FIXED** | Settled by measurement, not taste: a manual `SFChartFrame.scan()` on the settled wall took the count **9 → 30**, so the 21 unframed tiles were an attach-vs-fetch race (the UI-02 shape — a one-shot `DOMContentLoaded` scan against async-fetched content), not a design choice. `chartframe.js` now adopts late-arriving hosts via a childList observer. |
| **M5-02** the Language selector always returned the operator to `/` | **CONFIRMED-FIXED** | `/language` derived its destination from `Referer`, and the app sends `Referrer-Policy: no-referrer` on every response — measured absent, and the redirect measured as `/` from four different pages, contradicting the route's own docstring. Moved onto `data-sf-nexturl-submit` + a server-validated `next_url`, the idiom the banner Project switcher already uses and whose comment in `chrome.js` names the no-referrer policy as the reason. |

### The `/mission` design question, decided

WP1 floor-pinned 30 hosts against 9 bars and logged it as a question. It is not one, and three
measurements settle it: (1) a manual re-scan takes the count to 30, so the gap is a race;
(2) `mission.py` marks every tile it wants framed with `chart-host` and the tiles it does NOT
with `chart-note` — "so chartframe.js never adds a dead zoom toolbar" — making the class the
wall's own deliberate switch; (3) the nine existing toolbars were confirmed FUNCTIONAL first
(zoom grew their svg 536 → 670 px), so this restores a working affordance to 21 tiles rather than
spreading dead chrome. The census row moves from `(30, 9, …)` to `(30, 30, …)`.

### The A2 reduced-motion pin was failing open

M3-03 survived because `test_accessibility.py`'s A2 guard checked a **hand-written list of five**
module names while the app shipped twelve animated modules; `driving_path.js` was simply never
typed into it. A hand-derived population under-reports by construction — the lesson ADR-0439 paid
for with a route list, and the reason the WP1 census computes its pages from the app's own route
table. The sweep is now computed from the shipped JS, with a documented EXCLUSION list (pollers
and audio, which animate nothing) rather than an inclusion list, so a new animated module is RED
by default; a second guard fails if an exemption goes stale.

## Proof (QC-1)

- **Red first.** The M3 module was observed at **5 failed / 54 passed** on the unfixed tree, the
  four coordinator failures naming `[mission]` and `[curves]` on both the registry test and the
  end-to-end manual-click test; the reduced-motion failure named `[driving-path]` and was a
  finding the session had not predicted. The M5 module was observed at **3 failed / 5 passed**,
  with theme, page-scale and Task Information passing — i.e. genuinely working already.
- **Green.** M3 59/59, M5 8/8, census 57/57 with the updated `/mission` row.
- **Mutation battery, 15 mutations, every one RED BY NAME**: chartframe stops adopting `_pending`;
  `mission.js` back to the racy guard; `curves.js` loses `register()`; `driving_path.js` loses its
  reduced-motion branch (caught by BOTH the behavioural driver and the computed static sweep); a
  stale A2 exemption; a stepper that captions but never repaints (**the chart oracle, proved
  independently of the label oracle** — `volatility` keeps writing `#volLabel` while `#volChurn`
  stops redrawing, and an `sf-frame` bar that captions without calling `frames.draw()`); a Pause
  that never clears its interval; the coordinator dropping its `isTrusted` check (which would make
  Play-all halt on its own first beat); chartframe dropping the late-chart observer; and the
  language fix broken at the client half, the server half, and its open-redirect guard.
- **A security pin rides with M5-02.** Giving `/language` an operator-supplied destination is the
  classic way to introduce an open redirect, so `tests/web/test_ui_language_redirect_guard.py`
  asserts six hostile payloads all land on `/` and four genuine local paths are honoured. It is a
  route-level test on purpose: no browser, so it runs in the normal suite.

## What CI caught that this session's own green run did not (recorded, not tidied away)

The first push of this work was RED on two CI jobs. Every failure was this change's, and the
chain is worth keeping because two of the three links are process, not code.

**1. A regression introduced by the botched mutation restore (the serious one).** The
`git checkout --` incident above reverted three files to HEAD. Re-applying them, only HALF of
`chartframe.js` went back: the `watchForLateCharts` observer returned, the `_pending` adoption did
not. That left `window.SFPlayAll = window.SFPlayAll || {…}` — so `mission.js`'s stub (which has no
`stopAll`) SURVIVED, and every trusted click on an animation control threw
`window.SFPlayAll.stopAll is not a function`. **Twenty page errors on `/mission`, and strictly
worse than the code before this PR.** The compounding error was mine and is the real lesson: I
re-applied a fix and did not re-run the suite that proved it, so the local "59/59 green" I reported
described a tree that no longer existed. The assignment is now unconditional and commented as
load-bearing, and the mutation battery covers exactly this reversion (`P1`, red by name on both the
coordinator test and the zero-pageerror assertion).

**2. Four byte-freeze pins tripped, and my pre-flight grep for them was too narrow.** I searched
for pin-shaped lines that also NAMED my files and concluded there were none. The pins that fired
hash whole files and enumerate call sites by line number, so they never mention a filename on the
same line — a sweep whose pattern cannot see its subject reports "clean" by construction, which is
the same defect this ADR fixes in the A2 population. Re-baselined deliberately, each with its
reason recorded in place:

| pin | why it moved |
| --- | --- |
| `PAGE_SCRIPTS["driving_path.js"]` | the M3-03 reduced-motion branch |
| `GLOBAL_FORMS` `/language` (391 → 438 bytes) | the M5-02 hidden `next_url` + `data-sf-nexturl-submit` |
| `AXIS_CALL_SITES` line numbers | pure shifts from edits ABOVE six call sites — **every caption md5 verified IDENTICAL first**, which is the benign case the pin itself documents |
| `test_dd_line_ledger`'s `(file, line)` call sites | the same six shifts |

**3. `test_the_autoplay_stepper_pin_is_untouched` pinned the very literal this ADR replaced.** It
froze the five-name `_AUTOPLAY_JS` tuple and asserted `launch_audio.js` appeared NOWHERE in
`test_accessibility.py` — but the hum is now a NAMED EXEMPTION in the computed sweep, so the text
pin could not survive. It was re-expressed against the property it was always protecting (the
launch hum must never be counted an animated module), which is **stronger** than the text pin: it
checks membership of the real computed population rather than a spelling. Mutation-proved both ways.

**4. The embedded wheel went stale.** A late whitespace alignment in `curves.js`/`trend.js` landed
AFTER the wheel and installers were built, so `test_embedded_wheel_is_in_lockstep_with_the_source_tree`
failed on content drift. Rebuild the wheel and the nine installers as the LAST step, after the final
source edit — not when the code "looks done".

**5. The declared playwright floor was false, and this work made it so.** `pyproject.toml` declared
`playwright>=1.44`, but M3 drives `page.clock`, which does not exist below 1.45 — measured, not
recalled: the 1.44.0 wheel's `playwright/sync_api/_generated.py` contains the string `clock`
**zero** times, while 1.45.0 defines both `Page.clock` and `clock.run_for`. Raised to `>=1.45` with
that measurement recorded in the comment. This is the same shape as ADR-0346's `fastapi>=0.110.2`
Law-1 floor: a declared bottom nothing ever installed, and quietly false.

## Consequences

- Every `WP2:M3` deferral in the census is discharged; its driver values are now module-qualified
  (`<module>.py::<test>`) and `test_every_declared_driver_exists` imports the sibling module to
  resolve them, so a renamed or misspelled cross-module driver is RED (both spellings mutation-proved).
- `/mission` gains 84 chartframe buttons (21 tiles × 4). This is the census floor's job and it
  caught the change exactly, which is the intended behaviour, not a surprise.
- The operator's language choice now keeps them on the page they were reading.

## Traps this work paid for

- **`git checkout --` is not a mutation restore.** A battery that backed mutations out with
  `git checkout --` reverted three files to HEAD and silently deleted the very fixes under test,
  which also made one mutation "pass" while measuring unfixed code. Restore from a `cp` of the
  WORKING TREE, and diff the tree after every restore chain — WP1 wrote the second half of that
  rule and this session paid for the first.
- **A wrong oracle looks exactly like a defect.** Three families reported "the chart did not move"
  because the digest only walked SVG; two of the three surfaces are HTML tables. Scope the oracle
  before reporting the finding.
- **Measuring `document.body` to test a page zoom reports a working control as dead.** body is
  full-bleed at every zoom; the heading's own box scales correctly (212 → 265 → 371 → 191 px).
  `#uiScale` was nearly written up as a defect on that reading.
- **A probe's own wait can invent a finding and then retract it.** Reading `page.url` after
  `wait_for_load_state` — before the form's navigation had begun — reported the language selector
  landing on the page it started from. `expect_navigation` measured the truth.
- **The server session outlives a browser context.** Setting the language in one probe step
  translated a later step's page; the language driver restores English in a `finally`.
