"""The /cei page family: the Bow Wave / CEI page, its chapter header and its chart payload.

Monolith split, phase 4 slice 23 (ADR-0388), extracted VERBATIM from ``web/app.py``: every
function moves byte-for-byte -- docstrings, comments and HTML f-strings unchanged -- and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/cei`` + ``/api/cei`` + ``/export/{fmt}/cei``. Four names, ZERO descents.

**One member was oracle-dark, and the oracle was extended rather than the claim weakened.**
``_stack_not_measured`` renders only when ``/cei``'s latest snapshot has no scored CEI month --
the Law-2 panel that states an absence instead of drawing a bar of zeroes. Every pool the
corpus loaded carried a scored month, so the member moved zero labels and its byte-identity
claim would have rested on nothing. The corpus gained a ``[ceidark]`` stage whose two snapshots
produce ``cei_period=None`` (ADR-0374's rule, ADR-0379's precedent); the member then moves
exactly the two ``[ceidark] /cei`` labels and nothing else, which is what makes the new stage
provably load-bearing rather than decoration.

Layering: ``app`` -> ``cei`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from urllib.parse import quote

from schedule_forensics.engine.bow_wave import BowWave
from schedule_forensics.web.chrome import _EXPLAINERS, _e
from schedule_forensics.web.components import (
    _panel_head,
    _shell_tools,
    _stat_cards,
    _status_stack,
)


def _stack_not_measured(title: str, desc: str, note: str) -> str:
    """The :func:`_status_stack` shell with the bar replaced by a stated absence (ADR-0343).

    A stacked bar built from figures the source never provided renders every segment at 0 and a
    "0 of 0" foot — which reads as a *measurement of zero*, not as "not measured". Law 2 forbids
    that: an absent figure is an em dash, never a zero. The panel keeps its place in the two-up
    grid (so the layout does not reflow around a missing sibling) and says what is absent, exactly
    as the KPI cards beside it already render "—" for the same fields. Same shell as
    :func:`_status_stack` deliberately — one panel chrome, not two."""
    return (
        f'<div class="panel status-stack"><h2>{_e(title)}</h2>'
        f'<p class="muted">{_e(desc)}</p>'
        f'<p class="muted">{_e(note)}</p></div>'
    )


def _work_piling_header(wave: BowWave) -> str:
    """Chapter 06 "Work piling up" (ADR-0203): the data-driven takeaway + a CEI KPI strip +
    the latest-month plan-vs-done and finish-placement bars, from the bow-wave dataset the
    page already computes (monthly profiles + CEI per snapshot — no new math, only sums)."""
    snaps = wave.snapshots
    n_ver = len(snaps)
    latest = snaps[-1]
    scored = [s.cei for s in snaps if s.cei is not None]
    under = sum(1 for c in scored if c < 1.0)
    cei = latest.cei
    # ADR-0343 / Law 2 (ADR-0306 sweep row 1-2, settled by rendering the page). ``cei_planned``
    # and ``cei_finished`` are ``None`` when the snapshot has no comparable prior month — the
    # preceding version carries no data date, or the month following it falls outside the profiled
    # window (``bow_wave.py``: both are set only inside the ``lo <= period <= hi`` block). The old
    # ``or 0`` turned that absence into a measured zero and fed it to the month bar below, which
    # then drew "Finished 0 / Short of plan 0 / 0 planned in the month" under the heading "Latest
    # scored month" — on a page whose own takeaway said "No month could be CEI-scored" and whose
    # KPI cards rendered "—" for these very two fields. One panel contradicted the strip above it.
    planned = latest.cei_planned
    finished = latest.cei_finished

    # the latest version's finish placement on the shared month axis, split at the data date
    si = latest.status_index
    if si is not None:
        landed = sum(latest.scheduled[: si + 1])
        ahead = sum(latest.scheduled[si + 1 :])
    else:
        landed, ahead = sum(latest.scheduled), 0

    def _fin(x: int) -> str:
        return f"{x} finish" if x == 1 else f"{x} finishes"

    # ``cei`` is ``round(done / planned)`` and is ``None`` whenever ``planned`` is absent OR zero,
    # so the two extra conjuncts cannot change which branch a schedule takes — they state the
    # precondition the f-string already relied on, and let the checker see it.
    if cei is not None and latest.cei_period and planned is not None and finished is not None:
        takeaway = (
            f"In {latest.cei_period} the project completed {finished} of the {planned} "
            f"finishes it had planned (CEI {cei:.2f}) — execution ran under plan in "
            f"{under} of {len(scored)} scored month{'s' if len(scored) != 1 else ''}, "
            f"and {_fin(ahead)} now sit ahead of the data date."
        )
    elif scored:
        takeaway = (
            f"Across {n_ver} versions execution ran under plan in {under} of {len(scored)} "
            f"scored month{'s' if len(scored) != 1 else ''}, and {_fin(ahead)} now sit "
            "ahead of the data date."
        )
    else:
        takeaway = (
            f"No month could be CEI-scored across the {n_ver} loaded versions — the files "
            "carry no comparable month-over-month plan to measure execution against."
        )

    kpi = _stat_cards(
        [
            ("Versions compared", str(n_ver)),
            ("Latest CEI", f"{cei:.2f}" if cei is not None else "—"),
            ("CEI month", latest.cei_period or "—"),
            ("Planned that month", str(planned) if planned is not None else "—"),
            ("Finished that month", str(finished) if finished is not None else "—"),
            ("Months under plan", f"{under} / {len(scored)}" if scored else "—"),
        ]
    )
    if planned is not None and finished is not None:
        month_bar = _status_stack(
            "Latest scored month",
            f"Plan vs done in {latest.cei_period or 'the latest period'} — the CEI numerator and denominator.",
            [
                ("Finished", finished, "--ok"),
                ("Short of plan", max(planned - finished, 0), "--bad"),
            ],
            f"{planned} planned in the month",
        )
    else:
        month_bar = _stack_not_measured(
            "Monthly plan vs done",
            "Plan vs done in the latest CEI-scored month — the CEI numerator and denominator.",
            "No month is scored: no version carries a comparable prior month-over-month plan to "
            "measure execution against, so the numerator and denominator are absent — not zero.",
        )
    pile_bar = _status_stack(
        "Where the finishes sit",
        f"The newest version's finish months, split at the data date — {latest.label}.",
        [("Landed by the data date", landed, "--ok"), ("Piled ahead of it", ahead, "--warn")],
        f"{landed + ahead} finishes across {len(wave.month_labels)} months",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">Where unfinished work sits against each snapshot\'s data date, '
        "and how much of each period's plan was actually executed. Step or play through the "
        "snapshots to watch the wave move.</p>"
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{month_bar}{pile_bar}</div>'
    )


def _cei_body(
    wave: BowWave,
    target_uid: int | None = None,
    track_uids: list[int] | None = None,
    *,
    prov: str = "",
) -> str:
    """The Bow Wave / CEI view: per-snapshot animated chart + the CEI summary table.

    Panel contract (Mission Ops rank 10): a headline strip + ⤓ EXCEL (the EXISTING
    ``/export/xlsx/cei`` endpoint, whose workbook is exactly these two visuals — the CEI
    table and one monthly-finish profile per snapshot) + ⛶ ENLARGE + the series provenance
    chip + one ``.sf-take`` per panel. No ▦ DATA on either: the chart ships no drawer table
    (its ``.sr-only`` a11y fallback is injected by cei.js and is NOT an ``.sf-drawer``), and
    the CEI panel's own table IS the data (the home-shell precedent in :func:`_shell_tools`).
    Every figure a take quotes is already rendered verbatim elsewhere on this page — the
    snapshot count as the "Versions compared" KPI, the month count in the finish-placement
    bar's foot, and the label / period / planned / finished / CEI cells in the table below.
    ``prov`` is keyword-with-default so the existing direct ``_cei_body(wave)`` unit call
    keeps working."""
    latest = wave.snapshots[-1] if wave.snapshots else None
    if latest is None:
        take_chart = "No snapshot could be profiled from the loaded versions."
        take_table = take_chart
    else:
        take_chart = (
            f"{len(wave.snapshots)} snapshots on one shared "
            f"{len(wave.month_labels)}-month axis; the newest is {latest.label}."
        )
        if (
            latest.cei is not None
            and latest.cei_period
            and latest.cei_planned is not None
            and latest.cei_finished is not None
        ):
            take_table = (
                f"{latest.label}: CEI {latest.cei:.2f} in {latest.cei_period} — "
                f"{latest.cei_finished} of {latest.cei_planned} previously planned "
                "finishes actually landed."
            )
        else:
            take_table = (
                f"{latest.label} carries no comparable prior month, so no CEI is scored for it."
            )
    head_chart = _panel_head(
        "Bow Wave &mdash; Activity Finishes by month",
        tools=_shell_tools(
            export_title=(
                "Export the bow-wave monthly finish profiles and the CEI table — opens in Excel"
            )
        ),
        prov=prov,
    )
    head_table = _panel_head(
        "CEI &mdash; Current Execution Index",
        tools=_shell_tools(
            export_title=(
                "Export the CEI table and the bow-wave monthly finish profiles — opens in Excel"
            )
        ),
        prov=prov,
    )
    rows = "".join(
        f"<tr><td>{_e(s.label)}</td><td>{_e(s.cei_period or '—')}</td>"
        f"<td>{s.cei_planned if s.cei_planned is not None else '—'}</td>"
        f"<td>{s.cei_scheduled if s.cei_scheduled is not None else '—'}</td>"
        f"<td>{s.cei_finished if s.cei_finished is not None else '—'}</td>"
        f"<td><b class={'fail' if s.cei is not None and s.cei < 0.8 else 'pass'}>"
        f"{f'{s.cei:.2f}' if s.cei is not None else '—'}</b></td></tr>"
        for s in wave.snapshots
    )
    track_txt = ", ".join(str(u) for u in (track_uids or []))
    # ── Claude Design layout (ADR-0456, "06 Work piling up"; ADR-0451's method, functionality
    # unchanged): the chart panel wears the prototype's cursor strip — Auto-play as the primary
    # button, Prev / Next, ONE chip per snapshot, the frame pill — then the options row (the two
    # ADR-0268 forms, byte-for-byte), then the chart; below it the prototype's 1.1fr / .9fr row:
    # the CEI panel (verbatim) beside a "How to read this" block whose three beats are this
    # page's own explainer (chrome._EXPLAINERS — the collapsed "What am I looking at?" text, so no
    # new prose enters the loaded-terms audit surface). The chips are served here (cei.js also
    # runs the /mission wall, which serves none) and drive the SAME render() the stepper drives;
    # the chart opens on the first snapshot exactly as before, so the first chip opens `on`. Not
    # ported from the mock, on purpose: the WK/QTR/YR grain chips (the engine profiles months —
    # regrouping is a new visual, a week split would be a fabricated one), the CEI line chart (the
    # table IS the panel's data; a new visual needs its own ledger rows) and ▦ DATA (this page's
    # contract says neither panel ships a drawer). The `.cd-*` classes are the page-neutral
    # family for this layout (`docs/DESIGN-SYSTEM.md` §9); `vol-*` on /volatility predates it.
    explain = _EXPLAINERS.get("Bow Wave / CEI", ("", "", ""))
    beats = "".join(
        f'<div class="cd-beat {cls}"><b>{lead}</b> {_e(text)}</div>'
        for cls, lead, text in (
            ("cd-beat-accent", "The wave.", explain[0]),
            ("cd-beat-warn", "The index.", explain[1]),
            ("cd-beat-bad", "Why it matters.", explain[2]),
        )
    )
    chips = "".join(
        f'<button type=button class="cd-chip{" on" if i == 0 else ""}" data-idx="{i}" '
        f"aria-pressed={'true' if i == 0 else 'false'} data-no-i18n "
        f'title="{_e(s.label)}">v{i + 1}</button>'
        for i, s in enumerate(wave.snapshots)
    )
    return f"""
<div class=panel data-export="/export/xlsx/cei">{head_chart}
<p class=sf-take data-no-i18n>{_e(take_chart)}</p>
<div class="viz-controls cd-cursor">
<button id=autoPlay type=button class=cd-play>&#9654; Auto-play</button>
<button id=prevSnap type=button>&#9664; Prev</button>
<button id=nextSnap type=button>Next &#9654;</button>
<span class=cd-chips>{chips}</span>
<span id=snapLabel class="muted cd-pill" data-no-i18n></span>
<label><input id=ceiTotals type=checkbox> Running totals (cumulative)</label>
</div>
<div class=cd-options>
<form method=post action=/target class=viz-controls>
<input type=hidden name=next_url value="/cei{("?uids=" + quote(track_txt)) if track_txt else ""}">
<label>Target UID <input name=uid type=number min=1 value="{target_uid if target_uid is not None else ""}"
placeholder="UID"></label>
<button type=submit>Focus</button>
{'<button class=linkbtn type=submit name=uid value="">clear focus</button>' if target_uid is not None else ""}</form>
<form method=get action=/cei class=viz-controls>
<label>Track UIDs <input id=ceiTrack name=uids data-no-i18n value="{_e(track_txt)}"
placeholder="e.g. 155, 187, 411" size=28
title="Up to 20 UniqueIDs (comma/space separated) marked on every snapshot of the animation — independent of the primary target"></label>
<button type=submit>Track</button></form>
</div>
<div id=ceiChart class=chart-host></div>
<p class=muted>Gold = baselined to finish, blue = scheduled to finish, green = actually
finished; the dashed line is the snapshot's data date. Work that keeps sliding right shows
as a swelling wave of blue just past each data date. Step through the snapshots or press
Auto-play to watch the wave move. Tick <b>Running totals</b> for the cumulative finish curves,
focus a <b>Target UID</b> to mark where that activity lands (and slides) in each snapshot, and
<b>Track UIDs</b> (up to 20, comma-separated) to watch specific activities ride the wave.</p>
</div>
<div class="cd-grid cd-grid-2">
<div class=panel data-export="/export/xlsx/cei">{head_table}
<p class=sf-take data-no-i18n>{_e(take_table)}</p>
<p class=muted>For each snapshot: of the activities the <i>previous</i> snapshot planned to
finish in the following month, how many this snapshot re-scheduled for that month and how
how many of those planned activities actually finished by the end of it. CEI = completed-on-time &divide; previously planned (1.00 = executed to plan; an unplanned finish in the month earns no credit).</p>
<table><tr><th scope=col>Snapshot</th><th scope=col>Period</th><th scope=col>Previously planned</th><th scope=col>Re-scheduled</th>
<th scope=col>Actually finished</th><th scope=col>CEI</th></tr>{rows}</table></div>
<section class="cd-block cd-read"><h2>How to read this</h2>{beats}</section>
</div>
<script src="/static/cei.js"></script>
<script src="/static/panelkit.js"></script>"""


def _cei_data(wave: BowWave, target_uid: int | None = None) -> dict[str, object]:
    # locked Y-axis (item 5): the chart's count scale is the max bar across EVERY snapshot,
    # held through the animation so the bars stay comparable frame-to-frame (a per-snapshot
    # max made each frame rescale, hiding the bow wave's growth).
    max_count = max(
        (max([0, *s.baselined, *s.scheduled, *s.finished]) for s in wave.snapshots),
        default=0,
    )
    return {
        "months": list(wave.month_labels),
        "max_count": max_count,
        "target_uid": target_uid,
        "snapshots": [
            {
                "label": s.label,
                "status_index": s.status_index,
                "baselined": list(s.baselined),
                "scheduled": list(s.scheduled),
                "finished": list(s.finished),
                # per-month UID lists behind each monthly bar (drill; matches the counts above)
                "baselined_uids": [list(u) for u in s.baselined_uids],
                "scheduled_uids": [list(u) for u in s.scheduled_uids],
                "finished_uids": [list(u) for u in s.finished_uids],
                "cei": s.cei,
                "cei_period": s.cei_period,
                "cei_planned": s.cei_planned,
                "cei_scheduled": s.cei_scheduled,
                "cei_finished": s.cei_finished,
                "target_scheduled_index": s.target_scheduled_index,
                "target_finished_index": s.target_finished_index,
                "tracked": [
                    {
                        "uid": t.uid,
                        "name": t.name,
                        "scheduled_index": t.scheduled_index,
                        "finished_index": t.finished_index,
                        "pct": t.percent_complete,
                    }
                    for t in s.tracked
                ],
            }
            for s in wave.snapshots
        ],
    }
