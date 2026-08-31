# Handoff — 2026-08-31 (WP2 COMPLETE: the steppers are DRIVEN on a fake clock and the Play-all coordinator was dead on two of its three pages; the wall frames all 30 tiles; language stops throwing you to the dashboard; ADR-0443, v1.0.225)

> ## STATUS (current) — **WP2 is MERGED: PR #618 squash-landed on `main` @ `0e07d213` (2026-08-31 22:16Z), all seven CI checks green. The campaign runs under QC-1/QC-2 — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Next work package is **WP3 (M4 — the SRA grid)**; branch FRESH from `origin/main`, never stacked on the consumed WP2 branch.
> Highest ADR **0443**; version **1.0.225** (shipped code: `static/chartframe.js`, `static/mission.js`,
> `static/curves.js`, `static/trend.js`, `static/driving_path.js`, `web/chrome.py`, `web/app.py`);
> wheel + nine installers rebuilt in lockstep. Ledger: **docs/STATE/AUDIT-2026-08-27.md** WP2
> section. Gate numbers: SESSION-LOG 2026-08-31 (WP2) entry, recorded AFTER the runs (QC-1).
>
> ## M3 + M5 are driven, and the first runs found FIVE defects
> Two new modules, both clock-driven (never a wall-time sleep — autoplay is 1100–1800 ms):
> `tests/web/test_ui_stepper_autoplay_browser.py` (59 tests, ~1:52) drives all 47 id'd steppers/
> autoplay controls, the 138 `sf-frame` trio buttons, the three page masters and the ADR-0275
> coordinator; `tests/web/test_ui_chrome_controls_browser.py` (8 tests, ~30s) drives the REAL
> `#themeSelect` across four views, `#themeToggle`, `#uiScale`, language and Task Information.
> **Two oracles per control** — the label AND a DOM-shape-agnostic chart digest — because a
> control that flips its caption while the visual stands still is the WP0 defect class. Every
> `WP2:M3` census deferral is discharged; driver values are now module-qualified and the census
> meta-guard imports the sibling module to resolve them.
>
> ## Five defects, all CONFIRMED-FIXED red-first (ADR-0443)
> **M3-01** `/mission`'s wall master was NEVER registered with the ADR-0275 coordinator — the
> layout emits `chartframe.js` after `<main>` (measured DOM indices: `mission.js` 20,
> `chartframe.js` 24), so `if (window.SFPlayAll)` was always false and skipped it silently; a
> chart's own Stop could not halt the wall, the exact symptom ADR-0275 was written to kill.
> **M3-02** `/curves` never called `register()` at all; `/trend` worked only by the accident of
> registering after a `fetch`. Registration is now order-independent (stub queue + `_pending`
> adoption). **M3-03** `driving_path.js` was the ONLY animated module of twelve ignoring
> `prefers-reduced-motion`. **M5-01** the wall framed 9 of 30 tiles — settled by measurement
> (a manual `SFChartFrame.scan()` took it 9 → 30, so it is the UI-02 attach-vs-fetch race, not a
> design choice; the 9 existing toolbars were confirmed to actually zoom first). **M5-02** the
> Language selector always dumped the operator on `/` — `/language` trusted a `Referer` the app's
> own `Referrer-Policy: no-referrer` strips; moved onto the `data-sf-nexturl-submit` + validated
> `next_url` idiom the Project switcher already used.
>
> ## The A2 pin was failing open
> M3-03 survived because `test_accessibility.py` checked a hand-written list of FIVE modules while
> twelve are animated. The sweep is now COMPUTED from the shipped JS with a documented exclusion
> list, so a new animated module is RED by default, plus a guard that fails on a stale exemption.
>
> ## Proof
> **Definitive full suite on the SHIPPED tree (`e355cd58`): 4598 passed, 5 skipped, 0 failed**
> (41:58) — run to completion on the frozen tree, with `git status` and `git diff HEAD` both empty
> and the working tree, `HEAD` and the pushed ref all at that sha, so the number describes what
> shipped rather than a tree that has moved on.
> Red-first observed: M3 **5 failed / 54 passed**, M5 **3 failed / 5 passed**. **19-mutation
> battery, every one RED BY NAME** — including the chart oracle proved independently of the label
> oracle, and the coordinator's `isTrusted` check (whose removal would make Play-all halt on its
> own first beat). A route-level open-redirect pin rides with M5-02 (6 hostile payloads, 4 honoured
> paths, plus backslash payloads measured — Starlette percent-encodes them).
>
> ## The FIRST push was RED on CI, and every failure was this change's
> Honest record, because the fix chain is the lesson (ADR-0443 has the table). Local full suite on
> the as-pushed tree: **16 failed / 4578 passed**. (a) I re-applied only HALF of `chartframe.js`
> after the `git checkout --` restore, so the coordinator's assignment stayed conditional,
> `mission.js`'s stub survived and `/mission` threw 20 `stopAll is not a function` page errors —
> **worse than before the PR**, and the "59/59 green" I had quoted described a tree that no longer
> existed. (b) Four byte-freeze pins fired that my pre-flight grep could not see (it searched for
> my filenames; the pins hash whole files and index call sites by line) — all re-baselined
> deliberately, with every axis CAPTION md5 verified identical first. (c)
> `test_the_autoplay_stepper_pin_is_untouched` froze the literal this ADR replaced — re-expressed
> against the computed population (stronger: set membership, not a spelling). (d) The embedded
> wheel went stale after a late whitespace edit. (e) `playwright>=1.44` was a FALSE floor —
> `page.clock` does not exist below 1.45 (measured: the 1.44.0 wheel contains "clock" zero times).
>
> ## Traps paid for THIS session — check by name
> **`git checkout --` is NOT a mutation restore** — it reverts to HEAD and silently deleted three
> of this session's own fixes mid-battery, then let one mutation "pass" while measuring unfixed
> code; restore from a `cp` of the WORKING TREE and diff the tree after every chain ·
> **a wrong oracle looks exactly like a defect** — an SVG-only digest reported three false "chart
> did not move" rows because `/evolution`, `/driving-path` and `/trend`'s drill paint HTML tables ·
> **measuring `document.body` to test a page zoom calls a working control dead** (body is
> full-bleed at every zoom; `#uiScale` was nearly written up — the heading's box scales 212 → 371) ·
> **a probe's own wait can invent a finding** — reading `page.url` after `wait_for_load_state`
> before the navigation began mis-reported the language landing; `expect_navigation` measured it ·
> **the server session outlives a browser context** (a language set in one step translated a later
> step's page) · **re-applying a fix needs the suite RE-RUN — a green quoted from memory is
> testimony, not evidence** · **a byte-pin pre-flight grep must search the PIN SHAPE, not your
> filenames** · **rebuild the wheel + installers as the LAST step, after the final source edit**.
>
> ## Operator-facing state
> After this PR merges the operator re-downloads once (banner must say **v1.0.225**): the Mission
> wall's Play-all now stops when they touch any chart, all 30 wall tiles carry a working zoom
> toolbar instead of 9, the corridor no longer auto-animates under reduced motion, and choosing a
> language keeps them on the page they were reading.
>
> ## Next — campaign queue
> **WP3** (M4 SRA grid edit / paste-from-Excel / save round-trip) → **WP4** (route-coverage
> instrument, `SF_ROUTE_COVERAGE=1`, floor ≥139, + the 08-26 `startup_failure` root-cause; VERIFY
> a `pull_request` run appears per push meanwhile) → **WP5** (BOTH folder builds — the three
> 2026-08-21 folder-gesture facts govern, do NOT re-derive) → **WP6** (ledger highs: CPM-01
> `cpm.py:1316` · CPM-02 `driving_slack.py:314` · MC-02 · MC-03 `jcl.py:284` · MAN-01 · REC-02;
> parity-sensitive rows through the metric-parity skill; any golden shift = CONFIRMED-DEFERRED,
> never a silent re-pin) → **WP7** (thin dims, `ai/txlog.py` first — Law 1) → **WP8**
> (consolidated report + roadmap by testimony risk). Do-not-fix-blind rows unchanged (ledger +
> AUDIT do-not-fix list); the `/mission` 30-vs-9 row is now CLOSED, not deferred.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
