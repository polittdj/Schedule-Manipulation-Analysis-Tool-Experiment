# Lessons Learned — Schedule Manipulation Analysis Tool (POLARIS / SMAT)

> ## ⏱ STANDING RULE — UPDATE THIS LOG EVERY WORKING DAY
>
> This is the project's **living lessons-learned log**. It must be updated **daily** (every
> session that changes the codebase, and at least once per working day of active work).
> Append a dated entry to **Part VIII** at the moment you learn something — a bug that fought
> back, a fix that had to be reverted, a decision that paid off or backfired, a dead end, a
> parity surprise, a packaging or deployment gotcha, a process friction. Do **not** batch it
> for "later." The rule is mirrored in `CLAUDE.md` so every session sees it.
>
> Format for a daily entry: `### YYYY-MM-DD — <one-line headline>` then 2–8 tight bullets
> (what happened · what we tried · what worked / what didn't · the lesson). Keep the analytical
> sections (Parts I–VII) current too when a lesson generalizes — promote a recurring daily
> observation up into the relevant themed section.

**What this file is.** A single, durable, honest record of *everything we have done to date, what we
tried, and what did not work* — built as a retrospective across the full history: the original
build spec (`AUTONOMOUS-BUILD-PROMPT.md`), 271 ADRs (`docs/adr/0000–0270`), the ~7,200-line
`SESSION-LOG.md`, the ~5,700-line `HANDOFF-ARCHIVE.md`, four formal audits, and the current source
tree. It exists so a future engineer (human or agent) can learn from the road already travelled
without re-reading all of it, and so we can answer the standing question: **"knowing what we know
now, how would we build this better?"** (Part VI.)

*Created 2026-07-19. Owner: the lead engineer of record for the session. Companion docs:
`HANDOFF.md` (live status), `SESSION-LOG.md` (full history), `docs/adr/` (decisions).*

---

## Part I — Project snapshot (what this is)

**POLARIS** (*Program Oversight & Logic Analysis for Risk & Integrity of Schedules*) — a local,
offline, CUI-safe **forensic schedule-analysis** desktop tool. It ingests MS Project / Primavera
schedules, runs CPM + DCMA-14 / Acumen Fuse v8.11.0 / SSI / EVM parity metrics + manipulation-trend
detection + Schedule Risk Analysis, and serves an interactive, locally-rendered "Mission Ops" report
with a cited local-AI narrative.

| Dimension | Current state |
|---|---|
| **Version / scope** | v1.0.76; 271 ADRs (0000–0270); ~2,400+ tests; SCHEMA 2.8.0 |
| **Stack** | Python 3.11+/3.13, FastAPI, **std-lib-only I/O**, server-rendered HTML + Jinja |
| **Frontend** | ~58 **vendored, hand-written** vanilla-JS/CSS files (no framework, **no bundler**, no CDN); `node --check` only |
| **`.mpp` path** | Native `.mpp` → MSPDI via vendored **MPXJ (Java 17+)**, out-of-process, auto-discovered |
| **AI** | Local **Ollama** / OpenAI-compat, **loopback-only, fail-closed**; cloud never reached by default |
| **Packaging** | 9 one-file installers (3 RAM/GPU tiers × 3 OS families), wheel byte-locked to `src/` |
| **The two laws** | (1) **Data sovereignty** — nothing about a schedule ever leaves the machine; (2) **Fidelity over speed** — numbers must match the reference tools, gate-locked (`pytest -m parity`) |

**Module map:** `model/` (frozen pydantic, UID-keyed, integer working-minutes) → `engine/` (CPM +
~28 metric families + forensic layers) → `importers/` (mspdi/xer/json/mpp-mpxj) → `web/app.py` (the
entire UI in one ~15k-line file) → `exhibits/` (headless report pack) + `ai/` (narrative polish over
already-computed, cited figures).

---

## Part II — What we've built to date (capability inventory)

**The original build (sessions A1–A18, milestones M1–M17, → v1.0.0, 2026-06-05…10).** Greenfield
wipe → durable-state scaffold → domain model + units → MSPDI/XER importers → native `.mpp` via MPXJ →
CPM + float → **SSI driving-slack parity** → Acumen Schedule-Quality + DCMA-14 → EVM + change metrics →
consolidated **parity acceptance gate** (CI-wired) → DCMA audit + cited recommendations → version diff
+ manipulation trends → pluggable local AI + cited narrative → FastAPI web shell → dependency-free SVG
visuals + air-gap test → desktop launcher → docs/closeout. Declared **DONE** at ~645 tests / 32 ADRs.

**The post-"done" expansion (v1.0.0 → v1.0.76, 2026-06-10…07-19).** The tool then grew ~8× in ADRs
and ~4× in tests through continuous, operator-driven, one-PR-per-feature work:

- **Metric families:** CEI (+ variants), HMI, FEI/BRI, Float Ratio™, the 10-metric SEM family,
  Insufficient Detail™, Ribbon (Fuse-calibrated), on-time indices, Devaux DRAG — all validated
  against the NASA `.aft` "Bible" and Acumen exports.
- **Forensics:** version diff, manipulation signals, per-change counterfactual (`change_effects`),
  driving-path between two UIDs, CP-volatility (membership churn), Schedule Integrity page.
- **Risk/statistics:** Schedule Risk Analysis (seeded std-lib Monte-Carlo), unified risk register,
  SSI SRA (factor tables/OAT/5×5), schedule **margin** dashboard + NASA reserve sizing, credibility-
  weighted estimates, **JCL/FICSM** joint cost-&-schedule confidence, **correlation matrix +
  eigenvalue feasibility** (Gaussian copula).
- **Assessment:** NASA STAT / GAO-10 / SRA-readiness **scorecards**.
- **Views:** Trend (10+ versions), Bow Wave/CEI, Forecast (3 methods), Executive Briefing, Compare,
  Metric Workbench, Performance Summary, Standards & Execution Indices, Portfolio Manager.
- **Platform:** grouped ingestion + Portfolio, SQLite parse/summary cache, batch JVM, deep
  performance work (~10× cold `/performance`), MS-Project-faithful **saved filters/groups**,
  MS-Project-style Gantt everywhere, click-to-drill on every chart family, Excel round-trip templates.
- **Presentation:** the **"Mission Ops" 4-theme redesign** (console/daylight/apollo/jarvis) rolled out
  as a 12-chapter story spine, one page-shell per PR; POLARIS brand; role-selection front page; EN/ES/
  FR/DE/PT i18n; accessibility (focus/reduced-motion/non-color cues).
- **Compliance/deploy:** CUI pre-commit guard, net-egress guard, strict CSP (`script-src 'self'`),
  SEC-2/SEC-3 (Host allowlist + Fetch-Metadata CSRF gate), 9 installers with no-admin Java, self-
  diagnosing launcher, headless exhibit CLI.

---

## Part III — How the build was run (the method that *worked*)

The process discipline is the biggest success of this project and should be **kept** in any rebuild:

- **Git-as-memory, not chat-as-memory.** Every decision is an append-only **ADR**; every session
  writes a **HANDOFF** ("where we are / what's next") and a **SESSION-LOG** entry; a plan/RTM tracks
  requirements. This is what let a months-long autonomous build survive context compaction and
  resume cleanly across ~130 sessions. **Verdict: essential and non-negotiable.**
- **One milestone per session, stop early with margin.** Sized work to fit a session and triggered
  the end-of-session ritual proactively so a timeout could never lose an uncommitted decision.
- **Parity as a gate-locked acceptance test** (`pytest -m parity`). A strong, cheap invariant
  ("parity untouched" / "byte-identical") is what let the app grow ~10× while the engine stayed
  stable — nearly every UI/perf/importer change verified it was a no-op on the goldens.
- **"Fidelity over speed / never fabricate a number."** Repeatedly stopped bad fixes: composite
  scores and unreproducible residuals were **deferred or pinned-with-their-delta**, never guessed.
- **Verify-first, adversarial audits with a validating lead** (ADR-0240: "READ EVERYTHING, ASSUME
  NOTHING, VERIFY EVERYTHING; a mistaken fix is worse than the drift it chases"). Multi-agent audits
  found real, shippable defects *every time* — but their value came from the lead re-verifying each
  finding against code + executable tests, and recording the **refuted-vs-confirmed** split.
- **Turn every process failure into an executable guard.** The drift guard, the wheel↔source
  lockstep test, the metric-dictionary sync test, the `__version__`-from-metadata pin, the air-gap
  scanner — each was born from a real miss. Prose reminders decayed; tests didn't.

---

## Part IV — What we tried that did NOT work (by theme)

*The honest catalogue. Grouped by theme; each item is what was tried, why it failed, and how it
resolved. ADR/PR references are verifiable in-repo.*

### A. Parity & fidelity
- **Stale golden hid real bugs.** The committed `Project5` golden carried 37 stored-critical
  activities vs the authoritative file's 4, sustaining a phantom "High Float +1" residual and a
  cluster of §E change-metric residuals. Refreshing it forced a ~37-test re-baseline (ADR-0109/0112).
- **BEI was wrong twice.** ADR-0085 "fixed" BEI with a baseline filter + missing-baseline term; real
  Acumen output showed **both additions were wrong** and they were reverted (ADR-0089); the numerator
  was *still* subtly wrong (all-Normal vs baselined-**due**) and only corrected at ADR-0176 — the
  goldens had coincidentally matched all along.
- **Composite scores (SQ 88, DCMA 57/49) were never reproduced** — Acumen's weighting is unpublished;
  "reproducing them would be fabrication (Law 2)." Permanently deferred, not guessed.
- **The §E slip/erosion "research wall."** Naive "later finish" gave 99/100 vs golden 9/10 because
  the whole schedule rides a ~99-day data-date advance; several counts (SN04/06/07/09) proved
  **not reproducible from static MSPDI at all** — an artifact of MS Project's progress-aware
  scheduler — and were formally *accepted* as gate-locked deltas (ADR-0014).
- **Metric definitional drift.** The `.aft` audit found the tool's `SPI(t)` was a *different metric of
  the same name* (Earned-Schedule vs Acumen's per-activity duration-ratio), explaining the EVM2
  residual (0.27 vs 0.56); resolved with a dual SPI(t) (ADR-0110/0176).
- **The reference itself was defective.** The Power BI deck had four DAX authoring defects and a
  dangling `RatioMeasure`; the tool declined to reproduce them and declared the deck the outlier
  (ADR-0033). A vendor SEM "Delta" cell was proven non-reproducible and documented, not reverse-fit
  (ADR-0238).

### B. CPM / calendar / engine correctness
- **The in-progress data-date reschedule gap (ADR-0108).** MS Project reschedules remaining duration
  from the data date only when *behind*; the pure-logic CPM doesn't. **Two localized fix attempts each
  regressed EVM1 and broke Project2/5 parity and were reverted** — "a known gap beats a fast wrong
  number." Surfaced as a labeled forecast instead; still the single most consequential open engine gap.
- **Driving-slack span-snap was a misdiagnosis (ADR-0045 → reversed by ADR-0116).** A whole-day
  "span snap" was added to cure a "+1-day raggedness" that turned out to be a *resource-leveling*
  discrepancy; with the snap ON the engine matched only 325/783. Root cause: the fix had been
  "spot-checked against a handful of activities; never run end-to-end against a full SSI export."
  Removing it + honoring lunch calendars + per-task calendars reached 783/783 (ADR-0117/0118).
- **The "2 vs 76" critical-path bug (ADR-0150).** Path displays used the pure-logic CPM critical set,
  which on a progressed file collapses to the tail; the correct instrument (`is_effective_critical`)
  *already existed* — the displays just never used it. The same class recurred on chapter-01 (90 vs
  34, ADR-0220).
- **Silent calendar rescalings.** 24-hour continuous-ops calendars (`00:00→00:00`) collapsed to 8h/day
  (ADR-0224); elapsed "eday" durations fabricated negative float (ADR-0139); SRA day-counts divided by
  a hard-coded 480 min/day regardless of the real calendar (ADR-0221) — all **passed the figure gate**
  as authoritative numbers.
- **XER identity self-own (ADR-0185).** The importer keyed tasks on P6's renumbering `task_id`,
  violating the repo's own "never the row id" law → flat-0.00 CEI across a series. Fixed to
  `CRC32(Activity ID)`.

### C. The AI citation "figure-gate" saga (~8 hardening rounds)
The guarantee "no unsourced number reaches the analyst" was falsified, patched, re-falsified, and
hardened across **ADR-0129 → 0131 → 0132 → 0133/0135 → 0134→0137 → 0138 → 0145 → 0239** — and two of
those fixed defects in earlier "closed" fixes:
- The **default interpretive mode passed model-invented numbers** verbatim (a test even pinned
  `31415` reaching the client) → three modes, honestly scoped (ADR-0129).
- Strict mode was **falsified**: ISO-date fragments + a ±0.05 tolerance **laundered ~33% of invented
  integers with a tool-verified footer**; identifier digits re-roled as values; empty task names
  shredded the fact text (ADR-0138). Also sign-blindness (`-5` → "5 behind"), number-words, accusatory
  terms the engine never asserted, and the **entirely ungated translate path** (ADR-0239).
- **Lesson embodied:** token matching can police a number's *presence/value* but not its *meaning*;
  each tightening had to be collision-safe (fail-open on ambiguity, fail-closed on contradiction) or
  it produced strict false-positives. A denylist/tokenizer is inherently partial.

### D. Frontend / UI
- **A full redesign was eventually forced (ADR-0195+).** The UI accreted through dozens of one-off
  operator tweaks with no shared system — the **Reset button was relocated four times** (once landing
  exactly under the telemetry dock so it read as missing), the globe moved twice, tooltips double-
  rendered with styled callouts, a font cap made expanded charts render *tiny*. This churn is what
  motivated retrofitting a **design-token system + chart contract** and a 12-chapter story spine.
- **JS "tested" by source-grep.** Real UI defects (Workbench rendering `0.00` instead of "—", a CAM
  filter matching nothing due to a shared default `Query()` instance, briefing tables crushed to one
  char/line) hid behind green substring tests until a node-DOM harness arrived (late and partial).
- **Stored DOM-XSS (ADR-0245).** An attacker-controlled custom-field label flowed into `innerHTML` —
  first-party code execution in a CUI tool (a Law-1 exfil path with `'unsafe-inline'`).
- **Falsy-zero display traps recurred** across `/cei`, `/forecast`, EVM: CEI 0.00 rendered green,
  0.0 rates rendered "n/a" — the same `(x or 1)`/truthiness bug class in many places.

### E. Packaging, installers & deployment (all found by *executing*, never by inspection)
- **"The PR did not fix it" (ADR-0148).** A merged overlay fix never reached users because all 9
  installers **embedded a wheel built 14 hours before the fix**; browsers also served stale JS with no
  cache-busting. → version-busted URLs + a byte-level **wheel↔source lockstep test**.
- **The wheel omitted `web/static` (ADR-0144)** → deployed installs crashed at startup while every
  `pip install -e` dev env worked. "Every prior 'installer verified' claim covered structure, not
  execution."
- **The 17 MB MPXJ converter never shipped (ADR-0193)**; `_mpxj_home()` resolved *inside* the deployed
  venv, so no deployed install could open a native `.mpp`.
- **Windows-only field failures invisible in CI:** a PowerShell 1-element-array unroll invoked the
  character `'p'` on python-only machines (ADR-0191); a winget MSI died at a UAC prompt yet printed
  "[ok] Java installed" (ADR-0192); a windowless telemetry loop flashed a console every 5s with no
  `CREATE_NO_WINDOW` (ADR-0149); `pythonw` discarded stderr so pre-serve failures died on a dead port
  (ADR-0257).

### F. Performance & scale
- **A grid re-wrote ~10k inline styles per keystroke** on a ~1,700-row table with no filter debounce —
  jank, deferred then fixed via the perf harness.
- **Perf work was gated behind proof, correctly.** HIGH-parity-risk optimizations were **deferred**
  until a *deterministic* regression harness existed (op counts + residency, never wall-clock —
  ADR-0249); the safe subset shipped first and a **160-hash battery proved every number byte-identical**
  before the deep-perf work landed (ADR-0261). One ADR-0261 claim ("staleness structurally
  impossible") was later **refuted** by ADR-0263 finding a mixed-epoch pairing window.

### G. Security & CUI
- **The CUI guard fought the real workflow (ADR-0152).** The operator committed the (non-CUI)
  reference intake to `main` via the GitHub web UI (bypassing the local hook), which **wedged every
  `git merge origin/main`**. An `inherited_from_main` byte-identity exception had to be retrofitted,
  and the posture formally reversed ("keep binaries out of git" → "the reference set lives in the
  repo").
- **Dead defense-in-depth.** `net_guard.assert_local_only()` and CUI log-redaction existed as code
  with **zero runtime callers** for a long time — the guarantee rested entirely on every log call being
  hand-safe (wired at ADR-0241). A redaction leak fix (ADR-0247) was then found **incomplete in the
  very next audit** (ADR-0250) — a real Law-1 leak on freshly-shipped code.
- **A security fix that would have bricked the UI (ADR-0264 → 0268).** The SEC-2 CSRF gate required a
  loopback `Origin`; under the app's own `no-referrer` policy Chromium sends `Origin: null` on
  same-origin form POSTs, so **every POST form (Wipe, Target, filters, SRA…) would have 403'd in the
  field** — invisible because the suite only ever tested `fetch`, never a real form navigation. Fixed
  with `Sec-Fetch-Site`.

### H. Testing, CI & state-doc discipline
- **Vacuous / false-confidence tests.** Startup-guard tests passed off a leftover process-global
  handler and would pass even if the wiring were deleted (ADR-0242); the air-gap scan used hand-kept
  route lists that "scanned zero routes" while green; a real-`.mpp` test gated only on one file's
  presence.
- **Silent state-doc drift, twice.** SESSION-LOG/HANDOFF fell behind `main` (ADR #102 vs #113; later
  stale-by-one) → a drift guard now pins the highest ADR + version into both docs.
- **HANDOFF grew to 417 KB** before "read the entire HANDOFF" became physically impractical → a
  SessionStart hook auto-injects only the live section + a ≤64 KB size guard (ADR-0246).
- **Coverage-gate whiplash:** driven to 99.97% and pinned at `fail_under=99.9`, then honestly relaxed
  back to 70 to match CI.

### I. Process / project management
- **Early sessions were handed fresh greenfield branches** with none of the prior work and had to
  fast-forward onto the real tip each time; squash-merges made stacked branches conflict and forced
  branch restarts; the Stop hook mis-reported GitHub's own squash commit as "unpushed."
- **Multiple audit trails were not merged** (2026-06-25 / 07-13 / 07-14), so a remediation ADR closed
  one finding set while another sat **orphaned open** under a HANDOFF that falsely read "only
  artifact-gated items remain."
- **"Done" was declared ~a dozen times and reopened every time** — by an audit or a fresh operator
  spec. See Part V.

---

## Part V — Recurring pain points & their root causes

| Pattern (bit more than once) | Root cause | Durable countermeasure |
|---|---|---|
| **Progress-aware float vs pure-logic CPM** — drove High-Float, §E residuals, "2 vs 76", chapter-01 90-vs-34 | One concept ("critical"/"float") means two things and was defined per-module | `effective_total_float`/`is_effective_critical` chokepoint (ADR-0080); still audited 3×. **Define load-bearing semantics once, centrally, early.** |
| **Golden fixtures blind to the messy population** — "it worked on the example" | Clean goldens don't exercise inactive/elapsed/progressed/ragged data — exactly the forensic target | Pair every golden with **synthetic blind-spot tests** (institutionalized ADR-0136) |
| **Placeholder `0.0` presented as a real value** | Applicability keyed on `value==0` not on population count | Key on the population count; re-found in new places (ADR-0219→0223) |
| **Hard-coded 480 min/day** | Calendar not threaded to the conversion boundary | Convert on the schedule's real minutes/day everywhere (D13→0221) |
| **Deployment ships stale relative to `src/`** | Wheel/installers regenerated by hand, forgettably | Byte-level lockstep test; "wheel + 9 installers in lockstep" on every packaged change (ADR-0148) |
| **The AI figure gate leaks in a new way** | Token matching can't verify meaning | ~8 collision-safe hardening rounds + adversarial mutation tests; documented as "future work" |
| **CI green ≠ field-ready** | Dev container ≠ operator's locked-down Windows machine | Real-OS smoke CI + self-diagnosing launcher + **real-browser** verification |
| **Stale local `main` + squash-merge restarts** | Long-lived local refs | `git fetch --prune` + `checkout -B` restart ritual in CLAUDE.md |
| **"Done" reopened by the next audit/spec** | No phase gates; continuous operator-in-the-loop with a "never block/nag" UX | Treat **audits + feature waves as a standing line item**, not an exception; use explicit phases with exit criteria |
| **Reference inputs missing / owed** — SSI focus UID repinned 143→145→152→155→67 | Fidelity work can't proceed without the oracle; oracles arrived late or never | **Charter-block** a feature whose validation oracle is missing; track missing inputs explicitly |

---

## Part VI — If we rebuilt it today: lessons by domain

> The standing question: *knowing what we know now, how would we build this better?* This section is
> the answer, organized by the areas that matter to software delivery. It also seeds the companion
> **rebuild prompt** (`docs/REBUILD-PROMPT.md` / the delivered Word doc). **Two of the operator's new
> requirements change the calculus vs the original build:** (1) the tool **no longer needs to be
> air-gapped** — it must install and run **locally and offline** for its core work, but **may reach
> the web for the cloud-AI features**; and (2) it should be able to **use a cloud AI (e.g. Claude)**
> for insight into schedules being created or analyzed. Both are reflected below.

### 1. Frontend framework, styling & bundler (React / Vue / Bootstrap / Tailwind / bundler)
- **What we did & what it cost.** Server-rendered HTML + ~58 hand-written vanilla-JS files + ~110 KB
  of hand-written CSS, **no framework, no bundler, no component model**. Chosen for the *strongest
  air-gap posture* (every served byte auditable, nothing fetched). It was genuinely the right call
  *for an air-gapped build* — but it produced an enormous hand-rolled surface, near-duplicate widgets
  on every page, JS tested only by source-grep, a single ~15k-line `app.py`, and ultimately a **forced
  UI redesign** (ADR-0195+) to retrofit the design tokens/components that should have existed from day
  one.
- **Rebuild recommendation (now that air-gap is relaxed).** Adopt a **component framework + utility
  CSS + a bundler from day one, all bundled locally** so the runtime stays offline. Recommended:
  **React + Vite + TypeScript + Tailwind** (with a small headless component library such as Radix/
  shadcn), or **Vue 3 + Vite + Tailwind** if the team prefers SFCs. A **design-token layer** (the
  Mission Ops themes) sits under Tailwind so theming stays declarative. Vite emits **self-contained,
  hashed, offline assets** — this resolves the original tension: you get components, type-safety, HMR,
  and a real test story *without* a CDN. **Keep a hard "no runtime network fetch for app assets" lint**
  so offline-first survives the framework.
- **Testing dividend.** A component framework makes **component/DOM/interaction tests first-class**
  (Vitest + Testing Library + Playwright), directly fixing the "JS tested by grep" gap that hid real
  bugs for entire releases.
- **Trade-off to respect.** A bundler adds a build step and a (dev-time) dependency tree — acceptable
  now, and the **supply chain must still be pinned, `npm audit`-gated, and vendored into the release**
  so a deployed install never phones home for JS.

### 2. System architecture & design
- **Keep:** the layered core (`model → engine → importers → web`), the **frozen/UID-keyed model**,
  **integer working-minutes** with a single presentation boundary (determinism), the **single-CPM-pass
  chokepoint**, and **derived-never-stored** CPM values. These aged extremely well.
- **Change:** split the **~15k-line `web/app.py`** — it "scaled functionally but not for reviewability"
  (the E501 exemption and un-provable escaping sweep are symptoms). Rebuild the web layer as a real
  **API (typed, versioned) + a separate SPA/SSR frontend**, so routes, HTML, and view logic aren't one
  file. Define **cross-cutting domain semantics once** (one "critical"/"float" basis object) to kill
  the recurring ambiguity. Make the **engine a stable library with a versioned result contract** so the
  UI, exhibits, and any future API all consume the same numbers.
- **Design system first, not retrofitted.** Ship tokens + a chart contract + a component kit in the
  first UI milestone; the redesign proved their value but at rework cost.

### 3. Security & compliance model (air-gap → local-offline, cloud-capable)
- **The new posture:** local install, **offline-capable core**, **online-capable AI**. This is a
  *fundamental* change from the original Law 1 (absolute air-gap). Redesign the trust model around a
  **per-project / per-document data-governance boundary** instead of a global air-gap:
  - Default **local-only**; a schedule's data leaves the machine **only** on an explicit, per-action,
    consented "send to cloud AI" with a **persistent banner naming the endpoint** and an **audit log**
    of exactly what was sent.
  - Offer **redaction/minimization** before egress (send derived metrics or a redacted fact-sheet, not
    raw task names/dates) and a **"local-only" lock** for sensitive projects (the original CUI mode,
    retained as an option).
- **Keep every hard-won control:** strict CSP (`script-src 'self'`), the loopback validation for
  *local* AI, XXE hardening, Host allowlist + **Fetch-Metadata** CSRF gate, output escaping at the
  boundary. **Wire every guard at runtime with a startup assertion AND a test that the assertion
  runs** — the "dead defense-in-depth" class (guards that lived only in tests) was a top recurring
  defect. Verify security gates in a **real browser**, not just a TestClient (the null-Origin bug hid
  for a release).
- **Decide the data-classification boundary at charter time.** The late air-gap→commit reversal
  (ADR-0152) shows an over-defensive initial posture costs rework; make the "what can go to the cloud,
  when, with what consent" ruling *first*.

### 4. AI strategy (local + cloud / Claude)
- **What we learned:** an 8B local model **can't do the math** — it mis-traced driving paths — so the
  design fed it **engine-computed, cited facts to narrate**, never to compute (ADR-0114/0150). That
  separation (engine computes → AI phrases) is correct and should be **preserved regardless of model
  size**. Determinism (temp 0, fixed seed) matters for a forensic tool (ADR-0136).
- **Rebuild with a first-class cloud tier.** Add **Claude (Anthropic API)** as a governed backend
  alongside local Ollama: use the latest models (e.g. Opus/Sonnet class) for deep narrative,
  Q&A over the cited fact-sheet, and "explain/critique this schedule" insight. **Route through the
  same citation/figure-gate** so a cloud model is no more trusted than a local one — the gate guards
  *the number*, not the model. Support **tool-use / structured output** so the cloud model returns
  citations it must satisfy.
- **Governance:** cloud calls are **opt-in per project**, consented, banner-named, audit-logged, and
  redaction-aware (see §3). Keep **NullBackend** as the deterministic offline default so the tool is
  fully useful with no network and no model.
- **Don't re-litigate the figure gate from scratch** — port the role-aware value/identifier split and
  unit-role semantics, but recognize (as the code concedes) that a token gate is partial; a cloud
  model with enforced structured citations can make the guarantee *stronger and cheaper*.

### 5. Debugging, observability & verification
- **The #1 lesson:** *inspection and green unit tests lie; execute the artifact end-to-end.* Almost
  every packaging/UI/security war story was invisible to code review and CI and only surfaced by
  **running the real installer, driving a real browser, or reasoning about the real (windowless
  Windows) runtime.** Build for this from day one:
  - **Real-OS smoke CI** (Windows + macOS + Linux) that runs the actual installer lifecycle.
  - **Playwright/browser E2E** as a first-class gate (would have caught the XSS, the null-Origin
    403, the double tooltip, tiny-expanded charts, the CAM filter).
  - A **self-diagnosing launcher** and **structured, CUI-safe logging wired at startup** (not dead).
  - **Determinism everywhere** (integer minutes, `Decimal` boundary, seeded RNG, NullBackend verbatim,
    byte-deterministic exhibits) — this is what made falsification-oriented auditing *possible*.
- **Institutionalize adversarial audits** with a validating lead and a **refuted-vs-confirmed ledger**
  — but budget them as recurring, and always re-verify the fix (fixes were themselves incomplete).

### 6. Scalability & extensibility
- **Keep:** content-hash + engine-version cache keys that **auto-invalidate** (a stale number can never
  reach the analyst), the lazy summary tier, the batch JVM, bounded offload, **disclose-don't-truncate**
  on dense cross-products, and the **deterministic** perf-regression harness. These are model
  citizens.
- **Change / plan for:** a **plugin-style metric/analysis registry** (each metric a self-describing
  unit with formula + citation + population + test) so "continue to add capabilities" is additive by
  construction — the tool already trends this way (~28 metric modules) but grew it ad hoc. A **stable
  engine result contract** lets new UIs/exports/an API attach without touching the engine. Consider a
  **real datastore** (SQLite is already the cache) for portfolio-scale history rather than in-memory
  `SessionState`. Make **large-dataset reliability** a standing role (it became one at ADR-0257 after a
  five-project lag report) — design for thousands of activities and dozens of files from day one, not
  as a retrofit (the file cap went 10 → 20 → 100 → uncapped).

### 7. Testing & QC
- **Keep:** parity as a hard gate, coverage gates (engine ≥85% / overall ≥70%), the ratcheting
  residual gate (assert the value **and** the delta), single-sourced docs with sync tests, mutation-
  checking of guard tests.
- **Add:** **browser-executed UI tests** and **real-OS install tests** as first-class from milestone 1
  (the two biggest coverage blind spots); **blind-spot synthetic fixtures** (inactive/elapsed/24h/
  progressed/ragged) alongside every clean golden; **contract tests** on the engine result schema.

### 8. Packaging & deployment
- **Keep:** one-file cross-OS installers, no-admin portable-JDK path, the wheel↔source lockstep test,
  `CREATE_NO_WINDOW` + `stdin=DEVNULL` on every subprocess (AST-guarded).
- **Change:** treat **the deployed artifact as the unit of test** from the start (real-OS smoke CI on
  day one); ship a **self-diagnosing bootstrap** that surfaces errors instead of dying on a dead port;
  keep the JVM/MPXJ dependency **explicitly packaged and discovery-tested**, not assumed.

### 9. Process, planning & scope management
- **Keep** the ADR/HANDOFF/SESSION-LOG/RTM discipline and one-milestone-per-session pacing — they are
  the reason this worked at all.
- **Change:** plan in **phases with explicit exit criteria**, not one open backlog — "done" reopened a
  dozen times because operator-in-the-loop iteration has no natural endpoint. **Merge audit trails**
  into one verification ledger. **Distinguish blocked vs deprioritized explicitly** and give every
  deferred item an owner/trigger (the installer and XER-calendars items drifted for many sessions).
  **Right-size durable state** (the 417 KB HANDOFF) with size budgets and auto-injection.

### 10. Documentation & knowledge management
- **The most-repeated defect class was documentation drift** — READMEs/FINAL-REPORT/PARITY-REPORT
  citing numbers the tool no longer produced (a *testimony* risk). **Generate docs from code + a sync
  test** wherever possible (as `METRIC-DICTIONARY.md` from `help.py`), and apply that pattern to the
  parity/final reports too. Keep this lessons log **daily-current** so knowledge doesn't rot.

---

## Part VII — Key numbers & decision index (quick reference)

- **Original build:** A1–A18, M1–M17, → v1.0.0 (2026-06-10), ~645 tests, 32 ADRs.
- **Current:** v1.0.76 (2026-07-19), 271 ADRs, ~2,400+ tests, SCHEMA 2.8.0, 0 xfails/skips target.
- **Parity landmarks:** SSI driving slack 107/107 → 108/108 (UID 145) → 783/783 (leveled IMS, UID 152);
  Acumen §A/§B/§C/§E ENGINE==FUSE on the golden pair + Hard_File; HMI/BEI/BRI/FEI/CEI exact; Net
  Finish Impact −148 (CPM) reconciled to −134 (Fuse).
- **"Bible":** NASA `.aft` = 759 named metrics; formula audit = 34 match / 3 variant / 4 drift / 52
  not-in-bible across ~93 documented metrics.
- **Scale handled:** 2,126-activity IMS; 60-file multi-project portfolio; `/performance` 0.674 s →
  0.066 s (~10×) with a 160-hash byte-identical battery.
- **Most-cited reversals:** ADR-0045→0116 (span-snap), 0085→0089→0176 (BEI), 0134→0137 (figure role),
  0152 (CUI-in-git), 0264→0268 (SEC-2), 0108 (data-date, twice reverted, still open).
- **Single biggest open engine gap:** ADR-0108 in-progress data-date reschedule (understates some
  slips; surfaced/labeled, not fixed).

---

## Part VIII — Daily update entries (newest first)

### 2026-07-19 — Lessons-learned log created
- Built this log from a full-history deep dive (271 ADRs, the 7.2k-line SESSION-LOG, the 5.7k-line
  HANDOFF-ARCHIVE, four audits, the build spec, and the source tree), synthesized via six parallel
  read-only reviewers with lead re-verification against first-hand reads of CI, hooks, the CUI guard,
  the risk register, and the cloud-AI guide.
- Wired the **daily-update standing rule** into `CLAUDE.md` so every future session maintains this log.
- Produced the companion **rebuild prompt** (delivered as an MS Word document) answering "how would we
  build this better knowing what we know now" — factoring in React/Vue/Bootstrap/Tailwind/bundler,
  architecture, security, debugging, UI, **cloud AI (Claude)**, scalability, and the shift from
  air-gapped to **local-install / offline-core / cloud-AI-capable**.
- Lesson captured today: the project's single most valuable habit — *git-as-memory + verify-first +
  turn every miss into a test* — is exactly why a retrospective this complete was even possible.

<!-- Append new dated entries ABOVE this line, newest first. Keep Parts I–VII current when a lesson generalizes. -->
