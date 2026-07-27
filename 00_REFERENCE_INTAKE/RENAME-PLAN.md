# GUIDED-MODE — the five-Act teaching layer (SPEC ONLY, awaiting approval)

**Nothing has been built.** Per PROMPT 3 §1 this is the spec, and it stops for approval before any code. Governing law: repo `CLAUDE.md` + `docs/DESIGN-SYSTEM.md`. Source inventory: `docs/UI-INVENTORY.md`.

**Two corrections before the spec starts.**
1. **Route count is 133, not 128** (`docs/UI-INVENTORY.md` §1: 32 HTML · 28 JSON · 39 export · 32 POST, parsed line-by-line from the 19,081-line `app.py`). All 133 must keep working; the additive rule is unchanged, the number is just larger than the prompt assumed.
2. **Tooltip text does not need new dictionary fields.** `MetricDoc` in `src/schedule_forensics/web/help.py` already carries `definition`, `formula`, `source`, `importance`, `indicates`, `threshold`, `example_ok`, `example_fail`, `use_case`, `citation_basis`. The required what / how / decision triple is a **projection of existing fields** (§4), so guided mode is a renderer, not a documentation migration.

*This workspace has no Python runtime, no app and no network: the gates, the 200-check sweep and the screenshots run in the repo.*

---

## 1. Design rules that bind every Act

| Rule | Value |
|---|---|
| Visuals per Act | **≤ 3** (hard cap) |
| Headline per Act | **exactly 1** — a sentence with a number in it, per DESIGN-SYSTEM §2 |
| Metric readouts per Act | **≤ 5**, each with a tooltip |
| Everything else | **not removed — deep-linked.** Each visual carries "see the full view →" to the existing page, which keeps every current control (column pickers, zoom, filters, play, ▦/⤓/⛶) exactly one click away |
| New charts | **none.** Every visual is an existing module rendered against an existing endpoint |
| New engine calls | **none.** Guided mode reads what the page it links to already reads |
| Reading order | Act *n* unlocks Act *n+1*'s Continue footer; any Act is still directly addressable by URL |

The density fix is structural: today a report page carries 6–12 panels; an Act carries 3. Nothing is deleted — the other 9 live on the page the Act links to.

---

## 2. The five Acts

### Act 1 — What is this project?

*Teaches: a schedule is a network of activities joined by logic, not a list of dates; the data date splits history from forecast; float is spare time.*

| Slot | Visual | Existing module | Route it deep-links to | Endpoint |
|---|---|---|---|---|
| 1 | Driving-path Gantt (bars + data-date line) | `gantt.js` | `/analysis/{name}` | existing analysis payload |
| 2 | Total-float distribution | `histogram.js` | `/analysis/{name}` | same |
| 3 | Schedule ID card (population / calendars / constraints / open ends / baseline) — a **table**, not a new chart | existing analysis fields | `/analysis/{name}` | same |

Metric readouts (dictionary ids): activity population · data date · min total float · open ends (`DCMA01`) · hard constraints (`DCMA05`).
Headline pattern: *"N activities, M of them decide the finish date — and K of those already have negative float."*
Deliberately omitted here: every quality percentage, every trend, every forecast. A first-time reader gets shape and vocabulary only.
Continue segue: *"You can read the plan. Next: whether it can be trusted."*

### Act 2 — Is it healthy?

*Teaches: structural quality is a separate question from lateness; DCMA-14 inspects the file, not the progress; margin is reserve, not float.*

| Slot | Visual | Module | Deep-links to |
|---|---|---|---|
| 1 | DCMA-14 ribbon (the "must stay below" checks) | `ribbon_drill.js` | `/ribbon` |
| 2 | Execution indices strip (SPI · SPI(t) · CPI · BEI · CPLI · TCPI) | `performance.js` | `/performance` |
| 3 | Margin burn-down vs guideline | `margin.js` / `margin_dashboard.js` | `/margin` |

Metric readouts: `DCMA01` · `DCMA09` · `DCMA13` (CPLI) · `DCMA14` (BEI) · margin remaining.
Headline pattern: *"X of 14 quality checks fail and Y% of the approved reserve is spent."*
Note for implementation: the ribbon has **two axis conventions** (ten checks with a 5% ceiling; the FS-relationship check with a 90% floor). Act 2 shows the ten-check ribbon only and links the FS check to `/ribbon`; mixing them on one axis is the defect `docs/AXIS-TITLES-PATCH.md` and the operator's own review already flagged.
Continue segue: *"You know its condition. Next: when it started going wrong."*

### Act 3 — What went wrong and when?

*Teaches: one version tells you where you are, the chain of versions tells you where you are going; deferred work accumulates.*

| Slot | Visual | Module | Deep-links to |
|---|---|---|---|
| 1 | Milestone drift across versions | `drift.js` (or `trend.js`) | `/trend` |
| 2 | Driving-path churn / CP evolution | `path_evolution.js` | `/evolution` |
| 3 | Bow wave + current execution index | `cei.js` | `/cei` |

Metric readouts: forecast slip vs baseline · churn % · CEI · BEI (`DCMA14`) · min-float trend.
Headline pattern: *"The finish has moved N workdays across M updates, and the remaining plan now needs P× the demonstrated throughput."*
Continue segue: *"You know the trend. Next: whether the trend was managed or edited."*

### Act 4 — Was it manipulated?

*Teaches: a date can improve two ways — work, or editing; concentration of edits on the driving path is the forensic signal; SUSPECTED is a legitimate answer.*

| Slot | Visual | Module | Deep-links to |
|---|---|---|---|
| 1 | Version-pair change signals (duration cuts · logic removed · lags added · constraints added · baseline edits) | compare diff view | `/compare` |
| 2 | Integrity findings ledger (old → new → shift rows) | `findings_drill.js` / `drilldown.js` | `/integrity` |
| 3 | Float erosion / negative-float emergence | `volatility.js` | `/volatility` |

Metric readouts: relationships changed · driving-path edits · constraints added (`DCMA05`) · invalid dates (`DCMA09`) · min total float.
Headline pattern: *"N edits between the last two updates moved the reported finish earlier while no work completed; M of them landed on the driving path."*
**Honesty rule for this Act specifically:** every claim renders its `⌖ file · UID` citation and any engine-flagged uncertainty stays visible as `SUSPECTED`. Guided mode may not soften a flag to keep a story tidy.
Continue segue: *"You know what changed. Next: what to do about it."*

### Act 5 — What has to happen now?

*Teaches: a forecast is defensible when independent methods agree; commit to a confidence level, not a date; reserve is sized from the distribution.*

| Slot | Visual | Module | Deep-links to |
|---|---|---|---|
| 1 | Three-method forecast S-curve | `scurve.js` / `curves.js` | `/forecast` |
| 2 | Simulated finish distribution + cumulative P-curve (P50/P80) | `sra.js` | `/sra` |
| 3 | Recommended actions with citations (existing briefing content) | briefing view | `/brief` |

Metric readouts: P50 · P80 · P(target met) · reserve required vs held · joint confidence (where cost-loaded).
Headline pattern: *"P50 is <date>, P80 is <date>, and holding the committed date needs N more workdays of reserve than remain."*
**Caveat that must render:** when the SRA runs on auto-default uncertainty, Act 5 shows the existing "screening placeholder, not SME-validated" warning verbatim. It is the last screen a reader sees; it may not be the one where the caveat is dropped.
Closing segue: *"You have the whole story. Leave guided mode to work the detail →"* (links to `/mission`).

---

## 3. What guided mode is, technically (and why the goldens cannot move)

**New surface, 6 routes:**

```
GET  /guided                 -> Act picker + progress (HTML)
GET  /guided/act/{n}         -> Act n, n in 1..5 (HTML)
POST /guided/dismiss         -> sets the opt-out, redirects to /mission
```

- Each Act template **includes the existing chart modules** and fetches **the endpoints those charts already use**. No new JSON endpoint, no new field, no serializer touched, no engine function called that the linked page does not already call.
- **Therefore `/api/dashboard` is untouched and the three goldens are byte-identical by construction** — `_SHA_TWO_VERSION` `d62a4f9e…58d1`, `_SHA_UNSOLVABLE` `8d7bcc38…fc16`, `_SHA_TWO_VERSION_PARITY` `51691cb7…504cb`. Re-pinning a golden is not an option in this task; if an Act appears to need a payload change, see §5 and stop.
- Existing routes: **zero diffs**. Guided mode adds nav entries and one post-ingest prompt; it changes no existing handler's response. The one interaction with existing behaviour is the landing rule, and it defers: **an ingest with errors still lands on the manifest** (ADR-0255/0267) regardless of guided mode.

**Opt-in / dismissible:**
- Trigger: after a *clean* first ingest, `/` offers "Explain this project to me" beside the existing role cards. It is an offer, never a redirect.
- State: `localStorage["sf-guided"]` = `"on" | "off"`, matching the `sf-*` convention `theme.js` already uses (`sf-theme`, `sf-theme-dark`). Absent = off.
- Dismiss: a persistent "Leave guided mode" control on every Act; `POST /guided/dismiss` sets `off` and returns the user to `/mission`. Re-entry is always available from the nav.
- Power users are unaffected: with `sf-guided` unset, every landing, nav target and page is exactly today's.

**Files touched:** `web/app.py` (+6 routes, +1 offer block on `/`), one new template shell, one new `web/static/guided.js` (Act navigation + tooltip wiring only — it draws nothing), `base.css` (Act layout tokens), nav definitions, `docs/DESIGN-SYSTEM.md` (§2 gains the Act layer), `docs/UI-INVENTORY.md` (§1 gains the 6 routes).

---

## 4. Tooltip contract — a projection of `MetricDoc`, nothing invented

`MetricDoc` (in `web/help.py`) is the single source. Guided mode renders exactly three beats:

| Tooltip beat | Field(s) used | Fallback |
|---|---|---|
| **What it means** | `definition` (title = `name`) | none — a metric with no definition is a doc bug, fail loudly |
| **How to read it** | `formula` + `threshold`, and `indicates` when a value is failing | `formula` alone |
| **What decision it supports** | `use_case` | `importance`, then `indicates` |
| footer | `source` + `citation_basis` | — |
| on a failing value | `example_fail`; on a passing value `example_ok` | omit |

Rules:
- Tooltips read `METRIC_DICTIONARY` **from `web/help.py`**, never from `docs/METRIC-DICTIONARY.md` — the `.md` is *generated* from `help.py` and `tests/web/test_docs.py::test_metric_dictionary_doc_is_in_sync` exists to prove it.
- **Do not add metric ids.** `tests/engine/test_aft_formula_audit.py:843` asserts `set(audited) == set(METRIC_DICTIONARY)`; a new id fails there too. Guided mode documents no new metric — it explains existing ones.
- Where `use_case` is empty, fill it **in `help.py`** with one plain sentence naming the decision, then regenerate the doc with the command the sync test prints. That keeps `test_docs`, `test_help` (every emitted metric documented) and `test_visuals` (DCMA entries) green, and adds no ids.
- Audit first: `python -c "from schedule_forensics.web.help import METRIC_DICTIONARY as M; print([k for k,v in M.items() if not v.use_case])"` — that list is the content backlog for this task, and it is the only `help.py` edit guided mode is allowed to make.

---

## 5. Gap register — the only things the Acts want that the app may not already produce

| # | Gap | Resolution that needs **no** payload change |
|---|---|---|
| 1 | An Act-level headline sentence with numbers in it | Compose in the **template** from values the linked page already renders. Never a new payload field; if a number isn't already on screen somewhere, the Act does not claim it |
| 2 | Reading progress (which Acts a user has seen) | Client-side `localStorage`, same as theme. No server state, no payload |
| 3 | "What changed since the last update" in one sentence for Act 4 | The existing `/compare` view already computes the signal counts; the Act quotes them |
| 4 | Per-Act "teach" copy (the three teaching lines) | Static template copy, reviewed by the operator — it is UI text, not data |
| 5 | `use_case` text for tooltips where empty | `help.py` content fill + doc regeneration (§4) |

If implementation hits a sixth gap that genuinely requires a payload change: **stop, write it here with the failing Act and the field needed, and ask** — do not re-pin a golden.

---

## 6. Definition of done

Same gate as PROMPT 1, plus:

- [ ] The three dashboard goldens **byte-identical** (no re-pinning).
- [ ] Every pre-existing route returns 200 with unchanged content: sweep all 133 (`docs/UI-INVENTORY.md` §1 is the list) and diff each HTML/JSON body against `main`. A new test — `tests/web/test_guided_is_additive.py` — should assert the route table's size and that no existing handler's response changed for a fixed fixture session.
- [ ] `/guided`, `/guided/act/{1..5}` and `POST /guided/dismiss` render in all four themes, both densities, 90/100/125%.
- [ ] With `sf-guided` unset, every landing and nav target is identical to today (screenshot diff `/`, `/mission`, `/trend`).
- [ ] Each Act: ≤3 visuals, exactly 1 headline, ≤5 readouts, every readout tooltip renders all three beats, every claim cites `file · UID`, `SUSPECTED` flags visible, SRA caveat present in Act 5.
- [ ] Ingest-with-errors still lands on the manifest (ADR-0255/0267), guided mode or not.
- [ ] `docs/DESIGN-SYSTEM.md` records the Act layer; `docs/UI-INVENTORY.md` §1 lists the 6 new routes; `engine/` untouched; nothing renamed.

---

## STOP — five decisions needed before code

1. **Act 3 primary visual:** `drift.js` (milestone drift, simpler) or `trend.js` (the full trend engine, richer but 1,165 lines)? I recommend `drift.js` for the lean page and a link into `/trend`.
2. **Act 4 slot 2:** `findings_drill.js` (integrity findings) or `drilldown.js` (activity-level diff)? Recommend findings — it reads as a ledger, which is the forensic register a reader can follow.
3. **Margin in Act 2:** `margin.js` (compact) or `margin_dashboard.js` (full burn-down + erosion)? Recommend `margin.js` compact, deep-linking `/margin`.
4. **Where guided mode lives in the nav:** its own top group above "Load", or an entry inside the existing story spine? Recommend its own group, so the twelve chapters keep their numbering untouched.
5. **The `use_case` backlog:** do you want to review the filled sentences before they land in `help.py` (they become the tooltip "what decision it supports" text, and they end up in the generated dictionary doc)?

No code will be written until these are answered.
