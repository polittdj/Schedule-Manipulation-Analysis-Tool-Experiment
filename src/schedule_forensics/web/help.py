"""In-tool metric dictionary — plain-language definition + formula + citation per metric (§6.A).

Every metric/measure the engine emits has an entry here (id → :class:`MetricDoc`) so the UI
can explain it and the user can fact-check the number against the parent schedule. A test
(`tests/web/test_help.py`) asserts **coverage**: every metric id produced by the engine on
the golden schedules has a dictionary entry — the in-tool help can never show an unexplained
figure. Formulas are stated per the cited sources (`docs/PLAN/METRICS-CATALOG.md`,
`PARITY-TARGETS.md`, ADRs 0010-0017).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDoc:
    """One metric's help entry: what it is, how it's computed, and how to verify it."""

    metric_id: str
    name: str
    definition: str
    formula: str
    source: str  # citing reference / framework
    citation_basis: str = "Every value cites file + UniqueID + task name (§6)."


def _doc(mid: str, name: str, definition: str, formula: str, source: str) -> MetricDoc:
    return MetricDoc(
        metric_id=mid, name=name, definition=definition, formula=formula, source=source
    )


_DCMA = (
    "DCMA 14-Point Assessment / Acumen Fuse 'Fuse Analyst Report' (PARITY-TARGETS §B, ADR-0012)."
)
_SQ = "Acumen Fuse Schedule-Quality summary (PARITY-TARGETS §A, ADR-0012)."
_C = "Acumen Fuse baseline-compliance / Half-Step-Delay (PARITY-TARGETS §C, ADR-0013)."
_EVM = "EVM performance indices (METRICS-CATALOG §3, ADR-0013)."
_E = "Acumen Fuse Schedule-Network / PP & Change (PARITY-TARGETS §E, ADR-0013/0016)."
_SSI = "SSI MS Project add-on driving slack (SSI-DRIVING-SLACK.md, ADR-0011)."


METRIC_DICTIONARY: dict[str, MetricDoc] = {
    # --- DCMA-14 ribbon (DCMA-04 split into FS / SS-FF / SF rows) ---
    "DCMA01": _doc(
        "DCMA01",
        "Logic",
        "Incomplete activities missing a predecessor and/or successor.",
        "count(incomplete without pred or succ) / incomplete <= 5%",
        _DCMA,
    ),
    "DCMA02": _doc(
        "DCMA02",
        "Leads",
        "Relationships with a negative lag (a lead).",
        "count(lag < 0) == 0",
        _DCMA,
    ),
    "DCMA03": _doc(
        "DCMA03",
        "Lags",
        "Relationships with a positive lag into an incomplete successor.",
        "count(lag > 0) / links <= 5%",
        _DCMA,
    ),
    "DCMA04_FS": _doc(
        "DCMA04_FS",
        "FS Relationships",
        "Share of relationships that are Finish-to-Start.",
        "count(FS) / links >= 90%",
        _DCMA,
    ),
    "DCMA04_SSFF": _doc(
        "DCMA04_SSFF",
        "SS/FF Relationships",
        "Start-Start / Finish-Finish links into incomplete work.",
        "count(SS|FF into incomplete)",
        _DCMA,
    ),
    "DCMA04_SF": _doc(
        "DCMA04_SF",
        "SF Relationships",
        "Start-to-Finish relationships (discouraged).",
        "count(SF into incomplete)",
        _DCMA,
    ),
    "DCMA05": _doc(
        "DCMA05",
        "Hard Constraints",
        "Activities with a hard/mandatory constraint (MSO/MFO/SNLT/FNLT).",
        "count(hard constraint) / activities <= 5%",
        _DCMA,
    ),
    "DCMA06": _doc(
        "DCMA06",
        "High Float",
        "Incomplete activities with total float > 44 working days.",
        "count(total_float > 44d) / incomplete <= 5%",
        _DCMA,
    ),
    "DCMA07": _doc(
        "DCMA07",
        "Negative Float",
        "Incomplete activities with total float < 0.",
        "count(total_float < 0) == 0",
        _DCMA,
    ),
    "DCMA08": _doc(
        "DCMA08",
        "High Duration",
        "Incomplete activities with baseline duration > 44 working days.",
        "count(baseline_dur > 44d) / incomplete <= 5%",
        _DCMA,
    ),
    "DCMA09": _doc(
        "DCMA09",
        "Invalid Dates",
        "Actuals after the status date, or an incomplete forecast in the past.",
        "count(invalid actual/forecast vs status) == 0",
        _DCMA,
    ),
    "DCMA10": _doc(
        "DCMA10",
        "Resources",
        "Incomplete, real-duration activities with no resource assigned.",
        "count(no resource) / incomplete-with-duration <= 5%",
        _DCMA,
    ),
    "DCMA11": _doc(
        "DCMA11",
        "Missed Activities",
        "Baselined-due-by-status activities not finished on time.",
        "count(due not finished on time) / due <= 5%",
        _DCMA,
    ),
    "DCMA12": _doc(
        "DCMA12",
        "Critical Path Test",
        "A delay on a critical activity must flow to the project finish.",
        "inject delay on critical task -> finish moves by the delay",
        _DCMA,
    ),
    "DCMA13": _doc(
        "DCMA13",
        "CPLI",
        "Critical Path Length Index.",
        "(crit path length + project total float) / crit path length >= 0.95",
        _DCMA,
    ),
    "DCMA14": _doc(
        "DCMA14",
        "BEI",
        "Baseline Execution Index.",
        "activities completed / activities baselined-to-complete-by-status >= 0.95",
        _DCMA,
    ),
    # --- Acumen Schedule-Quality summary ---
    "missing_logic": _doc(
        "missing_logic",
        "Missing Logic",
        "Activities with an open start or finish (no pred/succ).",
        "count(open-ended) / activities <= 5%",
        _SQ,
    ),
    "logic_density": _doc(
        "logic_density",
        "Logic Density",
        "Average relationships per activity.",
        "2 x links / activities",
        _SQ,
    ),
    "critical": _doc(
        "critical",
        "Critical",
        "Incomplete activities on the critical path.",
        "count(total_float <= 0 and incomplete)",
        _SQ,
    ),
    "hard_constraints": _doc(
        "hard_constraints",
        "Hard Constraints",
        "Activities with a hard/mandatory constraint.",
        "count(hard constraint) / activities",
        _SQ,
    ),
    "negative_float": _doc(
        "negative_float",
        "Negative Float",
        "Incomplete activities with total float < 0.",
        "count(total_float < 0) / incomplete",
        _SQ,
    ),
    "insufficient_detail": _doc(
        "insufficient_detail",
        "Insufficient Detail",
        "Activities with a baseline duration > 44 working days.",
        "count(baseline_dur > 44d) / activities <= 5%",
        _SQ,
    ),
    "number_of_lags": _doc(
        "number_of_lags",
        "Number of Lags",
        "Relationships carrying a positive lag.",
        "count(lag > 0) / activities <= 5%",
        _SQ,
    ),
    "number_of_leads": _doc(
        "number_of_leads",
        "Number of Leads",
        "Relationships carrying a negative lag.",
        "count(lag < 0) / activities",
        _SQ,
    ),
    "merge_hotspot": _doc(
        "merge_hotspot",
        "Merge Hotspot",
        "Activities with 3 or more predecessors (a merge point).",
        "count(predecessors >= 3) / activities",
        _SQ,
    ),
    # --- Baseline compliance / Half-Step-Delay (§C) ---
    "forecast_to_be_finished": _doc(
        "forecast_to_be_finished",
        "Forecast to be Finished",
        "Activities the baseline placed on/before the status date.",
        "count(baseline_finish <= status) / activities",
        _C,
    ),
    "completed_on_time": _doc(
        "completed_on_time",
        "Completed On Time",
        "Due activities completed on/before their baseline finish.",
        "count(complete and actual_finish <= baseline_finish) / due",
        _C,
    ),
    "completed_late": _doc(
        "completed_late",
        "Completed Late",
        "Due activities completed after their baseline finish.",
        "count(complete and actual_finish > baseline_finish) / due",
        _C,
    ),
    "not_completed": _doc(
        "not_completed",
        "Not Completed",
        "Due activities not yet complete.",
        "count(due and incomplete) / due",
        _C,
    ),
    "baseline_finish_compliance": _doc(
        "baseline_finish_compliance",
        "Baseline Finish Compliance",
        "Share of due activities finished on time (BFC).",
        "completed_on_time / forecast_to_be_finished",
        _C,
    ),
    "forecast_to_be_started": _doc(
        "forecast_to_be_started",
        "Forecast to be Started",
        "Activities the baseline placed to start on/before the status date.",
        "count(baseline_start <= status) / activities",
        _C,
    ),
    "started_on_time": _doc(
        "started_on_time",
        "Started On Time",
        "Start-due activities started on/before their baseline start.",
        "count(actual_start <= baseline_start) / start-due",
        _C,
    ),
    "started_late": _doc(
        "started_late",
        "Started Late",
        "Start-due activities started after their baseline start.",
        "count(actual_start > baseline_start) / start-due",
        _C,
    ),
    "not_started": _doc(
        "not_started",
        "Not Started",
        "Start-due activities not yet started.",
        "count(start-due without actual_start) / start-due",
        _C,
    ),
    "baseline_start_compliance": _doc(
        "baseline_start_compliance",
        "Baseline Start Compliance",
        "Share of start-due activities started on time (BSC).",
        "started_on_time / forecast_to_be_started",
        _C,
    ),
    # --- EVM indices ---
    "spi": _doc(
        "spi",
        "SPI",
        "Schedule Performance Index (cost-based; NA without cost).",
        "BCWP / BCWS",
        _EVM,
    ),
    "cpi": _doc("cpi", "CPI", "Cost Performance Index (NA without cost).", "BCWP / ACWP", _EVM),
    "tcpi": _doc(
        "tcpi",
        "TCPI",
        "To-Complete Performance Index (NA without cost).",
        "(BAC - BCWP) / (BAC - ACWP)",
        _EVM,
    ),
    "cei_finish": _doc(
        "cei_finish",
        "CEI (Finish)",
        "Current Execution Index, finish side (= BFC).",
        "completed_on_time / forecast_to_be_finished",
        _EVM,
    ),
    "cei_start": _doc(
        "cei_start",
        "CEI (Start)",
        "Current Execution Index, start side (= BSC).",
        "started_on_time / forecast_to_be_started",
        _EVM,
    ),
    "spi_t": _doc(
        "spi_t",
        "SPI(t)",
        "Time-based Earned-Schedule index (count-based; informational).",
        "Earned Schedule / Actual Time",
        _EVM,
    ),
    # --- Schedule-Network change (§E) + HSD ---
    "SN01": _doc(
        "SN01",
        "Total Activities",
        "Count of schedulable activities in the version.",
        "count(non-summary activities)",
        _E,
    ),
    "SN02": _doc(
        "SN02",
        "Activities Added",
        "Activities present in the current version but not the prior (by UID).",
        "current UIDs - prior UIDs",
        _E,
    ),
    "SN03": _doc(
        "SN03",
        "New Critical",
        "Activities newly on the critical path vs the prior version.",
        "critical-incomplete now and not before (present in both)",
        _E,
    ),
    "SN04": _doc(
        "SN04",
        "No Longer Critical",
        "Activities that left the critical path while still incomplete.",
        "critical-incomplete before, not now, still incomplete",
        _E,
    ),
    "SN05": _doc(
        "SN05",
        "Finish Date Slips",
        "Activities the prior plan placed to finish by now, still incomplete.",
        "prior forecast_finish <= status and incomplete now",
        _E,
    ),
    "SN06": _doc(
        "SN06",
        "Start Date Slips",
        "Activities the prior plan placed to start by now, still not started.",
        "prior forecast_start <= status and not started now",
        _E,
    ),
    "SN07": _doc(
        "SN07",
        "Remaining Duration Increases",
        "Activities whose duration grew vs the prior version.",
        "count(duration_now > duration_prior)",
        _E,
    ),
    "SN09": _doc(
        "SN09",
        "Float Erosion",
        "Incomplete activities whose total float decreased vs the prior version.",
        "count(total_float_now < total_float_prior and incomplete)",
        _E,
    ),
    "SN18": _doc(
        "SN18", "Completed", "Activities at 100% complete.", "count(percent_complete >= 100)", _E
    ),
    "SN19": _doc(
        "SN19",
        "In-Progress",
        "Activities between 0% and 100% complete.",
        "count(0 < percent_complete < 100)",
        _E,
    ),
    "HSD10": _doc(
        "HSD10",
        "Net Finish Impact",
        "Calendar-day move of the project finish vs the prior version.",
        "(prior CPM finish date) - (current CPM finish date), in days",
        _C,
    ),
    # --- SSI driving slack ---
    "driving_slack": _doc(
        "driving_slack",
        "Driving Slack",
        "Days an activity may slip before it delays the focus (target UID).",
        "anchored backward pass to the focus task; days of slack to the focus",
        _SSI,
    ),
}


def metric_doc(metric_id: str) -> MetricDoc | None:
    """The help entry for ``metric_id`` (or ``None`` if undocumented)."""
    return METRIC_DICTIONARY.get(metric_id)


def documented_metric_ids() -> frozenset[str]:
    return frozenset(METRIC_DICTIONARY)


def render_dictionary_markdown() -> str:
    """Render the metric dictionary as a Markdown table — the source of `docs/METRIC-DICTIONARY.md`.

    `docs/METRIC-DICTIONARY.md` is generated from this (a test asserts it stays in sync), so the
    in-tool `/help` page and the committed doc can never drift apart.
    """
    lines = [
        "# Metric dictionary",
        "",
        "> Generated from `schedule_forensics.web.help.METRIC_DICTIONARY`. To regenerate:",
        '> `python -c "from schedule_forensics.web.help import render_dictionary_markdown as r;'
        " open('docs/METRIC-DICTIONARY.md','w').write(r())\"`",
        "",
        "Every metric/measure the tool emits, with its formula and source. Each computed "
        "value also cites **file + UniqueID + task name** so it can be verified in the parent "
        "schedule (§6).",
        "",
        "| Metric | Definition | Formula | Source |",
        "|--------|------------|---------|--------|",
    ]
    for doc in METRIC_DICTIONARY.values():
        lines.append(f"| {doc.name} | {doc.definition} | `{doc.formula}` | {doc.source} |")
    return "\n".join(lines) + "\n"
