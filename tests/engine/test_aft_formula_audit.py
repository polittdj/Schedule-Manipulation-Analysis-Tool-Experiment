"""Definitional audit — tool metric formulas vs the NASA Acumen "Bible" (``.aft``).

This is **not** a parity test; it is a *definitional* check. For every metric the tool
documents in :mod:`schedule_forensics.web.help` we record the corresponding NASA Acumen
metric (by ``Name``) and its **verbatim** ``Formula`` from ``NASA Metrics_Complete_*.aft``,
classify the correspondence, and assert the pinned NASA formula still matches EVERY
committed Bible snapshot (a guard against silent Bible drift *and* the canonical record of
which NASA formula each tool metric was built against). ADR-0263: the guard audits ALL
``.aft`` files under ``00_REFERENCE_INTAKE/`` — auditing only ``sorted(...)[0]`` silently
skipped the newer ``acumen_v8.11.0`` snapshot (verified near-identical: 759 metric names in
both; one formula-set difference, 'Invalid Forecast Dates', which is a dropped duplicate
entry differing only by outer parentheses and is not pinned here).

Why a curated table rather than a string-normalised auto-match: ``help.py`` formulas are
plain-language pseudocode while the ``.aft`` carries Acumen's own formula notation, so a
literal comparison is meaningless. Each row therefore carries a human verdict:

* ``match``        — semantically equivalent; only notation / wording differs.
* ``variant``      — a deliberate, Acumen-validated tool extension/variant of a Bible metric.
* ``drift``        — a *real* definitional difference. Each is documented in **ADR-0110**.
* ``not_in_bible`` — no formula-bearing Bible counterpart (DCMA-standard / EVM-standard /
  SSI / reference-deck / cross-version / tool-proprietary). The note records provenance.

The **non-CUI reference** ``.aft`` is **committed** under ``00_REFERENCE_INTAKE/``
(ADR-0151/0152), so the formula-pinning test **runs** against it — on CI too, not only on an
operator machine. The ``pytest.skip`` below is now just a defensive fallback for the case where
that reference file is ever absent (mirroring the existing ``.mpp`` skips). A **real CUI** ``.aft``
from a production machine is still never committed (the pre-commit guard blocks it). See ADR-0110
(the pinned formula table) and ADR-0151/0152 (the committed non-CUI reference suite).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pytest

from schedule_forensics.web.help import METRIC_DICTIONARY

# --- verdict vocabulary -------------------------------------------------------------------
MATCH = "match"
VARIANT = "variant"
DRIFT = "drift"
NOT_IN_BIBLE = "not_in_bible"
_VERDICTS = frozenset({MATCH, VARIANT, DRIFT, NOT_IN_BIBLE})
_HAS_FORMULA = frozenset({MATCH, VARIANT, DRIFT})  # verdicts that pin a NASA formula

#: The Bible was extracted from this snapshot; bump the note in ADR-0110 if it is refreshed.
_BIBLE_SNAPSHOT = "NASA Metrics_Complete_20260423.aft"


@dataclass(frozen=True)
class Row:
    """One tool-metric ↔ NASA-metric correspondence."""

    tool_id: str
    nasa_name: str  # "" ⇒ no Bible counterpart (NOT_IN_BIBLE)
    nasa_formula: str  # verbatim from the .aft; "" ⇒ NOT_IN_BIBLE
    verdict: str
    note: str = ""


# =====================================================================================
# The audit table — one row per documented metric (ordered as in help.py).
# NASA formulas are copied verbatim from the .aft; whitespace is irrelevant (normalised
# away before comparison), so they are written readably here.
# =====================================================================================
AUDIT: tuple[Row, ...] = (
    # --- DCMA-14 ribbon (DCMA standard; some have formula-bearing Bible counterparts) ---
    Row(
        "DCMA01",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA 14-point check (incomplete-scoped, 5% threshold). The Bible's open-ends "
        "metric is 'Missing Logic' (period-windowed) — audited under tool id 'missing_logic'.",
    ),
    Row(
        "DCMA02",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA standard (count of negative-lag relationships). The Bible's 'Number of Leads' "
        "is display-only; 'Total # Predecessor Leads' = sum(numberofleads) is predecessor-only.",
    ),
    Row(
        "DCMA03",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA standard (positive-lag relationships). Bible 'Number of Lags' is display-only.",
    ),
    Row("DCMA04_FS", "", "", NOT_IN_BIBLE, "DCMA standard (FS relationship share)."),
    Row("DCMA04_SSFF", "", "", NOT_IN_BIBLE, "DCMA standard (SS/FF into incomplete)."),
    Row(
        "DCMA04_SF",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA standard (SF relationships). Bible 'SF Relations' = SUM(NumberofSFPredecessors).",
    ),
    Row(
        "DCMA05",
        "Hard Constraints",
        'SUM(((ActivityConstraint="MandatoryStart")+(ActivityConstraint="MandatoryFinish")'
        '+(ActivityConstraint="MustStartOn")+(ActivityConstraint="MustFinishOn")'
        '+(ActivityConstraint="StartAndFinish")>0)*1)',
        DRIFT,
        "ADR-0110: the engine counts {MSO, MFO, SNLT, FNLT} as hard; NASA's headline "
        "'Hard Constraints' counts must/mandatory/StartAndFinish only (NOT SNLT/FNLT). NASA's "
        "'B.03.12 FC IMS with hard constraints' variant DOES include StartOnOrBefore/"
        "FinishOnOrBefore — i.e. the tool follows the DCMA/FC-IMS convention. Latent: no parity "
        "impact unless a schedule carries SNLT/FNLT.",
    ),
    Row(
        "DCMA06",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA 44-working-day rule. The Bible's formula-bearing 'High Float 10%' uses 10% of the "
        "project span (SUM((TotalFloat/(ProjectFinish-ProjectStart)>0.1)*1)) — a different "
        "definition; its '44d' variant carries no formula in this library.",
    ),
    Row("DCMA07", "", "", NOT_IN_BIBLE, "DCMA standard. Bible 'Negative Float' is display-only."),
    Row(
        "DCMA08",
        "High Duration",
        'SUM((OriginalDuration>44)*(ActivityType="Normal")*(ActivityStatus<>"Complete"))',
        DRIFT,
        "ADR-0110: the engine keys High Duration on BASELINE duration > 44d; NASA keys on "
        "current OriginalDuration > 44d AND ActivityType=Normal. Differs on schedules where "
        "current duration ≠ baseline duration, or for non-Normal activities.",
    ),
    Row("DCMA09", "", "", NOT_IN_BIBLE, "DCMA standard (invalid actuals/forecasts vs status)."),
    Row(
        "DCMA10",
        "",
        "",
        NOT_IN_BIBLE,
        "DCMA standard. The Bible's resource checks (B.05.x) use a different IMS framing "
        "(BudgetCost/TotalWork over baseline-statused populations).",
    ),
    Row("DCMA11", "", "", NOT_IN_BIBLE, "DCMA standard (baselined-due not finished on time)."),
    Row(
        "DCMA12",
        "12. Critical Path Test",
        'IF(SUM((ProjectCriticalPathTest=TRUE)*1)=COUNTA(ID), "✓", '
        'IF(SUM((ProjectCriticalPathTest="")*1)=COUNTA(ID), "N/A", "X"))',
        MATCH,
        "Same DCMA-12 test. Mechanism differs: the tool injects a live delay on a critical "
        "activity and checks the finish moves; NASA evaluates a precomputed "
        "ProjectCriticalPathTest flag.",
    ),
    Row(
        "DCMA13",
        "13. CPLI",
        "(ProjectRemainingDuration + ProjectMinimumTotalFloat) / ProjectRemainingDuration",
        MATCH,
        "ProjectMinimumTotalFloat is the project total float; identical to the tool's CPLI.",
    ),
    Row(
        "DCMA14",
        "BEI - Value Tasks",
        'countif(PercentComplete,"=100%") / SUM(IF(BaselineFinish<=ProjectTimeNow,1))',
        MATCH,
        "Validated exact in ADR-0089 ('BEI - Value Tasks'); Normal-task population is implicit "
        "in the value-task metric.",
    ),
    # --- Acumen Schedule-Quality summary ---
    Row(
        "missing_logic",
        "Missing Logic",
        "SUM((((NumberOfPredecessors+NumberofExternalPredecessors=0)*(Start>=_PeriodStart))"
        "+((NumberOfSuccessors+NumberofExternalSuccessors=0)*(Finish<=_PeriodFinish))>0)*1)",
        MATCH,
        "Period-windowed open-ends; reduces to a pure open-ends count when run full-project "
        "(_PeriodStart/_PeriodFinish = project span). Matches the tool's full-project value.",
    ),
    Row(
        "logic_density",
        "Logic Density™",
        "AVERAGE(NumberOfPredecessors+NumberofExternalPredecessors+NumberOfSuccessors"
        "+NumberofExternalSuccessors)",
        MATCH,
        "Mean (in+out) degree per activity = 2·links/activities; identical.",
    ),
    Row(
        "critical",
        "",
        "",
        NOT_IN_BIBLE,
        "Bible critical-path metrics ('Critical', 'Critical Path (Normal Tasks)', …) are "
        "display-only (no formula). Tool: count(total_float<=0 and incomplete).",
    ),
    Row(
        "hard_constraints",
        "Hard Constraints",
        'SUM(((ActivityConstraint="MandatoryStart")+(ActivityConstraint="MandatoryFinish")'
        '+(ActivityConstraint="MustStartOn")+(ActivityConstraint="MustFinishOn")'
        '+(ActivityConstraint="StartAndFinish")>0)*1)',
        DRIFT,
        "ADR-0110: same engine constraint set as DCMA05 ({MSO,MFO,SNLT,FNLT}); NASA's headline "
        "metric excludes SNLT/FNLT. See the DCMA05 row.",
    ),
    Row("negative_float", "", "", NOT_IN_BIBLE, "Bible 'Negative Float' is display-only."),
    Row(
        "insufficient_detail",
        "Insufficient Detail™",
        "SUM((OriginalDuration / (ProjectFinish-ProjectStart) > 0.1) * 1)",
        MATCH,
        "Identical: current duration > 10% of project span. The tool documents the working-day / "
        "calendar-day unit handling explicitly; Acumen's OriginalDuration is likewise in days.",
    ),
    Row(
        "number_of_lags",
        "",
        "",
        NOT_IN_BIBLE,
        "Bible 'Number of Lags' display-only; 'Total # Predecessor Lags' = sum(numberoflags) is "
        "predecessor-only, whereas the tool counts all positive-lag relationships.",
    ),
    Row(
        "number_of_leads",
        "",
        "",
        NOT_IN_BIBLE,
        "Bible 'Number of Leads' display-only; 'Total # Predecessor Leads' is predecessor-only.",
    ),
    Row(
        "merge_hotspot",
        "Merge Hotspot",
        "SUM((NumberOfPredecessors+NumberofExternalPredecessors>2)*1)",
        MATCH,
        ">2 predecessors == >=3 predecessors; identical.",
    ),
    # --- Baseline compliance / Half-Step-Delay (Acumen 'by Status Dates' family) ---
    Row(
        "forecast_to_be_finished",
        "Forecast to be Finished",
        "Sum(1*(BaselineFinish < ProjectTimeNow))",
        MATCH,
        "Boundary: NASA uses strict < status; tool documents <= status (immaterial unless a "
        "baseline finish lands exactly on the status instant).",
    ),
    Row(
        "completed_on_time",
        "Completed On Time",
        "sum((BaselineFinish < ProjectTimeNow) * (Finish < ProjectTimeNow) "
        "* (INT(Finish) <= INT(BaselineFinish)))",
        MATCH,
        "Due (baselined to finish by status) AND finished AND on/before baseline finish (day "
        "granularity via INT).",
    ),
    Row(
        "completed_late",
        "Completed Late",
        "sum((BaselineFinish < ProjectTimeNow) * (Finish < ProjectTimeNow) "
        "* (INT(Finish) > INT(BaselineFinish)))",
        MATCH,
        "Due AND finished AND after baseline finish.",
    ),
    Row(
        "not_completed",
        "",
        "",
        NOT_IN_BIBLE,
        "Bible 'Not Completed' is display-only. Tool: count(due and incomplete)/due.",
    ),
    Row(
        "baseline_finish_compliance",
        "Baseline Finish Compliance",
        "sum((BaselineFinish<ProjectTimeNow) * (Finish<ProjectTimeNow) "
        "* (INT(Finish) <= INT(BaselineFinish))) / Sum(1*(BaselineFinish<ProjectTimeNow))",
        MATCH,
        "= Completed On Time / Forecast to be Finished; identical to the tool's BFC.",
    ),
    Row(
        "logic_unsupported_dates",
        "",
        "",
        NOT_IN_BIBLE,
        "Tool-specific stored-date-CPM diagnostic (ADR-0034); no Bible counterpart.",
    ),
    Row(
        "logic_on_summary_tasks",
        "",
        "",
        NOT_IN_BIBLE,
        "Tool-specific summary-logic diagnostic (ADR-0043); no Bible counterpart.",
    ),
    Row(
        "forecast_to_be_started",
        "Forecast to be Started",
        "Sum(1*(BaselineStart< ProjectTimeNow))",
        MATCH,
        "Boundary < vs <= as in forecast_to_be_finished.",
    ),
    Row(
        "started_on_time",
        "Started On Time",
        "sum((BaselineStart < ProjectTimeNow) * (Start < ProjectTimeNow) "
        "* (INT(Start) <= INT(BaselineStart)))",
        MATCH,
        "Start-due AND started AND on/before baseline START (distinct from the Half-Step-Delay "
        "compliance numerator, which uses baseline finish).",
    ),
    Row(
        "started_late",
        "Started Late",
        "SUM((((ActualStart)-(BaselineStart))>0) * 1)",
        MATCH,
        "Actual start after baseline start.",
    ),
    Row(
        "not_started",
        "Not Started",
        "sum((BaselineStart < ProjectTimeNow) * NOT(ISNUMBER(ActualStart)))",
        MATCH,
        "Start-due with no actual start.",
    ),
    Row(
        "baseline_start_compliance",
        "Baseline Start Compliance",
        "sum((BaselineStart<ProjectTimeNow) * (Start<ProjectTimeNow) "
        "* (INT(Start) <= INT(BaselineFinish))) / Sum(1*(BaselineStart<ProjectTimeNow))",
        MATCH,
        "Half-Step-Delay: started on/before baseline FINISH / forecast-to-be-started; identical.",
    ),
    # --- EVM indices ---
    Row(
        "spi",
        "SPI",
        "sum(BCWPEV)/sum(BCWSPV)",
        MATCH,
        "BCWP/BCWS (cost-based).",
    ),
    Row("cpi", "CPI", "sum(BCWPEV)/sum(ACWPAC)", MATCH, "BCWP/ACWP."),
    Row(
        "tcpi",
        "TCPI(BAC)",
        "sum((BaselineCost-BCWPEV))/sum((BaselineCost-ACWPAC))",
        MATCH,
        "(BAC-BCWP)/(BAC-ACWP); BAC = BaselineCost.",
    ),
    Row(
        "cei_finish",
        "",
        "",
        NOT_IN_BIBLE,
        "Single-schedule baseline-anchored CEI (= Baseline Finish Compliance). Distinct from the "
        "Bible's forecast-anchored CEI — audited under 'cei_tasks'.",
    ),
    Row(
        "cei_start",
        "",
        "",
        NOT_IN_BIBLE,
        "Single-schedule baseline-anchored CEI (start side). See cei_finish.",
    ),
    Row(
        "cei_bow_wave",
        "",
        "",
        NOT_IN_BIBLE,
        "Bow-wave (monthly-forward) CEI of the /cei view; distinct from the Bible CEI.",
    ),
    Row(
        "spi_t",
        "SPI(t)",
        'AVERAGE(IF(ActivityStatus = "Complete", (BaselineFinish - BaselineStart) / '
        "(ActualFinish - ActualStart), ((BaselineFinish - BaselineStart) - "
        "(Finish - ProjectTimeNow)) / (ActualFinish - ActualStart)))",
        DRIFT,
        "ADR-0110: the tool's SPI(t) = Earned Schedule / Actual Time (count/time-based ES). "
        "Acumen's '.aft' SPI(t) is a per-activity duration-ratio average (baseline vs "
        "actual/remaining duration) — a different metric of the same name, kept deliberately "
        "(ADR-0176: both are now reported side by side; the Bible formula itself is implemented "
        "verbatim as 'spi_t_acumen' below, closing the former EVM2 residual).",
    ),
    Row(
        "spi_t_acumen",
        "SPI(t)",
        'AVERAGE(IF(ActivityStatus = "Complete", (BaselineFinish - BaselineStart) / '
        "(ActualFinish - ActualStart), ((BaselineFinish - BaselineStart) - "
        "(Finish - ProjectTimeNow)) / (ActualFinish - ActualStart)))",
        MATCH,
        "ADR-0176: the Bible formula implemented faithfully, including Acumen's evaluation "
        "quirks proven against the Fuse Metric History (started-incomplete term = 0 via blank "
        "ActualFinish; zero-span completions excluded). Parity EXACT on Hard_File_updated/2/3 "
        "(0.80 / 1.14 / 1.25).",
    ),
    # --- Schedule-Network change (§E) + HSD ---
    Row("SN01", "", "", NOT_IN_BIBLE, "Cross-version network metric (count of activities)."),
    Row("SN02", "", "", NOT_IN_BIBLE, "Cross-version (UID set difference)."),
    Row("SN03", "", "", NOT_IN_BIBLE, "Cross-version (newly critical)."),
    Row(
        "SN04",
        "Activities No Longer Critical",
        "SUM(if( (Previous_Critical=True) * (Critical=False) ,1,0))",
        MATCH,
        "Was critical, now not. The tool additionally requires 'still incomplete' (an immaterial "
        "refinement for a forensic read).",
    ),
    Row("SN05", "", "", NOT_IN_BIBLE, "Cross-version (prior-forecast finish slips)."),
    Row("SN06", "", "", NOT_IN_BIBLE, "Cross-version (prior-forecast start slips)."),
    Row("SN07", "", "", NOT_IN_BIBLE, "Cross-version (remaining-duration increases)."),
    Row("SN09", "", "", NOT_IN_BIBLE, "Cross-version (float erosion)."),
    Row("SN18", "", "", NOT_IN_BIBLE, "Bible 'Completed' is display-only."),
    Row("SN19", "", "", NOT_IN_BIBLE, "Bible in-progress metrics are display-only."),
    Row(
        "HSD10",
        "Net Finish Impact (Days)",
        "IF(ISNUMBER(ProjectPreviousFinish), ROUND(TRIM(ProjectPreviousFinish) "
        '- TRIM(ProjectFinish),0), "0")',
        MATCH,
        "Prior project finish - current project finish, in days.",
    ),
    # --- SSI driving slack ---
    Row("driving_slack", "", "", NOT_IN_BIBLE, "SSI MS Project add-on metric; no Bible formula."),
    Row("driving_path", "", "", NOT_IN_BIBLE, "SSI/tool path trace; no Bible formula."),
    # --- M15: reference-deck measure families (ADR-0030) ---
    Row("float_total_0", "", "", NOT_IN_BIBLE, "Reference-deck float band (ADR-0030)."),
    Row("float_total_lt5", "", "", NOT_IN_BIBLE, "Reference-deck float band."),
    Row("float_total_lt10", "", "", NOT_IN_BIBLE, "Reference-deck float band."),
    Row("float_free_0", "", "", NOT_IN_BIBLE, "Reference-deck float band (free float)."),
    Row("float_free_lt5", "", "", NOT_IN_BIBLE, "Reference-deck float band (free float)."),
    Row("float_free_lt10", "", "", NOT_IN_BIBLE, "Reference-deck float band (free float)."),
    Row(
        "completed_ahead",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck. Bible 'Completed Ahead' is display-only (no formula).",
    ),
    Row(
        "completed_on_schedule",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck. Bible 'Completed On-Schedule' is display-only.",
    ),
    Row(
        "completed_behind", "", "", NOT_IN_BIBLE, "Reference deck. Bible 'Completed' display-only."
    ),
    Row(
        "avg_days_ahead",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck. The Bible carries 'Avg Days Late' (signed) but no early-only average.",
    ),
    Row(
        "avg_days_late",
        "Avg Days Late",
        "AVERAGE(ISNUMBER(BaselineFinish)*ISNUMBER(ActualFinish)*(IF(ISNUMBER(ActualFinish),"
        "ActualFinish,0)-IF(ISNUMBER(BaselineFinish),BaselineFinish,0)))",
        VARIANT,
        "Tool averages (actual-baseline) over completed-BEHIND activities; NASA averages the "
        "signed difference over all activities with both dates. Same kernel, different population.",
    ),
    Row(
        "avg_completion_variance",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck (signed finish variance over all completed). Closest Bible kernel is "
        "'Avg Days Late'.",
    ),
    Row(
        "longer_than_planned",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck; Bible counterpart display-only.",
    ),
    Row(
        "shorter_than_planned",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference deck; Bible counterpart display-only.",
    ),
    Row(
        "duration_ratio_min",
        "Min Duration Ratio Value",
        "Min(ActualDuration/BaselineDuration)",
        MATCH,
        "Identical (over completed activities).",
    ),
    Row(
        "duration_ratio_avg",
        "Avg Duration Ratio",
        'sum(ActualDuration/BaselineDuration)/Countif(PercentComplete, "=100%")',
        MATCH,
        "Mean of the actual/baseline ratio over completed activities; identical.",
    ),
    Row(
        "duration_ratio_max",
        "Max Duration Ratio Value",
        "Max(ActualDuration/BaselineDuration)",
        MATCH,
        "Identical (over completed activities).",
    ),
    Row(
        "mei",
        "",
        "",
        NOT_IN_BIBLE,
        "Milestone Execution Index (BEI restricted to milestones). No 'MEI' metric in the Bible.",
    ),
    Row(
        "hmi_tasks",
        "HMI - Value Task Finishes - by Status Dates",
        "SUM(IF(PercentComplete=100%, IF(Finish>ProjectPreviousTimeNow, "
        "IF(BaselineFinish<=ProjectTimeNow, IF(BaselineFinish>ProjectPreviousTimeNow,1))))) / "
        "SUM(IF(BaselineFinish<=ProjectTimeNow, IF(BaselineFinish>ProjectPreviousTimeNow,1)))",
        MATCH,
        "Finishes baselined-due in the status period that completed in it / baselined-due in it "
        "(ADR-0087).",
    ),
    Row(
        "hmi_milestones",
        "HMI - Value Task Finishes - by Status Dates",
        "SUM(IF(PercentComplete=100%, IF(Finish>ProjectPreviousTimeNow, "
        "IF(BaselineFinish<=ProjectTimeNow, IF(BaselineFinish>ProjectPreviousTimeNow,1))))) / "
        "SUM(IF(BaselineFinish<=ProjectTimeNow, IF(BaselineFinish>ProjectPreviousTimeNow,1)))",
        MATCH,
        "Same HMI finishes formula, milestone population.",
    ),
    Row(
        "cei_tasks",
        "CEI - Value Task Finishes - by Status Dates",
        'countif(PercentComplete,"=100%") / '
        "SUM(IF(PreviousFinish>ProjectPreviousTimeNow, (IF(PreviousFinish<=ProjectTimeNow,1))))",
        MATCH,
        "Forecast-anchored: prior-forecast finishes in the period that completed / forecast in it "
        "(ADR-0098, validated 24/129 = 0.19).",
    ),
    Row(
        "cei_milestones",
        "CEI - Value Task Finishes - by Status Dates",
        'countif(PercentComplete,"=100%") / '
        "SUM(IF(PreviousFinish>ProjectPreviousTimeNow, (IF(PreviousFinish<=ProjectTimeNow,1))))",
        MATCH,
        "Same CEI finishes formula, milestone population (validated 1/6 = 0.17).",
    ),
    Row(
        "cei_task_starts",
        "CEI - Value Task Starts - by Status Dates",
        'countif(ActualStart,">0") / '
        "SUM(IF(PreviousStart>ProjectPreviousTimeNow, (IF(PreviousStart<=ProjectTimeNow,1))))",
        MATCH,
        "Start cut (validated 12/117 = 0.10).",
    ),
    Row(
        "cei_critical",
        "Critical CEI - Value Tasks",
        'countif(PercentComplete,"=100%") / '
        "SUM(IF(PreviousFinish>ProjectPreviousTimeNow, (IF(PreviousFinish<=ProjectTimeNow,1))))",
        MATCH,
        "CEI finishes restricted to the critical-path population (validated 0/3).",
    ),
    Row(
        "cei_tasks_adjusted",
        "CEI - Value Task Finishes - by Status Dates",
        'countif(PercentComplete,"=100%") / '
        "SUM(IF(PreviousFinish>ProjectPreviousTimeNow, (IF(PreviousFinish<=ProjectTimeNow,1))))",
        VARIANT,
        "Tool variant: same denominator, but the numerator also credits activities forecast to "
        "finish later yet done ahead of plan (validated 28/129 = 0.22). Base metric pinned here.",
    ),
    Row(
        "fei_starts",
        "FEI - Value Task Starts - Cumulative",
        "Sum((Start>=ProjectTimeNow)*1)/SUM((BaselineStart>=ProjectTimeNow)*1)",
        MATCH,
        "To-go starts forecast vs baselined (ADR-0100).",
    ),
    Row(
        "fei_finish",
        "FEI - Value Task Finish - Cumulative",
        "Sum((Finish>=ProjectTimeNow)*((ActualFinish >= ProjectTimeNow) "
        "+ NOT(ISNUMBER(ActualFinish)*1)))/SUM((BaselineFinish>=ProjectTimeNow)*1)",
        MATCH,
        "To-go finishes forecast (not finished early) vs baselined (ADR-0100).",
    ),
    Row(
        "bri_cumulative",
        "BRI Cumulative",
        "ROUND(IF(SUM(IF( (BaselineFinish <= ProjectTimeNow) , 1 , 0)) > 0, "
        "SUM(IF( (BaselineFinish <= ProjectTimeNow), "
        "IF( (ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0), 0)) / "
        "SUM( IF( (BaselineFinish <= ProjectTimeNow) , 1 , 0) ), 0), 2)",
        MATCH,
        "Baselined-due-by-now that actually finished by now / baselined-due-by-now (ADR-0100, "
        "validated 0.51, denominator 1228 exact).",
    ),
    # --- Schedule Execution Metrics (SEM) — the Bible's Industry-Standards family (ADR-0238);
    # all formulas verbatim; validated vs the committed P2/P5 Fuse DCMA report SEM rows ---
    Row(
        "sem_completed",
        "Completed Activities",
        "SUM( IF( (ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish) ,1 ,0) )",
        MATCH,
        "Validated exact: Project2=20, Project5_TAMPERED=27.",
    ),
    Row(
        "sem_workoff_burden",
        "Workoff Burden",
        "SUM( IF( (ActualFinish >= ProjectTimeNowMinus30Days) * (ActualFinish <= ProjectTimeNow)"
        " * ISNUMBER(ActualFinish) , IF( (BaselineFinish < ProjectTimeNowMinus30Days), 1, 0) ,"
        " 0) )",
        MATCH,
        "Validated exact: 5 / 2 on the reference pair.",
    ),
    Row(
        "sem_bri_current",
        "BRI Current",
        "ROUND( IF(SUM(IF( (BaselineFinish >= ProjectTimeNowMinus30Days) * (BaselineFinish <= "
        "ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( (BaselineFinish >= ProjectTimeNowMinus30Days) "
        "* (BaselineFinish <= ProjectTimeNow) , IF( (ActualFinish >= ProjectTimeNowMinus30Days) "
        "* (ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0) , 0) ) / SUM( IF( "
        "(BaselineFinish >= ProjectTimeNowMinus30Days) * (BaselineFinish <= ProjectTimeNow) , 1 "
        ", 0) ) ,0 ) ,2)",
        MATCH,
        "Window-restricted numerator (unlike BEI Current). Validated: 0 / 0 on the pair.",
    ),
    Row(
        "sem_bpi_current",
        "BPI Current",
        "ROUND( IF(SUM(IF( (BaselineFinish >= ProjectTimeNowMinus30Days) * (BaselineFinish <= "
        "ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( (BaselineFinish >= ProjectTimeNowMinus30Days) "
        "* (BaselineFinish <= ProjectTimeNow) , IF( (ActualFinish <= ProjectTimeNow) * "
        "ISNUMBER(ActualFinish), 1, 0) , 0) ) / SUM( IF( (BaselineFinish >= "
        "ProjectTimeNowMinus30Days) * (BaselineFinish <= ProjectTimeNow) , 1 , 0) ) ,0 ) ,2)",
        MATCH,
        "Finished-at-all numerator over the window's baselined finishes.",
    ),
    Row(
        "sem_bei_current",
        "BEI Current",
        "ROUND( IF(SUM(IF((BaselineFinish >= ProjectTimeNowMinus30Days) * (BaselineFinish <= "
        "ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( (ActualFinish >= ProjectTimeNowMinus30Days) * "
        "(ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0) ) / SUM( IF( "
        "(BaselineFinish >= ProjectTimeNowMinus30Days) * (BaselineFinish <= ProjectTimeNow) , 1,"
        " 0) ) ,0 ) ,2)",
        MATCH,
        "Numerator counts ALL window finishes (can exceed 1). Validated exact: 1.25 = 5/4.",
    ),
    Row(
        "sem_bei_cumulative",
        "BEI Cumulative",
        "ROUND( IF(SUM(IF((BaselineFinish <= ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( "
        "(ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0) ) / SUM( IF( "
        "(BaselineFinish <= ProjectTimeNow) , 1 , 0) ) ,0 ) ,2)",
        MATCH,
        "Actual-finish twin of the DCMA %-complete BEI (both ship — ADR-0176 precedent). "
        "Validated exact: 0.74 / 0.59.",
    ),
    Row(
        "sem_tc_bei",
        "TC-BEI",
        "IF(SUM(IF( (BaselineFinish >= ProjectTimeNow), 1, 0)) > 0 , SUM( IF( (Finish >= "
        "ProjectTimeNow), 1, 0) ) / SUM( IF( (BaselineFinish >= ProjectTimeNow) * (( "
        "(ActualFinish >= ProjectTimeNow) + NOT(ISNUMBER(ActualFinish)) )=1) , 1, 0) ) , 0 )",
        MATCH,
        "No ROUND in the Bible (2-dp at display). Validated exact: 1.07 = 106/99, 1.24 = 99/80.",
    ),
    Row(
        "sem_fri_current",
        "FRI Current",
        "ROUND( IF( SUM(IF( (PreviousFinish >= ProjectTimeNowMinus30Days) * (PreviousFinish <= "
        "ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( (PreviousFinish >= ProjectTimeNowMinus30Days) "
        "* (PreviousFinish <= ProjectTimeNow) , IF( (ActualFinish >= ProjectTimeNowMinus30Days) "
        "* (ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0) , 0) ) / SUM( IF( "
        "(PreviousFinish >= ProjectTimeNowMinus30Days) * (PreviousFinish <= ProjectTimeNow) , 1 "
        ", 0) ) ,0 ) ,2)",
        MATCH,
        "PreviousFinish = the prior loaded version's forecast finish (UniqueID join); NA with "
        "no prior, as the reference prints. Validated: 0 = 0/9 with Project2 as prior.",
    ),
    Row(
        "sem_delta",
        "Delta (BEI vs TC-BEI)",
        "ROUND( IF(SUM(IF((BaselineFinish <= ProjectTimeNow) , 1 , 0)) > 0 , SUM( IF( "
        "(ActualFinish <= ProjectTimeNow) * ISNUMBER(ActualFinish), 1, 0) ) / SUM( IF( "
        "(BaselineFinish <= ProjectTimeNow) , 1 , 0) ) ,0 ) - IF(SUM(IF( (BaselineFinish >= "
        "ProjectTimeNow), 1, 0)) > 0 , SUM(IF( (Finish >= ProjectTimeNow), 1, 0)) / SUM(IF( "
        "(BaselineFinish >= ProjectTimeNow), 1, 0)) , 0 ) ,2)",
        MATCH,
        "Implemented verbatim (to-complete term = the SIMPLE baselined-to-go denominator). The "
        "reference export's Delta cells (-0.34/-0.61) do not reproduce from this formula on "
        "inputs matching every sibling exactly (formula-faithful: -0.33/-0.65) — a vendor "
        "export artifact; the pinned formula wins.",
    ),
    Row(
        "float_ratio",
        "Float Ratio™",
        "AVERAGE(TotalFloat/RemainingDuration)",
        MATCH,
        "Verbatim Bible formula (ADR-0103).",
    ),
    Row(
        "float_ratio_aggregate",
        "CP - Float Ratio™",
        "AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)",
        VARIANT,
        "Ratio-of-means companion to Float Ratio. The Bible metric with this exact formula is "
        "critical-path-scoped ('CP - Float Ratio'); the tool applies it over the full Normal "
        "planned/in-progress population (ADR-0103).",
    ),
    Row(
        "epi",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference-deck DAX adopted verbatim (ADR-0033); no 'EPI' metric in the Bible.",
    ),
    Row(
        "start_finish_ratio",
        "",
        "",
        NOT_IN_BIBLE,
        "Reference-deck DAX (ADR-0033); no 'Start-to-Finish Ratio' in the Bible.",
    ),
    Row(
        "elapsed_since_last_finish",
        "",
        "",
        NOT_IN_BIBLE,
        "Tool diagnostic (schedule elapsed since latest actual finish); no Bible formula.",
    ),
    Row("forecast_cpm", "", "", NOT_IN_BIBLE, "Tool forecasting (CPM forward pass)."),
    Row("forecast_rate", "", "", NOT_IN_BIBLE, "Tool forecasting (completion-rate extrapolation)."),
    Row(
        "forecast_earned_schedule",
        "",
        "",
        NOT_IN_BIBLE,
        "Tool forecasting (IEAC(t) = AT + (PD-ES)/SPI(t)); see the spi_t drift row.",
    ),
    # Derived metrics (Layer A, ADR-0133): standard secondary figures computed from the primary
    # metrics, not literal .aft library entries.
    Row(
        "dcma_pass_rate",
        "",
        "",
        NOT_IN_BIBLE,
        "Derived roll-up of the DCMA 14-Point Assessment (passing applicable checks / applicable); "
        "not a literal .aft metric (ADR-0133).",
    ),
    Row(
        "population_share",
        "",
        "",
        NOT_IN_BIBLE,
        "Derived normalisation (count / population) applied to a primary metric; standard ratio, "
        "not a literal .aft metric (ADR-0133).",
    ),
    # --- Performance Analysis Summary (the operator's reference workbook, ADR-0182) ---
    Row(
        "duration_ratio",
        "",
        "",
        NOT_IN_BIBLE,
        "DRM = ActualDuration / BaselineDuration per completed task, from the operator's "
        "PerformanceAnalysisSummary workbook (G5 'Duration Ratio (S-curve)'); the Bible has no "
        "formula-bearing per-task duration-growth metric (ADR-0182).",
    ),
    Row(
        "to_go_start_ratio",
        "",
        "",
        NOT_IN_BIBLE,
        "To-go starts / baseline's post-data-date remaining starts, from the operator's "
        "PerformanceAnalysisSummary workbook (G6 'To-Go-Starts vs. To-Go-Finishes' quad); "
        "no Bible counterpart (ADR-0182).",
    ),
    Row(
        "to_go_finish_ratio",
        "",
        "",
        NOT_IN_BIBLE,
        "To-go finishes / baseline's post-data-date remaining finishes — the finish twin of "
        "to_go_start_ratio, same workbook provenance; no Bible counterpart (ADR-0182).",
    ),
)


# --- the live Bible ----------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_afts() -> tuple[Path, ...]:
    """EVERY committed Bible snapshot — each one is drift-audited (ADR-0263)."""
    base = _REPO_ROOT / "00_REFERENCE_INTAKE"
    if not base.exists():
        return ()
    return tuple(sorted(base.rglob("*.aft")))


def _parse_aft(path: Path) -> dict[str, set[str]]:
    """Map each NASA metric Name → the set of Formula strings it appears with."""
    out: dict[str, set[str]] = {}
    for elem in ET.parse(path).getroot().iter():
        if elem.tag.split("}")[-1] != "Metric":
            continue
        name: str | None = None
        formula = ""
        for child in elem:
            tag = child.tag.split("}")[-1]
            if tag == "Name":
                name = (child.text or "").strip()
            elif tag == "Formula":
                formula = (child.text or "").strip()
        if name:
            out.setdefault(name, set()).add(formula)
    return out


def _norm(formula: str) -> str:
    return re.sub(r"\s+", "", formula or "").lower()


@pytest.fixture(scope="module")
def live_bibles() -> tuple[tuple[Path, dict[str, set[str]]], ...]:
    paths = _find_afts()
    if not paths:
        pytest.skip("NASA Acumen .aft reference not present under 00_REFERENCE_INTAKE/")
    return tuple((p, _parse_aft(p)) for p in paths)


# =====================================================================================
# Tests that DO NOT need the Bible on disk (always run, incl. CI).
# =====================================================================================
def test_audit_covers_every_documented_metric() -> None:
    """Every metric in help.py must have exactly one audit row (and vice-versa)."""
    audited = [r.tool_id for r in AUDIT]
    assert len(audited) == len(set(audited)), "duplicate tool_id in AUDIT"
    assert set(audited) == set(METRIC_DICTIONARY), (
        "AUDIT and help.py are out of sync — every documented metric must be classified "
        "against the NASA Bible.\n"
        f"  only in help.py: {sorted(set(METRIC_DICTIONARY) - set(audited))}\n"
        f"  only in AUDIT:   {sorted(set(audited) - set(METRIC_DICTIONARY))}"
    )


def test_verdicts_are_valid_and_internally_consistent() -> None:
    for r in AUDIT:
        assert r.verdict in _VERDICTS, f"{r.tool_id}: bad verdict {r.verdict!r}"
        if r.verdict in _HAS_FORMULA:
            assert r.nasa_name, f"{r.tool_id}: {r.verdict} must name a NASA metric"
            assert r.nasa_formula, f"{r.tool_id}: {r.verdict} must pin a NASA formula"
        else:  # NOT_IN_BIBLE
            assert not r.nasa_formula, f"{r.tool_id}: not_in_bible must not pin a formula"
            assert r.note, f"{r.tool_id}: not_in_bible must record provenance in the note"


def test_definitional_drift_is_documented_in_an_adr() -> None:
    """Each real definitional difference must point at the ADR that records it."""
    for r in AUDIT:
        if r.verdict == DRIFT:
            assert "ADR-0110" in r.note, f"{r.tool_id}: drift must reference ADR-0110"


def test_bible_sourced_metrics_map_to_a_bible_formula() -> None:
    """Any metric whose help.py source cites the NASA Bible must map to a Bible formula."""
    by_id = {r.tool_id: r for r in AUDIT}
    for mid, doc in METRIC_DICTIONARY.items():
        cites_bible = "Bible" in doc.source or "NASA Acumen metric library" in doc.source
        if cites_bible:
            row = by_id[mid]
            assert row.verdict in _HAS_FORMULA, (
                f"{mid} cites the NASA Bible as its source but is classified {row.verdict!r} "
                "(must map to a verbatim Bible formula)."
            )


# =====================================================================================
# Test that DOES need the Bible on disk (skips when absent — like the .mpp skips).
# =====================================================================================
def test_pinned_nasa_formulas_match_every_live_bible(
    live_bibles: tuple[tuple[Path, dict[str, set[str]]], ...],
) -> None:
    """The pinned NASA formulas must still match EVERY committed ``.aft`` (Bible-drift guard —
    a snapshot whose formula moved must fail loudly, never sit unaudited)."""
    mismatches: list[str] = []
    for path, live_bible in live_bibles:
        label = path.name
        for r in AUDIT:
            if r.verdict not in _HAS_FORMULA:
                continue
            if r.nasa_name not in live_bible:
                mismatches.append(f"{r.tool_id}: NASA metric {r.nasa_name!r} not found in {label}")
                continue
            live = {_norm(f) for f in live_bible[r.nasa_name]}
            if _norm(r.nasa_formula) not in live:
                mismatches.append(
                    f"{r.tool_id}: pinned formula for {r.nasa_name!r} no longer matches "
                    f"{label}.\n    pinned: {_norm(r.nasa_formula)}\n    live:   {sorted(live)}"
                )
    assert not mismatches, "Bible drift / mapping errors:\n" + "\n".join(mismatches)
