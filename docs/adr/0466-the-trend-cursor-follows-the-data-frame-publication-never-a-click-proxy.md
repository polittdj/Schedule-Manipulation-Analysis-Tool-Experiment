# ADR-0466 — The /trend design cursor follows the `data-frame` publication, never a click proxy: the race a runner exposed on a docs-only PR

- **Status:** Accepted — 2026-09-06 (a CI-red wake on draft PR #640 at 2026-09-05 23:41Z)
- **Version:** 1.0.239
- **Extends:** ADR-0460 (the /trend design cursor: "the active chip and the frame pill follow the FIRST framed chart whichever control moved it"), ADR-0275 (the page master and its coordinator), ADR-0442 / ADR-0443 / ADR-0461 (the earlier intermittent cells this repo refused to call flakes), ADR-0393 (QC-1 / QC-2)
- **Shipped:** `static/trend.js` (one block in `sfDesignCursor`), `tests/web/test_trend_design_browser.py` (two tests, NEW; the module's waits as function strings), version 1.0.239, wheel + nine installers

## Context — the red cell, and whose bytes it was

`browser (measured-box proof)` failed on #640's head `914f74ba` in
`test_the_master_step_moves_the_cursor_and_a_single_next_moves_only_its_chart` (line 183):
`stepped["on"] == ['2']` while `frames == [3] * 21` and `qual == 3` — every chart had stepped, the
chip had not. #640 was docs-only: its `src`, `tests`, `pyproject.toml` and `.github` trees are
byte-identical to `main` @ `b8e8aa42` (`30cb40b9…` / `60df5fa7…` / `7c66e78c…` / `08fef405…`), and
`main`'s own browser job on those bytes (run #1743, job 101392932202) went green at 23:38Z, as had
#639's final head before it. So: not this PR's bytes, green on the base — and, by this repo's
standing rule (steward §3), a flake is not a root cause. The mechanism was read, then measured.

**The mechanism.** `sfDesignCursor` (ADR-0460) synced the chips from a document-level click
listener that deferred `syncChips` with `setTimeout(…, 0)`. Every stepper, meanwhile, publishes its
frame **synchronously inside the click** — `show()` sets `data-frame` on the bar it owns
(`trend.js`, `margin.js`) and `render()` sets it on `#qualBars` (`trend_drill.js`). The chip was
therefore one macrotask behind the very attribute the test waits on, and a reader over CDP
(`page.evaluate`) is a separate task the browser may service before the timer queue drains.
**Proven by construction:** a state read inside the click's own task shows `on == ['2']` with every
frame on 3, every time (three probes of three); the next task shows `['3']`.

**What did not reproduce.** The cross-task ordering the runner produced: 0 of 34 local runs read the
chip behind the frames across the CDP boundary — 12 with one browser (unthrottled, then CPU-throttled
10×), 16 with a fresh browser per run under three CPU hogs and 4× throttling, plus the module's own
test ×3. The runner ran Chrome for Testing 151.0.7922.34 (playwright build 1234); the container's
vendored browser is chromium-1194. A scheduler difference between the two is the plausible reason
and is UNVERIFIED. The proof rests on the construction (the gap exists and the fix removes it), not
on reproducing the runner's luck.

**A second defect of the same class** fell out of reading the code before fixing it: a chart's own
▶ Play advances through its interval calling `show()` directly — no click anywhere — so the cursor
followed only Play's FIRST beat, contradicting ADR-0460's "whichever control moved it (a chip,
Prev / Next / Play, the master's programmatic beat)". Measured red before the fix.

## Decisions

### 1. The cursor follows the publication
```js
new MutationObserver(syncChips).observe(document.body, {
  subtree: true, attributes: true, attributeFilter: ["data-frame"],
});
```
replaces the click listener and its timer. A mutation observer's callback runs as a **microtask at
the end of the task that mutated**, so no later task — a CDP reader, the next paint, the interval's
next beat — can see the frames and the chip out of step; and it sees every publication, click or
not, so Play's later beats move the cursor too. `goTo(i)` keeps its own synchronous `syncChips()`.
The class of defect is "derived state driven by a proxy of the control that usually causes the
change, instead of by the publication it derives from"; the proxy misses movements it does not
know about, and a timer puts the derived state one task behind.

### 2. Two tests, red before green, red by name after
- `test_the_cursor_never_lags_the_frames_once_a_step_settles` — clicks ⏭ Step all, then one chart's
  Next, **inside `page.evaluate`**, awaits one microtask and reads the state in the same task:
  frames, drill, chip and pill must already agree. A deferred timer can never pass this; a
  publication-driven sync always does. It is the runner's failure made deterministic.
- `test_a_charts_own_play_moves_the_cursor_on_every_beat_not_only_the_first` — Play's second beat
  (the interval alone, 1600 ms real, awaited on the bar's own `data-frame`) must move the chip.

### 3. The module's waits are FUNCTION strings
Measured on the served page under its `script-src 'self'` CSP, on chromium-1194: a
`wait_for_function` **expression** string is evaluated with the DevTools bypass on its FIRST poll
only; a later poll re-evaluates the string in the page and throws `EvalError: Refused to evaluate a
string as JavaScript`. A wait that passes only when its condition already holds at poll one is a
wait that fails under load — three CPU hogs turned every existing wait in this module into that
error before a single assertion ran. A `() => …` **function** string survives later polls (same page:
an expression flipped by a 400 ms timer fails, the function form resolves). Whether the runner's
Chrome 151 blocks later polls too is UNVERIFIED (its `_open` almost certainly needed more than one
poll and did not throw, which suggests it does not). Other browser modules still carry
expression-string waits — observed, not fixed blind; a census is the next step, never a blind rewrite.

## Consequences
- No line-keyed pin moved: trend.js's five r11 / DD-ledger sites (483 · 587 · 712 · 830 · 920) sit
  above the edit; the file grew 1345 → 1348 lines below them. The r11 contract, the DD ledger, the
  M1 control-effect census (59), and the trend layout / animation / mission / bar-drill /
  readability / legend / accessibility / theme guards (176 green, 3 standing env skips) are unchanged.
- Version 1.0.239; wheel + nine installers rebuilt after the last source edit; lockstep 68.
- **#640 is no longer docs-only.** The designated branch is the only one this session may push, so
  the fix rides the PR that turned red rather than a PR of its own; installers changed, so eight
  checks apply. The PR title and body say so.
- Playbook: when a runner's scheduling will not reproduce, prove the mechanism **by construction**
  (read the state in the same task, or after one microtask) and judge the fix by whether the gap is
  gone — never by whether the luck came back.

## QC-1 record
- RED first, pristine `trend.js` (md5 `1f872059…`): `on == ['2']` with frames all 3; `on == ['2']`
  after Play's beat two.
- GREEN: the module 5/5, three consecutive runs; the guards above 176 / 3 skips; census 59;
  installers 68.
- MUTATION by name: a scratch `src` with HEAD's `trend.js` restored (md5 verified;
  `schedule_forensics.__file__` proven to resolve to the copy under `PYTHONPATH`): both tests red at
  the same asserts, controls green on the real tree.
- Statics: ruff (whole tree) · format · mypy --strict (163 files) · bandit exit 0 · `node --check`
  every static file · `pytest --collect-only` 4,867.
- Full pytest on a worktree of the final bytes: see the SESSION-LOG follow-up line (2026-09-06).
