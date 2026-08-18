# Design gap analysis — repo `main` @ v1.0.211 vs. the MERLIN deck

**Date:** 2026-08-17 · **Repo baseline:** `main` @ `f4eaf32`, v1.0.211, highest ADR 0417
**Design baseline:** `Mission Ops Redesign v2.dc.html` (the MERLIN deck) from the Claude Design
handoff bundle, plus its 16 chat transcripts.

This is a **read-then-verify** audit, not a summary of the bundle's own claims. Every "present"
and "absent" below was checked against this tree, and the two places where the bundle's own
documents were wrong are called out.

---

## 0. Which prototype is the truth

The bundle's `CLAUDE.md` §0 states *"`ASTROLABE.dc.html` … the current pixel/behaviour truth …
Where the two disagree, ASTROLABE wins."* **That sentence is stale.** The chat record shows the
opposite order of events:

- chat12 (2026-07-30): the operator asks for ASTROLABE's launch screen to be merged **into** Mission
  Ops Redesign v2 — *"make it one project"* — and it is.
- chat12, later: *"change the name of the project to Merlin as well as come up with a meaning for
  Merlin"* → **MERLIN** — *Milestone Evidence, Risk & Logic INtelligence*.
- chat13/14 (2026-08-14/15) then work exclusively on the v2 deck as "the MERLIN deck".

The file contents agree: `Mission Ops Redesign v2.dc.html` carries 13 `MERLIN` references,
`ASTROLABE.dc.html` carries 3 `ASTROLABE` and 2 `MERLIN`. **`Mission Ops Redesign v2.dc.html` is the
design truth; ASTROLABE is a superseded ancestor.** The bundle's `CLAUDE.md` §9 (ASTROLABE
additions) still describes real intent and is worth reading — but as a *backlog*, not as the spec.

## 1. Headline: the repo is much further along than the bundle assumes

The bundle was synced against **v1.0.91 / ADR-0284**. The repo is at **v1.0.211 / ADR-0417** — 127
ADRs later. The bundle's TASK-1 phase order is therefore largely historical:

| Bundle phase | Actual state |
|---|---|
| 1. Tokens + theme select | **Done** — `static/sf-themes.css`, `theme.js`, four views (console / daylight / apollo / jarvis), legacy `light`→`daylight` migration, ADR-0195 |
| 2. Global chrome | **Done** — three-act spine, Continue footers, story progress, global Analysis-Target selector, CUI bars, Ask panel, roles (ADR-0196/0255/0284) |
| 3. Page shells, one per PR | **Mostly done** — all twelve chapters exist as real routes |
| 4. New analytics panels | **Mostly done** — `/integrity`, `/workbench`, `/margin`, `/standards`, `/scorecards`, JCL, LHS, branching all shipped |

**Do not re-run phases 1–2.** A "restyle the app to the prototype" sweep started from the bundle's
own text would rewrite working, ADR-backed code.

## 2. What was genuinely missing — and is now fixed (ADR-0425)

The deck groups non-story pages into **four** nav rails. The repo shipped **one**.

| Deck rail | Repo before | Repo after ADR-0425 |
|---|---|---|
| FORENSICS · Schedule Integrity | folded **beat** under ch. 02 | own rail |
| LIBRARY · Metric Workbench | in `SETUP` | LIBRARY |
| LIBRARY · WBS Rollup | folded beat under ch. 07 | LIBRARY |
| LIBRARY · Schedule ID Card | folded beat under ch. 01 | LIBRARY |
| LIBRARY · EVM | folded beat under ch. 07 | LIBRARY |
| CONTROL · Margin Dashboard | in `SETUP` | CONTROL |
| CONTROL · Standards & Execution | in `SETUP` | CONTROL |
| CONTROL · Assessment Scorecards | folded beat under ch. 02 | CONTROL |
| SETUP · Groups / AI Settings / Dictionary | in `SETUP` | unchanged |

Schedule Integrity — one of the two things this tool exists to do — rendered as a muted sub-link
under "Can we trust the plan?". That is the same defect the operator escalated during design
(*"One example is schedule integrity. This page looks for schedule manipulation. I don't see it
here."*), one level up. See ADR-0425 for the decision and its mutation record.

## 3. What is still missing, ranked

### Tier 1 — deck screens with no repo route at all

| # | Screen | Deck ref | Notes |
|---|---|---|---|
| 1 | **Beyond the Schedule** | nav `bs` | Analyst-entered exposure the file cannot supply: staffing coverage, funding alignment, TPMs. Deck marks it `deck-only · project vitals`. Needs a route, a store, and the SUSPECTED/engine separation the deck insists on. |
| 2 | **Portfolio at Scale** | nav `sl` | `/portfolio` scale mode — the 2,000-project / 600-file virtualized scatter that demonstrates the ADR-0226/0261/0281 scale contract. No `scale` handling exists in `portfolio.py`. |
| 3 | **Portfolio Trend Lab + Manipulation Watch** | chat12 | Pick any file-level field → every program's last six updates as small multiples or a 12-program overlay, ▶ PLAY, plus a strip auto-ranking programs whose masking flags rise while slip grows. **Caveat the deck itself records: its trend histories are demo-seeded** — the repo build must feed them from the real update chain. |

### Tier 2 — the engine exists, the screen does not

| # | Screen | What exists upstream |
|---|---|---|
| 4 | **Metric Lab** (single-metric focus across versions) | `/workbench` + `engine/metric_catalog.py` carry the library and the per-version values; only the single-metric ribbon view is missing. Lowest-effort Tier-2 item. |
| 5 | **Segment Forecast** as a Library page | `compute_field_forecast` + `_field_forecast_panel` + `/export/{fmt}/field-forecast` all ship — it renders as a *panel* on `/forecast` and `/evm`, never as its own screen. |

Both were deliberately **left out of the new LIBRARY rail**: a nav entry pointing at a route that
does not implement the screen is a dead link wearing a label.

### Tier 3 — cross-cutting chrome

| # | Feature | Gap |
|---|---|---|
| 6 | **PDF export** | `_EXPORT_MEDIA` supports `xlsx` + `docx` only. The deck put a format dialog (XLSX / CUI-marked PDF print sheet / CSV) behind **every** ⤓ button. |
| 7 | **GUIDE ME** teaching layer | Per-screen what / when-why / example / how-to-read, a next-chapter walk, auto-open on first run. Absent. |
| 8 | **SHOW UIDs** visibility overlay | ≤20 UID pins + target pins that slide as versions play (bow wave, ch-07 census, float-erosion lines). Explicitly never affects calculations. Absent. |
| 9 | **Boot / launch sequence** | The repo ships only `static/launch_audio.js` (the ADR-0328 generative hum). The deck's particle canvas, Hohmann transit, telemetry and welcome screen are absent. |
| 10 | **MERLIN wordmark** | No product name is applied. Note the operator's standing requirement is to **drop "NASA" from the wordmark**, not from citations — the 114 `NASA` hits in the view layer are metric-library and NASA-STAT provenance strings and must stay. |

## 4. Deviations the deck itself declares (do not treat as bugs)

From `docs/coverage-verification.md` in the bundle: **EN-only copy** (the repo has EN/ES/FR/DE/PT —
the deck is behind here, not the repo), **partial legend-toggle parity**, and **demo-seeded Trend
Lab histories**.

## 5. Method note

Route inventory taken from `@app.get`/`@app.post` decorators across `web/*.py` (137 routes; 32
user-facing HTML routes). Nav coverage read from `chrome.py::_SPINE`. Feature presence checked by
grep over `web/*.py` + `web/static/*.js`, then confirmed by reading the hit. One earlier reading of
this tree recorded `/wbs` as orphaned from the nav — **that was wrong**: it was a declared beat of
chapter 07 (`("WBS", "@wbs")`), found only on a second pass with a different pattern. Recorded here
because a coverage sweep is only as good as its pattern, which is this repo's own standing lesson.
