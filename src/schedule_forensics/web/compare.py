"""The /compare page family: the chapter-10 "What changed" header and the compare body.

Monolith split, phase 3 slice 18 (ADR-0382), extracted VERBATIM from ``web/app.py``: both
functions move byte-for-byte — every docstring, comment and HTML f-string unchanged — and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/compare`` page route and the ``/export/{fmt}/compare`` signals export): TWO names in ONE
contiguous block (app.py 7762-7929) — the version-diff story header and the two-panel body.

**The closure equals the census, and nothing was folded in first.** The ``compare`` prefix finds
2 names / 166 ast lines; the referrer walk over both routes finds the same 2 / 166 (1.00x).
Every other name the two members touch resolves to an *import* — ``_e`` (chrome);
``_metric_help_cell``, ``_pair_prov_chip``, ``_panel_head``, ``_shell_tools``, ``_stat_cards``,
``_status_stack`` (components); ``Schedule`` (model); ``CPMResult``, ``offset_to_datetime``,
``diff_versions``, ``detect_manipulation``, ``trend_across_versions``,
``compute_net_finish_impact`` (engine) — so there is nothing to descend into. The prefix remains
a finder and the walk remains the definition (ADR-0378).

**The export route contributes NO movers.** ``export_compare`` re-derives the signals itself
(``detect_manipulation`` -> ``findings_table`` -> ``_export_response``) rather than calling
``_compare_body``; its app-level callee set is empty, measured. So a page-only probe anchor does
not understate either member here — the ADR-0378 trap is checked, not assumed.

``_sources_line``, ``_export_bar``, ``_skipped_notice``, ``_focus_panel`` and ``_pair_versions``
are called by the ROUTE, not by a mover: routes live in ``create_app`` and import downward, so a
route-only referrer never forces a descent (ADR-0378).

Layering: ``app`` -> ``compare`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.diff import diff_versions
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import compute_net_finish_impact
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _metric_help_cell,
    _pair_prov_chip,
    _panel_head,
    _shell_tools,
    _stat_cards,
    _status_stack,
)


def _what_changed_header(
    prior: Schedule, current: Schedule, prior_cpm: CPMResult, current_cpm: CPMResult
) -> str:
    """Chapter 10 "What changed" (ADR-0208): the data-driven takeaway + a change KPI strip + the
    activity-change and logic-change bars, from the UniqueID-matched version diff the page already
    computes (diff_versions — no new math). Compares the two latest loaded versions."""
    diff = diff_versions(prior, current)
    added = len(diff.added_tasks)
    removed = len(diff.deleted_tasks)
    changed = len(diff.changed_tasks)
    links_added = len(diff.added_links)
    links_removed = len(diff.removed_links)
    # Count on the SAME population diff_versions uses (non-summary, INCLUDING inactive tasks —
    # deactivation is a tracked change). compute_activity_makeup drops inactive tasks, so mixing it
    # with the diff counts miscounts "Unchanged" whenever a version carries deactivated activities.
    total_current = sum(1 for t in current.tasks if not t.is_summary)
    in_both = max(total_current - added, 0)
    unchanged = max(in_both - changed, 0)

    prior_fin = offset_to_datetime(prior.project_start, prior_cpm.project_finish, prior.calendar)
    cur_fin = offset_to_datetime(
        current.project_start, current_cpm.project_finish, current.calendar
    )
    fin_delta = (cur_fin.date() - prior_fin.date()).days

    def _acts(n: int) -> str:
        return "activity" if n == 1 else "activities"

    if fin_delta > 0:
        fin = f"; the finish moved out {fin_delta} day{'s' if fin_delta != 1 else ''}"
    elif fin_delta < 0:
        n = -fin_delta
        fin = f"; the finish pulled in {n} day{'s' if n != 1 else ''}"
    else:
        fin = "; the finish held"
    if added + removed + changed + links_added + links_removed == 0:
        takeaway = (
            f"Nothing changed between {_e(prior.source_file or prior.name)} and "
            f"{_e(current.source_file or current.name)} — the two versions are identical."
        )
    else:
        takeaway = (
            f"Between the two versions, {changed} {_acts(changed)} changed, {added} added and "
            f"{removed} removed, with {links_added} logic links added and {links_removed} "
            f"removed{fin}."
        )

    kpi = _stat_cards(
        [
            ("Activities changed", str(changed)),
            ("Added", str(added)),
            ("Removed", str(removed)),
            ("Logic added", str(links_added)),
            ("Logic removed", str(links_removed)),
            ("Finish move", f"{fin_delta:+d} d" if fin_delta else "0 d"),
        ]
    )
    act_bar = _status_stack(
        "Activity changes",
        "How the activity list moved version-to-version, matched by unique id.",
        [
            ("Added", added, "--ok"),
            ("Changed", changed, "--warn"),
            ("Removed", removed, "--bad"),
            ("Unchanged", unchanged, "--muted"),
        ],
        f"{total_current} activities in the newer version",
    )
    logic_bar = _status_stack(
        "Logic changes",
        "Predecessor/successor links added vs removed between the two versions.",
        [("Links added", links_added, "--ok"), ("Links removed", links_removed, "--bad")],
        f"{links_added + links_removed} link changes",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{act_bar}{logic_bar}</div>'
    )


def _compare_body(
    prior: Schedule,
    current: Schedule,
    prior_cpm: CPMResult,
    current_cpm: CPMResult,
    *,
    vfrom: int = 1,
    vto: int = 2,
) -> str:
    """Chapter-10 body (Mission Ops rank 5, ADR-0298): the two legacy tables wearing the panel
    contract. Presentation only — every figure is the same engine output the flat panels already
    rendered. The Net-Finish-Impact sentence MOVES into the trend panel's takeaway slot verbatim,
    and the manipulation-signals table (the page's forensic headline) takes the verdict-band wash,
    toned by the ENGINE's own worst severity. Loaded-term guard: the takeaway lines only restate
    engine findings — no wording is added around the engine's signal titles."""
    manip = detect_manipulation(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    trend = trend_across_versions([prior, current])
    impact = compute_net_finish_impact(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    days = int(impact.value)
    if days < 0:
        impact_take = (
            f"Net Finish Impact: <b class=fail>{days} calendar days</b> "
            "&mdash; the project finish moved later since the prior version."
        )
    elif days > 0:
        impact_take = (
            f"Net Finish Impact: <b class=pass>+{days} calendar days</b> "
            "&mdash; the project finish moved earlier since the prior version."
        )
    else:
        impact_take = (
            "Net Finish Impact: <b class=pass>0 calendar days</b> "
            "&mdash; the project finish is unchanged."
        )
    manip_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.title)}</td>'
        f"<td class=muted>{_e(f.course_of_action)}</td></tr>"
        for f in manip
    )
    trend_rows = "".join(
        f"<tr><td>{_e(p.source_file or p.version_index)}</td><td>{_e(p.project_finish.date())}</td>"
        f"<td>{p.completed}</td><td>{p.in_progress}</td><td>{p.critical}</td></tr>"
        for p in trend
    )
    prov = _pair_prov_chip(prior, current, vfrom, vto)
    # Version-trend panel: the table IS its own data drawer (no ▦ DATA — the /evm precedent) and
    # no existing endpoint serves exactly these rows, so the toolbar is ⛶ only (never a dead ⤓).
    trend_head = _panel_head(
        f"Version trend &mdash; {_e(prior.source_file or 'prior')} &rarr; "
        f"{_e(current.source_file or 'current')}",
        tools=_shell_tools(),
        prov=prov,
    )
    # Manipulation-signals panel: verdict-band wash toned by the worst ENGINE severity present
    # (HIGH → --bad, MEDIUM/LOW → --warn, none → --ok); ⤓ EXCEL rides the EXISTING
    # /export/xlsx/compare endpoint, which exports exactly these signals.
    severities = {str(f.severity) for f in manip}
    if "HIGH" in severities:
        band_cls = "vb-at-risk"
    elif severities:
        band_cls = "vb-watch"
    else:
        band_cls = "vb-on-track"
    if manip:
        worst = next(s for s in ("HIGH", "MEDIUM", "LOW", "INFO") if s in severities)
        n = len(manip)
        sig_take = (
            f"{n} manipulation-trend signal{'s' if n != 1 else ''} between these two versions "
            f"&mdash; highest severity {worst}; each signal and its course of action is the "
            "engine's own finding, listed below."
        )
    else:
        sig_take = "No manipulation signals detected (honest progress)."
    sig_head = _panel_head(
        "Manipulation-trend signals",
        tools=_shell_tools(export_title="Export these manipulation signals — opens in Excel"),
        prov=prov,
    )
    return f"""
<div class=panel>{trend_head}
<p class=sf-take data-no-i18n>{impact_take}</p>
<p class=muted>Versions are ordered by data date (oldest first); the trend reads prior &rarr; current.</p>
<table><tr><th scope=col>Version</th><th scope=col>Project finish</th><th scope=col class=metric-th>{_metric_help_cell("Completed", "completed")}</th><th scope=col class=metric-th>{_metric_help_cell("In progress", "in_progress")}</th><th scope=col class=metric-th>{_metric_help_cell("Critical", "critical")}</th></tr>{trend_rows}</table></div>
<div class="panel verdict-band vb-stack {band_cls}" data-export="/export/xlsx/compare">{sig_head}
<p class=sf-take data-no-i18n>{sig_take}</p>
<table><tr><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
{manip_rows or "<tr><td colspan=3 class=muted>No manipulation signals detected (honest progress).</td></tr>"}</table></div>"""
