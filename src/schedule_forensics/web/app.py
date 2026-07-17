"""Local-only FastAPI web app — the dark, NASA-themed forensic dashboard (M13, §6.A).

Runs entirely on the local machine (binds 127.0.0.1 only): upload up to twenty schedules,
see each one's DCMA audit, Acumen §A/§C metrics, cited risk/opportunity/concern findings
and AI narrative, compare two versions (manipulation trends + Net Finish Impact), manage the
local AI model + classification (with the persistent CUI banner), browse the in-tool metric
dictionary, and wipe the session. No schedule content is ever logged (paths/counts only —
CUI), and the AI never leaves the box (`ai.route_backend` fail-closed). Interactive
Power-BI-style visuals are layered on at M14; M13 is the shell + server-rendered views.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import html
import importlib.metadata
import itertools
import json
import logging
import math
import re
import tempfile
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar, cast
from urllib.parse import quote, urlparse

import uvicorn
from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Template

from schedule_forensics.ai import (
    AIBackend,
    AIConfig,
    Classification,
    NullBackend,
    OllamaBackend,
    OpenAICompatBackend,
    banner_for,
    reattach,
    route_backend,
)
from schedule_forensics.ai.brief import DiagnosticBrief, brief_blocks, build_brief
from schedule_forensics.ai.briefing import (
    BriefingSection,
    ExecutiveBriefing,
    briefing_blocks,
    build_briefing,
)
from schedule_forensics.ai.citations import CitedStatement, Narrative, preserves_figures
from schedule_forensics.ai.driving_facts import driving_path_facts, driving_path_summary
from schedule_forensics.ai.narrative import build_narrative, clean_polish, polish_prompt
from schedule_forensics.ai.ollama_process import OllamaLauncher
from schedule_forensics.ai.qa import (
    answer_question,
    build_fact_sheet,
    build_workbook_fact_sheet,
    figure_agreement,
    manipulation_forensics_facts,
)
from schedule_forensics.engine import (
    analyze_floats,
    audit_schedule,
    compute_cpm,
    compute_driving_slack,
    recommend,
)
from schedule_forensics.engine.bow_wave import BowWave, compute_bow_wave
from schedule_forensics.engine.cache import content_hash, get_default_cache
from schedule_forensics.engine.change_effects import ChangeEffect, compute_change_effects
from schedule_forensics.engine.cpm import (
    CPMError,
    CPMResult,
    datetime_to_offset,
    off_project_calendars,
    offset_to_datetime,
)
from schedule_forensics.engine.dcma_audit import AuditCheck, Citation, ScheduleAudit
from schedule_forensics.engine.diff import diff_versions
from schedule_forensics.engine.driving_path import (
    DrivingPathEvolution,
    DrivingPathSnapshot,
    compute_driving_path_evolution,
)
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    PathDirection,
    PathTier,
    date_basis,
)
from schedule_forensics.engine.forecast import (
    CarnacSummary,
    ForecastSet,
    compute_carnac_summary,
    compute_finish_forecasts,
    compute_group_rollup,
)
from schedule_forensics.engine.grouping import (
    MAX_FIELDS,
    Criterion,
    available_fields,
    available_fields_union,
    distinct_values,
    field_value,
    filter_schedule,
    filter_to_uids,
    group_values,
    select,
    with_ancestors,
)
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.margin_dashboard import (
    GOLD_RULE_DAYS_PER_YEAR,
    MarginDashboard,
    MarginMonth,
    compute_margin_dashboard,
)
from schedule_forensics.engine.margin_guideline import (
    DEFAULT_CORRECTIVE_PCT,
    DEFAULT_WATCH_PCT,
    FIG_5_30_DEFAULT_RATES,
    FIG_5_30_ROWS,
    MONTH_WORK_DAYS,
    BandPoint,
    GuidelineBandConfig,
    band_position,
    expected_margin_band,
    margin_risk_read,
)
from schedule_forensics.engine.memory import (
    DEFAULT_WARN_BYTES,
    estimate_resident_bytes,
    format_bytes,
)
from schedule_forensics.engine.metric_catalog import (
    catalog_entries,
    catalog_families,
    evaluate_catalog,
)
from schedule_forensics.engine.metrics import (
    RibbonMetrics,
    WBSGroup,
    compute_activity_makeup,
    compute_baseline_compliance,
    compute_bei,
    compute_bri,
    compute_completion_performance,
    compute_constraint_distribution,
    compute_dcma14,
    compute_fei,
    compute_float_bands,
    compute_float_sums,
    compute_net_finish_impact,
    compute_ribbon,
    compute_schedule_quality,
    compute_wbs_breakdown,
    ribbon_offender_map,
)
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    effective_total_float,
    is_effective_critical,
    non_summary,
    percent,
)
from schedule_forensics.engine.metrics.cei import compute_cei
from schedule_forensics.engine.metrics.constraint_health import compute_constraint_health
from schedule_forensics.engine.metrics.evm import (
    ActivityVariance,
    compute_evm_indices,
    compute_schedule_variance,
)
from schedule_forensics.engine.metrics.field_forecast import compute_field_forecast
from schedule_forensics.engine.metrics.float_erosion import compute_float_erosion
from schedule_forensics.engine.metrics.float_ratio import compute_float_ratio
from schedule_forensics.engine.metrics.health_extra import compute_health_checks
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.engine.metrics.margin import (
    MarginCandidate,
    compute_margin,
    compute_margin_trend,
    margin_candidates,
)
from schedule_forensics.engine.metrics.performance_summary import (
    activity_flow,
    duration_ratio,
    to_go_snapshot,
    work_to_go_census,
    workoff_burden,
)
from schedule_forensics.engine.metrics.sem import compute_sem
from schedule_forensics.engine.metrics.vertical_integration import compute_vertical_integration
from schedule_forensics.engine.month_curves import MonthCurves, compute_month_curves
from schedule_forensics.engine.msp_field_resolver import FieldValue
from schedule_forensics.engine.msp_filters import (
    coerce_prompt_answers,
    required_prompts,
)
from schedule_forensics.engine.msp_filters import select as _select_saved
from schedule_forensics.engine.path_counterfactual import (
    PathCounterfactual,
    compute_path_counterfactual,
)
from schedule_forensics.engine.path_evolution import PathEvolution, compute_path_evolution
from schedule_forensics.engine.path_trace import subschedule_to_target, topo_order
from schedule_forensics.engine.projects import (
    IngestRecord,
    Project,
    group_into_projects,
)
from schedule_forensics.engine.recommendations import (
    SEVERITY_ORDER,
    Category,
    Finding,
    Severity,
)
from schedule_forensics.engine.resources import ResourceLoading, compute_resource_loading
from schedule_forensics.engine.s_curve import SCurve, compute_s_curve
from schedule_forensics.engine.saved_grouping import (
    find_saved_filter,
    find_saved_group,
    group_by_clauses,
    saved_filters_union,
    saved_groups_union,
)
from schedule_forensics.engine.scorecards import (
    Scorecard,
    compute_scorecards,
    reserve_recommendation,
)
from schedule_forensics.engine.sra import (
    ActivityRisk,
    OATSensitivity,
    RiskEvent,
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
    SRAResult,
    SSIResult,
    SSIRiskStat,
    compute_oat_sensitivity,
    compute_sra,
    compute_sra_ssi,
    deterministic_margin_bounds,
    factor_to_bc_wc,
)
from schedule_forensics.engine.sra_conclusions import (
    conclusions_as_dicts,
    conclusions_from_sra,
    conclusions_from_ssi,
)
from schedule_forensics.engine.summary import VersionSummary, compute_summary
from schedule_forensics.engine.trend import (
    compute_cei_trend,
    compute_float_ratio_trend,
    compute_hmi_trend,
    compute_quality_trend,
    order_versions,
)
from schedule_forensics.importers import (
    ImporterError,
    decode_xer_bytes,
    load_schedule,
    parse_json,
    parse_json_text,
    parse_mspdi_text,
    parse_xer_text,
    supported_extensions,
    to_json_text,
)
from schedule_forensics.importers.mpp_mpxj import mpxj_batch_session
from schedule_forensics.logging_redaction import configure_logging
from schedule_forensics.model.saved_view import Criterion as SavedCriterion
from schedule_forensics.model.saved_view import Operand as SavedOperand
from schedule_forensics.model.saved_view import SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.net_guard import (
    assert_local_only,
    is_local_http_endpoint,
    is_loopback_host,
)
from schedule_forensics.reports.docx import (
    Block,
    Chart,
    ChartText,
    DocTable,
    Heading,
    Paragraph,
    render_document,
    render_docx,
)
from schedule_forensics.reports.tables import (
    Cell,
    Table,
    TableSet,
    activities_table,
    bow_wave_tables,
    carnac_table,
    dcma_table,
    driving_table,
    findings_table,
    forecast_tables,
    metric_results_table,
    month_curves_tables,
    path_evolution_tables,
    schedule_summary_table,
    trend_tables,
    wbs_breakdown_tables,
)
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx
from schedule_forensics.web import i18n
from schedule_forensics.web.help import (
    METRIC_DICTIONARY,
    field_help_payload,
    field_or_metric_doc,
    metric_doc,
    reliability_dimension,
)
from schedule_forensics.web.offload import (
    OFFLOAD_TASK_THRESHOLD,
    run_maybe_offloaded,
    shutdown_offload,
)

logger = logging.getLogger("schedule_forensics.web")

#: Locally-vendored static assets (CSS/JS) — served from /static; no CDN, no external fetch.
_STATIC_DIR = Path(__file__).parent / "static"
try:  # the installed package version, used to cache-bust static asset URLs on upgrade
    _ASSET_VERSION = importlib.metadata.version("schedule-forensics")
except importlib.metadata.PackageNotFoundError:  # running from a raw source tree
    _ASSET_VERSION = "dev"
#: /static/<asset> not already carrying a query — rewritten to /static/<asset>?v=<version> at the
#: page-render boundary. Deployed installs serve a FIXED port, so the browser cache origin
#: persists across upgrades; without a versioned URL a browser may serve a heuristically-cached
#: stale JS/CSS (StaticFiles sends no Cache-Control) and an upgraded tool keeps OLD behavior.
_STATIC_REF = re.compile(r"(/static/[A-Za-z0-9_.\-]+)(?![A-Za-z0-9_.\-?])")


def _bust_static(html_text: str) -> str:
    """Append ``?v=<package version>`` to every static asset URL in a rendered page."""
    return _STATIC_REF.sub(rf"\1?v={_ASSET_VERSION}", html_text)


#: Bundled, non-CUI sample schedule for the "Load example" button.
_EXAMPLE = Path(__file__).parent / "examples" / "house_build.json"
#: File types the open/import picker accepts.
_ACCEPT = ".json,.xml,.mspdi,.xer,.mpp,.mpt"
#: Decimal places for the per-task remaining-days values shared with the client SRA derive math
#: (``window.SF_REMAIN_DAYS``). The server and client MUST round each per-task value at the SAME
#: precision before averaging, or their derived days↔% magnitudes diverge for sub-day tasks
#: (audit M5). 6 dp keeps sub-day tasks from collapsing to 0 while still matching exactly.
_REMAIN_DAYS_DP = 6

#: Per-file upload cap (bytes). Local operator files; largest real exports are well under this.
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024

_LAYOUT = Template(
    """<!doctype html><html lang="{{ lang }}"><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{ title }} — POLARIS</title>
<link rel=icon href="/static/favicon.ico">
<script>window.SF_LANG={{ lang_json }};window.SF_I18N={{ catalog_json }};</script>
<script src="/static/theme.js"></script>
<script src="/static/checklist.js"></script>
<script src="/static/gantt.js"></script>
<script src="/static/timescale.js"></script>
<script src="/static/colresize.js"></script>
<script src="/static/taskinfo.js"></script>
<script src="/static/persist.js"></script>
<script src="/static/a11y.js"></script>
<script src="/static/translate.js"></script>
<script src="/static/drilldown.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css"><link rel=stylesheet href="/static/hud.css"><link rel=stylesheet href="/static/sf-themes.css">
<style>
/* Density + containment overrides (operator request, ADR-0150): tighter spacing everywhere,
   and grid/table containment so wide tables scroll inside their card instead of overlapping
   the neighbouring column (the Executive Briefing 3-column blowout). */
.panel{padding:10px 14px;margin:10px 0}
.panel h2{margin:.15em 0 .35em}
.panel h3{margin:.5em 0 .25em}
td,th{padding:3px 8px}
p{margin:.4em 0}
p.muted{margin:.3em 0}
.brief-card,.brief-cards .panel,.dash-card,.stat-card{min-width:0}
.brief-card{overflow-x:auto}
.brief-card table{width:100%}
/* Never let table auto-layout crush columns into vertical one-character text: headers stay on
   one line, data cells wrap at word boundaries only, and a too-wide table scrolls inside its
   card (overflow-x above) instead of squeezing its columns. */
.brief-card th{white-space:nowrap}
.brief-card td{overflow-wrap:break-word;word-break:normal}
.cite{overflow-wrap:break-word}
</style></head><body>
<div class="cui-banner {{ cui_class }}" data-no-i18n>{{ cui_text }}</div>
<details class=compliance-drawer id=complianceDrawer>
<summary>Handling &amp; export-control notice — click to review (CUI / ITAR / EAR)</summary>
<div class=compliance-body>
<h3>Controlled Unclassified Information (CUI)</h3>
<p>Treat every loaded schedule and every derived metric on these pages as CUI unless the project
is explicitly marked UNCLASSIFIED in AI Settings. Handle per 32 CFR Part 2002 and your
organization's CUI program: store on approved systems only, share only with a lawful government
purpose, and destroy per records schedules. This tool enforces the technical side — it binds
127.0.0.1 only and no schedule content ever leaves this machine.</p>
<h3>Export control (ITAR / EAR)</h3>
<p>WARNING — Schedules for defense or space programs may contain technical data subject to the
International Traffic in Arms Regulations (ITAR, 22 CFR 120&ndash;130) or the Export
Administration Regulations (EAR, 15 CFR 730&ndash;774). Do not export, release, or disclose such
data to foreign persons, in the U.S. or abroad, without proper authorization. Violations carry
severe criminal and civil penalties.</p>
<h3>Your responsibility</h3>
<p>The markings above reflect the session's declared classification &mdash; not a review of your
data. You remain responsible for confirming the actual sensitivity, markings, and distribution
statements of every file you load and every report you export.</p>
</div>
</details>
<header><h1 class=brand data-no-i18n
aria-label="POLARIS — Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules"
title="POLARIS — Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules">
<!-- POLARIS wordmark (ADR-0175): hand-set NASA-worm-style letterforms drawn as SVG strokes —
     no webfont, fully inline, so the air-gap CSP stays intact and it renders identically
     on every machine. Uniform stroke, rounded joins, crossbar-less A, trailing north star. -->
<svg class=brand-mark viewBox="0 0 344 72" aria-hidden=true focusable=false>
<g class=brand-strokes fill=none stroke-width=13 stroke-linecap=round stroke-linejoin=round>
<path d="M6 62 V10 H20 A13 13 0 0 1 20 36 H6"/>
<rect x="54" y="10" width="28" height="52" rx="14"/>
<path d="M102 10 V62 H128"/>
<path d="M150 62 V28 A14 14 0 0 1 178 28 V62"/>
<path d="M198 62 V10 H212 A13 13 0 0 1 212 36 H198 M212 36 L226 62"/>
<path d="M248 10 V62"/>
<path d="M299 12 H285 A12 12 0 0 0 285 36 H287 A12 12 0 0 1 287 60 H273"/>
</g>
<path class=brand-star d="M328 6 Q329.5 16.5 340 18 Q329.5 19.5 328 30 Q326.5 19.5 316 18 Q326.5 16.5 328 6 Z"/>
</svg>
<span class=brand-sub>Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules</span>
</h1>
<input type=checkbox id=navToggle class=nav-toggle aria-label="Toggle navigation menu">
<label for=navToggle class=nav-burger title="Menu" data-no-i18n><span aria-hidden=true>&#9776;</span></label>
{{ nav }}
<span class="nasa-globe" data-no-i18n title="Local AI status: the globe spins up while the model is generating"><canvas width="96" height="96" aria-hidden="true"></canvas></span>
</header>
<main>{{ banner }}{{ body }}</main><script src="/static/heartbeat.js"></script>
<script src="/static/chartframe.js"></script>
<script src="/static/target.js"></script>
<script src="/static/globe.js"></script>
<script src="/static/sysmon.js"></script>
<script src="/static/hints.js"></script>
<script src="/static/vizhints.js"></script>
<script src="/static/story.js"></script>
<div class="cui-banner {{ cui_class }} bottom" data-no-i18n>{{ cui_text }}</div>
</body></html>"""
)


@dataclass(frozen=True)
class _Flash:
    """A one-shot import result message shown on the next dashboard render."""

    accepted: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    #: non-blocking grouping notices (v4): folders with disagreeing internal titles, files grouped
    #: by filename needing attention, or a data-date tie broken by last-modified time.
    notices: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Analysis:
    """Everything a report view needs, computed once from a single CPM pass per schedule.

    Building this runs the network just once and threads that CPM through the audit, the
    baseline-compliance panel, the findings, the narrative, and the activity grid — instead
    of each view recomputing the CPM several times over.
    """

    cpm: CPMResult
    audit: ScheduleAudit
    compliance: dict[str, MetricResult]
    float_bands: dict[str, MetricResult]
    completion: dict[str, MetricResult]
    findings: tuple[Finding, ...]
    narrative: Narrative
    activity_rows: list[dict[str, object]]


def _compute_analysis(sch: Schedule) -> _Analysis:
    """Run the engine once for ``sch`` (a single ``compute_cpm``, reused everywhere)."""
    cpm = compute_cpm(sch)
    return _Analysis(
        cpm=cpm,
        audit=audit_schedule(sch, cpm),
        compliance=compute_baseline_compliance(sch, cpm),
        float_bands=compute_float_bands(sch, cpm),
        completion=compute_completion_performance(sch),
        findings=recommend(sch, current_cpm=cpm),
        # the cached narrative is always the deterministic (NullBackend) one; a real
        # session-selected backend rephrases it per request via _polished_narrative
        # (citations re-attached, figures re-verified — see ai.citations.reattach).
        narrative=build_narrative(sch, current_cpm=cpm),
        activity_rows=_activity_rows(sch, cpm),
    )


@dataclass(frozen=True)
class UnifiedRisk:
    """One operator-entered risk/opportunity that feeds BOTH SRA models.

    The operator enters a risk ONCE. It carries two magnitudes for the same event: an additive
    ``impact_days`` (the SSI model) and a multiplicative ``impact_pct`` uplift (the legacy model;
    ``20`` => x1.20). Typing one auto-derives the other from the affected tasks' remaining duration
    (client-side ``sra_risk.js``; the server mirrors it for the JS-off / load path). A field the
    operator set explicitly is *locked* (``days_locked`` / ``pct_locked``) and used verbatim for that
    model; the unlocked one is the derived value. At the web boundary this record is turned into the
    engine's frozen :class:`ScheduleRisk` (from ``impact_days``) and :class:`RiskEvent` (from
    ``impact_pct``) — the engine and its byte-frozen parity tests are untouched.
    """

    id: str
    name: str
    probability: float  # 0..1
    affected: tuple[int, ...]
    impact_days: float  # additive working days (>=0 risk, <0 opportunity) — the SSI magnitude
    impact_pct: (
        float  # multiplicative % uplift (20 => x1.20; <0 opportunity) -- the legacy magnitude
    )
    days_locked: bool = False  # the operator set days explicitly → use verbatim for the SSI model
    pct_locked: bool = False  # the operator set % explicitly → use verbatim for the legacy model
    consequence_rating: int | None = None  # 1..5 for the 5x5 matrix; None auto-derives from days


_V = TypeVar("_V")

#: Max full analyses / polished narratives kept resident before the least-recently-used is evicted
#: (audit #4). A full ``_Analysis`` is heavy (~6 KiB/task; a portfolio of 100 large versions would
#: otherwise pin >1 GiB); the summary tier (``summaries``) carries portfolio scale, so this cap
#: applies only to the expensive detailed caches. Generous enough that any realistic multi-version
#: comparison never evicts — an evicted entry simply recomputes byte-identically, so the cap only
#: trades memory for occasional recompute and can never change a computed number.
_ANALYSIS_CACHE_MAX = 48


class _LRUCache(OrderedDict[str, _V]):
    """A count-bounded, access-ordered LRU over string keys (std-lib only — no ``cachetools``).

    Used ONLY for value caches whose entries recompute IDENTICALLY on a miss (the detailed
    ``analyses`` / ``polished`` caches), so bounding memory never changes any computed output.
    Plain dict operations still work (``__setitem__`` / ``in`` / ``clear`` / ``== {}``, which the
    filter/wipe paths and tests rely on); production reads/writes go through :meth:`get_lru` /
    :meth:`put` for the LRU discipline (most-recently-used survives, least-recently-used evicts).
    """

    def __init__(self, maxsize: int) -> None:
        super().__init__()
        self._maxsize = maxsize

    def get_lru(self, key: str) -> _V | None:
        """Return the cached value and mark it most-recently-used, or ``None`` on a miss."""
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key: str, value: _V) -> None:
        """Insert/refresh ``key`` as most-recently-used, evicting the LRU entry over the cap."""
        self[key] = value
        self.move_to_end(key)
        while len(self) > self._maxsize:
            self.popitem(last=False)


@dataclass
class SessionState:
    """In-memory, local-only session: loaded schedules (by name) + AI config. No disk persistence."""

    schedules: dict[str, Schedule] = field(default_factory=dict)
    # ingestion origin per loaded key (v4 grouped ingestion): key -> (top folder name or None for a
    # loose file, browser last-modified epoch-ms or None). Feeds engine.projects grouping; the
    # Schedule itself carries the real document Title (``project_title``). Cleared on wipe.
    file_meta: dict[str, tuple[str | None, float | None]] = field(default_factory=dict)
    ai_config: AIConfig = field(default_factory=AIConfig)
    flash: _Flash | None = None  # transient import feedback, consumed on the next home() render
    # per-schedule analysis cache (key -> (schedule, analysis)); identity-checked so a re-upload
    # under the same key recomputes. Bounded by the loaded-schedule count; cleared on wipe.
    analyses: _LRUCache[tuple[Schedule, _Analysis]] = field(
        default_factory=lambda: _LRUCache(_ANALYSIS_CACHE_MAX)
    )
    # v4 Feature 2 lazy summary tier: the small per-version rollup (finish/margin/DCMA) the Portfolio
    # needs, cached in-memory (key -> (scoped schedule, summary)) and — for uploads, keyed by the raw
    # file content hash below — persisted in the SQLite cache so a portfolio of thousands renders from
    # summaries, not a fresh CPM per row. Identity-checked and scope-aware like ``analyses``.
    summaries: dict[str, tuple[Schedule, VersionSummary]] = field(default_factory=dict)
    # key -> raw uploaded-file content hash (the SQLite summary/parse cache key). Only set for the
    # /upload path; a schedule loaded another way simply has no on-disk summary (in-memory only).
    content_hashes: dict[str, str] = field(default_factory=dict)
    # F3a/3b confirmed schedule-margin overlay: key -> the operator-confirmed margin-task UniqueIDs
    # for that loaded version (set on the analysis-page margin panel via POST /margin/confirm). When a
    # key has an entry, every margin computation for it uses that set instead of the name-based default
    # (is_margin_task); absent => name-based. Cleared on wipe. Margin-task UIDs are stable across a
    # project's versions, so the cross-version dashboard/trend use the union (confirmed_margin_union).
    margin_overlay: dict[str, frozenset[int]] = field(default_factory=dict)
    # v4 Feature 2: the loaded-schedule RAM estimate above which an ingest WARNS (never blocks). The
    # tool keeps parsed schedules resident for instant comparative analysis; on a big folder of
    # thousands this can be many GB. Operator-configurable (POST /session/ram-threshold).
    ram_warn_bytes: int = DEFAULT_WARN_BYTES
    # optional session-wide target activity: every view that can focus on a UniqueID
    # (report trace, trend focus, compare movement) defaults to this when set.
    target_uid: int | None = None
    # F3c: operator-settable NASA Gold-Rule margin-requirement rate (work-days per program year) the
    # dashboard measures effective margin against. 30/yr (the Schedule Management Handbook default) is
    # the initial value; set via GET /margin?rate=. The burn-down requirement line, the per-version
    # "NASA rqmt" column, the trigger flag, and the Excel/Word export all follow this one rate.
    margin_rate: float = GOLD_RULE_DAYS_PER_YEAR
    # F3c-fuller (ADR-0254): the operator's Fig 5-30 guideline band — four ISO phase-boundary
    # dates (Confirmation Review, I&T start, delivery to launch site, launch; program facts the
    # engine cannot derive — None until entered, the band simply absent) + the three (low, high)
    # wd/yr rates prefilled from the cited Fig 5-30 defaults. Set via POST /margin/band.
    margin_band_dates: tuple[str, str, str, str] | None = None
    margin_band_rates: tuple[tuple[float, float], ...] = FIG_5_30_DEFAULT_RATES
    # F3c-fuller: the §7.3.3.2.3 sufficiency-read percentile thresholds (Watch, Corrective
    # Action) — the handbook's EXAMPLE values 70/50 prefilled, operator-editable (program-set per
    # the SMP, §7.3.3.1.6 Thresholds).
    margin_risk_pcts: tuple[float, float] = (DEFAULT_WATCH_PCT, DEFAULT_CORRECTIVE_PCT)
    # v4 F4 (ADR-0255): the operator's selected audience role — a curated ENTRY POINT only
    # (home "Start here" strip, nav highlight, post-upload landing). None = "Show everything",
    # byte-identical to the pre-F4 behavior. Never hides a page, never touches a number.
    role: str | None = None
    # UI/AI display language (ADR-0099): "en" (source) or "es". Drives the layout's lang attribute
    # and the client translation pass; AI fallback translations are memoised in ``translations``.
    language: str = "en"
    # AI-fallback translation cache: (lang, source text) -> translated, so a string is translated
    # at most once per session (the catalog covers fixed terms; this covers dynamic content).
    translations: dict[tuple[str, str], str] = field(default_factory=dict)
    # the routed AI backend, cached briefly (config, probed-at, backend) so report renders
    # don't re-probe a down Ollama every time; reset on a settings change / TTL lapse.
    backend_cache: tuple[AIConfig, float, AIBackend] | None = None
    # per-schedule narrative as polished by a real (non-null) backend:
    # key -> (schedule identity, "backend/model" stamp, narrative). Cleared on wipe.
    polished: _LRUCache[tuple[Schedule, str, Narrative]] = field(
        default_factory=lambda: _LRUCache(_ANALYSIS_CACHE_MAX)
    )
    # the cross-check second model, cached like backend_cache (None = off/unreachable).
    second_cache: tuple[AIConfig, float, AIBackend | None] | None = None
    # session-wide group/filter (ADR-0104): when set, EVERY metric on EVERY page — and every loaded
    # file — is scoped to the tasks matching ALL criteria. Empty tuple = no filter (full schedules).
    active_filter: tuple[Criterion, ...] = ()
    # identity-stable cache of filtered schedules, id(original) -> (original, filtered), so a scoped
    # schedule keeps one identity across a request and the analysis cache below still hits. Cleared
    # whenever the filter changes (set_filter) or the session is wiped.
    _scoped: dict[int, tuple[Schedule, Schedule]] = field(default_factory=dict)
    # --- feature #10: session-wide SAVED (MS Project) filters & groups + HIGHLIGHT mode ----------
    # The session-wide SAVED FILTER — a faithful MS Project criteria tree (the reproduction
    # counterpart of the flat, field-based `active_filter` above). MUTUALLY EXCLUSIVE with it:
    # setting one clears the other (two ways to name one session scope). None = no saved filter.
    active_saved_filter: SavedFilter | None = None
    # Operator answers for an interactive saved filter ("Date Range..." → 2 prompts), keyed by the
    # prompt label; passed straight to the evaluator. Empty until the operator answers.
    saved_filter_prompts: dict[str, FieldValue] = field(default_factory=dict)
    # Filter MODE, applying to BOTH filter sources. "reduce" = today's behaviour (drop non-matching
    # tasks). "highlight" = keep the FULL population and only MARK the matches — scope() does not
    # reduce; the match set is carried to grids/gantt via highlight_uids().
    filter_mode: str = "reduce"
    # The session-wide SAVED GROUP (multi-clause) — ordering/banding only, never a population change.
    # None = file order.
    active_saved_group: SavedGroup | None = None
    # match-set memo, id(original) -> (original, matched-UIDs | None). None value = "no filter" for
    # that object. Same identity-stability contract as `_scoped`; cleared by every filter setter +
    # wipe (grouping does NOT clear it — grouping never changes the match set).
    _matched: dict[int, tuple[Schedule, frozenset[int] | None]] = field(default_factory=dict)
    # SRA manual inputs (ADR-0106, manual path). The global triangular multipliers applied to every
    # activity's REMAINING duration when no per-activity override is set (defaults = the industry
    # "Quick Risk" screening values, Deltek Acumen "Realistic" 90/100/110).
    sra_low: float = 0.9
    sra_ml: float = 1.0
    sra_high: float = 1.10
    # per-activity 3-point overrides: uid -> (optimistic, most_likely, pessimistic) WORKING MINUTES.
    sra_overrides: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    # UNIFIED risk register (entered once): each risk carries BOTH an additive-days (SSI) and a
    # multiplicative-% (legacy) magnitude + per-model lock flags. At the compute boundary it derives
    # the engine's ScheduleRisk (additive) and RiskEvent (multiplicative). Set via POST /sra/risk-register.
    sra_risks: list[UnifiedRisk] = field(default_factory=list)
    # monotonic id counter so each registered risk keeps a stable, unique id across removals.
    sra_risk_seq: int = 0
    # which loaded file the SRA runs against (operator choice). None / unknown key => the latest
    # solvable version (the historical default). Set via GET /sra?file=<key>.
    sra_file: str | None = None
    # --- SSI Schedule Risk & Opportunity Analysis inputs (ADR-0123) ---
    # the focus event whose finish the SSI run/OAT report (SSI "Flag for Analysis"); None => project.
    sra_focus_uid: int | None = None
    # the Risk Factors table: (factor 1..5, % subtract for Best Case, % add for Worst Case).
    sra_factor_rows: tuple[tuple[int, float, float], ...] = field(
        default_factory=lambda: RiskFactorTable().rows
    )
    sra_factors: dict[int, int] = field(default_factory=dict)  # uid -> Risk Ranking Factor 1..5
    sra_bcwc: dict[int, tuple[int, int]] = field(default_factory=dict)  # uid -> (BC, WC) minutes
    # (the SSI + legacy registers are unified into `sra_risks` above — both magnitudes per risk)
    sra_occurrence_mode: str = "random_each"  # "random_each" | "exact_overall"
    sra_use_risk_register: bool = True
    sra_correlation: float = 0.0  # 0 = independent; 0.3-0.5 typical blanket correlation
    #: one-shot feedback from an Excel round-trip import (ADR-0211), rendered once on /sra
    sra_import_msg: str | None = None
    # Routes are sync `def` (Starlette threadpool = real concurrency); this reentrant lock makes
    # the scope/analysis caches and the filter/wipe invalidations atomic, so a render can never
    # iterate a dict another request is clearing (QC audit D18 — live-reproduced KeyError on
    # /trend under concurrent filter+render). Single-operator tool: contention is negligible.
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def _match_uids(self, sch: Schedule) -> frozenset[int] | None:
        """The UIDs of ``sch`` matching the active filter — the faithful saved-filter tree OR the
        flat field criteria — or ``None`` when no filter is set (⇒ every task). Memoised by the
        original's identity (the tree walk can be called several times per request); invalidated by
        every filter setter and by wipe. Callers hold ``self._lock``."""
        cached = self._matched.get(id(sch))
        if cached is not None and cached[0] is sch:
            return cached[1]
        matched: frozenset[int] | None
        if self.active_saved_filter is not None:
            matched = frozenset(
                _select_saved(sch, self.active_saved_filter, self.saved_filter_prompts)
            )
        elif self.active_filter:
            matched = frozenset(select(sch, self.active_filter))
        else:
            matched = None
        self._matched[id(sch)] = (sch, matched)
        return matched

    def scope(self, sch: Schedule) -> Schedule:
        """``sch`` reduced to the active filter AND truncated to the target endpoint — the single
        point every page funnels through.

        Returns ``sch`` unchanged when nothing narrows the population. A filter narrows only in
        **reduce** mode: in **highlight** mode the matches are merely marked (see
        :meth:`highlight_uids`), so ``scope()`` leaves the population whole and only the Target UID
        can still truncate it. In reduce mode the matching tasks (plus their summary ancestors when
        the saved filter asks to "show related summary rows") are kept, then — when a Target UID is
        set and present — the result is restricted to that activity plus everything that drives it
        (:func:`subschedule_to_target`). A version that does not contain the target keeps its
        (filtered) population. Memoised by the original's identity so repeated calls in one request
        share one object (keeping the per-key analysis cache valid); the memo resets on the filter/
        target setters and wipe."""
        with self._lock:
            matched = self._match_uids(sch)
            reducing = matched is not None and self.filter_mode == "reduce"
            if not reducing and self.target_uid is None:
                return sch  # nothing changes the population
            cached = self._scoped.get(id(sch))
            if cached is not None and cached[0] is sch:
                return cached[1]
            if reducing and matched is not None:
                kept = matched
                if self.active_saved_filter is not None and (
                    self.active_saved_filter.show_related_summary_rows
                ):
                    kept = with_ancestors(sch, kept)
                scoped = filter_to_uids(sch, kept)
            else:
                scoped = sch
            if self.target_uid is not None and any(
                t.unique_id == self.target_uid and not t.is_summary for t in scoped.tasks
            ):
                # target present in this version → truncate to it + its drivers; a version that
                # doesn't contain the target keeps its full (filtered) population.
                scoped = subschedule_to_target(scoped, self.target_uid)
            self._scoped[id(sch)] = (sch, scoped)
            return scoped

    def highlight_uids(self, sch: Schedule) -> frozenset[int] | None:
        """When a filter is active in **highlight** mode, the UIDs of ``sch``'s matching tasks (to
        shade rows / outline bars). ``None`` when no filter is active or the mode is ``reduce`` —
        reduce already dropped the non-matches, so there is nothing to mark."""
        with self._lock:
            if self.filter_mode != "highlight":
                return None
            return self._match_uids(sch)

    def _invalidate_scope(self) -> None:
        """Clear every scope-derived cache — the shared body of the filter setters + wipe."""
        self._scoped.clear()
        self._matched.clear()
        self.analyses.clear()
        self.summaries.clear()  # summaries are scope-aware too — recompute against the new scope
        self.polished.clear()

    def set_filter(self, criteria: Sequence[Criterion]) -> None:
        """Set (or clear, with ``()``) the session-wide FIELD filter and invalidate the scope/
        analysis caches. Clears any active saved filter (mutual exclusivity — one scope at a time)."""
        with self._lock:
            self.active_filter = tuple(criteria)
            self.active_saved_filter = None
            self.saved_filter_prompts = {}
            self._invalidate_scope()

    def set_saved_filter(
        self, saved: SavedFilter | None, prompts: dict[str, FieldValue] | None = None
    ) -> None:
        """Set (or clear) the session-wide SAVED (MS Project) filter. Clears any field filter (mutual
        exclusivity). ``prompts`` supplies the operator's answers for an interactive filter."""
        with self._lock:
            self.active_saved_filter = saved
            self.saved_filter_prompts = dict(prompts or {})
            if saved is not None:
                # mutual exclusivity applies only when actually SETTING a saved filter; clearing one
                # (saved is None) must not also drop an unrelated active field filter.
                self.active_filter = ()
            self._invalidate_scope()

    def set_filter_mode(self, mode: str) -> None:
        """Switch the filter MODE between ``reduce`` and ``highlight``. Reduce↔highlight changes the
        population, so the full scope cache is invalidated."""
        with self._lock:
            self.filter_mode = "highlight" if mode == "highlight" else "reduce"
            self._invalidate_scope()

    def set_saved_group(self, group: SavedGroup | None) -> None:
        """Set (or clear) the session-wide SAVED group. Grouping is ordering/banding only — it does
        NOT change any metric population, so it deliberately does not invalidate the analysis/summary
        caches (a regroup stays cheap)."""
        with self._lock:
            self.active_saved_group = group

    def set_target(self, uid: int | None) -> None:
        """Set (or clear) the session-wide Analysis Target and invalidate the scope/analysis caches
        so every metric, audit, and visual recomputes against the target's driving sub-network (or
        the full schedule again when cleared). The one global target also drives the SRA/SSI focus
        event (ADR-0196), so the header selector and the SRA focus never disagree; an analyst can
        still override the SRA focus in-panel afterward."""
        with self._lock:
            self.target_uid = uid
            self.sra_focus_uid = uid
            self._invalidate_scope()

    def set_margin_rate(self, rate: float) -> None:
        """Set the NASA Gold-Rule margin-requirement rate (work-days per program year) the margin
        dashboard measures against (F3c). Accepted only in a sane ``(0, 365]`` band; anything else is
        ignored, keeping the current rate (fail-soft — a bad query value never wipes the setting). The
        rate feeds only the freshly-computed requirement line / trigger, not the analysis or summary
        caches, so nothing needs invalidating."""
        with self._lock:
            if 0 < rate <= 365:
                self.margin_rate = rate

    def set_margin_band(
        self, dates: tuple[str, str, str, str] | None, rates: tuple[tuple[float, float], ...]
    ) -> None:
        """Set the operator's Fig 5-30 guideline band (F3c-fuller, ADR-0254) — fail-soft like
        ``set_margin_rate``: dates must be four strictly-increasing ISO dates (or None to clear),
        each rate ``0 < low <= high <= 365``; an invalid piece is IGNORED, keeping the current
        value (a bad form value never wipes the setting). No cache invalidation — the band feeds
        only the freshly-computed overlay, never the analysis/summary caches."""
        with self._lock:
            if dates is None:
                self.margin_band_dates = None
            else:
                try:
                    parsed = [dt.date.fromisoformat(s) for s in dates]
                except ValueError:
                    parsed = []
                if len(parsed) == 4 and all(b > a for a, b in itertools.pairwise(parsed)):
                    self.margin_band_dates = dates
            if len(rates) == 3 and all(0 < lo <= hi <= 365 for lo, hi in rates):
                self.margin_band_rates = rates

    def set_margin_risk_pcts(self, watch: float, corrective: float) -> None:
        """Set the §7.3.3.2.3 Watch / Corrective-Action percentile thresholds (fail-soft: must
        satisfy ``0 < corrective < watch < 100``, else the current values are kept)."""
        with self._lock:
            if 0 < corrective < watch < 100:
                self.margin_risk_pcts = (watch, corrective)

    def set_role(self, role: str | None) -> None:
        """Set (or clear) the audience role (v4 F4, ADR-0255). Fail-soft: an unknown role id is
        ignored, keeping the current selection. Pure wayfinding — no cache is invalidated because
        the role can never change a computed figure."""
        with self._lock:
            if role is None or role in _ROLE_BY_ID:
                self.role = role

    def confirmed_margin_union(self) -> frozenset[int] | None:
        """The union of every loaded version's operator-confirmed margin-task set, or ``None`` when no
        version carries a confirmed overlay (⇒ the name-based default). Margin-task UniqueIDs are
        stable across a project's versions, so a UID confirmed on any version is treated as margin
        wherever it appears in the cross-version burn-down / trend (the per-version panel still uses
        that key's own set). Once ANY overlay exists this returns a concrete frozenset — even the empty
        set (operator unchecked everything) — so the dashboard honors a deliberate zero, never silently
        reverting to name-based."""
        with self._lock:
            if not self.margin_overlay:
                return None
            union: set[int] = set()
            for uids in self.margin_overlay.values():
                union |= uids
            return frozenset(union)

    def ordered(self) -> list[Schedule]:
        """Loaded schedules **scoped to the active filter**, ordered by data date (oldest first).

        This is what the multi-version views that call engine functions directly (bow-wave, S-curve,
        month curves) iterate, so the filter reaches them too. Views that go through
        :meth:`analysis_for` pass the raw schedule from :meth:`ordered_versions` (it scopes)."""
        with self._lock:
            return [self.scope(s) for s in order_versions(list(self.schedules.values()))]

    def ordered_versions(self) -> list[tuple[str, Schedule]]:
        """(key, UNSCOPED schedule) pairs, oldest first. Callers either hand the schedule to
        :meth:`analysis_for` (which scopes it) or, for the filter UI, need the full field/value set —
        so this stays raw. Use :meth:`ordered` / :meth:`scope` when you need the filtered tasks."""
        with self._lock:
            by_obj = {id(s): k for k, s in self.schedules.items()}
            return [(by_obj[id(s)], s) for s in order_versions(list(self.schedules.values()))]

    def projects(self) -> tuple[Project, ...]:
        """Loaded files grouped into Projects (v4 grouped ingestion). Folder uploads → one Project
        per top folder (all files beneath it, any depth, its versions); loose files → grouped by
        their real document Title; a title-less loose file → its own needs-attention Project.
        Derived from ``schedules`` + ``file_meta`` on each call — pure and cheap (no engine math)."""
        with self._lock:
            records = [
                IngestRecord(
                    key=key,
                    project_title=sch.project_title,
                    filename=sch.source_file or key,
                    status_date_ordinal=(
                        sch.status_date.timestamp() if sch.status_date is not None else None
                    ),
                    folder=self.file_meta.get(key, (None, None))[0],
                    mtime=self.file_meta.get(key, (None, None))[1],
                )
                for key, sch in self.schedules.items()
            ]
            return group_into_projects(records)

    def analysis_for(self, key: str, sch: Schedule) -> _Analysis:
        """The cached analysis for ``key`` over the active scope; recomputes when the schedule object
        or the filter changes (both reflected in the scoped object's identity)."""
        with self._lock:
            scoped = self.scope(sch)
            cached = self.analyses.get_lru(key)
            if cached is not None and cached[0] is scoped:
                return cached[1]
            analysis = _compute_analysis(scoped)
            self.analyses.put(key, (scoped, analysis))
            return analysis

    def summary_for(self, key: str, sch: Schedule) -> VersionSummary:
        """The cached rollup summary for ``key`` (v4 Feature 2 lazy tier) — the Portfolio's cheap
        path: finish, effective margin, DCMA-14 pass/fail, without holding the full analysis.

        In-memory first; then, only when the version is UNSCOPED (no active filter/target changes
        the numbers, so ``scope`` returned the schedule unchanged), the on-disk SQLite summary keyed
        by the file's content hash — surviving a session restart. A scoped version, or one with no
        content hash (loaded outside /upload), computes fresh and is memoised for the session only.
        A summary equals the fully-computed row (test-enforced), so this only ever changes speed."""
        with self._lock:
            scoped = self.scope(sch)
            cached = self.summaries.get(key)
            if cached is not None and cached[0] is scoped:
                return cached[1]
            on_disk = scoped is sch  # unscoped ⇒ the whole-file summary the SQLite cache holds
            chash = self.content_hashes.get(key) if on_disk else None
            summary: VersionSummary | None = None
            if chash is not None:
                blob = get_default_cache().get_summary(chash)
                if blob is not None:
                    try:
                        summary = VersionSummary.from_json(blob)
                    except (ValueError, KeyError, TypeError):
                        summary = None  # a stale/corrupt blob is a miss, never an error
            if summary is None:
                summary = compute_summary(scoped)
                if chash is not None:
                    get_default_cache().put_summary(chash, summary.to_json())
            self.summaries[key] = (scoped, summary)
            return summary


def _explain(what: str, read: str, decide: str) -> str:
    """A collapsed "What am I looking at?" explainer rendered above a chart/section: WHAT the
    visual shows, HOW to read it, and the DECISIONS it should inform. Server-rendered plain text
    (escaped) so the i18n pass translates it like any other prose."""
    return (
        "<details class=explain><summary>What am I looking at &mdash; and how do I use it?"
        "</summary><div class=explain-body>"
        f"<h4>What this shows</h4><p>{_e(what)}</p>"
        f"<h4>How to read it</h4><p>{_e(read)}</p>"
        f"<h4>Decisions it informs</h4><p class=explain-decide>{_e(decide)}</p>"
        "</div></details>"
    )


def _guide(tip_id: str, text: str) -> str:
    """A dismissable first-visit guide tip (hints.js persists the dismissal per tip id)."""
    return (
        f'<div class=guide-tip data-tip-id="{_e(tip_id)}"><button type=button '
        'class=guide-dismiss title="Dismiss this tip" data-no-i18n>&times;</button>'
        f"<b>Tip:</b> {_e(text)}</div>"
    )


def _banner_html(state: SessionState) -> str:
    # the persistent banner reflects the project's classification intent (config-driven);
    # actual generation still fails closed via route_backend.
    banner = banner_for(state.ai_config)
    css = "cloud" if banner.cloud_active else "local"
    return f'<div class="banner {css}">{html.escape(banner.text)}</div>'


def _filter_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a session-wide filter/group is active, so the
    operator always knows how the numbers are scoped — with one-click manage/clear (ADR-0104).
    Branches on the active source (saved MS Project filter vs field rows) and states the MODE
    honestly: reduce scopes every metric; highlight only marks (metrics stay whole-schedule)."""
    lines: list[str] = []
    if state.active_saved_filter is not None:
        saved = state.active_saved_filter
        tree = _e(_criteria_text(saved.criteria))
        if state.filter_mode == "highlight":
            reach = (
                "matching tasks are <b>highlighted</b> on the grids &mdash; metrics are "
                "<b>not</b> scoped (full schedules)"
            )
        else:
            reach = "every metric on every page (all files) is <b>scoped</b> to its matches"
        lines.append(
            f"<b>Saved filter “{_e(saved.display_name)}”</b> &mdash; {reach}: "
            f'<span class="dp-chip">{tree}</span>. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?clear=1">clear</a>'
        )
    elif state.active_filter:
        parts = []
        for fld, value in state.active_filter:
            vals = _criterion_value_list(value)
            shown = (
                "(populated)"
                if not vals
                else _expandable_more(_e(", ".join(vals[:3])), [_e(v) for v in vals[3:]])
            )
            parts.append(f"{_e(fld)} = {shown}")
        chips = " &middot; ".join(parts)
        mode_note = (
            " (highlight mode &mdash; matches marked, metrics NOT scoped)"
            if state.filter_mode == "highlight"
            else ""
        )
        lines.append(
            f"<b>Filter active</b>{mode_note} &mdash; every metric on every page (all files) is "
            f'scoped to: {chips}. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?clear=1">clear filter</a>'
        )
    if state.active_saved_group is not None:
        lines.append(
            f"<b>Grouped by “{_e(state.active_saved_group.display_name)}”</b> &mdash; ordering/"
            'banding only, metric populations unchanged. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?saved_group=">clear group</a>'
        )
    if not lines:
        return ""
    body = "<br>".join(lines)
    return (
        f'<div class="panel filter-active" style="border-left:4px solid var(--accent)">{body}</div>'
    )


def _endpoint_clear_form(label: str) -> str:
    """An inline form that clears the Target-UID endpoint, returning to the current page (the
    shared ``targetform`` class lets target.js rewrite next_url to the current location)."""
    return (
        '<form action="/target" method=post class="targetform endpoint-clear">'
        '<input type=hidden name=uid value=""><input type=hidden name=next_url value="/">'
        f"<button type=submit class=linkbtn>{_e(label)}</button></form>"
    )


def _endpoint_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a Target UID endpoint is active, so the operator
    always knows every metric/visual is limited to that activity and the work that drives it — with
    the count of omitted activities and a one-click clear (forensic transparency)."""
    uid = state.target_uid
    if uid is None:
        return ""
    found = False
    kept = total = 0
    for s in state.schedules.values():
        if any(t.unique_id == uid and not t.is_summary for t in s.tasks):
            found = True
        scoped = state.scope(s)
        total += sum(1 for t in s.tasks if not t.is_summary)
        kept += sum(1 for t in scoped.tasks if not t.is_summary)
    if not found:
        return (
            '<div class="panel endpoint-active" style="border-left:4px solid var(--bad)">'
            f"<b>Endpoint UID {uid} not found</b> &mdash; no loaded version contains that activity, "
            f"so nothing is being truncated. Check the UID. {_endpoint_clear_form('clear endpoint')}"
            "</div>"
        )
    omitted = total - kept
    return (
        '<div class="panel endpoint-active" style="border-left:4px solid var(--warn)">'
        f"<b>Analysis endpoint: UID {uid}</b> &mdash; every metric and visual on every page is "
        f"limited to UID {uid} and the activities that drive it "
        f"({kept} of {total} activities shown; {omitted} omitted). "
        f"{_endpoint_clear_form('clear endpoint')}</div>"
    )


def _flash_html(flash: _Flash | None) -> str:
    """Render one-shot import feedback (loaded N / per-file errors), or nothing."""
    if flash is None or (not flash.accepted and not flash.errors):
        return ""
    parts: list[str] = []
    if flash.accepted:
        names = ", ".join(_e(a) for a in flash.accepted)
        parts.append(f'<div class="notice ok">Loaded {len(flash.accepted)}: {names}</div>')
    for err in flash.errors:
        parts.append(f'<div class="notice err">Could not import {_e(err)}</div>')
    for note in flash.notices:
        parts.append(f'<div class="notice info">{_e(note)}</div>')
    return "".join(parts)


def _ollama_or_none(config: AIConfig) -> OllamaBackend | None:
    if config.backend != "ollama":
        return None
    try:
        return OllamaBackend(
            endpoint=config.endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def _openai_or_none(config: AIConfig) -> OpenAICompatBackend | None:
    if config.backend != "openai":
        return None
    try:
        # construction enforces loopback (CUIEgressError on a remote host — Law 1)
        return OpenAICompatBackend(
            endpoint=config.openai_endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def _model_installed(model: str, installed: tuple[str, ...]) -> bool:
    """Tolerant match of a configured model name against an Ollama install list.

    Ollama tags models ``name:tag`` (``llama3.1:8b``); a config of ``llama3.1`` should match
    ``llama3.1:8b`` (and vice-versa) so the diagnostic doesn't cry "not installed" over a tag.
    """
    m = model.strip().lower()
    if not m:
        return True
    base = m.split(":")[0]
    return any(n.strip().lower() == m or n.strip().lower().split(":")[0] == base for n in installed)


def _ai_status_note(cfg: AIConfig) -> str:
    """An actionable settings line when a configured LOCAL backend isn't actually serving.

    Turns the silent 'Active backend: null' into a concrete reason + fix (the operator could
    not see why the AI was off): server down / wrong port / model not pulled. Empty for the
    Null backend (no server expected) and for cloud (handled by the banner)."""
    if cfg.backend not in ("ollama", "openai"):
        return ""
    probe = _ollama_or_none(cfg) if cfg.backend == "ollama" else _openai_or_none(cfg)
    if probe is None:  # construction refused a non-loopback endpoint — field validation handles it
        return ""
    is_ollama = cfg.backend == "ollama"
    label = "Ollama" if is_ollama else "the OpenAI-compatible server"
    endpoint = cfg.endpoint if is_ollama else cfg.openai_endpoint
    # unavailable_reason() is on the concrete local backends (not the AIBackend protocol); fall
    # back to is_available() for any other backend object (e.g. a test/cloud stand-in).
    reason_fn = getattr(probe, "unavailable_reason", None)
    reason = (
        reason_fn() if callable(reason_fn) else (None if probe.is_available() else "not reachable")
    )
    if reason is not None:
        if is_ollama:
            hint = (
                "The tool tries to start Ollama for you when it launches, so if this still shows "
                "OFF it is probably still starting — <b>wait a few seconds and reload this page</b>. "
                "If it never connects, Ollama may not be installed, or it is on a different port: "
                f"start it manually (the Ollama app, or <code>ollama serve</code>) and confirm the "
                f"port matches <code>{_e(endpoint)}</code>. On a work laptop the local model still "
                "works — the tool talks to it directly and never via a proxy."
            )
        else:
            hint = (
                "Start your local server (LM Studio / llamafile / vLLM), load a model, and confirm "
                f"the port matches <code>{_e(endpoint)}</code>."
            )
        return (
            f'<div class="notice err">Local AI is OFF — could not reach {label} at '
            f"<code>{_e(endpoint)}</code>: {_e(reason)}. {hint}</div>"
        )
    if is_ollama and cfg.model:  # reachable — is the chosen model actually pulled?
        try:
            installed = probe.list_models()
        except Exception:  # diagnostics only, never sink the page
            installed = ()
        if installed and not _model_installed(cfg.model, installed):
            return (
                f'<div class="notice err">Ollama is reachable but the selected model '
                f"<code>{_e(cfg.model)}</code> isn't installed — <b>pick an installed model from "
                f"the Model dropdown below</b> and Save (installed: {_e(', '.join(installed))}), or "
                f"run <code>ollama pull {_e(cfg.model)}</code> to fetch it.</div>"
            )
    return (
        f'<div class="notice ok">Local AI is ON — {label} reachable at '
        f"<code>{_e(endpoint)}</code>; answers are interpreted by the local model.</div>"
    )


def _second_backend(state: SessionState) -> AIBackend | None:
    """The configured cross-check model, probed + cached like the primary (or ``None``).

    Only the two LOCAL backend kinds are constructible here — a cloud second model does
    not exist by design. Unreachable/missing servers cache as ``None`` (cross-check off)
    so a down second server costs one probe per TTL, not one per question.
    """
    cfg = state.ai_config
    if cfg.second_backend not in ("ollama", "openai"):
        return None
    cached = state.second_cache
    now = time.monotonic()
    if cached is not None and cached[0] == cfg and now - cached[1] < _BACKEND_PROBE_TTL:
        return cached[2]
    backend: AIBackend | None = None
    try:
        if cfg.second_backend == "ollama":
            backend = OllamaBackend(
                endpoint=cfg.endpoint,
                model=cfg.second_model or cfg.model,
                timeout=cfg.gen_timeout,
            )
        else:
            backend = OpenAICompatBackend(
                endpoint=cfg.openai_endpoint, model=cfg.second_model, timeout=cfg.gen_timeout
            )
    except Exception:
        backend = None
    if backend is not None and not backend.is_available():
        backend = None
    state.second_cache = (cfg, now, backend)
    return backend


#: How long a routed-backend probe result is trusted before re-probing (seconds). Keeps
#: report renders from paying the Ollama availability probe on every page view, while an
#: Ollama started mid-session is still picked up promptly.
_BACKEND_PROBE_TTL = 15.0


def _active_backend(state: SessionState) -> AIBackend:
    """The session's routed AI backend (fail-closed local — `route_backend`).

    The routing result is cached for ``_BACKEND_PROBE_TTL`` seconds per config value; a
    settings save resets the cache so changes take effect immediately.
    """
    cached = state.backend_cache
    now = time.monotonic()
    if cached is not None and cached[0] == state.ai_config and now - cached[1] < _BACKEND_PROBE_TTL:
        return cached[2]
    backend, _banner = route_backend(
        state.ai_config,
        null_backend=NullBackend(),
        ollama_backend=_ollama_or_none(state.ai_config),
        openai_backend=_openai_or_none(state.ai_config),
    )
    state.backend_cache = (state.ai_config, now, backend)
    return backend


def _ai_translate(texts: list[str], lang: str, backend: AIBackend) -> dict[str, str]:
    """Translate ``texts`` with the configured model; return only the ones it produced.

    Numbered, tab-delimited round-trip so partial/garbled output degrades gracefully (the caller
    keeps the source text for anything not returned). The Null backend (no model) returns nothing —
    the catalog already covers the fixed UI, and dynamic content stays in the source language."""
    if backend.name == "null" or not texts:
        return {}
    target = i18n.LANGUAGES.get(lang, lang)
    prompt = (
        f"Translate each numbered line into {target}. These are short UI labels and "
        "schedule-activity names from a project-management tool. Output ONLY the translations, one "
        "per line, each prefixed with its number and a tab, in the same order. Keep numbers, dates, "
        "codes and IDs unchanged.\n\n" + "\n".join(f"{i}\t{t}" for i, t in enumerate(texts))
    )
    try:
        raw = backend.generate(prompt)
    except Exception:
        return {}
    out: dict[str, str] = {}
    for line in raw.splitlines():
        num, sep, es = line.partition("\t")
        if sep and num.strip().isdigit() and int(num.strip()) < len(texts) and es.strip():
            source = texts[int(num.strip())]
            # Law 2 (audit H1): a translation that drops, invents, or alters ANY numeric figure
            # of its source line is discarded — the caller then keeps the source text verbatim.
            # This was the one AI emission without a figure gate; now every .generate() output
            # that reaches the operator passes the same preserves_figures check.
            if not preserves_figures(source, es.strip()):
                continue
            out[source] = es.strip()
    return out


def _translate_batch(texts: list[str], lang: str, state: SessionState) -> dict[str, str]:
    """Translations for ``texts``: catalog → session cache → AI model. Source text for the rest."""
    cat = i18n.catalog_for(lang)
    out: dict[str, str] = {}
    need: list[str] = []
    for raw in texts:
        key = raw.strip()
        if not key:
            continue
        if key in cat:
            out[raw] = cat[key]
        elif (lang, key) in state.translations:
            out[raw] = state.translations[(lang, key)]
        elif raw not in need:
            need.append(raw)
    for raw, translated in _ai_translate(need, lang, _active_backend(state)).items():
        state.translations[(lang, raw.strip())] = translated
        out[raw] = translated
    return out


def _polished_narrative(
    state: SessionState, key: str, sch: Schedule, analysis: _Analysis
) -> Narrative:
    """The report narrative, rephrased by the session-selected backend when one is active.

    The Null backend (the default, and the fail-closed route) returns the cached
    deterministic narrative at zero cost. A real backend rephrases each statement once per
    (schedule, backend, model) — `reattach` re-verifies citations AND figures, so polish can
    never drop a citation or alter a number — and any generation failure falls back to the
    deterministic narrative (a dying model server must never 500 the report)."""
    backend = _active_backend(state)
    if backend.name == "null":
        return analysis.narrative
    stamp = f"{backend.name}/{getattr(backend, 'model', '')}"
    # the polished cache is guarded by the same _lock as its peer caches (audit ADR-0250): take it
    # for each atomic get/put — NOT across the slow backend.generate below, which would serialize
    # every narrative request — so a concurrent clear() (ai_off / _invalidate_scope) can never race
    # the multi-step get_lru/put (the D18 KeyError hazard).
    with state._lock:
        cached = state.polished.get_lru(key)
    if cached is not None and cached[0] is sch and cached[1] == stamp:
        return cached[2]
    sources = analysis.narrative.statements
    try:
        polished = tuple(clean_polish(backend.generate(polish_prompt(s.text))) for s in sources)
    except Exception:
        logger.warning("AI narrative generation failed; serving the deterministic narrative")
        return analysis.narrative
    narrative = Narrative(title=analysis.narrative.title, statements=reattach(polished, sources))
    with state._lock:
        state.polished.put(key, (sch, stamp, narrative))
    return narrative


def _ask_panel_html(state: SessionState, page_schedule: str | None = None) -> str:
    """The Ask-the-AI panel every page carries once schedules are loaded (M18 item 4).

    Scope select: the whole workbook (multi-version cited facts) or any single loaded
    schedule; a page with a natural schedule context pre-selects it. The disclaimer is
    standing and permanent — answers may be model-interpreted (settings: AI answer mode)
    but are always grounded by, and shown with, the engine's cited facts.
    """
    if not state.schedules:
        return ""
    keys = [k for k, _ in state.ordered_versions()]
    options: list[str] = []
    if len(keys) > 1:
        sel = " selected" if page_schedule is None else ""
        options.append(f'<option value=""{sel}>Workbook — all {len(keys)} versions</option>')
    for k in keys:
        sel = " selected" if k == page_schedule or len(keys) == 1 else ""
        options.append(f'<option value="{_e(k)}"{sel}>{_e(k)}</option>')
    return f"""
<div class=panel id=askPanel><h2>Ask the AI</h2>
<p class=muted><b>AI can err &mdash; verify against citations.</b> Ask anything about the loaded
data: with a local model active (Ollama) you get a full written analysis grounded in the
engine's computed, cited facts &mdash; the matching facts are always shown alongside. With no
local model active you get the cited facts themselves; <a href="/settings">enable Ollama in AI
Settings</a> for interpretation.</p>
<p class=muted><b>Figure check is role-aware.</b> In <i>strict</i> and <i>annotate</i> modes a number
the model writes is matched against the figures in the cited facts, and a digit that appears only in
an activity <i>name</i> or <i>ID</i> (e.g. "Milestone 2099", UID&nbsp;6077) &mdash; never as an engine
value &mdash; is treated as an identifier the model has re-used in another role (a finish year, a
count): <i>strict</i> discards that answer and <i>annotate</i> flags it &mdash; and the identifier
check runs <i>before</i> the derived-figure check, so a re-used ID can never pass as a coincidental
derivation. Writing an ID <i>as</i> an ID ("UID&nbsp;143", a quoted activity name) is fine; dates
count as whole dates, not digit fragments; a derived whole number must reconstruct exactly; and a
figure re-written with a <i>different explicit unit</i> than the engine stated (a "5%" re-used as
"5&nbsp;days") is likewise discarded/flagged. A digit
that is also a genuine value is untouched (collision-safe). <i>Interpretive</i> mode is not
figure-gated at all. Read any figure against the cited facts &mdash; the meaning, not just the
number.</p>
<div class=viz-controls>
<label>About <select id=askScope>{"".join(options)}</select></label>
<input id=askInput type=text size=60 maxlength=500
 placeholder="e.g. Why is the finish slipping? How many critical activities?">
<button id=askBtn type=button>Ask</button></div>
<div class=viz-controls><span class=muted>Driving path (exact, no AI):</span>
<label>to UID <input id=drivePathUid type=number min=1 step=1 style="width:7em"
 placeholder="UID"></label>
<button id=drivePathBtn type=button>Show driving path</button></div>
<div id=askOut></div></div>
<script src="/static/ask.js"></script>"""


#: Per-page "What am I looking at?" explainers (title → what / how to read / decisions). Rendered
#: collapsed at the top of every matching page by _page(); plain text (escaped + translated by the
#: normal i18n pass). Written for a project analyst, decision-first.
_EXPLAINERS: dict[str, tuple[str, str, str]] = {
    "Dashboard": (
        "Every schedule version loaded in this session, with its headline health: activity "
        "counts, data date, computed finish, and the DCMA 14-point pass rate.",
        "Each row is one schedule file. Green PASS rates and a stable computed finish are "
        "healthy; a falling pass rate or a finish that moves right between versions is the "
        "first warning. Click a file name for its full forensic report.",
        "Decide which version needs attention first, whether the latest update degraded "
        "schedule quality, and whether the finish date is drifting before anyone reports it.",
    ),
    "Mission Control": (
        "A single wall-view of the whole session: every loaded version's key indicators side "
        "by side, built for a stand-up or a war room screen.",
        "Scan for red: failing checks, negative float, slipped finishes. Everything here is "
        "computed by the engine from the files — nothing is typed in.",
        "Use it to open a status meeting: pick the reddest column and drill into that "
        "version's report before discussing anything else.",
    ),
    "Schedule Quality Ribbon": (
        "The Acumen-Fuse-style quality ribbon: one chip per structural metric (missing logic, "
        "leads, lags, constraints, high float, negative float, logic density and more) for the "
        "selected version.",
        "Each chip is a metric with its count and pass/fail color. Hover a chip for its "
        "definition; click through to the Metric Dictionary for the formula, thresholds and a "
        "worked example.",
        "A failing chip tells you exactly which structural repair to schedule next — fix "
        "missing logic before trusting any critical-path or float number downstream.",
    ),
    "Assessment Scorecards": (
        "Three named assessment frameworks beside DCMA-14: the NASA STAT construction checks, the "
        "GAO Schedule Assessment Guide's ten best practices, and an SRA-readiness gate — plus a "
        "reserve-sizing card that says how much buffer protects a committed date at P70/P80.",
        "Each line is a chip (green pass / red fail / grey info) whose figure is drawn straight "
        "from the tool's already-validated metrics — the gate-locked DCMA-14 audit, the "
        "logic-integrity checks, and deterministic model scans; nothing is re-scored here. Pick a "
        "version to assess, and enter a committed date to size the schedule reserve.",
        "Use it to answer 'is this schedule fit for a defensible risk analysis, and does it meet "
        "the GAO/NASA construction bar?' in one view — and to justify the contingency you carry "
        "against the committed finish, at a confidence you can defend in testimony.",
    ),
    "Path Analysis": (
        "The activity network laid out on a time axis: the critical path plus every driving "
        "and near-driving chain, with float per activity.",
        "Bars are activities; the highlighted chain is the path controlling the finish. Tight "
        "float (colored) means little room before a slip hits the end date. Use the filter to "
        "isolate a subsystem, and the export bar to take the picture into a report.",
        "Identify WHERE to add resources or resequence: only work on the driving chain moves "
        "the finish; float elsewhere is schedule margin you can spend deliberately.",
    ),
    "Driving Path": (
        "The exact chain of activities that drives a chosen target activity (or the project "
        "finish), with each link's driving slack — the SSI driving-path view.",
        "Read top-down: each row is the next activity in the chain, and the slack column shows "
        "how much that link can give before it stops driving. Zero-slack links are the "
        "controlling logic.",
        "This is the repair map for a late milestone: accelerate or de-couple the zero-slack "
        "links; anything off this chain will not move the target date.",
    ),
    "Critical-Path Evolution": (
        "How the critical path CHANGED across the loaded versions: which activities joined, "
        "left, and stayed on the controlling path over time.",
        "Each column is a version; each row an activity. Long unbroken rows are a stable "
        "controlling chain; churn (rows appearing/disappearing) means the network's logic is "
        "being rewired between updates.",
        "Stable paths justify targeted recovery plans. Heavy churn is a red flag — either the "
        "plan is being re-baselined quietly or logic is being edited to mask slips; ask for "
        "the change log before accepting the update.",
    ),
    "CP Volatility": (
        "How STABLE the critical path's membership is across the loaded versions: which "
        "activities stayed on the controlling chain longest, and which jumped off and on.",
        "Ten linked visuals over the same per-version critical sets — a stability gauge and "
        "churn timeline (Jaccard similarity), entry/exit flows, a membership heatmap, tenure "
        "and jumper leaderboards, dwell distribution, animated transition ribbons, and a "
        "sortable per-activity scoreboard.",
        "GAO/DCMA best practice expects a stable controlling chain. Heavy churn means the "
        "network is being rewired between updates — cross-reference the worst update with "
        "the Schedule Integrity findings and ask for the change log.",
    ),
    "Trend": (
        "Every metric family tracked ACROSS versions: quality counts, float, completion "
        "performance, forecast movement — the direction of the schedule over time.",
        "Each mini-chart is one metric plotted per version, oldest to newest. Flat or "
        "improving lines are health; worsening lines show exactly when a problem entered. "
        "Click a point to drill into that version.",
        "Trends turn one bad number into a story: use the inflection version to ask what "
        "changed in THAT update — a re-baseline, a calendar edit, a logic rewrite.",
    ),
    "Bow Wave / CEI": (
        "The bow-wave chart: work planned vs work actually finished per period, plus the "
        "Current Execution Index (CEI) — how much of what was planned near-term actually got "
        "done.",
        "Bars pushing right of the data date are the bow wave — work sliding ahead of itself. "
        "CEI below about 0.8 means the near-term plan is not being executed as written.",
        "A growing bow wave predicts a finish slip BEFORE the finish moves: force-rank the "
        "pushed work, fix the choke (resources, predecessors), and re-check next period.",
    ),
    "Finish & Slippage": (
        "Two curves per version pair: where finishes were promised and how far they slipped — "
        "the schedule's promise-keeping record.",
        "Each point compares an activity's finish across versions. Points off the diagonal "
        "slipped; the spread shows whether slippage is isolated or systemic.",
        "Systemic slippage means the baseline is unrealistic — re-plan capacity. Isolated "
        "slippage names the specific work packages to manage this period.",
    ),
    "S-Curve": (
        "Cumulative planned vs actual progress over time — the classic S-curve for the "
        "selected version(s).",
        "The gap between the planned and actual curves is the schedule's true position; a "
        "flattening actual curve means momentum is being lost even if percent-complete "
        "numbers still look busy.",
        "Use the gap and its growth rate to justify (or refute) a recovery plan: a widening "
        "gap with a flat actual curve will not be closed by optimism.",
    ),
    "Forecast": (
        "Multiple engine-computed finish forecasts side by side: pure-logic CPM, the stored "
        "as-scheduled finish, and performance-adjusted projections.",
        "Each method row shows its date and its basis. When methods disagree, the spread IS "
        "the uncertainty; the as-scheduled row shows what the source tool itself stored.",
        "Never brief a single date without the spread: use the range to set commitment dates "
        "with margin, and investigate when the methods diverge sharply.",
    ),
    "EVM": (
        "Earned-value indices computed from the schedule's cost loading: BCWS/BCWP/ACWP, "
        "SPI, CPI and companions, validated against Acumen Fuse where reference data exists.",
        "SPI/CPI near 1.0 is on-plan; below ~0.9 is trouble. NOT APPLICABLE rows mean the "
        "loaded file carries no cost data — that is a fact about the file, not a failure.",
        "Falling SPI with steady CPI means schedule pressure without overspend — a staffing or "
        "sequencing fix. Falling both means the plan itself is broken: re-baseline.",
    ),
    "Resources": (
        "Resource loading over time: who/what is booked, where bookings exceed capacity, and "
        "which activities drive the peaks.",
        "Bars above the capacity line are over-allocations. Expand a peak to see the exact "
        "activities stacking on that resource in that window.",
        "Level BEFORE committing dates: an over-allocated critical resource makes the whole "
        "plan fiction. Move, split, or re-staff the peak drivers first.",
    ),
    "Risks & Opportunities": (
        "The engine's cited findings ranked in a 5x5 risk matrix: every schedule-quality and "
        "manipulation signal, with severity, likelihood and the exact activities cited.",
        "Each finding carries its evidence (file + UID + activity). The matrix position comes "
        "from computed exposure — the days of float actually at stake — not opinion.",
        "Work the top-right cells first; every finding lists its recommended course of action "
        "and the activities to open. Treat manipulation signals as questions to ASK, not "
        "verdicts.",
    ),
    "Schedule Integrity": (
        "Version-over-version change forensics: every manipulation-pattern signal the engine "
        "detects between consecutive files (deleted tasks or logic, shortened in-progress "
        "durations, added hard constraints, loosened calendars, baseline-date changes, edited "
        "or erased actuals), each cited to file + UniqueID + task — plus a counterfactual that "
        "reverts the path-shedding changes and re-runs CPM to show what the finish would have "
        "been without them.",
        "Read each version-pair section top to bottom: the severity column ranks the signals; "
        "the citations name the exact activities; the counterfactual panel quantifies how much "
        "apparent recovery came from the changes rather than performed work. Select an "
        "exception field (for example a BCR number) to badge or hide changes that were "
        "authorized.",
        "Whether the schedule's reported recovery is real; which specific changes to interrogate "
        "in a schedule review; which findings are already covered by an approved change request "
        "and which have no paper trail.",
    ),
    "Risk Analysis (SRA)": (
        "A Monte-Carlo schedule risk analysis: activity durations varied per your 3-point "
        "settings and risk register, run through the real CPM engine to a finish-date "
        "distribution.",
        "The histogram shows possible finish dates and their likelihood; P50/P80 markers are "
        "the dates with 50%/80% confidence. The tornado ranks which activities drive the "
        "spread.",
        "Commit to P80-class dates, not the deterministic finish. Attack the top tornado "
        "drivers — tightening their uncertainty moves the whole distribution left.",
    ),
    "Diagnostic Brief": (
        "A printable, fully-cited diagnostic of the selected version: every failing check, "
        "finding and key figure with its evidence trail.",
        "Read it like an audit report: each statement cites the file, activity ID and name it "
        "rests on. Nothing here is AI-generated — it is the engine's own computation.",
        "Hand this to the schedule owner as the work list; every line is defensible because "
        "every line is cited.",
    ),
    "Executive Briefing": (
        "The whole session condensed for leadership: bottom line up front, cross-version "
        "trend, per-version verdicts, risks and recommended actions — every statement cited.",
        "Start at the one-sentence bottom line. Optional local-AI polish only rewords "
        "sentences — every figure is verified against the engine before display.",
        "Use it as the meeting document: decisions land faster when every claim carries its "
        "citation inline.",
    ),
    "Metric Dictionary": (
        "The authoritative definition of every metric this tool computes: formula, source, "
        "thresholds, and a worked example for each.",
        "Each entry states what the metric measures, the exact formula, why it matters, what "
        "a failure indicates, and PASS/FAIL examples. Metrics link here from every page.",
        "When two stakeholders argue about a number, this page ends the argument: same "
        "formula, same thresholds, same source for everyone.",
    ),
    "Groups & Filters": (
        "A session-wide lens: filter every page and every loaded version to the activities "
        "matching your criteria (WBS, name, custom fields...).",
        "Set criteria and Apply — the filter banner then shows on every page until cleared. "
        "All metrics recompute over the filtered population only.",
        "Isolate one subsystem or contractor and read its health in minutes instead of "
        "exporting subsets by hand. Clear the filter before quoting whole-project numbers.",
    ),
    "AI Settings": (
        "Controls for the OPTIONAL local AI: backend, model, answer mode, second-model "
        "cross-check, and the project's classification posture.",
        "Everything runs on 127.0.0.1 — a cloud backend is refused while the project is "
        "CLASSIFIED. Answer modes trade breadth for strictness: strict never shows an "
        "unverified number; annotate flags derived ones; interpretive is unfiltered analysis.",
        "Pick strict for testimony work, annotate for daily analysis. If a figure ever "
        "surprises you, check its citation before repeating it.",
    ),
    "Compare": (
        "Two versions side by side: every tracked field change per activity — dates, "
        "durations, logic, constraints, status.",
        "Each row is one activity's deltas between the versions. Sort by the change that "
        "matters (finish slip, duration growth, constraint added).",
        "This is where quiet edits surface: baseline changes, added constraints and "
        "deactivated work show up here even when the summary numbers look stable.",
    ),
}


def _page_explainer(title: str) -> str:
    entry = _EXPLAINERS.get(title)
    if entry is None or not entry[0]:
        return ""
    return _explain(*entry)


def _global_sources_banner(state: SessionState, focus_key: str | None = None) -> str:
    """The ALWAYS-ON provenance banner every page carries (operator 2026-07-10: "NO MATTER
    WHAT ... I want them to see clearly what file it is being pulled from"): the loaded
    file(s), oldest first, under the page header. Single-file pages and per-visual captions
    still name their specific file; animated visuals caption the file per step on top of this."""
    try:
        schedules = [s for _k, s in state.ordered_versions()]
    except Exception:
        return ""
    if not schedules:
        return ""
    names = [_e(s.source_file or s.name) for s in schedules]
    # a per-file page (e.g. /analysis — "Where We Stand") names ITS file and offers a switcher
    # instead of implying the numbers mix all loaded files (operator 2026-07-16)
    if focus_key is not None:
        pairs = state.ordered_versions()
        cur = dict(pairs).get(focus_key)
        cur_name = _e((cur.source_file or cur.name) if cur is not None else focus_key)
        if len(pairs) <= 1:
            inner = f"All data on this page is computed from: <b>{cur_name}</b>"
        else:
            opts = "".join(
                f'<option value="/analysis/{quote(k, safe="")}"'
                f"{' selected' if k == focus_key else ''}>{_e(s.source_file or s.name)}</option>"
                for k, s in pairs
            )
            inner = (
                f"This page shows ONE file: <b>{cur_name}</b> &mdash; switch file: "
                f'<select onchange="location.href=this.value" data-no-i18n>{opts}</select> '
                "(versions are compared on the Trend / Compare / Evolution pages, never mixed here)"
            )
        return f"<div class=src-banner data-no-i18n>&#128196; {inner}</div>"
    if len(names) == 1:
        inner = f"All data on this page is computed from: <b>{names[0]}</b>"
    else:
        inner = (
            f"Data on this page is computed from the {len(names)} loaded files "
            "(oldest first): <b>" + "</b> &rarr; <b>".join(names) + "</b> — each visual/table "
            "names its own file scope, and animated visuals caption the file shown at each step."
        )
    return f"<div class=src-banner data-no-i18n>&#128196; {inner}</div>"


# ── Mission Ops story spine (ADR-0196) ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class _Chapter:
    """One entry in the three-act / twelve-chapter story spine (the Mission Ops redesign).

    ``route`` is where the nav link points; ``@analysis`` / ``@wbs`` resolve to the first loaded
    schedule's report. ``beats`` are secondary pages folded under the chapter — kept in the nav so
    nothing is orphaned. ``titles`` are the ``_page(...)`` title strings that resolve to this
    chapter (drives the kicker / Continue footer / progress "you are here"); ``takeaway`` seeds the
    Continue segue.
    """

    num: str
    label: str
    route: str
    beats: tuple[tuple[str, str], ...] = ()
    titles: tuple[str, ...] = ()
    takeaway: str = ""


_SPINE: tuple[tuple[str, tuple[_Chapter, ...]], ...] = (
    (
        "LOAD",
        (
            _Chapter(
                "00",
                "Import",
                "/",
                (),
                ("Dashboard",),
                "Load the mission — drop schedule files to begin.",
            ),
        ),
    ),
    (
        "OVERVIEW",
        (
            _Chapter(
                "",
                "Portfolio",
                "/portfolio",
                (),
                ("Portfolio",),
                "Every project across the portfolio, at a glance.",
            ),
            _Chapter(
                "",
                "Mission Control",
                "/mission",
                (),
                ("Mission Control",),
                "The whole session on one wall.",
            ),
        ),
    ),
    (
        "ACT I · SITUATION",
        (
            _Chapter(
                "01",
                "Where we stand",
                "@analysis",
                (),
                (),
                "Where the project stands at the data date.",
            ),
            _Chapter(
                "02",
                "Can we trust the plan?",
                "/ribbon",
                (
                    ("Schedule Integrity", "/integrity"),
                    ("Assessment Scorecards", "/scorecards"),
                ),
                ("Schedule Quality Ribbon", "Schedule Integrity", "Assessment Scorecards"),
                "Whether the schedule is built soundly enough to trust its numbers.",
            ),
        ),
    ),
    (
        "ACT II · DIAGNOSIS",
        (
            _Chapter(
                "03",
                "What drives the date",
                "/path",
                (("Driving Path", "/driving-path"),),
                ("Path Analysis", "Driving Path"),
                "The chain of work that controls the finish.",
            ),
            _Chapter(
                "04",
                "How stable is the path",
                "/evolution",
                (("CP Volatility", "/volatility"),),
                ("Critical-Path Evolution", "CP Volatility"),
                "Whether the critical path holds or thrashes between updates.",
            ),
            _Chapter(
                "05",
                "How it moved",
                "/trend",
                (("Finish & Slippage", "/curves"),),
                ("Trend", "Finish & Slippage"),
                "How the finish has moved, update over update.",
            ),
            _Chapter(
                "06",
                "Work piling up",
                "/cei",
                (),
                ("Bow Wave / CEI",),
                "Whether work is bow-waving into the future.",
            ),
            _Chapter(
                "07",
                "How we execute",
                "/performance",
                (("EVM", "/evm"), ("WBS", "@wbs")),
                ("Performance Summary", "EVM"),
                "How execution is actually tracking to plan.",
            ),
            _Chapter(
                "08",
                "Who is overloaded",
                "/resources",
                (),
                ("Resources",),
                "Where resource pressure concentrates.",
            ),
        ),
    ),
    (
        "ACT III · OUTLOOK",
        (
            _Chapter(
                "09",
                "Where it lands",
                "/forecast",
                (("S-Curve", "/scurve"),),
                ("Forecast", "S-Curve"),
                "Where the finish is most likely to land.",
            ),
            _Chapter(
                "10",
                "What changed",
                "/compare",
                (),
                ("Compare",),
                "What actually changed between two versions.",
            ),
            _Chapter(
                "11",
                "What could go wrong",
                "/sra",
                (("Risks & Opportunities", "/risks"),),
                ("Risk Analysis (SRA)", "Risks & Opportunities"),
                "What could still bite the finish.",
            ),
            _Chapter(
                "12",
                "The briefing",
                "/briefing",
                (("Diagnostic Brief", "/brief"),),
                ("Executive Briefing", "Diagnostic Brief"),
                "The one-page verdict for leadership.",
            ),
        ),
    ),
    (
        "SETUP",
        (
            _Chapter("", "Margin Dashboard", "/margin", (), ("Margin Dashboard",), ""),
            _Chapter("", "Metric Workbench", "/workbench", (), ("Metric Workbench",), ""),
            _Chapter(
                "",
                "Standards & Execution",
                "/standards",
                (),
                ("Standards & Execution Indices",),
                "",
            ),
            _Chapter("", "Groups & Filters", "/groups", (), ("Groups & Filters",), ""),
            _Chapter("", "AI Settings", "/settings", (), ("AI Settings",), ""),
            _Chapter("", "Metric Dictionary", "/help", (), ("Metric Dictionary",), ""),
        ),
    ),
)

# ── Role-selection front page (v4 F4, ADR-0255) ────────────────────────────────────────────
# Five audience roles, each a CURATED ENTRY POINT into pages that already exist. Selecting a
# role is pure wayfinding: it reorders/emphasizes (a "Start here" strip on the home page, a
# highlight on the role's chapters in the nav) and picks the post-upload landing page — it
# NEVER hides a page, never changes a computation, a default parameter, or a number (Law 2:
# every figure is identical under every role). The mapping is static, committed, and cited to
# the spine's own pages; "Show everything" (no role) is byte-identical to the pre-F4 behavior.


@dataclass(frozen=True)
class _Role:
    """One front-page audience role: a label, a one-line who-this-is-for, the post-upload
    landing route (None = inherit the default upload destination), and the "Start here" cards
    as (title, spine route, one-line why)."""

    id: str
    label: str
    blurb: str
    landing: str | None
    cards: tuple[tuple[str, str, str], ...]


_ROLES: tuple[_Role, ...] = (
    _Role(
        "scheduler",
        "Scheduler / Planner",
        "Builds and maintains the IMS — is the schedule sound enough to trust?",
        "/ribbon",
        (
            ("Schedule Quality Ribbon", "/ribbon", "The Fuse-parity quality read at a glance."),
            ("Schedule Integrity", "/integrity", "Logic, constraints, and structure health."),
            ("Where we stand (DCMA-14)", "@analysis", "The full report with the DCMA-14 audit."),
            ("Path Analysis", "/path", "What drives the finish, SSI-style."),
            ("Groups & Filters", "/groups", "Scope every metric to the population you manage."),
        ),
    ),
    _Role(
        "pm",
        "Program / Project Manager",
        "Owns the decisions — margin, forecast, and the portfolio picture.",
        "/portfolio",
        (
            ("Portfolio", "/portfolio", "Every project across the portfolio, at a glance."),
            ("Mission Control", "/mission", "The whole session on one wall."),
            ("Margin Dashboard", "/margin", "Burn-down, the Fig 5-30 band, and sufficiency."),
            ("Forecast", "/forecast", "Every finish forecast side by side."),
            ("Executive Briefing", "/briefing", "The cited story, ready to present."),
        ),
    ),
    _Role(
        "analyst",
        "Forensic Analyst",
        "Hunts manipulation — how the schedule moved and what changed it.",
        None,  # inherit the default (the analysis report / dashboard) — today's behavior
        (
            ("Where we stand", "@analysis", "The full per-schedule forensic report."),
            ("Trend", "/trend", "Every metric across every loaded version."),
            ("Critical-Path Evolution", "/evolution", "Whether the path holds or thrashes."),
            ("Bow Wave / CEI", "/cei", "Work pushed ahead of the data date."),
            ("Compare", "/compare", "What changed between the two most recent versions."),
        ),
    ),
    _Role(
        "auditor",
        "Auditor (DCMA / IG)",
        "Checks compliance — the standards, the scorecards, the definitions.",
        "/standards",
        (
            ("Standards & Execution Indices", "/standards", "SEM/SSI families, Fuse-validated."),
            ("Schedule Quality Ribbon", "/ribbon", "DCMA-14 and the quality gates."),
            ("Assessment Scorecards", "/scorecards", "The graded assessment rollup."),
            ("Metric Dictionary", "/help", "Every metric's definition, formula, and source."),
        ),
    ),
    _Role(
        "counsel",
        "Counsel / Testifying Expert",
        "Builds the record — cited narrative, exhibits, and the delta story.",
        "/briefing",
        (
            ("Executive Briefing", "/briefing", "The cited narrative, figure-gated."),
            ("Diagnostic Brief", "/brief", "The engine's findings with citations."),
            ("Compare", "/compare", "The version-to-version delta record."),
            ("Path Analysis", "/path", "The driving chain behind the finish date."),
        ),
    ),
)

_ROLE_BY_ID: dict[str, _Role] = {r.id: r for r in _ROLES}


def _role_strip(state: SessionState) -> str:
    """The front-page "Who's analyzing today?" picker + the active role's Start-here strip
    (v4 F4, ADR-0255). Emphasis only: everything stays reachable under every role, and the
    "Show everything" pill (no role) reproduces the pre-F4 page exactly. Cards whose spine
    route cannot resolve yet (``@analysis`` with nothing loaded) are skipped, not broken."""
    active = _ROLE_BY_ID.get(state.role) if state.role else None

    def _pill(rid: str, label: str, blurb: str, is_active: bool) -> str:
        cls = "role-card active" if is_active else "role-card"
        return (
            f'<form method=post action="/role" class=roleform>'
            f'<input type=hidden name=role value="{_e(rid)}">'
            f'<button type=submit class="{cls}" aria-pressed={"true" if is_active else "false"} '
            f'title="{_e(blurb)}">{_e(label)}</button></form>'
        )

    pills = "".join(_pill(r.id, r.label, r.blurb, active is r) for r in _ROLES)
    pills += _pill("", "Show everything", "No role — the full console, unfiltered.", active is None)
    strip = (
        "<div class=panel><h2 data-no-i18n>Who&rsquo;s analyzing today?</h2>"
        "<p class=muted>Pick a role to get a tailored <b>Start here</b> strip, highlighted "
        "chapters in the nav, and a role-matched landing page after an import. Nothing is hidden "
        "and no number changes &mdash; every page stays reachable under every role.</p>"
        f"<div class=role-strip>{pills}</div>"
    )
    if active is None:
        return strip + "</div>"
    cards = ""
    for title, route, why in active.cards:
        href = _resolve_route(state, route)
        if not href or (route == "@analysis" and not state.schedules):
            continue  # unresolvable until a schedule is loaded — skipped, never a dead link
        cards += (
            f'<a class=start-card href="{href}"><b>{_e(title)}</b>'
            f"<span class=muted>{_e(why)}</span></a>"
        )
    return (
        strip
        + f"<h3 data-no-i18n>Start here &mdash; {_e(active.label)}</h3>"
        + f"<p class=muted>{_e(active.blurb)}</p>"
        + f"<div class=start-strip>{cards}</div></div>"
    )


# Narrative order for the Continue footer + progress (Import → Mission Control → 01…12; Setup off-spine).
_STORY_ORDER: tuple[_Chapter, ...] = tuple(
    ch for label, chapters in _SPINE for ch in chapters if label != "SETUP"
)
# Numbered chapters only, for the progress dashes.
_STORY_CHAPTERS: tuple[_Chapter, ...] = tuple(c for c in _STORY_ORDER if c.num)


def _build_title_map() -> dict[str, _Chapter]:
    m: dict[str, _Chapter] = {}
    for _label, chapters in _SPINE:
        for ch in chapters:
            for t in ch.titles:
                m.setdefault(t, ch)
    return m


# Chapters whose page carries a dynamic title (e.g. /analysis renders the schedule name) can't be
# resolved from the title, so a route may name its chapter explicitly via _page(..., chapter=…).
_CHAPTER_BY_NUM: dict[str, _Chapter] = {
    ch.num: ch for _label, chapters in _SPINE for ch in chapters if ch.num
}


_TITLE_TO_CHAPTER: dict[str, _Chapter] = _build_title_map()


def _resolve_route(state: SessionState, route: str) -> str:
    """Resolve a spine ``route`` to a real URL. ``@analysis`` / ``@wbs`` point at the first loaded
    schedule's report (the dropzone when nothing is loaded)."""
    if route in ("@analysis", "@wbs"):
        first_key = next(iter(state.schedules), None)
        if first_key is None:
            return "/" if route == "@analysis" else ""
        base = "/analysis/" if route == "@analysis" else "/wbs/"
        return base + quote(first_key)
    return route


def _render_target_control(state: SessionState) -> str:
    """The global Analysis-Target selector: pick the activity every metric, path, forecast and the
    briefing verdict is measured to (Project finish = the whole schedule). The dropdown lists the
    **milestones** across every loaded version (so a milestone deleted in a later version is still
    selectable); the **UID box** measures to ANY activity by UniqueID — a non-milestone, or a UID
    that exists only in an older version. Both post to ``/target`` (which drives the endpoint scope
    and the SRA/SSI focus). A non-milestone target still shows as a selected custom dropdown option."""
    seen: dict[int, str] = {}
    for s in state.schedules.values():
        for t in s.tasks:
            if t.is_milestone and not t.is_summary and t.unique_id not in seen:
                seen[t.unique_id] = t.name or f"UID {t.unique_id}"
    cur = state.target_uid
    opts = ['<option value="">Project finish (whole schedule)</option>']
    for uid, name in seen.items():
        sel = " selected" if uid == cur else ""
        opts.append(f'<option value="{uid}"{sel}>{_e(f"{name} · UID {uid}")}</option>')
    if cur is not None and cur not in seen:
        opts.append(f'<option value="{cur}" selected>UID {cur} (custom)</option>')
    options = "".join(opts)
    return (
        '<form action="/target" method=post class="navform targetform" '
        'title="Measure every view to one milestone (Project finish = the whole schedule)" '
        'data-sf-hint="Pick a milestone every metric, path, forecast and the briefing verdict is '
        "measured to (Project finish uses the whole schedule), or enter any activity's UID at right.\">"
        '<input type=hidden name=next_url value="/">'
        "<label>Measure to "
        f'<select name=uid data-no-i18n onchange="this.form.submit()">{options}</select></label>'
        "</form>"
        '<form action="/target" method=post class="navform targetform sf-uid-form" '
        'data-sf-hint="Measure to ANY activity by UniqueID — including a non-milestone or a milestone '
        "that was deleted in a later version. The UID is matched across every loaded version; a blank "
        'or unknown UID clears back to Project finish.">'
        '<input type=hidden name=next_url value="/">'
        "<label class=sf-uid-ctl>or UID "
        '<input type=number name=uid min=1 step=1 inputmode=numeric placeholder="any UID…" '
        'data-no-i18n aria-label="Measure to any activity by UniqueID"></label>'
        "<button type=submit class=linkbtn data-no-i18n>Set</button>"
        "</form>"
    )


def _render_nav(state: SessionState) -> str:
    """The story-spine navigation: three acts / twelve chapters (with folded beat links) plus the
    off-spine Load / Overview / Setup rails, followed by the session controls. Rendered server-side
    so the milestone target selector and the chapter-01 link can read the loaded session."""
    lang = i18n.normalize(state.language)
    lang_options = "".join(
        f'<option value="{code}"{" selected" if code == lang else ""}>{_e(name)}</option>'
        for code, name in i18n.LANGUAGES.items()
    )

    # v4 F4 (ADR-0255): the active role's card routes get a nav HIGHLIGHT — emphasis only,
    # every chapter stays rendered and reachable regardless of role.
    role = _ROLE_BY_ID.get(state.role) if state.role else None
    role_routes: frozenset[str] = (
        frozenset(route for _t, route, _w in role.cards) if role else frozenset()
    )

    def _chapter_link(ch: _Chapter) -> str:
        href = _resolve_route(state, ch.route) or "/"
        num = f"<span class=ch-num>{ch.num}</span>" if ch.num else ""
        beats = ""
        beat_links = []
        for lbl, route in ch.beats:
            r = _resolve_route(state, route)
            if r:
                beat_links.append(f'<a href="{r}">{_e(lbl)}</a>')
        if beat_links:
            beats = "<span class=nav-beats>" + "".join(beat_links) + "</span>"
        hl = (
            " role-hl"
            if ch.route in role_routes or any(rt in role_routes for _lbl, rt in ch.beats)
            else ""
        )
        return (
            f'<a class="nav-chapter{hl}" href="{href}">{num}'
            f"<span class=ch-label>{_e(ch.label)}</span></a>{beats}"
        )

    sections = ""
    for sect_label, chapters in _SPINE:
        links = "".join(_chapter_link(c) for c in chapters)
        cls = "nav-sect setup" if sect_label == "SETUP" else "nav-sect"
        sections += (
            f'<div class="{cls}"><span class=nav-sect-label>{_e(sect_label)}</span>{links}</div>'
        )

    controls = (
        "<div class=nav-controls>"
        '<form action="/session/wipe" method=post class=navform '
        "onsubmit=\"return confirm('Wipe all loaded schedules?')\">"
        "<button type=submit class=linkbtn>Wipe Session</button></form>"
        '<a href="#" onclick="return sfQuit()" title="Stop the local server and exit">Quit</a>'
        '<button id=sfResetView type=button class="linkbtn sf-reset-view" data-no-i18n '
        'title="Clear every selection you made on THIS page (inputs, filters, toggles, remembered '
        'view) and return to its default view">&#10226; Reset view</button>'
        + _render_target_control(state)
        # nosec B608 — this is HTML markup (a <select> control), not a SQL query; the B608
        # heuristic false-matches the "select"/option keywords in the concatenated view picker.
        + '<label class=ui-scale-ctl title="Choose the console view — four complete themes '  # nosec B608
        '(ADR-0195)">View'
        "<select id=themeSelect data-no-i18n>"
        "<option value=console>CONSOLE — mission control</option>"
        "<option value=daylight>DAYLIGHT — clean light</option>"
        "<option value=apollo>APOLLO — retro CRT</option>"
        "<option value=jarvis>JARVIS — HUD</option>"
        "</select></label>"
        "<button id=themeToggle type=button class=linkbtn data-no-i18n "
        'title="Toggle daylight vs your last dark view" '
        'data-sf-hint="Flips between DAYLIGHT and the last dark view you used (Console, Apollo or '
        'JARVIS). Pick any of the four views from the View menu.">Theme</button>'
        '<label class=ui-scale-ctl title="Rescale the whole page — text and layout together">Size'
        "<select id=uiScale data-no-i18n>"
        '<option value="0.9">90%</option><option value="1">100%</option>'
        '<option value="1.1">110%</option>'
        '<option value="1.25">125%</option><option value="1.5">150%</option>'
        '<option value="1.75">175%</option>'
        "</select></label>"
        '<form action="/language" method=post class="navform langform" '
        'title="Display language for the UI and AI results">'
        "<label>Language: <select name=lang data-no-i18n "
        f'onchange="this.form.submit()">{lang_options}</select></label>'
        "</form>"
        "</div>"
    )
    return f"<nav><div class=nav-spine>{sections}</div>{controls}</nav>"


def _chapter_kicker(title: str, chapter: _Chapter | None = None) -> str:
    """The slim chapter kicker above a page's content: ``CHAPTER NN · NAME`` (story position).
    ``chapter`` overrides title-based resolution for dynamic-title pages (e.g. /analysis)."""
    ch = chapter if chapter is not None else _TITLE_TO_CHAPTER.get(title)
    if ch is None:
        return ""
    prefix = f"CHAPTER {ch.num} · " if ch.num else ""
    return f"<div class=chapter-kicker data-no-i18n>{prefix}{_e(ch.label.upper())}</div>"


def _story_footer(state: SessionState, title: str, chapter: _Chapter | None = None) -> str:
    """The Continue → next-chapter footer + the STORY-SO-FAR progress dashes, on every spine page.
    ``chapter`` overrides title-based resolution for dynamic-title pages (e.g. /analysis)."""
    ch = chapter if chapter is not None else _TITLE_TO_CHAPTER.get(title)
    if ch is None:
        return ""
    try:
        idx = _STORY_ORDER.index(ch)
    except ValueError:
        return ""
    dashes = ""
    for c in _STORY_CHAPTERS:
        state_cls = " cur" if c is ch else ""
        dashes += (
            f'<span class="story-dash{state_cls}" data-route="{_resolve_route(state, c.route)}" '
            f'title="{_e(c.num + " " + c.label)}"></span>'
        )
    progress = (
        "<div class=story-progress data-no-i18n>"
        "<span class=story-so-far>STORY SO FAR</span>"
        f"<span class=story-dashes>{dashes}</span></div>"
    )
    cont = ""
    if idx + 1 < len(_STORY_ORDER):
        nxt = _STORY_ORDER[idx + 1]
        href = _resolve_route(state, nxt.route)
        if href:
            label = f"Chapter {nxt.num} → {nxt.label}" if nxt.num else f"{nxt.label} →"
            seg = _e(nxt.takeaway) if nxt.takeaway else ""
            cont = (
                "<div class=continue-foot data-no-i18n>"
                f"<span class=continue-seg>{seg}</span>"
                f'<a class="btn continue-btn" href="{href}">{_e(label)}</a></div>'
            )
    return f"<div class=story-foot>{progress}{cont}</div>"


def _page(
    state: SessionState,
    title: str,
    body: str,
    *,
    status_code: int = 200,
    ask_schedule: str | None = None,
    chapter: _Chapter | None = None,
    focus_file: str | None = None,
) -> HTMLResponse:
    lang = i18n.normalize(state.language)
    # NASA CUI page-marking (top + bottom banner on every page). Default CLASSIFIED → mark CUI;
    # only the operator-asserted UNCLASSIFIED mode drops the CUI controls marking. Kept out of the
    # i18n pass (data-no-i18n) so the control marking stays in its required standard wording.
    classified = state.ai_config.classification is Classification.CLASSIFIED
    cui_class = "cui" if classified else "unclassified"
    cui_text = (
        "Controlled Unclassified Information • CUI"
        if classified
        else "Unclassified • no CUI controls asserted"
    )
    # _bust_static: version-bust every /static URL so an upgraded install can never keep
    # executing a stale browser-cached JS/CSS (the fixed-port deployment reuses the same
    # cache origin across restarts, and StaticFiles alone sends no Cache-Control).
    return HTMLResponse(
        _bust_static(
            _LAYOUT.render(
                # _LAYOUT is a bare jinja2.Template (autoescape=False) because `body`/`banner` are
                # already-built raw HTML; `title` is the one untrusted plain-text value (derived from the
                # uploaded filename via _clean_key), so escape it here at the boundary to close the latent
                # reflected-XSS in <title> (audit F-06 / ADR-0130). The CSP allows 'unsafe-inline', so
                # escaping — not CSP — is the barrier; do NOT pass raw schedule-derived text as `title`.
                title=_e(title),
                nav=_render_nav(state),
                banner=_banner_html(state),
                body=(
                    _filter_banner(state)
                    + _endpoint_banner(state)
                    + _global_sources_banner(state, focus_file)
                    + _chapter_kicker(title, chapter)
                    + _page_explainer(title)
                    + body
                    + _ask_panel_html(state, ask_schedule)
                    + _story_footer(state, title, chapter)
                ),
                lang=lang,
                lang_json=json.dumps(lang),
                # the catalog is only shipped to the client when not English (no payload for en)
                catalog_json=json.dumps(i18n.catalog_for(lang)),
                cui_class=cui_class,
                cui_text=cui_text,
            )
        ),
        status_code=status_code,
    )


def _parse_uid(value: str | None) -> int | None:
    """A UniqueID from form/query text — blank, non-numeric, or non-positive means none."""
    if value is None:
        return None
    text = value.strip()
    if not text.isdigit():
        return None
    uid = int(text)
    return uid if uid > 0 else None


def _parse_uid_list(value: str | None) -> list[int]:
    """UniqueIDs from a free-text list (comma / space / semicolon separated), order-preserving.

    Each token is parsed with :func:`_parse_uid` rules (positive integers only); blanks and
    non-numeric tokens are dropped, and duplicates are removed keeping first appearance."""
    if not value:
        return []
    out: list[int] = []
    for token in value.replace(";", " ").replace(",", " ").split():
        uid = _parse_uid(token)
        if uid is not None and uid not in out:
            out.append(uid)
    return out


#: Cap on the operator-tracked UIDs on the Bow-Wave / S-Curve charts (operator 2026-07-09:
#: "max of 20 UIDs") — more markers than that turn the animation into noise.
_MAX_TRACK_UIDS = 20


def _parse_track_uids(value: str | None) -> list[int]:
    """The Bow-Wave / S-Curve tracked-UID list: free-text UIDs, capped at 20 (first kept)."""
    return _parse_uid_list(value)[:_MAX_TRACK_UIDS]


def _to_float(value: str | None, default: float) -> float:
    """A float from form/query text — blank, non-numeric, or non-finite falls back to ``default``.

    ``inf``/``nan`` are rejected at the boundary (audit L2): ``float('inf')`` parses cleanly but
    later poisons SRA arithmetic (a magnitude of ``inf`` 422s every downstream sim), so a
    non-finite entry is treated like any other invalid input and discarded here.
    """
    if value is None:
        return default
    try:
        parsed = float(value.strip())
    except ValueError:
        return default
    return parsed if math.isfinite(parsed) else default


def _clamp_float(
    value: str | None, lo: float, hi: float, default: float, *, scale: float = 1.0
) -> float:
    """Parse ``value`` times ``scale``, clamp to ``[lo, hi]``; non-numeric keeps ``default``."""
    parsed = _to_float(value, default / scale if scale else default)
    return max(lo, min(hi, parsed * scale))


def _e(text: object) -> str:
    return html.escape(str(text))


def _mdY(value: dt.date | dt.datetime | str | None) -> str:
    """A displayed date as ``MM/DD/YYYY`` (operator convention), never a time-of-day.

    Accepts a date, a datetime (time dropped), or an ISO ``YYYY-MM-DD[Txx]`` string; ``None``
    or an unparsable string renders as an em dash. Data payloads/exports stay ISO — this is
    the presentation boundary only."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            parsed: dt.date = dt.date.fromisoformat(value[:10])
        except ValueError:
            return value
    elif isinstance(value, dt.datetime):
        parsed = value.date()
    else:
        parsed = value
    return f"{parsed.month:02d}/{parsed.day:02d}/{parsed.year:04d}"


def _user_tip(text: str) -> str:
    """A small, consistent "User Tip" call-out to guide the operator on a page or control.

    ``text`` is a developer-authored static string (it may contain simple inline HTML such as
    ``<b>`` for emphasis); it is never operator input, so it is embedded as-is. Rendered the same
    way everywhere so tips read consistently across the tool.
    """
    return (
        '<p class="user-tip" role="note"><span class="ut-badge">User Tip</span> '
        f"<span>{text}</span></p>"
    )


def _sources_line(schedules: Sequence[Schedule]) -> str:
    """The provenance line every multi-file visual carries (ADR-0150): which loaded file(s)
    the data on this page is drawn from, so the operator always knows what they are looking
    at — one name for a single file, the full list for a mix."""
    names = [_e(s.source_file or s.name) for s in schedules]
    if not names:
        return ""
    if len(names) == 1:
        return f"<p class=muted>Source file: <b>{names[0]}</b></p>"
    return (
        f"<p class=muted>Sources ({len(names)} files, oldest first): <b>"
        + "</b>, <b>".join(names)
        + "</b></p>"
    )


def _parse_committed_date(value: str | None) -> dt.datetime | None:
    """A committed finish date from an ``YYYY-MM-DD`` form value (midnight), or ``None``."""
    if not value:
        return None
    try:
        d = dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    return dt.datetime(d.year, d.month, d.day)


def _expandable_more(shown_html: str, hidden_items: list[str]) -> str:
    """``shown … <details>+N more</details>`` — every truncated list is expandable in place.

    ``shown_html`` is already-escaped/authored HTML for the visible prefix; ``hidden_items``
    are the already-escaped overflow entries. The operator asked that "(+N more)" never be a
    dead end — the full list opens inline (native ``<details>``, no JS, air-gap safe)."""
    if not hidden_items:
        return shown_html
    return (
        f'{shown_html} <details class=more-inline style="display:inline-block">'
        f'<summary style="display:inline;cursor:pointer" class=btn-link>+{len(hidden_items)}'
        " more</summary> "
        f"<span>{', '.join(hidden_items)}</span></details>"
    )


#: Content-Security-Policy that enforces the air-gap (Law 1) in EVERY browser at runtime, not
#: just in the test: ``default-src``/``connect-src``/``img-src`` are ``'self'`` so the page can
#: never pull or beacon to a remote host (no CDN, no font, no exfil fetch). ``'unsafe-inline'``
#: is allowed for style + script because the UI legitimately uses inline ``style=`` (the Gantt's
#: px widths) and two inline handlers (Quit / wipe-confirm); that permits INLINE code but still
#: forbids any REMOTE script/style, so the no-remote-asset guarantee holds. Tightening to a strict
#: ``script-src 'self'`` (after moving the two handlers to addEventListener) is a tracked follow-up.
_CSP = (
    "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
    "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
    "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
)
#: Security headers added to every response (CSP enforces the air-gap; nosniff/Referrer/Frame
#: are free hardening for the CUI threat model — the operator analyzes opposing-party files).
_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

#: FastAPI defaults for the optional repeated-string query params (the S-curve per-chart filter's
#: cf/cv). Each param needs its OWN ``Query`` instance: FastAPI binds the field's query key from the
#: FieldInfo, so sharing one instance across two params silently aliases the second to the first's
#: key (cv would read cf's values). Module-level singletons still dodge a call-in-default (ruff B008).
_CF_QUERY = Query(default_factory=list)
_CV_QUERY = Query(default_factory=list)


def create_app(
    state: SessionState | None = None,
    *,
    auto_shutdown: bool = False,
    idle_grace: float = 600.0,
    ollama: OllamaLauncher | None = None,
) -> FastAPI:
    """Build the FastAPI app. ``state`` lets a test/launcher inject a fresh session.

    ``auto_shutdown`` (set by the desktop launcher) makes :func:`serve` run a watchdog that
    stops the server once the browser stops sending heartbeats for ``idle_grace`` seconds —
    so closing the window turns the whole tool off. ``request_shutdown`` is wired by
    :func:`serve`; the in-page "Quit" control and the watchdog both call it.

    ``idle_grace`` defaults to **600s (10 minutes)** of no heartbeat before the tool times out
    (ADR-0120). The page beats every 3s, but browsers throttle timers in a backgrounded/minimized
    tab — so a short grace would shut a still-open tool down when it was merely in the background.
    Ten minutes also lets the operator navigate away briefly (or let the laptop sleep) and come
    back to the same session. The in-page **Quit** control still stops it immediately.

    ``ollama`` (passed by the desktop launcher) is the Ollama process manager. It is started
    **lazily** — only when the operator turns the Ollama backend on in AI Settings — and stopped
    on tool close, so the tool never spins Ollama up for a session that never uses the AI (ADR-0122).
    """
    # Law 1, at every construction path (desktop launcher, `run()`, tests, embedding):
    # activate the CUI-redacting JSON log handler on the `schedule_forensics` namespace
    # (idempotent), then fail closed if a forbidden egress-capable dependency or cloud SDK
    # reached the runtime — the app refuses to build rather than serve with a leak path.
    configure_logging()
    assert_local_only()
    app = FastAPI(title="POLARIS", docs_url=None, redoc_url=None)
    app.state.session = state if state is not None else SessionState()
    app.state.auto_shutdown = auto_shutdown
    app.state.idle_grace = idle_grace
    app.state.ollama = ollama  # lazy-started on AI enable, stopped on close (None in tests)
    app.state.last_beat = time.monotonic()
    app.state.browser_seen = False  # armed once the first heartbeat arrives
    app.state.shutting_down = False
    app.state.request_shutdown = None  # set by serve() to flip the server's should_exit
    app.state.active_requests = 0  # in-flight work holds the auto-shutdown watchdog
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.middleware("http")
    async def _liveness(request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        # A long import (several real .mpp files spawning Java) once starved the heartbeat
        # and the watchdog killed the server MID-LOAD. Any request in flight is proof the
        # operator is here: count it (the watchdog waits) and refresh the beat on completion.
        app.state.active_requests += 1
        try:
            response: Response = await call_next(request)
            for key, value in _SECURITY_HEADERS.items():
                response.headers.setdefault(key, value)  # CSP/nosniff on every response (Law 1)
            if request.url.path.startswith("/static/"):
                # Always revalidate vendored assets (cheap 304s stay). StaticFiles sends no
                # Cache-Control, so browsers heuristically cache JS/CSS — after an upgrade a
                # deployed install (fixed port = same cache origin) could keep executing the
                # OLD asset for days. Belt to the ?v= cache-busting braces in _bust_static.
                response.headers.setdefault("Cache-Control", "no-cache")
            return response
        finally:
            app.state.active_requests -= 1
            app.state.last_beat = time.monotonic()

    def session() -> SessionState:
        s: SessionState = app.state.session
        return s

    @app.post("/api/heartbeat")
    def heartbeat() -> JSONResponse:
        app.state.last_beat = time.monotonic()
        app.state.browser_seen = True
        return JSONResponse({"ok": True})

    @app.get("/api/system")
    def system_snapshot() -> JSONResponse:
        """Live LOCAL machine telemetry for the HUD dock (sysmon.js) — CPU/RAM/disk/GPU/temps.

        Local reads only (/proc, /sys, shutil, optional psutil, optional nvidia-smi) — nothing
        network-facing, so Law 1 is untouched; fields a platform can't provide are null."""
        from schedule_forensics.web import system as _system  # local: optional-psutil module

        return JSONResponse(_system.snapshot(), headers={"Cache-Control": "no-store"})

    @app.post("/api/shutdown")
    def shutdown() -> JSONResponse:
        shutdown_offload()  # tear down the SRA worker process, if one was started
        _trigger_shutdown(app)
        return JSONResponse({"stopping": True})

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        st = session()
        flash = _flash_html(st.flash)
        st.flash = None  # one-shot: clear after rendering
        rows = "".join(
            f'<tr><td><a href="/analysis/{quote(name)}">{_e(name)}</a></td>'
            f"<td>{len(non_summary(sch))}</td><td class=muted>{_e(sch.source_file or '-')}</td>"
            f'<td class=row-actions><a href="/analysis/{quote(name)}">Open report</a>'
            f' &middot; <a href="/card/{quote(name)}">Card</a>'
            f' &middot; <a href="/wbs/{quote(name)}">WBS</a>'
            f' &middot; <a href="/download/{quote(name)}.json">Save .json</a></td></tr>'
            for name, sch in st.ordered_versions()  # earliest -> latest data date
        )
        loaded = (
            "<div class=panel><h2>Schedule health</h2>"
            "<p class=muted>A health snapshot per loaded schedule &mdash; activity status mix, "
            "critical-path exposure, computed finish vs. baseline, and the DCMA-14 checks at a "
            "glance. Click any card to dive into its full report.</p>"
            "<div id=dashboardHealth class=dash-cards></div></div>"
            '<script src="/static/dashboard.js"></script>'
            "<div class=panel><h2>Loaded schedules</h2>"
            "<table><tr><th scope=col>Schedule</th><th scope=col>Activities</th><th scope=col>Source</th><th scope=col></th></tr>"
            f"{rows}</table>"
            + (
                '<p style="margin-top:14px"><a class=btn-link href="/briefing">'
                "Executive briefing &rarr;</a>"
                + (
                    ' &middot; <a class=btn-link href="/trend">Trend across all versions &rarr;</a>'
                    ' &middot; <a class=btn-link href="/cei">Bow Wave / CEI &rarr;</a>'
                    ' &middot; <a class=btn-link href="/curves">Finish &amp; slippage curves &rarr;</a>'
                    ' &middot; <a class=btn-link href="/evolution">Critical-path evolution &rarr;</a>'
                    ' &middot; <a class=btn-link href="/compare">Compare the two most recent &rarr;</a>'
                    if len(st.schedules) >= 2
                    else ""
                )
                + "</p>"
            )
            + "</div>"
            if rows
            else ""
        )
        body = f"""
{flash}
<section class=hero>
  <h2>Forensic schedule analysis &mdash; entirely on your machine</h2>
  <p class=muted>Open or import a Microsoft&nbsp;Project / Primavera schedule to get a DCMA-14 audit,
  schedule-quality&nbsp;&amp;&nbsp;schedule-risk metrics, driving-path and manipulation-trend analysis,
  and a cited AI narrative &mdash; nothing leaves this computer.</p>
</section>
{_role_strip(st)}
<div class=panel>
  <div id=dropzone class=dropzone>
    <div class=dz-icon>&#8682;</div>
    <p class=dz-title>Drop schedules here, or
      <button type=button class=linkbtn id=pickBtn>choose files&hellip;</button>
      <span class=muted>&middot;</span>
      <button type=button class=linkbtn id=pickFolderBtn>choose a folder&hellip;</button></p>
    <p class=muted>Microsoft Project <code>.mpp</code> / <code>.mpt</code>, MS Project XML
      <code>.xml</code>, Primavera <code>.xer</code>, or the tool's own <code>.json</code>.
      Load any number of files, or a whole folder (nested sub-folders and all) &mdash; a folder is
      one Project and every schedule inside it is a version.</p>
    <div class=dz-actions>
      <form id=exampleForm action="/example" method=post><button type=submit class=btn>Load example</button></form>
      <span class=muted>or import your own above</span>
    </div>
  </div>
  <form id=uploadForm action="/upload" method=post enctype="multipart/form-data" hidden>
    <input id=fileInput type=file name=files multiple accept="{_ACCEPT}">
    <input id=folderInput type=file name=files multiple webkitdirectory>
    <input id=fileMeta type=hidden name=file_meta value="">
  </form>
  <div id=uploadNotice class="notice warn" hidden role=alert></div>
</div>
<div id=loadOverlay class=load-overlay hidden role=status aria-live=assertive aria-hidden=true>
  <div class=load-card>
    <div class=load-spinner aria-hidden=true></div>
    <p class=load-title>Loading your project(s)&hellip;</p>
    <p class=muted>Importing and analyzing &mdash; large files can take a moment. The tool is
      working, not stuck.</p>
  </div>
</div>
{loaded}
<script src="/static/home.js"></script>"""
        tip = _guide(
            "dash-start",
            "Load two or more versions of the same schedule to unlock the cross-version views "
            "(Trend, Compare, Critical-Path Evolution, manipulation signals). Every chart has a "
            "'What am I looking at?' explainer at the top, and every metric links to its "
            "definition in the Metric Dictionary.",
        )
        return _page(st, "Dashboard", tip + body)

    @app.get("/api/dashboard")
    def dashboard_json() -> JSONResponse:
        return JSONResponse(_dashboard_data(session()))

    @app.post("/example")
    def load_example() -> RedirectResponse:
        st = session()
        schedule = parse_json(_EXAMPLE).model_copy(update={"source_file": "house_build.json"})
        key = _unique_key(_clean_key(schedule.name), st.schedules)
        st.schedules[key] = schedule
        logger.info("loaded bundled example schedule")
        return RedirectResponse(url=f"/analysis/{quote(key)}", status_code=303)

    @app.get("/download/{name}")
    def download_json(name: str) -> Response:
        st = session()
        key = name[:-5] if name.endswith(".json") else name
        sch = st.schedules.get(key)
        if sch is None:
            return Response("not found", status_code=404)
        filename = _safe_filename(f"{key}.json")
        return Response(
            to_json_text(sch),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/upload")
    def upload(
        request: Request,
        files: list[UploadFile],
        file_meta: str = Form(""),
        skipped_files: str = Form(""),
    ) -> Response:
        # sync on purpose: parsing runs in the threadpool, so the event loop keeps serving
        # heartbeats and pages while big native .mpp files import (Java subprocess each). No file
        # count cap (v4 grouped ingestion): a whole recursive folder of a project's versions loads
        # in one go. `file_meta` is the client's per-file companion JSON (webkitRelativePath +
        # last-modified), aligned to the upload order — the folder/version-order signal the raw
        # multipart cannot carry. `skipped_files` is the client's list of files it could NOT read
        # (an un-hydrated OneDrive placeholder / a file open in MS Project): home.js pre-reads each
        # file and drops the unreadable ones so one bad file no longer aborts the whole upload at the
        # browser network layer (Chrome ERR_ACCESS_DENIED) — they are reported here instead.
        st = session()
        cache = get_default_cache()  # content-hash keyed parse cache (v4 Feature 2; fails soft)
        accepted: list[str] = []
        errors: list[str] = []
        ignored = 0  # non-schedule files inside a folder upload (skipped, not errored)
        upload_exts = {e.lower() for e in supported_extensions()}
        meta = _parse_upload_meta(file_meta)  # per-file (top-folder or None, mtime or None)
        # one heap-capped JVM for every native .mpp in this ingest (v4 Feature 2) instead of a fresh
        # java process per file — one boot for a whole folder, not thousands. Harmless for text
        # formats (they never touch the JVM) and for a cache-hit re-upload (it never parses).
        with mpxj_batch_session():
            for i, upload_file in enumerate(files):
                name = upload_file.filename or "schedule"
                # a folder upload sweeps in every file; silently skip anything that isn't a schedule
                # (the operator cares only about the schedule files) — checked before any read
                if Path(name).suffix.lower() not in upload_exts:
                    ignored += 1
                    continue
                # read one byte past the cap: whole-file reads are memory-bound, so an oversized file
                # is rejected with a named reason instead of exhausting RAM (QC audit INFO; 500 MB
                # comfortably exceeds any real schedule export)
                data = upload_file.file.read(_MAX_UPLOAD_BYTES + 1)
                if len(data) > _MAX_UPLOAD_BYTES:
                    errors.append(
                        f"{name}: exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB per-file cap"
                    )
                    logger.warning("rejected oversized upload; ext=%s", Path(name).suffix)
                    continue
                # identical bytes under the same engine version skip the (possibly JVM-bound) parse:
                # a cache hit returns the exact same parsed model, so re-uploading a folder of a
                # project's versions is cheap. A cache miss / error just recomputes (fails soft).
                chash = content_hash(data)
                schedule = cache.get_schedule(chash)
                if schedule is None:
                    try:
                        schedule = _parse_upload(name, data)
                    except (ImporterError, ValueError, OSError) as exc:
                        reason = str(exc).splitlines()[0][:160] if str(exc) else "unreadable file"
                        errors.append(f"{name}: {reason}")
                        logger.warning(
                            "rejected upload; ext=%s bytes=%d", Path(name).suffix, len(data)
                        )
                        continue
                    cache.put_schedule(chash, schedule)
                key = _unique_key(_clean_key(name), st.schedules)
                st.schedules[key] = schedule.model_copy(update={"source_file": name})
                st.file_meta[key] = meta[i] if i < len(meta) else (None, None)
                # lets the Portfolio read this version's on-disk summary
                st.content_hashes[key] = chash
                accepted.append(key)
        notices = list(_grouping_notices(st.projects())) if accepted else []
        if ignored:
            plural = "file" if ignored == 1 else "files"
            notices.append(f"Skipped {ignored} non-schedule {plural} in the selection.")
        # files the browser could not read (OneDrive cloud-only placeholder, or open in MS Project):
        # reported, not silently lost, with the concrete self-service fix
        client_skipped = _parse_skipped_files(skipped_files)
        if client_skipped:
            shown = ", ".join(client_skipped[:5])
            more = f" (+{len(client_skipped) - 5} more)" if len(client_skipped) > 5 else ""
            plural = "file" if len(client_skipped) == 1 else "files"
            notices.append(
                f"Could not read {len(client_skipped)} {plural}: {shown}{more}. "
                "This usually means the file is online-only in OneDrive or open in Microsoft "
                "Project. In File Explorer right-click it → 'Always keep on this device', close "
                "Microsoft Project, then re-add it."
            )
        # v4 Feature 2: a non-blocking RAM notice once the loaded set's estimate crosses the
        # operator's threshold — the tool keeps schedules resident for comparative analysis, so a
        # very large folder is worth flagging (never gating). Raise the threshold in Portfolio.
        if accepted:
            est = estimate_resident_bytes(st.schedules.values())
            if est > st.ram_warn_bytes:
                notices.append(
                    f"Loaded schedules use an estimated {format_bytes(est)} of memory "
                    f"(warn threshold {format_bytes(st.ram_warn_bytes)}). You can keep working; "
                    f"adjust the threshold on the Portfolio page if this is expected."
                )
        logger.info(
            "loaded %d schedule(s); %d rejected; %d non-schedule skipped; total now %d",
            len(accepted),
            len(errors),
            ignored,
            len(st.schedules),
        )
        st.flash = _Flash(accepted=tuple(accepted), errors=tuple(errors), notices=tuple(notices))
        # a single clean open jumps straight to its report (one file is unambiguous — a title-less
        # loose file's needs-attention flag can wait for /portfolio); but a folder ingest that also
        # skipped non-schedule OR unreadable files goes to the dashboard so its manifest is seen.
        # v4 F4 (ADR-0255): a CLEAN ingest lands on the active role's primary page when one is
        # set (e.g. Auditor → /standards, PM → /portfolio); any errors/skips still land on the
        # dashboard so the ingest manifest is always seen — disclosure outranks the role landing.
        clean = bool(accepted) and not errors and not ignored and not client_skipped
        role_landing = (
            _ROLE_BY_ID[st.role].landing if st.role is not None and st.role in _ROLE_BY_ID else None
        )
        if clean and role_landing:
            dest = role_landing
        elif len(accepted) == 1 and clean:
            dest = f"/analysis/{quote(accepted[0])}"
        else:
            dest = "/"
        # home.js posts with X-SF-Ajax and navigates to `redirect` itself: a fetch (not a full-page
        # form.submit) means a browser-side read failure surfaces as a catchable error in-app
        # instead of nuking the page to Chrome's ERR_ACCESS_DENIED. The server-side flash still
        # renders on the followed GET, so the single-open jump + import manifest both survive.
        if request.headers.get("x-sf-ajax"):
            return JSONResponse(
                {
                    "redirect": dest,
                    "accepted": len(accepted),
                    "errors": len(errors),
                    "skipped_unreadable": len(client_skipped),
                }
            )
        return RedirectResponse(url=dest, status_code=303)

    @app.get("/analysis/{name}", response_class=HTMLResponse)
    def analysis(name: str, erosion_field: str | None = Query(None)) -> HTMLResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return _page(st, name, _unschedulable_panel(sch, exc))
        # Render the DETERMINISTIC narrative immediately so the report opens at once; ai_polish.js
        # fetches /api/ai/narrative in the background and swaps in the local-AI-polished prose when a
        # model is active. The old synchronous per-statement generate here blocked the whole render
        # for minutes on a slow local model — a big .mpp landing on /analysis with a 72B Ollama active
        # looked exactly like "the file won't load" (the browser tab just kept spinning).
        return _page(
            st,
            name,
            _analysis_body(
                name,
                sch,
                analysis,
                st.target_uid,
                erosion_field=erosion_field,
                margin_confirmed=st.margin_overlay.get(name),
            ),
            ask_schedule=name,
            chapter=_CHAPTER_BY_NUM.get(
                "01"
            ),  # "Where we stand" (dynamic title → explicit chapter)
            focus_file=name,
        )

    @app.get("/card/{name}", response_class=HTMLResponse)
    def schedule_card(name: str) -> HTMLResponse:
        """The deck's *Metrics* page (PBIX page 1): the schedule's ID card."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return _page(st, name, _unschedulable_panel(sch, exc), ask_schedule=name)
        focus = _target_panel(sch, analysis, st.target_uid) if st.target_uid is not None else ""
        return _page(
            st, f"{name} — card", focus + _card_body(name, sch, analysis), ask_schedule=name
        )

    @app.get("/wbs/{name}", response_class=HTMLResponse)
    def wbs_breakdown_view(name: str) -> HTMLResponse:
        """The deck's *Completion Metrics* + *SPI and Earned Schedule* pages (PBIX 8, 9):
        the completion family and Earned Schedule pivoted by WBS."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        groups = compute_wbs_breakdown(sch)
        focus = ""
        if st.target_uid is not None:
            try:
                focus = _target_panel(sch, st.analysis_for(name, sch), st.target_uid)
            except CPMError:
                focus = ""  # unschedulable: skip the focus panel, still show the WBS pivot
        return _page(st, f"{name} — WBS", focus + _wbs_body(name, groups), ask_schedule=name)

    @app.get("/api/wbs/{name}")
    def wbs_json(name: str) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(_wbs_data(compute_wbs_breakdown(sch)))

    @app.get("/api/analysis/{name}")
    def analysis_json(name: str) -> JSONResponse:
        st = session()
        key, sch = _find_schedule(st, name)  # accept the session key OR the display label
        if key is None or sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            analysis = st.analysis_for(key, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_analysis_data(sch, analysis))

    @app.get("/api/driving/{name}")
    def driving_json(
        name: str,
        target: int = Query(...),
        secondary: int = Query(10),
        tertiary: int = Query(20),
        direction: str = Query("predecessors"),
        range_mode: str = Query("all"),
        range_days: int = Query(0),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
        drag: int = Query(0),
    ) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            cpm = st.analysis_for(name, sch).cpm
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        # pair the schedule with the SAME scope as its cpm: analysis_for computes cpm over
        # st.scope(sch), so tracing the raw (unscoped) network against that scoped cpm would mix a
        # filtered/target-truncated timing set onto the full task list (wrong path once a session
        # Analysis Target or filter is active). scope(sch) is sch when neither is set (unchanged).
        scoped = st.scope(sch)
        payload = _driving_data(
            scoped,
            cpm,
            target,
            secondary,
            tertiary,
            direction=direction,
            range_mode=range_mode,
            range_days=range_days,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
            with_drag=bool(drag),
        )
        # HIGHLIGHT mode (feature #10): the session filter's match set for THIS file, so the grid
        # marks matching rows/bars instead of dropping non-matches (None when not highlighting).
        marked = st.highlight_uids(sch)
        if marked is not None:
            payload["highlight_uids"] = sorted(marked)
        return JSONResponse(payload)

    @app.get("/standards", response_class=HTMLResponse)
    def standards_view() -> HTMLResponse:
        """Standards & Execution Indices: DCMA-14, the NASA/Acumen-Fuse execution indices, and
        the Schedule Execution Metrics (SEM) family — one formula-first row per metric."""
        st = session()
        versions = st.ordered_versions()
        if not versions:
            return _page(
                st,
                "Standards & Execution Indices",
                "<div class=panel>Load a schedule to see the DCMA-14, NASA/Acumen-Fuse, and "
                "Schedule Execution Metrics scorecards with their formulas and sources.</div>",
            )
        key, sch = versions[-1]  # the latest data date carries the current standing
        prior = versions[-2][1] if len(versions) > 1 else None
        try:
            analysis = st.analysis_for(key, sch)
        except CPMError as exc:
            return _page(
                st,
                "Standards & Execution Indices",
                f"<div class=panel>Network cannot be solved: {_e(exc)}</div>",
            )
        return _page(
            st,
            "Standards & Execution Indices",
            _standards_body(st, key, sch, prior, analysis),
        )

    @app.get("/portfolio", response_class=HTMLResponse)
    def portfolio() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Portfolio",
                "<div class=panel>Load schedules, or a whole project folder, to see the portfolio "
                "rollup &mdash; every project across the session at a glance.</div>",
            )
        return _page(st, "Portfolio", _portfolio_body(st))

    @app.get("/mission", response_class=HTMLResponse)
    def mission_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Mission Control",
                "<div class=panel>Load a schedule to populate the visual wall.</div>",
            )
        return _page(
            st,
            "Mission Control",
            _export_bar("mission") + _sources_line(st.ordered()) + _mission_body(st.target_uid),
        )

    @app.get("/compare", response_class=HTMLResponse)
    def compare() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Compare", "<div class=panel>Load at least two versions to compare.</div>"
            )
        # Forensic order is by data date (the Acumen/SSI ProjectTimeNow pattern), not load
        # order; unschedulable versions (e.g. a logic cycle) are skipped, never a 500.
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Compare",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to compare.</div>",
            )
        prior, current = schedules[-2], schedules[-1]
        body = (
            _what_changed_header(prior, current, cpms[-2], cpms[-1])
            + _export_bar("compare")
            + _skipped_notice(skipped)
            + _sources_line([prior, current])
            + _compare_body(prior, current, cpms[-2], cpms[-1])
        )
        if st.target_uid is not None:
            body += _focus_panel([prior, current], [cpms[-2], cpms[-1]], st.target_uid)
        return _page(st, "Compare", body)

    def _solvable_versions() -> tuple[list[Schedule], list[CPMResult], list[str]]:
        """Ordered (schedules, cpms) for every loaded version whose network solves,
        plus the names of versions skipped (e.g. a logic cycle) — multi-version views
        must degrade to the analyzable subset, never 500 on one bad file."""
        st = session()
        schedules: list[Schedule] = []
        cpms: list[CPMResult] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                cpms.append(st.analysis_for(key, sch).cpm)
                schedules.append(
                    st.scope(sch)
                )  # the CPM is for the scoped schedule; keep them paired
            except CPMError:
                skipped.append(key)
        return schedules, cpms, skipped

    def _solvable_versions_full() -> tuple[
        list[Schedule], list[CPMResult], list[_Analysis], list[str]
    ]:
        """Like _solvable_versions() but also returns the cached _Analysis objects."""
        st = session()
        schedules: list[Schedule] = []
        cpms: list[CPMResult] = []
        analyses: list[_Analysis] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                a = st.analysis_for(key, sch)
                schedules.append(st.scope(sch))  # paired with a.cpm (both over the active scope)
                cpms.append(a.cpm)
                analyses.append(a)
            except CPMError:
                skipped.append(key)
        return schedules, cpms, analyses, skipped

    def _skipped_notice(skipped: list[str]) -> str:
        if not skipped:
            return ""
        names = ", ".join(_e(s) for s in skipped)
        return (
            f'<div class="notice err">Skipped (network cannot be solved — see each report '
            f"for the reason): {names}</div>"
        )

    @app.get("/path", response_class=HTMLResponse)
    def path_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Path Analysis",
                "<div class=panel>Load a schedule to run the path analysis.</div>",
            )
        keys = [k for k, _ in st.ordered_versions()]
        header = ""
        if keys:  # anchor "What drives the date" on the latest version (ADR-0199)
            lkey = keys[-1]
            try:
                header = _what_drives_header(
                    st.schedules[lkey], st.analysis_for(lkey, st.schedules[lkey])
                )
            except CPMError:
                header = ""
        return _page(st, "Path Analysis", header + _path_body(keys, st.target_uid))

    def _ask_response(
        st: SessionState, facts: tuple[CitedStatement, ...], text: str
    ) -> JSONResponse:
        """Shared Q&A response: route the backend(s), answer in the configured mode.

        With a cross-check second model configured and reachable, BOTH models answer
        independently and a deterministic figure-agreement note is computed — the
        engine compares, never a third model."""
        mode = st.ai_config.qa_mode
        answer, used = answer_question(_active_backend(st), facts, text, mode=mode)
        second_answer: str | None = None
        second_model: str | None = None
        agreement: str | None = None
        second = _second_backend(st)
        if second is not None:
            second_answer, _ = answer_question(second, facts, text, mode=mode)
            second_model = f"{second.name}/{getattr(second, 'model', '') or 'default'}"
            if answer and second_answer:
                agreement = figure_agreement(answer, second_answer)
        return JSONResponse(
            {
                "answer": answer,  # null => no local model active / answer failed the gate
                "mode": mode,
                "second_answer": second_answer,
                "second_model": second_model,
                "agreement": agreement,
                "facts": [
                    {
                        "text": f.text,
                        "citations": [
                            {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                            for c in f.citations[:3]
                        ],
                    }
                    for f in used
                ],
            }
        )

    def _schedule_facts(st: SessionState, name: str, sch: Schedule) -> tuple[CitedStatement, ...]:
        analysis = st.analysis_for(name, sch)
        return build_fact_sheet(
            sch,
            analysis.cpm,
            analysis.audit,
            analysis.findings,
            analysis.float_bands,
            analysis.completion,
            compute_finish_forecasts(sch, analysis.cpm),
        )

    @app.post("/api/ask/{name}")
    def ask(name: str, question: str = Form("")) -> JSONResponse:
        """Grounded Q&A on ONE schedule: engine facts; the configured mode governs prose."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        text = question.strip()[:500]
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        try:
            facts = _schedule_facts(st, name, sch)
            facts += driving_path_facts(sch, st.analysis_for(name, sch).cpm, text)
            schedules, cpms, _skipped = _solvable_versions()
            if len(schedules) >= 2:
                facts += manipulation_forensics_facts(schedules, cpms, target_uid=st.target_uid)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _ask_response(st, facts, text)

    @app.post("/api/ask")
    def ask_workbook(question: str = Form("")) -> JSONResponse:
        """Grounded Q&A across EVERY loaded version (the multi-version pages' panel)."""
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "not found"}, status_code=404)
        text = question.strip()[:500]
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        if len(st.schedules) == 1:
            key, sch = next(iter(st.schedules.items()))
            try:
                facts = _schedule_facts(st, key, sch)
                facts += driving_path_facts(sch, st.analysis_for(key, sch).cpm, text)
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            return _ask_response(st, facts, text)
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "no analyzable versions loaded"}, status_code=422)
        # driving-path questions resolve against the newest analyzable version
        facts = build_workbook_fact_sheet(schedules, cpms)
        facts += driving_path_facts(schedules[-1], cpms[-1], text)
        # cross-version manipulation forensics (ADR-0150): duration cuts on the driving/
        # critical path, the reverted-changes counterfactual, the focus's baseline variance —
        # so "what was shortened to keep UID X from slipping?" is answerable with citations
        facts += manipulation_forensics_facts(schedules, cpms, target_uid=st.target_uid)
        return _ask_response(st, facts, text)

    @app.get("/api/driving-path")
    def driving_path_answer(uid: int = Query(...), scope: str = Query("")) -> JSONResponse:
        """One-click DETERMINISTIC driving-path answer for a UID — engine only, NO AI. The Ask
        panel's "Driving path" button calls this so the operator never depends on the model for
        path/slack (the model kept getting it wrong); the figures come straight from the engine."""
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "no schedule loaded"}, status_code=400)
        key = scope.strip()
        if key and key in st.schedules:
            raw = st.schedules[key]
            try:
                cpm = st.analysis_for(key, raw).cpm
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            sch = st.scope(raw)  # pair with analysis_for's scoped cpm (see /api/driving)
        else:
            schedules, cpms, _skipped = _solvable_versions()
            if not schedules:
                return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=422)
            sch, cpm = schedules[-1], cpms[-1]
        facts = driving_path_summary(sch, cpm, uid)
        if not facts:
            return JSONResponse(
                {
                    "uid": uid,
                    "answer": f"UID {uid} is not a scheduled activity in this file.",
                    "facts": [],
                }
            )
        return JSONResponse(
            {
                "uid": uid,
                "answer": " ".join(f.text for f in facts),
                "facts": [
                    {
                        "text": f.text,
                        "citations": [
                            {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                            for c in f.citations[:12]
                        ],
                    }
                    for f in facts
                ],
            }
        )

    @app.get("/trend", response_class=HTMLResponse)
    def trend_view(target: str | None = Query(None)) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Trend",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to see a trend.</div>",
            )
        # an explicit ?target= (even blank, from the Focus form) wins; otherwise the
        # session-wide target focuses the trend automatically
        uid = _parse_uid(target) if target is not None else st.target_uid
        return _page(
            st,
            "Trend",
            _how_it_moved_header(schedules, cpms)
            + _export_bar("trend")
            + _skipped_notice(skipped)
            + _sources_line(schedules)
            + _trend_body(schedules, cpms, uid),
        )

    @app.get("/api/trend")
    def trend_json(target: str | None = Query(None)) -> JSONResponse:
        st = session()
        schedules, cpms, analyses, _skipped = _solvable_versions_full()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        return JSONResponse(_trend_data(schedules, cpms, analyses, uid))

    @app.get("/api/margin")
    def margin_json() -> JSONResponse:
        """Schedule-margin burndown across versions: total vs effective buffer per submission.

        Iterates the loaded versions (oldest -> newest by data date), skipping any whose network
        cannot be solved, and reports each version's total and effective margin (working days) over
        the active scope. ``{"versions": []}`` when nothing analyzable is loaded.
        """
        st = session()
        rows: list[tuple[str, str | None, Schedule, CPMResult]] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                continue
            status = raw.status_date.date().isoformat() if raw.status_date else None
            rows.append((raw.source_file or raw.name, status, st.scope(raw), a.cpm))
        if not rows:
            return JSONResponse({"versions": []})
        points = compute_margin_trend(rows, margin_uids=st.confirmed_margin_union())
        return JSONResponse(
            {
                "versions": [
                    {
                        "label": p.label,
                        "status_date": p.status_date,
                        "total": p.total_margin_days,
                        "effective": p.effective_margin_days,
                    }
                    for p in points
                ]
            }
        )

    @app.get("/margin", response_class=HTMLResponse)
    def margin_view(rate: float | None = Query(None)) -> HTMLResponse:
        st = session()
        if rate is not None:
            st.set_margin_rate(rate)  # F3c: operator-set Gold-Rule requirement rate (fail-soft)
        if not st.schedules:
            return _page(
                st,
                "Margin Dashboard",
                "<div class=panel>Load one or more monthly schedule versions to see the NASA "
                "margin/contingency burn-down and the margin-erosion trend.</div>",
            )
        return _page(st, "Margin Dashboard", _margin_dashboard_body(st))

    @app.get("/api/margin/dashboard")
    def margin_dashboard_json() -> JSONResponse:
        st = session()
        d = _margin_dashboard_for(st)
        data = _margin_dashboard_data(d)
        data["band"] = _band_payload(st, d)  # the Fig 5-30 overlay (None until dates entered)
        return JSONResponse(data)

    @app.post("/margin/confirm")
    async def margin_confirm(request: Request) -> RedirectResponse:
        """Persist (or reset) the operator's confirmed schedule-margin set for one loaded version (F3b).

        ``action="reset"`` drops the overlay for ``key`` (revert to the name-based default);
        ``action="confirm"`` stores the ticked UniqueIDs as this version's margin set — an explicitly
        empty tick list is a deliberate "no margin" stored as an empty frozenset (NOT a reset), so the
        dashboard honors it. Only real non-summary UIDs present in the version are kept; unknown /
        summary UIDs are dropped. Redirects back to the version's analysis page (multi-value ``uid``
        checkboxes are read straight off the form body, so there is no list default to worry about)."""
        form = await request.form()
        key = str(form.get("key", ""))
        action = str(form.get("action", "confirm"))
        back = str(form.get("back", ""))
        raw_uids = form.getlist("uid")
        st = session()
        with st._lock:
            sch = st.schedules.get(key)
            if sch is not None:
                if action == "reset":
                    st.margin_overlay.pop(key, None)
                else:
                    valid: set[int] = set()
                    for raw in raw_uids:
                        u = _parse_uid(str(raw))
                        if u is None:
                            continue
                        t = sch.tasks_by_id.get(u)
                        if t is not None and not t.is_summary:
                            valid.add(u)
                    st.margin_overlay[key] = frozenset(valid)
        dest = back if back.startswith("/analysis/") else f"/analysis/{quote(key, safe='')}"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/margin/band")
    async def margin_band(request: Request) -> RedirectResponse:
        """Persist the operator's Fig 5-30 guideline band + sufficiency thresholds (ADR-0254).

        ``action="clear"`` drops the phase dates (the band disappears; rates/thresholds reset to
        the cited defaults). Otherwise the four phase dates, six band rates, and two percentile
        thresholds are read off the form; each piece is validated fail-soft by the SessionState
        setters — an invalid piece keeps the current value, it never wipes the setting."""
        form = await request.form()
        st = session()
        if str(form.get("action", "apply")) == "clear":
            st.set_margin_band(None, FIG_5_30_DEFAULT_RATES)
            st.set_margin_risk_pcts(DEFAULT_WATCH_PCT, DEFAULT_CORRECTIVE_PCT)
            return RedirectResponse(url="/margin", status_code=303)
        dates: tuple[str, str, str, str] = (
            str(form.get("phase0", "")).strip(),
            str(form.get("phase1", "")).strip(),
            str(form.get("phase2", "")).strip(),
            str(form.get("phase3", "")).strip(),
        )
        rates: list[tuple[float, float]] = []
        for i in range(3):
            try:
                rates.append(
                    (float(str(form.get(f"low{i}", ""))), float(str(form.get(f"high{i}", ""))))
                )
            except ValueError:
                rates.append((-1.0, -1.0))  # invalid row -> setter rejects the whole rate set
        st.set_margin_band(
            dates if all(dates) else None if not any(dates) else st.margin_band_dates,
            tuple(rates),
        )
        with contextlib.suppress(ValueError):  # fail-soft: keep the current thresholds
            st.set_margin_risk_pcts(
                float(str(form.get("watch_pct", ""))), float(str(form.get("ca_pct", "")))
            )
        return RedirectResponse(url="/margin", status_code=303)

    def _margin_risk_data(
        st: SessionState, iterations: int = 1000, distribution: str = "triangular"
    ) -> dict[str, object]:
        """The §7.3.3.2.3 risk-based margin-sufficiency read (F3c tier-b, ADR-0254) — shared by
        the API route and the Excel/Word export (identical results by seeded determinism).

        Runs the seeded SSI SRA through the same path as ``/api/sra/ssi``, computes the
        deterministic margin window ``[E, D]`` EXACTLY on the run's own all-ML axis via
        ``sra.deterministic_margin_bounds`` (the confirmed margin overlay, else the name-based
        default set), and reads the stored CDF against it. Every parameter is echoed for the
        provenance chip and the export. Fail-soft: no schedule / a raised run / a degenerate
        (point-mass) distribution each return an honest disclosure (an ``error`` or flagged
        payload), never a fabricated verdict."""
        chosen = _sra_selected(st)
        if chosen is None:
            return {"error": "No analyzable schedule loaded."}
        key, sch, _cpm = chosen
        # the margin set: this version's confirmed overlay, else the cross-version union, else the
        # name-based default — the same precedence the margin dashboard uses
        confirmed = st.margin_overlay.get(key, st.confirmed_margin_union())
        if confirmed is not None:
            margin_uids = frozenset(confirmed)
        else:
            from schedule_forensics.engine.metrics.margin import is_margin_task

            margin_uids = frozenset(t.unique_id for t in non_summary(sch) if is_margin_task(t))
        cfg = SRAConfig(
            iterations=max(100, min(10000, iterations)),
            distribution="pert" if distribution == "pert" else "triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            result = run_maybe_offloaded(
                heavy,
                compute_sra_ssi,
                sch,
                config=cfg,
                three_point=_ssi_three_point(st, sch),
                risks=_schedule_risks(st),
            )
        except Exception as exc:
            return {"error": str(exc)}
        d_anchor, e_zero = deterministic_margin_bounds(sch, cfg.target_uid, margin_uids)
        watch, corrective = st.margin_risk_pcts
        wmpd = sch.calendar.working_minutes_per_day or 480
        read = margin_risk_read(
            result.cdf,
            d_anchor,
            e_zero,
            wmpd=wmpd,
            watch_pct=watch,
            corrective_pct=corrective,
        )
        cal = sch.calendar

        def _iso(offset: int) -> str:
            return offset_to_datetime(sch.project_start, offset, cal).date().isoformat()

        return {
            "file": key,
            "focus_uid": cfg.target_uid,
            "iterations": cfg.iterations,
            "seed": result.seed,
            "distribution": cfg.distribution,
            "occurrence_mode": cfg.occurrence_mode,
            "use_risk_register": cfg.use_risk_register,
            "correlation": cfg.correlation,
            "margin_task_count": len(margin_uids),
            "have_margin": bool(margin_uids) and d_anchor > e_zero,
            "covered_pct": read.covered_pct,
            "verdict": read.verdict,
            "degenerate": read.degenerate,
            "margin_wd": read.margin_wd,
            "watch_pct": read.watch_pct,
            "corrective_pct": read.corrective_pct,
            "deterministic_finish": d_anchor,
            "deterministic_finish_date": _iso(d_anchor),
            "zero_margin_finish": e_zero,
            "zero_margin_finish_date": _iso(e_zero),
            "basis_wmpd": wmpd,
            "rows": [
                {
                    "pct": r.pct,
                    "finish_offset": r.finish_offset,
                    "finish_date": _iso(r.finish_offset),
                    "delta_vs_plan_wd": r.delta_vs_plan_wd,
                    "margin_needed_wd": r.margin_needed_wd,
                    "covered": r.covered,
                }
                for r in read.rows
            ],
        }

    @app.get("/api/margin/risk")
    def margin_risk_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        """Button-triggered risk-based margin sufficiency (never on page load — SRA doctrine)."""
        data = _margin_risk_data(session(), iterations, distribution)
        if "error" in data:
            code = 400 if data["error"] == "No analyzable schedule loaded." else 422
            return JSONResponse(data, status_code=code)
        return JSONResponse(data)

    @app.get("/evm", response_class=HTMLResponse)
    def evm_view(group_field: str = Query("")) -> HTMLResponse:
        st = session()
        # per-field metric grouping, same machinery as /forecast (operator 2026-07-10: the
        # ADR-0179 forecast-calculation treatment applies to the EVM metrics too — per-group
        # indices with honest N/A, never an imputed figure)
        schedules, _cpms, _skipped = _solvable_versions()
        panel = _field_forecast_panel(schedules, group_field, action="/evm") if schedules else ""
        bar = _export_bar("evm") if schedules else ""
        return _page(st, "EVM", bar + _evm_body(st) + panel)

    @app.get("/resources", response_class=HTMLResponse)
    def resources_view(bucket: str = Query("month")) -> HTMLResponse:
        st = session()
        bar = _export_bar(f"resources?bucket={bucket}") if st.schedules else ""
        return _page(
            st,
            "Resources",
            _who_is_overloaded_header(st, bucket) + bar + _resources_body(st, bucket),
        )

    @app.get("/cei", response_class=HTMLResponse)
    def cei_view(target: str | None = Query(None), uids: str = Query("")) -> HTMLResponse:
        st = session()
        # focusing a target from this view sets the session-wide target (ADR-0061), so the
        # /api/cei fetch that draws the chart sees the same activity; a blank clears it. Go through
        # set_target (NOT a raw assignment) so the scope/analysis caches invalidate and the SRA
        # focus stays coupled — a raw write left every page scoped to the PREVIOUS target (audit).
        if target is not None:
            st.set_target(_parse_uid(target))
        if len(st.schedules) < 2:
            return _page(
                st,
                "Bow Wave / CEI",
                "<div class=panel>Load at least two versions (monthly snapshots) to run the "
                "bow-wave / CEI analysis.</div>",
            )
        track = _parse_track_uids(uids)
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid, track_uids=track)
        except ValueError as exc:
            return _page(st, "Bow Wave / CEI", f"<div class=panel>{_e(exc)}</div>")
        return _page(
            st,
            "Bow Wave / CEI",
            _work_piling_header(wave)
            + _export_bar("cei")
            + _sources_line(st.ordered())
            + _cei_body(wave, st.target_uid, track_uids=track),
        )

    @app.get("/api/cei")
    def cei_json(uids: str = Query("")) -> JSONResponse:
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid, track_uids=_parse_track_uids(uids))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_cei_data(wave, st.target_uid))

    @app.get("/scurve", response_class=HTMLResponse)
    def scurve_view(uids: str = Query("")) -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "S-Curve",
                "<div class=panel>Load a schedule to see the cumulative progress S-curve "
                "(load several versions to animate it over time).</div>",
            )
        track = _parse_track_uids(uids)
        try:
            sc = compute_s_curve(st.ordered(), track_uids=track)
        except ValueError as exc:
            return _page(st, "S-Curve", f"<div class=panel>{_e(exc)}</div>")
        return _page(
            st,
            "S-Curve",
            _export_bar("scurve" + (f"?uids={uids}" if uids else ""))
            + _scurve_body(sc, _scurve_filter_fields(st.ordered()), track_uids=track),
        )

    @app.get("/api/scurve")
    def scurve_json(
        cf: list[str] = _CF_QUERY, cv: list[str] = _CV_QUERY, uids: str = Query("")
    ) -> JSONResponse:
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "no schedule loaded"}, status_code=400)
        versions = st.ordered()
        # per-chart filter (independent of the page-wide Groups & Filters): up to MAX_FIELDS
        # (field, value) conditions over the parent file's fields, applied on top of the scope.
        criteria = _pair_criteria(cf, cv, versions)
        if criteria:
            versions = [
                v for v in (filter_schedule(s, criteria) for s in versions) if non_summary(v)
            ]
        if not versions:
            return JSONResponse({"months": [], "versions": []})
        try:
            sc = compute_s_curve(versions, track_uids=_parse_track_uids(uids))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_scurve_data(sc))

    @app.get("/ribbon", response_class=HTMLResponse)
    def ribbon_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Schedule Quality Ribbon",
                "<div class=panel>Load one or more schedules to see the "
                "schedule-quality ribbon.</div>",
            )
        rows: list[tuple[str, object, dict[str, MetricResult]]] = []
        skipped: list[str] = []
        drill: dict[str, dict[str, tuple[int, ...]]] = {}
        for key, sch in st.ordered_versions():
            try:
                analysis = st.analysis_for(key, sch)
            except CPMError:
                skipped.append(key)
                continue
            rows.append(
                (
                    key,
                    compute_ribbon(sch, analysis.cpm, analysis.audit),
                    compute_schedule_quality(sch, analysis.cpm),
                )
            )
            drill[key] = ribbon_offender_map(sch, analysis.cpm, analysis.audit)
        note = _skipped_notice(skipped) if skipped else ""
        header = ""
        if rows:  # the latest schedulable version anchors "Can we trust the plan?" (ADR-0198)
            lkey, lribbon, _lq = rows[-1]
            if isinstance(lribbon, RibbonMetrics):
                header = _can_we_trust_header(
                    st.schedules[lkey], st.analysis_for(lkey, st.schedules[lkey]), lribbon
                )
        return _page(
            st,
            "Schedule Quality Ribbon",
            header + _export_bar("ribbon") + _ribbon_body(rows, note, drill),
        )

    @app.get("/volatility", response_class=HTMLResponse)
    def volatility_view() -> HTMLResponse:
        """Critical-Path Volatility (operator 2026-07-09): ten visualizations of how the
        critical-path MEMBERSHIP churns across the loaded versions — which activities stayed
        on the path longest, which jumped off and on, and how stable the controlling chain is
        overall. Framed to the published best practice: GAO's Schedule Assessment Guide (Best
        Practice 6 — a valid, stable critical path) and the DCMA 14-point construct (the CP
        test / CPLI treat an erratic controlling chain as a health failure)."""
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "CP Volatility",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions — critical-path "
                "volatility is a cross-version analysis (membership churn over time).</div>",
            )
        return _page(
            st,
            "CP Volatility",
            _skipped_notice(skipped)
            + _sources_line(st.ordered())
            + _volatility_body(schedules, cpms),
        )

    @app.get("/export/{fmt}/volatility")
    def export_volatility(fmt: str) -> Response:
        """The per-activity volatility scoreboard (tenure / longest streak / flips) as a file."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=422)
        data = _volatility_data(schedules, cpms)
        task_rows = cast(list[dict[str, Any]], data["tasks"])
        headers = (
            "UID",
            "Activity",
            "Versions on path",
            "Longest streak",
            "Jumps (on/off flips)",
            "On path now",
            "Membership (1 = on path, oldest first)",
        )
        rows = tuple(
            (
                t["uid"],
                t["name"],
                t["tenure"],
                t["streak"],
                t["flips"],
                "yes" if t["member"][-1] else "no",
                " ".join(str(m) for m in t["member"]),
            )
            for t in task_rows
        )
        tableset = TableSet(
            "Critical-path volatility scoreboard",
            (Table("CP volatility", headers, rows),),
        )
        return _export_response(fmt, tableset, "cp-volatility")

    @app.get("/export/{fmt}/evm")
    def export_evm(fmt: str) -> Response:
        """Every loaded version's EVM indices + schedule variance + baseline compliance
        (operator 2026-07-10: every graph/table exports to Excel)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        idx_keys = ("spi_t", "spi_t_acumen", "cei_finish", "cei_start", "spi", "cpi", "tcpi")
        rows = []
        for s, c in zip(schedules, cpms, strict=True):
            indices = compute_evm_indices(s, c)
            sv = compute_schedule_variance(s, non_summary(s))
            rows.append(
                (
                    s.source_file or s.name,
                    *(
                        (indices[k].value if k in indices and indices[k].value is not None else "")
                        for k in idx_keys
                    ),
                    sv.svt_days if sv.svt_days is not None else "",
                    sv.es_days if sv.es_days is not None else "",
                )
            )
        headers = ("File", *(k.upper() for k in idx_keys), "SVt (wd)", "ES (wd)")
        tableset = TableSet("EVM indices per version", (Table("EVM", headers, tuple(rows)),))
        return _export_response(fmt, tableset, "evm")

    @app.get("/export/{fmt}/scurve")
    def export_scurve(fmt: str, uids: str = Query("")) -> Response:
        """The S-Curve dataset (per version x month cumulative planned/actual %) as a file."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        versions = st.ordered()
        if not versions:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        try:
            sc = compute_s_curve(versions, track_uids=_parse_track_uids(uids))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        rows = []
        for v in sc.versions:
            for i, month in enumerate(sc.month_labels):
                rows.append((v.label, month, v.planned[i], v.actual[i]))
        tableset = TableSet(
            "S-Curve — cumulative planned vs actual (%)",
            (
                Table(
                    "S-Curve",
                    ("File", "Month", "Planned cum %", "Actual/forecast cum %"),
                    tuple(rows),
                ),
            ),
        )
        return _export_response(fmt, tableset, "scurve")

    @app.get("/export/{fmt}/resources")
    def export_resources(fmt: str, bucket: str = Query("month")) -> Response:
        """The resource-loading dataset (per resource x period load/capacity/over) + roster."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _latest_solvable(st)
        if chosen is None:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        _key, sch, cpm = chosen
        bucket = bucket if bucket in ("day", "week", "month") else "month"
        rl = compute_resource_loading(sch, cpm, bucket)
        mpd = rl.working_minutes_per_day or 480
        series_rows = []
        for r in rl.resources:
            for per in r.series:
                series_rows.append(
                    (
                        r.name,
                        per.period,
                        round(per.load_minutes / mpd, 2),
                        round(per.capacity_minutes / mpd, 2),
                        "yes" if per.over_allocated else "",
                    )
                )
        roster_rows = tuple(
            (
                r.name,
                r.type.title(),
                r.max_units,
                round(r.total_work_minutes / mpd, 1),
                r.task_count,
                r.peak_period or "",
                len(r.over_allocated_periods),
            )
            for r in rl.resources
        )
        tableset = TableSet(
            f"Resource loading — {sch.source_file or sch.name} ({bucket})",
            (
                Table(
                    "Loading",
                    ("Resource", "Period", "Load (d)", "Capacity (d)", "Over-allocated"),
                    tuple(series_rows),
                ),
                Table(
                    "Roster",
                    (
                        "Resource",
                        "Type",
                        "Max units",
                        "Work (d)",
                        "Tasks",
                        "Peak period",
                        "Over-allocated periods",
                    ),
                    roster_rows,
                ),
            ),
        )
        return _export_response(fmt, tableset, "resources")

    @app.get("/export/{fmt}/risks")
    def export_risks(fmt: str) -> Response:
        """The Risks & Opportunities findings (severity / category / finding / citations)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        solv: list[tuple[str, Schedule, _Analysis]] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                continue
            solv.append((key, st.scope(raw), a))
        if not solv:
            return JSONResponse({"error": "load an analyzable schedule first"}, status_code=422)
        _key, current, cur_an = solv[-1]
        prior = solv[-2][1] if len(solv) >= 2 else None
        prior_cpm = solv[-2][2].cpm if len(solv) >= 2 else None
        findings = recommend(
            current, prior, current_cpm=cur_an.cpm, prior_cpm=prior_cpm, target_uid=st.target_uid
        )
        tableset = TableSet("Risks, issues & opportunities", (findings_table(findings),))
        return _export_response(fmt, tableset, "risks")

    @app.get("/export/{fmt}/mission")
    def export_mission(fmt: str) -> Response:
        """The Mission Control wall's underlying series: quality trend + critical-path
        evolution (each tile's own page carries its full export too)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=422)
        tables: list[Table] = list(trend_tables(compute_quality_trend(schedules, cpms)))
        tables.extend(path_evolution_tables(compute_path_evolution(schedules, cpms)))
        tableset = TableSet("Mission Control — underlying series", tuple(tables))
        return _export_response(fmt, tableset, "mission")

    @app.get("/performance", response_class=HTMLResponse)
    def performance_view(file: str = Query("")) -> HTMLResponse:
        """Performance Analysis Summary (operator 2026-07-10): the seven graph families of the
        operator's PerformanceAnalysisSummary reference workbook, recreated live from the
        loaded schedules — G1 work-to-go census, G2 bow-wave starts/finishes, G3 execution
        index curves, G4 workoff burden, G5 duration ratio, and the G6/G7 portfolio quads
        (one dot per loaded version)."""
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Performance Summary",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule — the Performance "
                "Analysis Summary graphs are computed from the loaded versions.</div>",
            )
        return _page(
            st,
            "Performance Summary",
            _how_we_execute_header(schedules[-1])
            + _skipped_notice(skipped)
            + _sources_line(st.ordered())
            + _performance_body(schedules, cpms, file),
        )

    @app.get("/export/{fmt}/performance")
    def export_performance(fmt: str, file: str = Query("")) -> Response:
        """Every Performance-Summary dataset (census / flow / burden / DRM / quads) as a file."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        data = _performance_data(schedules, cpms, file)
        census = cast(list[dict[str, Any]], data["census"])
        flow = cast(list[dict[str, Any]], data["flow"])
        burden = cast(list[dict[str, Any]], data["burden"])
        drm = cast(dict[str, Any], data["drm"])
        quads = cast(list[dict[str, Any]], data["quads"])

        def _tbl(name: str, rows: list[dict[str, Any]]) -> Table:
            headers = tuple(rows[0].keys()) if rows else ("empty",)
            return Table(
                name,
                headers,
                tuple(tuple("" if r[h] is None else r[h] for h in headers) for r in rows),
            )

        tableset = TableSet(
            f"Performance Analysis Summary — {data['version']}",
            (
                _tbl("G1 Work-to-Go census", census),
                _tbl("G2-G3 Activity flow + indices", flow),
                _tbl("G4 Workoff burden", burden),
                _tbl("G5 Duration ratio", cast(list[dict[str, Any]], drm["points"])),
                _tbl("G6-G7 Portfolio quads", quads),
            ),
        )
        return _export_response(fmt, tableset, "performance-summary")

    @app.get("/evolution", response_class=HTMLResponse)
    def evolution_view(
        target: str | None = Query(None),
        tier: str = Query("off"),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
        cf_a: int = Query(-1),
        cf_b: int = Query(-1),
    ) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Critical-Path Evolution",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to watch the "
                "critical path evolve.</div>",
            )
        uid = _parse_uid(target) if target is not None else st.target_uid
        schedules, cpms, opt_banner = _optioned_versions(
            schedules,
            cpms,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
        opt_form = _trace_options_form(
            "/evolution",
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
            keep={"target": target or "", "tier": tier},
        )
        header = _how_stable_header(compute_path_evolution(schedules, cpms, target_uid=uid))
        return _page(
            st,
            "Critical-Path Evolution",
            header
            + _export_bar("evolution")
            + _skipped_notice(skipped)
            + opt_banner
            + opt_form
            + _sources_line(schedules)
            + _evolution_body(schedules, cpms, uid, tier, cf_a=cf_a, cf_b=cf_b),
        )

    @app.get("/integrity", response_class=HTMLResponse)
    def integrity_view(
        a: int = Query(-1),
        b: int = Query(-1),
        file: str = Query(""),
    ) -> HTMLResponse:
        """Schedule Integrity & Change Forensics — the tool's namesake page (operator
        2026-07-08): manipulation-pattern findings for one CHOSEN version pair and the
        counterfactual "what the finish would have been without those changes". ``a``/``b`` are
        the baseline / comparison file indices (operator: pick exactly two files to compare when
        more are loaded); ``file`` is honored for back-compat (comparison label -> its
        predecessor). The custom-field exception filter was removed (operator 2026-07-09: "the
        Exception Field makes no sense")."""
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Schedule Integrity",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two versions of the schedule — integrity "
                "findings are version-over-version comparisons (what changed, and what the "
                "change did to the critical path).</div>",
            )
        # back-compat: a bare ?file=<label> means "compare that file to its predecessor"
        if b < 0 and file:
            labels = [sch.source_file or sch.name for sch in schedules]
            if file in labels:
                b = labels.index(file)
                a = b - 1
        return _page(
            st,
            "Schedule Integrity",
            _skipped_notice(skipped)
            + _integrity_body(
                schedules,
                cpms,
                st.target_uid,
                baseline_idx=a,
                comparison_idx=b,
            ),
        )

    @app.get("/api/evolution")
    def evolution_json(target: str | None = Query(None), tier: str = Query("off")) -> JSONResponse:
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        if tier in _EVO_TIER_SELECT:
            return JSONResponse(_evolution_tier_data(schedules, cpms, uid, tier))
        return JSONResponse(_evolution_data(schedules, cpms, uid))

    @app.get("/driving-path", response_class=HTMLResponse)
    def driving_path_view(
        source: str | None = Query(None),
        target: str | None = Query(None),
        file: str = Query(""),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
    ) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Driving Path",
                "<div class=panel>Load a schedule to trace the driving path between two "
                "activities.</div>",
            )
        # per-file scope (operator 2026-07-08): the driving path can differ between files, so
        # the operator picks WHICH loaded version to trace; default stays every version.
        # Options are the FILENAMES (source_file), not the internal project name — every
        # version of the same project carries the same name, so the picker read as N identical
        # entries (operator 2026-07-09: "They all say the same thing").
        file_options = [s.source_file or s.name for s in schedules]
        if file and file in file_options:
            pair = next(
                (s, c)
                for s, c in zip(schedules, cpms, strict=True)
                if (s.source_file or s.name) == file
            )
            schedules, cpms = [pair[0]], [pair[1]]
        else:
            file = ""
        src = _parse_uid(source)
        tgt = _parse_uid(target)
        # the session KEY of the last displayed version — the Excel trace export route looks
        # schedules up by session key, NOT by internal project name (which the old link used
        # and which 404'd whenever the filename-derived key differed from the project name)
        last_label = schedules[-1].source_file or schedules[-1].name
        export_key = next(
            (k for k, s in st.ordered_versions() if (s.source_file or s.name) == last_label),
            None,
        )
        schedules, cpms, opt_banner = _optioned_versions(
            schedules,
            cpms,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
        return _page(
            st,
            "Driving Path",
            _skipped_notice(skipped)
            + opt_banner
            + _driving_path_body(
                schedules,
                cpms,
                src,
                tgt,
                ignore_constraints=bool(ignore_constraints),
                ignore_leveling=bool(ignore_leveling),
                file_options=file_options,
                selected_file=file,
                export_key=export_key,
            ),
        )

    @app.get("/groups", response_class=HTMLResponse)
    def groups_view(request: Request) -> HTMLResponse:
        st = session()
        versions = st.ordered_versions()
        if not versions:
            return _page(
                st,
                "Groups & Filters",
                "<div class=panel>Load a schedule to scope the metrics by a field value.</div>",
            )
        qp = request.query_params
        version_key = qp.get("version") or versions[-1][0]
        sch = dict(versions).get(version_key, versions[-1][1])
        breakdown = qp.get("breakdown") or ""
        # Parse any submitted filter rows. Each row's selected values arrive as repeated value{i}
        # params (the MS-Project-style multi-select); a legacy single `value` list (one per field,
        # exact match) is still honoured. Empty values = "field is populated".
        fields = qp.getlist("field")
        legacy = qp.getlist("value")
        param_criteria: list[Criterion] = []
        for i, f in enumerate(fields):
            if not f:
                continue
            vals = qp.getlist(f"value{i}")
            param_criteria.append((f, vals if vals else (legacy[i] if i < len(legacy) else "")))
        param_criteria = param_criteria[:MAX_FIELDS]
        # Filter MODE (feature #10): reduce = drop non-matches (default); highlight = keep the
        # full population and only MARK the matches. Applies to BOTH filter sources.
        if qp.get("mode") in ("reduce", "highlight"):
            st.set_filter_mode(qp["mode"])
        # Apply / clear MUTATE the session-wide filter (ADR-0104) so it scopes every page and every
        # loaded file; without them a row selection just PREVIEWS here without persisting.
        schedules = [s for _, s in versions]
        prompt_form = ""
        if "clear" in qp:
            st.set_filter(())
            st.set_saved_filter(None)
        elif "apply" in qp:
            st.set_filter(param_criteria)
        elif (sf_name := qp.get("saved_filter")) is not None:
            # the MS Project SAVED-filter picker: "" clears; a name applies (after its prompts)
            if sf_name == "":
                st.set_saved_filter(None)
            else:
                saved = find_saved_filter(schedules, sf_name)
                if saved is not None:
                    labels = required_prompts(saved)
                    raw_answers = {
                        label: qp.get(f"prompt_{i}", "") for i, label in enumerate(labels)
                    }
                    if labels and any(v == "" for v in raw_answers.values()):
                        # interactive filter, unanswered → render the prompt form, do NOT apply
                        # (mirrors MS Project's modal prompt)
                        prompt_form = _saved_prompt_form(saved, raw_answers, st.filter_mode)
                    else:
                        st.set_saved_filter(saved, coerce_prompt_answers(saved, raw_answers))
        if (sg_name := qp.get("saved_group")) is not None:
            # the SAVED-group picker: "" clears; grouping is presentation-only (never a metric)
            st.set_saved_group(find_saved_group(schedules, sg_name) if sg_name else None)
        # the page shows the URL preview when rows are present, else the live session filter
        criteria: list[Criterion] = param_criteria if fields else list(st.active_filter)
        applied = bool(st.active_filter) and criteria == list(st.active_filter)
        return _page(
            st,
            "Groups & Filters",
            _saved_views_panel(st, schedules)
            + prompt_form
            + _groups_body(versions, version_key, sch, criteria, breakdown, applied, st),
        )

    @app.get("/api/group-values")
    def group_values_json(
        version: str | None = Query(None), field: str = Query("")
    ) -> JSONResponse:
        """Distinct values of ``field`` across ALL loaded files — the /groups value autocomplete.

        Aggregated over every version (not just one) because the filter applies to all files, so a
        value present in any version must be offerable. ``version`` is accepted for compatibility."""
        st = session()
        schedules = [s for _, s in st.ordered_versions()]
        if not schedules or not field:
            return JSONResponse({"values": []})
        values = distinct_values(schedules, field)
        return JSONResponse({"values": values[:500]})  # cap for a sane datalist

    @app.get("/forecast", response_class=HTMLResponse)
    def forecast_view(group_field: str = Query("")) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Forecast",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to forecast the "
                "finish.</div>",
            )
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        return _page(
            st,
            "Forecast",
            _where_it_lands_header(schedules[-1], sets[-1])
            + _export_bar("forecast")
            + _skipped_notice(skipped)
            + _forecast_body(schedules, cpms, sets)
            + _field_forecast_panel(schedules, group_field)
            + (_group_rollup_panel(schedules[-1], sets[-1], group_field) if group_field else ""),
        )

    @app.get("/export/{fmt}/field-forecast")
    def export_field_forecast(fmt: str, field: str = Query(...)) -> Response:
        """The per-field group execution metrics (ADR-0179) as a file."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, _cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "no analyzable schedule"}, status_code=422)
        if field not in available_fields_union(schedules):
            return JSONResponse({"error": "unknown field"}, status_code=404)
        rows_data = compute_field_forecast(schedules, field)

        def n(v: float | None) -> str | float:
            return "N/A" if v is None else v

        headers = (
            field,
            "Version",
            "Activities",
            "Completed",
            "Started",
            "To go",
            "BEI",
            "HMI (tasks)",
            "CEI (Finish)",
            "CEI (Start)",
            "SPI(t) ES",
            "SPI(t) Acumen",
            "Start index (SEI)",
            "No completed work",
        )
        rows = tuple(
            (
                g.group,
                g.version,
                g.activities,
                g.completed,
                g.started,
                g.to_go,
                n(g.bei),
                n(g.hmi),
                n(g.cei_finish),
                n(g.cei_start),
                n(g.spi_t),
                n(g.spi_t_acumen),
                n(g.sei),
                "yes" if g.no_completed_work else "",
            )
            for g in rows_data
        )
        tableset = TableSet(
            f"Execution metrics by {field}",
            (Table(f"By {field}", headers, rows),),
        )
        return _export_response(fmt, tableset, "field-forecast")

    @app.get("/api/forecast")
    def forecast_json() -> JSONResponse:
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        return JSONResponse(_forecast_data(schedules, sets))

    @app.get("/curves", response_class=HTMLResponse)
    def curves_view() -> HTMLResponse:
        st = session()
        # the finish/slippage curves are stored-date views — they do not need the network
        # to solve, so every loaded version contributes (unlike the CPM-gated pages)
        versions = st.ordered()
        if not versions:
            return _page(
                st,
                "Finish & Slippage",
                "<div class=panel>Load at least one schedule to see the finish and slippage "
                "curves.</div>",
            )
        try:
            curves = compute_month_curves(versions)
        except ValueError as exc:
            return _page(st, "Finish & Slippage", f"<div class=panel>{_e(exc)}</div>")
        return _page(
            st,
            "Finish & Slippage",
            _export_bar("curves") + _sources_line(versions) + _curves_body(curves),
        )

    @app.get("/api/curves")
    def curves_json(hide_complete: bool = Query(False)) -> JSONResponse:
        st = session()
        versions = st.ordered()
        if not versions:
            return JSONResponse({"error": "need at least one schedule"}, status_code=400)
        if hide_complete:
            # drop 100%-complete activities so the curves show only the remaining/forecast work
            crit: list[Criterion] = [("% Complete", ["In Progress", "Not Started"])]
            versions = [v for v in (filter_schedule(s, crit) for s in versions) if non_summary(v)]
            if not versions:
                return JSONResponse({"months": [], "versions": []})
        try:
            curves = compute_month_curves(versions)
        except ValueError:
            return JSONResponse({"months": [], "versions": []})
        return JSONResponse(_curves_data(curves))

    # --- exports (M18): every view's tables, rendered locally as Excel or Word -------

    _EXPORT_MEDIA: dict[str, tuple[str, Callable[[TableSet], bytes]]] = {
        "xlsx": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            render_xlsx,
        ),
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            render_docx,
        ),
    }

    def _export_response(fmt: str, tableset: TableSet, stem: str) -> Response:
        media, renderer = _EXPORT_MEDIA[fmt]
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem) or "export"
        return Response(
            content=renderer(tableset),
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{safe}.{fmt}"'},
        )

    def _bad_format(fmt: str) -> JSONResponse | None:
        if fmt not in _EXPORT_MEDIA:
            return JSONResponse({"error": "format must be xlsx or docx"}, status_code=404)
        return None

    @app.get("/export/{fmt}/analysis/{name}")
    def export_analysis(fmt: str, name: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        quality = compute_schedule_quality(sch, analysis.cpm)
        tableset = TableSet(
            f"POLARIS - {sch.name}",
            (
                schedule_summary_table(sch),
                dcma_table(analysis.audit),
                metric_results_table("Schedule quality", quality),
                metric_results_table("Float bands", analysis.float_bands),
                metric_results_table("Completion performance", analysis.completion),
                metric_results_table("Baseline compliance", analysis.compliance),
                findings_table(analysis.findings),
                activities_table(analysis.activity_rows),
            ),
        )
        return _export_response(fmt, tableset, f"{name}-analysis")

    @app.get("/export/{fmt}/path/{name}")
    def export_path(
        fmt: str,
        name: str,
        target: int = Query(...),
        secondary: int = Query(10),
        tertiary: int = Query(20),
        cols: str = Query(""),
        direction: str = Query("predecessors"),
        range_mode: str = Query("all"),
        range_days: int = Query(0),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
        drag: int = Query(0),
    ) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            cpm = st.analysis_for(name, sch).cpm
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        data = _driving_data(
            sch,
            cpm,
            target,
            secondary,
            tertiary,
            direction=direction,
            range_mode=range_mode,
            range_days=range_days,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
            with_drag=bool(drag),
        )
        rows = data.get("rows") or []
        if not rows:
            return JSONResponse({"error": str(data.get("note", "no path"))}, status_code=422)
        # selected custom-field columns to mirror the grid (ADR-0095): only the schedule's own
        # mapped fields, in the order requested, deduped.
        valid = set(sch.custom_field_labels)
        custom_labels = list(
            dict.fromkeys(c for c in (s.strip() for s in cols.split(",")) if c in valid)
        )
        tableset = TableSet(
            f"Path analysis - {sch.name}",
            (driving_table(rows, target, custom_labels),),  # type: ignore[arg-type]
        )
        return _export_response(fmt, tableset, f"{name}-path-uid{target}")

    @app.get("/export/{fmt}/ribbon")
    def export_ribbon(fmt: str) -> Response:
        """The full Schedule Quality Ribbon (all measures, one row per loaded file) as a
        spreadsheet/document — the operator's per-page Excel export (2026-07-08)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        headers = (
            "Schedule",
            "Missing Logic",
            "Logic Density™",
            "Critical",
            "Hard Constraints",
            "Negative Float",
            "Number of Lags",
            "Number of Leads",
            "Merge Hotspot",
            "Insufficient Detail™",
            "Avg Float (d)",
            "Max Float (d)",
        )
        body = []
        for key, sch in st.ordered_versions():
            try:
                analysis = st.analysis_for(key, sch)
            except CPMError:
                continue
            r = compute_ribbon(sch, analysis.cpm, analysis.audit)
            # Empty incomplete-activity population → avg/max float are a placeholder 0.0; export the
            # "—" sentinel, not a fabricated mean/max, to match the grid and the Workbench (NEW-1).
            na_floats = r.incomplete_float_count == 0
            body.append(
                (
                    key,
                    r.missing_logic,
                    r.logic_density,
                    r.critical,
                    r.hard_constraints,
                    r.negative_float,
                    r.number_of_lags,
                    r.number_of_leads,
                    r.merge_hotspot,
                    r.insufficient_detail,
                    "—" if na_floats else r.avg_float_days,
                    "—" if na_floats else r.max_float_days,
                )
            )
        if not body:
            return JSONResponse({"error": "no analyzable schedules loaded"}, status_code=422)
        tableset = TableSet(
            "Schedule Quality Ribbon", (Table("Quality Ribbon", headers, tuple(body)),)
        )
        return _export_response(fmt, tableset, "quality-ribbon")

    @app.get("/export/{fmt}/float-band/{name}")
    def export_float_band(
        fmt: str, name: str, band: int = Query(...), cols: str = Query("")
    ) -> Response:
        """The activities inside one total-float histogram band, with any extra columns the
        operator toggled on in the drill panel (standard or custom fields) — the histogram
        click-through's Excel export (operator 2026-07-08)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        if not 0 <= band < len(_FLOAT_HIST_BANDS):
            return JSONResponse({"error": "unknown band"}, status_code=422)
        label, member = _FLOAT_HIST_BANDS[band]
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError:  # an unsolvable file has no float histogram — 422, never 500
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Name", "Total float (d)", *extra)

        def _cell(value: object) -> str | int | float | None:
            return value if isinstance(value, str | int | float) or value is None else str(value)

        body: list[tuple[str | int | float | None, ...]] = []
        for a in analysis.activity_rows:
            tf = a.get("total_float_days")
            if a.get("is_summary") or not isinstance(tf, int | float) or not member(float(tf)):
                continue
            custom_obj = a.get("custom")
            custom: dict[str, object] = custom_obj if isinstance(custom_obj, dict) else {}
            body.append(
                (
                    _cell(a.get("unique_id")),
                    _cell(a.get("name")),
                    tf,
                    *(_cell(a.get(c, custom.get(c))) for c in extra),
                )
            )
        tableset = TableSet(
            f"{name} — total float {label} d",
            (Table(f"Float band {label} d", headers, tuple(body)),),
        )
        return _export_response(fmt, tableset, "float-band")

    @app.get("/export/{fmt}/ribbon-drill/{name}")
    def export_ribbon_drill(
        fmt: str, name: str, metric: str = Query(...), cols: str = Query("")
    ) -> Response:
        """The activities behind one Quality-Ribbon cell (file x metric), with any extra columns
        the operator toggled on in the drill panel — the ribbon click-through's Excel export
        (operator 2026-07-08)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError:  # an unsolvable file has no ribbon drill — 422, never 500
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        offenders = ribbon_offender_map(sch, analysis.cpm, analysis.audit)
        if metric not in offenders:
            return JSONResponse({"error": "unknown metric"}, status_code=422)
        uid_order = {uid: i for i, uid in enumerate(offenders[metric])}
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Name", "Duration (d)", "% complete", "Start", "Finish", *extra)

        def _cell(value: object) -> str | int | float | None:
            return value if isinstance(value, str | int | float) or value is None else str(value)

        rows_by_uid: dict[int, tuple[str | int | float | None, ...]] = {}
        for a in analysis.activity_rows:
            uid = a.get("unique_id")
            if not isinstance(uid, int) or uid not in uid_order:
                continue
            custom_obj = a.get("custom")
            custom: dict[str, object] = custom_obj if isinstance(custom_obj, dict) else {}
            rows_by_uid[uid] = (
                uid,
                _cell(a.get("name")),
                _cell(a.get("duration_days")),
                _cell(a.get("percent_complete")),
                _cell(a.get("start")),
                _cell(a.get("finish")),
                *(_cell(a.get(c, custom.get(c))) for c in extra),
            )
        body = tuple(rows_by_uid[uid] for uid in offenders[metric] if uid in rows_by_uid)
        tableset = TableSet(
            f"{name} — ribbon {metric}",
            (Table(f"Ribbon drill — {metric}", headers, body),),
        )
        return _export_response(fmt, tableset, "ribbon-drill")

    # ── Metric Workbench (ADR-0204): pick any library metric, computed per version like Acumen ──

    def _workbench_versions() -> list[tuple[str, Schedule, CPMResult, _Analysis]]:
        """Loaded solvable versions oldest→newest, each with its scoped schedule + cached analysis."""
        st = session()
        out: list[tuple[str, Schedule, CPMResult, _Analysis]] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                continue
            out.append((key, st.scope(raw), a.cpm, a))
        return out

    @app.get("/workbench", response_class=HTMLResponse)
    def workbench_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Metric Workbench",
                "<div class=panel>Load one or more schedules to build the metric workbench.</div>",
            )
        return _page(st, "Metric Workbench", _workbench_body())

    @app.get("/api/workbench")
    def workbench_json() -> JSONResponse:
        versions = _workbench_versions()
        if not versions:
            return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=400)
        entries = catalog_entries()
        cells: dict[str, dict[str, object]] = {e.metric_id: {} for e in entries}
        version_rows: list[dict[str, object]] = []
        for key, sch, cpm, a in versions:
            version_rows.append(
                {
                    "key": key,
                    "label": sch.source_file or sch.name,
                    "status": sch.status_date.date().isoformat() if sch.status_date else None,
                }
            )
            rows = evaluate_catalog(sch, cpm, a.audit)
            for e in entries:
                r = rows[e.metric_id]
                cells[e.metric_id][key] = {
                    "value": r.value,
                    "unit": r.unit,
                    "status": r.status,
                    "applicable": r.applicable,  # False → the cell renders "—", not a placeholder 0
                    "offenders": len(r.offender_uids),
                }
        return JSONResponse(
            {
                "versions": version_rows,
                "families": list(catalog_families()),
                "metrics": [
                    {
                        "id": e.metric_id,
                        "name": e.name,
                        "family": e.family,
                        "unit": e.unit,
                        "describe": e.describe,
                        "threshold": e.threshold,
                        "lower_is_better": e.lower_is_better,
                    }
                    for e in entries
                ],
                "cells": cells,
            }
        )

    def _workbench_drill_rows(
        sch: Schedule, a: _Analysis, uids: tuple[int, ...]
    ) -> tuple[list[str], list[dict[str, object]]]:
        """The offender activities as grid rows: the standard columns plus every available field
        value (so the client can add-column / group-by / sort with no refetch). Offender order."""
        fields = list(available_fields(sch))
        by_uid = sch.tasks_by_id
        wanted = {u: i for i, u in enumerate(uids)}
        rows: list[dict[str, object]] = []
        for act in a.activity_rows:
            uid = act.get("unique_id")
            if not isinstance(uid, int) or uid not in wanted:
                continue
            task = by_uid.get(uid)
            field_map = {f: field_value(sch, task, f) for f in fields} if task is not None else {}
            rows.append(
                {
                    "uid": uid,
                    "Name": act.get("name"),
                    "Duration (d)": act.get("duration_days"),
                    "% complete": act.get("percent_complete"),
                    "Start": act.get("start"),
                    "Finish": act.get("finish"),
                    "fields": field_map,
                }
            )
        rows.sort(key=lambda r: wanted.get(cast("int", r["uid"]), 0))
        return fields, rows

    @app.get("/api/workbench/drill")
    def workbench_drill_json(metric: str = Query(...), file: str = Query(...)) -> JSONResponse:
        st = session()
        raw = st.schedules.get(file)
        if raw is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        try:
            a = st.analysis_for(file, raw)
        except CPMError:
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        sch = st.scope(raw)
        rows = evaluate_catalog(sch, a.cpm, a.audit)
        row = rows.get(metric)
        if row is None:
            return JSONResponse({"error": "unknown metric"}, status_code=422)
        entry = next((e for e in catalog_entries() if e.metric_id == metric), None)
        fields, drill = _workbench_drill_rows(sch, a, row.offender_uids)
        return JSONResponse(
            {
                "metric": metric,
                "metric_name": entry.name if entry else metric,
                "file": file,
                "label": sch.source_file or sch.name,
                "columns": ["Name", "Duration (d)", "% complete", "Start", "Finish"],
                "fields": fields,
                "rows": drill,
            }
        )

    @app.get("/export/{fmt}/workbench")
    def export_workbench(fmt: str) -> Response:
        """The whole workbench ribbon (metrics x versions) as one Excel/Word table."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        versions = _workbench_versions()
        if not versions:
            return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=400)
        labels = [sch.source_file or sch.name for _k, sch, _c, _a in versions]
        per_version = [evaluate_catalog(sch, cpm, a.audit) for _k, sch, cpm, a in versions]
        headers = ("Metric", "Family", "Unit", *labels)
        body: list[tuple[Cell, ...]] = []
        for e in catalog_entries():
            cells: list[Cell] = []
            for rows in per_version:
                r = rows[e.metric_id]
                # an unmeasurable metric exports as "NA", not a placeholder 0 (matches the grid);
                # the informational extras stay applicable and export their real value
                cells.append("NA" if not r.applicable else r.value)
            body.append((e.name, e.family, e.unit, *cells))
        tableset = TableSet(
            "Metric Workbench",
            (Table("Metric library vs versions (oldest first)", headers, tuple(body)),),
        )
        return _export_response(fmt, tableset, "metric-workbench")

    @app.get("/export/{fmt}/margin")
    def export_margin(fmt: str) -> Response:
        """The margin/contingency burn-down + the erosion summary as one Excel/Word workbook."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        d = _margin_dashboard_for(session())
        headers = (
            "Status date",
            "Target",
            "Planned margin (wd)",
            "Effective margin (wd)",
            "Total margin (wd)",
            "Consumed (wd)",
            "Contingency (days)",
            "Total available",
            "NASA requirement (wd)",
            "Days-to-go",
            "% available",
            "% effective",
            "Corrective (>=50% consumed)",
            "Trigger",
        )
        body: list[tuple[Cell, ...]] = [
            (
                m.status_date or "—",
                m.target_name or "project finish",
                m.planned_margin_wd if m.planned_margin_wd is not None else "—",
                m.effective_margin_wd,
                m.total_margin_wd,
                m.consumed_wd if m.consumed_wd is not None else "—",
                m.contingency_wd,
                m.total_available,
                m.nasa_rqmt_wd,
                m.days_to_go,
                round(100 * m.pct_available, 1) if m.pct_available is not None else "—",
                round(100 * m.pct_effective, 1) if m.pct_effective is not None else "—",
                "yes" if m.corrective_action else "no",
                "trigger" if m.below_requirement else "ok",
            )
            for m in d.months
        ]
        basis_note = (
            "mixed — " + " vs ".join(_wmpd_label(w) for w in d.erosion_mixed_basis)
            if d.erosion_mixed_basis
            else (_wmpd_label(d.erosion_basis_wmpd) if d.erosion_basis_wmpd else "—")
        )
        erosion: tuple[tuple[Cell, ...], ...] = (
            ("NASA requirement rate (wd / program year)", d.gold_rule_per_year),
            (
                "Erosion (work days / month)",
                d.erosion_wd_per_month if not d.erosion_mixed_basis else "—",
            ),
            ("Projected zero-margin date", d.zero_margin_date or "—"),
            ("Trend fit R-squared", d.erosion_r2),
            ("Work-day basis", basis_note),
        )
        # Fig 5-30 guideline band (ADR-0254): the operator's parameters + the per-status-date
        # expected/actual/position read — or the single not-configured row (the band is never
        # derived). The convention and every rate are stated (export provenance, like the rate).
        st = session()
        band_rows: list[tuple[Cell, ...]] = []
        if st.margin_band_dates is None:
            band_rows = [("not configured (enter the phase dates on /margin)", "—", "—", "—", "—")]
        else:
            try:
                cfg_band: GuidelineBandConfig | None = GuidelineBandConfig(
                    phase_dates=(
                        dt.date.fromisoformat(st.margin_band_dates[0]),
                        dt.date.fromisoformat(st.margin_band_dates[1]),
                        dt.date.fromisoformat(st.margin_band_dates[2]),
                        dt.date.fromisoformat(st.margin_band_dates[3]),
                    ),
                    rates=st.margin_band_rates,
                )
            except ValueError:
                cfg_band = None  # fail-soft: disclose, never render a wrong band
            if cfg_band is None:
                band_rows = [("stored band configuration invalid", "—", "—", "—", "—")]
            else:
                dated = [(m.status_date, m.effective_margin_wd) for m in d.months if m.status_date]
                pts = {
                    p.date.isoformat(): p
                    for p in expected_margin_band(
                        cfg_band, tuple(dt.date.fromisoformat(s) for s, _ in dated)
                    )
                }
                mixed = bool(d.erosion_mixed_basis)
                for iso, eff in dated:
                    p = pts[iso]
                    pos = (
                        "— (mixed work-day basis)"
                        if mixed
                        else band_position(eff, p.low_wd, p.high_wd)
                    )
                    band_rows.append((iso, p.low_wd, p.high_wd, eff, pos))
                if not band_rows:
                    band_rows = [("no dated versions to compare", "—", "—", "—", "—")]
        band_params: tuple[tuple[Cell, ...], ...] = (
            (
                "Phase dates (CR / I&T start / delivery / launch)",
                ", ".join(st.margin_band_dates) if st.margin_band_dates else "—",
            ),
            *(
                (
                    f"Rate row {i + 1}: {frm} -> {to}",
                    f"{st.margin_band_rates[i][0]:g}-{st.margin_band_rates[i][1]:g} wd/yr "
                    f'(handbook: "{amount}")',
                )
                for i, (frm, to, amount) in enumerate(FIG_5_30_ROWS)
            ),
            ("Conversion convention", f"1 month = {MONTH_WORK_DAYS:g} work days (ADR-0230/0253)"),
        )
        # §7.3.3.2.3 risk-based sufficiency: the same seeded read the panel button runs
        # (byte-identical by determinism); parameters stated; disclosures instead of fabrication.
        risk = _margin_risk_data(st)
        if "error" in risk:
            risk_rows: tuple[tuple[Cell, ...], ...] = (("Status", str(risk["error"])),)
        else:
            verdict = (
                "no verdict — every iteration identical (no uncertainty/risk inputs)"
                if risk["degenerate"]
                else str(risk["verdict"])
            )
            risk_pct_rows = [
                (
                    f"P{row['pct']:g} finish",
                    f"{row['finish_date']}  (delta vs plan {row['delta_vs_plan_wd']:+g} wd; "
                    f"margin needed {row['margin_needed_wd']:g} wd; "
                    f"{'covered' if row['covered'] else 'NOT covered'})",
                )
                for row in cast("list[dict[str, object]]", risk["rows"])
            ]
            risk_rows = (
                ("File", str(risk["file"])),
                ("Covered percentile (CDF at deterministic finish)", f"{risk['covered_pct']}"),
                ("Verdict", verdict),
                ("Margin window (wd)", f"{risk['margin_wd']}"),
                (
                    "Watch / Corrective thresholds (%)",
                    f"{risk['watch_pct']:g} / {risk['corrective_pct']:g} "
                    "(handbook example values, operator-set)",
                ),
                ("Deterministic finish (D)", str(risk["deterministic_finish_date"])),
                ("Zero-margin finish (E)", str(risk["zero_margin_finish_date"])),
                (
                    "Iterations / seed / distribution",
                    f"{risk['iterations']} / {risk['seed']} / {risk['distribution']} "
                    "(computed at export time; deterministic by seed)",
                ),
                *risk_pct_rows,
            )
        tableset = TableSet(
            "Margin Dashboard",
            (
                Table("Margin & contingency burn-down (oldest first)", headers, tuple(body)),
                Table("Margin erosion trend", ("Measure", "Value"), erosion),
                Table(
                    "Figure 5-30 guideline band (operator-set; SMH §5.5.11.2 / §7.3.3.1.6)",
                    (
                        "Status date",
                        "Expected low (wd)",
                        "Expected high (wd)",
                        "Actual effective (wd)",
                        "Position",
                    ),
                    tuple(band_rows),
                ),
                Table("Figure 5-30 band parameters", ("Parameter", "Value"), band_params),
                Table(
                    "Risk-based margin sufficiency (SRA; SMH §7.3.3.2.3)",
                    ("Measure", "Value"),
                    risk_rows,
                ),
            ),
        )
        return _export_response(fmt, tableset, "margin-dashboard")

    @app.get("/export/{fmt}/workbench-drill/{name}")
    def export_workbench_drill(
        fmt: str, name: str, metric: str = Query(...), cols: str = Query("")
    ) -> Response:
        """The activities behind one workbench cell (file x metric) + any extra field columns."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        raw = st.schedules.get(name)
        if raw is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        try:
            a = st.analysis_for(name, raw)
        except CPMError:
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        sch = st.scope(raw)
        row = evaluate_catalog(sch, a.cpm, a.audit).get(metric)
        if row is None:
            return JSONResponse({"error": "unknown metric"}, status_code=422)
        _fields, drill = _workbench_drill_rows(sch, a, row.offender_uids)
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Name", "Duration (d)", "% complete", "Start", "Finish", *extra)

        def _cell(v: object) -> str | int | float | None:
            return v if isinstance(v, str | int | float) or v is None else str(v)

        body = tuple(
            (
                _cell(r["uid"]),
                _cell(r["Name"]),
                _cell(r["Duration (d)"]),
                _cell(r["% complete"]),
                _cell(r["Start"]),
                _cell(r["Finish"]),
                *(_cell(cast("dict[str, object]", r["fields"]).get(c)) for c in extra),
            )
            for r in drill
        )
        tableset = TableSet(
            f"{name} — workbench {metric}",
            (Table(f"Workbench drill — {metric}", headers, body),),
        )
        return _export_response(fmt, tableset, "workbench-drill")

    # ── Assessment Scorecards (issue #331): NASA STAT / GAO-10 / SRA-readiness + reserve sizing.
    # A consolidation of already-validated metrics into three named frameworks
    # (engine/scorecards.py) — no new metric math (Law 2). The reserve card runs the existing
    # seeded SRA Monte-Carlo on demand (off the page-load path). ──

    def _scorecard_versions() -> list[tuple[str, Schedule, _Analysis]]:
        """Loaded solvable versions oldest→newest, each scoped + with its cached analysis."""
        st = session()
        out: list[tuple[str, Schedule, _Analysis]] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                continue
            out.append((key, st.scope(raw), a))
        return out

    def _pick_scorecard_version(file: str) -> tuple[str, Schedule, _Analysis] | None:
        """The chosen version by key/label, else the latest loaded solvable version."""
        versions = _scorecard_versions()
        if not versions:
            return None
        if file:
            for key, sch, a in versions:
                if key == file or (sch.source_file or sch.name) == file:
                    return (key, sch, a)
        return versions[-1]

    @app.get("/scorecards", response_class=HTMLResponse)
    def scorecards_view(file: str = Query("")) -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Assessment Scorecards",
                "<div class=panel>Load a schedule to build the NASA STAT, GAO 10-practices and "
                "SRA-readiness scorecards.</div>",
            )
        picked = _pick_scorecard_version(file)
        if picked is None:
            return _page(
                st,
                "Assessment Scorecards",
                "<div class=panel>No loaded version could be solved for the network, so the "
                "assessment scorecards cannot be built. Resolve the logic and re-import.</div>",
            )
        key, sch, a = picked
        return _page(
            st,
            "Assessment Scorecards",
            _scorecards_body(_scorecard_versions(), key, sch, a),
        )

    @app.get("/api/scorecards/buffer")
    def scorecards_buffer_json(
        file: str = Query(""),
        committed: str = Query(""),
        iterations: int = Query(1000),
    ) -> JSONResponse:
        """Size the reserve to hit a committed PROJECT finish date at P50/P70/P80/P90.

        Runs the existing seeded SRA Monte-Carlo on demand, then reads the reserve off its finish
        CDF (engine/scorecards.reserve_recommendation) — pure percentile arithmetic, no new stats.
        """
        picked = _pick_scorecard_version(file)
        if picked is None:
            return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=400)
        key, sch, a = picked
        committed_dt = _parse_committed_date(committed)
        if committed_dt is None:
            return JSONResponse(
                {"error": "a committed date (YYYY-MM-DD) is required"}, status_code=422
            )
        iters = max(100, min(5000, iterations))
        sra = compute_sra(sch, a.cpm, config=SRAConfig(iterations=iters))
        # a committed finish DATE means "finish by the end of that day", so map it to the start of
        # the next day (strictly after any finish on the committed day) for the confidence/reserve.
        end_of_day = committed_dt + dt.timedelta(days=1)
        committed_offset = datetime_to_offset(sch.project_start, end_of_day, sch.calendar)
        rec = reserve_recommendation(
            sra.cdf,
            committed_offset,
            sch.project_start,
            sch.calendar,
            committed_date_display=committed_dt.date().isoformat(),
        )
        return JSONResponse(
            {
                "file": key,
                "label": sch.source_file or sch.name,
                "iterations": iters,
                "committed_date": rec.committed_date,
                "committed_confidence": rec.committed_confidence,
                "deterministic_finish_date": sra.deterministic_finish_date,
                "recommended_p70_days": rec.recommended_p70_days,
                "recommended_p80_days": rec.recommended_p80_days,
                "rows": [
                    {
                        "percentile": r.percentile,
                        "finish_date": r.finish_date,
                        "reserve_days": r.reserve_days,
                    }
                    for r in rec.rows
                ],
            }
        )

    @app.get("/export/{fmt}/scorecards")
    def export_scorecards(fmt: str, file: str = Query("")) -> Response:
        """The three scorecards (STAT / GAO / readiness) for the chosen version as one export."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        picked = _pick_scorecard_version(file)
        if picked is None:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        _key, sch, a = picked
        cards = compute_scorecards(sch, a.cpm, a.audit)
        tables = tuple(_scorecard_export_table(c) for c in cards)
        label = sch.source_file or sch.name
        tableset = TableSet(f"Assessment scorecards — {label}", tables)
        return _export_response(fmt, tableset, "assessment-scorecards")

    # ── Generic activity drill (shared): click any element carrying a UID set (a scorecard line,
    # a churn-bar segment, …) → the activities behind it, with add-columns + Excel. Reuses
    # `_workbench_drill_rows`; `_pick_scorecard_version` doubles as the version resolver (by key or
    # label, else latest solvable). The UID set is server-computed and sanitized (_parse_uid_list). ──
    _DRILL_BASE_COLS = ("Name", "Duration (d)", "% complete", "Start", "Finish")

    @app.get("/api/activities/drill")
    def activities_drill_json(
        file: str = Query(""), uids: str = Query(""), title: str = Query("")
    ) -> JSONResponse:
        picked = _pick_scorecard_version(file)
        if picked is None:
            return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=400)
        key, sch, a = picked
        fields, rows = _workbench_drill_rows(sch, a, tuple(_parse_uid_list(uids)))
        return JSONResponse(
            {
                "title": title or "Activities",
                "file": key,
                "label": sch.source_file or sch.name,
                "columns": list(_DRILL_BASE_COLS),
                "fields": fields,
                "rows": rows,
            }
        )

    @app.get("/export/{fmt}/activities-drill")
    def export_activities_drill(
        fmt: str,
        file: str = Query(""),
        uids: str = Query(""),
        cols: str = Query(""),
        title: str = Query(""),
    ) -> Response:
        """The activities behind any drillable element (UID set) + chosen extra columns, as Excel/Word."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        picked = _pick_scorecard_version(file)
        if picked is None:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        _key, sch, a = picked
        fields, rows = _workbench_drill_rows(sch, a, tuple(_parse_uid_list(uids)))
        extra = [c for c in cols.split(",") if c and c in fields]
        headers = ("UID", *_DRILL_BASE_COLS, *extra)
        body: list[tuple[Cell, ...]] = []
        for r in rows:
            fmap = cast("dict[str, object]", r.get("fields", {}))
            cells: list[Cell] = [cast("Cell", r.get("uid"))]
            cells += [cast("Cell", r.get(c)) for c in _DRILL_BASE_COLS]
            cells += [cast("Cell", fmap.get(c)) for c in extra]
            body.append(tuple(cells))
        clean_title = title or "Activities"
        tableset = TableSet(clean_title, (Table(clean_title, headers, tuple(body)),))
        return _export_response(fmt, tableset, "activities-drill")

    @app.get("/export/{fmt}/resource-drill")
    def export_resource_drill(
        fmt: str,
        resource: int = Query(...),
        period: str = Query(...),
        bucket: str = Query("month"),
        cols: str = Query(""),
    ) -> Response:
        """The activities behind one resource-loading bar (resource x period), with the
        operator's extra drill columns — the Resources click-through's Excel export
        (operator 2026-07-10)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _latest_solvable(st)
        if chosen is None:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        _key, sch, cpm = chosen
        bucket = bucket if bucket in ("day", "week", "month") else "month"
        rl = compute_resource_loading(sch, cpm, bucket)
        res = next((r for r in rl.resources if r.resource_id == resource), None)
        if res is None:
            return JSONResponse({"error": "unknown resource"}, status_code=422)
        per = next((p for p in res.series if p.period == period), None)
        if per is None:
            return JSONResponse({"error": "unknown period"}, status_code=422)
        mpd = rl.working_minutes_per_day or 480
        analysis = st.analysis_for(_key, sch)
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = (
            "UID",
            "Name",
            f"Work (d) this {bucket}",
            "Duration (d)",
            "% complete",
            "Start",
            "Finish",
            *extra,
        )

        def _cell(value: object) -> str | int | float | None:
            return value if isinstance(value, str | int | float) or value is None else str(value)

        by_uid: dict[int, dict[str, Any]] = {}
        for a in analysis.activity_rows:
            uid_v = a.get("unique_id")
            if isinstance(uid_v, int):
                by_uid[uid_v] = cast(dict[str, Any], a)
        body = []
        for uid, mins in per.contributors:
            a = by_uid.get(uid, {})
            custom_obj = a.get("custom")
            custom: dict[str, object] = custom_obj if isinstance(custom_obj, dict) else {}
            body.append(
                (
                    uid,
                    _cell(a.get("name", f"UID {uid}")),
                    round(mins / mpd, 2),
                    _cell(a.get("duration_days")),
                    _cell(a.get("percent_complete")),
                    _cell(a.get("start")),
                    _cell(a.get("finish")),
                    *(_cell(a.get(c, custom.get(c))) for c in extra),
                )
            )
        tableset = TableSet(
            f"{sch.source_file or sch.name} — {res.name} @ {period}",
            (Table(f"Resource drill — {res.name} {period}", headers, tuple(body)),),
        )
        return _export_response(fmt, tableset, "resource-drill")

    @app.get("/export/{fmt}/activities/{name}")
    def export_activities(
        fmt: str, name: str, uids: str = Query(""), cols: str = Query("")
    ) -> Response:
        """A chosen set of activities (by UniqueID) from one file, with any extra columns — the
        Integrity finding-citation "view all" chart's Excel export (operator 2026-07-08). Rows are
        emitted in the requested UID order."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        key, sch = _find_schedule(st, name)  # accept the session key OR the display label
        if key is None or sch is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        try:
            analysis = st.analysis_for(key, sch)
        except CPMError:
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        want: list[int] = []
        for tok in uids.split(","):
            tok = tok.strip()
            if tok.lstrip("-").isdigit():
                want.append(int(tok))
        order = {u: i for i, u in enumerate(want)}
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Name", "Duration (d)", "% complete", "Start", "Finish", *extra)

        def _cell(value: object) -> str | int | float | None:
            return value if isinstance(value, str | int | float) or value is None else str(value)

        by_uid: dict[int, tuple[str | int | float | None, ...]] = {}
        for a in analysis.activity_rows:
            uid = a.get("unique_id")
            if not isinstance(uid, int) or uid not in order:
                continue
            custom_obj = a.get("custom")
            custom: dict[str, object] = custom_obj if isinstance(custom_obj, dict) else {}
            by_uid[uid] = (
                uid,
                _cell(a.get("name")),
                _cell(a.get("duration_days")),
                _cell(a.get("percent_complete")),
                _cell(a.get("start")),
                _cell(a.get("finish")),
                *(_cell(a.get(c, custom.get(c))) for c in extra),
            )
        body = tuple(by_uid[u] for u in want if u in by_uid)
        tableset = TableSet(
            f"{name} — cited activities", (Table("Cited activities", headers, body),)
        )
        return _export_response(fmt, tableset, "activities")

    @app.get("/export/{fmt}/driving-tiers/{name}")
    def export_driving_tiers(
        fmt: str,
        name: str,
        target: int = Query(...),
        cols: str = Query(""),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
    ) -> Response:
        """Every activity driving ``target`` in one file, bucketed by driving-slack tier, with a
        Tier + Slack(d) column and any extra fields the operator toggled on — the Driving-Path
        tiers chart's Excel export (operator #72). Rows are ordered driving → secondary → tertiary,
        then by slack then UID (matching the on-screen buckets). The export honours the same
        ``ignore_constraints`` / ``ignore_leveling`` trace options as the page, so the downloaded
        tier membership + slack are computed on the SAME network the panel shows (ADR-0174)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        key, sch = _find_schedule(st, name)  # accept the session key OR the display label
        if key is None or sch is None:
            return JSONResponse({"error": "unknown schedule"}, status_code=404)
        if target not in sch.tasks_by_id:
            return JSONResponse({"error": "target not in schedule"}, status_code=404)
        try:
            analysis = st.analysis_for(key, sch)
            # re-solve with the active trace options (constraints stripped / dates cleared), exactly
            # as _driving_tiers_panel does, so the exported tier/slack match the on-screen table
            # rather than the stored network (ADR-0174). No options => the originals, untouched.
            opt_scheds, opt_cpms, _banner = _optioned_versions(
                [sch],
                [analysis.cpm],
                ignore_constraints=bool(ignore_constraints),
                ignore_leveling=bool(ignore_leveling),
            )
            osch, ocpm = opt_scheds[0], opt_cpms[0]
            results = compute_driving_slack(osch, target, cpm_result=ocpm)
        except (CPMError, KeyError, ValueError):
            return JSONResponse({"error": "schedule does not solve"}, status_code=422)
        tier_order = {"driving": 0, "secondary": 1, "tertiary": 2}
        tier_title = {
            "driving": "Critical / driving",
            "secondary": "Secondary",
            "tertiary": "Tertiary",
        }
        graded: list[tuple[int, int, float, str]] = []
        for uid, r in results.items():
            if uid == target:
                continue
            label = _EVO_TIER_LABEL.get(r.tier)
            if label in tier_order:
                graded.append((tier_order[label], uid, float(r.driving_slack_days), label))
        graded.sort(key=lambda g: (g[0], g[2], g[1]))
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        by_row: dict[int, dict[str, object]] = {}
        for a in analysis.activity_rows:
            row_uid = a.get("unique_id")
            if isinstance(row_uid, int):
                by_row[row_uid] = a

        def _cell(value: object) -> str | int | float | None:
            return value if isinstance(value, str | int | float) or value is None else str(value)

        headers = ("Tier", "UID", "Activity", "Slack (d)", *extra)
        rows: list[tuple[str | int | float | None, ...]] = []
        for _ord, uid, slack, label in graded:
            a = by_row.get(uid, {})
            custom_obj = a.get("custom")
            custom: dict[str, object] = custom_obj if isinstance(custom_obj, dict) else {}
            rows.append(
                (
                    tier_title[label],
                    uid,
                    _cell(a.get("name")),
                    round(slack, 1),
                    *(_cell(a.get(c, custom.get(c))) for c in extra),
                )
            )
        tableset = TableSet(
            f"{name} — driving tiers to {target}",
            (Table(f"Driving tiers to {target}", headers, tuple(rows)),),
        )
        return _export_response(fmt, tableset, "driving-tiers")

    @app.get("/export/{fmt}/whatif")
    def export_whatif(
        fmt: str, a: str = Query(""), b: str = Query(""), cols: str = Query("")
    ) -> Response:
        """The 'What-if' reverted-changes list for a chosen version pair, with any extra columns
        the operator toggled on — the Evolution counterfactual table's Excel export (operator
        2026-07-08)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        labels = [s.source_file or s.name for s in schedules]
        if a not in labels or b not in labels:
            return JSONResponse({"error": "unknown file(s)"}, status_code=404)
        ia, ib = labels.index(a), labels.index(b)
        prior_idx, cur_idx = (ia, ib) if ia < ib else (ib, ia)
        st = session()
        pc = compute_path_counterfactual(
            schedules[prior_idx],
            schedules[cur_idx],
            cpms[prior_idx],
            cpms[cur_idx],
            target_uid=st.target_uid,
        )
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Activity", "Why it left", "Change reverted", *extra)
        by_id = schedules[cur_idx].tasks_by_id
        per_day = schedules[cur_idx].calendar.working_minutes_per_day or 480

        def _field(uid: int, key: str) -> str | int | float | None:
            t = by_id.get(uid)
            if t is None:
                return ""
            simple: dict[str, object] = {
                "duration_days": round(
                    t.duration_minutes / (1440 if t.duration_is_elapsed else per_day), 1
                ),
                "percent_complete": t.percent_complete,
                "start": _iso_date(t.start),
                "finish": _iso_date(t.finish),
                "wbs": t.wbs or "",
                "resource_names": ", ".join(t.resource_names),
            }
            if key in simple:
                v = simple[key]
                return v if isinstance(v, str | int | float) else str(v)
            cv = t.custom_field_map.get(key)
            return cv if isinstance(cv, str | int | float) or cv is None else str(cv)

        rev = pc.reverted if pc is not None else ()
        rows = tuple(
            (r.uid, r.name, r.reason, "; ".join(r.changes), *(_field(r.uid, c) for c in extra))
            for r in rev
        )
        tableset = TableSet(
            f"What-if reverted changes — {a} → {b}",
            (Table("Reverted changes", headers, rows),),
        )
        return _export_response(fmt, tableset, "whatif")

    @app.get("/export/{fmt}/whatif-added")
    def export_whatif_added(
        fmt: str, a: str = Query(""), b: str = Query(""), cols: str = Query("")
    ) -> Response:
        """The 'What-if' work-ADDED-to-the-critical-path list for a chosen version pair, with any
        extra columns the operator toggled on (operator 2026-07-09 — the mirror of /whatif)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        labels = [s.source_file or s.name for s in schedules]
        if a not in labels or b not in labels:
            return JSONResponse({"error": "unknown file(s)"}, status_code=404)
        ia, ib = labels.index(a), labels.index(b)
        prior_idx, cur_idx = (ia, ib) if ia < ib else (ib, ia)
        st = session()
        added = _whatif_added_rows(
            schedules[prior_idx],
            schedules[cur_idx],
            cpms[prior_idx],
            cpms[cur_idx],
            st.target_uid,
        )
        extra = [c for c in (s.strip() for s in cols.split(",")) if c]
        headers = ("UID", "Activity", "Why it entered", "Detail", *extra)

        def _cell(row: dict[str, object], key: str) -> str | int | float | None:
            v = row.get(key)
            if v is None:
                custom = row.get("custom")
                if isinstance(custom, dict):
                    v = custom.get(key)
            return v if isinstance(v, str | int | float) or v is None else str(v)

        rows = tuple(
            (
                _cell(r, "unique_id"),
                _cell(r, "name"),
                _cell(r, "why_entered"),
                _cell(r, "detail"),
                *(_cell(r, c) for c in extra),
            )
            for r in added
        )
        tableset = TableSet(
            f"What-if — work added to the critical path — {a} → {b}",
            (Table("Added to the critical path", headers, rows),),
        )
        return _export_response(fmt, tableset, "whatif-added")

    @app.get("/export/{fmt}/integrity")
    def export_integrity(fmt: str, file: str = Query("")) -> Response:
        """Every integrity finding across the analyzed version pairs."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need two versions"}, status_code=422)
        labels = [sch.source_file or sch.name for sch in schedules]
        body = []
        for i in range(len(schedules) - 1):
            if file and labels[i + 1] != file:
                continue
            prior, current = schedules[i], schedules[i + 1]
            for f in detect_manipulation(
                current, prior, current_cpm=cpms[i + 1], prior_cpm=cpms[i]
            ):
                cites = "; ".join(
                    f"UID {c.unique_id} — {c.task_name}" for c in f.citations if c.unique_id
                )
                body.append(
                    (
                        f"{labels[i]} → {labels[i + 1]}",
                        str(f.severity),
                        f.metric_id,
                        f.title,
                        f.detail,
                        f.course_of_action,
                        cites,
                    )
                )
        headers = (
            "Version pair",
            "Severity",
            "Signal",
            "Finding",
            "Detail",
            "Course of action",
            "Citations",
        )
        tableset = TableSet(
            "Schedule Integrity findings",
            (Table("Integrity findings", headers, tuple(body)),),
        )
        return _export_response(fmt, tableset, "schedule-integrity")

    @app.get("/export/{fmt}/trend")
    def export_trend(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        tableset = TableSet(
            "Schedule-quality trend", trend_tables(compute_quality_trend(schedules, cpms))
        )
        return _export_response(fmt, tableset, "trend")

    @app.get("/export/{fmt}/cei")
    def export_cei(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt, TableSet("Bow Wave - CEI", bow_wave_tables(wave)), "bow-wave-cei"
        )

    @app.get("/export/{fmt}/evolution")
    def export_evolution(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        # match the on-screen view: honour the session-wide focused UID (driving-path basis)
        ev = compute_path_evolution(schedules, cpms, target_uid=session().target_uid)
        return _export_response(
            fmt,
            TableSet("Critical-path evolution", path_evolution_tables(ev)),
            "critical-path-evolution",
        )

    @app.get("/export/{fmt}/forecast")
    def export_forecast(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        labels = [s.source_file or s.name for s in schedules]
        carnac = compute_carnac_summary(schedules[-1], cpms[-1], sets[-1])
        return _export_response(
            fmt,
            TableSet("Finish forecasts", (carnac_table(carnac), *forecast_tables(labels, sets))),
            "forecast",
        )

    @app.get("/export/{fmt}/curves")
    def export_curves(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        versions = st.ordered()
        if not versions:
            return JSONResponse({"error": "need at least one schedule"}, status_code=400)
        try:
            curves = compute_month_curves(versions)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt,
            TableSet("Finish & slippage curves", month_curves_tables(curves)),
            "finish-slippage-curves",
        )

    @app.get("/export/{fmt}/wbs/{name}")
    def export_wbs(fmt: str, name: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        groups = compute_wbs_breakdown(sch)
        return _export_response(
            fmt,
            TableSet(f"WBS breakdown - {sch.name}", wbs_breakdown_tables(groups)),
            f"{name}-wbs",
        )

    @app.get("/export/{fmt}/compare")
    def export_compare(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        manip = detect_manipulation(
            schedules[-1], schedules[-2], current_cpm=cpms[-1], prior_cpm=cpms[-2]
        )
        tableset = TableSet(
            "Compare - manipulation signals",
            (findings_table(manip),),
        )
        return _export_response(fmt, tableset, "compare-signals")

    @app.get("/brief", response_class=HTMLResponse)
    def brief_view() -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Diagnostic Brief",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to build the "
                "diagnostic brief.</div>",
            )
        brief = build_brief(schedules, cpms)
        return _page(
            st,
            "Diagnostic Brief",
            _export_bar("brief") + _skipped_notice(skipped) + _brief_body(brief),
        )

    @app.get("/risks", response_class=HTMLResponse)
    def risks_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Risks & Opportunities",
                "<div class=panel>Load a schedule to see risks, issues &amp; opportunities.</div>",
            )
        # latest analyzable version (with the one before it for change findings), scoped to the
        # session filter; keep the key so the narrative cache + ask scope stay consistent.
        solv: list[tuple[str, Schedule, _Analysis]] = []
        skipped: list[str] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                skipped.append(key)
                continue
            solv.append((key, st.scope(raw), a))
        if not solv:
            return _page(
                st,
                "Risks & Opportunities",
                _skipped_notice(skipped) + "<div class=panel>No analyzable version loaded.</div>",
            )
        key, current, cur_an = solv[-1]
        prior = solv[-2][1] if len(solv) >= 2 else None
        prior_cpm = solv[-2][2].cpm if len(solv) >= 2 else None
        findings = recommend(
            current,
            prior,
            current_cpm=cur_an.cpm,
            prior_cpm=prior_cpm,
            target_uid=st.target_uid,
        )
        # Render the deterministic narrative immediately so the page never blocks on the model; the
        # local-AI polish (when a model is active) is fetched asynchronously by ai_polish.js via
        # /api/ai/narrative and swapped in. The old synchronous per-statement generate on page load
        # made this page hang (effectively "won't open") on big workbooks with a slow local model.
        body = (
            _export_bar("risks")
            + _skipped_notice(skipped)
            + _risks_body(current, findings, cur_an.narrative, key)
        )
        return _page(st, "Risks & Opportunities", body, ask_schedule=key)

    @app.get("/sra", response_class=HTMLResponse)
    def sra_view(file: str = Query("")) -> HTMLResponse:
        st = session()
        # operator picks which loaded file the SRA runs against; persist it so the simulation API
        # and the server-rendered override/risk tables all target the same schedule.
        if file.strip() and file.strip() in st.schedules:
            st.sra_file = file.strip()
        if not st.schedules:
            return _page(
                st,
                "Risk Analysis (SRA)",
                "<div class=panel>Load a schedule to run the Schedule Risk Analysis "
                "(Monte-Carlo).</div>",
            )
        # Render the controls + empty chart hosts IMMEDIATELY — the simulation (1000x CPM) is run
        # only when sra.js fetches /api/sra, never on page load (a synchronous run here would hang
        # the page on a large schedule, the prior Risks/Briefing bug).
        return _page(st, "Risk Analysis (SRA)", _what_could_go_wrong_header(st) + _sra_body(st))

    @app.post("/sra/risk")
    def sra_risk(
        low: str = Form(""),
        ml: str = Form(""),
        high: str = Form(""),
        uid: str = Form(""),
        opt_days: str = Form(""),
        ml_days: str = Form(""),
        pess_days: str = Form(""),
        remove: str = Form(""),
        clear: str = Form(""),
    ) -> RedirectResponse:
        """Persist the analyst's SRA risk inputs on the session, then redirect back to /sra.

        Handles three independent operations (any combination per request): the global triangular
        percentages (entered as 90/100/110 → stored as fractions, clamped + ordered), a per-activity
        3-point override (days → working minutes via the schedule calendar; ignored for an unknown /
        summary uid), and override removal (``remove`` a single uid / ``clear`` all)."""
        st = session()
        # global low/ml/high (percent inputs → fractions); only update on a non-blank value
        lo, mid, hi = st.sra_low, st.sra_ml, st.sra_high
        if low.strip():
            lo = _clamp_float(low, 0.05, 1.0, lo, scale=0.01)
        if ml.strip():
            mid = _clamp_float(ml, 0.5, 1.5, mid, scale=0.01)
        if high.strip():
            hi = _clamp_float(high, 1.0, 3.0, hi, scale=0.01)
        # coerce to low <= ml <= high (the triangular a <= m <= b)
        mid = max(lo, mid)
        hi = max(mid, hi)
        st.sra_low, st.sra_ml, st.sra_high = lo, mid, hi
        # per-activity override removal / clear
        if clear.strip():
            st.sra_overrides.clear()
        rm = _parse_uid(remove)
        if rm is not None:
            st.sra_overrides.pop(rm, None)
        # per-activity 3-point override (days → working minutes), only for a real non-summary task
        add_uid = _parse_uid(uid)
        if add_uid is not None and (opt_days.strip() or ml_days.strip() or pess_days.strip()):
            chosen = _sra_selected(st)
            if chosen is not None:
                _, sch, _cpm = chosen
                task = sch.tasks_by_id.get(add_uid)
                if task is not None and not task.is_summary:
                    per_day = sch.calendar.working_minutes_per_day or 1
                    o = max(0, round(_to_float(opt_days, 0.0) * per_day))
                    m = max(0, round(_to_float(ml_days, 0.0) * per_day))
                    p = max(0, round(_to_float(pess_days, 0.0) * per_day))
                    m = max(o, m)  # keep opt <= ml <= pess
                    p = max(m, p)
                    st.sra_overrides[add_uid] = (o, m, p)
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/risk-register")
    def sra_risk_register(
        action: str = Form("add"),
        rid: str = Form(""),
        name: str = Form(""),
        prob: str = Form(""),
        affected: str = Form(""),
        impact_days: str = Form(""),
        impact_pct: str = Form(""),
        days_locked: str = Form(""),
        pct_locked: str = Form(""),
        consequence: str = Form(""),
    ) -> RedirectResponse:
        """Maintain the UNIFIED risk register (entered ONCE; feeds both SRA models), then redirect.

        A risk = a name, a probability (% it occurs), an ``affected`` UID list, and BOTH magnitudes of
        the same event: an additive ``impact_days`` (the SSI model) and a multiplicative ``impact_pct``
        uplift (the legacy model). The operator types one; the other is auto-derived (client-side, and
        mirrored here for the JS-off / load path) from the affected tasks' average remaining duration;
        a supplied field is locked and used verbatim for that model. ``action`` is add / remove /
        clear. Unknown / summary UIDs are dropped; a risk mapping to no real activity is ignored."""
        st = session()
        if action == "clear":
            st.sra_risks.clear()
            return RedirectResponse(url="/sra", status_code=303)
        if action == "remove":
            st.sra_risks = [r for r in st.sra_risks if r.id != rid.strip()]
            return RedirectResponse(url="/sra", status_code=303)
        label = name.strip()
        chosen = _sra_selected(st)
        sch = chosen[1] if chosen is not None else None
        valid: list[int] = []
        if sch is not None:
            for u in _parse_uid_list(affected):
                task = sch.tasks_by_id.get(u)
                if task is not None and not task.is_summary and u not in valid:
                    valid.append(u)
        if label and valid:
            avg_rem = _affected_avg_remaining_days(sch, valid)
            days, pct, dl, pl = _reconcile_magnitudes(
                impact_days,
                impact_pct,
                days_locked.strip() in ("1", "on", "true"),
                pct_locked.strip() in ("1", "on", "true"),
                avg_rem,
            )
            p = _clamp_float(prob, 0.0, 1.0, 0.0, scale=0.01)
            cons = int(consequence) if consequence.strip().isdigit() else None
            st.sra_risk_seq += 1
            st.sra_risks.append(
                UnifiedRisk(
                    id=f"R{st.sra_risk_seq}",
                    name=label,
                    probability=p,
                    affected=tuple(valid),
                    impact_days=days,
                    impact_pct=pct,
                    days_locked=dl,
                    pct_locked=pl,
                    consequence_rating=min(5, max(1, cons)) if cons is not None else None,
                )
            )
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/api/sra")
    def sra_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, cpm = chosen
        iters = max(100, min(10000, iterations))
        dist = "pert" if distribution == "pert" else "triangular"
        config = SRAConfig(
            iterations=iters,
            auto_low=st.sra_low,
            auto_most_likely=st.sra_ml,
            auto_high=st.sra_high,
            distribution=dist,
        )
        # The Risk Ranking Factors + Best/Worst-Case durations are entered ONCE (the SSI grid) and
        # apply to BOTH models: here they become this legacy run's per-activity 3-point overrides
        # (BestCase, MostLikely=remaining, WorstCase minutes -> optimistic/most_likely/pessimistic).
        # An explicit legacy per-activity override still wins; tasks with neither use the global
        # triangular. compute_sra/RiskEvent are untouched — only the inputs we hand it are shared.
        overrides = {
            u: ActivityRisk(u, o, m, p)
            for u, (o, m, p) in _ssi_three_point(st, sch).items()
            if u in sch.tasks_by_id and o <= m <= p  # skip any inverted manual BC/WC triple
        }
        overrides.update(
            {
                u: ActivityRisk(u, o, m, p)
                for u, (o, m, p) in st.sra_overrides.items()
                if u in sch.tasks_by_id and o <= m <= p
            }
        )
        # never 500 on the simulation — surface the engine message as a 422 instead. A large schedule
        # runs the 1000x CPM Monte-Carlo in a worker process so a concurrent request (e.g. Ask-the-AI)
        # isn't starved while it computes; the result is byte-identical to an in-process run.
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            result = run_maybe_offloaded(
                heavy,
                compute_sra,
                sch,
                cpm,
                config=config,
                overrides=overrides,
                risks=_risk_events(st),
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_sra_data(st, sch, cpm, result))

    # --- SSI Schedule Risk & Opportunity Analysis (ADR-0123) -------------------------------
    @app.post("/sra/ssi-run-config")
    def ssi_run_config(
        focus_uid: str = Form(""),
        occurrence_mode: str = Form("random_each"),
        correlation: float = Form(0.0),
        use_risks: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        st.sra_focus_uid = int(focus_uid) if focus_uid.strip().isdigit() else None
        st.sra_occurrence_mode = (
            "exact_overall" if occurrence_mode == "exact_overall" else "random_each"
        )
        st.sra_correlation = min(1.0, max(0.0, correlation))
        st.sra_use_risk_register = use_risks in ("on", "true", "1")
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/factor-table")
    def ssi_factor_table(
        sub1: float = Form(50.0),
        add1: float = Form(10.0),
        sub2: float = Form(40.0),
        add2: float = Form(20.0),
        sub3: float = Form(30.0),
        add3: float = Form(30.0),
        sub4: float = Form(20.0),
        add4: float = Form(40.0),
        sub5: float = Form(10.0),
        add5: float = Form(50.0),
    ) -> RedirectResponse:
        st = session()
        raw = ((1, sub1, add1), (2, sub2, add2), (3, sub3, add3), (4, sub4, add4), (5, sub5, add5))
        st.sra_factor_rows = tuple(
            (f, min(100.0, max(0.0, s)), min(300.0, max(0.0, a))) for f, s, a in raw
        )
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/factor")
    def ssi_set_factor(uids: str = Form(""), factor: int = Form(3)) -> RedirectResponse:
        st = session()
        f = min(5, max(0, factor))  # factor 0 is valid = no Best/Worst uncertainty
        for tok in re.split(r"[,\s]+", uids.strip()):
            if tok.isdigit():
                st.sra_factors[int(tok)] = f
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/auto-calc")
    def ssi_auto_calc(scope: str = Form("all"), uids: str = Form("")) -> RedirectResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is not None:
            _key, sch, _cpm = chosen
            tbl = RiskFactorTable(rows=st.sra_factor_rows)
            want: set[int] | None = None
            if scope == "selected":
                want = {int(t) for t in re.split(r"[,\s]+", uids.strip()) if t.isdigit()}
            for t in non_summary(sch):
                u = t.unique_id
                if u not in st.sra_factors or (want is not None and u not in want):
                    continue
                rem = (
                    t.remaining_duration_minutes
                    if t.remaining_duration_minutes is not None
                    else t.duration_minutes
                )
                bc, _ml, wc = factor_to_bc_wc(rem, st.sra_factors[u], tbl)
                st.sra_bcwc[u] = (bc, wc)
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/api/sra/ssi")
    def sra_ssi_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        cfg = SRAConfig(
            iterations=max(100, min(10000, iterations)),
            distribution="pert" if distribution == "pert" else "triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        # offload the heavy Monte-Carlo to a worker process on big schedules (keeps the server
        # responsive for a concurrent Ask-the-AI call); byte-identical to an in-process run
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            result = run_maybe_offloaded(
                heavy,
                compute_sra_ssi,
                sch,
                config=cfg,
                three_point=_ssi_three_point(st, sch),
                risks=_schedule_risks(st),
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_ssi_data(sch, result))

    @app.get("/api/sra/oat")
    def sra_oat_json() -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        exclude = (
            frozenset(u for r in st.sra_risks for u in r.affected)
            if st.sra_use_risk_register
            else frozenset()
        )
        # the OAT sweep is one CPM solve per task — offload it on big schedules too
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            oat = run_maybe_offloaded(
                heavy,
                compute_oat_sensitivity,
                sch,
                three_point=_ssi_three_point(st, sch),
                target_uid=st.sra_focus_uid,
                exclude_uids=exclude,
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        names = sch.tasks_by_id
        mpd = sch.calendar.working_minutes_per_day or 480
        return JSONResponse(
            {
                "rows": [
                    {
                        "uid": o.unique_id,
                        "name": names[o.unique_id].name if o.unique_id in names else "",
                        "bc_days": round(o.bc_minutes / mpd, 1),
                        "wc_days": round(o.wc_minutes / mpd, 1),
                        "ml_days": round(o.ml_minutes / mpd, 1),
                        "opportunity": o.opportunity_days,
                        "risk": o.risk_days,
                        "total": o.total_days,
                    }
                    for o in oat[:40]
                ]
            }
        )

    @app.get("/api/sra/grid")
    def sra_grid_json() -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, cpm = chosen
        return JSONResponse(
            {
                "rows": _ssi_grid_rows(st, sch, cpm),
                "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
            }
        )

    @app.post("/sra/grid")
    def sra_grid_save(deltas: str = Form("[]")) -> JSONResponse:
        """Batched inline-edit save from the SSI grid: one JSON array of per-task deltas
        ``[{uid, factor?, bc_days?, wc_days?, focus?}]`` (the fields_json/gantt JSON-in-page
        precedent). A factor delta auto-fills Best/Worst from the factor table; an explicit
        bc_days/wc_days delta is a manual override that wins (mirrors ``_ssi_three_point``)."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        mpd = sch.calendar.working_minutes_per_day or 480
        tbl = RiskFactorTable(rows=st.sra_factor_rows)
        by_id = sch.tasks_by_id
        try:
            items = json.loads(deltas)
        except (ValueError, TypeError):
            return JSONResponse({"error": "bad deltas payload"}, status_code=422)
        saved = 0
        for d in items if isinstance(items, list) else []:
            if not isinstance(d, dict):
                continue
            uid = d.get("uid")
            if not isinstance(uid, int) or uid not in by_id or by_id[uid].is_summary:
                continue
            task = by_id[uid]
            rem = (
                task.remaining_duration_minutes
                if task.remaining_duration_minutes is not None
                else task.duration_minutes
            )
            changed = False
            if d.get("focus"):
                st.sra_focus_uid = uid
                changed = True
            if d.get("factor") not in (None, ""):
                try:
                    # factor 0 is VALID (no Best/Worst uncertainty -> use remaining); only 1..5 carry
                    # a Best/Worst spread, so clamp to 0..5, not 1..5
                    f = min(5, max(0, int(d["factor"])))
                except (TypeError, ValueError):
                    f = None
                if f is not None:
                    st.sra_factors[uid] = f
                    bc, _ml, wc = factor_to_bc_wc(rem, f, tbl)
                    st.sra_bcwc[uid] = (bc, wc)
                    changed = True
            bc_min, wc_min = st.sra_bcwc.get(uid, (rem, rem))
            manual = False
            for key, slot in (("bc_days", 0), ("wc_days", 1)):
                if d.get(key) not in (None, ""):
                    try:
                        minutes = max(0, round(float(d[key]) * mpd))
                    except (TypeError, ValueError):
                        continue
                    bc_min, wc_min = (minutes, wc_min) if slot == 0 else (bc_min, minutes)
                    manual = True
            if manual:
                st.sra_bcwc[uid] = (int(bc_min), int(wc_min))
                changed = True
            saved += int(changed)
        return JSONResponse({"ok": True, "saved": saved})

    @app.get("/sra/ssi/save")
    def sra_ssi_save() -> Response:
        """Download the whole SSI setup (focus, factor table, per-task factors + Best/Worst,
        risk register, run options) as a versioned JSON file — local download, CUI-safe."""
        st = session()
        return Response(
            json.dumps(_ssi_setup_dict(st), indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sra-ssi-setup.json"'},
        )

    @app.post("/sra/ssi/load")
    def sra_ssi_load(setup: UploadFile) -> RedirectResponse:
        """Restore an SSI setup from a previously-saved JSON file. UIDs are validated against the
        active schedule (unknown/summary tasks dropped, factors clamped) so a setup saved on one
        version applies cleanly to another."""
        st = session()
        try:
            payload = json.loads(setup.file.read())
        except (ValueError, TypeError):
            return RedirectResponse(url="/sra", status_code=303)
        if isinstance(payload, dict):
            _apply_ssi_setup(st, payload)
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/export/{fmt}/sra")
    def export_sra(fmt: str) -> Response:
        """The SSI setup + a focus-targeted run + the deterministic OAT as a six-table Excel/Word
        hand-out (ADR-0123). Runs the Monte-Carlo + OAT on demand (off the page-load path)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        tp = _ssi_three_point(st, sch)
        cfg = SRAConfig(
            iterations=2000,
            distribution="triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        result = run_maybe_offloaded(
            heavy, compute_sra_ssi, sch, config=cfg, three_point=tp, risks=_schedule_risks(st)
        )
        exclude = (
            frozenset(u for r in st.sra_risks for u in r.affected)
            if st.sra_use_risk_register
            else frozenset()
        )
        oat = run_maybe_offloaded(
            heavy,
            compute_oat_sensitivity,
            sch,
            three_point=tp,
            target_uid=st.sra_focus_uid,
            exclude_uids=exclude,
        )
        if fmt == "docx":
            # the comprehensive narrative SRA report (PM summary -> per-section detail + vector
            # charts + the 5x5 matrices + assumptions); ADR-0124
            return Response(
                content=render_document(_sra_report_blocks(st, sch, result, oat)),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="sra-report.docx"'},
            )
        return _export_response(fmt, _ssi_export_tables(st, sch, result, oat), "sra-ssi")

    @app.get("/export/{fmt}/sra-registry")
    def export_sra_registry(fmt: str) -> Response:
        """The risk / opportunity registry as a standalone downloadable workbook/doc (register +
        the per-task Best/Worst durations) — the operator's downloadable risk registry (ADR-0124)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        tp = _ssi_three_point(st, sch)
        cfg = SRAConfig(
            iterations=2000,
            distribution="triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        result = run_maybe_offloaded(
            len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD,
            compute_sra_ssi,
            sch,
            config=cfg,
            three_point=tp,
            risks=_schedule_risks(st),
        )
        keep = {"Risk register", "Per-task durations"}
        full = _ssi_export_tables(st, sch, result, [])  # registry needs no OAT (skip the 2N solves)
        ts = TableSet(
            f"SRA Risk Registry - {sch.name}",
            tuple(t for t in full.tables if t.title in keep),
        )
        return _export_response(fmt, ts, "sra-risk-registry")

    # ── SRA Excel round-trip templates (ADR-0211) ─────────────────────────────────────────────
    # Export a fill-in workbook, edit it in Excel, re-import — no third-party parser (Law 1), and
    # nothing fabricated on import: unmatched UIDs are dropped and counted, an inverted Best/Worst
    # pair is skipped, and the operator sees a one-shot summary of exactly what landed (Law 2).
    @app.get("/export/xlsx/risk-register-template")
    def export_risk_register_template() -> Response:
        """Download the risk-register fill-in template (current register or one example row + a
        read-only task reference sheet). Re-import via ``POST /sra/import/risk-register``."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        return _export_response("xlsx", _risk_register_template(st, sch), "risk-register-template")

    @app.get("/export/xlsx/task-risk-template")
    def export_task_risk_template() -> Response:
        """Download the per-task Best/Worst-Case + Risk-Ranking-Factor fill-in template (one row per
        activity, pre-filled). Re-import via ``POST /sra/import/task-risk``."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        return _export_response("xlsx", _task_risk_template(st, sch), "task-risk-template")

    @app.post("/sra/import/risk-register")
    def sra_import_risk_register(file: UploadFile) -> RedirectResponse:
        """Rebuild the session risk register from a filled-in template, then redirect to /sra with a
        one-shot summary. A bad workbook (or no schedule loaded) is reported, never silently lost."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            st.sra_import_msg = "Load a schedule before importing a risk register."
            return RedirectResponse(url="/sra", status_code=303)
        _key, sch, _cpm = chosen
        # cap the COMPRESSED upload (parity with /upload's 500 MB per-file limit) before read_xlsx,
        # whose own decompression cap then guards against a zip bomb (small file, huge inflation).
        data = file.file.read(_MAX_UPLOAD_BYTES + 1)
        if len(data) > _MAX_UPLOAD_BYTES:
            st.sra_import_msg = (
                f"Risk register not imported — file exceeds the "
                f"{_MAX_UPLOAD_BYTES // (1024 * 1024)} MB cap."
            )
            return RedirectResponse(url="/sra", status_code=303)
        try:
            sheets = read_xlsx(data)
        except XlsxError as exc:
            st.sra_import_msg = f"Could not read that file: {exc}"
            return RedirectResponse(url="/sra", status_code=303)
        summary = _import_risk_register(st, sch, sheets)
        if "error" in summary:
            st.sra_import_msg = f"Risk register not imported — {summary['error']}."
        else:
            st.sra_import_msg = (
                f"Imported {summary['imported']} risk(s); skipped {summary['skipped']} incomplete "
                f"row(s); dropped {summary['dropped_uids']} unmatched UID(s)."
            )
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/import/task-risk")
    def sra_import_task_risk(file: UploadFile) -> RedirectResponse:
        """Apply per-task Risk Ranking Factors + Best/Worst-Case durations from a filled-in template,
        then redirect to /sra with a one-shot summary."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            st.sra_import_msg = "Load a schedule before importing task risk inputs."
            return RedirectResponse(url="/sra", status_code=303)
        _key, sch, _cpm = chosen
        # cap the COMPRESSED upload (parity with /upload's 500 MB per-file limit) before read_xlsx,
        # whose own decompression cap then guards against a zip bomb (small file, huge inflation).
        data = file.file.read(_MAX_UPLOAD_BYTES + 1)
        if len(data) > _MAX_UPLOAD_BYTES:
            st.sra_import_msg = (
                f"Task risk inputs not imported — file exceeds the "
                f"{_MAX_UPLOAD_BYTES // (1024 * 1024)} MB cap."
            )
            return RedirectResponse(url="/sra", status_code=303)
        try:
            sheets = read_xlsx(data)
        except XlsxError as exc:
            st.sra_import_msg = f"Could not read that file: {exc}"
            return RedirectResponse(url="/sra", status_code=303)
        summary = _import_task_risk(st, sch, sheets)
        if "error" in summary:
            st.sra_import_msg = f"Task risk inputs not imported — {summary['error']}."
        else:
            st.sra_import_msg = (
                f"Set {summary['factors']} Risk Ranking Factor(s) and {summary['bcwc']} Best/Worst "
                f"duration pair(s); dropped {summary['dropped_uids']} unmatched UID(s)."
            )
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/export/{fmt}/brief")
    def export_brief(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        brief = build_brief(schedules, cpms)
        if fmt == "docx":
            blocks = cast("list[Block]", brief_blocks(brief))
            return Response(
                content=render_document(blocks),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="diagnostic-brief.docx"'},
            )
        tables = tuple(s.table for s in brief.sections if s.table is not None)
        questions = Table(
            "Questions the data raises",
            ("#", "Question (cited)"),
            tuple(
                (i + 1, stmt.rendered())
                for i, stmt in enumerate(p for s in brief.sections for p in s.paragraphs)
            ),
        )
        return _export_response(
            fmt, TableSet(brief.title, (*tables, questions)), "diagnostic-brief"
        )

    @app.get("/export/{fmt}/briefing")
    def export_briefing(fmt: str) -> Response:
        """The leadership Executive Briefing as a Word (.docx) or Excel (.xlsx) hand-out — the
        same cited content the /briefing page renders (ADR-0121)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        briefing = build_briefing(schedules, cpms=cpms)
        if fmt == "docx":
            blocks = cast("list[Block]", briefing_blocks(briefing))
            return Response(
                content=render_document(blocks),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="executive-briefing.docx"'},
            )
        tables = tuple(
            Table(s.heading, s.table.headers or ("Field", "Value"), s.table.rows)
            for s in briefing.sections
            if s.table is not None and s.table.rows
        )
        return _export_response(fmt, TableSet(briefing.title, tables), "executive-briefing")

    @app.get("/briefing", response_class=HTMLResponse)
    def briefing_view() -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Executive Briefing",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to build the briefing.</div>",
            )
        # Render the DETERMINISTIC briefing immediately so the page opens instantly. The
        # synchronous per-section AI polish on page load made this page hang (effectively "won't
        # open") on big workbooks with a slow local model. ai_polish.js fetches /api/ai/briefing in
        # the background and swaps in the local-AI-polished version when a model is active.
        briefing = build_briefing(schedules, cpms=cpms)
        body = (
            _the_briefing_header(briefing, schedules[-1], cpms[-1])
            + _skipped_notice(skipped)
            + '<div id=briefingBody data-ai-endpoint="/api/ai/briefing">'
            + _briefing_body(briefing)
            + '</div><script src="/static/ai_polish.js"></script>'
        )
        return _page(st, "Executive Briefing", body)

    @app.get("/api/ai/narrative")
    def api_ai_narrative(key: str = "") -> JSONResponse:
        """Local-AI-polished Risks narrative for one schedule (fetched off the page-load path).

        Runs the (possibly slow) model here instead of during the page render, wrapping the whole
        AI path so it can never hang or 500 the page: ``{"polished": false}`` when no model is
        active or anything fails (the client keeps the engine read), else the polished list HTML."""
        st = session()
        raw = st.schedules.get(key)
        if raw is None:
            return JSONResponse({"polished": False})
        try:
            analysis = st.analysis_for(key, raw)
            narrative = _polished_narrative(st, key, st.scope(raw), analysis)
            polished = narrative is not analysis.narrative  # a real backend produced new prose
            html = "".join(f"<li>{_e(s.rendered())}</li>" for s in narrative.statements)
        except Exception:
            logger.warning("AI narrative endpoint failed; client keeps the deterministic read")
            return JSONResponse({"polished": False})
        return JSONResponse({"polished": polished, "html": html})

    @app.get("/api/ai/briefing")
    def api_ai_briefing() -> JSONResponse:
        """Local-AI-polished Executive Briefing (fetched off the page-load path).

        Same contract as :func:`api_ai_narrative`: never blocks or 500s the page —
        ``{"polished": false}`` when no model is active or generation fails, else the polished
        briefing body HTML for the client to swap in."""
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"polished": False})
        backend = _active_backend(st)
        if backend.name == "null":
            return JSONResponse({"polished": False})
        try:
            briefing = build_briefing(schedules, cpms=cpms, backend=backend)
            html = _briefing_body(briefing)
        except Exception:
            logger.warning("AI briefing endpoint failed; client keeps the deterministic briefing")
            return JSONResponse({"polished": False})
        return JSONResponse({"polished": True, "html": html})

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> HTMLResponse:
        st = session()
        return _page(st, "AI Settings", _settings_body(st))

    @app.post("/settings")
    def update_settings(
        classification: str = Form("CLASSIFIED"),
        backend: str = Form("ollama"),
        model: str = Form("qwen2.5:7b-instruct"),
        qa_mode: str = Form("annotate"),
        endpoint: str = Form("http://127.0.0.1:11434"),
        openai_endpoint: str = Form("http://127.0.0.1:1234"),
        second_backend: str = Form("none"),
        second_model: str = Form(""),
        gen_timeout: float = Form(3600.0),
    ) -> RedirectResponse:
        st = session()
        try:
            cls = Classification(classification)
        except ValueError:
            cls = Classification.CLASSIFIED  # unknown -> safe default
        if qa_mode not in ("annotate", "strict", "interpretive"):
            qa_mode = "annotate"
        if second_backend not in ("none", "ollama", "openai"):
            second_backend = "none"
        # generation timeout: clamp to a sane window (30s … 1h) so a big slow model can finish
        # but a wedged one can't hang a request forever
        gen_timeout = min(3600.0, max(30.0, gen_timeout))
        # the backend constructor enforces loopback too (Law 1) — this just keeps a typo'd
        # remote host from sitting in the config looking accepted
        if not is_local_http_endpoint(endpoint.strip()):
            endpoint = "http://127.0.0.1:11434"
        if not is_local_http_endpoint(openai_endpoint.strip()):
            openai_endpoint = "http://127.0.0.1:1234"
        st.ai_config = AIConfig(
            classification=cls,
            backend=backend,
            model=model,
            endpoint=endpoint.strip(),
            qa_mode=qa_mode,
            openai_endpoint=openai_endpoint.strip(),
            second_backend=second_backend,
            second_model=second_model.strip(),
            gen_timeout=gen_timeout,
        )
        st.backend_cache = None  # re-route immediately — a settings change must take effect now
        st.second_cache = None
        # Lazy Ollama lifecycle (ADR-0122): the desktop launcher's manager starts `ollama serve`
        # only when the operator turns the Ollama backend on — never at tool launch — and stops it
        # again the moment they switch the AI off it (to Null/OpenAI/Cloud), so the local model is
        # never left consuming RAM/CPU once it is no longer the chosen backend. Both run off-thread
        # so the redirect never waits on the server coming up or shutting down.
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            if "ollama" in (backend, second_backend):
                threading.Thread(target=manager.ensure_running, daemon=True).start()
            else:
                threading.Thread(target=manager.shutdown, daemon=True).start()
        return RedirectResponse(url="/settings", status_code=303)

    @app.get("/api/ai/models")
    def ai_models(kind: str = Query("ollama"), endpoint: str = Query("")) -> JSONResponse:
        """Probe a LOCAL model server for the model ids it currently serves.

        Feeds the live model dropdowns in AI Settings so the operator picks a real, valid id
        (especially for OpenAI-compatible servers, where the loaded model id must match exactly).
        Loopback-only and fail-closed: a non-loopback endpoint returns ``reachable: false`` and
        never reaches out (Law 1)."""
        kind = kind if kind in ("ollama", "openai") else "ollama"
        ep = endpoint.strip()
        default = "http://127.0.0.1:11434" if kind == "ollama" else "http://127.0.0.1:1234"
        if ep and not is_local_http_endpoint(ep):
            return JSONResponse(
                {"reachable": False, "models": [], "reason": "endpoint must be a loopback URL"}
            )
        try:
            be: AIBackend = (
                OllamaBackend(endpoint=ep or default, model="", timeout=8.0)
                if kind == "ollama"
                else OpenAICompatBackend(endpoint=ep or default, model="", timeout=8.0)
            )
        except Exception as exc:  # loopback guard or bad URL — report, never raise outward
            return JSONResponse({"reachable": False, "models": [], "reason": str(exc)})
        reason: str | None
        try:
            reason = be.unavailable_reason()  # type: ignore[attr-defined]
        except Exception as exc:
            reason = str(exc)
        models: list[str] = []
        if reason is None:
            try:
                models = list(be.list_models())
            except Exception as exc:
                reason = str(exc)
        return JSONResponse({"reachable": reason is None, "models": models, "reason": reason or ""})

    @app.post("/settings/ai-off")
    def ai_off() -> RedirectResponse:
        """One click: turn the AI fully off — route back to the deterministic Null backend AND stop
        the local model. The operator asked for an explicit off switch once the AI is on; this also
        frees the RAM/CPU the local model was using without quitting the tool."""
        st = session()
        st.ai_config = AIConfig(classification=st.ai_config.classification, backend="null")
        st.backend_cache = None  # re-route to Null immediately
        st.second_cache = None
        with st._lock:  # guard the polished clear like its peer caches (audit ADR-0250)
            st.polished.clear()  # drop any model-polished narratives so pages show the engine read
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            threading.Thread(
                target=manager.shutdown, daemon=True
            ).start()  # unload + stop, off-thread
        return RedirectResponse(url="/settings", status_code=303)

    @app.get("/help", response_class=HTMLResponse)
    def help_page() -> HTMLResponse:
        st = session()
        rows = "".join(
            f'<tr id="m-{_e(d.metric_id)}"><td>{_e(d.name)}</td>'
            f"<td class=muted>{_e(reliability_dimension(d.metric_id))}</td>"
            f"<td>{_e(d.definition)}</td>"
            f"<td><code>{_e(d.formula)}</code></td><td class=muted>{_e(d.source)}</td></tr>"
            for d in METRIC_DICTIONARY.values()
        )
        body = (
            "<div class=panel><h2>Metric dictionary</h2>"
            "<p class=muted>Every metric the tool emits, with its formula and source. "
            "Each computed value also cites file + UniqueID + task name so you can verify it "
            "in the parent schedule. The <b>Dimension</b> column tags each metric with the NASA "
            "Schedule Management Handbook reliability dimension it most informs (Comprehensiveness "
            "/ Construction / Realism / Affordability) &mdash; an organizational lens, not a "
            "computed figure.</p>"
            f"<table><tr><th scope=col>Metric</th><th scope=col>Dimension</th>"
            f"<th scope=col>Definition</th><th scope=col>Formula</th>"
            f"<th scope=col>Source</th></tr>{rows}</table></div>"
        )
        return _page(st, "Metric Dictionary", body)

    @app.post("/target")
    def set_target(uid: str = Form(""), next_url: str = Form("/")) -> RedirectResponse:
        """Set (or clear, with a blank/invalid uid) the session-wide target activity.

        The target now also acts as the analysis ENDPOINT (every metric/visual is restricted to it
        and its drivers), so this funnels through :meth:`SessionState.set_target` to invalidate the
        scope/analysis caches — otherwise stale full-population results would survive the change."""
        st = session()
        st.set_target(_parse_uid(uid))
        # local redirect only: a path on this app, never a scheme/host ("//host" included)
        dest = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/role")
    def set_role_route(role: str = Form("")) -> RedirectResponse:
        """Set (or clear, via ``role=""``) the audience role (v4 F4, ADR-0255) — a curated entry
        point only; fail-soft on an unknown id. Returns to the front page, where the Start-here
        strip and nav highlight reflect the pick."""
        session().set_role(role or None)
        return RedirectResponse(url="/", status_code=303)

    @app.post("/language")
    def set_language(request: Request, lang: str = Form("en")) -> RedirectResponse:
        """Set the UI/AI display language (ADR-0099); returns to the page the user was on."""
        session().language = i18n.normalize(lang)
        # return to the referring page, reduced to a local path (host stripped, no open redirect)
        path = urlparse(request.headers.get("referer") or "/").path or "/"
        dest = path if path.startswith("/") and not path.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/api/translate")
    async def translate_api(request: Request) -> JSONResponse:
        """Translate a batch of strings for the client (catalog → session cache → AI model).

        Covers what the catalog does not (imported names, AI prose). Falls back to the source text
        when no model is reachable, so the page is never broken — only less fully translated."""
        st = session()
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"translations": {}})
        lang = i18n.normalize(body.get("lang"))
        texts = body.get("texts")
        if lang == i18n.DEFAULT_LANGUAGE or not isinstance(texts, list):
            return JSONResponse({"translations": {}})
        wanted = [str(t) for t in texts][:400]
        return JSONResponse({"translations": _translate_batch(wanted, lang, st)})

    @app.post("/session/wipe")
    def wipe() -> RedirectResponse:
        st = session()
        with st._lock:  # atomic vs any in-flight render (QC audit D18)
            st.schedules.clear()
            st.file_meta.clear()
            st.content_hashes.clear()
            st.margin_overlay.clear()  # drop the operator's confirmed schedule-margin overlay
            st.margin_band_dates = None  # drop the Fig 5-30 band phase dates (ADR-0254)
            st.margin_band_rates = FIG_5_30_DEFAULT_RATES
            st.margin_risk_pcts = (DEFAULT_WATCH_PCT, DEFAULT_CORRECTIVE_PCT)
            st.role = None  # back to "Show everything" (ADR-0255)
            st.analyses.clear()
            st.summaries.clear()
            st.polished.clear()
            st.set_filter(())  # drop the session-wide field filter and its scope cache
            st.set_saved_group(None)  # drop the session-wide saved group
            st.filter_mode = "reduce"  # back to the default (reduce) filter mode
            st.flash = None
            st.target_uid = None
            st.sra_focus_uid = None  # target_uid + sra_focus_uid are coupled (see set_target)
        # a wipe clears the on-disk CUI cache too (parsed schedules + derived metrics), so nothing
        # of the operator's data survives the reset (fails soft; outside the state lock — its own)
        get_default_cache().clear()
        # reset the SRA manual inputs back to the screening defaults
        st.sra_low = 0.9
        st.sra_ml = 1.0
        st.sra_high = 1.10
        st.sra_overrides.clear()
        st.sra_risks.clear()
        st.sra_risk_seq = 0
        # A wipe is a full reset: turn the AI back off and stop any local model it is running, so a
        # wiped session never leaves Ollama consuming RAM/CPU (operator report: Ollama survived a
        # Wipe → Quit). Re-enabling is one click in AI Settings.
        st.ai_config = AIConfig(classification=st.ai_config.classification, backend="null")
        st.backend_cache = None
        st.second_cache = None
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            threading.Thread(target=manager.shutdown, daemon=True).start()
        logger.info("session wiped")
        return RedirectResponse(url="/", status_code=303)

    @app.post("/session/ram-threshold")
    def ram_threshold(gb: float = Form(...)) -> RedirectResponse:
        """Set the loaded-schedule RAM warn threshold, in GB (v4 Feature 2). A warning only — it
        never blocks a load. Clamped to a sane floor so it can't be set to nag on every file."""
        st = session()
        st.ram_warn_bytes = max(1, int(gb * 1024**3))  # >=1 byte; 0/negative → 1 (warn always)
        logger.info("ram warn threshold set to %.2f GB", gb)
        return RedirectResponse(url="/portfolio", status_code=303)

    @app.get("/healthz")
    def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "loaded": len(session().schedules)})

    return app


def _safe_filename(name: str) -> str:
    """Strip characters that could break out of the Content-Disposition filename (header hygiene)."""
    return name.translate({ord(c): None for c in '"\\\r\n'})


def _clean_key(name: str) -> str:
    """A friendly schedule key: the filename with all supported extensions stripped."""
    exts = {e.lower() for e in supported_extensions()}
    path = Path(Path(name).name)
    while path.suffix.lower() in exts:
        path = path.with_suffix("")
    return path.name or "schedule"


def _find_schedule(st: SessionState, name: str) -> tuple[str | None, Schedule | None]:
    """Resolve a schedule by its session KEY or its display label (source_file / cleaned name).

    Drill panels cite a file by its display label (``source_file``) while the session keys by the
    extension-stripped filename, so a raw ``st.schedules.get(label)`` would miss. This tries the
    key first, then matches on source_file / cleaned name, and returns ``(key, schedule)`` (the key
    is needed for the per-key analysis cache) or ``(None, None)``."""
    sch = st.schedules.get(name)
    if sch is not None:
        return name, sch
    for key, s in st.schedules.items():
        if s.source_file == name or _clean_key(s.source_file or s.name) == name:
            return key, s
    return None, None


def _unique_key(base: str, existing: dict[str, Schedule]) -> str:
    """``base`` unless taken, else ``base (2)``, ``base (3)``, … so uploads never collide."""
    if base not in existing:
        return base
    counter = 2
    while f"{base} ({counter})" in existing:
        counter += 1
    return f"{base} ({counter})"


def _parse_upload_meta(file_meta: str) -> list[tuple[str | None, float | None]]:
    """Parse the client's per-file companion metadata into ``(top_folder | None, mtime | None)``.

    The browser POSTs a JSON array aligned to the upload order, each entry
    ``{"rel": webkitRelativePath, "mtime": lastModified_ms}``. A folder upload gives
    ``rel = "TopFolder/2023/x.mpp"`` → folder ``"TopFolder"``; a loose (individually picked) file
    gives an empty ``rel`` → folder ``None``. Malformed / absent input returns ``[]`` (every file is
    then treated as loose — a missing companion field is never an error, only a lost grouping hint).
    """
    if not file_meta:
        return []
    try:
        parsed = json.loads(file_meta)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[tuple[str | None, float | None]] = []
    for entry in parsed:
        rel = (
            str(entry.get("rel") or "").replace("\\", "/").strip("/")
            if isinstance(entry, dict)
            else ""
        )
        folder = rel.split("/", 1)[0] if "/" in rel else None
        raw = entry.get("mtime") if isinstance(entry, dict) else None
        mtime = float(raw) if isinstance(raw, int | float) and not isinstance(raw, bool) else None
        out.append((folder, mtime))
    return out


def _parse_skipped_files(skipped_files: str) -> list[str]:
    """Parse the client's list of files it could not read into short ``"path (reason)"`` labels.

    ``home.js`` pre-reads each picked file and posts a JSON array of ``{"path", "reason"}`` for the
    ones whose read failed (an un-hydrated OneDrive placeholder, or a file open in MS Project — both
    surface as a browser ``NotReadableError``). Malformed / absent input returns ``[]``. Bounded so a
    huge selection can't flood the manifest; each label is escaped at render time by the caller."""
    if not skipped_files:
        return []
    try:
        parsed = json.loads(skipped_files)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for entry in parsed[:200]:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").replace("\\", "/").strip() or "(unnamed file)"
        reason = str(entry.get("reason") or "").strip()
        out.append(f"{path} ({reason})" if reason else path)
    return out


def _grouping_notices(projects: tuple[Project, ...]) -> tuple[str, ...]:
    """One concise manifest line per Project that carries a grouping notice (disagreeing folder
    titles, a title-less needs-attention file, or a data-date tie broken by last-modified time),
    prefixed with the Project title. Deduplicated and capped so a large ingest can't flood the
    dashboard."""
    lines: list[str] = []
    for p in projects:
        for note in p.notices:
            line = f"{p.title}: {note}"
            if line not in lines:
                lines.append(line)
    cap = 8
    if len(lines) > cap:
        lines = [*lines[:cap], f"(+{len(lines) - cap} more grouping notices)"]
    return tuple(lines)


def _parse_upload(name: str, data: bytes) -> Schedule:
    """Parse uploaded bytes by extension — text formats in memory, .mpp via a temp file."""
    # decode EXACTLY like the file-path importers so the same file can never parse
    # differently (or reject) depending on whether it was opened or uploaded
    suffix = Path(name).suffix.lower()
    if suffix == ".json":
        return parse_json_text(data.decode("utf-8-sig"))
    if suffix in {".xml", ".mspdi"}:
        return parse_mspdi_text(data.decode("utf-8-sig", errors="replace"))
    if suffix == ".xer":
        return parse_xer_text(decode_xer_bytes(data))
    # native .mpp / .mpt — needs the MPXJ runner + a JRE. Write into a temp *directory* and
    # close the file before parsing: on Windows an open NamedTemporaryFile handle blocks the
    # MPXJ java subprocess from reading the path (the upload would always fail on Windows).
    with tempfile.TemporaryDirectory(prefix="sf-upload-") as tmp:
        temp_path = Path(tmp) / f"upload{suffix or '.mpp'}"
        temp_path.write_bytes(data)
        return load_schedule(temp_path)


def _status_class(status: object) -> str:
    # the values are CSS class names (not secrets); B105 is a false positive here.
    return {"PASS": "pass", "FAIL": "fail"}.get(str(status), "na")  # nosec B105


def _stoplight_board(checks: tuple[AuditCheck, ...]) -> str:
    """The handbook's canonical at-a-glance metric stoplight (Figs 7-10..7-38): one chip per DCMA-14
    check, green PASS / red FAIL / grey N/A, with the value + threshold. Pure presentation over the
    existing ``AuditCheck.status`` — adds no new threshold or number."""
    if not checks:
        return ""
    chips = []
    for c in checks:
        cls = _status_class(c.status)
        thr = "" if c.threshold is None else f" (≤ {c.threshold:g}{_e(c.unit)})"
        title = f"{c.name}: {c.value:g}{c.unit} vs threshold{thr or ' n/a'} — {c.status}"
        chips.append(
            f'<span class="sl-chip sl-{cls}" title="{_e(title)}">'
            f"<span class=sl-name>{_e(c.name)}</span> "
            f"<b>{c.value:g}{_e(c.unit)}</b></span>"
        )
    legend = (
        '<div class=sl-legend><span class="sl-key sl-pass">pass</span>'
        '<span class="sl-key sl-fail">fail</span>'
        '<span class="sl-key sl-na">n/a</span></div>'
    )
    return f'<div class=stoplight-board role=list aria-label="DCMA-14 stoplight">{"".join(chips)}</div>{legend}'


def _unschedulable_panel(sch: Schedule, exc: CPMError) -> str:
    """A readable notice when the network itself cannot be scheduled (e.g. a logic cycle).

    The schedule still loaded; only the CPM-derived analysis is unavailable. We name the
    reason (no schedule contents — CUI) instead of returning a server error.
    """
    return (
        f"<div class=panel><h2>{_e(sch.name)} &mdash; cannot compute the network</h2>"
        f'<div class="notice err">This schedule loaded, but its critical-path network '
        f"could not be solved: {_e(exc)}</div>"
        "<p class=muted>The most common cause is a circular dependency (a logic loop) in the "
        "predecessor/successor links. Open the file in Microsoft Project and resolve the loop, "
        "then re-import. The activity list is still available from the dashboard.</p></div>"
    )


def _target_panel(sch: Schedule, analysis: _Analysis, target: int) -> str:
    """The session target activity's metrics in THIS schedule (or a gentle absence note)."""
    row = next((r for r in analysis.activity_rows if r["unique_id"] == target), None)
    if row is None:
        return (
            f"<div class=panel><h2>Target activity UID {target}</h2>"
            f'<p class="notice err">This schedule does not contain UniqueID {target}.</p></div>'
        )
    variance = ""
    if row["finish"] and row["baseline_finish"]:
        days = (
            dt.date.fromisoformat(str(row["finish"]))
            - dt.date.fromisoformat(str(row["baseline_finish"]))
        ).days
        cls = "fail" if days > 0 else "pass"
        variance = (
            f"<tr><th scope=col>Finish vs baseline</th>"
            f"<td><b class={cls}>{days:+d} calendar days</b></td></tr>"
        )
    flags = ", ".join(
        label
        for label, on in (
            ("critical", row["is_critical"]),
            ("milestone", row["is_milestone"]),
            ("summary", row["is_summary"]),
        )
        if on
    )
    cells = "".join(
        f"<tr><th scope=col>{label}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Start", row["start"] or "—"),
            ("Finish", row["finish"] or "—"),
            ("Baseline finish", row["baseline_finish"] or "—"),
            (
                "Total float (days)",
                row["total_float_days"] if row["total_float_days"] is not None else "—",
            ),
            (
                "Free float (days)",
                row["free_float_days"] if row["free_float_days"] is not None else "—",
            ),
            ("% complete", row["percent_complete"]),
            ("Flags", flags or "—"),
        )
    )
    return f"""
<div class=panel><h2>Target activity &mdash; UID {target}: {_e(row["name"])}</h2>
<p class=muted>The session-wide target: the trace below runs to it automatically, the Trend page
focuses on it, and Compare shows its movement. Set or clear it in the header.</p>
<table>{cells}{variance}</table>
<p class=cite>{_e(row["name"])} (UID {target}, {_e(row["source_file"] or "schedule")})</p></div>"""


def _float_bands_panel(analysis: _Analysis) -> str:
    """The deck-style low-float bands (M15/ADR-0030): to-go work running out of room."""
    fb = analysis.float_bands

    def cell(mid: str) -> str:
        r = fb[mid]
        return f"<td>{r.count} <span class=muted>({r.value:g}%)</span></td>"

    pop = fb["float_total_0"].population
    return f"""
<div class=panel><h2>Float analysis &mdash; low-float bands</h2>
<p class=muted>Of the {pop} incomplete activities, how many are running out of room: at 0 days
of float (critical or negative), under 5, and under 10 working days &mdash; cumulative bands on
this schedule's calendar. A swelling low-float band is the early warning that the schedule is
losing its ability to absorb slips.</p>
<table><tr><th scope=col></th><th scope=col>0 days</th><th scope=col>&lt; 5 days</th><th scope=col>&lt; 10 days</th></tr>
<tr><th scope=col class=metric-th>{_metric_help_cell("Total float", "total_float")}</th>{cell("float_total_0")}{cell("float_total_lt5")}{cell("float_total_lt10")}</tr>
<tr><th scope=col class=metric-th>{_metric_help_cell("Free float", "free_float")}</th>{cell("float_free_0")}{cell("float_free_lt5")}{cell("float_free_lt10")}</tr>
</table></div>"""


def _completion_panel(analysis: _Analysis) -> str:
    """The deck-style completion-performance read-out (M15/ADR-0030)."""
    cp = analysis.completion

    def fmt(mid: str) -> str:
        r = cp[mid]
        if r.unit == "%":
            return f"{r.count} of {r.population} ({r.value:g}%)" if r.population else "—"
        if r.unit == "days":
            return f"{r.value:g} days (over {r.count})" if r.count else "—"
        return f"{r.value:g}" if r.population else "—"

    rows = "".join(
        f"<tr><th scope=col class=metric-th>{_metric_help_cell(label, mid)}</th>"
        f"<td>{fmt(mid)}</td></tr>"
        for mid, label in (
            ("completed_ahead", "Completed ahead of baseline"),
            ("completed_on_schedule", "Completed on schedule"),
            ("completed_behind", "Completed behind baseline"),
            ("avg_days_ahead", "Average days ahead (early finishers)"),
            ("avg_days_late", "Average days late (late finishers)"),
            ("avg_completion_variance", "Average completion variance (+ = late)"),
            ("longer_than_planned", "Activities longer than planned"),
            ("shorter_than_planned", "Activities shorter than baseline"),
            ("duration_ratio_min", "Duration ratio (actual / baseline) — min"),
            ("duration_ratio_avg", "Duration ratio — average"),
            ("duration_ratio_max", "Duration ratio — max"),
            ("mei", "MEI (milestones finished / milestones due)"),
            ("epi", "EPI (execution events recorded / events expected)"),
            ("start_finish_ratio", "Start-to-Finish Ratio (scheduled pairs / actual pairs)"),
            ("elapsed_since_last_finish", "Schedule elapsed since latest actual finish"),
        )
    )
    return f"""
<div class=panel><h2>Completion performance</h2>
<p class=muted>How the completed work actually performed against its baseline: the
ahead / on-schedule / behind split, the days gained and lost, and actual-vs-baseline
durations. Day variances are calendar days.</p>
<table>{rows}</table></div>"""


def _what_drives_header(sch: Schedule, analysis: _Analysis) -> str:
    """Chapter 03 "What drives the date" (ADR-0199): the data-driven takeaway + a drivers KPI strip
    + the Critical-exposure and Path-composition bars, for the latest version. The critical path
    (``cpm.critical_path``) is already scoped to any global Analysis Target, so this respects it
    automatically. Every figure is read from what the report already computed (no engine math)."""
    cpm = analysis.cpm
    chain = cpm.critical_path  # unique_ids with total_float <= 0, topo order
    n = len(chain)
    total = sum(1 for _ in non_summary(sch)) or 1

    path_float_min = min((cpm.timings[u].total_float for u in chain if u in cpm.timings), default=0)
    path_float_days = path_float_min / 480.0
    longest_uid: int | None = None
    longest_min = -1
    for u in chain:
        t = sch.tasks_by_id.get(u)
        if t is not None and t.duration_minutes > longest_min:
            longest_min, longest_uid = t.duration_minutes, u
    longest_days = longest_min / 480.0 if longest_min >= 0 else 0.0
    longest_name = sch.tasks_by_id[longest_uid].name if longest_uid is not None else "—"
    cpm_finish = _mdY(offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar))

    if path_float_days < 0:
        float_phrase = f"{abs(path_float_days):g} days of negative float (already behind)"
    elif path_float_days == 0:
        float_phrase = "0 days of total float"
    else:
        float_phrase = f"{path_float_days:g} days of total float"
    acts = "activity" if n == 1 else "activities"
    if n:
        takeaway = (
            f"The finish rides on a critical path of {n} {acts} carrying {float_phrase} — "
            f"its longest single activity is {_e(longest_name)} at {longest_days:g} working days."
        )
    else:
        takeaway = "No critical path resolves for this version."

    floats: list[float] = []
    for r in analysis.activity_rows:
        tf = r.get("total_float_days")
        pc = r.get("percent_complete")
        if isinstance(tf, int | float) and isinstance(pc, int | float) and pc < 100.0:
            floats.append(float(tf))
    b0 = sum(1 for f in floats if f <= 0)
    b1 = sum(1 for f in floats if 0 < f <= 4)
    b2 = sum(1 for f in floats if 4 < f <= 9)
    b3 = sum(1 for f in floats if f > 9)

    kpi = _stat_cards(
        [
            ("Critical-path activities", str(n)),
            ("Path total float", f"{path_float_days:g} d"),
            ("Longest driver", f"{longest_days:g} d"),
            ("On the critical path", f"{100.0 * n / total:.0f}%"),
            ("Computed finish", cpm_finish),
            ("Near-critical (≤ 4d)", str(b0 + b1)),
        ]
    )
    exposure = _status_stack(
        "Critical exposure",
        "Incomplete activities by total-float band — how many sit at or near the edge.",
        [
            ("0 days", b0, "--bad"),
            ("1-4 days", b1, "--warn"),
            ("5-9 days", b2, "--accent"),
            ("10+ days", b3, "--muted"),
        ],
        f"{len(floats)} incomplete activities",
    )
    composition = _status_stack(
        "Path composition",
        "Activities that drive the finish (critical path) vs those carrying slack.",
        [("Critical path", n, "--bad"), ("Has slack", max(total - n, 0), "--ok")],
        f"{total} activities",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{exposure}{composition}</div>'
    )


def _path_body(keys: list[str], target_uid: int | None) -> str:
    """The SSI-style path-analysis workspace: controls, data grid left, scalable Gantt right.

    All interaction is client-side (`static/path.js`) over `/api/driving` — field
    add/remove, filters (incl. hide-completed), tier day-bands, zoom, the data-date
    line. The grounded ask-the-AI panel is the page-shell one (`_ask_panel_html`)."""
    # default the grid to the LATEST version (keys[-1]) — the same version the "What drives the
    # date" header above is anchored on (ADR-0199). Without this the browser defaults to the first
    # <option> (the OLDEST version), so the header described one file while the grid traced another
    # — the operator's "critical path is mixing up information from the various files" report.
    latest = keys[-1] if keys else None
    options = "".join(
        f'<option value="{_e(k)}"{" selected" if k == latest else ""}>{_e(k)}</option>'
        for k in keys
    )
    return f"""
<div class=panel><h2>Path analysis &mdash; driving / secondary / tertiary to a target</h2>
<p class=muted>Pick a schedule and a target UniqueID: the driving path (slack &le; 0) and the
secondary/tertiary tiers within your day-bands trace back from it — data on the
left, a scalable timeline on the right with the gold data-date line. Add/remove columns,
filter rows, and hide completed work. <b>Click a row</b> to highlight that task's fields and its
bar; click another task to move the highlight, or click off to clear it. <b>Double-click</b> a row
for the full Task Information.</p>
{_user_tip("Pick a tier such as <b>DRIVING</b> to fit the timeline to just that path so its bars fill the page; the data columns stay locked on the left as the timeline scrolls, and <b>View entire project</b> zooms back out to the whole trace.")}
<details class=path-explainer><summary>Why an activity can show 0&#8209;day driving slack here but not on another view</summary>
<p class=muted>This trace is <b>relative to the target UniqueID</b> you choose. An activity has
<b>0 days of driving slack</b> when a slip in it would push <i>this target's</i> finish, so it sits
on the driving path <b>to that target</b>. The same activity may legitimately not appear on a view
scoped to a <b>different</b> target, on the project&#8209;finish critical path (the DCMA
&ldquo;Critical Path Test&rdquo;), or when completed work is hidden &mdash; driving slack to a
target and the project's critical path answer different questions. Turn on the <b>Drives &#8594;</b>
column to see each activity's logic successors inside this trace (e.g. UID 8022 &#8594; UID 152);
a <b>*</b> marks the successor that keeps the chain on the driving path.</p></details>
<div class="viz-controls sf-freeze-bar" id=pathControls>
<label>Schedule <select id=pathSchedule>{options}</select></label>
<label>Target UID <input id=pathTarget type=number min=1 value="{target_uid if target_uid is not None else ""}" placeholder="UID"></label>
<label>Secondary &le; <input id=pathSec type=number min=1 value=10 title="days of driving slack"> d</label>
<label>Tertiary &le; <input id=pathTer type=number min=1 value=20 title="days of driving slack"> d</label>
<button id=pathRun type=button>Trace</button>
<button id=pathDrag type=button title="SSI-validated Devaux DRAG: how many working days each driving-path activity personally adds — capped by its remaining duration and by parallel branches">Run Drag Analysis</button>
<label><input id=pathHideDone type=checkbox> hide 100% complete</label>
<label>Tier <span id=pathTier class=tier-filter></span></label>
<label>Filter <input id=pathFilter type=text placeholder="name / UID contains"></label>
<label>Find <input id=pathFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every traced task whose row contains this text"></label>
<span id=pathFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=pathBarDates type=checkbox> dates on bars</label>
<label>Zoom <input id=pathZoom type=range min=2 max=40 value=8 title="pixels per day"></label>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<button id=pathFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
</div>
<details class=path-options open><summary>Path options (SSI Directional Path Tool)</summary>
<div class=viz-controls id=pathOptions>
<span class=opt-group><b>Path Direction</b>
<label><input type=radio name=pathDir value=predecessors checked> &#8592; Predecessors</label>
<label><input type=radio name=pathDir value=successors> &#8594; Successors</label>
<label><input type=radio name=pathDir value=both> &#8596; Both</label></span>
<span class=opt-group><b>Dependency Range</b>
<label><input type=radio name=pathRange value=slack> Driving Slack &le;
<input id=pathRangeDays type=number min=0 value=0 style="width:52px"> d</label>
<label><input type=radio name=pathRange value=all checked> Get all dependencies</label></span>
<span class=opt-group>
<label><input id=pathIgnoreConstraints type=checkbox title="SSI-parity option: strips constraint pins out of the CPM fallback that dates otherwise-undated tasks. Tasks with stored dates keep them — on a fully-dated file the trace is unchanged, matching SSI's own output with this option on (ADR-0251)"> Ignore constraints</label>
<label><input id=pathIgnoreLeveling type=checkbox title="SSI-parity option: measures link gaps on the project-calendar date basis (stored dates first; CPM only for undated tasks). Stored leveled dates still govern — on a fully-dated file the trace is unchanged, matching SSI's own output with this option on (ADR-0251)"> Ignore leveling delay</label></span>
<span class=opt-group><b>Output</b>
<label><input type=radio name=pathOutput value=waterfall checked> &#8615; Waterfall</label>
<label><input type=radio name=pathOutput value=summaries> With Summaries</label>
<label><input type=radio name=pathOutput value=parallel> Separate parallel paths</label></span>
<span class=opt-group><b>Group by</b>
<select id=pathGroupBy title="Group the traced activities by any field — standard or custom (e.g. a CA-WBS code); overrides the Output grouping"><option value="">(none)</option></select></span>
<span class=opt-group><label><input id=pathShowLinks type=checkbox title="Draw the logic links between traced activities on the timeline (MS-Project Layout style)"> Show links</label></span>
</div></details>
<div id=pathFields class=muted></div>
<div class="export-bar" id=pathExport style="display:none"><a id=pathXlsx href="#">&#11015; Excel</a><a id=pathDocx href="#">&#11015; Word</a></div>
<div id=pathStatus class=muted></div>
<div id=pathView class=path-view></div></div>
<script src="/static/path.js"></script>"""


def _portfolio_memory_panel(st: SessionState) -> str:
    """A compact resident-memory readout + the operator's warn-threshold control (v4 Feature 2).

    Estimate only, and a warning only — the tool never blocks a load. Lets an operator loading a
    folder of thousands see roughly how much RAM the loaded schedules occupy and tune when the tool
    should flag it."""
    est = estimate_resident_bytes(st.schedules.values())
    warn = st.ram_warn_bytes
    over = est > warn
    cls = "notice warn" if over else "muted"
    warn_gb = warn / 1024**3
    tail = " — over your threshold; you can keep working" if over else ""
    return (
        f'<div class=panel><h3>Memory</h3><p class="{cls}">'
        f"{len(st.schedules)} schedule(s) loaded &middot; estimated resident memory "
        f"<b>{format_bytes(est)}</b> (warn at {format_bytes(warn)}){tail}.</p>"
        "<form method=post action=/session/ram-threshold class=inline-form>"
        "<label>Warn above <input type=number name=gb min=1 step=1 "
        f'value="{warn_gb:g}" style="width:6em"> GB</label> '
        "<button type=submit>Update</button></form>"
        "<p class=muted>Schedules stay in memory for instant comparative analysis. This is an "
        "estimate; on a large workstation even a big portfolio fits.</p></div>"
    )


def _portfolio_body(st: SessionState) -> str:
    """The Portfolio Manager rollup: one row per Project (grouped from the loaded files/folders),
    each showing its latest-version headline — computed finish, effective schedule margin, DCMA-14
    pass/fail — plus an expandable version history (each version links to its full report). Every
    number traces to the engine's cached per-version summary (v4 Feature 2 lazy tier); a Project
    whose latest version won't solve shows "—". No new engine math (reuses ``compute_summary``)."""
    intro = (
        "<div class=panel><h2>Portfolio</h2>"
        "<p class=muted>Every project loaded in this session, grouped from your files and folders. "
        "Each row is one Project; the headline is its latest version by data date. Expand a row for "
        "the version history, or open any version's full report.</p>"
        "<table><tr>"
        "<th scope=col>Project</th><th scope=col>Versions</th>"
        "<th scope=col>Latest data date</th><th scope=col>Computed finish</th>"
        "<th scope=col>Effective margin</th><th scope=col>DCMA-14</th></tr>"
    )
    em = "—"  # the literal U+2014 sentinel (ADR-0219 M2: never the &mdash; entity)
    rows: list[str] = []
    for p in st.projects():
        latest = p.versions[-1]  # versions are oldest-first, so the last is the current version
        sch = st.schedules.get(latest.key)
        data_date = finish = margin = dcma = em
        if sch is not None:
            # the lazy summary tier (v4 Feature 2): finish/margin/DCMA without a fresh CPM per row —
            # cached in-memory and, for uploads, on disk. Equals the fully-computed row (never a
            # different number); an unsolvable version leaves the headline as "—", never a 500.
            summary = st.summary_for(latest.key, sch)
            if summary.status_date_iso is not None:
                data_date = _mdY(summary.status_date_iso)
            if not summary.unsolvable:
                finish = _mdY(summary.finish_iso)
                if summary.effective_margin_days is not None:
                    margin = f"{summary.effective_margin_days:g} d"
                cls = "rib-pass" if summary.dcma_fail == 0 else "rib-fail"
                dcma = (
                    f'<span class="{cls}">{summary.dcma_pass} pass / '
                    f"{summary.dcma_fail} fail</span>"
                )
        attn = " <span class=muted>(needs attention)</span>" if p.needs_attention else ""
        versions_html = "".join(
            '<li><a class=btn-link href="/analysis/{k}">{f}</a>{dd}</li>'.format(
                k=quote(v.key),
                f=_e(v.filename),
                dd=(
                    f" <span class=muted>&middot; data date {_mdY(vs.status_date)}</span>"
                    if (vs := st.schedules.get(v.key)) is not None and vs.status_date is not None
                    else ""
                ),
            )
            for v in p.versions
        )
        notices = "".join(f'<div class="notice info">{_e(n)}</div>' for n in p.notices)
        rows.append(
            f"<tr><td><details><summary><b>{_e(p.title)}</b>{attn}</summary>"
            f"<ul>{versions_html}</ul>{notices}</details></td>"
            f"<td>{len(p.versions)}</td><td>{data_date}</td><td>{finish}</td>"
            f"<td>{margin}</td><td>{dcma}</td></tr>"
        )
    return intro + "".join(rows) + "</table></div>" + _portfolio_memory_panel(st)


def _mission_body(target_uid: int | None) -> str:
    """Mission Control — every visual on one wall at small scale: expand any tile (⤢), reveal its
    underlying data table (▦ Data), and Play-all to step every animated chart in lockstep. Each
    tile hosts the SAME chart scripts/endpoints the dedicated pages use, so the session-wide
    Target UID and Groups & Filters scope every tile automatically."""
    target = target_uid if target_uid is not None else ""

    def tile(
        title: str,
        full_url: str,
        inner: str,
        *,
        controls: str = "",
        wide: bool = False,
        hint: str = "",
    ) -> str:
        cls = "tile panel" + (" tile-wide" if wide else "")
        # operator 2026-07-08: every visual explains itself on hover over its NAME — what it
        # shows, an example, how to read it, and what to decide from it (sf-hint-wide callout)
        hint_attr = f' class=viz-hint data-sf-hint="{_e(hint)}"' if hint else ""
        return f"""<section class="{cls}">
<div class=tile-head><h3{hint_attr}>{title}</h3>
<span class=tile-actions>\
<button type=button class=tile-expand aria-pressed=false title="Enlarge / shrink this tile">\
&#11122; Enlarge</button>\
<button type=button class=tile-data aria-pressed=false>&#9638; Data</button>
<a href="{full_url}" class=btn-link>Open &#8599;</a></span></div>
{controls}
<div class=chart-host>{inner}</div></section>"""

    def steps(prev: str, play: str, nxt: str) -> str:
        return (
            f"<div class=mini-steps><button type=button id={prev}>&#8249;</button>"
            f"<button type=button id={play}>&#9654;</button>"
            f"<button type=button id={nxt}>&#8250;</button></div>"
        )

    perf_tiles = "".join(
        [
            tile(
                "S-Curve",
                "/scurve",
                "<div id=scurveLabel class=muted></div><div id=scurveChart></div>",
                hint="WHAT: cumulative % of activities finished over time — the planned curve (baseline dates) vs the actual/current curve.\n\nEXAMPLE: plan says 38% done by the data date but the actual curve reads 22% — the project is running ~16 points behind plan.\n\nHOW TO READ: actual below planned = behind; the horizontal gap between the curves at today's height = roughly how far behind in time; a flattening actual curve = throughput stalling.\n\nDECIDE: whether claimed % complete matches reality, and whether the remaining rate must accelerate to hit the finish.",
                controls=steps("prevScurve", "scurvePlay", "nextScurve"),
            ),
            tile(
                "Bow Wave / CEI",
                "/cei",
                "<div id=snapLabel class=muted></div><div id=ceiChart></div>",
                hint="WHAT: where unfinished work piles up relative to each version's data date, stepped snapshot by snapshot, with the Current Execution Index (how much of the planned window's work was actually executed).\n\nEXAMPLE: each new version shows a taller hump of tasks packed just after the data date — work is being pushed ahead in a 'bow wave' instead of being finished.\n\nHOW TO READ: a stable, spread-out profile is healthy; a growing near-term hump that rolls forward version after version means replanning is deferring, not solving; CEI well below 1.0 means the team executes far less than each plan promises.\n\nDECIDE: whether the schedule is managed by slipping work windows (a classic health/manipulation red flag) and whether near-term commitments are credible.",
                controls=steps("prevSnap", "autoPlay", "nextSnap"),
            ),
            tile(
                "Forecast Drift",
                "/forecast",
                "<div id=driftLabel class=muted></div><div id=driftChart></div>",
                hint="WHAT: the forecast finish date from three independent methods (CPM network logic, historical throughput rate, earned schedule), tracked across every loaded version.\n\nEXAMPLE: over five updates the logic forecast holds March while the rate and earned-schedule forecasts drift to August — the network promises what the demonstrated pace can't deliver.\n\nHOW TO READ: lines drifting right = slipping; methods that AGREE make the forecast credible; a logic forecast far ahead of the performance-based ones usually means optimistic remaining durations or loosened logic.\n\nDECIDE: which finish date to plan around, and whether to challenge an optimistic official forecast.",
                controls=steps("prevDrift", "driftPlay", "nextDrift"),
            ),
            tile(
                "Finishes",
                "/curves",
                "<div id=finishesChart></div>",
                hint="WHAT: the distribution of activity FINISH dates — baseline vs current — as overlaid curves.\n\nEXAMPLE: the current curve's bulk sits two quarters right of the baseline curve — most finishes have moved later, not just a few outliers.\n\nHOW TO READ: a rightward shift of the whole curve = broad slip; a matching shape but offset = uniform delay; a stretched tail = a few activities carrying extreme slips.\n\nDECIDE: whether delay is systemic (replan) or concentrated (recover the few outliers).",
            ),
            tile(
                "Data-date Finishes",
                "/curves",
                "<div id=dataDateChart></div>",
                hint="WHAT: finish dates relative to each version's own data date — how much work each update claims it will finish, and how soon.\n\nEXAMPLE: every version promises a surge of finishes in the 60 days after its data date, and every next version shows the surge didn't happen.\n\nHOW TO READ: compare the promised near-term finishes against what the next snapshot actually closed; repeated over-promising shows up as the same near-term bulge rolling forward.\n\nDECIDE: how much of the near-term plan to believe, and whether commitments need de-risking.",
            ),
            tile(
                "Slippage",
                "/curves",
                "<div id=slippageChart></div>",
                hint="WHAT: how far activity finishes have slipped against baseline (working days, positive = late), across the loaded versions.\n\nEXAMPLE: median slip grows +10 wd per update for three updates straight — the schedule is losing ground at a steady, predictable rate.\n\nHOW TO READ: a rising slip trend that never recovers is erosion; sudden drops without matching scope/logic changes can mean the baseline was quietly moved.\n\nDECIDE: the realistic slip rate to project forward, and whether baseline integrity needs a forensic look.",
            ),
            tile(
                "Critical-Path Evolution",
                "/evolution",
                f'<div id=evoLabel class=muted></div><div id=evoChart data-target="{target}"></div>',
                hint="WHAT: the driving path to the project finish (or your Target UID), version by version — which activities carry the schedule and how membership changes.\n\nEXAMPLE: the path ran through fabrication for four versions, then suddenly runs through software integration — either real progress or a logic change moved the drive.\n\nHOW TO READ: stable membership = a settled plan; churn every version = an unstable network; watch for activities that leave the path exactly when they start slipping (a manipulation signature).\n\nDECIDE: where management attention belongs now, and which path changes deserve a 'why did this change?' interrogation.",
                controls=steps("prevEvo", "evoPlay", "nextEvo"),
            ),
            # operator 2026-07-09: the Quality visuals sit NEXT TO Critical-Path Evolution in the
            # same grid (the separate Quality Control section left a mostly-empty row of dead
            # space). The Quality Trend tile is a HOST: on the wall, trend.js lifts each of its
            # charts into its OWN tile (one graph per visual) right after this position.
            tile(
                "Quality Offenders",
                "/trend",
                "<div id=qualLabel class=muted></div>"
                "<div class=qual-drill-grid><div id=qualBars></div><div id=qualDrill></div></div>"
                "<label class=muted>Metric <select id=qualMetric></select></label>",
                hint="WHAT: for the selected quality metric (missing logic, hard constraints, high float…), which specific activities offend, ranked, with a drill-down — across versions.\n\nEXAMPLE: 'Hard constraints' shows 12 offenders and the drill list is dominated by one subproject — that team is pinning dates instead of using logic.\n\nHOW TO READ: click a bar to list the offending activities (UIDs); recurring offenders across versions are structural, not accidental.\n\nDECIDE: exactly which activities to send back to the planner, and where quality problems concentrate.",
                controls=steps("qualPrev", "qualPlay", "qualNext"),
            ),
            tile(
                "Quality Trend",
                "/trend",
                f'<div id=trendCharts data-target="{target}"></div>',
                hint="WHAT: the DCMA-14 / schedule-quality metric scores tracked across every loaded version — on this wall each metric renders as its own tile below.\n\nEXAMPLE: missing-logic count falls from 40 to 5 in one update with no matching activity changes — links were bulk-added to pass the audit; verify they are real logic.\n\nHOW TO READ: gradual improvement is normal cleanup; step changes right before reviews are audit-chasing; deteriorating trends flag eroding schedule discipline.\n\nDECIDE: whether schedule quality is genuinely improving and which metric family to audit in depth.",
            ),
        ]
    )
    return f"""
<div class=panel><h2>Mission Control &mdash; every visual on one wall</h2>
<p class=muted>Every visual on one wall, each the same size. <b>&#11122; Enlarge</b> any tile to the
full width (and back), reveal the underlying numbers with <b>&#9638; Data</b>, and use
<b>Play all</b> to step every animated chart &mdash; S-Curve, Bow Wave, Forecast Drift, Quality
Offenders, and Critical-Path Evolution &mdash; in lockstep. The session <b>Target UID</b> and
<b>Groups &amp; Filters</b> apply to every tile.</p>
<div class=viz-controls>
<button id=missionPlay type=button>&#9654; Play all</button>
<button id=missionStep type=button>&#9197; Step all</button>
</div></div>
<div id=missionGrid class=mosaic>
{perf_tiles}
</div>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>
<script src="/static/cei.js"></script>
<script src="/static/drift.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/curves.js"></script>
<script src="/static/trend.js"></script>
<script src="/static/path_evolution.js"></script>
<script src="/static/mission.js"></script>"""


def _carnac_cards(summary: CarnacSummary) -> str:
    """The deck's Carnac KPI card row (PBIX page 13) over the latest version."""

    def d(value: dt.date | None) -> str:
        return _mdY(value)

    def n(value: float | None, *, suffix: str = "") -> str:
        return f"{value:g}{suffix}" if value is not None else "—"

    return _stat_cards(
        [
            ("Earliest start", d(summary.earliest_start)),
            ("Latest finish (CPM)", d(summary.latest_finish)),
            ("Project duration (wd)", n(summary.project_duration_days)),
            ("Forecasted end (rate)", d(summary.forecasted_end)),
            ("Estimated end (ES, to-go)", d(summary.estimated_end_es)),
            ("Avg tasks / month", n(summary.avg_tasks_per_month)),
            ("Remaining duration (wd)", n(summary.remaining_duration_days)),
            ("SPI(t)", n(summary.spi_t)),
            ("Earned schedule (wd)", n(summary.earned_schedule_days)),
            ("Tasks to complete", str(summary.to_go_count)),
        ]
    )


#: lane color per forecast method (matches static/drift.js so the ruler and the animation
#: read consistently): logic = accent, throughput = ok, performance = bad.
_FORECAST_METHOD_COLORS = {
    "cpm": "var(--accent)",
    "rate": "var(--ok)",
    "earned_schedule": "var(--bad)",
}


def _forecast_ruler(fc: ForecastSet) -> str:
    """A static single-version SVG 'ruler' (M18 item 8): the data date, the baseline finish,
    and each method's forecast on one timeline so the spread between them is visible at a
    glance. Inline SVG (no JS, no external fetch); the multi-version movement is the animated
    drift stepper below. Methods with missing inputs render '— (inputs missing)'."""
    lanes = [(f.name, f.method_id, f.finish) for f in fc.forecasts]
    method_dates = [d for _, _, d in lanes if d is not None]
    axis_dates = list(method_dates)
    if fc.as_of is not None:
        axis_dates.append(fc.as_of)
    if fc.planned_finish is not None:
        axis_dates.append(fc.planned_finish)
    if not axis_dates:
        return ""
    lo, hi = min(axis_dates), max(axis_dates)
    if lo == hi:
        lo, hi = lo - dt.timedelta(days=15), hi + dt.timedelta(days=15)
    span = (hi - lo).days or 1

    w, pad_l, pad_r, pad_t, row_h = 940, 150, 130, 46, 40
    height = pad_t + row_h * len(lanes) + 24
    plot_w = w - pad_l - pad_r
    bottom = pad_t + row_h * len(lanes)

    def x(d: dt.date) -> float:
        return pad_l + ((d - lo).days / span) * plot_w

    parts = [
        f'<svg viewBox="0 0 {w} {height}" width="100%" role="img" '
        f'aria-label="Forecast finish dates on a shared timeline">'
    ]
    if fc.as_of is not None:
        ax = x(fc.as_of)
        parts.append(
            f'<line x1="{ax:.1f}" y1="{pad_t - 12}" x2="{ax:.1f}" y2="{bottom}" '
            'style="stroke:var(--muted)" stroke-width="1.5" stroke-dasharray="2 3"/>'
            f'<text x="{ax:.1f}" y="{pad_t - 16}" text-anchor="middle" '
            f'style="fill:var(--muted)" font-size="11">data date {_mdY(fc.as_of)}</text>'
        )
    if fc.planned_finish is not None:
        px = x(fc.planned_finish)
        parts.append(
            f'<line x1="{px:.1f}" y1="{pad_t - 12}" x2="{px:.1f}" y2="{bottom}" '
            'style="stroke:var(--warn)" stroke-width="2" stroke-dasharray="5 4"/>'
            f'<text x="{px:.1f}" y="{pad_t - 30}" text-anchor="middle" '
            f'style="fill:var(--warn)" font-size="11">baseline {_mdY(fc.planned_finish)}</text>'
        )
    for i, (name, mid, d) in enumerate(lanes):
        cy = pad_t + row_h * i + row_h / 2
        color = _FORECAST_METHOD_COLORS.get(mid, "var(--ink)")
        parts.append(
            f'<line x1="{pad_l}" y1="{cy:.1f}" x2="{w - pad_r}" y2="{cy:.1f}" '
            'style="stroke:var(--line)" stroke-width="1"/>'
            f'<text x="{pad_l - 10}" y="{cy + 4:.1f}" text-anchor="end" '
            f'style="fill:var(--muted)" font-size="12">{_e(name)}</text>'
        )
        if d is not None:
            cx = x(d)
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" style="fill:{color}"/>'
                f'<text x="{cx:.1f}" y="{cy - 11:.1f}" text-anchor="middle" '
                f'style="fill:var(--ink)" font-size="11">{_mdY(d)}</text>'
            )
        else:
            parts.append(
                f'<text x="{pad_l + 10}" y="{cy + 4:.1f}" '
                'style="fill:var(--muted)" font-size="11">&#8212; (inputs missing)</text>'
            )
    parts.append("</svg>")
    legend_items = "".join(
        f"<span class=chart-legend-item><span class=chart-swatch "
        f'style="background:{_FORECAST_METHOD_COLORS.get(mid, "var(--ink)")}"></span>'
        f"{_e(name)}</span>"
        for name, mid, _ in lanes
    )
    legend_items += (
        '<span class=chart-legend-item style="color:var(--muted)">'
        "&mdash; gold dashed = baseline finish &middot; grey dotted = data date</span>"
    )
    legend = f"<div class=chart-legend>{legend_items}</div>"
    spread = ""
    if len(method_dates) >= 2:
        lo_m, hi_m = min(method_dates), max(method_dates)
        spread = (
            f"<p class=muted>The methods span <b>{(hi_m - lo_m).days} days</b> "
            f"({_mdY(lo_m)} &rarr; {_mdY(hi_m)}). A wide fan means the plan, the "
            "throughput, and the earned-schedule performance disagree about the finish.</p>"
        )
    return f"<div id=forecastRuler>{''.join(parts)}{legend}</div>{spread}"


def _forecast_explainer(fc: ForecastSet) -> str:
    """Plain-English methodology for the finish forecasts (M18 item 8): one card per
    method (what it measures, the formula in words + symbols, when it is available, and this
    version's value), plus the static ruler. Every value reuses the forecast set — nothing
    is recomputed."""
    by = {f.method_id: f for f in fc.forecasts}

    def fin(mid: str) -> str:
        f = by.get(mid)
        return _mdY(f.finish) if (f is not None and f.finish is not None) else "&#8212;"

    rate_txt = f"{fc.rate_per_month:g} / month" if fc.rate_per_month is not None else "n/a"
    spi_txt = f"{fc.spi_t:g}" if fc.spi_t is not None else "n/a"
    cards = [
        (
            "Schedule logic (CPM)",
            "The date the plan claims",
            "Runs the network's own forward and backward pass over every activity, its links, "
            "durations and calendar, and reports the finish the logic computes. It reflects "
            "what the schedule says &mdash; not how the work has actually been going.",
            "Method: the critical-path method (the longest logic-driven chain to the end).",
            "Always available once the network schedules &mdash; it never reads &#8212;.",
            fin("cpm"),
        ),
        (
            "Completion-rate extrapolation",
            "The throughput answer",
            "Counts the activities that have actually finished, divides by the months elapsed "
            "since the project started to get a completion pace, then asks how long the "
            "remaining activities take at that same pace.",
            "Formula: rate = completed &divide; elapsed&nbsp;months, then "
            "finish = data&nbsp;date + (to-go &divide; rate) months "
            f"(here {fc.completed_count} done at {rate_txt}, {fc.remaining_count} to go).",
            "Needs a status (data) date and at least one completed activity, else &#8212;.",
            fin("rate"),
        ),
        (
            "Earned-schedule IEAC(t)",
            "The performance answer",
            "Earned Schedule (ES) is how much planned <i>time</i> the completed work was worth "
            "on the baseline; AT is the actual time elapsed; their ratio SPI(t) = ES &divide; AT "
            "is the schedule efficiency. The estimate projects the remaining planned duration "
            "at that observed efficiency.",
            f"Formula: IEAC(t) = AT + (PD &minus; ES) &divide; SPI(t) (here SPI(t) = {spi_txt}).",
            "Needs baselines, completed work, and SPI(t) &gt; 0, else &#8212;.",
            fin("earned_schedule"),
        ),
    ]
    card_html = "".join(
        f"<div class=forecast-method><h3>{_e(title)}</h3>"
        f"<p class=method-tag>{_e(tag)}</p>"
        f"<p>{what}</p><p class=muted>{how}</p>"
        f"<p class=muted><b>Availability:</b> {needs}</p>"
        f"<p class=method-finish>This version: <b>{value}</b></p></div>"
        for title, tag, what, how, needs, value in cards
    )
    return f"""
<div class=panel><h2>How the forecasts are computed</h2>
<p class=muted>Each method answers "when will it really end?" from a different angle &mdash;
the plan's own logic, the observed throughput, and the earned-schedule performance. When they
agree you can trust the date; when they fan apart, the disagreement is itself a finding. Every
figure here reuses the forecast above &mdash; nothing is recomputed.</p>
<div class=card-cols>{card_html}</div>
<h3>Forecast spread &mdash; latest version</h3>
<p class=muted>The data date, the baseline finish, and each method's forecast on one
timeline. The multi-version movement is animated in the stepper below when two or more
versions are loaded.</p>
{_forecast_ruler(fc)}</div>"""


def _field_forecast_panel(
    schedules: list[Schedule], group_field: str, action: str = "/forecast"
) -> str:
    """Per-field group execution metrics on /forecast (operator 2026-07-09, ADR-0179): pick
    any standard or custom field (e.g. a CAM code) and every version's tasks are grouped by
    its values (plus NA for unassigned), each group scored with the SAME engine functions the
    schedule-wide figures use — BEI / HMI / CEI / both SPI(t)s — plus the start-basis leading
    index for groups that have not completed work yet."""
    fields = available_fields_union(schedules)
    if group_field and group_field not in fields:
        group_field = ""
    opts = '<option value="">— pick a field —</option>' + "".join(
        f'<option value="{_e(f)}"{" selected" if f == group_field else ""}>{_e(f)}</option>'
        for f in fields
    )
    form = f"""
<div class=panel><h2>Execution metrics by field group</h2>
<p class=muted>Group every loaded version's activities by any <b>standard or custom field</b>
(for example a CAM code) and score each group with the same engine metrics the schedule-wide
figures use — <b>BEI</b>, <b>HMI</b>, <b>CEI (Finish / Start)</b>, and both <b>SPI(t)</b>
methods — computed over <b>only that group's tasks</b>. Activities carrying no value for the
field are grouped as <b>NA</b>.</p>
<form method=get action={action} class=viz-controls>
<label>Group by <select name=group_field data-no-i18n>{opts}</select></label>
<button type=submit>Compute</button>
{f'<a class=btn-link href="/export/xlsx/field-forecast?field={_e(group_field)}">&#11015; Excel</a>' if group_field else ""}
</form>"""
    if not group_field:
        return form + "</div>"
    rows_data = compute_field_forecast(schedules, group_field)

    def cell(v: float | None, *, na_hint: str = "") -> str:
        if v is None:
            return (
                f'<td class=muted title="{_e(na_hint)}">N/A</td>'
                if na_hint
                else ("<td class=muted>N/A</td>")
            )
        cls = "fail" if v < 0.95 else "pass"
        return f'<td class="num {cls}">{v:g}</td>'

    body_rows = ""
    last_group = None
    for g in rows_data:
        group_cell = (
            f"<th scope=row rowspan=1 data-no-i18n>{_e(g.group)}</th>"
            if g.group != last_group
            else "<th scope=row></th>"
        )
        last_group = g.group
        note = ""
        if g.activities and g.no_completed_work:
            note = (
                '<span class=exc-note title="No completed work in this group yet — the '
                "finish-anchored indices are undefined (never imputed). Read the start "
                'index (SEI) as the leading execution signal.">start-basis</span>'
            )
        sei_hint = (
            "Start execution index — started ÷ baselined-to-start-by-the-data-date: the "
            "leading indicator used when a group has no completions yet"
        )
        body_rows += (
            f"<tr>{group_cell}<td data-no-i18n>{_e(g.version)}</td>"
            f"<td class=num>{g.activities}</td><td class=num>{g.completed}</td>"
            f"<td class=num>{g.started}</td><td class=num>{g.to_go}</td>"
            f"{cell(g.bei)}{cell(g.hmi)}{cell(g.cei_finish)}{cell(g.cei_start)}"
            f"{cell(g.spi_t)}{cell(g.spi_t_acumen)}"
            f"{cell(g.sei, na_hint=sei_hint)}"
            f"<td>{note}</td></tr>"
        )
    analysis = """
<details class=explainer><summary><b>Groups without completed work — how these figures are
derived (best-practice analysis)</b></summary>
<div style="padding:8px 12px">
<p><b>The problem.</b> BEI, HMI, CEI (Finish) and both SPI(t) methods are <i>finish-anchored</i>:
they compare completed work against what was baselined or forecast to complete. A group (a CAM,
a resource, a WBS leg) whose work has not completed anything yet gives these indices no
qualifying data — the denominator or the earned set is empty.</p>
<p><b>What published practice says.</b> The NDIA Planning &amp; Scheduling Excellence Guide's
treatment of BEI-family indices and the DCMA construct are explicit that an index without
qualifying data reads <b>N/A</b> — imputing a 0 (reads as catastrophic failure) or a 1 (reads
as perfect execution) poisons any forecast built on it. The accepted practice is to switch to
<b>leading, start-anchored indicators</b>: work must start before it can finish, so start
execution predicts finish execution one period ahead (Acumen's own library carries the
start-anchored twin as "BEI - Value Task Starts").</p>
<p><b>What this table does.</b> (1) Finish-anchored indices are <b>never fabricated</b> — an
undefined cell reads N/A. (2) Every group additionally carries the <b>start execution index
(SEI)</b> = activities started &divide; activities baselined to start by the data date — defined
as soon as anything is due to start, so a no-completions group still gets a real execution read.
(3) The <b>Started / To-go</b> counts give the group's workoff burden. A group flagged
<b>start-basis</b> with SEI &lt; 0.95 is already executing late even though no finish-based
metric can say so yet — that is the earlier, more accurate forecast signal the grouping is for.
(4) As soon as the group completes its first activity, the finish-anchored indices activate
automatically on the same engine formulas as the schedule-wide figures.</p>
</div></details>"""
    table = f"""
<div class=hist-drill-scroll style="max-height:560px">
<table class=hist-drill-table>
<tr><th scope=col data-no-i18n>{_e(group_field)}</th><th scope=col>Version</th>
<th scope=col>Activities</th><th scope=col>Done</th><th scope=col>Started</th>
<th scope=col>To go</th><th scope=col>BEI</th><th scope=col>HMI</th>
<th scope=col>CEI (F)</th><th scope=col>CEI (S)</th><th scope=col>SPI(t) ES</th>
<th scope=col>SPI(t) Acumen</th><th scope=col>SEI (start)</th><th scope=col></th></tr>
{body_rows}</table></div>"""
    return form + analysis + table + "</div>"


def _group_rollup_panel(latest: Schedule, latest_set: ForecastSet, field: str) -> str:
    """The project forecast RECALCULATED from the group-weighted data points (ADR-0188/0189).

    Rendered under the per-group table when a group field is chosen: the groups' exact
    SPI(t)s weighted by their to-go work re-run IEAC(t) (direct-only AND full-coverage,
    where no-history groups contribute credibility-weighted estimates), and each group's
    throughput extrapolates its own backlog with the LATEST group finish as the project's
    bottleneck answer. Estimates are quantified and labeled (ADR-0189) — never silent."""
    rollup = compute_group_rollup(latest, field)
    if rollup is None:
        return ""
    top = {f.method_id: f.finish for f in latest_set.forecasts}

    def d(v: dt.date | None) -> str:
        return _mdY(v) if v else "—"

    spi_cell = f"{rollup.weighted_spi_t:g}" if rollup.weighted_spi_t is not None else "—"
    spi_all = f"{rollup.weighted_spi_t_all:g}" if rollup.weighted_spi_t_all is not None else "—"
    top_spi = f"{latest_set.spi_t:g}" if latest_set.spi_t is not None else "—"
    coverage = (
        f"{rollup.groups_used} of {rollup.groups_total} groups with to-go work carry a DIRECT "
        f"SPI(t), covering {rollup.covered_to_go} of {rollup.total_to_go} to-go activities; "
        "the full-coverage figure adds the estimated groups below (credibility-weighted)"
    )
    est_block = ""
    if rollup.estimated:
        rows = "".join(
            f"<tr><th scope=row data-no-i18n>{_e(e.group)}</th><td class=num>{e.to_go}</td>"
            f"<td class=num>{e.sei if e.sei is not None else '—'}</td>"
            f"<td class=num>{e.pooled_rate_per_month:g}/mo</td>"
            f"<td class=num>&times;{e.adjustment:g}</td>"
            f"<td><b>{d(e.finish)}</b></td>"
            f"<td class=muted>{d(e.finish_early)} &rarr; {d(e.finish_late)}</td>"
            f'<td class=muted title="{_e(e.basis)}">hover for the full basis</td></tr>'
            for e in rollup.estimated
        )
        est_block = f"""
<h3>Estimated groups &mdash; no completion history yet (credibility-weighted)</h3>
<p class=muted>These groups carry to-go work but have completed nothing, so a finish-anchored
measure has no qualifying data. Instead of flagging them unforecastable, each gets a
<b>quantified estimate</b> built on standard statistical practice: <b>partial pooling /
credibility weighting</b> (B&uuml;hlmann; with zero group observations the credibility weight
on the group's own history is Z&nbsp;=&nbsp;0, so the estimate borrows the <b>pooled
per-activity throughput</b> of the whole project), <b>discounted by the group's own start
execution index</b> (the NDIA PASEG-style start-anchored leading indicator &mdash; work must
start before it can finish, so demonstrated late starting slows the borrowed rate; the
discount only ever penalizes and is floored at &times;0.25), and <b>ranged by
reference-class forecasting</b> (the P75&rarr;P25 per-activity rates the groups WITH history
demonstrated &mdash; Flyvbjerg's outside view). Estimates are labeled everywhere they are
used and are replaced by direct measures the moment the group completes its first
activity.</p>
<table><tr><th scope=col>Group</th><th scope=col>To go</th><th scope=col>SEI</th>
<th scope=col>Borrowed rate</th><th scope=col>Discount</th><th scope=col>Estimated finish</th>
<th scope=col>Early &rarr; late (reference class)</th><th scope=col>Basis</th></tr>
{rows}</table>"""
    unforecastable = ""
    if rollup.unforecastable:
        names = ", ".join(_e(g) for g in rollup.unforecastable[:8])
        more = (
            f" (+{len(rollup.unforecastable) - 8} more)" if len(rollup.unforecastable) > 8 else ""
        )
        unforecastable = (
            f"<p class=muted><b>Unforecastable:</b> {names}{more} &mdash; no data date or no "
            "completions anywhere in the file, so there is nothing to borrow from; estimating "
            "here would be fabrication, not statistics.</p>"
        )
    limiting = (
        f" &mdash; limited by <b data-no-i18n>{_e(rollup.rate_limiting_group)}</b>"
        + (" <span class=exc-note>ESTIMATED</span>" if rollup.rate_finish_is_estimated else "")
        + " (the project finishes when its slowest group finishes)"
        if rollup.rate_limiting_group
        else ""
    )
    return f"""
<div class=panel><h2>Project rollup &mdash; recalculated from the group-weighted data points</h2>
<p class=muted>The per-group figures above, rolled BACK UP into a project-level forecast:
each group's <b>exact SPI(t)</b> is weighted by its <b>to-go activity count</b> (the groups
still carrying the remaining work dominate the index), and each group's own completion
throughput extrapolates its own backlog with the <b>latest</b> group finish as the project's
bottleneck answer. Groups without completion history contribute <b>credibility-weighted
estimates</b> (detailed below) so the rollup covers ALL the remaining work. Compare against
the top-down forecast &mdash; a gap means the remaining work sits in groups performing
differently than the project-wide average suggests.</p>
<table>
<tr><th scope=col>Figure</th><th scope=col>Rollup (direct only)</th>
<th scope=col>Rollup (full coverage)</th>
<th scope=col>Top-down (whole project)</th><th scope=col>Basis</th></tr>
<tr><th scope=row>SPI(t)</th><td class=num>{spi_cell}</td><td class=num><b>{spi_all}</b></td>
<td class=num>{top_spi}</td>
<td class=muted>{_e(rollup.weight_basis)}; {coverage}</td></tr>
<tr><th scope=row>Earned-schedule IEAC(t) finish</th><td>{d(rollup.ieac_finish)}</td>
<td><b>{d(rollup.ieac_finish_all)}</b></td>
<td>{d(top.get("earned_schedule"))}</td>
<td class=muted>IEAC(t) = AT + (PD &minus; ES) / <b>weighted</b> SPI(t)</td></tr>
<tr><th scope=row>Completion-rate finish</th><td colspan=2><b>{d(rollup.rate_finish)}</b></td>
<td>{d(top.get("rate"))}</td>
<td class=muted>each group's own throughput extrapolates its own to-go count; estimated
groups use their credibility-weighted rate{limiting}</td></tr>
</table>
{est_block}
{unforecastable}
<p class=cite>Weighted over {rollup.groups_total} group(s) of &ldquo;{_e(field)}&rdquo; with
to-go work &mdash; {_e(latest.source_file or latest.name)}</p></div>"""


def _where_it_lands_header(sch: Schedule, fset: ForecastSet) -> str:
    """Chapter 09 "Where it lands" (ADR-0207): the data-driven takeaway + a forecast KPI strip +
    the progress-to-finish and method-agreement bars, from the finish-forecast set the page
    already computes (compute_finish_forecasts — no new math). Anchored on the latest version."""
    dated = [f for f in fset.forecasts if f.finish is not None]
    n_methods = len(fset.forecasts)
    cpm_f = next((f for f in fset.forecasts if f.method_id == "cpm"), None)
    cpm_date = cpm_f.finish if cpm_f is not None else None
    dates: list[dt.date] = [f.finish for f in dated if f.finish is not None]
    earliest = min(dates, default=None)
    latest = max(dates, default=None)
    spread = (latest - earliest).days if earliest is not None and latest is not None else None
    var = (
        (cpm_date - fset.planned_finish).days
        if cpm_date is not None and fset.planned_finish is not None
        else None
    )

    def _vs(days: int) -> str:
        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} behind the baseline"
        if days < 0:
            n = -days
            return f"{n} day{'s' if n != 1 else ''} ahead of the baseline"
        return "on the baseline"

    if not dated:
        takeaway = (
            "No forecasting method could place the finish — the loaded files carry neither a "
            "computable network finish nor the progress history the rate methods need."
        )
    else:
        window = (
            f"between {_mdY(earliest)} and {_mdY(latest)}"
            if spread and spread > 0
            else f"at {_mdY(earliest)}"
        )
        cpm_clause = ""
        if cpm_date is not None:
            cpm_clause = f"; CPM logic lands on {_mdY(cpm_date)}"
            if var is not None:
                cpm_clause += f", {_vs(var)}"
        takeaway = f"{len(dated)} of {n_methods} forecasting methods place the finish {window}{cpm_clause}."

    kpi = _stat_cards(
        [
            ("Methods with a date", f"{len(dated)} / {n_methods}"),
            ("CPM finish", _mdY(cpm_date) if cpm_date is not None else "—"),
            ("Earliest", _mdY(earliest) if earliest is not None else "—"),
            ("Latest", _mdY(latest) if latest is not None else "—"),
            ("Spread (days)", str(spread) if spread is not None else "—"),
            ("vs Baseline", f"{var:+d} d" if var is not None else "—"),
        ]
    )
    progress_bar = _status_stack(
        "Progress to the finish",
        f"Activities complete vs still to go as of {_mdY(fset.as_of) if fset.as_of else 'the data date'}.",
        [
            ("Complete", fset.completed_count, "--ok"),
            ("Still to go", fset.remaining_count, "--muted"),
        ],
        f"{fset.completed_count + fset.remaining_count} activities",
    )
    agree_bar = _status_stack(
        "Method agreement",
        "How many independent forecasting methods could place a finish date.",
        [
            ("Placed a date", len(dated), "--ok"),
            ("Inputs missing", n_methods - len(dated), "--muted"),
        ],
        f"{spread}-day spread across the methods" if spread else "methods converge",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{progress_bar}{agree_bar}</div>'
    )


def _forecast_body(
    schedules: list[Schedule], cpms: list[CPMResult], sets: list[ForecastSet]
) -> str:
    """The multi-method finish-forecast page (M15/ADR-0030): logic vs throughput vs
    performance, the deck's Carnac KPI cards (PBIX p13, ADR-0042), plus per-version drift."""
    latest_sch, latest = schedules[-1], sets[-1]
    carnac = compute_carnac_summary(latest_sch, cpms[-1], latest)
    by_id = latest_sch.tasks_by_id
    method_rows = "".join(
        f"<tr><th scope=col>{_e(f.name)}</th>"
        f"<td><b>{_mdY(f.finish) if f.finish else '—'}</b></td>"
        f"<td class=muted>{_e(f.basis)}</td></tr>"
        for f in latest.forecasts
    )
    inputs = "".join(
        f"<tr><th scope=col>{_e(label)}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Data date", _mdY(latest.as_of) if latest.as_of else "none recorded"),
            ("Completed activities", latest.completed_count),
            ("To-go activities", latest.remaining_count),
            (
                "Historical completion rate",
                # `is not None`: a rate rounding to 0.0 must not display as absent (#67 class)
                f"{latest.rate_per_month:g} / month"
                if latest.rate_per_month is not None
                else "n/a",
            ),
            ("SPI(t)", f"{latest.spi_t:g}" if latest.spi_t is not None else "n/a"),
            (
                "Baseline (planned) finish",
                _mdY(latest.planned_finish) if latest.planned_finish else "n/a",
            ),
        )
    )
    cite = "; ".join(
        f"{by_id[uid].name} (UID {uid})" for uid in latest.citation_uids[:3] if uid in by_id
    )
    drift = ""
    if len(sets) >= 2:
        drift_rows = "".join(
            f"<tr><td>{_e(sch.source_file or sch.name)}</td>"
            f"<td>{_mdY(fs.as_of) if fs.as_of else '-'}</td>"
            + "".join(f"<td>{_mdY(f.finish) if f.finish else '—'}</td>" for f in fs.forecasts)
            + "</tr>"
            for sch, fs in zip(schedules, sets, strict=True)
        )
        drift = f"""
<div class=panel><h2>Forecast drift across versions</h2>
<p class=muted>The forecasts re-run per loaded version (oldest first). Forecasts that
keep sliding right are the bow-wave signature; methods that diverge from the CPM date tell
you the logic and the observed performance disagree.</p>
<div class=viz-controls>
<button id=prevDrift type=button>&#9664; Prev</button>
<span id=driftLabel class=muted></span>
<button id=nextDrift type=button>Next &#9654;</button>
<button id=driftPlay type=button>&#9654; Auto-play</button>
</div>
<p class=muted>Each forecast marker sits on a <b>locked date axis</b> (held fixed across every
version); step or play to watch the forecasts drift toward later dates as the project
progresses. Faint markers are the prior version's forecasts.</p>
<div id=driftChart class=chart-host></div>
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>CPM</th><th scope=col>Completion rate</th>
<th scope=col>Earned schedule</th></tr>{drift_rows}</table></div>
<script src="/static/drift.js"></script>"""
    return f"""
<div class=panel><h2>Forecast cards &mdash; {_e(latest_sch.name)}</h2>
<p class=muted>The reference deck's <i>Carnac</i> forecast KPIs (PBIX page 13): the project
window, the forecast end dates, the completion rate, remaining and project duration,
SPI(t), Earned Schedule, and the to-go activity count. A card with missing inputs shows
"—" &mdash; never a fabricated value. Every figure reuses the forecast below.</p>
{_user_tip("Independent methods (logic, the source schedule, throughput and performance) forecast the finish; where they disagree, the logic and the observed performance are telling different stories. A method whose inputs are missing shows a dash &mdash; never a fabricated date.")}
{_carnac_cards(carnac)}</div>
<div class=panel><h2>Finish forecast &mdash; {_e(latest_sch.name)}</h2>
<p class=muted>Independent answers to "when will it really end": the schedule's own
logic (CPM), the observed completion throughput, and earned-schedule performance
(IEAC(t) = AT + (PD &minus; ES) / SPI(t)). Methods that disagree are themselves a finding.
A method whose inputs are missing shows "—" &mdash; never a fabricated date.</p>
<table><tr><th scope=col>Method</th><th scope=col>Forecast finish</th><th scope=col>Basis</th></tr>{method_rows}</table>
<h3>Inputs</h3><table>{inputs}</table>
<p class=cite>Finish-controlling: {_e(cite)}</p></div>
{_forecast_explainer(latest)}{drift}"""


def _forecast_data(schedules: list[Schedule], sets: list[ForecastSet]) -> dict[str, object]:
    # LOCKED date axis (item 5) for the drift animation: span every version's
    # forecasts + data dates + baseline finishes, so the time scale is held fixed through
    # the stepper and the forecasts visibly drift right rather than the axis rescaling.
    axis_dates: list[dt.date] = []
    for fs in sets:
        if fs.as_of is not None:
            axis_dates.append(fs.as_of)
        if fs.planned_finish is not None:
            axis_dates.append(fs.planned_finish)
        axis_dates.extend(f.finish for f in fs.forecasts if f.finish is not None)
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    # the method order/labels the animation plots (stable, deterministic)
    methods = [{"id": f.method_id, "name": f.name} for f in (sets[-1].forecasts if sets else [])]
    return {
        "axis": axis,
        "methods": methods,
        "versions": [
            {
                "label": sch.source_file or sch.name,
                "as_of": fs.as_of.isoformat() if fs.as_of else None,
                "completed": fs.completed_count,
                "remaining": fs.remaining_count,
                "rate_per_month": fs.rate_per_month,
                "spi_t": fs.spi_t,
                "planned_finish": fs.planned_finish.isoformat() if fs.planned_finish else None,
                "forecasts": {
                    f.method_id: f.finish.isoformat() if f.finish else None for f in fs.forecasts
                },
            }
            for sch, fs in zip(schedules, sets, strict=True)
        ],
    }


def _curves_body(curves: MonthCurves) -> str:
    """The Finish & Slippage page (PBIX pages 6, 7, 12): three monthly-curve charts.

    Finishes (actual vs baseline, latest version), DATA Date Finishes (per-version
    actual-finish curves overlaid — the bow wave's line sibling), and Slippage (the
    per-version start and finish curves). All client-side SVG over /api/curves."""
    n_versions = len(curves.versions)
    latest = curves.versions[-1].label if curves.versions else ""
    multi = (
        ""
        if n_versions >= 2
        else "<p class=muted>Load more than one version (monthly snapshots, by data date) to "
        "see the per-version curve overlays — with a single version the curves show that "
        "version alone.</p>"
    )
    return f"""
<div class=viz-controls><label><input type=checkbox id=curvesHideDone> hide 100% complete</label>
<span class=muted>&mdash; show only the remaining / forecast work on every curve below.</span>
<label style="margin-left:1em">Time scale <select id=curvesGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label></div>
<div class=panel><h2>Finishes &mdash; actual vs baseline by month</h2>
<p class=muted>For the latest version (<b>{_e(latest)}</b>): activities counted by the month
they were <b>baselined</b> to finish (gold) against the month they <b>actually</b> finished
or are now scheduled to (blue). Where the blue curve sits to the right of the gold is slipped
finish work, read month by month.</p>
<div id=finishesChart class=chart-host></div></div>
<div class=panel><h2>DATA Date Finishes &mdash; actual-finish curve per version</h2>
<p class=muted>One file per frame on a month axis held fixed across every file (ADR-0150):
step or play through the loaded versions (oldest first by data date) and watch the finish
curve slide right &mdash; the bow wave of slipped finishes. The frame label names the file
you are looking at.</p>{multi}
<div id=dataDateChart class=chart-host></div></div>
<div class=panel><h2>Slippage &mdash; start &amp; finish curves per version</h2>
<p class=muted>One file per frame (fixed month axis, ADR-0150): activities counted by their
<b>start</b> month (solid) and <b>finish</b> month (dashed). Step or play through the versions
&mdash; the whole profile sliding right is the slippage signature. The frame label names the
file shown.</p>
<div id=slippageChart class=chart-host></div></div>
<script src="/static/timeaxis.js"></script>
<script src="/static/curves.js"></script>"""


def _curves_data(curves: MonthCurves) -> dict[str, object]:
    """JSON for the finish/slippage curves: shared month axis + per-version count series."""
    return {
        "months": list(curves.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_date": v.status_date,
                "status_index": v.status_index,
                "baseline_finishes": list(v.baseline_finishes),
                "actual_finishes": list(v.actual_finishes),
                "baseline_starts": list(v.baseline_starts),
                "actual_starts": list(v.actual_starts),
            }
            for v in curves.versions
        ],
    }


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _health_checks_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Extra structural health checks (handbook Fig. 6-9) as a stoplight list — green when clear,
    else the count + the first offending UIDs, with a plain-English reason for each."""
    checks = compute_health_checks(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            hidden = [_e(f"UID {u}") for u in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Structural health checks</h2>"
        "<p class=muted>Deterministic schedule-construction checks from the NASA Schedule "
        "Management Handbook (Fig. 6-9), beyond DCMA-14 &mdash; green = clear, otherwise the count "
        "and the first offending activities (the activity grid above is the full record).</p>"
        + "".join(cards)
        + "</div>"
    )


def _schedule_variance_panel(sch: Schedule) -> str:
    """Schedule variance in TIME (handbook §7.3.3.1): project SVt = ES - AT (working days), plus the
    per-activity finish slip (actual - baseline). Favorable when ahead of plan (SVt >= 0)."""
    sv = compute_schedule_variance(sch, non_summary(sch))
    if sv.svt_days is None and sv.completed == 0 and sv.started == 0:
        # Distinguish a baselined-but-un-statused plan (has baselines, no actuals) from a file
        # with no baseline at all — the operator's Hard_File pair is exactly the former for the
        # first version, and the message should point them at the statused version.
        if sv.baselined > 0:
            hint = (
                f"This is the <b>baselined plan</b> ({sv.baselined} activities carry a baseline) "
                "with <b>no progress statused yet</b> &mdash; there are no actual start/finish "
                "dates to measure against it. Open the <b>statused version</b> of this schedule "
                "(the later data date, with actuals recorded) to see the schedule variance."
            )
        else:
            hint = (
                "This schedule carries no baseline dates, so there is no plan to measure progress "
                "against. Baseline the schedule in the source tool, then status it with progress."
            )
        return (
            "<div class=panel><h2>Schedule variance (time)</h2>"
            f"<p class=muted>Not computable on this file &mdash; {hint}</p></div>"
        )
    if sv.svt_days is None:
        svt_val = "n/a"
    else:
        favorable = sv.svt_days >= 0
        sign = "+" if sv.svt_days > 0 else ""
        # SVt > 0 = ES ahead of AT = ahead of plan (favorable); < 0 = behind (unfavorable)
        svt_val = f"{sign}{sv.svt_days:g} wd ({'ahead' if favorable else 'behind'})"
    cards = _stat_cards(
        [
            ("Schedule variance (SVt = ES - AT)", svt_val),
            ("Earned Schedule (ES)", "n/a" if sv.es_days is None else f"{sv.es_days:g} wd"),
            ("Actual Time (AT)", "n/a" if sv.at_days is None else f"{sv.at_days:g} wd"),
            ("Completed (finish variance)", str(sv.completed)),
            (
                "Mean finish variance",
                "n/a"
                if sv.mean_activity_variance_days is None
                else f"{sv.mean_activity_variance_days:+g} wd",
            ),
            ("Started (start variance)", str(sv.started)),
            (
                "Mean start variance",
                "n/a"
                if sv.mean_start_variance_days is None
                else f"{sv.mean_start_variance_days:+g} wd",
            ),
        ]
    )
    names = sch.tasks_by_id

    def _var_table(title: str, rows_data: tuple[ActivityVariance, ...], kind: str) -> str:
        if not rows_data:
            return ""
        rows = "".join(
            f"<tr><td>{v.unique_id}</td>"
            f"<td>{_e(names[v.unique_id].name) if v.unique_id in names else ''}</td>"
            f'<td class="rk-score {"rk-high" if v.variance_days > 0 else "rk-min"}">'
            f"{v.variance_days:+g}</td></tr>"
            for v in rows_data
        )
        return (
            f"<h3>{title}</h3>"
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>{kind} variance (wd)</th></tr>{rows}</table>"
        )

    table = _var_table("Largest finish variances (actual &minus; baseline)", sv.worst, "Finish")
    table += _var_table(
        "Largest start variances (actual &minus; baseline)", sv.worst_start, "Start"
    )
    return (
        "<div class=panel><h2>Schedule variance (time)</h2>"
        "<p class=muted>The NASA Schedule Management Handbook (&sect;7.3.3.1) time view of progress. "
        "<b>SVt = ES &minus; AT</b> (Earned Schedule minus Actual Time): positive is "
        "<b>ahead</b> of plan (favorable), negative is <b>behind</b> (unfavorable) &mdash; the "
        "count-based Earned-Schedule companion to SPI(t). Per-activity <b>finish</b> variance is a "
        "completed activity's actual finish minus its baseline finish; <b>start</b> variance is a "
        "started activity's actual start minus its baseline start (in working days, positive = "
        "late) &mdash; the latter surfaces in-progress slippage before tasks complete.</p>"
        f"{cards}{table}</div>"
    )


#: float-erosion stoplight → the shared 5-level risk badge classes (green / amber / red)
_EROSION_BADGE = {"green": "rk-min", "yellow": "rk-mod", "red": "rk-extreme"}


def _float_erosion_panel(sch: Schedule, cpm: CPMResult, wbs_field: str | None = None) -> str:
    """Float erosion by WBS (handbook Figs 7-34/7-35): per-top-level-WBS minimum / average total
    float, critical count, and a stoplight on the group's minimum float — where buffer is thinning.

    ``wbs_field`` (ADR-0150): the operator-chosen grouping field — any custom field (e.g. a
    "CA-WBS" outline code) or the built-in WBS — selected via the panel's own form."""
    from schedule_forensics.engine.grouping import available_fields

    field = wbs_field if wbs_field else "WBS"
    fe = compute_float_erosion(sch, cpm, wbs_field=field)
    options = "".join(
        f'<option value="{_e(f)}"{" selected" if f == field else ""}>{_e(f)}</option>'
        for f in ["WBS", *sorted(x for x in available_fields(sch) if x != "WBS")]
    )
    picker = (
        '<form method=get class=viz-controls style="margin:.3em 0">'
        "<label>Group by field: "
        f'<select name=erosion_field data-no-i18n onchange="this.form.submit()">{options}'
        "</select></label> "
        "<span class=muted>use a custom field (e.g. an outline code) if your WBS lives there</span>"
        "</form>"
    )
    if not fe.groups:
        return (
            "<div class=panel><h2>Float erosion by WBS</h2>"
            + picker
            + "<p class=muted>No schedulable activities to group.</p></div>"
        )
    thr = f"{fe.low_float_threshold_days:g}"
    rows = []
    for g in fe.groups:
        badge = _EROSION_BADGE.get(g.status, "rk-min")
        rows.append(
            f"<tr><td>{_e(g.wbs)}</td><td>{g.count}</td>"
            f'<td class="rk-score {badge}">{g.min_float_days:g}</td>'
            f"<td>{g.avg_float_days:g}</td><td>{g.critical_count}</td></tr>"
        )
    proj_min = "n/a" if fe.min_float_days is None else f"{fe.min_float_days:g} wd"
    cards = _stat_cards(
        [
            ("Lowest total float (any WBS)", proj_min),
            ("WBS groups", str(len(fe.groups))),
            ("Eroded groups (min float < 0)", str(sum(1 for g in fe.groups if g.status == "red"))),
        ]
    )
    return (
        "<div class=panel><h2>Float erosion by WBS</h2>"
        + picker
        + f"<p class=muted>Grouping field: <b>{_e(field)}</b> (top-level dotted segment). "
        "Total float grouped by top-level WBS (NASA Schedule Management Handbook) "
        "&mdash; where buffer is thinning before the project-level margin is hit. The stoplight is on "
        f"each group's <b>minimum</b> total float: <b>red</b> below 0 (eroded / behind a constraint), "
        f"<b>amber</b> 0&ndash;{thr} working days (thin buffer), <b>green</b> above {thr}. Float is "
        "read progress-aware (the source tool's stored Total Slack when present).</p>"
        f"{cards}"
        "<table><tr><th scope=col>WBS</th><th scope=col>Activities</th>"
        "<th scope=col>Min float (wd)</th><th scope=col>Avg float (wd)</th>"
        "<th scope=col>Critical</th></tr>"
        f"{''.join(rows)}</table></div>"
    )


def _constraint_checks_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Constraint-health checks (handbook Fig. 6-9): unsatisfied hard date constraints and breached
    deadlines, as a stoplight list — green when clear, else the count + the first offending UIDs."""
    checks = compute_constraint_health(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            hidden = [_e(f"UID {u}") for u in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        pop = f"<span class=muted> of {c.population}</span>" if c.population else ""
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Constraint health</h2>"
        "<p class=muted>How imposed dates fare against the network logic (NASA Schedule Management "
        "Handbook, Fig. 6-9): a <b>hard constraint</b> the CPM date runs past cannot be honored, and "
        "a <b>deadline</b> the logic finish overruns is artificial negative float. Green = clear, "
        "otherwise the count and the first offending activities.</p>" + "".join(cards) + "</div>"
    )


def _vertical_integration_panel(sch: Schedule) -> str:
    """Vertical-integration check (handbook Fig. 6-9): summaries whose stored span does not envelope
    the work beneath them — a stoplight finding card, green when clear else the offending summaries."""
    vi = compute_vertical_integration(sch)
    ok = vi.count == 0
    badge_cls = "rk-min" if ok else "rk-high"
    badge = "✓ clear" if ok else str(vi.count)
    offs = ""
    if vi.offenders:
        shown = ", ".join(f"UID {u}" for u in vi.offenders[:8])
        hidden = [_e(f"UID {u}") for u in vi.offenders[8:]]
        if vi.count > len(vi.offenders):
            hidden.append(f"&hellip; and {vi.count - len(vi.offenders)} beyond the citation cap")
        offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
    pop = f"<span class=muted> of {vi.population} summary group(s)</span>" if vi.population else ""
    note = (
        ""
        if vi.population
        else "<p class=muted>No summaries with a WBS code, stored dates, and dated descendants "
        "to evaluate.</p>"
    )
    return (
        "<div class=panel><h2>Vertical integration</h2>"
        "<p class=muted>Whether each summary (rollup) bar envelopes the detail activities beneath it "
        "(by WBS nesting), using the schedule's stored dates &mdash; the handbook's vertical-"
        "traceability check. A parent that starts after its earliest child or finishes before its "
        "latest is an inconsistent rollup.</p>"
        f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
        f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
        f"<b>Inconsistent vertical integration</b>{pop}</div>"
        f"<p>{_e(vi.description)}</p>{offs}</div>{note}</div>"
    )


def _logic_checks_panel(sch: Schedule) -> str:
    """Logic-integrity checks (out-of-sequence progress, redundant logic) as a stoplight list —
    green when clear, else the count + the first offending links, with a plain-English reason."""
    checks = compute_logic_integrity(sch).checks
    cards = []
    for c in checks:
        if not c.evaluated:
            cards.append(
                '<div class="finding sev-INFO">'
                '<div class=finding-head><span class="rk-score rk-min">n/a</span> '
                f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p></div>"
            )
            continue
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(c.offenders[:8])
            hidden = [_e(o) for o in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        pop = f"<span class=muted> of {c.population} link(s)</span>" if c.population else ""
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Logic integrity</h2>"
        "<p class=muted>Forensic logic-construction checks from the NASA Schedule Management "
        "Handbook (Fig. 6-9), beyond DCMA-14 &mdash; <b>out-of-sequence</b> progress (work recorded "
        "in an order the logic forbids) and <b>redundant logic</b> (a direct link a longer path "
        "already implies). Green = clear, otherwise the count and the first offending links "
        "(written predecessor&rarr;successor by UniqueID).</p>" + "".join(cards) + "</div>"
    )


# NASA Schedule Management Handbook citations — verified against the committed reference PDF
# (00_REFERENCE_INTAKE/references/schedule-management-handbook-20240315-update.zip); the section
# numbers and the 50%-consumed corrective threshold are quoted from that document, not invented.
# CITATION CORRECTED (ADR-0254, verified against the PDF): the sentence "The corrective action
# threshold is set where the margin is 50% consumed" lives in §7.3.3.2.3 "Sufficiency of Margin"
# (printed p.324 / PDF p.325), NOT §7.3.3.1.6 as ADR-0230 recorded — and it is EXAMPLE-framed
# there ("In this example case, the P/p has chosen..."). §7.3.3.1.6's own Thresholds paragraph is
# deliberately non-numeric ("corrective action is required when significant margin is consumed");
# the handbook's general rule is that thresholds are program-set in the SMP.
_HB = "NASA Schedule Management Handbook"
_HB_MARGIN_SEC = "&sect;5.5.11, Establish and Allocate Margin"
_HB_CONSUME_SEC = "&sect;7.3.3.2.3 Sufficiency of Margin (the handbook's example threshold)"


def _margin_terminology() -> str:
    """A collapsed MARGIN vs CONTINGENCY vs FLOAT glossary, cited to the handbook — the three are
    routinely conflated and the distinction is load-bearing for the burn-down (F3a)."""
    return (
        "<details class=explain><summary>MARGIN vs CONTINGENCY vs FLOAT &mdash; what each term means"
        "</summary><div class=explain-body>"
        f"<h4>Schedule margin</h4><p>A <b>separately-planned, visible buffer activity</b> the planner "
        f"inserts before a committed milestone to absorb risk and uncertainty &mdash; it has a real "
        f"working-day duration in the schedule. The {_HB} ({_HB_MARGIN_SEC}) manages margin as an "
        f"explicit activity and &ldquo;places emphasis on identifying and managing schedule margin over "
        f"float.&rdquo;</p>"
        "<h4>Contingency</h4><p>Here, the schedule calendar&rsquo;s <b>non-working time</b> "
        "(weekends + holidays) between the status date and the target &mdash; unplanned cushion in the "
        "calendar, distinct from the work-day margin (no overlap).</p>"
        "<h4>Float (slack)</h4><p>A <b>computed</b> CPM quantity: how long an activity can slip without "
        "moving the finish. It is not planned buffer &mdash; the handbook manages margin <i>over</i> "
        "float, because margin that sits on a path with float protects nothing.</p>"
        "</div></details>"
    )


def _margin_panel(key: str, sch: Schedule, cpm: CPMResult, confirmed: frozenset[int] | None) -> str:
    """Schedule-margin panel: BOTH margin numbers, the MARGIN/CONTINGENCY/FLOAT glossary, and the
    operator's confirm/deny overlay of the margin-task set (name-based by default).

    ``confirmed`` is this version's operator-confirmed margin UniqueIDs (``None`` ⇒ the name-based
    default). The two numbers may differ: **total margin** sums the margin activities' durations;
    **effective margin** is how far the finish pulls in if all margin were removed — the buffer
    actually on the driving chain. Margin sitting on a path with float counts toward total but not
    effective (NASA Schedule Management Handbook)."""
    candidates = margin_candidates(sch, cpm)
    if not candidates:
        return (
            "<div class=panel><h2>Schedule margin</h2>"
            + _margin_terminology()
            + "<p class=muted>No schedule-margin activities found &mdash; no non-summary activity is "
            "named &ldquo;margin&rdquo; and none carries a handbook alias (reserve / contingency / "
            f"integrated return). Margin is identified by name ({_HB} {_HB_MARGIN_SEC}); rename a "
            "buffer activity to include &ldquo;margin&rdquo; (or confirm it here once it appears) so "
            "the burn-down can measure the reserve.</p></div>"
        )
    m = compute_margin(sch, cpm, margin_uids=confirmed)
    using = (
        "operator-confirmed set"
        if confirmed is not None
        else "name-based default (activities named &ldquo;margin&rdquo;)"
    )
    plural = "activities" if m.count != 1 else "activity"
    crit_note = (
        f"{m.on_critical_count} of {m.count} on the critical path"
        if m.on_critical_count
        else f"{m.count} margin {plural}; 0 on the critical path"
    )
    gap_note = (
        " Here the two <b>differ</b>: margin sitting on a path with float counts toward total but "
        "protects nothing, so effective is lower."
        if m.total_margin_days != m.effective_margin_days
        else " Here the two <b>agree</b>: all margin is on the driving chain."
    )
    cards = _stat_cards(
        [
            ("Total margin (sum of durations)", f"{m.total_margin_days:g} wd"),
            ("Effective margin (on driving chain)", f"{m.effective_margin_days:g} wd"),
            ("Margin activities", crit_note),
        ]
    )

    def _crow(c: MarginCandidate) -> str:
        checked = (c.unique_id in confirmed) if confirmed is not None else (c.tier == "primary")
        badge_cls = "rk-min" if c.tier == "primary" else "rk-high"
        return (
            "<tr>"
            f'<td><input type=checkbox name=uid value="{c.unique_id}"'
            f'{" checked" if checked else ""} aria-label="mark UID {c.unique_id} as schedule margin">'
            "</td>"
            f"<td>{c.unique_id}</td><td>{_e(c.name)}</td>"
            f'<td><span class="rk-score {badge_cls}">{c.tier}</span></td>'
            f"<td class=num>{c.duration_days:g}</td>"
            f"<td class=num>{c.total_float_days:g}</td>"
            f'<td class="rk-score {"rk-high" if c.on_critical else "rk-min"}">'
            f"{'Yes' if c.on_critical else 'No'}</td></tr>"
        )

    rows = "".join(_crow(c) for c in candidates)
    back = f"/analysis/{quote(key, safe='')}"
    form = (
        '<form method=post action="/margin/confirm">'
        f'<input type=hidden name=key value="{_e(key)}">'
        f'<input type=hidden name=back value="{_e(back)}">'
        "<table><tr><th scope=col>Margin?</th><th scope=col>UID</th><th scope=col>Name</th>"
        "<th scope=col>Match</th><th scope=col>Days</th><th scope=col>Total float (d)</th>"
        "<th scope=col>On critical path?</th></tr>"
        f"{rows}</table>"
        '<div class=row-actions style="margin-top:8px">'
        "<button type=submit name=action value=confirm>Confirm margin set</button> "
        "<button type=submit name=action value=reset class=btn-link "
        'title="Discard the confirmed set for this version and revert to the name-based default">'
        "Reset to name-based</button></div></form>"
    )
    return (
        "<div class=panel><h2>Schedule margin</h2>"
        + _margin_terminology()
        + "<p class=muted>Explicit buffer activities that protect the project finish. "
        "<b>Total margin</b> sums the margin activities&rsquo; durations; <b>effective margin</b> is "
        "how far the finish would pull in if all margin were removed &mdash; the buffer actually "
        "protecting the finish."
        + gap_note
        + f" ({_HB} {_HB_MARGIN_SEC}).</p>"
        + cards
        + f"<p class=muted>Currently measuring from the <b>{using}</b>. Tick the activities that ARE "
        "schedule margin and <b>Confirm</b> to pin the set for this version (near-miss aliases are "
        "listed but unticked until you confirm them); the burn-down and erosion trend then use your "
        "confirmed set across the project&rsquo;s versions. <b>Reset</b> reverts to the name-based "
        "default.</p>"
        + form
        # ADR-0254: the Fig 5-30 band + SRA sufficiency are inherently cross-version/time-series
        # views, so they live on the Margin Dashboard — this per-version panel links, not embeds.
        + '<p style="margin-top:10px"><a class=btn-link href="/margin">Compare against the '
        "Figure 5-30 guideline band + risk-based sufficiency on the Margin Dashboard &rarr;</a></p>"
        "</div>"
    )


def _scatter_panel(key: str, sch: Schedule, cpm: CPMResult) -> str:
    """An activity scatter (total float x duration) on the analysis page, WITH the story
    (ADR-0150): a written health analysis naming the pressure points — long, low-float
    incomplete work — plus what the float distribution says about logic quality. Every figure
    is engine-computed here; the chart (scatter.js) is presentation over the same rows."""
    per_day = sch.calendar.working_minutes_per_day or 480
    incomplete: list[tuple[float, float, Task]] = []
    for task in non_summary(sch):
        if task.percent_complete >= 100.0:
            continue
        timing = cpm.timings.get(task.unique_id)
        recomputed = float(timing.total_float) if timing is not None else 0.0
        tf_days = effective_total_float(task, recomputed) / per_day
        dur_days = task.duration_minutes / (1440 if task.duration_is_elapsed else per_day)
        incomplete.append((tf_days, dur_days, task))
    n = len(incomplete)
    story: str
    pressure_rows = ""
    if n:
        critical = sum(1 for tf, _d, task in incomplete if tf <= 0)
        thin = sum(1 for tf, _d, _t in incomplete if 0 < tf <= 10)
        high = sum(1 for tf, _d, _t in incomplete if tf > 44)
        # pressure points: the longest incomplete activities inside the thin-float band
        pressure = sorted((x for x in incomplete if x[0] <= 10), key=lambda x: -x[1])[:5]
        med = sorted(tf for tf, _d, _t in incomplete)[n // 2]
        story = (
            f"<p><b>What this data says:</b> of the <b>{n}</b> incomplete activities, "
            f"<b>{critical}</b> ({percent(critical, n):.1f}%) have zero-or-negative float "
            f"(no room to slip), <b>{thin}</b> more sit within 10 working days of it, and "
            f"<b>{high}</b> ({percent(high, n):.1f}%) carry more than 44 wd of float "
            "&mdash; float that high usually means missing logic (DCMA-06), not genuine "
            f"slack. The median float is <b>{med:.0f} wd</b>. "
            + (
                "The schedule's ability to absorb a slip rests on how the low-float band "
                "is managed; the table below names the biggest pressure points &mdash; the "
                "longest tasks with the least room."
                if (critical + thin)
                else "No incomplete work is inside the 10-day low-float band &mdash; the "
                "network currently has room to absorb slips."
            )
            + "</p>"
        )
        if pressure:
            prows = "".join(
                f"<tr><td>{task.unique_id}</td><td>{_e(task.name)}</td>"
                f"<td>{d:.0f}</td><td>{tf:.0f}</td>"
                f"<td>{round(task.percent_complete)}%</td></tr>"
                for tf, d, task in pressure
            )
            pressure_rows = (
                "<details><summary class=btn-link>Top pressure points (longest low-float "
                "work)</summary><table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
                "<th scope=col>Duration (wd)</th><th scope=col>Float (wd)</th>"
                f"<th scope=col>%</th></tr>{prows}</table></details>"
            )
    else:
        story = "<p class=muted>No incomplete activities to analyze.</p>"
    return (
        "<div class=panel><h2>Activity scatter &mdash; float vs duration</h2>"
        f"<p class=muted>Source: <b>{_e(sch.source_file or sch.name)}</b>. "
        "One dot per activity: <b>total float</b> (x) against <b>duration</b> (y), "
        "red = critical (progress-aware), diamonds = milestones. Long-duration, low-float "
        "activities sit at the lower-left &mdash; the schedule's pressure points a count "
        "metric never reveals. The full activity grid above is the accessible data table.</p>"
        f"{story}{pressure_rows}"
        f'<div class=chart-host id=scatterChart data-name="{_e(key)}"></div></div>'
        '<script src="/static/scatter.js"></script>'
    )


#: The histogram's DCMA-aligned total-float bands, by index — MUST mirror static/histogram.js
#: BUCKETS (the drill panel posts the band INDEX to /export/{fmt}/float-band/{name}).
_FLOAT_HIST_BANDS: tuple[tuple[str, Callable[[float], bool]], ...] = (
    ("< 0", lambda v: v < 0),
    ("0", lambda v: v == 0),
    ("1-5", lambda v: 0 < v <= 5),
    ("6-10", lambda v: 5 < v <= 10),
    ("11-20", lambda v: 10 < v <= 20),
    ("21-44", lambda v: 20 < v <= 44),
    ("> 44", lambda v: v > 44),
)


def _float_histogram_panel(key: str) -> str:
    """An activity total-float distribution histogram on the analysis page (handbook §6.3.2.5.2.2).

    Operator 2026-07-08: the chart takes the LEFT half of the panel; clicking a bar fills the
    RIGHT half with that band's activities (UID + Name by default, any other standard or custom
    column addable like the Gantt's Columns dropdown) and an Excel export of the selection.
    """
    return (
        "<div class=panel><h2>Total-float distribution</h2>"
        "<p class=muted>Activities binned by <b>total float</b> (working days), in DCMA-aligned "
        "bands. Mass at <b>0 / &lt; 0</b> is the critical-and-behind core; a spike in the "
        "<b>&gt; 44 d</b> band is float padding or missing successor logic (DCMA-06). "
        "<b>Click a bar</b> to list that band's activities on the right; add columns with the "
        "selector and export the selection to Excel.</p>"
        "<div class=hist-split>"
        f'<div class="chart-host hist-left" id=floatHist data-name="{_e(key)}"></div>'
        "<div class=hist-right id=floatHistDrill><p class=muted>Click a histogram bar to see "
        "the activities in that float band here.</p></div>"
        "</div></div>"
        '<script src="/static/histogram.js"></script>'
    )


def _calendar_panel(sch: Schedule) -> str:
    """The working calendar the analysis runs on — imported from the file (ADR-0028).

    Every computed date, float, and day-denominated threshold rides this calendar, so the
    analyst must be able to verify the time basis (and spot a fail-soft default) on the page.
    When the file assigns some activities their own calendar, the base CPM still models only the
    single project calendar (ADR-0028), so this panel discloses that single-calendar basis rather
    than letting the analyst read the project-calendar row as the whole story (#26).
    """
    cal = sch.calendar
    days = ", ".join(_WEEKDAY_NAMES[d] for d in cal.work_weekdays)
    hours_text = f"{cal.working_minutes_per_day / 60:g} h/day ({cal.working_minutes_per_day} min)"
    if cal.holidays:
        shown = ", ".join(_mdY(d) for d in cal.holidays[:10])
        holidays = _expandable_more(
            f"{len(cal.holidays)} — {shown}", [_mdY(d) for d in cal.holidays[10:]]
        )
    else:
        holidays = "none"
    # Fail-soft disclosure (#26): the base CPM solves on this ONE project calendar; when the file
    # carries per-task calendars with a different working pattern, its base-CPM dates/float are a
    # single-calendar approximation for those activities (the SSI driving path honors each task's
    # own calendar, ADR-0118). Silent on a single-calendar file (off is empty).
    off = off_project_calendars(sch)
    disclosure = ""
    if off:
        n = len(off)
        cal_word = "calendar" if n == 1 else "calendars"
        names = ", ".join(f"<b>{_e(c.name)}</b>" for c in off)
        disclosure = (
            f'<div class="notice info">Some activities run on {n} per-task {cal_word} whose working '
            f"pattern differs from the project calendar <b>{_e(cal.name)}</b> ({names}). The engine's "
            "base CPM models the single project calendar (ADR-0028), so a date or float it computes "
            "(shown where the file carries no stored value of its own) is a single-calendar "
            "approximation for those activities; the file's own stored dates and the Path Analysis / "
            "Driving Path views honor each task's own calendar (ADR-0118)."
            "</div>"
        )
    return f"""
<div class=panel><h2>Working calendar</h2>
<p class=muted>The time basis behind every computed date, float, and day-denominated
threshold — imported from the file's project calendar (the standard 8h/Mon-Fri default
when the file carries none).</p>
{disclosure}
<table>
<tr><th scope=col>Calendar</th><td>{_e(cal.name)}</td></tr>
<tr><th scope=col>Working day</th><td>{_e(hours_text)}</td></tr>
<tr><th scope=col>Work week</th><td>{_e(days)}</td></tr>
<tr><th scope=col>Holidays</th><td>{_e(holidays)}</td></tr>
</table></div>"""


def _stat_cards(cards: list[tuple[str, str]]) -> str:
    """A responsive grid of label/value stat cards (the deck's KPI-card row)."""
    items = "".join(
        f"<div class=stat-card><div class=stat-value>{_e(value)}</div>"
        f"<div class=stat-label>{_e(label)}</div></div>"
        for label, value in cards
    )
    return f"<div class=stat-grid>{items}</div>"


def _count_bar_table(headers: tuple[str, str], rows: list[tuple[str, int, float]]) -> str:
    """A count + percent table with an inline percent bar (deck pie/pivot, as a table)."""
    body = "".join(
        f"<tr><td>{_e(label)}</td><td>{count}</td>"
        f'<td class=pct-cell><span class=pct-bar style="width:{min(pct, 100):.0f}%"></span>'
        f"<span class=pct-num>{pct:.1f}%</span></td></tr>"
        for label, count, pct in rows
    )
    return (
        f"<table class=card-table><tr><th scope=col>{_e(headers[0])}</th><th scope=col>Count</th>"
        f"<th scope=col>{_e(headers[1])}</th></tr>{body}</table>"
    )


def _card_body(key: str, sch: Schedule, analysis: _Analysis) -> str:
    """The deck's *Metrics* page (PBIX page 1) — the schedule's ID card.

    Reproduces the landing-page aggregates: activity makeup, status split, completion
    performance, the primary-constraint distribution, and the KPI cards — all from the
    engine outputs already computed for this schedule (no recomputation of the CPM)."""
    makeup = compute_activity_makeup(sch)
    constraints = compute_constraint_distribution(sch)
    cpm, comp = analysis.cpm, analysis.completion
    cal = sch.calendar

    # makeup pie -> count/percent table
    total = makeup.total or 1
    makeup_tbl = _count_bar_table(
        ("Task makeup", "% of activities"),
        [
            ("Normal", makeup.normal, 100.0 * makeup.normal / total),
            ("Milestones", makeup.milestones, 100.0 * makeup.milestones / total),
            ("Summaries", makeup.summaries, 100.0 * makeup.summaries / (total + makeup.summaries)),
        ],
    )
    status_tbl = _count_bar_table(
        ("Activity status", "% of activities"),
        [
            ("Complete", makeup.complete, 100.0 * makeup.complete / total),
            ("In progress", makeup.in_progress, 100.0 * makeup.in_progress / total),
            ("Planned", makeup.planned, 100.0 * makeup.planned / total),
        ],
    )
    # completion-performance split (deck "Completion Performance" pie)
    split = [
        ("Completed ahead", comp["completed_ahead"]),
        ("Completed on schedule", comp["completed_on_schedule"]),
        ("Completed behind", comp["completed_behind"]),
    ]
    perf_tbl = _count_bar_table(
        ("Completion performance", "% of measured completions"),
        [(label, r.count, r.value) for label, r in split],
    )
    constraint_tbl = _count_bar_table(
        ("Primary constraint", "% of activities"),
        [(r.constraint_type, r.count, r.percent) for r in constraints],
    )

    # KPI cards (reuse the engine outputs the report already computed)
    starts = [t.start for t in non_summary(sch) if t.start is not None]
    earliest = _mdY(min(starts)) if starts else "—"
    latest_finish = _mdY(offset_to_datetime(sch.project_start, cpm.project_finish, cal))
    critical = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and (tm := cpm.timings.get(t.unique_id)) is not None
        and tm.total_float <= 0
    )
    togo_normal = sum(
        1 for t in non_summary(sch) if t.percent_complete < 100.0 and not t.is_milestone
    )
    togo_ms = sum(1 for t in non_summary(sch) if t.percent_complete < 100.0 and t.is_milestone)
    ahead, late = comp["avg_days_ahead"], comp["avg_days_late"]
    stale = comp["elapsed_since_last_finish"]
    cards = _stat_cards(
        [
            ("Earliest start", earliest),
            ("Computed finish", latest_finish),
            ("Data date", _mdY(sch.status_date) if sch.status_date else "—"),
            ("Activities complete", f"{100.0 * makeup.complete / total:.1f}%"),
            ("Critical (incomplete)", str(critical)),
            ("To-go activities", str(togo_normal)),
            ("To-go milestones", str(togo_ms)),
            ("Avg days ahead", f"{ahead.value:g}" if ahead.population else "—"),
            ("Avg days late", f"{late.value:g}" if late.population else "—"),
            ("% elapsed since last finish", f"{stale.value:g}%" if stale.population else "—"),
        ]
    )
    return f"""
<div class=panel><h2>Schedule card &mdash; {_e(sch.name)}</h2>
<p class=muted>The schedule's ID card (the reference deck's <i>Metrics</i> page): activity
makeup, status, completion performance, the primary-constraint distribution, and the
headline KPI cards — every figure computed from this file and verifiable on the
<a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
{cards}</div>
<div class="panel"><div class=card-cols>
<div>{makeup_tbl}</div><div>{status_tbl}</div>
<div>{perf_tbl}</div><div>{constraint_tbl}</div>
</div></div>"""


def _num(value: float | None, *, suffix: str = "") -> str:
    """Render an optional number for a table cell — em-dash when absent (never a fake 0)."""
    return f"{value:g}{suffix}" if value is not None else "—"


def _wbs_body(key: str, groups: tuple[WBSGroup, ...]) -> str:
    """The deck's *Completion Metrics* (PBIX 8) + *SPI and Earned Schedule* (PBIX 9) pages.

    Two WBS pivots over one version: a completion-by-WBS table (counts, %, ahead/on/behind,
    duration ratio) and the SPI(t)/Earned-Schedule-by-WBS combo chart + table. Grouped by
    the top-level WBS segment; every figure verifiable on the full report."""
    if not groups:
        return (
            "<div class=panel><h2>WBS breakdown</h2><p class=muted>This schedule has no "
            "schedulable activities to break down by WBS.</p></div>"
        )
    completion_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{g.total}</td><td>{g.completed}</td>"
        f"<td>{g.not_completed}</td><td>{g.percent_complete:g}%</td>"
        f"<td>{g.completed_ahead}</td><td>{g.completed_on_schedule}</td><td>{g.completed_behind}</td>"
        f"<td>{_num(g.avg_days_ahead)}</td><td>{_num(g.avg_days_late)}</td>"
        f"<td>{_num(g.avg_completion_variance)}</td>"
        f"<td>{g.longer_than_planned}</td><td>{g.shorter_than_planned}</td>"
        f"<td>{_num(g.duration_ratio_min)}</td><td>{_num(g.duration_ratio_avg)}</td>"
        f"<td>{_num(g.duration_ratio_max)}</td></tr>"
        for g in groups
    )
    es_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{_num(g.spi_t)}</td>"
        f"<td>{_num(g.earned_schedule_days)}</td><td>{_num(g.actual_time_days)}</td>"
        f"<td>{g.completed}/{g.total}</td></tr>"
        for g in groups
    )
    return f"""
<div class=panel><h2>Completion metrics by WBS &mdash; {len(groups)} groups</h2>
<p class=muted>The reference deck's <i>Completion Metrics</i> pivot (PBIX page 8), grouped by
the top-level WBS segment: counts and completion, the ahead / on-schedule / behind split with
average calendar days, and the actual-vs-baseline duration ratio. Every figure is verifiable
on the <a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
<div style="overflow-x:auto"><table class=wbs-table>
<tr><th scope=col>WBS</th><th scope=col>Total</th><th scope=col>Done</th><th scope=col>To go</th><th scope=col>% comp</th>
<th scope=col>Ahead</th><th scope=col>On sched</th><th scope=col>Behind</th>
<th scope=col>Avg ahead</th><th scope=col>Avg late</th><th scope=col>Avg var</th>
<th scope=col>Longer</th><th scope=col>Shorter</th><th scope=col>Dur min</th><th scope=col>Dur avg</th><th scope=col>Dur max</th></tr>
{completion_rows}</table></div></div>
<div class=panel><h2>SPI(t) &amp; Earned Schedule by WBS</h2>
<p class=muted>The deck's <i>SPI and Earned Schedule</i> pivot + combo (PBIX page 9). Per WBS
group: the count-based <b>SPI(t)</b> (Earned Schedule &divide; Actual Time; &lt; 1 = behind),
the <b>Earned Schedule</b> and <b>Actual Time</b> in working days. A group with no completions
or no baseline finishes reads &mdash; (never a fabricated value).</p>
<div id=wbsChart class=chart-host></div>
<table class=wbs-table><tr><th scope=col>WBS</th><th scope=col>SPI(t)</th><th scope=col>Earned schedule (wd)</th>
<th scope=col>Actual time (wd)</th><th scope=col>Completed</th></tr>{es_rows}</table></div>
<script src="/static/wbs.js"></script>"""


def _wbs_data(groups: tuple[WBSGroup, ...]) -> dict[str, object]:
    """JSON for the SPI/Earned-Schedule combo chart: per-WBS SPI(t) + ES/AT days."""
    return {
        "groups": [
            {
                "wbs": g.wbs,
                "total": g.total,
                "completed": g.completed,
                "percent_complete": g.percent_complete,
                "spi_t": g.spi_t,
                "earned_schedule_days": g.earned_schedule_days,
                "actual_time_days": g.actual_time_days,
                "uids": list(g.uids),  # the group's activities, for the SPI-bar drill
            }
            for g in groups
        ],
    }


def _dcma_label(metric_id: str) -> str:
    """The spaced display label the operator asked for: ``DCMA01`` -> ``DCMA 01``;
    ``DCMA04_FS`` -> ``DCMA 04 FS``. Non-DCMA ids pass through unchanged."""
    if not metric_id.startswith("DCMA"):
        return metric_id
    base, _, suffix = metric_id[4:].partition("_")
    return f"DCMA {base}" + (f" {suffix.replace('_', ' ')}" if suffix else "")


def _dcma_measure(check: AuditCheck) -> str:
    """A concise measured value to sit beside the stoplight (replacing the old bar): a percentage
    with its count for population checks, the index for CPLI/BEI, a raw count otherwise."""
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"{check.value:.2f}"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return f"{pct:.1f}%  ({check.count} of {check.population})"
    if check.count:
        unit = f" {check.unit}" if check.unit and check.unit != "count" else ""
        return f"{check.count}{unit}"
    return str(check.status).title()  # e.g. the critical-path test: Pass / Fail


def _dcma_card(check: AuditCheck) -> dict[str, object]:
    """One DCMA check as Dashboard-overview JSON: the spaced label + human name, a simple measured
    value, the PASS/FAIL/NA status (the stoplight), and the help text for the hover tooltip — what
    the metric is, why it matters, the pass/fail threshold, and a pass + a fail example (operator
    request). ``status`` and ``count`` are retained for back-compatibility with existing readers."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    return {
        "label": _dcma_label(check.metric_id),
        "name": doc.name if doc else check.name,
        "status": str(check.status),
        "count": check.count,
        "value": check.value,
        "measure": _dcma_measure(check),
        "definition": doc.definition if doc else "",
        "why": doc.importance if doc else "",
        "threshold": doc.threshold if doc else "",
        "example_ok": doc.example_ok if doc else "",
        "example_fail": doc.example_fail if doc else "",
    }


def _dcma_definition_cell(metric_id: str) -> str:
    """The 'what it measures (how)' cell for a DCMA row, from the in-tool metric dictionary —
    plain-language definition + the formula/threshold, so each score is explained in place."""
    doc = METRIC_DICTIONARY.get(metric_id)
    if doc is None:
        return "<td></td>"
    return (
        f"<td class=dcma-def>{_e(doc.definition)} "
        f"<span class=muted>How: {_e(doc.formula)}</span></td>"
    )


def _dcma_metric_cell(check: AuditCheck) -> str:
    """The 'Check' cell: the metric name plus a hover/focus tooltip that explains the metric,
    its pass/fail criteria, why it matters, and what a failing value indicates (operator request).

    The tooltip is keyboard-operable (the trigger is focusable and labelled) and also carries a
    plain-text ``title=`` so the same detail is available with no CSS/JS (air-gap, a11y)."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    if doc is None:
        return f"<td>{_e(check.name)}</td>"
    display = f"{_dcma_label(check.metric_id)} — {doc.name}"
    tip_id = f"dcma-tip-{_e(check.metric_id)}"
    rich = [
        f"<b>{_e(display)}</b>",
        f"<p>{_e(doc.definition)}</p>",
        f'<p><a class=metric-info href="/help#m-{_e(check.metric_id)}">Full definition, '
        "example and decision guidance &raquo;</a></p>",
    ]
    title = f"{doc.definition}"
    threshold = doc.threshold or f"Pass criteria: {doc.formula}"
    rich.append(f"<p><b>Threshold:</b> {_e(threshold)}</p>")
    title += f" Threshold: {threshold}."
    if doc.importance:
        rich.append(f"<p><b>Why it matters:</b> {_e(doc.importance)}</p>")
        title += f" Why it matters: {doc.importance}"
    if doc.example_ok:
        rich.append(f"<p><b>Pass example:</b> {_e(doc.example_ok)}</p>")
        title += f" Pass example: {doc.example_ok}"
    if doc.example_fail:
        rich.append(f"<p><b>Fail example:</b> {_e(doc.example_fail)}</p>")
        title += f" Fail example: {doc.example_fail}"
    if doc.indicates:
        rich.append(f"<p><b>Indicates:</b> {_e(doc.indicates)}</p>")
        title += f" Indicates: {doc.indicates}"
    return (
        f"<td class=dcma-cell>"
        f'<span class=dcma-metric tabindex=0 role=button aria-describedby="{tip_id}" '
        f'title="{_e(title)}">{_e(display)} '
        f"<span class=dcma-info aria-hidden=true>&#9432;</span></span>"
        f'<div class=dcma-tip id="{tip_id}" role=tooltip>{"".join(rich)}</div></td>'
    )


def _metric_help_cell(label: str, metric_id: str, *, align: str = "left") -> str:
    """Inner HTML for a metric column header: the label plus a hover/focus call-out from the in-tool
    dictionary — what the metric is, how it's calculated, a real-world example of how it's used, and
    what it indicates. Falls back to the plain label when the metric isn't documented. Reuses the
    DCMA tooltip styling; wrap the result in a positioned cell (``<th class=metric-th>``). ``align``
    'right' anchors the pop-out to the cell's right edge so a wide table's right columns don't clip."""
    doc = field_or_metric_doc(metric_id)
    if doc is None:
        return _e(label)
    tip_id = f"mh-{_e(metric_id)}"
    tip_cls = "dcma-tip mtip mtip-right" if align == "right" else "dcma-tip mtip"
    used = doc.use_case or doc.importance
    rich = [
        f"<b>{_e(doc.name)}</b>",
        f"<p>{_e(doc.definition)}</p>",
        f"<p><b>How it&#39;s calculated:</b> {_e(doc.formula)}</p>",
    ]
    title = f"{doc.name}. {doc.definition} How it's calculated: {doc.formula}."
    if used:
        rich.append(f"<p><b>Real-world use:</b> {_e(used)}</p>")
        title += f" Real-world use: {used}"
    if doc.indicates:
        rich.append(f"<p><b>Indicates:</b> {_e(doc.indicates)}</p>")
        title += f" Indicates: {doc.indicates}"
    if doc.threshold:
        rich.append(f"<p><b>Threshold:</b> {_e(doc.threshold)}</p>")
    return (
        f'<span class="dcma-metric mhelp" tabindex=0 role=button aria-describedby="{tip_id}" '
        f'title="{_e(title)}">{_e(label)} '
        f"<span class=dcma-info aria-hidden=true>&#9432;</span></span>"
        f'<div class="{tip_cls}" id="{tip_id}" role=tooltip>{"".join(rich)}</div>'
    )


def _dcma_count_cells(check: AuditCheck) -> str:
    """The Count + '% of tasks' cells, matching how Acumen Fuse shows each metric — the raw
    count over its population plus the percentage, instead of only a pass/fail colour.

    Count-based checks show ``n of population`` and the metric's percentage; the CPLI / BEI
    index checks show the index value (no count); the pass/fail critical-path test shows neither."""
    dash = "<span class=muted>&mdash;</span>"
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"<td class=num>{dash}</td><td class=num>{round(check.value, 2)}</td>"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return (
            f"<td class=num>{check.count} <span class=muted>of {check.population}</span></td>"
            f"<td class=num>{pct:.1f}%</td>"
        )
    return f"<td class=num>{check.count}</td><td class=num>{dash}</td>"


def _status_stack(
    title: str,
    desc: str,
    segments: list[tuple[str, int, str]],
    foot: str,
    drill: list[tuple[tuple[int, ...], str]] | None = None,
) -> str:
    """A single stacked bar with a legend of labelled counts — the redesign's composition visual
    (Activity status mix; Float remaining). ``segments`` = (label, count, css-var color).

    ``drill`` (optional, parallel to ``segments``) makes a segment CLICKABLE: entry ``i`` is
    ``(activity_uids, file_key)``; a segment with a non-empty UID set + file gets the ``sf-drill``
    hook (data-uids / data-file / data-title) that ``drilldown.js`` turns into a "list the
    activities behind this segment + add columns + Excel" grid. Omit ``drill`` (default) and every
    existing caller renders byte-for-byte as before."""
    total = sum(c for _, c, _ in segments) or 1

    def _drill_attrs(i: int, label: str) -> tuple[str, str]:
        """(extra class, extra attributes) for segment/legend ``i`` when it is drillable."""
        if not drill or i >= len(drill):
            return "", ""
        uids, fkey = drill[i]
        if not uids or not fkey:
            return "", ""
        payload = ",".join(str(u) for u in uids)
        attrs = (
            f' data-uids="{_e(payload)}" data-file="{_e(fkey)}" '
            f'data-title="{_e(f"{title} — {label}")}" role="button" tabindex="0"'
        )
        return " sf-drill", attrs

    seg_html = []
    for i, (label, c, color) in enumerate(segments):
        if c <= 0:
            continue
        cls, attrs = _drill_attrs(i, label)
        tip = f"{label}: {c}" + (" — click to list the activities" if cls else "")
        seg_html.append(
            f'<span class="stack-seg{cls}" style="width:{100.0 * c / total:.3f}%;'
            f'background:var({color})" title="{_e(tip)}"{attrs}></span>'
        )
    bar = "".join(seg_html)
    legend_html = []
    for i, (label, c, color) in enumerate(segments):
        cls, attrs = _drill_attrs(i, label)
        legend_html.append(
            f'<span class="stack-key{cls}"{attrs}>'
            f'<span class="stack-dot" style="background:var({color})"></span>'
            f"{_e(label)} <b>{c}</b></span>"
        )
    legend = "".join(legend_html)
    return (
        f'<div class="panel status-stack"><h2>{_e(title)}</h2>'
        f'<p class="muted">{_e(desc)}</p>'
        f'<div class="stack-bar" role="img" aria-label="{_e(title)}">{bar}</div>'
        f'<div class="stack-legend">{legend}</div>'
        f'<div class="stack-foot">{_e(foot)}</div></div>'
    )


def _where_we_stand_header(key: str, sch: Schedule, analysis: _Analysis) -> str:
    """Chapter 01 "Where we stand" (ADR-0197): the data-driven takeaway h1 + the six-KPI strip +
    the Activity-status-mix and Float-remaining bars — every figure read from what the report
    already computed for this schedule (no CPM math added; missing inputs render as an em dash)."""
    cpm = analysis.cpm
    cal = sch.calendar
    makeup = compute_activity_makeup(sch)
    total = makeup.total or 1
    complete_pct = 100.0 * makeup.complete / total

    cpm_finish_dt = offset_to_datetime(sch.project_start, cpm.project_finish, cal)
    cpm_finish_str = _mdY(cpm_finish_dt)

    # vs-baseline finish variance — the existing forecast helper is handed the cached CPM, so no
    # second solve; planned_finish is the latest baseline finish (None when the file carries none).
    fset = compute_finish_forecasts(sch, cpm)
    if fset.planned_finish is not None:
        var_days = (cpm_finish_dt.date() - fset.planned_finish).days
        if var_days > 0:
            vs_base = f"+{var_days}d"
            base_phrase = f"{var_days} day{'s' if var_days != 1 else ''} behind the baseline finish"
        elif var_days < 0:
            vs_base = f"{var_days}d"
            n = -var_days
            base_phrase = f"{n} day{'s' if n != 1 else ''} ahead of the baseline finish"
        else:
            vs_base = "0d"
            base_phrase = "on the baseline finish"
    else:
        vs_base = "—"
        base_phrase = "with no baseline finish to compare against"

    # plan-at-DD proxy: the share of activities the baseline scheduled to be finished by the data
    # date (compute_baseline_compliance's "Forecast to be Finished"); None when the population is 0.
    plan = analysis.compliance.get("forecast_to_be_finished")
    plan_at_dd = f"{plan.value:.0f}%" if plan is not None and plan.population else None

    # critical (incomplete) on the SAME progress-aware basis as the ribbon (ch 02) and ch 11:
    # Acumen reads MS Project's STORED Critical flag, falling back to pure-logic CPM critical only
    # when the file carries no flag (_common.is_effective_critical). Reading raw tm.total_float here
    # made a progressed file show a different Critical count than every other chapter (audit M3).
    critical = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and is_effective_critical(
            t, cpm.timings[t.unique_id].total_float if t.unique_id in cpm.timings else 0
        )
    )
    data_date = _mdY(sch.status_date) if sch.status_date else "—"

    # takeaway h1 — a sentence with a number; every clause is a real figure or is omitted
    plan_clause = f" against a {plan_at_dd} baseline plan at the data date" if plan_at_dd else ""
    takeaway = f"{complete_pct:.0f}% complete{plan_clause} — computed finish {cpm_finish_str}, "
    # base_phrase / vs_base may carry an entity (&mdash;); keep the takeaway HTML-safe by escaping
    # only the parts we build from user-independent computed values (all of the above are).

    kpi = _stat_cards(
        [
            ("Activities", str(makeup.total)),
            (
                "Earned complete",
                f"{complete_pct:.0f}%" + (f" · plan {plan_at_dd}" if plan_at_dd else ""),
            ),
            ("Critical (incomplete)", str(critical)),
            ("Computed finish", cpm_finish_str),
            ("vs baseline", vs_base),
            ("Data date", data_date),
        ]
    )

    status_bar = _status_stack(
        "Activity status mix",
        "Every activity by progress state, from the file's percent-complete.",
        [
            ("Complete", makeup.complete, "--ok"),
            ("In progress", makeup.in_progress, "--warn"),
            ("Planned", makeup.planned, "--accent"),
        ],
        f"{makeup.total} activities",
    )

    # incomplete-activity float bands on the SAME progress-aware basis as the ribbon/ch 11:
    # effective total float (stored Total Slack first, else recomputed CPM float) in working days.
    # analysis.activity_rows carries the PURE-LOGIC float, which diverges on a progressed file.
    per_day = cal.working_minutes_per_day or 1
    floats: list[float] = [
        effective_total_float(t, cpm.timings[t.unique_id].total_float) / per_day
        for t in non_summary(sch)
        if t.percent_complete < 100.0 and t.unique_id in cpm.timings
    ]
    b0 = sum(1 for tf in floats if tf <= 0)
    b1 = sum(1 for tf in floats if 0 < tf <= 4)
    b2 = sum(1 for tf in floats if 4 < tf <= 9)
    b3 = sum(1 for tf in floats if tf > 9)
    float_bar = _status_stack(
        "Float remaining",
        "Incomplete activities by total-float band — how much room before a slip hits the finish.",
        [
            ("0 days", b0, "--bad"),
            ("1-4 days", b1, "--warn"),
            ("5-9 days", b2, "--accent"),
            ("10+ days", b3, "--muted"),
        ],
        f"{len(floats)} incomplete activities",
    )

    export_bar = _export_bar(f"analysis/{quote(key, safe='')}")
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}{base_phrase}.</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{status_bar}{float_bar}</div>'
        f"{export_bar}"
    )


def _analysis_body(
    key: str,
    sch: Schedule,
    analysis: _Analysis,
    target: int | None = None,
    narrative: Narrative | None = None,
    erosion_field: str | None = None,
    margin_confirmed: frozenset[int] | None = None,
) -> str:
    audit = analysis.audit
    audit_rows = "".join(
        f'<tr>{_dcma_metric_cell(c)}<td class="{_status_class(c.status)}">{_e(c.status)}</td>'
        f"{_dcma_count_cells(c)}"
        f"{_dcma_definition_cell(c.metric_id)}"
        f"<td class=muted>{_e(c.suggested_improvement)}</td></tr>"
        for c in audit.checks
    )
    findings = analysis.findings
    find_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.category)}</td>'
        f"<td>{_e(f.title)}</td><td class=muted>{_e(f.course_of_action)}</td>"
        f"<td class=cite>{_cites_cell(f)}</td></tr>"
        for f in findings
    )
    story_source = narrative if narrative is not None else analysis.narrative
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in story_source.statements)
    target_panel = _target_panel(sch, analysis, target) if target is not None else ""
    viz = f"""{target_panel}
<div class=panel><h2>Interactive analysis</h2>
{_user_tip("Click a column header to sort, use the per-column <b>Filter</b> dropdowns to scope the rows, and drag a column edge to resize it. The data columns stay locked on the left while the Gantt timeline scrolls.")}
<div id=viz data-name="{_e(key)}">
<div class="charts chart-host" id=charts></div>
<p class=muted aria-label="chart color legend" style="margin:4px 0 8px">
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--ok)"></span> pass / on time &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--warn)"></span> late / warning &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--bad)"></span> fail / missed &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--muted)"></span> not applicable</p>
<div class="viz-controls sf-freeze-bar" id=gridControls>Driving path to target UID:
<input id=targetUid type=number min=1 placeholder="UID" value="{target if target is not None else ""}">
secondary&le;<input id=secMax type=number value=10>d
tertiary&le;<input id=terMax type=number value=20>d
<button id=ganttBtn type=button>Trace</button>
<label><input id=showDone type=checkbox checked> show completed tasks</label>
<label><input id=showLinks type=checkbox checked> links</label>
<label>Tier <span id=ganttTier class=tier-filter></span></label>
<label>Scale <input id=vizZoom type=range min=0.2 max=40 step=0.05 value=8 title="pixels per day — drag to zoom both timelines (fine steps: 0.05 px/day)"></label>
<button id=fitBtn type=button title="Zoom out so the entire project fits on screen">Fit project</button>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<label>Find <input id=gridFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every task whose row contains this text"></label>
<span id=gridFindStatus class=muted aria-live=polite></span>
<label>Outline <select id=gridOutline title="Show tasks up to this outline level (like MS Project)"></select></label>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=gridBarDates type=checkbox> dates on bars</label></div>
<div id=gantt></div>
<h3>Activities &amp; Gantt <span class=muted>(add/remove columns; the right-hand timeline is
scalable — drag <b>Scale</b> to zoom (pixels/day) and scroll horizontally; red = critical,
diamonds = milestones, thin = summaries, amber line = data date; click a row to drill into its
metadata)</span></h3>
<div id=fieldToggles></div><div id=grid></div><div id=drill class=drill></div>
</div></div>
<script src="/static/app.js"></script>"""
    return f"""{_where_we_stand_header(key, sch, analysis)}
{viz}
{_scatter_panel(key, sch, analysis.cpm)}
{_float_histogram_panel(key)}
{_calendar_panel(sch)}
{_float_bands_panel(analysis)}
{_completion_panel(analysis)}
{_health_checks_panel(sch, analysis.cpm)}
{_logic_checks_panel(sch)}
{_constraint_checks_panel(sch, analysis.cpm)}
{_vertical_integration_panel(sch)}
{_schedule_variance_panel(sch)}
{_float_erosion_panel(sch, analysis.cpm, erosion_field)}
{_margin_panel(key, sch, analysis.cpm, margin_confirmed)}
<div class=panel><h2>{_e(sch.name)} &mdash; DCMA-14 audit</h2>
<p class=muted>{audit.passed} passed &middot; {audit.failed} failed &middot; {audit.not_applicable} N/A.
Each row shows the <b>count</b> and the <b>percentage</b> of its population,
not just a pass/fail colour. <b>Hover or focus a check name</b> for its definition, pass/fail
criteria, why it matters, and what it indicates; full formulas + citations are in the
<a href="/help">Metric Dictionary</a>.</p>
{_stoplight_board(audit.checks)}
<table><tr><th scope=col>Check</th><th scope=col>Status</th><th scope=col>Count</th><th scope=col>% of tasks</th>
<th scope=col>What it measures (how)</th>
<th scope=col>Suggested improvement</th></tr>{audit_rows}</table></div>
<div class=panel><h2>Risks, opportunities &amp; concerns</h2>
<table><tr><th scope=col>Severity</th><th scope=col>Type</th><th scope=col>Finding</th><th scope=col>Course of action</th><th scope=col>Citations</th></tr>
{find_rows or "<tr><td colspan=5 class=muted>No findings — schedule is well-formed.</td></tr>"}</table></div>
<div class=panel><h2>AI narrative (local, cited)</h2>
<ul class=story data-ai-endpoint="/api/ai/narrative?key={_e(quote(key))}">{story}</ul></div>
<script src="/static/ai_polish.js"></script>"""


def _brief_body(brief: DiagnosticBrief) -> str:
    """The Diagnostic Brief page: cited prose + the finish table, print-friendly."""
    parts = [
        f"<div class=panel><h2>{_e(brief.title)}</h2>",
        f"<p class=muted>Report generated on {brief.generated_on.strftime('%A, %B %d, %Y')}. "
        "Every claim carries its citation [schedule, UID, activity] — see the final "
        "section for how to verify.</p></div>",
    ]
    for section in brief.sections:
        parts.append(f"<div class=panel><h2>{_e(section.heading)}</h2>")
        for stmt in section.paragraphs:
            parts.append(f"<p>{_e(stmt.rendered())}</p>")
        if section.table is not None:
            head = "".join(f"<th scope=col>{_e(str(h))}</th>" for h in section.table.headers)
            rows = "".join(
                "<tr>"
                + "".join(f"<td>{_e('' if c is None else str(c))}</td>" for c in row)
                + "</tr>"
                for row in section.table.rows
            )
            parts.append(f"<table><tr>{head}</tr>{rows}</table>")
        parts.append("</div>")
    return "".join(parts)


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


def _cites_cell(f: Finding) -> str:
    """A findings-table citation cell: first two cited, the rest expandable in place."""
    shown = _e("; ".join(str(c) for c in f.citations[:2]))
    return _expandable_more(shown, [_e(str(c)) for c in f.citations[2:]])


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


def _risk_matrix(items: list[Finding]) -> str:
    """A 5x5 Likelihood (columns) by Impact (rows) heat-map of the risks + issues, each placed by
    its quantified scores; cells carry the conventional risk colour and the count landing there."""
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
    return (
        "<div class=panel><h2>Risk matrix &mdash; likelihood &times; impact</h2>"
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


def _risk_ranking(items: list[Finding]) -> str:
    """The risks + issues ranked by score (highest first) as labelled bars, each annotated with the
    quantified float, driving float to the target, and working-day exposure."""
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
    return (
        "<div class=panel><h2>Risk ranking &mdash; highest score first</h2>"
        "<p class=muted>Risks and issues ordered by score, with the quantified slack (total float, "
        "and driving float to the target when one is set) and the working-day schedule exposure if "
        "the item is realised.</p>"
        f"<ol class=rk-ranking>{''.join(rows)}</ol></div>"
    )


def _risks_section(title: str, lead: str, items: list[Finding], empty: str) -> str:
    body = "".join(_finding_card(f) for f in items) if items else f"<p class=muted>{empty}</p>"
    return (
        f"<div class=panel><h2>{title} <span class=muted>({len(items)})</span></h2>"
        f"<p class=muted>{lead}</p>{body}</div>"
    )


def _risks_body(
    sch: Schedule, findings: tuple[Finding, ...], narrative: Narrative, ai_key: str = ""
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

    threats = risks + issues
    matrix = _risk_matrix(threats)
    ranking = _risk_ranking(threats)

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
            "<div class=panel><h2>Recovery plan &mdash; prioritized actions</h2>"
            "<p class=muted>The highest-leverage actions to recover the plan, most severe first, "
            "each tied to the finding that motivates it.</p>"
            f"<ol class=recovery-list>{action_items}</ol></div>"
        )

    high_note = f" &mdash; {high} flagged HIGH severity" if high else ""
    summary = f"""
<div class=panel><h2>Risks, Issues &amp; Opportunities &mdash; {_e(sch.name)}</h2>
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
        )
        + _risks_section(
            "Issues (current concerns)",
            "Quality / integrity problems present right now, including manipulation signals.",
            _by_score(issues),
            "No current concerns identified in this version.",
        )
        + _risks_section(
            "Opportunities",
            "Levers to recover or improve the schedule.",
            _by_score(opps),
            "No specific opportunities surfaced from the current signals.",
        )
    )


def _export_bar(path: str, *, xlsx_id: str = "", docx_id: str = "") -> str:
    """The per-view 'download as Excel / Word' links (local files only — Law 1)."""
    a = f' id="{xlsx_id}"' if xlsx_id else ""
    b = f' id="{docx_id}"' if docx_id else ""
    return (
        f'<div class="export-bar"><a{a} href="/export/xlsx/{path}">&#11015; Excel</a>'
        f'<a{b} href="/export/docx/{path}">&#11015; Word</a></div>'
    )


# ── Executive Margin Dashboard (NASA Margin/Contingency Burn-Down + Margin Erosion Trend) ──────


def _margin_dashboard_for(st: SessionState) -> MarginDashboard:
    """Build the margin/contingency dashboard from the loaded versions (oldest -> newest), scoped to
    the active group/filter, measured to the session target milestone (else the project finish)."""
    versions: list[tuple[str, Schedule, CPMResult]] = []
    for key, raw in st.ordered_versions():
        try:
            a = st.analysis_for(key, raw)
        except CPMError:
            continue
        versions.append((raw.source_file or raw.name, st.scope(raw), a.cpm))
    return compute_margin_dashboard(
        versions,
        target_uid=st.target_uid,
        gold_rule_per_year=st.margin_rate,
        margin_uids=st.confirmed_margin_union(),
    )


def _margin_dashboard_data(d: MarginDashboard) -> dict[str, object]:
    return {
        "have_margin_tasks": d.have_margin_tasks,
        "erosion_wd_per_month": d.erosion_wd_per_month,
        "zero_margin_date": d.zero_margin_date,
        "erosion_r2": d.erosion_r2,
        "erosion_basis_wmpd": d.erosion_basis_wmpd,
        "erosion_mixed_basis": list(d.erosion_mixed_basis),
        "gold_rule_per_year": d.gold_rule_per_year,
        "months": [
            {
                "label": m.label,
                "status_date": m.status_date,
                "target_name": m.target_name,
                "target_finish": m.target_finish,
                "zero_margin_finish": m.zero_margin_finish,
                "effective_margin_wd": m.effective_margin_wd,
                "total_margin_wd": m.total_margin_wd,
                "planned_margin_wd": m.planned_margin_wd,
                "consumed_wd": m.consumed_wd,
                "consumed_pct": m.consumed_pct,
                "corrective_action": m.corrective_action,
                "margin_cd": m.margin_cd,
                "contingency_wd": m.contingency_wd,
                "total_available": m.total_available,
                "days_to_go": m.days_to_go,
                "nasa_rqmt_wd": m.nasa_rqmt_wd,
                "pct_available": m.pct_available,
                "pct_effective": m.pct_effective,
                "below_requirement": m.below_requirement,
            }
            for m in d.months
        ],
    }


def _wmpd_label(wmpd: int) -> str:
    """Human label for a working-minutes-per-day basis (480 -> '8h/day', 1440 -> '24h/day')."""
    if wmpd % 60 == 0:
        return f"{wmpd // 60}h/day"
    return f"{wmpd}-min/day"


def _margin_dashboard_header(d: MarginDashboard) -> str:
    """The data-driven takeaway + KPI strip: latest effective margin vs the NASA requirement, the
    trigger state, and the erosion projection. Every figure comes from the engine (no new math)."""
    dated = [m for m in d.months if m.status_date is not None]
    latest = dated[-1] if dated else None
    if latest is None:
        takeaway = (
            "Load monthly schedule versions (each carrying a status date) to track how schedule "
            "margin is being consumed against the plan."
        )
        return f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'

    target = latest.target_name or "the project finish"
    if not d.have_margin_tasks:
        takeaway = (
            f'No schedule-margin activity (an activity named "margin") was found in the loaded '
            f"versions, so effective margin to {target} reads 0. Name the buffer activities "
            '"…margin…" so the burn-down can measure the reserve protecting the date.'
        )
    elif latest.below_requirement:
        takeaway = (
            f"Effective margin to {target} is {latest.effective_margin_wd:g} work days as of "
            f"{_mdY(latest.status_date)} — BELOW the NASA Gold-Rule requirement of "
            f"{latest.nasa_rqmt_wd:g} — a trigger to enact contingency or buy back schedule."
        )
    else:
        takeaway = (
            f"Effective margin to {target} is {latest.effective_margin_wd:g} work days as of "
            f"{_mdY(latest.status_date)} — at or above the {latest.nasa_rqmt_wd:g}-day NASA "
            "Gold-Rule requirement."
        )
    if d.erosion_mixed_basis:
        bases = " vs ".join(_wmpd_label(w) for w in d.erosion_mixed_basis)
        takeaway += (
            f" The margin-erosion trend is not shown: the loaded versions express margin in "
            f"different work-day bases ({bases}) because the schedule calendar changed, so a "
            "single erosion rate would conflate the two — compare margin within one calendar basis."
        )
    elif d.zero_margin_date is not None and d.erosion_wd_per_month:
        takeaway += (
            f" At the current erosion of {d.erosion_wd_per_month:g} work days per month, margin "
            f"reaches zero around {_mdY(d.zero_margin_date)}."
        )
    # 50%-consumed corrective-action trigger, quoted from the handbook: "The corrective action
    # threshold is set where the margin is 50% consumed" — §7.3.3.2.3 Sufficiency of Margin
    # (printed p.324), where it is the handbook's EXAMPLE-case threshold choice (citation
    # corrected from ADR-0230's §7.3.3.1.6, ADR-0254; the flag's behavior is unchanged).
    if latest.corrective_action and latest.consumed_pct is not None:
        takeaway += (
            f" {round(100 * latest.consumed_pct)}% of the planned margin was consumed this period — "
            "at or past the 50%-consumed corrective-action threshold (the Schedule Management "
            "Handbook's example threshold, §7.3.3.2.3); enact a corrective action (watch / "
            "re-plan / re-baseline)."
        )

    trigger = "TRIGGERED" if (latest.below_requirement or latest.corrective_action) else "OK"
    consumed_txt = (
        f"{round(100 * latest.consumed_pct)}%" if latest.consumed_pct is not None else "—"
    )
    kpi = _stat_cards(
        [
            ("Effective margin (wd)", f"{latest.effective_margin_wd:g}"),
            ("Total margin (wd)", f"{latest.total_margin_wd:g}"),
            ("NASA requirement (wd)", f"{latest.nasa_rqmt_wd:g}"),
            ("Contingency (days)", str(latest.contingency_wd)),
            ("Consumed this period", consumed_txt),
            (
                "Erosion (wd/month)",
                f"{d.erosion_wd_per_month:g}" if d.erosion_wd_per_month else "—",
            ),
            ("Zero-margin date", _mdY(d.zero_margin_date) if d.zero_margin_date else "—"),
            ("Trigger for action", trigger),
        ]
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1><div class="ws-kpi">{kpi}</div>'
    )


def _margin_rate_control(rate: float) -> str:
    """F3c operator control: the NASA Gold-Rule margin-requirement rate (work-days per program year)
    the dashboard measures effective margin against. 30/yr is the Schedule Management Handbook
    default, but the handbook states margin as a program-managed guideline, so the rate is
    operator-parameterized here — a GET form persists it on the session (fail-soft on a bad value),
    and the requirement line, the per-version ``NASA rqmt`` column, the trigger, and the export all
    follow it. The verbatim 50%-consumed corrective threshold stays fixed (it is not a guideline)."""
    reset = (
        ""
        if rate == GOLD_RULE_DAYS_PER_YEAR
        else f' <a class="btn-link" href="/margin?rate={GOLD_RULE_DAYS_PER_YEAR:g}" '
        f"data-no-i18n>Reset to {GOLD_RULE_DAYS_PER_YEAR:g}</a>"
    )
    return (
        '<div class="panel"><form method="get" action="/margin" class="viz-controls">'
        "<label data-no-i18n>NASA Gold-Rule margin requirement: "
        f'<input name="rate" type="number" min="1" max="365" step="0.5" value="{rate:g}" '
        'title="Work-days of margin per program year the requirement expects '
        '(days-to-go x rate / 365)"> work-days / program year</label> '
        '<button type="submit">Apply</button>'
        f"{reset}"
        '<p class="muted" data-no-i18n style="margin:.4em 0 0;font-size:12px">The NASA requirement '
        "line is <b>days-to-go &times; rate &divide; 365</b>. <b>30</b>/yr is the Schedule Management "
        "Handbook &ldquo;Gold Rule&rdquo; default; a program may set a different guideline, so the "
        "rate is parameterized here &mdash; the burn-down requirement line, the per-version "
        "<i>NASA&nbsp;rqmt</i> column, the trigger flag, and the Excel/Word export all follow it.</p>"
        "</form></div>"
    )


def _band_payload(st: SessionState, d: MarginDashboard) -> dict[str, object] | None:
    """The Fig 5-30 guideline-band overlay for the burn-down chart + table (ADR-0254), or ``None``
    when the operator has not entered the phase dates (the band is simply absent — never derived).

    Evaluates the stepped band at every dated version's status date plus the phase boundaries;
    classifies each dated month via :func:`band_position`. Month verdicts are SUPPRESSED (None)
    when the versions mix work-day bases — comparing one band against two different "work day"
    units would conflate them, the same refusal the erosion fit makes (disclosed, not fabricated).
    """
    if st.margin_band_dates is None:
        return None
    try:
        cfg = GuidelineBandConfig(
            phase_dates=(
                dt.date.fromisoformat(st.margin_band_dates[0]),
                dt.date.fromisoformat(st.margin_band_dates[1]),
                dt.date.fromisoformat(st.margin_band_dates[2]),
                dt.date.fromisoformat(st.margin_band_dates[3]),
            ),
            rates=st.margin_band_rates,
        )
    except ValueError:
        return None  # fail-soft: a corrupted stored config renders no band, never a wrong one
    dated = [(m.status_date, m.effective_margin_wd) for m in d.months if m.status_date]
    points = expected_margin_band(cfg, tuple(dt.date.fromisoformat(s) for s, _ in dated))
    by_date: dict[str, BandPoint] = {p.date.isoformat(): p for p in points}
    mixed = bool(d.erosion_mixed_basis)
    months = []
    for iso, eff in dated:
        p = by_date[iso]
        months.append(
            {
                "date": iso,
                "low_wd": p.low_wd,
                "high_wd": p.high_wd,
                "position": None if mixed else band_position(eff, p.low_wd, p.high_wd),
            }
        )
    return {
        "points": [
            {"date": p.date.isoformat(), "low_wd": p.low_wd, "high_wd": p.high_wd} for p in points
        ],
        "months": months,
        "mixed_basis": mixed,
        "dates": list(st.margin_band_dates),
        "rates": [list(r) for r in st.margin_band_rates],
        "month_work_days": MONTH_WORK_DAYS,
    }


def _margin_band_control(st: SessionState) -> str:
    """The Fig 5-30 guideline-band operator control (F3c-fuller, ADR-0254): the three verbatim
    handbook rows beside editable (low, high) wd/yr rates, the four phase-boundary date inputs
    (program facts — never auto-filled), and the §7.3.3.2.3 Watch / Corrective-Action percentile
    thresholds. Every default is cited; the conversion convention is stated on the panel."""
    dts = st.margin_band_dates or ("", "", "", "")
    date_labels = (
        "Confirmation Review",
        "Start of Integration &amp; Test",
        "Delivery to Launch Site",
        "Launch",
    )
    date_inputs = " ".join(
        f'<label data-no-i18n>{lbl} <input type=date name=phase{i} value="{_e(dts[i])}"></label>'
        for i, lbl in enumerate(date_labels)
    )
    rate_rows = "".join(
        f"<tr><td class=muted data-no-i18n>{_e(frm)} &rarr; {_e(to)}</td>"
        f"<td class=muted data-no-i18n>&ldquo;{_e(amount)}&rdquo;</td>"
        f'<td><input type=number name=low{i} min=1 max=365 step=0.5 value="{st.margin_band_rates[i][0]:g}" style="width:5em">'
        f' &ndash; <input type=number name=high{i} min=1 max=365 step=0.5 value="{st.margin_band_rates[i][1]:g}" style="width:5em"> wd/yr</td></tr>'
        for i, (frm, to, amount) in enumerate(FIG_5_30_ROWS)
    )
    watch, ca = st.margin_risk_pcts
    return f"""
<div class=panel><h2 data-no-i18n>Expected margin &mdash; Figure 5-30 guideline band</h2>
<p class=muted data-no-i18n>The NASA SMH's "Established standards for margin allocation" (Figure 5-30,
&sect;5.5.11.2) give per-phase margin <b>rate ranges</b> &mdash; each explicitly "Varies" (program-defined).
Enter the program's phase-boundary dates to draw the stepped expected-margin band on the burn-down
(&sect;7.3.3.1.6, Fig 7-32: "stepped burndowns that mimic the margin guidelines over time"). Rates are
editable; the prefills convert the handbook ranges at the tool's disclosed convention
<b>1 month = {MONTH_WORK_DAYS:g} work days</b> (the ADR-0230/0253 Gold-Rule reading; row 3 lists three
alternatives &mdash; the prefill spans their extremes). A month below the band is flagged as a
<b>guideline deviation</b> (&sect;7.3.3.1.6 Thresholds: deviations "trigger a requirement for either an
explanation&hellip; or&hellip; activities to mitigate the trend" &mdash; thresholds themselves are program-set
in the SMP).</p>
<form method=post action="/margin/band" class=viz-controls>
<table class=card-table><tr><th scope=col>Phase (Fig 5-30)</th><th scope=col>Handbook amount (verbatim)</th><th scope=col>Rate (wd / program year)</th></tr>
{rate_rows}</table>
<p style="margin:.5em 0 0">{date_inputs}</p>
<p style="margin:.5em 0 0" data-no-i18n><label>Watch percentile <input type=number name=watch_pct min=1 max=99 step=1 value="{watch:g}" style="width:4em">%</label>
<label>Corrective-Action percentile <input type=number name=ca_pct min=1 max=99 step=1 value="{ca:g}" style="width:4em">%</label>
<span class=muted>(the handbook's <i>example</i> thresholds &mdash; Fig 7-45 prose / &sect;7.3.3.2.1; program-set per the SMP)</span></p>
<p style="margin:.5em 0 0"><button type=submit name=action value=apply>Apply band</button>
<button type=submit name=action value=clear>Clear</button></p>
</form></div>"""


def _margin_risk_panel(st: SessionState) -> str:
    """The §7.3.3.2.3 risk-based margin-sufficiency panel shell (F3c tier-b, ADR-0254). The SRA
    run is OFF the page-load path — clicking the button fetches ``/api/margin/risk`` (the repo's
    SRA doctrine); the shell only carries the cited explanation and the result container."""
    watch, ca = st.margin_risk_pcts
    return f"""
<div class=panel><h2 data-no-i18n>Risk-based margin sufficiency (SRA)</h2>
<p class=muted data-no-i18n>&sect;7.3.3.2.3 (Sufficiency of Margin): "using a stochastic tracking curve
takes the results from a routine SRA and plots the results against organizational margin
requirements." Runs the seeded SSI SRA (same engine and inputs as the Risk Analysis page), then reads
the finish distribution against the deterministic margin window &mdash; the all-ML finish <b>D</b> and
the same solve with the margin activities zeroed <b>E</b>. The <b>covered percentile</b> is the fraction
of simulated finishes the margin absorbs; it is classified against the operator thresholds
(Watch {watch:g}% / Corrective {ca:g}% &mdash; the handbook's <i>example</i> values, editable above).
Note: the simulation carries the margin activities in-network at their plan durations (the handbook's
Fig 7-43 curves are "Current Plan, Zero Margin, With Risks" &mdash; a zero-margin run is a documented
follow-up); duration uncertainty and risks come from the Risk Analysis page inputs.</p>
<p><button type=button id=marginRiskRun>Run margin-sufficiency SRA</button>
<span id=marginRiskStatus class=muted aria-live=polite></span></p>
<div id=marginRisk></div></div>"""


def _margin_dashboard_body(st: SessionState) -> str:
    """The Margin Dashboard page: the takeaway + KPI header, the operator rate control (F3c), the
    Fig 5-30 band control + risk-sufficiency panel (F3c-fuller, ADR-0254), the two reference charts
    (burn-down + erosion trend), the per-version table, and the embedded dataset
    margin_dashboard.js reads."""
    d = _margin_dashboard_for(st)
    data = _margin_dashboard_data(d)
    data["band"] = _band_payload(st, d)
    blob = json.dumps(data).replace("<", "\\u003c")

    def _row(m: MarginMonth) -> str:
        pct = f"{100 * m.pct_available:.1f}%" if m.pct_available is not None else "—"
        sd = _mdY(m.status_date) if m.status_date else "—"
        planned = f"{m.planned_margin_wd:g}" if m.planned_margin_wd is not None else "—"
        consumed = f"{m.consumed_wd:g}" if m.consumed_wd is not None else "—"
        trig = "&#9888; trigger" if m.below_requirement else "ok"
        corr = "&#9888; 50%+" if m.corrective_action else "—"
        return (
            f"<tr{' class=below' if m.below_requirement else ''}><td>{_e(sd)}</td>"
            f"<td class=num>{planned}</td>"
            f"<td class=num>{m.effective_margin_wd:g}</td>"
            f"<td class=num>{m.total_margin_wd:g}</td>"
            f"<td class=num>{consumed}</td>"
            f"<td class=num>{m.contingency_wd}</td>"
            f"<td class=num>{m.total_available:g}</td>"
            f"<td class=num>{m.nasa_rqmt_wd:g}</td>"
            f"<td class=num>{m.days_to_go}</td>"
            f"<td class=num>{pct}</td><td>{corr}</td><td>{trig}</td></tr>"
        )

    rows = "".join(_row(m) for m in d.months)
    r2 = d.erosion_r2
    fit = f" (R&sup2; {r2:.2f})" if r2 is not None else ""
    return (
        _margin_dashboard_header(d)
        + _export_bar("margin")
        + _margin_rate_control(st.margin_rate)
        + _margin_band_control(st)
        + '<div class="panel"><h2 data-no-i18n>Margin &amp; Contingency Burn-Down</h2>'
        + _margin_terminology()
        + '<p class="muted" data-no-i18n>Per status date: effective schedule <b>margin</b> (work days) '
        "stacked with <b>contingency</b> (weekends + holidays to the target), against the NASA "
        "Gold-Rule requirement line. A red bar is a month where margin has fallen below the "
        "requirement &mdash; the trigger for action. The dashed <b>planned</b> line traces the "
        "period-start margin carried forward; a &#9650; marker flags a month where half or more of "
        "the planned margin was consumed (the 50%-consumed corrective-action threshold &mdash; the "
        "Schedule Management Handbook's <i>example</i> threshold, &sect;7.3.3.2.3; thresholds are "
        "program-set in the SMP). <b>Total margin</b> (sum of the "
        "margin activities&rsquo; durations) and <b>effective margin</b> (the buffer on the driving "
        "chain) can differ &mdash; both are reported.</p>"
        '<div class="chart-host" id="marginBurndownChart"></div></div>'
        '<div class="panel"><h2 data-no-i18n>Margin Erosion Trend (MET)</h2>'
        f'<p class="muted" data-no-i18n>Effective margin (work days) over the status dates with a '
        f"least-squares erosion line extrapolated to zero{fit}. The projected zero-margin date is "
        "the honest linear read of the current trend, not a commitment.</p>"
        '<div class="chart-host" id="marginErosionChart"></div></div>'
        + _margin_risk_panel(st)
        + '<div class="panel"><h2 data-no-i18n>Per-version figures</h2>'
        "<table><tr><th scope=col>Status date</th><th scope=col>Planned (wd)</th>"
        "<th scope=col>Effective (wd)</th><th scope=col>Total (wd)</th><th scope=col>Consumed</th>"
        "<th scope=col>Contingency</th><th scope=col>Total avail.</th>"
        "<th scope=col>NASA rqmt (wd)</th><th scope=col>Days-to-go</th>"
        "<th scope=col>% available</th><th scope=col>Corrective</th><th scope=col>Trigger</th></tr>"
        f"{rows or '<tr><td colspan=12 class=muted>No dated versions loaded.</td></tr>'}</table></div>"
        f'<script type="application/json" id=marginDashData>{blob}</script>'
        '<script src="/static/margin_dashboard.js"></script>'
    )


def _analysis_data(sch: Schedule, analysis: _Analysis) -> dict[str, object]:
    audit = analysis.audit
    compliance = analysis.compliance
    return {
        "name": sch.name,
        "source_file": sch.source_file,
        "tasks": len(sch.tasks),
        "status_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "calendar": {
            "name": sch.calendar.name,
            "working_minutes_per_day": sch.calendar.working_minutes_per_day,
            "work_weekdays": list(sch.calendar.work_weekdays),
            "holidays": [d.isoformat() for d in sch.calendar.holidays],
        },
        # every named calendar in the file — the Timescale dialog's Non-working-time tab lets
        # the operator pick which calendar's weekends/holidays to shade on the Gantt
        "calendars": [
            {
                "name": c.name,
                "work_weekdays": list(c.work_weekdays),
                "holidays": [d.isoformat() for d in c.holidays],
            }
            for c in sch.calendars
        ],
        "dcma": {c.metric_id: _dcma_card(c) for c in audit.checks},
        "baseline_compliance": {k: v.count for k, v in compliance.items()},
        "float_bands": {
            k: {"count": v.count, "population": v.population, "value": v.value}
            for k, v in analysis.float_bands.items()
        },
        "completion": {
            k: {"count": v.count, "population": v.population, "value": v.value, "unit": v.unit}
            for k, v in analysis.completion.items()
        },
        "activities": analysis.activity_rows,
        # the schedule's mapped .mpp custom/extended fields (declared order) -> optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
        "findings": [
            {
                "severity": str(f.severity),
                "category": str(f.category),
                "title": f.title,
                "citations": [
                    {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                    for c in f.citations
                ],
            }
            for f in analysis.findings
        ],
    }


def _iso_date(value: object) -> str:
    return value.date().isoformat() if hasattr(value, "date") else ""


def _activity_rows(sch: Schedule, cpm: CPMResult) -> list[dict[str, object]]:
    """Per-activity rows for the interactive grid + Gantt (float in days, citable metadata).

    Scheduled activities carry their CPM floats; WBS summary rows (which the CPM excludes)
    are included too so the Gantt reads like the source plan, with null floats. Every row also
    carries the FULL Task-Information payload (operator 2026-07-10, ADR-0183): actuals,
    constraint + deadline, work/cost, predecessors/successors with type + lag, resource
    assignments with units/work, the task note, and the mode flags — everything MS Project's
    Task Information dialog shows, so the row-click popup never has to guess.
    """
    by_id = sch.tasks_by_id
    per_day = sch.calendar.working_minutes_per_day or 480
    res_by_id = {r.unique_id: r for r in sch.resources}
    # Each task's GOVERNING calendar name, so the Gantt can shade non-working time per the
    # calendar that task actually runs on (ADR-0243): a 24-hour task shows no weekend gray, a
    # Mon-Fri task still does. A task with no own calendar inherits the project calendar (MSP
    # semantics). The name matches one registered client-side by `SFTimescale.setCalendars`.
    _cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
    _proj_cal_name = sch.calendar.name

    def _task_calendar_name(task: Task) -> str:
        uid = task.calendar_uid
        if uid is not None and uid in _cal_name_by_uid:
            return _cal_name_by_uid[uid]
        return _proj_cal_name

    preds: dict[int, list[dict[str, object]]] = {}
    succs: dict[int, list[dict[str, object]]] = {}
    for rel in sch.relationships:
        lag_days = round(rel.lag_minutes / per_day, 1)
        p_t = by_id.get(rel.predecessor_id)
        s_t = by_id.get(rel.successor_id)
        preds.setdefault(rel.successor_id, []).append(
            {
                "uid": rel.predecessor_id,
                "name": p_t.name if p_t else "",
                "type": rel.type.value,
                "lag_days": lag_days,
            }
        )
        succs.setdefault(rel.predecessor_id, []).append(
            {
                "uid": rel.successor_id,
                "name": s_t.name if s_t else "",
                "type": rel.type.value,
                "lag_days": lag_days,
            }
        )
    # file order (the task list order MS Project displays) so the Gantt nests parents above
    # their children regardless of UID numbering; the indent itself comes from outline_level.
    order = {t.unique_id: i for i, t in enumerate(sch.tasks)}

    def _days(minutes: int | None) -> float | None:
        return None if minutes is None else round(minutes / per_day, 2)

    def _row(task: Task) -> dict[str, object]:
        assignments = []
        for a in task.resource_assignments:
            res = res_by_id.get(a.resource_id)
            assignments.append(
                {
                    "resource": res.name if res else f"Resource {a.resource_id}",
                    "units": a.units,
                    "work_days": _days(a.work_minutes),
                    "remaining_work_days": _days(a.remaining_work_minutes),
                }
            )
        return {
            "unique_id": task.unique_id,
            "name": task.name,
            "wbs": task.wbs or "",
            "start": _iso_date(task.start),
            "finish": _iso_date(task.finish),
            "baseline_start": _iso_date(task.baseline_start),
            "baseline_finish": _iso_date(task.baseline_finish),
            "actual_start": _iso_date(task.actual_start),
            "actual_finish": _iso_date(task.actual_finish),
            "deadline": _iso_date(task.deadline),
            "constraint_type": task.constraint_type.value,
            "constraint_date": _iso_date(task.constraint_date),
            "duration_days": round(
                task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
            ),
            "remaining_duration_days": _days(task.remaining_duration_minutes),
            "baseline_duration_days": _days(task.baseline_duration_minutes),
            "work_days": _days(task.work_minutes),
            "actual_work_days": _days(task.actual_work_minutes),
            "cost": task.cost,
            "actual_cost": task.actual_cost,
            "budgeted_cost": task.budgeted_cost,
            "percent_complete": task.percent_complete,
            "physical_percent_complete": task.physical_percent_complete,
            "complete": task.is_complete or task.actual_finish is not None,
            "is_milestone": task.is_milestone,
            "is_summary": task.is_summary,
            "is_manual": task.is_manual,
            "is_active": task.is_active,
            "is_estimated_duration": task.is_estimated_duration,
            "duration_is_elapsed": task.duration_is_elapsed,
            "outline_level": task.outline_level,
            "order": order[task.unique_id],
            "calendar": _task_calendar_name(task),
            "resource_names": ", ".join(task.resource_names),
            "assignments": assignments,
            "predecessors": preds.get(task.unique_id, []),
            "successors": succs.get(task.unique_id, []),
            "notes": task.notes,
            "source_file": sch.source_file,
            # mapped .mpp custom/extended fields populated on this task (label -> value); the
            # grid offers each as an optional column (ADR-0088 mapping -> ADR-0093 display)
            "custom": dict(task.custom_field_map),
        }

    rows: list[dict[str, object]] = []
    for fr in analyze_floats(sch, cpm):
        task = by_id[fr.unique_id]
        row = _row(task)
        row["is_summary"] = False
        row["total_float_days"] = float(fr.total_float_days)
        row["free_float_days"] = float(fr.free_float_days)
        # progress-aware effective critical (stored flag first, ADR-0150) — what MS Project
        # shows; the pure-logic fr.is_critical collapses on a progressed file
        row["is_critical"] = is_effective_critical(task, float(fr.total_float_days) * per_day)
        rows.append(row)
    for task in sch.tasks:
        if not task.is_summary:
            continue
        row = _row(task)
        row["total_float_days"] = None
        row["free_float_days"] = None
        row["is_critical"] = False
        rows.append(row)
    rows.sort(key=lambda r: cast(int, r["order"]))
    return rows


def _driving_data(
    sch: Schedule,
    cpm: CPMResult,
    target: int,
    secondary: int,
    tertiary: int,
    *,
    direction: str = "predecessors",
    range_mode: str = "all",
    range_days: int = 0,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
    with_drag: bool = False,
) -> dict[str, object]:
    """Driving-slack rows for the Gantt — tier + CPM ordinal positions for each traced UID.

    SSI Directional Path Tool options (operator 2026-07-08): ``direction`` traces
    predecessors / successors / both; ``range_mode`` "slack" keeps only rows with driving
    slack <= ``range_days`` (SSI "Get dependencies with Driving Slack <= x"), "all" keeps the
    full trace; ``ignore_constraints`` / ``ignore_leveling`` mirror SSI's same-named options —
    stored dates still govern dated tasks (a fully-dated file traces identically; the flags
    reach only the CPM fallback for undated tasks and the calendar basis — ADR-0251);
    ``with_drag`` adds Devaux DRAG (SSI-validated, test_ssi_drag_exact) per path activity.
    The payload always carries ``parallel_paths`` — the on-path set decomposed into its
    parallel branches — so the client can render the SSI "Separate parallel paths" output.
    Defaults reproduce the original behavior byte-for-byte."""
    by_id = sch.tasks_by_id
    # per-task governing calendar name for per-row non-working shading (ADR-0243)
    _cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
    _proj_cal_name = sch.calendar.name
    if target not in by_id:
        return {
            "target_uid": target,
            "target_name": None,
            "rows": [],
            "note": f"UID {target} is not in this schedule.",
        }
    if by_id[target].is_summary:
        # summary rollups are not in the logic network — tracing one raised before
        return {
            "target_uid": target,
            "target_name": by_id[target].name,
            "rows": [],
            "note": f"UID {target} is a summary rollup — pick one of its activities instead.",
        }
    try:
        dir_enum = PathDirection(direction)
    except ValueError:
        dir_enum = PathDirection.PREDECESSORS
    results = compute_driving_slack(
        sch,
        target_uid=target,
        secondary_max_days=secondary,
        tertiary_max_days=tertiary,
        cpm_result=cpm,
        direction=dir_enum,
        ignore_constraints=ignore_constraints,
        ignore_leveling_delay=ignore_leveling,
    )
    if range_mode == "slack":
        keep = {
            uid
            for uid, r in results.items()
            if uid == target or int(r.driving_slack_days) <= max(0, range_days)
        }
        results = {uid: r for uid, r in results.items() if uid in keep}
    drag_by_uid: dict[int, object] = {}
    if with_drag:
        from schedule_forensics.engine.drag import compute_drag

        drag_by_uid = {uid: float(d.drag_days) for uid, d in compute_drag(sch, results).items()}
    cal = sch.calendar
    per_day = cal.working_minutes_per_day
    # display the AS-SCHEDULED stored-date axis the slack math runs on — pure CPM
    # timings pack real files' completed work at the project start (wrong bars/dates)
    basis_start, basis_finish = date_basis(sch, cpm)
    date_driven = set(cpm.date_driven)

    def day(ordinal: int | None) -> str | None:
        if ordinal is None:
            return None
        return offset_to_datetime(sch.project_start, max(ordinal, 0), cal).date().isoformat()

    # Driving links: each traced activity's immediate logic successors that are themselves on the
    # trace to the target — the "what is this linked to on the way to the target" detail (e.g.
    # UID 8022 → UID 152). on_path marks the successor that keeps the chain on the 0-slack path.
    trace_ids = set(results)
    drives: dict[int, list[dict[str, object]]] = {uid: [] for uid in trace_ids}
    for rel in sch.relationships:
        if rel.predecessor_id in trace_ids and rel.successor_id in trace_ids:
            drives[rel.predecessor_id].append(
                {
                    "uid": rel.successor_id,
                    "type": rel.type.value,
                    "lag_days": round(rel.lag_minutes / per_day, 1) if per_day else 0.0,
                    "on_path": results[rel.successor_id].on_driving_path,
                }
            )

    rows = []
    for uid in sorted(results):
        timing = cpm.timings.get(uid)
        task = by_id[uid]
        start_ord = basis_start.get(uid, timing.early_start if timing else None)
        finish_ord = basis_finish.get(uid, timing.early_finish if timing else None)
        if task.start is not None and task.finish is not None:
            # the same stored-or-CPM split date_basis() makes; stored dates render
            # verbatim (an actual start may legally predate the project start)
            start_iso: str | None = task.start.date().isoformat()
            finish_iso: str | None = task.finish.date().isoformat()
        else:
            start_iso, finish_iso = day(start_ord), day(finish_ord)
        rows.append(
            {
                "unique_id": uid,
                "name": task.name,
                "wbs": task.wbs or "",
                "tier": str(results[uid].tier),
                "driving_slack_days": int(results[uid].driving_slack_days),
                "on_driving_path": results[uid].on_driving_path,
                "calendar": (
                    _cal_name_by_uid.get(task.calendar_uid, _proj_cal_name)
                    if task.calendar_uid is not None
                    else _proj_cal_name
                ),
                "start_ord": start_ord,
                "finish_ord": finish_ord,
                "start": start_iso,
                "finish": finish_iso,
                "baseline_finish": _iso_date(task.baseline_finish),
                "duration_days": round(
                    task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
                )
                if per_day
                else 0.0,
                "total_float_days": (
                    float(round(timing.total_float / per_day, 1)) if timing else None
                ),
                "percent_complete": task.percent_complete,
                # robust "complete" for the hide-completed toggles: a real .mpp/.xer may
                # report a done activity at 99.x% while carrying an actual finish — treat
                # an actual finish (or >=100%) as complete so the toggle never misses it.
                "complete": task.is_complete or task.actual_finish is not None,
                "is_milestone": task.is_milestone,
                "date_driven": uid in date_driven,
                "drag_days": drag_by_uid.get(uid),
                "resource_names": ", ".join(task.resource_names),
                # immediate logic successors within this trace (uid, type, lag, on_path) — the
                # "linked to UID X" detail surfaced by the Drives → column
                "drives": drives[uid],
                # mapped custom fields populated on this task (label → value); the grid offers
                # each as an optional column (ADR-0088 mapping → ADR-0093 display)
                "custom": dict(task.custom_field_map),
            }
        )
    # waterfall order: earliest finish first, so the chain cascades to the target's finish
    rows.sort(key=lambda r: (r["finish_ord"] is None, r["finish_ord"], r["start_ord"]))
    # the trace is logic-only by definition: say how much of the schedule it covers, so
    # absent (e.g. unlinked completed) work reads as explained, not missing
    activities = sum(1 for t in sch.tasks if not t.is_summary)
    coverage = (
        f"{len(rows)} of the schedule's {activities} activities have a logic path to this target"
    )
    driven_in_trace = sum(1 for r in rows if r["date_driven"])
    if driven_in_trace:
        coverage += f"; {driven_in_trace} traced date(s) are not supported by logic (see report)"
    # SSI "Separate parallel paths": decompose the on-path set into serial branches — a new
    # branch starts wherever a path task is not the single continuation of the previous one
    path_set = {uid for uid, r in results.items() if r.on_driving_path}
    succ_in_path: dict[int, list[int]] = {u: [] for u in path_set}
    pred_in_path: dict[int, list[int]] = {u: [] for u in path_set}
    for rel2 in sch.relationships:
        if rel2.predecessor_id in path_set and rel2.successor_id in path_set:
            succ_in_path[rel2.predecessor_id].append(rel2.successor_id)
            pred_in_path[rel2.successor_id].append(rel2.predecessor_id)
    ordered_path = [u for u in topo_order(sch, path_set)]
    visited: set[int] = set()
    branches: list[list[int]] = []
    for u in ordered_path:
        if u in visited:
            continue
        chain = [u]
        visited.add(u)
        cur = u
        while True:
            nxt = [x for x in succ_in_path.get(cur, ()) if x not in visited]
            if len(nxt) == 1 and len(pred_in_path.get(nxt[0], ())) <= 1:
                cur = nxt[0]
                chain.append(cur)
                visited.add(cur)
            else:
                break
        branches.append(chain)
    parallel_paths = [
        {"label": f"Path 01 ({i})", "uids": chain} for i, chain in enumerate(branches, 1)
    ]

    return {
        "target_uid": target,
        "target_name": by_id[target].name,
        "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "coverage": coverage,
        # the schedule's mapped custom fields (declared order) → optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
        "rows": rows,
        "parallel_paths": parallel_paths,
    }


def _integrity_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target_uid: int | None,
    *,
    baseline_idx: int,
    comparison_idx: int,
) -> str:
    """Schedule Integrity & Change Forensics: cited manipulation findings for ONE chosen version
    pair + the counterfactual finish.

    The operator picks exactly TWO files to compare (baseline A vs comparison B) — previously the
    page diffed EVERY consecutive pair, which on many large files ran a counterfactual CPM sweep
    per pair and, if any single pair produced an unsolvable revert, 500'd the whole page. Now one
    pair is analyzed at a time and every heavy compute is guarded, so it never crashes."""
    n = len(schedules)
    labels = [sch.source_file or sch.name for sch in schedules]
    # resolve the chosen pair; default to the two most recent (what changed last). Order prior ->
    # current chronologically (schedules are oldest-first) regardless of pick order, and never let
    # the two collapse to the same file. The baseline guard must also catch an OUT-OF-RANGE index
    # (e.g. comparison_idx==0 makes cur-1 == -1): a negative base would wrap to schedules[-1], the
    # NEWEST file, and silently render a chronologically REVERSED diff (Law 2 fidelity bug) — so we
    # re-pick an in-range neighbour whenever base is out of range or equal to cur.
    cur = comparison_idx if 0 <= comparison_idx < n else n - 1
    base = baseline_idx if 0 <= baseline_idx < n else cur - 1
    if base == cur or not (0 <= base < n):
        base = cur - 1 if cur > 0 else cur + 1
    prior_idx, cur_idx = (base, cur) if base < cur else (cur, base)

    def _file_opts(selected: int) -> str:
        return "".join(
            f'<option value="{i}"{" selected" if i == selected else ""}>{_e(lb)}</option>'
            for i, lb in enumerate(labels)
        )

    banner_name = f"{labels[prior_idx]} → {labels[cur_idx]}"
    picker = (
        f"<label>Baseline (A) <select name=a>{_file_opts(prior_idx)}</select></label>"
        f"<label>Comparison (B) <select name=b>{_file_opts(cur_idx)}</select></label>"
        if n > 2
        else f'<input type=hidden name=a value="{prior_idx}"><input type=hidden name=b value="{cur_idx}">'
    )
    two_note = (
        "<p class=muted>Pick the <b>two</b> versions to compare — A (baseline) vs B (comparison). "
        "The analysis runs on that one pair.</p>"
        if n > 2
        else ""
    )
    controls = f"""
<div class=panel><div class=integrity-file data-no-i18n>{_e(banner_name)}</div>
<p class=muted>Every statement below is engine-computed and cited (file + UniqueID + task) —
version-over-version changes and what each change did to the critical / driving path. This is
analysis for review, not an accusation: each finding's course of action asks the analyst to
confirm the change was authorized.</p>
{two_note}
<form method=get action=/integrity class=viz-controls>
{picker}
<button type=submit>Apply</button>
<a class=btn-link href="/export/xlsx/integrity?file={_e(labels[cur_idx])}">&#11015; Excel (all findings)</a>
</form></div>"""

    sections: list[str] = []
    pairs = [(prior_idx, schedules[prior_idx], schedules[cur_idx], cpms[prior_idx], cpms[cur_idx])]
    for i, prior, current, pcpm, ccpm in pairs:
        cur_i = (
            cur_idx  # section header uses the actual comparison index (pairs are not consecutive)
        )
        try:
            findings = detect_manipulation(current, prior, current_cpm=ccpm, prior_cpm=pcpm)
        except (CPMError, ValueError, KeyError) as exc:  # never 500 the page on one bad pair
            logging.getLogger("schedule_forensics").warning("integrity findings failed: %s", exc)
            findings = ()
        rows = ""
        findings_data: list[dict[str, object]] = []  # per-finding full citation UIDs for the drill
        for f in findings:
            cites = "; ".join(
                f"UID {c.unique_id} — {c.task_name}" for c in f.citations[:4] if c.unique_id
            )
            uids = [c.unique_id for c in f.citations if c.unique_id]
            fi = len(findings_data)
            findings_data.append({"title": f.title, "uids": uids})
            # clickable "view all N" opens a full, columnable, exportable chart of every cited
            # activity below the table (operator 2026-07-08) — no more truncated "(+66 more)".
            more = (
                f' <a href="#" class=cite-more data-finding="{fi}" '
                f'title="List all {len(uids)} cited activities in a chart you can add columns to '
                f'and export">(+{len(f.citations) - 4} more — view all {len(uids)})</a>'
                if len(f.citations) > 4
                else ""
            )
            rows += (
                f"<tr>"
                f'<td class="sev-{_e(f.severity)}">{_e(f.severity)}</td>'
                f"<td>{_e(f.title)}</td>"
                f"<td>{_e(f.detail)}</td>"
                f"<td class=muted>{_e(f.course_of_action)}</td>"
                f"<td class=cite>{_e(cites)}{more}</td></tr>"
            )
        findings_blob = json.dumps({"file": labels[cur_idx], "findings": findings_data}).replace(
            "<", "\\u003c"
        )
        findings_drill = (
            "<div id=findingsDrill class=findings-drill></div>"
            f'<script type="application/json" id=findingsData>{findings_blob}</script>'
            '<script src="/static/findings_drill.js"></script>'
            if findings_data
            else ""
        )
        # Per-change effect (operator 2026-07-08): revert EACH detected change one at a time and
        # re-run CPM to show its isolated working-day effect on the chosen target UID (or, when no
        # target is set, the last task on the critical path). This catches changes the path
        # counterfactual below misses — e.g. a removed predecessor link whose endpoints STAYED
        # critical (the 188→187 case), which nonetheless moves the target's finish.
        effects_html = ""
        try:
            eff = compute_change_effects(prior, current, ccpm, target_uid=target_uid)
        except (
            CPMError,
            ValueError,
            KeyError,
        ) as exc:  # defense in depth; the engine already guards
            logging.getLogger("schedule_forensics").warning("change effects failed: %s", exc)
            eff = None
        if eff is not None and (eff.per_change or eff.skipped_unsolvable or eff.skipped_capped):
            tgt_label = f"UID {eff.target_uid} ({_e(eff.target_name)})" + (
                " — the last task on the critical path" if eff.target_is_last_critical else ""
            )
            n_measured = len(eff.per_change)
            partial = bool(eff.skipped_unsolvable or eff.skipped_capped)
            # disclose any reverts we could not measure (Law 2: no silent drop)
            notes = []
            if eff.skipped_unsolvable:
                notes.append(
                    f"{eff.skipped_unsolvable} change(s) could not be measured individually — "
                    "reverting one alone reintroduces a logic cycle."
                )
            if eff.skipped_capped:
                cap_note = (
                    f"{eff.skipped_capped} further change(s) beyond the first {n_measured} were "
                    "not individually measured (large diff)."
                )
                if eff.skipped_capped_artifacts:
                    cap_note += (
                        f" {eff.skipped_capped_artifacts} of them match the MS Project "
                        "reschedule-artifact pattern (SNET stamped at the data date on an "
                        "incomplete task) — artifacts are measured last, so the cap starves "
                        "statusing noise, not deliberate changes."
                    )
                notes.append(cap_note)
            skip_note = f"<p class=muted>{' '.join(_e(x) for x in notes)}</p>" if notes else ""
            if not eff.per_change:
                # every detected revert was skipped — disclose it instead of hiding the panel
                total_skipped = eff.skipped_unsolvable + eff.skipped_capped
                effects_html = f"""
<div class=change-effects><h4>Effect of each change on {tgt_label}</h4>
<p class=muted>{total_skipped} change(s) were detected between these versions but none could be
measured individually — reverting any one alone reintroduces a logic cycle. (Currently
{_e(eff.target_name)} finishes {_e(eff.actual_target_finish)}.)</p>{skip_note}</div>"""
            else:

                def _eff_rows(changes: list[ChangeEffect]) -> str:
                    out = ""
                    for e in sorted(changes, key=lambda ce: -abs(ce.target_finish_delta_days)):
                        d = e.target_finish_delta_days
                        cls = "fail" if d > 0 else "ok" if d < 0 else "muted"
                        effect_txt = (
                            f"<b class={cls}>{d:+d} wd</b>"
                            if d
                            else "<span class=muted>no effect</span>"
                        )
                        cites = ", ".join(f"UID {u}" for u in e.citation_uids)
                        out += (
                            f"<tr><td>{_e(e.label)}</td><td>{effect_txt}</td>"
                            f"<td>{'+' if e.project_finish_delta_days > 0 else ''}"
                            f"{e.project_finish_delta_days} wd</td>"
                            f"<td class=cite>{_e(cites)}</td></tr>"
                        )
                    return out

                # MS Project "reschedule uncompleted work" stamps an SNET constraint at the data
                # date on every incomplete task it pushes — dozens of REAL (never hidden) but
                # tool-generated constraint rows. Cluster them under an explanatory collapsible
                # so they don't read as deliberate manual constraint edits (operator 2026-07-09).
                artifacts = [e for e in eff.per_change if e.is_reschedule_artifact]
                genuine = [e for e in eff.per_change if not e.is_reschedule_artifact]
                eff_rows = _eff_rows(genuine)
                artifact_html = ""
                n_art_total = len(artifacts) + eff.skipped_capped_artifacts
                if artifacts:
                    n_noeff = sum(1 for e in artifacts if not e.target_finish_delta_days)
                    art_note = (
                        f"{n_art_total} constraint change(s) look like the MS Project "
                        "&ldquo;reschedule uncompleted work&rdquo; statusing artifact: the later "
                        "version carries a Start-No-Earlier-Than constraint stamped exactly at "
                        "its own data date. MS Project writes these automatically when "
                        "incomplete work is pushed past the status date &mdash; they are real "
                        "file differences, but usually a statusing side effect rather than "
                        "manual constraint edits. "
                        f"{n_noeff} of {len(artifacts)} have no effect on the target finish."
                    )
                    if eff.skipped_capped_artifacts:
                        art_note += (
                            f" {eff.skipped_capped_artifacts} further artifact-pattern change(s) "
                            "were detected but not individually measured (measurement cap; see "
                            "the note above) and are not in the table below."
                        )
                    artifact_html = f"""
<details class=artifact-cluster><summary>&#9432; {n_art_total} MS Project reschedule
artifact(s) &mdash; SNET stamped at the data date (click to expand)</summary>
<p class=muted>{art_note}</p>
<table class=integrity-table><tr><th scope=col>Change (reverted)</th>
<th scope=col>Effect on target finish</th><th scope=col>Effect on project finish</th>
<th scope=col>Citations</th></tr>{_eff_rows(artifacts)}</table></details>"""
                agg = eff.aggregate_target_finish_delta_days
                agg_txt = (
                    f"<b class={'fail' if agg > 0 else 'ok' if agg < 0 else 'muted'}>{agg:+d} "
                    f"working day(s)</b>"
                )
                # "all changes together" line — the aggregate folds in ONLY the individually-
                # measured reverts, so state that count honestly and, when any change was skipped/
                # capped, say the total EXCLUDES them rather than over-claiming "every change".
                scope_txt = (
                    f"the {n_measured} individually-measured change(s) reverted together (the "
                    "skipped change(s) noted below are excluded)"
                    if partial
                    else f"all {n_measured} change(s) reverted together"
                )
                agg_line = (
                    f" With {scope_txt}, {_e(eff.target_name)} would move {agg_txt} (currently "
                    f"{_e(eff.actual_target_finish)})."
                    if eff.aggregate_solved
                    else f" (Currently {_e(eff.target_name)} finishes "
                    f"{_e(eff.actual_target_finish)}; reverting these changes together would "
                    "reintroduce a logic cycle, so only the per-change effects above are shown.)"
                )
                main_table = (
                    "<table class=integrity-table><tr><th scope=col>Change (reverted)</th>"
                    "<th scope=col>Effect on target finish</th>"
                    "<th scope=col>Effect on project finish</th>"
                    f"<th scope=col>Citations</th></tr>{eff_rows}</table>"
                    if eff_rows
                    else "<p class=muted>Every change between these versions is an MS Project "
                    "reschedule artifact (see below).</p>"
                )
                effects_html = f"""
<div class=change-effects><h4>Effect of each change on {tgt_label}</h4>
<p class=muted>For each change below, the tool reverts <b>only that change</b> on the later version
and re-runs CPM. A <b class=fail>positive</b> value is the working-day slip the change
<b>hid</b> from the target's finish (restoring it would push the finish out that far); a
<b class=ok>negative</b> value means the change pushed the finish out.{agg_line}</p>{skip_note}
{main_table}{artifact_html}</div>"""
        cf_html = ""
        try:
            cf = compute_path_counterfactual(prior, current, pcpm, ccpm, target_uid=target_uid)
        except (CPMError, ValueError, KeyError) as exc:
            logging.getLogger("schedule_forensics").warning("path counterfactual failed: %s", exc)
            cf = None
        if cf is not None and cf.reverted:
            delta_txt = (
                f" — <b class=fail>{cf.finish_delta_days} working day(s)</b> of apparent"
                " recovery came from the changes themselves, not from performed work"
                if cf.finish_delta_days > 0
                else ""
            )
            reverted = ", ".join(str(r.uid) for r in cf.reverted[:12])
            tgt = ""
            if cf.target_uid is not None and cf.target_counterfactual_finish:
                tgt = (
                    f"<p>Target UID {cf.target_uid} ({_e(cf.target_name or '')}): would have"
                    f" finished <b>{_e(cf.target_counterfactual_finish)}</b> instead of"
                    f" <b>{_e(cf.target_actual_finish or '?')}</b>.</p>"
                )
            cf_html = f"""
<div class=counterfactual><h4>Counterfactual — without these changes</h4>
<p>Activities left the critical/driving path after their own duration / logic / constraints
changed (UIDs {_e(reverted)}). Reverting exactly those changes and re-running CPM: the project
finish would have been <b>{_e(cf.counterfactual_finish)}</b> instead of the reported
<b>{_e(cf.actual_finish)}</b>{delta_txt}.</p>{tgt}</div>"""
        empty = (
            "<p class=muted>No manipulation-pattern findings between these two versions.</p>"
            if not rows
            else ""
        )
        sections.append(f"""
<div class=panel><h2>{_e(labels[i])} &rarr; {_e(labels[cur_i])}</h2>
{f"<table class=integrity-table><tr><th scope=col>Severity</th><th scope=col>Finding</th><th scope=col>Detail</th><th scope=col>Course of action</th><th scope=col>Citations</th></tr>{rows}</table>" if rows else empty}
{findings_drill}
{effects_html}
{cf_html}</div>""")

    if not sections:
        sections.append(
            "<div class=panel><p class=muted>No version pair matches the selected file.</p></div>"
        )
    return controls + "".join(sections)


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
    prior: Schedule, current: Schedule, prior_cpm: CPMResult, current_cpm: CPMResult
) -> str:
    manip = detect_manipulation(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    trend = trend_across_versions([prior, current])
    impact = compute_net_finish_impact(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    days = int(impact.value)
    if days < 0:
        impact_html = (
            f"<p>Net Finish Impact: <b class=fail>{days} calendar days</b> "
            "&mdash; the project finish moved later since the prior version.</p>"
        )
    elif days > 0:
        impact_html = (
            f"<p>Net Finish Impact: <b class=pass>+{days} calendar days</b> "
            "&mdash; the project finish moved earlier since the prior version.</p>"
        )
    else:
        impact_html = (
            "<p>Net Finish Impact: <b class=pass>0 calendar days</b> "
            "&mdash; the project finish is unchanged.</p>"
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
    return f"""
<div class=panel><h2>Version trend &mdash; {_e(prior.source_file or "prior")} &rarr; {_e(current.source_file or "current")}</h2>
<p class=muted>Versions are ordered by data date (oldest first); the trend reads prior &rarr; current.</p>
<table><tr><th scope=col>Version</th><th scope=col>Project finish</th><th scope=col class=metric-th>{_metric_help_cell("Completed", "completed")}</th><th scope=col class=metric-th>{_metric_help_cell("In progress", "in_progress")}</th><th scope=col class=metric-th>{_metric_help_cell("Critical", "critical")}</th></tr>{trend_rows}</table>
{impact_html}</div>
<div class=panel><h2>Manipulation-trend signals</h2>
<table><tr><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
{manip_rows or "<tr><td colspan=3 class=muted>No manipulation signals detected (honest progress).</td></tr>"}</table></div>"""


def _focus_rows(
    schedules: list[Schedule], cpms: list[CPMResult], target: int
) -> list[tuple[str, str, str]]:
    """Per version: (label, the focus UID's computed finish date, % complete) — '—' if absent."""
    rows: list[tuple[str, str, str]] = []
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        timing = cpm.timings.get(target)
        task = sch.tasks_by_id.get(target)
        if timing is None or task is None:
            rows.append((label, "—", "—"))
            continue
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
        rows.append((label, finish.date().isoformat(), f"{task.percent_complete:g}%"))
    return rows


def _focus_panel(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
    title = f"Focus activity UID {target}" + (f" &mdash; {_e(names[0])}" if names else "")
    focus_rows = _focus_rows(schedules, cpms, target)
    rows = "".join(
        # focus_rows keeps ISO (the movement math below parses it); format at render only
        f"<tr><td>{_e(label)}</td><td>{_e(_mdY(finish))}</td><td>{_e(pct)}</td></tr>"
        for label, finish, pct in focus_rows
    )
    note = "" if names else '<p class="notice err">No loaded version contains that UniqueID.</p>'
    known = [finish for _, finish, _ in focus_rows if finish != "—"]
    movement = ""
    if len(known) >= 2:
        # same sign convention as Net Finish Impact: negative == moved later (a slip)
        days = (dt.date.fromisoformat(known[0]) - dt.date.fromisoformat(known[-1])).days
        cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
        movement = (
            f"<p>Computed finish moved <b class={cls}>{days:+d} calendar days</b> "
            f"({word}) between the first and last version that schedule it.</p>"
        )
    return f"""
<div class=panel><h2>{title}</h2>{note}
<p class=muted>The focus activity's computed finish and progress across the versions
(its movement is charted below).</p>
<table><tr><th scope=col>Version</th><th scope=col>Computed finish</th><th scope=col>% complete</th></tr>{rows}</table>
{movement}</div>"""


def _how_it_moved_header(schedules: list[Schedule], cpms: list[CPMResult]) -> str:
    """Chapter 05 "How it moved" (ADR-0202): the data-driven takeaway + a slippage KPI strip
    + the update-behaviour and work-status bars, from the per-version trend the page already
    tabulates (trend_across_versions) and the latest version's activity makeup (no new math)."""
    points = trend_across_versions(schedules, cpms)
    n_ver = len(points)
    updates = n_ver - 1
    moves = [
        (points[i].project_finish.date() - points[i - 1].project_finish.date()).days
        for i in range(1, n_ver)
    ]
    net = (points[-1].project_finish.date() - points[0].project_finish.date()).days
    slipped = sum(1 for m in moves if m > 0)
    improved = sum(1 for m in moves if m < 0)
    held = updates - slipped - improved
    biggest = max(moves, key=abs) if moves else 0
    latest = points[-1]
    makeup = compute_activity_makeup(schedules[-1])

    def _cal(n: int) -> str:
        return f"{abs(n)} calendar day" + ("" if abs(n) == 1 else "s")

    if net > 0:
        moved = f"slipped {_cal(net)}"
    elif net < 0:
        moved = f"pulled in {_cal(net)}"
    else:
        moved = "held steady"
    upd = f"update{'s' if updates != 1 else ''}"
    takeaway = (
        f"Across {n_ver} versions the finish {moved} — {slipped} of {updates} {upd} slipped it "
        f"— and the current forecast finish is {_mdY(latest.project_finish)}."
    )

    kpi = _stat_cards(
        [
            ("Versions compared", str(n_ver)),
            ("Current finish", _mdY(latest.project_finish)),
            ("Net finish move", f"{net:+d} d" if net else "0 d"),
            ("Updates that slipped", f"{slipped} / {updates}"),
            ("Biggest single move", f"{biggest:+d} d" if biggest else "0 d"),
            ("Critical now", str(latest.critical)),
        ]
    )
    behaviour = _status_stack(
        "Update behaviour",
        "How each update moved the forecast finish vs the version before it.",
        [("Slipped", slipped, "--bad"), ("Held", held, "--muted"), ("Improved", improved, "--ok")],
        f"over {updates} {upd}",
        # (no drill — these segments count version-to-version updates, not activities)
    )
    # the "Where the work stands" segments DO map to activity sets — partition the latest version's
    # non-summary tasks by percent-complete, exactly as compute_activity_makeup counts them.
    latest_sch = schedules[-1]
    ns = non_summary(latest_sch)
    fkey = latest_sch.source_file or latest_sch.name
    complete_uids = tuple(sorted(t.unique_id for t in ns if t.percent_complete >= 100.0))
    inprog_uids = tuple(sorted(t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0))
    planned_uids = tuple(sorted(t.unique_id for t in ns if t.percent_complete <= 0.0))
    work = _status_stack(
        "Where the work stands",
        f"Activity status in the newest version — {latest.source_file or 'latest'}.",
        [
            ("Complete", makeup.complete, "--ok"),
            ("In progress", makeup.in_progress, "--accent"),
            ("Not started", makeup.planned, "--muted"),
        ],
        f"{makeup.total} activities in scope",
        drill=[(complete_uids, fkey), (inprog_uids, fkey), (planned_uids, fkey)],
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{behaviour}{work}</div>'
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
    )


def _trend_body(schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None) -> str:
    """The multi-version trend view: table, quality-trend sentences, pairwise signals, charts."""
    points = trend_across_versions(schedules, cpms)
    trend_rows = "".join(
        f"<tr><td>{_e(p.source_file or p.version_index)}</td>"
        f"<td>{_e(p.status_date.date()) if p.status_date else '-'}</td>"
        f"<td>{_e(p.project_finish.date())}</td>"
        f"<td>{p.completed}</td><td>{p.in_progress}</td><td>{p.critical}</td></tr>"
        for p in points
    )
    quality_items = "".join(
        f"<li>{_e(t.sentence())}</li>" for t in compute_quality_trend(schedules, cpms)
    )
    impact = compute_net_finish_impact(
        schedules[-1], schedules[0], current_cpm=cpms[-1], prior_cpm=cpms[0]
    )
    days = int(impact.value)
    cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
    signal_rows: list[str] = []
    # each signal's cited activities, embedded so the operator can drill into the tasks behind a
    # finding (UID/name/duration/%/start/finish + add columns + Excel) — reuses findings_drill.js
    # with a PER-FINDING file (a signal cites its own version: deletions cite the prior, most
    # others cite the current).
    signal_findings: list[dict[str, object]] = []
    for i in range(len(schedules) - 1):
        prior, current = schedules[i], schedules[i + 1]
        p_label = prior.source_file or prior.name
        c_label = current.source_file or current.name
        step = f"{_e(p_label)} &rarr; {_e(c_label)}"
        for f in detect_manipulation(current, prior, current_cpm=cpms[i + 1], prior_cpm=cpms[i]):
            task_cites = [c for c in f.citations if c.unique_id > 0]
            cite_file = next((c.source_file for c in task_cites if c.source_file), None)
            signal_cell = _e(f.title)
            if task_cites and cite_file:
                fi = len(signal_findings)
                signal_findings.append(
                    {
                        "title": f"{f.title} — {p_label} → {c_label}",
                        "file": cite_file,
                        "uids": [c.unique_id for c in task_cites],
                    }
                )
                n = len(task_cites)
                signal_cell = (
                    f"{_e(f.title)} "
                    f'<a class=cite-more data-finding="{fi}">'
                    f"(view {n} task{'s' if n != 1 else ''})</a>"
                )
            signal_rows.append(
                f'<tr><td>{step}</td><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td>'
                f"<td>{signal_cell}</td><td class=muted>{_e(f.course_of_action)}</td></tr>"
            )
    signals_blob = json.dumps({"findings": signal_findings}).replace("<", "\\u003c")
    focus_panel = _focus_panel(schedules, cpms, target) if target is not None else ""
    focus_form = f"""
<div class=panel><form method=get action=/trend class=viz-controls>
Focus the trend on a specific activity &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{'<a class=btn-link href="/trend?target=">clear focus</a>' if target is not None else ""}
</form></div>"""
    return f"""
<div class=panel><h2>Version trend &mdash; {len(schedules)} versions, oldest first (by data date)</h2>
{_user_tip("Load two or more versions (oldest first by data date) to see how the finish, criticality and schedule quality move over time &mdash; a finish that keeps sliding right is the classic bow-wave signature.")}
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>Project finish</th>
<th scope=col class=metric-th>{_metric_help_cell("Completed", "completed")}</th>
<th scope=col class=metric-th>{_metric_help_cell("In progress", "in_progress")}</th>
<th scope=col class=metric-th>{_metric_help_cell("Critical", "critical")}</th></tr>{trend_rows}</table>
<p>Net Finish Impact across the series: <b class={cls}>{days:+d} calendar days</b>
&mdash; the project finish moved {word} between the first and last version.</p></div>
{focus_form}{focus_panel}
<div class=panel><h2>Trend charts</h2><div id=trendCharts class="charts chart-host"
data-target="{target if target is not None else ""}"></div></div>
<div class=panel id=qualDrillPanel><h2>Quality drill-down &amp; animation</h2>
<p class=muted>Step through the versions (oldest first) and watch the count of <b>offending
activities</b> for each schedule-quality metric move on a <b>locked axis</b> &mdash; bar
heights stay comparable frame to frame, so a metric that worsens stands out. Pick a metric to
list the exact activities behind its number in the current version (the drill-down).</p>
<div class=viz-controls>
<label>Metric <select id=qualMetric></select></label>
<button id=qualPrev type=button>&#9664; Prev</button>
<span id=qualLabel class=muted></span>
<button id=qualNext type=button>Next &#9654;</button>
<button id=qualPlay type=button>&#9654; Auto-play</button>
</div>
<div class=qual-drill-grid>
<div id=qualBars class=qual-bars></div>
<div id=qualDrill class=qual-offenders></div>
</div></div>
<div class=panel><h2>Schedule-quality trends</h2>
<p class=muted>How each schedule-quality metric moves across the versions.</p>
<ul>{quality_items}</ul></div>
<div class=panel><h2>Manipulation-trend signals (consecutive versions)</h2>
<p class=muted>Each signal with cited activities is a <b>view N tasks</b> link &mdash; click it to
list the exact activities behind that finding (UID / name / duration / % complete / start /
finish), add any standard or custom field, filter, and export to Excel.</p>
<table><tr><th scope=col>Step</th><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
{"".join(signal_rows) or "<tr><td colspan=4 class=muted>No manipulation signals detected across the series (honest progress).</td></tr>"}</table>
<div id=findingsDrill class=findings-drill></div>
<script type="application/json" id=findingsData>{signals_blob}</script>
<script src="/static/findings_drill.js"></script></div>
<div class=panel><h2>Schedule margin burndown</h2>
<p class=muted>Tracks <b>total</b> vs <b>effective</b> margin &mdash; the buffer protecting the project
finish &mdash; across submissions, so margin erosion (a buffer being spent or quietly removed) is
visible at a glance.</p>
<div class="chart-host" id=marginBurndown></div></div>
<script src="/static/trend.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/margin.js"></script>"""


def _trend_data(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    analyses: list[_Analysis],
    target: int | None = None,
) -> dict[str, object]:
    """JSON for the trend charts: per-version headline numbers + quality-metric series.

    The ``analyses`` are pre-computed (cached) _Analysis objects parallel to schedules/cpms.
    Extended in ADR-0039 to carry per-version cross-file comparison and float-analysis data
    for the PBIX page 4+5 charts rendered by trend.js.
    """
    points = trend_across_versions(schedules, cpms)
    focus: dict[str, object] | None = None
    if target is not None:
        finishes: list[str | None] = []
        percents: list[float | None] = []
        for sch, cpm in zip(schedules, cpms, strict=True):
            timing = cpm.timings.get(target)
            task = sch.tasks_by_id.get(target)
            if timing is None or task is None:
                finishes.append(None)
                percents.append(None)
            else:
                fin = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
                finishes.append(fin.date().isoformat())
                percents.append(task.percent_complete)
        names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
        focus = {
            "uid": target,
            "name": names[0] if names else None,
            "finishes": finishes,
            "percents": percents,
        }

    # HMI and CEI are period-over-period (each version scored against the previous version's data
    # date), so they are computed once across the ordered series and indexed per version (first =
    # None). HMI is baseline-anchored; CEI is forecast-anchored (prior forecast vs current actuals).
    hmi_series = compute_hmi_trend(schedules)
    cei_series = compute_cei_trend(schedules)
    # Float Ratio is single-snapshot; the trend scores each version and carries the period-over-period
    # delta (this minus prior) so the chart reads as a period-to-period series (ADR-0103).
    float_ratio_series = compute_float_ratio_trend(schedules, cpms)
    version_rows: list[dict[str, object]] = []
    for i, (p, sch, cpm, an) in enumerate(zip(points, schedules, cpms, analyses, strict=True)):
        makeup = compute_activity_makeup(sch)
        cp = an.completion
        fb = an.float_bands
        fs = compute_float_sums(sch, cpm)
        # BEI lives in the DCMA14 check (metric_id="DCMA14")
        bei_chk = next((c for c in an.audit.checks if c.metric_id == "DCMA14"), None)
        bei: float | None = bei_chk.value if (bei_chk and bei_chk.population) else None
        mei_r = cp["mei"]
        epi_r = cp["epi"]
        sfr_r = cp["start_finish_ratio"]
        # FEI (to-go forecast execution) + BRI (baseline realism) — single-snapshot (ADR-0100)
        fei = compute_fei(sch)
        bri_r = compute_bri(sch)
        # SVt (Earned-Schedule time variance, working days) per version — the SV/SVt trend (D4)
        svt = compute_schedule_variance(sch, non_summary(sch)).svt_days
        # the activity ids behind each stacked-bar segment, so the trend bars can drill (same
        # predicates as compute_activity_makeup / completion_performance / the float bands)
        ns = non_summary(sch)
        status_uids = {
            "complete_uids": [t.unique_id for t in ns if t.percent_complete >= 100.0],
            "in_progress_uids": [t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0],
            "planned_uids": [t.unique_id for t in ns if t.percent_complete <= 0.0],
        }
        makeup_uids = {
            "milestones_uids": [t.unique_id for t in ns if t.is_milestone],
            "normal_uids": [t.unique_id for t in ns if not t.is_milestone],
            "summaries_uids": [t.unique_id for t in sch.tasks if t.is_summary and t.unique_id != 0],
        }
        version_rows.append(
            {
                "label": p.source_file or f"v{p.version_index + 1}",
                # a resolvable schedule key for the bar drill (the label may be a synthetic "v3")
                "file": sch.source_file or sch.name,
                "status_date": p.status_date.date().isoformat() if p.status_date else None,
                "finish": p.project_finish.date().isoformat(),
                "completed": p.completed,
                "in_progress": p.in_progress,
                "critical": p.critical,
                # SVt (Earned-Schedule time variance, working days; None when undefined) — SV/SVt trend
                "svt_days": svt,
                # PBIX p4 — Cross File Comparison
                "makeup": {
                    "milestones": makeup.milestones,
                    "normal": makeup.normal,
                    "summaries": makeup.summaries,
                    **makeup_uids,
                },
                "status_split": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                    **status_uids,
                },
                "completion_perf": {
                    "ahead": cp["completed_ahead"].count,
                    "on_schedule": cp["completed_on_schedule"].count,
                    "behind": cp["completed_behind"].count,
                    "ahead_uids": list(cp["completed_ahead"].offender_uids),
                    "on_schedule_uids": list(cp["completed_on_schedule"].offender_uids),
                    "behind_uids": list(cp["completed_behind"].offender_uids),
                },
                "indices": {
                    "mei": mei_r.value if mei_r.population else None,
                    "bei": bei,
                    "epi": epi_r.value if epi_r.population else None,
                    "sfr": sfr_r.value if sfr_r.population else None,
                    # HMI / CEI (period-over-period): None on the first version (no predecessor)
                    "hmi_tasks": hmi_series.task_values[i],
                    "hmi_milestones": hmi_series.milestone_values[i],
                    "cei_tasks": cei_series.task_values[i],
                    "cei_milestones": cei_series.milestone_values[i],
                    "cei_starts": cei_series.start_values[i],
                    "cei_critical": cei_series.critical_values[i],
                    "cei_adjusted": cei_series.adjusted_values[i],
                    # FEI / BRI (single-snapshot, baseline-anchored)
                    "fei_starts": fei["fei_starts"].value if fei["fei_starts"].population else None,
                    "fei_finish": fei["fei_finish"].value if fei["fei_finish"].population else None,
                    "bri": bri_r.value if bri_r.population else None,
                    # Float Ratio (single-snapshot; the delta is period-over-period)
                    "float_ratio": float_ratio_series.values[i],
                    "float_ratio_aggregate": float_ratio_series.aggregate_values[i],
                    "float_ratio_delta": float_ratio_series.deltas[i],
                },
                # PBIX p5 — Float Analysis
                "float_sums": {
                    "total_days": fs.total_days,
                    "free_days": fs.free_days,
                },
                "float_bands": {
                    k: {"count": v.count, "pct": round(v.value, 1), "uids": list(v.offender_uids)}
                    for k, v in fb.items()
                },
            }
        )

    # Per-metric drill-down (M18 item 8): every §A quality metric carries, per version,
    # the offending activities (UID + name) behind the trended number — the data the
    # drill-down/animation panel steps through. Names resolve against each version's own
    # task map (an activity can change name between versions). No cap (Law 1, local).
    by_id_per_version = [s.tasks_by_id for s in schedules]
    quality: dict[str, object] = {}
    for t in compute_quality_trend(schedules, cpms):
        offenders_per_version = [
            [
                {"uid": uid, "name": by_id_per_version[vi][uid].name}
                for uid in offs
                if uid in by_id_per_version[vi]
            ]
            for vi, offs in enumerate(t.offenders_by_version)
        ]
        quality[t.metric_id] = {
            "name": t.name,
            "values": list(t.values),
            "lower_is_better": t.lower_is_better,
            "worst_index": t.worst_index,
            "counts": [len(offs) for offs in t.offenders_by_version],
            "offenders": offenders_per_version,
        }
    return {"target": focus, "versions": version_rows, "quality": quality}


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
    planned = latest.cei_planned or 0
    finished = latest.cei_finished or 0

    # the latest version's finish placement on the shared month axis, split at the data date
    si = latest.status_index
    if si is not None:
        landed = sum(latest.scheduled[: si + 1])
        ahead = sum(latest.scheduled[si + 1 :])
    else:
        landed, ahead = sum(latest.scheduled), 0

    def _fin(x: int) -> str:
        return f"{x} finish" if x == 1 else f"{x} finishes"

    if cei is not None and latest.cei_period:
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
            ("Planned that month", str(planned) if latest.cei_planned is not None else "—"),
            (
                "Finished that month",
                str(finished) if latest.cei_finished is not None else "—",
            ),
            ("Months under plan", f"{under} / {len(scored)}" if scored else "—"),
        ]
    )
    month_bar = _status_stack(
        "Latest scored month",
        f"Plan vs done in {latest.cei_period or 'the latest period'} — the CEI numerator and denominator.",
        [("Finished", finished, "--ok"), ("Short of plan", max(planned - finished, 0), "--bad")],
        f"{planned} planned in the month",
    )
    pile_bar = _status_stack(
        "Where the finishes sit",
        f"The newest version's finish months, split at the data date — {latest.label}.",
        [("Landed by the data date", landed, "--ok"), ("Piled ahead of it", ahead, "--warn")],
        f"{landed + ahead} finishes across {len(wave.month_labels)} months",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{month_bar}{pile_bar}</div>'
    )


def _cei_body(
    wave: BowWave, target_uid: int | None = None, track_uids: list[int] | None = None
) -> str:
    """The Bow Wave / CEI view: per-snapshot animated chart + the CEI summary table."""
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
    return f"""
<div class=panel><h2>Bow Wave &mdash; Activity Finishes by month</h2>
<p class=muted>Gold = baselined to finish, blue = scheduled to finish, green = actually
finished; the dashed line is the snapshot's data date. Work that keeps sliding right shows
as a swelling wave of blue just past each data date. Step through the snapshots or press
Auto-play to watch the wave move. Tick <b>Running totals</b> for the cumulative finish curves,
focus a <b>Target UID</b> to mark where that activity lands (and slides) in each snapshot, and
<b>Track UIDs</b> (up to 20, comma-separated) to watch specific activities ride the wave.</p>
<form method=get action=/cei class=viz-controls>
<label>Target UID <input name=target type=number min=1 value="{target_uid if target_uid is not None else ""}"
placeholder="UID"></label>
<label>Track UIDs <input id=ceiTrack name=uids data-no-i18n value="{_e(track_txt)}"
placeholder="e.g. 155, 187, 411" size=28
title="Up to 20 UniqueIDs (comma/space separated) marked on every snapshot of the animation — independent of the primary target"></label>
<button type=submit>Focus</button>
{'<a class=btn-link href="/cei?target=">clear focus</a>' if target_uid is not None else ""}</form>
<div class=viz-controls>
<button id=prevSnap type=button>&#9664; Prev</button>
<span id=snapLabel class=muted></span>
<button id=nextSnap type=button>Next &#9654;</button>
<button id=autoPlay type=button>&#9654; Auto-play</button>
<label><input id=ceiTotals type=checkbox> Running totals (cumulative)</label>
</div>
<div id=ceiChart class=chart-host></div></div>
<div class=panel><h2>CEI &mdash; Current Execution Index</h2>
<p class=muted>For each snapshot: of the activities the <i>previous</i> snapshot planned to
finish in the following month, how many this snapshot re-scheduled for that month and how
how many of those planned activities actually finished by the end of it. CEI = completed-on-time &divide; previously planned (1.00 = executed to plan; an unplanned finish in the month earns no credit).</p>
<table><tr><th scope=col>Snapshot</th><th scope=col>Period</th><th scope=col>Previously planned</th><th scope=col>Re-scheduled</th>
<th scope=col>Actually finished</th><th scope=col>CEI</th></tr>{rows}</table></div>
<script src="/static/cei.js"></script>"""


def _scurve_filter_fields(versions: list[Schedule]) -> dict[str, list[str]]:
    """The parent file(s)' filterable fields → their distinct values, for the S-curve's own
    up-to-5-field filter. Capped so the embedded payload stays small on large schedules."""
    out: dict[str, list[str]] = {}
    for fld in available_fields_union(versions):
        values = distinct_values(versions, fld)
        if 0 < len(values) <= 1000:
            out[fld] = values[:300]
    return out


def _pair_criteria(cf: list[str], cv: list[str], versions: list[Schedule]) -> list[Criterion]:
    """Zip the cf/cv query lists into validated (field, value) criteria (<= MAX_FIELDS)."""
    fields = set(available_fields_union(versions))
    out: list[Criterion] = []
    for fld, value in zip(cf, cv, strict=False):
        if fld in fields and value:
            out.append((fld, value))
        if len(out) >= MAX_FIELDS:
            break
    return out


def _scurve_interpretation(sc: SCurve) -> str:
    """A grounded, always-present plain-English read of the S-curve: plan-vs-actual at the data
    date and how that gap is trending across versions — what the trend says about execution."""
    versions = sc.versions
    if not versions:
        return ""
    latest = versions[-1]
    si = latest.status_index
    if si is None or si >= len(latest.planned):
        read = (
            "This version has no data date, so plan-vs-actual can't be read at a status point; "
            "the curves show how the planned and scheduled finishes are distributed over time."
        )
    else:
        actual, planned = latest.actual[si], latest.planned[si]
        gap = planned - actual
        if gap > 2:
            verdict = f"running <b>{gap:.0f} points behind plan</b> at the data date"
            health = (
                "Execution is lagging the baseline — less work has completed than was promised "
                "by now, so the forecast finish is at risk unless the team recovers."
            )
        elif gap < -2:
            verdict = f"running <b>{-gap:.0f} points ahead of plan</b> at the data date"
            health = "Execution is ahead of the baseline — work is completing faster than planned."
        else:
            verdict = "tracking <b>on plan</b> at the data date"
            health = "Execution is essentially on the baseline at the status date."
        read = (
            f"As of the latest data date, <b>{actual:.0f}%</b> of the work has finished versus "
            f"<b>{planned:.0f}%</b> planned — {verdict}. {health}"
        )
    gaps = [
        v.planned[v.status_index] - v.actual[v.status_index]
        for v in versions
        if v.status_index is not None and v.status_index < len(v.planned)
    ]
    trend = ""
    if len(gaps) >= 2:
        delta = gaps[-1] - gaps[0]
        if delta > 1:
            trend = (
                f" Across the loaded versions the gap has <b>widened by {delta:.0f} points</b> — "
                "the schedule is falling further behind."
            )
        elif delta < -1:
            trend = (
                f" Across the loaded versions the gap has <b>narrowed by {-delta:.0f} points</b> — "
                "the team is recovering."
            )
        else:
            trend = " The plan-vs-actual gap has held roughly steady across the loaded versions."
    return (
        "<div class=panel><h2>AI interpretation</h2>"
        f"<p>{read}{trend}</p>"
        "<p class=muted><b>Auto-generated</b> from the S-curve's computed values &mdash; verify "
        'against the chart. Enable a local model in <a href="/settings">AI Settings</a> for a '
        "fuller, model-written read.</p></div>"
    )


def _scurve_body(
    sc: SCurve, fields: dict[str, list[str]], track_uids: list[int] | None = None
) -> str:
    """The animated S-curve view: cumulative planned vs actual/forecast progress per version,
    with a per-chart up-to-5-field filter over the parent file's fields."""
    # escape "<" so a field value can never break out of the inline <script> embed
    fields_json = json.dumps(fields).replace("<", "\\u003c")
    track_txt = ", ".join(str(u) for u in (track_uids or []))
    return f"""
<div class=panel><h2>S-Curve &mdash; cumulative progress</h2>
<p class=muted>Each version's cumulative progress on a fixed 0&ndash;100% scale: <b>gold</b> =
planned (share of activities the baseline had finishing by each month), <b>blue</b> =
actual / forecast (share whose actual or scheduled finish lands by each month). The dashed
line is that version's data date &mdash; actuals to its left, forecast to its right; the blue
curve sitting below the gold at the data date is work behind plan. Step through the versions
or press Auto-play to watch the actual curve climb (and lag) over time. <b>Track UIDs</b>
(up to 20) marks those activities' finish months on every animated frame.</p>
<div class=viz-controls id=scurveFilterBar><span class=muted>Filter this chart by up to
{MAX_FIELDS} field(s) of the parent file:</span> <span id=scurveFilter></span>
<form method=get action=/scurve style="display:inline">
<label>Track UIDs <input id=scurveTrack name=uids data-no-i18n value="{_e(track_txt)}"
placeholder="e.g. 155, 187, 411" size=28
title="Up to 20 UniqueIDs (comma/space separated) marked on every frame of the animation"></label>
<button type=submit>Track</button></form></div>
<div class=viz-controls>
<label id=scurveVersionWrap style="display:none">File <select id=scurveVersion data-no-i18n>
<option value=all>All files (chronological)</option>
</select></label>
<button id=prevScurve type=button>&#9664; Prev</button>
<span id=scurveLabel class=muted></span>
<button id=nextScurve type=button>Next &#9654;</button>
<button id=scurvePlay type=button>&#9654; Auto-play</button>
<label>Time scale <select id=scurveGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label>
</div>
<div id=scurveChart class=chart-host></div></div>
{_scurve_interpretation(sc)}
<script>window.SF_SCURVE_FIELDS = {fields_json};</script>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>"""


#: display convention (operator 2026-07-08): a thresholded measure that PASSES but sits at or
#: above this fraction of its threshold shows as a YELLOW warning (approaching the limit).
_RIBBON_WARN_FRACTION = 0.8

#: ribbon columns whose color comes from a zero-tolerance DCMA threshold (any offender = fail)
_RIBBON_ZERO_TOLERANCE = {"negative_float": "DCMA-07", "number_of_leads": "DCMA-02"}
#: ribbon columns colored from the DCMA-05 5%-of-activities threshold
_RIBBON_PCT5 = {"hard_constraints"}
#: ribbon float columns that are a mean/max of the incomplete-activity population — a placeholder
#: 0.0 when that population is empty, so they render "—" not a fabricated figure (audit NEW-1)
_RIBBON_FLOAT_EXTRAS = {"avg_float_days", "max_float_days"}


def _ribbon_cell_class(attr: str, r: object, quality: dict[str, MetricResult]) -> str:
    """pass (green) / warning (yellow) / fail (red) for thresholded measures; '' = no threshold.

    Thresholds come from the Bible-validated quality metrics where they exist; Negative Float
    and Leads use the DCMA zero-tolerance rule; Hard Constraints uses the DCMA-05 5% rule.
    The warning band (PASS but >= 80% of the threshold) is a display convention, not a metric.
    """
    q = quality.get(attr)
    if q is not None and q.threshold is not None:
        if q.status is CheckStatus.FAIL:
            return "rib-fail"
        if q.status is CheckStatus.PASS:
            return "rib-warn" if q.value >= _RIBBON_WARN_FRACTION * q.threshold else "rib-pass"
        return ""
    count = getattr(r, attr, None)
    if attr in _RIBBON_ZERO_TOLERANCE and isinstance(count, int):
        return "rib-pass" if count == 0 else "rib-fail"
    if attr in _RIBBON_PCT5 and isinstance(count, int) and q is not None and q.population:
        pct = 100.0 * count / q.population
        if pct > 5.0:
            return "rib-fail"
        return "rib-warn" if pct >= _RIBBON_WARN_FRACTION * 5.0 else "rib-pass"
    return ""  # no published threshold — neutral


def _can_we_trust_header(sch: Schedule, analysis: _Analysis, ribbon: RibbonMetrics) -> str:
    """Chapter 02 "Can we trust the plan?" (ADR-0198): the data-driven takeaway + a quality-KPI
    strip + the DCMA-outcome and logic-completeness bars, for the LATEST loaded version — every
    figure read from the ribbon/audit the page already computed (no engine math; honest counts)."""
    checks = analysis.audit.checks
    passes = sum(1 for c in checks if _status_class(c.status) == "pass")
    fails = sum(1 for c in checks if _status_class(c.status) == "fail")
    na = sum(1 for c in checks if _status_class(c.status) == "na")
    scored = passes + fails
    total = compute_activity_makeup(sch).total

    # takeaway — the top one/two structural weaknesses, stated as real counts with correct
    # singular/plural agreement (or "clean" when there are none)
    def _acts(n: int) -> str:
        return "activity" if n == 1 else "activities"

    phrases: list[str] = []
    if ribbon.missing_logic:
        n = ribbon.missing_logic
        phrases.append(f"{n} {_acts(n)} {'misses' if n == 1 else 'miss'} logic")
    if ribbon.negative_float:
        n = ribbon.negative_float
        phrases.append(f"{n} {_acts(n)} {'carries' if n == 1 else 'carry'} negative float")
    if ribbon.hard_constraints:
        n = ribbon.hard_constraints
        con = "a hard constraint" if n == 1 else "hard constraints"
        phrases.append(f"{n} {_acts(n)} {'sits' if n == 1 else 'sit'} on {con}")
    if phrases:
        weak = " — " + ", and ".join(phrases[:2]) + "."
    else:
        weak = " — logic is complete, with no negative float or hard constraints."
    scored_txt = (
        f"{passes} of {scored} DCMA-14 quality checks pass"
        if scored
        else ("the DCMA-14 checks don't apply to this file")
    )
    takeaway = f"{scored_txt}{weak}"

    kpi = _stat_cards(
        [
            ("DCMA checks passed", f"{passes} / {scored}" if scored else "—"),
            ("Missing logic", str(ribbon.missing_logic)),
            ("Hard constraints", str(ribbon.hard_constraints)),
            ("Negative float", str(ribbon.negative_float)),
            ("Logic density", f"{ribbon.logic_density:g}"),
            ("Insufficient detail", str(ribbon.insufficient_detail)),
        ]
    )
    dcma_bar = _status_stack(
        "DCMA-14 checks",
        "The 14 DCMA schedule-quality checks by outcome (n/a where no threshold applies).",
        [("Pass", passes, "--ok"), ("Fail", fails, "--bad"), ("N/A", na, "--muted")],
        f"{len(checks)} checks",
    )
    wired = max(total - ribbon.missing_logic, 0)
    logic_bar = _status_stack(
        "Logic completeness",
        "Activities wired with a predecessor and successor vs those missing logic.",
        [("Logic wired", wired, "--ok"), ("Missing logic", ribbon.missing_logic, "--bad")],
        f"{total} activities",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{dcma_bar}{logic_bar}</div>'
    )


def _workbench_body() -> str:
    """The Metric Workbench (ADR-0204): an Acumen-style page — the selectable metric library on
    the left, the ribbon (chosen metrics x versions, oldest-first) on the right, and a
    click-to-drill grid (filter / sort / group / add columns / Excel) below. The library is
    server-rendered so it works before JS; ``workbench.js`` reads the checkboxes to draw the
    ribbon and drill via ``/api/workbench`` + ``/api/workbench/drill``."""
    families: dict[str, list[tuple[str, str, str]]] = {}
    for e in catalog_entries():
        families.setdefault(e.family, []).append((e.metric_id, e.name, e.describe))
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
    return f"""
<div class=panel>
<h2>Metric Workbench</h2>
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
<script src="/static/workbench.js"></script>"""


def _sc_status_class(status: str) -> str:
    # class-name lookup (not a secret) — B105 is a false positive.
    return {"PASS": "pass", "FAIL": "fail", "INFO": "info"}.get(status, "na")  # nosec B105


def _scorecard_export_table(sc: Scorecard) -> Table:
    """One assessment scorecard as an export table (Check / Result / Detail / Source)."""
    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (c.label, c.status, c.detail, c.provenance) for c in sc.checks
    )
    return Table(f"{sc.name} — {sc.framework}", ("Check", "Result", "Detail", "Source"), rows)


def _scorecard_panel(sc: Scorecard, file_key: str) -> str:
    """One assessment scorecard as a panel: a pass/fail/info chip ribbon over a detail table.

    Pure presentation over the validated :class:`Scorecard`; every chip's figure and the source it
    is drawn from come straight from the engine (no re-scoring here). A check that cites offending
    activities gets the ``sf-drill`` hook so clicking "(N activities)" lists them (add columns +
    Excel) via ``drilldown.js`` against ``file_key``."""
    score = f"{sc.passed}/{sc.scored} scored checks pass" if sc.scored else "no scored checks"
    chips = "".join(
        f'<span class="sl-chip sl-{_sc_status_class(c.status)}" '
        f'title="{_e(c.label)}: {_e(c.detail)} — {_e(c.provenance)}">'
        f"<span class=sl-name>{_e(c.label)}</span> <b>{_e(c.status)}</b></span>"
        for c in sc.checks
    )
    rows = ""
    for c in sc.checks:
        if c.offender_uids:
            payload = ",".join(str(u) for u in c.offender_uids)
            drill = (
                f' <button type=button class="linkbtn sf-drill" data-uids="{_e(payload)}" '
                f'data-file="{_e(file_key)}" data-title="{_e(c.label)}">'
                f"{len(c.offender_uids)} activities</button>"
            )
        else:
            drill = ""
        rows += (
            f"<tr><td>{_e(c.label)}</td>"
            f'<td><span class="sl-chip sl-{_sc_status_class(c.status)}">'
            f"<b>{_e(c.status)}</b></span></td>"
            f"<td>{_e(c.detail)}{drill}</td>"
            f"<td class=muted>{_e(c.provenance)}</td></tr>"
        )
    return (
        f'<div class=panel data-scorecard="{_e(sc.key)}">'
        f"<h2>{_e(sc.name)}</h2>"
        f"<p class=muted>{_e(sc.framework)}</p>"
        f"<p><b>{score}</b> &middot; {sc.info} informational &middot; {sc.na} n/a</p>"
        f'<div class=stoplight-board role=list aria-label="{_e(sc.name)} ribbon">{chips}</div>'
        "<table class=scorecard-table><tr><th scope=col>Check</th>"
        "<th scope=col>Result</th><th scope=col>Detail</th><th scope=col>Source</th></tr>"
        f"{rows}</table></div>"
    )


def _scorecards_body(
    versions: list[tuple[str, Schedule, _Analysis]],
    current_key: str,
    sch: Schedule,
    a: _Analysis,
) -> str:
    """The Assessment Scorecards page (issue #331): NASA STAT + GAO-10 + SRA-readiness ribbons for
    the chosen version, plus a reserve-sizing card fed by the on-demand SRA buffer API."""
    stat, gao, ready = compute_scorecards(sch, a.cpm, a.audit)

    def _clause(sc: Scorecard, noun: str) -> str:
        return f"{sc.passed}/{sc.scored} {noun}" if sc.scored else f"no scored {noun}"

    takeaway = (
        f"GAO {_clause(gao, 'best practices met')} &middot; "
        f"NASA STAT {_clause(stat, 'structural checks pass')} &middot; "
        f"SRA-readiness {_clause(ready, 'gates green')}."
    )
    opts = ""
    for key, vsch, _va in versions:
        label = vsch.source_file or vsch.name
        status = f" · {vsch.status_date.date().isoformat()}" if vsch.status_date is not None else ""
        sel = " selected" if key == current_key else ""
        opts += f'<option value="{_e(key)}"{sel}>{_e(label)}{_e(status)}</option>'
    selector = (
        "<form method=get action=/scorecards class=viz-controls>"
        "<label>Assess version <select name=file data-no-i18n "
        f'onchange="this.form.submit()">{opts}</select></label>'
        f'<a class=btn href="/export/xlsx/scorecards?file={_e(current_key)}">Export (Excel)</a>'
        f'<a class=btn href="/export/docx/scorecards?file={_e(current_key)}">Export (Word)</a>'
        "</form>"
    )
    reserve = (
        "<div class=panel>"
        "<h2>Reserve / buffer sizing</h2>"
        "<p class=muted>How much schedule reserve protects a committed <b>project finish</b> date "
        "at a chosen confidence, read from the SRA Monte-Carlo finish distribution "
        "(engine/sra.py). Enter the committed date and run — the simulation is off the page-load "
        "path so it only runs when you ask.</p>"
        f'<form id=reserveForm class=viz-controls data-file="{_e(current_key)}">'
        "<label>Committed finish date <input type=date id=reserveDate></label>"
        "<label>Iterations <input type=number id=reserveIters value=1000 min=100 max=5000 "
        "step=100></label>"
        "<button type=button id=reserveRun class=btn>Size the reserve</button>"
        "</form>"
        "<div id=reserveOut aria-live=polite></div></div>"
    )
    panels = (
        _scorecard_panel(stat, current_key)
        + _scorecard_panel(gao, current_key)
        + _scorecard_panel(ready, current_key)
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f"{_sources_line([sch])}"
        f"{selector}"
        f"{panels}"
        f"{reserve}"
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
        '<script src="/static/scorecards.js"></script>'
    )


def _ribbon_body(
    rows: list[tuple[str, object, dict[str, MetricResult]]],
    note: str,
    drill: dict[str, dict[str, tuple[int, ...]]] | None = None,
) -> str:
    """The Acumen-Fuse-style Schedule Quality Ribbon: one row per loaded schedule, one column
    per ribbon metric — the metrics validated against the operator's Fuse workbook export.
    Thresholded measures are color-coded pass/warning/fail, and every metric cell is CLICKABLE
    (operator 2026-07-08): the click lists that file's activities behind the figure below, with
    UID / name / duration / % complete / start / finish plus a set-once persistent Columns
    picker (standard + custom fields) and an Excel export of exactly the selection."""
    cols = [
        ("Missing Logic", "missing_logic"),
        ("Logic Density™", "logic_density"),
        ("Critical", "critical"),
        ("Hard Constraints", "hard_constraints"),
        ("Negative Float", "negative_float"),
        ("Number of Lags", "number_of_lags"),
        ("Number of Leads", "number_of_leads"),
        ("Merge Hotspot", "merge_hotspot"),
        ("Insufficient Detail™", "insufficient_detail"),
        ("Avg Float (d)", "avg_float_days"),
        ("Max Float (d)", "max_float_days"),
    ]
    midcol = len(cols) // 2
    head = "<th scope=col>Schedule</th>" + "".join(
        f"<th scope=col class=metric-th>"
        f"{_metric_help_cell(label, attr, align='right' if i >= midcol else 'left')}</th>"
        for i, (label, attr) in enumerate(cols)
    )
    body = ""
    for key, r, quality in rows:
        cells = ""
        # A fully-progressed schedule has an empty incomplete-activity float population, so
        # avg/max_float_days are a placeholder 0.0 — render "—" (not a fabricated mean/max), and
        # make the cell non-clickable since there is nothing to drill (audit NEW-1).
        na_floats = getattr(r, "incomplete_float_count", 0) == 0
        for _, attr in cols:
            if attr in _RIBBON_FLOAT_EXTRAS and na_floats:
                cells += (
                    '<td class="rib-na" title="No incomplete activities — '
                    'this measure is not applicable">—</td>'
                )
                continue
            cls = _ribbon_cell_class(attr, r, quality)
            cells += (
                f'<td class="rib-cell {cls}" data-file="{_e(key)}" data-metric="{attr}" '
                f'tabindex=0 role=button title="Click to list the activities behind this figure">'
                f"{_e(getattr(r, attr))}</td>"
            )
        body += f"<tr><td>{_e(key)}</td>{cells}</tr>"
    labels = {attr: label for label, attr in cols}
    # <-escape the inline-JSON embeds like every sibling embed (audit ADR-0250): a </script> in a
    # schedule key can't currently arise (keys are Path.name, no slash) but the escape is the
    # explicit barrier, not an implicit Path.name side effect, and keeps the pattern uniform.
    drill_json = json.dumps(
        {k: {m: list(u) for m, u in v.items()} for k, v in (drill or {}).items()}
    ).replace("<", "\\u003c")
    labels_json = json.dumps(labels).replace("<", "\\u003c")  # uniform <-escape (static labels)
    drill_script = (
        f"<script>window.SF_RIBBON_DRILL = {drill_json}; "
        f"window.SF_RIBBON_LABELS = {labels_json};</script>"
        "<div id=ribbonDrill class=ribbon-drill></div>"
        '<script src="/static/ribbon_drill.js"></script>'
    )
    return f"""{note}
<div class=panel><h2>Schedule Quality Ribbon</h2>
<p class=muted>The schedule-quality ribbon metrics, one row per loaded
schedule. <b>Missing Logic</b> = activities missing a predecessor and/or successor;
<b>Logic Density™</b> = logic links per activity (2&times;links &divide; activities);
<b>Critical</b> = activities the source tool flags critical (its stored Critical / Total Slack);
<b>Lags</b> / <b>Leads</b> = activities whose predecessors carry a positive / negative offset,
counted across all statuses (planned, in-progress, or complete &mdash; unlike the
incomplete-only DCMA-14 checks); <b>Hard Constraints</b> / <b>Negative Float</b> are the DCMA
counts; <b>Merge Hotspot</b> = activities with more than two predecessors. <b>Insufficient Detail™</b> = activities whose duration exceeds 10% of the
project span (the NASA Acumen library formula, Fuse-validated). These are validated against the
reference schedule-quality export. <i>Float Ratio™ is omitted pending its exact definition.</i>
<span class=rib-legend><span class=rib-pass>pass</span> <span class=rib-warn>warning
(&ge;80% of threshold)</span> <span class=rib-fail>fail</span> &mdash; colored where a
published threshold exists; unthresholded measures stay neutral.</span>
<b>Click any metric cell</b> to list the activities behind that figure below.</p>
<table><tr>{head}</tr>{body}</table></div>{drill_script}"""


def _scurve_data(sc: SCurve) -> dict[str, object]:
    return {
        "months": list(sc.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_index": v.status_index,
                "status_date": v.status_date,
                "activities": v.activities,
                "planned": list(v.planned),
                "actual": list(v.actual),
                "tracked": [
                    {
                        "uid": t.uid,
                        "name": t.name,
                        "finish_index": t.finish_index,
                        "baseline_index": t.baseline_index,
                        "pct": t.percent_complete,
                    }
                    for t in v.tracked
                ],
            }
            for v in sc.versions
        ],
    }


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


def _latest_solvable(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The newest analyzable version (key, scoped schedule, cpm), scoped to the session filter.

    The same selection ``/api/sra`` and ``POST /sra/risk`` share: iterate the loaded versions
    oldest-first, keep the last one whose CPM solves, and return its scoped schedule + CPM. Returns
    ``None`` when nothing loaded version is analyzable (the caller surfaces the empty state)."""
    chosen: tuple[str, Schedule, CPMResult] | None = None
    for key, raw in st.ordered_versions():
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            continue
        chosen = (key, st.scope(raw), analysis.cpm)
    return chosen


def _sra_selected(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The schedule the SRA runs against — the operator's pick (``st.sra_file``) when it names a
    loaded, solvable version, otherwise the latest-solvable default. One resolver shared by the
    page, the simulation API, and the override POST so all three always agree on the file."""
    key = st.sra_file
    if key is not None and key in st.schedules:
        raw = st.schedules[key]
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            pass  # the chosen file no longer solves (e.g. filtered to nothing) -> fall back
        else:
            return (key, st.scope(raw), analysis.cpm)
    return _latest_solvable(st)


def _sra_overrides_table(st: SessionState, sch: Schedule | None) -> str:
    """The current per-activity overrides as a table (UID, opt/ml/pess in days) + Remove buttons."""
    if not st.sra_overrides:
        return "<p class=muted>No per-activity overrides &mdash; every activity uses the global triangular above.</p>"
    per_day = sch.calendar.working_minutes_per_day if sch is not None else 0
    names = sch.tasks_by_id if sch is not None else {}

    def _days(minutes: int) -> str:
        return f"{minutes / per_day:g}" if per_day else str(minutes)

    rows = []
    for uid in sorted(st.sra_overrides):
        opt, ml, pess = st.sra_overrides[uid]
        name = _e(names[uid].name) if uid in names else ""
        rows.append(
            f"<tr><td>{uid}</td><td>{name}</td><td>{_days(opt)}</td><td>{_days(ml)}</td>"
            f"<td>{_days(pess)}</td><td>"
            f'<form action="/sra/risk" method=post class=navform style="display:inline">'
            f'<input type=hidden name=remove value="{uid}">'
            "<button type=submit class=linkbtn>Remove</button></form></td></tr>"
        )
    return (
        "<table><thead><tr><th scope=col>UID</th><th scope=col>Activity</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Optimistic (d)', 'optimistic_duration')}</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Most-likely (d)', 'most_likely_duration')}</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Pessimistic (d)', 'pessimistic_duration')}</th>"
        "<th scope=col></th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + '<form action="/sra/risk" method=post class=navform style="margin-top:8px">'
        + '<input type=hidden name=clear value="1">'
        + "<button type=submit>Clear all overrides</button></form>"
    )


_CONSEQUENCE_HINT = (
    "Leave blank to auto-rate from the schedule impact (NASA Schedule guideline: the impact days "
    "converted to calendar months -- &lt;1 week=1, 1 week to &lt;1 month=2, 1 to &lt;3 months=3, "
    "3 to &lt;=6 months=4, &gt;6 months=5)."
)


def _unified_risk_section(st: SessionState) -> str:
    """The single 'enter once' risk/opportunity register: ONE form carrying BOTH a days magnitude
    (SSI) and a %/multiplicative magnitude (legacy), the registered-risk table (with each magnitude
    and its lock state), and the client-side days<->% auto-derive (sra_risk.js, fed a uid->remaining-
    days map). Removing/clearing posts to the same /sra/risk-register route. Both magnitudes are
    turned into the engine's ScheduleRisk / RiskEvent at the compute boundary."""
    chosen = _sra_selected(st)
    sch = chosen[1] if chosen is not None else None
    mpd = (sch.calendar.working_minutes_per_day or 480) if sch is not None else 480
    rem_map: dict[int, float] = {}
    if sch is not None:
        for t in non_summary(sch):
            rem = (
                t.remaining_duration_minutes
                if t.remaining_duration_minutes is not None
                else t.duration_minutes
            )
            rem_map[t.unique_id] = round(rem / mpd, _REMAIN_DAYS_DP)
    rem_json = json.dumps({str(u): d for u, d in rem_map.items()}).replace("<", "\\u003c")
    lock = "&#128274;"  # a small lock marks a magnitude the operator set explicitly (used verbatim)
    rows = (
        "".join(
            f"<tr><td>{_e(r.id)}</td><td>{_e(r.name)}</td><td>{r.probability * 100:g}%</td>"
            f"<td>{r.impact_days:g} d{(' ' + lock) if r.days_locked else ''}</td>"
            f"<td>{r.impact_pct:g}%{(' ' + lock) if r.pct_locked else ''}</td>"
            f"<td>{_e(', '.join(str(u) for u in r.affected))}</td>"
            f'<td><form action="/sra/risk-register" method=post style="display:inline">'
            f'<input type=hidden name=action value=remove><input type=hidden name=rid value="{_e(r.id)}">'
            "<button type=submit class=linkbtn>remove</button></form></td></tr>"
            for r in st.sra_risks
        )
        or "<tr><td colspan=7 class=muted>No risks registered.</td></tr>"
    )
    return f"""
<h3>Risk / Opportunity register</h3>
<p class=muted>Enter a risk <b>once</b> &mdash; it feeds <b>both</b> the additive-days (SSI) and the
multiplicative-% (legacy) Monte-Carlo. Type a <b>days</b> impact <i>or</i> a <b>%</b> impact and the
other auto-calculates from the affected tasks' remaining duration; edit either to override it (it
locks {lock} and is used as-entered for that model). A negative value is an opportunity.</p>
<form id=riskForm action="/sra/risk-register" method=post class=viz-controls>
<input type=hidden name=action value=add>
<input type=hidden id=riskDaysLocked name=days_locked value="">
<input type=hidden id=riskPctLocked name=pct_locked value="">
<label>Name <input type=text name=name maxlength=80 placeholder="e.g. Permit delay"></label>
<label>Probability % <input type=number name=prob min=0 max=100 step=any placeholder="40"></label>
<label>Affected UIDs <input type=text id=riskAffected name=affected placeholder="106, 152"></label>
<label>Impact (days) <input type=number id=riskDays name=impact_days step=any placeholder="auto"></label>
<label>Impact (%) <input type=number id=riskPct name=impact_pct step=any placeholder="auto"></label>
<label title="{_CONSEQUENCE_HINT}">Consequence 1-5 <input type=number name=consequence min=1 max=5
 style="width:56px" placeholder="auto &#9432;"></label>
<button type=submit>Add risk</button></form>
<table><thead><tr><th scope=col>ID</th><th scope=col>Name</th><th scope=col>Prob</th>
<th scope=col>Impact (days)</th><th scope=col>Impact (%)</th><th scope=col>Affected</th>
<th scope=col></th></tr></thead><tbody>{rows}</tbody></table>
<form action="/sra/risk-register" method=post class=navform style="margin-top:6px">
<input type=hidden name=action value=clear><button type=submit>Clear all risks</button></form>
<script>window.SF_REMAIN_DAYS={rem_json};</script>
<script src="/static/sra_risk.js"></script>"""


def _ssi_three_point(st: SessionState, sch: Schedule) -> dict[int, tuple[int, int, int]]:
    """Per-task ``(BestCase, MostLikely=remaining, WorstCase)`` minutes for the SSI run — a manual /
    auto Best-Worst override when present, else derived from the task's Risk Ranking Factor. Tasks
    with neither are absent (the engine treats them as a point mass = no duration uncertainty)."""
    tbl = RiskFactorTable(rows=st.sra_factor_rows)
    out: dict[int, tuple[int, int, int]] = {}
    for t in non_summary(sch):
        u = t.unique_id
        rem = (
            t.remaining_duration_minutes
            if t.remaining_duration_minutes is not None
            else t.duration_minutes
        )
        if u in st.sra_bcwc:
            bc, wc = st.sra_bcwc[u]
            out[u] = (bc, rem, wc)
        elif u in st.sra_factors:
            out[u] = factor_to_bc_wc(rem, st.sra_factors[u], tbl)
    return out


def _risk_events(st: SessionState) -> tuple[RiskEvent, ...]:
    """The legacy multiplicative RiskEvents derived from the unified register: ``impact_pct`` becomes
    a point multiplier (``low = ml = high = 1 + pct/100``). compute_sra/RiskEvent stay byte-frozen —
    only the inputs handed to them are derived."""
    out: list[RiskEvent] = []
    for r in st.sra_risks:
        m = max(0.0, 1.0 + r.impact_pct / 100.0)
        out.append(
            RiskEvent(
                id=r.id,
                name=r.name,
                probability=r.probability,
                impact_low=m,
                impact_ml=m,
                impact_high=m,
                affected=r.affected,
            )
        )
    return tuple(out)


def _schedule_risks(st: SessionState) -> tuple[ScheduleRisk, ...]:
    """The SSI additive-days ScheduleRisks derived from the unified register."""
    return tuple(
        ScheduleRisk(
            id=r.id,
            name=r.name,
            probability=r.probability,
            impact_days=r.impact_days,
            affected=r.affected,
            consequence_rating=r.consequence_rating,
        )
        for r in st.sra_risks
    )


def _affected_avg_remaining_days(sch: Schedule | None, uids: Sequence[int]) -> float:
    """Average REMAINING duration (working days) of the affected leaf tasks — the basis the days↔%
    auto-derive uses so the additive and multiplicative magnitudes produce the same TOTAL schedule
    impact across the affected set. 0.0 when nothing is known (then no derivation is possible)."""
    if sch is None:
        return 0.0
    mpd = sch.calendar.working_minutes_per_day or 480
    rems: list[float] = []
    for u in uids:
        t = sch.tasks_by_id.get(u)
        if t is not None and not t.is_summary:
            rem = (
                t.remaining_duration_minutes
                if t.remaining_duration_minutes is not None
                else t.duration_minutes
            )
            # round each per-task value at the SAME precision the client receives in
            # SF_REMAIN_DAYS so the two averages match exactly for sub-day tasks (audit M5)
            rems.append(round(rem / mpd, _REMAIN_DAYS_DP))
    return sum(rems) / len(rems) if rems else 0.0


def _reconcile_magnitudes(
    days_str: str, pct_str: str, days_locked: bool, pct_locked: bool, avg_rem: float
) -> tuple[float, float, bool, bool]:
    """Parse the two magnitudes and derive whichever the operator did not supply, using ``avg_rem``
    (days = pct/100 x avg ; pct = days/avg x 100). A field that was supplied (or flagged) is locked
    and used verbatim. Mirrors the client-side ``sra_risk.js`` so the JS-off / load path agrees."""
    days = _to_float(days_str, 0.0) if days_str.strip() else None
    pct = _to_float(pct_str, 0.0) if pct_str.strip() else None
    dl = days_locked or days is not None
    pl = pct_locked or pct is not None
    if avg_rem > 0:
        if days is not None and pct is None:
            pct = round(days / avg_rem * 100.0, 2)
        elif pct is not None and days is None:
            days = round(pct / 100.0 * avg_rem, 2)
    return (days or 0.0), (pct or 0.0), dl, pl


# ── SRA Excel round-trip templates (ADR-0211): export a fill-in workbook, reimport it ──────────
# Headers are the contract between the exported template and the importer. The importer matches a
# column by a case-insensitive substring of these labels, so the operator can reorder/rename
# lightly and re-imports still bind — while a missing figure is skipped and reported, never guessed.
_RR_HEADERS = (
    "Risk ID",
    "Risk name",
    "Probability %",
    "Impact (working days)",
    "Consequence (1-5)",
    "Affected UIDs (; separated)",
)
_TR_HEADERS = (
    "UID",
    "Task name",
    "Remaining (days)",
    "Risk Ranking Factor (0-5)",
    "Best-Case (days)",
    "Worst-Case (days)",
)


def _reference_tasks_table(sch: Schedule) -> Table:
    """A read-only UID → name → remaining-days reference sheet so the operator maps valid UIDs."""
    mpd = sch.calendar.working_minutes_per_day or 480
    rows: list[tuple[Cell, ...]] = []
    for t in non_summary(sch):
        rem = (
            t.remaining_duration_minutes
            if t.remaining_duration_minutes is not None
            else t.duration_minutes
        )
        rows.append((t.unique_id, t.name, round(rem / mpd, 1)))
    return Table(
        "Tasks (reference - do not edit)", ("UID", "Task name", "Remaining (days)"), tuple(rows)
    )


def _risk_register_template(st: SessionState, sch: Schedule) -> TableSet:
    """The risk-register fill-in template: the current register (or one example row) + a task
    reference sheet. Re-import via ``POST /sra/import/risk-register``."""
    names = sch.tasks_by_id
    rows: list[tuple[Cell, ...]] = []
    for r in st.sra_risks:
        rows.append(
            (
                r.id,
                r.name,
                round(r.probability * 100, 1),
                round(r.impact_days, 2),
                r.consequence_rating if r.consequence_rating is not None else "",
                "; ".join(str(u) for u in r.affected),
            )
        )
    if not rows:
        example_uid = next((t.unique_id for t in non_summary(sch)), 0)
        example_name = names[example_uid].name if example_uid in names else "some activity"
        rows.append(
            (
                "EXAMPLE (delete this row)",
                f"e.g. vendor delay to {example_name}",
                30,
                10,
                3,
                str(example_uid),
            )
        )
    return TableSet(
        "Risk Register Template",
        (Table("Risk Register", _RR_HEADERS, tuple(rows)), _reference_tasks_table(sch)),
    )


def _task_risk_template(st: SessionState, sch: Schedule) -> TableSet:
    """The per-task Best/Worst-Case + Risk-Ranking-Factor fill-in template, one row per activity,
    pre-filled with any current values. Re-import via ``POST /sra/import/task-risk``."""
    mpd = sch.calendar.working_minutes_per_day or 480

    def _days(minutes: int | None) -> Cell:
        return "" if minutes is None else round(minutes / mpd, 1)

    rows: list[tuple[Cell, ...]] = []
    for t in non_summary(sch):
        u = t.unique_id
        rem = (
            t.remaining_duration_minutes
            if t.remaining_duration_minutes is not None
            else t.duration_minutes
        )
        bc, wc = st.sra_bcwc.get(u, (None, None))
        rows.append(
            (
                u,
                t.name,
                round(rem / mpd, 1),
                st.sra_factors.get(u, ""),
                _days(bc),
                _days(wc),
            )
        )
    return TableSet("Task Risk Template", (Table("Task Risk Inputs", _TR_HEADERS, tuple(rows)),))


def _first_sheet_rows(sheets: dict[str, list[list[str]]], *prefer: str) -> list[list[str]]:
    """The rows of the first sheet whose name matches a preferred label (case-insensitive
    substring), else the first non-empty sheet."""
    for want in prefer:
        for name, rows in sheets.items():
            if want.lower() in name.lower() and rows:
                return rows
    for rows in sheets.values():
        if rows:
            return rows
    return []


def _header_columns(rows: list[list[str]], wanted: Sequence[str]) -> tuple[int, dict[str, int]]:
    """Find the header row (the first row that matches >=2 wanted labels) and map each wanted label
    to its column index by case-insensitive substring. Returns (header_row_index, {label: col})."""
    for i, row in enumerate(rows[:5]):
        cells = [c.strip().lower() for c in row]
        found: dict[str, int] = {}
        for label in wanted:
            key = label.split(" (")[0].strip().lower()  # match on the label before any "( … )"
            for col, cell in enumerate(cells):
                if cell and (key in cell or cell in key):
                    found[label] = col
                    break
        if len(found) >= 2:
            return i, found
    return -1, {}


def _cell(row: list[str], col: int | None) -> str:
    return row[col].strip() if col is not None and 0 <= col < len(row) else ""


def _import_risk_register(
    st: SessionState, sch: Schedule, sheets: dict[str, list[list[str]]]
) -> dict[str, object]:
    """Replace the session risk register from an uploaded template. Returns a summary
    (imported / skipped-empty / dropped-uids) — nothing is fabricated; unmatched UIDs are dropped
    and counted, a row with no name or no valid activity is skipped."""
    rows = _first_sheet_rows(sheets, "risk register", "register", "risk")
    hdr_i, cols = _header_columns(rows, _RR_HEADERS)
    if hdr_i < 0:
        return {
            "error": "could not find a Risk Register header row (need Risk name + Affected UIDs)"
        }
    c_id = cols.get("Risk ID")
    c_name = cols.get("Risk name")
    c_prob = cols.get("Probability %")
    c_days = cols.get("Impact (working days)")
    c_cons = cols.get("Consequence (1-5)")
    c_aff = cols.get("Affected UIDs (; separated)")
    imported: list[UnifiedRisk] = []
    skipped = dropped_uids = 0
    seq = 0
    for row in rows[hdr_i + 1 :]:
        name = _cell(row, c_name)
        rid_raw = _cell(row, c_id)
        # the exported seed row carries the "EXAMPLE (delete this row)" marker in the ID column
        # (its name is illustrative) — skip it whether or not the operator deleted it
        if rid_raw.lower().startswith("example") or name.lower().startswith("example"):
            continue
        aff_raw = _cell(row, c_aff)
        valid: list[int] = []
        for u in _parse_uid_list(aff_raw):
            task = sch.tasks_by_id.get(u)
            if task is not None and not task.is_summary and u not in valid:
                valid.append(u)
            else:
                dropped_uids += 1
        if not name or not valid:
            if name or aff_raw or _cell(row, c_days):
                skipped += 1
            continue
        avg_rem = _affected_avg_remaining_days(sch, valid)
        days, pct, dl, pl = _reconcile_magnitudes(_cell(row, c_days), "", True, False, avg_rem)
        prob = _clamp_float(_cell(row, c_prob) or "0", 0.0, 1.0, 0.0, scale=0.01)
        cons_raw = _cell(row, c_cons)
        cons = min(5, max(1, int(float(cons_raw)))) if _is_number(cons_raw) else None
        seq += 1
        rid = rid_raw or f"R{seq}"
        imported.append(
            UnifiedRisk(
                id=rid,
                name=name,
                probability=prob,
                affected=tuple(valid),
                impact_days=days,
                impact_pct=pct,
                days_locked=dl,
                pct_locked=pl,
                consequence_rating=cons,
            )
        )
    st.sra_risks = imported
    st.sra_use_risk_register = bool(imported)
    return {"imported": len(imported), "skipped": skipped, "dropped_uids": dropped_uids}


def _import_task_risk(
    st: SessionState, sch: Schedule, sheets: dict[str, list[list[str]]]
) -> dict[str, object]:
    """Apply per-task Risk Ranking Factors and Best/Worst-Case durations from an uploaded template.
    Days are converted to working minutes via the schedule calendar; unknown UIDs are dropped and
    counted. A BC/WC pair only lands when BOTH cells are present (an incomplete pair is skipped)."""
    rows = _first_sheet_rows(sheets, "task risk", "task", "risk inputs")
    hdr_i, cols = _header_columns(rows, _TR_HEADERS)
    if hdr_i < 0:
        return {"error": "could not find a Task Risk header row (need UID + a factor or duration)"}
    mpd = sch.calendar.working_minutes_per_day or 480
    c_uid = cols.get("UID")
    c_fac = cols.get("Risk Ranking Factor (0-5)")
    c_bc = cols.get("Best-Case (days)")
    c_wc = cols.get("Worst-Case (days)")
    factors = dropped = bcwc = 0
    for row in rows[hdr_i + 1 :]:
        uid_raw = _cell(row, c_uid)
        if not uid_raw or not _is_number(uid_raw):
            continue
        uid = int(float(uid_raw))
        task = sch.tasks_by_id.get(uid)
        if task is None or task.is_summary:
            dropped += 1
            continue
        fac_raw = _cell(row, c_fac)
        if _is_number(fac_raw):
            st.sra_factors[uid] = min(5, max(0, int(float(fac_raw))))
            factors += 1
        bc_raw, wc_raw = _cell(row, c_bc), _cell(row, c_wc)
        if _is_number(bc_raw) and _is_number(wc_raw):
            bc_min = round(float(bc_raw) * mpd)
            wc_min = round(float(wc_raw) * mpd)
            if bc_min <= wc_min:  # BestCase must not exceed WorstCase (Law 2: no inverted range)
                st.sra_bcwc[uid] = (bc_min, wc_min)
                bcwc += 1
    return {"factors": factors, "bcwc": bcwc, "dropped_uids": dropped}


def _is_number(text: str) -> bool:
    try:
        float(text.replace("%", "").strip())
        return True
    except (ValueError, AttributeError):
        return False


def _ssi_matrix_counts(risks: Sequence[SSIRiskStat], *, opportunity: bool) -> list[list[int]]:
    """A 5x5 ``[consequence-1][probability-1]`` count grid for the risks (impact >= 0) or the
    opportunities (impact < 0) — the operator's Risk / Opportunity Assessment Matrix."""
    grid = [[0] * 5 for _ in range(5)]
    for r in risks:
        if (r.impact_days < 0) == opportunity:
            # clamp defensively: a hand-edited / third-party setup.json can carry a rating outside
            # 1..5 (the form route clamps, the load route did too after the fix below) and must never
            # IndexError or silently mis-bin a forensic export
            c = min(5, max(1, r.consequence_rating))
            p = min(5, max(1, r.probability_rating))
            grid[c - 1][p - 1] += 1
    return grid


def _ssi_data(sch: Schedule, result: SSIResult) -> dict[str, object]:
    """The SSI run summary for ``sra.js`` — the focus finish dates + percentile + per-risk stats +
    the 5x5 Risk/Opportunity matrices. Dates are already realigned to the stored finish (ADR-0123)."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    return {
        "target_uid": result.target_uid,
        "focus_name": focus,
        "iterations": result.iterations,
        "occurrence_mode": result.occurrence_mode,
        "correlation": result.correlation,
        "used_risks": result.used_risks,
        "deterministic": {
            "date": result.deterministic_finish_date,
            "percentile": round(result.deterministic_percentile * 100, 1),
        },
        "mean": result.mean_date,
        "std_days": round(result.std_days, 1),
        "std_cal_days": round(result.std_cal_days, 1),
        "percentiles": [
            {"label": "P10", "date": result.p10_date},
            {"label": "P50", "date": result.p50_date},
            {"label": "P80", "date": result.p80_date},
            {"label": "P90", "date": result.p90_date},
        ],
        "risks": [
            {
                "id": r.id,
                "name": r.name,
                "probability": round(r.probability * 100, 1),
                "impact_days": r.impact_days,
                "hits": r.hits,
                "mean_delta_days": r.mean_delta_days,
                "probability_rating": r.probability_rating,
                "consequence_rating": r.consequence_rating,
            }
            for r in result.risks
        ],
        "risk_matrix": _ssi_matrix_counts(result.risks, opportunity=False),
        "opportunity_matrix": _ssi_matrix_counts(result.risks, opportunity=True),
        # dense plotting series (realigned dates): the cumulative S-curve + the finish-date histogram
        "s_curve": [{"date": d, "p": p} for d, p in result.s_curve],
        "finish_hist": [{"date": d, "count": c} for d, c in result.finish_hist],
        # plain-language "what the results mean" cards (ADR-0201) — deterministic templates
        # filled with the run's own figures; sra_ssi.js renders them under the result table
        "conclusions": conclusions_as_dicts(conclusions_from_ssi(sch, result)),
    }


def _ssi_grid_rows(st: SessionState, sch: Schedule, cpm: CPMResult) -> list[dict[str, object]]:
    """Per-task rows for the editable SSI Gantt grid: the activity row (name, indent, dates,
    bar metadata — reusing ``_activity_rows``) plus the SSI inputs (Remaining d, Risk Ranking
    Factor, Best/Worst-case days, a risk flag, the focus flag). Only leaf (non-summary) tasks
    are editable — summaries carry no factor."""
    mpd = sch.calendar.working_minutes_per_day or 480
    risk_uids = {u for r in st.sra_risks for u in r.affected}
    by_id = sch.tasks_by_id
    rows = _activity_rows(sch, cpm)
    for row in rows:
        uid = cast("int", row["unique_id"])
        task = by_id.get(uid)
        editable = task is not None and not row["is_summary"]
        rem_days: float | None = None
        if editable and task is not None and mpd:
            rem_min = (
                task.remaining_duration_minutes
                if task.remaining_duration_minutes is not None
                else task.duration_minutes
            )
            rem_days = round(rem_min / mpd, 1)
        bc_days: float | None = None
        wc_days: float | None = None
        if uid in st.sra_bcwc and mpd:
            bc_days = round(st.sra_bcwc[uid][0] / mpd, 1)
            wc_days = round(st.sra_bcwc[uid][1] / mpd, 1)
        row.update(
            {
                "remaining_days": rem_days,
                "factor": st.sra_factors.get(uid),
                "bc_days": bc_days,
                "wc_days": wc_days,
                "has_risk": uid in risk_uids,
                "is_focus": uid == st.sra_focus_uid,
                "editable": editable,
            }
        )
    return rows


_SSI_SETUP_VERSION = (
    2  # 2: + legacy triangular (low/ml/high) + per-activity overrides (whole setup)
)


def _ssi_setup_dict(st: SessionState) -> dict[str, object]:
    """The WHOLE SRA setup as a plain, versioned, JSON-serialisable dict (Save/Load + Excel) — both
    models: the SSI factor/BC-WC/risk inputs AND the legacy global triangular + per-activity
    overrides, so a load restores every model's inputs verbatim."""
    return {
        "setup_version": _SSI_SETUP_VERSION,
        "focus_uid": st.sra_focus_uid,
        "occurrence_mode": st.sra_occurrence_mode,
        "use_risk_register": st.sra_use_risk_register,
        "correlation": st.sra_correlation,
        # legacy global triangular (fractions of each activity's remaining duration) + per-activity
        # 3-point overrides in working minutes — the legacy Monte-Carlo's inputs
        "triangular": {"low": st.sra_low, "ml": st.sra_ml, "high": st.sra_high},
        "overrides_minutes": {str(u): [o, m, p] for u, (o, m, p) in st.sra_overrides.items()},
        "factor_table": [[f, sub, add] for f, sub, add in st.sra_factor_rows],
        "factors": {str(u): f for u, f in st.sra_factors.items()},
        "bcwc_minutes": {str(u): [bc, wc] for u, (bc, wc) in st.sra_bcwc.items()},
        "risks": [
            {
                "id": r.id,
                "name": r.name,
                "probability": r.probability,
                "impact_days": r.impact_days,
                "impact_pct": r.impact_pct,
                "days_locked": r.days_locked,
                "pct_locked": r.pct_locked,
                "affected": list(r.affected),
                "consequence_rating": r.consequence_rating,
            }
            for r in st.sra_risks
        ],
    }


def _apply_ssi_setup(st: SessionState, data: dict[str, object]) -> None:
    """Repopulate the SSI SessionState from a saved setup dict, validating against the active
    schedule: unknown / summary UIDs are dropped, factors clamped 1..5, probabilities 0..1."""
    chosen = _sra_selected(st)
    leaf: set[int] = set()
    if chosen is not None:
        _key, sch, _cpm = chosen
        leaf = {t.unique_id for t in non_summary(sch)}

    def _ok(uid: object) -> bool:
        return isinstance(uid, int) and (not leaf or uid in leaf)

    rows = data.get("factor_table")
    if isinstance(rows, list) and len(rows) == 5:
        with contextlib.suppress(TypeError, ValueError, IndexError):
            st.sra_factor_rows = tuple(
                (int(r[0]), min(100.0, max(0.0, float(r[1]))), min(300.0, max(0.0, float(r[2]))))
                for r in rows
            )
    focus = data.get("focus_uid")
    st.sra_focus_uid = focus if isinstance(focus, int) and _ok(focus) else None
    mode = data.get("occurrence_mode")
    st.sra_occurrence_mode = "exact_overall" if mode == "exact_overall" else "random_each"
    st.sra_use_risk_register = bool(data.get("use_risk_register", True))
    try:
        st.sra_correlation = min(1.0, max(0.0, float(data.get("correlation", 0.0))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        st.sra_correlation = 0.0
    # legacy global triangular (fractions of remaining duration); absent in a v1 setup -> screening
    # defaults, so a load is a clean, complete reset of every model's inputs
    lo, ml, hi = 0.9, 1.0, 1.10
    tri = data.get("triangular")
    if isinstance(tri, dict):
        with contextlib.suppress(TypeError, ValueError):
            lo = max(0.0, float(tri.get("low", lo)))
            ml = max(0.0, float(tri.get("ml", ml)))
            hi = max(0.0, float(tri.get("high", hi)))
    st.sra_low, st.sra_ml, st.sra_high = lo, ml, hi
    # legacy per-activity 3-point overrides in working minutes (validated against the active schedule)
    overrides: dict[int, tuple[int, int, int]] = {}
    raw_over = data.get("overrides_minutes")
    if isinstance(raw_over, dict):
        for okey, triple in raw_over.items():
            try:
                ouid = int(okey)
            except (TypeError, ValueError):
                continue
            if _ok(ouid) and isinstance(triple, list) and len(triple) == 3:
                with contextlib.suppress(TypeError, ValueError):
                    overrides[ouid] = (
                        max(0, int(triple[0])),
                        max(0, int(triple[1])),
                        max(0, int(triple[2])),
                    )
    st.sra_overrides = overrides
    factors: dict[int, int] = {}
    raw_factors = data.get("factors")
    if isinstance(raw_factors, dict):
        for key, val in raw_factors.items():
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            if _ok(uid):
                try:
                    factors[uid] = min(5, max(0, int(val)))  # 0 = no Best/Worst uncertainty
                except (TypeError, ValueError):
                    continue
    st.sra_factors = factors
    bcwc: dict[int, tuple[int, int]] = {}
    raw_bcwc = data.get("bcwc_minutes")
    if isinstance(raw_bcwc, dict):
        for key, pair in raw_bcwc.items():
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            if _ok(uid) and isinstance(pair, list) and len(pair) == 2:
                try:
                    bcwc[uid] = (max(0, int(pair[0])), max(0, int(pair[1])))
                except (TypeError, ValueError):
                    continue
    st.sra_bcwc = bcwc
    risks: list[UnifiedRisk] = []
    seq = 0
    raw_risks = data.get("risks")
    sch_sel = chosen[1] if chosen is not None else None
    if isinstance(raw_risks, list):
        for item in raw_risks:
            if not isinstance(item, dict):
                continue
            # `affected` MUST be a list/tuple; a hand-edited non-list (e.g. 5 or null) previously
            # raised TypeError mid-loop, 500ing the route AND leaving the session half-mutated
            # (the factor/focus/override/bcwc fields were already assigned above). Guard like the
            # sibling dict fields so a malformed risk is dropped, not fatal (audit H1).
            raw_affected = item.get("affected", [])
            if not isinstance(raw_affected, (list, tuple)):
                continue
            affected = tuple(u for u in raw_affected if _ok(u))
            if not affected:
                continue
            seq += 1
            cons = item.get("consequence_rating")
            try:
                prob = min(1.0, max(0.0, float(item.get("probability", 0.0))))
                days = float(item.get("impact_days", 0.0))
            except (TypeError, ValueError):
                continue
            # a new setup carries BOTH magnitudes + locks; an older (SSI-only) setup carries
            # impact_days alone — derive the % from the affected tasks' avg remaining so it still
            # feeds both models, and lock days (the value the operator actually entered).
            has_pct = "impact_pct" in item
            try:
                pct = float(item.get("impact_pct", 0.0))
            except (TypeError, ValueError):
                pct = 0.0
            if not has_pct:
                avg = _affected_avg_remaining_days(sch_sel, affected)
                pct = round(days / avg * 100.0, 2) if avg > 0 else 0.0
            risks.append(
                UnifiedRisk(
                    id=str(item.get("id") or f"R{seq}"),
                    name=str(item.get("name") or f"Risk {seq}"),
                    probability=prob,
                    affected=affected,
                    impact_days=days,
                    impact_pct=pct,
                    days_locked=bool(item.get("days_locked", not has_pct)),
                    pct_locked=bool(item.get("pct_locked", False)),
                    consequence_rating=min(5, max(1, int(cons))) if isinstance(cons, int) else None,
                )
            )
    st.sra_risks = risks
    st.sra_risk_seq = seq


def _ssi_export_tables(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> TableSet:
    """The SSI hand-out (ADR-0123): the plain-language conclusions (ADR-0201) lead, then run
    setup, per-task durations, risk register, focus-finish results, OAT sensitivity, and the
    two 5x5 matrices."""
    conclusions = Table(
        "What the results mean",
        ("Topic", "Severity", "Finding", "What it means", "Evidence"),
        tuple(
            (
                c.topic,
                c.severity.upper(),
                c.finding,
                c.meaning,
                "; ".join(f"{label}: {value}" for label, value in c.evidence),
            )
            for c in conclusions_from_ssi(sch, result)
        ),
    )
    mpd = sch.calendar.working_minutes_per_day or 480
    names = sch.tasks_by_id
    focus_name = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    setup = Table(
        "Run setup",
        ("Field", "Value"),
        (
            (
                "Focus event",
                f"{result.target_uid} - {focus_name}"
                if result.target_uid is not None
                else focus_name,
            ),
            ("Occurrence mode", result.occurrence_mode),
            ("Correlation", result.correlation),
            ("Risk register", "on" if result.used_risks else "off"),
            ("Iterations", result.iterations),
            ("Schedule", sch.name),
        ),
    )
    dur_rows: list[tuple[Cell, ...]] = []
    for uid in sorted(set(st.sra_factors) | set(st.sra_bcwc)):
        task = names.get(uid)
        if task is None:
            continue
        bc = st.sra_bcwc.get(uid)
        dur_rows.append(
            (
                uid,
                task.name,
                st.sra_factors.get(uid),
                round(bc[0] / mpd, 2) if bc else None,
                round(bc[1] / mpd, 2) if bc else None,
            )
        )
    durations = Table(
        "Per-task durations",
        ("UID", "Task", "Factor", "Best case d", "Worst case d"),
        tuple(dur_rows),
    )
    risk_by_id = {r.id: r for r in _schedule_risks(st)}
    risks = Table(
        "Risk register",
        (
            "ID",
            "Name",
            "Probability %",
            "Impact d",
            "Affected",
            "Consequence",
            "Hits",
            "Mean delta d",
        ),
        tuple(
            (
                rs.id,
                rs.name,
                round(rs.probability * 100, 1),
                rs.impact_days,
                ", ".join(str(u) for u in risk_by_id[rs.id].affected)
                if rs.id in risk_by_id
                else "",
                rs.consequence_rating,
                rs.hits,
                rs.mean_delta_days,
            )
            for rs in result.risks
        ),
    )
    results = Table(
        "Focus-finish results",
        ("Measure", "Value"),
        (
            ("Deterministic finish", result.deterministic_finish_date),
            ("Deterministic percentile", round(result.deterministic_percentile * 100, 1)),
            ("P10", result.p10_date),
            ("P50", result.p50_date),
            ("P80", result.p80_date),
            ("P90", result.p90_date),
            ("Mean", result.mean_date),
            ("Std deviation (working days)", round(result.std_days, 2)),
            ("Std deviation (calendar days)", round(result.std_cal_days, 2)),
        ),
    )
    sens = Table(
        "OAT sensitivity",
        (
            "UID",
            "Task",
            "Best case d",
            "Worst case d",
            "ML d",
            "Opportunity wd",
            "Risk wd",
            "Total wd",
        ),
        tuple(
            (
                o.unique_id,
                names[o.unique_id].name if o.unique_id in names else "",
                round(o.bc_minutes / mpd, 2),
                round(o.wc_minutes / mpd, 2),
                round(o.ml_minutes / mpd, 2),
                o.opportunity_days,
                o.risk_days,
                o.total_days,
            )
            for o in oat[:200]
        ),
    )
    risk_grid = _ssi_matrix_counts(result.risks, opportunity=False)
    opp_grid = _ssi_matrix_counts(result.risks, opportunity=True)
    risk_matrix = Table(
        "Risk matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(risk_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    opp_matrix = Table(
        "Opportunity matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(opp_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    return TableSet(
        f"Schedule Risk & Opportunity Analysis - {sch.name}",
        (conclusions, setup, durations, risks, results, sens, risk_matrix, opp_matrix),
    )


# The NASA 5x5 priority ranks (1..25) + tri-band zones (mirrors web/static/sra_ssi.js), reused to
# render the Risk/Opportunity matrices as shaded grids in the Word report (ADR-0124).
_NASA_RANK = (
    (1, 3, 5, 8, 12),
    (2, 6, 11, 14, 17),
    (4, 9, 15, 19, 21),
    (7, 13, 18, 22, 24),
    (10, 16, 20, 23, 25),
)
_NASA_ZONE = (
    ("g", "g", "g", "g", "y"),
    ("g", "g", "y", "y", "r"),
    ("g", "y", "y", "r", "r"),
    ("g", "y", "r", "r", "r"),
    ("g", "y", "r", "r", "r"),
)
_NASA_FILL = {
    "risk": {"g": "43A047", "y": "FFD400", "r": "E53935"},
    "opp": {"g": "A8D3EA", "y": "3D8EC4", "r": "15527D"},
}
_NASA_LIK = ("Remote", "Unlikely", "Possible", "Highly Likely", "Near Certainty")
_NASA_CONS_RISK = ("Low", "Minor", "Moderate", "Significant", "Severe")
_NASA_CONS_OPP = ("Low", "Minor", "Moderate", "High", "Very High")


def _sra_chart_scurve(result: SSIResult) -> Chart | None:
    """The cumulative finish-date S-curve as a fully-labelled vector chart: gridlines + axis + dense
    curve + dashed deterministic line + P10/50/80/90 dots, with a title, y-axis confidence ticks,
    x-axis date ticks + axis title, a legend, and a parked block of the percentile dates."""
    pts = [(dt.date.fromisoformat(d), p) for d, p in result.s_curve]
    if len(pts) < 2:
        return None
    x0 = min(d.toordinal() for d, _ in pts)
    span = (max(d.toordinal() for d, _ in pts) - x0) or 1

    def fx(day: dt.date) -> float:
        return max(0.0, min(1.0, (day.toordinal() - x0) / span))

    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.25, 0.5, 0.75, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    curve = (tuple((fx(d), p) for d, p in pts), "0B6BCB", 19050)
    detf = fx(dt.date.fromisoformat(result.deterministic_finish_date))
    det_line = (((detf, 0.0), (detf, 1.0)), "D29922", 9525)
    dots = tuple(
        (fx(dt.date.fromisoformat(ds)), q, "E8352E")
        for q, ds in (
            (0.10, result.p10_date),
            (0.50, result.p50_date),
            (0.80, result.p80_date),
            (0.90, result.p90_date),
        )
    )
    start_iso, end_iso = pts[0][0].isoformat(), pts[-1][0].isoformat()
    labels = (
        ChartText(0.0, 1.15, "Finish-date confidence (S-curve)", "l", 18, "222B35", True),
        *(ChartText(-0.015, q, f"{int(q * 100)}%", "r", 12) for q in (0.0, 0.25, 0.5, 0.75, 1.0)),
        ChartText(0.0, -0.07, start_iso, "l", 12),
        ChartText(1.0, -0.07, end_iso, "r", 12),
        ChartText(
            0.5, -0.18, "Forecast finish date  (y = % chance of finishing on or before)", "c", 12
        ),
        ChartText(
            0.02,
            0.84,
            f"P10  {result.p10_date}\nP50  {result.p50_date}\nP80  {result.p80_date}\n"
            f"P90  {result.p90_date}\nDeterministic  {result.deterministic_finish_date}",
            "l",
            13,
            "33414E",
        ),
        ChartText(0.04, -0.30, "— confidence curve", "l", 11, "0B6BCB"),
        ChartText(0.40, -0.30, "- - deterministic (logic-only) finish", "l", 11, "B5790C"),
        ChartText(0.80, -0.30, "* P10-P90 markers", "l", 11, "E8352E"),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.7,
        polylines=(*grids, axis, curve, det_line),
        dots=dots,
        labels=labels,
    )


def _sra_chart_hist(result: SSIResult) -> Chart | None:
    """The finish-date distribution (histogram) as labelled vector bars: title, a 0..max frequency
    y-axis, x-axis date ticks + axis title, and a call-out on the most-likely (tallest) bar."""
    bins = result.finish_hist
    if not bins:
        return None
    maxc = max((c for _d, c in bins), default=0) or 1
    peak_i = max(range(len(bins)), key=lambda i: bins[i][1])
    peak_date, peak_count = bins[peak_i]
    n = len(bins)
    rects = tuple(
        (i / n + 0.008, 0.0, (i + 1) / n - 0.008, c / maxc, "3D8EC4")
        for i, (_d, c) in enumerate(bins)
    )
    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.5, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    labels = (
        ChartText(0.0, 1.15, "Finish-date distribution", "l", 18, "222B35", True),
        ChartText(-0.015, 0.0, "0", "r", 12),
        ChartText(-0.015, 0.5, f"{round(maxc / 2)}", "r", 12),
        ChartText(-0.015, 1.0, f"{maxc}", "r", 12),
        ChartText(-0.04, 1.13, "Iterations", "l", 11),
        ChartText(0.0, -0.07, bins[0][0], "l", 12),
        ChartText(1.0, -0.07, bins[-1][0], "r", 12),
        ChartText(0.5, -0.18, "Forecast finish date  (y = number of simulated finishes)", "c", 12),
        ChartText(
            (peak_i + 0.5) / n,
            min(1.07, peak_count / maxc + 0.07),
            f"most likely\n{peak_date} ({peak_count})",
            "c",
            11,
            "1A5276",
        ),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.5,
        polylines=(*grids, axis),
        rects=rects,
        labels=labels,
    )


def _sra_chart_tornado(oat: Sequence[OATSensitivity]) -> Chart | None:
    """The duration-sensitivity tornado: per task a centred bar — opportunity-to-accelerate (green,
    left of centre) and risk-of-delay (red, right) — scaled to the largest total swing, with a
    title, per-row UID + total-swing labels, a centre baseline, a working-day scale, and a legend."""
    rows = [o for o in oat if o.total_days > 0][:12]
    if not rows:
        return None
    maxv = max((o.opportunity_days + o.risk_days for o in rows), default=0.0) or 1.0
    n = len(rows)
    rects: list[tuple[float, float, float, float, str]] = []
    labels: list[ChartText] = [
        ChartText(
            0.0, 1.13, "Duration sensitivity (tornado) — working-day swing", "l", 18, "222B35", True
        ),
        ChartText(0.27, 1.04, "◀ opportunity (accelerate)", "c", 11, "2E7D32"),
        ChartText(0.73, 1.04, "risk (delay) ▶", "c", 11, "C62828"),
        ChartText(0.5, -0.06, "0", "c", 12),
        ChartText(0.0, -0.06, f"-{maxv:g} wd", "l", 11),
        ChartText(1.0, -0.06, f"+{maxv:g} wd", "r", 11),
        ChartText(
            0.5,
            -0.17,
            "Working days the focus finish moves when each task is swung Best↔Worst",
            "c",
            12,
        ),
    ]
    for i, o in enumerate(rows):
        y0 = 1.0 - (i + 0.85) / n
        y1 = 1.0 - (i + 0.15) / n
        yc = 1.0 - (i + 0.5) / n
        opp = (o.opportunity_days / maxv) * 0.5
        risk = (o.risk_days / maxv) * 0.5
        if opp > 0:
            rects.append((0.5 - opp, y0, 0.5, y1, "43A047"))
        if risk > 0:
            rects.append((0.5, y0, 0.5 + risk, y1, "E53935"))
        labels.append(ChartText(-0.015, yc, str(o.unique_id), "r", 11, "33414E"))
        labels.append(ChartText(1.0, yc, f"{o.total_days:g} wd", "l", 11, "33414E"))
    center = (((0.5, 0.0), (0.5, 1.0)), "555555", 9525)
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.9,
        polylines=(center,),
        rects=tuple(rects),
        labels=tuple(labels),
    )


def _sra_matrix_chart(result: SSIResult, *, opportunity: bool) -> Chart:
    """The 5x5 Risk/Opportunity assessment matrix as a shaded grid: NASA rank (1-25) + (count)."""
    counts = _ssi_matrix_counts(result.risks, opportunity=opportunity)  # [consequence-1][prob-1]
    fam = "opp" if opportunity else "risk"
    cons = _NASA_CONS_OPP if opportunity else _NASA_CONS_RISK
    fill = _NASA_FILL[fam]

    def cell(lk: int, c: int) -> tuple[str, str, str]:
        cnt = counts[c - 1][lk - 1]
        zone = _NASA_ZONE[lk - 1][c - 1]
        text = f"{_NASA_RANK[lk - 1][c - 1]}" + (f" ({cnt})" if cnt else "")
        dark_text = zone == "r" or (opportunity and zone == "y")
        return (text, fill[zone], "FFFFFF" if dark_text else "10202E")

    header = (
        ("L \\ C", "E9EEF5", "333333"),
        *((f"{c + 1} {cons[c]}", "E9EEF5", "333333") for c in range(5)),
    )
    body = tuple(
        ((f"{lk} {_NASA_LIK[lk - 1]}", "E9EEF5", "333333"), *(cell(lk, c) for c in range(1, 6)))
        for lk in range(5, 0, -1)
    )
    return Chart(kind="matrix", grid=(header, *body))


def _sra_report_blocks(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> list[Block]:
    """The comprehensive narrative SRA Word report (ADR-0124): a PM-level executive summary, then
    per-section detail (focus-finish + S-curve + distribution, duration sensitivity + tornado,
    per-task durations, risk register, the 5x5 matrices) with embedded vendor-free vector charts,
    plus a methodology & assumptions section. Reuses the export tables for the data grids."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    by_title = {t.title: t for t in _ssi_export_tables(st, sch, result, oat).tables}

    def doc(title: str) -> DocTable:
        t = by_title[title]
        return DocTable(t.headers, t.rows)

    top = oat[0] if oat else None
    top_txt = (
        f"{top.unique_id} {names[top.unique_id].name if top.unique_id in names else ''} "
        f"({top.total_days:g} wd total swing)"
        if top
        else "n/a"
    )
    det_pct = round(result.deterministic_percentile * 100)
    blocks: list[Block] = [Heading(f"Schedule Risk Analysis Report - {sch.name}", level=0)]
    blocks += [
        Heading("Executive summary", level=1),
        Paragraph(
            f"This Schedule Risk Analysis evaluates the finish of {focus} over {result.iterations} "
            f"Monte-Carlo iterations. The deterministic (logic-only) finish is "
            f"{result.deterministic_finish_date} (about P{det_pct}). The risk-adjusted finish is most "
            f"likely {result.p50_date} (P50); {result.p80_date} at P80 and {result.p90_date} at P90 "
            f"carry progressively more contingency. The mean outcome is {result.mean_date} with a "
            f"standard deviation of {round(result.std_days, 1)} working days "
            f"({round(result.std_cal_days, 1)} calendar days). "
            f"{len(result.risks)} discrete risk/opportunity event(s) were modeled. The largest "
            f"duration-sensitivity driver is task {top_txt}."
        ),
        DocTable(
            ("Measure", "Value"),
            (
                (
                    "Focus event",
                    f"{result.target_uid} - {focus}" if result.target_uid is not None else focus,
                ),
                (
                    "Deterministic finish",
                    f"{result.deterministic_finish_date} (P{round(result.deterministic_percentile * 100, 1)})",
                ),
                ("P50 (most likely)", result.p50_date),
                ("P80", result.p80_date),
                ("P90", result.p90_date),
                ("Mean", result.mean_date),
                ("Std deviation (working days)", round(result.std_days, 1)),
                ("Std deviation (calendar days)", round(result.std_cal_days, 1)),
                ("Risk / opportunity events", len(result.risks)),
                ("Top sensitivity driver", top_txt),
            ),
        ),
        Paragraph(
            "Read the P-values as confidence levels: a P80 date has an approximately 80% modeled "
            "chance of being met. The deterministic finish typically sits well below P50, so the gap "
            "between them is the contingency the current logic does not yet carry.",
            lead="How to read this:",
        ),
    ]
    blocks += [
        Heading("How to set up this analysis (inputs)", level=1),
        Paragraph(
            "The forecast is driven entirely by the inputs below. Enter them on the Schedule Risk & "
            "Opportunity Analysis page, then run the Monte-Carlo. This section documents exactly what "
            "was used for this report so the analysis can be reviewed and reproduced."
        ),
        DocTable(
            ("Input", "How you enter it", "What it does"),
            (
                (
                    "Focus event",
                    "Type the task UID whose finish you want to forecast (blank = project finish).",
                    "Every result (S-curve, percentiles, sensitivity) is measured at this event's finish.",
                ),
                (
                    "Risk Ranking Factor (0-5)",
                    "Per task, in the grid or the 'Assign Risk Ranking Factor' box (one value, a list of "
                    "UIDs, or paste a whole column from Excel/MS Project).",
                    "0 = no duration uncertainty (uses the Remaining Duration as-is). 1-5 widen the "
                    "Best/Worst-case spread using the Risk Factors table below.",
                ),
                (
                    "Best / Worst-case duration",
                    "Auto-calculated from the factor (ML = current Remaining Duration), or type a value "
                    "to override.",
                    "Sets the low/high ends of each task's sampled duration range.",
                ),
                (
                    "Risk / Opportunity register",
                    "Add an event with a probability %, a schedule impact in days (positive = delay/risk, "
                    "negative = acceleration/opportunity), and the affected task UID(s).",
                    "On each iteration the event may fire and add its impact to the affected tasks.",
                ),
                (
                    "Occurrence mode",
                    "Choose 'Random each iteration' or 'Exact percentage overall'.",
                    "How often registered events fire across the run (see below).",
                ),
                (
                    "Correlation",
                    "0 to 1 (0 = independent; 0.3-0.5 typical).",
                    "Couples task durations so highs/lows do not fully cancel, widening the spread.",
                ),
            ),
        ),
        Heading("Risk Factors table (factor -> Best/Worst case)", level=2),
        Paragraph(
            "Best case = ML x (1 - subtract%/100); Worst case = ML x (1 + add%/100), where ML is the "
            "task's current Remaining Duration. These are the percentages used for this report:"
        ),
        DocTable(
            ("Risk Ranking Factor", "% subtract (Best case)", "% add (Worst case)"),
            (
                ("0 (no uncertainty)", "0", "0"),
                *((f, f"{s:g}", f"{a:g}") for f, s, a in st.sra_factor_rows),
            ),
        ),
        Paragraph(_OCC_RANDOM, lead="Random each iteration:"),
        Paragraph(_OCC_EXACT, lead="Exact percentage overall:"),
    ]
    blocks += [
        Heading("Focus-finish results", level=1),
        Paragraph(
            "The simulated finish-date distribution of the focus event: the deterministic finish, the "
            "P10/P50/P80/P90 confidence dates, the mean, and the spread (standard deviation)."
        ),
        doc("Focus-finish results"),
    ]
    sc = _sra_chart_scurve(result)
    if sc is not None:
        blocks += [
            Heading("Finish-date confidence (S-curve)", level=2),
            sc,
            Paragraph(
                "Cumulative probability of finishing on or before each date (blue). The dashed amber "
                "line is the deterministic finish; the red dots mark P10/P50/P80/P90.",
                italic=True,
            ),
        ]
    hc = _sra_chart_hist(result)
    if hc is not None:
        blocks += [
            Heading("Finish-date distribution", level=2),
            hc,
            Paragraph(
                "How many of the simulated runs landed on each finish date (taller = more likely). The "
                "labelled bar is the single most-likely finish date.",
                italic=True,
            ),
        ]
    blocks += [
        Heading("Duration sensitivity (one-at-a-time)", level=1),
        Paragraph(
            "Each ranked activity's Best/Worst-case duration is swung independently to measure how far "
            "it can pull in (opportunity to accelerate, green) or push out (risk of delay, red) the "
            "focus finish. This deterministic one-at-a-time method is validated against the "
            "reference tool."
        ),
    ]
    tor = _sra_chart_tornado(oat)
    if tor is not None:
        ranked = sum(1 for o in oat if o.total_days > 0)
        scope = (
            f"Top {min(12, ranked)} of {ranked} ranked activities shown"
            if ranked > 12
            else "All ranked activities shown"
        )
        blocks += [
            tor,
            Paragraph(
                "Bars centred on zero: green extends left (acceleration), red right (delay); the "
                f"longest total swing sets the scale. {scope}; the full set is in the table below.",
                italic=True,
            ),
        ]
    blocks.append(doc("OAT sensitivity"))
    blocks.append(
        Paragraph(
            "Swings are measured on pure-logic CPM float; this tool does not consume the file's "
            "stored, progress-aware Critical flag (ADR-0010). A near-critical activity that a tool "
            "reading the stored float treats as driving can show a smaller delay-swing here, and "
            "vice-versa, so the mid/low ranking may differ slightly from such a tool even though the "
            "top drivers and the Best/Worst-case inputs agree.",
            lead="Float basis:",
        )
    )
    blocks += [
        Heading("Per-task Best/Worst-case durations", level=1),
        Paragraph(
            "The Risk Ranking Factor assigned to each ranked task and the Best/Worst-case durations "
            "derived from it (ML = current Remaining Duration), or entered manually."
        ),
        doc("Per-task durations"),
    ]
    blocks += [
        Heading("Risk / Opportunity register", level=1),
        Paragraph(
            "Discrete risks and opportunities, each with its probability, additive schedule impact, "
            "simulated occurrence count, and 1-5 probability/consequence ratings."
        ),
        doc("Risk register"),
    ]
    blocks += [
        Heading("Risk & Opportunity assessment matrices", level=1),
        Paragraph(
            "Each event is placed by its Likelihood of Occurrence (rows, 1-5) and Consequence/Benefit "
            "of Occurrence (columns, 1-5). Each cell shows the NASA priority rank (1-25) and, in "
            "parentheses, the count of events that land there."
        ),
        Heading("Risk Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=False),
        Heading("Opportunity Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=True),
    ]
    blocks += [
        Heading("Methodology & assumptions", level=1),
        Paragraph(
            "Best/Worst-case durations use ML = the current Remaining Duration; "
            "BC = ML x (1 - subtract%/100), WC = ML x (1 + add%/100) with the per-factor percentages "
            f"from the Risk Factors table. Occurrence mode: {result.occurrence_mode}. Correlation: "
            f"{result.correlation:g}. Risk register: {'on' if result.used_risks else 'off'}. "
            "Consequence (1-5) is auto-rated from the schedule impact via the NASA Schedule guideline "
            "(impact days converted to calendar months: <1 week=1, 1 week to <1 month=2, 1 to "
            "<3 months=3, 3 to <=6 months=4, >6 months=5)."
        ),
        Paragraph(
            "The Best/Worst-case derivation and the deterministic one-at-a-time sensitivity are "
            "validated against the reference tool. The stochastic distribution (S-curve, histogram, "
            "percentiles) uses a standard-library random generator that is statistically "
            "representative but NOT bit-identical to the reference tool's, so treat the P-values as "
            "close, not exact "
            "(ADR-0005/0106). All computation is local and offline; this document carries the CUI "
            "marking in its header and footer.",
            italic=True,
        ),
    ]
    return blocks


_OCC_RANDOM = (
    "When this option is selected, the probability of risks/opportunities occurring is evaluated "
    "independently on each iteration of the SRA using the entered probability of occurrence. Over "
    "many iterations the average result will be close to the entered percentage, but the exact "
    "number of occurrences may vary each time you run the SRA."
)
_OCC_EXACT = (
    "When this option is selected, the total number of times a given risk/opportunity occurs is "
    "determined at the beginning of the SRA process based on the entered probability and the total "
    "number of SRA iterations chosen. That total is then randomly distributed across the iterations, "
    "so the risk/opportunity occurs the exact expected number of times overall."
)


def _ssi_panel(st: SessionState) -> str:
    """The SSI Schedule Risk & Opportunity Analysis controls (ADR-0123): focus event, Risk Factors
    table + per-task ranking + auto-calc, occurrence/correlation run options, the risk register, and
    the run/sensitivity buttons feeding ``/api/sra/ssi`` and ``/api/sra/oat`` (run off page-load)."""
    # field help for the JS-rendered SRA tables (run results + OAT sensitivity) — same hover call-out
    field_help_json = json.dumps(
        field_help_payload(
            (
                "risk_ranking_factor",
                "bc_duration",
                "wc_duration",
                "ml_duration",
                "opportunity_accelerate",
                "risk_of_delay",
                "total_sensitivity",
                "deterministic_finish",
                "mean_finish",
                "std_dev_finish",
            )
        )
    ).replace("<", "\\u003c")
    factor_rows = "".join(
        f"<tr><td>{f}</td>"
        f'<td><input type=number name=sub{f} min=0 max=100 step=1 value="{s:g}" style="width:60px"></td>'
        f'<td><input type=number name=add{f} min=0 max=300 step=1 value="{a:g}" style="width:60px"></td></tr>'
        for f, s, a in st.sra_factor_rows
    )
    rand_ck = " checked" if st.sra_occurrence_mode == "random_each" else ""
    exact_ck = " checked" if st.sra_occurrence_mode == "exact_overall" else ""
    iters = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    return f"""
<div class=panel><h2>Schedule Risk &amp; Opportunity Analysis</h2>
<p class=muted>Rank each task 1&ndash;5 (Risk Ranking Factor), auto-calculate
its Best/Worst Case from the factor table, attach discrete risks with an additive schedule impact in
days, and run a Monte-Carlo to a chosen <b>focus event</b>. The current Remaining Duration is the Most
Likely. <b>Best/Worst Case and the deterministic sensitivity are validated against the reference
tool</b>; the random distribution is statistically close, not bit-identical (a different RNG,
ADR-0005).</p>
<form action="/sra/ssi-run-config" method=post class=viz-controls>
<label>Focus event UID <input type=number name=focus_uid min=1 value="{st.sra_focus_uid or ""}"
 placeholder="project finish"></label>
<label title="{_e(_OCC_RANDOM)}"><input type=radio name=occurrence_mode value=random_each{rand_ck}>
 Random each iteration &#9432;</label>
<label title="{_e(_OCC_EXACT)}"><input type=radio name=occurrence_mode value=exact_overall{exact_ck}>
 Exact percentage overall &#9432;</label>
<label title="Blanket correlation between the task duration distributions (0 = independent; 0.3&ndash;0.5 typical) — offsets the cancelling of extreme high/low results.">Correlation
 <input type=number name=correlation min=0 max=1 step=0.05 value="{st.sra_correlation:g}" style="width:60px"></label>
<label><input type=checkbox name=use_risks value=on{" checked" if st.sra_use_risk_register else ""}>
 Use risk register</label>
<button type=submit>Save run options</button></form>
<details class=explainer><summary><b>What is Correlation, and what value should I use?</b> (with examples &amp; pros/cons)</summary>
<p><b>What it is.</b> A single <b>blanket correlation</b> (0&ndash;1) that ties the task duration draws
together in the Monte-Carlo. At <b>0</b> every task's duration is sampled <i>independently</i>. At a
positive <b>r</b>, when one task draws toward its worst case the others tend to as well (and toward best
case together) &mdash; modelling a <b>common cause</b> (a shared crew, the weather, one vendor, a single
test rig) that pushes many activities the same direction at once.</p>
<p><b>Why it matters &mdash; the "cancelling" trap.</b> With <i>independent</i> draws, one task's high
swing is offset by another's low swing, so across a big schedule the extremes cancel (the central-limit
effect) and the simulated finish distribution comes out <b>too narrow</b>. That <u>understates</u> the
real spread and gives a <b>falsely optimistic</b> P50/P80. Real programs have systemic drivers, so
durations <i>are</i> correlated; adding correlation <b>widens and fattens the tails</b> of the finish
distribution for a more honest confidence.</p>
<p><b>How to choose the value.</b></p>
<ul>
<li><b>0</b> &mdash; independent. Only defensible if tasks are genuinely unrelated (rare on one program).</li>
<li><b>0.3&ndash;0.5</b> &mdash; the <b>typical, recommended</b> range (GAO/NASA SRA guidance leans here).
Start around <b>0.3&ndash;0.4</b>.</li>
<li><b>0.6&ndash;0.9</b> &mdash; strongly coupled work (one team/resource/site driving most tasks).</li>
<li><b>1.0</b> &mdash; perfect lockstep (every task moves together); usually too extreme.</li>
</ul>
<p><b>Example 1 (shared driver).</b> A 200-task program where most work flows through one integration
team. Independent run &rarr; P80 = +12 days; at <b>r&nbsp;=&nbsp;0.4</b> the P80 widens to +28 days,
because the shared team makes slips <i>compound</i> instead of cancel &mdash; the 0.4 number is the
defensible one. <b>Example 2 (truly separate).</b> Two unrelated subprojects with their own teams and
funding &rarr; <b>r&nbsp;=&nbsp;0</b> (or a low 0.1&ndash;0.2); forcing high correlation would overstate
the spread.</p>
<p><b>Pros of using it.</b> A realistic, wider, fatter-tailed finish distribution; avoids the false
precision of independent draws; aligns with GAO/NASA practice; yields defensible contingency / P-values.
<b>Cons of using it.</b> It's one blanket value &mdash; it can't say <i>which</i> task pairs are actually
correlated (a full correlation matrix could, but needs far more elicitation); set too high it overstates
risk; the "right" number is a judgement call, so document your rationale.</p>
<p><b>Not using it (r&nbsp;=&nbsp;0).</b> <b>Pro:</b> simplest, and correct when tasks really are
independent. <b>Con:</b> on a real project it almost always <u>understates</u> schedule risk (the
cancelling effect) and reads falsely optimistic &mdash; not recommended for a forecast you intend to
defend.</p>
<p class=muted>Mechanics: a single-factor Gaussian copula (one shared draw per iteration), std-lib only;
risk firing is a separate stream, and <b>r&nbsp;=&nbsp;0 reproduces the independent run exactly</b>.</p></details>
<h3>Risk Factors table</h3>
<form action="/sra/factor-table" method=post>
<table style="width:auto"><tr><th>Factor</th><th>% subtract (Best Case)</th><th>% add (Worst Case)</th></tr>
{factor_rows}</table><button type=submit>Save factor table</button></form>
<h3>Assign Risk Ranking Factor &amp; calculate Best/Worst durations</h3>
<form action="/sra/factor" method=post class=viz-controls>
<label>UIDs <input type=text name=uids placeholder="101, 102 205"></label>
<label title="0 = no Best/Worst uncertainty (use the remaining duration as-is); 1-5 widen the Best/Worst spread.">Factor (0&ndash;5) <input type=number name=factor min=0 max=5 value=3 style="width:56px"></label>
<button type=submit>Set factor</button></form>
<p class=muted>{len(st.sra_factors)} task(s) ranked; {len(st.sra_bcwc)} have calculated Best/Worst durations.</p>
<form action="/sra/auto-calc" method=post style="display:inline"><input type=hidden name=scope value=all>
<button type=submit>Calculate SRA Durations — all</button></form>
<form action="/sra/auto-calc" method=post style="display:inline;margin-left:8px"><input type=hidden name=scope value=selected>
<input type=text name=uids placeholder="selected UIDs" style="width:150px">
<button type=submit>Calculate — selected</button></form>
{_unified_risk_section(st)}
<h3>Editable schedule grid</h3>
<p class=muted>The whole schedule as a spreadsheet-style grid: type a <b>Risk Ranking Factor</b> (0&ndash;5) or
edit <b>Best/Worst Case</b> days inline, and pick the <b>focus</b> event with the radio. <b>Factor 0
means no duration uncertainty</b> &mdash; no Best/Worst case, the remaining duration is used as-is;
1&ndash;5 widen the Best/Worst spread. A factor auto-fills Best/Worst from the table above; an explicit
Best/Worst entry is a manual override.
<b>Paste from Excel / MS&nbsp;Project:</b> copy a whole column (or a Factor/BC/WC block) and paste it
onto the first cell to fill the column down across every task in one go. Edits queue until you press
<b>Save grid</b>. Summary rows are bold and not editable.</p>
<div class=viz-controls>
<label>Zoom <input id=ssiGridZoom type=range min=0.4 max=6 step=0.2 value=1.4></label>
<button id=ssiGridFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
<label><input id=ssiShowDone type=checkbox checked> show completed tasks</label>
<label>Find UID <input id=ssiFind type=number min=1 placeholder="UID" title="Jump to a UniqueID in the grid"></label>
<span id=ssiFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=ssiBarDates type=checkbox> dates on bars</label>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<label>Group by <select id=ssiGridGroupBy data-no-i18n title="Group the grid rows under headers by any field — WBS, resources, critical, outline level, or any custom field (like the Path pages)">
<option value="">(none)</option>
<option value=wbs>WBS</option>
<option value=resource_names>Resources</option>
<option value=is_critical>Critical</option>
<option value=is_milestone>Milestone</option>
<option value=outline_level>Outline level</option>
</select></label>
<button id=ssiGridReload type=button>Refresh grid</button>
<button id=ssiGridSave type=button>Save grid</button>
<span id=ssiGridStatus class=muted aria-live=polite></span></div>
<div id=ssiGrid class=sra-grid-host></div>
<div class=viz-controls style="margin-top:12px">
<label>Iterations <select id=ssiIters>{iters}</select></label>
<label>Distribution <select id=ssiDist data-no-i18n><option value=triangular>Triangular</option>
<option value=pert>Beta-PERT</option></select></label>
<button id=ssiRun type=button>Run SRA</button>
<button id=ssiOat type=button title="Deterministic one-at-a-time Best/Worst swing on the focus event (2xN CPM solves)">Run sensitivity</button></div>
<p id=ssiStatus class=muted aria-live=polite></p>
<div id=ssiResult></div>
<div id=ssiConclusions class=sra-conclusions data-no-i18n></div>
<div id=ssiCharts class=ssi-charts></div>
<div id=ssiMatrices class=ssi-matrices></div>
<p class=muted style="font-size:11px">Tip: each chart and matrix has its own toolbar (full screen, zoom in/out, reset) to enlarge or shrink it, and hovering any point, bar, or matrix cell calls out its values (a matrix cell lists the risks that land there).</p>
<h3>Sensitivity — deterministic one-at-a-time (OAT)</h3>
<p class=muted style="font-size:11px">Swings are measured on <b>pure-logic CPM float</b> (this tool does not consume the file's stored, progress-aware Critical flag &mdash; ADR-0010). A near-critical activity that a tool reading the stored float treats as driving can therefore show a smaller delay-swing here, and vice-versa, so the mid/low ranking may differ slightly versus a stored-float tool while the top drivers agree.</p>
<div id=ssiOatOut></div>
<h3>Save / load setup &amp; export</h3>
<div class=viz-controls>
<a class=btn href="/sra/ssi/save" download>Save setup (JSON)</a>
<form action="/sra/ssi/load" method=post enctype="multipart/form-data" style="display:inline">
<label>Load setup <input type=file name=setup accept="application/json,.json"></label>
<button type=submit>Load</button></form>
<a class=btn href="/export/xlsx/sra">Export tables (Excel)</a>
<a class=btn href="/export/docx/sra" title="A full PM-level SRA report: summary, S-curve, distribution, sensitivity tornado, risk register, and the 5x5 matrices as embedded graphics.">Download SRA report (Word)</a>
<a class=btn href="/export/xlsx/sra-registry">Download risk registry (Excel)</a>
<a class=btn href="/export/docx/sra-registry">Risk registry (Word)</a></div>
<h3>Excel fill-in templates (export &rarr; edit &rarr; re-import)</h3>
<p class=muted>Download a pre-formatted Excel workbook, fill it in offline, and re-import it &mdash; a
faster way to build the register or rank many tasks than the forms above. The <b>Risk Register</b>
template carries a read-only task-reference sheet (valid UIDs + names); the <b>Task Risk</b> template
has one row per activity. On re-import, unmatched UIDs are dropped and an inverted Best/Worst pair is
skipped &mdash; nothing is fabricated, and you get a summary of exactly what landed.</p>
{_user_tip("Re-importing the Risk Register REPLACES the whole register; re-importing Task Risk UPDATES only the rows you filled in (blank cells are left untouched). Both round-trip the same figures the forms above use.")}
<div class=viz-controls>
<a class=btn href="/export/xlsx/risk-register-template" download>Risk Register template (Excel)</a>
<form action="/sra/import/risk-register" method=post enctype="multipart/form-data" style="display:inline">
<label>Import filled register <input type=file name=file accept=".xlsx" required></label>
<button type=submit>Import</button></form></div>
<div class=viz-controls style="margin-top:6px">
<a class=btn href="/export/xlsx/task-risk-template" download>Task Risk template (Excel)</a>
<form action="/sra/import/task-risk" method=post enctype="multipart/form-data" style="display:inline">
<label>Import filled task risk <input type=file name=file accept=".xlsx" required></label>
<button type=submit>Import</button></form></div>
<script>window.SF_FIELD_HELP = {field_help_json};</script>
<script src="/static/gantt.js"></script><script src="/static/sra_ssi.js"></script>
<script src="/static/sra_grid.js"></script></div>"""


def _sra_explainers() -> str:
    """Detailed, example-rich "which model, and when" guidance for the SRA page: the two Monte-Carlo
    models the tool offers (SSI additive vs legacy multiplicative) and JCL — what each does, its
    pros/cons, and when to reach for it. Collapsible so it never crowds the working controls."""
    return """
<div class=panel><h2>Which risk model should I use? (pros, cons &amp; examples)</h2>
<p class=muted>This page offers two schedule risk models. They answer the same question &mdash; "how
confident am I in the finish?" &mdash; with different math. Open each below. JCL is explained too, so
it is clear why a cost+schedule confidence is a separate thing.</p>
<details class=explainer><summary><b>SSI Schedule Risk &amp; Opportunity</b> &mdash; additive days, focus event (the top model)</summary>
<p><b>What it does.</b> Each task gets a <b>Best / Worst Case</b> duration &mdash; either from a 1&ndash;5
<b>Risk Ranking Factor</b> (e.g. factor&nbsp;3 = Best&nbsp;&minus;30% / Worst&nbsp;+30% of the remaining
duration) or from Best/Worst days you type. A Monte-Carlo samples each task between those bounds and
reports the <b>finish-date confidence of a chosen focus event</b> (e.g. "Ready to Ship"). Discrete
<b>risks add a fixed number of days</b> to the tasks they hit when they fire.</p>
<p><b>Pros.</b> Mirrors SSI Tools' SRA workflow (factor table, focus event, additive risks); intuitive
for SMEs who think "this task could run X&ndash;Y days"; the focus-event curve answers "how likely is
<i>this milestone</i> by date&nbsp;D?"; the deterministic facts (all-most-likely finish, one-at-a-time
sensitivity) validate against SSI to a fraction of a day.</p>
<p><b>Cons.</b> An additive day impact is a fixed count, not scaled to task size; the stochastic
distribution is statistically close to SSI but <i>not bit-identical</i> (different RNG, ADR-0005); you
must supply factors / Best-Worst durations and day-based risks.</p>
<p><b>When to use.</b> You want the SSI-style milestone confidence and risk register, and your SMEs give
you factors or best/worst durations and discrete risks measured <b>in days</b>.</p>
<p class=muted><b>Example.</b> Focus = "Ready to Ship". Set factor&nbsp;3 on the integration tasks, add a
risk "Late castings" 40% likely / <b>+20 days</b> on UIDs&nbsp;101,&nbsp;102. Run &rarr; P50/P80 finish
for the milestone and a tornado of which tasks drive the date.</p></details>
<details class=explainer><summary><b>Legacy Monte-Carlo</b> &mdash; multiplicative risk drivers (GAO/AACE/Hulett)</summary>
<p><b>What it does.</b> Samples each activity's duration from a triangular/PERT distribution (a global
"Min&nbsp;90% / ML&nbsp;100% / Max&nbsp;110%" default, or your per-activity 3-point), optionally fires
discrete <b>risks that MULTIPLY</b> the duration of the tasks they hit (e.g. 1.0&nbsp;/&nbsp;1.2&nbsp;/
&nbsp;1.5), and recomputes the whole project finish each iteration.</p>
<p><b>Pros.</b> The canonical <b>risk-driver</b> method (GAO Schedule Assessment Guide / AACE / Hulett);
percentage impacts <b>scale with task size</b> (a 20% slip is 20% on a 10-day or a 100-day task); one
risk mapped to several tasks <b>correlates</b> them automatically (the shared-driver correlation, no
coefficient needed); a clean project-finish confidence curve.</p>
<p><b>Cons.</b> Oriented to the <b>project</b> finish rather than a chosen milestone; multiplicative
thinking is less intuitive than "add N days"; the auto 90&ndash;100&ndash;110 default is a
<b>screening default, not SME-validated</b> (supply elicited ranges for a real run).</p>
<p><b>When to use.</b> You want the classic risk-driver Monte-Carlo for the overall project finish, with
<b>percentage</b> impacts and automatic shared-driver correlation.</p>
<p class=muted><b>Example.</b> Keep the global 90&ndash;100&ndash;110, add a risk "Permit delay" 40% likely /
100&ndash;120&ndash;150% on the permit tasks &rarr; the S-curve shows project-finish confidence and the
risk-driver tornado ranks each risk by the mean slip it causes.</p></details>
<details class=explainer><summary><b>JCL (Joint Confidence Level)</b> &mdash; why cost+schedule is a separate thing</summary>
<p><b>What it is.</b> A <b>joint cost-AND-schedule</b> confidence: the probability of finishing at or
below a given <b>cost</b> <i>and</i> on or before a given <b>date</b>, from a cost-loaded, risk-loaded
schedule (NASA NPR&nbsp;7120.5 / CEH Appendix&nbsp;J; the policy target is typically <b>~70%</b>).</p>
<p><b>Requirement.</b> A <b>cost-loaded</b> schedule (a budget and actuals on the tasks). Without cost, a
duration-only run is a <b>Schedule</b> Confidence Level (SCL) only &mdash; it must <u>not</u> be called a
JCL.</p>
<p><b>Pros.</b> The integrated cost+schedule risk picture agencies require at major milestones; ties
reserve (cost contingency + schedule margin) to a confidence target; captures cost/schedule
correlation that a schedule-only run cannot.</p>
<p><b>Cons.</b> Needs trustworthy cost loading and cost-risk inputs; more data and effort than a
schedule-only SRA.</p>
<p><b>When to use.</b> A formal cost+schedule confidence at a decision point (e.g. a NASA KDP) where a
cost-loaded, risk-adjusted IMS exists.</p>
<p class=muted><b>Status here.</b> The two models above are <b>schedule</b> SRA (an SCL). JCL is out of
scope until cost inputs exist (ADR-0106): load a cost-loaded schedule and the <a href="/evm">EVM</a>
section surfaces the cost indices; a full joint cost+schedule Monte-Carlo is a tracked follow-on.</p></details>
</div>"""


def _what_could_go_wrong_header(st: SessionState) -> str:
    """Chapter 11 "What could go wrong" (ADR-0209): the data-driven takeaway + a risk-exposure
    KPI strip + the float-exposure and risk-flag bars. The Monte-Carlo runs client-side on
    demand, so the header reports the DETERMINISTic structural risk of the SRA-selected file
    (float exposure + constraint/negative-float/registered-risk flags) — no simulation, no new
    math; every figure comes from the cached analysis + the risk register."""
    chosen = _sra_selected(st)
    if chosen is None:
        return ""
    key, sch, cpm = chosen
    try:
        audit = st.analysis_for(key, st.schedules[key]).audit
    except (CPMError, KeyError):
        return ""
    mpd = sch.calendar.working_minutes_per_day or 480
    crit = near = comfy = incomplete = neg = 0
    for task in non_summary(sch):
        if task.is_complete:
            continue
        incomplete += 1
        timing = cpm.timings.get(task.unique_id)
        if timing is None:
            continue
        tf_days = effective_total_float(task, timing.total_float) / mpd
        if tf_days < 0:
            neg += 1
        if tf_days <= 0:
            crit += 1
        elif tf_days <= 5:
            near += 1
        else:
            comfy += 1

    def _count(metric_id: str) -> int:
        return next((c.count for c in audit.checks if c.metric_id == metric_id), 0)

    hard = _count("DCMA05")
    risks = len(st.sra_risks)

    def _acts(n: int) -> str:
        return "activity" if n == 1 else "activities"

    if incomplete == 0:
        takeaway = (
            "Every activity is complete — there is no remaining work for the risk simulation to "
            "put at risk."
        )
    else:
        risk_clause = f", with {risks} risk{'s' if risks != 1 else ''} registered" if risks else ""
        takeaway = (
            f"{crit} {_acts(crit)} drive the finish and {near} more are near-critical "
            f"(within 5 days of float){risk_clause} — run the Monte-Carlo below to quantify the "
            "finish-date confidence."
        )

    kpi = _stat_cards(
        [
            ("Critical activities", str(crit)),
            ("Near-critical (≤5d)", str(near)),
            ("Negative float", str(neg)),
            ("Hard constraints", str(hard)),
            ("Registered risks", str(risks)),
            ("Incomplete activities", str(incomplete)),
        ]
    )
    exposure_bar = _status_stack(
        "Float exposure",
        "Incomplete activities by how much total float protects them from driving the finish.",
        [
            ("Critical", crit, "--bad"),
            ("Near-critical", near, "--warn"),
            ("Comfortable", comfy, "--ok"),
        ],
        f"{incomplete} incomplete {_acts(incomplete)}",
    )
    flags_bar = _status_stack(
        "Risk flags",
        "The structural risk sources the simulation and register draw on.",
        [
            ("Negative float", neg, "--bad"),
            ("Hard constraints", hard, "--warn"),
            ("Registered risks", risks, "--accent"),
        ],
        "deterministic flags on the selected file",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{exposure_bar}{flags_bar}</div>'
    )


def _sra_body(st: SessionState) -> str:
    """The Schedule Risk Analysis (SRA) results page: risk-input panel + (empty) chart hosts.

    The simulation is intentionally NOT run here — ``sra.js`` fetches ``/api/sra`` (which now reads
    the session's manual risk inputs) and renders the confidence S-curve, finish-date histogram,
    and the sensitivity tornado. Running 1000x CPM during the page render would hang on a large
    schedule, so the page opens instantly and the run happens off the page-load path.
    """
    iter_opts = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    sch = _sra_selected(st)
    scoped = sch[1] if sch is not None else None
    selected_key = sch[0] if sch is not None else None
    file_opts = "".join(
        f'<option value="{_e(key)}"{" selected" if key == selected_key else ""}>{_e(key)}</option>'
        for key, _raw in st.ordered_versions()
    )
    file_selector = (
        '<form method=get action="/sra" class=viz-controls style="margin-bottom:8px">'
        "<label>Run SRA against file "
        f"<select name=file>{file_opts}</select></label>"
        "<button type=submit>Run on this file</button></form>"
        if len(st.schedules) > 1
        else ""
    )
    # The file pick governs EVERY model on the page (SSI, OAT, and the legacy Monte-Carlo all
    # resolve their schedule through _sra_selected), so it lives in one panel at the very top.
    active_note = (
        f"<p class=muted>Active file: <b>{_e(selected_key) if selected_key else '—'}</b> "
        f"{'(latest solvable version)' if st.sra_file is None else ''}</p>"
    )
    top_file_panel = (
        "<div class=panel><h2>Schedule file for the SRA</h2>"
        "<p class=muted>Choose which loaded version <b>every</b> SRA model on this page runs "
        "against &mdash; the SSI Schedule Risk &amp; Opportunity model, the one-at-a-time "
        "sensitivity, and the legacy Monte-Carlo all use this same file.</p>"
        f"{_user_tip('Set your Risk Ranking Factors, Best/Worst-Case durations and risks once: they are shared by both the SSI model and the legacy Monte-Carlo, so you never re-enter them per model.')}"
        f"{file_selector}{active_note}</div>"
    )
    # one-shot Excel round-trip import feedback (ADR-0211): shown once, then cleared
    import_banner = ""
    if st.sra_import_msg:
        import_banner = f'<div class="notice ok" role=status>{_e(st.sra_import_msg)}</div>'
        st.sra_import_msg = None
    low_pct = f"{st.sra_low * 100:g}"
    ml_pct = f"{st.sra_ml * 100:g}"
    high_pct = f"{st.sra_high * 100:g}"
    on_defaults = (
        st.sra_low == 0.9 and st.sra_ml == 1.0 and st.sra_high == 1.10 and not st.sra_overrides
    )
    if on_defaults:
        disclaimer = (
            '<div class="notice warn" role=note><b>Auto defaults &mdash; screening placeholder, '
            "not SME-validated.</b> With no analyst-supplied risk ranges this run applies an "
            "industry-default <b>triangular</b> distribution to each activity's <i>remaining</i> "
            "duration (Min&nbsp;90% / Most-Likely&nbsp;100% / Max&nbsp;110% &mdash; an industry "
            '"Realistic" default). It is a <b>screening placeholder, not SME-validated</b> (GAO/NASA/AACE '
            "prefer elicited ranges) and is overridable per-activity. A duration-only run is a "
            "<i>schedule</i> confidence level &mdash; JCL (cost-loaded) is out of scope until cost "
            "inputs exist (ADR-0106).</div>"
        )
    else:
        disclaimer = (
            '<div class="notice ok" role=note>Using your analyst-supplied uncertainty (global '
            f"low/ml/high = {low_pct}/{ml_pct}/{high_pct}%, {len(st.sra_overrides)} per-activity "
            "overrides). A duration-only run is a <i>schedule</i> confidence level &mdash; JCL "
            "(cost-loaded) is out of scope until cost inputs exist (ADR-0106).</div>"
        )
    # B608 is bandit's SQL heuristic tripping on HTML ("<select ..." + "drawn from the latest
    # run" in one f-string) — this is a server-rendered page template, no SQL anywhere.
    return f"""
{import_banner}
{top_file_panel}
{_sra_explainers()}
{_ssi_panel(st)}
<div class=panel><h2>Legacy SRA &mdash; Monte-Carlo (multiplicative risk drivers)</h2>
<p class=muted>A seeded Monte-Carlo simulation samples each activity's duration from its
distribution and recomputes the network finish through the trusted CPM solver, building a
finish-date confidence curve. The deterministic CPM finish is marked against the distribution
so you can read how much contingency it implies (the deterministic date typically sits well
below P50). Per-activity criticality and duration sensitivity drive the tornado.</p>
{disclaimer}
<div class=viz-controls>
<label>Iterations <select id=sraIters>{iter_opts}</select></label>
<label>Distribution <select id=sraDistribution data-no-i18n>
<option value=triangular selected>Triangular</option>
<option value=pert>Beta-PERT</option>
</select></label>
<button id=sraRun type=button>Run simulation</button>
</div>
<p id=sraStatus class=muted aria-live=polite></p></div>
<div class=panel><h2>What the results mean</h2>
<p class=muted>Plain-language conclusions drawn from the latest run &mdash; each card names the
evidence figures behind it (nothing here is AI-generated; the sentences are templates filled with
the run's own numbers). Refreshed on every run and included first in the Excel export.</p>
<div id=sraConclusions class=sra-conclusions data-no-i18n></div></div>
<div class=panel><h2>Risk inputs</h2>
<p class=muted>These uncertainty ranges feed the next simulation run. The <b>global</b> triangular
applies to every activity's <i>remaining</i> duration (the standard "Quick Risk" screening
approach); completed work is fixed at its actuals (no uncertainty). Per-activity 3-point overrides
take precedence over the global for the activities you elicit.</p>
<form action="/sra/risk" method=post class=viz-controls>
<label>Low % <input type=number id=sraLow name=low min=5 max=100 step=any value="{low_pct}"></label>
<label>Most-likely % <input type=number id=sraMl name=ml min=50 max=150 step=any value="{ml_pct}"></label>
<label>High % <input type=number id=sraHigh name=high min=100 max=300 step=any value="{high_pct}"></label>
<button type=submit>Save global risk</button>
</form>
<h3>Per-activity override (3-point, days)</h3>
<form action="/sra/risk" method=post class=viz-controls>
<label>UID <input type=number name=uid min=1 step=1></label>
<label>Optimistic (d) <input type=number name=opt_days min=0 step=any></label>
<label>Most-likely (d) <input type=number name=ml_days min=0 step=any></label>
<label>Pessimistic (d) <input type=number name=pess_days min=0 step=any></label>
<button type=submit>Add override</button>
</form>
{_sra_overrides_table(st, scoped)}</div>
<div class=panel><h2>Risk drivers (tornado)</h2>
<p class=muted>Register risks <b>once</b> in the <b>Risk / Opportunity register</b> above (the Schedule
Risk &amp; Opportunity Analysis panel) &mdash; each carries both an additive-days (SSI) and a
multiplicative-% (legacy) magnitude and feeds this Monte-Carlo. This tornado ranks each registered
risk by the mean project-finish slip it contributes: the difference between the mean finish over the
iterations the risk fired and the iterations it did not (working days), with its observed occurrence
rate. Empty until a risk is registered.</p>
<div id=sraRisk class=chart-host></div></div>
<div class=panel><h2>Finish-date confidence (S-curve)</h2>
<p class=muted>Cumulative probability of finishing on or before each date, with P10/P50/P80/P90
markers and the deterministic CPM finish annotated with the percentile it sits at.</p>
<div id=sraCdf class=chart-host></div></div>
<div class=panel><h2>Finish-date distribution</h2>
<div id=sraHist class=chart-host></div></div>
<div class=panel><h2>Duration sensitivity (tornado)</h2>
<p class=muted>The activities whose duration most drives the project finish (Spearman rank
correlation), with each activity's Criticality Index and Schedule Sensitivity Index.</p>
<div id=sraSens class=chart-host></div></div>
<script src="/static/sra.js"></script>"""  # nosec B608 (HTML, not SQL)


def _sra_data(
    st: SessionState, sch: Schedule, cpm: CPMResult, result: SRAResult
) -> dict[str, object]:
    """The SRA results payload for ``sra.js`` — offsets resolved to ISO dates on the calendar."""
    cal = sch.calendar
    ps = sch.project_start

    def _iso(offset: int) -> str:
        return offset_to_datetime(ps, max(offset, 0), cal).isoformat()

    names = sch.tasks_by_id
    # tornado: the most influential activities by |duration sensitivity| (top 20)
    top = sorted(result.activities, key=lambda a: abs(a.duration_sensitivity), reverse=True)[:20]
    sensitivity = [
        {
            "uid": a.unique_id,
            "name": names[a.unique_id].name if a.unique_id in names else "",
            "ci": round(a.criticality_index, 4),
            "sens": round(a.duration_sensitivity, 4),
            "ssi": round(a.ssi, 4),
        }
        for a in top
    ]
    return {
        "iterations": result.iterations,
        "auto_used": result.auto_used,
        "manual": {
            "low": st.sra_low,
            "ml": st.sra_ml,
            "high": st.sra_high,
            "overrides": len(st.sra_overrides),
        },
        "deterministic": {
            "date": _iso(result.deterministic_finish),
            "percentile": round(result.deterministic_percentile * 100, 1),
        },
        "percentiles": [
            {"label": "P10", "date": result.p10_date},
            {"label": "P50", "date": result.p50_date},
            {"label": "P80", "date": result.p80_date},
            {"label": "P90", "date": result.p90_date},
        ],
        "mean": _iso(round(result.mean)),
        "cdf": [[_iso(offset), prob] for offset, prob in result.cdf],
        "histogram": [[_iso(lo), _iso(hi), count] for lo, hi, count in result.histogram],
        "sensitivity": sensitivity,
        "constraints_flagged": len(result.constraints_flagged),
        "risk_drivers": [
            {
                "id": d.id,
                "name": d.name,
                "probability": round(d.probability, 4),
                "hits": d.hits,
                "iterations": result.iterations,
                "delta_days": d.mean_delta_days,
            }
            for d in result.risk_drivers
        ],
        # plain-language "what the results mean" cards (ADR-0201) — deterministic templates
        # filled with the run's own figures; sra.js renders them under the run controls
        "conclusions": conclusions_as_dicts(conclusions_from_sra(sch, cpm, result)),
    }


def _task_name_across(schedules: list[Schedule], uid: int) -> str | None:
    """The activity's name from the newest version that has it (None if no version does)."""
    for sch in reversed(schedules):
        task = sch.tasks_by_id.get(uid)
        if task is not None:
            return task.name
    return None


def _corridor_chips(snap: DrivingPathSnapshot) -> str:
    """The corridor as an ordered chain of UID — name chips; entered chips flag the new ones."""
    if not snap.between.path:
        return f"<span class=muted>{_e(snap.status)}</span>"
    entered = set(snap.entered)
    chips: list[str] = []
    for uid, name in zip(snap.between.path, snap.names, strict=True):
        cls = "ev-entered" if uid in entered else "ev-stayed"
        chips.append(f'<span class="dp-chip {cls}">{uid} &mdash; {_e(name)}</span>')
    return " <span class=dp-arrow>&rarr;</span> ".join(chips)


def _task_iso_dates(
    sch: Schedule,
    basis_start: dict[int, int],
    basis_finish: dict[int, int],
    uid: int,
) -> tuple[str | None, str | None]:
    """A task's (start, finish) as ISO dates — the same stored-or-CPM basis the Path page uses
    (stored dates render verbatim; otherwise the date_basis offsets convert on the calendar)."""
    task = sch.tasks_by_id.get(uid)
    if task is None:
        return None, None
    if task.start is not None and task.finish is not None:
        return task.start.date().isoformat(), task.finish.date().isoformat()
    cal = sch.calendar
    s, f = basis_start.get(uid), basis_finish.get(uid)
    si = (
        offset_to_datetime(sch.project_start, max(s, 0), cal).date().isoformat()
        if s is not None
        else None
    )
    fi = (
        offset_to_datetime(sch.project_start, max(f, 0), cal).date().isoformat()
        if f is not None
        else None
    )
    return si, fi


def _driving_path_gantt(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    evo: DrivingPathEvolution,
    a_name: str,
    b_name: str,
) -> dict[str, object]:
    """Per-version corridor activities with dates — the payload the animated Gantt steps through.

    Each version carries the corridor's activities (ordered, with start/finish + an ``entered``
    flag vs the prior version) so the JS can draw the bars on a date axis held fixed across every
    version, the corridor visibly shifting as the schedule slips."""
    version_data: list[dict[str, object]] = []
    # Union of every calendar across all versions (name -> shading def), so the page can register
    # them once with SFTimescale.setCalendars and resolve each row's per-task calendar name (#382
    # shipped the JS read `a.calendar` but the server never emitted the field or the registry, so
    # the corridor fell back to a flat project-calendar shade — audit ADR-0247 completes the wiring).
    calendars: dict[str, dict[str, object]] = {}
    for sch, cpm, snap in zip(schedules, cpms, evo.snapshots, strict=True):
        basis_start, basis_finish = date_basis(sch, cpm)
        by_id = sch.tasks_by_id
        entered = set(snap.entered)
        # each task's GOVERNING calendar name (ADR-0243), matching the /analysis grid's resolution:
        # the task's own calendar_uid -> its registered name, else the project calendar (MSP inherit).
        cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
        proj_cal_name = sch.calendar.name
        for cal in (sch.calendar, *sch.calendars):
            if cal is not None and cal.name:
                calendars.setdefault(
                    cal.name,
                    {
                        "name": cal.name,
                        "work_weekdays": list(cal.work_weekdays),
                        "holidays": [d.isoformat() for d in cal.holidays],
                    },
                )
        acts: list[dict[str, object]] = []
        for uid, name in zip(snap.between.path, snap.names, strict=True):
            start, finish = _task_iso_dates(sch, basis_start, basis_finish, uid)
            task = by_id.get(uid)
            cal_name: str | None = None
            if task is not None:
                cuid = task.calendar_uid
                cal_name = (
                    cal_name_by_uid.get(cuid, proj_cal_name) if cuid is not None else proj_cal_name
                )
            acts.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "is_milestone": task.is_milestone if task is not None else False,
                    "entered": uid in entered,
                    "calendar": cal_name,
                }
            )
        version_data.append(
            {
                "label": snap.label,
                "data_date": snap.status_date,
                "status": snap.status,
                "change_note": snap.change_note,
                "drives": snap.between.drives,
                "activities": acts,
            }
        )
    return {
        "source_uid": evo.source_uid,
        "target_uid": evo.target_uid,
        "source_name": a_name,
        "target_name": b_name,
        "versions": version_data,
        "calendars": list(calendars.values()),
    }


def _driving_tiers_panel(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int,
    *,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
) -> str:
    """Three columns of the activities driving ``target`` in the LATEST version, bucketed by
    driving-slack tier (ADR-0011): critical/driving (0 working days — the driving path), secondary
    (<= 10 days), tertiary (<= 20 days). Fewer days = more control over the target.

    ``ignore_constraints`` / ``ignore_leveling`` are the active page trace options (the caller has
    already re-solved the schedules with them); they are embedded so the tiers Excel export runs on
    the SAME network the panel shows (ADR-0174)."""
    sch, cpm = schedules[-1], cpms[-1]
    if target not in sch.tasks_by_id:
        return ""  # the corridor branch already reports a target absent from every version
    try:
        results = compute_driving_slack(sch, target, cpm_result=cpm)
    except (KeyError, ValueError):
        return ""
    by_id = sch.tasks_by_id
    buckets: dict[str, list[tuple[int, str, float]]] = {
        "driving": [],
        "secondary": [],
        "tertiary": [],
    }
    for uid, r in results.items():
        if uid == target:
            continue
        label = _EVO_TIER_LABEL.get(r.tier)
        if label in buckets:
            t = by_id.get(uid)
            buckets[label].append(
                (uid, t.name if t is not None else f"UID {uid}", float(r.driving_slack_days))
            )
    for items in buckets.values():
        items.sort(key=lambda a: (a[2], a[0]))
    cols = [
        ("driving", "Critical / driving", "0 days"),
        ("secondary", "Secondary", f"&le; {DEFAULT_SECONDARY_MAX_DAYS} days"),
        ("tertiary", "Tertiary", f"&le; {DEFAULT_TERTIARY_MAX_DAYS} days"),
    ]
    blocks: list[str] = []
    for key, title, sub in cols:
        items = buckets[key]
        if items:
            rows = "".join(
                f"<tr><td class=num>{u}</td><td>{_e(n)}</td><td class=num>{d:.1f}</td></tr>"
                for u, n, d in items
            )
            body = (
                "<table class=card-table><tr><th scope=col>UID</th>"
                "<th scope=col>Activity</th><th scope=col>Slack (d)</th></tr>"
                f"{rows}</table>"
            )
        else:
            body = "<p class=muted>none</p>"
        blocks.append(
            f'<div style="flex:1;min-width:15em"><h3>{title} '
            f"<span class=muted>({len(items)} &middot; {sub})</span></h3>{body}</div>"
        )
    focus = by_id.get(target)
    fname = _e(focus.name) if focus is not None else f"UID {target}"
    # The file whose driving path this is (operator 2026-07-08: a bold banner naming the traced
    # file, because the driving path can differ between files). Its display label doubles as the
    # /api/analysis + export token, resolved by _find_schedule.
    file_label = sch.source_file or sch.name
    banner = f'<p class="dp-file-banner">Driving path computed on <b>{_e(file_label)}</b></p>'
    # Interactive "all driving-tier activities" chart (operator #72): one table across the three
    # tiers with a Tier + Slack(d) column, a Columns dropdown (any standard/custom field, set
    # once), a Filter box, and an Excel export of the selection — the same drill pattern as the
    # ribbon / finding-citation tables. Tier + slack are embedded here (from the same driving-slack
    # pass the buckets use); the field columns come from same-origin /api/analysis.
    tier_rows = [
        {"uid": u, "tier": key, "slack": round(d, 1)}
        for key, _title, _sub in cols
        for u, _n, d in buckets[key]
    ]
    drill = ""
    if tier_rows:
        blob = json.dumps(
            {
                "file": file_label,
                "target": target,
                "rows": tier_rows,
                "ignore_constraints": 1 if ignore_constraints else 0,
                "ignore_leveling": 1 if ignore_leveling else 0,
            }
        ).replace("<", "\\u003c")
        drill = (
            "<div class=panel><h2>All driving-tier activities</h2>"
            "<p class=muted>Every activity driving this target, across all three tiers, in one "
            "chart. Add any standard or custom field (set once), filter by any shown column, and "
            "export exactly your columns to Excel."
            + (
                " <b>Trace options active:</b> Tier and Slack come from the re-solved "
                "counterfactual network; added field columns (dates, floats, % complete, …) "
                "re-read the stored schedule and do not apply the options (ADR-0251)."
                if (ignore_constraints or ignore_leveling)
                else ""
            )
            + "</p>"
            "<div id=drivingTiers></div>"
            f'<script type="application/json" id=drivingTiersData>{blob}</script>'
            '<script src="/static/driving_tiers.js"></script></div>'
        )
    return (
        f"<div class=panel><h2>Driving tiers to {target} &mdash; {fname}</h2>"
        f"{banner}"
        "<p class=muted>Activities driving this target in the latest version, by their driving "
        "slack: <b>critical</b> (0 working days &mdash; the driving path), <b>secondary</b>, and "
        "<b>tertiary</b>. Fewer days = more control over the target (ADR-0011).</p>"
        '<div style="display:flex;gap:1em;align-items:flex-start;flex-wrap:wrap">'
        f"{''.join(blocks)}</div></div>"
        f"{drill}"
    )


def _driving_tier_trend(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    """Per-version trend of how the driving path to ``target`` degrades: the count of activities at
    each driving-slack tier — driving (0 days) / secondary (<=10) / tertiary (<=20) — over the
    loaded versions, oldest first. A GROWING driving count means slack is eroding into the path
    (more activities now control the target's date); the delta column flags that movement."""
    if len(schedules) < 2:
        return ""
    rows: list[tuple[str, str, int | None, int | None, int | None, int | None]] = []
    prior_driving: int | None = None
    any_present = False
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        dd = _mdY(sch.status_date) if sch.status_date else "—"
        if target not in sch.tasks_by_id:
            rows.append((label, dd, None, None, None, None))
            continue
        any_present = True
        counts = {"driving": 0, "secondary": 0, "tertiary": 0}
        try:
            for uid, r in compute_driving_slack(sch, target, cpm_result=cpm).items():
                if uid == target:
                    continue
                lab = _EVO_TIER_LABEL.get(r.tier)
                if lab in counts:
                    counts[lab] += 1
        except (KeyError, ValueError):
            pass
        delta = None if prior_driving is None else counts["driving"] - prior_driving
        prior_driving = counts["driving"]
        rows.append((label, dd, counts["driving"], counts["secondary"], counts["tertiary"], delta))
    if not any_present:
        return ""

    def num(v: int | None) -> str:
        return "—" if v is None else str(v)

    body = ""
    for label, dd, drv, sec, ter, delta in rows:
        if delta is None or delta == 0:
            dtxt = "" if delta is None else "0"
        elif delta > 0:  # the driving path GREW — slack eroded (degradation)
            dtxt = f'<span style="color:var(--bad)">&#9650;+{delta}</span>'
        else:
            dtxt = f'<span style="color:var(--ok)">&#9660;{delta}</span>'
        body += (
            f"<tr><td>{_e(label)}</td><td>{dd}</td><td class=num>{num(drv)}</td>"
            f"<td class=num>{num(sec)}</td><td class=num>{num(ter)}</td>"
            f"<td class=num>{dtxt}</td></tr>"
        )
    return (
        "<div class=panel><h2>Driving-slack degradation trend</h2>"
        "<p class=muted>How the driving path to this target changes across the loaded versions "
        "(oldest first): the count of activities at each driving-slack tier. A rising "
        "<b>driving (0d)</b> count means slack is eroding into the path &mdash; more work now "
        "controls the target's finish (ADR-0011).</p>"
        "<table class=card-table><tr><th scope=col>Version</th><th scope=col>Data date</th>"
        "<th scope=col>Driving (0d)</th><th scope=col>Secondary</th><th scope=col>Tertiary</th>"
        f"<th scope=col>&Delta; driving</th></tr>{body}</table></div>"
    )


def _trace_options_form(
    action: str, *, ignore_constraints: bool, ignore_leveling: bool, keep: dict[str, str]
) -> str:
    """The trace-option toggles for the server-rendered path pages (operator 2026-07-08):
    Ignore constraints / Ignore leveling delay re-solve every version's network un-pinned —
    a genuine counterfactual re-solve via ``_optioned_versions``, unlike the Path-Analysis
    options of the same name, which keep SSI's stored-date parity (ADR-0251).
    Direction and dependency range live on Path Analysis, whose trace is target-relative;
    this corridor/evolution pair is directional by construction (A→B / to the finish)."""
    hidden = "".join(
        f'<input type=hidden name="{_e(k)}" value="{_e(v)}">' for k, v in keep.items() if v
    )
    ic = " checked" if ignore_constraints else ""
    il = " checked" if ignore_leveling else ""
    return f"""<form method=get action="{action}" class="viz-controls trace-options">{hidden}
<label><input type=checkbox name=ignore_constraints value=1{ic}
title="Counterfactual re-solve: every version recomputed with all date constraints removed (pure logic). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore constraints</label>
<label><input type=checkbox name=ignore_leveling value=1{il}
title="Counterfactual re-solve: incomplete tasks' stored dates are cleared and the CPM recomputed (a 0-day leveling delay). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore leveling delay</label>
<button type=submit>Apply</button></form>"""


def _optioned_versions(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    *,
    ignore_constraints: bool,
    ignore_leveling: bool,
) -> tuple[list[Schedule], list[CPMResult], str]:
    """Apply the trace options to every loaded version (operator 2026-07-08).

    ``ignore_constraints`` re-solves each version on a constraint-stripped copy;
    ``ignore_leveling`` additionally clears incomplete tasks' stored dates so the
    corridor/evolution engines (which honor stored dates) run on the pure-logic CPM
    ("0-day leveling delay"). This is a genuine re-solve — a **counterfactual** view,
    stronger than SSI's same-named Directional Path options, which keep reporting against
    the stored (leveled/progressed) dates: SSI's own options-ON export is reproduced by
    the stored-date trace, NOT by this transform (ADR-0251) — so paths here diverge from
    SSI/MS Project output by design, and the banner says so. Returns the
    possibly-substituted lists plus that banner — defaults return the originals
    untouched."""
    if not ignore_constraints and not ignore_leveling:
        return schedules, cpms, ""
    from schedule_forensics.engine.driving_slack import strip_constraints

    out_s: list[Schedule] = []
    out_c: list[CPMResult] = []
    for sch in schedules:
        s2 = strip_constraints(sch) if ignore_constraints else sch
        if ignore_leveling:
            tasks = tuple(
                t.model_copy(update={"start": None, "finish": None}) if not t.is_complete else t
                for t in s2.tasks
            )
            s2 = s2.model_copy(update={"tasks": tasks})
        out_s.append(s2)
        out_c.append(compute_cpm(s2))
    opts = [
        name
        for on, name in (
            (ignore_constraints, "constraints ignored"),
            (ignore_leveling, "leveling delay ignored (pure-logic dates)"),
        )
        if on
    ]
    banner = (
        '<div class="notice">Trace options active: ' + ", ".join(opts) + " — the "
        "server-rendered dates and paths below come from the re-solved pure-logic network, not "
        "the stored schedule. This is a counterfactual view: SSI / MS Project report against "
        "the stored dates even with their same-named options on, so these paths will not match "
        "those tools' output (ADR-0251). Client-fetched sub-charts and drill-added field "
        "columns re-read the stored schedule and do not apply these options.</div>"
    )
    return out_s, out_c, banner


def _driving_path_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    source: int | None,
    target: int | None,
    *,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
    file_options: list[str] | None = None,
    selected_file: str = "",
    export_key: str | None = None,
) -> str:
    """Server-rendered Driving Path view: the controlling logic corridor between two chosen
    UniqueIDs, and how it changes across every loaded version (oldest first by data date) — or
    within ONE chosen file (operator 2026-07-08: the path can differ between files, so the File
    selector scopes the whole page, tiers and Gantt included, to that version).
    The counterfactual trace options (ignore constraints / leveling — a genuine
    ``_optioned_versions`` re-solve, ADR-0251) persist through the form; the page
    is directional by construction (A→B), so Path Direction lives on Path Analysis."""
    ic = " checked" if ignore_constraints else ""
    il = " checked" if ignore_leveling else ""
    file_select = ""
    if file_options and len(file_options) > 1:
        opts = '<option value="">All files (chronological)</option>' + "".join(
            f'<option value="{_e(n)}"{" selected" if n == selected_file else ""}>{_e(n)}</option>'
            for n in file_options
        )
        file_select = (
            f"<label>File <select name=file data-no-i18n "
            f'title="Trace the driving path in one chosen file — it can differ between files">'
            f"{opts}</select></label> "
        )
    export_link = ""
    if target is not None and schedules and export_key:
        # the export route looks the schedule up by SESSION KEY (filename-derived), never the
        # internal project name — the old link used last.name and 404'd (fixed 2026-07-09)
        opts = f"&ignore_constraints={int(ignore_constraints)}&ignore_leveling={int(ignore_leveling)}&drag=1"
        # the full-trace export runs the Path-Analysis (SSI-parity, stored-date) trace — with the
        # counterfactual options active it will NOT mirror the re-solved tiers above (ADR-0251)
        export_link = (
            f'<a class=btn-link href="/export/xlsx/path/{_e(export_key)}?target={target}{opts}" '
            'title="Exports the SSI-parity stored-date trace (Path Analysis basis). With trace '
            "options active it will not mirror the re-solved tiers above — stored dates still "
            'govern dated tasks in this export (ADR-0251)">'
            "&#11015; Excel (full trace to target, latest version, incl. Drag)</a>"
        )
    form = f"""
<div class=panel><form method=get action=/driving-path class=viz-controls>
{file_select}<label>From (source UniqueID): <input name=source type=number min=1
value="{source if source is not None else ""}" placeholder="UID A"></label>
<label>To (target UniqueID): <input name=target type=number min=1
value="{target if target is not None else ""}" placeholder="UID B"></label>
<label><input type=checkbox name=ignore_constraints value=1{ic}
title="Counterfactual re-solve: every version recomputed with all date constraints removed (pure logic). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore constraints</label>
<label><input type=checkbox name=ignore_leveling value=1{il}
title="Counterfactual re-solve: incomplete tasks' stored dates are cleared and the CPM recomputed (a 0-day leveling delay). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore leveling delay</label>
<button type=submit>Trace</button> {export_link}</form>
<p class=muted style="margin:.4em 0 0">The <b>driving path</b> from A to B is the chain of
activities controlling B's date that lie on a logic route from A &mdash; the work that, if it
slips, moves B. If A reaches B only through activities with float, the two are <b>connected</b>
but A does not <b>drive</b> B (the slack is reported instead). Trace it across every loaded
version to see the corridor shift.</p></div>"""

    tiers_html = (
        _driving_tiers_panel(
            schedules,
            cpms,
            target,
            ignore_constraints=ignore_constraints,
            ignore_leveling=ignore_leveling,
        )
        + _driving_tier_trend(schedules, cpms, target)
        if target is not None
        else ""
    )

    if source is None or target is None:
        hint = (
            "Enter a source and a target UniqueID above to trace the driving path between them"
            + (
                " &mdash; or enter just a target to see its driving tiers above."
                if target is None
                else "."
            )
        )
        return form + tiers_html + f"<div class=panel><p class=muted>{hint}</p></div>"

    a_name = _task_name_across(schedules, source)
    b_name = _task_name_across(schedules, target)
    if a_name is None or b_name is None:
        missing = source if a_name is None else target
        return (
            form
            + tiers_html
            + (
                f'<div class="notice err">UniqueID {missing} is not present in any loaded '
                f"version.</div>"
            )
        )

    evo = compute_driving_path_evolution(schedules, cpms, source, target)
    header = (
        f"<div class=panel><h2>Driving path: {source} &mdash; {_e(a_name)} "
        f"&rarr; {target} &mdash; {_e(b_name)}</h2>"
        f"<p class=muted>{len(evo.snapshots)} version(s), oldest first.</p></div>"
    )

    # animated date-axis Gantt of the corridor over the versions (ADR-0096); only when at least
    # one version actually has a corridor to draw (and there's more than one version to step).
    gantt = _driving_path_gantt(schedules, cpms, evo, a_name, b_name)
    versions = cast("list[dict[str, object]]", gantt["versions"])
    has_corridor = any(v["activities"] for v in versions)
    gantt_html = ""
    if has_corridor and len(schedules) > 1:
        blob = json.dumps(gantt).replace("<", "\\u003c")  # match the scurve/rem embeds (QC INFO)
        gantt_html = f"""
<div class=panel><h2>Corridor over time</h2>
<p class=muted>The driving corridor drawn on a date axis held fixed across every version, so it
visibly shifts as the schedule slips. Step or play through the versions; activities that
<b class=ev-entered>entered</b> the corridor since the prior version are outlined.</p>
<div class=viz-controls>
<button id=dpPrev type=button>&#9664; Prev</button>
<span id=dpLabel class=muted></span>
<button id=dpNext type=button>Next &#9654;</button>
<button id=dpPlay type=button>&#9654; Auto-play</button>
<span class=muted style="margin-left:1em">Zoom:</span>
<button id=dpZoomOut type=button title="zoom out">&minus;</button>
<button id=dpZoomIn type=button title="zoom in">&plus;</button>
<button id=dpFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
<label>Find <input id=dpFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every corridor task whose row contains this text"></label>
<span id=dpFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=dpBarDates type=checkbox> dates on bars</label>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
</div>
<div id=dpChart class=path-view></div></div>
<script type="application/json" id=dpData>{blob}</script>
<script src="/static/driving_path.js"></script>"""

    rows: list[str] = []
    for snap in evo.snapshots:
        when = f" &middot; data date {snap.status_date}" if snap.status_date else ""
        note = f' <span class="dp-note">{_e(snap.change_note)}</span>' if snap.change_note else ""
        delta = ""
        if snap.length_delta:
            sign = "+" if snap.length_delta > 0 else ""
            delta = f" <span class=muted>(corridor length {sign}{snap.length_delta})</span>"
        left = ""
        if snap.left:
            names = ", ".join(
                f"{uid} {_e(_task_name_across(schedules, uid) or '')}".strip() for uid in snap.left
            )
            left = f"<div class=muted>Left the corridor: <span class=ev-left>{names}</span></div>"
        rows.append(
            f"<div class=panel><h3>{_e(snap.label)}{when}</h3>"
            f"<p>{_corridor_chips(snap)}</p>"
            f"<p class=muted>{_e(snap.status)}{note}{delta}</p>"
            f"{left}</div>"
        )

    return form + tiers_html + header + gantt_html + "".join(rows)


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


def _standards_section(title: str, note: str, rows_html: str) -> str:
    return (
        f"<div class=panel><h2>{title}</h2><p class=muted>{note}</p>"
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
    intro = (
        f"<div class=panel><p>All values on this page are computed from the latest file, "
        f"<b>{fname}</b> (period metrics use the prior file's data date"
        f"{' — none loaded' if prior is None else ''}). Formulas and sources are the same "
        "entries the metric dictionary pins to the NASA Acumen metric library; each family "
        "below names its framework.</p></div>"
    )
    # §1 DCMA-14 — re-projected from the cached audit (no new math)
    audit = analysis.audit
    dcma_rows = _standards_rows([(c, c.metric_id, "") for c in audit.checks])
    dcma = _standards_section(
        "DCMA-14 point assessment",
        f"{audit.passed} passed · {audit.failed} failed · {audit.not_applicable} N/A on {fname}.",
        dcma_rows,
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
    fuse = _standards_section(
        "NASA / Acumen-Fuse execution indices",
        "Hit-or-Miss, Current/Baseline Execution, Forecast Execution, Float Ratio™, MEI and "
        f"SPI(t) — the Fuse-parity forms the /performance trends chart over time.{cei_note}",
        _standards_rows(idx),
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
    )
    return intro + dcma + fuse + sem


def _metric_scorecard_table(results: dict[str, MetricResult]) -> str:
    """A compact check/value/status table from a DCMA-14 result dict (over any (sub)schedule)."""
    rows = []
    for m in results.values():
        if m.unit == "ratio":  # CPLI / BEI — an index
            valcell = f"{round(m.value, 2)}"
        elif m.population:
            pct = m.value if m.unit == "%" else 100.0 * m.count / m.population
            valcell = f"{m.count} <span class=muted>of {m.population}</span> ({pct:.1f}%)"
        else:
            valcell = str(m.count)
        rows.append(
            f"<tr><td>{_e(m.name)}</td><td class=num>{valcell}</td>"
            f'<td class="{_status_class(m.status)}">{_e(m.status)}</td></tr>'
        )
    return (
        "<table class=card-table><tr><th scope=col>Check</th><th scope=col>Value</th>"
        f"<th scope=col>Status</th></tr>{''.join(rows)}</table>"
    )


def _threshold_legend() -> str:
    """Explain, on-page, why some measures read PASS/FAIL and others N/A, and how the on-time
    thresholds were derived (operator 2026-07-08: "define for the user what those are and how you
    calculated them")."""
    return (
        "<details class=threshold-legend><summary>How these PASS / FAIL / N&#47;A results are "
        "scored</summary><div class=threshold-legend-body>"
        "<p><b>On-time execution indices</b> (Baseline Finish/Start Compliance, Completed/Started "
        "On&nbsp;Time, CEI Finish/Start) score <b>PASS at &ge; 95%</b>. That bar is the DCMA "
        "14-Point Assessment's Baseline-Execution-Index / CPLI standard (0.95), reinforced by the "
        "GAO Schedule Assessment Guide (GAO-16-89G, Best Practice&nbsp;9); these indices are the "
        "same on-time-delivery family, so they inherit the same threshold (ADR-0161).</p>"
        "<p><b>Late mirrors</b> (Completed&nbsp;Late, Started&nbsp;Late) score <b>PASS at &le; 5%</b> "
        "&mdash; the complement of the 95% on-time bar.</p>"
        "<p><b>Informational counts</b> (Forecast to be Finished/Started, Not Started, Not "
        "Completed) carry <b>no pass/fail</b> &mdash; they are denominators / status counts, not "
        "quality gates, so they read <b>N&#47;A</b> by design.</p>"
        "<p><b>Cost indices</b> (SPI, CPI, TCPI) read <b>N&#47;A</b> only when the schedule is not "
        "cost-loaded &mdash; a <i>data limitation of the file</i>, not a missing threshold. On a "
        "cost-loaded schedule they score against 1.0. A fabricated number is never shown in place "
        "of a genuinely undefined one.</p>"
        "<p class=muted>Every threshold and its derivation is in the "
        '<a href="/help">Metric Dictionary</a>; hover any measure name for its own tooltip.</p>'
        "</div></details>"
    )


def _evm_idx_str(m: MetricResult | None) -> str:
    """A rounded index value for an EVM stat card; em dash when the metric is NOT_APPLICABLE."""
    if m is None or str(m.status) == "NA":
        return "—"
    return f"{round(m.value, 2)}"


def _evm_days_str(v: float | None) -> str:
    return "—" if v is None else f"{v:g}"


def _evm_explainer() -> str:
    """Collapsible "what these EVM numbers mean" guidance, including how EVM relates to a JCL."""
    return """
<div class=panel><h2>What these EVM numbers mean</h2>
<details class=explainer><summary><b>Schedule-based EVM</b> (always available)</summary>
<p><b>Earned Schedule SPI(t)</b> = Earned Schedule &divide; Actual Time. Unlike the cost-based SPI
(which mathematically returns to 1.0 as a late project finishes), SPI(t) stays meaningful to the end.
<b>SVt</b> = ES &minus; AT in working days (negative = behind the baseline plan).</p>
<p><b>CEI (Finish / Start)</b> &mdash; the Current Execution Index: of the activities the baseline said
should have finished (started) by now, how many actually did, on time. <b>Baseline compliance</b>
(BFC / BSC) measures the same idea against the baseline finish/start dates.</p></details>
<details class=explainer><summary><b>Cost-based EVM</b> (needs a cost-loaded schedule)</summary>
<p><b>SPI</b> = BCWP &divide; BCWS (value earned vs planned). <b>CPI</b> = BCWP &divide; ACWP (value earned
per dollar spent). <b>TCPI</b> = (BAC &minus; BCWP) &divide; (BAC &minus; ACWP) &mdash; the cost efficiency
the remaining work must hit to land on budget. These read <b>N/A</b> until the schedule carries task
budgets and actual costs; the tool never fabricates a cost figure (Law&nbsp;2).</p></details>
<details class=explainer><summary><b>How EVM relates to a JCL</b></summary>
<p>A <b>JCL</b> (Joint Confidence Level) is a Monte-Carlo over a <b>cost-loaded, risk-loaded</b> schedule
&mdash; the joint probability of finishing at or below a cost AND on or before a date. EVM here gives
you the deterministic cost+schedule performance to date; once a schedule is cost-loaded, those cost
indices populate and a full JCL becomes possible (today's <a href="/sra">Risk Analysis</a> is a
schedule-only confidence level). See the JCL explainer on the Risk Analysis page.</p></details>
</div>"""


def _evm_body(st: SessionState) -> str:
    """Earned Value Management page: schedule-based EVM always, plus cost EVM when the schedule is
    cost-loaded (else gracefully N/A), baseline compliance, and the worst finish variances."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return (
            "<div class=panel>Load an analyzable schedule to see its earned-value metrics "
            "&mdash; SPI(t), schedule variance, baseline compliance, and (if the schedule is "
            "cost-loaded) SPI / CPI / TCPI.</div>"
        )
    _key, sch, cpm = chosen
    indices = compute_evm_indices(sch, cpm)
    sv = compute_schedule_variance(sch, non_summary(sch))
    compliance = compute_baseline_compliance(sch, cpm)
    cost_loaded = any((t.budgeted_cost or 0.0) > 0 for t in non_summary(sch))

    # explicit str keys: newer mypy infers the comprehension key type as a Literal union,
    # which does not unify with _metric_scorecard_table's dict[str, MetricResult]
    sched_idx: dict[str, MetricResult] = {
        k: indices[k] for k in ("spi_t", "spi_t_acumen", "cei_finish", "cei_start") if k in indices
    }
    cost_idx: dict[str, MetricResult] = {
        k: indices[k] for k in ("spi", "cpi", "tcpi") if k in indices
    }

    cards = _stat_cards(
        [
            ("SPI(t) — Earned Schedule", _evm_idx_str(indices.get("spi_t"))),
            ("SPI(t) — Acumen", _evm_idx_str(indices.get("spi_t_acumen"))),
            ("SVt (working days)", _evm_days_str(sv.svt_days)),
            ("Earned Schedule (wd)", _evm_days_str(sv.es_days)),
            ("Actual Time (wd)", _evm_days_str(sv.at_days)),
        ]
    )

    if sv.worst:
        worst_rows = "".join(
            f"<tr><td class=num>{w.unique_id}</td>"
            f"<td>{_e(_task_name_across([sch], w.unique_id) or '')}</td>"
            f"<td class=num>{w.variance_days:+g}</td></tr>"
            for w in sv.worst
        )
        worst_tbl = (
            "<table class=card-table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>Finish variance (wd)</th></tr>{worst_rows}</table>"
        )
    else:
        worst_tbl = (
            "<p class=muted>No completed activities carry both an actual and a baseline "
            "finish yet.</p>"
        )

    cost_note = (
        ""
        if cost_loaded
        else _user_tip(
            "This schedule is <b>not cost-loaded</b>, so the cost indices (SPI / CPI / TCPI) read "
            "<b>N/A</b> &mdash; the tool never fabricates a cost number. Load a schedule with task "
            "budgets and actual costs to compute them; the schedule-based metrics need no cost."
        )
    )

    tip = _user_tip(
        "SPI(t) and SVt come from <b>Earned Schedule</b> (time-based), so they stay meaningful late "
        "in a project where the classic cost-based SPI saturates at 1.0. A negative SVt (in working "
        "days) means the project is running behind the baseline plan."
    )
    # Operator 2026-07-09: BOTH SPI(t) methods are reported, each explained with pros/cons and a
    # worked example — they measure different things and can legitimately disagree in direction.
    dual_spi = _user_tip(
        "<b>Two SPI(t) methods are shown &mdash; they answer different questions and can "
        "legitimately disagree.</b><br><br>"
        "<b>SPI(t) &mdash; Earned Schedule</b> = ES &divide; AT: how far along the <i>baseline "
        "finish curve</i> the completed work reaches (ES), divided by the working time actually "
        "elapsed (AT). <i>Example:</i> 27 activities are complete; the baseline expected the "
        "27th finish at working day 80, but 115 working days have elapsed &mdash; SPI(t) = "
        "80 &divide; 115 = <b>0.70</b> (behind). "
        "<i>Pros:</i> a true schedule-position index &mdash; it sees work that <u>has not "
        "happened</u> (stalled work drags AT while ES freezes), follows the standard "
        "Earned-Schedule literature, and feeds the IEAC(t) finish forecast. "
        "<i>Cons:</i> count-based (a tiny task and a 6-month task each move ES one step) and it "
        "needs a meaningful baseline finish sequence.<br><br>"
        "<b>SPI(t) &mdash; Acumen</b> (the Fuse metric library formula) = the <i>average "
        "duration-efficiency of started activities</i>: for each completed activity, baselined "
        "span &divide; actual span; an in-progress activity contributes 0 until it finishes. "
        "<i>Example:</i> two completed tasks ran exactly to baseline (1.0 each) and one task "
        "baselined at 10 days took 20 (0.5) &mdash; average = <b>0.83</b>: completed work ran "
        "17% slower than baselined. "
        "<i>Pros:</i> per-activity and intuitive (&gt;1 = tasks finishing faster than their "
        "baselined spans), matches Acumen Fuse exactly, unaffected by the plan's task "
        "granularity ordering. "
        "<i>Cons:</i> only sees <u>started</u> work &mdash; a schedule that is executing its "
        "few started tasks efficiently but starting far too little scores well; each in-progress "
        "activity dilutes the average toward 0 by design (the Fuse formula's blank-ActualFinish "
        "term); and equal weight per activity lets many small on-pace tasks mask one huge "
        "overrun. "
        "<i>Read them together:</i> Earned-Schedule SPI(t) low + Acumen SPI(t) high means the "
        "work being touched runs efficiently but the project is not progressing through the "
        "baselined sequence &mdash; a classic under-resourced or logic-blocked pattern."
    )
    return f"""
<div class=panel><h2>Earned Value Management (EVM) &mdash; {_e(sch.source_file or sch.name)}</h2>
<p class=muted>Performance against the baseline. The <b>schedule-based</b> metrics (Earned Schedule,
baseline compliance) always compute; the <b>cost</b> indices (SPI / CPI / TCPI) need a cost-loaded
schedule and otherwise read N/A.</p>
{tip}
{cards}</div>
<div class=panel><h2>Schedule performance</h2>
<p class=muted>Both SPI(t) methods (Earned-Schedule and Acumen per-activity) and the
baseline-anchored Current Execution Index (finish / start).</p>
{dual_spi}
{_threshold_legend()}
{_metric_scorecard_table(sched_idx)}</div>
<div class=panel><h2>Cost performance</h2>
<p class=muted>Cost-based EVM indices &mdash; applicable only when the schedule carries task budgets
and actual costs.</p>
{cost_note}
{_metric_scorecard_table(cost_idx)}</div>
<div class=panel><h2>Baseline compliance</h2>
<p class=muted>How the executed work lines up with the baseline dates (BFC / BSC and the on-time
counts).</p>
{_threshold_legend()}
{_metric_scorecard_table(compliance)}</div>
<div class=panel><h2>Worst finish variances</h2>
<p class=muted>Completed activities that finished latest relative to their baseline (working days;
positive = late).</p>
{worst_tbl}</div>
{_evm_explainer()}"""


def _resource_loading_json(rl: ResourceLoading, sch: Schedule) -> str:
    """The resource-loading payload for resources.js (load/capacity in working DAYS for display).

    Each period carries its per-task ``contributors`` (uid, name, days) so clicking a bar opens the
    over-allocation drill entirely client-side (the work behind that bar), same-origin only."""
    mpd = rl.working_minutes_per_day or 480
    by_id = sch.tasks_by_id
    payload = {
        "granularity": rl.granularity,
        # provenance + drill wiring (operator 2026-07-10): the drill fetches field data from
        # /api/analysis/<source_file> and builds its Excel link against the same file
        "source_file": sch.source_file or sch.name,
        "resources": [
            {
                "id": r.resource_id,
                "name": r.name,
                "type": r.type,
                "max_units": r.max_units,
                "total_days": round(r.total_work_minutes / mpd, 1),
                "over": list(r.over_allocated_periods),
                "series": [
                    {
                        "period": p.period,
                        "load": round(p.load_minutes / mpd, 2),
                        "cap": round(p.capacity_minutes / mpd, 2),
                        "over": p.over_allocated,
                        "tasks": [
                            {
                                "uid": uid,
                                "name": (by_id[uid].name if uid in by_id else f"UID {uid}"),
                                "days": round(mins / mpd, 2),
                            }
                            for uid, mins in p.contributors
                        ],
                    }
                    for p in r.series
                ],
            }
            for r in rl.resources
        ],
    }
    return json.dumps(payload).replace("<", "\\u003c")  # match the scurve/rem embeds (QC INFO)


def _resources_explainer() -> str:
    return """
<div class=panel><h2>How to read the resource loading</h2>
<details class=explainer><summary><b>What this shows &amp; how it's computed</b></summary>
<p>Each task's assigned <b>work</b> (hours, from the schedule's resource assignments) is spread evenly
across the <b>working days</b> of the task's span (its CPM early start &rarr; early finish) and totalled
into the chosen <b>bucket</b> (day / week / month), per resource. A resource's per-bucket <b>capacity</b>
is <code>max&nbsp;units &times; working&nbsp;hours/day &times; working&nbsp;days&nbsp;in&nbsp;the&nbsp;bucket</code>,
so over-allocation is consistent at every granularity.</p>
<p>A bucket where booked work <b>exceeds capacity</b> is <b class=res-over>over-allocated</b> (shown red)
&mdash; the resource is asked to do more than its availability allows there, a signal to re-level,
re-sequence, or add capacity. <b>Click any bar</b> to see the exact activities driving that bucket's
load. A schedule that records resource <i>names</i> but no <i>work</i> hours shows assignment counts
only (no load bars).</p></details>
<details class=explainer><summary><b>Pros &amp; cons of the even-spread method</b></summary>
<p><b>Pro:</b> works on any schedule that carries assignment work, with no extra inputs, and gives a
faithful monthly histogram. <b>Con:</b> it assumes work is spread evenly across the task (no front/back
loading) when the source file doesn't carry a time-phased contour &mdash; the totals are exact, the
within-task shape is an approximation.</p></details>
</div>"""


def _who_is_overloaded_header(st: SessionState, granularity: str = "month") -> str:
    """Chapter 08 "Who is overloaded" (ADR-0206): the data-driven takeaway + an allocation KPI
    strip + the resource-allocation and overload-concentration bars, from the same resource
    loading the page charts (compute_resource_loading — no new math). Empty when the schedule
    carries no resources (the body renders its own notice)."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return ""
    _key, sch, cpm = chosen
    granularity = granularity if granularity in ("day", "week", "month") else "month"
    rl = compute_resource_loading(sch, cpm, granularity)
    if not rl.resources:
        return ""
    mpd = rl.working_minutes_per_day or 480
    n_res = len(rl.resources)
    over = [r for r in rl.resources if r.over_allocated_periods]
    over_count = len(over)
    within = n_res - over_count
    total_days = round(sum(r.total_work_minutes for r in rl.resources) / mpd, 1)
    unit = {"day": "day", "week": "week", "month": "month"}[granularity]
    # the single worst resource by number of over-allocated periods
    worst = max(rl.resources, key=lambda r: len(r.over_allocated_periods), default=None)
    worst_over = len(worst.over_allocated_periods) if worst else 0

    def _res(n: int) -> str:
        return "resource" if n == 1 else "resources"

    if over_count == 0:
        takeaway = (
            f"All {n_res} loaded {_res(n_res)} stay within capacity across the {len(rl.periods)} "
            f"{unit}{'s' if len(rl.periods) != 1 else ''} covered — no over-allocation."
        )
    elif worst is not None and worst_over > 0:
        takeaway = (
            f"{over_count} of {n_res} {_res(n_res)} are over-allocated in at least one {unit} — "
            f"the worst is {worst.name}, over capacity in {worst_over} {unit}"
            f"{'s' if worst_over != 1 else ''}."
        )
    else:
        takeaway = (
            f"{over_count} of {n_res} {_res(n_res)} are over-allocated in at least one {unit}."
        )

    kpi = _stat_cards(
        [
            ("Resources loaded", str(n_res)),
            ("Over-allocated", str(over_count)),
            ("Within capacity", str(within)),
            ("Total work (days)", f"{total_days:g}"),
            ("Busiest resource", worst.name if worst else "—"),
            (f"{unit.title()}s covered", str(len(rl.periods))),
        ]
    )
    alloc_bar = _status_stack(
        "Resource allocation",
        f"Loaded resources within vs over their capacity, bucketed by {unit}.",
        [("Within capacity", within, "--ok"), ("Over-allocated", over_count, "--bad")],
        f"{n_res} {_res(n_res)} loaded",
    )
    if worst is not None and len(rl.periods) > 0:
        w_over = len(worst.over_allocated_periods)
        w_clear = max(len(rl.periods) - w_over, 0)
        conc_bar = _status_stack(
            "Overload concentration",
            f"The busiest resource's timeline — {worst.name} — over vs within capacity per {unit}.",
            [("Over capacity", w_over, "--bad"), ("Within", w_clear, "--muted")],
            f"{w_over} of {len(rl.periods)} {unit}{'s' if len(rl.periods) != 1 else ''} over capacity",
        )
    else:
        conc_bar = ""
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{alloc_bar}{conc_bar}</div>'
    )


def _resources_body(st: SessionState, granularity: str = "month") -> str:
    """Resources page: per-resource loading histogram + over-allocation, and a roster table."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return (
            "<div class=panel>Load a resource-loaded schedule to see resource loading and "
            "over-allocation.</div>"
        )
    _key, sch, cpm = chosen
    granularity = granularity if granularity in ("day", "week", "month") else "month"
    rl = compute_resource_loading(sch, cpm, granularity)
    if not rl.resources:
        return (
            "<div class=panel><h2>Resources</h2><p class=muted>This schedule has no resource "
            "assignments to load. Load an MS Project / Primavera file with assigned resources.</p>"
            "</div>"
        )
    mpd = rl.working_minutes_per_day or 480
    over_count = sum(1 for r in rl.resources if r.over_allocated_periods)
    total_days = round(sum(r.total_work_minutes for r in rl.resources) / mpd, 1)
    gran_label = {"day": "Days", "week": "Weeks", "month": "Months"}[granularity]
    cards = _stat_cards(
        [
            ("Resources loaded", str(len(rl.resources))),
            ("Total work (days)", f"{total_days:g}"),
            ("Over-allocated resources", str(over_count)),
            (f"{gran_label} covered", str(len(rl.periods))),
        ]
    )
    rows = "".join(
        f"<tr><td>{_e(r.name)}</td><td>{_e(r.type.title())}</td>"
        f"<td class=num>{r.max_units:g}</td><td class=num>{round(r.total_work_minutes / mpd, 1):g}</td>"
        f"<td class=num>{r.task_count}</td><td>{_e(r.peak_period or '')}</td>"
        f"<td class={'res-over' if r.over_allocated_periods else 'num'}>"
        f"{len(r.over_allocated_periods) or ''}</td></tr>"
        for r in rl.resources
    )
    unit = gran_label[:-1].lower()  # "day" / "week" / "month"
    roster = (
        "<table class=card-table><tr><th scope=col>Resource</th><th scope=col>Type</th>"
        "<th scope=col>Max units</th><th scope=col>Work (days)</th><th scope=col>Tasks</th>"
        f"<th scope=col>Peak {unit}</th><th scope=col>Over-alloc {unit}s</th></tr>"
        f"{rows}</table>"
    )
    res_opts = "".join(
        f'<option value="{r.resource_id}">{_e(r.name)}'
        f"{' ⚠' if r.over_allocated_periods else ''}</option>"
        for r in rl.resources
    )
    blob = _resource_loading_json(rl, sch)
    # day/week/month bucket selector (operator #74) — a plain GET so the server recomputes capacity
    # at the chosen granularity (capacity scales with the working days in each bucket).
    bucket_opts = "".join(
        f'<option value="{g}"{" selected" if g == granularity else ""}>{g.title()}</option>'
        for g in ("day", "week", "month")
    )
    bucket_form = (
        '<form method=get action=/resources class=viz-controls style="display:inline-flex">'
        f'<label>Bucket <select name=bucket data-no-i18n onchange="this.form.submit()" '
        f'title="Time-bucket the histogram by day, week or month">{bucket_opts}</select></label>'
        "</form>"
    )
    tip = _user_tip(
        "Pick a resource to see its <b>work vs capacity</b> histogram at the chosen bucket "
        "(day&nbsp;/&nbsp;week&nbsp;/&nbsp;month). Bars above the capacity line (red) are "
        "<b>over-allocated</b> &mdash; where that resource is booked beyond its availability. "
        "<b>Click any bar</b> to list the activities driving that bucket's load."
    )
    return f"""
<div class=panel><h2>Resource loading &amp; over-allocation &mdash; {_e(sch.source_file or sch.name)}</h2>
<p class=muted>Time-phased work per resource per {unit}, against each resource's capacity. Over-allocated
{unit}s are flagged.</p>
{tip}
{cards}</div>
<div class=panel><h2>Loading histogram</h2>
<div class=viz-controls><label>Resource <select id=resPick>{res_opts}</select></label>
{bucket_form}<span id=resStatus class=muted></span></div>
<div id=resChart class=chart-host></div>
<div id=resDrill></div>
<script type="application/json" id=resData>{blob}</script>
<script src="/static/resources.js"></script></div>
<div class=panel><h2>Resource roster</h2>
<p class=muted>Every resource that carries work, sorted by total work. Over-allocated {unit}s are the
count of {unit}s booked beyond capacity.</p>
{roster}</div>
{_resources_explainer()}"""


def _groups_field_options(fields: Sequence[str], selected: str) -> str:
    """``<option>`` list of the given selectable fields with one pre-selected."""
    opts = ['<option value="">(field…)</option>']
    for f in fields:
        sel = " selected" if f == selected else ""
        opts.append(f'<option value="{_e(f)}"{sel}>{_e(f)}</option>')
    return "".join(opts)


def _criterion_value_list(value: str | Sequence[str]) -> list[str]:
    """A criterion's selected values as a list ([] = no value restriction / field populated)."""
    if isinstance(value, str):
        return [value] if value else []
    return [v for v in value if v]


def _groups_form(
    versions: list[tuple[str, Schedule]],
    version_key: str,
    sch: Schedule,
    criteria: list[Criterion],
    breakdown: str,
) -> str:
    """The scope controls: filter rows (applied session-wide to every file), a preview-version
    picker, and a breakdown field. Field options are the union across all loaded files."""
    fields = available_fields_union([s for _, s in versions])
    vsel = ""
    if len(versions) > 1:
        vopts = "".join(
            f'<option value="{_e(k)}"{" selected" if k == version_key else ""}>'
            f"{_e(s.source_file or s.name)}</option>"
            for k, s in versions
        )
        vsel = f"<label>Preview file: <select name=version>{vopts}</select></label> "
    # MAX_FIELDS filter rows. groups.js mounts an MS-Project-style value checklist (SFChecklist)
    # per row from the field's actual values; the chosen values are submitted as hidden value{i}
    # inputs (rendered here too, so the current selection round-trips and works without JS).
    rows = []
    for i in range(MAX_FIELDS):
        f, v = criteria[i] if i < len(criteria) else ("", "")
        selected = _criterion_value_list(v)
        hidden = "".join(f'<input type=hidden name="value{i}" value="{_e(x)}">' for x in selected)
        data_sel = _e(json.dumps(selected))
        rows.append(
            f'<div class=group-row data-row="{i}" data-selected="{data_sel}">'
            f"<select name=field class=gf-field>{_groups_field_options(fields, f)}</select> "
            f"<span class=gf-values></span><span class=gf-hidden>{hidden}</span></div>"
        )
    bsel = f"<select name=breakdown>{_groups_field_options(fields, breakdown)}</select>"
    return f"""
<div class=panel><form method=get action=/groups class=group-form data-version="{_e(version_key)}">
{vsel}
<fieldset><legend>Filter &mdash; scope every metric on every page, across all loaded files, to tasks
matching ALL rows (up to {MAX_FIELDS})</legend>
{"".join(rows)}</fieldset>
<label>Break down by: {bsel}</label>
<div class=viz-controls><button type=submit name=apply value=1>Apply to all pages</button>
<a class=btn-link href="/groups?clear=1">clear filter</a></div>
</form>
<p class=muted style="margin:.3em 0 0">Pick a field (standard or custom, e.g. <b>CA-WBS</b>), then
choose its <b>values</b> from the dropdown (checkboxes with <b>All / None</b> and a search, like MS
Project). <b>Apply</b> makes it the session-wide scope &mdash; <b>every</b> metric on <b>every</b> page,
for <b>every</b> loaded file, then runs over the matching activities until you clear it. Within a field
the chosen values are OR'd; combine up to {MAX_FIELDS} fields (AND). <b>Break down by</b> a field to
score each of its values separately (one BEI per group) on the preview file below.</p></div>
<script src="/static/groups.js"></script>"""


def _groups_breakdown_table(sub: Schedule, field: str) -> str:
    """One row per distinct value of ``field`` in ``sub`` — population, % complete, and BEI."""
    groups = group_values(sub, field)
    if not groups:
        return (
            f"<div class=panel><h3>Breakdown by {_e(field)}</h3>"
            f"<p class=muted>No activities in scope carry a value for this field.</p></div>"
        )
    limit = 200
    shown = list(groups.items())[:limit]
    rows = []
    for value, uids in shown:
        group = filter_schedule(sub, [(field, value)])
        tasks = non_summary(group)
        total = len(tasks) or 1
        complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
        bei = compute_bei(group)
        bei_cell = f"{round(bei.value, 2)}" if bei.population else "<span class=muted>—</span>"
        rows.append(
            f"<tr><td>{_e(value)}</td><td class=num>{len(uids)}</td>"
            f"<td class=num>{100.0 * complete / total:.0f}%</td>"
            f"<td class=num>{bei_cell} <span class=muted>({bei.count}/{bei.population})</span></td></tr>"
        )
    more = (
        f"<p class=muted>Showing the first {limit} of {len(groups)} values.</p>"
        if len(groups) > limit
        else ""
    )
    return (
        f"<div class=panel><h3>Breakdown by {_e(field)} &mdash; {len(groups)} value(s)</h3>"
        "<table class=card-table><tr><th scope=col>Value</th><th scope=col>Activities</th>"
        "<th scope=col>% complete</th><th scope=col>BEI</th></tr>"
        f"{''.join(rows)}</table>{more}</div>"
    )


def _groups_per_file_table(versions: list[tuple[str, Schedule]], criteria: list[Criterion]) -> str:
    """One row per loaded file: how many of its activities the active filter matches (ADR-0104)."""
    rows = []
    grand_m = grand_t = 0
    for _key, s in versions:
        sub = filter_schedule(s, criteria)
        matched, total = len(non_summary(sub)), len(non_summary(s))
        grand_m += matched
        grand_t += total
        pct = f"{100.0 * matched / total:.0f}%" if total else "—"
        rows.append(
            f"<tr><td>{_e(s.source_file or s.name)}</td><td class=num>{matched}</td>"
            f"<td class=num>{total}</td><td class=num>{pct}</td></tr>"
        )
    tpct = f"{100.0 * grand_m / grand_t:.0f}%" if grand_t else "—"
    return (
        f"<h3>Per file &mdash; {len(versions)} loaded</h3>"
        "<table class=card-table><tr><th scope=col>File</th><th scope=col>Matched</th>"
        "<th scope=col>Activities</th><th scope=col>%</th></tr>"
        f"{''.join(rows)}"
        f"<tr><td><b>All files</b></td><td class=num><b>{grand_m}</b></td>"
        f"<td class=num><b>{grand_t}</b></td><td class=num><b>{tpct}</b></td></tr></table>"
    )


_OP_TEXT = {
    "EQUALS": "=",
    "DOES_NOT_EQUAL": "≠",
    "IS_GREATER_THAN": ">",
    "IS_LESS_THAN": "<",
    "IS_GREATER_THAN_OR_EQUAL_TO": "≥",
    "IS_LESS_THAN_OR_EQUAL_TO": "≤",
    "CONTAINS": "contains",
    "DOES_NOT_CONTAIN": "does not contain",
    "CONTAINS_EXACTLY": "contains exactly",
    "IS_WITHIN": "is within",
    "IS_NOT_WITHIN": "is not within",
    "IS_ANY_VALUE": "is any value",
}


def _criteria_text(node: SavedCriterion | None) -> str:
    """A compact, human-readable rendering of a saved filter's criteria tree (for chips/banner)."""
    if node is None:
        return "all tasks"
    if node.is_branch:
        parts = [_criteria_text(c) for c in node.children]
        joiner = " AND " if node.operator == "AND" else " OR "
        return "(" + joiner.join(parts) + ")" if len(parts) > 1 else (parts[0] if parts else "all")

    def operand_text(op: SavedOperand) -> str:
        if op.kind == "null":
            return "(none)"
        if op.kind == "prompt":
            return f"?[{op.text or 'prompt'}]"
        if op.kind == "field":
            return f"[{op.text}]"
        return op.text or ""

    ops = ", ".join(operand_text(o) for o in node.operands)
    verb = _OP_TEXT.get(node.operator, node.operator)
    return f"{node.field or '?'} {verb} {ops}".rstrip()


def _saved_prompt_form(saved: SavedFilter, answers: dict[str, str], mode: str) -> str:
    """MS Project's interactive-filter prompt, as a form: one input per prompt label; the filter is
    applied only when every prompt is answered (the route re-renders this until then)."""
    labels = required_prompts(saved)
    rows = []
    for i, label in enumerate(labels):
        val = _e(answers.get(label, ""))
        rows.append(
            f"<label style='display:block;margin:.3em 0'>{_e(label)} "
            f'<input type=text name="prompt_{i}" value="{val}" '
            "placeholder='e.g. 2026-05-24 / 3d / 42'></label>"
        )
    return (
        "<div class=panel><h2>Filter needs values</h2>"
        f"<p class=muted>“{_e(saved.display_name)}” is an interactive filter — MS Project asks "
        "for these values when it is applied. Dates accept ISO (2026-05-24), durations accept "
        "3d / 16h, numbers plain.</p>"
        "<form method=get action=/groups>"
        f'<input type=hidden name=saved_filter value="{_e(saved.name)}">'
        f'<input type=hidden name=mode value="{_e(mode)}">'
        f"{''.join(rows)}"
        "<button type=submit>Apply filter</button></form></div>"
    )


def _saved_views_panel(st: SessionState, schedules: list[Schedule]) -> str:
    """Feature #10's saved-views controls: the MS Project saved FILTER picker (A-Z), the
    reduce/highlight mode, and the saved GROUP picker (A-Z) — applied session-wide."""
    filters = saved_filters_union(schedules)
    groups = saved_groups_union(schedules)
    if not filters and not groups:
        return (
            "<div class=panel><h2>MS Project saved views</h2><p class=muted>None of the loaded "
            "files carries saved filters or groups (they load from native .mpp files; MSPDI/XER "
            "formats do not define them).</p></div>"
        )
    active_f = st.active_saved_filter
    fopts = ['<option value="">(no saved filter)</option>']
    for f in filters:
        marks = []
        if f.is_interactive:
            marks.append("…asks values")
        if not f.is_task_filter:
            marks.append("resource")
        suffix = f" ({', '.join(marks)})" if marks else ""
        sel = " selected" if active_f is not None and f.name == active_f.name else ""
        fopts.append(f'<option value="{_e(f.name)}"{sel}>{_e(f.display_name)}{_e(suffix)}</option>')
    gopts = ['<option value="">(no group — file order)</option>']
    for g in groups:
        gsel = (
            " selected"
            if st.active_saved_group is not None and g.name == st.active_saved_group.name
            else ""
        )
        gopts.append(f'<option value="{_e(g.name)}"{gsel}>{_e(g.display_name)}</option>')
    reduce_ck = " checked" if st.filter_mode != "highlight" else ""
    hi_ck = " checked" if st.filter_mode == "highlight" else ""
    active_bits = []
    if active_f is not None:
        answered = ""
        if st.saved_filter_prompts:
            answered = " — " + ", ".join(
                f"{_e(k)} = {_e(str(v))}" for k, v in st.saved_filter_prompts.items()
            )
        active_bits.append(
            f"<p class=muted>Active saved filter: <b>{_e(active_f.display_name)}</b> "
            f"<span class=dp-chip>{_e(_criteria_text(active_f.criteria))}</span>{answered}</p>"
        )
    if st.active_saved_group is not None:
        active_bits.append(
            f"<p class=muted>Active group: <b>{_e(st.active_saved_group.display_name)}</b> "
            "(ordering/banding only — metric populations never change).</p>"
        )
    return f"""
<div class=panel><h2>MS Project saved views</h2>
<p class=muted>The filters and groups saved INSIDE the loaded .mpp files, reproduced faithfully
(A-Z). A saved filter scopes <b>every metric on every page</b> in <b>Reduce</b> mode; in
<b>Highlight</b> mode it only marks the matching tasks and metrics stay whole-schedule.</p>
<form method=get action=/groups class=viz-controls>
<label>Saved filter: <select name=saved_filter data-no-i18n>{"".join(fopts)}</select></label>
<span class=opt-group><b>Mode</b>
<label><input type=radio name=mode value=reduce{reduce_ck}> Reduce (scope metrics)</label>
<label><input type=radio name=mode value=highlight{hi_ck}> Highlight (mark only)</label></span>
<label>Saved group: <select name=saved_group data-no-i18n>{"".join(gopts)}</select></label>
<button type=submit>Apply saved views</button>
</form>
{"".join(active_bits)}</div>"""


def _saved_group_table(sch: Schedule, group: SavedGroup) -> str:
    """The active saved group realized on the preview file: one row per bucket (in the group's
    own order), with the bucket's activity count and completion split. Presentation only."""
    buckets = group_by_clauses(sch, group)
    by_id = sch.tasks_by_id
    rows = []
    for label, uids in buckets[:200]:
        tasks = [by_id[u] for u in uids if u in by_id]
        n = len(tasks)
        done = sum(1 for t in tasks if t.percent_complete >= 100.0)
        rows.append(
            f"<tr><td>{_e(label)}</td><td class=num>{n}</td>"
            f"<td class=num>{done}</td><td class=num>{n - done}</td></tr>"
        )
    more = (
        f"<p class=muted>… and {len(buckets) - 200} more buckets (showing the first 200).</p>"
        if len(buckets) > 200
        else ""
    )
    return (
        f"<div class=panel><h2>Grouped preview — {_e(group.display_name)}</h2>"
        "<p class=muted>Buckets in the group's own order (each clause's direction honored; "
        "MS Project semantics). Grouping never changes a metric.</p>"
        '<div style="overflow-x:auto"><table class=data-table><thead><tr><th>Group</th>'
        "<th>Activities</th><th>Complete</th><th>Remaining</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>{more}</div>"
    )


def _groups_body(
    versions: list[tuple[str, Schedule]],
    version_key: str,
    sch: Schedule,
    criteria: list[Criterion],
    breakdown: str,
    applied: bool = False,
    st: SessionState | None = None,
) -> str:
    """The Groups & Filters view: build a filter that scopes EVERY metric on EVERY page across ALL
    loaded files (ADR-0104), see its reach per file, and preview the scorecard/breakdown on one
    file. ``applied`` marks whether ``criteria`` is the live session scope (vs a URL preview)."""
    form = _groups_form(versions, version_key, sch, criteria, breakdown)
    sub = filter_schedule(sch, criteria) if criteria else sch

    if criteria:

        def _chip(field: str, value: str | Sequence[str]) -> str:
            vals = _criterion_value_list(value)
            shown = (
                "(populated)"
                if not vals
                else _expandable_more(_e(", ".join(vals[:4])), [_e(v) for v in vals[4:]])
            )
            return f'<span class="dp-chip">{_e(field)} = {shown}</span>'

        chips = " ".join(_chip(f, v) for f, v in criteria)
        matched, total = len(non_summary(sub)), len(non_summary(sch))
        live = (
            "This filter is the session-wide scope &mdash; applied to "
            if applied
            else "Not applied yet &mdash; <b>Apply to all pages</b> to scope "
        )
        summary = (
            f"<div class=panel><h2>Active scope</h2><p>{chips}</p>"
            f"<p class=muted>{live}<b>every metric on every page</b>, for all loaded files "
            "(logical AND across rows; values OR'd within a row).</p>"
            f"<p class=muted><b>{matched}</b> of {total} activities match in the preview file.</p>"
            f"{_groups_per_file_table(versions, criteria)}</div>"
        )
    elif st is not None and st.active_saved_filter is not None:
        # a SAVED filter owns the session scope (mutual exclusivity with the field rows)
        saved = st.active_saved_filter
        matched_set = st.highlight_uids(sch) if st.filter_mode == "highlight" else None
        if matched_set is None:
            scoped_n = len(non_summary(st.scope(sch)))
            reach = (
                f"<b>{scoped_n}</b> of {len(non_summary(sch))} activities remain in the preview "
                "file (Reduce mode — every metric on every page is scoped)."
            )
        else:
            reach = (
                f"<b>{len(matched_set)}</b> of {len(sch.tasks)} tasks match in the preview file "
                "(Highlight mode — matches are only MARKED; metrics stay whole-schedule)."
            )
        summary = (
            f"<div class=panel><h2>Active scope</h2><p>Saved filter "
            f"<b>{_e(saved.display_name)}</b> "
            f'<span class="dp-chip">{_e(_criteria_text(saved.criteria))}</span></p>'
            f"<p class=muted>{reach}</p></div>"
        )
    else:
        summary = (
            f"<div class=panel><h2>Active scope</h2><p class=muted>No filter &mdash; every page uses "
            f"the full schedules ({len(non_summary(sch))} activities in the preview file). Build a "
            "filter above and <b>Apply to all pages</b> to scope the whole tool.</p></div>"
        )

    if not non_summary(sub):
        scorecard = "<div class=panel><p class=muted>No activities match this filter.</p></div>"
    else:
        makeup = compute_activity_makeup(sub)
        cards = _stat_cards(
            [
                ("Activities", str(makeup.total)),
                ("Normal", str(makeup.normal)),
                ("Milestones", str(makeup.milestones)),
                ("Complete", str(makeup.complete)),
                ("In progress", str(makeup.in_progress)),
                ("Planned", str(makeup.planned)),
            ]
        )
        try:
            dcma = compute_dcma14(sub)
            table = _metric_scorecard_table(dcma)
        except CPMError as exc:
            table = f'<p class="notice err">Network for this scope cannot be solved: {_e(exc)}</p>'
        preview_name = _e(sch.source_file or sch.name)
        scorecard = (
            f"<div class=panel><h2>Preview &mdash; metric scorecard for {preview_name}</h2>"
            f"<p class=muted>The same scope drives this file's full report and every other page.</p>"
            f"{cards}{table}</div>"
        )

    breakdown_html = (
        _groups_breakdown_table(sub, breakdown)
        if breakdown and breakdown in available_fields(sch)
        else ""
    )
    # the session-wide SAVED group realized on the (scoped) preview file — presentation only
    group_html = ""
    if st is not None and st.active_saved_group is not None:
        group_html = _saved_group_table(st.scope(sch), st.active_saved_group)
    tip = _user_tip(
        "Build a filter here and <b>Apply to all pages</b> to scope <b>every</b> metric on "
        "<b>every</b> page across all loaded files at once. Rows are AND-ed together; the values "
        "within a row are OR-ed."
    )
    return tip + form + summary + group_html + scorecard + breakdown_html


def _how_stable_header(ev: PathEvolution) -> str:
    """Chapter 04 "How stable is the path" (ADR-0200): the data-driven takeaway + a churn KPI strip
    + the Latest-critical-path and Total-churn bars, from the per-version critical-path snapshots.
    Every figure is read from the evolution the page already computed (no engine math)."""
    snaps = ev.snapshots
    n_ver = len(snaps)
    updates = max(n_ver - 1, 1)
    entered = sum(len(s.entered) for s in snaps[1:])
    left = sum(len(s.left) for s in snaps[1:])
    latest = snaps[-1]
    crit_now = len(latest.critical)
    moves = [s.finish_delta_days for s in snaps[1:] if s.finish_delta_days is not None]
    net = sum(moves) if moves else None
    churn = entered + left

    def _acts(x: int) -> str:
        return "activity" if x == 1 else "activities"

    if churn == 0:
        stability = "held completely steady"
    elif churn <= updates:
        stability = "stayed largely stable"
    else:
        stability = "churned"
    if net is None:
        fin = ""
    elif net > 0:
        fin = f", and the finish slipped {net} calendar day{'s' if net != 1 else ''}"
    elif net < 0:
        fin = f", and the finish pulled in {abs(net)} calendar day{'s' if net != -1 else ''}"
    else:
        fin = ", while the finish held"
    takeaway = (
        f"Across {n_ver} versions the critical path {stability} — {entered} {_acts(entered)} "
        f"entered it and {left} left{fin}."
    )

    kpi = _stat_cards(
        [
            ("Versions compared", str(n_ver)),
            ("Critical now", str(crit_now)),
            ("Entered (all updates)", str(entered)),
            ("Left (all updates)", str(left)),
            ("Net finish move", f"{net:+d} d" if net is not None else "—"),
            ("Churn per update", f"{churn / updates:.1f}"),
        ]
    )
    # the latest file resolves the segment activities (entered/left UIDs are matched against it)
    fkey = latest.label
    churn_entered_uids = tuple(sorted({u for s in snaps[1:] for u in s.entered}))
    churn_left_uids = tuple(sorted({u for s in snaps[1:] for u in s.left}))
    latest_bar = _status_stack(
        "Latest critical path",
        f"How the newest version's path formed — {latest.label}.",
        [("Entered", len(latest.entered), "--ok"), ("Stayed", len(latest.stayed), "--muted")],
        f"{crit_now} on the path now; {len(latest.left)} left since the prior version",
        drill=[(tuple(latest.entered), fkey), (tuple(latest.stayed), fkey)],
    )
    churn_bar = _status_stack(
        "Total churn",
        "Activities that entered vs left the critical path across every update.",
        [("Entered", entered, "--ok"), ("Left", left, "--bad")],
        f"over {updates} update{'s' if updates != 1 else ''}",
        drill=[(churn_entered_uids, fkey), (churn_left_uids, fkey)],
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{latest_bar}{churn_bar}</div>'
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
    )


def _evolution_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None = None,
    tier: str = "off",
    *,
    cf_a: int = -1,
    cf_b: int = -1,
) -> str:
    """The Critical-Path Evolution view (M18 item 7): a Bow-Wave-style stepper over the
    versions, showing the critical path and how it enters/leaves between versions. ``target``
    focuses a UniqueID (highlighted across every frame); zoom/pan controls scope the axis. ``tier``
    scopes the stepper to a driving-slack tier (secondary/tertiary/all) instead of the float
    critical path — the activities driving the focused UID (or the project finish)."""
    tier_opts = "".join(
        f'<option value="{v}"{" selected" if tier == v else ""}>{lbl}</option>'
        for v, lbl in [
            ("off", "Critical path"),
            ("secondary", f"Secondary tier (≤{DEFAULT_SECONDARY_MAX_DAYS}d slack)"),
            ("tertiary", f"Tertiary tier (≤{DEFAULT_TERTIARY_MAX_DAYS}d slack)"),
            ("all", "All tiers (colour-coded)"),
        ]
    )
    focus_form = f"""
<div class=panel><form method=get action=/evolution class=viz-controls>
Focus a specific activity across every version &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{'<a class=btn-link href="/evolution?target=">clear focus</a>' if target is not None else ""}
<label style="margin-left:1em">Path tier:
<select name=tier data-no-i18n onchange="this.form.submit()">{tier_opts}</select></label>
<span class=muted>critical / secondary / tertiary by driving slack to the focused UID (or the
project finish).</span>
</form></div>"""
    return (
        focus_form
        + f"""
<div class=panel><h2>Critical-Path Evolution</h2>
{_user_tip("The date axis is held fixed across versions, so the critical path visibly extends as the finish slips. Use <b>View entire project</b> to fit the whole timeline, and set a <b>target UID</b> to highlight one activity across every frame.")}
<p class=muted><b>Path basis (ADR-0150):</b> with a <b>focused UID</b> the path shown is the
<b>0-driving-slack chain to that UID</b> (the same set as the /path driving-slack view); with no
focus it is the <b>progress-aware critical set</b> &mdash; the source tool&rsquo;s stored Critical
flag (what MS Project shows), falling back to recomputed CPM float only when the file carries no
flag. Completed work leaves the path and is recorded below under
<b>Completed on the path</b>.</p>
<p class=muted>Step through the versions (oldest first by data date) to watch the critical
path change, drawn as a <b>Gantt</b> on a date axis held fixed across every version (so the
path visibly extends as the finish slips). Bars are colored
<b class=ev-entered>green</b> for activities that <b>entered</b> the path since the prior
version, <b class=ev-stayed>grey</b> for those that <b>stayed</b>, with a &#9650; marking a
duration change; activities that <b class=ev-left>left</b> the path appear below as dashed
ghost bars at their prior position. Every entered/left activity carries a <b>reason chip</b>
explaining <b>why</b> it moved &mdash; a new task, a duration change, a logic change, a
constraint, a completion, or a slip elsewhere consuming its float (hover the chip for the
detail). The callout reports the finish movement and the schedule-optics signals, so a path
shedding work while the finish holds steady (a slip being absorbed rather than recovered) is
visible.</p>
<div class=viz-controls>
<button id=prevEvo type=button>&#9664; Prev</button>
<span id=evoLabel class=muted></span>
<button id=nextEvo type=button>Next &#9654;</button>
<button id=evoPlay type=button>&#9654; Auto-play</button>
<label class=muted style="margin-left:1em"><input type=checkbox id=evoHideDone> hide completed</label>
<label class=muted title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input type=checkbox id=evoBarDates> dates on bars</label>
</div>
<div class=viz-controls>
<span class=muted>Zoom the date axis:</span>
<button id=evoZoomOut type=button title="zoom out">&minus;</button>
<button id=evoZoomIn type=button title="zoom in">&plus;</button>
<button id=evoPanL type=button title="pan earlier">&#9664;</button>
<button id=evoPanR type=button title="pan later">&#9654;</button>
<button id=evoZoomReset type=button title="Auto-scale to show the whole project">View entire project</button>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
</div>
<div class=viz-controls>
<label>Filter the path:
<select id=evoFilterMode>
<option value=none selected>none &mdash; whole critical path</option>
<option value=driving>driving path to the focused UID</option>
<option value=version>track one version's path</option>
<option value=movement>entered / left / stayed</option>
<option value=search>name / UID search</option>
</select></label>
<select id=evoFilterVersion style="display:none"></select>
<span id=evoFilterMovement style="display:none">
<label><input type=checkbox class=evoMove value=entered checked> entered</label>
<label><input type=checkbox class=evoMove value=stayed checked> stayed</label>
<label><input type=checkbox class=evoMove value=left checked> left</label>
</span>
<input id=evoFilterText type=search placeholder="name or UID" style="display:none">
<span id=evoFilterNote class=muted></span>
</div>
<p class=muted style="margin:.2em 0">Each row carries its grid columns &mdash; <b>%&nbsp;complete</b>,
<b>duration</b> (working days), <b>start</b> and <b>finish</b> &mdash; beside the bar.
Use <b>Focus</b> above to highlight one activity across every version.</p>
<div id=evoChart data-target="{target if target is not None else ""}"
data-tier="{tier}"></div></div>
<script src="/static/path_evolution.js"></script>"""
        + _completed_on_path_panel(schedules, cpms, target)
        + _counterfactual_panel(schedules, cpms, target, baseline_idx=cf_a, comparison_idx=cf_b)
    )


def _completed_on_path_panel(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None
) -> str:
    """Version-to-version record of path activities that COMPLETED — the operator's "what got
    done on the path month to month". Server-rendered from the page's evolution snapshots
    (ADR-0150) — the OPTIONED versions when the ADR-0251 counterfactual trace options are
    active, unlike the client-fetched stepper chart, which re-reads `/api/evolution` (no
    option params — always the stored schedule): for each version pair, the prior version's
    path activities that are complete in the newer version, with their actual finishes."""
    ev = compute_path_evolution(schedules, cpms, target_uid=target)
    basis = f"driving path to UID {target}" if target is not None else "effective critical path"
    sections: list[str] = []
    for i in range(1, len(ev.snapshots)):
        snap = ev.snapshots[i]
        prior_label = _e(ev.snapshots[i - 1].label)
        label = _e(snap.label)
        period = f"{prior_label} &rarr; {label}"
        if not snap.completed_on_path:
            sections.append(
                f"<h3>{period}</h3><p class=muted>No path activities completed this period.</p>"
            )
            continue
        by_id = schedules[i].tasks_by_id
        rows = "".join(
            f"<tr><td>{uid}</td><td>{_e(t.name if t else f'UID {uid}')}</td>"
            f"<td>{_mdY(t.actual_finish) if t is not None else '—'}</td>"
            f"<td>{round(t.percent_complete) if t is not None else 0}%</td></tr>"
            for uid in snap.completed_on_path
            for t in (by_id.get(uid),)
        )
        sections.append(
            f"<h3>{period} &mdash; {len(snap.completed_on_path)} completed on the path</h3>"
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>Actual finish</th><th scope=col>%</th></tr>{rows}</table>"
        )
    src_names = ", ".join(_e(s.source_file or s.name) for s in schedules)
    return (
        "<div class=panel><h2>Completed on the path &mdash; version to version</h2>"
        f"<p class=muted>Basis: <b>{basis}</b>. Sources ({len(schedules)} files): {src_names}. "
        "Activities that were ON the path in one version and show complete in the next &mdash; "
        "the work that actually burned down the driving chain each period.</p>"
        + "".join(sections)
        + "</div>"
    )


def _counterfactual_panel(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None,
    *,
    baseline_idx: int = -1,
    comparison_idx: int = -1,
) -> str:
    """The 'what-if' panel for a CHOSEN version pair: revert the duration/logic/constraint changes
    that took non-completed activities off the critical path, and report what the finish (and the
    target UID) would have been — isolating slip removed by changes vs progress.

    Operator 2026-07-08: the panel previously always used the LATEST two versions, so on a long
    history it only showed the tiny most-recent update (looking like "no change") and hid the
    cumulative manipulation. It now runs on ANY two files the operator picks (Baseline A vs
    Comparison B), defaulting to the two most recent, so first-vs-last reveals the real change."""
    if len(schedules) < 2:
        return ""
    n = len(schedules)
    labels = [s.source_file or s.name for s in schedules]
    # resolve the chosen pair safely (same rule as Integrity): default the two most recent, order
    # prior -> current chronologically, never collapse to one file or a negative index.
    cur = comparison_idx if 0 <= comparison_idx < n else n - 1
    base = baseline_idx if 0 <= baseline_idx < n else cur - 1
    if base == cur or not (0 <= base < n):
        base = cur - 1 if cur > 0 else cur + 1
    prior_idx, cur_idx = (base, cur) if base < cur else (cur, base)

    picker = ""
    if n > 2:

        def _opts(selected: int) -> str:
            return "".join(
                f'<option value="{i}"{" selected" if i == selected else ""}>{_e(lb)}</option>'
                for i, lb in enumerate(labels)
            )

        picker = f"""
<form method=get action=/evolution class=viz-controls style="margin:.4em 0">
<span class=muted>Compare any two of the {n} loaded versions:</span>
<label>Baseline (A) <select name=cf_a>{_opts(prior_idx)}</select></label>
<label>Comparison (B) <select name=cf_b>{_opts(cur_idx)}</select></label>
<button type=submit>Run what-if</button></form>"""

    pc = compute_path_counterfactual(
        schedules[prior_idx], schedules[cur_idx], cpms[prior_idx], cpms[cur_idx], target_uid=target
    )
    # enrich each reverted activity with its current-version fields (duration / % complete / start /
    # finish / WBS / custom) so the client table can add columns and FILTER by any of them.
    current = schedules[cur_idx]
    by_id = current.tasks_by_id
    per_day = current.calendar.working_minutes_per_day or 480
    enriched: list[dict[str, object]] = []
    if pc is not None:
        for r in pc.reverted:
            t = by_id.get(r.uid)
            row: dict[str, object] = {
                "unique_id": r.uid,
                "name": r.name,
                "why_left": r.reason,
                "change_reverted": "; ".join(r.changes),
            }
            if t is not None:
                row.update(
                    {
                        "duration_days": round(
                            t.duration_minutes / (1440 if t.duration_is_elapsed else per_day), 1
                        ),
                        "percent_complete": t.percent_complete,
                        "start": _iso_date(t.start),
                        "finish": _iso_date(t.finish),
                        "wbs": t.wbs or "",
                        "resource_names": ", ".join(t.resource_names),
                        "custom": dict(t.custom_field_map),
                    }
                )
            enriched.append(row)
    custom_labels = sorted(current.custom_field_labels)
    added_rows = _whatif_added_rows(
        schedules[prior_idx], current, cpms[prior_idx], cpms[cur_idx], target
    )
    return _render_counterfactual(
        pc,
        picker=picker,
        pair=(labels[prior_idx], labels[cur_idx]),
        enriched_rows=enriched,
        custom_labels=custom_labels,
        added_rows=added_rows,
    )


def _whatif_added_rows(
    prior: Schedule,
    current: Schedule,
    prior_cpm: CPMResult,
    current_cpm: CPMResult,
    target: int | None,
) -> list[dict[str, object]]:
    """Activities ADDED to the critical path between the chosen pair (operator 2026-07-09),
    with the engine's per-activity reason attribution (path_evolution's classifier — new task,
    own duration/logic/constraint change, or float consumed by a NAMED slip elsewhere) plus the
    current-version fields so the client table can add columns / filter / export."""
    try:
        ev = compute_path_evolution([prior, current], [prior_cpm, current_cpm], target_uid=target)
    except (CPMError, ValueError, KeyError) as exc:
        logging.getLogger("schedule_forensics").warning("what-if added-path failed: %s", exc)
        return []
    snap = ev.snapshots[-1]
    by_id = current.tasks_by_id
    per_day = current.calendar.working_minutes_per_day or 480
    rows: list[dict[str, object]] = []
    for ch in snap.entered_changes:
        row: dict[str, object] = {
            "unique_id": ch.uid,
            "name": ch.name,
            "why_entered": ch.reason,
            "detail": ch.detail,
        }
        t = by_id.get(ch.uid)
        if t is not None:
            row.update(
                {
                    "duration_days": round(
                        t.duration_minutes / (1440 if t.duration_is_elapsed else per_day), 1
                    ),
                    "percent_complete": t.percent_complete,
                    "start": _iso_date(t.start),
                    "finish": _iso_date(t.finish),
                    "wbs": t.wbs or "",
                    "resource_names": ", ".join(t.resource_names),
                    "custom": dict(t.custom_field_map),
                }
            )
        rows.append(row)
    return rows


def _render_counterfactual(
    pc: PathCounterfactual | None,
    *,
    picker: str = "",
    pair: tuple[str, str] | None = None,
    enriched_rows: list[dict[str, object]] | None = None,
    custom_labels: list[str] | None = None,
    added_rows: list[dict[str, object]] | None = None,
) -> str:
    """Render the counterfactual panel from a computed result (split out for direct testing)."""
    pair_txt = (
        f"between <b data-no-i18n>{_e(pair[0])}</b> and <b data-no-i18n>{_e(pair[1])}</b>"
        if pair
        else "between the two chosen versions"
    )
    # Work ADDED to the critical path (operator 2026-07-09) — the mirror of the reverted list:
    # every activity that ENTERED the path between the pair, with the engine's reason attribution.
    added_html = ""
    if added_rows is not None:
        a_attr = _e(pair[0]) if pair else ""
        b_attr = _e(pair[1]) if pair else ""
        added_blob = json.dumps({"rows": added_rows, "customLabels": custom_labels or []}).replace(
            "<", "\\u003c"
        )
        added_body = (
            f'<div id=whatifAddedTable data-a="{a_attr}" data-b="{b_attr}"></div>'
            f'<script type="application/json" id=whatifAddedData>{added_blob}</script>'
            if added_rows
            else f"<p class=muted>No activity entered the critical path {pair_txt}.</p>"
        )
        added_html = f"""
<div class=panel><h2>What-if: work added to the critical path</h2>
<p class=muted>The mirror of the list above: activities that <b>entered</b> the critical (driving)
path {pair_txt}. Each carries the engine's reason — a <b>new</b> activity, its <b>own</b> duration
/ logic / constraint change, or <b>float consumed</b> by a named slip elsewhere. Work joining the
path is where the schedule's risk is moving: a path that churns member activities version over
version is unstable even when the finish date holds.</p>
{added_body}</div>"""
    intro = f"""
<div class=panel><h2>What-if: work removed from the critical path</h2>
<p class=muted>This runs on the <b>one pair you pick</b> {pair_txt} — not lumped across the whole
history. Some activities leave the critical (driving) path between these two versions. A
<b>completed</b> activity leaving is real progress (excluded here). An unchanged activity leaving
<b>gained float</b> &mdash; a slip elsewhere made another chain longer, so this one is no longer on
the longest path (nothing about it changed). But an activity that leaves because <b>its own
remaining duration was cut, a logic link was removed, or a constraint was dropped</b> can make a
slipping finish look recovered. Below, those specific changes (on non-completed activities) are
reverted to their prior values and the schedule re-run &mdash; the gap is schedule time the
<b>changes</b>, not progress, removed from the path.</p>{picker}"""
    if pc is None:
        return (
            intro + f"<p class=muted>No non-completed activity left the critical path {pair_txt} "
            "&mdash; nothing to revert. Pick a wider pair (e.g. the first vs the latest version) "
            "to see cumulative change.</p></div>"
            + added_html
            + '<script src="/static/whatif.js"></script>'
        )

    def _delta(days: int) -> str:
        if days > 0:
            return f"<b class=fail>+{days} day(s) later</b>"
        if days < 0:
            return f"<b class=pass>{days} day(s) earlier</b>"
        return "<b>no change</b>"

    # interactive reverted-changes table: filter by any field + add standard/custom columns + Excel
    # export (operator 2026-07-08). Rows carry each activity's current fields (embedded server-side).
    # Fall back to the base columns from pc.reverted when no enriched rows were supplied (direct
    # callers / tests) so the table always lists the reverted activities.
    rows_data = (
        enriched_rows
        if enriched_rows is not None
        else [
            {
                "unique_id": r.uid,
                "name": r.name,
                "why_left": r.reason,
                "change_reverted": "; ".join(r.changes),
            }
            for r in pc.reverted
        ]
    )
    whatif_blob = json.dumps({"rows": rows_data, "customLabels": custom_labels or []}).replace(
        "<", "\\u003c"
    )
    a_attr = _e(pair[0]) if pair else ""
    b_attr = _e(pair[1]) if pair else ""
    table_html = (
        f'<div id=whatifTable data-a="{a_attr}" data-b="{b_attr}"></div>'
        f'<script type="application/json" id=whatifData>{whatif_blob}</script>'
    )
    body = [intro]
    if pc.reverted:
        finish_line = (
            f"Computed finish is <b>{_e(pc.actual_finish)}</b>; had these "
            f"{len(pc.reverted)} change(s) not been made it would be "
            f"<b>{_e(pc.counterfactual_finish)}</b> ({_delta(pc.finish_delta_days)})."
        )
        if pc.uncomputable:
            finish_line = (
                "Reverting these changes produced an unsolvable network (a logic cycle), so the "
                "counterfactual finish cannot be computed; the changed activities are named below."
            )
        body.append(f"<p>{finish_line}</p>")
        if pc.target_uid is not None and pc.target_delta_days is not None:
            body.append(
                f"<p>Target activity <b>UID {pc.target_uid}: {_e(pc.target_name or '')}</b> "
                f"finishes <b>{_e(pc.target_actual_finish or '')}</b> now; without the changes "
                f"it would finish <b>{_e(pc.target_counterfactual_finish or '')}</b> "
                f"({_delta(pc.target_delta_days)}).</p>"
            )
        elif pc.target_uid is not None:
            body.append(
                f"<p class=muted>Target UID {pc.target_uid} is not in both the current and "
                "counterfactual networks, so its individual impact is not shown.</p>"
            )
        body.append(table_html)
    if pc.gained_float:
        names = "; ".join(f"{g.name} (UID {g.uid})" for g in pc.gained_float)
        body.append(
            f"<p class=muted><b>Gained float (no change to revert):</b> {_e(names)} left the path "
            "because a slip elsewhere lengthened another chain, freeing this one's float &mdash; "
            "not because the activity itself was altered.</p>"
        )
    body.append("</div>")
    body.append(added_html)
    body.append('<script src="/static/whatif.js"></script>')
    return "".join(body)


def _volatility_data(schedules: list[Schedule], cpms: list[CPMResult]) -> dict[str, object]:
    """The critical-path volatility dataset (operator 2026-07-09): per-version membership of
    the effective critical set for every activity that was EVER on the path, plus the derived
    stability measures the ten visuals draw — per-task tenure / longest streak / on-off flips,
    per-pair Jaccard similarity and stayed/entered/left splits, and the overall stability
    index (mean Jaccard). Everything derives from the loaded versions' critical sets — the
    same effective-critical basis (stored Critical flag, CPM fallback) every other page uses."""
    from schedule_forensics.engine.path_evolution import effective_critical_set

    sets = [effective_critical_set(s, c) for s, c in zip(schedules, cpms, strict=True)]
    labels = [s.source_file or s.name for s in schedules]
    dates = [s.status_date.date().isoformat() if s.status_date else None for s in schedules]
    ever: list[int] = []
    seen: set[int] = set()
    for cs in sets:
        for uid in sorted(cs):
            if uid not in seen:
                seen.add(uid)
                ever.append(uid)
    # latest-known name per uid (newest version wins)
    names: dict[int, str] = {}
    for sch in schedules:
        for t in sch.tasks:
            if t.unique_id in seen:
                names[t.unique_id] = t.name

    tasks: list[dict[str, Any]] = []
    for uid in ever:
        member = [1 if uid in cs else 0 for cs in sets]
        streak = best = 0
        flips = 0
        for i, m in enumerate(member):
            streak = streak + 1 if m else 0
            best = max(best, streak)
            if i and m != member[i - 1]:
                flips += 1
        tasks.append(
            {
                "uid": uid,
                "name": names.get(uid, f"UID {uid}"),
                "member": member,
                "tenure": sum(member),
                "streak": best,
                "flips": flips,
            }
        )
    # most-tenured first, then fewest flips, then uid — the leaderboard/heatmap order
    tasks.sort(key=lambda t: (-t["tenure"], t["flips"], t["uid"]))

    pairs: list[dict[str, object]] = []
    for i in range(1, len(sets)):
        a, b = sets[i - 1], sets[i]
        union = a | b
        entered_uids = sorted(b - a)  # newly on the path in version i (present in the "to" file)
        left_uids = sorted(a - b)  # dropped off the path (present in the "from" file)
        stayed, entered, left = len(a & b), len(entered_uids), len(left_uids)
        pairs.append(
            {
                "from": labels[i - 1],
                "to": labels[i],
                "jaccard": round(len(a & b) / len(union), 3) if union else None,
                "stayed": stayed,
                "entered": entered,
                "left": left,
                # the activity IDs behind the entry/exit counts, so the waterfall bars can drill
                "entered_uids": entered_uids,
                "left_uids": left_uids,
            }
        )
    jaccards = [p["jaccard"] for p in pairs if p["jaccard"] is not None]
    return {
        "versions": [
            {"label": lb, "status_date": d, "critical": len(cs)}
            for lb, d, cs in zip(labels, dates, sets, strict=True)
        ],
        "tasks": tasks,
        "pairs": pairs,
        # the newest version's label — the drill's data-file for the leaderboard/dwell bars (whose
        # activities are "ever on the path"; those present in the latest version resolve there).
        "latest": labels[-1] if labels else "",
        "stability": (
            round(sum(jaccards) / len(jaccards), 3) if jaccards else None  # type: ignore[arg-type]
        ),
    }


def _volatility_body(schedules: list[Schedule], cpms: list[CPMResult]) -> str:
    """The CP Volatility page shell: intro framed to GAO/DCMA best practice, the master
    stepper, ten chart mounts, the scoreboard, and the embedded dataset volatility.js reads."""
    data = _volatility_data(schedules, cpms)
    blob = json.dumps(data).replace("<", "\\u003c")
    return f"""
<div class=panel><h2>Critical-Path Volatility &mdash; membership churn across versions</h2>
<p class=muted>The critical path should be <b>stable</b>: GAO's Schedule Assessment Guide (Best
Practice 6 — maintain a valid critical path) and the DCMA 14-point construct (the critical-path
test and CPLI) both treat an erratic controlling chain as a schedule-health failure. A path that
churns member activities version over version means the network's logic is being rewired between
updates — either real replanning that deserves a change log, or edits that quietly move the
controlling chain away from slipping work. The ten visuals below answer two questions from the
loaded files: <b>which activities stayed on the critical path longest</b>, and <b>which jumped
off and on over time</b> (every figure derives from the same effective-critical sets the other
pages use; nothing is fabricated).</p>
<div class=viz-controls>
<button id=volPrev type=button>&#9664; Prev</button>
<span id=volLabel class=muted data-no-i18n></span>
<button id=volNext type=button>Next &#9654;</button>
<button id=volPlay type=button>&#9654; Play</button>
<a class=btn-link href="/export/xlsx/volatility">&#11015; Excel (scoreboard)</a>
</div></div>
<div class=mosaic id=volGrid>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the overall stability index — the average Jaccard similarity of consecutive critical paths (100% = the same path every update).\n\nHOW TO READ: GAO/DCMA expect a largely stable controlling chain; below ~70% the network is being rewired between updates.\n\nDECIDE: whether to ask for the change log before accepting the latest update.">Stability gauge</h3></div><div class=chart-host id=volGauge></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: path similarity between each consecutive pair of versions (Jaccard %).\n\nHOW TO READ: dips are the updates where the controlling chain was rewired — cross-reference those updates with the Schedule Integrity findings.\n\nDECIDE: which update to interrogate for logic/duration edits.">Churn timeline (Jaccard %)</h3></div><div class=chart-host id=volChurn></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: per update — how many activities stayed on, joined, and left the critical path.\n\nHOW TO READ: joined bars up, left bars down; a healthy schedule shows small bars (progress-driven turnover), not tall ones.\n\nDECIDE: which update churned the most members.">Entry / exit waterfall</h3></div><div class=chart-host id=volFlow></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the composition of each version's path — the share carried over vs newly joined.\n\nHOW TO READ: a mostly-'stayed' area is a settled plan; a growing 'entered' share is instability.\n\nDECIDE: whether the path is converging or churning over time.">Path composition (stayed vs entered)</h3></div><div class=chart-host id=volArea></div></section>
<section class="tile panel tile-wide"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the presence matrix — one row per activity ever on the critical path, one column per version; a filled cell = on the path that version. The stepper highlights the animated version.\n\nHOW TO READ: long unbroken rows are the stable backbone; gap-toothed rows are the jumpers.\n\nDECIDE: which rows deserve a 'why did this change?' interrogation.">Membership heatmap</h3></div><div class=chart-host id=volHeatmap></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the activities that spent the most versions on the critical path.\n\nHOW TO READ: these carry the schedule — the true backbone of the finish date.\n\nDECIDE: where sustained management attention belongs.">Tenure leaderboard</h3></div><div class=chart-host id=volTenure></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: how long activities typically stay on the path (distribution of versions-on-path).\n\nHOW TO READ: a healthy path skews long (stable membership); a spike at 1 version means most members blink on and off.\n\nDECIDE: whether churn is a few bad actors or systemic.">Dwell histogram</h3></div><div class=chart-host id=volDwell></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the biggest jumpers — activities ranked by on/off flips.\n\nHOW TO READ: an activity that repeatedly leaves and rejoins the controlling chain usually marks logic being toggled around it.\n\nDECIDE: exactly which activities' predecessors/durations to audit across updates.">Jumper leaderboard (on/off flips)</h3></div><div class=chart-host id=volJumpers></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: on-path intervals for the top jumpers as timeline strips (filled = on the path).\n\nHOW TO READ: aligned breaks across many strips point at ONE update that rewired the chain; scattered breaks are activity-level toggling.\n\nDECIDE: whether to investigate an update or an activity.">Jumper timelines</h3></div><div class=chart-host id=volStrips></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the animated stayed/entered/left transition between the stepper's current pair of versions, as proportional ribbons.\n\nHOW TO READ: a thick 'stayed' ribbon is continuity; thick 'entered'/'left' ribbons mark a rewired update.\n\nDECIDE: step through the pairs to find the update that moved the chain.">Transition flow (animated)</h3></div><div class=chart-host id=volRibbon></div></section>
</div>
<div class=panel><h2>Volatility scoreboard</h2>
<p class=muted>Every activity that was ever on the critical path — versions on path, longest
unbroken streak, and on/off flips (click a column header to sort; the Excel export carries the
full membership vector).</p>
<div id=volTable></div></div>
<script type="application/json" id=volData>{blob}</script>
<script src="/static/volatility.js"></script>"""


def _performance_data(
    schedules: list[Schedule], cpms: list[CPMResult], file: str
) -> dict[str, object]:
    """The Performance-Summary dataset (operator 2026-07-10): the per-version G1-G5 series for
    the SELECTED file (default: the newest version) plus the G6/G7 portfolio quad points for
    EVERY loaded version. Every figure comes from the engine's performance_summary /
    bei / hmi / evm functions — the same single sources of truth the rest of the tool cites."""
    from dataclasses import asdict

    from schedule_forensics.engine.path_evolution import effective_critical_set

    labels = [s.source_file or s.name for s in schedules]
    sel = labels.index(file) if file in labels else len(schedules) - 1
    sch, cpm = schedules[sel], cpms[sel]
    critical = frozenset(effective_critical_set(sch, cpm))

    census = work_to_go_census(sch, critical)
    flow = activity_flow(sch)
    burden = workoff_burden(sch)
    drm = duration_ratio(sch)

    # per-version G1-G5 series for the master stepper (operator 2026-07-10: "automate" the
    # Performance visuals like the Mission wall) — each animation step redraws every chart
    # from THIS version's series and captions its file name (provenance per iteration).
    per_version: list[dict[str, object]] = []
    for s_i, c_i in zip(schedules, cpms, strict=True):
        crit_v = critical if s_i is sch else frozenset(effective_critical_set(s_i, c_i))
        cen_v = work_to_go_census(s_i, crit_v)
        flow_v = activity_flow(s_i)
        bur_v = workoff_burden(s_i)
        drm_v = duration_ratio(s_i)
        per_version.append(
            {
                "label": s_i.source_file or s_i.name,
                "status_date": s_i.status_date.date().isoformat() if s_i.status_date else None,
                "status_month": flow_v.status_month,
                "census": [asdict(m) for m in cen_v.months],
                "flow": [asdict(m) for m in flow_v.months],
                "burden": [asdict(m) for m in bur_v.months],
                "drm": {
                    "points": [asdict(pt) for pt in drm_v.points],
                    "bins": [asdict(b) for b in drm_v.bins],
                    "min": drm_v.drm_min,
                    "avg": drm_v.drm_avg,
                    "max": drm_v.drm_max,
                    "n": drm_v.n,
                    "excluded": drm_v.n_excluded,
                },
            }
        )

    quads: list[dict[str, object]] = []
    for i, (s, c) in enumerate(zip(schedules, cpms, strict=True)):
        crit_i = critical if i == sel else frozenset(effective_critical_set(s, c))
        snap = to_go_snapshot(s, crit_i)
        prior_status = schedules[i - 1].status_date if i > 0 else None
        # HMI is informational (its status is ALWAYS NOT_APPLICABLE by design) — the genuine
        # "no qualifying period/population" case is population == 0, so gate on that instead.
        hmi = compute_hmi(s, prior_status)["hmi_tasks"]
        evm = compute_evm_indices(s)
        cei = evm["cei_finish"]
        bei = compute_bei(s)
        quads.append(
            {
                "label": labels[i],
                "hmi": None if hmi.population == 0 else hmi.value,
                # cei_finish is a PERCENT (0-100); the quad plots 0-1 like HMI, so rescale
                "cei": (
                    None
                    if cei.status is CheckStatus.NOT_APPLICABLE or cei.value is None
                    else round(cei.value / 100.0, 3)
                ),
                "bei": None if bei.status is CheckStatus.NOT_APPLICABLE else bei.value,
                "start_ratio": snap.start_ratio,
                "finish_ratio": snap.finish_ratio,
                "cp_share": snap.critical_share,
                "tm_to_go": snap.tm_to_go,
                "critical_to_go": snap.critical_to_go,
                "baselined_to_start_remaining": snap.baselined_to_start_remaining,
                "scheduled_to_start_to_go": snap.scheduled_to_start_to_go,
                "baselined_to_finish_remaining": snap.baselined_to_finish_remaining,
                "scheduled_to_finish_to_go": snap.scheduled_to_finish_to_go,
            }
        )

    return {
        "version": labels[sel],
        "versions": labels,
        "cursor": sel,
        "per_version": per_version,
        "status_month": flow.status_month,
        "truncated": census.truncated or flow.truncated or burden.truncated,
        "census": [asdict(m) for m in census.months],
        "flow": [asdict(m) for m in flow.months],
        "burden": [asdict(m) for m in burden.months],
        "drm": {
            "points": [asdict(p) for p in drm.points],
            "bins": [asdict(b) for b in drm.bins],
            "min": drm.drm_min,
            "avg": drm.drm_avg,
            "max": drm.drm_max,
            "n": drm.n,
            "excluded": drm.n_excluded,
        },
        "quads": quads,
    }


def _how_we_execute_header(sch: Schedule) -> str:
    """Chapter 07 "How we execute" (ADR-0205): the data-driven takeaway + an execution-quality
    KPI strip + the baseline-pace and duration-performance bars, from the same throughput and
    duration-ratio functions the page charts (compute_bei / duration_ratio / activity makeup —
    no new math). Anchored on the latest loaded version."""
    makeup = compute_activity_makeup(sch)
    total = makeup.total or 1
    complete_pct = 100.0 * makeup.complete / total
    bei = compute_bei(sch)
    kept = bei.count  # completed among the baselined-due
    missed = max(bei.population - bei.count, 0)  # due but not finished on the baseline
    drm = duration_ratio(sch)

    lead = (
        f"The project has finished {makeup.complete} of {makeup.total} activities "
        f"({complete_pct:.0f}%)"
    )
    if bei.population == 0:
        takeaway = f"{lead}; no work is yet baselined-due to measure the execution pace."
    else:
        if bei.value >= 1.0:
            pace = f"baselined-due work is finishing at BEI {bei.value:.2f} — on or ahead of the baseline pace"
        elif bei.value >= 0.95:
            pace = f"baselined-due work is finishing at BEI {bei.value:.2f} — just behind the baseline pace"
        else:
            pace = (
                f"baselined-due work is finishing at BEI {bei.value:.2f} — behind the baseline pace"
            )
        if drm.drm_avg is None:
            dur = ""
        elif drm.drm_avg > 1.05:
            dur = f", and completed work ran {drm.drm_avg:.2f}x its planned duration"
        elif drm.drm_avg < 0.95:
            dur = f", and completed work beat its plan at {drm.drm_avg:.2f}x planned duration"
        else:
            dur = f", and completed work ran close to plan ({drm.drm_avg:.2f}x planned duration)"
        takeaway = f"{lead}; {pace}{dur}."

    kpi = _stat_cards(
        [
            ("Activities complete", f"{makeup.complete} / {makeup.total}"),
            ("Complete", f"{complete_pct:.0f}%"),
            ("BEI (throughput)", f"{bei.value:.2f}" if bei.population else "—"),
            (
                "Duration ratio (avg)",
                f"{drm.drm_avg:.2f}x" if drm.drm_avg is not None else "—",
            ),
            ("Missed the baseline", str(missed) if bei.population else "—"),
            ("Still to go", str(makeup.total - makeup.complete)),
        ]
    )
    pace_bar = _status_stack(
        "Baseline pace (BEI)",
        "Activities baselined to finish by the data date — kept pace vs missed the baseline.",
        [("Kept pace", kept, "--ok"), ("Missed", missed, "--bad")],
        f"BEI {bei.value:.2f} over {bei.population} baselined-due"
        if bei.population
        else "no baselined-due activities yet",
    )
    # completed-task duration bands: under (<0.95x) / on-target (0.95-1.05x) / over (>1.05x)
    under = sum(1 for p in drm.points if p.drm < 0.95)
    ontgt = sum(1 for p in drm.points if 0.95 <= p.drm <= 1.05)
    over = sum(1 for p in drm.points if p.drm > 1.05)
    dur_bar = _status_stack(
        "Duration performance",
        "Completed activities by how their actual duration compared to their baseline.",
        [
            ("Under plan", under, "--ok"),
            ("On target", ontgt, "--muted"),
            ("Over plan", over, "--bad"),
        ],
        f"{drm.n} completed with a baseline"
        + (f"; {drm.n_excluded} lack one" if drm.n_excluded else ""),
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{pace_bar}{dur_bar}</div>'
    )


def _performance_body(schedules: list[Schedule], cpms: list[CPMResult], file: str) -> str:
    """The Performance-Summary page shell: version picker, the thirteen chart mounts (G1-G7 of
    the operator's reference workbook), the DRM stat chips, and the embedded dataset
    performance.js reads. Every chart carries a hover explainer (viz-hint) like the rest of
    the tool."""
    data = _performance_data(schedules, cpms, file)
    blob = json.dumps(data).replace("<", "\\u003c")
    versions = cast(list[str], data["versions"])
    sel = cast(str, data["version"])
    opts = "".join(
        f'<option value="{_e(v)}"{" selected" if v == sel else ""}>{_e(v)}</option>'
        for v in versions
    )
    trunc_note = (
        "<p class=muted>&#9888; The month axis hit the 30-year safety cap; the earliest months "
        "are shown and the remainder truncated (check the file for corrupt far-future dates).</p>"
        if data["truncated"]
        else ""
    )
    intro = _explain(
        "The seven graph families of the Performance Analysis Summary workbook, recreated "
        "live from the loaded schedule(s): a monthly census of where the remaining work sits "
        "(G1), the bow-wave of activity starts and finishes against the baseline (G2), the "
        "BEI/HMI execution-index curves (G3), the workoff burden of past-due baseline work "
        "(G4), the duration-ratio S-curve and histogram (G5), and three portfolio quad charts "
        "with one dot per loaded version (G6/G7).",
        "Time-series charts share a month axis; the vertical dashed line is the data date. "
        "Counts left of the line are history (actuals); everything right of it is forecast. "
        "Index curves stop at the data date — no index is fabricated for future months. N/A "
        "means the qualifying population is empty, never zero-filled.",
        "Where the remaining work is piling up (bow wave), whether execution is keeping pace "
        "with the baseline (BEI/HMI), how much past-due baseline work is being carried "
        "(workoff burden), how realistic remaining durations are (DRM), and which loaded "
        "version sits in the danger quadrant of each portfolio quad.",
    )
    # bandit B608 false positive: this is server-rendered HTML (a <select> control + prose
    # containing the words select/from), not SQL construction.
    return f"""
<div class=panel><h2>Performance Analysis Summary</h2>
<p class=muted>Recreates the operator's <b>PerformanceAnalysisSummary</b> reference workbook
(G1&ndash;G7) from the loaded files &mdash; no manual pasting: every series below is computed
from the schedule's own dates, baseline, progress and logic, and matches the engine figures
cited on the other pages.</p>{intro}{trunc_note}
<form method=get action=/performance class=viz-controls>
<label>Project graphs (G1&ndash;G5) use:&nbsp;<select name=file onchange="this.form.submit()">
{opts}</select></label>
<noscript><button type=submit>Apply</button></noscript>
<a class=btn-link href="/export/xlsx/performance?file={_e(sel)}">&#11015; Excel (all datasets)</a>
</form>
<div class=viz-controls>
<button id=perfPrev type=button>&#9664; Prev</button>
<span id=perfStep class=muted data-no-i18n></span>
<button id=perfNext type=button>Next &#9654;</button>
<button id=perfPlay type=button>&#9654; Play</button>
<span class=muted>animates G1&ndash;G5 through every loaded file (the caption names the file
shown at each step); the quads ring the current file's dot</span>
</div></div>
<div class=mosaic id=perfGrid>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: per calendar month, the tasks &amp; milestones ACTIVE in that month (span overlaps it) — total, completed, and still to-go — plus how many sit on the longest path.\n\nHOW TO READ: the to-go area right of the data date is the remaining-work profile; a hump far right of the baseline plan is the bow wave. The longest-path line shows how much of each month's work controls the finish.\n\nDECIDE: which months are overloaded with remaining work and deserve resource/logic scrutiny.">G1 &mdash; Completed vs Work-to-Go (Tasks &amp; Milestones)</h3></div><div class=chart-host id=g1Census></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same census restricted to NORMAL tasks (no milestones): active, to-go, and longest-path counts per month.\n\nHOW TO READ: normal tasks carry the real work; a widening gap between the active line and the to-go line left of the data date is completed work, and the to-go line right of it is the workload still ahead.\n\nDECIDE: whether the remaining normal-task load is spread or spiking.">G1 &mdash; Work-to-Go (Normal Tasks)</h3></div><div class=chart-host id=g1Normal></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: activity STARTS per month — baselined vs scheduled/forecast vs actual (lines), with stacked bars for starts that happened late vs baseline (&le;30 / 31&ndash;60 / &gt;60 days).\n\nHOW TO READ: actuals tracking under the baseline line = starts falling behind; tall late-bars show how late. Right of the data date the scheduled line is the forecast start plan.\n\nDECIDE: whether work is being initiated on pace (a start bow-wave precedes a finish bow-wave).">G2 &mdash; Activity Starts (baselined / scheduled / actual + late buckets)</h3></div><div class=chart-host id=g2Starts></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: activity FINISHES per month — baselined vs scheduled/forecast vs actual (lines) with late-finish buckets (&le;30 / 31&ndash;60 / &gt;60 days vs baseline).\n\nHOW TO READ: if starts are on pace but finishes lag, in-progress work is piling up (the classic bow wave); the late buckets show the severity distribution.\n\nDECIDE: whether completion (not initiation) is the constraint, and how much forecast finish work is stacked after the data date.">G2 &mdash; Activity Finishes (baselined / scheduled / actual + late buckets)</h3></div><div class=chart-host id=g2Finishes></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: cumulative S-curves — baselined, scheduled and actual starts and finishes accumulated over time.\n\nHOW TO READ: the horizontal gap between the baseline curve and the actual curve is schedule slip in time units; a scheduled curve bending right of baseline is the re-planned (slipped) plan.\n\nDECIDE: how far behind the baseline the schedule is running and whether the recovery slope is credible.">G2 &mdash; Cumulative S-curves (starts &amp; finishes)</h3></div><div class=chart-host id=g2Cum></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: execution-index curves for STARTS — BEI-Starts (cumulative actual &divide; cumulative baselined) and the monthly HMI-Starts hit rate with its 3-month rolling average. Curves stop at the data date; nothing is projected.\n\nHOW TO READ: BEI &lt; 0.95 (DCMA practice band) = execution behind plan; HMI is the sharper month-by-month pulse.\n\nDECIDE: whether start execution is recovering or deteriorating.">G3 &mdash; Start execution indices (BEI / HMI)</h3></div><div class=chart-host id=g3Starts></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same indices for FINISHES — BEI-Finishes and monthly HMI-Finishes (+ 3-mo rolling average).\n\nHOW TO READ: finish indices below the start indices mean work is started but not being closed out — the in-progress pileup signature.\n\nDECIDE: whether completion discipline (not just starts) is holding.">G3 &mdash; Finish execution indices (BEI / HMI)</h3></div><div class=chart-host id=g3Finishes></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: workoff burden for STARTS. Above the axis, each month's starts categorized: on-plan (baselined that month), early, workoff of a PAST-DUE baseline, past-due backlog now forecast here, and slipped future baseline. BELOW the axis, the same un-started work mirrored at the month its baseline promised it.\n\nHOW TO READ: below-axis bars are broken promises at their original month; the matching above-axis bars show where that work has been pushed — the further right, the bigger the bow wave.\n\nDECIDE: how much past-due work the forecast is carrying and where it has been re-stacked.">G4 &mdash; Workoff burden (starts)</h3></div><div class=chart-host id=g4Starts></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same workoff-burden categorization for FINISHES — where past-due baseline finishes went, and the un-finished backlog mirrored below the axis at its baselined month.\n\nHOW TO READ: a tall past-due (workoff) stack just right of the data date = a recovery plan betting on immediate catch-up; spread far right = acknowledged slip.\n\nDECIDE: whether the finish workoff plan is credible or front-loaded hope.">G4 &mdash; Workoff burden (finishes)</h3></div><div class=chart-host id=g4Finishes></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the Duration Ratio S-curve — every COMPLETED task's actual duration &divide; baseline duration (DRM), sorted ascending against cumulative probability.\n\nHOW TO READ: DRM 1.0 = took exactly as long as baselined. The curve's crossing of 1.0 tells you what share of completed work beat its baseline; a long right tail = chronic under-estimation.\n\nDECIDE: what growth factor history supports when judging the remaining durations (and any SRA).">G5 &mdash; Duration Ratio S-curve</h3></div><div class=chart-host id=g5Scurve></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: histogram of the MIDDLE 70% of completed-task duration ratios (the workbook's convention — the tails are excluded from the bars but included in the min/avg/max chips).\n\nHOW TO READ: a mode below 1.0 = durations typically beaten; mass above 1.0 = systematic overrun. The chips carry the full-population min / average / max and the excluded-count disclosure.\n\nDECIDE: the realistic duration growth factor for forecasts.">G5 &mdash; Duration Ratio histogram (middle 70%)</h3></div><div class=chart-host id=g5Hist></div><div id=g5Stats class=stat-row></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — HMI (tasks, latest period) vs CEI (finish) for EVERY loaded version; dashed guides at the 0.95 practice band used across this tool's index metrics.\n\nHOW TO READ: top-right = hitting current commitments AND closing out to plan; bottom-left = missing both. A version drifting left over time is losing period discipline.\n\nDECIDE: which version/update deserves the deep-dive first.">G3 quad &mdash; HMI vs CEI (per loaded version)</h3></div><div class=chart-host id=quadHmiCei></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — to-go starts ratio vs to-go finishes ratio (remaining scheduled work &divide; work the baseline said should remain). Guides at 1.0 = carrying exactly what the baseline planned.\n\nHOW TO READ: above/right of 1.0 = more to-go work than planned (the bow wave, quantified); far above the diagonal = finishes lagging starts.\n\nDECIDE: which version is quietly accumulating un-done work.">G6 quad &mdash; To-Go Starts vs To-Go Finishes</h3></div><div class=chart-host id=quadRatio></div></section>
<section class="tile panel"><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — BEI (baseline execution) vs the share of the to-go work sitting on the critical path. Vertical guide at BEI 0.95 (DCMA practice); horizontal guide at the portfolio median critical share (labeled — no industry threshold exists for this axis).\n\nHOW TO READ: bottom-right (high BEI, low critical share) is healthy; top-left (poor execution AND a critical-heavy backlog) is the danger quadrant.\n\nDECIDE: which version pairs poor execution with a critical-path-loaded backlog.">G7 quad &mdash; BEI vs % critical of to-go work</h3></div><div class=chart-host id=quadBeiCp></div></section>
</div>
<script type="application/json" id=perfData>{blob}</script>
<script src="/static/performance.js"></script>"""  # nosec B608 (HTML, not SQL)


def _evolution_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None
) -> dict[str, object]:
    """JSON for the critical-path evolution Gantt stepper: per-version snapshots with each
    critical activity's bar geometry (start/finish), the entered/left attribution (the reason
    WHY each entered or left the path), and a date axis LOCKED across every version so bars
    stay comparable frame to frame. ``target`` (if set) is echoed so the view can highlight
    that UniqueID's row in every frame."""
    # With a focused UID the path IS the 0-driving-slack chain to it (the /path basis);
    # untargeted, the progress-aware effective critical set (stored Critical flag).
    evolution = compute_path_evolution(schedules, cpms, target_uid=target)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = offset_to_datetime(sch.project_start, timing.early_start, sch.calendar).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def is_complete_in(idx: int, uid: int) -> bool:
        """Robust complete flag (ADR-0051: ≥100% OR an actual finish) for ``uid`` in version
        ``idx`` — False when the activity is absent from that version."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        return task is not None and (task.is_complete or task.actual_finish is not None)

    def stats(idx: int, uid: int) -> dict[str, object]:
        """Per-activity grid columns for the row: %complete, duration (working days), and the
        robust complete flag. Empty when the activity is absent from version ``idx`` (e.g. a
        removed activity shown at its prior position)."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": is_complete_in(idx, uid),
        }

    def path_to_target(idx: int) -> list[int]:
        """When a UID is focused, the activities that DRIVE it in version ``idx`` — the target
        plus its transitive predecessors — so the "driving path to focus" filter can scope the
        Gantt to just the chain feeding the focused activity. Empty when no target is set or it
        is absent from this version."""
        if target is None or not (0 <= idx < len(schedules)) or target not in by_id[idx]:
            return []
        preds_of: dict[int, list[int]] = {}
        for r in schedules[idx].relationships:
            preds_of.setdefault(r.successor_id, []).append(r.predecessor_id)
        seen, stack = {target}, [target]
        while stack:
            for p in preds_of.get(stack.pop(), ()):
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return sorted(seen)

    snapshots: list[dict[str, object]] = []
    for i, s in enumerate(evolution.snapshots):
        names = {str(uid): by_id[i][uid].name for uid in s.critical if uid in by_id[i]}
        if i > 0:
            for uid in s.left:
                if uid in by_id[i - 1]:
                    names[str(uid)] = by_id[i - 1][uid].name
        entered_reason = {c.uid: c for c in s.entered_changes}
        dur_changed = set(s.duration_changed)
        critical_rows: list[dict[str, object]] = []
        for uid in s.critical:
            start, finish = bar(i, uid)
            change = entered_reason.get(uid)
            critical_rows.append(
                {
                    "uid": uid,
                    "name": names.get(str(uid), f"UID {uid}"),
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered_reason,
                    "duration_changed": uid in dur_changed,
                    "reason": change.reason if change is not None else None,
                    "detail": change.detail if change is not None else None,
                    **stats(i, uid),
                }
            )
        critical_rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for c in s.left_changes:
            start, finish = bar(i - 1, c.uid) if i > 0 else (None, None)
            # left activities are drawn at their PRIOR-version position, so %complete/duration
            # read from that version (i - 1); the complete flag is the CURRENT status, so an
            # activity that left *because it completed* hides under the hide-completed toggle.
            grid = stats(i - 1, c.uid)
            grid["complete"] = is_complete_in(i, c.uid)
            left_rows.append(
                {
                    "uid": c.uid,
                    "name": c.name,
                    "start": start,
                    "finish": finish,
                    "reason": c.reason,
                    "detail": c.detail,
                    **grid,
                }
            )
        snapshots.append(
            {
                "label": s.label,
                "status_date": s.status_date,
                "project_finish": s.project_finish,
                "finish_delta_days": s.finish_delta_days,
                "critical": list(s.critical),
                "entered": list(s.entered),
                "left": list(s.left),
                "duration_changed": list(s.duration_changed),
                "shortened_on_path": list(s.shortened_on_path),
                "removed_logic_count": s.removed_logic_count,
                "names": names,
                "critical_rows": critical_rows,
                "left_rows": left_rows,
                "path_to_target": path_to_target(i),
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target}


#: Evolution tier modes → the driving-slack tiers (ADR-0011) to include. "off" = the float
#: critical-path view (the page default, with its rich entered/left attribution).
_EVO_TIER_LABEL = {
    PathTier.DRIVING: "driving",
    PathTier.SECONDARY: "secondary",
    PathTier.TERTIARY: "tertiary",
}
_EVO_TIER_SELECT: dict[str, set[PathTier]] = {
    "critical": {PathTier.DRIVING},
    "secondary": {PathTier.SECONDARY},
    "tertiary": {PathTier.TERTIARY},
    "all": {PathTier.DRIVING, PathTier.SECONDARY, PathTier.TERTIARY},
}


def _project_finish_uid(sch: Schedule, cpm: CPMResult) -> int | None:
    """The non-summary activity that finishes last (drives the project finish) — the default focus
    for the tiered driving-path view when no target UID is pinned."""
    best_uid: int | None = None
    best: int | None = None
    for t in sch.tasks:
        if t.is_summary:
            continue
        tm = cpm.timings.get(t.unique_id)
        if tm is None:
            continue
        if best is None or tm.early_finish > best:
            best, best_uid = tm.early_finish, t.unique_id
    return best_uid


def _evolution_tier_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None, tier: str
) -> dict[str, object]:
    """Critical-Path Evolution scoped to a DRIVING-SLACK tier (ADR-0011) instead of the float
    critical path: per version, classify the activities driving the focus (the pinned ``target``,
    else that version's project-finish activity) into driving (0 days) / secondary (<=10 days) /
    tertiary (<=20 days), and show ONLY the chosen tier (``all`` shows all three, the client colours
    them by tier). Same payload shape as :func:`_evolution_data` so the Gantt stepper renders it
    unchanged; ``entered`` / ``left`` are by set difference of the tier membership across versions,
    and the version framing (label / data date / project finish) is reused from the evolution."""
    selected = _EVO_TIER_SELECT.get(tier, _EVO_TIER_SELECT["critical"])
    evolution = compute_path_evolution(schedules, cpms)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = offset_to_datetime(sch.project_start, timing.early_start, sch.calendar).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def grid(idx: int, uid: int) -> dict[str, object]:
        task = by_id[idx].get(uid) if 0 <= idx < len(by_id) else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": task.is_complete or task.actual_finish is not None,
        }

    # per-version tier membership: uid -> tier label, for the selected tiers only
    members: list[dict[int, str]] = []
    for i, sch in enumerate(schedules):
        focus = (
            target
            if (target is not None and target in by_id[i])
            else _project_finish_uid(sch, cpms[i])
        )
        m: dict[int, str] = {}
        if focus is not None:
            try:
                results = compute_driving_slack(sch, focus, cpm_result=cpms[i])
            except (KeyError, ValueError):
                results = {}
            for uid, r in results.items():
                if r.tier in selected:
                    m[uid] = _EVO_TIER_LABEL[r.tier]
        members.append(m)

    snapshots: list[dict[str, object]] = []
    prior: set[int] = set()
    for i, snap in enumerate(evolution.snapshots):
        cur = set(members[i])
        entered = (cur - prior) if i > 0 else set()
        left = (prior - cur) if i > 0 else set()
        rows: list[dict[str, object]] = []
        for uid in cur:
            start, finish = bar(i, uid)
            task = by_id[i].get(uid)
            rows.append(
                {
                    "uid": uid,
                    "name": task.name if task is not None else f"UID {uid}",
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered,
                    "duration_changed": False,
                    "reason": None,
                    "detail": None,
                    "tier": members[i][uid],
                    **grid(i, uid),
                }
            )
        rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for uid in sorted(left):
            start, finish = bar(i - 1, uid) if i > 0 else (None, None)
            g = grid(i - 1, uid)
            now = by_id[i].get(uid)
            g["complete"] = bool(now and (now.is_complete or now.actual_finish is not None))
            name = by_id[i - 1][uid].name if (i > 0 and uid in by_id[i - 1]) else f"UID {uid}"
            left_rows.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "reason": None,
                    "detail": None,
                    "tier": members[i - 1].get(uid) if i > 0 else None,
                    **g,
                }
            )
        prior = cur
        snapshots.append(
            {
                "label": snap.label,
                "status_date": snap.status_date,
                "project_finish": snap.project_finish,
                "finish_delta_days": snap.finish_delta_days,
                "critical": sorted(cur),
                "entered": sorted(entered),
                "left": sorted(left),
                "duration_changed": [],
                "shortened_on_path": [],
                "removed_logic_count": 0,
                "names": {str(u): (by_id[i][u].name if u in by_id[i] else f"UID {u}") for u in cur},
                "critical_rows": rows,
                "left_rows": left_rows,
                "path_to_target": [],
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target, "tier": tier}


def _dashboard_data(st: SessionState) -> dict[str, object]:
    """Per-loaded-schedule health snapshot for the Dashboard cards: status mix, critical
    exposure, computed finish vs baseline, and the DCMA-14 verdicts. Reuses the cached
    per-schedule analysis (one CPM each); an unschedulable file degrades to a flagged card."""
    cards: list[dict[str, object]] = []
    for key, sch in st.ordered_versions():  # earliest -> latest data date
        scoped = st.scope(sch)  # the active filter applies to the dashboard cards too
        card: dict[str, object] = {
            "key": key,
            "name": sch.name,
            "source_file": sch.source_file,
            "activities": len(non_summary(scoped)),
            "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        }
        try:
            an = st.analysis_for(key, sch)
        except CPMError:
            card["solvable"] = False
            cards.append(card)
            continue
        makeup = compute_activity_makeup(scoped)
        total = makeup.complete + makeup.in_progress + makeup.planned
        # the activity IDs behind each status segment, so the card's status bar can drill (same
        # predicates as compute_activity_makeup — schedule_card.py)
        ns_scoped = non_summary(scoped)
        status_mix_uids = {
            "complete": [t.unique_id for t in ns_scoped if t.percent_complete >= 100.0],
            "in_progress": [t.unique_id for t in ns_scoped if 0.0 < t.percent_complete < 100.0],
            "planned": [t.unique_id for t in ns_scoped if t.percent_complete <= 0.0],
        }
        cpm_finish = offset_to_datetime(
            scoped.project_start, an.cpm.project_finish, scoped.calendar
        ).date()
        baseline_dates = [
            t.baseline_finish for t in non_summary(scoped) if t.baseline_finish is not None
        ]
        baseline_finish = max(baseline_dates).date() if baseline_dates else None
        fb0 = an.float_bands["float_total_0"]
        card.update(
            {
                "solvable": True,
                "status_mix": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                },
                "status_mix_uids": status_mix_uids,
                "percent_complete": round(100 * makeup.complete / total, 1) if total else 0.0,
                "critical_count": fb0.count,
                "critical_pct": round(fb0.value, 1),
                "cpm_finish": cpm_finish.isoformat(),
                "baseline_finish": baseline_finish.isoformat() if baseline_finish else None,
                # positive = computed finish later than baseline (a slip)
                "finish_delta_days": (cpm_finish - baseline_finish).days
                if baseline_finish
                else None,
                "dcma": [
                    {"id": c.metric_id, "name": c.name, "status": str(c.status)}
                    for c in an.audit.checks
                ],
            }
        )
        cards.append(card)
    return {"cards": cards}


def _cite_tag(citations: tuple[Citation, ...]) -> str:
    shown = "; ".join(str(c) for c in citations[:3])
    extra = f"; +{len(citations) - 3} more" if len(citations) > 3 else ""
    return f"{shown}{extra}"


def _briefing_table_html(section: BriefingSection) -> str:
    """A section's cited table: engine figures verbatim, a citation column per row."""
    table = section.table
    if table is None or not table.rows:
        return ""
    head = ""
    if table.headers:
        head = (
            "<tr>"
            + "".join(f"<th scope=col>{_e(h)}</th>" for h in table.headers)
            + "<th scope=col>Citation</th></tr>"
        )
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_e(cell)}</td>" for cell in row)
        + f"<td class=cite>{_e(_cite_tag(cites))}</td></tr>"
        for row, cites in zip(table.rows, table.row_citations, strict=True)
    )
    # .brief-scroll: a table whose column minimums exceed the card scrolls sideways inside it
    # instead of crushing its neighbours to a character a line (operator report 2026-07-08)
    return f"<div class=brief-scroll><table class=brief-table>{head}{body}</table></div>"


def _the_briefing_header(briefing: ExecutiveBriefing, sch: Schedule, cpm: CPMResult) -> str:
    """Chapter 12 "The briefing" (ADR-0210): the data-driven takeaway (the briefing's own
    verdict + headline figures), a KPI strip from the briefing banner, and the action-items
    and quality-snapshot bars — the executive synthesis. Every figure is one the briefing /
    audit already computes (no new math)."""
    banner = dict(briefing.banner)
    spi = banner.get("SPI (duration-based)") or banner.get("SPI")
    forecast = banner.get("Forecast finish")
    slip = banner.get("Slip")
    clauses = []
    if spi:
        clauses.append(f"SPI {spi}")
    if forecast:
        clauses.append(f"forecasting a finish of {forecast}")
    if slip:
        clauses.append(f"a {slip} slip from baseline")
    tail = f" — {', '.join(clauses)}" if clauses else ""
    takeaway = f"Bottom line: the schedule is {briefing.verdict}{tail}."

    # KPI strip = the briefing's own banner headline figures (up to six)
    kpi = _stat_cards([(label, value) for label, value in briefing.banner[:6]])

    findings = recommend(sch, current_cpm=cpm)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    med = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)
    audit = audit_schedule(sch, cpm)
    passed = sum(1 for c in audit.checks if c.status is CheckStatus.PASS)
    failed = sum(1 for c in audit.checks if c.status is CheckStatus.FAIL)
    na = sum(1 for c in audit.checks if c.status is CheckStatus.NOT_APPLICABLE)

    actions_bar = _status_stack(
        "Action items by severity",
        "The findings the briefing raises, ranked by severity.",
        [("High", high, "--bad"), ("Medium", med, "--warn"), ("Low", low, "--muted")],
        f"{len(findings)} finding{'s' if len(findings) != 1 else ''} in the briefing",
    )
    quality_bar = _status_stack(
        "Quality snapshot",
        "The DCMA-14 integrity checks behind the verdict.",
        [("Pass", passed, "--ok"), ("Fail", failed, "--bad"), ("N/A", na, "--muted")],
        f"{passed + failed} of {passed + failed + na} checks scored",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{actions_bar}{quality_bar}</div>'
    )


def _briefing_body(briefing: ExecutiveBriefing) -> str:
    """Render the leadership Executive Briefing (ADR-0121): a metadata header + a verdict banner,
    then the numbered forensic sections (Bottom Line, Performance, Critical Path Then & Now, Health
    Dashboard, Risks & Opportunities, Recommended Actions, How to Verify) as a single continuous
    document. Every statement and every table row carries its file + UID + task citation (§6)."""
    verdict_slug = briefing.verdict.lower().replace(" ", "-").replace("/", "")
    meta = "".join(
        f"<tr><th scope=row>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in briefing.meta_rows
    )
    banner = "".join(
        f"<div class=brief-stat><span class=brief-stat-label>{_e(k)}</span>"
        f"<span class=brief-stat-value>{_e(v)}</span></div>"
        for k, v in briefing.banner
    )
    # full-width header (title + meta + verdict banner), then the numbered sections tiled into a
    # responsive card grid so the briefing fills the whole page width and each section stays cleanly
    # boxed instead of running down one narrow column.
    header = (
        '<div class="panel brief-doc">'
        f"<h2>{_e(briefing.title)}</h2>"
        f"<p class=brief-subtitle>{_e(briefing.subtitle)}</p>"
        f"<table class=brief-meta>{meta}</table>"
        f'<div class="brief-banner verdict-{_e(verdict_slug)}">{banner}</div>'
        "<p class=muted>Every statement and table row cites file + UniqueID + task name. "
        'Hand-out copy: <a href="/export/docx/briefing">&#11015; Word</a> &middot; '
        '<a href="/export/xlsx/briefing">&#11015; Excel</a>.</p>'
    )

    def _section_html(section: BriefingSection) -> str:
        tag = f"h{min(section.level + 2, 6)}"
        prose = "".join(
            f"<p>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></p>"
            for s in section.statements
        )
        return (
            f"<{tag} class=brief-h>{_e(section.heading)}</{tag}>"
            f"{prose}{_briefing_table_html(section)}"
        )

    # group: each top-level (level 1) section opens a new card; its sub-sections nest inside it
    cards: list[list[str]] = []
    card_is_wide: list[bool] = []
    card_heading: list[str] = []
    for section in briefing.sections:
        if section.level <= 1 or not cards:
            cards.append([])
            card_is_wide.append(False)
            card_heading.append(section.heading)
        cards[-1].append(_section_html(section))
        # a table with many columns needs the full page row, not a half-width card
        if section.table is not None and len(section.table.headers) >= 5:
            card_is_wide[-1] = True
    # Half-page partner rows (operator 2026-07-08): pair sections that otherwise land in narrow
    # auto-fit columns with wasted white space beside a short neighbour. Each ordered (A, B) group
    # becomes one full-width `.brief-duo` row split 1fr/1fr, so neither section wastes page width
    # and long tables scroll inside their half (capped in CSS) rather than towering the page.
    duo_groups = (("Critical Path", "Schedule Health"), ("Recommended Actions", "How to Verify"))

    def _group_of(heading: str) -> tuple[int, int] | None:
        for g, (first, second) in enumerate(duo_groups):
            if first in heading:
                return (g, 0)
            if second in heading:
                return (g, 1)
        return None

    card_group = [_group_of(h) for h in card_heading]
    # only pair a group when BOTH members are actually present (a briefing with an empty/skipped
    # section falls back to a normal single card)
    counts: dict[int, int] = {}
    for cg in card_group:
        if cg:
            counts[cg[0]] = counts.get(cg[0], 0) + 1
    active_groups = {g for g, c in counts.items() if c == 2}

    card_html: list[str] = []
    duo_buffers: dict[int, list[str]] = {}
    for i, body in enumerate(cards):
        # the opening "Bottom Line" card spans the full width as the headline
        cls = (
            "brief-card lead"
            if i == 0
            else ("brief-card wide" if card_is_wide[i] else "brief-card")
        )
        cg = card_group[i]
        if cg and cg[0] in active_groups:
            buf = duo_buffers.setdefault(cg[0], [])
            buf.append(f'<section class="brief-card">{"".join(body)}</section>')
            if len(buf) == 2:
                card_html.append(f"<div class=brief-duo>{''.join(buf)}</div>")
        else:
            card_html.append(f'<section class="{cls}">{"".join(body)}</section>')
    grid = f"<div class=brief-grid>{''.join(card_html)}</div>"
    return f"{header}{grid}</div>"


def _ai_backend_explainer() -> str:
    """Collapsible "what each AI option does + how it handles CUI" guidance for AI Settings: where
    each model runs and therefore whether schedule data stays on this machine."""
    return """
<div class=panel><h2>What each AI option does &amp; how it handles your data (CUI)</h2>
<p class=muted>The AI only ever <b>polishes wording</b> over figures the engine already computed and
cites &mdash; it never invents numbers. What differs below is <b>where the model runs</b>, and
therefore whether your schedule data stays on this machine.</p>
<details class=explainer><summary><b>Ollama (local)</b> &mdash; recommended, CUI-safe</summary>
<p><b>What it is.</b> Runs an open model (Llama&nbsp;3.1, Qwen&nbsp;2.5, &hellip;) on THIS computer via a
local server on <code>127.0.0.1</code>.</p>
<p><b>CUI / data locality.</b> <b>Stays on the machine.</b> The tool talks to Ollama only over loopback
and a remote endpoint is refused, so no schedule content leaves the box. Safe for CUI.</p>
<p><b>Pros.</b> Easiest setup (one-line model pulls), broad model library, and the tool can start/stop
it for you. <b>Cons.</b> A separate install; large models need a lot of RAM/VRAM.</p></details>
<details class=explainer><summary><b>OpenAI-compatible (local)</b> &mdash; LM Studio / llamafile / vLLM, CUI-safe</summary>
<p><b>What it is.</b> A local server that speaks the OpenAI <code>/v1</code> API on a loopback address.
You load the model in that app; the tool calls it on <code>127.0.0.1</code>.</p>
<p><b>CUI / data locality.</b> <b>Stays on the machine</b> &mdash; the endpoint is loopback-validated
(a remote URL is refused, Law&nbsp;1). Safe for CUI.</p>
<p><b>Pros.</b> Use LM Studio's UI + model catalog and GPU offload; standard OpenAI-API tooling.
<b>Cons.</b> Load the model in that app first and select the <b>exact model id it serves</b> &mdash; use
the <i>Model</i> dropdown above, which lists what the server reports (click <b>Refresh models</b>).</p></details>
<details class=explainer><summary><b>Null (offline, deterministic)</b> &mdash; CUI-safe</summary>
<p><b>What it is.</b> No model at all &mdash; the answers are the engine's own <b>cited facts</b>, returned
verbatim.</p>
<p><b>CUI / data locality.</b> <b>Nothing can leave the machine</b> (no model, no network). Always safe.</p>
<p><b>Pros.</b> Zero setup, fully deterministic, instant. <b>Cons.</b> No written interpretation &mdash;
you get the facts, not prose.</p></details>
<details class=explainer><summary><b>Cloud</b> &mdash; UNCLASSIFIED only, NOT for CUI</summary>
<p><b>What it is.</b> Sends the prompt to a remote provider's model.</p>
<p><b>CUI / data locality.</b> <b>Data LEAVES this machine.</b> This is <u>disqualifying for CUI</u>. It is
only selectable after you explicitly switch <i>Classification</i> to <b>UNCLASSIFIED</b>, and a persistent
banner then names the endpoint. Never use it with controlled schedule data.</p>
<p><b>Pros.</b> The most capable models, no local hardware. <b>Cons.</b> Data egress &mdash; off-limits for
CUI, and needs an internet connection.</p></details>
<details class=explainer><summary><b>Cross-check second model</b> &mdash; corroboration, CUI-safe</summary>
<p><b>What it is.</b> An optional second <b>local</b> model that answers every question independently; the
engine compares the two answers' figures deterministically (agreement is corroboration; the citations
remain the ground truth).</p>
<p><b>CUI / data locality.</b> Both models are <b>local</b> (Ollama or OpenAI-compatible) &mdash; a cloud
second model does not exist by design, so cross-checking never sends data off the machine.</p>
<p><b>Pros.</b> Catches a single model's mistakes; raises confidence. <b>Cons.</b> Runs two models, so each
answer uses more time and memory.</p></details>
</div>"""


def _settings_body(state: SessionState) -> str:
    cfg = state.ai_config
    backend, _banner = route_backend(
        cfg,
        null_backend=NullBackend(),
        ollama_backend=_ollama_or_none(cfg),
        openai_backend=_openai_or_none(cfg),
    )
    models: tuple[str, ...] = ()
    try:
        models = backend.list_models()
    except Exception:
        models = ()
    model_list = ", ".join(_e(m) for m in models) or "<span class=muted>none available</span>"
    second = _second_backend(state)
    second_status = (
        f"reachable ({_e(second.name)})"
        if second is not None
        else ("off" if cfg.second_backend == "none" else "configured but not reachable")
    )
    second_models: tuple[str, ...] = ()
    if second is not None:
        try:
            second_models = second.list_models()
        except Exception:
            second_models = ()
    status_note = _ai_status_note(cfg)

    def sel(value: str, current: str) -> str:
        return " selected" if value == current else ""

    # When a real local backend is active and reporting installed models, the Model field is a
    # dropdown of those models (one click to pick, e.g., a purpose-built model) instead of a
    # free-text box the operator must match exactly. The configured model is always kept as a
    # (selected) option — marked if it isn't installed — so a save never silently loses it.
    real_backend = backend.name in ("ollama", "openai-compat")
    # The Model field is ALWAYS a <select> so settings.js can repopulate it live the instant the
    # operator switches backend/endpoint — no save+reload. This is what makes OpenAI-compatible work
    # in one flow: pick the exact model id the local server serves. A blank option = the server's
    # loaded default; the configured model is always kept (flagged if the server isn't serving it).
    model_opts = [
        f'<option value=""{" selected" if not cfg.model else ""}>'
        "(server default / loaded model)</option>"
    ]
    if cfg.model and not _model_installed(cfg.model, models):
        model_opts.append(
            f'<option value="{_e(cfg.model)}" selected>{_e(cfg.model)} &mdash; not installed</option>'
        )
    model_opts += [f'<option value="{_e(m)}"{sel(m, cfg.model)}>{_e(m)}</option>' for m in models]
    model_field = (
        "<select name=model id=primaryModel>" + "".join(model_opts) + "</select>"
        " <span id=primaryModelStatus class=muted aria-live=polite></span>"
        " <button type=button id=refreshModels class=linkbtn"
        ' title="Re-probe the selected backend for the models it currently serves">'
        "Refresh models</button>"
    )

    # The cross-check second model is a live <select> too (operator asked for a dropdown, not free
    # text) — populated from the chosen second backend's served models, refreshed by settings.js.
    second_opts = [
        f'<option value=""{" selected" if not cfg.second_model else ""}>'
        "(server default / loaded model)</option>"
    ]
    if cfg.second_model and not _model_installed(cfg.second_model, second_models):
        second_opts.append(
            f'<option value="{_e(cfg.second_model)}" selected>'
            f"{_e(cfg.second_model)} &mdash; not installed</option>"
        )
    second_opts += [
        f'<option value="{_e(m)}"{sel(m, cfg.second_model)}>{_e(m)}</option>' for m in second_models
    ]
    second_model_field = (
        "<select name=second_model id=secondModel>" + "".join(second_opts) + "</select>"
        " <span id=secondModelStatus class=muted aria-live=polite></span>"
    )

    # A one-click "off" switch, shown only while a real local model is active (the operator asked
    # for an explicit way to turn the AI off once it is on). It routes back to the deterministic Null
    # backend AND stops the local model, freeing its RAM/CPU without quitting the tool.
    ai_off_btn = (
        '<form action="/settings/ai-off" method=post style="margin:6px 0 2px">'
        '<button type=submit class=btn-danger title="Switch the AI back to offline deterministic '
        "mode and stop the local model now (frees its RAM and CPU). You can turn it back on here any "
        'time.">Turn the AI off &amp; stop the local model</button></form>'
        if real_backend
        else ""
    )

    return f"""
<div class=panel><h2>Local AI</h2>
{_user_tip("The tool works fully offline with no AI. Turning on a local model only adds written narrative on top of the engine&rsquo;s already-computed, cited numbers &mdash; every AI figure is re-checked against those citations, and nothing ever leaves this machine.")}
<p>Active backend: <b>{_e(backend.name)}</b> &middot; installed models: {model_list}
&middot; cross-check model: <b>{second_status}</b></p>
{status_note}
<form action="/settings" method=post>
<p>Classification:
<select name=classification>
<option value=CLASSIFIED{sel("CLASSIFIED", cfg.classification)}>CLASSIFIED (CUI — local only)</option>
<option value=UNCLASSIFIED{sel("UNCLASSIFIED", cfg.classification)}>UNCLASSIFIED (cloud allowed, banner shown)</option>
</select></p>
<p>Backend:
<select name=backend id=backendSel>
<option value=ollama{sel("ollama", cfg.backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.backend)}>OpenAI-compatible (local — LM Studio / llamafile / vLLM)</option>
<option value=null{sel("null", cfg.backend)}>Null (offline, deterministic)</option>
<option value=cloud{sel("cloud", cfg.backend)}>Cloud (UNCLASSIFIED only)</option>
</select></p>
<p>Model: {model_field}</p>
<p>Generation timeout (seconds):
<input name=gen_timeout type=number min=30 max=3600 step=10 value="{_e(int(cfg.gen_timeout))}"
 title="How long a single answer may take. Defaults to the maximum (3600 s = 1 hour) so a big, slow model (e.g. llama3.1:70b) can always finish; lower it if you prefer to cap it."> <span class=muted>(default = max, 3600 s)</span></p>
<p>Ollama endpoint (loopback only):
<input name=endpoint size=28 value="{_e(cfg.endpoint)}"
 title="Ollama defaults to http://127.0.0.1:11434"></p>
<p>OpenAI-compatible endpoint (loopback only):
<input name=openai_endpoint size=28 value="{_e(cfg.openai_endpoint)}"
 title="LM Studio defaults to http://127.0.0.1:1234; llamafile to http://127.0.0.1:8080"></p>
<p>AI answer mode:
<select name=qa_mode>
<option value=annotate{sel("annotate", cfg.qa_mode)}>Annotate (default) — the model may analyze and
derive figures grounded in the cited facts, but any figure the engine did not compute is flagged as
AI-derived</option>
<option value=strict{sel("strict", cfg.qa_mode)}>Strict — any answer containing a figure the
engine never computed is discarded wholesale</option>
<option value=interpretive{sel("interpretive", cfg.qa_mode)}>Interpretive — the model's text is
shown verbatim, ungated (raw analysis; no sourced-figure guarantee — verify against the citations)</option>
</select></p>
<p>Cross-check second model:
<select name=second_backend id=secondBackend>
<option value=none{sel("none", cfg.second_backend)}>Off</option>
<option value=ollama{sel("ollama", cfg.second_backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.second_backend)}>OpenAI-compatible (local)</option>
</select>
 model id: {second_model_field}</p>
<input type=submit value="Save"></form>
{ai_off_btn}
{_ai_backend_explainer()}
<p class=muted>The tool never sends schedule data off this machine while CLASSIFIED. Cloud is only
reachable after you explicitly switch to UNCLASSIFIED, and a persistent banner names the endpoint.
Either answer mode is prose-only: the cited facts shown with each answer are always engine-computed.
With a cross-check model on, both local models answer every question independently and the engine
compares their figures deterministically — agreement is corroboration, the citations stay the
ground truth.</p>
<details class=setup-guide><summary>How to download &amp; set up a local model (Llama&nbsp;3.1:8b and others)</summary>
<ol>
<li><b>Install Ollama</b> (one time). In your browser, go to <code>ollama.com/download</code> and run
the installer — Windows, macOS, or Linux. This is the only step that uses the internet.</li>
<li><b>Download the standard model.</b> Open a terminal / command prompt and run:
<br><code>ollama pull qwen2.5:7b-instruct</code></li>
<li><b>Pick a model that fits your computer's memory (RAM):</b>
<ul>
<li>8&nbsp;GB &rarr; <code>ollama pull llama3.2:3b</code> (small, quick)</li>
<li>16&nbsp;GB &rarr; <code>ollama pull qwen2.5:7b-instruct</code> (the tool's default — balanced)</li>
<li>16&ndash;32&nbsp;GB &rarr; <code>ollama pull qwen2.5:14b</code> (noticeably smarter)</li>
<li>32&nbsp;GB+ &rarr; <code>ollama pull qwen2.5:32b</code> &middot; 64&nbsp;GB+ &rarr;
<code>ollama pull llama3.1:70b</code> (most powerful, slowest)</li>
</ul></li>
<li><b>Point the tool at it.</b> Set <i>Backend</i> = <i>Ollama (local)</i> above, choose the model
in <i>Model</i>, and click <b>Save</b>. The tool talks to Ollama only on
<code>127.0.0.1</code> — nothing leaves the machine.</li>
<li><b>(Optional) cross-check second model.</b> Pull a second model
(e.g. <code>ollama pull qwen2.5:14b</code>), set <i>Cross-check second model</i> to
<i>Ollama (local)</i> — the model id auto-fills with the primary; change it to the second model
so both answer every question and the engine compares their figures.</li>
<li><b>If a big model runs slowly,</b> the <i>Generation timeout</i> above already defaults to the
maximum (3600&nbsp;seconds = 1 hour) so it can finish; lower it only if you want to cap answer time.
The full walk-through lives in <code>docs/CONNECT-A-BIGGER-AI-MODEL.md</code>.</li>
</ol>
<p class=muted style="margin-top:10px"><b>About Ollama running:</b> this tool starts Ollama only
when you turn the <i>Ollama (local)</i> backend on here, and when you close the tool it unloads the
model and <b>stops the Ollama server</b> (even one that was already running). If you installed
Ollama on Windows, its desktop app (<code>ollama&nbsp;app.exe</code>) <b>auto-starts again at your
next login</b> and brings the server back. To make Ollama run <i>only</i> with the tool, turn that
auto-start off once: <b>right-click the Ollama icon in the system tray &rarr; Settings &rarr;
uncheck &ldquo;Run at login&rdquo;</b> (or Windows <b>Settings &rarr; Apps &rarr; Startup &rarr;</b>
switch <b>Ollama</b> off), then sign out and back in.</p>
</details></div>
<script src="/static/settings.js"></script>"""


def _trigger_shutdown(app: FastAPI) -> None:
    """Request a graceful server stop, once (idempotent). No-op if no server is wired."""
    if app.state.shutting_down:
        return
    app.state.shutting_down = True
    callback = app.state.request_shutdown
    if callback is not None:
        callback()


def _is_idle(browser_seen: bool, idle_seconds: float, grace: float) -> bool:
    """True once a browser has connected and then gone quiet for longer than ``grace``."""
    return browser_seen and idle_seconds > grace


def _watchdog(app: FastAPI, *, poll: float = 2.0) -> None:
    """Stop the server when the browser stops beating (closing the window = tool off).

    In-flight requests hold it off: a long import/trace is the opposite of an absent
    operator, even when the beat goes quiet because the work itself is consuming the
    server (the mid-load self-shutdown the operator hit)."""
    grace = app.state.idle_grace
    while not app.state.shutting_down:
        time.sleep(poll)
        if app.state.active_requests > 0:
            continue
        if _is_idle(app.state.browser_seen, time.monotonic() - app.state.last_beat, grace):
            logger.info("no browser heartbeat for %.0fs — shutting the tool down", grace)
            _trigger_shutdown(app)
            return


def serve(
    app: FastAPI,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    server_factory: Callable[[uvicorn.Config], uvicorn.Server] = uvicorn.Server,
    log_level: str = "warning",
) -> None:
    """Serve ``app`` on a loopback address (refuses a non-local host — Law 1).

    Wires graceful shutdown: the in-page Quit control, ``POST /api/shutdown``, and (when the
    app was built with ``auto_shutdown``) the browser-gone watchdog all flip the server's
    ``should_exit``, so the process ends cleanly with nothing left running.
    """
    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind a non-loopback host {host!r} (CUI: local-only).")
    server = server_factory(uvicorn.Config(app, host=host, port=port, log_level=log_level))
    app.state.request_shutdown = lambda: setattr(server, "should_exit", True)
    if app.state.auto_shutdown:
        threading.Thread(target=_watchdog, args=(app,), daemon=True).start()
    # Ctrl+C in the terminal: uvicorn has already caught SIGINT and run its graceful shutdown, but
    # Python 3.13's asyncio.run then RE-RAISES KeyboardInterrupt, which would dump a stack trace on a
    # perfectly clean stop and read as a crash. Swallow it so a deliberate stop looks like a stop.
    # The in-page Quit control and the browser-gone watchdog flip should_exit and return from run()
    # normally — they never raise here.
    with contextlib.suppress(KeyboardInterrupt):
        server.run()


def run(
    host: str = "127.0.0.1", port: int = 8765, *, auto_shutdown: bool = False
) -> None:  # pragma: no cover - server entrypoint (covered via serve() unit tests)
    """Serve the app on loopback. ``auto_shutdown`` enables the browser-gone watchdog."""
    serve(create_app(auto_shutdown=auto_shutdown), host=host, port=port)
