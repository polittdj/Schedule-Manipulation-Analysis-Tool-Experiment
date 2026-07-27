# AXIS-TITLES-PATCH — Law 2's missing captions

Applyable spec for PROMPT 2. Governing law: repo `CLAUDE.md` + `docs/DESIGN-SYSTEM.md`. Labelling only — no plotted value, scale, domain, or engine call changes.

**What this workspace could not execute:** no Python runtime, no app, no network, so the gates (`pytest`, `ruff`, `mypy`, `bandit`, `pip-audit`, wheel + 9 installers) and the rendered verification must be run in the repo. The census, the convention, the per-chart captions and the anti-regression test source below are complete and ready to apply.

---

## 1. Census — corrected. It is worse than "3 of 21"

Grepped all 33 chart-bearing modules for `xLabel` / `yLabel` / `axisTitle` / `axisLabel` / `rotate(-90)`:

| Module | axis-title state | evidence |
|---|---|---|
| `performance.js` | **the only real implementation** — `opts.xLabel` / `opts.yLabel` drawn at **L457–L458**, consumed by 3 scatter charts (**L463, L467, L474**) | `txt(svg, R, B - 4, opts.xLabel, {anchor:"end", size:9, weight:"bold"})` · `txt(svg, L + 4, T + 9, opts.yLabel, {size:9, weight:"bold"})` |
| `scatter.js` | **ad-hoc, Y only** — one rotated caption built inline at **L103** with `svgEl("text", …, transform:"rotate(-90 …)")`, `font-size:11` hard-coded. No X caption, does not use `xLabel`/`yLabel`. | second convention — must be folded into the first |
| `margin.js` | **none** — `docs/UI-INVENTORY.md` scored it "yes" in error. Its `xLabels()` (**L32**, used **L139**) generates **tick** labels, not a caption. My §2 token heuristic matched the substring `xLabel`. | **correct the inventory row** |
| the other 30 modules | **zero hits** on every axis-title token — `gantt`, `histogram`, `curves`, `scurve`, `drift`, `path`, `path_evolution`, `driving_path`, `driving_tiers`, `cei`, `resources`, `margin_dashboard`, `scorecards`, `ribbon_drill`, `drilldown`, `findings_drill`, `workbench`, `volatility`, `trend` (1,165 lines), `trend_drill`, `sra`, `sra_grid`, `sra_jcl`, `sra_risk`, `sra_ssi`, `wbs`, `whatif` | — |

So the true baseline is **one** module with the convention (covering 3 charts) plus **one** ad-hoc half-caption — not three modules. Tick labels are indeed broadly present; named captions are essentially absent.

**Also flagged:** performance.js draws its captions at `size: 9`, which the crispness work (`docs/CRISPNESS-PATCH.md`) forbids. The shared helper below reads the type token instead, so this batch and that batch cannot fight.

---

## 2. The one convention — promote it, do not clone it

Keep the **names** (`xLabel`, `yLabel`) and the **placement** (X caption right-aligned at the bottom-right of the plot; Y caption at the top-left, above the axis) from `performance.js`. The only change is that the drawing code moves into `chartframe.js` so 30 modules can call it instead of copy-pasting:

```js
/* chartframe.js — the single axis-caption implementation (promoted from performance.js
   L457-L458 unchanged in placement and option names; size now comes from the token). */
SFChartFrame.axisTitles = function (svg, geom, opts) {
  var L = geom.L, R = geom.R, T = geom.T, B = geom.B;
  if (opts.xLabel) SFChartFrame.text(svg, R, B - 4, opts.xLabel,
      { anchor: "end", cls: "ch-at", weight: "bold" });
  if (opts.yLabel) SFChartFrame.text(svg, L + 4, T + 9, opts.yLabel,
      { cls: "ch-at", weight: "bold" });
};
```

```css
/* base.css — the caption's only styling. No numeric size in JS, per Law 1. */
.ch-at { font-family: var(--sf-font-mono); font-size: var(--sf-fs-label);
         fill: var(--muted); letter-spacing: .08em; text-transform: uppercase; }
```

Then in every chart module: pass `xLabel`/`yLabel` in the existing options object and call `SFChartFrame.axisTitles(svg, geom, opts)` after the ticks are drawn. `performance.js` deletes its local copy and calls the shared one (its three `xLabel`/`yLabel` values are unchanged). `scatter.js` drops the inline `rotate(-90)` text at L103 and calls the helper, gaining the X caption it never had.

**Rotated Y captions are not adopted.** `performance.js` places the Y caption horizontally at the top-left; `scatter.js` rotates it. Two placements is two conventions — keep the `performance.js` one, because horizontal text at 11px stays legible in all four themes and never collides with the widest tick label.

---

## 3. Captions and units, per chart

Format: `CAPTION (UNIT)` — uppercase, unit in parentheses only where a unit exists, no arrows, no trailing punctuation.

| Module | X caption | Y caption |
|---|---|---|
| `gantt.js` | PROJECT TIME (TICK = CALENDAR MONTH) | ACTIVITY (DRIVING PATH FIRST) |
| `histogram.js` | TOTAL FLOAT BAND (WORKDAYS) | ACTIVITIES (COUNT) |
| `curves.js` | MONTH | CUMULATIVE VALUE (\$M) |
| `scurve.js` | MONTH | CUMULATIVE COMPLETION (%) |
| `drift.js` | SCHEDULE VERSION (UPDATE) | SLIP AGAINST BASELINE (WORKDAYS) |
| `path.js` | PROJECT TIME (TICK = CALENDAR MONTH) | ACTIVITY ON THE PATH |
| `path_evolution.js` | SCHEDULE VERSION (UPDATE) | DRIVING-PATH MEMBERSHIP CHANGED (%) |
| `driving_path.js` | PROJECT TIME (TICK = CALENDAR MONTH) | ACTIVITY (DRIVING ORDER) |
| `driving_tiers.js` | PROJECT TIME (TICK = CALENDAR MONTH) | PATH TIER (1 = DRIVES THE TARGET) |
| `cei.js` | MONTH | ACTIVITIES (COUNT) — secondary axis: EXECUTION INDEX (RATIO) |
| `resources.js` | WEEK (COMMENCING) | DEMAND (FTE) |
| `margin.js` | SCHEDULE VERSION (UPDATE) | MARGIN REMAINING (WORKDAYS) |
| `margin_dashboard.js` | SCHEDULE VERSION (UPDATE) | MARGIN REMAINING (WORKDAYS) — burn panel: MARGIN CONSUMED (WORKDAYS) |
| `scorecards.js` | SCORE (0–100) | ASSESSMENT AREA |
| `scatter.js` | *(per chart — keep the existing metric name)* | *(per chart — keep the existing metric name)* |
| `ribbon_drill.js` | DCMA-14 CHECK | SHARE OF MEASURED POPULATION (%) |
| `drilldown.js` | ACTIVITY | TOTAL FLOAT (WORKDAYS) |
| `findings_drill.js` | FINDING | OCCURRENCES (COUNT) |
| `workbench.js` | SCHEDULE VERSION | METRIC (LIBRARY) |
| `volatility.js` | SCHEDULE VERSION (UPDATE) | *(per visual — 10 visuals; see §3.1)* |
| `trend.js` | SCHEDULE VERSION (UPDATE) | *(per metric — see §3.1)* |
| `trend_drill.js` | SCHEDULE VERSION (UPDATE) | METRIC VALUE |
| `sra.js` | SIMULATED FINISH DATE | RUNS ENDING IN WINDOW (COUNT) — secondary: CUMULATIVE PROBABILITY (%) |
| `sra_grid.js` | ACTIVITY | THREE-POINT DURATION (WORKDAYS) |
| `sra_jcl.js` | COST AT COMPLETION (\$M) | FINISH DATE |
| `sra_risk.js` | RISK DRIVER | CORRELATION WITH FINISH (COEFFICIENT) |
| `sra_ssi.js` | ACTIVITY | SCHEDULE SENSITIVITY INDEX (0–1) |
| `wbs.js` | WBS BRANCH | PERCENT COMPLETE (%) |
| `whatif.js` | SCENARIO | FINISH SHIFT (WORKDAYS) |

### 3.1 The two modules where the caption must be per-visual, not per-module

`trend.js` (1,165 lines) and `volatility.js` (486 lines) each render many charts sharing one X axis (schedule version). Their Y caption must come from the metric definition already used for the series name + its unit — pass `yLabel: metric.label + " (" + metric.unit + ")"` rather than hard-coding 10–20 strings. If a metric has no unit in the catalogue, that is a **metric-catalogue gap to report**, not a caption to invent.

### 3.2 Exempt from the rule (and from the test)

`chartframe.js` (frame, draws no data) · `timeaxis.js` / `timescale.js` (shared ruler consumed by charts that carry their own captions) · `legend_toggle.js` · `globe.js` (insignia/status light, not a data visual) · `sysmon.js`, `heartbeat.js`, `hints.js`, `a11y.js`, `persist.js`, `colresize.js`, `taskinfo.js`, `tooltips.js`, `vizhints.js`, `theme.js`, `story.js`, `target.js`, `translate.js`, `ask.js`, `chrome.js`, `checklist.js`, `ai_polish.js`, `groups.js`, `settings.js`, `home.js`, `dashboard.js`, `mission.js` (tiles link out to the charts), `app.js`.

A Gantt is **not** exempt: its Y axis is the activity list and its X axis is time, and both get captions.

---

## 4. The anti-regression test

`tests/web/test_axis_titles.py` — static, no browser, runs in the existing suite:

```python
"""Every chart module must caption both axes (DESIGN-SYSTEM Law 2).

Static guard: a module that draws axis ticks must also call the single shared
caption helper, and must not re-implement it locally. Kept static (no browser) so
it runs in the same second as the rest of the suite and cannot be skipped in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"

#: Modules that legitimately draw no data axes (frames, rulers, chrome, insignia).
EXEMPT = {
    "chartframe.js", "timeaxis.js", "timescale.js", "legend_toggle.js", "globe.js",
    "sysmon.js", "heartbeat.js", "hints.js", "a11y.js", "persist.js", "colresize.js",
    "taskinfo.js", "tooltips.js", "vizhints.js", "theme.js", "story.js", "target.js",
    "translate.js", "ask.js", "chrome.js", "checklist.js", "ai_polish.js", "groups.js",
    "settings.js", "home.js", "dashboard.js", "mission.js", "app.js", "scatter.js",
}

#: A module is "a chart" if it draws SVG/DOM tick labels of its own.
TICKY = re.compile(r"""(svgEl\(\s*["']text["']|createElementNS\([^)]*["']text["']|class=["'][^"']*(?:-tick|tick-|ch-xl|ch-yl)|["'](?:ch-xl|ch-yl|g-tick|pv-tick)["'])""")
CALLS_HELPER = re.compile(r"SFChartFrame\.axisTitles\s*\(")
LOCAL_CAPTION = re.compile(r"""(opts\.(?:xLabel|yLabel)\s*,|rotate\(-90|axisTitle\s*=)""")


def chart_modules() -> list[Path]:
    return sorted(p for p in STATIC.glob("*.js") if p.name not in EXEMPT)


@pytest.mark.parametrize("mod", chart_modules(), ids=lambda p: p.name)
def test_chart_module_captions_both_axes(mod: Path) -> None:
    src = mod.read_text(encoding="utf-8")
    if not TICKY.search(src):
        pytest.skip(f"{mod.name} draws no axis ticks")
    assert CALLS_HELPER.search(src), (
        f"{mod.name} draws axis ticks but never calls SFChartFrame.axisTitles(...) — "
        "DESIGN-SYSTEM Law 2 requires a titled X and Y axis on every visual. "
        "Pass xLabel/yLabel and call the shared helper; see docs/AXIS-TITLES-PATCH.md §3."
    )
    for call in CALLS_HELPER.finditer(src):
        window = src[call.end() : call.end() + 400]
        assert "xLabel" in window and "yLabel" in window, (
            f"{mod.name}: axisTitles() called without both xLabel and yLabel nearby "
            "(one-axis captions are not acceptable)."
        )


def test_no_module_reimplements_the_caption_helper() -> None:
    """Only chartframe.js may contain caption-drawing code (one convention, ADR-0195)."""
    offenders = [
        p.name for p in STATIC.glob("*.js")
        if p.name != "chartframe.js" and LOCAL_CAPTION.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "axis captions must be drawn only by SFChartFrame.axisTitles: " + ", ".join(offenders)
    )


def test_caption_size_comes_from_the_token_not_a_literal() -> None:
    """The caption class carries the size; a numeric font-size would break the 11px floor."""
    frame = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    body = frame[frame.find("axisTitles") :][:800]
    assert not re.search(r"size\s*:\s*\d", body), "axisTitles must not set a numeric size"
    assert "ch-at" in body, "axisTitles must apply the .ch-at class"
```

Notes on the test's design, so review is quick:
- `scatter.js` is in `EXEMPT` **only until batch 1 lands** — remove it from the set in that same commit, once its inline caption is replaced. Leaving it exempt permanently would hide the second convention.
- `test_no_module_reimplements_the_caption_helper` is what actually prevents the regression the prompt is worried about: not a missing caption, but a *second* way of drawing one.
- If the repo already has a DOM-level web test harness, add one rendered assertion per page (`.ch-at` count ≥ 2 × chart count) as a second layer. Static first: it cannot be skipped for want of a browser.

---

## 5. Batching — 5 modules per commit, in dependency order

| # | Commit | Modules | Why this order |
|---|---|---|---|
| 0 | `chore(chart): promote axisTitles to chartframe` | `chartframe.js`, `base.css` (`.ch-at`), `performance.js` (use shared), `scatter.js` (drop inline caption, gain X), + the test file | nothing else can land first; ends with the guard already green |
| 1 | `feat(chart): caption axes — schedule shape` | `gantt.js`, `histogram.js`, `drilldown.js`, `driving_path.js`, `driving_tiers.js` | the Act I charts; simplest geometry |
| 2 | `feat(chart): caption axes — time series` | `drift.js`, `curves.js`, `scurve.js`, `cei.js`, `resources.js` | shared month/week X axis |
| 3 | `feat(chart): caption axes — versions` | `path_evolution.js`, `volatility.js`, `trend.js`, `trend_drill.js`, `workbench.js` | the per-metric Y caption work (§3.1) |
| 4 | `feat(chart): caption axes — risk` | `sra.js`, `sra_grid.js`, `sra_jcl.js`, `sra_risk.js`, `sra_ssi.js` | secondary axes + the SSI grid |
| 5 | `feat(chart): caption axes — control` | `margin.js`, `margin_dashboard.js`, `scorecards.js`, `ribbon_drill.js`, `wbs.js`, `whatif.js`, `findings_drill.js`, `path.js` | remainder (8 — split if review prefers 5) |

Each commit: run the gate, screenshot the touched pages in `console` + `daylight`, and flip that batch's rows in the inventory (§6) in the same commit.

---

## 6. Inventory updates required

In `docs/UI-INVENTORY.md` §2:
1. **Correct `margin.js`** — (a) and (b) are **no**, not yes; add the footnote that `xLabels()` is a tick generator.
2. **Correct `scatter.js`** — (a) **no**, (b) **yes (ad-hoc, rotated)** until batch 0 lands, then both yes.
3. Flip (a)/(b) to **yes** per module only as its batch lands, and change the §2 preamble from "INFERRED (grep-derived)" to "verified by `tests/web/test_axis_titles.py`" for those columns once the whole table is yes.
4. Delete §2.2's "Read this before any restyle" gap note when the table is all-yes, and record the date + commit range in its place.

---

## 7. Definition of done

Same gate as PROMPT 1 (`ruff check` · `ruff format --check` · `mypy` · `pytest --cov-fail-under=70` · engine coverage ≥85% · `pytest -m parity` · `bandit` · `pip-audit`; wheel + 9 installers regenerated in lockstep; version bumped), plus:

- [ ] `pytest tests/web/test_axis_titles.py -q` green, and **red** if you delete one `axisTitles(...)` call (verify the guard actually bites before merging batch 0).
- [ ] The three dashboard goldens unchanged — `_SHA_TWO_VERSION` `d62a4f9e…58d1`, `_SHA_UNSOLVABLE` `8d7bcc38…fc16`, `_SHA_TWO_VERSION_PARITY` `51691cb7…504cb`. A caption cannot move a payload hash; if one moves, something non-labelling was changed.
- [ ] No plotted value, scale, domain, tick set, or axis range altered — diff review should show only caption strings, the helper call, and deleted local caption code.
- [ ] `grep -rn "rotate(-90" src/schedule_forensics/web/static/*.js` → empty (one convention).
- [ ] Captions legible in all four themes at 90/100/125%, including `apollo` (uppercase mono) and `daylight`.
- [ ] `docs/UI-INVENTORY.md` §2 all-yes on (a) and (b), with the two corrections from §6 applied.
- [ ] `engine/` untouched; nothing renamed; no feature added.
