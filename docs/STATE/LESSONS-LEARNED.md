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
