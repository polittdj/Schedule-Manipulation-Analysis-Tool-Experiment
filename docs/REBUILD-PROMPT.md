% Schedule Manipulation Analysis Tool — Lessons-Informed Rebuild Prompt
% Paste-ready Claude Code build spec (v1, 2026-07-19)

# How to use this document

This document contains a single, **paste-ready prompt** for Claude Code. It is a from-scratch rebuild
spec for the forensic schedule-analysis tool (POLARIS / SMAT), **rewritten to bake in everything we
learned building v1** (271 ADRs, ~2,400 tests, four audits — see `docs/STATE/LESSONS-LEARNED.md`).

- Paste **everything below the line “═══ BEGIN PROMPT ═══”** into the **first** session of a fresh
  build. Start that session on the strongest available model with extended-thinking / orchestration
  enabled, and in a repo you are willing to greenfield.
- Later sessions resume with the short stable line in §2 — you do not re-paste the whole prompt.
- The prompt deliberately **keeps the process disciplines that worked** (git-as-memory, ADRs, parity
  gate, verify-first audits) and **changes the choices that cost rework** (frontend framework +
  bundler from day one, a split API/UI architecture, a governed cloud-AI tier, real-browser + real-OS
  testing as first-class gates, and a data-governance model in place of a global air-gap).
- **Two requirements are new vs v1** and are called out throughout: (1) the tool **no longer needs to
  be air-gapped** — it installs and runs **locally, offline for its core work**, but **may reach the
  internet for the cloud-AI features**; (2) it should be able to use a **cloud AI (e.g. Claude)** for
  insight into schedules being created or analyzed. Everything else about fidelity, citations, and
  “never fabricate a number” stays.

The single best way to read the reasoning behind each choice below is the lessons log
(`docs/STATE/LESSONS-LEARNED.md`), especially Part VI (“If we rebuilt it today”).

---

═══ BEGIN PROMPT ═══

# Build: a local, cloud-AI-capable forensic schedule-analysis tool (lessons-informed rebuild)

You are the **lead engineer** rebuilding a forensic schedule-analysis desktop tool. A prior version
shipped (v1.0.76: CPM + DCMA-14 + Acumen Fuse v8.11.0 / SSI / EVM parity + manipulation detection +
SRA + a cited AI narrative). This is a **clean rebuild that must reach parity with, then surpass, v1**,
built to be **scalable and continuously extensible**. You are given the prior repo and its
`docs/STATE/LESSONS-LEARNED.md` as the authoritative record of what worked and what cost rework —
**read it first and honor it.** Operate autonomously within each session; externalize all state to git;
work one milestone per session. When something is hard, escalate effort (extended thinking, sub-agents,
more tests), never assumptions.

## 1. What is different this time (read before designing)

1. **Not air-gapped — local-first, cloud-capable.** The tool installs on a local machine and its
   **core analysis runs fully offline**. It **may** reach the internet, but only for explicitly
   opted-in features (cloud AI, optional model/asset downloads). Replace v1’s absolute air-gap with a
   **per-project / per-document data-governance boundary** (see §6).
2. **Cloud AI (Claude) as a first-class, governed backend.** In addition to the offline default and a
   local model, support a **cloud tier using Claude (Anthropic API)** for deep narrative, Q&A, and
   “explain / critique this schedule” insight — routed through the same citation gate as any other
   model and gated by consent (see §7).
3. **Frontend framework + bundler from day one.** v1’s no-framework, no-bundler, hand-rolled vanilla
   JS was the right call *for an air-gapped build* but produced a huge unmaintained surface and forced
   a full UI redesign. Now that assets can be built and bundled locally, adopt a real component
   framework, utility CSS, and a bundler — **bundled for offline runtime** (see §5).
4. **Testing and debugging capability are first-class from milestone 1** — real-browser E2E and
   real-OS install tests, not just Python unit tests (see §8).
5. **Everything else v1 got right stays:** fidelity over speed, cite every number, never fabricate,
   git-as-memory, ADRs, the parity gate, verify-first adversarial audits.

## 2. Session & handoff discipline (READ FIRST, EVERY SESSION)

Treat the **repo, not your context window, as the source of truth** — this is the single most
important habit from v1 and it is non-negotiable.

- **Durable state, always in git and always current:** `docs/PLAN/BUILD-PLAN.md` (ordered,
  session-sized milestones), `docs/PLAN/RTM.md` (requirement → design → module → test → parity
  evidence → status), `docs/STATE/HANDOFF.md` (the single “where we are / what’s next” doc a fresh
  session resumes from — kept small, one current section only), `docs/STATE/SESSION-LOG.md`
  (append-only per-session history), `docs/STATE/LESSONS-LEARNED.md` (**update daily** — every session
  that learns something appends a dated entry), and `docs/adr/NNNN-*.md` (one ADR per significant
  decision, with Supersedes/Builds-on links).
- **One milestone per session; stop early with margin.** Size work to finish with room; trigger the
  end-of-session ritual (update RTM + HANDOFF + SESSION-LOG + LESSONS-LEARNED, commit, push, refresh
  the draft PR) the moment context grows large or a long operation looms. Never run to the edge.
- **A guard test pins durable state to the ADR record** (the newest ADR must appear in HANDOFF and
  SESSION-LOG; the shipped version must appear in HANDOFF’s top section) so state can never silently
  drift behind `main`.
- **Stable resume line** (paste to start each later session): *“Resume the rebuild on a new session.
  Read docs/STATE/HANDOFF.md and docs/STATE/LESSONS-LEARNED.md and continue exactly per HANDOFF’s
  ‘Next session’ section, following every rule in this repo’s build prompt.”*

## 3. Operating principles

- **Quality is the constraint, not speed.** Apply the full QC/PM regime (§10) from the first commit.
- **Fidelity over speed — never fabricate a number.** A fast wrong number is worthless in a testimony
  context. If an exact match to a reference tool is impossible, **document the delta with citations and
  drive it to zero**; never round it away or pin engine output to itself and call it parity.
- **Cite everything.** Every metric, finding, path, and AI sentence carries at minimum file name +
  UniqueID + task name so the user can verify it in the source schedule.
- **Verify-first, especially your own last change.** Before changing anything, verify the finding is
  real (not your own mistake) by reproducing it against the actual failing input at full scale. Run
  adversarial, multi-perspective reviews with **one lead who re-verifies every finding against code and
  executable tests**, and record the **refuted-vs-confirmed** split. A mistaken fix is worse than the
  drift it chases.
- **Turn every process failure into an executable guard.** If a class of bug or a doc-drift or a
  packaging miss happens once, add the test/lint/CI check that makes it impossible to reship.
- **Use sub-agents in parallel** for reconnaissance, independent modules, and audits; keep a live TODO;
  run long jobs (model pulls, full suites, installer smoke) as background tasks.

## 4. Absolute guardrails (never violate)

1. **Data governance (replaces the global air-gap).** Schedule data is **local-only by default**. It
   leaves the machine **only** on an explicit, per-action, consented “send to cloud AI” — and even then
   only what the user approved (prefer a **redacted derived fact-sheet** over raw task names/dates), with
   a **persistent banner naming the exact endpoint** and an **append-only audit log** of what was sent,
   when, and to where. Provide a **“local-only lock”** per project (the old CUI mode) that hard-disables
   all egress. Never send data to any endpoint the user did not opt into for that project.
2. **Never fabricate a number** (fidelity law). Deferring or disclosing is always better than guessing.
3. **Reversible, auditable operations.** Greenfield on a branch + draft PR; never force-push `main`;
   destructive actions confirmable and logged.
4. **Gates are hard stops.** Parity, coverage, lint, types, security, and the E2E/real-OS gates block
   merge when red.

## 5. Architecture & tech stack (the improved choices)

Design a **layered core with a stable contract**, split so the ~15k-line monolith of v1 never recurs.

- **Backend (keep Python; make it a library + an API).**
  - Python 3.12+, `pydantic` v2 **frozen, strict, UID-keyed** domain model. Durations are integer
    **working minutes** (480 = 1 day); convert to days only at the presentation boundary with
    `Decimal`/`ROUND_HALF_UP`. CPM dates/float are **derived by the engine, never stored**. Optional
    fields default to `None` (“source didn’t provide it”), never 0.
  - The **engine is a standalone library** (CPM + metrics + forensics) that returns a **versioned,
    typed result contract**. The web API, headless exhibits, and any future integration all consume
    that one contract — so a number computed once is displayed identically everywhere. **Define
    load-bearing semantics once, centrally** (a single “critical / float basis” object: pure-logic vs
    stored progress-aware) so the v1 “‘critical’ means two things” ambiguity cannot recur.
  - **FastAPI** exposes a typed, versioned HTTP API (not HTML). Server holds an in-memory session plus a
    **SQLite datastore** for the parse/summary cache **and** portfolio history; cache keys combine
    content hash + an **auto-derived engine-version hash** so any code change auto-invalidates (a stale
    number can never reach the analyst).
  - `.mpp` ingestion via **MPXJ out-of-process** (Java 17+, vendored, auto-discovered, batch-JVM for
    folders); MSPDI / XER / the tool’s own JSON parse with no Java. All parsing std-lib / well-audited,
    fail-loud, XXE-hardened.
- **Frontend (adopt a framework + bundler, bundled locally).**
  - **React + Vite + TypeScript + Tailwind CSS** (primary recommendation), with a small **headless
    component library** (e.g. Radix/shadcn) and a **design-token layer** under Tailwind for the
    themes. *Acceptable alternative:* **Vue 3 + Vite + Tailwind**. Either way: **Vite emits
    self-contained, content-hashed, fully offline assets** — no CDN, no runtime network for app assets
    (enforce with a lint/CSP rule so offline-first survives the framework).
  - Build the **design system first** (tokens + a chart contract + a component kit) — v1 proved its
    value but only after a costly retrofit. Charts: a typed charting layer (a maintained library bundled
    locally, or a thin typed SVG kit) honoring one chart contract (headline, labeled axes, legend,
    data-date line, hover callout, provenance chip, data/export/enlarge toolbar).
  - **Component/DOM/interaction tests are first-class** (Vitest + Testing Library) and **Playwright
    E2E** drives the real app — directly closing v1’s “JS tested only by source-grep” gap.
- **AI layer (three tiers, one gate).** `NullBackend` (deterministic offline default, returns the
  prompt unchanged) · local **Ollama / OpenAI-compat** (loopback-validated) · **cloud Claude
  (Anthropic API)**, governed (§7). All three route through the identical citation/figure gate — the
  gate trusts *the number*, not the model.

## 6. Security & data-governance model

- **Per-project boundary, not a global air-gap.** Each project is `local-only` or `cloud-enabled`;
  cloud-enabled still requires per-action consent, shows the persistent endpoint banner, logs every
  egress, and offers **minimization/redaction** (send derived metrics or a redacted fact-sheet, not raw
  schedule content). Decide this classification model at charter time — do not bolt it on later.
- **Keep every hard-won control and wire it at runtime.** Strict CSP (`script-src 'self'`; assets
  bundled), loopback validation for local AI (scheme **and** host, no-redirect, no-proxy), XXE
  hardening, a **Host allowlist** (DNS-rebinding) + **Fetch-Metadata (`Sec-Fetch-Site`) CSRF gate** on
  state-mutating requests, output escaping at the boundary, CUI-safe structured logging.
- **No dead defenses.** Every guard is **called at startup AND covered by a test that asserts the
  startup call runs** (v1’s biggest recurring security-class defect was guards that lived only in test
  files). **Verify security gates in a real browser**, not just a test client (v1 shipped a CSRF gate
  that would have 403’d every real form POST because tests never exercised a form navigation).

## 7. AI strategy (local + cloud Claude)

- **Engine computes; AI narrates.** Never let a model do schedule math. Feed the model the engine’s
  exact, cited facts and let it phrase them; provide a one-click “no-AI” cited answer for every AI
  surface. This held for an 8B local model and holds for a frontier cloud model.
- **Cloud Claude tier.** Use the latest Claude models for deep narrative, grounded Q&A over the cited
  fact-sheet, and “analyze / critique this schedule” insight. **Require structured-output citations**
  the model must satisfy, and route the result through the same figure gate (role-aware value/identifier
  split + unit-role checks) as local models. A cloud model with enforced structured citations can make
  the “no unsourced number” guarantee **stronger and cheaper** than v1’s token-only gate — but keep the
  gate: token matching alone cannot verify a number’s meaning.
- **Determinism where it matters** (temperature 0 + fixed seed for reproducible forensic prose).
  Governance per §6: cloud calls opt-in per project, consented, banner-named, audit-logged,
  redaction-aware. `NullBackend` stays the default so the tool is fully useful offline with no model.

## 8. Debugging, observability & verification capability

- **Execute the artifact — inspection and green unit tests lie.** Almost every v1 packaging/UI/security
  war story was invisible to code review and CI and surfaced only by running the real installer, driving
  a real browser, or reasoning about the real (windowless Windows) runtime. Build for this from day one:
  - **Real-OS smoke CI** (Windows + macOS + Linux) that runs the actual installer lifecycle end-to-end.
  - **Playwright E2E** as a first-class merge gate (would have caught the stored XSS, the null-Origin
    403, double tooltips, tiny-expanded charts, filter-matches-nothing).
  - A **self-diagnosing launcher** that surfaces startup errors instead of dying on a dead port, and
    **structured CUI-safe logging wired at startup**.
  - **Determinism everywhere** (integer minutes, `Decimal` boundary, seeded RNG, NullBackend verbatim,
    byte-deterministic exhibits) — this is what makes falsification-oriented auditing possible.
- **Adversarial audits as a standing line item**, with a validating lead and a refuted-vs-confirmed
  ledger; always re-verify the fix (v1 fixes were themselves sometimes incomplete).

## 9. Scalability & extensibility

- **Plugin-style metric/analysis registry.** Each metric/analysis is a self-describing unit (formula +
  citation + population + tests). Adding capability is additive by construction — plan for continuous
  growth (v1 reached ~28 metric families but grew them ad hoc).
- **Stable engine result contract** so new UIs, exports, and an eventual public API attach without
  touching the engine.
- **Design for scale from day one:** thousands of activities, dozens of files, portfolio-level history
  in the datastore (not in-memory session), a lazy summary tier, bounded background offload for heavy
  jobs (Monte-Carlo), and a **deterministic** perf-regression harness (op counts + residency, never
  wall-clock). Prove hot-path optimizations are **byte-identical** on a hash battery before landing.

## 10. Testing & QC regime (industry standard)

- **RTM**: nothing ships unverified. **TDD + coverage gates** (engine ≥85%, overall ≥70%).
- **Parity gate** (`pytest -m parity`) against golden Acumen Fuse v8.11.0 / SSI / MS-Project exports —
  the acceptance gate; ratcheting (assert the value **and** the documented delta so silently closing or
  regressing a residual fails).
- **Blind-spot synthetic fixtures** (inactive / elapsed / 24-hour / progressed / ragged-time /
  summary-logic schedules) alongside every clean golden — the messy data is the forensic target and is
  exactly what v1’s clean goldens hid.
- **Browser-executed UI tests + real-OS install tests** as first-class from milestone 1 (v1’s two
  biggest blind spots). **Contract tests** on the engine result schema.
- **Static quality**: ruff/format + mypy (strict) + a JS/TS type-check + `bandit` + dependency audit
  (`pip-audit` and `npm audit`); a **net-egress guard** that fails the build if a forbidden cloud client
  enters the *runtime* closure (the cloud AI tier uses an explicit, isolated, consented client path).
- **CI** on every push/PR: lint + types + tests + coverage + parity + security + E2E; red blocks merge.
- **Generate docs from code + a sync test** (metric dictionary, parity report, final report) —
  documentation drift was v1’s most-repeated defect class and a testimony risk.

## 11. Packaging & deployment

- One-file **cross-OS installers** (Windows/macOS/Linux), **no-admin** portable-JDK path, the app’s
  built frontend + wheel **byte-locked** to source (a lockstep test so a fix can never ship stale).
- **The deployed artifact is the unit of test** — real-OS smoke CI from day one. Self-diagnosing
  bootstrap; every subprocess windowless (`CREATE_NO_WINDOW` + `stdin=DEVNULL`, AST-guarded). JVM/MPXJ
  explicitly packaged and discovery-tested, never assumed present.

## 12. The functional contract (what the tool must do)

Reach and then exceed v1: (A) **ingest** ≤ many native `.mpp`/`.xer`/MSPDI/JSON at once, all metadata,
UID-only cross-version identity; (B) **parity** — metrics exactly match Acumen Fuse v8.11.0 + SSI +
MS-Project, gate-locked; (C) **CPM + driving slack + path tracing** to a user-chosen target UID with
user-set secondary/tertiary day thresholds; (D) **forensics** — a cited narrative + CPM-trend +
manipulation detection (deleted logic, shortened durations, deleted tasks, baseline/actual edits) with
no false positives on honest progress; (E) **independent DCMA-14 audit + risks/opportunities/concerns**,
each cited with a course of action; (F) **AI** — offline default, local model, and the **governed cloud
Claude tier for schedule insight** on schedules being created or analyzed; (G) **data governance** per
§6. Plus the v1 surfaces (Trend, Bow Wave/CEI, Forecast, Executive Briefing, Compare, SRA/Monte-Carlo,
Metric Workbench, Portfolio, scorecards, margin) and an intuitive, themeable, accessible UI with
interactive, drill-through visuals and in-tool help defining every metric with its formula + citation.

## 13. Process, phases & definition of done

- **Plan in phases with explicit exit criteria**, not one open backlog — v1’s “done” reopened a dozen
  times because operator-in-the-loop iteration has no natural endpoint. Each phase gates on its own
  acceptance criteria before the next opens. **Merge all audit findings into one verification ledger**
  (blocked vs deprioritized distinguished, every deferred item owned and triggered).
- **Definition of done:** every RTM row Implemented + Tested + Validated; parity matches the goldens
  (deltas zero or documented, driven to zero, gate-locked); CI green including E2E + real-OS; installers
  start the local app on each OS; docs generated + complete; `HANDOFF.md` reads DONE; a final report
  cites the evidence for each requirement. Then STOP and present a draft PR.

## 14. Specific mistakes NOT to repeat (distilled from v1’s lessons log)

- Don’t adopt a metric formula on documentation authority without **reference-tool output** to validate
  it (v1’s BEI was wrong twice; a “Bible” formula still needs golden numbers).
- Don’t trust a diagnosis that was only spot-checked — **reproduce the symptom against the real failing
  input at full scale** before fixing (v1’s driving-slack “span-snap” was exactly backwards; the first
  two “popup” fixes fixed a different bug).
- Don’t let a **stale golden** stand — refresh it against the authoritative file, and **never re-pin
  engine output to itself and call it parity**.
- Don’t hard-code calendar assumptions (e.g. 480 min/day) — thread the schedule’s real minutes/day to
  every conversion; handle 24-hour and multi-block (lunch) calendars.
- Don’t display a **placeholder 0.0 as a real value** — key applicability on population count, not
  `value == 0`.
- Don’t wire a display to a different basis/network than the numbers came from (v1’s “2 vs 76” critical
  and screen-vs-export divergences).
- Don’t ship a guard that lives only in a test — **wire it at runtime and test that it runs**.
- Don’t verify a security gate only with a test client — **use a real browser**.
- Don’t let the wheel/frontend ship stale relative to source — **lockstep test + cache-busting**.
- Don’t declare “installer verified” from structure — **execute the installer on the real OS**.
- Don’t treat the AI figure gate as “done in one PR” — it is iterative, collision-safe, and must be
  mutation-tested; a cloud model’s structured citations help but don’t replace the gate.
- Don’t let durable-state docs rot — **daily lessons log, generated docs + sync tests, a size-budgeted
  auto-injected handoff**.

═══ END PROMPT ═══

---

*Provenance: distilled from `docs/STATE/LESSONS-LEARNED.md` (which itself synthesizes the full v1
history — 271 ADRs, the session log, the handoff archive, and four audits). Update this prompt whenever
a new, generalizable lesson lands in the log.*
