# Operator requests — the standing intake queue

Verbatim-intent capture of feature requests the operator raises mid-session, parked here so they
survive the session that received them. **This file is durable state** alongside `HANDOFF.md` /
`SESSION-LOG.md` / `LESSONS-LEARNED.md`: an item is added the moment it is raised, and removed only
when it ships (with the ADR / PR that closed it recorded on the line).

Status vocabulary: `OPEN` (not started) · `IN FLIGHT` (a round owns it) · `SHIPPED (ref)` · `PARKED
(reason)`.

---

## 2026-07-28 — `07282026_Prompt_Notes.docx` (received mid-round-11)

### OR-01 — Per-project summary must name what each metric is computing · `SHIPPED (ADR-0321)`

Every individual project schedule should list, **for every file**:

- SITE / COMPANY
- VERSIONS
- LATEST DATA DATE
- COMPUTED FINISH
- EFFECTIVE MARGIN
- DCMA-14 score

…and when the project is **wrapped up** (the rolled-up, one-row-per-project view), show:

- the SITE / COMPANY name
- the **number of versions** (how many schedules make up the project)
- the **LATEST DATA DATE** of the latest file
- the **most recent COMPUTED FINISH DATE**
- the **most recent EFFECTIVE MARGIN**
- the **average DCMA-14 score across the schedules**

**And the metric TITLE itself must make clear what the view is computing** — i.e. a rolled-up column
must say so in its heading ("Average DCMA-14 across N versions", "Latest data date"), never reuse the
per-file label for an aggregate. Reading the title alone must tell the analyst whether they are
looking at a latest-value or an average.

*Implementation notes for whoever picks this up:* this lands on the portfolio/ledger surface
(`_portfolio_body`, `/portfolio`) and the per-project card views. Law 2 applies — the aggregation rule
for each column is a **stated** rule (latest vs mean), and the heading must match the rule the engine
actually applied. Do not invent an aggregate the engine does not compute.

### OR-02 — A help call-out sticks over the left menu bar and cannot be dismissed · `SHIPPED (ADR-0314)` · **BUG**

> "I keep getting this weird call-out that covers the menu bar on the left side of the screen that I
> can't get to go away unless I switch to another page but then it will return. This should never
> happen. It is the DCMA 11 — Missed Activities call-out which explains what it is, why it matters,
> threshold, pass example, etc."

Reproduced, measured, and closed as **two** defects in the DCMA-overview float tip (`app.js`, not
the hint layer the notes guessed): a FOCUS-shown tip (what a click/tap does) had no reachable
dismissal — Escape, pointer-away, and alt-tab all stuck — and the nav-avoidance clamp tested for a
`fixed` header only, so daylight's `sticky` full-width bar was never avoided (overlap measured at
three viewport sizes). Fixed with document-level Escape/pointer/blur dismissal + a fixed-OR-sticky
clamp that clears a rail sideways and a bar downward. Both pinned by measured-box tests
(`tests/web/test_float_tip_dismiss.py`, the operator's own DCMA-11 callout by name). ADR-0314.

### OR-03 — Launch Sequence: motion + a full-length boot hum while projects load · `OPEN`

On the boot-up start screen (the **Launch Sequence**):

- keep the visuals showing **while projects are loading**, with "something flying around" so it is
  unmistakable that the tool is working and **not frozen**;
- play a **longer version of the Boot Audio "Hum"** for the **entire** load;
- **mix the audio correctly** if a loop is used — no audible seam;
- the source audio must be **at least a minute long** and must **not be one repeating sound**: a
  *series* of similar sounds, a *pattern* of the "Hum" boot audio.

*Implementation notes:* the loading indicator must be driven by real load state (start on upload,
end on ready) — never a fixed timer that lies about progress. Honor `prefers-reduced-motion` for the
animation and keep audio opt-in/mutable per the design system's a11y line. Audio must be a **local,
vendored** asset (Law 1: no remote fetch, and the air-gap test must stay green).

---

## 2026-07-30 — chat report (mid-planning session)

### OR-04 — Ollama's model runner keeps the GPU after quit · `SHIPPED (ADR-0315)` · **BUG**

> "when I open the tool and then close the tool Ollama stays active and it is eating up my
> Dedicated GPU memory."

Reproduced by the operator (enable in AI Settings → ask → wipe → quit): `llama-server.exe`
resident post-quit at ~10.9/12 GB dedicated VRAM and ~30 GB committed shared GPU memory, while
both of the tool's own cleanup taskkills reported "process not found". Behavior ruling (operator,
same day): **free the GPU on exit** — stop the runtime if the tool started it; if it is an
external service the tool merely used, unload the model (`keep_alive: 0`); never kill a process
the tool didn't start.

Root cause per the operator-gated adversarial audit
(`audit/VERIFICATION-REPORT-ollama-lifecycle.md`): shutdown no-opped for default-config use
(`_engaged` set only by the Settings POST), and the engaged path's own kill ordering orphaned the
runner (parent terminated before the `/T` tree-walk) with every failure invisible. Closed by the
three-tier shutdown + durable marker + startup reconciliation (ADR-0315). Operator verification:
the four-scenario smoke script in the PR body; park artifacts #1/#3/#5 (+#4) remain open in the
audit's §8.

---

## 2026-07-31 — session prompt (engine-correctness deep dive; pre-empts the PR-8/9/10 queue)

### OR-05 — PowerPoint-oracle parity for the two "Jacked" schedules · `SHIPPED (ADR-0322/0323)`

**Outcome:** the base CPM now honors per-task calendars (24-Hours task, eDays as the 24/7
degenerate case) with float measured in the task's own calendar minutes — every stored Total
Slack on both files reproduces EXACTLY (36 900 / 3 780 / 3 840 / 480 / −2 400 / 6 240 min),
finish 10/07 / 10/09, critical sets match, a violated MSO/MFO pin reports MS Project's negative
slack, and the Bible-named Open Start / Open Finish dangling checks catch the slide-1 pair.
**One file-vs-slide divergence, verified and NOT chased:** the committed
`Jacked up Schedule 2.mpp` does not contain Task 11's deadline (MPXJ provably reads MPP14
deadlines elsewhere; the .mpp's last save 09:23 EDT predates the pptx's final edit 10:29 EDT —
the deadline was added after the last save). The tool therefore correctly shows +13 d for
Task 11, the slide's own stated no-deadline outcome. **Operator action if desired:** re-save
the .mpp with the deadline set; the pipeline already flows it (pinned by test) and Task 11
will then read −5 d.
**CLOSED same day:** the operator re-saved the file with the deadline and uploaded it
(operator will also add it to `00_REFERENCE_INTAKE/` on main). Verified end-to-end with ZERO
code change: UID 32 deadline 2026-08-14 imports, stored TF −2 400 == recomputed −2 400 exactly
(every task exact), critical set gains Task 11, DCMA-07 cites all three −5 d tasks (29/30/32) —
the slide-6 picture precisely. The conversion is pinned as
`tests/fixtures/mspdi/jacked_up_schedule_2_with_deadline.xml` with its own regression test.

Three files are committed on `main` under `00_REFERENCE_INTAKE/mpp/` (non-CUI, operator-added via
the GitHub web UI, `inherited_from_main`): `Jacked Up Schedule 1.mpp`, `Jacked up Schedule 2.mpp`
(note the case difference), and `Politte Schedule Tool.pptx` (6 slides). The PowerPoint explains
the two `.mpp` files — they are built with **KNOWN issues the tool must identify** (named classes:
**Dangling Tasks**, **eDays/elapsed durations**, **Total Slack calculation**).

Operator intent, verbatim capture: READ EVERYTHING, ASSUME NOTHING — extract and read every slide
(text, tables, notes, embedded images), convert both `.mpp` via
`java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in> <out>` (verified working on both:
16 and 12 tasks), and read every task/link/calendar field. Then run the tool on both files and
compare **EVERY output** (CPM dates, Total Slack per task, DCMA-14 verdicts and offender lists,
dangling/logic checks, float metrics, finish, margin) against the PowerPoint. **The PowerPoint is
the oracle — the tool is known to be WRONG on these files.** For each variance: root-cause it in
the engine, write a test that FAILS on the current code (prove-able-to-fail), prototype the fix in
a sandbox, iterate until validated, then implement it **GENERALLY** — engine-level, applying to any
file the tool ever runs (no special-casing these two), so future eDays / dangling-task / Total
Slack cases are always computed correctly.

Recon hooks recorded with the request (verify, they may drift): Jacked 1 carries a
`DurationFormat=8` (eDays) task — intersects the carried debts CC-01 rendering half (74 call
sites), V3 elapsed literals (`engine/msp_filters.py`), and CC-05 negative sub-day slack floor;
`engine/metrics/_common.py::effective_total_float` prefers the file's STORED Total Slack over
recomputed CPM float — triage every slack variance as stored-vs-recomputed FIRST. Engine changes
are in scope (Law-2 work); the parity gate (`pytest -m parity`) and goldens must stay green — any
legitimately-shifted pin gets a DELIBERATE ADR-named re-baseline via that pin's own path, never a
silent update. If the PowerPoint and the `.mpp` bytes genuinely contradict, STOP and ask the
operator rather than "fixing" to a misread oracle.

### OR-06 — Fresh launch shows stale fields from previous sessions · `SHIPPED (ADR-0324 + ADR-0332 + ADR-0334)` · **BUG**

> Operator: a fresh open of the deployed tool shows fields populated from PREVIOUS sessions
> (e.g. Target UID from a project never loaded), even after wipe-then-Quit.

**OPERATOR MEASUREMENT, 2026-08-01, on the deployed box (v1.0.149) — THE ANSWER IS ONE PID.**
This is the datum Phase 1b was blocked on. Captured verbatim because it took three runs to get a
valid one and it must never have to be re-collected:

| step | LISTENING on 8321 | `pythonw` processes |
| --- | --- | --- |
| after stopping | none | none |
| after **1st** launch | **18664** | 18664 + 39740, both 19:33:17 |
| after closing **only the browser** | **18664** (survives) | 18664 + 39740, both 19:33:17 |
| after **2nd** launch | **18664** | 18664 + 39740, **both still 19:33:17** |

**The second launch produced NOTHING — no new listener, and no fourth process even transiently
(25 s later the process list is byte-identical).** So the second launcher started, failed to take
the port, exited mute, and its already-queued browser timer opened onto the OLD server. That is
the handoff's branch one, confirmed: `sys.exit` into `os.devnull` under `pythonw`, browser timer
armed BEFORE the bind. It also defeats ADR-0324's launch token — same process, same token.

**Consequence for this item: OR-06 has a SECOND, deeper cause than the localStorage one below.**
The stale fields are not only browser memory — **the server itself is the previous session**, still
holding the previously loaded schedules and settings in RAM. No client-side sweep could ever have
fixed that half.

Two corroborating facts from the same session: an earlier snapshot showed PID 24788 LISTENING with
**zero** ESTABLISHED connections — a survivor inside its grace window; and the watchdog grace is
`idle_grace=600.0` (`web/app.py`), i.e. the server legitimately outlives the browser by up to **10
minutes**, which is the window in which a relaunch lands on the old process. A first attempt at the
measurement showed the server gone 25 s after the browser closed — that run is DISCARDED as invalid
(it contradicts the 600 s grace; Quit was evidently clicked), and is recorded here only so the
contradiction is not re-investigated as a finding.

Root cause is VERIFIED mechanism-level: `web/static/persist.js` (ADR-0186 per-page selection
memory) stores `sf-qs:<path>` (query strings incl. `?target=…`) and `sf-ui:<path>` (control
values) in browser localStorage, which survives server wipe/quit by design of localStorage —
nothing invalidates it for a new session. Fix so a wipe and/or a fresh server launch invalidates
the per-page selection memory (e.g. a server-issued launch/session ID that keys or clears the
`sf-qs:`/`sf-ui:` layers), WITHOUT killing ADR-0186's within-session page memory or the global
prefs (theme/scale/timescale are deliberately separate). UI change → DESIGN-SYSTEM.md rules; check
for JS digest/line pins over `persist.js` BEFORE editing; own ADR.

---

## How to work this queue

- Pick items up in a numbered round like any other tail work; record the ADR that closes each.
- An item here is **not** a licence to widen an in-flight round's scope — round 11 was mid-flight when
  these arrived and correctly did not absorb them.
