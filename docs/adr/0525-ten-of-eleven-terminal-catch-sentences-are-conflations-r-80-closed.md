# ADR-0525 — Ten of the eleven remaining terminal-`.catch` sentences are conflations, one is not, and the row's census was a statement about its FILTER (R-80 CLOSED)

**Status:** Accepted · **Date:** 2026-09-22 · **Extends:** ADR-0521 / R-09 (the load/draw seam, `SFLoad.drawn`) · **Row:** R-80 (T3, S) in `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3

## Context

Roadmap row R-80 (T3, S). The row read:

> the rest of the terminal-`.catch` sentence class, UNASSESSED. A census of `.catch(` handlers
> assigning a literal to `textContent`/`innerHTML` finds **26** across 22 `web/static/*.js` files;
> ADR-0521 repaired the **16** of the `"Failed to load"` class. The other **10** … were NOT read
> site by site, so none is claimed as a conflation: a catch covering exactly one failure mode is
> not one.

The row's restraint was right and is preserved here: the reading decided each site, and one site
is **not** a defect. Its arithmetic was not.

### The census does not reproduce

Measured over all 64 `web/static/*.js` files, counting every `.catch(` whose body assigns a
**non-empty** string literal to `textContent`/`innerHTML`:

| | register row | measured | |
| --- | --- | --- | --- |
| sites | 26 | **27** | does not reproduce |
| files | 22 | **23** | does not reproduce |
| repaired by ADR-0521 | 16 | **16** | **exact** |
| residual | 10 | **11** | the row's own list enumerates 11 |

A filter that also counts an *empty* literal (`textContent = ""` — a clear, not a sentence) reads
**31 / 26**. Both filters are written down in the guard, because the population is a statement
about the filter and leaving that implicit is how the number drifted in the first place.

The row's residual list — app.js (1), ask.js (2), sra_grid.js (2), sra_ssi.js (2), sra_jcl.js (1),
settings.js (1), margin_dashboard.js (1), ai_polish.js (1) — **sums to eleven while the row calls it
ten**. An arithmetic slip in the row, not a missing site.

## The per-site verdicts

A CONFLATION is ADR-0521's class: the terminal `.catch` also spans **synchronous drawing work**, so
a draw bug is reported as a load/run failure.

| site | sentence | work the catch also spans | verdict |
| --- | --- | --- | --- |
| `app.js:1310` | "No driving path for that UID." | `renderGantt` — full Gantt + table build | **CONFLATION** (asserts a *schedule fact*) |
| `ask.js:109` | "Could not compute the driving path." | `appendChild` ×2, `renderFacts` | **CONFLATION** |
| `ask.js:179` | "Could not answer (the local model may have timed out…)" | `appendChild` ×4, `renderFacts` | **CONFLATION** (misattributes to the AI backend) |
| `margin_dashboard.js:433` | "failed: " + e | `renderRisk` | **CONFLATION** (prints the real error text) |
| `settings.js:89` | "check failed" | `fill(...)`, then an arbitrary `then()` | **CONFLATION** |
| `sra_grid.js:437` | "Could not load the grid." | `populateGroupCustom`, `render`, `renderLegend` | **CONFLATION** |
| `sra_grid.js:457` | "Save failed." | `saveSummary`, `load`'s prelude — a **successful save** reads as failed | **CONFLATION** |
| `sra_jcl.js:294` | "Run failed." | `renderResult` — a **completed** Monte-Carlo reads as a failed run | **CONFLATION** |
| `sra_ssi.js:413` | "Run failed." | `renderResult`, `dispatchEvent` | **CONFLATION** |
| `sra_ssi.js:443` | "Sensitivity failed." | builds the whole table | **CONFLATION** |
| `ai_polish.js:35` | "Local-AI interpretation unavailable — showing the engine read." | `node.innerHTML = d.html` only | **SINGLE-MODE — not a defect** |

`ai_polish.js` is the site that proves the row was right to refuse to claim all of them. `innerHTML =`
throws only under a Trusted Types policy, and the served CSP sets no `require-trusted-types-for`
directive. Even if it threw, the sentence — "showing the engine read" — stays **true**: the node keeps
its engine content. It is left untouched, and a control test fails if anyone "repairs" it.

In a tool whose output is testimony, four of these are worse than the sixteen ADR-0521 fixed: a
completed Monte-Carlo reported as a failed run, a saved edit reported as a failed save, and a drawing
bug reported as "no driving path exists for that UID" are all **true symptoms with false explanations
about the schedule itself**.

## The filter, not the tree, set the population

Two further sites are the same defect and are invisible to a literal-matching census:

* `path.js:767` — prints a **variable** (`failText`), not a literal; its `.then` runs
  `applyPayload(…)` → `render()`.
* `sra.js:497` — routes its sentence through a **setter** (`setStatus(…)`), not a direct assignment.

Both are named and **deliberately not repaired**: widening a registered population by accident is how
a census stops meaning anything, and the operator should re-price the row rather than inherit a
silent expansion. The generalisable rule, pinned by
`test_a_literal_only_census_under_reports_this_class`: **this class's census must match the SEAM — a
terminal `.catch` spanning synchronous draw work — not the SENTENCE's syntax.** A literal-matching
census under-reports by construction, in the direction that makes the work look done.

## Decision

The ten measured conflations route their drawing callback through `SFLoad.drawn(build, report)`, each
with a draw sentence in its own words that says **the data arrived and the draw did not finish**. The
terminal `.catch` is left untouched, so it says exactly what it always claimed: a transport or parse
failure. Two reports also restore state the failed `.then` would have left broken —
`margin_dashboard`'s run button is re-enabled, and `sra_grid`'s save says the deltas **were** saved.

`ai_polish.js` is not touched.

## Deliberately NOT done

* **`path.js:767` and `sra.js:497`** — real, read, named, outside the registered population.
* **Extending ADR-0521's browser poison battery** to these ten. That battery drives a real Chromium
  and poisons a *dependency global* (`SFChartFrame` / `SFGantt` / `SFDrill`); these ten draw through
  module-local helpers with no shared global to poison, so the same instrument does not transfer.
  The guards added here are static, like ADR-0521's own
  `test_every_module_routes_its_draw_through_the_loader_seam`. **This is a real gap and it is named:
  the seam is asserted to be in the chain, not observed to catch a throw in a browser.**
* **i18n entries for the new sentences** — ADR-0521 held the same and this follows it, so the two
  sets stay consistent rather than half-translated.
