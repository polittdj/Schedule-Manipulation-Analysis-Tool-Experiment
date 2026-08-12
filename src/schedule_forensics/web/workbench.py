"""The /workbench page family: the Metric Workbench body (ADR-0204).

Monolith split, phase 4 slice 24 (ADR-0389), extracted VERBATIM from ``web/app.py``: the one
definition moves byte-for-byte -- docstring, comments and HTML f-strings unchanged -- and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/workbench`` + ``/api/workbench`` + ``/api/workbench/drill`` + ``/export/{fmt}/workbench``
+ ``/export/{fmt}/workbench-drill/{name}``. ONE name, ZERO descents -- the ribbon and drill grid
the page shows are drawn client-side by ``workbench.js`` from those APIs, and the three helpers
that feed them (``_workbench_versions``, ``_workbench_drill_rows``, and the drill export) are
nested inside ``create_app``, so they stay there.

Layering: ``app`` -> ``workbench`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from collections.abc import Sequence

from schedule_forensics.engine.metric_catalog import catalog_entries
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e, _utility_takeaway
from schedule_forensics.web.components import _panel_head, _series_prov_chip, _shell_tools


def _workbench_body(versions: Sequence[Schedule]) -> str:
    """The Metric Workbench (ADR-0204): an Acumen-style page — the selectable metric library on
    the left, the ribbon (chosen metrics x versions, oldest-first) on the right, and a
    click-to-drill grid (filter / sort / group / add columns / Excel) below. The library is
    server-rendered so it works before JS; ``workbench.js`` reads the checkboxes to draw the
    ribbon and drill via ``/api/workbench`` + ``/api/workbench/drill``.

    Panel contract (rank 12 toolbar sweep, ADR-0327; blocker cleared by ADR-0326): the one
    panel wears the head strip + ⛶ ENLARGE + the whole-series provenance chip (``versions``).
    The deliberate decisions:

    * **⤓ EXCEL is NOT in the strip** — the ribbon's exports already ship as the panel's own
      labeled links (Export ribbon Excel / Word, pinned by test_workbench_view), which is how
      DESIGN-SYSTEM §3:78 "tables get ⤓ EXCEL only" was recorded satisfied in ADR-0326; a head
      glyph would be a SECOND affordance for the same URL inside one panel (the round-11
      inert-duplicate class). The drill grid ships its own export button (workbench.js) that
      rebuilds ``&cols=<live selection>`` per render — exactly what a static ``data-export``
      cannot follow (the round-10 defect).
    * **no ▦ DATA** — the ribbon and drill ARE tables; a drawer would duplicate the panel's
      own content (the home-shell precedent)."""
    families: dict[str, list[tuple[str, str, str]]] = {}
    for e in catalog_entries():
        families.setdefault(e.family, []).append((e.metric_id, e.name, e.describe))
    _n_metrics = sum(len(v) for v in families.values())
    takeaway = _utility_takeaway(
        f"{_n_metrics} metrics across {len(families)} families are available to compare, "
        "version by version.",
        "Pick metrics on the left; the ribbon plots them across every loaded version oldest-first, "
        "and any cell drills to the activities behind it. Each metric names the formula and source "
        "the metric dictionary pins.",
    )
    groups = ""
    for fam, metrics in families.items():
        checks = "".join(
            f'<label class=wb-metric title="{_e(desc)}">'
            f'<input type=checkbox class=wb-pick value="{_e(mid)}" checked> {_e(name)}</label>'
            for mid, name, desc in metrics
        )
        groups += (
            f'<div class=wb-family data-family="{_e(fam)}">'
            f"<div class=wb-family-head><b>{_e(fam)}</b>"
            f'<button type=button class="linkbtn wb-fam-all" data-family="{_e(fam)}">all</button>'
            f'<button type=button class="linkbtn wb-fam-none" data-family="{_e(fam)}">none</button>'
            f"</div>{checks}</div>"
        )
    return f"""{takeaway}
<div class=panel>
{_panel_head("Metric Workbench", tools=_shell_tools(), prov=_series_prov_chip(list(versions)))}
<p class=muted>Pick any metrics from the <b>validated library</b> on the left; each is computed for
every loaded schedule <b>independently</b> and laid out oldest&rarr;newest, Acumen-style. Click any
value to list the activities behind it &mdash; then filter, sort, group by a project field, add
columns, and export. Every figure is the same gate-locked number the rest of the tool reports
(no re-interpretation of raw formulas).</p>
<div class=viz-controls>
<button type=button id=wbAll class=linkbtn>Select all</button>
<button type=button id=wbNone class=linkbtn>Clear</button>
<a class=btn href="/export/xlsx/workbench">Export ribbon (Excel)</a>
<a class=btn href="/export/docx/workbench">Ribbon (Word)</a>
</div>
<div class=wb-layout>
<aside class=wb-library aria-label="Metric library">{groups}</aside>
<div class=wb-ribbon-wrap><div id=wbRibbon class=wb-ribbon aria-live=polite></div></div>
</div>
<div id=wbDrill class=wb-drill></div>
</div>
<script src="/static/workbench.js"></script>
<script src="/static/panelkit.js"></script>"""
