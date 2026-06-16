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
_PBIX = (
    "Reference Power BI deck measure, reconstructed — the deck's DataModel DAX is "
    "XPress9-compressed and unreadable (M15, ADR-0030)."
)


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
    "logic_unsupported_dates": _doc(
        "logic_unsupported_dates",
        "Dates Not Supported by Logic",
        "Unstarted activities whose stored dates network logic does not produce: "
        "manually-scheduled tasks pinned where MS Project stored them, and unlinked "
        "auto tasks floored at their stored start (a pure CPM would pack them at the "
        "project start). The tool honors the file's dates and cites each divergence.",
        "count(unstarted tasks where honored stored start != pure logic early start)",
        "Stored-date CPM mandate (ADR-0034); MS Project manual-task semantics.",
    ),
    "logic_on_summary_tasks": _doc(
        "logic_on_summary_tasks",
        "Logic on Summary Tasks",
        "Summary (roll-up) tasks carrying predecessor or successor relationships. MS "
        "Project applies that logic to the summary's children, so the tool lowers it onto "
        "the leaf descendants and schedules the children to match the file — but logic on "
        "a summary is a DCMA/PMI anti-pattern that hides the true driver and breaks when "
        "the summary's contents change. Each offending summary is cited.",
        "count(summary tasks that are a predecessor or successor in any relationship)",
        "Summary-logic handling (ADR-0043); MS Project summary-scheduling semantics.",
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
        "Current Execution Index, finish side — single-schedule, baseline-anchored (= BFC).",
        "completed_on_time / forecast_to_be_finished",
        "EVM performance indices (METRICS-CATALOG §3, ADR-0013; re-verified ADR-0052).",
    ),
    "cei_start": _doc(
        "cei_start",
        "CEI (Start)",
        "Current Execution Index, start side — single-schedule, baseline-anchored (= BSC).",
        "started_on_time / forecast_to_be_started",
        "EVM performance indices (METRICS-CATALOG §3, ADR-0013; re-verified ADR-0052).",
    ),
    "cei_bow_wave": _doc(
        "cei_bow_wave",
        "CEI (Bow Wave)",
        "Current Execution Index of the /cei view — pairwise and forecast-anchored. Of the "
        "activities the prior snapshot's current schedule forecast to finish in the month "
        "after its data date, the share that actually finished by the end of that month. A "
        "distinct metric from the baseline-anchored CEI (Finish) above — they answer "
        "different questions and must not be conflated.",
        "finished_by_end_of_P / prior_forecast_for_P  (P = month after prior data date)",
        "Bow-wave / Current Execution Index (engine/bow_wave.py, §6.D; re-verified ADR-0052).",
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
    # --- M15: reference-deck measure families (ADR-0030) ---
    "float_total_0": _doc(
        "float_total_0",
        "Total Float 0 Days",
        "Incomplete activities with no total float left (critical or negative).",
        "count(incomplete, total_float <= 0) / incomplete",
        _PBIX,
    ),
    "float_total_lt5": _doc(
        "float_total_lt5",
        "Total Float < 5 Days",
        "Incomplete activities with under 5 working days of total float (cumulative band).",
        "count(incomplete, total_float < 5d) / incomplete",
        _PBIX,
    ),
    "float_total_lt10": _doc(
        "float_total_lt10",
        "Total Float < 10 Days",
        "Incomplete activities with under 10 working days of total float (cumulative band).",
        "count(incomplete, total_float < 10d) / incomplete",
        _PBIX,
    ),
    "float_free_0": _doc(
        "float_free_0",
        "Free Float 0 Days",
        "Incomplete activities with no free float left.",
        "count(incomplete, free_float <= 0) / incomplete",
        _PBIX,
    ),
    "float_free_lt5": _doc(
        "float_free_lt5",
        "Free Float < 5 Days",
        "Incomplete activities with under 5 working days of free float (cumulative band).",
        "count(incomplete, free_float < 5d) / incomplete",
        _PBIX,
    ),
    "float_free_lt10": _doc(
        "float_free_lt10",
        "Free Float < 10 Days",
        "Incomplete activities with under 10 working days of free float (cumulative band).",
        "count(incomplete, free_float < 10d) / incomplete",
        _PBIX,
    ),
    "completed_ahead": _doc(
        "completed_ahead",
        "Completed Ahead",
        "Completed activities that finished before their baseline finish.",
        "count(actual_finish < baseline_finish) / completed-with-both-dates",
        _PBIX,
    ),
    "completed_on_schedule": _doc(
        "completed_on_schedule",
        "Completed On Schedule",
        "Completed activities that finished exactly on their baseline finish date.",
        "count(actual_finish == baseline_finish) / completed-with-both-dates",
        _PBIX,
    ),
    "completed_behind": _doc(
        "completed_behind",
        "Completed Behind Baseline",
        "Completed activities that finished after their baseline finish.",
        "count(actual_finish > baseline_finish) / completed-with-both-dates",
        _PBIX,
    ),
    "avg_days_ahead": _doc(
        "avg_days_ahead",
        "Average Days Ahead",
        "Average calendar days gained, among the early finishers.",
        "mean(baseline_finish - actual_finish) over completed-ahead",
        _PBIX,
    ),
    "avg_days_late": _doc(
        "avg_days_late",
        "Average Days Late",
        "Average calendar days lost, among the late finishers.",
        "mean(actual_finish - baseline_finish) over completed-behind",
        _PBIX,
    ),
    "avg_completion_variance": _doc(
        "avg_completion_variance",
        "Average Completion Variance",
        "Signed average finish variance across all completed activities (+ = late).",
        "mean(actual_finish - baseline_finish) over completed",
        _PBIX,
    ),
    "longer_than_planned": _doc(
        "longer_than_planned",
        "Activities Longer Than Planned",
        "Completed activities whose duration exceeded their baseline duration.",
        "count(duration > baseline_duration) / completed-with-baseline-duration",
        _PBIX,
    ),
    "shorter_than_planned": _doc(
        "shorter_than_planned",
        "Activities Shorter Than Baseline",
        "Completed activities that took less than their baseline duration.",
        "count(duration < baseline_duration) / completed-with-baseline-duration",
        _PBIX,
    ),
    "duration_ratio_min": _doc(
        "duration_ratio_min",
        "Duration Ratio Min",
        "Smallest actual-to-baseline duration ratio among completed activities.",
        "min(duration / baseline_duration)",
        _PBIX,
    ),
    "duration_ratio_avg": _doc(
        "duration_ratio_avg",
        "Duration Ratio Average",
        "Average actual-to-baseline duration ratio among completed activities.",
        "mean(duration / baseline_duration)",
        _PBIX,
    ),
    "duration_ratio_max": _doc(
        "duration_ratio_max",
        "Duration Ratio Max",
        "Largest actual-to-baseline duration ratio among completed activities.",
        "max(duration / baseline_duration)",
        _PBIX,
    ),
    "mei": _doc(
        "mei",
        "MEI",
        "Milestone Execution Index — BEI restricted to milestones.",
        "milestones finished by status / milestones baselined-to-finish by status",
        _PBIX,
    ),
    "epi": _doc(
        "epi",
        "EPI",
        "Execution Progress Index — the deck's DAX adopted verbatim (ADR-0033): the "
        "recorded execution events over the events the plan expected once started.",
        "(n actual starts + n actual finishes) / (n actual starts + n baseline finishes)",
        _PBIX,
    ),
    "start_finish_ratio": _doc(
        "start_finish_ratio",
        "Start-to-Finish Ratio",
        "The deck's DAX adopted verbatim (ADR-0033): scheduled start/finish pairs per "
        "actually-completed pair; falls toward 1.0 as the schedule finishes things.",
        "n(start & finish present) / n(actual start & actual finish present)",
        _PBIX,
    ),
    "elapsed_since_last_finish": _doc(
        "elapsed_since_last_finish",
        "% Schedule Elapsed Since Latest Actual Finish",
        "Share of the elapsed schedule that has passed since anything actually finished.",
        "(status - max(actual_finish)) / (status - project_start)",
        _PBIX,
    ),
    "forecast_cpm": _doc(
        "forecast_cpm",
        "Finish Forecast — Schedule Logic (CPM)",
        "The network's own computed finish, given its logic, durations, and calendar.",
        "CPM forward-pass project finish",
        _PBIX,
    ),
    "forecast_rate": _doc(
        "forecast_rate",
        "Finish Forecast — Completion Rate",
        "Throughput extrapolation: to-go activities at the historical completions-per-month pace.",
        "status + (remaining / (completed / elapsed_months)) months",
        _PBIX,
    ),
    "forecast_earned_schedule": _doc(
        "forecast_earned_schedule",
        "Finish Forecast — Earned Schedule",
        "The standard Earned-Schedule estimate-at-completion on the working-time axis.",
        "IEAC(t) = AT + (PD - ES) / SPI(t)",
        _PBIX,
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
