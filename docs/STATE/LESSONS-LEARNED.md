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

### 2026-07-27e — the bug was inside the fix, in the guard the ADR called load-bearing; and two sessions built the same thing (ADR-0300)
- **A defect hid inside the defence against that same defect.** ADR-0299's block states two rules
  for itself in its own comment: never destroy an installed converter, and report the deployed
  capability rather than the copy step. A single path — a candidate that is a **symlink** to the
  installed converter — broke **both at once**: `sf_realpath` used a *logical* `pwd`, so the
  spellings differed, the self-copy skip never fired, the block `rm -rf`'d the real converter and
  copied a dangling link back, and then printed `native .mpp import enabled`. **LESSON: after
  writing a guard, ask what INPUT SHAPE makes it silently not apply. Guards fail by not firing, and
  a guard that does not fire looks exactly like a guard that passed.**
- **The existing test proved the guard for the only spelling it thought of.**
  `test_a_re_run_never_destroys_the_installed_converter` passed `SF_MPXJ_HOME` as the destination's
  *own path string*, which a logical `pwd` compares equal — so it was green and the guard was
  broken one indirection away. **LESSON: when a test establishes identity between two things,
  vary HOW each is named, not just whether they match. Path equality, ID equality and name equality
  all have more than one spelling of the same thing.**
- **Review caught what the whole suite could not.** 46 installer tests, a bash harness that
  executes the real shipped block, mutation testing, a real-Windows CI leg — and this came from an
  automated reviewer reading the diff. **LESSON: executable tests prove the cases you imagined;
  review is how you find the case you did not. Neither substitutes for the other, and a rich test
  suite is a reason to take review MORE seriously, not less — it is the only remaining source of
  unimagined cases.**
- **I reproduced the reviewer's claim against the SHIPPED artifact before believing it.** The P1
  was filed against my PR, but the same helper had already merged to `main` via #446 — so the
  reproduction had to run against main's installer, not my branch's. It destroyed the converter
  exactly as described. **LESSON: when a review lands on a PR, check whether the flagged code is
  already SHIPPED elsewhere. The urgency of a finding depends on where the code lives, not where
  the diff is.**
- **Scoped the fix by reading the other implementation instead of assuming symmetry.** The
  PowerShell family has the same imprecise comparison but uses `New-Item -Force` + `Copy-Item
  -Force` and never removes the destination — so there it costs a redundant copy, not data. Fixing
  bash and *recording* the PowerShell imprecision was correct; "fix it everywhere for consistency"
  would have meant changing unexecutable code on speculation. **LESSON: the same flaw has different
  severity in different implementations. Establish blast radius per implementation before deciding
  the fix is uniform.**
- **Two sessions independently built the same fix, and the parallel one was better.** #446 took the
  diagnosis I had staged in #445, implemented it, and added a verified download I had explicitly
  scoped out. My #447 was left redundant — and merging it would have duplicated an ADR number *and*
  reverted the better work. Resetting my branch onto main cost nothing because the durable state
  (plan doc, credited in #446's ADR) had already carried my contribution across. **LESSON: staging
  a diagnosis as a committed document is what let parallel work compound instead of collide. And
  when your branch loses the race, check what the winner actually contains before resolving the
  conflict — the reflex "merge mine in" can silently revert someone else's superior fix.**
- **Left one finding unfixed on purpose.** `template.ps1` builds its candidates eagerly inside
  `@(...)`, and `Join-Path` may throw on the empty string `Split-Path -Parent` returns for a drive
  root — which under `ErrorActionPreference = "Stop"` would abort the install. I could not execute
  PowerShell to confirm it, so it went into the handoff with a suggested one-line CI probe instead
  of into the code. **LESSON (reinforces Part V): shipping an unverified fix to a hypothetical is
  how you trade a possible bug for a certain one. "Flagged, with the experiment that would settle
  it" is a legitimate deliverable.**

### 2026-07-27c — three months of green CI never ran the way the operator actually installs (ADR-0299)
- **The bug was not in the code; it was in the shape CI never tested.** The installer deployed the
  MPXJ converter from `<installer dir>/../tools/mpxj`. Every test and every CI job ran it **from the
  repo checkout**, where that path is correct — so it passed, always. The operator has no clone and
  runs a single downloaded file from `~/Downloads`, where the same expression resolves to
  `%USERPROFILE%\tools\mpxj`. It missed, warned once, and printed a green `DONE`; every `.mpp`
  import then failed, and `.mpp` is the tool's primary input. **LESSON: a test that runs from the
  developer's layout cannot validate a deploy path that has a different layout. When the deploy
  instruction is written down in the handoff — "download ONE file into Downloads and run it" —
  make CI execute exactly that, literally, including the directory it lands in. The gap was not
  subtle logic; it was a working directory nobody reproduced.**
- **A "one-file installer" is only self-contained for the parts you actually embedded.** The wheel
  was embedded, so the promise felt true; the 17 MB Java converter was not, and the header's "no
  internet needed for the tool itself" quietly covered for the omission. **LESSON: when a component
  advertises self-sufficiency, enumerate what it needs at RUNTIME and check each item is either
  embedded or fetched — a partial guarantee reads exactly like a whole one right up until the
  feature it silently dropped is the one the user needs.**
- **An optional step killed the mandatory ones.** Under `set -euo pipefail`, a failed `ollama pull`
  — explicitly documented as skippable — terminated the installer *before* the launchers,
  uninstaller and README were written. **LESSON: `set -e` makes every unguarded command mandatory
  regardless of what the docs call it. Anything labelled optional must be wrapped in `if …; then`
  (or `|| true`) or the label is a lie; and order matters — put the essential artifacts BEFORE the
  optional downloads so a late failure cannot un-install what already succeeded.**
- **My own first sweep produced twelve false positives.** The export-route scan reported 12 failing
  endpoints; every one was my harness omitting a required query param, not a defect. Re-run with
  real params derived from the engine, all 76 route/format combinations were clean. **LESSON: a
  red result from a harness you just wrote indicts the harness first. Disproving those twelve cost
  one iteration; "fixing" them would have been twelve changes to working code — and the standing
  rule is that a mistaken fix is worse than the drift it chases.**
- **Separate the live bug from the latent one, in the write-up.** `pull_model` really was
  mis-timed-out (a non-streaming multi-GB download on a 120 s budget), but nothing calls it, so it
  had never hurt anyone. It got fixed and labelled latent. **LESSON: shipping a latent fix inside a
  bug report inflates the apparent severity of the real defect and erodes trust in the next report.
  Fix it, say it was a trap not a symptom, and let the reproduced failure carry the headline.**
### 2026-07-27c — "is this an issue?" was the highest-value question of the week; and a fix that would have opened a destructive edge
- **The operator asked whether an installer warning mattered, and the honest answer was "not the way
  you fear, but yes — worse than you think."** They saw `native .mpp import stays OFF` on a machine
  where `.mpp` import was demonstrably ON. My first instinct was to reassure ("benign on the upgrade
  path — the else branch only warns"), and that was true but incomplete. **LESSON: "harmless" and
  "correct" are different findings. An installer that misreports the capability of the tool it just
  installed is a correctness defect on a testimony tool, even when nothing is broken. Finish the
  question before closing it — the reassuring half of an answer is where defects hide.**
- **I executed the shipped code instead of reading it.** Rather than reasoning about the PowerShell,
  I lifted the `# --- 3b.` block verbatim out of the *generated* `install-tier2.sh`, stubbed the
  three names it borrows, and ran it under the installer's own `set -euo pipefail` against four
  machine layouts. The bug appeared as a table row where the printed sentence and the filesystem
  disagreed. **LESSON (reinforces ADR-0289): shell and installer logic is as testable as Python —
  extract the real section from the ARTIFACT THAT SHIPS, stub the ambient names, and run it. A
  source-pin test (`assert "…" in template`) would never have found this, and indeed the existing
  pin asserted the *wrong sentence* was present and passed for months.**
- **The right assertion was an invariant, not a string.** The test I drafted does not check that a
  message appears; it checks that *whatever the installer claims about native `.mpp`, the filesystem
  agrees* — looked up exactly where the runtime's walk-up discovery looks. **LESSON: when guarding a
  report, assert the agreement between the report and the reality it describes. String pins ossify
  the wording and are blind to the lie.**
- **My own fix would have destroyed operator data, and only a mutation caught it.** Widening the
  converter search to `SF_MPXJ_HOME`/CWD quietly made the *already-installed* copy selectable as the
  source — and the copy step `rm -rf`s the destination before copying. A re-run would have deleted
  the operator's only converter. Guard added, then mutation-tested both ways to prove it was
  load-bearing. **LESSON: widening a search path is not a safe, additive change when the consumer of
  that path is destructive. Whenever you add candidates to a lookup, ask what happens if a candidate
  IS the target — and prove the answer with a mutant, not an argument.**
- **Verify the advice, not just the code.** The new message tells the operator to download the
  repository ZIP; before writing it I checked `git ls-files tools/mpxj` and confirmed all 28 files
  (converter class + 24 jars, no LFS) are tracked, so the ZIP really carries them. That check is now
  a test, so the advice cannot rot silently. **LESSON: remediation text is a claim the tool makes.
  Test it like one — the previous message advised setting `SF_MPXJ_HOME`, which the installer never
  read.**
- **The bad instruction was mine, in a durable doc.** The DEPLOY NOTE I had been carrying forward in
  every handoff told the operator to download the single `.ps1` into `Downloads` — the one layout
  that guarantees the converter is not found. It rode along unchallenged for many sessions because
  it *looked* like settled knowledge. **LESSON (reinforces Part V): a handoff line repeated often
  enough starts reading as verified fact. Re-derive load-bearing operational instructions against
  the code they drive, especially the ones you have copied forward more than twice.**
- **Stopped mid-flight without losing the work.** The session was called to a handoff before the fix
  landed, so the evidence, both ready-to-apply blocks and the drafted test went into
  `docs/PLAN/MPXJ-CAPABILITY-REPORT.md` rather than a scratchpad that dies with the session.
  **LESSON: when a session ends with a diagnosis but no patch, the diagnosis is the deliverable —
  commit it in enough detail that the next session applies rather than re-derives.**

### 2026-07-27b — a spec written without a runtime had five false premises; the mutants caught my guard, not my code (ADR-0298)
- The AXIS-TITLES spec is genuinely good work — its census of 58 modules is exact and its caption
  wording is sound. But it was authored with **no Python, no app, no network** (it says so), and
  **five** load-bearing implementation claims failed on contact: a helper that does not exist
  (`SFChartFrame.text`), CSS tokens that do not exist (`--sf-fs-label`, `--sf-font-mono` — the
  theme file is colour-only), a module described as missing an X caption that already had one
  (`scatter.js`), a "not exempt" Gantt that renders **HTML** and therefore cannot take an SVG
  caption, and stale golden SHAs plus a wrong doc path. **LESSON: an applyable spec's OBSERVATIONS
  (what the code contains) survive without a runtime; its PRESCRIPTIONS (what to call, what token
  to read) do not. Verify every symbol and every token the spec tells you to use actually exists
  before writing a line — that check took minutes and would have produced five broken commits.**
- **The mutation test caught MY GUARD, not my code.** My first "size must come from the token"
  assertion sliced the source from `function axisTitles` forward — and the planted numeric
  `font-size` sat in the node-building helper *just above* that line, so the mutant passed. The
  test was green and worthless in exactly the dimension it existed for. **LESSON: mutation-test the
  ASSERTION's reach, not just the code's behaviour. A guard that greps a window is only as good as
  the window; prefer slicing to a semantic boundary (the whole block) over an offset.**
- **`git checkout --` is not an undo when the tree is dirty.** Reverting a mutant that way wiped a
  legitimate uncommitted edit in the same file and I only noticed because the ledger test failed
  with a name I did not expect. **LESSON: mutation-test with file backups (`cp` to a scratch dir),
  never with git, whenever the working tree carries changes you have not committed.**
- **A heuristic that under-detects is worse than no heuristic, because it looks like coverage.**
  The spec's tick-regex found 14 of 28 remaining chart modules and said nothing at all about the
  dozen HTML-rendered visuals. Replacing it with an exhaustive three-way ledger (captioned /
  pending / not-applicable) made the remaining work *countable* and made an unclassified new module
  a hard failure. **LESSON: prefer an explicit ledger over a clever matcher for "what still needs
  doing" — the ledger cannot silently shrink, and it forces triage of anything new.**
- **Say what you did not verify.** The design system's DoD wants a four-theme rendered pass; this
  sandbox has no browser automation, so the ADR, handoff and PR all say the visual pass is *owed*
  rather than implying the static + node layers covered it. **LESSON: an unchecked DoD box is a
  disclosure, not a footnote — name it where the reviewer will see it.**

### 2026-07-27a — splitting a monolith is a test-namespace problem, not a code-move problem (ADR-0297)
- The code move itself was the easy 90%: cut byte-ranges by script, re-export with `X as X`
  (the one idiom that satisfies BOTH mypy-strict's explicit-reexport rule and ruff F401), let
  F821/F401 + mypy find the misses. The hard 10% was entirely about **monkeypatch targets**:
  Python resolves a callee in the CALLING module's namespace, so moving a call site silently
  disconnects every `setattr(app_mod, ...)` spy aimed at it. **LESSON: before moving code, grep
  the suite for every setattr on the source module and classify each by WHERE ITS CALL SITE will
  end up — that list, not the import graph, is the real blast radius of a Python refactor.**
- I got two of the eleven retargets wrong — in OPPOSITE directions (`work_to_go_census` is called
  from app's `_perf_version_block`, not state's `summary_for`; and one test READ `real` off the
  app module after the import vanished). Both failed loudly within seconds because the
  perf-contract suite pins call COUNTS, not just outcomes. **LESSON: op-count pins (ADR-0249)
  double as refactor armour — a suite that counts calls turns "silently ineffective spy" (the
  worst refactor failure, a test that passes while testing nothing) into an immediate red.**
- The strongest behaviour-freedom proof cost nothing: the three dashboard payload golden SHAs
  (ADR-0281) passed untouched across the split. **LESSON: goldens you already own are the
  cheapest refactor oracle — run them FIRST after a big move; a byte-identical payload closes
  the argument in a way "all tests green" doesn't quite.**
- Scoping discipline held under temptation: the full split (19k lines → modules) wants to be one
  heroic PR, and phase 1 (state machinery only, 1,616 lines) looks "small". But phase 1 is the
  piece with the trickiest coupling (caches, epochs, single-flight, 126 imports) — landing it
  alone, verbatim, with the patch-rule documented, makes phases 2-3 mechanical for whoever does
  them. **LESSON (ADR-0195 reaffirmed): cut the phase with the highest coupling-to-size ratio
  first, while the file is still hot in context — the cheap bulk (HTML helpers) can move any day.**

### 2026-07-26a — the two-PR sequencing paid for itself; and a golden SHA is a tripwire, not proof (ADR-0296)
- The `status_mix_uids` trim landed exactly as sequenced: ADR-0295's resolver fix + forward guard
  FIRST, the lazy trim SECOND. When the trim flipped the dashboard drill to `{ segment: name }`
  descriptors, the guard test (server-resolved segment == the card's own count, for every card in
  the manifest) was already sitting there to catch any regression — the trim's riskiest property
  was pinned before the trim existed. **LESSON: when change B deepens reliance on a property that
  change A establishes, commit A's guard test in A's PR, phrased so B cannot land without
  satisfying it. The guard is cheap in A; it is a bug report in B.**
- **Re-pinning a golden SHA is only honest when something else proves the delta.** The three
  ADR-0281 payload SHAs had to change (the payload lost a key), and a bare re-pin would have
  laundered ANY payload change through the same commit. What makes it safe: the new trim tests
  prove at ROW level that every count survives and every segment drill returns identical
  activities, so the SHA delta is exactly the removed key and nothing else. **LESSON: a golden
  hash detects change; it never explains it. Every re-pin needs a companion test that proves the
  intended delta is the only delta — otherwise the golden silently becomes "whatever HEAD does".**
- **Not every categorical bar went lazy, and the asymmetry is the design.** Status/type/completion
  segments are re-derivable by NAME from predicates the server owns; WBS groups partition by
  arbitrary data values, so they keep explicit UID arrays. **LESSON: lazy descriptors work only
  where the name is a total function to the set. If re-deriving needs the data itself, shipping
  the ids IS the honest design — don't force the pattern past its precondition.**
- Payload numbers for the record: the arrays were **87.6%** of /api/dashboard; growth per version
  9,698 B → 1,195 B. Second confirmation (after ADR-0288's 46%) that per-activity ID arrays
  dominate these payloads — worth checking any NEW chart payload for the same shape at design time.

### 2026-07-25d — scoping a perf change surfaced a shipped correctness bug (ADR-0295)
- The `status_mix_uids` trim looked like pure plumbing: swap an id array for a segment name, reuse
  the ADR-0288 pattern. Before building it I probed its core assumption — "the drill resolves the
  card's own file" — with two distinct Projects loaded. It doesn't: `_pick_scorecard_version`
  searches the ACTIVE population only and silently falls back to `versions[-1]`, so a non-active
  card's drill listed the active Project's activities under the clicked card's label.
  **LESSON: before building on an assumption, write the probe that would falsify it — especially
  when the assumption is "this obviously routes to the right place." The probe cost 20 lines and
  found a shipped, operator-visible wrong-data bug.**
- **The perf change would have upgraded the bug from visible to invisible.** With explicit UIDs,
  the substituted file produces a half-empty, obviously-broken drill. With a lazy segment name,
  the substituted file produces a fully self-consistent, plausible, WRONG activity list.
  **LESSON: lazy resolution deepens trust in the resolver. Any change that moves data derivation
  from "shipped with the view" to "resolved on demand" must first prove the resolver's identity
  guarantees, because it removes the incoherence that used to expose mis-resolution.**
- **Silent fallback is the defect pattern, again.** The resolver's `versions[-1]` default was
  correct for its original caller (a page with its own version selector) and wrong for a drill
  trigger carrying an exact key. **LESSON: "fall back to something reasonable" is only safe when
  the caller can SEE what was chosen. For programmatic callers that name an exact target, a miss
  must be an error — substituting is how wrong numbers acquire the right labels (Law 2).**
- Fix ordering mattered and was itself a decision: correctness PR first (ADR-0295), trim second,
  never folded — the standing "a correctness fix never rides with a perf change" rule, third use.

### 2026-07-25c — I wrote a number into a handoff as an instruction, and it was wrong (ADR-0294)
- Yesterday's handoff told the next session: *"the ONE hypothesis that survived — skip
  `_strip_namespaces`, **114 ms / 8.1%**, implement it."* Today I implemented it, measured it
  end-to-end, and **reverted it**. The walk really does cost 114 ms — that number was never wrong.
  What was wrong was the inference that deleting it *saves* 114 ms: the replacement (rebuild the
  21 MB string, 52.9 ms + scan for `xmlns`, 7.4 ms) costs **60 ms**, and the parser only hands back
  **7 ms** because ElementTree's namespace handling is nearly free. **LESSON: a component
  measurement prices what you REMOVE. It is silent on what you ADD in its place. Never promote a
  component delta to a predicted win without an end-to-end A/B of the real function.**
- **The A/B itself needed two instruments to be trustworthy.** Wall-clock said −28.7 ms (−1.8%) with
  samples ranging 1,503–4,989 ms — useless. CPU time said median −55.5 ms but **min-to-min −8.0 ms**.
  **LESSON: when the median and the minimum of the same measurement disagree by 7x, you are
  measuring allocator/GC state, not work. Report both, and believe the one that survives repetition.**
- **Writing a forward-looking claim into durable state is a commitment, and it propagates.** The
  handoff is auto-injected into every session, so a wrong "implement this, here's the number" would
  have been read as settled fact by whoever picked it up — they'd have shipped a mutation of the
  document text *before parsing*, on the most parity-critical path in the tool, for an unmeasurable
  few percent. **LESSON: mark forward-looking estimates in the handoff as HYPOTHESES with the
  measurement still owed, and reserve the declarative voice for what has been proven end to end.**
- **Closing an item as "declined" is a real deliverable.** Item 6 ships no code. What it ships is a
  profile of record and five hypotheses with their kill-shots attached (bytes-not-str is *slower*;
  `Tasks` is 78.7% of the DOM so selective parsing has no headroom; a per-task dict saves 1%; lxml
  is a binary dep across 9 installers; the pre-strip above). That list is worth more than a 2%
  optimisation, because it stops the next five sessions from re-deriving it. Third precedent now,
  after ADR-0290's declined rename and ADR-0292's two untouched cache tiers.

### 2026-07-25a — the measurement killed two of my three fixes, and that was the deliverable (ADR-0293)
- Perf item 5 arrived as five words: *"an MPP capability probe."* I had three candidate fixes before
  measuring anything, and **two of them were wrong**:
  **(a)** memoise the JRE lookup process-wide — it costs **0.3 ms**, so the entire purchase would
  have been microseconds in exchange for a stale "no Java here" answer that outlives the operator
  installing a JRE; **(b)** pre-warm the JVM in the background — the whole window between the upload
  arriving and the first conversion starting is **97 ms**, so there is nothing to overlap the 1.35 s
  MPXJ warm-up with. **LESSON: a backlog item's NAME is a hypothesis, not a finding. Measure what it
  points at before you design the fix for it — half the time the named thing is already free and the
  real cost is one layer over.**
- **The ADR-0292 order-dependence trap bit again, in a completely different subsystem.** My first
  reading said the persistent batch JVM was **1.4 s slower** than a one-shot for a single file
  (2.99 s vs 1.58 s) — a regression on the most common case, and I nearly went looking for it.
  Re-measured interleaved and repeated: **1.52 s vs 1.49 s** at N=1 and **2.71 s vs 11.74 s** at
  N=8. The first number was cold page cache on the MPXJ jars, because the server path ran first.
  **LESSON: the "measure A then B" habit is a bug generator. Interleave and repeat by default —
  this is now the second session in a row where the naive ordering produced a confident wrong
  answer.** (Promoted alongside the ADR-0292 entry below; treat it as standing practice, not a
  one-off.)
- **What actually survived was I/O, in the layer above.** The upload path spilled every `.mpp` to a
  temp file *before* asking whether the machine could convert one at all — 16 files = **3.2 MB**
  written then discarded, and the operator's real files are ~10 MB, so a 500-file folder is **~5 GB**
  of pointless writes. Nobody would have found that by profiling CPU; it only showed up because I
  counted `write_bytes` calls in the failure case. **LESSON: profile the FAILURE path too. The
  happy path was fine; all the waste lived where the answer was "no".**
- **Scoped the cache to the ingest, not the process — deliberately, and it is the whole safety
  argument.** A process-wide memo would need invalidating the moment the operator installs a JRE
  and retries, and a stale answer that outlives its own fix is worse than the cost it removed. A
  batch session is one ingest; the next upload re-probes; there is no long-lived answer to get
  wrong. **LESSON: pick the smallest scope at which the memo still pays. "Cache it forever" is not
  the default — it is the version with an invalidation bug you haven't written yet.**
- **Kept the UI out of the perf PR.** Surfacing "native .mpp is unavailable on this machine" is real
  value and the probe is now the hook for it — but it owes the DESIGN-SYSTEM Definition-of-Done
  (ADR-0195), and a perf diff is exactly where a UI change goes unreviewed. Named it in the ADR as
  deferred instead of quietly shipping it.

### 2026-07-24h — I measured the same thing three ways and got three answers; only the third was right (ADR-0292)
- Sizing the session cache tiers looked trivial and was not, because every tier stores `(sch, value)`
  where `sch` REFERENCES a Schedule already held in `st.schedules`.
  **Attempt 1** (a fresh visited-set per tier) double-counted that Schedule and reported `dash_cores`
  at 923 KiB/entry — I was one step from filing ADR-0281's "~1 KiB" estimate as a 900x defect.
  **Attempt 2** (one shared visited-set, tiers charged in sequence) fixed that but produced
  `cpms = 0.1 KiB/entry`, and I wrote a scratchpad conclusion that item 4 needed no action at all.
  **Attempt 3** — forced on me when the test I had just written FAILED at 641 KiB — charged each tier
  independently and found the truth. **LESSON: when a measurement's answer depends on the ORDER you
  measure in, you are measuring the wrong quantity. Ask "what does this cost if the others were
  empty?" and measure that.**
- **The test caught me, not the other way round.** I had already written the conclusion down. The
  only reason it did not ship is that I encoded the claim as an executable ceiling and ran it. A
  scratchpad note asserting "cpms is free" would have been believed by the next session.
  **LESSON: turn a measurement into an assertion immediately — a number in a doc is a rumour, a
  number in a test is a fact.**
- **The real bug was a cap that did not cap.** `analyses` was LRU-bounded; `cpms` was a plain dict
  holding the SAME heavy objects. While both were resident that was invisible — `cpms` genuinely
  shares. But after an analysis eviction the `cpms` entry kept the scoped Schedule + CPMResult alive
  by itself, so the bound everyone trusted was not bounding anything at 200 versions.
  **LESSON: a memory cap is only real if EVERY tier holding the object is capped. Check the whole
  retention graph, not the tier you happen to be looking at.**
- **Said no to two of the three tiers the backlog named.** `dash_cores` (2.8 KiB) and `dash_cards`
  (20.1 KiB) are under 5 MiB even at 200 versions; capping them would add exactly the
  "slightly-too-small LRU" ADR-0281 warned against. And I left `_ANALYSIS_CACHE_MAX` alone and
  flagged it (~348 MiB worst case) instead of quietly retuning it — that trade is the operator's
  hardware, not mine.

### 2026-07-24g — a cache fixed the expensive half and left the cheap half running N times (ADR-0291)
- ADR-0281 cached the dashboard's ENGINE work and I treated the dashboard as "done". It wasn't: with
  that cache fully warm, `/api/dashboard` still burned **117 ms at 30 versions** re-deriving the
  projection built *around* the cached figures — `scope()` per version, `non_summary()` three times
  per version, activity-makeup, the status-UID partition. **LESSON: after caching the expensive step,
  re-measure the warm path. The remaining cost is never zero, and "cheap × N versions × every
  refresh" is exactly the shape that hides from profiling done at N=1.**
- **LESSON: I wrote a guard that was a tautology, and only reading the existing pattern caught it.**
  My first `dashboard_card_store` did `if self.wipe_gen != self._wipe_gen_at_entry(sch)` where the
  helper returned `self.wipe_gen` — comparing a value to itself, so the guard could never fire. It
  would have passed every test I had written. The fix came from reading how `dashboard_core_for`
  actually does it (capture `gen` at ENTRY, compare at STORE) rather than inventing a shape. When
  adding a tier to an existing family, copy the family's proven guard; don't improvise one.
- **LESSON: prefer a memo whose cached value IS the finished artifact.** Caching the assembled card
  dict makes "payload byte-identical" true *by construction* rather than something to re-verify —
  there is no second code path that could drift. The equality pin then guards the cache key, not the
  arithmetic.
- **Named the residual instead of quietly absorbing it.** After the memo, the warm cost that remains
  is JSON-serialising the `status_mix_uids` arrays the payload ships — the dashboard's version of the
  trend-payload problem ADR-0288 solved. Recorded as its own item rather than scope-crept into this
  PR, so the next measurement starts from a known baseline.

### 2026-07-24f — verify a planning doc's PREMISE before you execute its plan (ADR-0289/0290)
- The operator committed six Claude-Design planning docs. Two of them turned out to rest on claims
  the tree contradicts. `CRISPNESS-PATCH.md` states `sf-themes.css` "was never committed" and builds
  its whole §2.1 recommendation on that — move the type ramp into `base.css` and rewrite
  DESIGN-SYSTEM to name it the token file. **`sf-themes.css` exists**: 4,576 bytes, 36 custom
  properties, linked in `_LAYOUT`. Executing that plan would have split the token layer and
  documented the wrong file as canonical. **LESSON: a planning doc is a hypothesis. Check its factual
  claims against the tree before you implement even one line — the same rule we already apply to
  audit findings applies to specs.**
- `RENAME-PLAN.md` asked which of five names to adopt; its own §0 recommended never. Checking the
  premise made the decision free: the brand is already POLARIS everywhere and "Schedule Forensics"
  appears **zero** times in any user-visible surface — so the "cheap alternative" the plan offered was
  already done. **LESSON: before choosing between options, verify which of them is already true.**
  The answer cost one grep and saved a ~350-file refactor.
- **LESSON: for a CONCURRENCY change, a source-assertion test is worthless — execute it.** The
  bounded-concurrency pre-read could have been "verified" by grepping for `Promise.all`. Instead the
  harness runs the real function under node against an oracle re-implementation of the OLD sequential
  algorithm, with seeded jittered latency so completion order never matches pick order by luck, and
  injected failures so the error path is exercised too. That is what actually proves `readable[j]`
  still pairs with `meta[j]`. Then I proved the test discriminates by setting the cap to 1 and
  watching both assertions fail.
- **LESSON: bound the parallelism, and say why in both directions.** Serial was slow; `Promise.all`
  over a whole FileList would hold every picked file's bytes in memory at once. The cap is the
  decision, so it is a single named constant with a test asserting it stays in a sane band — a future
  "optimisation" that sets it to 1 (silently serial) now fails the gate.

### 2026-07-24e — measure the payload before optimising it, and let the SERVER own the expensive half (ADR-0288)
- The backlog said "lazy status-UID payload trim (486 KB → ~40 KB @ 50 versions)". Before writing
  any code I measured: the `*_uids` arrays were **46.5%** of `/api/trend` and it grew **46,600 B per
  version**. The estimate's *direction* was right and its *magnitude* was roughly right, but only the
  measurement told me which three groups mattered (the two that PARTITION the schedule) and which to
  leave alone (the float bands, whose id sets are small and genuinely sparse). **LESSON: a backlog
  estimate tells you where to look, never what to change.**
- **LESSON: when data is only needed on an interaction, ship the QUESTION not the ANSWER.** The bars
  needed "which activities are in this segment?" — so the bar now carries the segment NAME and the
  server rebuilds the set on click, using the same predicates. Payload halves, and the drill result
  is provably identical because both paths run the same code.
- **LESSON: a whitelist beats a fallback when the two sides must agree.** `trend.js` could have
  lazily segmented ANY key whose `_uids` were missing — but then a typo or a future chart would make
  a bar silently inert (server returns empty). An explicit `LAZY_SEGMENTS` list, pinned equal to the
  server resolver by a test, makes drift a build failure instead of a dead click.
- **LESSON: when a test breaks because you changed the contract it pinned, rewrite it to the NEW
  contract — and take the chance to make it stronger.** Three pins in `test_categorical_bar_drill.py`
  asserted the old `*_uids` payload. The replacement for the drill-resolution one no longer checks
  "some rows came back" for the first 5 ids; it asserts the resolved row count EQUALS the bar's
  count. The change forced a better test than was there before.

### 2026-07-24d — "the numbers are wrong" was a DEFAULT, not a defect; and one hover should mean one tooltip (ADR-0286/0287)
- The operator reported for the second time in a day that the DCMA-14 ribbon disagreed with Acumen
  Fuse. Before touching the engine I re-hashed their uploads: the `.mpp` and the Acumen detail export
  were **md5-identical** to the morning's copies, and the freshly re-exported ribbon carried
  **identical numbers**. Their screenshot read "parity mode ☐ OFF", and every value on it reproduced
  the engine's DEFAULT output exactly. **LESSON: when a user says a number is wrong, first establish
  WHICH MODE produced it and whether the inputs actually changed — hashing the uploads took seconds
  and ruled out an entire engine investigation.** The fix was a one-line default, not a formula.
- **LESSON: a correct feature behind a default-off toggle reads as a broken product.** Parity mode was
  verified UID-exact and thoroughly documented, and the operator still hit the mismatch twice. When
  the tool's headline promise is "it reconciles with Acumen", the default has to answer that question;
  the alternative view stays one click away. Being right in an unticked checkbox is not being right.
- **LESSON: flip a PRESENTATION default, never the ENGINE default.** `SessionState.dcma_acumen_parity`
  went True while `compute_dcma14`/`audit_schedule`/`recommend` kept `acumen_parity=False`. Every
  golden passes the flag explicitly, so not one parity test moved. The blast radius was six tests that
  had been *inheriting* the session default — and the right fix there was to make each one state its
  mode explicitly, which is better hygiene than it had before.
- **LESSON: implement a hover delay as a `transition-delay`, not a `setTimeout`.** The requirement was
  "only show if the cursor rests for 1.5s". A CSS transition-delay gives that for free and is
  inherently cancellable — leave early and the transition never completes, so nothing paints and there
  is no timer to clean up. This forced `.dcma-tip` off `display:none` (which cannot be transitioned)
  onto opacity/visibility. Only the JS-positioned tip needed a real timer, and that one does need an
  explicit `clearTimeout` on mouseleave.
- **LESSON: fix a duplicated-affordance bug at the layer that OWNS the duplication.** There were ~104
  server-rendered `title=` attributes; editing each call site would have been a huge diff that the
  next `title` would silently re-break. One runtime normaliser in `tooltips.js` (plus a
  MutationObserver for client-rendered charts) fixes every current and future occurrence, and the
  test pins the invariant rather than the call sites.

### 2026-07-24c — the feared golden re-pin didn't exist; and a mode flag must reach EVERY derived surface (ADR-0285)
- ADR-0282 predicted that making findings follow the parity audit would force "fresh parity-variant
  goldens **and** re-pinned `ai.citations` goldens" — the main reason it looked expensive. Before
  changing anything I had the test/golden surface mapped and then verified it myself: there are **no
  stored goldens** for findings/narrative/briefing/risk-matrix (they're all inline, default-mode
  assertions), and every `ai.citations` test is built from literal `CitedStatement` fixtures, so it is
  mode-independent. The real breaking surface was **two tests** that deliberately pinned the old
  behaviour. **LESSON: an ADR's cost estimate is a hypothesis written before the work — re-measure it
  against the tree before you either accept the cost or shy away from the change.** The change landed
  in one sitting instead of the multi-session golden re-pin it was billed as.
- **LESSON: "make X follow the mode" means finding every surface DERIVED from X, not just the obvious
  call.** The first pass wired `_compute_analysis` + the two `/risks` sites and looked complete. A
  grep for the remaining call sites found `build_briefing()` and `build_narrative()` each calling
  `recommend()` internally, plus `build_briefing` computing its verdict from its OWN default audit —
  so the `/briefing` page would have shown a parity-aware HEADER above a default-audit BODY. Chasing
  the flag to the leaves is the difference between "every surface agrees" and a new, subtler
  disagreement than the one being fixed.
- **A behaviour fix that also removes work:** deleting the ADR-0281 pin let parity mode reuse the one
  audit it already computes, so the extra pass disappeared (2×/1×/1× → 1×/1×/1×). Worth noting because
  the usual assumption is that correctness costs speed; here the *inconsistency* was the thing costing
  speed.
- **Process that paid off:** a full-suite checkpoint BEFORE the version bump / installer regen isolated
  the only failure (wheel lockstep, caused by my own later edit) from any real regression — and
  confirmed no golden moved.

### 2026-07-24b — a population narrowing must reach the CHROME, not just the analysis (ADR-0284, Fix E)
- ADR-0258 narrowed every *analysis* population to the active project via `ordered()` /
  `ordered_versions()`, but two page-chrome helpers (`_render_target_control`, `_endpoint_banner`) kept
  iterating `state.schedules.values()`. The dropdown keys milestones by `unique_id` and keeps the first
  label, so a UID shared across projects rendered a **foreign project's name** — a real identity leak
  hiding in the nav bar, not the engine. **LESSON: when you introduce a scoping helper, grep for every
  remaining raw iteration of the unscoped collection (`schedules.values()`) — the ones left behind are
  usually in rendering/summary code that "looks read-only" and gets skipped in the analysis-focused
  review.** The fix was a one-line swap to `ordered_versions()` in each, but finding the second site
  mattered as much as the first.
- **LESSON: a committed `xfail(strict=True)` is the cleanest hand-off for a known bug.** ADR-0281
  parked this leak as a strict-xfail characterization test. Picking it up a session later was
  friction-free: the test already encoded the exact expected behavior (Beta active ⇒ no Alpha label,
  banner counts Beta's 2 not 4), so "fix it" meant "make this pass and delete the marker" — no
  re-deriving what "correct" was. Strict-xfail also guarantees the marker can't rot: the moment the fix
  lands, the suite fails loudly until the marker is removed.
- **Confirmed before trusting it:** `ordered_versions()` takes the session lock; I checked `_lock` is a
  reentrant `RLock` before calling it from the render path, so a caller already holding the lock can't
  deadlock. Verify the lock discipline, don't assume it.

### 2026-07-24 — "why don't the numbers match Acumen?" was mostly a toggle; the real bug was one unscoped check (ADR-0283)
- The operator sent a screenshot of our DCMA ribbon next to Acumen Fuse's and asked why they differ.
  The instinct is to hunt the engine. The disciplined move paid off instead: I MPXJ-converted the exact
  `.mpp`, ran `compute_dcma14` in both modes, and the **default-mode** output reproduced the screenshot
  **byte-for-byte** — so the headline "discrepancy" was simply that **Acumen-parity mode was OFF**.
  Parity mode already matched Acumen's ribbon on 12/14 checks. **LESSON: before fixing a parity gap,
  first confirm which mode produced the number** — a mode toggle explains a whole table of "differences"
  that no code change should chase.
- **LESSON: the ribbon and the detail of the SAME external tool can disagree — pick the surface your
  data model represents.** Acumen's ribbon counts SS/FF and Lags by *link* (90, 8); its detail lists
  *distinct activities* (70, 5). Our count field matched the ribbon on SS/FF and the detail on Lags —
  because DCMA-04 doesn't dedupe successors and DCMA-02/03 do. Both "match Acumen," just different
  Acumen surfaces. For a citation tool the activity (detail) count is the one that has to be right; the
  ribbon's field/link tallies are a documented units divergence, not a bug to chase.
- **The one real residual** was DCMA-09 Invalid Dates (parity 182 vs Acumen detail 173). Set-diff by
  activity name: we caught all 173 + 9 extra, every extra with **no baseline duration**. The `.aft`
  proved it — `9. Invalid Forecast/Actual Dates` carry the SAME `PrimaryFilter Baseline Duration > 0`
  as every other work check, which ADR-0280 had applied everywhere EXCEPT DCMA-09 (explicitly, to avoid
  unverified regressions). **LESSON: a deliberately-deferred "leave it for now" is a debt with a name —
  when the ground truth finally arrives (a new reference file), pay it.** The fix reuses the existing
  `ap_tasks` population; default stays byte-identical; parity goes UID-exact (0 FP / 0 miss).
- **LESSON: one combined loop can faithfully reproduce two separately-filtered external metrics IF each
  predicate self-excludes the wrong population.** I nearly split DCMA-09 into forecast/actual halves to
  mirror Acumen's two metrics (IncludeComplete=0 / IncludePlanned=0). Unnecessary: a complete task
  carries actuals so it never trips a "no-actual" forecast term; a planned task has no actuals so it
  never trips an "actual-in-future" term. Only `Baseline Duration > 0` changes any count. Verified, not
  assumed — the merged loop gives exactly 173.

### 2026-07-23b — validate an external audit against HEAD, not against the report (ADR-0281/0282)
- Implemented four performance fixes from a ChatGPT "5.6 Sol" audit. The audit was **directionally
  right on all three P0/P1 mechanisms** (dashboard full-analysis + LRU thrash, no single-flight,
  duplicate dependency computes) — but its *specifics* had rotted: it referenced the retired
  `dcma_exclude_milestones` (ADR-0280 replaced it with `dcma_acumen_parity`/`A=1`/`acumen_parity`),
  claimed an importer `strptime` hotspot that doesn't exist (we already use `datetime.fromisoformat`),
  and cited a **63-hex-character "SHA-256"** as its byte-for-byte proof (not a valid length).
- **LESSON: re-ground every finding against current HEAD and re-prove it before adopting it.** The
  validation session that produced our implementation prompt did exactly this — it rebuilt every
  finding as a characterization test, ran them against the untouched tree, and prototyped the fixes in
  a disposable clone — so by the time I implemented, each fix was a known-good against `f551b01`. An
  audit is a set of *hypotheses*; treat its API names, its hotspots, and its "proofs" as claims to
  verify, not facts to act on. (Our own sandbox SHA-256 was a valid 64-char hash and byte-equal — the
  report's conclusion was right even though its cited hash was impossible; right conclusion, unusable
  evidence.)
- **LESSON: op-count characterization tests belong in the tree before the fix.** Committing them first
  (failing) proved they were genuine — a reader can check out that commit and watch them fail — and
  they doubled as the acceptance contract (byte-identical payload golden, 1×/1× dep counts,
  single-flight). This is the repo's "turn every miss into a test" habit applied to *performance*.
- **LESSON: a second knob changes the op-count truth table — re-run the audit with it set.** The
  parity-mode findings inconsistency (displayed audit is parity, findings derive from the default
  audit) was invisible until the dependency-count check re-ran with `A=1`. Had I only measured the
  default mode I'd have "fixed" the dep counts and silently frozen a latent product bug. Filed it as
  **ADR-0282** (open question for the operator) rather than quietly re-sourcing findings inside a
  performance PR — a behaviour change rides its own PR with its own parity goldens (Law 2 / ADR-0240).

### 2026-07-23 — the AUTHORITATIVE SOURCE dissolved three sessions of proxies in one read (ADR-0280)
- Over three sessions I set-differenced our offenders against Acumen's flagged-task lists and shipped:
  a milestone-exclusion scope (0277), a correction to it (0278), and a stored-float CPLI (0279). Each
  was empirically verified and each was *partly a proxy*. Then the operator handed me the **`.aft`
  metric library** — Acumen's formulas AND population filters verbatim — and in one reading every
  proxy collapsed into a single true rule: **`Baseline Duration > 0`, truncated to whole days**, with
  milestones INCLUDED. The milestones I'd been excluding just happen to have baseline duration 0.
- **LESSON: get the spec before you reverse-engineer the behavior.** Set-differencing against outputs
  is powerful but it finds *a* rule that fits the sample, not necessarily *the* rule. I had the `.aft`
  reference concept in CLAUDE.md the whole time ("metric formulas come from the Bible") but was
  matching against exported *counts/detail* instead of reading the library's `<PrimaryFilter>`. When an
  authoritative definition exists, spend the hour to parse it FIRST; it is worth more than ten
  set-diffs. (The committed `.aft` was even the older 20260423 — the operator's newer 20260708 had the
  current formulas.)
- **A wrong root cause I had written down as fact:** ADR-0278 claimed the ~24-task gap was an Acumen
  `.afw` workspace `Excluded`/Level-of-Effort exclusion (I'd even found those strings in the binary and
  reasoned they weren't reproducible from the schedule). The `.aft` showed the real discriminator —
  `Baseline Duration > 0` — was in the schedule all along. Finding a *plausible* mechanism in a side
  artifact (the `.afw`) is not proof; I stopped digging one layer too early and enshrined a guess.
  RETRACT loudly when the authoritative source contradicts a prior ADR.
- **What went right:** default-off/configurable at every step meant three proxy iterations shipped with
  ZERO risk to the golden gate or existing behavior — each was opt-in, byte-identical by default. So
  the proxies were never *wrong in production*, only incomplete, and collapsing them into one correct
  "Acumen parity mode" was a clean supersede, not a firefight. Configurability bought the freedom to be
  iteratively-wrong safely.
- **Two views, not one truth:** the final design keeps BOTH the pure-logic/forensic scoring and the
  Acumen-faithful scoring as first-class modes with an explicit when-to-use, because they answer
  different questions (independent recomputation vs "what would Acumen report"). Resisting the urge to
  pick a single "correct" default on a testimony tool is itself the lesson.

### 2026-07-21 (cont. 4) — CPLI parity: a two-part fix whose halves are worthless apart (ADR-0279)
- Root-caused why our CPLI (1.00) ≠ Acumen (0.97 / 0.59). Two causes, and the trap was that fixing
  ONE makes the answer WORSE: (1) we use recomputed CPM float (min ~0) where Acumen uses stored Total
  Slack; (2) our pure-logic CPM collapses File 2's finish to ~2025 (78-day remaining length) where the
  stored schedule finishes ~2028 (~1053 d). Swap in the stored float but keep the recomputed length
  and File 2's CPLI is **−4.55** — a nonsense number that would look like a new bug. LESSON: when a
  metric has multiple divergent inputs, verify the fix with ALL of them swapped together on EVERY
  sample; a partial swap can score worse than the original and mislead you into reverting the right
  idea. File 1 (where recomputed ≈ stored finish) would have "passed" a one-input fix and hidden it.
- **The consistency tell:** `effective_total_float` (stored-preferring) was ALREADY the default for
  DCMA-06/07 — CPLI was the one float-based check still on raw recomputed float. Noticing that
  inconsistency is what pointed at the fix. When one metric disagrees with a tool the others match,
  ask what input the odd one out is reading differently — the answer is usually "it never adopted the
  convention the rest of the engine already uses."
- **Ground truth that contradicts itself is itself a finding.** Acumen's own exports disagree on Logic
  for File 1 (Ribbon-Analysis says 0; the DCMA-14 detail workbook says ribbon 8 / detail 5). When the
  reference tool isn't internally consistent, that metric is not a parity target you can chase to an
  exact number — flag it as needing the operator's Acumen settings, don't invent a rule to fit one
  of the conflicting exports.

### 2026-07-21 (cont. 3) — the fix I shipped an hour earlier was PARTLY WRONG, and richer ground truth caught it (ADR-0278 corrects 0277)
- Right after ADR-0277 merged (milestone-exclusion for the DCMA "work" checks {01,04,05,06,07}), the
  operator committed the **ground-truth workbooks** — Acumen's ACTUAL per-check flagged-task detail
  rows (not just counts, not just the ribbon). A **UID-level** re-diff overturned part of my fix:
  excluding milestones is UID-EXACT for Hard (05) and Negative Float (07), but **HARMFUL for High
  Float (06)** — Acumen's 814 detail *includes* 7 zero-duration milestones with genuinely high stored
  float, so excluding them = 7 false negatives (under-report, the wrong direction for testimony).
- **The root LESSON: a count match can be a coincidental proxy.** In the prior session I saw
  "exclude milestones ⇒ 41→35, matches Acumen's 35" and generalised "work checks omit milestones" to
  all five. But 41→35 matched *by count*; I hadn't confirmed the 6 dropped were the *only* difference
  AND that the same rule held on the OTHER checks' actual rows. On High Float the milestone count (60
  of 84 FP) looked like the story but the real driver was a **non-milestone** population Acumen
  excludes workspace-side. Milestone-ness was correlated, not causal. VERIFY THE RULE ON EACH CHECK'S
  ENTITY LIST, not one check's count — a proxy that fits sample A can be actively wrong on sample B.
- **What the richer data resolved that I'd left "unexplained":** the `.afw` (gzip → .NET
  BinaryFormatter) exposes a per-activity **`Excluded`** field + a **`FilterActivityTypeLevelOfEffort`**
  filter. So the ~24-task class Acumen omits from every check is an **Acumen workspace-side exclusion /
  LOE classification**, not derivable from the `.mpp` — our engine is CORRECT to flag them. Confirms
  the (cont. 2) instinct to STOP deriving and label it tool-state, now with positive evidence.
- **Meta-lesson on "verified":** I described the milestone fix as "verified, parity-safe" in the
  handoff and PR. It was verified against *counts and the ribbon*; it was not verified against
  Acumen's per-check detail rows (which I didn't have until the operator committed them). "Verified"
  must name the oracle. When better ground truth arrives, re-run — and be willing to correct a
  just-merged decision the same day. Default-off saved us: nothing live was wrong, only the opt-in.

### 2026-07-21 (cont. 2) — root-cause an external-tool parity gap by SET-DIFF against its own output, and distrust the first clean hypothesis
- Acumen-vs-our-DCMA parity investigation on a real 2,100-activity dataset. The single most valuable
  move: the operator's Acumen export contained the **actual flagged task-ID lists** per check, so
  instead of theorising about formulas I **set-differenced our offender UIDs against Acumen's**, then
  characterised the differing tasks. Every conclusion became "these specific tasks, this shared
  attribute," not "maybe it's X." LESSON: when matching an external tool, diff the *entities* it
  flagged, not just the counts — the shared attribute of the disagreement set IS the root cause.
- **My first "clean fix" was wrong, and only exact-count verification caught it.** I was confident
  Resources over-counted because our importer drops MS Project's `-65535` unassigned-work placeholder
  — the 24 over-flagged tasks all had it. But I hadn't checked the tasks Acumen *does* flag: they have
  the **identical** `-65535` assignment. The discriminator didn't exist. Had I implemented on the
  first hypothesis (it looked airtight), I'd have shipped a wrong fix that also touched P2/P5. LESSON
  (ADR-0240, verbatim): a mistaken fix is worse than the drift — verify a hypothesis against the
  *counter*-population (what the tool does NOT flag), not just the population that fits your story.
- **Distinguish "reproducible from the file" from "config in the tool."** After ruling out resource,
  calendar, type, WBS, work/cost, and create-date, ~24 tasks Acumen omits remained structurally
  identical in the `.mpp`. That exclusion isn't *in the schedule* — it's tool/workspace state. Knowing
  when to STOP deriving from the data and ask the operator (vs. inventing a rule that happens to fit)
  is itself the discipline. Shipped only the milestone finding, which was exact and parity-safe;
  documented the rest honestly rather than forcing a fit.
- **Default-off is how you add an Acumen-matching behavior without breaking validated parity.** The
  milestone scope reverses a prior P2/P5-matching choice, so it ships as an opt-in flag whose default
  is byte-identical to before (and isn't in the cache-key shape unless enabled). "Configurable,
  default-preserves-goldens" let both truths coexist — Acumen's population and our validated parity.

### 2026-07-21 (cont.) — not every legend swatch is a togglable series; and fit the mechanism to the chart
- Legend phase 3b (margin_dashboard.js). The burn-down legend has seven swatches, but one — "Below
  requirement" — is **not a series**: the margin bars are drawn green above / red below the NASA
  requirement, and that swatch explains the *recoloring*. Toggling it ("hide the red months, keep the
  green") is meaningless; it is one series with a per-month threshold color. The honest model is a
  `static:true` legend entry that renders as a plain color KEY (no toggle), while the real series
  (including the conditional-color margin bars, tagged with a **single** key so both colors hide
  together) stay togglable. LESSON: before wiring a toggle to every legend row, ask of each "is this a
  separable series, a threshold *state* of another series, or a scale key?" — only the first should
  toggle. Forcing toggles onto states/keys produces incoherent filters.
- **Fit the mechanism to the chart's actual behavior — don't cargo-cult.** performance/cei needed the
  `data-series-scope` host marker because their svg is rebuilt every animation frame. margin renders
  **once** (no stepper), so its svg scope is already stable and the marker would be pure ceremony —
  omitted, and documented why. Same feature, different mechanism, decided by whether the chart
  re-renders. Reflexively stamping the marker everywhere would add noise and imply an animation that
  isn't there.
- **The generic module kept paying off:** a static entry simply carries no toggle attribute, so
  `SFLegend` ignores it and all/none skips it — zero module change for a genuinely new legend *shape*.
  Verified the shape (conditional-color hides together, static is inert, all/none skips it) against the
  REAL module in a node harness before shipping — the same reproduce-then-build discipline, one more time.

### 2026-07-21 — an abstraction proven on ONE structural shape can silently fail on another
- Legend phase 3 (performance.js + cei.js). The phase-1 `SFLegend` module was verified on trend.js,
  where the legend sits OUTSIDE the redrawn svg, so `scopeFor`'s "smallest ancestor containing the
  series" lands on the stable `.chart` wrap. performance.js / cei.js draw the legend **inside** the
  svg — and `frame()` / `render()` replace that whole svg every animation frame. So the exact same
  `scopeFor` now resolves to the **transient svg**, the hidden set (and its MutationObserver) die on
  the next step, and the toggle silently reverts on Play. The module "just worked" in phase 2 (bars
  are also outside-legend), which lulled me — but a different **structural shape** broke the invariant.
  LESSON: when a generic mechanism meets a new adopter, re-verify the *structural assumption* it
  depends on (here: "the scope element survives a redraw"), don't assume prior success transfers.
- **Prototype-verify caught it before a single line of the fix.** I ran the REAL module in a scratch
  harness that models host>svg(transient)>legend, clicked a toggle, simulated an svg-replacing redraw,
  and watched the series reappear — reproducing the bug against trusted code first, then confirming the
  `data-series-scope` stable-host marker flips it green (and that trend.js's fallback is untouched).
  Same discipline as the engine work: reproduce against the real thing, then build.
- **Not every legend is a set of separable series — recognize the ones that shouldn't toggle.** Of the
  six "phase-3" charts, only performance + cei are clean adoptions. margin_dashboard mixes true series
  (contingency, requirement line) with per-month conditional **color-states** (the same margin bar is
  green or red) and marker glyphs (corrective carets, guideline band) — a mechanical toggle would be
  incoherent. dashboard's legend lives inside an `<a>` card (a toggle needs `preventDefault` or it
  follows the link) and one card scope spans two mini-charts. sra_grid (tint-scale heatmap key) and
  path_evolution (descriptive legend) have **no series to toggle** at all. LESSON: "add toggles to all
  charts" is not uniform work — classify each legend (separable series? conditional state? scale key?)
  and defer/skip the ones a toggle would misrepresent, rather than forcing the convention everywhere.
- **Don't launch the authoritative full-gate run mid-edit — it reads a half-updated tree and reports
  phantom failures.** Twice today a background `pytest` I kicked off "to run while I prep the rest"
  came back RED for something already fixed by the time it finished: once the installer lockstep test
  (I'd changed JS but not yet regenerated the wheel), once the state-doc version-pin test (pyproject
  was bumped to 1.0.85 but HANDOFF still read 1.0.84 because the run started before I rotated it). Both
  were stale-read timing artifacts — the *committed* tree was green (each re-verified in isolation).
  LESSON: sequence the release ceremony so the ONE authoritative full run starts only AFTER every
  artifact is regenerated and every state doc is rotated; a run started earlier is a progress check at
  best, a false alarm at worst. Always re-verify such a failure against the current tree before
  treating it as real — it usually points at your own mid-flight edit, not a bug.

### 2026-07-19 (cont. 7) — a good abstraction makes phase 2 nearly free; and check for what already exists
- Phase 2 of the interactive-legend rollout (trend.js stacked + grouped bars) needed **zero** change
  to the SFLegend module — just `data-series` on the bar rects + an opt-in flag on the legend call.
  The convention-based module (phase 1) paid off immediately: each new chart is a ~4-line adoption.
- **Look before you build:** `curves.js` already had a hand-rolled interactive legend (show/hide +
  Show-all/Hide-all). Had I not read it, I'd have "added" a feature it already has. LESSON for the
  remaining rollout: grep each target for an existing toggle before adopting SFLegend — some charts
  are already done, and duplicating would regress (two competing handlers).
- **Honest degradation beats hidden cleverness:** hiding a STACKED segment leaves its gap rather than
  silently re-stacking. Re-stacking would misrepresent the bar's composition; the gap plainly says
  "this segment is hidden." A forensic tool should prefer the visibly-honest behavior.

### 2026-07-19 (cont. 6) — a good abstraction turns an "18-file" ask into a module + one adopter
- The operator wanted interactive legends "on ALL charts, all pages." The naive read is an 18-file
  edit (no shared legend helper exists). The better read: build ONE generic, opt-in module
  (`SFLegend`) keyed by data-attributes, wire the FIRST chart (the one screenshotted), and let the
  rest adopt the convention in phased PRs — delivering the capability now without a big-bang.
- **The non-obvious hard part was animation, not the click.** trend/curves/margin steppers rebuild
  their series SVG every frame, so a "hide this element" toggle is dropped on the next redraw. A lazy
  per-scope MutationObserver that re-applies the hidden set on childList changes (and disconnects
  when nothing is hidden) solves it generically — and watching childList only means apply()'s own
  style writes can't retrigger it (no loop). LESSON: when adding interactivity to a chart, ask "does
  this chart re-render?" first; if yes, the state must live outside the redrawn DOM and re-apply.
- **Honest-N still applies to a view filter.** Hiding a series is display:none on the SVG only — the
  data-table and Excel export are untouched, so a "hidden" series is a view choice, not a dropped
  number (Law 2). Worth stating explicitly so a future reader doesn't mistake it for data suppression.
- **Match the repo's test idiom.** The repo executes vendored JS via node .mjs harnesses (theme.js,
  sra_derive), not Playwright. A faithful DOM-stub harness that drives the real module + asserts the
  redraw-persistence is the consistent, cheap verification — no new browser-test dependency introduced.

### 2026-07-19 (cont. 5) — a concurrent tree-mutating agent corrupted a commit; and audit-before-ship pays
- **The costly one:** while a commit was in flight, a background audit-workflow agent ran
  `git checkout origin/main -- sra.py` in the same working tree, so the commit captured a class-less
  engine file → CI mypy failed on the just-opened PR. LESSON: never run agents that can mutate the
  working tree concurrently with a `git add`/`commit`; commit (or use an isolated worktree) BEFORE
  launching any audit fan-out. The re-run audit was made **strictly read-only** (agents forbidden any
  write/git-mutation) and behaved.
- **Measure the tool's own exit, not a pipe's:** the gate had `bandit … | tail; echo $?` — reporting
  tail's exit (0), not bandit's. Real bandit findings (bare asserts, a B608 false positive) sat hidden
  until a clean rebuild surfaced them. Use `${PIPESTATUS[0]}` / run the checker unpiped.
- **Audit-before-ship earns its keep:** the read-only Ultracode audit of the *merged* #417 found a
  real Law-2 defect (M1: a summary/inactive monitor crashed the SSI run or silently reported the wrong
  plan mix) that 2 reviewers + a lead repro confirmed — caught only because the audit probed the
  non-scheduled-task edge the tests didn't. Adversarial verify (default-refuted) kept the noise out.
- **Fix bugs where the operator sees them, not just where they're reported:** the "hit stop, kept
  playing" bug lived in the master-vs-per-chart timer coupling, not the enlarge code the report named.
  Reading the screenshot carefully (chart button said "▶ Play" yet it animated ⇒ the *master* drove
  it) pinned the true cause; `event.isTrusted` cleanly separates the master's programmatic
  `.click()` from a real user click, so the fix is one shared coordinator, not per-chart edits.
- **Know when a feature is a phase, not a commit:** "interactive legends on ALL charts" meets ~18
  hand-rolled legends with no shared helper. The right answer is a reusable module + a phased,
  chart-by-chart rollout (DESIGN-SYSTEM: never big-bang) — ship the verified bug fixes now, scope the
  feature honestly, rather than half-do a cross-cutting change.

### 2026-07-19 (cont. 5) — an adversarial-audit WORKFLOW corrupted my working tree mid-commit; and a piped `$?` hid a real bandit failure
- **The incident.** After the local gate passed on #9 (v1.0.81) I launched a background multi-agent
  **audit workflow** over the *uncommitted* diff, then committed + pushed. CI failed at **mypy** with
  8 `has no attribute` errors — the committed `sra.py` was the **class-less baseline**, missing every
  line of the conditional-branching code, even though app.py/tests/JS/docs committed correctly. Root
  cause: a workflow review agent (byte-freeze dimension) ran `git checkout origin/main -- sra.py` to
  diff the baseline and never restored it; that landed in the window before my `git add -A`, so the
  commit captured the reverted file. Worse, when I first looked I **misread** the working-tree diff
  (the classes shown as `+` because HEAD lacked them) as a corruption and `git checkout`-reverted the
  *correct* working copy — then a still-running agent re-added it — a moving target until I stopped the
  workflow with its **task id** (not the run id) and hard-reset `sra.py` to the pinned `origin/main`
  blob, re-applying every edit deterministically.
- **Lessons (generalizable, high value):**
  1. **Never run a workflow whose agents can touch the working tree while you have uncommitted work
     you intend to commit.** Audit/review agents must be *read-only* — or run with `isolation:
     "worktree"` so they operate on a throwaway copy. A concurrent `git checkout`/edit from an agent
     is indistinguishable from your own change and will be captured by `git add -A`.
  2. **Commit BEFORE launching a background audit**, not after. Review the committed SHA; push fixes
     as follow-ups. (The draft-PR + Codex-review loop already provides the adversarial pass safely.)
  3. **When git state looks impossible, establish ground truth before acting** — `git show HEAD:file`,
     `md5sum` vs `origin/main`, `git status` — don't `git checkout` on a hunch. My revert destroyed the
     one correct copy.
  4. **`cmd | tail; echo $?` reports the tail's exit, not cmd's.** My "bandit exit: 0" was `tail`'s 0
     the whole time — bandit had been failing on two bare `assert`s (B101) since the first gate run,
     and would have failed CI's bandit step too (CI just never reached it, dying at mypy first). For a
     pass/fail gate, capture the tool's OWN exit: `cmd; echo $?` or `set -o pipefail`.
- **Two real code fixes surfaced by rebuilding clean:** (a) replaced the two bare `assert`s with
  explicit `raise ... # pragma: no cover` (the src convention is **zero** bare asserts — they vanish
  under `python -O`, and bandit B101-flags them); (b) an HTML `<select>` element plus the tooltip
  words "offset **from** project start" tripped bandit's **B608** `select…from` SQL heuristic — reworded
  to "offset into the project" (no `# nosec` needed). Both were latent in the original build; the
  forced clean-rebuild caught them.

### 2026-07-19 (cont. 4) — a shadowed loop variable silently corrupted a sampler arg; the new tests caught it
- Building Hulett #9 conditional branching (ADR-0274), the per-iteration switch did
  `plan = cond.plan_b if trips else cond.plan_a`. That **shadowed** the outer `plan` — the Latin
  Hypercube plan passed to `_iteration_duration_overrides(..., plan=plan)` at the top of the *next*
  iteration. Iteration 0 ran fine; iteration 1 handed a `BranchPlan` to the LHS sampler →
  `AttributeError: 'BranchPlan' object has no attribute 'columns'`. Fix: rename to `chosen_plan`.
- **Why it was caught instantly:** the 11 new engine tests (written before wiring the web) failed on
  the very first non-frozen run. A 2-second signal, not a field bug. Reinforces the standing habit:
  write the pins first, run them the moment the mechanism exists.
- **Generalizable lesson:** in a long function that already threads a variable named for a domain
  noun (`plan` = the LHS plan), never reuse that name for a loop-local of a *different* type. mypy
  did **not** catch it (both are objects passed positionally through an `Any`-ish boundary), and ruff
  doesn't flag same-name rebind. Only an executable test did. Prefer distinct, specific local names
  (`chosen_plan`, `plan_arm`) over the tempting short one.
- **Also reaffirmed:** mirroring an existing feature's *entire* surface pays off. #9 touched the
  exact same file set as #8 (`sra.py`, `app.py`, `sra_ssi.js`, the two test files, one ADR, the
  state docs) — grepping #8's wiring points (`sra_branch_seq`, `_schedule_branches`, the 4
  `compute_sra_ssi` call sites, save/load, export tables, DOCX) gave a complete checklist so nothing
  was missed (e.g. the dense-id Save/Load guard from #8's Codex P1 was carried over pre-emptively).
- **Prototype-first, again:** `scratchpad/cond_branch_verify.py` proved the load-bearing
  *monitor-finish invariance* (a downstream branch can't move its upstream monitor's finish, so the
  finish-metric condition reads cleanly from one probe solve) **before** any engine code — so the
  probe-solve design was known-correct, not hoped-correct.

### 2026-07-19 (cont. 3) — an automated reviewer caught three real edge cases my own tests missed
- **Context:** right after probabilistic branching (#415) merged, a **Codex bot review** posted three
  findings on the exact feature. I verified each against the code (not blindly applying — external
  review is a *claim*, same discipline as an audit) and all three were **real**:
  - **Save/Load id collision:** the restore set the id counter to the loaded *count*, not the highest
    suffix; a gapped id set (only "B3" survives) could later recreate "B3", and since the fragnet map
    is keyed by id, one branch would overwrite another's tie. My own round-trip test used dense ids,
    so it never exercised the gap.
  - **Two branches on the same tie:** the first consumed the FS tie, the second silently went inert
    (order-dependent). My tests only ever put one branch per tie.
  - **Exports didn't disclose branches:** the export path *did* pass `branches=` (so the numbers
    shifted), but the XLSX/DOCX tables listed only the risk register — a self-describing-report gap I
    simply didn't think to test, because the on-screen table was right.
- **Lesson (generalizes → Part V):** my test suite proved the feature's *happy paths and core
  invariants* well, but missed **cross-feature seams** — Save/Load × id generation, multiplicity on a
  shared resource, and *every output surface* (screen vs. export) of a new modeled input. When adding
  a modeled input that shifts results, enumerate: does it round-trip through Save/Load with adversarial
  ids? what happens with two of them on the same target? and is it disclosed on **every** export, not
  just the screen? An independent reviewer (human or bot) is cheap insurance for exactly the seams the
  author's mental model glosses over — treat its findings as leads to verify, and fold the confirmed
  ones back as tests (I added four).
- **Process note:** the PR merged before the review landed, so these became follow-up fixes on a new
  branch rather than pre-merge edits. Not wrong (draft-PR review + fast follow-up works), but a beat
  more patience before merging a large new feature would have folded them into the original PR.

### 2026-07-19 (cont. 2) — prototype-verify a NEW mechanism against the trusted solver before the big build
- **Context:** probabilistic branching (Hulett #8, ADR-0273) — the first SRA feature that changes
  network *topology* per iteration (inserting a rework fragnet), not just activity durations. The
  natural fear was a large, architecturally-significant build (per-iteration schedule rebuilds, new
  spec types, merge-bias correctness).
- **What worked:** before writing a line of feature code, a ~60-line scratchpad script drove the
  **real `compute_cpm`** on a hand-built base + augmented schedule and proved the load-bearing
  claim: a fragnet inserted as `pred --FS0--> F --FS(lag)--> before` with `F` at duration 0 is
  **byte-identical** to the base (calendars included), firing shifts the finish exactly when `F`
  drives, an off-path fire that doesn't overtake leaves the finish unchanged (merge bias), and a
  synthetic high uid doesn't perturb base timings. That single verification collapsed the design to
  its elegant form: **one** augmented schedule built up front, `F`'s duration toggled 0/sampled via
  the existing `duration_overrides` hook — no per-iteration rebuild, the trusted solver stays the
  sole source of every number, and the freeze is automatic (no branch → no augmentation).
- **Lesson (generalizes → Part III / Part VI):** when a feature introduces a genuinely NEW
  mechanism (not just a new number), spend the cheap prototype first — drive the *real* engine on a
  tiny fixture and assert the invariant you're about to depend on. It's the difference between
  discovering "0-duration FS chains are exact passthroughs" in 5 minutes vs. debugging a subtle
  calendar mismatch after building the whole feature on a wrong assumption. The prototype also
  becomes the ADR's verification pointer and the shape of the engine tests.
- **Process note:** the build was large and architecturally significant, so I tried to checkpoint
  scope with the operator (AskUserQuestion + a recommendation). The tool aborted and the operator
  was away; with the standing "do all you can without files" mandate and the draft-PR review as the
  scope safety net, I proceeded with the recommended MVP rather than stall. Reasonable call, but the
  reminder stands: for a big speculative build, a cheap prototype + a draft PR the operator can
  redirect beats either stalling or over-building on a guess.

### 2026-07-19 (cont.) — verify-everything caught a false premise in our OWN handoff
- **Context:** implementing the risk-critical Gantt tint (Hulett #12, ADR-0272). The prior session's
  handoff — which *we* wrote — scoped it as a "pure UI feature: tint the SSI grid by criticality
  index from the last MC run," on the belief that `SSIResult` already carried a per-activity
  Criticality Index.
- **The catch:** a read-only recon agent, then a first-hand code read, proved it did **not**.
  `compute_sra_ssi` tallies `critical_counts` every iteration and then **discards** it —
  `_build_ssi_result` never received it and `SSIResult` had no CI field. CI only ever lived on the
  **legacy** `compute_sra`/`SRAResult.activities` path (a *different* simulation, exposed at
  `/api/sra`, top-20-truncated). Grepping `criticality` matched BOTH paths; the earlier session had
  conflated them.
- **Why it mattered:** had we trusted the handoff, we'd have wired the tint to the wrong (legacy,
  truncated) data source or invented a web-side re-computation (duplicating engine logic, breaking
  Law 2's single source of truth). Instead the correct fix was a *minimal additive* engine change:
  stop discarding the already-computed value (`SSIResult.criticality`, appended last, inert to the
  finish-cdf + ssi==jcl pins). No new math.
- **Lesson (generalizes → Part V / Part VI):** a handoff or ADR is a **claim, not a fact** — even
  one we authored. "READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING" applies to our own prior
  notes as hard as to an external audit. A single grep that matches two code paths is a classic way
  a false premise survives into the next session; disambiguate which path owns the value before
  building on it. The recon-agent-then-lead-reverify pattern paid for itself here in one catch.
- **Also:** the strict CSP (`script-src 'self'`, no `unsafe-eval`) blocks Playwright's
  `wait_for_function`/string-eval — a *good* signal the air-gap holds. Drive browser checks with
  `page.evaluate`/`eval_on_selector` (isolated world) and poll manually instead.

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
