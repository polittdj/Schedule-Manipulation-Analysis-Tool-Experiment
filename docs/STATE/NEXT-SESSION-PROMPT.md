# Kickoff prompt — next session

PR state (2026-09-10): **#661 MERGED** → `main` @ **`6c4f2f31`** (ADR-0482 / OR-12, **v1.0.252**),
tree-verified `9ce04715…` on both the squash and head `03e33b34`, eight of eight checks green.
**PR #662 is OPEN (docs-only)**, registering OR-13. **Always `git fetch origin` and read
`git log origin/main` before trusting any sha written here** — three consecutive kickoffs have been
stale by the time they were read.

## TAKE OR-13 FIRST. It is ahead of R-56, and the operator lost a day to it.

**Root cause is FOUND and verified against the installed API, not from memory:**

```
uvicorn 0.52.4 — Config(..., timeout_graceful_shutdown: int | None = None)
web/app.py serve(): uvicorn.Config(app, host=host, port=port, log_level=log_level)   # never set
```

`None` means **wait forever**. The watchdog fires, `_trigger_shutdown` sets `should_exit`, and
uvicorn then blocks indefinitely draining a connection the browser abandoned. The operator's live
reproduction, on v1.0.252:

```
LocalPort RemotePort    State OwningProcess
     8321      54055 FinWait2         16876      <- half-closed; the browser is gone
     8321          0   Listen         16876      <- and it is STILL answering /api/whoami
```

**The bug was never in the detection. It is in the EXIT.** This also explains why the 600 s idle
rule never worked either (a server survived ~18 h), and why the desktop icon fails **invisibly**
under `pythonw` — a handover timeout with stderr going to `nul`.

**ADR-0482 is NOT the culprit and is not wrong.** A real-Chromium test measures `POST
/api/heartbeat` → 200, `POST /api/closing` sent on unload, and the server stopping **5 s** after a
clean single-cycle close. Do not "fix" ADR-0482.

**DO NOT ship the one-line fix without a RED-FIRST repro.** The proposal is a bounded
`timeout_graceful_shutdown`. The argument that a short value is safe — `active_requests > 0`
already blocks the watchdog while real work is in flight — **is the same species of reasoning that
was wrong FOUR times on 2026-09-10**: the CSRF gate refusing the beacon, an Ollama-manager hang,
the `browser_seen` gate, a surviving tab. All dead on measurement. Build the repro first: a
half-closed socket that hangs the current build and goes green with the timeout. Every refutation
is recorded in `docs/STATE/OPERATOR-REQUESTS.md` OR-13.

**Two diagnostic rules this cost a day to learn.** A filter in a diagnostic is an ASSERTION about
where the answer lives: `Get-Process pythonw` and `Get-NetTCPConnection -State Listen` both
returned empty while a server was running and holding the port, because the evidence was a
`FinWait2` connection the filter excluded by construction. And **every "install this and try
again" must end with a command that prints what actually got installed** — the operator spent a
day testing v1.0.251 because I never asked.

**Three steward traps, all measured — do not re-learn any of them:**
1. `pull_request_read` method **`get_status`** returns `{"state":"pending","total_count":0,
   "statuses":[]}` on a PR whose checks are ALL green — that is the LEGACY commit-status API and
   this repo posts none. Use **`get_check_runs`**; `total_count` gives the lie away.
2. A `check_suite.completed` event can carry a **superseded** `head_sha`. Re-read the current head.
3. Check set: **eight** when `installer/**` changes, **six** for docs-only (no `windows` job).

**Environment, measured:** the shallow-clone remedy is **deepening**, and budget it big —
`--deepen=25` did nothing, and `--deepen=<n> origin main` kept resolving `git log -1 -- tools/mpxj`
to the NEW graft boundary twice running. A cumulative **`60 + 200 + 400` on `origin main`** (742
commits) surfaced the true `42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca`, after which
`build_installers.py` pinned it with **no `SF_MPXJ_REF`**. Install with
`uv pip install --python /usr/local/bin/python3 --system -e '.[dev]'` (add `build` and `playwright`
the same way; never `playwright install` — use `tests/web/browser_chrome.py::chrome_kwargs()`).
**Use the real browser.** `render-verify` exists for exactly this and skipping it is what let
OR-12 ship without touching the operator's actual failure.

**After OR-13 take R-56** — the operator queue is now EMPTY of blocking rows (OR-11a/c/e all shipped;
OR-11b needs a measurement first and OR-11d is cosmetic), so the audit rows resume. R-56 is far
better specified than the report's row: it is a duration-CONTOUR defect on UNSTARTED work, so no
progress rule reaches it, and it is what still holds `Hard_File_updated3`'s finish 13 d early after
ADR-0476. updated3 has **SEVEN** chain heads (a disagreeing activity whose every predecessor
already agrees) and 45 rows inherited from them; the report names only UID 403, and **UID 385 is
the larger driver**:

| UID | duration | engine span | MS Project span |
|---|---|---|---|
| 385 | 5,664 min | ~6 wd (944 min/d) | ~17 wd (333 min/d) |
| 403 | 1,920 min | ~5 wd (384 min/d) | ~14 wd (137 min/d) |

MS Project is spreading these at a FRACTION of a working day — a contoured / part-time assignment
the booking rule does not model. First executable step: tally `<Assignment>` Units, Work and any
TimephasedData for 385 / 403 / 302 against their `<Task>` Duration, and **check the rule against
EVERY golden by task Type** before believing it (a booking rule proven on one file has broken
another here twice). What settles it: updated3 within a day of the stored 2026-12-12 with
`-m parity` unmoved and Project2 / Project5 still exact. Two heads are the day-boundary residual
below, not R-56's.

**Environment, MEASURED this session — the shallow-clone remedy is DEEPENING, and budget it big.**
`git fetch --deepen=25 origin` (no refspec) did nothing at all. `--deepen=<n> origin main` moved the
graft boundary, and `git log -1 -- tools/mpxj` then resolved to the NEW boundary — the same
artifact one commit further back — twice running. Only a cumulative **`60 + 200 + 400` on
`origin main`** (742 commits, boundary `d582e104`) surfaced the true last touch
`42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca`, after which `build_installers.py` pinned it with **no
`SF_MPXJ_REF` and no new graft artifact**. A partial deepen is indistinguishable from success
unless you check the sha. The container may have NO project install:
`uv pip install --python /usr/local/bin/python3 --system -e '.[dev]'` completes first try (add
`build` and `playwright` the same way; do NOT run `playwright install` — use
`tests/web/browser_chrome.py::chrome_kwargs()` in scratch probes too).

**Heads-up on review cover:** `chatgpt-codex-connector[bot]` reported EXHAUSTED Codex review quota
on #655, #656 AND #657. Until it is restored, the mutation battery and the full gate are the only
review this repo is actually getting.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read
`docs/STATE/HANDOFF.md` FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the
roadmap by testimony tier, pinned by `tests/guards/test_audit_report_wp8.py` (every row priced or
owned, tier order, a nine-figure census recomputed by method — re-measure, never edit by hand).
QC-1/QC-2 bind every session (ADR-0393). `git fetch origin` before you branch, number an ADR, or
commit. The container may have NO project install, and **pip read-timed-out on it twice** —
`uv pip install --python /usr/local/bin/python3 --system -e '.[dev]'` completed first try
(add `build` the same way). The installer builder REFUSES a shallow clone: `git log -1 --
tools/mpxj` resolves to the graft boundary. Deepening is one remedy; the cheap one is
`git fetch --depth 1 origin <true last-touch sha>` then `SF_MPXJ_REF=<sha>` — the script verifies
the tree is identical itself. As of v1.0.248 that sha is
`42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca` (tree `2001032378e5253edaecf0a8fe142bcbd54f666e`).

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01, the multi-project Fuse
oracle) · ADR-0474 (R-44 CLOSED: resource calendars + leveling delay in the base CPM, MS Project's
stored dates as the oracle; + the latency amendment and the floor job's seven pins) · **ADR-0475 —
the design page, owed twice, delivered first and alone:** `/standards` wears the Control "Standards
and Execution Indices" artboard (`setScreen('sd')`, executed over loopback in four themes, zero page
errors). The mock's `· 16 / · 14 / · 10` were measured to BE the page's own live counts. The selector
row is ported as NAVIGATION that hides nothing (`.viz-controls.cd-cursor#standardsFamilies`, anchor
chips with live counts, a `cd-note` saying nothing is hidden); all three families gained the take the
mock gives each; the REF column carries the ENGINE's `metric_id`. Refused and named: the tab-hiding,
`⤓ EXCEL · ALL FAMILIES` (no covering export — ADR-0327), the mock's `INFO` status, its `01a`/`01b`
split of DCMA-01, the Continue footer. **The design queue: 9 done, 21 artboards remain; /scorecards
(`setScreen('sk')`) is next by cost.** · **ADR-0476 (R-55 CLOSED)** · **ADR-0477 (R-20 / UI-03
CLOSED)** · **ADR-0478 — `/api/ask` says WHY there is no written answer** (`NoAnswer` +
`answer_question_detail` in `ai/qa.py`; `_no_answer_note` in `web/app.py`; `no_answer: {code,
text}` on the payload; `ask.js` renders the server's sentence). Do NOT re-open: the panel's
blanket sentence is pinned gone, and the primary answer's call site is
`answer_question_detail` — a monkeypatch left on `answer_question` intercepts the cross-check
SECOND model only. · **ADR-0481 (OR-11e CLOSED)** — the tool SENDS `num_ctx`, but only when the
operator sets one; `0` (default) omits the key entirely, non-zero clamps at all THREE entry
points into `[2048, 262144]`, ceiling = Ollama's OWN `>= 48 GiB` tier default. What the server
does on RECEIPT is UNVERIFIED by design and claimed nowhere. · **ADR-0482 (OR-12 CLOSED)** —
closing the browser stops the tool in ~5 s instead of 600 s: `heartbeat.js` beacons
`POST /api/closing` on `pagehide`, the server arms a fuse, and **a heartbeat CLEARS it** so an
ordinary navigation (every one of 35 server-rendered routes unloads the page!) cancels the fuse
it just armed. `CLOSE_GRACE = 5.0 > HEARTBEAT_INTERVAL = 3.0` is a CONSTRAINT. Do NOT wire
`visibilitychange` (tab switch; cancellation would ride on a throttled background tab) and do
NOT beacon on `event.persisted` (bfcache — stops the tool behind a Back button). Do NOT 'fix'
this by lowering `idle_grace`; it is load-bearing for a long unattended read. · **ADR-0481 (OR-11e CLOSED)** — the tool SENDS `num_ctx`, but only
when the operator sets one: `num_ctx=0` (default) omits the key, so the request is
byte-for-byte the old one; non-zero clamps at all THREE entry points (form POST, settings
file, backend constructor) into `[2048, 262144]`, the ceiling being Ollama's OWN `>= 48 GiB`
tier default, not ours. `_num_ctx_cost_note` states the mechanism, the `OLLAMA_NUM_PARALLEL`
multiplier, the tier defaults, the #14073 incident **attributed** (a 52 GB-VRAM machine), and
what is actually in force — and NO GB-per-token figure, which the tool cannot know. Do NOT
re-open: what the server does on RECEIPT is UNVERIFIED by design and claimed nowhere.

⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → mutation proofs by name →
the full gate → an ADR → the state docs → a draft PR): **R-56** FIRST, and it is now far better
specified than the report's row. It is a duration-CONTOUR defect on UNSTARTED work, so no progress rule
reaches it, and it is what still holds `Hard_File_updated3`'s finish 13 d early after ADR-0476.
updated3 has **SEVEN chain heads** (a disagreeing activity whose every predecessor already agrees) and
45 rows inherited from them; the report names only UID 403 and **UID 385 is the larger driver**:

| UID | duration | engine span | MS Project span |
| --- | ---: | --- | --- |
| 385 | 5,664 min | ~6 wd (**944 min/d**) | ~17 wd (**333 min/d**) |
| 403 | 1,920 min | ~5 wd (**384 min/d**) | ~14 wd (**137 min/d**) |

MS Project is spreading these at a FRACTION of a working day — a contoured / part-time assignment the
booking rule does not model. First executable step: tally `<Assignment>` `Units`, `Work` and any
`TimephasedData` for 385 / 403 / 302 against their `<Task>` `Duration`, and check the rule against
EVERY golden by task `Type` before believing it (a booking rule proven on one file has broken another
here twice). What settles it: updated3 within a day of the stored 2026-12-12 with `-m parity` unmoved
and Project2 / Project5 still exact. Two heads are the day-boundary residual below, not R-56's ·
**R-49** — MPXJ omits a ZERO `TotalSlack` (62 of Fuse's 66 zero-float activities on
LTF2 carry none): the importer infers 0 when the file carries the element elsewhere and the task
carries `Critical`; red-first on Fuse's Zero Days Float 66 / 2 · R-46 (BCWS +150 — prorate the
straddling activity on its crew calendar) · R-47 (SPI(t) 8.24 vs 8.22) · R-52 (the `.pptx` LibreOffice
refuses) · R-50 (expose the History variants) · R-57 / R-58 / R-59 (ADR-0474's residuals) · then R-03 ·
R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. PLUS the design page owed each session —
**now CURRENT, not owed**: deliver **/scorecards** (`setScreen('sk')`) as its own unit, recipe in
ADR-0471/0475.

⇢ Traps paid for, by name (2026-09-09 b first): **an oracle read out of the state under test cannot judge that state** — a check recorded a 'before' value from `app.state`, probed, then asserted equality; the mutation cleared that state on EVERY request, so both sides were `None` and it passed over a comprehensively broken feature. Assert the ABSOLUTE fact first (is it armed at all?), the relative one second · **a mutation with `old == new` proves nothing and reads exactly like a pass** — the sandbox harness now refuses them; a testing tool needs its own guard rails · **engineer the red to prove the instrument**: the node harness failed on exactly the 3 new-behaviour assertions while its other 5 passed against the OLD file — all-red might just be a broken harness, all-green proves nothing. (2026-09-09 a:) **an assertion is only as strong as the text that was NOT already there** — two of twenty mutations came back GREEN because the cost-note checks searched the WHOLE `/settings` body, which already carried `OLLAMA_NUM_PARALLEL` (the ADR-0315 env report) and `262,144` (the new input's own `max=`); deleting the note entirely walked through. Before asserting a NEW string is present in a rendered artifact, grep that artifact for it FIRST; the fix that works is compositional — assert the PRODUCER's return value carries it AND that its exact output is a substring of the page · **the suite measures the tree as it was at second zero** — I fixed three docstrings mid-run after verifying a sourced number, and had to kill it, rebuild the wheel + nine installers, and restart; freeze the source, THEN build, THEN run · **run the CONTROL before believing your own new instrument** — `/settings` measured scrollWidth 1877 vs innerWidth 1440, and a pristine `HEAD` worktree measured byte-identical, so the finding is about SCOPE (ADR-0477's guard renders FOUR routes and fixed the HINT-BUBBLE mechanism; `/settings` was never in that census and its cause is an over-wide `<select>`), not a regression · **refute your own hypothesis first** — I was sure a blank `<input type=number>` would 422 a FastAPI `int = Form(0)`; measured, blank AND absent both fall back to the default with 200, so the defensive handler I was about to write was unnecessary. (2026-09-08 first:) **a green suite is not evidence the INPUTS are
consistent — only that nothing reads the inconsistent part**: `clean_program` passed 41 tests for
months over completed leaves recording an 8-working-day window against a declared 10-day duration and
starting before their predecessors finished, because the engine read neither; when a long-green fixture
fails, ask FIRST whether the change made the engine read something it used to ignore · **when a change
makes the engine honour a previously-ignored input, sweep for code whose correctness depended on it
being ignored** — the backward pass (retreating by the PLANNED duration against a RECORDED window put
−13 wd of float on finished work) and DCMA-12 (injecting a delay into an activity the pin makes
immovable) both broke, neither caused by the rule · **measure the blast radius of a fixture redesign
before committing to one** — three "corrections" scored 16, 16 and 7 failures against leaving it at 3 ·
**never let an example into a comment without executing it** — mine said Project2's UID 26 carried no
actuals; it carries both · **two errors can CANCEL** — R-55 improved every
per-activity measure (engine-LATE 68/31/13 → 0, completed activities past their own record → 0
corpus-wide) while making updated3's project finish look WORSE (−6 → −13 d), because the old engine's
spurious lateness was propping the composite up; when a fix that improves every constituent worsens the
composite, a second bug was holding it together — quantify both and pin the constituents · **an
inherited attribution is TESTIMONY** — the report's "UID 403's contour and the milestone snaps" named
the smaller of two drivers and one head of seven, and the "milestone snaps" are not milestone-specific
· **refute your own hypothesis before the report's** — a data-date theory was built first and died on
its own probe (5 of 68 unstarted activities start before `StatusDate`, 1 of the 50 disagreeing rows) ·
**a GREEN mutation may mean the FIXTURE CORPUS cannot express the case, not that the assertion is
weak** — count the population before re-aiming: zero part-complete activities carry an `ActualFinish`,
zero completed activities have `resume > stop`, zero actuals are inverted in ANY committed golden, so
three branches needed hand-authored rigs that say so · **Playwright's virtual mouse SURVIVES `goto()`**
— park it (`page.mouse.move(0, 0)`) before any resting measurement, or you measure a hovered page ·
**run the CONTROL before believing a red from an instrument you just wrote** (a /evolution hover
"failure" reproduced identically on the pristine stylesheet) · **an `assert` in `src/` is a house-style
violation** — there are none in the tree and `python -O` strips the narrowing · **the full suite must be
started AFTER the version bump and the wheel/installer rebuild**, or the lockstep test fails as an
artifact and the run is not a valid measurement (2026-09-07 d paid for this too). (2026-09-07 d:) **a
mutation that comes back GREEN is a finding about the TEST** — a count that is structurally constant on every fixture (DCMA always 16, SEM always 10)
cannot be distinguished from a hardcode; aim the pin at the value that VARIES (Fuse reads 9 with one
file, 14 with two) and record the rest UNVERIFIABLE · **verify a literal against the RENDER, not
memory** (two of my own probe strings were wrong before the tree was) · **the container's pip
playwright may demand a browser build the container does not vendor** (`-1234` vs the vendored
`-1194`) — use `tests/web/browser_chrome.py::chrome_kwargs()` in scratch probes too, never
`playwright install` · **a helper added to an extracted page module is red on the monolith split
contract until `app.py` carries its `X as X` re-export** · **do not leave a scratch script in the repo
root** — `ruff check .` is whole-tree · a design mock's status word, decomposition and export label
are claims about the ENGINE: check each before drawing it · a mock that HIDES is proposing a
functionality change, not a layout. (Earlier, still live: MS Project's stored Start/Finish/Early/Late/
TotalSlack/Critical are a per-activity CPM oracle in every MSPDI · `LevelingDelay` is tenths of a
minute · a booking rule proven on one file breaks another — tally by task `Type` on every golden · the
full suite is ~40 min, start it in the background the moment the engine settles · MPXJ writes no zero ·
`Large_Test_File.mpp` ≠ `Large Test File.mpp`.)

⇢ Measured-false / deliberately held — do NOT re-chase: the ribbon tiles' scopes · TP3's ribbon 8 /
Lags 3 (R-53) · the DCMA08 baseline basis (R-48) · Fuse's ACWP-to-time-now and updated3's BAC (R-45) ·
the four Hard_File bookings the MSPDI cannot explain (R-56) · **R-20 / UI-03 is now CLOSED (ADR-0477)** — every page measures
`document.scrollingElement.scrollWidth == innerWidth == 1440` in all four themes; do NOT re-chase the
1719 / 1734 readings · the HELD and CLOSED rows of the report · the S-curve & finish-window residuals of earlier sessions.

⇢ NEW residual registered 2026-09-09 (measured, not taken): **`/settings` scrolls sideways** — `document.scrollingElement.scrollWidth` 1877 / 1641 / 1877 / 1877 at a 1440 viewport (console / daylight / apollo / jarvis), IDENTICAL on a pristine `HEAD` control, widest element the `AI answer mode` `<select>` sized by Chrome to its longest option. NOT the hint bubble, NOT a regression, NOT covered by ADR-0477's four-route guard — its own UI unit with the design-system DoD. Do NOT re-chase the hint bubble at rest: that IS closed.

⇢ Residuals from 2026-09-08 (both measured, neither taken): **the working-minute axis
cannot carry a recorded instant that lands on a day boundary or a non-working moment** — UID 323's
`Wed 2026-08-19 08:00` renders back as `Tue 08-18 16:00`, UID 300's **Sunday** `08-30 04:00` as
`Fri 08-28 16:00`, and UID 292 (not a milestone) loses an hour; 2 of 42 completed activities on
updated3, 19 of 699 on Large_Test_File. Carrying the raw instant means populating the wall fields on
the project-axis path, which today SIGNAL "off-calendar task" codebase-wide — structural, not a
one-liner. **And:** the hint bubble still widens the document WHILE OPEN near the right edge (ADR-0477
fixed only the resting state); closing it needs edge-aware placement, not a size reset.

⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; read a verdict on the FINAL head; a red cell on
`main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
after a squash-merge restart the branch with `--prune` + `remote set-head` + `checkout -B`, never amend
the squash.
