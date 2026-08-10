"""The /standards page family: the value cell, the metric rows, the family section panel
and the page body of Standards & Execution Indices.

Monolith split, phase 4 slice 20 (ADR-0384), extracted VERBATIM from ``web/app.py``: every
function moves byte-for-byte — docstrings, comments and HTML f-strings unchanged — and only the
module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour. Here
the seed is a single route, ``GET /standards``: the page has **no export route at all** (grep
and the route census agree — the family's ⤓ EXCEL points at the *analysis* workbook, which
``export_analysis`` serves without touching a member). FOUR names in ONE contiguous block
(app.py 8764-8930).

**Census-exact, and that is not what makes it membership.** The ``standards`` prefix finds the
same 4 names / 161 ast lines the referrer walk does — 1.00x, the second exact closure of the
split (ADR-0378 was the first). The walk is still what assigns membership: a census can be exact
and still not be membership, and only the walk can say so (standing trap 1).

**Zero descent, zero shared names, zero owned constants.** Every other name the four members
touch resolves to an *import*: ``_e``, ``_utility_takeaway`` (chrome); ``_ANALYSIS_XLSX_TITLE``,
``_panel_head``, ``_prov_chip``, ``_shell_tools``, ``_status_class`` (components);
``SessionState``, ``_Analysis`` (state); ``metric_doc`` (help); ``AuditCheck`` (engine.dcma_audit);
``CheckStatus``, ``MetricResult`` and the eight ``compute_*`` families (engine.metrics);
``Schedule`` (model); ``Sequence``, ``quote`` (stdlib). The free-name pass that caught
ADR-0383's four stranded constants finds **no** module-level assignment owned by this block.

Layering: ``app`` -> ``standards`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import quote

from schedule_forensics.engine.dcma_audit import AuditCheck
from schedule_forensics.engine.metrics import (
    compute_bri,
    compute_completion_performance,
    compute_fei,
)
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult
from schedule_forensics.engine.metrics.cei import compute_cei
from schedule_forensics.engine.metrics.evm import compute_evm_indices
from schedule_forensics.engine.metrics.float_ratio import compute_float_ratio
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.engine.metrics.sem import compute_sem
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e, _utility_takeaway
from schedule_forensics.web.components import (
    _ANALYSIS_XLSX_TITLE,
    _panel_head,
    _prov_chip,
    _shell_tools,
    _status_class,
)
from schedule_forensics.web.help import metric_doc
from schedule_forensics.web.state import SessionState, _Analysis


def _standards_value_cell(m: AuditCheck | MetricResult) -> str:
    # NB: the informational indices (Fuse/SEM) carry NA *status* by design (no pass/fail
    # threshold) while still computing a real value — so the display keys on whether a
    # denominator/population exists, never on the status pill (a 0-denominator reads "—").
    if m.unit == "ratio":
        return f"{round(m.value, 2)}" if m.population > 0 else "—"
    if m.unit == "count":
        return str(m.count) if m.population > 0 else "—"
    if m.population:
        pct = m.value if m.unit == "%" else 100.0 * m.count / m.population
        return f"{m.count} <span class=muted>of {m.population}</span> ({pct:.1f}%)"
    return str(m.count) if m.status is not CheckStatus.NOT_APPLICABLE else "—"


def _standards_rows(items: Sequence[tuple[AuditCheck | MetricResult | None, str, str]]) -> str:
    """Rows of (metric-or-None, metric_id-for-docs, fallback-name): value + status pill +
    threshold + verbatim formula + source, all from the single help.py dictionary (the same
    entries the formula-audit test pins to the .aft Bible)."""
    out = []
    for m, mid, fallback_name in items:
        doc = metric_doc(mid) if mid else None
        # an explicit row label (the SEM family names) outranks the engine's internal name
        name = _e(fallback_name or (m.name if m is not None else (doc.name if doc else mid)))
        if m is None:
            val, status_html = "—", "<td class=muted>not built — PR-M2</td>"
        else:
            val = _standards_value_cell(m)
            status_html = f'<td class="{_status_class(m.status)}">{_e(m.status)}</td>'
        thr = _e(doc.threshold) if doc and doc.threshold else "—"
        formula = f"<code>{_e(doc.formula)}</code>" if doc and doc.formula else "—"
        source = _e(doc.source) if doc and doc.source else "—"
        out.append(
            f"<tr><td>{name}</td><td class=num>{val}</td>{status_html}"
            f"<td>{thr}</td><td class=std-formula>{formula}</td><td>{source}</td></tr>"
        )
    return "".join(out)


def _standards_section(
    title: str,
    note: str,
    rows_html: str,
    *,
    tools: str = "",
    prov: str = "",
    take: str = "",
    export_url: str = "",
) -> str:
    """One formula-first metric family as a contract panel (rank 12, ADR-0327): head strip +
    tools + provenance chip, an optional ``.sf-take`` (data-driven counts), the muted ``note``
    as the read-me line, then the table. ``export_url`` becomes the panel ``data-export``
    panelkit.js follows — pass it ONLY with a covering endpoint (dead/lying ⤓ is a defect
    class; the Fuse/SEM families have no covering export today, so their panels carry ⛶ only).
    Defaults keep the pre-rank-12 shape byte-compatible for any caller that passes none."""
    export_attr = f' data-export="{_e(export_url)}"' if export_url else ""
    take_html = f"<p class=sf-take data-no-i18n>{take}</p>" if take else ""
    return (
        f"<div class=panel{export_attr}>{_panel_head(title, tools=tools, prov=prov)}"
        f"{take_html}<p class=muted>{note}</p>"
        '<div style="overflow-x:auto"><table class=card-table>'
        "<tr><th scope=col>Metric</th><th scope=col>Value</th><th scope=col>Status</th>"
        "<th scope=col>Threshold</th><th scope=col>Formula</th><th scope=col>Source</th></tr>"
        f"{rows_html}</table></div></div>"
    )


def _standards_body(
    st: SessionState, key: str, sch: Schedule, prior: Schedule | None, analysis: _Analysis
) -> str:
    """The Standards & Execution Indices page: DCMA-14 + the NASA/Acumen-Fuse execution indices
    + the SEM family, one formula-first row per metric, computed on the LATEST loaded file."""
    fname = _e(sch.source_file or sch.name)
    # the takeaway states the DCMA-14 outcome the §1 section already renders (audit.passed/failed)
    _ck = analysis.audit
    _scored = _ck.passed + _ck.failed
    _head = (
        (
            f"{_ck.failed} of {_scored} scored DCMA-14 checks fail on this schedule."
            if _ck.failed
            else f"All {_scored} scored DCMA-14 checks pass on this schedule."
        )
        if _scored
        else "No DCMA-14 check scored on this schedule."
    )
    takeaway = _utility_takeaway(
        _head,
        f"{_ck.passed} passed &middot; {_ck.failed} failed &middot; {_ck.not_applicable} N/A on "
        f"<b>{fname}</b>, plus the NASA/Acumen-Fuse execution indices and the SEM family below. "
        "Every row names its formula and source.",
    )
    intro = (
        f"<div class=panel><p>All values on this page are computed from the latest file, "
        f"<b>{fname}</b> (period metrics use the prior file's data date"
        f"{' — none loaded' if prior is None else ''}). Formulas and sources are the same "
        "entries the metric dictionary pins to the NASA Acumen metric library; each family "
        "below names its framework.</p></div>"
    )
    # §1 DCMA-14 — re-projected from the cached audit (no new math). The panel contract
    # (rank 12, ADR-0327): the old counts note becomes the .sf-take (same figures, verbatim),
    # a read-me line explains the row anatomy, and ⤓ EXCEL points at the EXISTING per-schedule
    # analysis workbook — its DCMA-14 sheet is this table's measured data (the formula/source
    # columns are pinned dictionary metadata, not measurements; docs/METRIC-DICTIONARY.md
    # carries them).
    audit = analysis.audit
    prov = _prov_chip(sch)
    dcma_rows = _standards_rows([(c, c.metric_id, "") for c in audit.checks])
    dcma = _standards_section(
        "DCMA-14 point assessment",
        "One row per DCMA-14 check: the measured value, its PASS / FAIL / N&#47;A status, the "
        "pass threshold, and the verbatim library formula and source. ⤓ EXCEL exports this "
        "schedule's analysis workbook — the DCMA-14 sheet is this table's data.",
        dcma_rows,
        tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE),
        prov=prov,
        take=f"{audit.passed} passed · {audit.failed} failed · {audit.not_applicable} N/A "
        f"on {fname}.",
        export_url=f"/export/xlsx/analysis/{quote(key, safe='')}",
    )
    # §2 NASA / Acumen-Fuse execution indices (single-file forms; CEI needs a prior version)
    idx: list[tuple[AuditCheck | MetricResult | None, str, str]] = []
    hmi = compute_hmi(sch, prior.status_date if prior is not None else None)
    idx += [(hmi[k], k, "") for k in ("hmi_tasks", "hmi_milestones")]
    if prior is not None:
        cei = compute_cei(prior, sch)
        idx += [(cei[k], k, "") for k in sorted(cei)]
    fei = compute_fei(sch)
    idx += [(fei[k], k, "") for k in ("fei_starts", "fei_finish")]
    idx.append((compute_bri(sch), "bri_cumulative", ""))
    fr = compute_float_ratio(sch, analysis.cpm)
    idx += [(fr[k], k, "") for k in ("float_ratio", "float_ratio_aggregate")]
    completion = compute_completion_performance(sch)
    if "mei" in completion:
        idx.append((completion["mei"], "mei", ""))
    evm = compute_evm_indices(sch, analysis.cpm)
    if "spi_t_acumen" in evm:
        idx.append((evm["spi_t_acumen"], "spi_t_acumen", ""))
    cei_note = "" if prior is not None else " CEI needs ≥2 loaded versions — load a prior update."
    # §2/§3 carry ⛶ only: NO existing export covers the Fuse-index or SEM families (the
    # workbench workbook stops at DCMA-14 / Schedule Quality / Float; the performance workbook
    # ships different datasets) — a ⤓ here would lie (ADR-0327 records the residual).
    fuse = _standards_section(
        "NASA / Acumen-Fuse execution indices",
        "Hit-or-Miss, Current/Baseline Execution, Forecast Execution, Float Ratio™, MEI and "
        f"SPI(t) — the Fuse-parity forms the /performance trends chart over time.{cei_note}",
        _standards_rows(idx),
        tools=_shell_tools(),
        prov=prov,
    )
    # §3 Schedule Execution Metrics (SEM) — the full Bible family (engine/metrics/sem.py),
    # validated verbatim against the committed Fuse DCMA report SEM rows (ADR-0238)
    sem_results = compute_sem(sch, prior)
    sem_rows = _standards_rows([(m, mid, "") for mid, m in sem_results.items()])
    fri_note = (
        ""
        if prior is not None
        else " FRI Current needs a prior loaded version (its "
        "PreviousFinish join) — it reads N/A here, as the reference tool prints."
    )
    sem = _standards_section(
        "Industry Standards — Schedule Execution Metrics (SEM)",
        "The Bible's SEM family (SEM01-SEM09), computed verbatim from the pinned library "
        f"formulas and validated against the committed Fuse SEM exports.{fri_note}",
        sem_rows,
        tools=_shell_tools(),
        prov=prov,
    )
    return takeaway + intro + dcma + fuse + sem + '\n<script src="/static/panelkit.js"></script>'
