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
    importance: str = ""  # why the check matters (tooltip "Why it matters")
    indicates: str = ""  # what a failing value tells the analyst (tooltip "Indicates")
    threshold: str = ""  # plain-language pass/fail threshold (tooltip "Threshold")
    example_ok: str = ""  # a concrete passing example (tooltip "Pass example")
    example_fail: str = ""  # a concrete failing example (tooltip "Fail example")
    citation_basis: str = "Every value cites file + UniqueID + task name (§6)."


def _doc(
    mid: str,
    name: str,
    definition: str,
    formula: str,
    source: str,
    importance: str = "",
    indicates: str = "",
    threshold: str = "",
    example_ok: str = "",
    example_fail: str = "",
) -> MetricDoc:
    return MetricDoc(
        metric_id=mid,
        name=name,
        definition=definition,
        formula=formula,
        source=source,
        importance=importance,
        indicates=indicates,
        threshold=threshold,
        example_ok=example_ok,
        example_fail=example_fail,
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
_HMI = "NASA Acumen metric library ('Bible') — extracted formula, ADR-0087."


METRIC_DICTIONARY: dict[str, MetricDoc] = {
    # --- DCMA-14 ribbon (DCMA-04 split into FS / SS-FF / SF rows) ---
    "DCMA01": _doc(
        "DCMA01",
        "Logic",
        "Incomplete activities missing a predecessor and/or successor.",
        "count(incomplete without pred or succ) / incomplete <= 5%",
        _DCMA,
        importance="Every activity must be tied into the network on both ends so a slip "
        "anywhere flows through to the finish. Dangling tasks break that chain.",
        indicates="Open ends mean the schedule cannot reliably predict the finish date; the "
        "missing links must be added before the critical path can be trusted.",
        threshold="No more than 5% of incomplete activities may be missing a predecessor or a "
        "successor.",
        example_ok="12 open-ended tasks on a 783-activity plan = 1.5% -> PASS (well under 5%).",
        example_fail="180 of 600 incomplete tasks (30%) have no successor -> FAIL; the finish "
        "date cannot be trusted.",
    ),
    "DCMA02": _doc(
        "DCMA02",
        "Leads",
        "Relationships with a negative lag (a lead).",
        "count(lag < 0) == 0",
        _DCMA,
        importance="Leads (negative lag) let a successor start before its predecessor finishes, "
        "compressing the plan in a way that hides true logic and can mask a slip.",
        indicates="Any lead is a red flag: the overlap should be modelled with an explicit "
        "SS/FF relationship and a positive lag so the logic is visible and statusable.",
        threshold="Zero relationships may carry a negative lag (a lead).",
        example_ok="No relationship has a negative lag -> PASS.",
        example_fail="A 'FS -5d' link pulls a successor 5 days early -> FAIL; remodel as an SS "
        "with a positive lag.",
    ),
    "DCMA03": _doc(
        "DCMA03",
        "Lags",
        "Relationships with a positive lag into an incomplete successor.",
        "count(lag > 0) / links <= 5%",
        _DCMA,
        importance="Lags bury real work (cure, delivery, review) inside a relationship where it "
        "cannot be progressed, resourced, or seen — over-use distorts the critical path.",
        indicates="Heavy lag use suggests work modelled as delay instead of activities; replace "
        "each material lag with a real, statusable task.",
        threshold="No more than 5% of relationships may carry a positive lag.",
        example_ok="8 lagged links out of 900 (0.9%) -> PASS.",
        example_fail="140 of 900 links (16%) bury cure/delivery time as lag -> FAIL; model the "
        "wait as a real task.",
    ),
    "DCMA04_FS": _doc(
        "DCMA04_FS",
        "FS Relationships",
        "Share of relationships that are Finish-to-Start.",
        "count(FS) / links >= 90%",
        _DCMA,
        importance="Finish-to-Start is the clearest, most defensible logic. A schedule built "
        "mostly from FS links is easier to analyse and behaves predictably under change.",
        indicates="A low FS share means heavy use of SS/FF/SF, which can overlap work "
        "artificially and obscure the true driving path.",
        threshold="At least 90% of relationships must be Finish-to-Start.",
        example_ok="92% of links are FS -> PASS.",
        example_fail="FS share is 71% (heavy SS/FF use) -> FAIL; the true driving path is "
        "obscured.",
    ),
    "DCMA04_SSFF": _doc(
        "DCMA04_SSFF",
        "SS/FF Relationships",
        "Start-Start / Finish-Finish links into incomplete work.",
        "count(SS|FF into incomplete)",
        _DCMA,
        importance="SS/FF links model genuine overlap, but each one should reflect real "
        "concurrency rather than a workaround for missing detail.",
        indicates="A high count warrants review — some SS/FF links are often standing in for "
        "logic that should be broken into discrete FS-linked activities.",
        threshold="Informational: the count of SS/FF links into incomplete work should reflect "
        "real overlap, not missing detail.",
        example_ok="A handful of SS/FF links, each a genuine concurrency -> acceptable.",
        example_fail="Dozens of SS/FF links standing in for missing detail -> review and break "
        "them into FS-linked tasks.",
    ),
    "DCMA04_SF": _doc(
        "DCMA04_SF",
        "SF Relationships",
        "Start-to-Finish relationships (discouraged).",
        "count(SF into incomplete)",
        _DCMA,
        importance="Start-to-Finish logic is rarely correct and is almost never needed; it "
        "inverts the normal flow of work and confuses analysis.",
        indicates="Any SF relationship should be justified or removed — it usually signals a "
        "modelling error rather than a real dependency.",
        threshold="Zero Start-to-Finish relationships (they are almost never correct).",
        example_ok="No SF links in the network -> PASS.",
        example_fail="Any SF link -> review; it inverts the normal flow of work and usually "
        "signals a modelling error.",
    ),
    "DCMA05": _doc(
        "DCMA05",
        "Hard Constraints",
        "Activities with a hard/mandatory constraint (MSO/MFO/SNLT/FNLT).",
        "count(hard constraint) / activities <= 5%",
        _DCMA,
        importance="Hard constraints override network logic, freezing dates so the schedule no "
        "longer reacts to upstream slips. They mask true float and hide risk.",
        indicates="Excess hard constraints mean the dates are imposed rather than logic-driven; "
        "the plan may look on-track while the underlying network is already late.",
        threshold="No more than 5% of activities may carry a hard constraint (MSO/MFO/SNLT/FNLT).",
        example_ok="10 of 600 activities (1.7%) hard-constrained -> PASS.",
        example_fail="120 of 600 (20%) hard-constrained -> FAIL; dates are imposed, not "
        "logic-driven.",
    ),
    "DCMA06": _doc(
        "DCMA06",
        "High Float",
        "Incomplete activities with total float > 44 working days.",
        "count(total_float > 44d) / incomplete <= 5%",
        _DCMA,
        importance="Very high float usually means an activity is not properly tied to its "
        "successors, so it floats free of the network and understates risk.",
        indicates="A cluster of high-float tasks points to missing successor logic — tie them "
        "back in so their true float (and risk) is revealed.",
        threshold="No more than 5% of incomplete activities may have total float over 44 working "
        "days.",
        example_ok="15 of 600 incomplete tasks (2.5%) above 44 d -> PASS.",
        example_fail="200 of 600 (33%) float free of the network -> FAIL; successor logic is "
        "missing.",
    ),
    "DCMA07": _doc(
        "DCMA07",
        "Negative Float",
        "Incomplete activities with total float < 0.",
        "count(total_float < 0) == 0",
        _DCMA,
        importance="Negative float means the plan is already behind a constraint or deadline — "
        "work must be recovered for the schedule to be achievable.",
        indicates="Any negative float flags a path that cannot meet its imposed finish; the "
        "logic, durations, or the constraint driving it must be addressed.",
        threshold="Zero incomplete activities may have negative total float.",
        example_ok="No task carries negative float -> PASS; the plan is achievable as drawn.",
        example_fail="40 tasks at -12 d total float -> FAIL; a path cannot meet its imposed "
        "finish.",
    ),
    "DCMA08": _doc(
        "DCMA08",
        "High Duration",
        "Incomplete activities with baseline duration > 44 working days.",
        "count(baseline_dur > 44d) / incomplete <= 5%",
        _DCMA,
        importance="Long activities are hard to status accurately and hide progress and risk "
        "inside a single bar; they should be decomposed into measurable detail.",
        indicates="Many long-duration tasks reduce visibility — break them down so progress and "
        "emerging slip can be seen and managed.",
        threshold="No more than 5% of incomplete activities may have a baseline duration over 44 "
        "working days.",
        example_ok="12 of 600 (2%) run longer than 44 d -> PASS.",
        example_fail="150 of 600 (25%) exceed 44 d -> FAIL; decompose them so progress is visible.",
    ),
    "DCMA09": _doc(
        "DCMA09",
        "Invalid Dates",
        "Actuals after the status date, or an incomplete forecast in the past.",
        "count(invalid actual/forecast vs status) == 0",
        _DCMA,
        importance="Actual dates in the future or forecast (incomplete) work in the past are "
        "logically impossible and corrupt every downstream calculation.",
        indicates="Invalid dates mean the schedule was not properly statused against the data "
        "date; they must be corrected before any metric can be trusted.",
        threshold="Zero actuals after the data date and zero incomplete (forecast) work "
        "scheduled in the past.",
        example_ok="Every actual is on or before the data date and every forecast is after it "
        "-> PASS.",
        example_fail="An actual finish dated two weeks after the data date -> FAIL; the schedule "
        "was not statused.",
    ),
    "DCMA10": _doc(
        "DCMA10",
        "Resources",
        "Incomplete, real-duration activities with no resource assigned.",
        "count(no resource) / incomplete-with-duration <= 5%",
        _DCMA,
        importance="A resource-loaded schedule supports cost and earned-value analysis; "
        "unresourced real-duration work cannot be costed or levelled.",
        indicates="Gaps here mean the plan is not fully resource-loaded — confirm each open "
        "activity is either resourced or genuinely level-of-effort.",
        threshold="No more than 5% of incomplete, real-duration activities may have no resource "
        "assigned.",
        example_ok="Every open task is resourced or flagged level-of-effort -> PASS.",
        example_fail="300 of 600 open tasks carry no resource -> FAIL; the plan cannot be costed "
        "or levelled.",
    ),
    "DCMA11": _doc(
        "DCMA11",
        "Missed Activities",
        "Baselined-due-by-status activities not finished on time.",
        "count(due not finished on time) / due <= 5%",
        _DCMA,
        importance="Tasks baselined to finish by now that have not is the most direct measure "
        "of slip against the plan of record.",
        indicates="A high missed-activity rate shows the schedule is falling behind its "
        "baseline; the work needs re-planning or recovery.",
        threshold="No more than 5% of activities baselined to finish by the data date may still "
        "be unfinished.",
        example_ok="5 of 200 due tasks slipped (2.5%) -> PASS.",
        example_fail="60 of 200 due tasks (30%) not finished -> FAIL; the schedule is behind its "
        "baseline.",
    ),
    "DCMA12": _doc(
        "DCMA12",
        "Critical Path Test",
        "A delay on a critical activity must flow to the project finish.",
        "inject delay on critical task -> finish moves by the delay",
        _DCMA,
        importance="A schedule must have a continuous, controlling critical path; if a delay on "
        "a critical task does not move the finish, the network logic is broken.",
        indicates="Failure means a broken or discontinuous critical path — open ends or "
        "constraints are absorbing the delay instead of passing it to the finish.",
        threshold="A delay injected on a critical activity must move the project finish by the "
        "same amount.",
        example_ok="Inject +10 d on a critical task and the finish moves +10 d -> PASS.",
        example_fail="The finish does not move -> FAIL; a constraint or open end is absorbing the "
        "delay (broken critical path).",
    ),
    "DCMA13": _doc(
        "DCMA13",
        "CPLI",
        "Critical Path Length Index.",
        "(remaining crit-path length + project total float) / remaining crit-path length >= 0.95",
        _DCMA,
        importance="CPLI measures how realistic the finish is: 1.0 means the critical path just "
        "fits, below ~0.95 means the path is already eroding into negative float.",
        indicates="A CPLI below 0.95 shows the controlling path is behind; recover its negative "
        "float to make the finish date credible.",
        threshold="Critical Path Length Index must be at least 0.95 (1.0 means the path just "
        "fits).",
        example_ok="CPLI of 1.02 -> PASS; the finish has a little slack.",
        example_fail="CPLI of 0.78 -> FAIL; the controlling path is eroding into negative float.",
    ),
    "DCMA14": _doc(
        "DCMA14",
        "BEI",
        "Baseline Execution Index (Acumen 'BEI - Value Tasks'; Normal activities only).",
        "complete Normal tasks / Normal tasks baselined-to-finish-by-status >= 0.95",
        _DCMA,
        importance="BEI tracks throughput against the baseline: are activities being completed "
        "as fast as the plan said they would be?",
        indicates="A BEI below 0.95 means the team is finishing work slower than baselined — an "
        "early, leading indicator of overall slip.",
        threshold="Baseline Execution Index must be at least 0.95 (work completed / work "
        "baselined to be complete).",
        example_ok="BEI of 0.98 -> PASS; throughput is on plan.",
        example_fail="BEI of 0.62 -> FAIL; work is finishing far slower than baselined - an "
        "early slip signal.",
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
        "Activities whose (current) duration exceeds 10% of the project's calendar span.",
        "count(OriginalDuration_workdays / (ProjectFinish - ProjectStart)_days > 0.1) <= 5%",
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
        "Share of start-due activities that started before their baseline FINISH (Acumen's "
        "Half-Step-Delay definition — distinct from Started On Time, which uses baseline start).",
        "count(actual start <= baseline finish) / forecast_to_be_started",
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
        "Current Execution Index, start side — single-schedule, baseline-anchored (= Started On "
        "Time %, distinct from Baseline Start Compliance's Half-Step-Delay numerator).",
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
    "driving_path": _doc(
        "driving_path",
        "Driving Path (between two UIDs)",
        "The chain of activities controlling target B's date that lie on a logic route from "
        "source A — the work that, if it slips, moves B. Traced across every loaded version.",
        "driving path to B (driving_slack < 1 working day) ∩ descendants(A), ordered A → … → B",
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
    "hmi_tasks": _doc(
        "hmi_tasks",
        "HMI (Tasks)",
        "Hit or Miss Index for tasks — period-over-period, not cumulative. A 'hit' is a task the "
        "baseline placed to finish in the current status period that actually completed in it.",
        "tasks baselined-due this period AND completed this period / tasks baselined-due in it",
        _HMI,
        importance="HMI measures whether the team is hitting the commitments it set for THIS "
        "period — a sharper, time-boxed read than the cumulative BEI/MEI.",
        indicates="A low HMI means activities baselined to finish this period are slipping out of "
        "it; the misses are the activities that were due but did not complete.",
    ),
    "hmi_milestones": _doc(
        "hmi_milestones",
        "HMI (Milestones)",
        "Hit or Miss Index for milestones — the milestone counterpart of HMI (Tasks): milestones "
        "the baseline placed in the current status period that actually completed in it.",
        "milestones baselined-due this period AND completed this period / milestones baselined-due "
        "the period",
        _HMI,
        importance="Milestone hits/misses per period are the contract-level heartbeat of the IMS.",
        indicates="A missed milestone baselined for this period is an immediate, citable slip.",
    ),
    "cei_tasks": _doc(
        "cei_tasks",
        "CEI (Tasks)",
        "Current Execution Index for tasks — period-over-period, forecast-anchored. Of the tasks "
        "the PRIOR schedule forecast to finish in the current status period, the share that "
        "actually completed by the data date. Needs two versions (N/A for a single schedule).",
        "tasks the prior schedule forecast to finish this period AND now complete / "
        "tasks the prior schedule forecast to finish this period",
        _HMI,
        importance="CEI reads whether the team executes the plan it most recently COMMITTED to "
        "(its own forecast) — the forecast-anchored sibling of the baseline-anchored HMI.",
        indicates="A low CEI means the latest forecast is not being met; the misses are the "
        "forecast-due activities that did not complete by the data date. Validated EXACT vs Acumen "
        "(Large Test File v1→v2: 24/129 = 0.19).",
    ),
    "cei_milestones": _doc(
        "cei_milestones",
        "CEI (Milestones)",
        "Current Execution Index for milestones — the milestone counterpart of CEI (Tasks): "
        "milestones the prior schedule forecast to finish this period that completed by the data "
        "date.",
        "milestones the prior schedule forecast to finish this period AND now complete / "
        "milestones the prior schedule forecast to finish this period",
        _HMI,
        importance="Forecast milestone execution per period — whether committed milestone dates "
        "hold.",
        indicates="A forecast-due milestone that did not complete by the data date is a citable "
        "slip against the team's own latest plan (validated vs Acumen: 1/6 = 0.17).",
    ),
    "cei_task_starts": _doc(
        "cei_task_starts",
        "CEI (Task Starts)",
        "CEI start cut — of the activities the prior schedule forecast to START in the period, the "
        "share that actually started by the data date.",
        "count(ActualStart > 0) / count(prior Start in (prev data date, data date])",
        _HMI,
        importance="The start-side companion to CEI — are the activities the team planned to kick "
        "off this period actually starting?",
        indicates="A low value means planned starts are slipping (validated vs Acumen: 12/117 = "
        "0.10).",
    ),
    "cei_critical": _doc(
        "cei_critical",
        "Critical CEI",
        "CEI restricted to the critical-path activities — of the CRITICAL activities the prior "
        "schedule forecast to finish this period, the share that actually completed.",
        "CEI (Tasks), population filtered to current critical-path activities",
        _HMI,
        importance="Execution on the critical path is what moves the finish; this isolates CEI to "
        "the activities that matter most.",
        indicates="A low Critical CEI means the driving work is not being executed to plan "
        "(validated vs Acumen: 0/3).",
    ),
    "cei_tasks_adjusted": _doc(
        "cei_tasks_adjusted",
        "CEI (adjusted)",
        "CEI finish cut that credits early completions — same denominator as CEI (Tasks), but the "
        "numerator also counts activities the prior schedule forecast to finish later but done "
        "ahead of plan.",
        "count(complete AND prior Finish > prev data date) / count(prior Finish in (prev, now])",
        _HMI,
        importance="Rewards finishing ahead of the committed forecast, not just on time — a fuller "
        "picture of execution than the plain CEI.",
        indicates="Higher than the plain CEI when work is being pulled forward (validated vs "
        "Acumen: 28/129 = 0.22).",
    ),
    "fei_starts": _doc(
        "fei_starts",
        "FEI (Starts)",
        "Forecast Execution Index, start cut — forward-looking (to-go). Of the remaining work, the "
        "count of activities still forecast to START in the remaining window over the count the "
        "baseline placed there.",
        "count(Start >= now) / count(BaselineStart >= now), over Normal value tasks",
        _HMI,
        importance="FEI reads the to-go plan vs the baseline; above 1.0 means more remaining work "
        "is forecast than baselined — a to-go bow wave being pushed into the future.",
        indicates="A rising FEI is work piling into the remaining window (validated vs Acumen on "
        "the Large Test File: ~2.78; start numerator EXACT).",
    ),
    "fei_finish": _doc(
        "fei_finish",
        "FEI (Finish)",
        "Forecast Execution Index, finish cut — the remaining activities still forecast to FINISH "
        "in the to-go window over the count the baseline placed there.",
        "count(Finish >= now AND not finished early) / count(BaselineFinish >= now), value tasks",
        _HMI,
        importance="The finish-side companion to FEI (Starts) — to-go finish load vs baseline.",
        indicates="Above 1.0 = more finishes forecast in the remaining window than baselined "
        "(validated vs Acumen: ~2.89).",
    ),
    "bri_cumulative": _doc(
        "bri_cumulative",
        "BRI",
        "Baseline Realism Index (cumulative) — of the activities the baseline placed to finish by "
        "now, how many actually finished by now. Backward-looking realism of the baseline.",
        "count(BaselineFinish <= now AND actually finished <= now) / count(BaselineFinish <= now)",
        _HMI,
        importance="BRI asks whether the baseline was realistic / the team is executing the plan; "
        "the baselined-due activities that did not finish are the misses.",
        indicates="A low BRI means the baseline placed work to finish by now that did not — slip "
        "against the plan (validated EXACT vs Acumen: 0.51, denominator 1228 EXACT).",
    ),
    "float_ratio": _doc(
        "float_ratio",
        "Float Ratio™",
        "Average, across the live activities, of each activity's total float divided by its "
        "remaining duration — how much breathing room the remaining work has relative to how much "
        "work is left. Over Normal planned/in-progress activities (completed work excluded). The "
        "cited offenders are the very-tight activities (per-activity ratio < 0.1).",
        "AVERAGE(TotalFloat / RemainingDuration), Normal planned/in-progress activities",
        _HMI,
        importance="Float Ratio reads how much slack the schedule carries per day of remaining "
        "work; bands (Bible): <0.1 very tight, 0.1-0.3 tight, 0.3-0.6 healthy, >0.6 generous.",
        indicates="A very low ratio is a schedule running out of room (delay risk); an excessively "
        "high ratio flags poor logic — missing links / out-of-sequence work inflating float. "
        "Validated on the Large Test File: the population's average remaining duration (18.4 "
        "working days) matches Acumen's reported Avg. Remaining Duration (~18).",
    ),
    "float_ratio_aggregate": _doc(
        "float_ratio_aggregate",
        "Float Ratio (aggregate)",
        "The ratio-of-means companion to Float Ratio™: total float over total remaining duration "
        "across the same population. More robust than the mean-of-ratios to activities with a tiny "
        "remaining duration (which can otherwise dominate the average).",
        "AVERAGE(TotalFloat) / AVERAGE(RemainingDuration), Normal planned/in-progress activities",
        _HMI,
        importance="Reported alongside the canonical Float Ratio so a few near-zero-remaining "
        "activities can't skew the period-to-period read.",
        indicates="Tracks the canonical Float Ratio; a divergence between the two means a handful "
        "of almost-finished activities carry outsized float.",
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


# --------------------------------------------------------------------------------------
# Reliability-Dimension framework (NASA Schedule Management Handbook §6, plan section C).
# Each metric is tagged with the schedule-reliability dimension it most informs, so the
# dictionary can present the handbook's four-dimension organizing lens. This is an
# ORGANIZATIONAL label over the existing metrics — presentation only; it changes no computed
# figure (so it does not engage the parity law). The mapping is family-level with the rationale
# below; an unmapped id falls through to "Realism" (the execution-performance bucket).
# --------------------------------------------------------------------------------------

RELIABILITY_DIMENSIONS = ("Comprehensiveness", "Construction", "Realism", "Affordability")

#: cost-based EVM indices — the only cost-feasibility (affordability) measures the tool carries
_DIM_AFFORDABILITY = frozenset({"spi", "cpi", "tcpi"})
#: "is everything captured and tied in?" — network/logic completeness, resource loading, census
_DIM_COMPREHENSIVENESS = frozenset(
    {"DCMA01", "DCMA10", "missing_logic", "SN01", "SN02", "SN18", "SN19"}
)
#: "is the network built per scheduling best practice?" — logic quality, constraints, float health
_DIM_CONSTRUCTION = frozenset(
    {
        "DCMA02",
        "DCMA03",
        "DCMA04_FS",
        "DCMA04_SSFF",
        "DCMA04_SF",
        "DCMA05",
        "DCMA06",
        "DCMA07",
        "DCMA08",
        "DCMA09",
        "DCMA12",
        "logic_density",
        "critical",
        "hard_constraints",
        "negative_float",
        "insufficient_detail",
        "number_of_lags",
        "number_of_leads",
        "merge_hotspot",
        "logic_unsupported_dates",
        "logic_on_summary_tasks",
        "SN03",
        "SN04",
        "driving_slack",
        "driving_path",
        "float_total_0",
        "float_total_lt5",
        "float_total_lt10",
        "float_free_0",
        "float_free_lt5",
        "float_free_lt10",
        "float_ratio",
        "float_ratio_aggregate",
    }
)


def reliability_dimension(metric_id: str) -> str:
    """The NASA reliability dimension a metric most informs (organizational tag, not a figure).

    Affordability = cost EVM; Comprehensiveness = network/resource/census completeness; Construction
    = network-build quality (logic, constraints, float); everything else (execution performance,
    variance, forecasts, slips) is Realism — "is the plan achievable and matching reality?"
    """
    if metric_id in _DIM_AFFORDABILITY:
        return "Affordability"
    if metric_id in _DIM_COMPREHENSIVENESS:
        return "Comprehensiveness"
    if metric_id in _DIM_CONSTRUCTION:
        return "Construction"
    return "Realism"


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
        "schedule (§6). The **Dimension** column tags each metric with the NASA Schedule "
        "Management Handbook reliability dimension it most informs (Comprehensiveness / "
        "Construction / Realism / Affordability) — an organizational lens, not a computed figure.",
        "",
        "| Metric | Dimension | Definition | Formula | Source |",
        "|--------|-----------|------------|---------|--------|",
    ]
    for doc in METRIC_DICTIONARY.values():
        dim = reliability_dimension(doc.metric_id)
        lines.append(f"| {doc.name} | {dim} | {doc.definition} | `{doc.formula}` | {doc.source} |")
    return "\n".join(lines) + "\n"
