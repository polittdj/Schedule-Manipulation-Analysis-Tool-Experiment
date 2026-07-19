# LESSONS-LEARNED.md — the running "what we did, what we tried, what didn't work" log

> **What this is.** The durable, plain-language memory of the Schedule-Manipulation-Analysis-Tool
> (POLARIS) build: everything we have shipped to date, everything we tried, and — most importantly —
> everything that **did not work** and why. It complements the other durable-state docs: `HANDOFF.md`
> is "where we are right now," `SESSION-LOG.md` is the append-only per-session diary, `docs/adr/` is the
> decision record. This file is the **cross-cutting lessons layer** that sits above all of them, so a
> new engineer (human or agent) can absorb the hard-won judgment without re-reading 271 ADRs and 7,200
> lines of session log.

---

## ⚠️ STANDING MANDATE — UPDATE THIS FILE DAILY

**Every working session on this project MUST append to the [Change log](#change-log) at the bottom of
this file before it ends.** Even a one-line entry ("no substantive change; verification-only session")
counts — the point is a continuous, dated trail of what was learned. When a session produces a real
lesson (a reversal, a wrong fix caught, a new footgun, a validated approach), record it in the relevant
Part **and** summarize it in the Change log the same day.

- **This mandate is wired into memory** via a standing rule in `CLAUDE.md` ("Durable state" section),
  which the SessionStart hook surfaces every session, so no session can plausibly claim it "didn't know."
- **There is deliberately NO automated date-based test** enforcing the daily cadence. A test that fails
  because "today is more than N days after the last entry" is a time-dependent flaky gate, and this
  project's standing principle (ADR-0249) is *a flaky gate is worse than none*. The mandate is enforced
  by discipline + the CLAUDE.md standing rule + code review, not by a brittle clock check.
- **If you are an AI agent resuming this project:** treat updating this log as part of the Definition of
  Done for the session, exactly like refreshing `HANDOFF.md` and `SESSION-LOG.md`.

---

## Part I — What we have built to date (capability inventory as of v1.0.76)

**What it is.** A local, offline, **CUI-safe forensic schedule-analysis tool**. It ingests MS Project /
Primavera schedules, runs CPM + DCMA-14 / Acumen Fuse v8.11.0 / SSI / EVM parity metrics + manipulation
detection + Monte-Carlo risk analysis, and serves an interactive, locally-rendered report with a cited
local-AI narrative. Python 3.11+, FastAPI, standard-library-only runtime I/O. Branded **POLARIS** in the UI.

**The milestone arc (greenfield → now):**

| Phase | What landed | Key ADRs |
|---|---|---|
| **M1–M17** (greenfield → "complete", ~Jun 2026) | Build rails/CI/egress guard; frozen pydantic model; MSPDI/XER/JSON importers + MPXJ `.mpp`; CPM/float; driving-slack SSI parity; DCMA-14 + Acumen Schedule-Quality; EVM + baseline compliance; parity acceptance gate; DCMA audit + cited recommendations; version-diff + manipulation trend; local-AI cited narrative; FastAPI web shell; interactive visuals; desktop launcher | 0006–0021 |
| **M18 + PBIX reproduction** (mid-Jun) | Stored-date CPM mandate; "AI at full power"; summary-logic lowering; `/evolution` critical-path animation; Bow Wave/CEI; `/forecast` | 0030–0045 |
| **Parity deepening + metric expansion** (late Jun) | CEI/FEI/BRI/HMI/Float-Ratio pulled verbatim from the NASA `.aft` "Bible" and validated exact vs Acumen; EN/ES/FR/DE i18n; custom-field grouping; a11y audit + CSP | 0052, 0073–0077, 0099 |
| **Handbook D-plan + SRA epic** (early Jul) | Deterministic handbook tranches (logic integrity, float-erosion-by-WBS, stoplight, constraint health); Monte-Carlo SRA; risk register; schedule margin | 0106–0141 |
| **Audit cycles + platform hardening** (Jul) | Inactive-task exclusion; operator-selectable AI figure modes; role-aware figure gate; 3-OS installers (9 total); HUD/JARVIS telemetry; wheel↔source lockstep; windowless-subprocess fix | 0128–0149 |
| **Mission Ops redesign** (Jul 11+) | Four-theme tokens → story-spine chrome → twelve chapter page shells (one per PR) → shared drill; Metric Workbench; `/standards` + SEM engine | 0195–0219, 0237–0238 |
| **v4 + #331 advanced analysis** (mid-Jul → now) | Grouped ingestion + Portfolio; scale layer; roles front page; faithful MSP saved filters; NASA STAT/GAO scorecards + reserve sizing; **JCL/FICSM joint confidence** (0269); **correlation matrix + eigenvalue feasibility** (0270) | 0213, 0225–0270 |

**Module map (`src/schedule_forensics/`):**
- **`model/`** — frozen pydantic `Task`/`Schedule`/`Calendar`/`Resource`; `unique_id` is the *sole* identity;
  integer working minutes; CPM values **derived, never stored**.
- **`importers/`** — `mspdi` (richest), `xer`, `json_schedule`, `mpp_mpxj` (Java MPXJ → MSPDI) + saved-view sidecar ingest.
- **`engine/`** — `cpm.py` (trust-root solver); `metrics/` (DCMA-14, CEI, HMI, FEI/BRI, SEM, EVM, float bands,
  schedule-quality…); forensic layers (`driving_slack`, `manipulation`, `path_evolution`, `change_effects`);
  `trend`, `grouping`, `margin`, `sra`, `jcl`, `correlation`, `scorecards`; scale tier (`cache`/`summary`/`memory`).
- **`ai/`** — `AIBackend` protocol (Null / Ollama / OpenAICompat, loopback-validated, fails closed); `citations`,
  `qa`, `narrative`, `derivation` (figure re-verification gates).
- **`web/`** — `app.py` (**all** routes + `SessionState` + server-rendered HTML — the ~18K-line monolith),
  `i18n.py`, `help.py`, vendored `static/*.js|css`.
- **`reports/`** — std-lib `xlsx`/`docx` export; **`exhibits/`** — offline SVG exhibit pack + headless report CLI.
- Plus `launcher.py`, `net_guard.py` (egress guard).

**The gate & guards (what protects the build):**
- **CI gate** (Python 3.11 + 3.13): `ruff check` · `ruff format --check` · `mypy --strict` · `pytest` with
  coverage gates (overall ≥70 %, engine ≥85 %) · **parity gate** (`pytest -m parity`) · `bandit` · `pip-audit`.
- **CUI pre-commit guard** (`.githooks/pre-commit`): blocks schedule/Office/PBIX/pickle extensions everywhere
  except `tests/fixtures/` and blobs byte-identical to `origin/main` (the `inherited_from_main` exception).
- **Egress guard** (`net_guard.py`): fails CI if a forbidden HTTP client (requests/httpx/urllib3/websockets/…)
  enters the *runtime* dependency closure. Net result: **zero runtime deps added across the entire build**
  beyond pydantic/fastapi/uvicorn/jinja2/python-multipart.
- **Air-gap test**: scans every served asset for off-box references (no CDN, no remote fonts/images).
- **Strict CSP** (`default-src/connect-src 'self'`, `script-src 'self'`) enforces the air-gap at runtime.

---

## Part II — What worked (validated approaches to KEEP in any rebuild)

1. **Parity gate as the regression backstop.** Golden fixtures + `pytest -m parity` as an acceptance gate
   held **10/10 from M9 onward**; every later visual/AI/refactor can only ever display gate-verified
   numbers. This is the single most valuable structural decision (ADR-0005/0014).
2. **Frozen, UID-keyed, minutes-axis determinism.** `Task.unique_id` as the *only* cross-version identity;
   durations as integer working minutes; days conversion only at the presentation boundary with
   `Decimal`/`ROUND_HALF_UP`. Parity assertions reproduce bit-for-bit; the units boundary never drifted (0007).
3. **CPM values derived, never stored.** The engine recomputes dates/float from source-of-truth fields, so
   they cannot silently drift from their inputs (0007).
4. **Std-lib-only runtime + out-of-process MPXJ.** Kept the supply chain tiny and the air-gap trivially
   provable. MPXJ runs as a subprocess (`java … MpxjToMspdi`), never in-process JPype — the JVM stays out
   of Python and everything reuses the tested MSPDI path (0001/0009).
5. **Cite everything; never fabricate; document the precise delta.** NA reads "—", never a placeholder 0.
   Every divergence from a reference tool is documented to the day with citations. This is what made every
   later reversal *auditable* instead of a silent correctness regression, and it is why the parity story is
   defensible in a testimony context (0005/0014; HSD10/SN04 basis deltas).
6. **The engine owns citations; the AI only rephrases — and never traverses the schedule.** The founding
   AI principle (0114): inject the engine's *exact, cited* driving-path facts and have the model only
   narrate; it never walks the schedule itself, and a one-click no-AI path always exists. Decoding is
   forced to **temperature-0 + a fixed seed** so narrative is reproducible (0136). Local-AI narrative is
   bolted *on top of* already-computed, cited figures — the model never originates a number that reaches
   the analyst in the gated modes (0017). Graphical AI reports use **vendor-free DrawingML**, not a
   rasterizer, to stay inside Law 1 (0124).
7. **ADR discipline from commit 0.** "Any single context window may be lost… decisions must survive in git,
   not chat history." Append-only Nygard-format ADRs with explicit supersession made a 271-decision,
   many-session autonomous build coherent (0000).
8. **Vanilla-JS + strict CSP was the right call for THIS threat model.** For a CUI, air-gapped, testimony
   tool, "nothing fetched at build or run time" is the strongest posture; `node --check` is the only "build."
   (0019) — see Part VII for the cost side of this trade.
9. **Verify-everything audit protocol** (ADR-0240) and **deterministic perf harness** (ADR-0249): op-count /
   residency gates, never wall-clock; node DOM harnesses that actually execute vendored JS. A flaky gate is
   worse than none.

---

## Part III — What we TRIED that did NOT work (dead ends, reversals, wrong fixes)

> This is the heart of the log. Each entry: what we tried → why it failed → what replaced it.

**A. The central CPM tension: pure-logic vs MS Project's stored, progress-aware dates.**
Recurred for the *entire* project. Pure-logic CPM gave "+16 days too much slack" on late-completed
activities at M6 (0011). We deferred the mismatch as "documented residuals" — "accepted (not closed)" at M9
(0014) on the theory that independence beat imitation. **That theory broke on real files:** ADR-0080
(2026-06-18) found the tool reporting **2 critical / 0 negative-float vs Acumen's 33 / 31** on a progressed
schedule. The engine had to consume the file's stored `TotalSlack`/`Critical` after all. *Months of
"residuals" were one deferred decision.* **Lesson:** decide "independent recompute vs source-tool fidelity"
up front, **per surface** (the forensic driving-path wants an independent CPM; the DCMA audit must mirror
the source tool).

**B. Clean goldens gave false confidence.** Every committed golden was all-active, all-8h, whole-day,
well-named. Whole divergence classes were invisible to `pytest -m parity`: inactive tasks counted in every
DCMA denominator (M1), 24-hour continuous-ops calendars parsing as 8h×7 (H3, still open), sub-day
arithmetic, and a `>=100 %` "hide completed" bug that clean 100.0 % goldens masked (0051 — real exports
report finished work at 99.x %). **Lesson:** build goldens with **population diversity** — a fixture per
*behavioral edge* (elapsed tasks, non-480 calendars, in-progress %, hostile/empty names), not just per metric.

**C. The 480-minutes-per-day hard-code — a serial footgun.** The same "assume an 8-hour day" bug recurred
across modules: `recommendations.py` (D13), `sra_conclusions._wd` (0221, where two metric families visibly
disagreed), the ch-01 critical basis (0220, pure-logic 90 vs effective 34), and the 24-hour-calendar parse
falling back to 8h (0224). The real calendar was never threaded through *once and for all*. **Lesson: never
hard-code the working day; thread the schedule calendar through every day/float conversion from day one** —
the single most repeated bug family in the project.

**D. Span-snap (ADR-0045) was a misdiagnosis; removed in ADR-0116.** The whole-day "afternoon-shift
raggedness" snap was a wrong explanation of a resource-*leveling* date discrepancy. With snap ON,
`compute_driving_slack(UID 152)` matched only **325/783** predecessors; with snap OFF (raw working-minute
span) the engine reproduced SSI's path 61/61 and slack within one working day for 782/783. **A design
decision stood for weeks on a bad root cause.** Its own erratum also admits "matches SSI exactly" was
overstated (SSI's focus UID was never recorded, so absolute tiers are unreproducible). **Lesson:** record
the reference tool's focus/target UID **at capture time**, and don't lock a fix until the root cause is proven.

**E. Formula changes on "Bible authority" alone were provisional and repeatedly wrong.** BEI (0085 → 0089,
"both wrong"): ADR-0085 added a `baseline_duration` filter and a missing-baseline term on the `.aft`
formula-library alone; when the operator's real Acumen ribbon exports arrived, BEI was off (0.52–0.53 vs
0.51) and had to be reimplemented verbatim. Same story for Insufficient Detail (0012 → 0084 superseded),
SPI(t) (count-based 0.27 vs Acumen's duration-ratio 0.56, only resolved by the `.aft` audit at 0110), and
two different indices both named "CEI" conflated until separated (0052). **Lesson:** get the authoritative
metric library **and real reference-tool *output*** before implementing a metric; a formula audit confirms
*structure*, not *values*.

**F. Data-date reschedule of in-progress tasks — attempted twice, reverted both times, then permanently
refused.** Two localized attempts (0108) regressed the correct EVM finish *and* broke Project2/5 parity.
Root reason: MS Project reschedules remaining duration only when *behind*, and an ahead/behind call is not
safely reverse-engineerable from two snapshots — a Law-2 (fidelity) violation. Left deliberately un-built
pending a Fuse oracle (0136/0143). **The canonical "choose no number over a fast wrong number" example.**

**G. The AI figure-gate laundering channel + oscillation.** The digit-multiset gate kept getting outflanked:
prose injection ("DELIBERATELY CONCEALED fraud" survived a digit-only check — H2/0132), sign-blindness
(`-5 days` → `5 days behind` — M6), number-words ("Twelve activities" invisible — M4, still open), the
ungated translate path (H1, still open). Worst: **ADR-0138's "laundering channel"** — ISO-date fragments
tokenizing into month/day pseudo-figures + a ±0.05 tolerance laundered ~33 % of invented small integers
*with* a "tool-verified" footer. **Three individually-reasonable figure-gate changes composed into an
exploit; 26 confirmed defects were sitting behind a green gate.** The gate also oscillated: strict wholesale
discard (0031) blocked legitimate derived analysis → interpretive default (0035) → annotate default (C2).
**Lesson:** design the value/identifier/**semantic** role model **once**, not in composable layers; a
digit-multiset gate is a partial control, and the durable fix is the semantic model the code itself concedes
is future work.

**H. Caching became its own source of correctness bugs.** ADR-0261 claimed staleness was "structurally
impossible"; **ADR-0263 refuted it** — mixed-epoch cache pairing served *persistent* wrong numbers (a
P3-memo-poisoning race). Fixed by making the inconsistent pair unrepresentable. **Lesson:** a scale-driven
caching layer in a single-process session store needs a **consistency model designed up front**, not
accreted; and "structurally impossible" claims must themselves be adversarially refuted.

**I. Security machinery built but never wired (dead defense-in-depth).** ADR-0241 found the Law-1
log-redaction and egress guards were **dead code with zero runtime callers — their docstrings lied.** Wired
to fail closed at startup. Several controls (redaction, `assert_local_only`, egress set) still surface in
audits as "built but only run in tests." **Lesson: build-it is not wire-it.** Security machinery needs a
startup *call* **and** a startup *assertion*, plus a test that the call actually happens.

**J. Deployment freshness — "the PR didn't fix it" saga.** Three sequential misdiagnoses of one operator
report (0148/0149): the wheel was built 14 h before the fix; the installer test pinned only the version
*string* (still 1.0.0); no `/static` Cache-Control + a fixed port served stale JS for days; and the real
"popup" was telemetry subprocesses spawning console windows with no `CREATE_NO_WINDOW`. Separately, the
wheel once omitted `web/static`/`web/examples` — invisible under editable installs, a startup crash only on a
*deployed* wheel (0144). **Lesson:** deployment-freshness gating (byte-compare embedded wheel vs `src`,
cache-busting, version-string-*independent* checks, installer smoke tests that run the WHEEL) belongs in the
design, not after an incident.

**K. Cross-project blending.** ADR-0225's grouping was display-only, so every multi-version page produced
"cross-project nonsense" until ADR-0258 scoped analysis to the active project — which then had to *pool*
untitled files after the test suite "proved the alternative wrong." **Lesson:** multi-tenant/multi-project
scoping is a data-model decision, not a display filter bolted on later.

**L. A security gate that bricked the UI.** ADR-0264's Origin gate 403'd *every* real-browser form POST
because its tests only exercised `fetch` POSTs; under `Referrer-Policy: no-referrer` Chromium sends
`Origin: null`. Fixed with OWASP Fetch-Metadata (`Sec-Fetch-Site`) in 0268. **Lesson: verify a fix the way
the bug manifests** — in a real browser for UI/security, not just via `TestClient`.

**M. Verify-your-own-verification failures.** ADR-0250 found ADR-0247's *own* redaction fix incomplete (the
spaced-path `C:\Users\John Smith\` case still leaked). Audit finding L2 first came back **REFUTED — and the
refutation itself was wrong** (the repro used field `probability` instead of the real `prob`, and a UID that
didn't exist, so the risk never fired). **Lesson:** a refutation can be a test artifact; verify your own
verification before trusting a "refuted."

---

## Part IV — Recurring friction (process & tooling)

- **Handoff staleness / drift guards were bolted on reactively three times.** HANDOFF went "stale by one"
  every cycle; a HANDOFF referencing ADR-0046 when disk had ADR-0057 forced `test_handoff_references_latest_adr`;
  then a 64 KB + single-`# (prior)` size guard; finally the auto-inject SessionStart hook + archive split
  (0246). **Durable-state hygiene deserves guards and auto-injection from day one.**
- **Squash-merge / stale-branch pain.** Squash-merges make stacked branches conflict (standing rule: always
  branch fresh from `origin/main`; `git fetch origin` first). After a merge the stale remote-tracking ref
  made the stop-hook mis-report GitHub's own squash commit as an "unverified unpushed commit" → a
  `--prune` restart rule. Idle-container reclamation later resurrected five stale June branches.
- **Environment/toolchain gotchas.** Fresh containers ship without the dev toolchain (`pip install -e .[dev]`
  first); the PATH `pytest` is a separate uv tool that can't see the editable install, so the gate must run
  via `python -m pytest`.
- **CI flakes** were predicted and pinned rather than suppressed: `pip-audit` red on `setuptools`
  PYSEC-2026-3447 (pinned `setuptools>=83`), an earlier `requests`/`urllib3` false positive dismissed as
  ambient container noise, a bandit B608 HTML false positive (`# nosec`).
- **Lockstep wheel + 9 installers.** Every `src/` change must rebuild the wheel and all 9 installers or a
  byte-comparison test fails — real friction, but it is what caught the missing-`web/static` crash.
- **The `web/app.py` monolith tax.** "The entire UI in one file" (line refs past 15,000; E501-exempt) is
  touched on nearly every PR and was the *direct* cause of the perf pain in 0257/0261 (a single chokepoint
  building the whole analysis just to read one `.cpm` field). ADR-0261 explicitly *declined* the
  lazy-`_Analysis` refactor because the blast radius across "dozens of consumers" wasn't worth it — i.e., the
  monolith had become too risky to refactor. See Part VII.
- **Diagnose UI in a real browser.** BFCache overlays, console-window flashes, and two DOM-XSS bugs were
  invisible in the Linux container and only reproduced under headless Chromium.

---

## Part V — Security & CUI lessons

- **Both non-negotiable laws survived aggressive falsification every time.** Across three QC audits
  (2026-06-25 = 26 items, 07-13 = 33, 07-14) **no audit ever found a CRITICAL active data-egress defect.**
  The architecture (no runtime HTTP client, loopback-only AI failing closed, strict CSP) is sound.
- **Real vulnerabilities were found and fixed** (the audits earned their cost): a **BLOCKER stored DOM-XSS in
  `path.js`** (an opposing party's `<Alias>` custom field flowing through `innerHTML`, exfiltrating via
  `location=` — reproduced in Chromium, ADR-0245); a second `</script>`-breakout XSS (0250); a loopback guard
  that validated host but not *scheme*, so `file://localhost/etc/passwd` read local disk while a `# nosec`
  claimed it couldn't (0058); redirect-following that could bounce CUI off-machine (0058); a corporate proxy
  intercepting `127.0.0.1` so local AI never connected (0070).
- **The compensating control that always held:** the global CSP blocks exfiltration on every response even
  when a narrower gap exists — defense in depth is why no *proven* leak ever occurred.
- **Still-open, care-required items** (as of the last audit): the ungated `_ai_translate` path (H1),
  number-word bypass of the digit tokenizer (M4), an incomplete accusation denylist (M5). These are Law-2
  fidelity items awaiting a live local model to exercise them.

---

## Part VI — Parity & correctness lessons

- Parity is now broadly **ENGINE == FUSE, UID-exact** against committed Acumen/SSI oracles (SSI driving
  slack 108/108 at UID 145; High Float 44/44; Baseline-Start-Compliance resolved). This only became possible
  once the reference exports were committed (the CUI-posture reversal, ADR-0151/0152).
- **Accepted, gate-locked residuals are documented to the day, not smoothed** — SN04's 96↔99 one-UID swap
  (Fuse reads MS Project's progress-aware Critical flag; engine recomputes pure-logic CPM float), HSD10's
  −148 vs −134 net-finish basis delta. Keeping these explicit is what makes the numbers defensible.
- **The parity gate is only as good as its fixtures** (see Part III-B). Add a fixture per behavioral edge.
- **Round-trip-only bugs exist:** the MSPDI generator emitted summary rollups top-down (year-0001 baselines)
  and put `<Active>`/`<Manual>` where MS Project ignores them (link application silently broke) — catchable
  only by importing into real MS Project, not by reading our own XML back. The tool's *own* JSON save was
  also silently lossy at schedule level (per-task calendars, resources, project calendar all dropped —
  0131 C1 → 0140), so a "save and reload" was not identity. **Test serialization round-trips for identity,
  both against the foreign format and your own.**
- **The most testimony-dangerous defect class was fabricated float.** The backward pass fabricated
  *negative* float (TF = −480) on weekend-spanning elapsed tasks (0139), and a "fix" (NEW-1) was itself
  wrong on the float axis — invented values are far worse than "—" in a testimony exhibit. Compute float on
  the working grid in cap space; **never let an arithmetic edge invent a number.**

---

## Part VII — Architecture & scalability lessons (the big-picture regrets)

1. **Scale was a retrofit, not a foundation.** Capabilities were added far ahead of the performance layer.
   Removing the 10-file cap (0225) *preceded* the scale work (0226); a wholesale `_invalidate_scope`
   cache-nuke forced a late, parity-risky deep-perf epoch-cache overhaul (0261). Earlier lazy analysis and
   content-hash-keyed caches would have avoided the churn. **Design the scale/caching model up front.**
2. **The `web/app.py` monolith is the recurring tax — and the auditability asset.** It is the single biggest
   structural drag (every PR touches it; it became too risky to decompose). *Yet* the monolithic
   server-render + vendored-JS is exactly what makes the strict-CSP air-gap cheap to prove. **The lesson is
   not "monolith bad" — it is: separate the API layer from the presentation layer, and modularize routes by
   domain, from day one, without giving up the air-gap.** (See the rebuild prompt for how.)
3. **No bundler/framework was correct for the threat model but expensive in UI velocity.** The cost was real:
   inline-handler elimination for strict CSP (0268), a hand-built i18n DOM-translation layer, CSP upload
   workarounds (0225). A modern component framework would have made the twelve-chapter redesign far cheaper —
   *if and only if* it could be pinned fully offline and still pass the air-gap test. This is the central
   open architectural question the rebuild prompt resolves explicitly.
4. **The scalability ceiling remains:** full schedules still materialize in RAM; summary-only eviction is a
   follow-up. A tool that targets "thousands of activities across dozens of versions" needs streaming
   importers and out-of-core analysis as first-class, not deferred.
5. **Local AI should be planned from day one, not bolted on at M12.** The figure-gate, operator-mode gating,
   and citation model are load-bearing safety features that had to be retrofitted and hardened repeatedly.
   Treat "AI narrative over cited engine figures, fail-closed, semantic role model" as a founding subsystem.

---

## Part VIII — Open risks & owed items (snapshot at v1.0.76)

- **R-01 CUI egress** — Low likelihood / Critical impact; controls in place; the soft spot is any
  built-but-not-fully-wired runtime guard.
- **R-06 DCMA interpretation drift** — thresholds may not match the user's authoritative reference.
- **R-07 local-model quality** — hallucinated citations; the figure-gate is the (imperfect) compensating control.
- **R-11 source-pending importer mappings** — MSPDI `LinkLag` scaling, XER `cstr_type`/`target_*`→baseline
  reasoned but never confirmed against a real export.
- **Owed by the operator (blocking):** a PowerShell crash log + a real large dataset for on-machine perf
  re-validation (0261); a Claude-Design prompt for the Portfolio US-map/site-drill (0258).
- **Queued (file-free, one gated PR each):** Latin Hypercube sampling (Hulett #11), risk-critical Gantt tint
  (Hulett #12). **PARKED:** #13 XER per-task calendars (no reference `.xer`).

---

## Part IX — "If we rebuilt it, knowing what we know now"

The consolidated improvement themes below are the seed of the **autonomous rebuild prompt** delivered
separately to the operator (an MS Word document). In one line each:

1. **Thread the calendar everywhere from day one** — no `480`/8h assumption survives anywhere (Part III-C).
2. **Decide independent-recompute vs source-fidelity per surface, up front** (Part III-A).
3. **Goldens with population diversity before any metric ships** (Part III-B, VI).
4. **Reference-tool *output* is the only parity basis — never "Bible authority" alone** (Part III-E).
5. **Separate API from presentation; modularize routes by domain; keep the air-gap** (Part VII-2).
6. **Resolve the framework/bundler question explicitly against an offline-pinned toolchain** (Part VII-3).
7. **Scale + caching + consistency model designed up front, streaming importers first-class** (Part VII-1/4).
8. **Local AI as a founding subsystem with a semantic role model, not a composable digit gate** (Part III-G).
9. **Security controls wired + asserted at startup, verified the way bugs manifest (real browser)** (Part III-I/L).
10. **Deployment-freshness and durable-state hygiene guarded from commit 0** (Part III-J, IV).

---

## Appendix A — Notable reversal / supersession index

| Topic | First attempt | Reversed / superseded by | One-line reason |
|---|---|---|---|
| CPM basis (pure-logic vs stored) | 0011/0014 "residuals accepted" | 0080 (consume stored) | Real progressed files: 2 vs 33 critical |
| Span-snap driving path | 0045 | 0116 (removed) | Misdiagnosed leveling as raggedness |
| BEI formula | 0085 | 0089 | Bible-only formula was wrong vs Acumen output |
| Stored-float bands | (attempt) | 0141 (reverted) | Broke pinned Acumen critical counts |
| Data-date reschedule | 0108 (×2) | 0136/0143 (refused) | Ahead/behind not reverse-engineerable |
| AI figure gate | 0031 strict → 0035 interpretive | 0129/0137/0138/0145 | Laundering channel; oscillation |
| Handoff drift | ad hoc | 0246 (auto-inject + archive) | Went stale/oversized repeatedly |
| Cache staleness "impossible" | 0261 | 0263 (refuted) | Mixed-epoch pairing served wrong numbers |
| Redaction fix | 0247 | 0250 (still leaked) | Spaced-path case incomplete |
| Origin gate | 0264 | 0268 (Fetch-Metadata) | 403'd every real-browser form POST |
| Cross-project scope | 0225 (display-only) | 0258/0262 | Produced cross-project nonsense |

---

## Change log

> **Append a dated entry every session (the daily-update mandate).** Newest first.

- **2026-07-19** — **Log created.** Deep-dive of the full repo (271 ADRs, 7.2K-line session log, 5.7K-line
  handoff archive, three QC audits, parity/fuse reports) via six parallel research agents + lead
  synthesis. Established this file as the cross-cutting lessons layer and wired the daily-update mandate into
  `CLAUDE.md`'s "Durable state" section. Companion deliverable: an autonomous "rebuild-from-scratch" Claude
  Code prompt (adversarially hardened over two attack rounds) delivered to the operator as an MS Word
  document. No engine/parity change. (ADR-0271.)
