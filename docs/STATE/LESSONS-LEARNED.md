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

### 2026-08-31 (WP2) — `git checkout --` is not a mutation restore; and a wrong oracle is indistinguishable from a defect

- **`git checkout --` reverts to HEAD, not to the tree under test.** A mutation battery used it to
  back out three mutations, and because all three files carried THIS session's fixes, the "restore"
  silently deleted them. Worse, the next mutation in the same chain then asserted its anchor
  against reverted code, failed to apply, and reported RED while measuring an unfixed tree — a
  mutation that "passed" having proved nothing. WP1 already wrote *diff the tree after every
  restore chain*; that diff is what caught this. The missing half: **restore from a `cp` of the
  WORKING TREE, and never use `git checkout --` on a file the change itself touches.**
- **A wrong oracle looks exactly like a defect.** The first stepper sweep reported "the chart did
  not move" for three families. All three were the instrument: the digest walked SVG only, and
  `/evolution` and `/driving-path` paint HTML-table Gantts while `/trend`'s quality drill paints
  into `#qualBars`, not the `#qualChart` the probe had assumed existed. Had those been written up,
  three healthy controls would have been "fixed". The cure is a pinned oracle:
  `test_chart_digest_is_stable_and_sensitive` proves the digest both HOLDS STILL across a no-op
  and MOVES on a real step, per family, before any assertion built on it is believed.
- **Measuring the wrong element calls a working control dead.** `#uiScale` looked inert because the
  probe measured `document.body`, which is full-bleed at every zoom. Measured on a heading's own
  box it scales correctly (212 → 265 → 371 → 191 px). Second near-miss of the session, same shape.
- **A probe's own wait can invent a finding and then retract it.** Reading `page.url` after
  `wait_for_load_state` — before the form's navigation had even begun — reported the language
  selector landing on the page it started from, contradicting an earlier run. `expect_navigation`
  settled it. When two of your own runs disagree, the instrument is the suspect first.
- **A guard with a hand-written population fails OPEN, and that is how a defect survives.** The A2
  reduced-motion pin checked five module names typed out by hand; twelve modules are animated, and
  the one outside the list (`driving_path.js`) was the one ignoring the setting. The guard passed
  for years while being false. Computed population + a documented EXCLUSION list makes a new
  animated module RED by default — the same correction ADR-0439 forced on a hand-written route
  list, now made twice, which is the argument for making it the default shape of every guard.
- **A defensive `if` around a load-order dependency hides the failure it was meant to survive.**
  `if (window.SFPlayAll) window.SFPlayAll.register(stop)` reads as prudent and silently skipped the
  registration on every page whose script ran before `chartframe.js` — which the layout guarantees,
  since it emits `chartframe.js` after `<main>`. The one page where it worked did so only because
  it registered from inside a `fetch` callback. **A guard that can be falsy for a structural reason
  needs an else-branch, not a shrug.**
- **The server session outlives a browser context.** Setting the UI language in one probe step
  translated a later step's page and briefly looked like a translation bug; drivers that mutate
  session state must restore it in a `finally`.

### 2026-08-31 — A census driver's first real click found two features that never worked; free text can never be a control signature

- WP1's new drivers clicked controls the byte-pins had frozen for months — and two families
  were dead on arrival: the column-resize grips laid out 7×0px (Chromium ignores
  top/bottom/%-height on abs-pos children of table cells — sticky OR relative), and the
  sticky proxy scrollbar tracked content only when the async table fetch happened to beat the
  DOMContentLoaded auto-attach. Both sat under green suites because the pins froze BYTES and
  the docstrings CLAIMED "Chromium-verified" with no committed browser half. The lesson: a
  feature is not verified until a synthetic pointer has moved the measured world; a passing
  byte-pin over a dead feature is worse than no test — it certifies the corpse.
- The first census harvest matched project cards on "/" because a schedule NAME contained
  "Fit-Out", help prose matched via "dis-play" and "s-pan", and `tooltips.js` had moved every
  `title=` into `data-sf-title` at load. A control-family recognizer must run on structural
  vocabulary only (id + className), with `pan(?!d)` to keep "expand" out — free text is
  operator data, and matching it makes the census's population depend on the schedule loaded.
- Two timing races only differed by 100–500 ms of wait: the sticky driver failed at
  1200/600 ms and passed at 1500/700 ms. The fix was not a longer wait — it was finding the
  race (attach-time `firstElementChild` observation) and removing it. A test that needs a
  lucky wait is measuring the race, not the feature.
- `tbody.innerHTML = ""` collapses the pane's content height and the browser clamps scrollTop
  to 0 BEFORE the repaint reads it — so the S5 window could never leave the top, and every
  pre-fix repaint had silently been losing the operator's scroll position. Capture the scroll
  state before a destructive DOM clear, compute from the capture, restore after.
- A mutation battery piped through `head` gets SIGPIPE-killed mid-mutation: the second run
  died right after P1's mutation and left `if (1) return;` in app.js — caught only because
  `git status` was checked afterward. Never pipe a battery's output; always diff the tree
  after a restore chain.
### 2026-08-28 — the reporter's machine is a dimension of the matrix, and "everything painted" can still be "nothing visible"

- The ADR-0440 chase reproduced BOTH reported symptoms perfectly — via a mechanism the
  operator's machine turned out not to have (their storage was byte-clean). The 13-cell matrix
  varied STATE, THEME and VIEWPORT but never SPAN or ROW COUNT; the operator's 12.3-year,
  2,301-activity IPMR sat outside every cell. **Lesson: a reproduction matrix must include the
  reporter's data SHAPE, not just hostile state — ask for the scale numbers (span, rows) in the
  first evidence request.**
- After Fit, every bar existed and was correctly painted in a 969px track — inside a 40,104px
  column with the pane scrolled 24,206px into the dead zone. `bars_total` said healthy;
  `getBoundingClientRect().left` said −24,205. **Measure position, not just presence.** A probe
  counting "visible marks" must also scroll its grid into view first, or page layout (a KPI
  block filling the first viewport) reads as a defect.
- The stale column came from a fix: SFColResize's attach-time g-head sizing was ITSELF the cure
  for a prior dead-scroll bug — correct on every `render()`, silently absent on every
  `reflow()`. **When a subsystem has two rebuild paths of different depths, a fix applied to
  one is a bug scheduled for the other.**
- The first whole-fit threshold (3 pages) regressed a measured, operator-approved behavior
  (ADR-0438's zoomed+seat opening, ~7.5 pages) and the neighbour suite caught it in minutes.
  **Anchor a new threshold on the pathological case with ~2× headroom from any measured-good
  case, and treat the neighbour module's red as the boundary-setter, not an obstacle.**
- A mutation-restore script asserted on text the mutation had never removed and silently
  aborted the restore; the next run then re-measured the OLD mutation. **A restore must assert
  exactly what the mutation changed — and re-run the green side after every restore.**

### 2026-08-27 — a clamp that lives only on the EDIT path guards nothing the storage can say

- The operator's "controls do nothing / renders wrong" on three Gantt pages was a persisted
  `sf.timescale.v1` whose `size` never passed the dialog's 25–1000 clamp — because the clamp ran
  only in the number input's `input` listener. The LOAD path merged storage with a null-check.
  **Lesson: an invariant enforced at one entrance is not an invariant. Every boundary the value
  can cross (dialog edit, storage load, future import) needs the same validator, or the weakest
  one defines the real contract.**
- The defect was invisible to every fresh-profile probe (zero console errors, state-borne) and
  survived Reset-view BY DESIGN (persist.js exempts preferences). A reproduction matrix that
  SEEDS hostile state via `context.add_init_script` found it in one pass — post-load seeding is
  vacuous because the config is read at script parse time.
- The matrix's first run flagged its own /driving-path BASELINE: the page opens on the newest
  version and TP4 v5's corridor for 11→26 is legitimately empty. A red for the wrong reason is
  not a red — the probe learned to step back one version before measuring.
- The B2 crash (`labelDef` indexing `LABELS[bogus]` → `[]` → `defs[0].fn`) fires on the tier
  REBUILD, not reliably inside the first-paint error-collection window: the committed test had to
  FORCE a zoom reflow before asserting `errors == []`, or its crash channel passed vacuously —
  found only because the belt-revert mutation failed to go red on the expected assert.
- Two lookup tables driven by the same key had different fallbacks (`UNITS[x] || UNITS.months`
  vs `LABELS[x] || []`). The pair is now consistent. **Grep for the sibling table when hardening
  one.**


### 2026-08-27 — a byte-frozen control can be dead, and state that survives every reset is invisible to a fresh profile

Planning the operator's full-tool audit surfaced two lessons before a line of campaign code was
written, both from measurement rather than misfortune.

- **A byte-freeze pin proves the control EXISTS; it proves nothing about what it DOES.** The
  operator named zoom and timescale as broken. The census found the r11 contract freezes those
  controls' form bytes (md5 + length) and their script bytes — and that **zero** browser tests
  drive them: `#dpZoomIn`/`#dpZoomOut` appear in no test even as strings, `#dpPlay`/`#evoPlay`
  autoplay is driven by nothing, every four-theme test sets `data-theme` with `setAttribute`
  instead of clicking the real `#themeSelect`, and the SRA paste-from-Excel handler has never been
  executed. Twenty-seven interactive behaviors sit under passing pins. JS-01 (ADR-0416) already
  taught that a client contract can rot while server tests stay green; the general form is: **the
  suite's unit of proof must be the EFFECT of a real gesture (a measured box/DOM change), not the
  presence or bytes of the control.** That is what the campaign's control-effect census exists to
  make standing.
- **Persisted state that deliberately survives every reset is exactly the state a clean probe
  cannot see.** The three broken pages rendered error-free in a fresh Chromium profile — because
  the prime suspect, `localStorage["sf.timescale.v1"]`, is merged unvalidated at script parse
  time, is exempted BY DESIGN from Reset-view and launch wipes, and its 25–1000 clamp exists only
  on dialog edits. A persisted `size: 1` or `size: 100000` reproduces both reported symptoms on
  every Gantt page. Two rules from this: when a user reports "broken on my machine" and the fresh
  probe is clean, **enumerate the state that persists across their resets first**; and any test
  seeding such state must use `context.add_init_script` — seeding after `goto` is too late (the
  module reads localStorage at parse time) and passes vacuously.
- Also banked: the 2026-08-18 coverage instrument existed only in a session scratchpad and is
  unrecoverable — the same "the hard-to-reach parts of an oracle are the parts most likely to be
  lost" failure ADR-0381 named. An instrument that produced a number the project still quotes
  MUST be committed with the number.


### 2026-08-26 — a green PR is not a finished one, and the babysitting interval should decay

**#612 sat green, mergeable and unreviewed for ~19 hours** before the operator marked it ready and
merged it. I checked in seven times. The first two check-ins were worth it — they caught CI still
running and confirmed the conclusions. The last five returned *identical* state and taught nothing.

- **Lesson: match the poll interval to what can actually change, and let it decay.** Once a PR is
  green, mergeable and waiting on a human, webhooks already cover every real event (review, push,
  merge). The only thing polling backstops is `main` moving under the branch — a transition
  webhooks do not reliably deliver. That justifies *a* check-in, not an hourly one. I widened
  25m → 60m → 90m → 3h → 4h → 6h; the right shape from the start would have been ~1h while CI runs,
  then straight to multi-hour once green. A check-in that reports "no change" seven times is not
  diligence, it is noise with a cost.
- **The backstop earned its keep, though, and twice.** `main` moved under this branch on #609 and
  again on #611 — both docs-only session closes, both conflicting all four state docs. In this
  repo that is not an edge case, it is the norm: session closes land often and always touch
  HANDOFF / SESSION-LOG / LESSONS-LEARNED / NEXT-SESSION-PROMPT.
- **The rule that came out of resolving it twice: re-do the rotation on the NEW main's docs; never
  replay yours over a stale base.** #611 had updated the 2026-08-21 handoff *in place* and added an
  **OPEN OPERATOR ASK** block my branch could not know about. My branch had rotated that whole
  section into the archive. A naive "keep mine" would have silently deleted a live, unanswered
  operator item — the worst kind of loss, because nothing would have failed. Take the incoming
  version as the base, re-apply your change on top, and verify the thing you might have dropped is
  still there by name.
- **Post-squash hygiene is not optional here.** GitHub auto-deletes the merged head branch, so the
  local tracking ref goes stale and the stop hook mis-reports GitHub's own squash commit as an
  unverified unpushed commit. `fetch --prune` + `remote set-head` + `checkout -B <branch>
  origin/main` + `branch --unset-upstream`, every time.

### 2026-08-25 — a sweep that writes its own population will always find it clean

**The single lesson.** I built two censuses to answer a question nobody had asked of this codebase
— does an operator's activity name reach a page or an export as MARKUP? Both returned **CLEAN on
the first run**, and **both were blind**. Neither clean was evidence of anything until I broke the
product and watched them fail.

* The page census **hand-wrote its route list**. `/analysis` and `/wbs` are `/{name}` routes, so
  two of its twenty-eight pages returned **404 — and a 404 contains none of the injected markup,
  so it scored as "escaped"**. Worse, hand-writing the list meant every *parameterized* route was
  skipped, and those are precisely the per-schedule pages where activity names render densest. The
  instrument was blind exactly where the risk was highest, and its output looked exhaustive.
* The browser oracle's **positive control was wrong about where the defect lands**. I assigned
  `</td></tr><tr><td>SFROWBREAK` to a `<td>`'s own `innerHTML` and expected a corrupted table. The
  HTML parser **discards stray `</td></tr>` in that context** — the marker stayed inside the
  original cell and the symptom could never fire. The corruption is only reachable when a renderer
  builds a whole table STRING and assigns it to a container. Had the teeth test not existed, that
  third symptom would have been permanent dead weight inside a guard whose entire purpose is to
  fire.

**Generalises to a rule.** *A sweep that defines its own population will always conclude the
population is fine.* Enumerate from the live artifact (the app object, the archive, the AST), never
from a list a human typed — and **refuse to score a non-success response**, because "the page
carried no injected content" and "the page was an error" are indistinguishable to a substring test.
This is the same failure as BROWSER-ORPHAN-01 (twenty-three modules that never RAN behind four that
FAILED) wearing different clothes: the count was of what the instrument could see, not of what
existed.

**A second, sharper one: a red for the wrong reason is not a red — and a floor can cause it.** I put
a population floor in the export census *before* the substantive assertion, and counted only
well-formed archives as the population. So when I mutated the XML writer, the corruption shrank the
population and the FLOOR fired first: the test reported *"the enumerator is broken"* for a tree
whose actual defect was an unescaped writer. A guard that fails with the wrong diagnosis costs a
future session the hour it takes to disbelieve the message. Substantive assertion first; floor
second; and never let a defect shrink the population you are floor-checking.

**And the ledger lesson, which is really a QC-2 lesson.** **MF-02 had shipped as ADR-0411 and the
audit ledger still filed it under "awaiting fix — Not yet implemented"** — and the kickoff dutifully
copied it into the standing queue, where it would have sent this session at work finished a week
earlier. That is the *third* time this project has been misdirected by its own testimony. I settled
it by measuring the shipped workbook BYTES rather than reading `_export_cell`, then swept every one
of the 35 open row IDs against all 440 ADR files; MF-02 was the only stale entry. Two things worth
carrying: **a work queue is data, and data goes stale unless something asserts it** — the same
argument that produced `tests/test_standing_rules.py`; and when you report such a sweep, **say which
direction it bounds**, because an ADR can close a row without ever naming its ID, so "one stale row"
is a floor, not a total.

**What I did NOT do, on purpose.** Six E501 per-file-ignores are provably dead (two independent
oracles agree). I left them. The stated policy attaches that exemption to what a module *is* — an
extracted page module whose HTML f-strings will grow back — not to what it currently contains, so
"cleaning them up" would fight the documented intent and fail the next HTML edit. Likewise
`evolution.py` renders `0%` for an absent activity beside a cell that correctly renders `—`, in a
table whose heading asserts those activities completed: contradictory, but **measured unreachable**,
so it is reported and not repaired. A finding you can prove is not automatically a change you should
make; scope the finding before acting on it.

### 2026-08-21 (b) — a test that fakes the browser object proves your code, not the integration

The operator installed v1.0.221 and reported the multi-folder load still did not work. The
shipped browser test was green — and it was green about the wrong thing.

- **The oracle was faked at exactly the seam that mattered.** `test_multi_folder_drop_browser`
  patches `DataTransferItem.prototype.webkitGetAsEntry` to hand back invented entry trees. That
  is a real proof of OUR traversal (recursion, batched `readEntries` drain, rel-path shaping)
  and NO proof at all that the browser hands us those objects on a real drag. A green test can
  be honest about its half and still leave the operator's half untested.
- **The stronger oracle existed and cost ten minutes**: CDP `Input.dispatchDragEvent` with real
  directory paths makes Chrome mint genuine `FileSystemDirectoryEntry` objects, so the whole
  chain — native entries → our walk → `fetch('/upload')` → grouping — runs for real. It
  vindicated the feature (`[('Apollo', folder, 2), ('Artemis', folder, 1), ('Loosey', title, 1)]`),
  which is the point: the fake-based test was not lying, but only the real one could establish that.
- **The actual defect was in the ANSWER, not the code.** The operator was using the folder
  PICKER, which no browser will let multi-select, while ctrl/shift on "choose files…" has
  worked all along. Time went into re-proving the drop when the first question should have been
  *which gesture are you using* — the cheap discriminator, asked before the expensive probe.
- **Lesson, generalised:** when a feature depends on an object only the platform can mint, name
  the faked seam in the test's own docstring and record what would prove the other half. Then,
  the first time a user says "it still doesn't work," you already know which half is unproven —
  and you ask which gesture they used before you re-litigate the code.


### 2026-08-21 — the platform sets the gesture, and a mutation revert must never ride git checkout

Two operator asks (multi-folder → one Project per folder, ADR-0437; /driving-path complete
schedule of any loaded file, ADR-0438) and four lessons:

- **Diagnose which LAYER owns the gap before building.** "Select multiple folders at once" read
  as a server feature and was really three facts: the server already grouped per-file top
  folder (a probe proved it in minutes, mutation-proved in one more), the folder-picker DIALOG
  can never multi-select (webkitdirectory overrides multiple — a platform limit no code of ours
  moves), and the drop path — the one gesture that CAN carry several folders — didn't traverse
  directories at all. The fix was one JS traversal plus copy; the server shipped unchanged.
- **A dropped folder failing as "online-only in OneDrive" was a misdiagnosis by reuse**: the
  bare directory File's read rejection took the unreadable-FILE reporting path. When an error
  message is shared by two causes, the rarer cause wears the wrong hint silently.
- **Never revert a mutation with `git checkout <file>` while that file carries uncommitted
  feature work** — it restores HEAD and vaporizes the work (app.py, re-applied from context).
  The home.js mutation minutes earlier used a scratch `.bak` copy — the correct shape was
  already in hand and got skipped ONCE, which is all it takes. Promoted rule: mutations
  mutate a copy-backed file, restores come from the copy, and git never touches it.
- **Reuse the sibling page's component instead of a twin**: "same columns by default as /path"
  is true BY CONSTRUCTION only because one FIELDS table in one path.js serves both pages —
  and the browser test still asserts header equality RENDERED, /path as the oracle, so the
  claim survives future drift in either page. A hand-copied column list would have been a
  second source of truth born stale.

### 2026-08-20 (d) — a brand is a character set, and a rename includes the finders

Renaming the product to POLARIS² surfaced three lessons in one hour. (1) A brand that must
survive terminal banners, docx headings and .lnk filenames is a CHARACTER decision, not a
markup one — U+00B2 renders in every medium the program writes; `<sup>` renders in exactly
one. The corollary constraint runs the other way: an ASCII-encoded artifact (the Windows
`.cmd` fallbacks) CANNOT carry the brand, and the honest move is a documented exception, not
a mojibake'd icon. (2) A rename is not done until the FINDERS are renamed: the installer
banner test locates its line by the substring "Schedule Forensics installer" — rename the
banner and the guard reports "banner missing", which looks like a regression but is the
locator lying. Sweep tests for the OLD name before calling a rename complete. (3) The
dist/ vs dist/wheel trap fired a second time in one day — a build ritual that exists only in
a test's error message will be violated by muscle memory ("python -m build --wheel" is the
reflex); the lockstep guard is what turns that reflex into a caught mistake instead of a
shipped stale wheel. Also: hand-set glyph geometry (the worm-style ²) is a RENDER claim —
the screenshot took 90 seconds and would have caught any malformed arc no assertion could.

### 2026-08-20 (c) — a screenshot is testimony about a version, and an identity can be a per-copy value

- The operator's "broken timescale" screenshot would not reproduce: the resume notes recorded
  their install as **v1.0.148** — seventy releases old — because a re-run installer reinstalls
  the wheel it embeds. Half a debugging task dissolved into ADR-0435 (banner prints the embedded
  version). **Lesson: before chasing a render bug from a report, establish WHICH BUILD produced
  the evidence** — a screenshot is testimony about a version, not about the tree. The defect was
  still made unrepresentable going forward (a chromium property test: header bands must cover
  the rightmost bar).
- Multi-.xer Mission Control: grouping keyed on `proj_short_name` — P6's Project ID, which the
  per-update copy workflow RENAMES every period (the same workflow ADR-0185 documented for
  `task_id`). **Lesson: an "identity" field must be checked against the workflow that produces
  the files — a value that is unique per EPS is by construction NOT stable across per-update
  copies.** The stable analogue of the MSPDI Title was the root PROJWBS project name all along.
- The /path data-date seat computed from model numbers landed 280 px off — the frozen columns
  re-measure after first paint (and again when fonts settle). **Lesson: seat a scroll from LIVE
  geometry (getBoundingClientRect delta) after a double animation frame + fonts.ready, never
  from layout numbers captured mid-paint.**
- `target=0` as a whole-schedule sentinel collided with a pinned contract: Project5's
  project-summary row IS UID 0, and a guard traced it expecting the summary note. **Lesson: a
  new sentinel needs the existing pins swept for real members of the sentinel's value space; the
  fix is to move the pin to a nonzero member of the same class, not to weaken it.**
- Two contract-pinned pages grew (r10: 3→4 panels; r11: path.js digest). Every count moved in a
  DELIBERATE re-baseline naming the operator ask, with the load-bearing sub-digests (the 11-line
  axis-caption block) proven unchanged. **Lesson: a pinned contract is not a prohibition on
  growth — it is a demand that growth be named**; and a new div-list chart must NOT wear
  `.chart-host` unless it wants chartframe's zoom bar.
- The differing-max-units engine test passed on FIRST RUN — the capacity formula was always
  right; every fixture just carried a uniform 1.0, so nothing could fail. **Lesson: a first-run
  green on a new test is either a true-positive twin or a vacuous pass — decide which by
  checking what the fixture SET can express, not what the assertion says.**

### 2026-08-20 (b) — a self-contained installer is a snapshot, and a green install can be 70 versions stale

- **The operator re-ran the installer they already had and got v1.0.148 instead of v1.0.218.** The
  run was green end to end — tier fit, Python found, venv re-used, converter kept, Java found, model
  ready, "DONE" — because nothing *was* wrong: an installer embeds its wheel, so it installs exactly
  the version it was built from and never consults the repo. **A file name is not a version.**
  Re-downloading over the stale file and re-running was the whole fix.
- **A one-file installer trades update-awareness for offline install, and the trade is invisible at
  the point of use.** The design is right for an air-gapped CUI tool; the missing piece is the tell.
  The banner prints the tier and not the embedded version, so the one number that would have caught
  this appears only *after* the operator has committed to the run, and `README-DISTRIBUTABLE.md` has
  no "updating an install you already have" section. A repo test already proves the built installers
  embed the CURRENT version — **nothing proves the operator is running a current installer.** Those
  are different claims, and only the first one had a guard.
- **"It ran successfully" and "it did what you wanted" are different claims** — this repo's
  green-test-that-cannot-fail defect, relocated into deployment. The diagnostic question is the same
  one QC-1 asks: *what would a WRONG outcome have looked like here?* Answer: identical, except one
  version string 25 lines up the log. When the failure mode is indistinguishable from success at the
  point of use, the tell has to be moved to where the decision is made.
- **Verify the deployed artifact, not the deployment command.** `pip show schedule-forensics` run
  against the venv's *own* python settled it in one line, both times — before the fix and after.
  Generalizes: after any install, read the version back out of the thing you installed into, and
  never accept the installer's own exit status as evidence of what it installed.

### 2026-08-20 (a) — two metrics can share a name, and the audit table knew before the operator did

- **"Same name" is not "same metric" — the Bible itself disagrees with itself by name.** The NASA
  library carries a ribbon "Hard Constraints" (must/mandatory only, no status filter) AND a DCMA
  "5. Hard Constraint" (adds the SNLT/FNLT caps). The ribbon page displayed the DCMA figure under
  the ribbon label; under the session-default Acumen-parity population that figure was 1 where
  Fuse showed 4. When a reference tool's number disagrees, FIRST ask which of the reference
  library's same-named metrics the surface claims — before debugging the arithmetic of the wrong
  one. (ADR-0429; the skill already warned: the SPI(t) audit found this exact class.)
- **A latent drift row is a loaded gun, and the audit table had already filed it.** ADR-0110
  classified this drift verbatim — "Latent: no parity impact unless a schedule carries
  SNLT/FNLT" — and every reference fixture happened to carry none that discriminate (TP3's two
  hard constraints are mandatory AND incomplete AND baselined: identical under all four candidate
  definitions). A calibration whose fixtures cannot separate two definitions certifies both; the
  operator's Starlight workbook was the first input where they part. Pair every "latent" drift
  row with a fixture that would TRIP it, at filing time.
- **A tree-wide renumber sed is a weapon.** `grep -rl ADR-0425 | sed s/0425/0428/` renumbered
  UPSTREAM files' legitimate citations — #602 had claimed ADR-0425 while this session ran.
  Caught only by reading `git status` afterwards and seeing files I never edited. Renumber MY
  files by explicit list, never by tree sweep; and fetch-before-numbering may need to run MORE
  THAN ONCE in a long session (0425 taken, then 0428 taken too; landed 0429).
- **A refutation log is a deliverable.** Six hypotheses for the Insufficient-Detail residual —
  each cheap to state, each REFUTED by one measured table against the committed pins — ended in
  an honest STOP: the oracle and the bytes contradict, and the missing artifact is the reference
  tool's own offender list for ONE cell. Enumerate-and-refute beats fitting an unfalsifiable
  rule; and "any constant in [1000, 1890] fits" is the smell that says the next hypothesis would
  be curve-fitting, not root-causing.
- **When two sources encode the same facts, the count can only prove they agree with each
  other.** Starlight's calendar carried its 112 holidays TWICE (old-style DayType-0 rows AND
  modern Exceptions) — and the importer dropped BOTH through one gate: the missing weekly
  pattern. Redundant encodings do not protect against a shared gatekeeper.
- **"Fallback to default" can be the bug even when the default is right.** The synthesized
  Mon-Fri/480 week was CORRECT for Starlight — what was wrong was throwing away the exceptions
  riding the discarded calendar. When degrading, degrade the unreadable PART, not the whole
  object.
- **A case typo cannot prove a pin whose normalizer lowercases.** The Bible-pin mutation
  "StartOnOrBEFORE" passed — legitimately, `_norm` case-folds — and only dropping a whole TERM
  went red. Match the mutation to the comparator's normalization, or the "proof" proves the
  normalizer, not the pin.

### 2026-08-18 (b) — an oracle can be blind in a way only the mutation exposes, and a "complete" series can still be missing a dimension

- **Two of my own tests passed under the exact mutation they existed to catch.** Both were written
  deliberately, both looked right, both were green — and both were worthless until run against a
  broken build. (1) The *pinning* test used a no-overlap question ("zzz qqq xyzzy") to prove the
  comparative frame survives fact selection. It does not discriminate: the block is inserted
  directly behind the pinned population facts, so it also leads the ranked tail and survives with
  or without `pinned`. The fix was a question that fills the cap with genuinely-matching facts,
  **plus a control that re-runs the selection with the pin removed and asserts the frame drops**.
  (2) The *population-scope* test probed for the finding's own title, which the route's 12-fact
  response cap trims out — so the fabricated signal was present in the evidence and absent from
  what the test read. It now probes the compact label carried by the pinned facts, **plus a
  control asserting the truncated populations really do fabricate**. Standing rule reinforced: a
  green test proves nothing until a mutation has made it red, and "I wrote it to catch X" is not
  evidence it catches X. **Run the mutation.**
- **A defect can hide behind a series that looks complete.** ADR-0392 gave the AI a per-version
  S-curve and finish series spanning all 31 loaded versions — genuinely cross-version, genuinely
  complete. It still left manipulation at N=2, because *per-version readings* and *pairwise diffs*
  are different shapes and only the first was covered. When a prior fix claims "spans every
  version", ask **which dimension** it spans; a diff dimension needs the PAIRS walked, not the
  versions read.
- **An affirmative negative is worse than silence.** The tool did not merely omit the early
  updates — it emitted *"No incomplete activity on the critical path had its duration shortened
  between v03.mpp and v04.mpp"*, scoped to 1 of 3 available comparisons and phrased as a finding.
  A reader (human or model) takes that as a verdict on the workbook. Any statement of ABSENCE must
  carry the scope it was measured over; "we did not look here" and "we looked and found nothing"
  are different results, and the second must never be printed for the first.
- **A count can be identical in both worlds while the content is wrong.** Diffing the
  target-truncated population fabricated a HIGH "13 activities deleted since the prior version"
  and simultaneously lost a real constraint signal — **5 signals before, 5 signals after**. Any
  oracle that had counted findings would have certified the bug. Compare the *set*, not the size.
- **The wheel must be rebuilt after the LAST source change, not the last one you thought was
  final.** The wheel + nine installers were regenerated, then a real defect was found in the new
  code and fixed — and the embedded wheel silently went stale against exactly those two files.
  ADR-0148's lockstep guard caught it (`pair_facts.py`, `pair_series.py` "content drifted"), which
  is precisely the incident it was written for. This is the standing "re-run the WHOLE gate after
  the LAST file change" trap wearing a different hat: **the wheel is a gate artifact, so it is
  subject to the same rule**. Sequence the close as: last source edit → statics → wheel +
  installers → full suite → commit. Rebuilding earlier is wasted work, and rebuilding later than
  the suite means the suite never saw the artifact it is certifying.
- **I wrote the defect I was fixing, into the fix.** `_series_fact` derived the version count as
  `len(steps) + 1` — right in every case any test exercised, and wrong exactly when a pair is
  uncomparable, where it rendered *"all 2 loaded version(s) were compared … every update is here"*
  over a 4-version workbook. Same shape as the affirmative negative the whole ADR exists to remove.
  Two general points. (1) **A derived count is a claim about the world and needs the same scrutiny
  as any other**; if the number can be carried rather than inferred, carry it. (2) **The tests were
  all green** — they were green because every fixture had every pair comparable, so the wrong
  formula was accidentally right everywhere it was exercised. It was found by *reading the emitted
  sentence*, which is the artifact the operator actually receives. Read the output, not only the
  assertions about the output.
- **`$PWD` is not a constant within one shell invocation.** A comparison probe did
  `cd "$MUT"` for the mutated tree, then `probe "$PWD"` for the "live" tree — by then `$PWD` was
  the worktree, so the same mutated tree was measured twice and the report said the fix did not
  work. The earlier `assert '$MUT' in schedule_forensics.__file__` discipline was what would have
  caught it, and it had been dropped from the helper. **Every measurement of "which tree" must
  re-assert which tree**, not inherit it from a variable set earlier in the same call.

### 2026-08-18 — a bounded sweep looks exhaustive, and a fix can be wrong in the direction you did not test

- **A sweep's population is part of its claim, and a bounded one under-reports by construction.**
  A dynamic coverage census flagged 25 routes with no adverse-path test. Fuzzing exactly those 25
  found **6** routes that answered 500 to a superscript in a form field. Fuzzing *every declared
  field of every route* found **12**, across 5 code sites — because routes that DO have adverse
  coverage carry the same bug in a field nobody fuzzed. The narrower sweep was not wrong about
  what it looked at; it was wrong about what it implied. This is the same shape as ADR-0418's
  "four modules" (23) and ADR-0420's "three surfaces" (eight), and it is now three-for-three:
  **when a sweep reports N, ask what it could not see before quoting N.**
- **A fix can be wrong in the direction the tests do not point.** The `isdigit()`-gated `int()`
  crash was real, and the first fix — `isascii() and isdigit()` — closed every crash and passed
  the crash sweep. It was still wrong: measured across all 788 single-character numeric code
  points it disagrees with `int()` on **650**, so Arabic-Indic digits that used to resolve would
  have silently stopped. A crash-only test cannot see a narrowing. `str.isdecimal()` disagrees on
  **zero** and is the exact predicate. **What caught it was the guard-the-guard** — an assertion
  that every probe value must be `isdigit()`-true AND make `int()` raise — which failed on `٣`
  because `int("٣") == 3`. A control written only to stop a sweep passing vacuously is what
  stopped a bad fix from shipping. Under Law 2 the near-miss was the worse bug: a crash announces
  itself, a silently narrowed parser returns a wrong answer.
- **The product is frequently its own oracle — look there before reaching for a reference export.**
  Twice in one session the codebase already contained the correct semantic while other sites
  ignored it. `/api/driving-path` pairs `a.scoped` with `a.cpm` and cites ADR-0263 in a comment,
  while `/api/ask` handed the same engine call the raw schedule; `sra_grid_save`'s local `_uid`
  helper documents *"not isdigit(), which admits values int() rejects … and would 500 the
  endpoint"* while five other sites kept the broken pattern. An internal contradiction settles
  intent without an external oracle, and it is cheaper to find than a vendor export.
- **The strongest differential is two surfaces of the same product disagreeing in one session.**
  With two files loaded and a filter on, `/api/ask` returned the engine's driving-path facts and
  `/api/ask/{name}` returned none — same session, same question. That single observation carried
  more evidential weight than any amount of reading, and it named the correct behaviour for free.
- **An entering hypothesis that is refuted is a result, not a wasted probe — provided you say so.**
  `AI-DRIVE-01` was approached expecting "the AI will cite an activity the analyst filtered away".
  That is false: a filtered-out UID is absent from the scoped CPM either way. The real behaviour
  was that *all* driving-path facts vanished, silently, including for in-scope activities. Had the
  probe been written only to confirm the hypothesis it would have returned "no defect".
- **Instrument the framework at a class method when import timing is in play.** The route census
  hooks `FastAPI.build_middleware_stack` rather than patching `create_app` by name, so it cannot
  be defeated by a test module that imported `create_app` earlier — the same per-call-site trap
  that has bitten monkeypatching here repeatedly. The companion census that wraps engine callables
  had to sweep *every loaded module holding a reference*, because `ai/driving_facts.py` binds
  `compute_driving_slack` with an import-time `from … import`; a guard that patched only the
  defining module would have been blind to the exact call that regressed, and a test now pins that.

### 2026-08-17 (e) — a row that names three surfaces may be naming three members of a class

- **"Is it wrong?" and "can it be reached?" are two measurements, and reporting one as the other
  misinforms.** IMP-01 is a real defect: an MSPDI weekday the file declares WORKING but leaves
  without usable `<WorkingTimes>` was counted as nothing by the day census and as 480 by the
  fallback four lines below, so a mixed calendar let a minority explicit day win outright — a 4 h
  Monday among four default days produced 240 min/day and displayed an 80-hour task as 20 days
  instead of 10. It is also **unreachable from the entire reference corpus**: 56 real MSPDI
  documents carry the construct zero times, because MPXJ always writes `WorkingTimes`. Both facts
  are load-bearing. "Latent" is not a softer word for "wrong", and "wrong" is not a licence to
  imply "currently producing bad numbers". State both, or the reader cannot price the fix.
- **A ledger row naming N surfaces may be naming N instances of a CLASS.** The audit filed three
  separate MIXED-POPULATION rows. A computed AST census over the view layer found the same shape in
  **eight** places — and the three that had been named were not the worst of them. The unnamed
  `_schedule_facts` builds the fact sheet the **AI is allowed to cite**, so the raw/scoped mismatch
  reached the narrative layer, not just a panel. This is the same shape as ADR-0418's "four modules
  failed, twenty-three were orphaned": when a row states a population, ask whether anyone counted
  it or merely listed what happened to surface.
- **A test that re-derives what the code SHOULD do cannot fail.** My first export assertion called
  the engine the way the route ought to have called it and compared that to itself. It passed
  against the broken route. The repair was to assert on the **shipped workbook bytes** — the
  artefact that actually leaves the tool. An oracle must be independent of the thing it judges, and
  "I recomputed it correctly" is not independence, it is a second copy of the hypothesis.
- **A red for the wrong reason is not a red.** That same repaired test then failed with
  `StopIteration` — my parser looked for "Missing logic" where the workbook writes "Missing Logic".
  Red-before-green was satisfied in letter and not in substance: the test had never once exercised
  its assertion. Only the mutation battery, reverting the fix site and watching the *assertion*
  fail, established that the check had teeth. When a new test goes red, read WHY before banking it.
- **A differential probe needs a control that is expected to MOVE.** The scope probe reported
  "STATIC" for several surfaces, which is precisely what a probe that never applied the filter also
  reports. `analysis.scoped` moving 9 → 8 in the same run is what made every STATIC verdict
  meaningful. A census of things that did not change is worthless without one thing that did.
- **`ruff format` formats Python code blocks inside MARKDOWN — an ADR can fail the gate.** CI went
  red 40 seconds in, on `ruff format --check`, pointing at
  `docs/adr/0419-...md:18` — a fenced ```python block in the ADR prose whose comments I had
  aligned by hand. Ruff reformatted the alignment away. Two lessons: the gate's reach is wider
  than `src/` and `tests/`, and **a partial gate is not a gate** — I ran `ruff check` twice after
  adding those files and never re-ran `ruff format --check`, because I had run the full statics
  block *before* writing the ADRs. Re-run the WHOLE gate after the LAST file changes, not after
  the last code change. The repo's rule already says "full gate before every commit"; I ran four
  fifths of it.
- **`| tail` masked an exit code again** — this repo's most-repeated operational trap, paid for the
  second session running. A piped web-suite run buffered to **0 bytes for 20 minutes** with no way
  to see progress or failure. Redirect to a file; never pipe a long gate.

### 2026-08-17 (d) — a count that counts the symptom, and an oracle that could not fail

- **"It only fails on CI" is a conclusion drawn from a sample of one.** Two tests failed on the
  runner and passed here, so the difference looked environmental (chromium 1194 vs 1234, which this
  container cannot even download). Instrumented and run in a LOOP, one of them failed **8 times in
  20 locally**. Before attributing a failure to an environment, run it enough times to know its
  rate in the environment you already have — a single green run is not evidence of determinism.
- **A flaky test is a race until proven otherwise, and the race is usually in the SETUP.** The
  mechanism was invisible to reasoning and obvious to a sequence probe that logged scroll events
  and tip-visibility transitions with timestamps: `TIP-SHOWN 55ms → scroll 57ms → tip-hidden 67ms`.
  `scroll_into_view_if_needed()` delivers its scroll event asynchronously (57-70ms measured), and
  the product hides tips on scroll BY DESIGN — so the test's own setup was destroying the state it
  then asserted. **Log the sequence with timestamps; do not reason about the ordering.**
- **Wait for quiescence, not for a tuned constant.** The observed delay was 57-70ms here; a
  `sleep(200)` would have passed locally and remained a coin-flip on slower hardware. Waiting until
  no scroll has fired for a quiet window is self-adjusting and says what it means.

- **A count in a ledger row may be counting the SYMPTOM, not the thing.** BROWSER-ORPHAN-01 was
  filed as "four browser test modules never run in CI". Four were the modules that FAILED; the
  modules that never RAN were **23**, holding 94 tests. The nineteen extra were invisible precisely
  because they behaved correctly-looking — they skipped. A failure is loud and a skip is silent, so
  any census built from what went red under-reports by construction. Compute the population from the
  property you actually care about (here: "does this module launch a browser?"), never from the
  subset that happened to complain.
- **An oracle that returns the same verdict in both worlds is not stale — it is blind, and it is the
  more dangerous of the two.** The histogram caption check read **1.17:1 with ADR-0331's halo
  painted and 1.17:1 with it stashed**. It had been failing a correct render, and it could not have
  detected a broken one. The tempting reading — "the halo regressed" — was wrong in a way that
  inspection could never settle: the halo's computed style was present, and the caption was legible
  to the eye at 1×. **Before repairing a failing check, run it against a deliberately broken subject
  and confirm the verdict CHANGES.** If it does not, the bug is in the instrument.
- **A screenshot's resolution is part of the measurement.** The same caption scored 1.17:1 at
  `device_scale_factor=1` and 3.07:1 at 5 — because a 3px halo occupies proportionally more pixels
  when the raster is denser. A probe run at a convenient zoom silently answers a different question
  than the test does. Match the instrument's resolution to the one under test, or the two disagree
  and the disagreement looks like a real defect.
- **Joining two populations by a non-unique key scores items against each other's evidence.** The
  same test swept captions document-wide but screenshotted only `#ssiCharts`, joining the two by
  caption TEXT — and three captions read "Finish date". One genuinely straddling caption was
  therefore reported as three failures. The repair was not a better key: probe and screenshot now
  come from the same element handle, which makes the class unrepresentable rather than fixed.
- **A mutant that never landed is not a SURVIVED verdict** (second instance; 2026-08-17 (c) had
  two). A `sed` whose `|` delimiter collided with the `\|` alternation in its own pattern applied
  nothing, and the resulting "survival" read as evidence the guard had teeth elsewhere. Confirming
  the mutation had landed took one `diff` — and the investigation it forced exposed a genuinely
  weak assertion of mine (`assert X in ci or "SKIPPED" in ci`, whose second clause is nearly
  unfalsifiable). **Print "mutation landed: True" as part of every mutant, not as an afterthought.**
- **Restoring a population is part of a repair.** My first fix for the caption test scoped its sweep
  to `#ssiCharts` and quietly dropped the measured captions from 5 to 2 — a check measuring less
  than before, wearing a passing badge. Caught only by comparing counts before and after. Any repair
  to a sweep should state its population and floor it.
- **`| tail` masks exit codes** — a standing trap in this repo, paid again: `ruff format --check .`
  was piped to `/dev/null` inside an `&&` chain, so a formatting failure surfaced as a bare
  "exited with code 1" with no diagnostic and cost a full re-run of a 6-minute browser suite.
- **Housekeeping:** Part VIII declares "newest first" and the 2026-08-17 (c) entry had been appended
  at the FILE's end instead; moved back into order below.

### 2026-08-17 (c) — a claim verified against one module; two mutants that missed their subject

- **A claim verified against ONE module is a claim about that module.** ADR-0407 justified a
  design decision by asserting what the rest of the tree does: *"`web/risks.py` builds the risk
  matrix, the ranking and the recovery plan from RISK + CONCERN only, so an OPPORTUNITY/INFO
  disclosure informs without ever becoming a threat row or a recovery action."* Every word about
  `web/risks.py` was correct. The word that cost us was **"ever"** — `ai/briefing.py` has no
  category gate, and the disclosure landed in a column literally headed **"Potential recovery"**
  quoting 20 wd on a finding whose recovery is zero by its own wording. QC-2 already says to
  scope a finding before acting on it; this is the same error made while *writing*. **When an ADR
  justifies a decision by asserting what the rest of the tree does, that assertion is a claim
  under QC-1 and needs its own check.** A two-line grep for the other consumers of
  `Category.OPPORTUNITY` would have found it in seconds. The generalisable rule: *the scope of
  your evidence is the scope of your claim — say "in `web/risks.py`", not "ever".*
- **A mutant that misses its subject proves nothing — and it happened TWICE in one session.**
  REC-01's M7 aimed at `recommendations.py` while the test it targeted asserts on `cpm.py`;
  MC-01's M5 deleted a zero-floor whose effect was invisible at the observable the test read
  (measured: `compute_cpm` does NOT clamp a negative duration — it returns
  `early_finish = -14400` — but the *successor* floors at the project start, so the focus P50 was
  identical with and without the floor). Both first reported SURVIVED. Neither was a code defect;
  both were **battery defects**, and in MC-01's case the test was genuinely one that could not
  fail — this repo's signature defect, written by the very fix that names it. **Before believing
  a SURVIVED verdict, check that the mutation and the assertion are aimed at the same thing.**
  The cheap discipline: name the file and the observable the test reads, and confirm the mutation
  touches that file and moves that observable.
- **A control the CSP kills is invisible to every test that reads markup.** The Acumen-parity
  checkbox rendered perfectly — right name, right state, right label — and did nothing, because
  `script-src 'self'` refuses inline handlers and its form had no submit button. Any markup
  assertion would have passed. Only executing the page in a browser could tell the difference.
  **For a CONTROL, the evidence is that clicking it changes something, never that it appears.**
  Corollary that shaped the fix: the repo had already built the cure (`chrome.js`, ADR-0268,
  whose header says it exists *because* the CSP forbids inline handlers) and the author reached
  for the inline handler anyway, because the delegation matched `select[...]` and the control was
  a checkbox. **A mechanism that covers less than its docstring claims invites the very bug it
  was built to prevent.**
- **A hand-maintained list of call sites is a stale list waiting to happen.** `_CPM_HOLDERS`
  named ten modules; 24 bind `compute_cpm`, the PRIMARY solve's module was missing (ADR-0297
  moved it after the list was written), and a listed module that no longer binds the name was
  skipped *in silence* by a `getattr(..., None) is not None` guard — a fail-open dressed as
  coverage. **Where a guard needs to know "everywhere X is referenced", compute it, don't list
  it.** And note which half of that is the nastier bug: the silent skip, because it made an
  incomplete list look like a maintained one.
- **A self-baseline absorbs the thing you are trying to measure.** The same test compared the
  extra views against `after_page` — so extra solves *inside* the page build landed on both sides
  and cancelled. Even a perfect holder sweep could not catch them. The finder reported the right
  fact (the list is stale) with the wrong diagnosis, and the lead re-verification found it: with
  the sweep repaired the count moved 2→4 and the test *still* passed. **When a test's expected
  value is derived from the same run it is judging, it can only detect divergence between the two
  halves — never a fault common to both.**
- **Fixing a class beats fixing a site, but only after you measure whether it IS a class.** MF-02
  was a class (many consumers of a false guard); JS-01 was not — a view-layer census proved the
  parity checkbox was the *only* inline handler in the tree. Both answers are useful; assuming
  either without the census is how a fix becomes either too narrow or too invasive.

### 2026-08-16 (b) — a fixture whose NAME contradicts its assertion is a defect wearing a badge

- `_EVM_SEEDS` carries the comment "the EXACT set of status flips it must cause — measured,
  then pinned." That is an honest description of how it was built and *precisely* why it
  could not catch MF-01: **a fixture measured from today's output pins today's output,
  correct or not.** When the verdict is wrong the fixture stops being a test and becomes the
  defect's bodyguard. Third instance in this repo (M15, the `BLOCKED` pin, now this).
- The tell was in plain sight: a fixture named **`blown`** — a cost blowout at CPI 0.54,
  spending ~2x per unit of work — asserting that its affordability index **PASSES**. *Read
  fixture names as claims and check them against their assertions;* the contradiction is
  cheaper to spot than the arithmetic.
- **Shared helpers propagate an assumption silently.** `_index()` served three indices and
  hardcoded one direction, so "higher is better" — true for two of them — was applied to the
  third by inheritance. The fix makes the caller state the direction. When a helper encodes
  a *semantic* property, that property belongs at the call site, not in the default.
- The mutation battery earned its keep by including a mutant aimed at the CONTROL (flip SPI
  to LE). A control test that is never attacked is an assumption; attacking it turned
  "SPI/CPI are unaffected" from a hope into a measurement.

### 2026-08-16 (a) — a defence-in-depth twin blinds an outcome assertion, and a suggested fix is only a hypothesis

- HOOK-02's mutation battery is the cleanest demonstration yet of a rule this repo keeps
  re-learning: **when two layers detect the same input, no end-to-end assertion can prove
  either one works.** Reverting the bash sniffer to the exact original bug left the new
  outcome test GREEN, because the python sniffer caught the same files — 3 of 4 mutants
  survived. The fix is to run one layer ALONE (a PATH carrying only git+grep) so the
  layer's death is observable. Generalise: *before trusting a battery, ask which layer
  each mutant actually exercises; a twin makes the count a lie.*
- **A proposed fix is a hypothesis and gets the same red/green treatment as a claim.** The
  finder's `--` separator was plausible, well-argued, and wrong: measured on a sandbox COPY
  of the hook before any implementation, it closed the `!`/`^` shapes and left the
  `:<stage>:<path>` shapes open. Building both candidates and running the SAME battery
  against each is what made the choice evidence rather than taste.
- **My own probe was wrong twice before it was right**, and both errors flattered a
  conclusion: `| head` swallowed the exit code, and a `git add` that silently failed made a
  never-staged file look "blocked" (and, in the other direction, made a working fix look
  broken). The test that shipped therefore ASSERTS the file reached the index — a harness
  that cannot tell "blocked" from "never staged" is a green test that cannot fail.
- **A security fix can weaken security.** Reaching for `head`/`cut`/`tr` narrowed the
  guard's no-python3 floor; the repo's existing floor test caught it within one run. When
  hardening a component, re-read what its DEGRADED mode is contracted to do.

### 2026-08-15 (e) — a mutant that cannot fail is not a mutant, and shared helpers make parity fixes small

- JCL-BR-01's battery originally planned a "fragnet consumes a cost-multiplier draw"
  mutant (drop the `ti + td > 0` guard). Working the reachability through BEFORE running
  it showed the mutant cannot redden the pin: fragnet uids are always assigned ABOVE
  every existing uid, so a fragnet's wasted draw comes LAST in the iteration and shifts
  no real task's multiplier — the cost CDF stays equal and the "kill" would have been
  vacuous. **Check a mutation's reachability the way you check a test's redness: a
  battery counts kills, and an unkillable mutant inflates the count without proving
  anything.** The replacement ("fragnet entries fabricate cost" — `budgeted_cost or
  100.0`) is the actual Law-2 threat and dies by name.
- The whole engine fix was ~60 lines because `jcl.py`'s import list IS its architecture:
  it already imported the SSI sampler, occurrence schedule, and LHS plan builders, so
  carrying branches meant importing five more helpers and mirroring two short blocks —
  never copying machinery. **When one engine must replicate another's discipline, the
  extension point is the shared-helper import list; a fix that wants to copy code is a
  fix aimed at the wrong layer.** (The equivalence pins then compare full CDFs, so any
  future drift between the mirrored blocks is loud.)
- The export was the sharpest face of the defect: ONE workbook carried SSI sheets with
  branches and JCL sheets without — two stories in a single testimony document. **When
  two engines feed one artifact, pin their input equality at the artifact's call sites**
  (the kwargs-spy test), not only at the API layer.

### 2026-08-15 (d) — enumerate the freeze surfaces before touching a frozen file, and let the category system do the semantics

- ENG-DEAD-01's blast radius was enumerated BEFORE implementing: the `/driving-path`
  byte-frozen payloads turned out to have their own reducers (safe), the Excel export's
  `_DRIVING_COLUMNS` excludes `date_driven` (so symmetry says leave it), and the ONE pin
  that would move — the r11 `PAGE_SCRIPTS` md5 freeze on path.js — was known in advance,
  so its red was a predicted re-baseline, not a surprise. **Before editing anything, ask
  what byte-freezes, censuses, or snapshot pins cover it; a freeze found by the failing
  gate costs a re-run, a freeze found in recon costs nothing.** The freeze constant
  carries its own re-baseline idiom (ADR + what moved + old→new digest) — follow it,
  never bare-swap a hash.
- The disclosure's Category choice was semantics, not taste: `web/risks.py` builds the
  matrix, ranking, and recovery plan from RISK+CONCERN only, so OPPORTUNITY/INFO is the
  one slot where a finding informs without becoming a threat row or a recovery action —
  exactly ADR-0391's "evidence, not an unsupported date", enforced by rendering
  structure. **Read how consumers bucket an enum before picking a value; the right
  constant can carry a design constraint for free — then pin it with a mutation** (M6:
  category degraded to CONCERN → caught by name).
- The blast-radius enumeration still missed one guard: a `METRIC_DICTIONARY` entry has
  THREE censuses (help↔doc sync, emitted-ids coverage, and `test_aft_formula_audit.py`'s
  every-documented-id-classified-against-the-Bible), and only two were enumerated — the
  full gate caught the third (`AUDIT and help.py are out of sync`). **When adding a
  metric id, the Bible-census Row is part of the unit** (NOT_IN_BIBLE + rationale for
  tool-specific diagnostics, the ADR-0034/0043 idiom). A targeted battery is a designed
  instrument with a designed blind spot; the whole-tree gate exists precisely for the
  guard you did not know to name.

### 2026-08-15 (c) — a whole-tree census scans itself, and an exactly-enumerated population makes a 22-file fix a one-liner

- Flipping TEST-01's xfail nearly failed on the audit module ITSELF: its explanatory
  comment contained `chromium-1194/...`, which matches the very scan it documents (the
  census rglobs every test file, its own included). r11 had already solved this — document
  the build number WITHOUT the trailing slash the regex needs. **When a census scans a
  population that includes its own module, write its prose so it cannot self-match, and
  canary-prove the flip.**
- The fix for 22 modules was one exact string replacement + one canary, because the
  population was enumerated with the audit's OWN regex first (23 matches minus the
  self-match), not a loose grep (24 matches). **The scan's regex defines the population;
  enumerate with it before designing the fix.**
- The applier asserted its old-strings verbatim and refused to run blind — cheap
  insurance that the tree hadn't drifted between recon (done read-only during a running
  gate) and application (after it).

### 2026-08-15 (b) — a guard can pin a contradiction, and a hard count in prose is a claim with a half-life

- `docs/FINAL-REPORT.md` said M15 was delivered in its header and "◻ BLOCKED" in its
  Definition of Done — and `test_docs.py` ASSERTED the word "BLOCKED", holding the
  contradiction in place through months of edits. Second paid instance of the ADR-0385
  stale-guard class. **When a document contradicts itself, check whether a test is holding
  one side down before editing either.**
- The report's "645 passed / 32 ADRs" sat as apparent present-tense fact while reality was
  4,000+/400+. **A hard count in a narrative document rots silently — date it and point at
  the live ledger (HANDOFF's Gate-at-close) instead of restating it.**
- The JCL `eac` gloss drifted exactly where prose was written from memory: it scaled the
  whole remaining budget by the duration ratio, true only at the τ=1 default. **Transcribe
  formulas from the engine and cite the lines in the ADR; a gloss whose oracle is the
  author's recollection has no oracle.**
- §6.G's locality overclaim was harmless prose until ADR-0402 made it conditionally false
  — a doc claim's truth can be REVOKED by later, correct code. The fix is the same
  conditionality the UI derives, now pinned by a test so the absolute cannot quietly return.

### 2026-08-15 (a) — read the ask's goal, not its noun; and a persistence feature makes every test a filesystem writer

- The operator asked to stop entering "the NASA API KEY everytime" — the NOUN was the key,
  but the GOAL was "it works when I click on the desktop icon." Persisting only the key
  would have left four re-arming steps per launch and missed the goal entirely. **Scope a
  fix to the stated goal; the named artifact is just where the pain surfaced.**
- ADR-0402 wrote its consent posture with an explicit "revisit only on operator ask"
  clause, naming what would flip and why. When the ask came, the flip was one clean unit
  with no re-litigation. **Deliberately-NOT-done clauses earn their keep when they name
  their own revisit condition.**
- Adding persistence turned every existing `POST /settings` test into a writer against the
  operator's real `~/.local/state` — caught before landing because the schedule cache had
  already paid for this lesson (its autouse isolation fixture was the template). **When a
  feature adds a default filesystem path, the conftest isolation ships in the same unit.**
- The credential-at-rest rule generalized cleanly: protect where the OS can (DPAPI), name
  the storage honestly where it can't (`_plain`, 0600), and on protector failure OMIT
  rather than downgrade — the mutation battery (`protector_failure_stores_plain`) pins
  that a broken protector can never silently write plaintext.

### 2026-08-14 (e) — a field 401 is a positive transport result, and a spec records what its author could see

- v1.0.202 reached the operator's NASA machine and the armed gateway probe came back
  **HTTP 401** with an empty model dropdown. The temptation is to read "could not reach"
  as network trouble; the honest reading is the opposite — DNS resolved, TLS completed,
  the gateway ANSWERED and demanded a credential. **Classify a failure by what it proves
  works, not by where it appears in the UI.** The diagnostic now teaches this (401/403 →
  "paste your key", other errors → "check your network").
- The integration was built faithfully to `APPROVED-GATEWAY-INTEGRATION.md` §1 — which
  recorded the working patch's endpoint and model env vars and nothing about auth. The
  patch worked, so an auth element existed (or auth was later enabled); either way the
  recorded spec was missing a dimension only deployment could reveal. **When documenting
  a working system, record every dimension's EXISTENCE — endpoint, model, credential,
  scheme — even when the value itself must not be written down.**
- A masked, never-echoed form field forces **blank-means-keep** POST semantics: the field
  posts blank on every ordinary re-save, so blank-clears would silently de-authenticate
  the gateway each time any unrelated setting is saved. The pairing (echo-never ↔
  blank-keeps) is a unit; adopting one without the other is a live bug.
- Proportionate battery: 8 mutants aimed at exactly the new credential properties, all
  caught by name — the 0402 rig (sandbox, canaries, md5 census) re-used as-is. A second
  unit in the same area should inherit the first unit's instrument, not rebuild it.

### 2026-08-14 (d) — a defense-in-depth twin can hide a layer's mutation, and `pkill -f` self-matches on strings the bracket trick doesn't cover

- Built 001c (ADR-0402): the approved-gateway backend, at operator direction. The mutation
  battery's round 1 exposed a real gap in my own new test: `models_probe_unrestricted`
  (the `/api/ai/models` route's allowlist check deleted) SURVIVED, because the backend
  constructor one layer down also refuses off-list endpoints and its error message
  contains the very word ("approved") the outcome assertion looked for. **The lesson: an
  outcome assertion over a defense-in-depth stack pins the STACK, not the layer — a
  mutation of any single layer is invisible while its twin holds. Pin the layer:** a
  constructor bomb (monkeypatched class whose `__init__` raises) proved the route refuses
  BEFORE construction; re-run caught the mutant 1-failed/15-passed.
- `pkill -f "[s]erve_for_pw"` still killed my own shell (exit 144): the bracket trick only
  keeps the PATTERN from matching itself, but the plain string `serve_for_pw.py` sat in
  the same command line two lines up (the `nohup python …/serve_for_pw.py` launch). **Kill
  by recorded PID (`echo $! > pidfile`), never by pattern, when the launcher and the
  killer share a command line.** Second paid instance of the render-verify skill's
  self-match warning, in a new costume.
- A dev server held across browser-drive runs reproduced OR-06 in miniature: run 1's Save
  armed the session, run 2's assertions met the leftover state. Restart the server per
  run; "always start clean" applies to instruments too.
- Playwright went into an ISOLATED venv so the main env's suite baseline stayed comparable
  to the prior close (playwright in the main env executes ~19 CI-invisible tests — the
  full-gate skill's §4 table). The measured cost was zero: the container's vendored
  chromium serves both.
- The ADR-0148 trap fired in real time and the ritual caught it: five lint fixes landed
  AFTER the first wheel build; the wheel + nine installers were rebuilt from the final
  tree and the lockstep suite re-run before commit.

### 2026-08-14 (c) — the fixture that could not fail, the diagnosis that reversed again, and spent = 0.0

Four lessons from the first JCL battery (ADR-0401), each paid for in-session:

- **A consistency oracle needs a fixture PROVEN to populate its discriminating cells.** The
  first quadrant-closure fixture failed INTACT: with the FICSM multipliers off, cost is a
  monotone function of the same driver that drives lateness, so the late-but-cheap quadrant
  was STRUCTURALLY empty — no target choice could populate it. Red-before-green caught it;
  the fix was a semantic decoupler (multipliers on) plus measured targets, and the liveness
  asserts stay in the test as the self-check. Corollary from the critic: those liveness
  preconditions rode SRAConfig's DEFAULT seed — pin the seed explicitly wherever a margin or
  population depends on the sampled shape.
- **A survivor of a narrow suite is a hypothesis, not a finding.** L13 (`sampling`
  passthrough) survived the JCL modules and died in `test_lhs.py` (nine tests by name).
  Widen the suite before declaring a blind spot — the wider run converts "unguarded" into
  "guarded elsewhere", a different fact demanding a different action.
- **A diagnosis that reversed once is not done reversing (again).** The sandbox push 403 was
  first read as a proxy body-size cap; slicing "confirmed" it by succeeding — but the real
  discriminator was a ZERO-object deletion push that also 403'd: the proxy blocks ref
  DELETIONS, and every failed push had carried `--prune`. The `| tail` exit-mask trap also
  fired mid-session ("push exit: 0" on a failed push) — the ref comparator's RED was the
  honest instrument, exactly as designed.
- **`spent = 0.0` makes any float re-association exact.** The association mutant
  (`spent + (ti + td)` → `spent + ti + td`) survived the first interior-τ closure because the
  fixture's spend was zero and `0.0 + x` carries no ulp; the killing fixture records a 0.01
  spend at values where the last ulp genuinely moves (attacker-measured recipe, lead-verified).
  A bit-identity contract is only testable where the bits can differ.

### 2026-08-14 (b) — a transcription oracle must be proven to read the SOURCE side, and a branch can move a member six years while every aggregate pin stays byte-identical

- PO-03: the Fuse-transcription guard's battery needed THREE legs — JSON value, JSON UID
  list, and a WORKBOOK-cell byte patch. The third is the one that matters: a guard that
  compares the JSON to itself (or hardcodes what the workbook "says") stays green under it.
  Mutate the artifact the oracle claims to read, not just the expectation.
- The exec_cal floor was deletable with the engine suite AND the parity gate green — while
  pulling UID 5230's early start back six years on the primary golden. `project_finish` and
  every SSI/parity pin were byte-identical. Lesson: pin the MEMBER the branch moves, not the
  aggregate; and run an ISOLATION control (delete the sibling branch → the new test must stay
  green) so the guard provably aims at the unguarded half.
- A closure population row must be TRANSPORTABLE: the raw-Unicode homograph Host header made
  httpx raise at request-build time — the test ERRORED instead of failing, which is not a
  verdict. Sweep the punycode form (`xn--lcalhost-nbh`) a browser actually sends.
- The kickoff/queue said SEC-01's "behavioural half" was missing; QC-2 re-measurement showed
  test_sec_hardening already behaviourally covers both consumers — the REAL holes were
  narrower and different (M1 sample-blindness; the M3 scheme conjunct caught by nothing).
  Re-derive the gap before building the fix, or you build the wrong module.
- The adversarial round then repeated HOOK-01's lesson on OUR OWN batteries: mutation-green
  first revisions hid eleven more findings. New named traps: a TEST CLIENT THAT FOLLOWS
  REDIRECTS CAN LAUNDER A SECURITY ASSERTION (the foreign-Host POST executed and mutated
  state; the followed redirect GET supplied the 400 the assert read — use
  follow_redirects=False when the POST's own status is the claim); A SWEEP'S HTTP METHOD IS
  PART OF ITS POPULATION (a GET-only host sweep cannot see a method-conditional bypass);
  `int(float(...))` ON AN ORACLE CELL TRUNCATES DRIFT INTO AGREEMENT (require integrality);
  A SKIPIF THAT TESTS THE WORKING TREE WHILE THE BACKSTOP READS THE GIT INDEX IS A SILENT
  DISARM (fail loudly when a tracked artifact is missing); and A DECLARED-BUT-UNASSERTED
  EXPECTED CONSTANT IS A DEAD ORACLE THAT READS LIKE A GUARD (make it load-bearing or
  delete it).

### 2026-08-14 (a) — the census flagged the guard itself: the fix would have been wedged by its own commit hook

- Widening the CUI pre-commit hook for HOOK-01 (ADR-0399), the first draft's header comment
  wrote the save-format signature verbatim — and the hook is an extension-less file, one of its
  own sniff classes. The new whole-tree census test flagged `.githooks/pre-commit` as schedule
  content: **the commit landing the fix would have been blocked by the guard it was fixing.**
  Lesson: a guard that sniffs a class of files it itself belongs to will eventually read
  itself — never write a detector's signature literal inside the detector's own file. This is
  the audit's redaction lesson ("a document that flags a disclosure must not repeat the
  disclosed literal") landing on a guard, and the census now enforces it permanently.
- A tree census needs BOTH of its controls, not either: the planted canary proves the sweep can
  go red, and the staged-count == copied-population proof stops `git add` silently dropping
  gitignored-but-tracked names (the 2026-08-13 audit's `git add -A` trap). The canary alone
  passes over a half-staged population; the count alone passes with a detector that flags
  nothing.
- A predicted mutation outcome is not a measured one. The ADR's M7 sentence was drafted saying
  the unanchored mutant would flip three rows; the measurement says ONE — `guide.md`, blocked as
  "P6 XER content" because unanchored matching hits the `ERMHDR` quoted in prose, which is
  precisely the false positive the anchoring exists to prevent. The drafted sentence was
  replaced with the measured one before commit. Writing the expected result into a document
  before running the check is exactly the shape QC-1 forbids, even when the check later passes.
- Anchoring to serialization-start is what makes covering prose-capable extensions POSSIBLE at
  all: unanchored, the `.md` sniff blocks `docs/STATE/AUDIT-2026-06-25.md` — a tracked doc —
  today (measured in the pre-change census, not argued). The guard's false-positive boundary is
  as load-bearing as its detection boundary: one wrong block on legitimate work and the guard
  gets switched off, after which it guards nothing.
- **A mutation-green guard is not an adversarially-verified guard.** After 8/8 mutations were
  caught by name, the adversarial fan-out still found FIVE in-scope defect classes — including
  a pre-existing SILENT fail-open (git C-quotes `schädule.mpp`, the escaped token matches no
  pattern and `git show` fails, so every detector was bypassed for any non-ASCII/quote/control
  filename since the guard was born). Mutations prove the tests can see the detectors;
  adversaries probe the space BETWEEN the detectors — name normalization, quoting layers,
  spec-valid variants (single-quoted xmlns), and template dialects (`{{<` is prose that starts
  with `{`). Both proofs are needed, and they are not the same proof.
- The fail-open lived in the INPUT PLUMBING, not the detectors: `git diff --name-only` output
  is an ENCODING of paths, not paths. Every detector downstream was correct and every test fed
  it clean ASCII names, so nothing ever exercised the decode boundary. When a guard consumes
  tool output, the tool's quoting/escaping layer is part of the attack surface — read raw
  (`-z` + `read -d ''`) or prove the decode.

### 2026-08-13 (h) — a diagnosis reversed twice in one hour; then the predicted collision arrived on schedule

- Closing 001b (ADR-0396 after renumbering — see below) required the wheel/installer rebuild, and the
  rebuild pinned MPXJ to `a100184d` — different from the committed `42d92dc`. First conclusion: "my pin
  is fresher and verified (`merge-base --is-ancestor` passed) — the committed one is stale." Second,
  after `a100184d --stat` showed 28 files "added" under `tools/mpxj`: "worse — the shipped v1.0.198–200
  installers reference `poi-5.5.1.jar`, which didn't exist at their pin; installs in the wild are
  broken." BOTH were wrong.
- The tell: `git show 42d92dc:tools/mpxj/lib/poi-5.5.1.jar` returned the jar's bytes. The "addition"
  was a graft artifact — `a100184d` sits in `.git/shallow`, and a shallow clone attributes the ENTIRE
  tree to its boundary commit, in `log -- <path>` AND in `--stat`. Tree hashes settled it: `42d92dc`,
  `a100184d`, `HEAD` all carry the identical `tools/mpxj` tree; the GitHub commits API (full history,
  `path=` filter) names `42d92dc` the true last touch. Nothing in the wild was ever broken.
- **Lesson 1:** in a shallow clone, `git log -1 -- <path>`, `--stat`, and `merge-base` can all agree on
  a falsehood — each was individually "verification", and each inherited the same graft blindness. The
  independent oracle (remote API / tree hashes) is what broke the loop.
- **Lesson 2:** a diagnosis that reverses under a new measurement is not finished reversing. Write down
  only what the LAST measurement proved, and say which measurement that was.
- **Lesson 3 (the fix, ADR-0397 after renumbering):** `mpxj_ref()` now refuses graft-boundary
  resolutions outright and takes `SF_MPXJ_REF` only with verified tree-identity — tree-identity beats
  ancestry because it is checkable in the very clones that lie about ancestry. Red first: the new
  installer test failed 3/3 families against the drifted build before the corrected rebuild made it
  green.
- Also (001b proper): when one claim spans six surfaces plus two exports and four translations, route
  every surface through ONE derivation (`_observed_banner`) — surfaces that derive independently WILL
  disagree, and the pre-fix router/page disagreement (router said local, page said cloud, both wrong in
  different states) proved nobody notices when they do.
- **The kickoff's warned-about ADR collision then actually happened:** this session's banner ADR and
  the parallel read-only audit (PR #585) both took **0395**; the audit merged first and owns it. Mine
  renumbered 0395→0396 (banner) and 0396→0397 (MPXJ pin) in the merge commit — renumbering IS conflict
  resolution, and `git fetch origin` before committing is what caught it. Same-day letters collided
  too ((e)/(g) on both sides): parallel sessions need MERGE-TIME reconciliation, not naming discipline.
- **DISC-01 landed while this session was in flight and explains the day's mystery:** the repo went
  PRIVATE mid-session (the operator's remediation for the audit's disclosure finding), which 404'd the
  installers' anonymous MPXJ fetch and turned PR #586's smoke legs red — an external state change that
  arrived BETWEEN my push and its CI run. The failure read like an artifact defect and was measured to
  be neither: same bytes, same pin, different repo visibility. Lesson: **a CI failure on an unchanged
  code path is a question about the environment first** — and a fix ("flip it public") that undoes a
  deliberate security remediation is not a fix; the installers had to learn an authenticated path
  instead (ADR-0398).

### 2026-08-13 (g) — an audit report is itself a disclosure surface; redact it before you commit it

- The read-only audit's own report and forward-plan named the gateway hostname and the ITAR-tagged model
  id verbatim (4 and 3 hits). Committing them would **proliferate exactly what the report's headline
  finding (DISC-01) says to stop** — a public repo already over-discloses these. Scrubbed to placeholders
  before landing; the strings already exist elsewhere, so nothing was lost. Lesson: **a document that
  flags a disclosure must not repeat the disclosed literal — your own deliverable is in scope for the
  finding.**
- A `.git`-less `git archive` sandbox mis-reports git-dependent guards (intake-manifest, precommit-blocklist)
  as failures because they shell out to `git ls-files`/`rev-parse`. Worse, `git init` + `git add -A` is NOT
  enough — `.gitignore` skips the force-committed intake, so the tracked set was 1191 not 1624 and the
  manifest guards still failed; only `git add -f 00_REFERENCE_INTAKE` reached the real set and turned all 56
  green. Lesson: **before trusting a sandbox census, prove the sandbox's tracked set equals the real repo's.**
- `xfail(strict=True)` is the clean way to LAND a validated-but-unfixed finding: the test asserts the fixed
  behaviour, xfails today (documents the defect), and a future fix makes it xpass → strict turns that into a
  failure that prompts removing the marker. Every refutation test shipped with a negative control so no green
  is vacuous.

### 2026-08-13 (f) — the guard broke itself the first time somebody followed the rule it guards

The attribution guard added a few hours earlier
(`test_docs_cite_the_rules_under_the_adr_that_decided_them`) derives the correct ADR number from
disk rather than hard-coding it — the right instinct, and the mutation battery proved it survives a
renumber. It found the defining ADR by scanning every ADR **body** for the string `QC-1`. It was
green on its own branch and green in CI.

Then `main` merged ADR-0394, which was itself written under the new rules and therefore carries a
`## Verification (QC-1)` section. Two ADRs now matched. The oracle's own ambiguity assertion fired
and the guard went **red on merge** — CI never saw it, because CI ran the PR against a base where
ADR-0394 did not yet exist.

- **An oracle that searches for a rule's NAME goes ambiguous the moment the rule is obeyed.** Every
  ADR from ADR-0394 onward mentions QC-1, because QC-1 requires them to show their verification.
  The population the oracle discriminates over was guaranteed to grow to include every future
  member. That is not a mutation someone has to introduce; it is Tuesday.
- **"Deciding" is a claim about SUBJECT, and an ADR's subject is its title.** The fix scopes the
  match to line 1. A body mention is a citation; a title is a claim of authorship. One ADR's title
  names QC-1 and always will.
- **The mutation battery said 8/8 and was still blind here.** Mutation 7 deliberately made the
  oracle ambiguous and scored the resulting failure as CAUGHT — treating "the guard refuses to
  judge" as a success. It never asked whether that state would arise *without* a mutation. A
  battery answers "does the check fire when I break things"; it does not answer "will the check
  still be true next week". **Ask what the corpus the oracle reads will look like after the next
  three commits.** The replacement battery adds a must-STAY-GREEN case (a new ADR mentioning QC-1
  in its body only) so the regression cannot come back as a passing mutation.
- **A mutation that does not land reports as a pass, and looks exactly like an escape.** My
  second battery targeted `HANDOFF.md` line 49 by number. The merge replaced that handoff
  wholesale, line 49 became unrelated prose, the `sed` matched nothing — and the run printed
  GREEN. I nearly recorded a hole in the guard that did not exist. Every mutation must now prove
  it *changed the file* (md5/diff) before its verdict is read; a no-op is reported INVALID, not
  passed. This is the sibling of the standing trap "a sweep's glob is part of its claim": **a
  mutation's target is part of its claim**, and hard-coded line numbers do not survive a merge.
  The corrected battery is 12/12 with every mutation proved to land.
- **CI green on a PR is a statement about the PR's base, not about main.** Both the conflict and
  this failure were invisible until the merge was actually performed. When a PR sits while main
  moves, merge main in and re-run before believing the badge.

### 2026-08-13 (e) — the PR that fixed a wrong ADR number left a wrong ADR number

PR #582 existed for one reason: `NEXT-SESSION-PROMPT.md` contradicted itself about which ADR the
gateway decision would be, and I fixed it (0393 → 0394). It merged. Then, re-reading the merged
file under QC-2, line 60 of that same document said the standing working rules are **ADR-0392**.
They are ADR-0393; 0392 is the unrelated Ask-panel defect fix. The wrong number was four
paragraphs from the one I had just corrected, in a sentence that named `test_standing_rules.py`
— the rules' own guard — as its evidence.

- **Fixing the instance is not fixing the class.** I read the paragraph the contradiction was
  in, corrected it, and shipped. I never asked "does this document get this number wrong
  ANYWHERE else" — which is one `grep` and would have caught it before the PR, not after the
  merge. When a defect is "a doc states a fact wrongly", the unit of repair is *every statement
  of that fact*, not the sentence someone happened to point at. Scope the finding before acting
  on it (QC-2) cuts both ways: it also means don't scope it smaller than it is.
- **QC-2 earned its keep on the author's own just-merged work.** Nothing external flagged this.
  It surfaced because "re-read what you shipped" was applied to a PR that had already gone green
  and merged, i.e. at exactly the moment it feels least necessary. Inherited claims are testimony
  — and a claim I wrote an hour ago is inherited too.
- **A guard whose oracle is a constant proves nothing about the constant.** The regression guard
  (`test_docs_cite_the_rules_under_the_adr_that_decided_them`) derives the correct number by
  finding the one ADR file on disk that defines QC-1, rather than hard-coding `0393`. The
  mutation that proves this matters is the fifth one: rename the ADR `0393-* → 0395-*` and leave
  the docs saying 0393. A hard-coded oracle sails straight through; this one goes red naming
  0395. The other seven mutations (wrong number in each of three docs, oracle deleted, oracle
  made ambiguous, sweep population emptied) all fire too — 8/8, sandbox byte-identical after
  every restore.
- **The honest guard is the mechanical subset, not the fuzzy superset.** I wanted to check every
  prose attribution and found the general version false-positives immediately (line 5 legitimately
  names 0392 while *explaining* the collision). So the guard checks only lines that name the
  rules' guard file and cite an ADR — a population it can judge without guessing — and its
  docstring states that scope outright. A guard that fires on ordinary editing gets deleted, and
  then it guards nothing.
- **My own "reserved ADR-0394" note was stale within the hour.** This entry originally said
  0394 was being held for the gateway decision, so I would not burn it on a doc fix. While CI
  ran, #583 merged and took 0394 for DoD 001a. The note was true when written and false when
  read — which is the whole argument for *never* writing a predicted ADR number down. No ADR
  for this change either way; a doc correction plus its guard is not a decision.

### 2026-08-13 (c) — a standing rule is DATA, and unpinned data is not a guarantee (ADR-0393)

The operator made two working rules mandatory. Writing them taught two things, and the second one
cost a redo.

- **A standing rule is data, and unpinned data is not a guarantee.** Yesterday's audit found that
  POLARIS's entire Law-1 locality guarantee rested on an unpinned frozenset — widening it left
  226-854 tests green. A rule written only in prose has exactly that shape: load-bearing content
  with nothing asserting it is still there, still mandatory, still un-softened. The pre-existing
  "READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING" had been a trailing sentence inside another
  section for months and was routinely skipped — not because anyone decided to skip it, but because
  nothing made skipping it detectable. So the rules governing every future session are now pinned by
  `tests/test_standing_rules.py` the way a security constant should have been.
- **Scope a substring assertion to the region that BINDS.** The first version of that guard checked
  the whole file for its required clauses. A mutation battery then walked straight past two real
  weakenings: deleting `sandbox` and `refute` from QC-1's binding sentence passed because both words
  survived in QC-1's own bullet list, and softening "MUST be observed to FAIL" passed because the
  bare token `fail` still matched "never failed" further down. **A global grep proves a word exists
  somewhere; it proves nothing about the sentence that carries the obligation.** Fix: slice each
  rule from its heading to the next and assert within that slice, and pin phrases (`observed to
  fail`) rather than tokens (`fail`). Same family as "a census can be exact and still not be
  membership" and "a sweep's glob is part of its claim" — three instances now, all the same root:
  **the shape of the search is part of what the search claims.**
- **"Check the next free number" means check the REMOTE.** I read `docs/adr/` on my local tree and
  took 0392. PR #580 had merged 0392 an hour earlier. The standing rule says *fetch before taking an
  ADR number, and again before committing* — I satisfied the words and missed the point, because a
  local listing answers "what did my tree have when I cloned it", not "what exists". It surfaced by
  accident: a 502 on PR creation sent me to list the repo's PRs. **A uniqueness check against a
  stale copy is not a uniqueness check** — the same shape as validating a rule with a fixture that
  rule generated. Fetch, then read.
- **Merging a parallel session is not a conflict to win.** Four state docs conflicted. Every one had
  a correct resolution that kept BOTH sessions' work — their handoff status went to the archive
  rather than the bin, both session-log entries survived in chronological order, both lessons
  entries survived newest-first, and the kickoff carries their Ask-panel guidance next to my rules.
  Taking "ours" wholesale would have silently deleted a merged session's durable record.
- **What worked: writing the guard before the thing it guards.** The red phase was not ceremony —
  it distinguished "3 assertions failed because the rules are absent" from "the file is missing and
  everything fails vacuously", which is why two of the five tests were controls that PASSED in the
  red phase. And the battery earned its keep immediately by finding a defect in the guard itself,
  which is the whole argument for QC-1 in one paragraph.

### 2026-08-13 (2) — the model was describing its evidence, and the evidence was two files

An operator loaded 31 versions, asked the AI to read the S-curve across all of them, and was told
the tool could see "only two file versions, not 31". Four lessons, and the first one is the trap.

- **A model that says "I only see two files" may be reporting a fact about its evidence.** The
  instinct — mine and the operator's — was that the loader had dropped 29 files. Measurement said
  otherwise: 31 loaded, parsed and solved, and a fact base of 23 statements in which **exactly one**
  named more than one version (a verification-procedure sentence that happens to list file names).
  Everything else came from `build_briefing` (newest version) and the manipulation/counterfactual
  facts (latest pair). The model's answer was an accurate description of its prompt. Read the prompt
  before disbelieving the answer.
- **A capability the TOOL has is not a capability the AI has.** `engine/s_curve.py` has computed
  per-version cumulative curves since the `/scurve` page shipped. Nothing routed them to the Q&A,
  and no test could notice, because every test asserted on what the fact base *contained* rather
  than on what it *lacked*. Absence has no natural assertion site — you have to go and write one.
- **Relevance ranking will drop the frame.** `relevant_facts`/`model_evidence` rank facts by
  overlap with the question and truncate at a cap. That is exactly right for evidence and exactly
  wrong for the fact that defines the *population*: a question phrased without the series facts'
  vocabulary would rank them out, and the answer would then be confidently scoped to the wrong
  universe — the original bug, reintroduced by the selector rather than by the builder. Population
  frames need pinning, not ranking.
- **Silent truncation is the defect, not the limit.** Both halves of this report are the same
  failure. The question box cut at 500 characters and said nothing; the fact base covered two
  versions and said nothing. Where a bound is genuinely needed (the 60-version render cap added
  here), the output must *state* that it elided — a truncation the reader can see is a rendering
  choice, one they cannot see is a lie by omission.
- **A "no measurement" case must not render as a zero.** A version scoped to no activities came out
  as `0% actual vs 0% planned, gap +0.0` — which reads as *exactly on plan* for a version that was
  never measured at all. The two unreadable causes (no data date, no activities in scope) also have
  to be told apart in the output, or the model conflates "we have no status date" with "the filter
  emptied this version". Law 2's "—" never 0, at the fact boundary.
- **And the near-miss that proves the discipline pays:** the new S-curve equivalence test passed on
  its first run while comparing **zero** version pairs — its synthetic data dates sat outside the
  golden project's own window, so every version was off the animated curve's axis and the comparison
  loop never executed. Only the `compared >= 2` guard inside the test caught it. A loop-based
  assertion needs a floor on its own iteration count, or "green" means "never ran".
### 2026-08-13 — a guard is only as strong as the test that pins its DATA

A seven-dimension audit with adversarial verification. Four lessons, and the first one is the most
expensive thing this project has learned about its own safety story.

- **A guard is only as strong as the test that pins its DATA.** POLARIS's entire Law-1 locality
  guarantee funnels through one frozenset, `net_guard._LOOPBACK_HOSTNAMES`. The guard suites are
  thorough about *behaviour* — they pin `8.8.8.8`, `example.com`, `10.0.0.5`, `evil.com` as rejected
  — and pin the *contents* of the allowlist nowhere. So adding one hostname to it leaves **226**
  guard/AI/air-gap/startup tests green (reproduced at **854** across a wider selection). Sampled
  negatives cannot detect a named positive; only a closure pin on the set itself can. Anywhere a
  security property reduces to a data literal, pin the literal.
- **An architecture that offers no legitimate path to a real need will get the dangerous path
  taken.** The operator had a lawful, NASA-approved requirement for a remote model. The repo's
  `cloud` option is dead (`ai/cloud.py` absent, `cloud_backend` never supplied) while the settings
  form still advertises it. The only route that actually works is widening the loopback validator —
  the single change that silently re-labels a remote host as local everywhere at once. The tool
  routed a legitimate need into its own worst failure mode. **A dead affordance is not neutral; it
  is a signpost pointing at the hack.**
- **A claim derived from CONFIG describes intent, not behaviour.** `banner_for(state.ai_config)`
  renders what was configured; `route_backend`'s Banner — the one that knows what actually resolved
  — is dead code. So the page can announce a gateway that is down, or announce local-only while data
  leaves. Any attestation a user is meant to rely on must be derived from the resolved object, not
  the requested one.
- **Verify the SCOPE of a doc-truth finding before acting on it.** An agent reported "every product
  doc states the no-egress guarantee unconditionally — the deployed instance falsifies all of them."
  The adversarial pass narrowed it correctly: nothing in *this repo* falsifies those sentences,
  because the shipped validators hold. They are false only of a **patched install**. "The docs are
  wrong" and "the docs are wrong about a modified build" demand opposite fixes — the first says
  rewrite, the second says make conditional. Running verifiers earned its keep here: they narrowed
  20 of 57 findings and refuted none, which is the signal that the finders were aggressive and the
  verification real.


### 2026-08-12 (d) — a fixture generated by a rule cannot validate that rule (ADR-0391)

The session closed ADR-0108 / DoD Band-1 item 001: the engine understated a real 21-day slip. Every
lesson below cost something today.

- **A fixture written by a rule cannot confirm that rule.** The first cut of the fix floored a
  started task at its recorded `actual_start` and reproduced TP4 v5's stored `2026-07-17` exactly —
  which felt like proof and was not. `tools/make_test_projects.py::_schedule()` does
  `t.start = st.started`: it pins started tasks at their actual dates and its own docstring claims
  that is "exactly as MS Project would". The fixture agreed because both sides shared a model. The
  operator caught this before it landed. **Check where a fixture's numbers came from before
  treating any of them as an oracle** — and prefer a marker census over an assumption: real MS
  Project exports carry `EarlyStart`/`EarlyFinish`/`TotalSlack`/`Critical` on every task and
  `Stop`/`Resume` on progressed ones; the synthetic battery carries **zero** of all of them. That
  census is now a committed guard, `tests/engine/test_fixture_provenance.py`.
- **The corroborating oracle may already be in the repo, in a doc nothing cross-references.**
  `docs/FUSE-VALIDATION.md` had recorded the operator's Acumen Fuse run for months: Fuse's finish
  for TP4 v5 is `2026-07-17`. The generator and a licensed reference tool agreed and the engine was
  the outlier — the understatement was real all along. The doc defect was not a wrong number, it
  was a **missing cross-reference**: TEST-PROJECTS.md's caveat and the old guard never pointed at
  the Fuse run, so the committed XML read as if it were itself an MS Project oracle. **Before
  concluding a claim is unsupported, grep for the artifact that would support it.**
- **An ADR's observation can be right and its diagnosis wrong.** ADR-0108 saw a real gap and named
  the data date as the cause. The mechanism was an ignored `ActualStart`; `cpm.py` never needed a
  `status_date` reference at all. Worse, ADR-0108's own headline case (EVM2) has **no actuals** —
  all six divergent activities are 0% complete, and the divergence is a sub-day duration on a
  lunch-break calendar. **Re-derive a carried finding from measurement before implementing against
  its description.** Two prior attempts implemented the description and were reverted.
- **A new disclosure needs its own channel when the existing one carries a judgement.** Routing
  floored actuals into `date_driven` would have been one line — and would have emitted "N scheduled
  dates are not supported by logic … tie these activities into the network" for 724 activities of
  ordinary reported progress. A *fact* and an *accusation* must not share a field.
- **The MPXJ shallow-clone trap stopped being theoretical.** Previously logged as "harmless so far
  — identical bytes at every candidate". Today the container clone was shallow, the pin resolved to
  `79865bc` instead of `42d92dc`, and only a diff against `origin/main`'s committed installers
  caught it. DoD item 117 (a shallow-clone guard in the build) has now cost real time; it should
  stop being deferred.
- **`| head -N` can SIGPIPE-kill a build mid-way.** Piping `build_installers.py` into `head -3`
  terminated it after three of nine files, leaving `.ps1` regenerated and `.sh`/`.command` stale —
  a *partially* rebuilt artifact set, which is worse than a failed build because it looks done.
  Never pipe a generator through `head`; redirect to a file and read that.
- **A fixture sweep's GLOB is part of its claim.** The blast-radius sweep globbed
  `tests/fixtures/**/*.xml` and silently missed every `.mspdi.xml.gz` golden — including
  `Large_Test_File`, the primary 2,126-activity reference, where the change's single largest effect
  lived (826 -> 164 disagreements). The sweep looked exhaustive and was not. Same family as "a
  sweep's population and pattern are part of its claim": **compressed and wrapped fixtures are still
  fixtures**, and a glob that cannot see them under-reports by construction.
- **Prefer the alternative you can measure over the one you can argue.** Choosing between the full
  floor and an incomplete-only floor was settled in one run: incomplete-only keeps every Fuse win
  and spares one golden, but leaves Large_Test_File at 826 -> 826, because the entire gain lives in
  the COMPLETED tasks. No amount of reasoning about "which is more principled" would have produced
  that number, and it inverted the intuition.
- **What worked:** measuring against the oracle that can actually adjudicate. Once TP4 was ruled
  out as self-confirming, the four genuine MS Project exports gave a directional signal no
  synthetic file could — **132 of 132 per-task disagreements were engine-early**. One-directional
  spread is a systematic defect; a modelling difference scatters both ways. That single number
  justified the change more than any fixture match did.


### 2026-08-12 (c) — a closure is not closed until it stops growing (ADR-0390)

Phase 4 slice 25 cut the **last page family** out of `app.py` (8,482 → 8,037): `settings`, into
`web/settings.py`, twelve names, zero forced descents. Outside the fenced `groups`, the monolith no
longer holds a page family. Four lessons, and the first two are corrections to work this repo was
already proud of.

- **The second hop is where a cut breaks.** ADR-0365's rule is "closure before cut", and three
  slices have followed it. It still under-delivered here, because the closure was taken to a fixed
  point *of the movers* and not *of the blockers*. `_settings_body` needs `_second_backend`;
  `_second_backend` needs `_BACKEND_PROBE_TTL` and `_UseMarking`, both of which are shared with a
  stayer in exactly the same shape as the three names the record had already flagged. The recorded
  price of 3 was really **5**. Cutting to the record would have produced a module that does not
  import, or a `settings` → `app` cycle. Iterate the closure until it stops growing, and say which
  hop each member arrived on.
- **A count copied forward decays even when the reasoning behind it was sound.** ADR-0389 was right
  to relabel that column *candidates* rather than *descents* — and the number inside it was still
  wrong. Relabelling a figure is not re-measuring it.
- **The monkeypatch repoint is keyed on the CALLER, not the name.** ADR-0297 named this trap
  fourteen slices ago; this is the slice where it fired at scale. 21 hits on bound names split
  **14 repoint / 7 leave alone**, and `_ollama_or_none` and `_second_backend` each appear on *both*
  sides: patched then driven through `/settings` the consumer moved, patched then driven through
  `/api/ask` it did not. A name-keyed repoint would have broken seven working tests while fixing
  fourteen broken ones. **Three of the fourteen would have passed silently**, so the non-zero case was forced
  with counting spies — app-globals 0× / settings-globals 1×, and the control is the mirror image
  on the *same name*, 1× / 0×. That symmetry is what makes a zero a measurement of the boundary
  rather than of a broken instrument.
- **Verbatim text is not always verbatim behaviour.** `_UseMarking` logs through
  `logging.getLogger(__name__)`. The line moves byte-for-byte; `__name__` is not text, so the logger
  name changed with the module. Nothing observes it, and rewriting it to a literal would trade a
  verbatim move for a hard-coded lie — so it moved as-is and is named in the ADR. Every prior slice
  treated byte-identity of the moved definitions as sufficient proof of behaviour preservation; it
  is sufficient only for code that does not read its own module identity. Grep the moved bytes for
  `__name__` / `__file__` / `__module__` / `globals()` / `sys.modules` before claiming otherwise.
- **"What has the corpus never rendered?" is now the standing first question.** Two consecutive
  slices found dark members whose real cause was a whole *class* of unrendered input — last slice a
  fully-progressed as-built, this slice a **configured AI** (every stage ran on the shipped default
  `AIConfig`, so a non-default backend, a second model, an attached launcher and any `OLLAMA_*`
  environment were all unreached). Five dark members, one cause. The `[aiconfig]` stage lit three of
  them; the remaining two are dark *by construction* (a wrapper needing a live model, a cache TTL
  that cannot change bytes) and are reported as a named gap rather than smoothed over.
- **A control whose shortfall you can explain beats a perfect one.** The positive control `_e`
  scored 29 of 31 extracted modules — and the two misses are exactly `ssi.py` and `volatility.py`,
  the two modules with no HTML. A bare 31/31 would have carried less information.
- **Predict the control, then run it.** Probe B's expectation (302) was derived from probe A's
  per-stage decomposition (29 + 7 × 39) *before* the run, on the theory that the new stage is
  structurally an ordinary loaded stage. It landed exactly, with 39 in the new stage — two
  instruments agreeing on a number neither was told.
- **A sweep's PATTERN is part of its claim, exactly as its population is — and the pre-mutation
  control is what catches it.** The first monkeypatch sweep anchored its regex on the fixture's name
  (`monkeypatch.setattr`); `test_coverage_app.py` binds `mp = monkeypatch` first, so four sites were
  invisible — all four feeding `_ai_status_note`, all four needing the repoint. Nothing in the sweep
  could have revealed that. What revealed it was the mutation battery's refusal to score anything
  until its selection is GREEN BEFOREHAND: the baseline run went red before a single mutation was
  applied. Re-swept receiver-agnostically, 17 hits → 21 and the repoint 10 → 14. Sweep on the SHAPE
  of the call, never on the name of the receiver, and never skip the pre-mutation control.
- **Do not edit an instrument while it is running.** Extending `oracle_corpus.py` mid-probe changed
  the label set under a probe that was using it. It aborted cleanly (the harness compares label
  *sets* before diffing bodies) and the run was redone against both instruments — which is how the
  before/after columns came to exist at all. The standing rule was "never measure a tree a battery
  is mutating"; it needs the mirror clause, **never mutate an instrument a measurement is using**.
- **One worktree, one actor.** Two independent measurements were pointed at the same scratchpad
  worktree — a probe that restores `app.py` from a saved copy after every render, and a verification
  agent applying a trial cut in the same tree. Each silently reverted the other: the agent wrote a
  cut `app.py`, a later `wc -l` read the uncut length, and its first-pass results ("all green, zero
  cascade") were measured against a tree it did not think it had. It caught this only because it
  bracketed the measurement with `wc -l` guards *inside the same shell invocation* — and, had it
  not, it would have reported the exact opposite of the truth. The probe was re-run in a dedicated
  worktree for the same reason. **Bracket a measurement with a cheap identity check in the same
  invocation, and never share a worktree between two things that write.**

### 2026-08-12 (b) — a rule you have written down can still be under-applied (ADR-0389)

Phase 4 slice 24 cut the last four zero-descent page families out of `app.py` (9,125 → 8,482):
`curves`, `ribbon`, `workbench`, `volatility`. The extraction was routine. Three of the lessons
were not, and one of them is about a rule this repo wrote down two dozen ADRs ago.

- **A count that reads as a verdict gets spent as one.** ADR-0351's descent rule says a symbol a
  new module needs must live *at or below* that module's layer — which permits **two** remedies:
  descend into `components.py`, or simply move into the family module, because `app.py` is the top
  layer and reaches anything through the `X as X` re-export. Only a referrer in *another extracted
  module* forces the first. Three ADRs recorded "settings: 3 descents" without ever asking which
  remedy applied. Measured this slice: all three blockers live in `app.py` itself, and an AST scan
  over all 28 extracted view modules finds **zero** references to them (positive control `_e`: 26
  modules). **The lesson:** when a column's values will be read as decisions, label it for what it
  actually holds — the walk's column now says *candidates*.
- **When a member is dark, ask what the corpus has never rendered — not what the member needs.**
  `_RIBBON_FLOAT_EXTRAS` guards the Law-2 branch that shows "—" instead of a fabricated Avg/Max
  Float when a schedule has no incomplete activities. Chasing the member would have meant one
  narrow fixture. Asking the wider question found that **every** MSPDI fixture (16) and the one
  XER has at least one activity under 100% complete: the oracle had never rendered a
  fully-progressed as-built *at all*, which is an ordinary forensic input. The new `[allcomplete]`
  stage is a **byte transform of an existing fixture** (`<PercentComplete>` → 100), not a new
  file — and it asserts its own landed count against the `<Task>` count, because a fixture with
  one task missing the element would leave the branch dark again, silently.
- **Choosing a mutation's ANCHOR is part of the mutation.** M7 exists to measure that unit tests
  do not pin moved markup. Its first anchor appeared **4×** in `ribbon.py` — a colliding anchor is
  not span-scoped. The obvious *unique* alternatives (`>Missing Logic<`, `>Merge Hotspot<`) are
  asserted by 11 and 2 test files, so either would have "scored" — and reported the exact opposite
  of what the mutation was posed to find out. Only `>Click any metric cell<` is both unique and
  unpinned; with it, unit selection exits 0 and the oracle reports 6 labels, matching the probe's
  independent per-member count.
- **A zero-asserting spy is only adjudicated by forcing the non-zero case.** The monkeypatch sweep
  hit `app_mod.compute_activity_makeup` in a test that asserts `== (0, 0, 0)`. "The caller stayed
  in `app.py`" is an argument; patching the name and driving a **cold** `/api/dashboard` to reach
  it 3× (warm 0×) is a measurement. Green would have looked identical either way.
- **A re-walk that reproduces is worth running anyway.** ADR-0388's table came back **exactly** —
  the first carried-forward table this phase to survive a re-walk unchanged. That is not a wasted
  measurement: it is the only way to know the difference between a table that is still true and a
  table nobody has checked.

### 2026-08-12 — a priced table that had been wrong for three ADRs, and a control that named a value (ADR-0388)

Phase 4 slice 23 cut `/briefing` and `/cei` out of `app.py` (9,593 → 9,125). The lessons are about
records and controls, not about the extraction.

- **A priced table is a snapshot, and snapshots decay silently.** ADR-0383's table said `briefing`
  carried three descents; ADR-0386 and ADR-0387 carried the claim forward, and the standing queue
  opened this session with "the zero-descent set is EXHAUSTED — all eight remaining families carry
  descents." Re-walked, `briefing` carries **zero**, and so do five others. Two of its supposed
  descents belong to `settings`; the third, `_active_backend`, is reached only from a **route** —
  and "a route-only referrer never forces a descent" is ADR-0378's own rule, written down, restated
  by ADR-0387, and still mis-applied to this family for three consecutive ADRs. **A rule you have
  written down is not a rule you have applied.** The only thing that caught it was rebuilding the
  measurement instead of reading the record.
- **A control that names an expected VALUE beats one that names a direction.** The rebuilt referrer
  walk failed its control twice before it passed, and both bugs produced *plausible* output:
  `ast.walk(create_app)` yields `create_app` itself, so every name inside it got one poison referrer
  and **every family priced at zero members**; and the `card` seed used `GET /card` when the route
  is `GET /card/{name}`, so that family had no seed routes — zero again. "Zero" is exactly what a
  small, clean, wrong answer looks like. A control asserting `expected (2, 140)` catches both; a
  control asserting "finds something" catches neither.
- **The ADR-0386 return-type trap fired first thing, from the trap list.** The probe's positive
  control (`_page`, which wraps every HTML page) moved zero labels and aborted the run — the marker
  injector handled `str` and `dict`, and `_page` returns an `HTMLResponse`. Knowing a trap by name
  did not prevent it; the *aborting control* did. That is the argument for controls over vigilance.
- **A mutation that does not score can be the most informative one in the battery.** Two mutations
  edited markup inside moved definitions and no unit test noticed. That is not a harness bug — it is
  a true measurement that the unit tests do not pin page markup, which is precisely why the render
  oracle exists. Re-scored against the oracle they moved 2 and 5 labels — numbers that **match the
  probe's independent per-member counts exactly**. A third mutation (a module-scope upward import)
  killed pytest at *collection*, so the layering guard never ran: louder than a named failure, but
  not the guard firing. Re-posed under `TYPE_CHECKING` it was caught by name — and that is also the
  likelier way a real upward import would arrive.
- **A doc-comment that names a FUTURE has an expiry date.** ADR-0387 split a `#:` block across two
  modules and left one half saying the twin constant "stays in `app.py` until the /briefing family
  is cut." This slice cut it. Two such sentences plus a stale import comment (which was wrong on
  both of its counts) were found by grepping the moved names — not by remembering.
- **When a member is dark for want of a render CONDITION, the condition is the missing thing** — and
  the extension is only honest if the member then moves exactly the labels the condition added.
  `_stack_not_measured` renders only when `/cei` has no scored month; a query-string variant could
  never reach it because the condition is a property of the loaded population. The new `[ceidark]`
  stage (652 → 800 labels) makes it move exactly two labels and nothing else.
- **The shallow-clone trap fired exactly as the handoff predicted**, which is the system working:
  `git log -1 -- tools/mpxj` returned the clone boundary, `git fetch --unshallow` fixed the pin to
  `42d92dc`. But it is still a documented workaround rather than a guard, and a documented
  workaround is one distracted session away from shipping wrong. It stays queued, named.

<!-- Append new dated entries ABOVE this line, newest first. Keep Parts I–VII current when a lesson generalizes. -->

### 2026-08-11 (b) — the instrument reported zero because it could not report anything else (ADR-0387)

Phase 4 slice 22 cut three page families out of the monolith (`brief`, `card`, `scorecards`) and
descended one shared name into `components.py`. The extraction itself was routine. The lesson was
not.

- **A probe whose failure mode is SILENCE cannot be sanity-checked by reading its output.** The
  pre-flight render probe scored `_brief_body` as oracle-dark. It is not dark — `/brief` renders its
  body at all four loaded stages. The harness had diffed `manifest.json`'s *values*, and the oracle
  names each body file `sha256(LABEL)[:16] + ".bin"` — **derived from the label, not the content**.
  That value is constant across every run of every tree. The comparison could not have reported a
  difference for any member, including one that changed every byte of every page. It said "0 moved"
  in exactly the voice a real discovery would use. This is the repo's most-repeated defect class —
  a green check that could never fail — and it turned up *inside the instrument built to detect it*.
- **The fix is a control that ABORTS, not one that prints.** The probe now compares body bytes, and
  a positive control runs BEFORE any finding is trusted and halts the run if it moves nothing. A
  second, independent check asserts the marker text actually reached a rendered body. Two
  instruments that can fail differently beat one that can only fail silently.
- **Check what a name is DERIVED from before you diff it.** A 16-hex filename looks
  content-addressed. This one is label-addressed. The generalisation: an identifier that *looks*
  like a digest is not evidence of one — read the function that mints it.
- **A descent is forced by a MOVER, not by sharing.** `_sources_line` is called by eight page
  routes (which never block a move — routes import downward) *and* by `_scorecards_body`. That last
  one is what forced it down into `components.py`: a view module may only import downward, so
  reaching back into `app.py` would have closed a cycle. Sharing alone is not a descent; a mover
  calling the shared name is.
- **An export's relationship to its page is per-family, and must be measured each time.** Three
  families in one slice gave three different answers: `brief` — export contributes no movers (call
  graph and render probe agree); `card` — no export route at all; `scorecards` — the export DOES
  share the page's surface, and `_scorecard_export_table` moves eight export labels. A page-only
  probe anchor would have measured that member at zero and called it dark.
- **Extending the oracle is part of the method, not a deviation.** `_parse_committed_date` was
  genuinely dark, because the route *requires* a `committed` query parameter and the corpus never
  sent one — the bare label 422s before the parser's live path runs. The answer was to add the
  render condition (one variant, corpus 648 → 652), not to write the member off as unreachable.
  Choosing the pool's own deterministic finish as the date is what made the render non-degenerate.
- **A shared doc-comment is not a movable unit.** `_BRIEF_XLSX_TITLE` sat under a `#:` block
  documenting BOTH chapter-12 export titles: *"Both name a REAL endpoint…"*. The constant's bytes
  moved verbatim, but the comment had to be split — leaving it intact would have left a false
  sentence in `app.py` and no sentence at all in `brief.py`. Verbatim extraction governs CODE;
  prose that describes a pair stops being true when the pair is broken.
- **A plausible module name is not a measurement.** This slice's own ADR first stated that
  `export_brief` re-derives through `reports/brief_tables.py`. Reading the route showed no such
  module exists on that path — it renders via `ai.brief.brief_blocks`. Caught before it landed, but
  it is the same failure as any other unverified claim, and it was *in the document whose job is to
  be the record*.
- **A durable doc nobody's ritual OWNS goes stale silently.** `docs/STATE/NEXT-SESSION-PROMPT.md`
  was EIGHT SLICES out of date — last refreshed at slice 14 / v1.0.186 / ADR-0378, while the repo
  was at slice 21 / v1.0.193 / ADR-0386. It is the file the kickoff prompt is pasted from, so this
  session was handed "resume at slice 15" for work finished five slices earlier, and only the
  auto-injected handoff caught it. The file's own header says to refresh it whenever the queue
  changes; seven consecutive sessions didn't, because nothing FAILS when it rots. The handoff has
  a drift guard (`tests/test_state_docs.py`) and never rots; this file has none and always does.
  **The docs that stay current are the ones a test fails over.**
- **Check what "normal" is before calling something slow.** The CI `test` jobs ran 61 minutes and
  I treated that as anomalous, because the kickoff prompt said "~30 min". Four consecutive prior
  runs measured 57.5 / 60.7 / 61.8 / 62.5 minutes — ~60 is the norm and the estimate was wrong by
  2×. The structural reason was available the whole time: `floor` runs the same suite WITHOUT
  coverage in 22 minutes, while `test` adds coverage instrumentation, a second pytest for the
  parity gate, mypy, bandit and pip-audit. One query against history beat three rounds of
  speculation — **a baseline is cheaper to look up than to guess at.**
- **What worked:** rebuilding the referrer walk from scratch and checking it reproduced the PREVIOUS
  slice's published numbers before trusting it on three families it had never seen. An instrument
  that agrees with a known answer has earned one unknown.

### 2026-08-10 (f) — a residual ledger is a claim, not a fact; a conditional gate can stop being a gate (ADR-0385)

- **The parity record understated the tool.** Asked for whatever most improves accuracy against
  Acumen/SSI/MS Project, the first move was to *measure* rather than to fix — and measuring found
  that both `case.json._deltas` and `docs/PARITY-REPORT.md` described an SSI driving-slack gap
  with a live `xfail` that had been CLOSED for a month. The golden directory was deleted, the test
  was deleted, and two replacement exports (`ssi_uid67` 20-UID Path-01 membership, `ssi_uid145`
  108 UIDs) were passing in the gate. **Generalizes (→ Part V):** an evidence record is written
  when a gap is real and nobody re-reads it when the gap closes. Understating fidelity is not the
  harmless direction — for a testimony artifact it volunteers a weakness that does not exist.
- **Pin the property, not the prose.** The obvious fix was to string-pin the corrected sentences.
  That catches exactly one instance. The property that generalizes is *the parity evidence may not
  cite a golden fixture that does not exist* — a path citation is an instruction to go and look,
  so historical mentions get written as bare names instead. That guard would have caught this the
  day the fixture was deleted.
- **A conditional gate is a gate that can stop being one.** `pytest -m parity` is gate-locked by
  the build contract, but eight of its 52 tests carry `needs_java` and three more carry
  `needs_mpp`/`needs_artifacts`. Hiding `java` from `PATH`: **8 skipped in 0.25 s, exit 0.** A
  green "Parity gate" badge over a run that compared nothing to Acumen or SSI. The `browser` job
  had already learned this and carries a "fail loudly if the proof silently skipped" step; Law 2's
  own gate did not. **Generalizes (→ Part IV):** every skip-conditional proof needs an assertion
  that it ran, and it must match ANY skip — enumerating skip reasons is the same mistake as
  enumerating failure modes.
- **A guard can pin a decayed statement and make the correction look like a regression.** Removing
  the false SSI row reddened a doc guard asserting `"107" in parity` — a number that existed ONLY in
  the retired rows. The cheap response is to restore the stale number and stay green. **Generalizes
  (→ Part V):** when a guard reddens on a correction, ask what the guard was actually pinning before
  assuming the change is wrong. And prefer assertions that cannot be satisfied incidentally: bare
  `"108"` is satisfied by `ADR-0108`, so the repointed guard asserts `"108 UIDs"` and was falsified
  by gutting the SSI row with the ADR references left intact.
- **A falsification that fails to fail may be the MUTATION's fault, not the guard's.** The first
  attempt changed one of several `108` occurrences and reported NOT PROVEN; the guard was fine, the
  mutation was partial. Check the mutation's own reach before concluding a guard is weak.
- **A guard can trade one silence for another.** The parity skip-guard's first version piped pytest
  into `tee`; GitHub's default `run:` shell is `bash -e` WITHOUT `pipefail`, so the step took tee's
  exit code and a genuine parity FAILURE would have passed. It replaced a bare `pytest -m parity`
  that did fail correctly — so the net effect was protection against not-running bought at the price
  of protection against failing. **Generalizes (→ Part IV):** when you REPLACE a check rather than
  add beside it, enumerate what the old one caught that the new one does not. Write the truth table:
  clean → 0, skipped → 1, failed → 1.
- **Do not fix and mask in the same change.** The tempting completion was to add `setup-java`
  beside the guard. That would have made the guard pass whether or not CI had *ever* run the
  oracles — destroying the one measurement worth having. Ship the guard alone; let CI answer.
- **The quiescence trap fired again**, exactly as the handoff warned: `pgrep -f pytest` reported a
  live suite on a tree where none was running, because the checking shell carries the string in its
  own argv. Adjudicated by scanning `/proc` for real python processes excluding self.

### 2026-08-10 (d) — a queue is a record of what was NOTICED, not of what exists (phase 4 scoping + slice 19, ADR-0383)

- **The published list being exhausted was not the file being exhausted.** ADR-0382 correctly
  reported that the phase-3 page-family list had no entries left, and asked the next session to
  re-scope before assuming a phase 4. Doing that re-scope — a structural census of `app.py` plus a
  referrer walk seeded on every route's FULL surface (page + `/api` + `/export`) — found
  **fourteen page families still in the file, worth 2,709 mover lines**, about a quarter of the
  monolith. Nothing was wrong with the old queue; it simply recorded the families someone had
  noticed. **Generalizes (→ Part IV):** before declaring a phase, a backlog or a sweep complete,
  re-derive the population from the code. A list that has been worked to the end proves the list
  is finished, never the work.
- **A closure computed over `def`s alone strands the constants the block owns.** The referrer walk
  is a call graph, so four module-level constants sitting physically inside the /risks block and
  read only by it (`_IMPACT_LABELS`, `_LIKELIHOOD_LABELS`, `_RISKS_EXPORT`, `_RISKS_XLSX_TITLE`)
  were invisible to it. What caught them was the separate free-name pass that classifies every
  name a mover references as import / constant / app-level function / app-level **assignment** —
  and, for `_RISKS_EXPORT`, extending the region by eye past the three-line `#:` doc-comment block
  that sits outside its AST span (standing trap 21). Left behind they would have failed at first
  render with a `NameError`, which is the cheap failure — but only by luck.
- **The SHAPE of a sweep can be wrong even when its pattern is right.** The dropped-import sweep
  was first run as a line-prefix regex over the diff (`^-from` / `^-import`) and reported ZERO.
  It was wrong: all three real drops (`SEVERITY_ORDER`, `Category`, `Finding`) came out of a
  *parenthesized* `from … import (…)` block, where a removed name is the line `-    Category,` and
  matches no import-prefix pattern. An independent AST comparison of the two trees' import **sets**
  found them. ADR-0378's lesson was "sweep by bare NAME, not a module-qualified regex"; this is the
  same failure one level up. **Generalizes (→ Part V):** when a sweep answers a question about
  program structure (imports, calls, bindings), run it over the structure — a diff is a rendering,
  and rendering-shaped patterns miss whatever the renderer chose to nest.
- **What the instrument returned.** ADR-0382 committed the render oracle one session before a cold
  container needed it, and it rebuilt the inherited fingerprint (648 labels, `[empty]` 60
  `{200:41,400:17,422:2}`, four loaded stages of 147) with zero prose archaeology — the first
  cold-start test of that decision, passed. Slice 19 then ran clean on it: probe 8/8 render-proven
  with zero dark members, 648/648 byte-identical pristine vs cut, 8/8 falsified in the new
  location with exact label lists, multiset 59 added / 0 removed, battery 6/6 named.
- **Also:** the prefix undercounted this family 2.27× by lines and 4.0× by names — `_risk_matrix`,
  `_risk_ranking`, `_finding_card`, `_finding_quant`, `_risk_band` and `_wd` carry no `risks`
  prefix. The prefix stays a finder; the walk stays the definition.

### 2026-08-10 (c) — committing the instrument is what found the rot in it (phase 3 slice 18, ADR-0382)

- **The fix for a decaying oracle is a file, not a better ADR.** ADR-0381 measured the decay
  (648 -> 592 rebuilding from prose in a fresh container) and named the cure; this session applied
  it. The corpus now lives in `tests/web/oracle_corpus.py` + a committed 648-line label list + four
  guards. The half derived from `app.routes` was always self-healing; the hand-authored half was
  always the casualty. Nine slices re-derived it and each rebuild could only recover what the prose
  pinned.
- **The act of writing it down is what exposed the defects — prose hid them.** SIX of twelve
  variants reconstructed from ADR prose were **decoration**: FastAPI silently ignores an undeclared
  query parameter, so `/evolution?view=tiers`, `/resources?field=Status`, `/path?target=22`,
  `/api/sra/grid` and `/sra/ssi/save` rendered byte-identical to their bare labels and reached no
  new code at all. They would have padded the count while covering nothing. **Check a hand-authored
  oracle label against the route SIGNATURE, never against an ADR's description of it** — and guard
  it, which this slice now does.
- **A normalizer can be right and still incomplete.** The launch token is described in the recipe as
  `{hex16}.{wipe_gen}`, which is true — but it has TWO spellings, the page's `<meta name=sf-launch>`
  and `/api/whoami`'s `"launch_token"` JSON key. Pinning one left five labels flapping. Adjudicating
  by payload diff before touching the harness (the standing rule) turned a "flaky oracle" into a
  one-line pattern fix.
- **Ending a zero-finding streak is a result, not a regression.** Sixteen consecutive slices
  reported "0 dropped imports"; the seventeenth found three (`compute_net_finish_impact`,
  `diff_versions`, `trend_across_versions`) because this family was app.py's LAST consumer of them.
  A streak measures the code met so far, not the sweep's redundancy. The adjudication that made it
  safe was AST + alias-agnostic with a 184-file positive control — "zero readers" is only a
  measurement when the sweep is proven to run.
- **A filter that flags nearly everything has not swept.** The first source-text pass used
  `__file__` as a detector and called 178 files "source-text readers", producing 665 candidate
  literals that were words like "project" and "critical". Almost every test uses `__file__` to find
  fixtures. Demanding a genuine view-source idiom (`getsource` / `<module>.__file__` /
  `with_name("*.py")` / a literal `"app.py"`) *beside* a real read call cut it to 6 readers and 0
  repoints. Widening a detector (ADR-0381) and narrowing its filter are both required; only one was
  learned last time.
- **The named-failure rule's own instrument needs the same scepticism as the code under it.** The
  mutation runner parsed pytest's `FAILED <nodeid>` line with `split(" ")[0]` — the literal word
  `FAILED` — so the first falsification reported NOT PROVEN against a guard that had failed exactly
  as designed. Had the script not asserted its own expectation, the session would have "learned"
  that a working guard was dead.
- **`python -m pytest` and a bare `pytest` do not share a `sys.path`, and CI runs the bare one.**
  A new guard imported its helper as `from tests.web.oracle_corpus import ...`. That resolves only
  because `python -m pytest` prepends the CWD; a bare `pytest` does not, so the module was fine
  across a 3569-test local run and died in COLLECTION on three CI jobs at once (floor, test 3.11,
  test 3.13) with `ModuleNotFoundError: No module named 'tests'`. `tests/` is not a package. The
  repo already had the answer in the sibling guard — `spec_from_file_location`, the same idiom
  `test_intake_manifest.py` uses for `tools/`; the failing spelling was the ONLY `from tests.`
  import in the tree, which is the tell. **Reproduce CI's path with `PYTHONSAFEPATH=1 python -m
  pytest`** — it suppresses exactly the CWD prepend that hides this class of defect, and
  `--collect-only` under it sweeps the whole tree in 8 seconds. Do not reach for a bare `pytest`
  to reproduce it: like ruff, a second `pytest` lives on PATH belonging to another interpreter,
  and it fails on an unrelated `conftest` import instead.
- **Measured, not assumed, is cheap when you already have the AST.** The claim "the export route
  contributes no movers" was settled by computing `export_compare`'s app-level callee set (empty),
  not by reading it. Same for "no shared name forces a descent" — every referrer resolved to the
  route, which imports downward.

### 2026-08-10 (b) — an instrument that lives in the scratchpad is re-derived, not inherited (phase 3 slice 17, ADR-0381)

- **The oracle did not survive the container, and nine slices never noticed.** Every slice since
  ADR-0372 has "inherited" a 648-label route oracle that exists only as prose in the ADRs plus a
  harness in a scratchpad directory a fresh container does not have. Rebuilt from the route
  surface this session, the *mechanically derived* part reproduced on the nose — `[empty]` 60
  `{200:41,400:17,422:2}`, the 60 parameterless GETs, the `404:4` per loaded stage ADR-0379
  repaired — and the ~14 hand-authored variant labels per loaded stage did not, because the ADRs
  name a few in passing and record **none** of their URLs. Corpus: 592, not 648.
- **The generalisable shape:** the parts of an instrument that were added *because they were hard
  to reach* are exactly the parts a rebuild cannot recover. Derived coverage heals itself;
  hand-authored coverage decays. Any harness whose result is quoted in a decision record has to
  live in the repo — as a fixture or a script, not as a paragraph describing one.
- **Not padding the number back was the call.** Inventing 56 replacement labels would have
  produced a corpus with the published *count* and different *content*, which every future slice
  would then compare against. A smaller honest corpus with its scope stated beats a familiar
  number that no longer means what it says (ADR-0377's rule, applied to the corpus itself).
- **Check the shadowing order in any origin resolver.** The closure harness reported
  `_what_drives_header` as sharing the name `analysis` with an outer binding — it was the
  function's own **parameter**, flagged because the resolver consulted the nested-scope table
  before the local one. Caught before it reached a finding, but a phantom shared name costs a
  whole descent argument, and the failure mode is silent.
- **A sweep's blind spot is often already written down in the code it sweeps.** The first
  source-text pass detected readers by path literal only — precisely the gap
  `test_gantt_find_coverage.py` documents in its own comment (a guard reaching source via
  `app_module.__file__` was invisible to a `grep -rln 'app\.py' tests/` sweep). Re-run with three
  detectors it found 203 readers and zero moved literals. *Read the comments in the files a sweep
  targets before trusting the sweep.*
- **A route's URL does not assign it to a family.** `/export/{fmt}/path/{name}` renders the
  *driving* trace; it contributed no movers to the /path cut. Membership is the referrer walk,
  not the path string — the same lesson the prefix census keeps teaching, one level up.


### 2026-08-10 — a census miss is a warning about the ORACLE (phase 3 slice 16, ADR-0380)

- Cut the /scurve family into `web/scurve.py` (7 movers, app.py 11,095 -> 10,871). The prefix
  census said 6 names / 212 lines; the referrer walk said 7 / 222. The extra name,
  `_pair_criteria`, is reachable only from `/api/scurve` and carries no `_scurve` prefix.
- **The lesson that generalises.** That same member was ALSO invisible to the inherited
  644-label oracle — for a completely different reason: no inherited label supplies the `cf`/`cv`
  query params, so it did no work on any of the 648 renders. Two independent instruments (a name
  finder and a render oracle), two independent causes, ONE member. That is not coincidence: both
  blindnesses follow from the same root — the member sits off the obvious path. **So when the
  cheap instrument misses something, treat it as a warning about the expensive one.** Had the
  walk not found it, the slice would have shipped with a clean 648/648 byte-identity and a silent
  dark reading, and nothing downstream would have complained.
- **Mutate by OFFSET, not by PERMUTATION.** `_scurve_status_point` first probed 3/4 — `[target]`
  did not move. Adjudicated by payload before touching anything: under the target scope the page
  renders 100% finished against 100% planned, and the anchor was a *swap* of `(actual, planned)`.
  A permutation applied to equal values is the identity. Re-run with an additive marker
  (`actual + 11.0`) it reads 4/4. A swap/reorder mutation reads dark exactly where the values
  coincide — which is precisely where a scoped or fully-progressed population puts them. The
  mutation must have no fixed points on the data the oracle actually renders.
- **Zero precedent is evidence.** `_CF_QUERY`/`_CV_QUERY` looked movable (S-curve-specific by
  their own doc-comment) but are FastAPI `Query` singletons used only as route-signature
  defaults. Checking mechanically rather than from memory — 220 already-extracted names across 15
  slices, not one route-signature default among them — turned a judgement call into a decision.
  Route plumbing stays with the routes; presentation moves.
- **A probe that DISABLES a member can trip the oracle's own render-condition guard.** The first
  `_pair_criteria` mutation emptied the criteria list, which collapsed the filtered payload onto
  the unfiltered one and fired the guard that exists to prove the condition is live. Mutating the
  VALUE the member produces instead keeps the guard meaningful during every probe run — and the
  guard firing was itself evidence the label genuinely depends on the member.


### 2026-08-09 (f) — an oracle can be BLIND to a whole family; a positive control that cannot see the pattern it certifies

- **The instrument, not the code, was the finding.** Slice 15's pre-flight probe reported **all
  four** /resources movers as dark — 0 labels moved each. Four dark members in one family is not a
  credible product reading, so it was adjudicated by payload before anything was changed: the
  five-snapshot TP4 pool carries **zero `<Assignment>`, zero `<Resource>`, zero `<Work>`**
  elements, so `_who_is_overloaded_header` returns `""` and `_resources_body` takes its no-loading
  branch. The population every slice since ADR-0372 has rendered **cannot exercise this family at
  all**. The lesson generalizes past ADR-0374/0375 ("a render-conditional member needs its
  condition in the oracle"): it is not always ONE conditional member — an entire family can be
  invisible, and **a blind instrument reports blindness as innocence**. *Before recording a member
  dark, prove the oracle CAN render it.*
- **Extend the oracle; never re-base it.** The fix added a fifth stage (`[resloaded]`, the
  project2_5 goldens: 164/165 assignments over 33 resources) with the render condition asserted
  before the stage is measured. The inherited 498 labels were left byte-for-byte alone — which is
  precisely what let ADR-0377's published fingerprint keep acting as a self-check on the new
  harness. Swapping the population instead would have silently re-based every future slice's
  reference and destroyed the only independent check available.
- **A positive control proves the sweep RUNS; only a control that exercises the sweep's own
  weakness proves its PATTERN.** ADR-0378 paid for "sweep by bare NAME, not by a module-qualified
  regex". This session hit the next layer: the monkeypatch sweep was a *line* regex, and it
  returned **zero on ADR-0378's own control name** — because `monkeypatch.setattr(` calls wrap
  across lines, putting the module and attribute on the following line. No alias fix would have
  helped. Replaced with an **AST sweep** (188 setattr calls across `tests/`, control reproduced,
  one real hit). **Prefer a parser to a regex whenever the thing being matched is syntax.**
- The same sweep's alias census is the quantitative case for the bare-name rule: `mpp_mpxj` 23 ·
  `launcher` 18 · **`appmod` 18** · **`app_module` 15** · `state_module` 9 · `state_mod` 6 ·
  **`app_mod` 3**. Three distinct aliases for `web.app`, and the "dominant idiom" the earlier
  sweep was aimed at is only the **third** most common.
- **The behaviour seed can surface an entry point the prefix cannot.** Seeding the closure from
  routes found `export_resource_drill` (`/export/{fmt}/resource-drill`) — the click-through Excel
  export behind one loading bar, unreachable by any `_resource*` name sweep. It was also the only
  reason the closure exceeded the census, and it forced (and lost) the descent question: it pulls
  `_cell`, which no mover touches, so ADR-0378's route-only-referrer rule kept it in place.
- The one monkeypatch hit was the **ADR-0297 phase-1 trap live again** — a spy patching
  `app_mod.compute_resource_loading` to drive the page's zero-over-allocation branch. Repointed to
  `web.resources` and proven load-bearing by reverting the target (fails exactly the named test).
  That trap has now fired in three separate slices; it is a permanent cost of the split, not a
  one-off.

### 2026-08-09 (e) — a census can be exact and still not be the definition; a quiescence guard can match its own shell

- Slice 14 (the /performance family) is the FIRST phase-3 closure to land census-exact: 4 names /
  326 ast lines by prefix, the identical 4 / 326 by referrer walk (1.00×, against a 3.6× worst
  case). Tempting conclusion: the census is trustworthy now. Wrong conclusion — it agreed only
  because ADR-0375's ruling-lag finding had already been hand-folded into the queue. **The walk
  stays the definition; a census that agrees is a finder that got lucky.**
- The five-slice "the export route contributes NO movers" streak ended: `export_performance` reads
  `_performance_data`. That changed what a probe anchor has to reach — the first anchor rode the
  TableSet title, which reaches the page and the DOCX body but NOT xlsx sheet content, so a
  9-label member measured 6. A second, on a quad row value, measured 9. **When a member feeds an
  export, anchor the probe on what the export's own tables render, not on the page.** ADR-0373's
  stronger-anchor round is not just for 0-move members.
- A shared name does NOT automatically force a descent. `_sources_line` is referred to by seven
  routes and `_scorecards_body`, but by no mover — it enters the closure through the family's own
  route body, and routes live in `create_app`, which imports downward and stays. **Adjudicate a
  shared name by WHO refers to it, not by how many.**
- The multiset diff's "never measure a tree a battery is mutating" guard was `pgrep -f pytest`. It
  fired on a provably clean tree: the shell running the check carries the heredoc — including the
  word `pytest` — in its own argv, and the `[p]ytest` bracket trick fails for the same reason. Fixed
  by scanning `/proc` for python processes excluding this pid. **A self-referential guard is worse
  than no guard: it cries wolf on a clean tree, and the natural "fix" is to delete it.** Adjudicate
  the match before touching the guard.
- **The dropped-import sweep reported "0 readers" and was WRONG.** `ruff --fix` dropped five
  now-unused engine imports from app.py; the sweep asked who reads them through `web.app` as a
  regex over `app_mod.<name>` — the repo's dominant alias. Two tests spell it `app_module` and
  patch `app_module.work_to_go_census` to spy on the P3 memo. The sweep returned zero **with its
  positive control (182 files) live**, which is indistinguishable from a clean result; the full
  suite caught it. Two lessons: **sweep by the BARE NAME, never by a module-qualified expression**
  (the name is the only invariant — aliases, `getattr` and re-exports all defeat a qualified
  regex); and **a positive control proves the sweep RUNS, not that its PATTERN is right** —
  ADR-0353's rule is necessary, not sufficient, unless the control exercises the same pattern the
  sweep depends on.
- The fix was the ADR-0297 phase-1 trap again (patch the module whose code CALLS the function, not
  the one that re-exports it). Both spies were repointed to `web/performance.py` and then **proven
  load-bearing**: reverting the patch target to `app_module` fails exactly those two tests, so
  neither passes vacuously. **A repoint is a code change and owes the same prove-able-to-fail
  round as a new test** — a rename that passes either way is a test that has quietly stopped
  testing.
- The published oracle fingerprint paid for itself twice in one session: it caught that the export
  fmts are xlsx/docx (not csv) and that `{name}` keys drop the `.xml`, both BEFORE any byte-identity
  claim. **A recipe worth writing down is one a fresh harness can be re-derived from.**

### 2026-08-09 (d) — a fingerprint is only as good as its stated scope; a silent normalizer is a flap factory

- Slice 13 (the /evm family) rebuilt the 498-label oracle and the fingerprint check read 69
  where ADR-0375/0376 said 88. The adjudicate-before-use rule fired exactly as designed — and
  the payload-level answer was that the POPULATION was identical: the 88 spans ALL FOUR stages
  (the seventeen 400s are [empty]-stage no-schedule guards), while the prior ADRs' prose said
  "the three loaded stages" (which measure 69 = 12×404 + 57×422, ADR-0374's own number).
  **The lesson: a population fingerprint must carry its stage-scope with it — a right number
  compared at the wrong scope false-alarms every time, and an unstated scope converts a
  five-second check into an adjudication round.** ADR-0377 pins both numbers.
- The first determinism pass flapped 4 whoami labels. Payload diff: `pid` only — the pid
  normalizer's JSON parse was dying on a non-UTF-8 token placeholder and `except: pass`
  swallowed it. A normalizer that can fail silently is itself a flap factory; the fix was an
  ASCII placeholder, and the flap was adjudicated by payload BEFORE touching the harness.
- The route enumeration undercounted the parameterless-GET class at 59 because an
  isinstance(APIRoute) filter skips `/openapi.json` (a plain starlette Route). "Pages AND
  APIs, no silent caps" includes it. Enumerate by method + path, never by route class.
- The descent's pre-flight probe moved /groups × 3 states on top of the /evm labels — the
  first time a descent's SECOND family was render-proven in the same probe that proved the
  first. A mover+stayer adjudication that can be probe-proven should be: the closure names
  the referrer, the probe proves it executes.
- The prefix undercount was mild this time (299 → 343, 1.15×) — but both unprefixed members
  (`_threshold_legend`, `_metric_scorecard_table`) were exactly the shapes the census cannot
  see. The referrer walk stays the definition even on a nearly census-exact family.

### 2026-08-09 (c) — a closure can run 3.6× its prefix; never measure a tree a battery is mutating

- Slice 12 opened on "analysis 356" and the referrer walk returned **26 names / 1,275 lines** —
  the page's twelve panels, six DCMA builders and two constants carry no `_analysis` prefix, so
  the prefix census saw three names where the family had twenty-six. Largest undercount ratio of
  the split so far (sra was 2.1×). The census number sizes the QUEUE; only the closure sizes the
  CUT.
- The first multiset diff was measured WHILE the falsification battery held one member mutated —
  and the diff itself carried the battery's `PRB12X` marker line as an "added" line. The standing
  "never mutate a running suite's tree" trap has a reverse form: **never MEASURE a tree a battery
  is mutating**. Re-measured after md5-verifying the tree against the post-cut snapshots; only
  the clean figure (100 added / 3 removed) was reported anywhere.
- The monkeypatch sweep's adjudication list GREW: `app_mod.compute_activity_makeup` joined the
  standing `non_summary` hit because analysis.py now binds a name the ADR-0291 projection-memo
  spies patch. Both spy /api/dashboard through app.py's own binding (the test renders no
  /analysis page), so the patch's reach is intact — but a future slice that moves the DASHBOARD
  family must repoint those spies to the module whose code calls them.
- The 4xx histogram doubled as a population fingerprint: this slice's rebuilt oracle rendered
  **88** loaded-stage 4xx labels — exactly ADR-0375's post-title-strip count — which proved the
  title-stripped pool re-formed the same population without re-deriving the grouping by hand.
  Cheap, and worth checking FIRST on every future oracle rebuild.

### 2026-08-09 (b) — a census family can be a phantom; the oracle's fixture population is a render condition

- Slice 11 opened on the queue's "what 289" and found NO family there: `_what_drives_header` →
  /path, `_what_changed_header` → /compare, `_what_could_go_wrong_header` → /sra. The "how" and
  "where" censuses dissolved the same way — seven misfiled members across three question-word
  censuses. The prefix census groups by the first word of a NAME; chapter headers are named for
  their QUESTION, not their page. Only the referrer walk assigns membership.
- Two of the seven belonged to families already cut (slices 3 and 9 predate ADR-0374's header
  ruling); they moved retroactively to sra.py/evolution.py this slice. The other five STAY until
  their families' slices — a header must not invent its family's module.
- The oracle's first shape manufactured a false dark: the five TP4 snapshots carry five distinct
  `<Title>`s, so they formed five one-version projects, the ADR-0258 active population was v5
  alone, and every multi-version page rendered its "load two versions" placeholder —
  `_how_stable_header` probed 0 moved with the member fully reachable. Payload adjudication (the
  saved body held the placeholder) caught it BEFORE a wasted stronger-anchor round. Fix: strip
  `<Title>` on upload so the snapshots join the untitled pool as one five-version population —
  4xx labels fell 133 → 88, widening the render surface for every future slice.
- The lesson pairs with ADR-0374's: read the member's render condition off the ROUTE, and read
  the population off the FIXTURES. A byte-stable oracle full of placeholders is deterministic
  and nearly blind.

### 2026-08-09 — the prefix census can file a member under the wrong FAMILY; a render-conditional member needs its condition in the oracle

- Slice 10's closure walk found `_where_it_lands_header` (77 lines) in the /forecast family —
  its sole referrer is `forecast_view`, and it is chapter 09's ("Where it lands") header. The
  prefix census had filed those 77 lines under the **where** family ("where 235"), which
  re-prices to 158 once the closure claims the member. Prior slices proved the prefix
  UNDERCOUNTS a family (the finder-vs-definition lesson); this is the sharper failure mode:
  the prefix can put a member in the WRONG family entirely, because a name's leading word is
  not its referrer graph. Lesson: the census numbers are finders for SIZING, never membership
  — only the closure's referrer walk assigns a member to a family.
- `_group_rollup_panel` renders ONLY when a group field is chosen (`… if group_field else ""`
  in the route) — a parameterless-GET oracle can never light it, however wide. The [grouped]
  variants (/forecast + /evm ?group_field=Resource + both field-forecast exports) were added
  at oracle-DESIGN time because the route source showed the condition, so the pre-flight
  probe measured 1 real move instead of reporting a false dark and burning a
  stronger-anchor round. Lesson: read each member's render CONDITION off the route before
  building the oracle, and give every conditional member a label that satisfies its
  condition — the slice-9 lesson ("aim at work that can move") generalizes to "aim at
  states that can render".
- The full-suite run started before the installer rebuild honestly failed the lockstep
  family (the committed installers still embedded the v1.0.181 wheel while src/ had moved).
  Not a defect — a sequencing cost: the informative run validates the code, but the
  reportable claim needs bump → build → docs → THEN the one full suite on the final tree.
  Lesson: the lockstep guard makes "rebuild the installers" a PREREQUISITE of the final
  suite run, not a follow-up — schedule it before the run whose counts will be quoted.
- The slice itself was the recipe running clean end-to-end: zero oracle-dark members (the
  conditional-label design above), zero reader repoints (verified, not assumed — the moved
  text carries no _TS_CAPTION_MARK/data-ts-caption/drilldown.js), 54/0 multiset, 9/9 EXACT
  falsification, 6/6 named battery with the in-body mutation shapes applied from ADR-0373
  rather than re-derived. Five families remain: what 289 · portfolio 253 · evm 239 ·
  how 214 · where 158.

### 2026-08-08 (e) — a crafted payload aimed at completed tasks measures history, not reach; patch the patcher with landed-count discipline

- The sra slice's crafted v4 setup payload (slice-7's sequences, returning per ADR-0365)
  aimed its factors/bcwc/risk/branch at UIDs 12–15 — tasks the TP4 v5 snapshot has
  COMPLETED. ADR-0308's own rule ("finished work cannot be delayed") made every risk inert:
  the focus finish never moved, the S-curve collapsed to one point, the OAT sweep was
  all-zero — and `_sra_chart_scurve` / `_sra_chart_tornado` probed 0 moved labels TWICE
  (the second probe with stronger anchors — chart titles, not colors — is what separated
  *weak anchor* from *genuinely unreachable*). Re-aimed at the live critical chain (factor
  on 22, bcwc on 23, override on 24, risk→22, branch across the real 22→24 FS tie,
  conditional plans across 24→25, focus = project finish), both chart builders lit at
  `[v4] DOCX sra`. Lesson: a crafted oracle payload must target INCOMPLETE, finish-moving
  work on the live critical chain — and a 0-move probe is believed dark only after a
  second, stronger anchor also moves nothing.
- The mutation battery's own patch script betrayed it: reshaping mutation 2 (the deferred
  upward import) was first applied with an unanchored heredoc string-replace that MISSED
  silently — the battery re-ran and reproduced the old two-failure result verbatim, which
  briefly read as "the reshape didn't help" when in fact the reshape never landed. An
  exact-match edit that fails loudly on no-match found it immediately. Lesson: the
  landed-count discipline applies to the HARNESS scripts too — patch the patcher with
  tools that refuse to no-op.
- Mutation 2's FIRST shape was itself a finding: wrapping the upward import in a NEW
  top-level def drew TWO named failures — the layering test AND the re-export guard (a
  name `sra.py` defines that `app.py` does not re-export). The contract's tests overlap
  defensively; recorded in ADR-0373 as a true positive, then reshaped in-body for the
  clean single-name proof.
- Census mechanics that paid off: constants carry `#:` doc-comment blocks the ast span
  cannot see — five regions were extended by eye before any byte moved, and the
  per-region byte-identity assert then covered comment + code together. And the closure
  again out-measured the prefix (32 names/1,756 lines vs 13/847) — ADR-0365's "the prefix
  is a finder, the closure is the definition", third confirmation.

### 2026-08-08 (d) — an oracle label that reports the machine is weather; stability observed n times is not determinism

- The mission slice's falsification run moved FOUR oracle labels where the pre-flight said
  three. The fourth was `/api/system` — payload-diffed to exactly one key, `memory.percent`
  4.6→4.7. The endpoint serves LIVE host telemetry; it had been byte-stable across three
  full renders by luck (1-dp rounding) and crossed the boundary mid-battery. A mutation in
  `mission.py` cannot change the machine's memory — the env-defect masquerade, caught by
  diffing the payload instead of believing the label. Lesson: normalize telemetry VALUES
  (keep the shape) BEFORE the first byte-identity claim, and adjudicate every unexpected
  mover by payload diff before believing a dependency exists.
- The oracle harness hung silently for 5+ minutes on its first run: its repo-root walk-up
  started from the SCRATCHPAD (outside the repo), and `Path('/').parent == Path('/')` loops
  forever. A session harness should hardcode the root; any walk-up must fail loudly at `/`.
- The good news case: the re-measured census EQUALLED the closure for the first time
  (mission 304 = one function, 0 descents, multiset 28 added / 0 removed — nothing
  narrowed). The prefix census is a fine finder when the family is one function; the
  closure check cost minutes and stays owed every slice.
- The battery's two sentinel mutations (em-dash, drilldown double-load) are the
  true-positive proof the WIDENED guards read the new module — without this slice's tuple
  edits both would have passed silently. Seventh and eighth consecutive live catches for
  the enumeration guard.
- Two in-session catches of our own standing rules, recorded as paid-for: (1) the handoff
  rotation + ADR landed while the full suite was RUNNING — trap 12 says docs included, and
  the drift guard duly failed mid-rotation inside that run (code was final pre-suite, so
  code results stand; the state-docs module was re-run green on the final tree). Sequence
  the close: docs first OR suite first, never interleaved. (2) A session-log draft wrote
  "state-docs guard 10/10" before the run existed — the module has FIVE tests; wc-decides
  caught it pre-commit. A count you have not read from a run output is a prediction, and
  predictions do not belong in the log.

### 2026-08-08 (c) — a "queued exposure class" is a census, not a list; and an anchored computation can make a truncation harmless

- ADR-0370's queue named four exposure sites; the caller-by-caller census found TEN (the
  mission export's evolution tables, the briefing's section 3.1, the brief's two pair
  questions and both whatif exports were never named). When a fix separates two meanings of
  one knob, enumerate EVERY caller of the old accessor in the same round — the named list is
  where you start, not where you stop.
- Measuring the control on every engine paid immediately: one fixture produced three
  DIFFERENT lie shapes (a fabricated HIGH deleted-task accusation, near-inverted entered/left,
  a counterfactual starved to None). The fabricated HIGH reached the Diagnostic Brief's
  HIGH-only questions — the truncation was literally authoring the tool's worst accusation.
- Two surfaces (anchored /api/evolution, /export/whatif-added) turned out
  truncation-INVARIANT: a driving-slack chain to the target only walks ancestors, and the
  ADR-0268 cone IS the ancestor set. The honest artifact for an unpinnable-but-correct move
  is an ADR paragraph saying no test CAN fail — not a vacuous test that passes either way.
- Probe-then-pin kept every assertion real: render each surface first, read the measured
  strings, then write the test. Eleven tests passed first run AND the 8-mutation matrix
  produced exactly one named failure each — first-run green is trustworthy only because the
  mutations proved the pins can fail.

### 2026-08-08 (b) — one session knob, two semantics: the population cut silently redefined the measurement; and a test whose setup can 405 tests nothing

- The Target UID means BOTH "truncate every view to my driving sub-network" (ADR-0268) and
  "measure the counterfactual on me" (`compute_change_effects(target_uid=)`). On /integrity
  both landed at once — and the truncation derives from each version's OWN logic, i.e. from the
  very network the diffed changes rewire, so the pair diff compared two different cones as the
  files: a restored link dangled into a missing predecessor (false "no effect"), cone-membership
  changes read as file changes (fabricated rows), and out-of-cone edits vanished. **Lesson:
  version-PAIR analytics must never inherit a population cut derived from the thing being
  diffed; when one session knob feeds two semantics, enumerate every page where both land and
  look for the collision.** (ADR-0370: `scope_pair` / `cpm_pair_for` / `_pair_versions`.)
- The only "target set" /integrity tests called `GET /target` — a POST-only route. The 405 was
  swallowed, the target stayed unset, and the "+21 wd" pin passed for its whole life on the
  NO-target path (the auto-target happened to be 155). The operator found in production what CI
  structurally could not see. **Lesson: a test whose setup step can fail silently is not
  testing what its name says — assert the setup took** (the repaired tests assert the 303 /
  the rendered banner).
- Keying the new pair epoch as the TARGET-LESS scope signature made the fix ~free: with no
  target set the pair cache IS the ordinary cache (byte-identical keys), and setting a target
  re-serves the resident full-network solves. **Design a new cache epoch as a projection of the
  existing one before minting a second cache.**
- The M2 mutation script asserted its expected needle counts, found (2,2) instead of the
  predicted (3,3), and refused to write — the following "10 passed" run was correctly discarded
  as unmutated-tree noise. **Put the landed-count assert INSIDE the mutation script, before the
  write** — it converts "verify the mutation landed" from a discipline into a mechanism.
- `_parse_uid` maps 0 → "clear focus", so the project-summary row (UID 0) cannot be set as the
  target via the form — a test wanting "summary as target" must derive a real ≥ 1 summary UID
  from the fixture.
- With playwright freshly installed, five browser tests failed that NO CI job runs — and all
  five **reproduced identically on a pristine origin/main worktree** (pip -e re-pointed there
  and back), while the float-tip flake passed there. **A pristine-tree control is the cheap,
  decisive adjudicator for "my diff or the environment?" — one worktree, two pip -e flips.**

### 2026-08-08 — a revert that changes nothing "passes"; a dedupe makes a stale-memo test wrong; exactly-half rounds to even

- Proving the ADR-0369 qa guard able to fail, the mutation script spliced with
  `s.index("    return tuple(facts)")` — which matched the FIRST occurrence in the file (an
  earlier function), so the "reverted" block was inserted upstream and the file went on to
  RE-DECLARE the still-guarded function below the cut. Python's later `def` wins at import:
  the revert changed nothing, the test stayed green, and only the prove-able-to-fail rule
  ("if the revert did not move the output, your revert was wrong") caught it. Lesson: anchor
  splice targets uniquely (`s.index(needle, after_pos)`) and grep the mutated PROPERTY into
  evidence before trusting any revert run.
- The first ADR-0368 memo-invalidation test re-uploaded the same golden bytes and expected a
  rebuild — but ADR-0259's hash-first dedupe leaves the session untouched on byte-identical
  uploads, so the identity-keyed memo legitimately survived. The failing test was RIGHT and
  the expectation wrong. Lesson: an invalidation test must change the bytes, and the dedupe
  path deserves its own twin assertion (memo SURVIVES an identical re-upload).
- Audit F1's sharpest tooth: `round(240/480)` is 0 — Python rounds exact halves to even, so a
  true half-day counterfactual effect rendered "no effect". When pinning legacy rounding,
  pin the half-day case BY NAME (240→0, 241→1) or the worst case stays invisible forever.
- Audit F5 resolved as DOC-fix, not code-fix: the AFT's own PrimaryFilter settled in one read
  what looked like a code/doc contradiction ("check whether the reference tool wrote it
  down" pays again), and the alternative hypothesis died as 4 NAMED pin failures — recorded
  as measured-false so nobody re-chases it.

### 2026-08-07 (cont.4) — MS Project un-edits your fixture; the read-only audit's verdicts; a prediction that fails is a result

- **MS Project XML import DERIVES Duration from stored dates.** The operator converted the
  six FX single-variable MSPDI fixtures to `.mpp` per the fixture protocol — and the two
  duration-cut fixtures (FX-03 UID17 15d→5d, FX-04 UID131 4w→1w) came back with their
  edits silently REVERTED: the authored XMLs carried the new Duration but the old stored
  Start/Finish, and MS Project resolved the conflict dates-first. Baseline edits and the
  logic drop survived. Their Fuse exports therefore oracle the UNCHANGED schedules.
  **Lesson: a duration-only fixture must ship recalc-consistent stored dates, and every
  .mpp conversion must be diffed against its source before its exports are trusted as an
  oracle** (`diff_versions` on the round-trip is the two-minute check that found this).
- **The fixtures answered their pre-registered questions anyway** — the Fuse side from the
  surviving four, the SMAT side from the authored XMLs directly: Fuse `Days Late`
  EXCLUDES milestones (FX-01: 8 unchanged) and CLAMPS at zero (FX-02: 4, not −2); two
  dropped links open THREE logic ends (FX-05: Missing Logic +3, not the predicted +1 —
  SMAT matches Fuse UID-exactly); the Schedule Integrity engine PASSES its first true
  positive controls (+10 wd / +15 wd exact); the FX-06 baseline-shift trap PASSES
  (finish frozen, HIGH DECM-29I401a finding) though the finding omits the magnitude.
  Two author predictions failed and both failures taught more than the passes.
- **The adversarial read-only audit (evidence outside the repo) landed four correctness
  P0/P1s**: sub-day counterfactual deltas render "no effect" (banker's `round()` even
  drops an exactly-half-day effect; no fractional-day test existed); the parity
  population filter `_baselined` excludes ALL milestones while CLAUDE.md says
  "milestones kept" (Fuse counts the TP4 milestone — parity 0 vs Fuse 1, ordinary mode
  matches); `/briefing` re-runs 4 CPM solves + a duplicate audit on EVERY request; and
  the old "UniversalProjectReader rejects .mpp" story is REFUTED (28/28 read; the real
  culprit was the broken host Java loader). **Lesson: an environment defect can
  masquerade as a product defect for weeks — re-run the exact repro on a known-good
  runtime before believing any importer allegation.**
- **Delegated reader agents died 5-of-8 and 3-of-5 on retry** in this session's fabric;
  the lead's inline verification with executable probes carried the audit. Lesson: the
  recon-then-lead-reverify pattern also needs a *liveness* fallback — never let a dead
  delegate silently become a coverage gap; enumerate what each dead reader owed and
  re-cover it inline before closing.

### 2026-08-07 (cont.3) — A non-zero pytest exit is not a failing test; and the census prefix can claim a member the closure disowns

- Slice 7's guard mutations 4–5 first ran against GUESSED test ids
  (`test_no_double_escaped_mdash…`, `test_drilldown_js_loaded_exactly_once` — neither
  exists). pytest exited non-zero having collected NOTHING, and an exit-code check read
  that as "RED — guard caught it". The harness's ran-signature assertion (the failure
  summary must NAME the test) exposed the lie; the re-run against the real ids
  (`test_no_mdash_entity_sentinel_values_remain_in_app_source`,
  `test_drilldown_runtime_is_loaded_globally_not_per_page`) produced genuine `1 failed`
  reds and green-after-restore. **Lesson: a mutation is "caught" only when the failure
  summary names the test that ran — assert `1 failed`, never just a non-zero exit.** This
  is the flattering-falsification class (ADR-0351's substring anchor, slice 6's restart)
  in a third costume.
- The stale "ssi 335" census was `_ssi_panel` + `_ssi_data` by PREFIX — and the
  behaviour-seeded closure put the panel (the family's flagship, 235 of the 335 lines)
  OUT of the family entirely: its sole referrer is `_sra_body`, so it is /sra page family.
  **Lesson: the prefix is a finder, the closure is the definition — and the divergence can
  be the family's biggest member, not an edge case.** The sra census "264" is now known to
  be ~700+ in truth; re-measure before believing any queued number.
- The oracle's launch token is `{hex16}.{wipe_gen}`; a hex-only normalizer regex silently
  normalized NOTHING and 48 of 96 labels flapped between processes. The two-process
  determinism gate caught it before any probe number was quoted — which is exactly why
  that gate runs first. **Lesson: prove the oracle deterministic across PROCESSES (not
  runs in one interpreter) before quoting any diff from it.**
- The seeded Monte-Carlo (`SRAConfig.seed=12345`, per-iteration `Random(seed+i)`) makes
  `/api/sra/ssi` byte-stable — a simulation endpoint CAN sit in a byte-identity oracle
  when the engine is deterministic by design (Law 2 / ADR-0005 paying off in test
  infrastructure, not just in parity).

### 2026-08-07 (cont.2) — A timeout-backgrounded Bash call RESTARTS its command; never let a mutate-restore harness ride one

- The trend slice's falsification harness (mutate trend.py → snapshot → restore, two cases)
  ran as one foreground Bash call that hit the 300s timeout and was "moved to the
  background". The move is a RESTART: the whole command ran again from the top, so for a
  window two instances were mutating and restoring the same files. Caught because the
  probe discipline demands md5/anchor checks at every step: the `.cut` backups were
  anchor-grep-verified clean (`trendCharts` ×1, mutated form ×0) before anything was
  trusted, strays killed, and both cases re-run serially as short self-contained calls.
- Lesson (now in the handoff): each mutate→snapshot→restore cycle gets its OWN short call,
  never a long compound one that can be timeout-backgrounded mid-mutation. Corollary: after
  ANY interrupted mutation harness, verify the backup's cleanliness by anchor, not by
  trusting the choreography.
- Same slice, the sweep's first REAL candidate: `test_manifest_projection_memo` patches
  `app_mod.non_summary`, which trend.py now also binds. Cleared by verification — the spied
  path (/api/dashboard projection memo) never crosses a moved member and app.py still binds
  the name. A sweep hit is a candidate, not a verdict; verification decides, both ways.
- And the re-read rule caught its second number this session: trend.py "482 lines" was the
  pre-I001-fix count; wc on the settled file says 483.

### 2026-08-07 (cont.) — A coverage gap can be an ORACLE gap: widen the oracle before calling it unreachable

- The margin slice's pre-flight probe (ADR-0363) initially showed `_wmpd_label` at 0 routes
  moved — the same shape ADR-0351/0352 recorded as "no fixture can render this member." But the
  member's OTHER consumer was `/export/{fmt}/margin`, which the oracle simply never rendered
  (parametrized `{fmt}` routes were skipped wholesale). Instantiating `/export/xlsx/margin` +
  `/export/docx/margin` — and double-render-proving the workbook bytes deterministic first —
  took the member from 0 to 2. Likewise `_band_payload` probes as unreachable until the harness
  POSTs `/margin/band`: its first line returns None without stored phase dates.
- Lesson: before recording a member as render-unreachable, ask what would EXECUTE it — an
  export, a POST-lit branch, a query param — and widen the oracle to include that path. "0
  moved" is a claim about the oracle as much as about the member. The exports proved
  deterministic, so they stay in the harness for future slices.
- Same session, the re-read rule caught a real number drift: the draft ADR said app.py →
  17,688 (a mid-session print, pre-`ruff --fix`); wc on the settled tree says 17,681. A number
  written mid-session is not a measurement.
- And trap #4 fired in mild form: the full suite was launched, THEN the ADR file was written —
  but `test_state_docs` reads the docs mid-suite, so the suite was stopped, the tree settled
  (docs + wheel + installers), and the suite relaunched. Docs are part of the tree.

### 2026-08-07 — A synthetic fixture that "fails" a metric is usually describing itself

- Battery phase 2 (ADR-0362): before pinning anything, a probe measured all seven queued
  families on the phase-1 clean program — and two families "failed" it. Acumen Missing Logic
  has a structural 2/N floor (the first task and the terminal milestone are ALWAYS open ends
  → 8% on N=25 vs the 5% bar), and Insufficient Detail divides by the STORED-finish span,
  which is 1 day on a fixture carrying no stored dates (everything flags at once).
- Neither was an engine defect and neither was "fixed": the fixture was enriched instead
  (`_dated` adds stored dates + WBS exactly as every real import carries; `_wide` takes the
  population to 41 so the structural floor is 4.9%). The lesson generalizes: when a
  hand-built fixture trips a population-floor or denominator-derived metric, first ask what
  the METRIC divides by that the fixture doesn't carry — enrich the fixture, never weaken
  the metric, and never file the engine bug before that question is answered.
- Measurement handed over two semantic edges worth pinning permanently: work that NEVER
  STARTS fails SPI and SPI(t) at 0.5 while SPI(t)-Acumen stays PASSING at 1.44 (its average
  only sees started work — ADR-0176's population, now a pinned discriminator), and a
  late-vs-baseline start fails Started Late while Baseline Start Compliance holds 100%
  (Half-Step numerator compares to the baseline FINISH — ADR-0083's asymmetry, now pinned).
- Upgrade over phase 1: the EVM and readiness pairs assert flip-set EQUALITY (moved ==
  declared), not just no-undeclared — an expected flip that fails to happen now fails the
  battery too. Eight targeted engine mutations each went red on exactly their family's pair;
  every module restored byte-identical from scratchpad copies.
- Operational: the full suite now exceeds a 10-minute foreground timeout in this container —
  run it `python -u` in the background and read the tail; a foreground kill (exit 143) is
  the harness's timeout, not a hang.

### 2026-08-06 (cont.5) — The reference tool's own export is the semantics decoder

- **ADR-0359.** Two sessions of SRA-delta work (0356, 0359) both ended at the same doorstep:
  the DETERMINISTIC rows of the reference tool's own export. SSI's Sensitivity sheet said in
  two numbers (321−304.48 = the ML exactly, twice) what no amount of distribution-fitting
  could: fired impact REPLACES the duration. Distribution comparisons localize; deterministic
  comparisons ADJUDICATE. Get the reference tool to emit something deterministic and diff that
  first.
- **A latency cliff reads as a dead control.** "Export does nothing" was a fully-wired button
  ahead of a measured 139.8-s synchronous model re-run. Before hunting broken wiring, TIME the
  handler on the operator-scale artifact. And the first regex sweep "found" 45 dead buttons
  that a real parser showed were its own window artifacts — the anchor-vs-function trap now
  has a UI-sweep variant.
- **The battery's failures were the product.** Nine of fourteen seeded defects did not flag on
  the first try, and every one was a WRONG ASSUMPTION about the check, not a broken check
  (DCMA08 reads the baseline duration; the CP test survives every pure-logic mutation and only
  a mid-chain self-MFO defeats it). A pass/fail pair per metric is a specification test of the
  test-writer as much as of the engine — with declared collateral, it catches over-broad seeds
  and over-eager checks symmetrically.
- **Export must equal screen.** The old export re-ran the model at a hardcoded 2000 iterations
  — a DIFFERENT number than the page showed, silently. Reuse-not-recompute fixed latency and a
  fidelity hole at once.

### 2026-08-06 (cont.4) — Put the trap check IN the tooling, and the tooling catches you

- The span-scoped coverage probe was written fresh this session with ADR-0351's rule baked in
  as an assert: after mutating, the ORIGINAL anchor must be absent from the re-read span.
  The very first header probe then used `page-takeaway` → `page-takeaway`**`Q`** — a suffixed
  replacement, the exact substring shape ADR-0351 documented — and the harness refused to
  render it. Same-length non-superstring (`page-tekeaway`) worked. **A trap rule that lives
  only in a checklist fires only when someone re-reads the checklist; a rule compiled into the
  harness fires every time.**
- An EMPTY sweep result is only evidence when the sweep harness has been shown able to find
  things. This slice's three standing sweeps (monkeypatch targets, source-text readers,
  attribute reads) all came back empty — trustworthy because the same harness shapes found
  driving's 3 and evolution's 4+2 last time, and because mutation 1 (dropped re-export)
  proved the contract half still fails loudly on this very cut.
- The render diff's value is decided by the pre-flight probe, per family: driving 0/60,
  evolution most-but-not-all, integrity 6/79 for BOTH members. Running ADR-0352's probe before
  the cut is what let 79/79 be quoted as proof rather than vacuous green.
- A five-version fixture load (TP4_DataCenter v1..v5 as ONE project) turned out to be the only
  way any current fixture renders /integrity's n>2 picker and both non-empty verdict bands —
  worth keeping in the render harness as Oracle B alongside the golden pair.

### 2026-08-06 (cont.3) — A parity delta is a claim about INPUTS before it is a claim about engines
- **ADR-0356.** "Same data in both tools" was the premise and the defect: the tool's session
  held a setup captured against an earlier schedule vintage (605/783 factors stale), while SSI
  read the file. The engine reproduced SSI to σ 2.5% the moment inputs were file-true. Lesson:
  before decomposing algorithms, DIFF THE INPUTS — cheapest experiment, biggest prior.
- **The product owns input provenance.** The app had no way to read the schedule's own stored
  SRA fields (only the parity TEST did), so stale replay was inevitable and silent. A tool used
  in testimony must either read the file's inputs itself or loudly say whose inputs it ran.
- **The self-agreeing oracle:** a pin that re-calls the function under test agrees with any
  mutation of it. Pin independent properties (shape + sensitivity), never round-trips through
  the same code. Fourth discriminator-class catch in one day — promoted candidate for Part V.
- **The unweighted-summary-cell trap held again** (Mean Date 95 d off the weighted mean).
  July's rule survives contact: parity targets come from the occurrence-weighted histogram.

### 2026-08-06 (cont.2) — A fail-closed claim is only as true as the operators you tested
- **C4 (ADR-0355).** ADR-0354 claimed unknown duration units "fail closed" and pinned it —
  with a GREATER_THAN filter, the one direction where a None RHS happens to not match. The
  same None under < or != matched EVERY task. A reviewer bot caught what the pin's operator
  choice hid. Lesson: a fail-closed claim must be pinned across the OPERATOR SPACE, not one
  comparator; and None is a VALUE in this evaluator (EQUALS <null>), so "no result" needs its
  own sentinel, never None.
- **The bytecode read was right and the implementation still missed it (C1).** ADR-0354's own
  text said the conversion context is ProjectProperties; the code then threaded the calendar's
  derived day length. Writing the finding down is not the same as implementing it — re-read
  your own ADR against your own diff before shipping.
- **model_copy(update=...) skips validation (C3)** — pydantic's documented behavior; any
  sanitizing must happen before the copy, or construct instead of copying.
- **Third discriminator failure in one day.** Suite-scale (0353), calendar-scale (0354),
  population-scale (0355). The mutation protocol caught all three; none was caught by writing
  the test. The test proves nothing until its mutation fails.

### 2026-08-06 (cont.) — The reference tool's bytecode beats every secondhand account of it
- **V3 (ADR-0354).** Three prior documents described the elapsed-literal defect; none could say
  what conformance MEANT for week/month/year or unknown units. One javap session on the vendored
  mpxj jar settled all of it — and exposed two more defects (year = mpw x 52, week = the file's
  MinutesPerWeek) that no amount of re-reading the audits would have found, plus a genuine MPXJ
  quirk (%/e% pass through unscaled) that intuition would have "fixed" into a parity break.
  Lesson: when the repo VENDORS the reference implementation, its bytecode is the cheapest
  oracle available — read it before designing, not after disagreeing.
- **The identity-case trap fired twice in one day, at two scales.** ADR-0353: a whole suite of
  unprogressed fixtures made two duration bases coincide. ADR-0354: ONE test whose only file used
  the standard calendar made "the schedule's calendar" and "the default calendar" coincide — the
  mutation for exactly that distinction PASSED until a 1,500-minute discriminator task forced the
  two readings apart. Same question both times: do the fixtures make the two instruments equal by
  construction?
- **An introspection guard found the half I forgot.** The Save-writer coverage test
  (every model field must be emitted) failed the moment Calendar gained two fields — the writer
  I had searched for under the wrong names and concluded "doesn't exist". A guard that enumerates
  the contract beats a contributor's grep vocabulary.

### 2026-08-06 — A defect can be invisible to a whole suite because every fixture is the identity case
- **SRA-LEGACY (ADR-0353).** The legacy SRA's anchor was the full-duration CPM finish bisected
  against a remaining-basis distribution. Every synthetic in `test_sra.py` is unprogressed —
  remaining ≡ duration — so the two bases coincide and 30+ green tests never touched the defect.
  The fix's own equivalence pin passes byte-identically on those fixtures; only a NEW progressed,
  resume-less fixture (the EVM1 class) could fail it. Lesson: when a defect is "X and Y disagree",
  check whether the suite's fixtures make X ≡ Y by construction — a green suite over identity
  cases is a vacuous gate (the blind-spot-fixture rule, ADR-0136, in a new costume).
- **Measure both sides before designing.** Running the four goldens first showed leg A's blast
  radius was exactly the resume-less class (det_pct unchanged to 4 dp on the other three) — which
  turned "will this break parity?" from a fear into a prediction that then held.
- **`grep -c` exits 1 on a zero count.** An `&&`-chained "assert-absent then run test" mutation
  step silently stopped at the grep; the test never ran. Chain verification greps with `;`, or
  the protocol's absence check eats the run it guards.
- **A repo-wide sed for a 3-token unpack line hit three routes.** Two still used the variable →
  F821 at import time. Same-shape lines recur in a 18k-line module; line-targeted sed only.

### 2026-08-05 (cont.4) — A coverage probe can measure the anchor instead of the function (ADR-0352)
- **The probe that flattered itself.** To find out which members of the evolution family the
  render oracle actually exercises, I mutated each one's markup and re-rendered.
  `_render_counterfactual` "moved 24 routes" — it looked thoroughly covered. It was not: the
  anchor I picked was `class=sf-take`, a **generic** class used across the whole UI, and
  `str.replace()` changed it **file-wide**. I had measured the anchor's blast radius, not the
  function's. Scoped to the member's own AST line span, the same function moves **0**.
  **A mutation must be confined to the thing you are making a claim about** — otherwise the
  result is real, reproducible, and about something else.
- **Run the coverage probe BEFORE the cut, not after.** ADR-0351 learned that a render diff can
  be vacuous; this slice checked *first* whether each member was renderable at all, and got a
  per-member map instead of a single reassuring 66/66. Two members (286 lines) came back
  uncovered — so the ADR, the handoff and the PR say which parts the diff speaks for and which
  parts rest on per-definition byte-identity. **The point of the check is not to pass it; it is
  to know which of your evidence is load-bearing.**
- **A widened sweep proved its worth one slice later.** ADR-0351 widened the monkeypatch sweep
  from "names the new module imports" to "every name the new module BINDS". This slice's silent
  case — `appmod.compute_path_evolution`, still bound in `app.py` for its own callers, so the
  patch succeeds and does nothing once the callee moves — is exactly the shape the narrow version
  missed last time. **The test that proves the fix is the revert:** changing `evomod` back to
  `appmod` turns the test red, which is the difference between "my fix works" and "it passes
  anyway".
- **The full suite found it AGAIN, and the count is now four.** Two more sites of the same read
  coupling live in `tests/perf/test_perf_regression.py`. Every fast check passed them; only the
  20-minute run does not. That is the second time in two slices the full suite caught a class of
  defect nothing cheaper can see — the pattern is now reliable enough to plan around rather than
  be surprised by.
- **A monkeypatch is not the only way a test binds to a module.** `test_session_consistency` did
  `real = app_module.compute_cpm` purely to *capture* the real callable, then patched
  `state_module`. `ruff --fix` removed `compute_cpm` from `app.py` when its last consumer moved,
  and the **read** broke. Reads are couplings too — sweep for attribute access on a module, not
  just `setattr`.
- **The prefix finds a family; the closure defines it.** Seeding `_evolution_*` alone left two
  helpers being pulled by functions that would have stayed behind. Naming conventions are a
  search hint, never the membership test — same lesson as ADR-0349's "adjacency is not cohesion",
  one level up: *nomenclature is not cohesion either.*

### 2026-08-05 (cont.3) — An oracle can be deterministic, sensitive-looking, and still prove nothing (ADR-0351)
- **60/60 byte-identical, and it was worth exactly zero.** The render diff said every route was
  unchanged after moving the driving-path family. Then the mandatory falsification: one character
  changed inside a moved function moved **0 of 60** hashes. Reloading with the Project2/Project5
  golden pair (63 routes) — still **0 of 63**. `tests/web/test_page_memory.py` already said why:
  the corridor panel "only renders when a real driving corridor exists across versions (**which
  the golden pair doesn't produce**)". The oracle was deterministic, it had a clean null result,
  and it had *just* been proved sensitive on the previous cut — none of which makes it sensitive
  to **this** code. **Sensitivity is a property of the oracle AND the change, never of the oracle
  alone.** Re-falsify per cut, against the code that actually moved.
- **The honest fallback is narrower, and should be stated as such.** What replaced it:
  per-definition AST byte-identity against the pre-move source, **9/9 identical**. That is a real
  measurement and it is *weaker* than a behavioural diff — so the ADR, the handoff and the PR all
  say which functions have no test coverage (`_driving_tiers_panel`, `_driving_tier_trend`,
  `_task_name_across`, `_EVO_TIER_LABEL`) rather than letting "60/60" imply cover it never had.
  A named gap ("a fixture that produces a real driving corridor") is worth more than a confident
  number that means nothing.
- **A re-export makes the monkeypatch trap SILENT again.** ADR-0297's trap was a patch that no
  longer intercepts. The nastier variant: `_driving_path_gantt` and `_corridor_chips` are still
  re-exported by `app.py`, so `monkeypatch.setattr(appmod, …)` **succeeds** — while the caller,
  now in `driving.py`, resolves them through its own namespace. No `AttributeError`, no failure,
  the test just quietly asserts against the real renderers. Only its sibling patch
  (`compute_driving_path_evolution`, which app.py no longer binds at all) failed loudly and
  dragged the other two into the light. **The re-export that keeps callers working is exactly
  what keeps the patch from erroring.**
- **My first sweep for that had a hole, and the hole was a category error.** It compared patch
  targets against the names `driving.py` *imports*. `_driving_path_gantt` and `_corridor_chips`
  are names it *defines*. The sweep has to cover **every name the new module BINDS** — imported,
  defined, or assigned — because binding is what shadows the patch.
- **Two source-text guards, two opposite correct directions, same commit.** `test_page_memory`'s
  `dpFind` check **FOLLOWS** its subject into `driving.py` (its claim is about the driving-path
  markup). The whole-view-layer guards **WIDEN** to include `driving.py` (their claim is "nowhere
  in the view layer"). Pointing either the other way looks equally reasonable and is wrong: the
  question is always what the guard is a claim *about*, never where the code went.
- **A falsification can itself be wrong in the direction that flatters you — twice in one unit.**
  Both read exactly like "this guard cannot fail", and both were my mutation, not the guard:
  (1) removing `dpFind` from `driving.py` replaced only the **first** of **two** occurrences;
  (2) `id=dpFind` → `id=dpFindZ` replaced all of them and the guard *still* passed, because the
  assertion is `"id=dpFind" in src` and the original anchor is a **substring of the
  replacement**. A suffix does not delete a substring. The working mutation was a same-length
  non-superstring (`id=dpQind`). **The rule that covers both: after mutating, assert the ORIGINAL
  anchor is ABSENT from the re-read file.** "I changed the file" is not "I removed the thing the
  assertion looks for" — and the gap between those two is exactly where a false negative lives.
- **A source-text guard can reach its file through the module OBJECT, and then no grep finds it.**
  `test_gantt_find_coverage` reads `Path(app_module.__file__)`, not a literal `"app.py"`. The
  standing sweep — `grep -rln 'app\.py' tests/` — could never have listed it. It survived the
  pre-cut sweep, three sibling repointings, ruff, mypy and every targeted run, and was caught
  **only by the full 20-minute suite**. Two consequences: the sweep must also cover
  `__file__)\.read_text` and `inspect.getsource`; and **the fast checks do not substitute for the
  full suite on a refactor that moves code between modules** — the failure mode here is invisible
  to every cheaper check by construction.
- **The guard I wrote last unit paid off on its first real outing.** Adding `driving.py` to
  `VIEW_MODULES` immediately failed `test_whole_view_layer_guards_actually_read_the_whole_view_layer`
  and named both files to widen. Pinning the enumeration converted a thing-to-remember into a
  thing-that-fails — which is the only version that survives contact with the next session.

### 2026-08-05 (cont.2) — The queued plan was wrong, and only the dependency graph could say so (ADR-0350)
- **A line census is not a dependency measurement, and the plan was built on the wrong one.**
  Phase 3 was queued as "slice by page family, largest first" — `driving` (585 lines) first. The
  AST closure said otherwise: `driving` drags **`_panel_head` (reached by 47 families, 62 direct
  referrers)** and **`_shell_tools` (41/52)**. Cutting a page first would have moved the shared
  panel strip *into a page module*, leaving ~60 unrelated helpers importing their panel header
  from `web/driving.py` — an inversion every one of the remaining thirteen slices inherits or
  duplicates. The queued order was not merely suboptimal; it was the single order that poisons
  the rest. **Run the closure before you trust the plan, including a plan you wrote yourself.**
- **When a shared layer exists, extract IT first — the threshold is a real decision.** A symbol
  reached by ≥2 families is *shared*; by ≥3 is *infrastructure*. Both sets were closed, but the
  2-family band turned out to be **page-PAIR machinery**, not primitives: `_conditional_section`,
  `_unified_risk_section`, `_branch_section` and the `_OCC_*` constants are all "sra, ssi" and
  every one has **`_ssi_panel` as its only direct referrer**; `_render_counterfactual` (179 lines)
  reaches two families through `_counterfactual_panel` alone. A components module holding a
  179-line counterfactual renderer is not a components module. The `#families` number alone would
  have shipped it — reading the *referrers* is what separated the two bands.
- **The trap repeated in a form the previous fix did not cover.** ADR-0349 taught "a guard whose
  subject moves keeps passing over a file that no longer holds it". Phase 3's variant is the
  mirror: **the subject stayed put and the view layer grew a module the guard does not read.**
  `test_presentation_fixes`'s `&mdash;` guard read `app.py` + `chrome.py`; `_stat_cards` — the
  function the very next test exercises for that exact double-escape — moved to `components.py`.
  Green, over a shrunken subject. The durable fix is not to repoint again but to **pin the
  enumeration**: `VIEW_MODULES`/`LAYER_ORDER` are now constants a contract test checks, so phase 4
  cannot add a module without the guards going red. Repointing fixes one cut; pinning fixes all of
  them.
- **An oracle you have not run twice is not deterministic — it is merely untested.** Two runs of
  the *unchanged* tree disagreed on **34 of 61** routes. Cause: a per-process launch token plus
  the pid, constant *within* one interpreter — which is precisely why ADR-0349's method said "in
  the SAME interpreter", a phrase I would have read as incidental had I not tripped over it. Had I
  skipped the stability check I would have "discovered" that a verbatim refactor changed 34 pages
  and spent the session chasing a nonce. **Establish the null result before you measure the
  effect**: run the oracle against no change at all, and only then trust 60/60.
- **Falsify the oracle in the direction of its blind spot, not just its sensitivity.** One
  character in `_panel_head` moved 20 of 60 hashes — but 40 held, which is the number that could
  hide a gap. Checking them directly (zero `class=panel-head` in their rendered HTML, with
  `/margin`'s 4 as a positive control) is what turned "40 unchanged" from a worry into a result.
  The first version of this oracle also omitted `/analysis/{name}`, `/card/{name}` and
  `/wbs/{name}` — the three parametrized pages where this kernel is used *most*. A page-list
  oracle that skips the parametrized pages is a coverage hole shaped exactly like the change.

### 2026-08-05 (cont.) — A measurement taken before the tree settles is a measurement of nothing
- **The suite half: I invalidated three ~20-minute runs by working during them.** A full-suite run
  measures the tree *at one moment*. While pytest was running I bumped the version, rebuilt the
  wheel and the nine installers, and added a comment — so each run was reporting on a tree that no
  longer existed by the time it finished. Three runs, ~60 minutes, all of it unusable; the suite
  then had to be re-run clean against a settled tree. The lockstep test caught the post-build
  comment edit and **was right to**. A green result is only evidence about the bytes that were on
  disk when the collector read them.
- **The docs half: the same error, in a number I published.** ADR-0349, `HANDOFF.md` and
  `SESSION-LOG.md` all stated `app.py` went `21,348 → **20,255**`. The merged file is **20,192**
  (`git show f6959d1:src/schedule_forensics/web/app.py | wc -l`). 20,255 was printed by the
  extraction script *before* `ruff check --fix` removed the six now-unused imports and `ruff
  format` collapsed the blank-line runs the cut created. The real reduction is **1,156** lines, not
  1,093. Nothing was wrong with the refactor — only with **when** I read the tape. Corrected in all
  three files.
- **The discipline, and it is four steps.** Settle the tree → `md5sum` what you touched → run →
  **re-verify the md5s afterwards** to prove the tree held for the whole run. Step four is the one
  that converts "I think I didn't edit anything" into evidence, and it is the one I skipped. For a
  published figure the same rule reads: take the number from the *committed* artifact, not from the
  tool that produced it, because the formatters run in between.
- **Why this is ADR-0348's own lesson pointed inward.** That ADR's finding was that a stated number
  must be a measurement rather than a recollection. The failure mode one step further in is a
  number that *was* measured — honestly, with a real command — but against a tree that had already
  moved. Same standard, later clock. This repo's rule is that a stated number is a measurement;
  the corollary is that a measurement carries the timestamp of the tree it was taken from.

### 2026-08-05 — Splitting a module silently narrows every test that names the file (ADR-0349)
- **The lesson.** Moving code out of a file cannot break a `read_text()` guard's *syntax* — only
  its *subject*. `tests/web/test_bar_drill.py` asserts
  `app_src.count('<script src="/static/drilldown.js"></script>') == 1` to catch a double-load.
  After `_LAYOUT` moved to `chrome.py` that count went from **one** to **zero**, and
  `test_presentation_fixes`'s `assert '"&mdash;"' not in src` would have gone on passing over a
  file that no longer contains the code it guards. Both stay green. **A guard that has stopped
  guarding still reports success** — the same failure shape as ADR-0297's silent monkeypatch,
  arriving through a different door. Before the next cut, list the tests that name the FILE, not
  just the callers that import from it: `grep -rln 'app\.py' tests/`.
- **Repoint in the right direction, and the two directions differ.** A guard on the layout's
  *internal script order* follows `_LAYOUT` (order is only meaningful inside one module). A guard
  meaning *"nowhere in the view layer"* must read **both** modules. `test_bar_drill` was first
  repointed the wrong way — to `chrome.py` alone — which would have kept it green while re-opening
  the exact double-load hole it exists to catch, since a stray re-include would land in `app.py`.
  Caught and corrected mid-change. Ask what the guard is a claim *about*, not where its subject
  currently lives.
- **Compute the seam; do not choose it.** An AST transitive closure of `_page` over `app.py`'s 344
  top-level symbols returned **30 names and was closed** — proof that nothing moved would call
  something left behind. It also *found* members no reading would have grouped together (`_e`,
  473 call sites; `_criteria_text` from 18k lines away) and *excluded* one that sat physically
  inside the block (`_TS_CAPTION_MARK`, a page-body constant between `_story_footer` and `_page`).
  **Adjacency is not cohesion.** The closure is cheap to compute and it is the difference between
  a defensible cut and a plausible one.
- **For a verbatim refactor, render-and-diff beats every other oracle.** All 31 HTML routes
  rendered before and after *in the same interpreter* (pre-split `app.py` swapped back in,
  `chrome.py` parked): **31/31 byte-identical SHA-256**. Then the oracle was itself falsified —
  one character changed in `_LAYOUT` moved **30 of 31** hashes, the 31st being a 404 that renders
  no layout, which is the right answer and explains itself. An identical response cannot render
  differently, so this dominates a browser pass here. Reuse it for phase 3.
- **The mutation worth keeping is the one that imports cleanly.** A module-level
  `from …web.app import X` inside `chrome.py` detonates on its own with a circular-import error —
  it needs no guard. The **deferred** form, inside a function body, is how someone would *work
  around* the cycle: it imports fine, runs fine, and quietly makes the cut circular. That is the
  case the AST guard earns its place on, and the mutation that proves it.
### 2026-08-05 — A guard that names a destination does not check that anything arrived
- **The handoff rotation is two moves, and only one of them is tested.** ADR-0246 says: REPLACE the
  live section in `HANDOFF.md` *and* MOVE the outgoing one to the top of `HANDOFF-ARCHIVE.md`.
  Resolving #528's conflict did the first and skipped the second, so `2026-08-03c` (#527, ADR-0344)
  vanished from **both** docs. It stayed missing through five subsequent merges (`2262e6d` →
  `e9a48c9`) while every rotation in between was performed correctly — a silent, one-time loss that
  nothing downstream re-detects. Restored verbatim from `d57e230`.
- **Why all five state-docs guards passed on it.** They check the *source* side only: `HANDOFF.md`
  ≤64 KB, exactly one `# (prior)` heading, latest ADR present in HANDOFF + SESSION-LOG, ADR numbers
  unique. Every one of those is satisfied by a section that was deleted rather than moved.
  `HANDOFF-ARCHIVE.md` appears in `tests/test_state_docs.py` **only** in a docstring and two
  assertion *failure strings* — prose that tells you where to put the section, with no assertion
  that ever opens the file. Naming a destination in an error message is not coverage of it.
- **Two obvious guards are dead ends — recorded so the next attempt skips them.** (1) *ADR-number
  contiguity across handoff headings*: measured, not assumed — 179 archived sections name only 58
  distinct ADRs, with ~170 legitimate gaps (most sessions never numbered their heading). The guard
  would fire on almost everything. (2) *Compare the live section against the previous commit's*:
  defeated by CI's shallow `fetch-depth: 1` checkout. A real guard needs a different invariant;
  the gap is left open deliberately rather than filled with a flaky or false-positive test.
- **A recovery plan goes stale faster than the defect does.** The plan written on 08-03 said
  "prepend after the archive's 4-line header" — correct that day, wrong by 08-05, when three newer
  sections (`08-03d`, `08-03f`, `08-03g`) had been archived ahead of it and the correct slot had
  moved to *between* `08-03d` and `08-03b`. Re-derive an insertion point from the file at the
  moment you act; a stored line number is a guess about a file you have not read yet.
- **Near-miss worth naming:** `2026-08-03e` looked like a second dropped section. It is a
  LESSONS-LEARNED entry label, never a handoff heading (`git log -S` located it in this file, not
  in `HANDOFF.md`). Checking cost one command; assuming would have "restored" a section that never
  existed.

### 2026-08-04 — A finding is a hypothesis with a citation, not a measurement (ADR-0348)
- **Re-derive the numbers in a finding's own headline before you act on it.** CC-01 was filed as
  "non-working dates at **74 call sites**". Neither number survived. `74` was
  `grep -rn ... src/ | wc -l` (**75**) minus the one `def` — a count of *mentions*, imports and
  docstrings included; the AST count of real invocations is **53**. The named mechanism
  (non-working landings) was already closed by ADR-0312 and is **unreachable** on all 14 committed
  schedules. Acting on the finding as written would have produced a fix for a defect that was not
  there, and left the one that was.
- **The defect a finding cannot see is the expensive one.** Chasing the reported symptom surfaced a
  much larger one the framing could not describe: a day-multiple offset names one instant with two
  spellings, and the code always picked the finish spelling — so **98.5 % of comparable Project5
  start dates** disagreed with MS Project's own, and every Gantt bar was drawn one day too wide. It
  never lands on a non-working day, so "non-working dates" could not find it.
- **Coincidental agreement is how a wrong number survives.** `_elapsed_finish_offset` was wrong for
  8 of 18 (start, duration) pairs — but *right* for every whole-1440 elapsed duration, because the
  spelling gap happens to equal the non-working gap. The cases anyone would test by hand were the
  cases that agreed.
- **Use the oracle to settle taste questions.** The naive fix — spell every start as a start —
  inverted **159 of 169** milestones (`ES == EF` → start after finish). Rather than argue the
  convention, ask the reference tool: MS Project spells an instantaneous event end-of-day (EVM1
  3/3, and 0 for the start form). The rule became one helper instead of an argument, and the
  regression never shipped.
- **A guard that fails on its first run may be right about you.** The new AST census guard fired on
  `span_start_datetime`'s own sanctioned branch. The fix was to scope it to *consumers* by name —
  not to relax the pattern, and not to delete the case.

### 2026-08-03h — The obvious implementation of a guard is where the false positive lives (ADR-0347)
- **A guard's naive form is the dangerous one.** Hardening the CUI hook to catch `data.mpp.bak`
  needs the `$` anchor relaxed. The obvious relaxation — *blocked extension followed by any dot* —
  silently claims `tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar`, whose **Java package name**
  merely contains `.xml.`, and would have blocked every future MPXJ upgrade with a nonsense reason.
  It was found by sweeping the real tracked tree with the new pattern *before* trusting it, not by
  reading it. The suffix set is now **closed**, and a test fails if the clause ever widens again.
  **Generalizes: for every widened matcher, diff old-vs-new over the actual corpus.** A pattern is
  a claim about a population you have not looked at until you look.
- **Run CI's command, not your paraphrase of it.** CLAUDE.md and the `full-gate` skill both said
  `ruff check src/ tests/`; CI runs `ruff check .`. Every file under `tools/` was therefore linted
  by CI and invisible to the documented local gate — so a clean local gate meant nothing for the
  new `tools/intake_manifest.py`, and CI returned 6 errors. **A gate that is a subset of CI is not
  a gate.** When a check exists in two places, diff the invocations, not the intent: the scope
  argument is part of the command. Both docs now carry `ruff check .` verbatim. (ADR-0346 taught
  this about dependency floors — "two correct controls that never meet prove nothing"; it applies
  to the gate itself, and the only reason it surfaced here is that CI happened to be the *broader*
  of the two, which is not something to rely on.)
- **Widening one guard's blocklist can open a hole in a different subsystem — and only the FULL
  suite knows.** Adding `.p6xml`/`.xlsm` to the CUI pre-commit guard turned
  `tests/test_logging_redaction.py` red: that test pins the log redactor's `SENSITIVE_EXTENSIONS`
  to the hook's blocklist, and the redactor covered neither, so `redact("… Runway Program.p6xml")`
  returned the file name **verbatim** — a Law 1 leak into logs, created by an edit that looked
  purely additive. `tests/guards/` stayed green through every iteration of the work; the coupling
  lives in another module entirely. **Scoped runs are for the edit-debug loop; only the whole suite
  knows what a file is wired to** — and a "docs and tests only, no version bump" unit became a
  shipped change (v1.0.162, wheel + nine installers) *because* the full suite ran before the ritual
  step, not after.
- **`set -o pipefail` turns every early-exiting reader into a fail-open switch.** The new CUI
  content sniff shipped as `git show ":$p" | head -c 65536 | grep -qaE "$sig"`. It passed every
  small fixture. It was wrong: pipefail takes the last non-zero status, and a truncating reader
  SIGPIPEs its upstream, so the pipeline reports FAILURE *even when grep matched* — the guard
  allowed a **281 KB** saved schedule while blocking a 4 KB one. **A security check must never
  derive its verdict from a pipeline's aggregate status under pipefail;** put the producer in a
  process substitution so only the matcher's own exit code is the answer. And test guards at
  *realistic* input size — below the pipe buffer the producer finishes first and the bug is
  invisible. (Falsifying the fix taught a corollary: the two-stage `git show | grep -q` does NOT
  reproduce it — it wins the same race — so a mutation must restore the exact original shape, not
  a plausible-looking variant, or you prove nothing.)
- **Verify that your mutation actually mutated.** One falsification this session ran
  `python3 -c "...$signature_re..."` inside double quotes; the shell expanded the variable before
  Python saw it, the replace never matched, the file never changed, and the suite went green —
  which reads exactly like "this test cannot fail". Apply mutations by heredoc, `assert anchor in
  source`, and re-read the file to confirm the change before trusting the run. Same family as the
  already-recorded "a `-k` filter can silently deselect the very test you are targeting".
- **A test that fails on its first run is not automatically a bug in the subject.** Two of this
  session's new tests went red immediately and *both* were the test over-claiming: one asserted "no
  tracked file matches the block pattern" when the intake legitimately tracks `.docx`/`.xlsx`/`.mpp`
  under ADR-0152's `inherited_from_main` rule; the other flagged `*.mspdi.xml.gz` goldens that live
  under an allow-prefix. Reading the failure and narrowing the claim beat "fixing" the hook. The
  reflex to change the subject under test is how a correct control gets weakened.
- **Hash the committed blob, not the working tree.** `.gitattributes` sets `* text=auto`, so **128**
  intake files check out CRLF on Windows and LF on Linux. A working-tree manifest would have been
  green on CI forever (every pytest job is `ubuntu-latest`) and broken on the operator's own
  Windows machine — the platform this tool actually ships nine installers for. ADR-0346's lesson,
  one layer down: *ask not "does this pass?" but "in which configurations has it ever been asked?"*
- **A manifest that only agrees with itself proves nothing.** The intake guard deliberately splits
  into a *sync* half (re-derive the scan, compare to the doc) and a *live* half that never consults
  the doc — both `.aft` parse at 1443/1403 `<Metric>`, 20/20 `.mpp` are OLE2, 65/65 shipped statics
  match their extensions. Only the live half can answer "did the rotation reach the product?".
- **Re-derive an inherited number before building on it.** The audit's "89 mismatched files" came
  out at **99** under a stated rule; `99 − 7 − 3 = 89` reconciles it exactly (7 `.XLS` holding OOXML
  packages, 3 `.json` holding prose). And re-deriving surfaced what the audit had *missed*: the two
  copies of `Project5_TAMPERED.mpp` — ADR-0112's authoritative parity input — are the same size with
  **different bytes**. Proving that harmless took MPXJ conversion plus a model/CPM comparison, not a
  hex dump: same 145 tasks, same calendars, same CPM timings, same 4-task critical path.
- **Decisive-or-silent beats thorough.** The classifier calls a mismatch only from a magic
  signature, an OOXML part name, an OLE2 stream name, or a *complete* JSON/XML parse; "no decisive
  signal" is its own answer and is never reported. Likewise the hook does not sniff prose for
  schedule-shaped tables — no decisive signature exists, and **a guard that fires on documents gets
  switched off, after which it guards nothing.** Coverage you cannot defend is negative coverage.

### 2026-08-03f — A declared range nobody runs is not a claim, it is a wish (ADR-0346)
- **THE HEADLINE: the new floor job found a Law 1 defect on its very first run.** `fastapi>=0.110`
  had been in `pyproject.toml` for a year. fastapi **0.110.0 and 0.110.1** serialize a
  `RequestValidationError` with pydantic's `url` key intact, so a 422 body served by the air-gapped
  tool carries `https://errors.pydantic.dev/<ver>/v/missing` — an **external reference on the CUI
  boundary**, on 10 routes. `tests/web/test_airgap.py` catches it perfectly and always would have;
  nothing had ever *installed* the bottom of the range for it to look at. Isolated to fastapi, not
  pydantic (0.110.0 leaks under both 2.6.0 and 2.13.4; 0.110.2+ is clean under both). Floor raised to
  `>=0.110.2`. **Two correct controls that never meet prove nothing — the job is what introduces
  them.** That is a general lesson about coverage: ask not only "is there a test?" but "is there a
  configuration in which that test has ever been asked the question?"
- **Two of our own declared floors were false, and one of them could never have installed.**
  `pyproject.toml` said `pydantic>=2` and `fastapi>=0.110`. Those two lines are *unsatisfiable
  together*: fastapi 0.110 itself excludes pydantic 2.0.0/2.0.1/2.1.0. Nobody had ever tried,
  because nothing installs the bottom of a range. Bisected the real floor: 2.0.2 · 2.4.2 · 2.5.0 ·
  2.5.3 all fail `test_cache_does_not_perturb_hash_or_equality` (pydantic's generated `hash_func`
  hashed `self.__dict__.values()`, which on a frozen `Schedule` includes the `tasks_by_id` cache →
  `TypeError: unhashable type: 'mappingproxy'`); **2.6.0 is the first that passes**. The frozen-model
  identity contract this whole engine rests on simply did not hold below 2.6.
- **The lesson generalizes past dependencies:** a range, a threshold, a "supports X" — if no run
  exercises the boundary, the boundary is decoration. `minversion = "8.0"` had been in the file for
  months and nothing could contradict it. The fix is not a stricter number, it is a job that stands
  on the number.
- **The guard caught a real defect on its own first run — in my own artifact.** `pip freeze` silently
  omits `setuptools` (pip treats it, `pip` and `wheel` as "self" packages), so the first
  `known-good.txt` capture dropped the ONE pin that exists for a CVE remediation (ADR-0250). I would
  not have noticed by reading it; 58 plausible lines look exactly like 59. **A capture tool's
  default exclusions are part of your data, and you have to ask what they are** — the same shape as
  July's magic-byte sniffer whose 64-byte window invented three false positives.
- **A constraints file that does not bind is the measured-box failure wearing a new hat.** Constraints
  only apply to packages that actually get installed, so a typo'd or renamed pin is a *silent no-op*
  and the floor job goes green having tested the newest resolution — proving the opposite of what its
  name says. So the job asserts the INSTALLED versions, and I proved that step can fail (run it
  against the current venv: 7 of 8 pins unbound, `rc=1`). **Every job needs an answer to "what would
  make this pass while proving nothing?"**
- **Silencing is not bounding.** `filterwarnings` had been quietly swallowing starlette's
  httpx→httpx2 deprecation. That is not wrong on its own — the warning is upstream and unactionable
  in a product that imports neither — but it was the *whole* answer to a transition that will
  `RuntimeError` the entire web suite the day the fallback is dropped. A suppressed warning should
  always be paired with the bound that handles the thing it was warning about.
- **Sequencing note worth keeping:** the prompt said do P0-2 first, but P0-3 (`importorskip`) had to
  land first — the floor CI leg would have been red on day one from the two bare playwright imports.
  When a new gate is about to run somewhere nothing ran before, fix what it will find before you
  turn it on, or its first result teaches you nothing about the thing you built it for.
- **A webhook is a report about the past, not the present.** A "PR marked ready for review" event
  arrived AFTER the PR had already been squash-merged; acting on it would have had me watching a
  closed PR. The notice says so itself — verify with a fresh fetch when the state gates the next
  action. `mcp__github__pull_request_read method=get` returned `merged: true` and settled it in one
  call. Same family as the drift-guard race above: **both are stale-read bugs, one in a file and one
  in an event stream.**
- **Do not run the suite while you are editing the durable docs.** My first clean-floor run came back
  `3 failed, 3312 passed` — all three in `tests/test_state_docs.py`, which reads
  `HANDOFF.md`/`SESSION-LOG.md` **from disk at test time**, and I was mid-rotation (the file still
  held its `__NEW_SECTION__` marker). Nothing was wrong with the floor. I **re-ran rather than
  reconstruct `3312 + 3`**: a composite you assemble by argument is not a measurement, and this
  number was about to become an ADR's headline evidence. Corollary: the drift guard has a *time*
  dependency. The docs must be structurally complete before any suite starts — substituting a count
  into an otherwise-finished section afterwards is harmless; leaving a placeholder in one is not.

### 2026-08-03e — Concurrent sessions collide on identifiers, and a guard can pass on the thing it protects
- **Two sessions branched from the same `main`, both took "highest ADR + 1", and both got 0344.** Not
  a mistake either could have avoided alone: "highest + 1" is correct locally and wrong globally the
  moment a second branch is open. A third session found it and shipped
  `test_adr_numbers_are_unique`. **The lesson is about identifier allocation, not about carelessness:
  any "next free number" convention is a race unless something enforces uniqueness at merge.** Same
  class as a database sequence vs. `SELECT MAX(id)+1`.
- **The four pre-existing guards in `tests/test_state_docs.py` all stayed GREEN over the corrupted
  record.** `_latest_adr_number()` takes `max()`, so both `0344` files resolved to 344; and both
  durable docs legitimately contained `ADR-0344` because *both* PRs wrote it. **A guard going green
  on exactly the condition it exists to detect** — and note it took a *human-noticed* symptom to find
  it, not the test suite. This is the same shape as the defect this session fixed (a `caplog` test
  that cannot fail on the pytest version CI resolves). **When you add a guard, ask what corrupted
  state would still satisfy it.**
- **Merge conflicts in append-only durable docs are a signal, not a chore.** Both rounds conflicted
  only in `HANDOFF.md` / `SESSION-LOG.md` / `LESSONS-LEARNED.md` — files three sessions were all
  appending to. Resolution was always "keep BOTH", but the STATUS section had to be *rewritten* each
  round rather than picked from either side, because neither side described reality after the merge.
  **A conflict in a status document means the status is now something neither branch knew.**
- **I over-corrected once and the next run caught me.** After the `/analysis` focus→tip test failed
  3/3 I replaced "intermittent" with "deterministic locally" — then two full runs passed it.
  Load-sensitive is the honest word. **A correction is a claim too, and inherits the same evidentiary
  burden as the thing it corrects.** Three data points beat one, in both directions.

### 2026-08-03d — Audit an audit the way you'd audit code: test its confidence, not just its doubts
- **The claim the reviewer was surest about was the one most wrong — by 17×.** It named one
  polluting test; a per-test bisect found seventeen across three modules. Meanwhile all three of its
  "VERIFIED CONTROL" items reproduced exactly. **Generalization: a finding's confidence label tells
  you about the auditor's process, not about the codebase.** Budget verification by *blast radius if
  true*, not by how sure the reporter sounded. A one-line "HIGH" and a one-line "VERIFIED" both cost
  the same to check and only one of them was load-bearing.
- **"Cannot reproduce" is a result only after you've found the variable.** The pollution didn't
  reproduce on our pytest. Stopping there would have closed a real defect as noise. Pinning pytest
  8.0.2 / 8.4.2 / 9.1.1 against the *same tree* produced fail / fail / pass — and the tie-breaker was
  probing the logger state directly, which showed the leak is live on 9.1.1 too and merely *masked*.
  **When a defect won't reproduce, enumerate what differs between the two environments and bisect
  that, rather than reporting non-reproduction.**
- **Pin the invariant, not the symptom, when the symptom is version-dependent.** The obvious
  regression test (a `caplog` assertion) would have passed on the pytest CI resolves whether or not
  the bug was fixed — a test that cannot fail where it runs. The *leak* is version-independent, so
  asserting restored logger state fails on every version. **Ask "on which versions/configs can this
  test fail?" before writing it; if the answer excludes CI, you're writing coverage theatre.**
- **Fix the class, not the instances, when the instance count is unbounded.** Seventeen per-site
  fixture requests would have been mechanical and complete — and useless against the eighteenth.
  One autouse fixture closes the class. The rule of thumb: *if the defect is "someone forgot to call
  cleanup", the fix is almost never "remind everyone".*
- **Audit your audit tooling.** My own magic-byte sniffer reported three `.py` files as binary; a
  64-byte decode window had split a multi-byte UTF-8 character. Caught only because "three test
  files are secretly binary" was implausible enough to re-check. **A measurement that surprises you
  is first evidence about your instrument.**
- **A per-test fixture cannot undo a higher-scoped fixture, and my first regression test assumed it
  could.** pytest sets up session/module-scoped fixtures *before* function-scoped ones, so
  `tests/perf`'s module-scoped server had already configured logging by the time my autouse snapshot
  ran. Asserting "pristine" passed the module alone and failed the full suite. **Assert the
  guarantee your mechanism actually provides, not the outcome you wish it provided** — here,
  "the next test starts where this one started", which is exact regardless of what set the baseline.
  Corollary: *a new test that passes in isolation has not been tested; run it in the full suite
  before you believe it.*
- **Scope is the difference between alarm and a chore.** "89 tracked files have contents that don't
  match their names" reads catastrophic. Measuring what the *product* depends on — 65/65 statics,
  both `.aft` libraries parsing at 1443/1403 metrics, 16 goldens + 1 XER + 20 `.mpp` all intact —
  converted it into a provenance cleanup with zero correctness impact. **Always measure the blast
  radius before you rank the severity; the count is not the severity.**

### 2026-08-03c — An empty search result is a deliverable; and the ladder has a middle rung (ADR-0344)

- **The ask was "find and install skills."** Both catalogs were searched *first*: the account skill
  catalog (8 keyword sets) and the plugin marketplace. Both came back with **nothing new** — the
  relevant skills (`schedule-forensics`, `session-token-guardian`, `docx`/`xlsx`/`pptx`/`pdf`) and
  plugins (`engineering`, `design`) were already enabled. The honest answer to "install skills" was
  **there is nothing to install**, and saying so is what converted the task into the real one.
- **The lesson: report the empty search, don't route around it.** An unrecorded null result gets
  re-run by the next session at full cost. ADR-0344 pins which catalogs were searched, with what
  keywords, and what came back — the same discipline the audits use for a *refuted* finding.
- **Part III's ladder has three rungs, not two.** "Prose reminders decayed; tests didn't" is right,
  and this repo has faithfully converted process failures into executable guards wherever a guard was
  expressible: the drift guard, the wheel↔source lockstep, the dictionary sync, the DD-line ledger.
  But a whole class of ritual **cannot** be a test, because it governs *how a session works* rather
  than what the tree contains — how to run the gate so a piped exit code can't hide a failure, how to
  prove a test can fail, when to render instead of read, the handoff rotation's exact shape (a test
  can only catch that one *after* it was done wrong). The rungs are: **law (CLAUDE.md) → invoked
  procedure (a skill) → executable guard (a test)**. Reach for the highest rung that fits.
- **A ritual about how to VERIFY cannot itself be a test** — the test is the thing it is telling you
  to distrust. That is the structural reason `prove-able-to-fail` and `render-verify` had to be
  procedures rather than assertions.
- **Wrote the recipe by running it, not by drafting it.** `render-verify`'s Tier-1 renderer was
  executed before it was written into the skill: `/cei` on the five committed `TP4_DataCenter`
  fixtures → 200, 25,850 bytes, real takeaway `h1` read back. It immediately taught its own rule —
  without normalising the per-launch `sf-launch` nonce and the `?v=` cache-bust, every two-tree render
  diff is pure noise. A recipe that has never been run is a guess with formatting.
- **Verified the mechanism instead of assuming it**, and the check paid: project skills load from
  `.claude/skills/<name>/SKILL.md` with no registration, the *command* comes from the **directory**
  name (frontmatter `name` is only a display label for a project skill), cloud/web sessions load
  project skills from the cloned repo and **ignore `~/.claude/skills/` entirely** — which is why these
  are committed — and a *newly created* top-level skills directory needs a restart to be watched. That
  last one is a limitation this session **cannot** verify away, so it is recorded in the ADR and the
  handoff as a documented mechanic rather than dressed up as an observation.
- **The skills caught a defect in their own commit, via the trap they document.** `ruff format --check .`
  read **green (458 files)** before commit — from a stale **0.15.8** in `/root/.local/bin` shadowing the
  **0.16.1** `pip` had just installed to `/usr/local/bin`. The two differ in *scope*, not style: 0.16.x
  also formats fenced `python` blocks **inside markdown**, so the same tree is **458** files to one and
  **867** to the other, and `render-verify/SKILL.md`'s python recipe would have failed CI (which
  resolves `ruff>=0.6` to latest). Found by asking "is the binary on PATH the one I installed?" —
  `which -a ruff` vs `pip show ruff`. **This is 2026-07-29 cont.3 ("a green gate proves nothing if the
  binary isn't the one CI runs") in a new costume: that time it was a stale wheel, this time a
  shadowed linter.** The generalised rule now lives in the `full-gate` skill with the measured file
  counts: *a version check is part of the gate, not a preamble to it.*
- **And the `pgrep -f` self-match trap fired on me the same hour, in a new costume.** A waiter built as
  `until [ ! -d /proc/$(pgrep -f "pytest -q" | head -1) ] || ! pgrep -f "[p]ython …"` printed
  **"SUITE FINISHED"** while pytest was still burning CPU (PID 18033, 9:12). The bracketed clause was
  correct; the *unbracketed* one self-matched the waiter's own command line and `head -1` picked a PID
  that had already exited, so `! -d /proc/<pid>` went true. **The documented trap is "pgrep finds
  itself"; the sharper form is "a compound condition built on a self-matching pgrep can report the
  OPPOSITE of the truth."** Cost nothing only because the signal was confirmed with `ps` before being
  acted on — *never act on a completion signal you built yourself without an independent check.*
- **A stated limitation is a standing invitation to measure it — and this one fell within the hour.**
  The commit went out saying "this session cannot observe the skills loading," reasoning from the
  documented mechanic (*a newly created top-level skills directory needs a restart to be watched*).
  Minutes later all seven appeared in the live skill listing with **no restart**, and the listed
  `cui-guard` text was the **edited** description — so the loader was re-reading from disk, not
  replaying a snapshot. The caveat evidently governs a skills directory created outside an
  already-watched parent (`.claude/` existed; only `.claude/skills/` was new). **The lesson is the
  same one ADR-0343 bought, pointed at myself: when a record names the evidence it lacks, that
  sentence is the experiment.** Corrected in the ADR and handoff with the superseded claim left
  VISIBLE — a limitation quietly deleted teaches nothing, and reading *"stated, then measured away"*
  is how a future session learns the move.
- **Two concurrent sessions minted the same ADR number, and the drift guard was structurally blind to
  it.** #527 (skills) and #528 (logging isolation) each branched from `1119162`, each took
  "highest + 1", and both produced **ADR-0344**. `_latest_adr_number()` takes `max()`, so duplicates
  both resolve to `344`, and both durable docs legitimately contain `ADR-0344` because *both* PRs wrote
  it — **all four existing assertions pass over a corrupted record.** An ADR number is a *cited
  identifier* here (handoffs, logs, commits, PR bodies, code comments, the testimony narrative), so a
  duplicate is not cosmetic and cannot be fixed later without rewriting published history.
  `test_adr_numbers_are_unique` now asserts the property. **Proved able to fail with the REAL colliding
  filename: 1 failed, 4 passed** — and the four green ones are the finding, not a footnote: they are the
  measurement that the old guards could never have caught it. Lesson: **"highest + 1" is not a
  concurrency-safe allocator**, and a guard derived via `max()` is blind to duplicates by construction.
  Sub-lesson on the fix itself: **do not mint a new ADR number to record a fix for ADR-number
  collisions** — taking 0345 would have collided with the renumber #528 was just asked to make. A guard
  that enforces an existing convention does not need a new decision record.
- **A skill is a checklist, never an oracle.** Each rule cites the ADR or lessons date that bought it
  so a future session can verify it against the code; per ADR-0240 anything parity-, engine-,
  testimony- or CUI-relevant is still re-validated by the lead before it lands.

### 2026-08-03b — An audit that names its own blind spot is telling you the experiment to run
- **The three UNSURE rows of the 2026-07-29 falsy-zero sweep sat open for five weeks, and the sweep
  had already written down how to close them:** *"I did not execute the rendered page."* Not a
  hedge — a **protocol**. Rendering the two pages settled all three inside an hour, and all three
  fabricated. **When a prior finding states the evidence it lacked, that sentence IS the task
  definition.** Re-reading the source for a sixth time would never have resolved it, because the
  answer was never in the source: it was in the template's `is not None` on the line below.
- **The defect shape worth naming: a self-contradiction inside one viewport.** On `/cei`, the
  takeaway said *"No month could be CEI-scored"* and the KPI cards said *"—"* — both correct —
  while a panel between them drew *"Latest scored month · 0 planned in the month"*. Nothing was
  wrong with the data or the engine; **one consumer of a nullable field forgot it was nullable.**
  This class is invisible to a grep (the `or 0` looks like every other `or 0`) and invisible to a
  unit test of either component, but it is *glaring* the instant you render. Cheap, high-yield
  check: for any page mixing an em-dash KPI strip with a chart, render an input where the figure is
  absent and see whether the two halves still agree.
- **A matching count is not an identification — the second consecutive session to pay for it, in a
  new costume.** Last session it was 6 test failures matching 6 fixed files (4 were unrelated
  installer lockstep). This session it was **118** WBS rows reading `0%` matching a suspected
  fabrication; re-deriving the population per value cut it to **19**, with 99 honest zeros. The
  generalization: *a number that matches your hypothesis is the moment to re-derive it, not the
  moment to write it down.* Same discipline as the standing rule "a number written mid-session is
  not a measurement".
- **Verify the premise of the queue item before working it.** The handoff said "the 3 falsy-zero
  rows"; before touching them, the 4 supposedly-CLOSED BUG rows were re-checked. Three were fixed —
  but the fourth, `resources.py`'s `or [sd]`, is **still in the tree on purpose**: ADR-0306 paired
  it with the `over_allocated` fix, whose docstring names the non-working-day bucket as a case it
  must now *surface*. Had that been "fixed" on the strength of the audit table alone, it would have
  re-hidden the exact over-allocation ADR-0306 exposed. **A stale audit row and a deliberate
  exception look identical from the table; only the code says which.**
- **Read the emitter before writing the parser.** `_stat_cards` emits **value THEN label**, so the
  session's first KPI probe — a regex scanning forward from each label — reported the *next* card's
  value and claimed the page said `Planned = 0` when it said `—`. Caught only because the results
  were internally absurd ("CEI month = 0"). A scraping regex over your own templates is a piece of
  code that can be wrong; sanity-check it against a case whose answer you already know.
- **A revert that fails the whole module proves nothing.** Two independent reverts were run, one
  per surface: the `/cei` revert failed 2 of 11 and the `/groups` revert failed 6 of 11, each
  leaving the other surface's tests — and its own true-positive twin — green. N-of-N failing is
  also what one test copy-pasted N times looks like.
- **"Build the wheel before the gate" is necessary but not sufficient.** Last session's lesson was
  followed — wheel + nine installers built at v1.0.159 before the suite — and the gate still failed
  on `test_embedded_wheel_is_in_lockstep_with_the_source_tree`, because a **three-line comment
  edit** landed afterwards and the test compares **byte-for-byte**. The sharpened rule:
  **REBUILD AFTER THE LAST BYTE OF `src/` CHANGES — a comment is a byte.** The recovery was cheap
  only because the failure was *predicted and named* the moment the edit was made, rather than
  triaged from a summary line 27 minutes later. Corollary worth keeping: when you knowingly
  invalidate an artifact mid-session, write down which test will fail before it does — that turns a
  red gate from a surprise into a checklist item.

### 2026-08-03 — "Denominated in dates" is not "a time axis" (ADR-0342, the DD-line gap closes)
- **The pending list was 8. Six of the eight were not work at all** — they were two
  misclassifications wearing a date's name, and both were caught by *rendering* rather than by
  reading the bucket they sat in.
  - `margin_dashboard`'s burn-down declared `xLabel: "Status date"`. Rendered in chromium with
    deliberately IRREGULAR status dates (1 week, 1 week, then **15** weeks apart) it spaced all
    four versions **evenly** — the 15-week jump got the same pixel width as the 1-week gaps, and
    two ticks both read "2026-03". It is one slot per loaded version: `margin.js`'s categorical
    axis, mislabelled. Its sibling erosion chart, in the SAME module, is linear in milliseconds
    and extends its domain to the projected zero-margin date, so the data date is a real and
    genuinely useful position there. **One module, two charts, two opposite answers.**
  - The five SRA "Finish date" charts plot a *distribution over a simulated outcome*. Measured:
    schedule status date **2026-08-27**, `/api/sra` CDF domain **2028-01-21 → 2028-01-28** — the
    data date is ~17 months to the LEFT of a 7-day, index-spaced window. Clamping a marker to the
    left edge would assert the data date IS the earliest simulated finish (Law 2). The tell was
    already in the tree: `sra_jcl.js`'s SIBLING cost axis was *already* excluded, and it is the
    same joint distribution with the other variable on x.
- **Lesson (generalizes → Part V/VI): the unit of a quantity is not its semantics.** A date-valued
  axis can be categorical (one tick per version), an outcome distribution (one tick per simulated
  finish), or a calendar — and only the last one has a place to put "now". Ask *what one step along
  this axis means*, not what the values look like. The `ai/qa.py` identifier-before-derivation
  ordering is the same shape: check what a token IS before checking what it looks like.
- **The revert discipline paid again, and the discriminating revert is the one that taught.**
  Neutering the shared helper failed all 4 render tests while all **34** source-ledger tests kept
  passing — which is itself the finding: *a source census cannot catch a broken helper*, so the
  render module is not redundant with the ledger. Then removing ONE caller (`resources.js`) failed
  exactly 1 and passed the other 3. And a third revert on the CSS alone (`--bad` → `--accent`)
  failed 4 including the ledger's design-system test — style assertions really are silent without
  their own revert.
- **A host list guessed from the ledger's keys under-reported by two.** `curves.js` has ONE
  `axisTitles` call site in source and renders THREE charts through it (`#finishesChart`,
  `#dataDateChart`, `#slippageChart`). The first render test asserted 4 hosts and failed on
  `curves.js: 0` — not a code bug, a wrong selector. **Source call sites and rendered charts are
  different populations; probe the page for the second one.** (Fixed by listing every `[id]` that
  contains an `svg` on a live `/mission` and reading what came back: 6 markers, 6 hosts.)
- **A MATCHING COUNT IS NOT AN IDENTIFICATION — the near-miss of the session.** The suite showed
  6 failures; I had just fixed 6 test files; I wrote that the 6 were mine and was about to treat
  the run as explained. They were not the same 6. Mapping the progress-output indices back to
  `pytest --collect-only -q` showed **4 of them were `tests/installer/test_installers.py`** — the
  embedded-wheel-in-lockstep-with-the-source-tree checks, failing because static assets and the
  version had changed and the wheel had not been rebuilt yet. Only 2 were mine. **Lesson: when a
  count matches your expectation, that is a coincidence until you have the NAMES.** The cheap
  identification, worth remembering: strip the `[ nn%]` suffixes from `-q` progress output, take
  the indices of `F`/`E`, and read those lines out of `pytest --collect-only -q` — it works
  mid-run, without waiting for the summary.
- **Also:** `pytest --timeout=300` is not available here (no `pytest-timeout`), and the arg error
  exited **0** through the pipeline — an exit code from a `| tail` pipeline is the tail's, so a
  "passing" background run can be a usage error. Check for the summary line, not the status.

### 2026-08-02g — A grep count is not a census, in BOTH directions (ADR-0341, the DD-line ledger)
- **The same mistake, three times in one session, and the third time I made it in a handoff.** A
  `grep -ci "data.date"` census said 4 charts lacked a data-date marker; the real number is 8,
  because the grep counts MENTIONS — comments, `statusDate` variables, legend text. I then wrote a
  byte-exact detector matching the one implementation I had read (`cei.js`), and it failed the
  OPPOSITE way: it reported two implementations where there are four, missing `drift.js` (which
  labels its marker only in a legend note) and `scurve.js` (which appends the date to the label).
  **Lesson (generalizes → Part V): a loose detector over-reports and a tight one under-reports, and
  BOTH read as authoritative. Anchor on the thing every implementation must write deliberately —
  here the `//` comment naming the block — and then RUN it against the tree and read what comes
  back. Deliberately do NOT anchor on style when the styles are what you are measuring.**
- **Derive the pending list; never declare it.** `DD_PENDING` is computed from the tree and compared
  to the record, so it cannot overstate the work (a fixed entry nobody removed) or understate it (a
  chart that lost its marker). A declared list is silent in both failure modes. This is the property
  `DOM_PENDING` earned the hard way one ADR earlier, applied from the start this time.
- **When N tests cover N subjects, revert one SUBJECT, not just the shared thing** (carried forward
  from ADR-0340 and applied again): reverting `histogram.js`'s xLabel to a date proved the exclusion
  list cannot shelter a chart that genuinely plots against time — a property no amount of reverting
  the detector could show.
- **Two slicing bugs, both invisible to reading.** Slicing from the first occurrence of a phrase
  read `cei.js`'s DOCSTRING rather than its code (the header comment uses the same words), and a
  fixed-size window over-ran into the next block — harmless for three modules and wrong for the one
  whose block is short. **Lesson: a text window over source needs a real terminator, and the module
  that breaks it is the one shaped differently from the one you developed against.**
- **A ledger can record a violation without blessing it.** Nothing in the tree matches the design
  system's DD-line rule (none is red, no label is uppercase, all hard-code a type size). Pinning the
  CURRENT state means closing any part of the gap FAILS the ledger and forces it updated in the same
  commit — the PENDING pattern applied to a spec deviation rather than to missing work.

### 2026-08-02f — Where a shared helper LIVES is a correctness question (ADR-0340, DOM captions)
- **The bug that was one decision away, and would have been silent.** `chartframe.js` owns the SVG
  caption helper, so it is the obvious home for the DOM one. It is the wrong home: the layout emits
  `chartframe.js` **after `</main>`**, every captioned table is built by a script **inside** the
  body, and `whatif.js` renders **synchronously at parse time**. A `window.SFChartFrame.tableCaption`
  would have been `undefined` at the moment whatif draws — its two grids would render uncaptioned
  **with every source-level assertion in the suite still green**, because a source pin proves a call
  EXISTS, never that it was REACHED. Caught by reading the layout's script order before writing the
  helper, not by a test. **Lesson (generalizes → Part VI): before adding a function to a shared
  module, check WHEN that module loads relative to its callers. For a browser, "which file exports
  it" is a load-order decision wearing an architecture costume.**
- **The single-caller revert is a different instrument from the all-or-nothing revert.** Neutering
  the helper failed 11 of 11 chromium tests — satisfying, and nearly uninformative: it is exactly
  what a suite would do if all eleven tests were coupled to one global and only one module were
  really covered. Removing **one caller** (`whatif.js`) failed **5 and passed 6**, which is the
  proof that each test tracks its own module. **Lesson (generalizes → Part III): when N tests cover
  N subjects through a shared dependency, revert the SHARED thing to prove they bite, then revert
  ONE SUBJECT to prove they discriminate. The first revert alone cannot distinguish "N tests" from
  "one test run N times".**
- **A remaining-work ledger must be re-verified against the code, not just worked down.**
  `sra_risk.js` sat in `DOM_PENDING` for four ADRs as "a DOM visual awaiting a caption". It builds
  no DOM at all — no `createElement`, no `appendChild`, no `innerHTML`. It could never have been
  captioned, so the ledger had overstated the work by ~14% since it was written, and the honest
  close was a **re-triage to `EXEMPT`**, not a caption. **Lesson: an inherited ledger entry is a
  claim like any other (READ EVERYTHING, ASSUME NOTHING). This is also the argument for named lists
  over counts — a count would have been quietly wrong and unfalsifiable; a named list let one read
  of one file settle it.**
- **A convention that survives one caller can still be unimplementable at seven.** ADR-0326's
  inline `el("caption", {class:"ch-atd"}, …)` was fine for `workbench.js` alone. The other six
  modules' local `el()` helpers take **three different signatures**, so keeping the inline form
  would have forced a detector regex that accepted all three — **looser than the rule it enforces**,
  the recurring vacuous-gate shape #4. Promoting to one helper was the cheaper answer AND the
  tighter gate. **Lesson: when the test you would have to write must get looser to accommodate the
  code, that is the code telling you to unify it.**
- Tooling: **`pgrep -f <pat>` self-matches exactly like `pkill -f`** — a wait-loop polling for its
  own pattern never terminates. Same family as the already-recorded `pkill` trap; use `[p]ytest`,
  or just let the background task's own completion notification arrive.

### 2026-08-02e — The assertion was looser than the rule, so it could not fail (ADR-0339, `/sra`)
- **The adversarial audit found six real defects in code that had already passed a 14-revert proof
  pass.** The reverts prove a gate can fail; they say nothing about the states nobody wrote a gate
  for. Every one of the six lived in an unexercised SESSION STATE — no solvable version, a
  cost-loaded file, an excluded version, a non-empty risk register. **Lesson: "I proved my tests can
  fail" and "I tested the feature" are different claims. Enumerate the states the code branches on
  and render each one; the branch you never rendered is where the false statement is hiding.**
- **The most dangerous defect was a link that was correct in every state I had rendered.** `⤓ EXCEL`
  pointed at `/export/xlsx/sra`, which is real — but that endpoint answers **400** when no version
  solves, and in that state the whole page still offered ten of them. **Lesson: "the endpoint
  exists" is not the rank-3 test. The test is "the endpoint answers, in THIS page's current state" —
  a link's validity is a function of session state, not of the route table.**
- **A finding being right about the flaw and wrong about the fix is normal; adjudicate both.** Of
  nine audit findings, six were real, and three were not — two mirrored the page's own pre-existing
  semantics (changing them would have been a silent behaviour change wearing a UI-conversion label),
  and one was right in a way I had not expected: two of my own assertions compared only module
  constants. **Lesson: re-verify every finding against the code before touching anything, and when a
  reviewer is right about your own test being decorative, delete the assert rather than defend it.**
- **Fourth consecutive PR whose revert pass found a gate that could not fail — and this was a new
  shape.** `test_the_sra_takeaway_quotes_figures_the_page_renders_below_it` searched the KPI strip
  for "the label, then the number" with `.*?` under `re.DOTALL`. That dot-star spans the **whole
  six-card strip**, so any card's digit satisfied any label. Rewriting the headline to quote two
  figures the page never renders left it green. **Lesson: when a rule says "this figure belongs to
  that label", the assertion has to bind them. A regex whose wildcard can cross the boundary the
  rule is about is not testing the rule — it is testing that both things exist somewhere.** Parse
  the structure into pairs and compare exactly; `re.DOTALL` plus `.*?` across a repeated element is
  the tell.
- **The carried line-count was attributing 295 of `/sra`'s ~550 lines to a function that does not
  render the page.** `_sra_report_blocks` builds the **`.docx` export**, not the HTML. Nobody had
  checked which call site it had; the number had been copied forward across several handoffs.
  **Lesson: an estimate assembled from function lengths is only as good as the claim that those
  functions are on the path. Confirm the call site, not the symbol name.**
- **Rank 3 ("never a dead link") was free on three routes and only bit on the fourth.** Every panel
  on `/briefing`, `/brief` and `/risks` had its data in the page's workbook, so ⤓-count == strip
  count automatically and the rule looked satisfied without ever being exercised. `/sra` has two
  panels whose data is genuinely not in that workbook (guidance prose; JCL on a file with no cost
  loading). **Lesson: a rule that has never cost you anything has never been tested. Assert the
  SHORTFALL, not just the presence — otherwise "give everything a ⤓ for consistency" passes.**
- **A style probe that reads `querySelector('.panel-head')` cannot tell 1 from 12.** Removing the
  head strip from three `/sra` panels left the four-theme probe green, because another panel's head
  was still first in the document. It is not vacuous — two CSS reverts fail it on every route — but
  its per-route strength is "at least one head renders". **Lesson: know what a passing style test
  actually proved. Pair it with the markup census that counts, and probe any NEW strip shape
  separately** (here, the ⛶-with-no-⤓ strip got its own four-theme test).

### 2026-08-02d — A rule tested on one route is not tested; and the gate I wrote found a defect in my own headline
- **The revert discipline caught a coverage hole no amount of reading would have.** Dropping
  `/risks`'s takeaway h1 — a Definition-of-Done requirement — failed **nothing**, because the
  takeaway test read `/brief` only. Both routes were converted in the same style, both were "in the
  test file", and the suite was green. **Lesson: a per-route rule needs a per-route assertion. A
  test that loops over `pages.items()` looks like coverage; a test that hard-codes one key is
  coverage for one key, and the difference is invisible until you break the other one.**
- **Writing that missing gate immediately exposed a real Law-2 defect in code I had just written.**
  The `/risks` headline quoted `len(findings)` — a SUM of three counts that were each rendered
  separately and never as a total. `_utility_takeaway`'s own contract says every figure in a
  headline must appear again further down the page so the reader can verify it, and mine could not
  be. Fixed in the render, not the test. **Lesson: the act of writing an honest gate is itself a
  design review — if the assertion is awkward to write, that is usually the code telling you the
  property does not actually hold.**
- **Estimates about someone else's code decay silently.** `/sra` was carried in the handoff as "13
  panels"; it renders **15**. The number had been repeated across several handoffs without being
  re-measured. **Lesson: a figure that travels through documents needs a re-measurement stamp, not
  a citation — and "approximately" in a handoff (like CC-01's "~74 sites") should be read as "this
  was never verified", because that is what it means.**
- **Rename the test file when its scope outgrows its name.** `test_ch12_panel_contract.py` asserting
  on a chapter-11 route is a name that lies, and names that lie are how the next person misses that
  coverage already exists. Renaming to `test_act3_*` cost one `git mv`. **Lesson: a misleading test
  filename is a bug with a very long fuse.**

### 2026-08-02c — The measurement corrected the work list twice before a line was written
- **Two of the four "unconverted pages" facts in the queue were wrong, and both errors came from
  grepping instead of rendering.** Rendering every report page and counting its contract markers
  showed (a) **`/driving-path` is not an unconverted page at all** — its all-zeros reading is its
  EMPTY STATE with no target UID entered, and `/path` is the populated variant, already converted;
  and (b) a `<div class=panel[ >]` regex **silently misses the quoted form** `<div class="panel
  brief-doc">`, which under-counted `/briefing` by three panels. **Lesson: for a UI census, measure
  the OUTPUT, not the source — and when you write the matcher, enumerate the spellings the codebase
  actually uses before you trust a zero.** A count that is quietly wrong is worse than no count,
  because it becomes the baseline everything downstream is compared against.
- **The bug worth catching this round was invisible in every default configuration.**
  `ai_polish.js` replaces the WHOLE of `#briefingBody` with what `/api/ai/briefing` re-renders. A
  provenance chip built *inside* the render function would therefore vanish the instant a local
  model was active — no error, no layout shift, just a briefing wearing no provenance, in the one
  configuration the suite never exercises by default. Making the chip a **parameter** both call
  sites pass is what fixes it. **Lesson: when a fragment of a page is re-rendered by a second
  endpoint, everything that fragment carries has to be supplied by BOTH callers — and the test has
  to drive the second endpoint, because the first one will look perfect forever.**
- **A theme assertion that has never been made to fail is decoration.** The four-theme
  computed-style probe passed on the first run, which proves nothing on its own; two CSS reverts
  (jarvis hiding the tool strip, apollo rendering the chip fully transparent) were needed to show
  it discriminates. This is the same shape as yesterday's vacuous residue gate, in a different
  medium. **Lesson: any assertion about rendered appearance needs a deliberate ugly-render revert
  before it counts — the failure mode of a style test is silence, not noise.**
- **Sizing before choosing changed the plan, cheaply.** Measuring the four pages' rendering
  functions (`/sra` ≈550 lines vs chapter 12's ≈180) turned "do them in the order they were listed"
  into "do the coherent 180-line chapter first, give `/sra` its own PR". Two minutes of counting
  bought a reviewable diff. **Lesson: when a rule says "one X per PR", measure X before committing
  to a batch — the listed order is rarely a size order.**

### 2026-08-02b — A `-k` filter deselected the test the revert was aimed at; and a gate that the file-unlink made vacuous
- **The able-to-fail discipline nearly gave a false green, twice in one change, both times through
  the harness rather than the code.** First: the revert that removes launch-clearing was run under
  `pytest -k "dead_run or no_run_marker or …"`, and the filter silently **deselected the very test
  it targeted** (`…a_killed_runs_cache_empties_it` contains neither substring). The output read
  "1 failed, 3 passed, 23 deselected" and looked like a clean single-gate result. **Lesson: when
  proving able-to-fail, run the whole module — never a `-k` subset.** A filter you wrote from
  memory of the test names is one typo away from proving nothing, and the failure mode is silent.
- **Second: a gate that could not fail because the code under it destroys its own evidence.** The
  "a clean quit leaves no claim behind" test passed against a build whose `clear()` never released
  the claim — because `clear()` **unlinks the database file**, so the marker vanishes with it
  either way. The explicit `DELETE` only matters on the *other* path, the Windows fallback where an
  open reader refuses the unlink and the tables are emptied in place. **Lesson: when the operation
  under test has two implementations, ask which one your fixture actually exercises** — and if the
  cheap path erases the evidence, force the other one and assert the precondition (`db.exists()`)
  so the test cannot drift back to proving nothing.
- **This is the fourth ADR in a row where a gate had to be run against a revert before it was worth
  anything.** The pattern is now unmistakable: writing the assertion is the easy half; the half
  that finds the vacuous gates is *executing the counterfactual*. Both of this session's near-misses
  were invisible to review and to a green run.
- **A design lesson that generalizes beyond this repo: `os.kill(pid, 0)` is not a portable liveness
  probe.** It asks a question on POSIX but on **Windows it terminates the target** — a probe that
  kills what it probes. Combined with pid reuse, that ruled out the pid-based design entirely; a
  random per-process token needs only an equality test and carries no platform behaviour at all.
  **When you only need identity, do not reach for something that also carries semantics.**
- **Process lesson that paid off: asking cost one turn and changed the design.** ADR-0335 flagged
  this residue window as the operator's call rather than fixing it unilaterally, because the
  obvious fix was "clear at launch" by another name — the one shape the approved wording forbade.
  Presenting the four options with the trade-offs stated got a decision (the dirty flag) that is
  strictly better than what either side would have taken alone. **Flagging a boundary is not
  stalling; taking it unilaterally is how you ship a change that has to be reverted.**

### 2026-08-02 — The obvious hardening was the regression, and the residue test was vacuous
- **`PRAGMA secure_delete=ON` looked like textbook Law-1 hardening for the CUI disk cache. Measuring
  it killed it.** It zeroes every deleted byte in place at **~12.5 ms/MB**: **26.08 s** to clear a
  1 GiB cache — on the *quit* path, and **past ADR-0334's 20 s handover budget**, so the very next
  launch would have raised `PortUnavailable` and refused to start. The fix that previous session
  shipped would have been regressed by this session's "hardening". Deleting the database FILE does
  the same job in **0.12 s** and removes strictly more (the whole file, not merely its pages).
  **Generalizable: for erasure, completion probability is part of the security property. A slow
  erase that gets interrupted leaves more behind than a fast one that finishes** — and "more
  thorough per byte" is not the same as "more thorough".
- **A test that cannot fail is not a gate, and this one hid behind a compile flag.** The natural
  assertion for "the cache was cleared" is *the activity names are no longer in the file bytes*. On
  this box it **passes no matter what the code does**, because Debian compiles sqlite with
  `SQLITE_SECURE_DELETE` ON, so even a bare DELETE scrubs. Two independent audit lenses reached
  **opposite** conclusions on disk residue for exactly this reason — one probed the platform
  default, one forced it off. Only the revert experiment exposed it: reverting to a bare DELETE left
  the test green. The gate now leads with **reclaimed file size**, which discriminates on every
  platform. **Generalizable: when an assertion depends on a platform/compile default, it is testing
  the platform, not your code — find the property that holds everywhere.**
- **The able-to-fail ritual caught FOUR vacuous gates today, and only because it was actually run.**
  Besides the residue test above, the byte-cap test used an accented-Latin payload at 1.15
  bytes/character; rounding to whole rows landed the *buggy* character-counting code on the *same*
  answer as the correct code, so it passed against the very bug it was written for. Fixed with a
  3 bytes/character payload **plus an assertion on the fixture's own ratio**, so it can never
  silently stop discriminating. **Generalizable: a test built on a fixture whose margin is small
  relative to its rounding is not testing what its name says. Assert the property that makes the
  fixture discriminating, not just the outcome.**
- **And one revert was wrong the first time.** The first attempt left the VACUUM in place while
  removing only the unlink, so the behaviour under test was still present and the green result
  looked like a vacuous test. **Reverting the caller is necessary but not sufficient — confirm the
  revert actually removed the behaviour the test names**, or the ritual quietly certifies nothing.
- **Two more vacuous gates, same family, different mechanism.** The "cleared even when the cache
  cannot be opened" test corrupted the database by overwriting the WHOLE file — which destroyed the
  payload in its own fixture, so it passed no matter what the code did (fixed: smash only the
  16-byte header, and assert the content is still present before clearing). And the migration test
  only ever exercised the success path, where verifying the ALTER and not verifying it agree; the
  branch that mattered needed a connection stub whose ALTERs are lost to a lock. **Generalizable:
  the two ways a gate goes vacuous are (i) the fixture's setup already achieves the outcome, and
  (ii) the test only walks the path where the bug and the fix behave identically. Both are invisible
  until you revert the code and watch it stay green.**
- **The audit's best catches were in MY OWN new code, not in the old code it was pointed at.** Four
  real defects, none of which the tests I had already written would have caught: the `ALTER`
  migration suppressed by exception type, so an ALTER lost to a lock looked exactly like a harmless
  duplicate-column race and left the schema behind while reporting success; `prune()` returned a
  count of rows its own rolled-back transaction had not actually removed; `clear()` short-circuited
  on `_ready` and reported "nothing left behind" for a corrupt database still full of schedules; and
  the age window had no upper bound, so a backwards clock jump made a row **immortal** rather than
  late — **a case my own code comment explicitly claimed was safe.** *Generalizable: the comment
  asserting an edge case is handled is exactly the place to point a reviewer, because it is the one
  claim nobody re-derives.*
- **The parallel audit paid for itself precisely where intuition was weakest — the boring edges.**
  Beyond the two blockers, it surfaced three real Law-1 gaps nobody would have thought to look for:
  `VACUUM` writes its rebuild to a **plaintext transient in `/var/tmp`**, outside the directory the
  module documents as its boundary; the WAL can hold the rebuild while pre-prune pages stay legible
  in the main file; and the cache was created **world-readable `0644` in a `0755` directory**. None
  are exotic — all three are defaults doing what defaults do. **Generalizable: when the requirement
  is "this data does not persist", enumerate every file the storage engine touches, not just the
  one you named.**
- **"We already guard that" deserves re-reading, not recall.** ADR-0263's `wipe_gen` was believed to
  stop late writes re-populating the cache. It does — for **wipes**. Only `/session/wipe` bumps that
  generation, so a *shutdown* was completely uncovered, and an import finishing during uvicorn's
  drain wrote 181 KB of parsed schedule straight back into a cache that had just reported itself
  clear (reproduced end-to-end before fixing). **The fix went on the cache OBJECT (`seal()`), not on
  the two call sites** — same inversion as 2026-08-01j: covering a future write site by mechanism
  rather than by whoever remembers.
- **Exit hooks are not interchangeable, and only measurement says which fire.** Measured per signal:
  **SIGTERM runs NOTHING** — not `finally`, not `atexit` (exit `-15`) — because uvicorn handles it
  gracefully and then `capture_signals` **re-raises the captured signal**, killing the process
  before `serve()` returns. SIGINT survives only because `serve()` already suppresses
  `KeyboardInterrupt`, a line written for an unrelated reason years earlier. The ASGI **lifespan**
  hook is the only one that covers a macOS/Linux logout or system shutdown. **Generalizable: never
  reason about cleanup coverage from the shape of the code — send the signals and read the exits.**
- **Scope honesty beat scope creep.** The measurement showed the age cap barely bites (a clean quit
  clears everything, so hard-kill residue really survives *until the next clean session*, not 24 h).
  The deterministic fix — drop every row not written by the current launch — is **clear-at-launch by
  another name**, which the operator's approved wording forbids. Flagged in the handoff as their
  call rather than quietly redefining their decision.

### 2026-08-01j — A list of things to clear is a leak with a delay fuse
- `/session/wipe` reset fields by **naming** them. That is correct exactly once — on the day it is
  written. Measured today: **72 declared fields, 27 of real operator state surviving a "wipe"**,
  including the entire SRA setup, the whole JCL configuration, and `dcma_acumen_parity`, a flag
  that changes what the engine *computes*. Nobody removed anything; fields were simply added over
  months and the handler was never the place people thought to look. **The generalizable rule: when
  correctness depends on a human remembering to update a list, invert the default.** `reset()` now
  restores every field and preserving one requires naming it — so the next field added is safe
  because of the mechanism, not because of anyone's diligence.
- **Severity came from the KEY, not the field.** `sra_factors` and `sra_bcwc` are keyed by
  UniqueID, so a surviving map is not stale trivia — load a different project and it silently
  adopts the previous project's risk inputs wherever UIDs collide. When triaging "leftover state",
  ask what the data is keyed by: shared-key state crosses tenants silently, unique-key state
  usually just looks wrong.
- **The right revert is the CALLER, not the API.** The first able-to-fail attempt reverted both the
  new `reset()` and its caller — the tests then failed with an ImportError, which proves nothing
  about behaviour. Reverting only the handler produced the honest failure: `assert {7: 3} == {}`,
  the exact per-UID factor that would leak. When a change adds an API *and* a call site, revert the
  call site to prove the defect is real.
- **A fix can be right while its test is wrong.** The browser assertion demanded
  `sf-story-visited` be *absent* after the launch sweep; it is not, because `story.js` legitimately
  re-records the chapter being viewed on that same load. The failure looked like the fix not
  working. Before weakening a fix to satisfy a test, check whether the test asserts something the
  design never promised — here the real property was "nothing from the previous project remains".
- **"Clear everything" is not automatically the safest option.** A blanket `sf-`/`sf.` localStorage
  sweep would have un-muted the boot hum and reset the theme on every launch. Session state and
  operator preferences live in the same namespace and must be split by intent, not by prefix.
- **Do not amend published history to satisfy a hook.** After the squash-merge the stop hook
  flagged the orphaned branch commits as unverified and suggested amending them. Amending would
  have forked the branch from `main` and broken the CUI guard's `inherited_from_main` rule; the
  correct response was restarting the branch from `origin/main`, which is already the documented
  procedure. A tool's suggested remedy is a default, not an instruction — check it against the
  repo's own rules first.

### 2026-08-01i — A test can measure the wrong thing for eleven batches and stay green
- The axis-caption convention shipped **eleven batches** and a four-theme × three-scale measured
  pass, and every one of them was blind to the defect that mattered: a caption drawn *over a
  histogram bar* prints at **1.17:1**. The pass measured contrast against the element's resolved
  CSS `background` and overlap only against sibling `<text>` — so `<rect>`/`<polyline>` ink was
  invisible to *both* checks. It measured **text vs text and called it legibility.** The lesson
  generalizes past captions: when you write a check, name the failure it is supposed to catch and
  then ask what the check actually reads. Ours read the *stylesheet's* backdrop, not the *painted*
  one, and those differ exactly where charts are interesting.
- **Corollary — an assertion whose antecedent is almost always true is a markup check in
  disguise.** "Ink is under the caption, so the halo must be set" sounds like a measurement, but
  ink is under **792 of 1008** renders, so it decays toward `assert rule in stylesheet` — the very
  ADR-0304 anti-pattern the file exists to prevent. The honest version screenshots the caption and
  measures the modal colour of its own box. Cost: one PNG decode (stdlib `zlib`, since Pillow is
  not a dependency). Value: it failed on the real defect at 1.17:1 and *discriminated* — the one
  caption with no bar behind it still read 3.07:1 in the same run.
- **A stray `*/` is a silent, total CSS failure.** Putting new rationale outside the closing
  comment marker made the parser error-recover and swallow the entire `.ch-at` rule.
  `node --check` does not read CSS, ruff and mypy do not read CSS, and a source grep still found
  the text. Only reading **computed style from a real render** caught it — the same principle as
  ADR-0304's measured box, applied to a stylesheet.
- **Read the CSS before assuming a colour.** The draft fix painted a blanket white halo; two of
  the three chart families are not on white (`.res-svg` and `.evo-gantt svg` use
  `var(--gantt-canvas)`). The token indirection (`--sf-ch-canvas`) is not decoration — it is what
  makes one rule correct on three different backdrops.
- **A bug that cannot reproduce in development will not be found by development.** The
  session-retention defect needs a *fixed* port; the deployed shortcut pins 8321 while every dev
  launch takes an ephemeral one. Same code, different origin, opposite behavior. When an operator
  reports something the team cannot reproduce, check whether the deployment differs from the dev
  path *in configuration* before doubting the report.
- **Adversarial review pays even when the plan is careful.** Red-teaming the approved plan
  overturned four of its proposed fixes before any of them were built — most sharply, that pausing
  the heartbeat to save CPU would have let `idle_grace` shut the tool down after ten minutes
  minimized and **lose the operator's whole session**: a data-loss defect introduced by a
  *performance* item. Also: agents that die mid-run must never be counted as agreement — 9 of 17
  audit verifiers died on credit exhaustion and the harness bucketed their findings as "refuted"
  by a falsy check. Unverified is not cleared.

### 2026-08-01h — A recorded prerequisite can hide a false premise of its own (batch 3c-ii)
- The 3c-i handoff recorded 3c-ii's prerequisite as "teach the visual harness to CLICK the Run
  buttons (#jclRun, #ssiRun) on /sra" — accurate, and still understated in a way that would
  have sunk the naive build: **the golden pair cannot exercise those panels at all.** The JCL
  panel is cost-gated (`cost_loaded_total > 0`, the honest-SCL rule) and Project2/Project5
  carry no budgeted cost, so the golden `/sra` renders NO `#jclRun` and no `sra_jcl.js` tag —
  a harness that "clicked the buttons" there would have waited on a button that does not
  exist. And with no Best/Worst spread set, `/api/sra/ssi` returns a ONE-point S-curve —
  captions measured on a degenerate chart. Ten minutes of empirical probing (boot the app with
  the goldens, GET the page, hit both APIs) surfaced both facts BEFORE any harness code was
  written. Lesson (the 2026-07-31 "a handoff is a claim, not a fact" lesson, recurring in a
  new costume): a prerequisite recorded by a PRIOR session is still a claim — re-derive what
  the fixture can actually RENDER before building measurement on top of it. The fix was the
  ADR-0325 dedicated-serve precedent generalized: a clicked cell gets its own serve
  (`served_sra`, synthetic cost-loaded + `sra_bcwc` spread) and the golden cell stays
  byte-identical to what the prior batch measured.
- Anti-masking pairs with clicking: on a page whose self-running charts already caption, "some
  captions rendered" is a DEAD assertion for an on-demand panel. The strict per-host wait
  (`#jclCharts text.ch-at`, never suppressed) plus a per-route caption floor (12 = 6 charts
  × 2) is what makes the clicked cell falsifiable — and the able-to-fail proof used exactly
  that lever (stash the modules, watch the TimeoutError name the host).
- Yield-mechanism choice is data-shape-driven, now twice recorded: rotated TICKS yield by
  live-box REMOVE (many, redundant, theme-width-dependent — ADR-0319); a CORNER DATA LABEL
  that collides by construction yields by static band-clamp (removal would delete it every
  render; vertical separation is theme-width-independent — the dwell precedent, now the
  football's quadrant %-labels). Picking remove for the football would have silently deleted
  two quadrant shares from every render.

### 2026-08-01l — Wait for the measurement, then let it kill your theory (Phase 1b / ADR-0334)

- **Blocking on one measurement for two sessions was the right call, and the data proves it.** The
  two candidate mechanisms — "the second launch died mute" vs "Windows let two servers bind the
  same port" — needed OPPOSITE fixes. The measurement showed the second launch produced **no
  listener and no process at all**, killing the double-bind theory outright. A bind-error reporter,
  the obvious fix under the other theory, would have changed nothing. **When two hypotheses imply
  different fixes, the cost of guessing is not "a bit of rework" — it is shipping something that
  looks like a fix and is not.**
- **A measurement that contradicts the source is a measurement to re-take.** The operator's first
  run showed the server dying 25 s after the browser closed. That contradicts `idle_grace=600`, so
  before building on it the code was checked for any faster stop path (there is none — only the
  Quit button). The run was called invalid and re-run; the second matched the code exactly. Had the
  first been accepted, the conclusion would have been "the tool shuts down cleanly, there is no
  bug" — the precise opposite of the truth.
- **Bank a hard-won datum on its own, before the code that uses it.** The measurement took three
  attempts on a machine only the operator can reach. It was committed alone (docs-only) before any
  implementation started, so no later failure — running out of context, a bad merge, a mistaken
  `git checkout` — could cost another round trip to a human. **Irreplaceable inputs get their own
  commit.**
- **Read a security linter as a question, not a nuisance.** Bandit's B310 on a new `urlopen` was
  trivially silenceable with a `# nosec`. Asking *why* it flags urlopen surfaced a genuine Law 1
  hazard: urllib's default opener reads system proxy settings, so on a corporate-managed laptop
  even a `127.0.0.1` request can be routed through the company proxy — refused, or sent
  off-machine. The codebase had already solved this once in `ai/ollama.py`; the new code had
  silently re-introduced it. **The lint was noise; the reason behind it was not.**
- **A test that fails on correct code is a broken model, not a broken system — fix the model.** The
  first proxy gate asserted the opener contained a present-but-empty `ProxyHandler`. It failed
  against the correct implementation. `ProxyHandler({})` installs no `<scheme>_open` methods, so
  `OpenerDirector.add_handler` never registers it: a hardened opener carries **no** `ProxyHandler`
  at all, and absence IS the property. The temptation is to delete the inconvenient assertion;
  the right move is to learn the API and assert the true property, with the reasoning written down
  so the next reader does not re-make the wrong assumption.
- **NEVER `git checkout <file>` to undo a temporary test mutation.** Reverting a prove-able-to-fail
  edit that way discarded every unstaged change in `launcher.py` — the entire round's
  implementation. Recovered only because a scratchpad copy existed. **`cp` from a scratchpad copy;
  `git checkout` is for files with nothing of yours in them.**
- **Deferring half a phase is a decision to state, not a scope to quietly shrink.** The disk-cache
  half of Phase 1b was held back because it is a CUI-at-rest policy call with a real cross-session
  warm-start trade-off — it needs the operator's intent, not an inference from a launcher
  measurement. It is named in HANDOFF ⇢ NEXT with its implementation points, so deferral costs
  nothing but is visible to everyone.

### 2026-08-01k — Optimise the metric before the code, and check the pump you were told about (Phase 2 / ADR-0333)

- **The unit you measure decides whether you can see your own fix.** The obvious meter for a
  MutationObserver storm is "how many `querySelectorAll` calls per insertion". It is the wrong one.
  After scoping the three observers to their records the call count was **flat** (150 → 150 on
  `/analysis`) and on one page it *rose* — each batched root now gets its own query. The property
  that actually changed is what each call has to **walk**: nodes returned went **1,368 → 84**
  (~16x). Had the gate been written against call count it would have read as "no improvement" and
  the fix would have been reverted as useless. **Pick the metric from the mechanism, not from
  what's easy to count** — and if the first metric shows nothing after a change you have reasoned
  through, suspect the metric before the change.
- **Verify the brief's own premises against the code before building on them.** The carried plan
  named `tooltips.js:71-79` in the observer fix. Reading it first showed it was **already**
  records-based — it is the exemplar to copy, and the real offenders (`vizhints.js`, `gantt.js`,
  `chartframe.js`) were only found by grepping every `MutationObserver` in `static/`. A handoff
  pointer is a lead, not a finding. (READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING earned its
  keep twice this round.)
- **A client-side guard cannot fix a server-side loop, and "it already pauses" deserves one more
  question.** The brief listed `sysmon.js` (2 s) as an idle pump. It already skips its fetch while
  `document.hidden` — so the client half was fine and it would have been easy to tick it off.
  Asking *what does that fetch actually start* found `web/system.py::_slow_loop`: a `while True`
  daemon spawning two subprocesses (two `powershell` children on Windows) **every 5 s from the
  first request until the process exits**, which no amount of `document.hidden` can reach. That is
  the operator's long-standing "probes from launch to quit", root-caused only because the pump was
  followed across the client/server boundary instead of being checked off on the client side.
- **An observer that writes to the DOM re-arms itself.** `stickyScrollbar` appends its proxy bar to
  `<body>`; `attachColumnMovers` appends a grip `<span>` to every header cell. Both run *from* a
  body-wide `childList` observer, so every insertion was paid for **twice** (measured: 80
  `table.gantt-grid` sweeps for 20 inserts, not 40). Records-based scoping fixes this for free —
  the echo's own record carries no table — where an rAF debounce alone would not have, because the
  echo lands in a later frame. **When an observer callback mutates, check whether its own writes
  fall inside what it observes.**
- **`querySelectorAll` returns DESCENDANTS ONLY, so scoping an observer is a correctness change,
  not just a perf change.** Handing an attacher the node that was inserted breaks it silently if
  that node *is* the target (an async Gantt inserted as a bare `.gantt-scroll` would lose its
  scrollbar). Every scoped walk needs a `root.matches(sel)` test before the descendant query — and
  that check earned its own gate, because nothing else would have failed.
- **The harness lies quietly: `node --check a.js b.js` checks only the FIRST file.** The documented
  gate command uses a glob, so 59 of 60 modules were never syntax-checked by it. Loop per file.
- **A byte-freeze pin is a question, not a verdict.** `gantt.js`'s digest pin exists to catch a
  caption/axis/tick moving. Re-baselining it is legitimate *only* after showing the property it
  guards cannot have changed — here: the diff is confined to three attachers and the boot IIFE, the
  module has zero `axisTitles` sites (asserted independently by a census test that stayed green),
  and no drawing function is in the diff. Record the old→new digest and the reasoning inline, as
  that file's own convention already does.

### 2026-08-01f — The measured pass catches what content tests cannot (batch 3c-i)
- Adding a bare `SFChartFrame.axisTitles` call to volatility.js passed EVERY content ledger
  (census, 24-site freeze, byte-digest) and node --check — and broke the entire /volatility
  page: the module draws synchronously at parse time and its script tag loads BEFORE
  chartframe.js, so the first draw threw `SFChartFrame is not defined` and every chart died.
  Only the MEASURED visual pass saw it ("no captions rendered" in all 12 cells). This is the
  third member of the ADR-0316 defer family (/performance, /resources before it); the lesson
  is now standing in HANDOFF: check the page's script ORDER before calling any SFChartFrame
  API from a parse-time renderer, and fix with `defer` on the tag, never a call-site guard.
- Scope honesty split batch 3c: sra_jcl/sra_ssi render only on a Run click, so their captions
  are UNMEASURABLE by the current visual harness — shipping them "captioned" this round would
  have been the exact vice the ledgers exist to prevent (a conformance claim nobody measured).
  3c-i ships the measurable half; 3c-ii's prerequisite (a click-driving serve) is recorded in
  the PENDING comment, the ADR, and HANDOFF ⇢ NEXT. A ledger that shrinks honestly beats one
  that empties fast.

### 2026-08-01e — Module-scoped browser fixtures meet the app's own dedup (PR-10, OR-03)
- The new chromium suite's first run failed in a way the feature couldn't explain: the
  gesture-flow test uploaded the same golden bytes an EARLIER test had already loaded into the
  module-scoped served app, ADR-0259's byte-identical dedup collapsed it ("skipped
  byte-identical upload"), the server redirected home instead of `/analysis/...`, and the
  test's `wait_for_url` burned its full 30 s. The app behaved exactly as designed — the TEST
  design forgot the app has memory. Lesson: in a module-scoped browser suite, any test that
  lets its upload COMPLETE must use bytes no earlier test loaded (Project2 vs Project5), and
  the fixture comment should say so; the alternative (function-scoped servers) buys isolation
  with ~6 uvicorn boots per run.
- Two reusable Playwright patterns landed with the suite: (1) NEVER sleep inside a sync-API
  route handler — it runs on the event loop and freezes the very waits the test then issues;
  park the route object in a list and `continue_()`/`fulfill()` it from the test body, which
  turns "the load phase" into a deterministic, test-controlled window (held POST ⇒ assert
  mid-load state ⇒ release ⇒ assert landing). (2) To prove a gesture-only autoplay policy,
  wrap `window.AudioContext` with a counting delegate in `add_init_script` — construction
  counts make "no context before a gesture / exactly one per gesture / a programmatic change
  primes nothing" assertable without ever asserting sound.
- Sound design under Law 2's cousin ("fidelity over speed" has a UI cousin: honesty over
  flash): the operator's "no audible seam" requirement dissolves entirely if the sound is
  GENERATIVE — a shuffled pitch bag has no loop point, so there is nothing to mix. Choosing
  synthesis over a ≥60 s asset also kept ~10 MB out of the wheel + nine installers. The
  operator's ear remains the acceptance (fallback held, ADR-0328).

- CI postscript: the round's ONE CI failure was `from tests.web.test_accessibility import
  _AUTOPLAY_JS` inside a test — importable locally (sys.path luck), `ModuleNotFoundError` on
  CI. Never import one test module from another here; pin cross-module invariants by TEXT
  (read the sibling file, assert the literal), which is also the stronger assertion.

### 2026-08-01d — A verification you remember making is not a verification (the codex round on PR-9b)
- An external automated reviewer raised five findings on #501; all five survived my
  re-verification, including one that overturned a sentence in the round's own ADR: I had
  "verified" that `_target_panel` already wore the head strip, but the `_panel_head` call I
  read was the /path WORKSPACE panel a few hundred lines away — real code, wrong function.
  The wrong belief then propagated into an ADR consequence bullet AND a route comment
  ("the focus panel carries controls of its own") that shaped the include-gating design.
  Only an independent reader caught it. Lesson: when a claim names a specific helper, the
  verification must read THAT helper's return statement, not a nearby lookalike — and a
  claim repeated in two places is not twice as checked, it is one unchecked claim with two
  copies.
- The population-mismatch pair (chips built from every loaded version while the panels draw
  the CPMError-skipping subset) is a class worth naming: **any decoration that DESCRIBES a
  population must be derived from the same code path that COMPUTES the population** — two
  loops that "obviously agree" drift the day one gains a skip. The fix factored the loop to
  one owner (`_solvable_scoped_versions`) instead of duplicating the skip in the chip line.
- Also confirmed the round's refusal discipline pays: all five bot findings were about the
  panels' HONESTY (attribution, population, missing contract), none about the ⤓ refusals —
  the covers-what-it-draws bar held under independent review.

### 2026-08-01c — A refused button needs the same proof as a wired one, and a census pinned from one tree proves nothing (PR-9b / ADR-0327)
- The rank-12 sweep's hard part was not adding toolbars — it was deciding, per panel, which
  glyph would LIE. Every ⤓ decision came down to reading what the export endpoint actually
  emits (the margin workbook's two sheets; `wbs_breakdown_tables` being exactly the two
  page pivots; the workbench catalog stopping at 21 entries — no Fuse/SEM anywhere) rather
  than what its name suggests. Two refusals were live-state refusals (margin's Zero-margin
  toggle, workbench's per-render `&cols=`) — the r10 static-attribute defect class shows up
  wherever a panel has options, and the check is mechanical: does anything on the panel
  change what the pinned URL would return?
- Absence assertions pass vacuously on ANY broken tree, so every "no ⤓ here" test pairs
  with a presence assertion in the same chunk (`_panel_titled` asserts unique + glyph set
  `== {"big"}`), and the ⤓-liveness loop pins per-page COUNTS — on the pre-change tree the
  collector finds zero exports and the count pin is what fails. Watched: 12 of 14 tests
  fail stashed; the 2 both-tree passes are deliberate invariants (empty states clean;
  panel census EQUAL pre/post — a census pinned only from the post-change render could
  never catch panel minting, so the stash run is part of the test's provenance, recorded
  in its docstring).
- The no-filter /groups "Active scope" panel taught the branch lesson again: the SAME
  heading is a status notice in one branch and a data visual in another — the toolbar
  belongs to the branch with the reach table, and the first test draft (toolbar on the
  heading wherever it appears) failed honestly against the deliberate notice branch.
- Sequencing gotcha for the ritual: the pyproject bump landed after the full background
  suite launched, so that run's installer-lockstep tests red-herring against the old wheel.
  Bump → rebuild wheel+installers → THEN launch the suite (or re-run tests/installer after
  and record that number). Promoted to the handoff's harness notes.

### 2026-08-01b — A vacuous pass hides in "the page loaded"; make the fixture EARN the assertion (PR-9a / ADR-0326)
- The chromium slot proof failed three times before it could pass, and every failure was the
  FIXTURE's, not the mechanism's: /path renders NO timescale without a session target,
  /driving-path renders none without a trace, and the first trace pair tried (26 → 143 —
  both critical) is not a DRIVING pair, so the server embeds no corridor at all. Lesson:
  for a rendered assertion, first prove the thing the assertion lives ON actually renders
  under the fixture — otherwise the test would have "passed" against an empty page the
  moment the wait was softened. The vacuity conditions are now recorded IN the test file.
- "Critical together" ≠ "driving": two activities can share the critical set while the
  driving-path tracer correctly refuses the pair. The distinction cost a probe cycle;
  it is exactly the kind of domain nuance worth writing down where the next fixture
  author will trip on it.
- Mechanism placement beats mechanism cleverness: the timescale caption could have ridden a
  MutationObserver (zero frozen-file edits) but would rebuild-race /evolution's animation
  frames and the Timescale dialog's repaints forever. One deliberate, named, re-baselined
  edit in the frozen shared builder makes the slot exist WHENEVER the header exists, by
  construction. A freeze is friction, not a wall — pay it once, in the open, in the ADR.
- The `cmd | tail` exit-code trap bit AGAIN ("1 file would be reformatted" behind a
  clean-looking pipeline) — second hit in two days. The guard that keeps catching us is
  earning its place in the handoff verbatim: read the tool's own summary line.

### 2026-08-01 — A guard someone already wrote is a load-order hazard sign, and only a measured run reads it (PR-8 / ADR-0325)
- Adding the first `SFChartFrame.axisTitles` call to `margin_dashboard.js` threw
  `SFChartFrame is not defined` and killed BOTH charts — the module executes at parse time,
  chartframe.js loads in the layout footer. The tell was already in the file: its last line
  guards `if (window.SFChartFrame && SFChartFrame.scan)`. Lesson: an existing defensive guard
  around a dependency is DOCUMENTATION that the dependency can be absent at that point; before
  adding a direct call to the same dependency, ask why the guard is there. The fix was the
  established family fix (`defer`, ADR-0316 — third member), not a new invention.
- No static check could see it: node --check, ruff, the ledger tests, and the census all
  passed on the broken page. The first REAL chromium run failed 12/12 combos instantly.
  Lesson: for UI work, the measured pass is not a formality — schedule it before believing
  the change works, and treat "the sibling modules do it unguarded" as evidence about THEIR
  load order, not yours (they render on DOMContentLoaded or are themselves deferred).
- localStorage is per-ORIGIN: serving `/margin` from a second app instance meant the
  theme/scale writes silently bound to the FIRST origin until the navigation order was fixed
  (land on the target origin, then write, then reload). A cross-origin fixture is easy to get
  subtly wrong in a way that still "passes" — the probe would have measured default-theme
  pages. Verify the knob actually turned, not just that the page loaded.
- The operator's Jacked-2 re-upload closed OR-05 exactly as the prior session predicted
  ("the pipeline already flows it") — and the verification cost one MPXJ conversion + one
  byte-diff because the fixture had been committed as the file's VERBATIM conversion. Lesson:
  pinning a fixture as "verbatim conversion of X" makes "did X really change / does the
  fixture match reality" a one-command check forever; cheap provenance discipline pays off
  on the first real-world file swap.

### 2026-07-31 — An aggregate's pool must be stated IN the figure — and the heading must state the pool the code APPLIES (OR-01 / ADR-0321)
- OR-01's core ask ("the title alone must say latest vs average") had a second layer the
  heading alone couldn't carry: the mean's POOL shrinks when an included version doesn't
  solve (its audit never ran — averaging a fake 0 would poison the figure, Law 2). Putting
  `· N versions` inside the cell made the pool size part of the number itself, so a
  solvability drop is visible exactly where the analyst reads the value. Lesson: when a
  stated rule has a data-dependent population, disclose the population WITH the value —
  a heading is a constant, the pool isn't. And the review round caught the first-draft
  heading saying "all included versions" while the code (correctly) dropped unsolvable ones —
  a spec-supplied title is still subordinate to R13: the heading states the rule as APPLIED.
- Baking a derived figure into an existing memo inherits the memo's invalidation contract —
  audit it BEFORE adding the field. `margin_days` rode into the ADR-0291 card memo whose
  epoch key covers filter/target/parity but NOT the margin overlay; `/margin/confirm` cleared
  only the summary tier, so `/api/dashboard` served a stale (fake-zero) margin while two
  other surfaces served the engine's new value — reproduced live by the adversarial review,
  fixed by clearing the memo beside the summaries, pinned by a regression test that fails on
  main. Lesson: a cache key is a claim about what can change the value; adding a value the
  key doesn't cover falsifies the claim silently.
- Fixture degeneracy is a finder's dream: every margin in the first-draft fixtures was
  exactly 0.0, so a hardcoded 0 would have passed every margin pin. A name-based "Schedule
  Margin" task made the engine value 2.0 d and a one-line guard (`margin not in (None, 0.0)`)
  makes the degeneracy impossible to reintroduce. Lesson: for every "verbatim" pin, ask what
  OTHER implementation would also pass it — 0.0, "", and [] are the classic impostors.
- The four-lens adversarial fan-out (find → per-finding refutation agents → lead re-verify)
  earned its cost in one round: three confirmed implementation defects and two test-quality
  gaps on a diff that had already passed the full gate, statics, and a proved-able-to-fail
  run. Green gates prove the pinned contracts hold — they say nothing about the contracts
  nobody wrote. The refutation stage matters as much as the finding stage: one plausible
  "5/8/5 guard is weak" finding was PROVEN false by brute force and correctly discarded.
- Golden-SHA payload pins and additive fields coexist cleanly IF the re-baseline rides the
  pin's own path and a row-level only-delta proof lands in the same commit (key-set pins on
  every card shape + engine-verbatim value checks). The ADR-0296 precedent (key REMOVAL with
  a row-level equality proof) generalized unchanged to key ADDITION.
- `ruff format --check . | tail` swallowed a real failure ("1 file would be reformatted")
  because the echoed `$?` was tail's — the exact `cmd | tail; echo $?` trap the harness notes
  already warn about, hit live this session by the session's own author. The guard exists
  because it keeps catching us: read the tool's own summary line, not the pipeline's exit.

### 2026-07-31 — Two "targets" that look synonymous are a population scope and a view focus (ADR-0320)
- PR-6's first draft pinned `/export/evolution?target=3` ≡ "session target 3" — the
  architecture proved the test wrong, not the code: `SessionState.scope()` truncates every
  version's POPULATION to the session target's driving subtree (`subschedule_to_target`,
  inside `_solvable_versions`), while the URL `?target=` is a view focus on the full
  population. The deterministic xlsx writer localized the fork instantly: one cell flipped
  (project finish 2025-01-20 → 2025-01-06). Lesson: when two inputs look synonymous, diff the
  actual OUTPUTS before pinning equivalence — and pin the MIRROR (export matches the page in
  each state), never the equation; a byte-deterministic export format is a first-class
  debugging instrument for exactly this.
- Scope-statement fidelity has a format asymmetry: the xlsx renderer never shows a TableSet
  title (sheets come from per-Table titles, 31-char cap), the docx uses it as H0 — so "the
  heading states the applied scope" needed TWO carriers (title suffix for Word, a prepended
  "Applied scope" sheet for Excel). Checking what each renderer actually consumes BEFORE
  designing the heading saved a truncated-sheet-name trap.
- Runner instability is a plannable constraint: the container restarted repeatedly, killing
  three background gate runs and the planned multi-agent verify fan-out, and wiping pip each
  time. What worked: statics foreground-first (results locked in), tree re-diff + reinstall
  after every resume, long pytest treated as re-runnable, and the verify pass done as a lead
  self-review of the full diff. Files survive restarts; processes don't — sequence the work so
  the tree is always the checkpoint.

### 2026-07-31 — Measured-box assertions must be scroll-invariant (ADR-0317)
- Playwright's `bounding_box` is viewport-relative, and a real click legitimately SCROLLS (the
  control's own `scrollIntoView`): the first draft of the scatter one-⛶ test failed its restore
  assertion on a box whose width/height/x had restored to the pixel — only Y differed, because
  the page was scrolled somewhere new. Assert the scroll-invariant axes (width/height/x) for
  both the move and the restore; Y proves nothing either way on a fixed overlay.
- Same round, same class as the ADR-0314 scrollbar lesson: the probe environment's geometry
  semantics (hidden scrollbars, viewport-relative boxes) must be understood before trusting a
  green — or a red.

### 2026-07-30 — "Engaged" is not "used": a lifecycle flag set only in Settings cannot represent default-config use (OR-04 / ADR-0315)
- The GPU leak survived because THREE mutually reinforcing defects each looked like another's
  absence: shutdown gated on a Settings-only flag (default-config Ask-the-AI never set it), the
  engaged path's own cleanup ORPHANED the model runner (parent terminated before the `/T`
  tree-walk could use it as the root), and every failure was invisible (`check=False` result
  discarded; listing failures silently `return 0`) — the tool *believed* it cleaned up. The
  operator's two manual "process not found" taskkills were the shipped code's exact output.
- Method lesson: the operator's adversarial audit prompt (report-only, prove-or-refute, treat
  docstrings as claims) caught what my own first design missed — the PR-1 draft kept the broken
  unload→terminate→sweep order and proposed runner image names instead, which would ALSO have
  been wrong (`llama-server` is llama.cpp's generic binary — LM Studio runs one). **PID-rooted
  ancestry beats image names**, and "a human gates the apply" caught a wrong fix before it landed.
- Silent best-effort cleanup is indistinguishable from success: read the returncode, verify the
  effect (`/api/ps` re-probe), and surface status in the UI — `no-binary` had been write-only
  since it shipped (a silent capability downgrade).
- Harness: `caplog` here needs `logger="schedule_forensics.<module>"` (the redaction layer stops
  propagation — the importer tests had the working pattern); the autouse `SF_CACHE_DIR` fixture
  gave the new durable marker per-test isolation for free — piggyback on an existing isolation
  seam before inventing one.

### 2026-07-30 (cont.6) — headless hides scrollbars, and the audit caught what the probe could not

- **A green probe can be measuring a browser that does not exist on the operator's desk.** The
  OR-02 nav-clamp compared against `window.innerWidth`; every headless probe passed because
  headless Chromium hides scrollbars. On a classic-scrollbar browser (Windows default — the
  operator's actual machine) `innerWidth` is ~15px wider than the layout, the full-width header
  classified as a RAIL, and the callout landed off-screen at a measured 9px sliver. The audit's
  reviewer caught it by reasoning from MDN semantics, then proved it with
  `ignore_default_args=["--hide-scrollbars"]`. **Lesson: any geometry that depends on viewport
  width must be probed WITH layout scrollbars too; and `documentElement.clientWidth`, not
  `innerWidth`, is the layout width.**
- **The audit found the root cause the fix had only worked around.** The DCMA tips are BORN
  visible (no inline display:none at creation; the float CSS computes visible) — all 16 stack over
  the nav on every render, masked only when a load happens to auto-scroll. Two rounds (07-27 and
  this one) had each fixed a SYMPTOM strand; the reviewer read the creation path nobody was
  looking at. **Lesson: when a bug "keeps coming back on every page change", ask what the RENDER
  path does, not just what the event handlers fail to do.**
- **Post-state inspection could not have tested the fix honestly**: the scroll-hide writes the
  same inline `display:none` that birth-hiding does, so "all tips hidden after load" passes on
  broken code. The pinning test observes the style AT INSERTION (MutationObserver microtask, which
  runs before any scroll event can). **Lesson: when two mechanisms produce the same end state, pin
  the mechanism, not the state.** (Same failure shape as the audit's vacuous-pass finding in my
  own test: counting hovered rows instead of measured tips.)
- Harness: `page.add_init_script` runs before `document.documentElement` exists — observe
  `document`. And a mid-session harness resume flip-flopped the uncommitted working tree twice
  (fix → pristine → fix); diff the tree after every resume before trusting it.

### 2026-07-31 — an oracle can contradict its own file, and the bytes decide (OR-05 deep dive)

- **The PowerPoint said −5 d; the .mpp said +13 d.** Slide 6 shows Task 11 with a deadline-driven
  −5 d Total Slack, but the committed `.mpp` carries no Deadline field at all. Resolution came from
  EVIDENCE, not preference: MPXJ provably reads MPP14 deadlines (positive controls: Hard_File
  UID 155, Large-Test UID 157), read none here, and the file's LastSaved (09:23 EDT) predates the
  pptx's final edit (10:29 EDT) — the deadline was added in the live MSP session after the last
  save and never hit disk. **Lesson: when the oracle and the artifact disagree, timestamp the
  artifacts and build a positive control before "fixing" the engine toward either** — the correct
  engine output here (13 d) is the one the slide itself names as the no-deadline outcome.
- **MS Project's stored values are a second oracle riding inside the file.** MSPDI slack fields are
  tenths of a minute; the stored TotalSlack on every off-calendar task (369000 → 36 900 min =
  76.88 d at /480; 37800 → 3 780 = 2.63 edays) told us EXACTLY which axis MSP measures slack on —
  the task's OWN calendar's minutes, displayed over the project's minutes-per-day. The whole
  multi-calendar design fell out of reading those numbers before writing any code.
- **A "safe approximation" pin can hide a real under-measurement for a year.** QC-D2's cap-space
  elapsed slack (pinned {1: 0}) prevented fabricated negatives but silently zeroed REAL slack
  across non-working gaps — the Jacked-1 eDays task (stored 3 780 for the same shape) finally
  proved it. Deliberately re-pinned to 1440 with the oracle cited at the pin. **Lesson: an
  approximation adopted to kill a false negative deserves a follow-up oracle for the false-zero
  direction.** Same shape at TP3: the Fuse workbook's neg-float 3 was captured against an artifact
  FUSE-VALIDATION.md itself marks "to reconcile" (finish differs 5 d from the fixture) — a pin's
  provenance note is what makes a later re-baseline adjudicable.
- **Design-review-before-implementation caught the blocker class cheaply**: the 3-lens ADR-0240
  panel (MSP semantics / architecture / parity blast radius) flagged the start-role int round-trip
  as oracle-contradicting while the code was still unwritten; the implementation propagated wall
  instants between off-calendar tasks instead and the 17-test oracle suite passed first run. The
  blast-radius lens's adjudication split (SSI goldens must not move; fuse per-UID; SRA
  deterministic anchors hold) turned the parity gate from a hazard into the verification plan.
- **OR-06 in one sentence: localStorage outlives the server by design, so server-session state
  cached client-side needs a server-issued epoch.** A per-process nonce + wipe-generation meta tag
  and a compare-then-clear in persist.js closed it without touching ADR-0186's within-session
  memory; the Playwright test seeds the operator's exact stale-Target-UID shape and proves both
  halves (stale cleared, live kept, theme untouched).

### 2026-07-30 (cont.5) — a "blocked" decision may already be half-answered by an old ADR

- Researching the three operator decisions gating rank 12, two of the three turned out to have
  **recorded partial answers nobody had surfaced**: `data-noprint`'s "which CSS mechanism" is
  half-settled by **ADR-0076** (2026-06-18: the print mechanism IS base.css's `@media print`
  block, pinned by `test_accessibility.py:102-109`), which kills the dedicated-print.css option;
  and the `/workbench` toolbar debt is shrunk by **DESIGN-SYSTEM §3:78 "Tables get `⤓ EXCEL`
  only"** — the full ▦/⤓/⛶ triple was never owed on a data table. **Lesson: before escalating a
  "blocked" decision to the operator, sweep the ADR index and the design system for a prior
  recorded decision** — the escalation may be smaller than the queue says, and an option you'd
  present may already be foreclosed.
- The reverse lesson from the same sweep: a recorded *prediction* is not a recorded *decision*.
  ADR-0302's "sra.js and margin_dashboard.js can use `y2Label`" does not survive contact with the
  rendering code (single-axis CDF; one scale, two named units) — quote the code, not the ADR, when
  the two disagree (ADR-0301's own rule, applied to an ADR).
- Handoff staleness, measured: this session's handoff said "#487 needs driving to green" and "the
  figure is OWED" — both were already done (merged 14:47Z, figure posted 12:49Z) before the
  session started. **A handoff written before the round's last actions records intent, not
  outcome; verify PR/comment state against the live system before redoing "owed" items.**
- Harness: a remote-session resume KILLS in-flight background work (a 6-agent research workflow
  died with one verifier mid-flight). The workflow journal + `resumeFromRunId` recovered the five
  finished agents' results without re-running them — background work should always be resumable
  from its journal, and the journal is also where you check what a "completed" agent actually
  returned.

### 2026-07-30 (cont.4) — a piped exit code is not the command's exit code

**The failure, twice in one day, same shape.** I ran `node harness.mjs 2>&1 | tail -20; echo "exit=$?"`,
read `exit=0`, and reported the harness green. `$?` after a pipeline is the **last** command's status
— `tail`'s — so it is 0 essentially always. The harness was exiting **1**. Earlier the same day the
identical shape bit differently: `pytest --timeout=1800` is not installed here, so pytest exited **0**
having run nothing, and the launched-in-background task reported success.

**Both are the same lesson at different altitudes:** a green signal is only evidence if it came from
the thing you meant to measure. `| tail` moves the exit code; an unrecognised flag moves what ran.
The operational rule now written into the handoff: **redirect to a file and check the exit code
directly** (`cmd > out 2>&1; echo $?`), and grep the file for the failure marker as a second,
independent check. Two cheap checks that disagree are far more informative than one that can't fail.

**What the wrong-green was hiding was itself instructive.** The harness had a state-residue bug: it
reset only the `%` field between cases, so the previous case's *days* value was still locked and
`derive()` re-derived a stale `%` — the loop passed for the wrong reason on the cases it did pass.
A test-loop that shares state between iterations is a test-loop whose passes mean nothing, and this
is the second time this project has found a *conformance sweep* that reported the wrong answer
(ADR-0311's probe regexed a pattern that could not match the conforming shape). **Generalises
(→ Part V): before trusting a sweep, break it on purpose.** Reverting `num()` to the old `parseFloat`
and confirming 16 failures is what made the fixed harness meaningful.

**A third, gentler instance of the same discipline paid off immediately.** Twelve integration tests
went red at once. The instinct on twelve red tests is that the code under test is wrong; the actual
cause was `TestClient` following the 303 and *consuming* the one-shot banner before the test's own
`GET`. Had I "fixed" the app I would have broken a working one-shot notice to satisfy a broken test.
**Twelve failures at once is weak evidence about the product and strong evidence about the harness.**

**Also worth keeping: measure the vulnerability before writing the guard.** The completion plan asked
for a "spreadsheet formula-injection guard on export" and pointed at the workbook writer. Unzipping a
rendered workbook showed it emits every string as `t="inlineStr"` and never emits an `<f>` element, so
Excel shows `=1+1` as text — no guard needed, and one would have prefixed a visible apostrophe onto
legitimate exhibit text. The real vector was the CSV sibling, which carries task names straight from
the schedule file. **A plan item is a hypothesis about where the bug is, not a finding.** The durable
form is a test that pins the *absence* of a guard where none is warranted, with the reason — otherwise
a future round adds it back on plausibility alone.

### 2026-07-30 (cont.3) — a note that told the operator something false, caught by the probe

**The lesson.** Enforcing ADR-0310's project-start precondition (ADR-0312) meant emitting an
operator-facing sentence explaining what the importer had changed. I wrote it from my mental model:
*"The date each activity is scheduled on is unaffected; only the time of day shown with it moves."*
It is **false**. The whole point of the normalisation is that the rendered calendar date moves — a
late-in-the-day instant stops spilling onto the following (possibly non-working) date. What is
actually invariant is the **working day**, because `offset_to_datetime`'s whole-working-day term is
a function of the offset and the calendar and never of the anchor's time of day.

The probe I had already run to justify the change contained the disproof — offset 6760 rendered
Saturday 00:40 before and Friday 16:40 after — and I only noticed on re-reading the output rather
than the code. **A disclosure sentence is a claim about behaviour and deserves the same evidence
standard as a computed figure.** It now has one: the reworded note's promise is pinned by
`test_normalisation_keeps_every_activity_on_the_same_working_day`, so the prose and the code cannot
drift apart later.

**Generalises (→ Part V):** in a testimony tool, the explanatory text *is* a deliverable. We already
gate AI-emitted figures against engine citations; hand-written disclosure prose currently has no
such gate, and this is the second time in two rounds that a sentence was more confident than the
measurement behind it (the first being a test result reported without reading the output). The
cheap discipline: **when you write a sentence describing what the code does, name the test that
would fail if it were wrong — and if there isn't one, write it.**

**A second, structural miss found in the same round.** `SCHEMA_VERSION` was left at 2.8.0 when
ADR-0309 added `Task.resume` in #483. The freeze test asserts `SCHEMA_VERSION == "2.8.0"` as a
literal, so updating the expected field set and forgetting the version passes — the guard cannot
see the add it exists to catch. Corrected retroactively in the 2.9.0 bump and recorded in the
change log. **A change-control guard that is satisfied by editing the guard is not change control**;
the same shape as ADR-0310's axis-caption freeze, which was obeyed rather than re-baselined
precisely because a guard you may update when it fires guards nothing.

**One harness trap worth writing down:** `pytest --timeout=...` is not installed here. Passing it
makes pytest exit **0** having run nothing, which in a background task reads as a green run. Caught
only because the previous round's lesson — *a launched run is not a result* — made me read the
output instead of the exit code.

### 2026-07-30 (cont.2) — I reported a green suite I never read

**The failure.** During the ADR-0310 round I launched two full-suite runs in the background, never
read either, and reported "2943 passed, zero failures" in both the chat summary and the PR body. The
runs had actually finished `3 failed, 2940 passed` — three failures caused by that round's own
changes (two axis-caption freeze tests on the `drift.js` edit, one `/trend` label assertion). The
figure was also arithmetically impossible: the real total was 2944, because I had added two tests that
session. Corrected by comment on #485 and in the session log.

**Why it happened, mechanically.** Long runs were started with `run_in_background`, the turn continued
on other work, and by the time the summary was written the *intent* to verify had been substituted for
the verification. Nothing lied deliberately; the number was reconstructed from expectation. That is
precisely the class of error this project spent the same day cataloguing in three external audits —
and it is worse coming from inside, because an internal report is what the durable docs quote.

**The rule that would have prevented it, stated operationally:** *do not put a test result in prose
unless the number appears in output read during that same turn.* Not "unless the tests were run" —
unless the figure was **read**. A launched run is not a result. If a summary is due before a run
finishes, the honest sentence is "suite still running", which costs nothing.

**The compounding hazard: scheduled context inherits the moment's rigour.** The wrong figure was
written into a `send_later` self-check-in as *"Local authoritative full suite: 2943 passed … ZERO
failures."* When that fired it presented my own unverified claim back to me as established fact, with
the word "authoritative" attached. **Anything written into a self-scheduled message or a handoff
becomes evidence later.** Provenance has to be carried with the number — "read from output at
<time>" vs "expected" — or a future reader (including a future self) cannot tell them apart.

**Corollary for this repo specifically.** `docs/STATE/*` and `audit/*` are cited as evidence in a
testimony tool. A doc that overstates a verification is more damaging than one that admits a gap,
because the gap is visible and the overstatement is not. When a merged PR's body carries a false
green claim, the correction belongs on the PR *and* in the durable log — the merge history is part of
the record.

**One narrower lesson from the same round.** A conformance test that checks only for an element's
*presence* passes on content that defeats the requirement: `<h1 class="page-takeaway">Metric
Workbench</h1>` satisfies "has a takeaway h1" while being exactly the topic-headline
`DESIGN-SYSTEM.md` §5 forbids. The rank-12 test therefore asserts the *property* — long enough to be
a sentence, and not the page title echoed back. **Assert the property the rule is about, not the tag
the rule is carried in.**

### 2026-07-30 (cont.) — the bug class is arithmetic between undeclared units

**Two findings, two audits, one unstated contract.** H2 (non-working dates) and H4 (elapsed filter
literals) were tracked as separate defects for weeks. Both external reviews independently said they
share a root and demanded the axes be written down before either was touched. Writing them down took
one document and immediately reclassified one of the two: **V3 stopped being a product decision.**

**The reclassification is the lesson.** V3 was carried as "needs a product decision on elapsed
semantics." The audit found the decision had already been made **eight times** in the codebase
(`1440 if duration_is_elapsed else per_day`), and that MPXJ agreed, and that exactly one module never
got the message. So the honest status was never "undecided" — it was "decided everywhere except
here." **Before recording an item as blocked on a decision, grep for whether the decision already
exists in the code.** A convention followed 8:1 is a convention, not an open question.

**"A wrong constant" is the wrong diagnosis.** `cpm.py:295` is `day + timedelta(minutes=intraday)` —
adding a *working*-minute remainder as *wall-clock* minutes. No constant is wrong; the units are.
That is why it hides on every 8h/08:00 calendar (the axes coincide inside the shift) and only surfaces
past midnight. A defect that is invisible on the entire committed corpus and reachable on supported
input is a units defect, and units defects are found by declaring units, not by testing harder.

**A mislabel can be worse than a wrong number, and it survives longer.** The briefing banner called a
pure-logic CPM date "Forecast finish" — a figure `engine/forecast.py` explicitly documents as *not*
progress-aware — and that label propagated to Mission Control and chapter 12. Three adversarial audits
looked at H6; one declared it disproved because the `/forecast` page labels its four methods
correctly. **It checked the page built to explain the distinction and not the pages that repeat the
number.** The generalisable check: for any figure with more than one legitimate basis, enumerate every
surface that *renders* it, not just the surface that *documents* it. ~50 finish-date surfaces; 7
labelled.

**Silence in a lookup table is a design decision nobody made.** `_FORECAST_METHOD_COLORS` had no
`as_scheduled` entry, so that lane fell through to a default and the one method reporting the source
tool's own answer had no visual identity. Same shape as the missing methodology card and the missing
`basis` in the payload: three independent omissions all pointing at the same method, because nothing
enforced that a method must be complete everywhere it appears. **When a set of things is enumerated in
more than one place, the enumeration wants a single source or a test that they match.**

### 2026-07-30 — before reverse-engineering a reference tool's judgement, check whether it wrote it down

**The five-week bug.** The SRA diverged from MS Project's SSI add-in badly enough that the
deterministic date sat at the P40 of our own distribution against SSI's P5.75, with σ 1.94x too wide.
ADR-0108 had diagnosed the same underlying gap on 2026-06-21, tried twice to fix it, reverted both
times, and concluded the rule *"cannot be reverse-engineered safely from two data points."* That
conclusion was correct about the fix that was attempted and wrong about the problem: MS Project stores
its own answer in MSPDI's `<Resume>`, and the importer read `<Stop>` and threw `<Resume>` away.
`Resume + remaining = the stored finish`, exactly, on the very task the prior attempts got wrong.

**The generalisable rule.** We framed it as *"what rule does the reference tool use to decide?"* — a
modelling question — when it was *"where did the reference tool record its decision?"* — a parsing
question. `_stored_date_bounds` (ADR-0034) had already established exactly this pattern for
*unstarted* tasks, with a docstring that even says "Started work is untouched". The started-task half
was simply never built. **When a reference tool's behaviour looks like an un-modellable judgement,
enumerate its file format's fields before building a model.** A discarded field is cheaper to find
than a scheduler is to reverse-engineer.

**An unconditional fix to a conditional behaviour will regress the cases the tool deliberately left
alone.** Both prior attempts floored *every* in-progress task at the data date. EVM2 UID 20 needed
moving (`Resume` 15 days after `Stop`); EVM1 UID 18 did not (`Resume == Stop`, remaining work
legitimately behind the data date). One rule, two required outcomes — so any rule without the
file's own discriminator had to break one of them. **A fix that cannot express "leave this one alone"
is not yet a fix.**

**My own fix was wrong first, and only measurement caught it.** The initial floor used the *stored*
remaining duration, which pins an in-progress task's finish regardless of the sampled value and
destroyed the Monte-Carlo's upside variance: all 2000 iterations finished on or before the
deterministic date. It improved **3 of the 6** headline metrics and would have read as progress in any
summary that did not check the maximum. The tell was `max == deterministic` and `det_pctile = 100%` —
a distribution with no upside is not a risk analysis. **Check the shape, not just the moments.**

**The oracle was in the repository the whole time.** Two external adversarial audits and our own
evidence file all classified the SRA question as oracle-gated and asked the operator to produce a new
artifact. The SSI export for the exact reference file was already committed under
`00_REFERENCE_INTAKE/ssi/`, and the `.mpp` carried SSI's entire SRA *input* set in custom fields.
Three independent passes recorded "unavailable" without enumerating the reference directory.
**"Oracle-gated" is a claim about the repository, and it needs an `ls` before it is written down** —
the cost of not checking was five weeks and three audits.

**Corollary on reference-tool exports: reproduce their summary cells before trusting them.** SSI's
exported `Mean Date` and `Standard Deviation` are computed over its 245 *distinct* histogram dates with
the occurrence weights dropped, while its cumulative-probability column is properly weighted. Chasing
the summary cell would have meant matching a 1.665x inflation, and our working-day σ sat close enough
to it to look like success. A parity target should be **derived from the reference's rawest available
data**, and a test should pin the trap shut so nobody "improves parity" toward the artifact later.

### 2026-07-29 (cont.5) — a guard one code path can walk around is not a guard

**What happened.** ADR-0307 corrected the SSI Best-Case rule and stopped the simulation randomising
completed work. It merged. An outside reviewer then found **three** ways the fix did not actually
hold, and every one of them reproduced under execution.

**The pattern, which is the lesson.** Correcting a rule in the place it is *computed* is only the
first of four jobs. The fix is not done until you have also closed:
- **the second writer of the same state** — the risk register still added its impact to the very
  activities the new guard had just point-massed (P90 moved 20 working days on finished work);
- **the persisted copy of the old output** — saved setups stored Best/Worst values computed by the
  old formula, and the loader preferred them over the corrected calculation, so an operator loading
  a setup silently re-ran the exact bug that had just been fixed, forever;
- **the reader that still displays it** — the grid kept showing a range the engine had stopped using.

Ask, every time: *who else writes this state, who has a saved copy of the old answer, and who still
reads it?* A guard that one code path can walk around is not a guard.

**Persisted derived values are a migration problem, not a formula problem.** The moment a computed
value is written to a file an operator can reload, correcting the formula stops being sufficient.
Version the schema and migrate — and when the stored data cannot distinguish *derived* from
*hand-entered* (ours could not), say so out loud and let the operator choose, rather than picking
silently. We asked; they chose recompute-where-a-factor-exists; the cost is written into the ADR.

**An outside review can be right — verify, then act, and do not let being burned before become a
reason to dismiss.** The ADR-0306 round taught that outside findings must be re-verified because some
are wrong. The correct conclusion was never "outside findings are wrong"; it is "**verify by
execution, then act on what survives**". Here all three survived, one of them naming a committed
fixture by exact value (UID 427, BC 432 on ML 480). Both failure modes are real: credulously
accepting a bad finding, and reflexively dismissing a good one. The defence against both is the same
executable check.

**A fix that ships, is believed, and is silently bypassed is the worst outcome available.** Worse
than not shipping — because the tool now carries a documented claim to be correct on a path where it
is not. That is what the saved-setup hole was, and it is why it was worth a same-day follow-up rather
than a backlog entry.

### 2026-07-29 (cont.4) — a validation that only samples the degenerate case validates nothing

**What happened.** The operator reported a Law-2 fidelity defect: the same SRA run gave materially
different answers in POLARIS and in MS Project. Root cause #1 was a formula inverted since ADR-0123 —
the SSI Risk Factors table's first column is the Best Case **as a percentage OF** the Most Likely, and
`factor_to_bc_wc` read it as a percentage **to subtract**. It had been wrong for 184 ADRs.

**Why it survived so long — the actual lesson.** At factor 1 the two readings coincide: `1 − 0.50 ==
0.50`. The docstring claimed the rule was *"validated to match SSI's stored Best/Worst Case durations
exactly"*, and the unit test called itself the *"headline parity anchor"* — but the test asserted the
**code's own arithmetic**, and the single line in it that agrees with the reference is the factor-1
line. A validation drawn from the degenerate band passes under either reading. Measured against the
reference tool's own stored values, the old rule reproduced **153/919** — and *every one* of those was
factor 1, with **zero** of the 765 rows at factors 2–5.

- **A parity test must assert values that came from the reference tool, not values recomputed by the
  code under test.** If a test would still pass when the formula is inverted, it is not an anchor.
- **Check that your fixture set spans the discriminating cases.** Any band where two candidate rules
  agree is worthless as evidence. Ask "which rows could distinguish these?" before claiming validation.
- **Sanity-check a formula against what its parameter is supposed to MEAN.** The inverted reading gave
  every risk factor the identical ±0.6·ML spread and merely slid the mean — i.e. a *risk ranking
  factor* that changed no uncertainty. The correct reading holds the triangular mean at a constant
  0.8667·ML and widens only the spread. That semantic contradiction was visible without any reference
  data at all, for 184 ADRs, and nobody looked.

**Root cause #2, and a rhyme with yesterday.** Duration uncertainty was being applied to 100%-complete
activities: MSPDI omits `<RemainingDuration>` on a finished task, so `rem if rem is not None else
duration` handed the **full original duration** to the sampler and the run re-randomised work that had
already happened. This is ADR-0306's "an absent figure is not a zero" with the **opposite sign** — the
absent figure was read as the *full* value. And `_is_completed`'s own docstring already said *"A
completed activity carries no schedule uncertainty"*: **the invariant was written down in the codebase
and silently violated on one code path.** A documented invariant with no executable guard is a comment.

**The hardest judgment call, and the one worth remembering.** Fixing *only* the completed-work defect
lands the mean at +132 against MS Project's +111 — *closer to the target* than fixing both (+27). It
would have been easy, and defensible-sounding, to keep the inverted Best-Case rule because the numbers
"looked better". That is two errors cancelling, and it is exactly what Law 2 forbids. **Fix what is
provably wrong against the reference; never tune a formula to hit a target number.** The round shipped
saying plainly that parity is *not* achieved and naming the one artifact that would settle the rest.

**Also learned.**
- **The reference input may itself be the reference oracle.** The `.mpp` carried SSI's own stored
  Best/Worst Case durations on 919 activities plus its whole risk register in custom fields. Reading
  the input file's custom fields *before* theorising turned an algorithm argument into a measurement.
- **Verify the reference tool too.** MS Project's own summary cells (B6 Mean Date, B7 Standard
  Deviation) are computed over the 245 *distinct* histogram dates with the occurrence weights
  discarded — they disagree with its own histogram. Had we anchored on them, the near-match of
  POLARIS's "110.9 working days" to MSP's "107.82 days" would have argued the spread was nearly right,
  when it is 2.5× too wide. **A reference number that disagrees with its own underlying data is not a
  target.**
- **Reproduce end-to-end before reasoning about the algorithm.** Converting the `.mpp` costs ~30 s and
  2000 SRA iterations run in ~90 s. The reproduction matching the operator's screenshot on *every*
  figure is what made every later claim trustworthy.
- **Run a Monte-Carlo bisection against an unpatched tree, and record run provenance next to every
  number.** A mid-run edit does not affect an already-imported module, but the *next* run picks it up:
  two variants that should have differed came back byte-identical because the new engine guard had
  already neutralised the input.

### 2026-07-29 (cont.3) — a green gate proves nothing if the binary isn't the one CI runs

**What happened.** The ADR-0306 correctness pass went out with a locally-green
`ruff format --check .` — "431 files already formatted" — and CI failed immediately on the same
command, reporting **801** files and two reformats. The gate had not been skipped or fudged; it had
been run against the **wrong binary**. `which -a ruff` showed a stale `/root/.local/bin/ruff` (0.15.8)
shadowing the pip-installed `ruff` (0.16.0), and CI resolves `ruff>=0.6` to the latest. **ruff 0.16
formats fenced ` ```python ` blocks inside Markdown; 0.15 does not** — hence 431 files vs 801, and a
failure mode that was structurally invisible locally.

**Lesson: `>=`-pinned dev tools make "I ran the gate" an ambiguous claim.** Invoke them as
`python -m <tool>` so the resolved dependency runs, not whatever is first on `PATH`, and when a local
file *count* differs from CI's, treat that as the signal — it is a version difference, not noise. The
count was right there in both logs and would have caught this before the push.

**Second lesson, the more interesting one: a formatter must never edit evidence.** The obvious fix —
let ruff reformat the audit markdown — was wrong. Ruff wanted to collapse a quoted `dcma14._r` snippet
into a 103-column one-liner; in the real file that statement is indented inside a function and stays
multi-line, so accepting the reformat would have produced an audit report whose "verbatim quote"
**does not appear anywhere in the tree**. In a testimony-context tool that is precisely the failure the
audit was written to prevent. Fixed with `[tool.ruff.format] exclude = ["audit/*.md"]` and a comment
saying why, so the next person does not helpfully "fix" it back. **Where a document's value is
fidelity, tooling that rewrites it is a correctness bug, not a convenience.**


### 2026-07-29 (cont.2) — the refutation that was itself wrong, and the accusation nobody had tested

**What happened.** An outside auditor handed us seven defects. Verifying them by execution confirmed all
seven in substance — but the two things that mattered most were not on its list.

**Lesson 1: adversarial verification has to cut both ways, including at the lead.** On V5 a verifier
refuted the *lead's own* written finding, and it was right: removing the `or 1.0` on `resources.py:171`
alone makes reported over-allocation **worse**, because the zero-capacity bucket it produces is then
skipped by `over_allocated`'s `capacity_minutes > 0` guard. The intuitive one-line patch flips a real
flag `True → False`. On V6 the opposite happened — a verifier's refutation was itself wrong, because its
5,000-trial randomized probe varied calendars and offsets but **never the project start's time of day**,
the one dimension the bug lives in. A big-N probe that holds the causal variable fixed is not evidence of
absence; it is a confident null. **Both were settled the same way: re-run it yourself before accepting a
verdict, whoever produced it and whichever direction it points.**

**Lesson 2: in a detector, a silent default is not a wrong number — it is a wrong accusation.** The worst
thing found was not on the outside list at all. `manipulation.py` compared `(cur.actual_cost or 0.0) <
(prior.actual_cost or 0.0)`. An update that merely stopped carrying its Actual Cost column therefore read
as a rollback, producing four findings — two HIGH — instructing the analyst to investigate *"expenditure
being hidden or moved"*. The false positive was **byte-identical** to the true one: same `metric_id`, same
title, same severity. Mixed-source version series (P6 → MSP, a changed export template) are the *normal*
case in a delay claim. The model layer already encodes the right rule (`| None` means "the source did not
provide it", and `CLAUDE.md` says *never assume 0*) — the engine just wasn't honouring it. **Wherever the
output is an allegation rather than a figure, the cost of a silent default is measured in credibility, not
decimals.**

**Lesson 3: `gt` versus `ge` decided 47 of 67 sites.** The repo-wide sweep looked daunting and collapsed
almost entirely to two model constraints: `Calendar.working_minutes_per_day` is `gt=0`, making 46
`or 480` / `or 1` / `or 0` fallbacks **dead code**; `Resource.max_units` is `ge=0.0`, making one `or 1.0` a
live defect that fabricates capacity. **Audit the validators first, then the call sites** — one character
in a model definition classified most of the table, and no site should ever be called SAFE without naming
the specific guard and executing it.

**Lesson 4: report the clean results too.** `evm.py` and `dcma14._r` were hunted on their most plausible
failure hypotheses (SPI/CPI divide-by-zero returning a plausible 1.0; an empty DCMA population rendering a
fabricated 0% that reads as PASS) and both are **correct** — `_r` even carries the Law-2 rationale in its
docstring. Saying so plainly is worth more than padding a findings list, and it stopped a "fix" that would
have broken working code. What it *did* surface is a layering inconsistency worth its own round: the engine
returns `NOT_APPLICABLE` for an empty population while the web layer reaches for `or 1` divisor guards and
prints `0.0%`.

**Lesson 5: know which fixes you are not qualified to make today.** Four findings shipped as documentation
only — CC-01 (74 call sites, a design decision about an unenforced precondition), CC-05 (parity literally
cannot distinguish floor from truncate on our goldens, so it needs the reference tool), V3 (a product
decision), V1/V2 (needs UI work, so the five standing UI requirements apply). Writing down *why* each was
deferred is what keeps the next session from "just patching" them.


### 2026-07-29 (cont.) — a pin that cannot fail is not a pin, and the gate moved up a level

**What happened.** Round 11's whole thesis is ADR-0304's *"verify the EFFECT, not the MECHANISM"*, and
it shipped a test module built around exactly that: two tests that click a control for real and assert
`getBoundingClientRect()` changed. Post-merge adversarial verification then asked the one question
nobody had: **can that test actually run where it is enforced?** It could not. Both assertions are
`importorskip("playwright")`-gated, `playwright` was in no extra and no CI step, and the proof was
decisive — the same deliberately-broken tree (a one-line markup edit that re-inerts ⛶, measured: the
box does not move) reports **23 passed WITH playwright** and **21 passed / 2 skipped WITHOUT it, exit
0**.

**Why it matters more than an ordinary gap.** This is round 10's failure class reappearing one level
up. Round 10 shipped a *control* that flipped a class and moved nothing; round 11 shipped a *test* that
skipped and proved nothing. Both are "the machinery ran, so it must be working" — and the second is
more dangerous, because a dead control is visible to a user while a skipped test is visible to nobody.
**Every `skipif`/`importorskip` in a gate is a silent exemption. Ask of each one: what regression does
this test exist to catch, and in which environment does it actually execute?** If the answer is "none
that CI runs", the requirement is decorative.

**The fix, and the shape worth reusing.** Three parts, deliberately layered so the cheap one always
runs: (1) a **browser-free structural guard** asserting the shipped markup still matches the CSS
selector the mechanism depends on — it caught both injected regressions, and with it deselected the
same broken tree goes green, so it is load-bearing rather than decorative; (2) a **separate CI job**
with the browser, which **fails loudly if the tests skip** (a skip is now an error, not a pass); (3) a
**daylight-theme assertion**, because every other rect assertion ran in the default theme and ADR-0305's
most subtle decision — rejecting a `vw` inset because daylight has no left rail — had nothing pinning
it. *A guard that only runs in the easy case is the same bug in miniature.*

**And a lesson about the reporters, not just the code.** Of the three verifiers, one refuted the round's
flip count (184 → "188"); the adjudicator re-derived it and **refuted the refutation** — 184 was right.
Another declared an instrument corrupt for a reason that turned out to be wrong, while the instrument
*was* in fact broken for a different reason. Both times the correct move was the same: **re-derive, do
not arbitrate.** Verify the finding, never the reporter's confidence.


### 2026-07-29 — three lessons from round 11: a control's effect, a shared tree, and a lying instrument

**1. When you give a control an effect, measure that effect in EVERY theme — the obvious geometry can
be right in three of four.** ADR-0304 taught "verify the EFFECT, not the MECHANISM." Round 11 fixed the
block-layout ⛶ by borrowing the geometry the project already shipped for standalone charts
(`.sf-tilebox.tile-expanded`, `inset:4vh 3vw`) — the textbook reuse move, and it would have been a
defect. **Daylight has no 236px left rail**, so its panels are 1384px wide while console/apollo/jarvis
are 1148px; a `3vw` inset yields **1354px**. Measured on `/scurve` daylight: panel `1384x752 → 1354x828`
and the chart svg `1354x436 → 1324x426` — **⛶ would have made the chart smaller in one of four themes**,
reproducing round 10's `/performance` failure *inside its own fix*. `inset:3vh 12px` is
theme-independent. The reuse instinct was right; the assumption that "reused = safe" was not. **A
borrowed mechanism inherits the assumptions of the context it was written for.**

**2. `git stash` is not read-only, and "read-only agent" is not a property you can assert in a prompt.**
The verification workflow told three adversarial agents to `git stash` for a pristine comparison — a
reasonable-looking instruction. They share ONE working tree. Verifier L1 stashed the entire round out
from under verifier L3 (mid-measurement, curling export URLs against what it believed was the patched
tree) **and** out from under the lead's concurrent full `pytest`. Nothing in any agent's own log would
have revealed it; it was caught only because the lead happened to re-read `pyproject.toml` and saw the
version had reverted to 1.0.120. **Isolation is a property of the ENVIRONMENT, not of the instruction.**
Any agent that needs to mutate the tree — even transiently, even to restore it — gets
`isolation: "worktree"`. The recovery was clean (snapshot the stash as a patch *before* touching
anything, stop the run, pop, verify md5s) but the real cost would have been a **false all-clear**, which
is the failure mode this project keeps paying for.

**3. An instrument that cannot reproduce its own baseline is worse than no instrument.** The lead
generated the requirement-5 axis-caption baseline by hashing a balanced-paren slice starting at each
`axisTitles(` match. It **missed one of `trend.js`'s five call sites** (a nested paren inside a string
broke the scan) and **included `chartframe.js`'s function definition**. An implementer reported it as
unusable — for a partly wrong reason (it claimed nine duplicate hashes; there were none) — and the lead
re-derived from scratch, found the flaw was real but different, retired the file and replaced it with a
whole-file md5 census of the 12 owning files. Two compounding lessons: **(a)** a gate that reports 16/16
changed on an unmodified tree trains the next agent to ignore red results, which is strictly worse than
having no gate; **(b)** *the agent was right that the instrument was broken and wrong about why* — the
correct response was to re-derive, not to accept or dismiss the report. Verify the finding, not the
reporter.

**4. Load the fixture the way the product loads it.** Without the browser's `file_meta` companion JSON,
the five TP4 snapshots upload as five one-version projects, and `/evolution` + `/volatility` render
their "load at least two analyzable versions" **fallback**. Four pages were surveyed in that empty state
before the lead noticed the pages were suspiciously thin — the same shape as round 10's `/resources`
mistake ("a page with no chart is not a missing caption — check WHY"). A harness that boots the app is
not the same as a harness that reproduces the user's session.


### 2026-07-28 (cont. 9) — merging mid-round does not just ship unverified code, it BLINDS the verifier

**What happened.** PR #473 was merged with 7 of 12 agents complete. Beyond shipping three pages
without any verification, it had a second-order effect nobody would predict: both adversarial
verifiers compute their Law-2 "no number moved" proof by diffing the working tree against
`origin/main`. Once the round's own code was merged **into** `origin/main`, that comparison went
blind for three of the four pages — it would have reported "nothing changed" for changes it could
no longer see. The baseline had to be re-pinned by hand to `a7a06fc`.

**The lesson.** Any verification defined relative to a *moving* reference silently degrades when
the reference moves. Pin baselines to an **immutable commit**, not to a branch name. And if a round
must be merged early, re-pin every in-flight baseline explicitly rather than assuming the checks
still mean what they meant when they were written.
### 2026-07-28 (cont. 8) — a finding can be REAL AS AN OBSERVATION and WRONG AS AN ATTRIBUTION

**What happened.** The no-op above was reported — by a verifier, then by the orchestrator to the
operator twice and in a PR body — as *"round 10 shipped 43 dead ENLARGE buttons"*. The CSS analysis
was correct and independently reproducible. The **attribution was false**: `.is-big` is
byte-identical at the round-9 baseline `a7a06fc`, which already carried 43 `_shell_tools` call
sites across `_analysis_body`, `_evm_body`, `_scurve_body`, `_portfolio_body`, `_ribbon_body`,
`_compare_body` and ~20 more — and measures the same no-op there (`/scurve` 2/2, `/portfolio` 2/2,
`/integrity` 4/4, `/evm` 4/4). It is a pre-existing property of the merged panel contract; round 10
replicated the merged convention onto four more pages.

**Why it matters.** The two readings imply different fixes. "Round 10 broke it" implies revert or
block the round. "The contract has always been half-defined" implies a global `base.css` decision
that touches ~9 merged pages and would move captions on `/scurve`, `/curves` and `/trend` —
forbidden by requirement 5 without an operator decision. Acting on the wrong one would have been a
mistaken fix, which this log has repeatedly recorded as worse than the drift it chases.

**The rule already existed.** Round 9 wrote down *"check merged `main` before calling a pattern a
defect"* after flagging `/trend`'s ⤓ buttons that turned out to be byte-for-byte the shipped
Mission-wall precedent. It was not applied here until the lead forced the baseline re-check.
**A rule you wrote down is not a rule you followed — verify the baseline before every attribution,
including your own.**

### 2026-07-28 (cont. 7) — a check that confirms the MECHANISM fired can pass while the FEATURE does nothing

**What happened.** Round 10's four-theme verifier measured `getBoundingClientRect()` on the closest
`.panel` immediately before and after every real ⛶ ENLARGE click and found that 8/8 buttons on
`/cei`, 12/12 on `/resources`, 23/23 on `/forecast` and 20/20 on `/evm` moved **zero pixels** in all
four themes. The cause is one line: `.is-big{grid-column:1/-1}` is the class's only rule, and
`grid-column` binds only on a grid item; those panels' parent computes `display:block`.

**Why it survived a standing requirement written to prevent exactly this.** Requirement 2 exists
because round 4 shipped `/evm` with a complete toolbar and no `panelkit.js`. It says: *prove the
script loads and click ⛶ for real, reading `is-big` back*. That assertion **succeeds perfectly**
here — the script loads, the click lands, the class toggles, the label flips to `⛶ SHRINK`. The
requirement asks whether the machinery ran, not whether anything happened.

**The generalisable form.** Every check this project has had that passed while the feature was
broken shares one shape: it asserted that the mechanism fired. The script loaded. The class
toggled. The token was defined (requirement 1's "a defined token is not a painting token"). The
caption existed (ADR-0298's first detector compared captions only against other captions, blind to
the collision that actually happens). **Ask what would be visibly different to the operator if the
feature worked, and measure that.** Requirement 2 is amended accordingly (ADR-0304).



### 2026-07-28 (cont. 6) — a contract's SCOPE must match the page's structure

- Round 9 hit the first case where applying the panel contract literally would have made the UI
  worse: /curves' panels host exactly ONE chart, so adding a `_shell_tools()` ⛶ to the head
  would have put a SECOND "⛶ ENLARGE" on the same panel; /trend's single panel hosts 20 charts,
  so a shared panel-scoped `.is-big` would desync 20 labels. The fix was scope-aware — /curves'
  existing strip button carries `data-sf-big` (one button, panelkit owns the state), /trend keeps
  its ⛶ chart-scoped and takes the contract strip in the sibling panel heads.
  **LESSON: a design contract is a VOCABULARY, not a stamp. Before applying it to a page, count
  what the panel actually contains — panel-scope vs visual-scope controls are different controls,
  and applying the wrong one produces duplicates or desynced state, not consistency.**
- The lead rejected the round's one reported deviation by checking origin/main and finding the
  pattern already shipped there byte-for-byte (the Mission wall's per-chart ⤓ buttons).
  **LESSON: "this looks wrong" and "this differs from what we already ship" are different
  findings. Check merged main before calling a pattern a defect — otherwise you hold a branch to
  a standard the product does not meet, and the 'fix' silently becomes a scope change.**

### 2026-07-28 (cont. 5) — when the VERIFIER dies, the work is unverified

- Round 8's lead agent failed on an infrastructure condition (usage credits exhausted) after both
  verifiers had returned clean. The tempting read is "two greens, ship it" — but ADR-0240 puts the
  lead there precisely because verifiers have been wrong before. The orchestrator performed the
  lead role itself on a different model: re-ran the scope check, the loaded-terms control, every
  static gate, the mandated suites, and the critical parity audit (ribbon matrix values dumped
  from an origin/main worktree vs the working tree — byte-identical).
  **LESSON: an orchestration step can die for reasons unrelated to the work. Distinguish "the
  check passed" from "the check ran". When a verification step fails to complete, the work is
  UNVERIFIED regardless of what the other steps said — perform the role yourself or hold.**
- Round 8 also shows the right shape for a derived display string: the ribbon tooltip's verdict
  word is read off the class `_ribbon_cell_class` already assigned, not recomputed from the value.
  **LESSON: when a UI needs to restate a judgement the engine already made, read the engine's own
  artifact (the class, the enum, the status) — recomputing it creates a second source that can
  disagree with the first under exactly the inputs a testimony context will scrutinize.**

### 2026-07-28 (cont. 4) — match the proof to the page's hazard; a core queue closes

- /portfolio's hazard was state-posting forms, so the round's proof was shaped to it: byte-diff
  every <form> block against an origin/main worktree in TWO states (baseline + after-exclude),
  then exercise the exclude→restore round trip live — done independently by the implementer,
  the gate verifier, AND the lead. **LESSON: a generic gate proves generic safety; each page's
  conversion needs one proof shaped to that page's specific way of breaking (forms → byte-diff
  + round trip; drill JSON → byte capture; EVM → no-arithmetic diff audit).**
- The prototype's pf tiles use a LEFT edge where ctl's use a TOP edge — a token-pure .k-edge
  VARIANT was added instead of repurposing ctl's classes. **LESSON: when the design system has
  two near-identical vocabularies, extend with a named variant rather than bending the nearest
  existing class — the cascade pin test then documents the difference.**
- With rank 7 shipped, the redesign's 7-rank core queue is complete in 7 PRs over ~24h, the
  last five rounds zero-defect. The standing-requirements list (jarvis probe + promotion
  census, panelkit real click, loaded-terms control proof) is what made the streak possible —
  every one of them exists because an earlier round shipped the defect it now prevents.

### 2026-07-28 (cont. 3) — the clobber trap fires on PROMOTION, not just on new classes

- Round 6 promoted two existing styled divs (isolated-effect, counterfactual) to `.panel` for the
  shell — and jarvis's broad `.panel` rule immediately flattened the 3px severity edges app.css
  had been painting. Third firing of the same family, new trigger: not a NEW class this time but
  an existing element GAINING `.panel`. The standing computed-style probe caught it pre-verifier;
  the hud.css jarvis-scoped restoration is now the established fix, pinned by a browser test.
  **LESSON: audit theme-broad rules on every class ADDITION to an element, not only on new CSS —
  `class="panel X"` means X now competes with every broad `.panel` override in every theme.**

### 2026-07-28 (cont. 2) — prove the gate can fail before trusting its passes

- Round 5's loaded-terms audit (testimony-critical on /compare) passed 12/12 strings — and the
  lead only accepted it after running a known-dirty CONTROL ("deliberate concealed fraud")
  through ai.citations.introduces_loaded_terms and watching it return True. **LESSON: a guard
  that never fires in your session is unproven — pair every all-clean audit with one control
  case that MUST fail, in the same run, before believing the clean results.**
- Also promoted this round: the round-4 "script include + one real click" manual step became a
  permanent playwright-gated regression test (test_compare_panelkit.py) — checklist items that
  survive two rounds belong in the suite, not the checklist.

### 2026-07-28 (cont.) — markup can be complete while the page is inert; click it

- Round 4's implementer found /evm wearing the FULL panel-contract toolbar markup with zero
  behavior: panelkit.js is a per-page include and /evm never loaded it. No static check catches
  this — the markup is correct, the CSS paints, node --check passes. It was caught by CLICKING
  ⛶ ENLARGE in real chromium and reading `panel.is-big` back. **LESSON: for every page converted
  to the shell, the checklist is "script include present + ONE real interaction probed", not
  "markup matches the contract". A selector footnote: _page cache-busts static src to `?v=…`,
  so exact-match script-src selectors false-negative — match on a substring.**

### 2026-07-28 — a repeated defect family ends when the probe becomes a standing requirement

- Three same-family defects in one session (apollo scanline clobber, jarvis --bgfx dead token,
  jarvis verdict-band clobber): hud.css's broad per-theme rules silently out-rank new
  panel-contract classes. Round 3 made the fix procedural — the implementer must PROBE every new
  class's computed style in jarvis before claiming four-theme support, and the fidelity verifier
  re-measures it — and round 3 came back the session's first zero-defect SHIP.
  **LESSON: when the same defect family bites twice, stop fixing instances and change the
  process: encode the check as a standing per-round requirement (a measurement, not a reminder),
  and put it in BOTH the builder's and the verifier's mandate.**
- Mechanism worth reusing: version chips as plain links (selection = the URL) let the existing
  persistence ride for free — the cheapest way to avoid forking state is to not create state.

### 2026-07-27n — the first theory of a UI bug must survive the browser; and re-run surprising mutation kills

- **Diagnosing the stranded float tip, the first theory (hover + scroll) was falsified by its own
  mutation test**: chromium synthesizes mouse events on scroll, so the hover path self-heals and
  the "fix" was untestable. The reachable path was focus/touch (`tabindex=0` rows + no `blur` on
  scroll) plus a degenerate 0x0 anchor. **LESSON: for event-lifecycle bugs, enumerate every path
  that SHOWS the artifact (hover, focus, touch, timer) and every event that can END each one —
  the stuck state is whichever show-path has no reachable hide-event.**
- **A mutation "kill" flaked**: removing a defensive guard failed the test once (6.5s run) and
  passed on re-run (2.6s). Claiming that guard as mutation-proven would have been false.
  **LESSON: a surprising mutation kill gets one immediate re-run before it is believed — a flaky
  kill manufactures exactly the confidence mutation testing exists to prevent.**

### 2026-07-27m — a collision report names TWO boxes; I read one and assumed the other (ADR-0303)

- **The failure.** The four-theme visual pass reported two caption collisions (`/cei` 14x6px,
  `/trend` 6x10px). I wrote them down as *"the Y caption sits where the top gridline's label
  already is"* — reasoning from the chart source, not from the measurement. That framing turned a
  local defect into a convention change, and it is what the operator was asked to decide between.
  Measuring the actual boxes falsified **both** halves: on `/cei` the top gridline label clears the
  caption by **13px** and the real neighbour is a **bar value label**; on `/trend` the colliding
  caption is the **X** caption, which no Y-placement rule touches.
  **LESSON: an overlap is a relation between two rectangles. Identify BOTH from the measurement.
  Naming one and inferring the other from source reading is a guess wearing a measurement's
  clothes — and it survived four commits, an operator decision, and a full implementation.**
- **The cost of adopting before measuring.** The chosen rule ("Y caption above the plot, adaptively
  when the band is free") was implemented and passed its unit harness — then measured, and it chose
  *inside* on **all four** charted pages, changing nothing, at the cost of a caption whose position
  moves with the data. **LESSON: a green unit harness proves the rule does what you wrote. It says
  nothing about whether the rule was worth writing. Run the justifying measurement BEFORE adoption.**
- **What actually fixed it, in two lines.** Placement stays fixed (ADR-0298); the *data label*
  yields where it enters a caption's band. Generalises without touching the shared helper.
  **LESSON: when a shared convention and a local detail collide, move the local detail first —
  the convention's cost is paid by every chart, the detail's by one.**
- **A dangling `ADR-0303` citation was found in code merged one commit earlier**, crediting a
  `/forecast` fix that had been reverted, on a page not even in that test's `PAGES`.
  **LESSON: an ADR number written into code before the ADR exists is a forward reference that
  outlives the revert it described. Cite an ADR only once its file is on disk.**
- **Packaging trap.** `python -m build --wheel` writes to `dist/`; `build_installers.py` defaults to
  `dist/wheel/*.whl`. It silently embedded the previous version's wheel and produced nine
  installers byte-identical to HEAD — a version bump that shipped the old version. The gate does
  pin the embedded version to `pyproject`, so it would have failed. **LESSON: the failure mode to
  fear from a defaulted path argument is a silent no-op. Verify the artefact, not the exit code.**

### 2026-07-27l — a task that stays owed across four ADRs is a task nobody can repeat (ADR-0302 addendum)
- **The four-theme visual pass was owed since 2026-07-27b and survived four ADRs untouched.** Not
  because it was hard — because it was *unrepeatable*: eyeballing four themes x three scales x
  every chart page is ~100 screenshots, and nobody re-checks 100 screenshots. Decomposing what
  "legible" actually asserts — contrast, computed size, real uppercase, clipping, collision — made
  it a 22-second test that measured 144 caption renders and came back clean.
  **LESSON (generalizes → Part V): when an item stays owed across sessions, the problem is usually
  its FORM, not its priority. Ask what it would take to make it repeatable; a manual check that
  nobody repeats is a check that isn't being done.**
- **I took a shortcut for cost and encoded the assumption it rested on — which is the only reason
  it was safe.** Factoring the matrix (colour per theme, geometry per scale) cut 72 page loads to
  22 on the reasoning that themes only redefine colours. The step-0 assertion failed immediately:
  apollo is `font-family:'IBM Plex Mono'`, so caption widths genuinely differ per theme, and
  apollo's wider glyphs are the likeliest clip. **LESSON: when you optimise a check by assuming
  two dimensions are independent, assert the independence in the same change. The shortcut then
  invalidates itself instead of quietly halving your coverage.**
- **A check for "X is missing" must distinguish "the thing carrying X never rendered".** The first
  run flagged `/resources` and `/margin` as having no captions. Both were right to have none: one
  needs a resource picked from a dropdown, the other needs tasks named "margin". **LESSON: an
  absence assertion needs a presence precondition, or it manufactures defects — and a
  manufactured defect costs the next session more than a missed one, because it sends them hunting
  something that was never there.**
- **Three self-inflicted harness traps, none of them product defects, all costing real time.**
  `wait_until="networkidle"` never settles against an app that polls (heartbeat 3s, sysmon 2s);
  `| tail` buffers a long run to EOF, so the progress prints added *specifically* to make it
  observable were invisible; and **`pkill -f <pattern>` kills the shell running it** when the
  pattern appears in that shell's own command line — which produced two "failed" runs that had
  nothing wrong with them. **LESSON: when a job hangs or dies, suspect the harness before the
  subject. I diagnosed the product three times before diagnosing my own tooling once.**

### 2026-07-27k — when you add an optional parameter, test the DEFAULT path (ADR-0302)
- **The dangerous mutant was not the new feature failing — it was the new feature firing when
  nobody asked.** Adding an optional `y2Label` to the shared caption helper, the four mutants I ran
  included "emit it unconditionally". That one adds a third caption to **every existing caller**,
  silently, and no assertion about the *new* behaviour catches it. Only an explicit "omitting
  `y2Label` leaves existing callers at two captions" does. **LESSON (generalizes → Part V): an
  optional parameter has two contracts — what it does when supplied, and that nothing changes when
  it is not. The second is the one that breaks callers who never heard of it, and it is the one
  people forget to assert.**
- **Extending a convention is not the same as breaking it — but only if you can say why.** ADR-0298
  established "one convention" for axis captions, so a third label looks like a violation. It is
  not: the rule is one *implementation*, one *token*, one *placement law*, not "exactly two
  labels". Y2 goes through the same node builder and the same `.ch-at` class, so the queued
  type-ramp change still moves one value. **LESSON: before extending a rule, restate what the rule
  actually protects. If the extension preserves that, it is an extension; if you cannot restate it,
  you are probably forking the convention.**
- **A decision that belongs to the operator should be surfaced BEFORE the batch that needs it, not
  during.** Batch 2 hit the combo-chart problem, captioned the primary pair, and recorded the gap
  rather than improvising. Asking at the boundary meant one decision unblocked three modules
  (`wbs`, `sra`, `margin_dashboard`) instead of three separate mid-batch judgement calls that would
  have been hard to reverse. **LESSON: when a gap will recur, stop and name it; a convention
  invented under batch pressure gets copied before anyone reviews it.**
- **A build step that rewrites N files is not interruption-safe.** Regenerating the nine installers
  hit the 120s foreground timeout in batch 2, was killed mid-write, and left `tier3.ps1` a version
  behind `tier1`/`tier2` — caught only by the cross-tier drift check. Run it in the background
  where it cannot be halved. **LESSON: for any generator that writes a set, treat "it was
  interrupted" as a real state and keep the check that proves the set is internally consistent.**

### 2026-07-27j — test a proposed classifier against the whole population, not the case in front of you (ADR-0301 addendum)
- **My "better" regex was worse, and only running it over every module caught that.** The ledger's
  proxy for "is this a chart" (grep the SVG namespace) had just mis-classified `path.js`, so I wrote
  a sharper one — an `<svg>` root *and* a declared plot rect — and, before swapping it in, ran it
  against all 30 modules. It mis-classified **five**: `performance.js` and `margin_dashboard.js`
  name their geometry `L/R/T/B` rather than `padL`; `resources.js`, `sra_jcl.js` and `sra_ssi.js`
  build through a local `svg()` factory rather than `svgEl("svg")`. It *also* still called `path.js`
  a chart. **LESSON (generalizes → Part V): a discriminator that is right about the case in front of
  you and wrong about five others is a regression dressed as a fix. Run a proposed classifier over
  the entire population and diff it against the current classification before adopting it — the
  disagreements are the whole point.**
- **When a property cannot be computed, price the exception instead of faking the computation.**
  The fix was not a cleverer heuristic but an explicit `INCIDENTAL_SVG` list: the module, the
  reason, and a test closing the three ways an escape hatch becomes a dumping ground (an entry not
  in the parent bucket; an entry that never needed excusing; an entry that has since gained
  captions). Parking a real chart there now costs two deliberate edits and a written justification.
  **LESSON: an escape hatch is safe in proportion to how expensive and visible it is to use.**
- **An ADR's incidental factual claims inherit no authority from its decision.** `path.js` sat in
  the wrong bucket because ADR-0298 asserted it "does draw SVG axes" — inside a *corrections* list,
  which is exactly the context that reads as already-verified. It draws a DOM table plus one
  two-element SVG connector overlay. **LESSON: a decision record is authoritative about the
  decision. Its supporting observations are still claims, and they age.**
- **`| head -2` SIGPIPE-killed the installer generator after ONE of nine files.** I piped
  `build_installers.py` to `head` to keep the log short; `head` exited after two lines, the producer
  took SIGPIPE, and the run died mid-sweep leaving **2 installers at the new version and 7 at the
  old**. Exit status looked fine because the pipeline's status is `head`'s. The lockstep guard
  caught it (5 failures), which is precisely the ADR-0148 incident it was written for — the
  operator once reinstalled and got stale JS. **LESSON: never pipe a command that WRITES artefacts
  into `head`/`grep -m`/any early-exiting reader. Redirect to a file and summarise afterwards.
  Truncating a log is not free when the producer is still working — and a half-finished artefact
  set is worse than none, because it looks complete.**
- **The failure arrived as "5 failed" in a background run I could have waved away.** The previous
  entry's lesson (a background suite is a snapshot) cuts both ways, and this was the other way: it
  was a real, current defect. What separated the two cases was ten seconds of diagnosis — reading
  which test failed and checking the artefacts by hand (`grep` the embedded version out of all nine
  installers) — not a prior about background runs.
- **Name the gap, do not improvise across it.** `wbs.js` is a combo chart whose right axis the
  shared helper cannot caption. Captioning the primary pair is strictly better than two unlabelled
  axes and says nothing false; inventing a second convention mid-batch would have undone ADR-0298.
  Recorded as a decision owed, with the two modules that will also need it.

### 2026-07-27i — a caption is an assertion; a spec written without running the app cannot make it (ADR-0301)
- **Four of the five captions I was told to apply were wrong about what the chart plots.** The
  applyable spec's §3 table said `curves.js` plots cumulative dollars (it plots activity counts),
  `resources.js` plots FTE demand per week (it plots work booked in **working days** over a
  runtime-chosen day/week/month bucket), `cei.js` has a secondary ratio axis (it has none — the CEI
  figure is a text callout), and `drift.js` plots version-vs-slip (it plots forecast **dates**
  against three forecast **methods**). Every one was caught by reading the rendering code before
  writing the caption. **LESSON (generalizes → Part VI): a caption is an assertion about what the
  reader is looking at. On a testimony tool, transcribing one from a document written without a
  running app is the same defect class as a false `[ok]` — our own output stating something we
  could have checked and didn't. Derive labels from the code that draws the pixels.**
- **A correction landed and the things derived from it were left standing.** ADR-0298 corrected the
  census — eleven modules render no SVG — but the spec's §5 *batch table*, which is derived from
  that census, was never revised. So its batch 1 is 4/5 DOM visuals the SVG helper cannot serve, and
  anyone following it would have written five calls that could not work. **LESSON: when you correct
  a premise, grep for what depended on it.** This is the same shape as yesterday's "correcting a
  figure is a grep, not an edit", one level up: it applies to premises, not just numbers.
- **A guard that cannot be completed should say so and name what does converge.** `histogram.js`
  turned out to carry a *third* local caption implementation past the two ADR-0298 retired; the
  `SECOND_CONVENTION` regex missed it because the regex pins variable names (`xt`, `yt`) and this
  one used `cap`. Widening it to `cap.textContent` would fire on two modules that use `cap` for
  legitimate non-axis text — a name-based regex simply cannot decide whether a `<text>` node is an
  axis caption. **LESSON: rather than widen a guard until it produces false positives, record the
  limitation and name the property that actually converges — here, the `PENDING` ledger reaching
  empty, at which point every SVG chart provably calls the helper.**
- **Defer with the reason written into the artefact, not the PR.** `drift.js` needs a caption
  decision *and* a layout nudge its batch may not make, so it stays in `PENDING` with both reasons
  as a comment in the ledger — where the next session reads it, rather than in a merged PR body
  nobody re-opens.
- **A long-running background test job is a snapshot, not a verdict.** The full suite reported
  `test_handoff_top_section_pins_the_current_pyproject_version` FAILED. It was real at the moment
  that test executed — the run had started before the handoff was rewritten, so it compared the old
  handoff (1.0.105) against the new `pyproject` (1.0.106) — and it was already false by the time I
  read it. **LESSON: when a background suite reports a failure, re-run THAT test against the current
  tree before believing it OR dismissing it.** Both errors are available here: believing a stale
  failure wastes a fix, and waving one away as "probably timing" is how a real defect ships. The
  cheap discriminator is a targeted re-run plus checking the two values the assertion compares.
- **A squash-merge orphans any SHA captured before it.** `mpxj_ref()` pins the last commit touching
  `tools/mpxj`; the pin shipped in v1.0.105 is **not an ancestor of `main`**, surviving only on an
  unmerged branch, so the operator's converter download depended on that branch not being deleted.
  Regenerating moved it onto `main`. **LESSON: a squash-merge gives identical content a NEW SHA. Any
  workflow that captures a commit SHA as a durable pointer must re-resolve it against `main` after
  the merge, or it is pinning something that can vanish.**

### 2026-07-27h — a guard that greps prose measures the documentation, not the behaviour (ADR-0300)
- **The guard I wrote to prevent a CI leg from being silently deleted passed with the leg gutted.**
  It asserted that the windows job mentioned `Junction`, `SymbolicLink` and `subst`. Mutating the
  reparse-point loop to `@("Directory")` left every explanatory comment naming both shapes in place,
  so the test stayed green. Removing every `subst` *call* left a `::warning::` string mentioning
  subst, so it stayed green again. **LESSON: when asserting that something RUNS, read comments and
  step names out of the text first, then pin an invocation (`& subst`, `$env:X =`,
  `New-Item … -Target`) rather than a word.** A well-commented file is the easiest thing in the world
  for a text guard to pass. This is the same family as "a string pin detects a rewording, never a
  falsehood" (2026-07-27f) seen from the other side: there the literal was too tight, here it was too
  loose, and both times the fix was to ask *what behaviour is the contract?*
- **I found it only because I mutation-tested my own new test, not just the code it guards.** The
  standing rule (ADR-0298) says mutate the guard; the temptation is to mutate the *product* and call
  it done. Six mutations, each required to fail, took about two minutes with file backups.
- **A leg that cannot fail is indistinguishable from a leg that passes.** Two legs shipped last
  session did exactly that: one satisfied itself from the checkout while appearing to prove a
  download, another swallowed a mid-run abort because a later command reset `$LASTEXITCODE`. So each
  new leg here permanently carries a mutation step that breaks the guard in a scratch copy of the
  installer and requires the leg's own assertion to fire — including an assertion that the mutation
  *applied*, since a stale needle would silently re-run the unmutated installer and report success.
  **LESSON (generalizes → Part V): the CI step that proves a defect cannot recur needs its own proof
  that it would still notice. Encode it as a step, not as a note in an ADR.**
- **Choosing OFFLINE mode was a correctness decision, not an optimisation.** With the converter fetch
  reachable, a destroyed destination would simply be re-downloaded and the leg would go green over
  real data loss. **LESSON: when a system self-heals, disable the healing in the test that checks for
  the wound.** The same reasoning made the setup step feed the converter from the checkout rather
  than the network — cheap *and* it isolates what is under test.
- **A dangling citation is a claim with no reachable source.** Thirteen shipped sites — nine
  installers, three templates, one test — cited `ADR-0300` for the symlink defect, which had been
  filed as ADR-0299 *Addendum 2*. Nothing failed: `tests/test_state_docs.py` anchors on the highest
  ADR **on disk**, so a citation pointing *past* the end of the record is invisible to it. **LESSON
  (generalizes → Part VI): this tool's whole thesis is that every figure has a citation you can
  follow. Apply it to our own decision record — a reference into `docs/adr/` should be resolvable at
  the moment it is written, and "I'll file it as an addendum" is not the same as what the code says.**
- **An inherited blocker was never re-tested, and it was false.** "The four-theme visual pass needs a
  browser this sandbox cannot automate" had been copied forward across handoffs since 2026-07-27b.
  This container ships Chromium at `/opt/pw-browsers` with `PLAYWRIGHT_BROWSERS_PATH` already set;
  `pip install playwright` plus an explicit
  `executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"` launches it and renders. The
  *real* obstacle was one version skew — the pip driver wants build 1228, the image has 1194, so a
  bare `launch()` dies with "Executable doesn't exist" and reads like "no browser here". **LESSON: an
  inherited "cannot" is a claim with a shelf life. Environments change between sessions; re-test the
  blocker before you re-copy it, and when a tool says "not installed", check whether it means "not
  installed" or "installed at a version I did not expect".** Recorded precisely: the browser is
  verified, the *pass* is not — do not let the correction over-claim in the other direction.
- **A `pull_request` `paths:` filter matches the WHOLE base…head diff, not the pushed commit.**
  Observed, and it contradicted what I had just written in a PR body: a docs-only push to this branch
  re-ran `installer-smoke` (windows + linux) because the PR's cumulative diff still touches
  `.github/workflows/installer-smoke.yml`. Useful both ways — every push to a PR that has ever
  touched installer content re-validates it (good), and each one costs a windows run (worth batching
  commits). **LESSON: `paths:` on `push` filters the commit; `paths:` on `pull_request` filters the
  PR. Do not reason about one from the other.**
- **A count taken from the wrong artefact reads exactly like a verified one.** I wrote "eleven steps
  and seven installs" into an ADR from a glance at the YAML; the log says **ten steps and nine
  installer runs**, and grepping `-File` over the workflow says 14 because `Get-ChildItem -Recurse
  -File` matches. Same family as last session's 50-vs-54. **LESSON: derive a number from the artefact
  that actually produced it — for "what did the job do", that is the job log.**
  **And the sharper half: I corrected it in the ADR and left it standing in the HANDOFF**, where it
  survived four commits inside the doc the SessionStart hook injects into every session. Last session
  learned "a number repeated across three artifacts is one unverified claim copied three times"; this
  session learned its corollary. **LESSON: correcting a figure is a `grep`, not an edit — fix every
  copy in the same commit, or the one you missed becomes the one that gets quoted.**
- **Read-before-write caught three traps in one leg**, none of which would have failed loudly: the
  installer had to be copied out of the checkout or `$PSScriptRoot`'s parent would supply a valid
  source and the link would never be reached; `SMOKE INSTALL OK`, not `DONE`, is the final line in
  smoke mode; and the reparse point had to be deleted with `[IO.Directory]::Delete($link, $false)`
  because `Remove-Item -Recurse` can empty a junction's target — my own test cleanup would have
  reproduced the bug it was testing for.

### 2026-07-27g — I found the bugs I was replacing and missed the ones I was introducing (ADR-0299)
- Across three PRs, six installer defects were fixed. **Three were mine, and an outside check caught
  every one** — a parallel session's report, that session's PR (twice), and a CI leg I had just
  added. My own verification was real and extensive, and it was systematically blind in one
  direction: I exercised the paths I was BUILDING (fresh install, download, offline) and not the
  states a user could already BE IN (an existing converter, a drive root, a symlink).
  **LESSON: enumerate the pre-existing states your change can encounter, not just the flows it
  adds. "Does my new path work?" is a different question from "what can my new path now reach?"**
- **Widening what a step may SELECT widens what it may DESTROY.** All three of my defects came from
  the same root: I broadened the converter search, and each new candidate became a new thing the
  `rm -rf` could point at. I fixed it twice with better path comparison and was wrong both times.
  **What held was staging: read and verify the source completely, THEN swap.** Proved independent
  by mutation — with the path guard disabled the converter still survived, only the message
  degraded. **A detection must be correct on every platform to protect anything; a staging step
  protects even when the detection is wrong. Prefer the defence that fails safe.**
- **Three literal test pins broke on CORRECT fixes in one session.** The worst had guarded the MPXJ
  block for months while asserting the exact sentence that was the lie (`"native .mpp import stays
  OFF"`). **LESSON: a string pin detects a REWORDING, never a FALSEHOOD. Pin a literal only when
  the literal itself is the contract; otherwise assert the behaviour or the invariant.**
- **A green check only proves the branch the job actually walked.** Twice a passing CI leg hid the
  thing it existed to prove: `$PWD/tools/mpxj` is a search candidate, so both my local harness and
  the first windows leg silently satisfied themselves from the repo checkout while appearing to
  test the download. **Read the log for which branch ran; and make the leg ASSERT the branch, not
  just the outcome.**
- **Judge a duplicate PR by its content, never its title.** Two PRs from one parallel session on one
  branch needed OPPOSITE verdicts — #447 was regressive (merging it would have stripped the
  download from main), #449 was additive and correct. Only `git show <branch>:<file> | grep` for the
  markers of the shipped work distinguished them. Reading either PR's own description would have
  gotten it wrong.

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

### 2026-08-10 (e) — two wrong sources agreed with each other; and `ast` columns are BYTES (ADR-0384)
- **What happened:** the session opened attached to `SMAT-SANDBOX` (the mirror, frozen at v1.0.4 /
  ADR-0194 / an unsplit 12,209-line `app.py`) while the resume prompt described POLARIS at v1.0.186
  and asked for phase-3 slice 15. Both were wrong, and they were wrong *consistently enough to feel
  like context*: the prompt's branch name matched the container's branch, and the mirror's own
  `HANDOFF.md` agreed with the mirror's tree. Production was in fact at v1.0.191 / ADR-0383 with
  slices 15–19 already shipped.
- **What worked:** two commands settled it — `grep '^version' pyproject.toml` and
  `ls src/schedule_forensics/web/`. A repo that has done fourteen extraction slices *looks* like it;
  one that has done none cannot fake the module list. Cost: a few minutes, before any work.
- **Lesson (generalizes → Part V):** "READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING" has to
  include **which repository you are standing in**. A resume prompt is a claim about the world;
  so is a handoff; two claims agreeing is not corroboration when they share an origin. Verify the
  artifact, not the narrative — and do it before the first edit, not after the first failing test.
- **The second lesson, paid for in an hour:** `ast` reports `col_offset` as a **UTF-8 byte** offset.
  The pre-flight probe character-indexed it, and every marker on a line carrying `—`/`·`/`⤓`/`⛶`
  landed several columns early. This time it produced a `SyntaxError` at import — the cheap failure.
  On a different line shape the identical skew lands *inside a string literal*, the module imports
  fine, and the probe silently measures a member it corrupted. Splice on `bytes`, and `ast.parse`
  the result before writing it: **a probe that does not parse is not a measurement**, and a probe
  that parses but was mis-spliced is worse than no probe at all.
- **Also:** a free-name pass that finds *nothing* is still evidence. ADR-0383 added it because four
  constants hid from the call graph; running it here and reporting the empty result is what
  separates "this block owns no constants" from "nobody looked."

### 2026-08-11 — three instruments that were measuring themselves (ADR-0386)
- **The sweep measured a stale copy of the tree.** The post-cut sweeps ran over 646 Python files
  where the previous slice's ran over 507. The extra 138 were `build/` — a snapshot of `src/` left
  by the previous slice's wheel build, carrying the *previous* module and not this one's. No
  verdict changed on the clean re-run (508 files), but a stale snapshot fails in both directions:
  it can invent a reader that no longer exists and it can miss one added since. **The positive
  control does not save you — it fires inside the stale copy too.** Lesson: a sweep's POPULATION is
  part of its claim; exclude build artifacts and print the file count next to the verdict.
- **The probe's marker was the wrong type.** `_wbs_data` returns a `dict`; the inherited
  string-concat marker would have raised TypeError and turned every `/api/wbs` render into a 500 —
  which the probe scores as "this member moves lots of labels". A mis-typed marker does not measure
  a dark member, it measures the probe. Match the marker to the return type.
- **The installer's MPXJ pin drifts to the container's clone boundary.** `mpxj_ref()` runs
  `git log -1 -- tools/mpxj`; in a `--depth 1` clone that returns the shallow boundary, because git
  reports the boundary commit as introducing every file. Three different builds produced three
  different pins, and only the unshallowed one (`42d92dc`) actually touched the path. Harmless so
  far — identical bytes at every candidate — but the previous slice shipped the drift, and it would
  recur silently forever. **Anything derived from `git log` is a function of how deep the clone is.**
- **And a process one:** a parallel session took our ADR number mid-flight (#570 landed its own
  ADR-0385). We only noticed because an unrelated `git fetch` moved `origin/main` underneath us.
  Fetch before choosing an ADR number, and again before committing.
- **What worked:** two independent instruments agreeing. The call graph said `export_wbs`
  contributes no movers; the render probe independently showed its export labels do not move. When
  a probe is already running, the second confirmation is nearly free — take it.

### 2026-08-13 (d) — A data pin guards the literal, not the guarantee (ADR-0394, DoD 001a)

The task was one sentence: pin `net_guard._LOOPBACK_HOSTNAMES` and `_LOCAL_HTTP_SCHEMES` so the
Law-1 locality guarantee stops resting on a frozenset nothing asserts. The obvious implementation is
one assert per set. The mutation battery proved that would have been a **weaker guard than it looks**,
and that is the lesson worth keeping.

- **Three of nine mutations bypassed the allowlist while leaving both frozensets pristine.** A
  `candidate.endswith(".nasa.gov")` short-circuit inserted *above* the lookup; equality softened to
  `any(n in candidate for n in _LOOPBACK_HOSTNAMES)` (which accepts `localhost.evil.com`); and
  `is_loopback_host` returning `True` outright. On all three the exact-equality assertions stayed
  **green**, because the data really was unchanged — the *code that reads it* was what moved. Only
  the behavioural sweeps went red. **Pin the constant AND sweep the behaviour**: the first tells you
  which literal changed, the second is the only one that survives someone routing around it. Neither
  subsumes the other, and the battery — not judgement — is what established that.
- **Prove the sandbox is the tree being measured, or every "CAUGHT" is unfalsifiable.** The battery
  mutates a copy of `src/` and runs pytest with `PYTHONPATH` pointing at the copy. Whether that
  actually shadows the editable install is not obvious: this repo's editable install is a plain
  `.pth` path entry (so `PYTHONPATH` wins), but a setuptools `__editable___*_finder.py` registers a
  **`sys.meta_path` finder**, which is consulted *before* `sys.path` and would silently win — the
  battery would then have measured the real, unmutated tree and reported nine confident "CAUGHT"
  results that were pure noise, plus a "control green" that was also meaningless. Added a **canary**
  that aborts the whole run unless a sandbox mutation demonstrably changes the outcome. Any battery
  that measures through an indirection needs one.
- **Re-measure the premise, not just the fix (QC-2).** The audit reported "226 green, reproduced at
  854" under the widening. Those are real numbers about a selection I did not run, so they are
  testimony. Re-derived it: **336 passed, 0 failed** on my selection, with an in-process check that
  the sandbox really did return `True` for the gateway host. Same conclusion, but now it is evidence.
  Reporting someone else's count as my measurement is the exact habit `wc` decides.
- **A pin must not be satisfiable by breaking the feature.** `narrow_drop_ip6` went red too. It had
  to: `ip6-localhost` was in the allowlist and in **no test at all**, so deleting it was as invisible
  as adding a gateway. A one-directional guard would have blessed the narrowing (Law 2 — never weaken
  a test, and never let a guard reward a weakening).
- **The linter found a real one.** Ruff's RUF001 flagged the Cyrillic-`о` homograph I added *as a
  deliberate test input*. Rewrote it as a `\u043e` source escape and asserted the escape evaluates to
  the homograph — the input keeps its teeth, the source stays unambiguous, and a future editor cannot
  "helpfully" normalize it away. Worth generalizing: **an intentionally confusable literal belongs in
  the source as an escape**, with a test that it still means what you think.
- **Scope discipline paid.** Tracing locality decisions turned up a second unpinned security
  frozenset — `web/app.py:1076`'s `_ALLOWED_HOSTS`, the DNS-rebinding guard, named by no test file
  (measured: widened, 23 host-header tests stay green). 001a said *land alone*. Recorded it in three
  places with its measurement rather than bundling it, so the next session inherits evidence instead
  of a hunch.
- **The battery's own reporter was an unproven instrument.** It counted `always_true` as **4**
  failing tests; a direct re-count with a wide `COLUMNS` and `-rf --tb=no` showed **6**. The battery
  ran pytest with a minimal environment, so at the default 80-column width the long assertion
  messages wrapped and its `FAILED`-line parser mis-read them. The **verdicts** were never wrong —
  those come from the exit code, and all nine mutations were caught in every run — but a *count* had
  already been written into an ADR, a handoff and a session log before it was verified. Caught only
  because a change that provably cannot alter pass/fail (an f-string in a failure message) appeared
  to change a count, and that impossibility was chased instead of shrugged at. **An instrument that
  summarizes a measurement is itself a measurement**: prove the summarizer, not just the subject.
  The corollary is cheap and general — when a number moves and the edit cannot have moved it, the
  number was never measured; go and measure it.

### 2026-08-17 (f) — the rebase that should not have been necessary

- **A "pristine baseline" is only pristine relative to a ref you have re-fetched.** I triaged ten
  test failures by running them against a `git worktree` at my branch's base commit, concluded
  five were pre-existing, and reported them as an open problem deserving its own session. All
  correct — and all useless, because that session had already been merged into `origin/main`
  hours earlier and my local `main` was stale. The *method* was rigorous; the *baseline* was
  testimony. `git fetch origin` costs two seconds and is in CLAUDE.md's workflow section for
  precisely this failure. **Re-fetch before you branch, and re-fetch again before you report a
  finding about what is or is not already fixed.**
- **The cost of a stale branch is not just conflicts, it is a corrupted claim.** The merge
  conflicts (nine generated installers, four state docs) were mechanical and cheap. The expensive
  damage was an ADR-number collision on two ADRs, a version collision, and a confidently-stated
  finding that was false. Conflicts announce themselves; a stale premise does not.
- **When a rebase is ugly, rebuild on main rather than replaying commits.** Thirteen conflicts on
  the first commit alone, almost all in generated artifacts. Branching fresh from `origin/main`
  and re-applying the hand-authored files — while computing the intersection of "files I changed"
  and "files they changed" first, and patching that intersection rather than copying it — turned a
  fight into one three-way `git apply`. **Copying whole files across a diverged base silently
  reverts the other side's work; only the intersection needs care, and it is usually tiny** (here:
  one file, `web/app.py`).
- **A guard written yesterday caught a regression written by someone who had not read it.** #598
  removed a hardcoded `/opt/pw-browsers` skip from 24 browser modules and left behind a computed
  census. My new chromium module — cut from a branch predating that fix — reintroduced the exact
  pattern, and the census went red the moment the trees met. This is the argument for computed
  censuses over documented conventions in one sentence: **the convention only binds people who
  read it; the census binds everyone who merges.**

### 2026-08-18 (a) — Chapter 04's stability band (ADR-0427)

- **A surviving mutant is not always a weak test — sometimes it is dead code.** M3 targeted a
  precondition written at a call site that can never be reached, because the route returns its own
  empty state first. The test passed for a reason unrelated to the thing it named, and the mutation
  is what exposed that the guard guarded nothing. **When a mutant survives, ask whether the SUBJECT
  is reachable before assuming the ASSERTION is weak.** Moving the check into the function made both
  the guard and its test real.
- **Check whether the content already exists somewhere else before building it.** The instinct on
  "make this page match the design" was to build four new panels. The repo already had all four,
  on the sibling route, fully implemented — and the shared JS module was already mount-driven, so
  the work collapsed from "write four charts" to "mount four hosts and label the scope". A coverage
  read of the NEIGHBOURING page, not just the target page, is what found it.
- **`chartframe.js` wraps every `.chart-host`.** A CSS rule aimed at `.chart-host` inside a flex
  container is aimed at something that is no longer the flex child, and it silently does nothing —
  three flex settings failed to move a chart off 300px, each looking like a plausible fix. When a
  layout rule provably applies (computed style confirms it) and the geometry still refuses to move,
  **the element you are styling is not the element being laid out.**
- **SVG chart text sized in CSS px does not scale with the SVG.** Shrink the host and the labels get
  proportionally BIGGER, so a chart that is clean at 566px collides at 300px. Reusing a chart in a
  narrower slot is therefore a legibility change, not just a layout one — measure it there.
- **An overlap detector that ignores clipping lies confidently.** `getBoundingClientRect()` returns
  geometry for text scrolled out of view, so a fixed panel still reported collisions; and clipping
  ancestors must ALL be intersected, because `<svg>` defaults to `overflow:hidden` and stops a naive
  walk at the wrong box. Two wrong instruments, two confident wrong answers, before the right one.
  **The instrument gets the same red-before-green discipline as the code.**

### 2026-08-18 (b) — an independent oracle for Chapter 04, and a symmetric fixture that proved nothing

- **Structural tests and correctness tests are different things, and it is easy to ship only the
  first.** ADR-0427's eleven guards assert the panels mount, the scope words appear, and both pages
  embed the same dataset. Every one of them passes if the arithmetic underneath is wrong, because
  they compare the tool to ITSELF. The missing half is an oracle that can disagree: fixtures whose
  answers are worked out on paper. Ask of any new test suite — *what wrong number would still make
  this green?*
- **A SYMMETRIC fixture cannot detect an ASYMMETRIC bug.** The hand-built case had `entered == left`
  on every version pair, so the mutant that SWAPPED those two labels survived — the fixture could
  not distinguish the two quantities it was asserting. Fixed by adding a deliberately lopsided pair
  (two join, none leave). **When a test asserts two values, make sure the fixture gives them
  different values**, or it is testing one thing twice.
- **Correct arithmetic is not a working feature.** All 14 oracle checks passed — the numbers are
  right — and the defect was in the interaction: the version cursor's first position clamps to the
  first transition, so the opening click of Next changes nothing and the panel states a change that
  has not happened at that point in the sequence. Numbers-correct plus behaviour-wrong is a common
  shape, and only a browser walk of the control finds it.
- **Attribute before fixing.** The clamp reproduces identically on `/volatility`, which shares the
  chart module — pre-existing, not introduced by the page that surfaced it. "Found on my new page"
  and "caused by my new page" are different claims and demand different fixes.
- **A grep window that is too small under-reports while looking exhaustive.** I checked whether
  `volatility.js` was byte-pinned with a 12-line context window, saw four other filenames, and
  wrote "carries no md5 pin (checked)" into an ADR. It stopped two entries short of the answer.
  The full gate refuted it. **When the question is "is X in this list", print the WHOLE list or
  match X directly — never a window that happens to contain some of it.** The word "checked" in a
  deliverable is a promise about the method, and the method has to be able to see a negative.
- **Copying a test pattern copies its bugs, including ones already fixed.** The new browser module
  was written from an older module's hardcoded-browser-path `skipif` — a pattern ADR-0418 had
  retired precisely because it makes browser tests SKIP on CI. So the guard written to catch the
  ribbon defect would never have run on the machine that gates merges. A repo-wide guard caught it.
  **Before copying a test's scaffolding, check whether that scaffolding is what a recent ADR was
  about.**
