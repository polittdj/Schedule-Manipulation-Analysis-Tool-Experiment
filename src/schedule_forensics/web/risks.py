"""The /risks page family: the risk matrix, the ranking, the finding cards and the page body.

Monolith split, phase 4 slice 19 (ADR-0383), extracted VERBATIM from ``web/app.py``: every
function and constant moves byte-for-byte — docstrings, comments and HTML f-strings unchanged —
and only the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/risks`` page route and the ``/export/{fmt}/risks`` workbook export): EIGHT names in ONE
contiguous block (app.py 7458-7759), plus the four module-level constants that block owns.

**The prefix would have undercounted this family by more than half.** A ``risks`` prefix census
finds 2 names / 121 ast lines; the referrer walk over both routes finds **8 names / 275 ast
lines** — 2.27x by lines and 4.0x by names, because the matrix, the ranking, the two finding-card
helpers, the band classifier and the working-days formatter carry no ``risks`` prefix at all. The
prefix is a finder; the walk is the definition (ADR-0378).

**Zero descent, zero shared names.** Every other name the eight members touch resolves to an
*import*: ``_e``, ``_expandable_more`` (chrome); ``_panel_head``, ``_shell_tools`` (components);
``Schedule`` (model); ``Category``, ``Finding``, ``SEVERITY_ORDER``, ``Severity`` (engine);
``Narrative`` (ai.citations); ``quote`` (stdlib). Nothing to descend into and nothing to
adjudicate.

**The export route contributes NO movers, measured rather than assumed.** ``export_risks``
re-derives its own findings (``recommend`` -> ``findings_table`` -> ``_export_response``) instead
of calling ``_risks_body``; its app-level callee set is empty. That is what licenses a page-only
probe anchor here — ADR-0378's trap (a page-only anchor understates an export-feeding member) is
checked off, not waved past.

Layering: ``app`` -> ``risks`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from urllib.parse import quote

from schedule_forensics.ai.citations import Narrative
from schedule_forensics.engine.recommendations import (
    SEVERITY_ORDER,
    Category,
    Finding,
    Severity,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e, _expandable_more
from schedule_forensics.web.components import _panel_head, _shell_tools

_IMPACT_LABELS = {5: "Severe", 4: "Major", 3: "Moderate", 2: "Minor", 1: "Negligible"}
_LIKELIHOOD_LABELS = {5: "Certain", 4: "Likely", 3: "Possible", 2: "Unlikely", 1: "Rare"}


def _risk_band(score: int) -> tuple[str, str]:
    """(css class, label) for a 1..25 risk score — the conventional 5x5 risk heat bands."""
    if score >= 20:
        return "rk-extreme", "Extreme"
    if score >= 12:
        return "rk-high", "High"
    if score >= 6:
        return "rk-mod", "Moderate"
    if score >= 3:
        return "rk-low", "Low"
    return "rk-min", "Minimal"


def _wd(value: float) -> str:
    """A working-days figure for a quantified field (callers guard against None)."""
    return f"{value:.1f} wd"


def _finding_quant(f: Finding) -> str:
    """The quantified read for one finding: likelihood/impact/score, plus float, driving float to
    the target (when set), and the working-day schedule exposure if it is realised."""
    bits = [
        f"Likelihood: <b>{_LIKELIHOOD_LABELS[f.likelihood_score]}</b>",
        f"Impact: <b>{_IMPACT_LABELS[f.impact_score]}</b>",
        f"Risk score: <b>{f.risk_score}</b>/25",
    ]
    if f.float_days is not None:
        bits.append(f"Total float: <b>{_e(_wd(f.float_days))}</b>")
    if f.driving_float_days is not None:
        bits.append(f"Driving float to target: <b>{_e(_wd(f.driving_float_days))}</b>")
    if f.impact_days is not None and f.impact_days > 0:
        bits.append(f"Schedule exposure: <b>{_e(_wd(f.impact_days))}</b>")
    return '<p class="finding-quant">' + " &middot; ".join(bits) + "</p>"


def _finding_card(f: Finding) -> str:
    """One risk/issue/opportunity card: severity + risk-score badge, quantified read, detail,
    recommended action, citations."""
    cites = _expandable_more(
        "; ".join(_e(str(c)) for c in f.citations[:3]), [_e(str(c)) for c in f.citations[3:]]
    )
    more = ""
    action = (
        f"<p class=finding-action><b>Recommended action:</b> {_e(f.course_of_action)}</p>"
        if f.course_of_action
        else ""
    )
    band, _label = _risk_band(f.risk_score)
    return f"""<div class="finding sev-{_e(f.severity)}" data-score="{f.risk_score}"\
 data-impact="{f.impact_score}" data-likelihood="{f.likelihood_score}">
<div class=finding-head><span class="sev-badge sev-{_e(f.severity)}">{_e(f.severity)}</span>
<span class="rk-score {band}" title="Risk score = likelihood x impact">{f.risk_score}</span>
<b>{_e(f.title)}</b> <span class=muted>[{_e(f.metric_id)}]</span></div>
<p>{_e(f.detail)}</p>{_finding_quant(f)}{action}
<p class=cite>Cited: {cites}{_e(more)}</p></div>"""


def _risk_matrix(items: list[Finding], *, prov: str = "", tools: str = "") -> str:
    """A 5x5 Likelihood (columns) by Impact (rows) heat-map of the risks + issues, each placed by
    its quantified scores; cells carry the conventional risk colour and the count landing there.

    Panel contract (ADR-0338): head strip + tools + chip + one ``.sf-take``. The empty return is
    unchanged and load-bearing — ``test_risks`` pins ``_risk_matrix([]) == ""``, and a panel head
    rendered over no matrix would be a box announcing nothing.
    """
    if not items:
        return ""
    counts: dict[tuple[int, int], int] = {}
    for f in items:
        counts[(f.impact_score, f.likelihood_score)] = (
            counts.get((f.impact_score, f.likelihood_score), 0) + 1
        )
    head = "".join(
        f"<th scope=col class=rk-axis>{_LIKELIHOOD_LABELS[lr]}<span class=muted> ({lr})</span></th>"
        for lr in range(1, 6)
    )
    body_rows = []
    for ir in range(5, 0, -1):
        cells = []
        for lr in range(1, 6):
            score = ir * lr
            band, _lab = _risk_band(score)
            n = counts.get((ir, lr), 0)
            n_html = f"<span class=rk-cell-n>{n}</span>" if n else ""
            tip = f"Impact {ir} x Likelihood {lr} = {score}" + (f" — {n} item(s)" if n else "")
            cells.append(
                f'<td class="rk-cell {band}{" rk-hit" if n else ""}" title="{tip}">'
                f"{n_html}<span class=rk-cell-s>{score}</span></td>"
            )
        body_rows.append(
            f"<tr><th scope=row class=rk-axis>{_IMPACT_LABELS[ir]}"
            f"<span class=muted> ({ir})</span></th>{''.join(cells)}</tr>"
        )
    legend = " ".join(
        f'<span class="rk-key {b}">{lab}</span>'
        for b, lab in (
            ("rk-min", "Minimal"),
            ("rk-low", "Low"),
            ("rk-mod", "Moderate"),
            ("rk-high", "High"),
            ("rk-extreme", "Extreme"),
        )
    )
    hot = sum(1 for f in items if f.risk_score >= 12)  # the High + Extreme bands (_risk_band)
    return (
        f"<div class=panel{_RISKS_EXPORT}>"
        + _panel_head("Risk matrix &mdash; likelihood &times; impact", tools=tools, prov=prov)
        + f"<p class=sf-take data-no-i18n>{hot} of {len(items)} risks and issues land in the "
        "High or Extreme bands.</p>"
        "<p class=muted>Each risk and issue placed by its quantified likelihood of occurrence and "
        "severity of schedule impact; cell colour is the conventional 5&times;5 risk heat "
        "(score = likelihood &times; impact, 1&ndash;25). The number in a cell is how many items "
        "fall there.</p>"
        '<table class="risk-matrix"><caption class=sr-only>Risk matrix: impact in rows (5 severe '
        "to 1 negligible) by likelihood in columns (1 rare to 5 certain); each cell shows its score "
        "and the count of items.</caption>"
        "<tr><th scope=col class=rk-corner>Impact &darr; / Likelihood &rarr;</th>"
        f"{head}</tr>{''.join(body_rows)}</table>"
        f"<p class=rk-legend>{legend}</p></div>"
    )


def _risk_ranking(items: list[Finding], *, prov: str = "", tools: str = "") -> str:
    """The risks + issues ranked by score (highest first) as labelled bars, each annotated with the
    quantified float, driving float to the target, and working-day exposure.

    Panel contract (ADR-0338). Empty return unchanged — ``test_risks`` pins
    ``_risk_ranking([]) == ""``.
    """
    if not items:
        return ""
    ranked = sorted(items, key=lambda f: (-f.risk_score, SEVERITY_ORDER[f.severity], f.metric_id))
    rows = []
    for f in ranked:
        band, band_label = _risk_band(f.risk_score)
        width = max(4, round(f.risk_score / 25 * 100))
        quant = []
        if f.float_days is not None:
            quant.append(f"float {_wd(f.float_days)}")
        if f.driving_float_days is not None:
            quant.append(f"driving float {_wd(f.driving_float_days)}")
        if f.impact_days is not None and f.impact_days > 0:
            quant.append(f"exposure {_wd(f.impact_days)}")
        quant_txt = (" &middot; " + " &middot; ".join(_e(q) for q in quant)) if quant else ""
        rows.append(
            f"<li class=rk-row><div class=rk-bar-track>"
            f'<div class="rk-bar {band}" style="width:{width}%"></div></div>'
            f'<div class=rk-row-meta><span class="rk-score {band}">{f.risk_score}</span> '
            f"<b>{_e(f.title)}</b> <span class=muted>[{_e(f.metric_id)}]</span>"
            f"<div class=rk-row-sub>{_LIKELIHOOD_LABELS[f.likelihood_score]} likelihood &middot; "
            f"{_IMPACT_LABELS[f.impact_score]} impact ({_e(band_label)}){quant_txt}</div>"
            f"</div></li>"
        )
    top = ranked[0]
    return (
        f"<div class=panel{_RISKS_EXPORT}>"
        + _panel_head("Risk ranking &mdash; highest score first", tools=tools, prov=prov)
        + f"<p class=sf-take data-no-i18n>Highest risk score: {top.risk_score}/25 &mdash; "
        f"{_e(top.title)}.</p>"
        "<p class=muted>Risks and issues ordered by score, with the quantified slack (total float, "
        "and driving float to the target when one is set) and the working-day schedule exposure if "
        "the item is realised.</p>"
        f"<ol class=rk-ranking>{''.join(rows)}</ol></div>"
    )


def _risks_section(
    title: str, lead: str, items: list[Finding], empty: str, *, prov: str = "", tools: str = ""
) -> str:
    """One findings section (Risks / Issues / Opportunities) as a contract panel (ADR-0338).

    The take is worded to hold when the section is EMPTY as well as populated — these three panels
    always render, so a take that only made sense with items would leave a panel wearing a headline
    that reads as a defect on a clean schedule.
    """
    body = "".join(_finding_card(f) for f in items) if items else f"<p class=muted>{empty}</p>"
    high = sum(1 for f in items if f.severity == Severity.HIGH)
    return (
        f"<div class=panel{_RISKS_EXPORT}>"
        + _panel_head(f"{title} <span class=muted>({len(items)})</span>", tools=tools, prov=prov)
        + f"<p class=sf-take data-no-i18n>{len(items)} identified &mdash; {high} at HIGH "
        "severity.</p>"
        f"<p class=muted>{lead}</p>{body}</div>"
    )


#: The panel-level export every /risks panel follows — the EXISTING risks workbook endpoint
#: (`@app.get("/export/{fmt}/risks")`), the same one the page's export bar already offers, so
#: ⤓ EXCEL is never a dead link (rank-3 law, ADR-0338).
_RISKS_EXPORT = ' data-export="/export/xlsx/risks"'
_RISKS_XLSX_TITLE = (
    "Export the risks workbook (this panel's findings are one of its sheets) — opens in Excel"
)


def _risks_body(
    sch: Schedule,
    findings: tuple[Finding, ...],
    narrative: Narrative,
    ai_key: str = "",
    *,
    prov: str = "",
) -> str:
    """The Risks, Issues & Opportunities page: a high-level read first, then the cited detail.

    Grounded entirely in the engine's :func:`recommend` findings (RISK / CONCERN / OPPORTUNITY,
    each with a course of action and citations) plus the local-AI-polished narrative — high level
    first (executive read + a prioritized recovery plan), supporting detail beneath."""
    risks = [f for f in findings if f.category == Category.RISK]
    issues = [f for f in findings if f.category == Category.CONCERN]
    opps = [f for f in findings if f.category == Category.OPPORTUNITY]
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in narrative.statements)

    def _by_score(items: list[Finding]) -> list[Finding]:
        return sorted(items, key=lambda f: (-f.risk_score, SEVERITY_ORDER[f.severity], f.metric_id))

    tools = _shell_tools(export_title=_RISKS_XLSX_TITLE)
    threats = risks + issues
    matrix = _risk_matrix(threats, prov=prov, tools=tools)
    ranking = _risk_ranking(threats, prov=prov, tools=tools)

    # prioritized, de-duplicated recovery actions across risks + issues (most severe first)
    seen: set[str] = set()
    actions: list[Finding] = []
    for f in sorted(risks + issues, key=lambda x: (SEVERITY_ORDER[x.severity], x.metric_id)):
        if f.course_of_action and f.course_of_action not in seen:
            seen.add(f.course_of_action)
            actions.append(f)
    recovery = ""
    if actions:
        action_items = "".join(
            f"<li><b>{_e(a.course_of_action)}</b> "
            f"<span class=muted>&mdash; {_e(a.title)} ({_e(a.severity)})</span></li>"
            for a in actions
        )
        recovery = (
            f"<div class=panel{_RISKS_EXPORT}>"
            + _panel_head("Recovery plan &mdash; prioritized actions", tools=tools, prov=prov)
            + f"<p class=sf-take data-no-i18n>{len(actions)} prioritized action"
            f"{'s' if len(actions) != 1 else ''}, most severe first.</p>"
            "<p class=muted>The highest-leverage actions to recover the plan, most severe first, "
            "each tied to the finding that motivates it.</p>"
            f"<ol class=recovery-list>{action_items}</ol></div>"
        )

    high_note = f" &mdash; {high} flagged HIGH severity" if high else ""
    summary_head = _panel_head(
        f"Risks, Issues &amp; Opportunities &mdash; {_e(sch.name)}", tools=tools, prov=prov
    )
    summary = f"""
<div class=panel{_RISKS_EXPORT}>{summary_head}
<p class=sf-take data-no-i18n>{len(findings)} finding{"s" if len(findings) != 1 else ""}:
{len(risks)} risk{"s" if len(risks) != 1 else ""}, {len(issues)}
issue{"s" if len(issues) != 1 else ""} and {len(opps)} opportunit{"ies" if len(opps) != 1 else "y"}
&mdash; {high} at HIGH severity.</p>
<p>At a glance: <b class=fail>{len(risks)} risk(s)</b>,
<b class=sev-MEDIUM>{len(issues)} issue(s)</b>, and
<b class=pass>{len(opps)} opportunity(ies)</b>{high_note}. The plain-English read is below; the
supporting detail for every item &mdash; with its citation and a recommended action &mdash;
follows in the sections beneath.</p>
<h3>AI read</h3>
<ul class=story id=riskStory data-ai-endpoint="/api/ai/narrative?key={_e(quote(ai_key))}">{story}</ul>
<p class=muted><b>AI can err &mdash; verify against the citations on each finding.</b> Enable a
local model in <a href="/settings">AI Settings</a> for a richer interpretation; the findings
themselves are engine-computed and cited.</p></div>
<script src="/static/ai_polish.js"></script>"""

    return (
        summary
        + matrix
        + ranking
        + recovery
        + _risks_section(
            "Risks",
            "Future-facing threats to the plan, highest risk score first.",
            _by_score(risks),
            "No forward-looking risks identified in this version.",
            prov=prov,
            tools=tools,
        )
        + _risks_section(
            "Issues (current concerns)",
            "Quality / integrity problems present right now, including manipulation signals.",
            _by_score(issues),
            "No current concerns identified in this version.",
            prov=prov,
            tools=tools,
        )
        + _risks_section(
            "Opportunities",
            "Levers to recover or improve the schedule.",
            _by_score(opps),
            "No specific opportunities surfaced from the current signals.",
            prov=prov,
            tools=tools,
        )
    )
