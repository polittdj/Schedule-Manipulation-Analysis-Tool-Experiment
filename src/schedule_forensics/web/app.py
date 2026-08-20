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
import json
import logging
import math
import os
import re
import tempfile
import threading
import time
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, urlparse, urlsplit

import uvicorn
from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from schedule_forensics.ai import (
    AIBackend,
    AIConfig,
    Classification,
    GatewayBackend,
    NullBackend,
    OllamaBackend,
    OpenAICompatBackend,
    reattach,
    route_backend,
)
from schedule_forensics.ai.brief import brief_blocks, build_brief
from schedule_forensics.ai.briefing import (
    briefing_blocks,
    build_briefing,
)
from schedule_forensics.ai.citations import CitedStatement, Narrative, preserves_figures
from schedule_forensics.ai.config_store import load_ai_config, save_ai_config
from schedule_forensics.ai.driving_facts import driving_path_facts, driving_path_summary
from schedule_forensics.ai.factory import resolve_gateway_api_key
from schedule_forensics.ai.narrative import clean_polish, polish_prompt
from schedule_forensics.ai.ollama_process import OllamaLauncher
from schedule_forensics.ai.pair_facts import pairwise_comparison_facts
from schedule_forensics.ai.qa import (
    answer_question,
    build_fact_sheet,
    build_workbook_fact_sheet,
    figure_agreement,
    manipulation_forensics_facts,
)
from schedule_forensics.engine import (
    compute_driving_slack,
    recommend,
)
from schedule_forensics.engine.bow_wave import compute_bow_wave
from schedule_forensics.engine.cache import content_hash, get_default_cache
from schedule_forensics.engine.correlation import CorrelationSpec
from schedule_forensics.engine.cpm import (
    CPMError,
    CPMResult,
    datetime_to_offset,
    offset_to_datetime,
)
from schedule_forensics.engine.forecast import (
    compute_carnac_summary,
    compute_finish_forecasts,
)
from schedule_forensics.engine.grouping import (
    MAX_FIELDS,
    Criterion,
    available_fields,
    available_fields_union,
    distinct_values,
    field_value,
    filter_schedule,
    group_values,
)
from schedule_forensics.engine.jcl import (
    JCLConfig,
    JCLResult,
    compute_jcl,
    cost_loaded_total,
)
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.margin_guideline import (
    DEFAULT_CORRECTIVE_PCT,
    DEFAULT_WATCH_PCT,
    FIG_5_30_DEFAULT_RATES,
    FIG_5_30_ROWS,
    MONTH_WORK_DAYS,
    GuidelineBandConfig,
    band_position,
    expected_margin_band,
    margin_risk_read,
)
from schedule_forensics.engine.memory import (
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
    compute_activity_makeup,
    compute_bei,
    compute_dcma14,
    compute_ribbon,
    compute_schedule_quality,
    compute_wbs_breakdown,
    ribbon_offender_map,
)
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    non_summary,
)
from schedule_forensics.engine.metrics.evm import (
    compute_evm_indices,
    compute_schedule_variance,
)
from schedule_forensics.engine.metrics.field_forecast import compute_field_forecast
from schedule_forensics.engine.metrics.margin import (
    compute_margin_trend,
)
from schedule_forensics.engine.month_curves import compute_month_curves
from schedule_forensics.engine.msp_filters import (
    EVALUATOR_VERSION,
    required_prompts,
    selection_migration_delta,
)
from schedule_forensics.engine.path_counterfactual import (
    compute_path_counterfactual,
)
from schedule_forensics.engine.path_evolution import compute_path_evolution
from schedule_forensics.engine.projects import (
    Project,
)
from schedule_forensics.engine.recommendations import (
    Severity,
)
from schedule_forensics.engine.resources import (
    compute_resource_loading,
)
from schedule_forensics.engine.s_curve import compute_s_curve
from schedule_forensics.engine.saved_grouping import (
    find_saved_filter,
    find_saved_group,
    group_by_clauses,
    saved_filters_union,
    saved_groups_union,
)
from schedule_forensics.engine.scorecards import (
    compute_scorecards,
    reserve_recommendation,
)
from schedule_forensics.engine.sra import (
    ActivityRisk,
    BranchPlan,
    ConditionalBranch,
    OATSensitivity,
    ProbabilisticBranch,
    RiskEvent,
    RiskFactorTable,
    SRAConfig,
    SSIResult,
    _is_completed,
    compute_oat_sensitivity,
    compute_sra,
    compute_sra_ssi,
    deterministic_margin_bounds,
    factor_to_bc_wc,
    stored_finish_correction,
)
from schedule_forensics.engine.trend import (
    compute_quality_trend,
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
from schedule_forensics.importers.mpp_mpxj import mpp_capability, mpxj_batch_session
from schedule_forensics.logging_redaction import configure_logging
from schedule_forensics.model.saved_view import SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.net_guard import (
    assert_local_only,
    is_approved_gateway_endpoint,
    is_local_http_endpoint,
    is_loopback_host,
)
from schedule_forensics.reports.docx import (
    Block,
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

# ADR-0376 (phase 3, slice 12): the /analysis page family — the per-schedule report body,
# the chapter-01 "Where we stand" header, the DCMA cell/card builders and the analysis-page
# panels — lives in ``web/analysis.py`` now, extracted verbatim. Same ``X as X`` re-export
# idiom. `_target_panel` descended to ``web/components.py`` in the same slice (3 families).
from schedule_forensics.web.analysis import _EROSION_BADGE as _EROSION_BADGE
from schedule_forensics.web.analysis import _WEEKDAY_NAMES as _WEEKDAY_NAMES
from schedule_forensics.web.analysis import _analysis_body as _analysis_body
from schedule_forensics.web.analysis import _analysis_data as _analysis_data
from schedule_forensics.web.analysis import _calendar_panel as _calendar_panel
from schedule_forensics.web.analysis import _cites_cell as _cites_cell
from schedule_forensics.web.analysis import _completion_panel as _completion_panel
from schedule_forensics.web.analysis import _constraint_checks_panel as _constraint_checks_panel
from schedule_forensics.web.analysis import _dcma_card as _dcma_card
from schedule_forensics.web.analysis import _dcma_count_cells as _dcma_count_cells
from schedule_forensics.web.analysis import _dcma_definition_cell as _dcma_definition_cell
from schedule_forensics.web.analysis import _dcma_label as _dcma_label
from schedule_forensics.web.analysis import _dcma_measure as _dcma_measure
from schedule_forensics.web.analysis import _dcma_metric_cell as _dcma_metric_cell
from schedule_forensics.web.analysis import _float_bands_panel as _float_bands_panel
from schedule_forensics.web.analysis import _float_erosion_panel as _float_erosion_panel
from schedule_forensics.web.analysis import _float_histogram_panel as _float_histogram_panel
from schedule_forensics.web.analysis import _health_checks_panel as _health_checks_panel
from schedule_forensics.web.analysis import _logic_checks_panel as _logic_checks_panel
from schedule_forensics.web.analysis import _margin_panel as _margin_panel
from schedule_forensics.web.analysis import _scatter_panel as _scatter_panel
from schedule_forensics.web.analysis import _schedule_variance_panel as _schedule_variance_panel
from schedule_forensics.web.analysis import _stoplight_board as _stoplight_board
from schedule_forensics.web.analysis import (
    _vertical_integration_panel as _vertical_integration_panel,
)
from schedule_forensics.web.analysis import _where_we_stand_header as _where_we_stand_header

# ADR-0387 (phase 4, slice 22): THREE page families leave together, each extracted verbatim
# and each re-exported with the same ``X as X`` idiom — the /brief document body with the export
# title only it reads (``web/brief.py``), the /card ID card and the count/percent pivot table
# only it calls (``web/card.py``), and the /scorecards ribbons, their export table and the
# committed-date parser behind the reserve API (``web/scorecards.py``). ``brief`` is seeded on
# the EXACT route list, never the substring: it is a prefix of ``briefing``, which left in
# slice 23 (ADR-0388) as its own module — the two families are still seeded separately, and
# that is exactly why.
from schedule_forensics.web.brief import _BRIEF_XLSX_TITLE as _BRIEF_XLSX_TITLE
from schedule_forensics.web.brief import _brief_body as _brief_body

# ADR-0388 (phase 4, slice 23): the /briefing and /cei page families leave together, both
# extracted verbatim, both re-exported with the same ``X as X`` idiom. Both carry ZERO descents
# — and the record said ``briefing`` carried three. Re-walked, its supposed AI-backend descents
# belong to ``settings`` (``_ollama_or_none`` / ``_openai_or_none``, reached from
# ``_ai_status_note`` and ``_settings_body``) or are reached only from a ROUTE
# (``_active_backend``, from ``/api/ai/briefing``), and a route-only referrer never forces a
# descent. All three stay here.
from schedule_forensics.web.briefing import _BRIEFING_XLSX_TITLE as _BRIEFING_XLSX_TITLE
from schedule_forensics.web.briefing import _briefing_body as _briefing_body
from schedule_forensics.web.briefing import _briefing_table_html as _briefing_table_html
from schedule_forensics.web.briefing import _cite_tag as _cite_tag
from schedule_forensics.web.briefing import _the_briefing_header as _the_briefing_header
from schedule_forensics.web.card import _card_body as _card_body
from schedule_forensics.web.card import _count_bar_table as _count_bar_table
from schedule_forensics.web.cei import _cei_body as _cei_body
from schedule_forensics.web.cei import _cei_data as _cei_data
from schedule_forensics.web.cei import _stack_not_measured as _stack_not_measured
from schedule_forensics.web.cei import _work_piling_header as _work_piling_header

# ADR-0349 (phase 2 of the monolith split): the page chrome — ``_LAYOUT``, the always-on
# banners, the story spine + nav, the explainers, ``_e``, and ``_page`` itself — lives in
# ``web/chrome.py`` now, extracted verbatim. Same ``X as X`` re-export idiom as phase 1 below.
# Phase 2's trap is NOT phase 1's: tests that read a module's SOURCE TEXT by path (the
# ``_LAYOUT`` script-order guards) do not fail when their subject moves — they quietly search a
# file that no longer contains it. Repoint them in the same commit as any further extraction.
from schedule_forensics.web.chrome import (
    _ASSET_VERSION as _ASSET_VERSION,
)
from schedule_forensics.web.chrome import (
    _CHAPTER_BY_NUM as _CHAPTER_BY_NUM,
)
from schedule_forensics.web.chrome import (
    _DRAWER_HTML as _DRAWER_HTML,
)
from schedule_forensics.web.chrome import (
    _EXPLAINERS as _EXPLAINERS,
)
from schedule_forensics.web.chrome import (
    _LAYOUT as _LAYOUT,
)
from schedule_forensics.web.chrome import (
    _OFF_SPINE as _OFF_SPINE,
)
from schedule_forensics.web.chrome import (
    _OP_TEXT as _OP_TEXT,
)
from schedule_forensics.web.chrome import (
    _SPINE as _SPINE,
)
from schedule_forensics.web.chrome import (
    _STATIC_REF as _STATIC_REF,
)
from schedule_forensics.web.chrome import (
    _STORY_CHAPTERS as _STORY_CHAPTERS,
)
from schedule_forensics.web.chrome import (
    _STORY_ORDER as _STORY_ORDER,
)
from schedule_forensics.web.chrome import (
    _TITLE_TO_CHAPTER as _TITLE_TO_CHAPTER,
)
from schedule_forensics.web.chrome import (
    _ask_panel_html as _ask_panel_html,
)
from schedule_forensics.web.chrome import (
    _banner_html as _banner_html,
)
from schedule_forensics.web.chrome import (
    _build_title_map as _build_title_map,
)
from schedule_forensics.web.chrome import (
    _bust_static as _bust_static,
)
from schedule_forensics.web.chrome import (
    _Chapter as _Chapter,
)
from schedule_forensics.web.chrome import (
    _chapter_kicker as _chapter_kicker,
)
from schedule_forensics.web.chrome import (
    _compliance_drawer as _compliance_drawer,
)
from schedule_forensics.web.chrome import (
    _criteria_text as _criteria_text,
)
from schedule_forensics.web.chrome import (
    _criterion_value_list as _criterion_value_list,
)
from schedule_forensics.web.chrome import (
    _cui_marking as _cui_marking,
)
from schedule_forensics.web.chrome import (
    _e as _e,
)
from schedule_forensics.web.chrome import (
    _endpoint_banner as _endpoint_banner,
)
from schedule_forensics.web.chrome import (
    _endpoint_clear_form as _endpoint_clear_form,
)
from schedule_forensics.web.chrome import (
    _expandable_more as _expandable_more,
)
from schedule_forensics.web.chrome import (
    _explain as _explain,
)
from schedule_forensics.web.chrome import (
    _filter_banner as _filter_banner,
)
from schedule_forensics.web.chrome import (
    _flash_html as _flash_html,
)
from schedule_forensics.web.chrome import (
    _global_sources_banner as _global_sources_banner,
)
from schedule_forensics.web.chrome import (
    _guide as _guide,
)
from schedule_forensics.web.chrome import (
    _observed_banner as _observed_banner,
)
from schedule_forensics.web.chrome import (
    _page as _page,
)
from schedule_forensics.web.chrome import (
    _page_explainer as _page_explainer,
)
from schedule_forensics.web.chrome import (
    _render_nav as _render_nav,
)
from schedule_forensics.web.chrome import (
    _render_target_control as _render_target_control,
)
from schedule_forensics.web.chrome import (
    _resolve_route as _resolve_route,
)
from schedule_forensics.web.chrome import (
    _role_strip as _role_strip,
)
from schedule_forensics.web.chrome import (
    _story_footer as _story_footer,
)
from schedule_forensics.web.chrome import (
    _utility_takeaway as _utility_takeaway,
)
from schedule_forensics.web.compare import _compare_body as _compare_body
from schedule_forensics.web.compare import _what_changed_header as _what_changed_header

# commit as any further extraction.
from schedule_forensics.web.components import _ANALYSIS_XLSX_TITLE as _ANALYSIS_XLSX_TITLE
from schedule_forensics.web.components import _EVO_TIER_LABEL as _EVO_TIER_LABEL
from schedule_forensics.web.components import _HB as _HB
from schedule_forensics.web.components import _HB_MARGIN_SEC as _HB_MARGIN_SEC
from schedule_forensics.web.components import _REMAIN_DAYS_DP as _REMAIN_DAYS_DP
from schedule_forensics.web.components import _TS_CAPTION_MARK as _TS_CAPTION_MARK
from schedule_forensics.web.components import (
    _affected_avg_remaining_days as _affected_avg_remaining_days,
)
from schedule_forensics.web.components import _analysis_export_attr as _analysis_export_attr
from schedule_forensics.web.components import _export_bar as _export_bar
from schedule_forensics.web.components import _focus_panel as _focus_panel
from schedule_forensics.web.components import _focus_rows as _focus_rows
from schedule_forensics.web.components import _latest_solvable as _latest_solvable
from schedule_forensics.web.components import _margin_terminology as _margin_terminology
from schedule_forensics.web.components import _mdY as _mdY
from schedule_forensics.web.components import _metric_help_cell as _metric_help_cell
from schedule_forensics.web.components import _metric_scorecard_table as _metric_scorecard_table
from schedule_forensics.web.components import _pair_prov_chip as _pair_prov_chip
from schedule_forensics.web.components import _panel_head as _panel_head
from schedule_forensics.web.components import _prov_chip as _prov_chip
from schedule_forensics.web.components import _schedule_risks as _schedule_risks
from schedule_forensics.web.components import _series_prov_chip as _series_prov_chip
from schedule_forensics.web.components import _shell_tools as _shell_tools

# ADR-0387: ``_sources_line`` DESCENDED into the shared kernel in slice 22. ``_scorecards_body``
# calls it and eight other page routes call it, so it could neither stay here (``scorecards.py``
# would have had to import UPWARD, closing a cycle) nor move into one page's module. Same
# resolution ADR-0351, ADR-0376 and ADR-0377 each reached for the same shape of name.
from schedule_forensics.web.components import _sources_line as _sources_line
from schedule_forensics.web.components import _sra_selected as _sra_selected
from schedule_forensics.web.components import _ssi_matrix_counts as _ssi_matrix_counts
from schedule_forensics.web.components import _stat_cards as _stat_cards
from schedule_forensics.web.components import _status_class as _status_class
from schedule_forensics.web.components import _status_stack as _status_stack
from schedule_forensics.web.components import _target_panel as _target_panel
from schedule_forensics.web.components import _task_name_across as _task_name_across
from schedule_forensics.web.components import _user_tip as _user_tip
from schedule_forensics.web.components import _volatility_data as _volatility_data

# ADR-0389 (phase 4, slice 24): the FOUR remaining zero-descent page families leave together —
# ``/curves`` (chapter 05's three monthly delivery curves), ``/ribbon`` (the Acumen-Fuse-style
# Schedule Quality Ribbon, its four ``#:``-documented threshold constants travelling with the
# code that reads them), ``/workbench`` (the Metric Workbench body) and ``/volatility``
# (critical-path membership churn). All four extracted verbatim, all four re-exported with the
# same ``X as X`` idiom. That empties the zero-descent set outside ``groups`` (fenced,
# ADR-0343); ``settings`` is the only page family left in this file, and its three shared
# AI-backend names are why it gets its own slice.
from schedule_forensics.web.curves import _curves_body as _curves_body
from schedule_forensics.web.curves import _curves_data as _curves_data
from schedule_forensics.web.curves import _curves_header as _curves_header

# ADR-0351 (phase 3, slice 2): the driving-path page family — ``_driving_data``,
# ``_driving_path_body``, ``_driving_tiers_panel`` and their private helpers — lives in
# ``web/driving.py`` now, extracted verbatim. First per-PAGE module, and the one the shared
# kernel (ADR-0350) had to come out before. Same ``X as X`` re-export idiom as phases 1-3.
from schedule_forensics.web.driving import _corridor_chips as _corridor_chips
from schedule_forensics.web.driving import _driving_data as _driving_data
from schedule_forensics.web.driving import _driving_path_body as _driving_path_body
from schedule_forensics.web.driving import _driving_path_gantt as _driving_path_gantt
from schedule_forensics.web.driving import _driving_tier_trend as _driving_tier_trend
from schedule_forensics.web.driving import _driving_tiers_panel as _driving_tiers_panel
from schedule_forensics.web.driving import _task_iso_dates as _task_iso_dates
from schedule_forensics.web.driving import _whole_schedule_data as _whole_schedule_data

# ADR-0377 (phase 3, slice 13): the /evm page family — the chapter-07 "How we execute"
# header, the EVM page body, the index/days formatters, the explainer and the threshold
# legend — lives in ``web/evm.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.evm import _evm_body as _evm_body
from schedule_forensics.web.evm import _evm_days_str as _evm_days_str
from schedule_forensics.web.evm import _evm_explainer as _evm_explainer
from schedule_forensics.web.evm import _evm_idx_str as _evm_idx_str
from schedule_forensics.web.evm import _how_we_execute_evm_header as _how_we_execute_evm_header
from schedule_forensics.web.evm import _threshold_legend as _threshold_legend
from schedule_forensics.web.evolution import _CH04_NUMERALS as _CH04_NUMERALS

# ADR-0350 (phase 3 of the monolith split): the SHARED presentation kernel — the panel-contract
# strip (``_panel_head``/``_shell_tools``/the provenance chips), the stat cards, the metric help
# cell, the status stack, the export bar and the shared formatters — lives in
# ``web/components.py`` now, extracted verbatim. Membership was measured: every name below is
# reached by the closure of THREE OR MORE page families, so no page module could own it. Same
# ``X as X`` re-export idiom as phases 1-2. The phase-2 trap applies here too: tests that read a
# module's SOURCE TEXT by path do not fail when their subject moves — repoint them in the same
# ADR-0352 (phase 3, slice 3): the /evolution page family - its body, the completed-on-path and
# counterfactual panels, the evolution/tier data builders and the shared trace-options controls -
# lives in ``web/evolution.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.evolution import _EVO_TIER_SELECT as _EVO_TIER_SELECT
from schedule_forensics.web.evolution import _completed_on_path_panel as _completed_on_path_panel
from schedule_forensics.web.evolution import _counterfactual_panel as _counterfactual_panel
from schedule_forensics.web.evolution import _delta_words as _delta_words
from schedule_forensics.web.evolution import _evolution_body as _evolution_body
from schedule_forensics.web.evolution import _evolution_data as _evolution_data
from schedule_forensics.web.evolution import _evolution_export_scope as _evolution_export_scope
from schedule_forensics.web.evolution import _evolution_state_qs as _evolution_state_qs
from schedule_forensics.web.evolution import _evolution_tier_data as _evolution_tier_data
from schedule_forensics.web.evolution import _how_stable_header as _how_stable_header
from schedule_forensics.web.evolution import _keep_hidden as _keep_hidden
from schedule_forensics.web.evolution import _optioned_versions as _optioned_versions
from schedule_forensics.web.evolution import _project_finish_uid as _project_finish_uid
from schedule_forensics.web.evolution import _render_counterfactual as _render_counterfactual
from schedule_forensics.web.evolution import _stability_panels as _stability_panels
from schedule_forensics.web.evolution import _trace_option_names as _trace_option_names
from schedule_forensics.web.evolution import _trace_options_form as _trace_options_form
from schedule_forensics.web.evolution import _whatif_added_rows as _whatif_added_rows

# ADR-0374 (phase 3, slice 10): the /forecast page family - the where-it-lands chapter header,
# the Carnac KPI cards, the method ruler + explainer, the per-field execution panel and its
# group rollup, the page body and the /api/forecast data builder - lives in
# ``web/forecast.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.forecast import _FORECAST_METHOD_COLORS as _FORECAST_METHOD_COLORS
from schedule_forensics.web.forecast import _carnac_cards as _carnac_cards
from schedule_forensics.web.forecast import _field_forecast_panel as _field_forecast_panel
from schedule_forensics.web.forecast import _forecast_body as _forecast_body
from schedule_forensics.web.forecast import _forecast_data as _forecast_data
from schedule_forensics.web.forecast import _forecast_explainer as _forecast_explainer
from schedule_forensics.web.forecast import _forecast_ruler as _forecast_ruler
from schedule_forensics.web.forecast import _group_rollup_panel as _group_rollup_panel
from schedule_forensics.web.forecast import _where_it_lands_header as _where_it_lands_header
from schedule_forensics.web.help import (
    METRIC_DICTIONARY,
    reliability_dimension,
)

# ADR-0358 (phase 3, slice 4): the /integrity page family - the chapter header and the page body
# (findings table + drill, per-change effects, counterfactual) - lives in ``web/integrity.py``
# now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.integrity import _integrity_body as _integrity_body
from schedule_forensics.web.integrity import _integrity_header as _integrity_header
from schedule_forensics.web.integrity import _integrity_ledger_tables as _integrity_ledger_tables
from schedule_forensics.web.integrity import _lag_chip as _lag_chip
from schedule_forensics.web.integrity import _ledger_was_now as _ledger_was_now
from schedule_forensics.web.integrity import _logic_changes_panel as _logic_changes_panel
from schedule_forensics.web.integrity import _target_effect_html as _target_effect_html
from schedule_forensics.web.integrity import _was_now as _was_now
from schedule_forensics.web.launch import _EMPTY_ACTION as _EMPTY_ACTION
from schedule_forensics.web.launch import _NONE as _NONE
from schedule_forensics.web.launch import _QUICK_ACTIONS as _QUICK_ACTIONS
from schedule_forensics.web.launch import _boot_facts as _boot_facts

# ADR-0426: the boot screen served at /launch. Its own module because it is the one route that
# does NOT render through ``_page`` — a startup screen with a nav rail is a dashboard with a
# picture on it. Same ``X as X`` re-export idiom as every other extracted page family.
from schedule_forensics.web.launch import _BootFacts as _BootFacts
from schedule_forensics.web.launch import _launch_html as _launch_html
from schedule_forensics.web.launch import _quick_action_html as _quick_action_html

# ADR-0363 (phase 3, slice 5): the /margin page family - the Executive Margin Dashboard
# (burn-down, Fig 5-30 band, erosion trend, risk-sufficiency shell) - lives in
# ``web/margin.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.margin import _band_payload as _band_payload
from schedule_forensics.web.margin import _margin_band_control as _margin_band_control
from schedule_forensics.web.margin import _margin_dashboard_body as _margin_dashboard_body
from schedule_forensics.web.margin import _margin_dashboard_data as _margin_dashboard_data
from schedule_forensics.web.margin import _margin_dashboard_for as _margin_dashboard_for
from schedule_forensics.web.margin import _margin_dashboard_header as _margin_dashboard_header
from schedule_forensics.web.margin import _margin_rate_control as _margin_rate_control
from schedule_forensics.web.margin import _margin_risk_panel as _margin_risk_panel
from schedule_forensics.web.margin import _solvable_scoped_versions as _solvable_scoped_versions
from schedule_forensics.web.margin import _wmpd_label as _wmpd_label

# ADR-0372 (phase 3, slice 8): Mission Control's wall body - the tile mosaic, the verdict
# band and the ctl KPI tiles - lives in ``web/mission.py`` now, extracted verbatim. Same
# ``X as X`` re-export idiom.
from schedule_forensics.web.mission import _mission_body as _mission_body
from schedule_forensics.web.offload import (
    OFFLOAD_TASK_THRESHOLD,
    run_maybe_offloaded,
    shutdown_offload,
)
from schedule_forensics.web.path import _path_body as _path_body
from schedule_forensics.web.path import _what_drives_header as _what_drives_header

# ADR-0378 (phase 3, slice 14): the /performance page family - the memoised per-version
# G1-G5 block, the dataset builder the page AND the export share, the chapter-07 header and
# the page body - lives in ``web/performance.py`` now, extracted verbatim. Same ``X as X``
# re-export idiom.
from schedule_forensics.web.performance import _how_we_execute_header as _how_we_execute_header
from schedule_forensics.web.performance import _perf_version_block as _perf_version_block
from schedule_forensics.web.performance import _performance_body as _performance_body
from schedule_forensics.web.performance import _performance_data as _performance_data

# ADR-0375 (phase 3, slice 11): the /portfolio page family - the cross-project rollup
# ledger, the resident-memory panel and the version-history rows - lives in
# ``web/portfolio.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.portfolio import _portfolio_body as _portfolio_body
from schedule_forensics.web.portfolio import _portfolio_combine_panel as _portfolio_combine_panel
from schedule_forensics.web.portfolio import _portfolio_memory_panel as _portfolio_memory_panel
from schedule_forensics.web.portfolio import _portfolio_version_li as _portfolio_version_li

# ADR-0379 (phase 3, slice 15): the /resources page family - the CSP-safe loading payload,
# the how-to-read explainer, the chapter-08 "Who is overloaded" header and the page body -
# lives in ``web/resources.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.resources import _resource_loading_json as _resource_loading_json
from schedule_forensics.web.resources import _resources_body as _resources_body
from schedule_forensics.web.resources import _resources_explainer as _resources_explainer
from schedule_forensics.web.resources import _who_is_overloaded_header as _who_is_overloaded_header
from schedule_forensics.web.ribbon import _RIBBON_CLS_VERDICT as _RIBBON_CLS_VERDICT
from schedule_forensics.web.ribbon import _RIBBON_FLOAT_EXTRAS as _RIBBON_FLOAT_EXTRAS
from schedule_forensics.web.ribbon import _RIBBON_PCT5 as _RIBBON_PCT5
from schedule_forensics.web.ribbon import _RIBBON_WARN_FRACTION as _RIBBON_WARN_FRACTION
from schedule_forensics.web.ribbon import _RIBBON_ZERO_TOLERANCE as _RIBBON_ZERO_TOLERANCE
from schedule_forensics.web.ribbon import _can_we_trust_header as _can_we_trust_header
from schedule_forensics.web.ribbon import _ribbon_body as _ribbon_body
from schedule_forensics.web.ribbon import _ribbon_cell_class as _ribbon_cell_class
from schedule_forensics.web.ribbon import _ribbon_cell_title as _ribbon_cell_title

# ADR-0383 (phase 4, slice 19): the /risks page family - the 5x5 risk matrix, the score ranking,
# the finding card + its quantified read, the band classifier, the working-days formatter, the
# three findings sections and the page body - lives in ``web/risks.py`` now, extracted verbatim.
# Same ``X as X`` re-export idiom.
from schedule_forensics.web.risks import _IMPACT_LABELS as _IMPACT_LABELS
from schedule_forensics.web.risks import _LIKELIHOOD_LABELS as _LIKELIHOOD_LABELS
from schedule_forensics.web.risks import _RISKS_EXPORT as _RISKS_EXPORT
from schedule_forensics.web.risks import _RISKS_XLSX_TITLE as _RISKS_XLSX_TITLE
from schedule_forensics.web.risks import _finding_card as _finding_card
from schedule_forensics.web.risks import _finding_quant as _finding_quant
from schedule_forensics.web.risks import _risk_band as _risk_band
from schedule_forensics.web.risks import _risk_matrix as _risk_matrix
from schedule_forensics.web.risks import _risk_ranking as _risk_ranking
from schedule_forensics.web.risks import _risks_body as _risks_body
from schedule_forensics.web.risks import _risks_section as _risks_section
from schedule_forensics.web.risks import _wd as _wd

# ADR-0387 (phase 4, slice 22): the /scorecards page family — the status-class lookup, the
# export table, the ribbon panel, the page body, and ``_parse_committed_date``, which lived
# 6,500 lines away and is reached only by the reserve-sizing API. Unlike the families since
# ADR-0378, this one's EXPORT shares the page's surface: ``export_scorecards`` calls
# ``_scorecard_export_table``, so both export formats sit inside the family's proven surface.
from schedule_forensics.web.scorecards import _parse_committed_date as _parse_committed_date
from schedule_forensics.web.scorecards import _sc_status_class as _sc_status_class
from schedule_forensics.web.scorecards import _scorecard_export_table as _scorecard_export_table
from schedule_forensics.web.scorecards import _scorecard_panel as _scorecard_panel
from schedule_forensics.web.scorecards import _scorecards_body as _scorecards_body

# ADR-0380 (phase 3, slice 16): the /scurve page family - the per-chart filter machinery, the
# shared status point, the AI-interpretation panel, the chapter-09 header, the animated page
# body and the chart's JSON payload - lives in ``web/scurve.py`` now, extracted verbatim. Same
# ``X as X`` re-export idiom.
from schedule_forensics.web.scurve import _pair_criteria as _pair_criteria
from schedule_forensics.web.scurve import _scurve_body as _scurve_body
from schedule_forensics.web.scurve import _scurve_data as _scurve_data
from schedule_forensics.web.scurve import _scurve_filter_fields as _scurve_filter_fields
from schedule_forensics.web.scurve import _scurve_header as _scurve_header
from schedule_forensics.web.scurve import _scurve_interpretation as _scurve_interpretation
from schedule_forensics.web.scurve import _scurve_status_point as _scurve_status_point

# ADR-0390 (phase 4, slice 25): the /settings page family — the AI-settings page body, its
# backend explainer, and the status/runtime notes it renders — lives in ``web/settings.py`` now,
# extracted verbatim, with the SAME ``X as X`` re-export idiom. It travels with a five-name
# AI-backend closure (``_ollama_or_none``, ``_openai_or_none``, ``_second_backend``,
# ``_UseMarking``, ``_BACKEND_PROBE_TTL``) that a first-round pricing missed: ADR-0389 recorded
# three descent CANDIDATES, and ``_second_backend`` needs two more names that ``_active_backend``
# also uses. NONE of the five is a forced descent — no extracted module references them, so they
# move into the family module and ``_active_backend`` / ``_ask_response`` stay here and reach them
# through this re-export (ADR-0351's rule permits either remedy; only a referrer in another
# extracted module forces ``components.py``).
from schedule_forensics.web.settings import _BACKEND_PROBE_TTL as _BACKEND_PROBE_TTL
from schedule_forensics.web.settings import _OLLAMA_ENV_VARS as _OLLAMA_ENV_VARS
from schedule_forensics.web.settings import _RUNTIME_STATUS_NOTES as _RUNTIME_STATUS_NOTES
from schedule_forensics.web.settings import _ai_backend_explainer as _ai_backend_explainer
from schedule_forensics.web.settings import _ai_runtime_note as _ai_runtime_note
from schedule_forensics.web.settings import _ai_status_note as _ai_status_note
from schedule_forensics.web.settings import _gateway_or_none as _gateway_or_none
from schedule_forensics.web.settings import _gateway_status_note as _gateway_status_note
from schedule_forensics.web.settings import _model_installed as _model_installed
from schedule_forensics.web.settings import _ollama_or_none as _ollama_or_none
from schedule_forensics.web.settings import _openai_or_none as _openai_or_none
from schedule_forensics.web.settings import _second_backend as _second_backend
from schedule_forensics.web.settings import _settings_body as _settings_body
from schedule_forensics.web.settings import _UseMarking as _UseMarking

# ADR-0373 (phase 3, slice 9): the /sra page family - the panel wall (SSI panel, correlation
# matrix, JCL, overrides, risk/branch/conditional sections), the report/export tables and
# charts, the page body and the /api/sra data builder - lives in ``web/sra.py`` now,
# extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.sra import _CONSEQUENCE_HINT as _CONSEQUENCE_HINT
from schedule_forensics.web.sra import _NASA_CONS_OPP as _NASA_CONS_OPP
from schedule_forensics.web.sra import _NASA_CONS_RISK as _NASA_CONS_RISK
from schedule_forensics.web.sra import _NASA_FILL as _NASA_FILL
from schedule_forensics.web.sra import _NASA_LIK as _NASA_LIK
from schedule_forensics.web.sra import _NASA_RANK as _NASA_RANK
from schedule_forensics.web.sra import _NASA_ZONE as _NASA_ZONE
from schedule_forensics.web.sra import _OCC_EXACT as _OCC_EXACT
from schedule_forensics.web.sra import _OCC_RANDOM as _OCC_RANDOM
from schedule_forensics.web.sra import _SRA_EXPORT as _SRA_EXPORT
from schedule_forensics.web.sra import _SRA_RISK_IMPACT_FIELD as _SRA_RISK_IMPACT_FIELD
from schedule_forensics.web.sra import _SRA_RISK_PROB_FIELD as _SRA_RISK_PROB_FIELD
from schedule_forensics.web.sra import _SRA_XLSX_TITLE as _SRA_XLSX_TITLE
from schedule_forensics.web.sra import _branch_section as _branch_section
from schedule_forensics.web.sra import _conditional_section as _conditional_section
from schedule_forensics.web.sra import _correlation_matrix_panel as _correlation_matrix_panel
from schedule_forensics.web.sra import _file_stored_risks as _file_stored_risks
from schedule_forensics.web.sra import _jcl_panel as _jcl_panel
from schedule_forensics.web.sra import _sra_body as _sra_body
from schedule_forensics.web.sra import _sra_chart_hist as _sra_chart_hist
from schedule_forensics.web.sra import _sra_chart_scurve as _sra_chart_scurve
from schedule_forensics.web.sra import _sra_chart_tornado as _sra_chart_tornado
from schedule_forensics.web.sra import _sra_data as _sra_data
from schedule_forensics.web.sra import _sra_explainers as _sra_explainers
from schedule_forensics.web.sra import _sra_matrix_chart as _sra_matrix_chart
from schedule_forensics.web.sra import _sra_overrides_table as _sra_overrides_table
from schedule_forensics.web.sra import _sra_report_blocks as _sra_report_blocks
from schedule_forensics.web.sra import _ssi_export_tables as _ssi_export_tables
from schedule_forensics.web.sra import _ssi_panel as _ssi_panel
from schedule_forensics.web.sra import _unified_risk_section as _unified_risk_section
from schedule_forensics.web.sra import _what_could_go_wrong_header as _what_could_go_wrong_header

# ADR-0365 (phase 3, slice 7): the SSI run machinery - the /api/sra/ssi dataset builder, the
# factor grid rows and the setup Save/Load - lives in ``web/ssi.py`` now, extracted verbatim.
# Same ``X as X`` re-export idiom.
from schedule_forensics.web.ssi import _SRA_BC_FIELD as _SRA_BC_FIELD
from schedule_forensics.web.ssi import _SRA_FACTOR_FIELD as _SRA_FACTOR_FIELD
from schedule_forensics.web.ssi import _SRA_WC_FIELD as _SRA_WC_FIELD
from schedule_forensics.web.ssi import _SSI_SETUP_VERSION as _SSI_SETUP_VERSION
from schedule_forensics.web.ssi import _apply_ssi_setup as _apply_ssi_setup
from schedule_forensics.web.ssi import _file_stored_sra_inputs as _file_stored_sra_inputs
from schedule_forensics.web.ssi import _schedule_sra_fingerprint as _schedule_sra_fingerprint
from schedule_forensics.web.ssi import _setup_vintage_warning as _setup_vintage_warning
from schedule_forensics.web.ssi import _ssi_data as _ssi_data
from schedule_forensics.web.ssi import _ssi_grid_rows as _ssi_grid_rows
from schedule_forensics.web.ssi import _ssi_setup_dict as _ssi_setup_dict

# ADR-0384 (phase 4, slice 20): the /standards page family - the value cell, the metric rows,
# the one-family section panel and the page body - lives in ``web/standards.py`` now, extracted
# verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.standards import _standards_body as _standards_body
from schedule_forensics.web.standards import _standards_rows as _standards_rows
from schedule_forensics.web.standards import _standards_section as _standards_section
from schedule_forensics.web.standards import _standards_value_cell as _standards_value_cell
from schedule_forensics.web.state import (
    _ANALYSIS_CACHE_MAX as _ANALYSIS_CACHE_MAX,
)
from schedule_forensics.web.state import (
    _CPM_CACHE_MAX as _CPM_CACHE_MAX,
)
from schedule_forensics.web.state import (
    _ROLE_BY_ID as _ROLE_BY_ID,
)
from schedule_forensics.web.state import (
    _ROLES as _ROLES,
)
from schedule_forensics.web.state import (
    _UNTITLED_PID as _UNTITLED_PID,
)

# ADR-0297 (phase 1 of the monolith split): the session-state machinery lives in
# ``web/state.py`` now, extracted verbatim. The ``X as X`` form is the explicit re-export
# idiom (mypy strict + ruff): every existing ``web.app`` import path and monkeypatch target
# keeps working; tests that patch the engine callables *called from state.py* patch state.
from schedule_forensics.web.state import (
    SessionState as SessionState,
)
from schedule_forensics.web.state import (
    UnifiedRisk as UnifiedRisk,
)
from schedule_forensics.web.state import (
    _activity_rows as _activity_rows,
)
from schedule_forensics.web.state import (
    _Analysis as _Analysis,
)
from schedule_forensics.web.state import (
    _AskFact as _AskFact,
)
from schedule_forensics.web.state import (
    _AskRecord as _AskRecord,
)
from schedule_forensics.web.state import (
    _compute_analysis as _compute_analysis,
)
from schedule_forensics.web.state import (
    _dash_core as _dash_core,
)
from schedule_forensics.web.state import (
    _DashCore as _DashCore,
)
from schedule_forensics.web.state import (
    _Flash as _Flash,
)
from schedule_forensics.web.state import (
    _iso_date as _iso_date,
)
from schedule_forensics.web.state import (
    _LRUCache as _LRUCache,
)
from schedule_forensics.web.state import (
    _Role as _Role,
)

# ADR-0364 (phase 3, slice 6): the /trend page family - the "How it moved" header, the
# multi-version trend body and the /api/trend dataset builder - lives in ``web/trend.py``
# now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.trend import _how_it_moved_header as _how_it_moved_header
from schedule_forensics.web.trend import _trend_body as _trend_body
from schedule_forensics.web.trend import _trend_data as _trend_data
from schedule_forensics.web.volatility import _volatility_body as _volatility_body

# ADR-0386 (phase 4, slice 21): the /wbs page family - the optional-number table cell, the
# completion + SPI(t)/Earned-Schedule pivots, and the combo chart's JSON payload - lives in
# ``web/wbs.py`` now, extracted verbatim. Same ``X as X`` re-export idiom.
from schedule_forensics.web.wbs import _num as _num
from schedule_forensics.web.wbs import _wbs_body as _wbs_body
from schedule_forensics.web.wbs import _wbs_data as _wbs_data
from schedule_forensics.web.workbench import _workbench_body as _workbench_body

logger = logging.getLogger("schedule_forensics.web")


def _export_cell(result: MetricResult | None) -> float | str:
    """A metric's exported value, or blank when the metric does not apply (MF-02, ADR-0411).

    NOT_APPLICABLE is carried by ``status``; ``value`` is 0.0 on such a result, so guarding a
    workbook cell on ``value is not None`` writes a fabricated 0.00 for every index the page
    honestly renders as NA. Law 2, and the design system's "missing shows an em dash, never a
    fabricated figure" — a workbook leaves the tool and gets quoted.
    """
    if result is None or result.status is CheckStatus.NOT_APPLICABLE or result.value is None:
        return ""
    return result.value


#: Locally-vendored static assets (CSS/JS) — served from /static; no CDN, no external fetch.
_STATIC_DIR = Path(__file__).parent / "static"


#: Bundled, non-CUI sample schedule for the "Load example" button.
_EXAMPLE = Path(__file__).parent / "examples" / "house_build.json"
#: File types the open/import picker accepts.
_ACCEPT = ".json,.xml,.mspdi,.xer,.mpp,.mpt"

#: Per-file upload cap (bytes). Local operator files; largest real exports are well under this.
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024

#: Cap for a saved **SSI setup JSON** (ADR-0313) — deliberately far below `_MAX_UPLOAD_BYTES`,
#: which is sized for an `.mpp`. A setup is scalars plus a per-UID factor / Best-Worst map, so
#: 8 MB holds a schedule an order of magnitude larger than any reference file. Reusing the 500 MB
#: schedule bound here would have been a cap in name only.
_MAX_SETUP_BYTES = 8 * 1024 * 1024


#: ADR-0261 P5: cap on the OAT sensitivity sweep's candidate activities (2 CPM solves each).
#: Far above any realistic schedule (sweeps below it are byte-identical to uncapped); above it
#: the largest-remaining candidates are swept and the payload + panel disclose the cap.
_OAT_MAX_ACTIVITIES = 1500


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
        gateway_backend=_gateway_or_none(state.ai_config),
    )
    hook = state.ai_use_hook
    if hook is not None and backend.name == "ollama":
        # ADR-0315: a successful generate marks REAL model use for the shutdown tiers.
        backend = _UseMarking(backend, hook, state.ai_config.model, state.ai_config.endpoint)
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
        if sep and _decimal_digits(num.strip()) and int(num.strip()) < len(texts) and es.strip():
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
    # ADR-0261 P1: epoch-keyed like the peer caches — a filter/target change switches the key,
    # so a narrative polished against one population can never serve another (the entry was
    # reattached/figure-verified against THAT epoch's analysis statements).
    key = state._cache_key(key, state.scope_signature())
    # the polished cache is guarded by the same _lock as its peer caches (audit ADR-0250): take it
    # for each atomic get/put — NOT across the slow backend.generate below, which would serialize
    # every narrative request — so a concurrent clear() (ai_off / wipe) can never race the
    # multi-step get_lru/put (the D18 KeyError hazard).
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


def _decimal_digits(text: str) -> bool:
    """``str.isdigit()`` corrected to the digits ``int()`` and ``float()`` actually accept.

    ``str.isdigit()`` is **True** for superscripts (``"\u00b2"``) and circled forms (``"\u2460"``)
    that ``int()`` rejects with ``ValueError``, so an ``isdigit()``-gated conversion is not a guard
    at all: it lets the value through and then crashes. A fuzz of every route's every declared
    field found **12 routes across 5 sites** answering 500 to a superscript typed into an ordinary
    form field (audit 2026-08-16, ``ISDIGIT-INT-500``).

    ``str.isdecimal()`` is the EXACT predicate, and that is measured rather than assumed: across
    all 788 single-character numeric code points, ``isdecimal()`` disagrees with ``int()`` on
    **zero**, while ``isdigit()`` disagrees on 128. Narrowing to ASCII instead would have been a
    different bug — it rejects 650 code points ``int()`` handles fine, including the Arabic-Indic
    digits, so a value that used to parse would silently stop parsing.

    Callers keep their own sign policy — strip the sign before asking, exactly as with
    ``isdigit()``.
    """
    return text.isdecimal()


def _parse_uid(value: str | None) -> int | None:
    """A UniqueID from form/query text — blank, non-numeric, or non-positive means none."""
    if value is None:
        return None
    text = value.strip()
    if not _decimal_digits(text):
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


def _drill_uid_set(sch: Schedule, analysis: _Analysis, uids: str, segment: str) -> tuple[int, ...]:
    """The UID set behind a drill request — an explicit ``uids`` list, or a named ``segment``
    resolved server-side (ADR-0288).

    The cross-file-comparison charts (status split / activity makeup / completion performance)
    partition the WHOLE schedule, so shipping their UID arrays in ``/api/trend`` cost ~21.8 KiB per
    version (46% of the payload) for data only ever read on a click. The client now marks those bars
    with a segment NAME and this resolver rebuilds the set on demand, using the SAME predicates the
    payload used — so the drill result is byte-identical, it is just no longer pre-shipped.

    An explicit ``uids`` list always wins (every other drill trigger still passes one); an unknown
    segment resolves to the empty set, which the drill renders as "no activities".
    """
    if uids:
        return tuple(_parse_uid_list(uids))
    if not segment:
        return ()
    ns = non_summary(sch)
    if segment == "complete":
        return tuple(t.unique_id for t in ns if t.percent_complete >= 100.0)
    if segment == "in_progress":
        return tuple(t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0)
    if segment == "planned":
        return tuple(t.unique_id for t in ns if t.percent_complete <= 0.0)
    if segment == "milestones":
        return tuple(t.unique_id for t in ns if t.is_milestone)
    if segment == "normal":
        return tuple(t.unique_id for t in ns if not t.is_milestone)
    if segment == "summaries":
        return tuple(t.unique_id for t in sch.tasks if t.is_summary and t.unique_id != 0)
    # completion performance — the engine already computed these offender sets for this version
    cp_key = {
        "ahead": "completed_ahead",
        "on_schedule": "completed_on_schedule",
        "behind": "completed_behind",
    }.get(segment)
    if cp_key is not None:
        return tuple(analysis.completion[cp_key].offender_uids)
    return ()


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


#: Content-Security-Policy that enforces the air-gap (Law 1) in EVERY browser at runtime, not
#: just in the test: ``default-src``/``connect-src``/``img-src`` are ``'self'`` so the page can
#: never pull or beacon to a remote host (no CDN, no font, no exfil fetch). ``script-src`` is
#: STRICT ``'self'`` (ADR-0268, closing the long-tracked follow-up): every former inline
#: handler is delegated in ``chrome.js`` via ``data-sf-*`` attributes, and every boot payload
#: is a non-executable ``<script type="application/json">`` block its consumer parses — so an
#: injected inline script or ``on*=`` handler cannot execute even if markup escaping ever
#: failed (defense in depth: the tool renders opposing-party file content). ``style-src`` keeps
#: ``'unsafe-inline'`` for the UI's legitimate inline ``style=`` (the Gantt's px widths) —
#: inline styles cannot execute code and remote styles stay forbidden.
_CSP = (
    "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
    "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'"
)
#: Security headers added to every response (CSP enforces the air-gap; nosniff/Referrer/Frame
#: are free hardening for the CUI threat model — the operator analyzes opposing-party files).
_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

#: SEC-3 (ADR-0264): the Host allowlist. The tool binds loopback only, but a DNS-rebinding
#: page (an attacker domain the victim's browser re-resolves to 127.0.0.1) reaches it with the
#: ATTACKER'S name in the Host header — on a production machine that is a read path to real
#: CUI. Only genuine loopback names are served. "testserver" is Starlette TestClient's default
#: base host: a single-label name public DNS cannot resolve, so admitting it adds no rebinding
#: surface (rebinding needs an attacker-controlled RESOLVABLE domain riding in Host).
_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})


def _host_allowed(host_header: str) -> bool:
    """True when the Host header names a loopback (or test) host — port ignored, IPv6 brackets
    handled. An absent/unparseable Host is rejected (HTTP/1.1 requires one)."""
    try:
        hostname = urlsplit("//" + host_header.strip()).hostname
    except ValueError:
        return False
    return hostname is not None and hostname in _ALLOWED_HOSTS


def _origin_allowed(origin_header: str | None) -> bool:
    """The FALLBACK CSRF check (used only when ``Sec-Fetch-Site`` is absent): True when the
    Origin is absent or loopback. An ABSENT Origin is a non-browser local client (curl,
    tests, the launcher's probes), not the CSRF vector, so it passes; a foreign or ``null``
    Origin is rejected."""
    if origin_header is None:
        return True
    try:
        parts = urlsplit(origin_header)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and parts.hostname in _ALLOWED_HOSTS


def _csrf_safe(sec_fetch_site: str | None, origin_header: str | None) -> bool:
    """SEC-2 (ADR-0264, corrected ADR-0268): is a state-mutating request non-cross-site?

    The PRIMARY signal is ``Sec-Fetch-Site`` — a browser-set forbidden header a cross-site
    page cannot forge, and (unlike ``Origin``) NOT nulled by the app's ``Referrer-Policy:
    no-referrer`` on same-origin **form** navigations. ``same-origin`` (the tool's own
    forms/fetches) and ``none`` (a user-initiated top-level navigation — address bar,
    bookmark; not a CSRF vector) pass; ``cross-site`` / ``same-site`` / ``cross-origin`` are
    the CSRF signatures and are refused. When the header is ABSENT (a non-browser client, or
    a browser too old to send Fetch Metadata) we fall back to the Origin check, which passes
    absent-Origin non-browser clients and loopback origins while refusing foreign ones.

    Why the correction: the Origin-only gate refused EVERY real-browser POST **form**
    navigation — ``no-referrer`` makes Chromium send ``Origin: null`` on those, which the old
    gate read as cross-site (surfaced by ADR-0268's browser verification; the ADR-0264 probe
    had only exercised ``fetch`` POSTs, which do carry a real Origin)."""
    if sec_fetch_site is not None:
        return sec_fetch_site in ("same-origin", "none")
    return _origin_allowed(origin_header)


#: methods that can change session state — the only ones SEC-2 gates (Sec-Fetch-Site/Origin
#: are not sent on same-origin GET navigations, so gating reads would break normal use)
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: ADR-0265: driving-tiers drill columns whose values are SOLVED (stored-network dates/float/
#: criticality) — dropped from the drill and its Excel while the counterfactual trace options
#: are active, so a re-solved view never mixes in stored-basis figures. Labels as the drill
#: sends them in ``cols``; the basis-independent INPUT columns (durations, %, WBS, resources,
#: baselines, custom fields) always remain.
_SOLVE_DEPENDENT_COLS = frozenset({"Start", "Finish", "Total float (d)", "Critical"})

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
    app = FastAPI(title="POLARIS", docs_url=None, redoc_url=None, lifespan=_cui_lifespan)
    # ADR-0404: the desktop-launch path (no injected state) comes up with the PERSISTED AI
    # settings — armed once, armed on every launch. An explicitly injected state (tests,
    # embedders) is never touched, and loading is fail-soft + boundary-sanitized.
    app.state.session = state if state is not None else SessionState(ai_config=load_ai_config())
    app.state.auto_shutdown = auto_shutdown
    app.state.idle_grace = idle_grace
    app.state.ollama = ollama  # lazy-started on AI enable, stopped on close (None in tests)
    if ollama is not None:
        # ADR-0315: let routed Ollama backends mark REAL use (a successful generate) on the
        # manager, so shutdown can free GPU memory even when Settings was never opened. The
        # getattr guard keeps managers/fakes without record_use working unchanged.
        hook = getattr(ollama, "record_use", None)
        if callable(hook):
            app.state.session.ai_use_hook = hook
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
            response: Response
            # ADR-0264 SEC-3: a non-loopback Host is a DNS-rebinding read attempt — refuse
            # before ANY route logic runs (the rejection still carries the security headers).
            if not _host_allowed(request.headers.get("host", "")):
                response = JSONResponse({"error": "invalid host header"}, status_code=400)
            # ADR-0264 SEC-2 (corrected ADR-0268): a cross-site state-mutating request is the
            # CSRF signature — refuse it. Sec-Fetch-Site is the primary discriminator (Origin
            # is nulled by no-referrer on same-origin form navigations); Origin is the
            # fallback for pre-Fetch-Metadata clients.
            elif request.method in _UNSAFE_METHODS and not _csrf_safe(
                request.headers.get("sec-fetch-site"), request.headers.get("origin")
            ):
                response = JSONResponse({"error": "cross-site request refused"}, status_code=403)
            else:
                response = await call_next(request)
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
            # ADR-0334: a LAUNCHER probing the port is not the operator being present. Refreshing
            # the beat for /api/whoami would push a predecessor's shutdown clock forward by the
            # full idle_grace at the exact moment it is being replaced — so the one endpoint whose
            # caller is another process, not a browser, is exempt. Every other path still counts.
            if request.url.path != "/api/whoami":
                app.state.last_beat = time.monotonic()

    def session() -> SessionState:
        s: SessionState = app.state.session
        return s

    @app.post("/api/heartbeat")
    def heartbeat() -> JSONResponse:
        app.state.last_beat = time.monotonic()
        app.state.browser_seen = True
        return JSONResponse({"ok": True})

    @app.get("/api/whoami")
    def whoami() -> JSONResponse:
        """Identify this server process to a LAUNCHER probing the port (ADR-0334).

        Deliberately side-effect-free, which is the whole reason it is not ``/api/heartbeat``:
        a probe must not refresh ``last_beat`` or set ``browser_seen`` on the instance it is
        about to ask to stand down — doing so would extend the life of the very process being
        replaced, and could arm a watchdog that had never seen a browser at all.

        Carries no schedule content (Law 1) — just enough for the launcher to tell "an older
        copy of ME" from "some unrelated program squatting on 8321", which is the difference
        between a clean handover and failing visibly.
        """
        return JSONResponse(
            {
                "app": "schedule-forensics",
                "pid": os.getpid(),
                "version": _ASSET_VERSION,
                "launch_token": app.state.session.launch_token,
            },
            headers={"Cache-Control": "no-store"},
        )

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

    @app.get("/launch", response_class=HTMLResponse)
    def launch_view() -> HTMLResponse:
        """The Boot Screen (ADR-0426) — the startup lightshow the launcher opens on.

        Deliberately outside the story chrome: no nav, no chapter, no Continue footer. The CUI
        marking bars are kept (design system §6 admits no exception) and come from the SAME
        derivation ``_page`` uses, so this page can never show a different marking than the rest
        of the session. Reads only in-memory session facts — no CPM pass.
        """
        st = session()
        cui_class, cui_text = _cui_marking(st)
        return HTMLResponse(_launch_html(st, cui_class=cui_class, cui_text=cui_text))

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        st = session()
        flash = _flash_html(st.flash)
        st.flash = None  # one-shot: clear after rendering
        versions = st.all_versions()  # every loaded file (manifest), oldest first
        n_versions = len(versions)
        latest_name, latest_sch = versions[-1] if versions else ("", None)
        latest_file = (latest_sch.source_file or latest_name) if latest_sch is not None else ""
        latest_dd = (
            latest_sch.status_date.date().isoformat()
            if latest_sch is not None and latest_sch.status_date is not None
            else "—"
        )
        # Screen header (Mission Ops slice 1, prototype screen 'imp' / PROLOGUE · LOAD): kicker +
        # complete-sentence takeaway (the number lives IN the sentence) + muted lede. Presentation
        # only — every figure below is already computed by the session manifest.
        if n_versions:
            noun = "version" if n_versions == 1 else "versions"
            takeaway = (
                f"{n_versions} {noun} loaded from {_e(latest_file)} &mdash; every number in "
                "this report is computed, never typed."
            )
        else:
            # the assurance clause is conditioned on the OBSERVED AI locality (DoD 001b) —
            # it may not print while any constructible or routed AI candidate is non-local.
            takeaway = (
                "Load a schedule to begin &mdash; nothing you load ever leaves this machine."
                if not _observed_banner(st).cloud_active
                else "Load a schedule to begin."
            )
        screen_head = (
            "<div class=page-kicker data-no-i18n>PROLOGUE · LOAD</div>"
            f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
            '<p class="page-lede">Drop one project&rsquo;s versions &mdash; or several projects at '
            "once. Every file parses on this machine; nothing is uploaded, and the full forensic "
            "report is one click from every loaded version.</p>"
        )
        # OR-01 (ADR-0321): the manifest names, PER FILE, what each figure is — Site / Company,
        # data date, computed finish, effective margin, DCMA-14 — dates/margin via the same
        # cached engine summary tier the Portfolio ledger reads (st.summary_for, v4 Feature 2;
        # never a full analysis per row). The DCMA-14 cell counts the PARITY-AWARE card tier
        # (st.dashboard_core_for — the exact checks the health cards above it render), so one
        # page can never show two DCMA verdicts for one file; the summary tier is default-mode
        # only (ADR-0321 residual). An unsolvable file keeps "—" for engine figures, never a 0.
        row_parts: list[str] = []
        for name, sch in st.all_versions():  # every loaded file (manifest), oldest first
            s = st.summary_for(name, sch)
            site = _e(sch.company) if sch.company else "—"
            dd = _mdY(s.status_date_iso) if s.status_date_iso is not None else "—"
            fin = margin = dcma = "—"
            if not s.unsolvable:
                fin = _mdY(s.finish_iso)
                if s.effective_margin_days is not None:
                    margin = f"{s.effective_margin_days:g} d"
            try:
                core = st.dashboard_core_for(name, sch)
            except CPMError:
                core = None  # unsolvable: the DCMA cell stays "—"
            if core is not None:
                n_pass = sum(1 for _mid, _nm, status in core.dcma if status == "PASS")
                n_fail = sum(1 for _mid, _nm, status in core.dcma if status == "FAIL")
                dcma_cls = "rib-pass sf-pill p-ok" if n_fail == 0 else "rib-fail sf-pill p-bad"
                dcma = f'<span class="{dcma_cls}">{n_pass} pass / {n_fail} fail</span>'
            row_parts.append(
                f'<tr><td><a href="/analysis/{quote(name)}">{_e(name)}</a></td>'
                f"<td>{len(non_summary(sch))}</td><td class=muted>{_e(sch.source_file or '-')}</td>"
                f"<td>{site}</td><td>{dd}</td><td>{fin}</td><td>{margin}</td><td>{dcma}</td>"
                f'<td class=row-actions><a href="/analysis/{quote(name)}">Open report</a>'
                f' &middot; <a href="/card/{quote(name)}">Card</a>'
                f' &middot; <a href="/wbs/{quote(name)}">WBS</a>'
                f' &middot; <a href="/download/{quote(name)}.json">Save .json</a></td></tr>'
            )
        rows = "".join(row_parts)
        file_noun = "FILE" if n_versions == 1 else "FILES"
        prov_chip = (
            f"<span class=prov-chip data-no-i18n>SOURCE: {_e(latest_file)} · DD {latest_dd}</span>"
        )
        loaded = (
            "<div class=panel><h2>Schedule health</h2>"
            "<p class=muted>A health snapshot per loaded schedule &mdash; activity status mix, "
            "critical-path exposure, computed finish vs. baseline, and the DCMA-14 checks at a "
            "glance. Click any card to dive into its full report.</p>"
            "<div id=dashboardHealth class=dash-cards></div></div>"
            '<script src="/static/dashboard.js"></script>'
            # Panel shell (Mission Ops slice 1): headline strip + ⤓/⛶ tools + provenance chip.
            # ▦ DATA is deliberately omitted — the table below IS the data drawer. The ⤓ EXCEL
            # export reuses the existing quality-ribbon endpoint (one row per loaded file).
            '<div class=panel data-export="/export/xlsx/ribbon"><div class=panel-head>'
            f"<h2>LOADED VERSIONS &mdash; {n_versions} {file_noun}</h2>"
            "<div class=sf-tools data-noprint=1>"
            "<button type=button data-sf-excel "
            'title="Export the quality ribbon for every loaded file — opens in Excel" '
            'aria-label="Export the loaded versions to Excel">⤓ EXCEL</button>'
            "<button type=button data-sf-big aria-pressed=false "
            'aria-label="Enlarge this panel">⛶ ENLARGE</button>'
            f"</div>{prov_chip}</div>"
            "<table><tr><th scope=col>Schedule</th><th scope=col>Activities</th><th scope=col>Source</th>"
            "<th scope=col>Site / Company</th><th scope=col>Data date</th>"
            "<th scope=col>Computed finish</th><th scope=col>Effective margin</th>"
            "<th scope=col>DCMA-14</th><th scope=col></th></tr>"
            f"{rows}</table>"
            + (
                '<p style="margin-top:14px"><a class=btn-link href="/briefing">'
                "Executive briefing &rarr;</a>"
                + (
                    ' &middot; <a class=btn-link href="/trend">Trend across all versions &rarr;</a>'
                    ' &middot; <a class=btn-link href="/cei">Bow Wave / CEI &rarr;</a>'
                    ' &middot; <a class=btn-link href="/curves">Finish &amp; slippage curves &rarr;</a>'
                    ' &middot; <a class=btn-link href="/evolution">Critical-path evolution &rarr;</a>'
                    ' &middot; <a class=btn-link href="/compare">Compare two versions &rarr;</a>'
                    if len(st.schedules) >= 2
                    else ""
                )
                + "</p>"
            )
            + "</div>"
            if rows
            else ""
        )
        # The hero's absolute locality claims are conditioned on the SAME observed derivation
        # as the persistent banner (DoD 001b): with a non-local AI candidate constructible,
        # "entirely on your machine" / "nothing leaves this computer" may not print.
        if not _observed_banner(st).cloud_active:
            hero_h2 = "Forensic schedule analysis &mdash; entirely on your machine"
            hero_tail = "and a cited AI narrative &mdash; nothing leaves this computer."
        else:
            hero_h2 = "Forensic schedule analysis"
            hero_tail = (
                "and a cited AI narrative. Engine computations stay on this machine; the "
                "session&rsquo;s AI is configured for a non-local endpoint."
            )
        body = f"""
{flash}
{screen_head}
<section class=hero>
  <h2>{hero_h2}</h2>
  <p class=muted>Open or import a Microsoft&nbsp;Project / Primavera schedule to get a DCMA-14 audit,
  schedule-quality&nbsp;&amp;&nbsp;schedule-risk metrics, driving-path and manipulation-trend analysis,
  {hero_tail}</p>
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
    <div class=load-orbit aria-hidden=true>
      <div class=load-spinner aria-hidden=true></div>
      <span class="orbit-dot orbit-a"></span>
      <span class="orbit-dot orbit-b"></span>
      <span class="orbit-dot orbit-c"></span>
    </div>
    <p class=load-title>Loading your project(s)&hellip;</p>
    <p class=muted>Importing and analyzing &mdash; large files can take a moment. The tool is
      working, not stuck.</p>
    <div class=load-audio>
      <button type=button id=humMute aria-pressed=false aria-label="Mute the loading hum">&#9834; HUM</button>
      <input id=humVol type=range min=0 max=100 step=5 value=40 aria-label="Loading hum volume">
    </div>
  </div>
</div>
{loaded}
<script src="/static/launch_audio.js"></script>
<script src="/static/home.js"></script>
<script src="/static/panelkit.js"></script>"""
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
        with st._lock:  # ADR-0263 (D18): key + store atomically vs concurrent locked readers
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
        duplicate_notes: list[str] = []  # byte-identical uploads collapsed loudly (ADR-0259)
        ignored = 0  # non-schedule files inside a folder upload (skipped, not errored)
        upload_exts = {e.lower() for e in supported_extensions()}
        meta = _parse_upload_meta(file_meta)  # per-file (top-folder or None, mtime or None)
        # one heap-capped JVM for every native .mpp in this ingest (v4 Feature 2) instead of a fresh
        # java process per file — one boot for a whole folder, not thousands. Harmless for text
        # formats (they never touch the JVM) and for a cache-hit re-upload (it never parses).
        # ADR-0263 (D18): every READ or WRITE of the shared session dicts happens under st._lock
        # in short windows (the slow parse stays outside), so a concurrent locked render can never
        # see a dict mutate mid-iteration; the wipe generation captured here makes a mid-upload
        # wipe final — nothing parsed before it is stored (in memory or on disk) after it.
        # ADR-0281: a reverse index (content-hash, folder-context) → first-loaded key, built ONCE
        # here so the per-file dedup is an O(1) lookup instead of rescanning the whole
        # ``content_hashes`` map for every file (the recorded O(M^2) upload cost). ``setdefault``
        # keeps the FIRST-loaded key on a collision — byte-identical to the old first-match scan —
        # and the batch keeps this local index in lockstep as it accepts files (below).
        with st._lock:
            upload_gen = st.wipe_gen
            dup_index: dict[tuple[str, str | None], str] = {}
            for k, h in st.content_hashes.items():
                dup_index.setdefault((h, st.file_meta.get(k, (None, None))[0]), k)
        wiped_midway = False
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
                # ADR-0259 hash-first dedup: a byte-identical file in the SAME grouping context
                # (same top folder, or both loose) is the same version twice — load it once,
                # loudly (notice + log, nothing silent). Identical bytes in a DIFFERENT context
                # are kept: they can legitimately be a version of two different Projects.
                folder_ctx = meta[i][0] if i < len(meta) else None
                with st._lock:
                    if st.wipe_gen != upload_gen:
                        wiped_midway = True
                        break
                    dup_key = dup_index.get((chash, folder_ctx))  # O(1) — ADR-0281
                    kept = (
                        (st.schedules[dup_key].source_file or dup_key)
                        if dup_key is not None
                        else None
                    )
                if dup_key is not None:
                    duplicate_notes.append(
                        f"Skipped “{name}” — byte-identical to the already-loaded “{kept}” "
                        "(the same file twice; nothing was lost)."
                    )
                    logger.info("skipped byte-identical upload; kept key=%s", dup_key)
                    continue
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
                    with st._lock:
                        if st.wipe_gen == upload_gen:  # never re-populate a wiped disk cache
                            cache.put_schedule(chash, schedule)
                with st._lock:
                    if st.wipe_gen != upload_gen:
                        wiped_midway = True
                        break
                    key = _unique_key(_clean_key(name), st.schedules)
                    st.schedules[key] = schedule.model_copy(update={"source_file": name})
                    st.file_meta[key] = meta[i] if i < len(meta) else (None, None)
                    # lets the Portfolio read this version's on-disk summary
                    st.content_hashes[key] = chash
                    # ADR-0281: keep the local dedup index in lockstep so a later byte-identical
                    # file in the SAME batch + context still collapses (first-loaded key wins).
                    dup_index.setdefault((chash, folder_ctx), key)
                accepted.append(key)
        if wiped_midway:
            errors.append(
                "Session was wiped while this upload was in flight — the remaining files were "
                "not loaded. Re-upload them if that was not intended."
            )
        notices: list[str] = []
        if accepted:
            with st._lock:
                pops = st.populations()
            if len(pops) > 1:
                # ADR-0258: the newest-loaded population becomes ACTIVE (auto-select — never
                # block, nag, or ask); every analysis page now shows exactly one Project (or the
                # pooled untitled files), and the banner offers the switch.
                landed = next((pop for pop in pops if accepted[-1] in pop[2]), None)
                if landed is not None:
                    st.set_active_project(landed[0])
                    others = len(pops) - 1
                    notices.append(
                        f"Now analyzing “{landed[1]}” ({len(landed[2])} "
                        f"version{'s' if len(landed[2]) != 1 else ''}). "
                        f"{others} other Project{'s' if others != 1 else ''} loaded — switch "
                        "from the banner on any page, or in Portfolio."
                    )
            notices.extend(_grouping_notices(st.projects()))
        notices.extend(duplicate_notes)
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
            with st._lock:  # snapshot; never iterate the live dict unlocked (D18)
                est = estimate_resident_bytes(list(st.schedules.values()))
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
        # Audit ROLES-1 (ADR-0256): advisory NOTICES (project-title grouping, the mtime
        # version-order tiebreak, the RAM warning) render only on the dashboard flash, so they
        # gate the role landing too — a noticed ingest is not "clean" for redirect purposes.
        # The no-role paths below are untouched (pre-F4 byte-compatibility preserved).
        clean = bool(accepted) and not errors and not ignored and not client_skipped
        role_landing = (
            _ROLE_BY_ID[st.role].landing if st.role is not None and st.role in _ROLE_BY_ID else None
        )
        if clean and role_landing and not notices:
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
                # ANALYSIS-HEADER-MIXED-POPULATION: the panels below pair this schedule with
                # ``analysis.cpm``, so it must BE the population that CPM was solved on, or the
                # header counts the raw file while the grid counts the scoped one (measured: one
                # filtered page saying "9 activities" and "8 activities in the grid"). Identity
                # fields (name, source_file, calendar, project frame) are preserved by the
                # reduction, and this is ``sch`` itself whenever nothing narrows.
                analysis.scoped,
                analysis,
                st.target_uid,
                erosion_field=erosion_field,
                margin_confirmed=st.margin_overlay.get(name),
                dcma_acumen_parity=st.dcma_acumen_parity,
                versions=st.ordered_versions(),
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
        focus = (
            _target_panel(analysis.scoped, analysis, st.target_uid)
            if st.target_uid is not None
            else ""
        )
        # OR-01 (ADR-0321): the effective margin rides the same cached summary tier the
        # Portfolio row reads (overlay-aware, memoised) — never a second engine path.
        margin_days = st.summary_for(name, sch).effective_margin_days
        return _page(
            st,
            f"{name} — card",
            focus + _card_body(name, analysis.scoped, analysis, margin_days=margin_days),
            ask_schedule=name,
            # ADR-0311: a dynamic title can never resolve through _TITLE_TO_CHAPTER, so this page
            # rendered with NO kicker at all. It is a per-file drill of chapter 01 (linked beside
            # "Open report"), exactly as /wbs is one of chapter 07 — named explicitly, like /analysis.
            chapter=_CHAPTER_BY_NUM.get("01"),
            focus_file=name,
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
        body = focus + _wbs_body(name, groups, prov=_prov_chip(sch))
        # the include rides ONLY a render that carries a contract control (the r11 law), so
        # the gate reads the ASSEMBLED body, not one builder's branch: the no-groups branch
        # and the absent-UID focus notice are bare, while a POPULATED focus panel carries ⛶
        # since the codex-review round (_target_panel wears the contract now — the original
        # comment here claimed it already did, a misread corrected in the ADR-0327 addendum)
        if "data-sf-" in body:
            body += '\n<script src="/static/panelkit.js"></script>'
        return _page(
            st,
            f"{name} — WBS",
            body,
            ask_schedule=name,
            # ADR-0311: /wbs was ALREADY a declared beat of chapter 07 (("WBS", "@wbs")) yet its
            # dynamic title resolved to no chapter, so it rendered with no kicker. Named explicitly.
            chapter=_CHAPTER_BY_NUM.get("07"),
            focus_file=name,
        )

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
        # the payload carries BOTH a "tasks" count and the activity list; they are two views of
        # one population and shipped disagreeing under a filter (9 vs 8).
        return JSONResponse(_analysis_data(analysis.scoped, analysis))

    @app.get("/api/driving/{name}")
    def driving_json(
        name: str,
        # target 0 / absent = the COMPLETE schedule (operator 2026-08-20): /path opens on the
        # whole plan and a UID click retargets; a positive target traces exactly as before.
        target: int = Query(0),
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
            a = st.analysis_for(name, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        # pair the schedule with the SAME scope as its cpm: tracing the raw (unscoped) network
        # against a scoped cpm would mix a filtered/target-truncated timing set onto the full
        # task list. a.scoped IS the object the cpm was computed from (ADR-0263 — one source,
        # no second lock window a concurrent scope change could slip between).
        cpm = a.cpm
        scoped = a.scoped
        # target <= 0 → the whole-schedule default view; the trace builder stays untouched
        # (its payload is byte-pinned under the SSI option flags, ADR-0251).
        payload = (
            _whole_schedule_data(scoped, cpm)
            if target <= 0
            else _driving_data(
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
            _standards_body(st, key, analysis.scoped, prior, analysis),
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
        # ADR-0262: the cross-version tiles degrade to a "needs ≥2 versions" note below their
        # population threshold, so their scripts never fetch the ≥2-version APIs (no console
        # 4xx — the ADR-0258 known pre-existing defect). Counts are ACTIVE-population-scoped,
        # the same truth the tile APIs serve. The solve pass now runs even for one loaded
        # version (Mission Ops rank 2): the verdict band + KPI tiles read the EXISTING
        # Executive Briefing verbatim — the same memoised briefing /briefing renders
        # (st.briefing_for, ADR-0368), deterministic (Null backend), never re-computed here.
        ordered = st.ordered()
        n_loaded = len(ordered)
        schedules, cpms, _skipped = _solvable_versions()
        n_solvable = len(schedules) if n_loaded >= 2 else 0
        # operator 2026-08-20: files that grouped into OTHER Projects (per-update .xer exports
        # with per-copy names) are invisible to this wall — count them so the degrade note can
        # say where they went instead of "load another update" while updates sit loaded.
        active_pop = st.active_population()
        other_files = len(st.schedules) - len(active_pop[2]) if active_pop is not None else 0
        # PAIR versions for the briefing's critical-path section 3.1 (ADR-0371): entered/left
        # diffs the version pair, so the target never truncates it.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        briefing = (
            st.briefing_for(schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms)
            if schedules
            else None
        )
        return _page(
            st,
            "Mission Control",
            _export_bar("mission")
            + _sources_line(ordered)
            + _mission_body(
                st.target_uid,
                n_loaded=n_loaded,
                n_solvable=n_solvable,
                latest=ordered[-1] if ordered else None,
                briefing=briefing,
                other_files=other_files,
            ),
        )

    def _resolve_pair_indices(n: int, a: int, b: int) -> tuple[int, int]:
        """Resolve the operator's A/B pick over ``n`` data-date-ordered versions (operator
        2026-08-20 — "select any two schedules", the /integrity precedent verbatim).

        Defaults to the two most recent. Ordered prior → current chronologically regardless
        of pick order, and the two can never collapse to one file. The baseline guard also
        catches an OUT-OF-RANGE index (e.g. ``b==0`` makes ``cur-1 == -1``): a negative base
        would wrap to ``schedules[-1]``, the NEWEST file, and silently render a
        chronologically REVERSED diff (a Law-2 fidelity bug), so an in-range neighbour is
        re-picked whenever base is out of range or equal to cur."""
        cur = b if 0 <= b < n else n - 1
        base = a if 0 <= a < n else cur - 1
        if base == cur or not (0 <= base < n):
            base = cur - 1 if cur > 0 else cur + 1
        return (base, cur) if base < cur else (cur, base)

    @app.get("/compare", response_class=HTMLResponse)
    def compare(a: int = Query(-1), b: int = Query(-1)) -> HTMLResponse:
        """What changed between TWO versions — any two (operator 2026-08-20): ``a``/``b`` are
        baseline / comparison indices into the data-date-ordered analyzable list, defaulting
        to the two most recent (yesterday's behavior, byte-compatible: the bare URL emits the
        bare export target)."""
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Compare", "<div class=panel>Load at least two versions to compare.</div>"
            )
        # Forensic order is by data date (the Acumen/SSI ProjectTimeNow pattern), not load
        # order; unschedulable versions (e.g. a logic cycle) are skipped, never a 500.
        # PAIR versions (ADR-0371, the ADR-0370 exposure sweep): the whole page is a version-
        # PAIR diff (diff_versions header, manipulation signals, focus rows), so the Target UID
        # must never truncate the populations being diffed — the truncated pair fabricated
        # "removed" activities/links from cone membership and hid real edits outside the cone.
        schedules, cpms, skipped = _pair_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Compare",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to compare.</div>",
            )
        n = len(schedules)
        prior_idx, cur_idx = _resolve_pair_indices(n, a, b)
        prior, current = schedules[prior_idx], schedules[cur_idx]
        default_pair = (prior_idx, cur_idx) == (n - 2, n - 1)
        # the ADR-0320 emit-only-non-default rule: a bare /compare keeps its exact byte shape
        # (export target, chip ordinals) so every existing pin and remembered URL still holds.
        export_qs = "" if default_pair else f"?a={prior_idx}&amp;b={cur_idx}"
        picker = ""
        if n > 2:
            labels = [sch.source_file or sch.name for sch in schedules]
            opts_a = "".join(
                f'<option value="{i}"{" selected" if i == prior_idx else ""}>{_e(lb)}</option>'
                for i, lb in enumerate(labels)
            )
            opts_b = "".join(
                f'<option value="{i}"{" selected" if i == cur_idx else ""}>{_e(lb)}</option>'
                for i, lb in enumerate(labels)
            )
            picker = (
                "<form method=get action=/compare class=viz-controls>"
                f"<label>Baseline (A) <select name=a>{opts_a}</select></label>"
                f"<label>Comparison (B) <select name=b>{opts_b}</select></label>"
                "<button type=submit>Apply</button>"
                "<span class=muted>Pick any two versions — the whole page compares that "
                "pair (chronological order is kept automatically).</span></form>"
            )
        body = (
            _what_changed_header(prior, current, cpms[prior_idx], cpms[cur_idx])
            + picker
            + _export_bar("compare" + export_qs.replace("&amp;", "&"))
            + _skipped_notice(skipped)
            + _sources_line([prior, current])
            + _compare_body(
                prior,
                current,
                cpms[prior_idx],
                cpms[cur_idx],
                # the pair chip's v-ordinals: position in the data-date-ordered solvable list
                vfrom=prior_idx + 1,
                vto=cur_idx + 1,
                export_qs=export_qs,
            )
        )
        if st.target_uid is not None:
            body += _focus_panel([prior, current], [cpms[prior_idx], cpms[cur_idx]], st.target_uid)
        # the panel-contract toolbar behavior (⛶ / ⤓) — a PER-PAGE include (rank-5 law:
        # markup alone is not evidence; the script must actually load on /compare)
        body += '\n<script src="/static/panelkit.js"></script>'
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
                # ADR-0261 P2: only the solve — never the full monolithic analysis — is needed
                # for the multi-version population pass; a resident full analysis is reused.
                # ADR-0263: the (scoped, cpm) pair comes from ONE call so a concurrent scope
                # change can never pair an old-epoch solve with a new-epoch population.
                scoped, cpm = st.cpm_scoped_for(key, sch)
                cpms.append(cpm)
                schedules.append(scoped)
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
                schedules.append(a.scoped)  # the exact schedule a.cpm was computed from (ADR-0263)
                cpms.append(a.cpm)
                analyses.append(a)
            except CPMError:
                skipped.append(key)
        return schedules, cpms, analyses, skipped

    def _pair_versions() -> tuple[list[Schedule], list[CPMResult], list[str]]:
        """``_solvable_versions`` for version-PAIR forensics (operator 2026-08-08): the active
        filter applies, but the session Target UID does NOT truncate the population — it is the
        counterfactual's MEASUREMENT ANCHOR, not a population cut. Diffing the target-truncated
        pair fabricated changes (cone membership read as file changes) and measured false
        "no effect" reverts (a restored link whose predecessor left the current cone dangles
        into a missing task, so CPM drops it) — see ``SessionState.scope_pair``. Versions whose
        full network cannot solve are skipped and named, exactly as ``_solvable_versions``."""
        st = session()
        schedules: list[Schedule] = []
        cpms: list[CPMResult] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                scoped, cpm = st.cpm_pair_for(key, sch)
                cpms.append(cpm)
                schedules.append(scoped)
            except CPMError:
                skipped.append(key)
        return schedules, cpms, skipped

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
        return _page(
            st, "Path Analysis", _TS_CAPTION_MARK + header + _path_body(keys, st.target_uid)
        )

    _UNRESTRICTED_MAX_ROWS = 400

    def _unrestricted_data_block(st: SessionState, name: str, sch: Schedule) -> str | None:
        """The bounded per-activity data table the UNRESTRICTED mode feeds the model
        (ADR-0361) — the raw material for "calculate new data". Engine-computed rows, one
        line per activity, truncation disclosed IN the block so the model can say so."""
        try:
            rows = st.analysis_for(name, sch).activity_rows
        except CPMError:
            return None
        head = (
            "UID|Name|WBS|Dur(d)|Rem(d)|%Complete|Start|Finish|TotalFloat(d)|Critical|"
            "Constraint|Resources"
        )
        lines = [head]
        for r in rows[:_UNRESTRICTED_MAX_ROWS]:
            if r.get("is_summary"):
                continue
            lines.append(
                "|".join(
                    str(v if v is not None else "—")
                    for v in (
                        r.get("unique_id"),
                        r.get("name"),
                        r.get("wbs"),
                        r.get("duration_days"),
                        r.get("remaining_duration_days"),
                        r.get("percent_complete"),
                        r.get("start"),
                        r.get("finish"),
                        r.get("total_float_days"),
                        r.get("is_critical"),
                        r.get("constraint_type"),
                        r.get("resource_names"),
                    )
                )
            )
        if len(rows) > _UNRESTRICTED_MAX_ROWS:
            lines.append(
                f"(first {_UNRESTRICTED_MAX_ROWS} of {len(rows)} activities by schedule "
                "order — say so if the question needs the rest)"
            )
        return "\n".join(lines)

    def _record_ask(
        st: SessionState,
        *,
        question: str,
        scope: str,
        facts: Sequence[CitedStatement],
        mode: str = "",
        model: str = "",
        answer: str | None = None,
        second_model: str | None = None,
        second_answer: str | None = None,
        agreement: str | None = None,
        kind: str = "AI answer",
    ) -> None:
        """Hold this exchange on the session so ``/export/{fmt}/ask`` can render it (ADR-0392).

        The answer arrives on a POST that streams straight into the panel, so nothing survived the
        response for a GET export route to read. Stores exactly what the analyst was shown."""
        st.last_ask = _AskRecord(
            question=question,
            scope=scope,
            mode=mode,
            model=model,
            answer=answer,
            facts=tuple(
                _AskFact(
                    f.text,
                    tuple((c.source_file, c.unique_id, c.task_name) for c in f.citations),
                )
                for f in facts
            ),
            second_model=second_model or "",
            second_answer=second_answer,
            agreement=agreement or "",
            kind=kind,
        )

    def _ask_response(
        st: SessionState,
        facts: tuple[CitedStatement, ...],
        text: str,
        data_block: str | None = None,
        scope: str = "",
    ) -> JSONResponse:
        """Shared Q&A response: route the backend(s), answer in the configured mode.

        With a cross-check second model configured and reachable, BOTH models answer
        independently and a deterministic figure-agreement note is computed — the
        engine compares, never a third model."""
        mode = st.ai_config.qa_mode
        backend = _active_backend(st)
        answer, used = answer_question(backend, facts, text, mode=mode, data_block=data_block)
        second_answer: str | None = None
        second_model: str | None = None
        agreement: str | None = None
        second = _second_backend(st)
        if second is not None:
            second_answer, _ = answer_question(
                second, facts, text, mode=mode, data_block=data_block
            )
            second_model = f"{second.name}/{getattr(second, 'model', '') or 'default'}"
            if answer and second_answer:
                agreement = figure_agreement(answer, second_answer)
        _record_ask(
            st,
            question=text,
            scope=scope,
            facts=used,
            mode=mode,
            model=(
                f"{backend.name}/{getattr(backend, 'model', '') or 'default'}"
                if answer is not None
                else ""
            ),
            answer=answer,
            second_model=second_model,
            second_answer=second_answer,
            agreement=agreement,
        )
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
        # the fact sheet is what the AI is allowed to cite, so it must describe the same
        # population every page shows (mixed-population class, audit 2026-08-16).
        pop = analysis.scoped
        return build_fact_sheet(
            pop,
            analysis.cpm,
            analysis.audit,
            analysis.findings,
            analysis.float_bands,
            analysis.completion,
            compute_finish_forecasts(pop, analysis.cpm),
        )

    @app.post("/api/ask/{name}")
    def ask(name: str, question: str = Form("")) -> JSONResponse:
        """Grounded Q&A on ONE schedule: engine facts; the configured mode governs prose."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        # ADR-0392: NO length cap. The former ``[:500]`` truncated a long forensic question
        # mid-sentence, silently — the model then answered the fragment and the analyst had no
        # way to see that half the question never arrived. Silent truncation is the defect class
        # this whole ADR closes; a local, loopback-only tool has no reason to cap its operator.
        text = question.strip()
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        try:
            analysis = st.analysis_for(name, sch)
            facts = _schedule_facts(st, name, sch)
            # ADR-0263: the driving-path engine call must receive the population its CPM was
            # solved FROM. Pairing the raw schedule with the scoped ``analysis.cpm`` made
            # ``compute_driving_slack`` raise KeyError on a filtered-out task, which
            # ``driving_path_summary`` swallows — so every engine driving-path fact vanished
            # silently under a filter and the model was left to traverse the network itself.
            facts += driving_path_facts(analysis.scoped, analysis.cpm, text)
            # PAIR versions (operator 2026-08-08): the manipulation facts diff a version pair,
            # so the target must anchor the measurement, never truncate the populations.
            pair_schedules, pair_cpms, _pskipped = _pair_versions()
            if len(pair_schedules) >= 2:
                # ADR-0424: scoping the Ask panel to ONE file does not make the other versions
                # stop existing — a question asked here still gets the whole consecutive-pair
                # comparison series, so "is this a pattern?" is answerable from every page.
                facts += pairwise_comparison_facts(pair_schedules, pair_cpms)
                facts += manipulation_forensics_facts(
                    pair_schedules, pair_cpms, target_uid=st.target_uid
                )
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        block = (
            _unrestricted_data_block(st, name, sch)
            if st.ai_config.qa_mode == "unrestricted"
            else None
        )
        return _ask_response(st, facts, text, data_block=block, scope=name)

    @app.post("/api/ask")
    def ask_workbook(question: str = Form("")) -> JSONResponse:
        """Grounded Q&A across EVERY loaded version (the multi-version pages' panel)."""
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "not found"}, status_code=404)
        text = question.strip()  # ADR-0392: no length cap — see /api/ask/{name}
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        unrestricted = st.ai_config.qa_mode == "unrestricted"
        if len(st.schedules) == 1:
            key, sch = next(iter(st.schedules.items()))
            try:
                analysis = st.analysis_for(key, sch)
                facts = _schedule_facts(st, key, sch)
                # ADR-0263: the driving-path engine call must receive the population its CPM was
                # solved FROM. Pairing the raw schedule with the scoped ``analysis.cpm`` made
                # ``compute_driving_slack`` raise KeyError on a filtered-out task, which
                # ``driving_path_summary`` swallows — so every engine driving-path fact vanished
                # silently under a filter and the model was left to traverse the network itself.
                facts += driving_path_facts(analysis.scoped, analysis.cpm, text)
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            block = _unrestricted_data_block(st, key, sch) if unrestricted else None
            return _ask_response(st, facts, text, data_block=block, scope=key)
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "no analyzable versions loaded"}, status_code=422)
        # PAIR versions (operator 2026-08-08 / ADR-0371) are resolved FIRST: the consecutive-pair
        # comparison series inside the fact sheet runs the manipulation DIFF detector, which must
        # never see a target-truncated population (ADR-0424 — it invents deleted tasks out of cone
        # membership). The S-curve/finish series still read the scoped population.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        # driving-path questions resolve against the newest analyzable version
        facts = build_workbook_fact_sheet(
            schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms
        )
        facts += driving_path_facts(schedules[-1], cpms[-1], text)
        # cross-version manipulation forensics (ADR-0150): duration cuts on the driving/
        # critical path, the reverted-changes counterfactual, the focus's baseline variance —
        # so "what was shortened to keep UID X from slipping?" is answerable with citations.
        # PAIR versions (operator 2026-08-08): the facts diff a version pair, so the target
        # must anchor the measurement, never truncate the populations being diffed.
        if len(pair_schedules) >= 2:
            facts += manipulation_forensics_facts(
                pair_schedules, pair_cpms, target_uid=st.target_uid
            )
        # unrestricted mode (ADR-0361) feeds the newest version's activity table as raw data
        block = None
        if unrestricted:
            # Resolve the newest ANALYZABLE version by KEY, never by name. Successive updates of
            # one project share a ``Schedule.name`` — that is what makes them versions of it — so
            # a name match returned the FIRST (oldest) file while the facts above come from the
            # newest. Unrestricted mode is deliberately ungated (ADR-0361), so nothing downstream
            # could catch a figure the model computed off that stale table.
            for version_key, version_sch in reversed(st.ordered_versions()):
                block = _unrestricted_data_block(st, version_key, version_sch)
                if block is not None:
                    break
        return _ask_response(st, facts, text, data_block=block)

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
                a = st.analysis_for(key, raw)
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            cpm = a.cpm
            sch = a.scoped  # the exact schedule the cpm was computed from (ADR-0263)
        else:
            schedules, cpms, _skipped = _solvable_versions()
            if not schedules:
                return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=422)
            sch, cpm = schedules[-1], cpms[-1]
        facts = driving_path_summary(sch, cpm, uid)
        question = f"Driving path to UID {uid}"
        if not facts:
            missing = f"UID {uid} is not a scheduled activity in this file."
            _record_ask(
                st,
                question=question,
                scope=key,
                facts=(),
                answer=missing,
                kind="Driving path (engine, no AI)",
            )
            return JSONResponse({"uid": uid, "answer": missing, "facts": []})
        answer = " ".join(f.text for f in facts)
        # the panel's other result kind is exportable too — one output box, one export button
        _record_ask(
            st,
            question=question,
            scope=key,
            facts=facts,
            answer=answer,
            kind="Driving path (engine, no AI)",
        )
        return JSONResponse(
            {
                "uid": uid,
                "answer": answer,
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
        # PAIR versions for the pairwise manipulation-signal roll-up ONLY (ADR-0371): the
        # series/header stay on the focused scope (the page's ?target= feature), but the
        # signals diff version pairs — on the truncated pair they fabricated deleted-task
        # findings from cone membership and missed real cuts outside the cone.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        return _page(
            st,
            "Trend",
            _how_it_moved_header(schedules, cpms)
            + _export_bar("trend")
            + _skipped_notice(skipped)
            + _sources_line(schedules)
            + _trend_body(schedules, cpms, uid, pair_schedules=pair_schedules, pair_cpms=pair_cpms),
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
            rows.append((raw.source_file or raw.name, status, a.scoped, a.cpm))
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
                # ADR-0263: the confirmed set feeds the summary tier's margin now, and the
                # UNION fallback means a confirm on ONE version can change every version's
                # summary — drop the in-memory tier so the Portfolio recomputes against the
                # new set (the disk blobs stay valid: they hold only the name-based default,
                # which overlaid sessions no longer consult).
                st.summaries.clear()
                # ADR-0321: the manifest-projection memo (ADR-0291) now bakes the summary
                # tier's margin_days into every /api/dashboard card, and its epoch key does
                # NOT cover the margin overlay — drop it with the summaries, or the cards
                # keep serving the pre-confirm margin the engine no longer computes.
                st.dash_cards.clear()
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
        st: SessionState,
        iterations: int = 1000,
        distribution: str = "triangular",
        zero_margin: bool = False,
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
            correlation_matrix=_correlation_spec(st),
            sampling=st.sra_sampling,
            lhs_centered=st.sra_lhs_centered,
        )
        three_point = _ssi_three_point(st, sch)
        if zero_margin:
            # ADR-0266 (Fig 7-43 "Current Plan, Zero Margin, With Risks"): every margin
            # activity is carried at ZERO duration in every iteration — via the existing
            # three-point surface, exactly as ADR-0254 queued. The [E, D] read window below
            # is untouched; only the CURVE's basis moves, and the payload labels which one.
            three_point = {**three_point, **dict.fromkeys(margin_uids, (0, 0, 0))}
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            result = run_maybe_offloaded(
                heavy,
                compute_sra_ssi,
                sch,
                config=cfg,
                three_point=three_point,
                risks=_schedule_risks(st),
                branches=_schedule_branches(st),
                conditionals=_schedule_conditionals(st),
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
        # Audit F1 (ADR-0256): convert offsets on the SAME realigned date axis the SSI result
        # itself uses — on a progressed schedule the naive conversion packs completed work at the
        # project start and would print D/E/percentile dates months before the stored plan dates
        # (while /sra shows the same seeded run realigned). The correction is the engine's own
        # constant stored-finish shift; _iso(D) == result.deterministic_finish_date is pinned.
        correction = stored_finish_correction(sch, cfg.target_uid, d_anchor)

        def _iso(offset: int) -> str:
            return (
                (offset_to_datetime(sch.project_start, max(offset, 0), cal) + correction)
                .date()
                .isoformat()
            )

        return {
            "file": key,
            "focus_uid": cfg.target_uid,
            "iterations": cfg.iterations,
            "seed": result.seed,
            "distribution": cfg.distribution,
            "occurrence_mode": cfg.occurrence_mode,
            "use_risk_register": cfg.use_risk_register,
            "correlation": cfg.correlation,
            "sampling": result.sampling,
            "lhs_centered": cfg.lhs_centered,
            "margin_task_count": len(margin_uids),
            "zero_margin": zero_margin,
            "curve_basis": (
                'zero-margin (Fig 7-43 "Current Plan, Zero Margin, With Risks")'
                if zero_margin
                else "in-network margin at plan durations"
            ),
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
        iterations: int = Query(1000),
        distribution: str = Query("triangular"),
        zero_margin: int = Query(0),
    ) -> JSONResponse:
        """Button-triggered risk-based margin sufficiency (never on page load — SRA doctrine).
        ``zero_margin=1`` (ADR-0266) runs the handbook-faithful Fig 7-43 curve: the margin
        activities at zero duration, read against the SAME deterministic [E, D] window."""
        data = _margin_risk_data(session(), iterations, distribution, bool(zero_margin))
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
        return _page(st, "EVM", _how_we_execute_evm_header(st) + bar + _evm_body(st) + panel)

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
    def cei_view(uids: str = Query("")) -> HTMLResponse:
        st = session()
        # ADR-0268: focusing a target is a STATE change, so it goes through POST /target now
        # (the Focus form), not a GET side effect — a GET must never mutate the session (the
        # ADR-0061 query-set was the recorded residual). ``uids`` stays a GET param: it is a
        # display-only track set, it changes no session state.
        # ADR-0262: the guard counts the ACTIVE population (ADR-0258 — never another Project's
        # files), matching the population compute_bow_wave below actually receives.
        if len(st.ordered()) < 2:
            return _page(
                st,
                "Bow Wave / CEI",
                "<div class=panel>Load at least two versions (monthly snapshots) to run the "
                "bow-wave / CEI analysis.</div>",
            )
        track = _parse_track_uids(uids)
        versions = st.ordered()  # read the population ONCE — the wave, the sources line and
        # the provenance chip must all describe the SAME list
        try:
            wave = compute_bow_wave(versions, st.target_uid, track_uids=track)
        except ValueError as exc:
            return _page(st, "Bow Wave / CEI", f"<div class=panel>{_e(exc)}</div>")
        return _page(
            st,
            "Bow Wave / CEI",
            _work_piling_header(wave)
            + _export_bar("cei")
            + _sources_line(versions)
            + _cei_body(wave, st.target_uid, track_uids=track, prov=_series_prov_chip(versions)),
        )

    @app.get("/api/cei")
    def cei_json(uids: str = Query("")) -> JSONResponse:
        st = session()
        # ADR-0262: population-scoped guard — the wave itself is built from st.ordered()
        if len(st.ordered()) < 2:
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
        versions = st.ordered()
        return _page(
            st,
            "S-Curve",
            _scurve_header(sc)
            + _export_bar("scurve" + (f"?uids={uids}" if uids else ""))
            + _scurve_body(
                sc,
                _scurve_filter_fields(versions),
                track_uids=track,
                prov=_series_prov_chip(versions),
            ),
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
            # RIBBON-MIXED-POPULATION: score the population the CPM was actually solved on.
            # ``ordered_versions()`` is documented UNSCOPED, so pairing its schedule with
            # ``analysis.cpm`` scored the raw file against a CPM from a different task set —
            # the ribbon's figures did not move AT ALL under a reduce filter. Identical to
            # ``sch`` whenever nothing narrows (``scope()`` is then the identity).
            pop = analysis.scoped
            rows.append(
                (
                    key,
                    compute_ribbon(pop, analysis.cpm, analysis.audit),
                    compute_schedule_quality(pop, analysis.cpm),
                )
            )
            drill[key] = ribbon_offender_map(pop, analysis.cpm, analysis.audit)
        note = _skipped_notice(skipped) if skipped else ""
        header = ""
        prov = ""
        if rows:  # the latest schedulable version anchors "Can we trust the plan?" (ADR-0198)
            lkey, lribbon, _lq = rows[-1]
            # the matrix panel's provenance chip quotes the SAME latest version the header
            # anchors on (Mission Ops rank 8) — presentation only, the _prov_chip vocabulary
            prov = _prov_chip(st.schedules[lkey])
            if isinstance(lribbon, RibbonMetrics):
                latest = st.analysis_for(lkey, st.schedules[lkey])
                header = _can_we_trust_header(latest.scoped, latest, lribbon)
        return _page(
            st,
            "Schedule Quality Ribbon",
            header + _export_bar("ribbon") + _ribbon_body(rows, note, drill, prov=prov),
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
                        # Gate on STATUS, not on `value is not None`: `_na_index` builds a
                        # NOT_APPLICABLE result with value=0.0 (never None), so a value-only
                        # guard never fires and a cost-free file exported CPI/SPI/TCPI as
                        # 0.00 — read as catastrophic performance while the page said NA
                        # (MF-02, ADR-0411). The workbook must not contradict the screen.
                        _export_cell(indices.get(k))
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
            solv.append((key, a.scoped, a))
        if not solv:
            return JSONResponse({"error": "load an analyzable schedule first"}, status_code=422)
        _key, current, cur_an = solv[-1]
        prior = solv[-2][1] if len(solv) >= 2 else None
        prior_cpm = solv[-2][2].cpm if len(solv) >= 2 else None
        findings = recommend(
            current,
            prior,
            current_cpm=cur_an.cpm,
            prior_cpm=prior_cpm,
            target_uid=st.target_uid,
            acumen_parity=st.dcma_acumen_parity,  # ADR-0282 Option A: findings follow the parity audit
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
            # ADR-0268: mirror the on-screen wall's ADR-0262 degrade — the wall's underlying
            # series are cross-version (trend + critical-path evolution), so a one-version
            # population has nothing to plot. Return a VALID workbook with a one-row note (the
            # operator gets a real file explaining why), never a raw 422 the browser downloads
            # as a broken document.
            note = TableSet(
                "Mission Control — underlying series",
                (
                    Table(
                        "Needs at least two analyzable versions",
                        ("Status",),
                        (
                            (
                                "The Mission wall's underlying series (quality trend + "
                                "critical-path evolution) are cross-version — load another "
                                "analyzable version of the active project to populate them.",
                            ),
                        ),
                    ),
                ),
            )
            return _export_response(fmt, note, "mission")
        tables: list[Table] = list(trend_tables(compute_quality_trend(schedules, cpms)))
        # PAIR versions for the evolution tables ONLY (ADR-0371): entered/left diffs version
        # pairs, so the target never truncates; the quality trend stays on the focused scope
        # (per-version series — the same basis as /export/{fmt}/trend).
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        if len(pair_schedules) >= 2:
            tables.extend(path_evolution_tables(compute_path_evolution(pair_schedules, pair_cpms)))
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
            + _performance_body(st, schedules, cpms, file),
        )

    @app.get("/export/{fmt}/performance")
    def export_performance(fmt: str, file: str = Query("")) -> Response:
        """Every Performance-Summary dataset (census / flow / burden / DRM / quads) as a file."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "load a schedule first"}, status_code=422)
        data = _performance_data(session(), schedules, cpms, file)
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
        # PAIR versions (ADR-0371): every panel here diffs a version pair — path_evolution's
        # entered/left + per-step signals, the counterfactual, the what-if tables. The focus
        # semantics are delivered by the target_uid ANCHOR (the 0-driving-slack chain to the
        # target), never by truncating the populations being diffed.
        schedules, cpms, skipped = _pair_versions()
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
        # ADR-0320: the ⤓ links carry the LIVE page state (focus / tier / trace options), so
        # the export route can honor the options banner's "including the Excel exports" line
        # for THIS render; a stateless render keeps the bare path byte-identical.
        export_qs = _evolution_state_qs(
            target=target,
            tier=tier,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
        # ALL solvable versions for the stability band -- a separate population from the PAIR
        # above, deliberately (ADR-0371 pairs; ADR-0427's band spans the history).
        all_schedules, all_cpms, _all_skipped = _solvable_versions()
        header = _how_stable_header(compute_path_evolution(schedules, cpms, target_uid=uid))
        return _page(
            st,
            "Critical-Path Evolution",
            _TS_CAPTION_MARK
            + header
            + _export_bar("evolution" + (f"?{export_qs}" if export_qs else ""))
            + _skipped_notice(skipped)
            + opt_banner
            + opt_form
            + _sources_line(schedules)
            # ADR-0427: the prototype's Chapter-04 stability band (panels 1-4) sits ABOVE the
            # pair-scoped panels. It is drawn from ALL solvable versions, not the pair, because
            # "how stable is the path" is a question about the whole loaded history -- and every
            # one of its takeaways says so, per ADR-0420's mixed-population rule.
            + (_stability_panels(all_schedules, all_cpms) if len(all_schedules) >= 2 else "")
            + _evolution_body(
                schedules,
                cpms,
                uid,
                tier,
                cf_a=cf_a,
                cf_b=cf_b,
                ignore_constraints=bool(ignore_constraints),
                ignore_leveling=bool(ignore_leveling),
            ),
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
        # PAIR versions (operator 2026-08-08): the diff/findings/counterfactuals must see the
        # two versions' REAL networks — the session Target UID anchors the measurement inside
        # _integrity_body, it must never truncate the populations being diffed (_pair_versions).
        schedules, cpms, skipped = _pair_versions()
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
    def evolution_json(
        target: str | None = Query(None),
        tier: str = Query("off"),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
    ) -> JSONResponse:
        """The stepper's feed. ADR-0265 (closing the ADR-0251 disclosure): it accepts the SAME
        counterfactual trace options as the /evolution page, so the client-fetched chart and
        the server-rendered panels share ONE basis. Defaults reproduce the stored-schedule
        payload byte-for-byte (the /mission wall passes no options). PAIR versions (ADR-0371):
        the stepper diffs version pairs, so the target anchors and never truncates."""
        st = session()
        schedules, cpms, _skipped = _pair_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        schedules, cpms, _banner = _optioned_versions(
            schedules,
            cpms,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
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
            _TS_CAPTION_MARK
            + _skipped_notice(skipped)
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
                        # RAW answers — coercion happens per schedule at selection (ADR-0354)
                        st.set_saved_filter(saved, raw_answers)
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
            _curves_header(curves)
            + _export_bar("curves")
            + _sources_line(versions)
            + _curves_body(curves, prov=_series_prov_chip(versions)),
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

    @app.get("/export/{fmt}/ask")
    def export_ask(fmt: str) -> Response:
        """The latest Ask-the-AI exchange as a workbook (ADR-0392).

        Three sheets, and the split is the point: **Answer** is what the model wrote, **Cited
        facts** is what the engine computed and handed it, and **Citations** resolves every fact
        to file + UniqueID + activity name so a reader can verify each one in MS Project. An AI
        answer that leaves this tool must travel with its evidence, or it is an assertion.
        """
        if (bad := _bad_format(fmt)) is not None:
            return bad
        rec = session().last_ask
        if rec is None:
            return JSONResponse(
                {"error": "ask a question first — there is no answer to export"}, status_code=422
            )
        answer_rows: list[tuple[Cell, ...]] = [
            ("Result type", rec.kind),
            ("Question", rec.question),
            ("Scope", rec.scope or "Workbook — all loaded versions"),
            ("AI answer mode", rec.mode or "n/a (engine result, no AI)"),
            ("Model", rec.model or "none — no live model answered"),
            # Law 2 at the export boundary: no answer is an EMPTY cell with a stated reason,
            # never a blank that reads as "the model said nothing of note".
            (
                "Answer",
                rec.answer
                or "— no model answer (no live model active, or the figure gate discarded it); "
                "the cited facts sheet is the engine's own answer",
            ),
        ]
        if rec.second_answer:
            answer_rows.append(("Second model", rec.second_model or "second"))
            answer_rows.append(("Second answer", rec.second_answer))
        if rec.agreement:
            answer_rows.append(("Cross-check", rec.agreement))
        answer_rows.append(
            (
                "Standing disclaimer",
                "AI can err — verify every figure against the cited facts and the source "
                "schedule. Figures in the cited facts are engine-computed.",
            )
        )
        fact_rows = tuple(
            (
                i,
                f.text,
                "; ".join(f"{name} (UID {uid})" for _file, uid, name in f.citations) or "—",
            )
            for i, f in enumerate(rec.facts, start=1)
        )
        citation_rows = tuple(
            (i, file or "—", uid, name)
            for i, f in enumerate(rec.facts, start=1)
            for file, uid, name in f.citations
        )
        tableset = TableSet(
            "POLARIS — Ask the AI",
            (
                Table("Answer", ("Field", "Value"), tuple(answer_rows)),
                Table("Cited facts", ("#", "Engine-computed fact", "Cited activities"), fact_rows),
                Table("Citations", ("Fact #", "File", "UniqueID", "Activity"), citation_rows),
            ),
        )
        return _export_response(fmt, tableset, "ask-the-ai")

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
        # ANALYSIS-EXPORT-QUALITY-UNSCOPED: a workbook leaves the tool and gets quoted, so it
        # must state the population the screen does — not the raw file scored against a CPM
        # solved on the scoped one (measured: 2 of 9 exported where the page showed 5 of 8).
        pop = analysis.scoped
        quality = compute_schedule_quality(pop, analysis.cpm)
        tableset = TableSet(
            f"POLARIS - {sch.name}",
            (
                schedule_summary_table(pop),
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
        basis: str = Query("stored"),
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
        # ADR-0265: ``basis=resolve`` (the /driving-path page's link) runs this export on the
        # page's COUNTERFACTUAL re-solved network — the same _optioned_versions transform the
        # tiers panel shows — so the downloaded trace mirrors the screen. The trace's own
        # family-A flags are then OFF (the transform already embodies them at the network
        # level). Default ``stored`` keeps the SSI-parity stored-date trace byte-identical.
        counterfactual = basis == "resolve" and bool(ignore_constraints or ignore_leveling)
        if counterfactual:
            opt_s, opt_c, _b = _optioned_versions(
                [sch],
                [cpm],
                ignore_constraints=bool(ignore_constraints),
                ignore_leveling=bool(ignore_leveling),
            )
            sch, cpm = opt_s[0], opt_c[0]
        data = _driving_data(
            sch,
            cpm,
            target,
            secondary,
            tertiary,
            direction=direction,
            range_mode=range_mode,
            range_days=range_days,
            ignore_constraints=bool(ignore_constraints) and not counterfactual,
            ignore_leveling=bool(ignore_leveling) and not counterfactual,
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
        title = f"Path analysis - {sch.name}" + (
            " (counterfactual re-solve basis - ADR-0265)" if counterfactual else ""
        )
        tableset = TableSet(
            title,
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
            r = compute_ribbon(analysis.scoped, analysis.cpm, analysis.audit)
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
        offenders = ribbon_offender_map(analysis.scoped, analysis.cpm, analysis.audit)
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
            out.append((key, a.scoped, a.cpm, a))
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
        # the chip's population must be the ribbon's population: the SOLVABLE subset
        # /api/workbench serves (codex-review round, ADR-0327 addendum) — the raw loaded
        # list can include an unschedulable version the ribbon never draws
        return _page(
            st,
            "Metric Workbench",
            _workbench_body([s for _k, s, _c, _a in _workbench_versions()]),
        )

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
        sch = a.scoped
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
    def export_margin(fmt: str, zero_margin: int = Query(0)) -> Response:
        """The margin/contingency burn-down + the erosion summary as one Excel/Word workbook.
        ADR-0268: ``zero_margin=1`` runs the §7.3.3.2.3 sufficiency read on the Fig 7-43
        zero-margin curve (ADR-0266) so an operator can export the same snapshot the panel
        toggle shows; the "Curve basis" row names which curve produced the figures."""
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
        risk = _margin_risk_data(st, zero_margin=bool(zero_margin))
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
                ("Curve basis", str(risk["curve_basis"])),
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
        sch = a.scoped
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
            out.append((key, a.scoped, a))
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

    def _pick_drill_version(file: str) -> tuple[str, Schedule, _Analysis] | None:
        """The version behind a drill trigger — resolved across EVERY loaded file, never
        substituted (ADR-0295).

        A drill trigger carries the exact key (or label) of the version whose numbers it was
        rendered from. The dashboard is the session MANIFEST (ADR-0258): its cards cover every
        Project, so a card from a non-active Project must resolve against ITS file — the old
        resolver searched only the active population and silently fell back to ``versions[-1]``,
        listing a DIFFERENT schedule's activities under the clicked card's label. A named version
        that cannot be resolved is therefore an error (``None``), never a substitution. Only an
        UNNAMED request (``file=""``) keeps the historical "latest solvable of the active
        population" meaning — that is how the UID-only triggers (e.g. sra.js) work.

        The active population is searched FIRST, exactly as before, so every trigger that
        resolved correctly yesterday resolves identically today (a label duplicated across
        Projects still prefers the active one); the manifest-wide search only ADDS resolution
        where the old path substituted.
        """
        if not file:
            return _pick_scorecard_version("")
        for key, sch, a in _scorecard_versions():
            if key == file or (sch.source_file or sch.name) == file:
                return (key, sch, a)
        st = session()
        for key, raw in st.all_versions():
            if key == file or (raw.source_file or raw.name) == file:
                try:
                    a = st.analysis_for(key, raw)
                except CPMError:
                    return None  # named but unsolvable — an error, never a substitution
                return (key, a.scoped, a)
        return None

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
        key, sch, _a = picked
        committed_dt = _parse_committed_date(committed)
        if committed_dt is None:
            return JSONResponse(
                {"error": "a committed date (YYYY-MM-DD) is required"}, status_code=422
            )
        iters = max(100, min(5000, iterations))
        sra = compute_sra(sch, config=SRAConfig(iterations=iters))
        # The operator's committed date lives on the STORED plan-date axis; the CDF's offsets live
        # on the pure-CPM axis (completed work packed at the project start). Convert the committed
        # date through the run's constant realignment so confidence/reserve compare like with like
        # (ADR-0353 — before this, a progressed file read 100% confidence / 0 reserve).
        correction = stored_finish_correction(sch, None, sra.deterministic_finish)
        # a committed finish DATE means "finish by the end of that day", so map it to the start of
        # the next day (strictly after any finish on the committed day) for the confidence/reserve.
        end_of_day = committed_dt + dt.timedelta(days=1)
        committed_offset = datetime_to_offset(
            sch.project_start, end_of_day - correction, sch.calendar
        )
        rec = reserve_recommendation(
            sra.cdf,
            committed_offset,
            sch.project_start,
            sch.calendar,
            committed_date_display=committed_dt.date().isoformat(),
            date_correction=correction,
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
        file: str = Query(""),
        uids: str = Query(""),
        title: str = Query(""),
        segment: str = Query(""),
    ) -> JSONResponse:
        picked = _pick_drill_version(file)
        if picked is None:
            msg = (
                f"unknown or unanalyzable version: {file}"
                if file
                else "no analyzable schedule loaded"
            )
            return JSONResponse({"error": msg}, status_code=400)
        key, sch, a = picked
        wanted = _drill_uid_set(sch, a, uids, segment)
        fields, rows = _workbench_drill_rows(sch, a, wanted)
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
        segment: str = Query(""),
    ) -> Response:
        """The activities behind any drillable element (UID set) + chosen extra columns, as Excel/Word."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        picked = _pick_drill_version(file)
        if picked is None:
            msg = f"unknown or unanalyzable version: {file}" if file else "load a schedule first"
            return JSONResponse({"error": msg}, status_code=422)
        _key, sch, a = picked
        fields, rows = _workbench_drill_rows(sch, a, _drill_uid_set(sch, a, uids, segment))
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
            if _decimal_digits(tok.lstrip("-")):
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
        if ignore_constraints or ignore_leveling:
            # ADR-0265: the extra columns come from the BASE (stored-network) analysis rows —
            # mixing them into a counterfactual export would put two bases in one file. The
            # solve-dependent columns are dropped (the drill hides them too); input columns
            # (durations, %, WBS, resources, baselines, custom fields) are basis-independent.
            extra = [c for c in extra if c not in _SOLVE_DEPENDENT_COLS]
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
        2026-07-08). PAIR versions (ADR-0371): the counterfactual restores prior links/durations
        onto the comparison network, so the target anchors the measurement and never truncates
        (a truncated pair starved the restore into a false "no changes to revert")."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _pair_versions()
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
        extra columns the operator toggled on (operator 2026-07-09 — the mirror of /whatif).
        PAIR versions (ADR-0371): entered-the-path attribution diffs the version pair."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _pair_versions()
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
    def export_integrity(
        fmt: str, file: str = Query(""), a: int = Query(-1), b: int = Query(-1)
    ) -> Response:
        """Every integrity finding across the analyzed version pairs. With a valid ``a``/``b``
        pair (the page's picker, operator 2026-08-08) the workbook restricts the findings to
        exactly that pair AND adds the UNDERLYING change ledger (every change's was→now,
        exact minute deltas, per-change effects on the session target, skipped reverts named)
        plus the logic changes as their own sheet; a legacy call without ``a``/``b`` keeps the
        findings-only shape. PAIR versions throughout: the Target UID anchors the ledger's
        measurement, it never truncates the populations being diffed (_pair_versions)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        schedules, cpms, _skipped = _pair_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need two versions"}, status_code=422)
        labels = [sch.source_file or sch.name for sch in schedules]
        n = len(schedules)
        chosen: tuple[int, int] | None = None
        if 0 <= a < n and 0 <= b < n and a != b:
            chosen = (a, b) if a < b else (b, a)  # chronological, like the page
        pair_indices = [chosen] if chosen is not None else [(i, i + 1) for i in range(n - 1)]
        body = []
        for pi, ci in pair_indices:
            if chosen is None and file and labels[ci] != file:
                continue
            prior, current = schedules[pi], schedules[ci]
            for f in detect_manipulation(current, prior, current_cpm=cpms[ci], prior_cpm=cpms[pi]):
                cites = "; ".join(
                    f"UID {c.unique_id} — {c.task_name}" for c in f.citations if c.unique_id
                )
                body.append(
                    (
                        f"{labels[pi]} → {labels[ci]}",
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
        tables: tuple[Table, ...] = (Table("Integrity findings", headers, tuple(body)),)
        if chosen is not None:
            tables += _integrity_ledger_tables(
                schedules[chosen[0]],
                schedules[chosen[1]],
                cpms[chosen[1]],
                st.target_uid,
            )
        tableset = TableSet("Schedule Integrity findings", tables)
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
        # ADR-0262: population-scoped guard — the wave itself is built from st.ordered()
        if len(st.ordered()) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt, TableSet("Bow Wave - CEI", bow_wave_tables(wave)), "bow-wave-cei"
        )

    @app.get("/export/{fmt}/evolution")
    def export_evolution(
        fmt: str,
        target: str | None = Query(None),
        tier: str = Query("off"),
        ignore_constraints: int = Query(0),
        ignore_leveling: int = Query(0),
    ) -> Response:
        """ADR-0320: the workbook honors the SAME page state as /evolution and /api/evolution —
        the focused UID (URL first, session fallback, exactly like the page) and the
        counterfactual trace options via ``_optioned_versions`` — so the options banner's
        "including the Excel exports" promise is true. Defaults reproduce the pre-0320 export
        byte-for-byte. ``tier`` never filters these tables (the tier stepper is a different
        on-screen lens over the same versions); a chosen tier is DISCLOSED as not applied
        rather than silently implied. PAIR versions (ADR-0371): same basis as the page."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _pair_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else session().target_uid
        schedules, cpms, _banner = _optioned_versions(
            schedules,
            cpms,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
        ev = compute_path_evolution(schedules, cpms, target_uid=uid)
        applied, notes = _evolution_export_scope(
            uid,
            tier,
            ignore_constraints=bool(ignore_constraints),
            ignore_leveling=bool(ignore_leveling),
        )
        tables = path_evolution_tables(ev)
        title = "Critical-path evolution"
        if applied:
            title += " - " + "; ".join(applied)
        if applied or notes:
            # the applied scope must be readable in BOTH formats: the TableSet title only
            # reaches the Word heading, so the workbook carries its own "Applied scope" sheet.
            scope_table = Table(
                "Applied scope", ("Applied scope",), tuple((p,) for p in (*applied, *notes))
            )
            tables = (scope_table, *tables)
        return _export_response(fmt, TableSet(title, tables), "critical-path-evolution")

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
    def export_compare(fmt: str, a: int = Query(-1), b: int = Query(-1)) -> Response:
        # PAIR versions (ADR-0371): the signals diff the version pair — same basis as /compare.
        # a/b (operator 2026-08-20): the SAME resolver as the page, so the workbook can never
        # describe a different pair than the one on screen.
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _pair_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        prior_idx, cur_idx = _resolve_pair_indices(len(schedules), a, b)
        manip = detect_manipulation(
            schedules[cur_idx],
            schedules[prior_idx],
            current_cpm=cpms[cur_idx],
            prior_cpm=cpms[prior_idx],
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
        # PAIR versions for the brief's version-pair questions (ADR-0371): the manipulation
        # and remaining-cut questions diff version pairs; the single-version sections keep
        # the focused scope (ADR-0268).
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        brief = build_brief(schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms)
        # ADR-0337 (chapter 12, DoD): the takeaway h1 + context line every page owes, stated as a
        # FINDING with a number in it. Both figures are rendered again in the panels below — the
        # section count and the cited-statement count — so the reader can verify the headline by
        # reading on, and neither is newly computed here.
        cited = sum(len(s.paragraphs) for s in brief.sections)
        versions = len(schedules)
        takeaway = _utility_takeaway(
            f"{cited} cited statement{'s' if cited != 1 else ''} across "
            f"{len(brief.sections)} sections — every one traceable to a schedule, a UID and an "
            "activity.",
            f"The forensic narrative built from {versions} loaded version"
            f"{'s' if versions != 1 else ''}: what the schedule says, in prose, with the citation "
            "for each claim beside it.",
        )
        return _page(
            st,
            "Diagnostic Brief",
            takeaway
            + _export_bar("brief")
            + _skipped_notice(skipped)
            + _brief_body(brief, prov=_series_prov_chip(schedules))
            + '<script src="/static/panelkit.js"></script>',
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
            solv.append((key, a.scoped, a))
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
            acumen_parity=st.dcma_acumen_parity,  # ADR-0282 Option A: findings follow the parity audit
        )
        # ADR-0338 provenance: the findings are computed from the CURRENT version, and the change
        # findings from the PAIR — so when a prior exists the chip names both, with the real
        # version indices rather than 1→2. A single-file chip would under-describe exactly the
        # findings that motivated loading a second version.
        prov = (
            _pair_prov_chip(prior, current, len(solv) - 1, len(solv))
            if prior is not None
            else _prov_chip(current)
        )
        n_high = sum(1 for f in findings if f.severity == Severity.HIGH)
        takeaway = _utility_takeaway(
            f"{len(findings)} finding{'s' if len(findings) != 1 else ''} on this version "
            f"&mdash; {n_high} at HIGH severity.",
            "Forward-looking risks, current issues and recovery opportunities, each scored "
            "likelihood &times; impact and carrying the citation it was derived from.",
        )
        # Render the deterministic narrative immediately so the page never blocks on the model; the
        # local-AI polish (when a model is active) is fetched asynchronously by ai_polish.js via
        # /api/ai/narrative and swapped in. The old synchronous per-statement generate on page load
        # made this page hang (effectively "won't open") on big workbooks with a slow local model.
        body = (
            takeaway
            + _export_bar("risks")
            + _skipped_notice(skipped)
            + _risks_body(current, findings, cur_an.narrative, key, prov=prov)
            + '<script src="/static/panelkit.js"></script>'
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
            days, pct, dl, pl, problems = _reconcile_magnitudes(
                impact_days,
                impact_pct,
                days_locked.strip() in ("1", "on", "true"),
                pct_locked.strip() in ("1", "on", "true"),
                avg_rem,
            )
            if problems:
                # ADR-0313: refuse the row rather than store a magnitude the operator never
                # entered. The register is a forensic input; a silently-zeroed impact is worse
                # than a rejected form, because nothing downstream can tell the two apart.
                st.sra_import_msg = "Risk not added — " + " ".join(problems)
                st.sra_import_is_error = True
                return RedirectResponse(url="/sra", status_code=303)
            p = _clamp_float(prob, 0.0, 1.0, 0.0, scale=0.01)
            cons = int(consequence) if _decimal_digits(consequence.strip()) else None
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

    @app.post("/sra/branch")
    def sra_branch(
        action: str = Form("add"),
        bid: str = Form(""),
        name: str = Form(""),
        prob: str = Form(""),
        after_uid: str = Form(""),
        before_uid: str = Form(""),
        low: str = Form(""),
        ml: str = Form(""),
        high: str = Form(""),
    ) -> RedirectResponse:
        """Maintain the probabilistic-branch list (ADR-0273, Hulett #8): a rework fragnet inserted
        onto the FS tie ``after_uid -> before_uid`` in ``prob``% of SSI iterations, delaying
        everything downstream by its sampled 3-point duration → a bi-modal finish. ``action`` is
        add / remove / clear; durations are entered in working DAYS and stored in minutes. Endpoints
        must be distinct non-summary activities of the selected schedule; a branch whose FS tie is
        absent is accepted but reported inert after the run (never silently dropped)."""
        st = session()
        if action == "clear":
            st.sra_branches.clear()
            return RedirectResponse(url="/sra", status_code=303)
        if action == "remove":
            st.sra_branches = [b for b in st.sra_branches if b.id != bid.strip()]
            return RedirectResponse(url="/sra", status_code=303)
        chosen = _sra_selected(st)
        sch = chosen[1] if chosen is not None else None
        a = int(after_uid) if _decimal_digits(after_uid.strip().lstrip("-")) else None
        b = int(before_uid) if _decimal_digits(before_uid.strip().lstrip("-")) else None
        label = name.strip()
        ok = (
            sch is not None
            and a is not None
            and b is not None
            and a != b
            and a in sch.tasks_by_id
            and b in sch.tasks_by_id
            and not sch.tasks_by_id[a].is_summary
            and not sch.tasks_by_id[b].is_summary
        )
        if label and ok and sch is not None and a is not None and b is not None:
            mpd = sch.calendar.working_minutes_per_day or 480
            p = _clamp_float(prob, 0.0, 1.0, 0.0, scale=0.01)
            lo = max(0, round(_clamp_float(low, 0.0, 1_000_000.0, 0.0) * mpd))
            mid = max(lo, round(_clamp_float(ml, 0.0, 1_000_000.0, 0.0) * mpd))
            hi = max(mid, round(_clamp_float(high, 0.0, 1_000_000.0, 0.0) * mpd))
            st.sra_branch_seq += 1
            st.sra_branches.append(
                ProbabilisticBranch(
                    id=f"B{st.sra_branch_seq}",
                    name=label,
                    probability=p,
                    after_uid=a,
                    before_uid=b,
                    low=lo,
                    ml=mid,
                    high=hi,
                )
            )
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/conditional")
    def sra_conditional(
        action: str = Form("add"),
        cid: str = Form(""),
        name: str = Form(""),
        monitor_uid: str = Form(""),
        metric: str = Form("duration"),
        threshold: str = Form(""),
        trip_when: str = Form("at_or_above"),
        a_after: str = Form(""),
        a_before: str = Form(""),
        a_low: str = Form(""),
        a_ml: str = Form(""),
        a_high: str = Form(""),
        b_after: str = Form(""),
        b_before: str = Form(""),
        b_low: str = Form(""),
        b_ml: str = Form(""),
        b_high: str = Form(""),
    ) -> RedirectResponse:
        """Maintain the conditional-branch list (ADR-0274, Hulett #9): a contingency switch that,
        each SSI iteration, tests a monitored activity and executes the primary Plan A (condition not
        tripped) or the contingency Plan B (tripped) — reporting which plan wins how often. ``metric``
        is ``duration`` (the monitor's sampled duration) or ``finish`` (its pre-contingency early
        finish, read via a probe solve); ``threshold`` is entered in working DAYS; ``trip_when`` is
        ``at_or_above`` (fall to B when the monitor runs late/long) or ``below``. Each plan is a
        fragnet on an FS tie ``after -> before`` with a 3-point rework duration (working days). The
        monitor and both plan endpoints must be distinct non-summary activities of the selected
        schedule; a plan whose FS tie is absent is accepted but the conditional is reported inert
        after the run (never silently dropped)."""
        st = session()
        if action == "clear":
            st.sra_conditionals.clear()
            return RedirectResponse(url="/sra", status_code=303)
        if action == "remove":
            st.sra_conditionals = [c for c in st.sra_conditionals if c.id != cid.strip()]
            return RedirectResponse(url="/sra", status_code=303)
        chosen = _sra_selected(st)
        sch = chosen[1] if chosen is not None else None
        tb = sch.tasks_by_id if sch is not None else {}

        def _valid(u: int | None) -> bool:
            # the monitor and plan endpoints must be SCHEDULED activities: non-summary AND active
            # (is_active) — the set the engine augments/times over. An inactive task would otherwise
            # be accepted here yet crash / silently mis-switch the run (audit M1).
            return u is not None and u in tb and not tb[u].is_summary and tb[u].is_active

        def _uid(raw: str) -> int | None:
            # int() directly (not isdigit(), which admits values int() rejects — '--5', '²', … —
            # and would 500 the endpoint); a clean parse or None (audit L5).
            try:
                return int(raw.strip())
            except ValueError:
                return None

        mon, aa, ab, ba, bb = (
            _uid(monitor_uid),
            _uid(a_after),
            _uid(a_before),
            _uid(b_after),
            _uid(b_before),
        )
        label = name.strip()
        ok = (
            sch is not None
            and label != ""
            and metric in ("duration", "finish")
            and trip_when in ("at_or_above", "below")
            and all(_valid(u) for u in (mon, aa, ab, ba, bb))
            and aa != ab
            and ba != bb
        )
        if (
            ok
            and sch is not None
            and mon is not None
            and aa is not None
            and ab is not None
            and ba is not None
            and bb is not None
        ):
            mpd = sch.calendar.working_minutes_per_day or 480

            def _dur(low: str, ml: str, high: str) -> tuple[int, int, int]:
                lo = max(0, round(_clamp_float(low, 0.0, 1_000_000.0, 0.0) * mpd))
                mid = max(lo, round(_clamp_float(ml, 0.0, 1_000_000.0, 0.0) * mpd))
                hi = max(mid, round(_clamp_float(high, 0.0, 1_000_000.0, 0.0) * mpd))
                return lo, mid, hi

            la, ma, ha = _dur(a_low, a_ml, a_high)
            lb, mb, hb = _dur(b_low, b_ml, b_high)
            thr = max(0, round(_clamp_float(threshold, 0.0, 10_000_000.0, 0.0) * mpd))
            st.sra_conditional_seq += 1
            st.sra_conditionals.append(
                ConditionalBranch(
                    id=f"C{st.sra_conditional_seq}",
                    name=label,
                    monitor_uid=mon,
                    metric=metric,
                    threshold_minutes=thr,
                    plan_a=BranchPlan(
                        after_uid=aa, before_uid=ab, low=la, ml=ma, high=ha, name="Plan A"
                    ),
                    plan_b=BranchPlan(
                        after_uid=ba, before_uid=bb, low=lb, ml=mb, high=hb, name="Plan B"
                    ),
                    trip_when=trip_when,
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
        sampling: str = Form("mc"),
        lhs_centered: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        st.sra_focus_uid = int(focus_uid) if _decimal_digits(focus_uid.strip()) else None
        st.sra_occurrence_mode = (
            "exact_overall" if occurrence_mode == "exact_overall" else "random_each"
        )
        st.sra_correlation = min(1.0, max(0.0, correlation))
        st.sra_use_risk_register = use_risks in ("on", "true", "1")
        st.sra_sampling = "lhs" if sampling == "lhs" else "mc"
        st.sra_lhs_centered = lhs_centered in ("on", "true", "1")
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/correlation-matrix")
    def sra_correlation_matrix(
        action: str = Form("add-pair"),
        uid_a: str = Form(""),
        uid_b: str = Form(""),
        rho: str = Form(""),
        uids: str = Form(""),
        group_rho: str = Form(""),
    ) -> RedirectResponse:
        """Maintain the correlation-matrix inputs (ADR-0270): ``add-pair`` (uid_a, uid_b, rho),
        ``add-group`` (a shared-driver block of uids at one rho), or ``clear``, then redirect to
        /sra. rho is clamped to [-1, 1] (negatives ARE allowed, unlike the [0,1] blanket); an
        unknown/summary uid is dropped; a pair needs two distinct valid uids and a group >= 2."""
        st = session()
        if action == "clear":
            st.sra_corr_pairs = ()
            st.sra_corr_groups = ()
            return RedirectResponse(url="/sra", status_code=303)
        chosen = _sra_selected(st)
        sch = chosen[1] if chosen is not None else None

        def _valid(uid: int) -> bool:
            if sch is None:
                return False
            task = sch.tasks_by_id.get(uid)
            return task is not None and not task.is_summary

        if action == "add-pair":
            a, b = _parse_uid(uid_a), _parse_uid(uid_b)
            if a is not None and b is not None and a != b and _valid(a) and _valid(b):
                r = _clamp_float(rho, -1.0, 1.0, 0.0)
                st.sra_corr_pairs = (*st.sra_corr_pairs, (a, b, r))
        elif action == "add-group":
            members = tuple(dict.fromkeys(u for u in _parse_uid_list(uids) if _valid(u)))
            if len(members) >= 2:
                r = _clamp_float(group_rho, -1.0, 1.0, 0.0)
                st.sra_corr_groups = (*st.sra_corr_groups, (members, r))
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
            if _decimal_digits(tok):
                st.sra_factors[int(tok)] = f
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/load-from-schedule")
    def sra_load_from_schedule() -> RedirectResponse:
        """Seed the SSI grid from the SCHEDULE'S OWN stored SRA fields (ADR-0356) — the values
        SSI itself reads. Replaces the session's factors + Best/Worst pairs wholesale, so the
        run analyzes what the file says instead of whatever a stale setup replayed."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            st.sra_import_msg = "Load a schedule before loading its stored SRA inputs."
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        _key, sch, _cpm = chosen
        factors, bcwc = _file_stored_sra_inputs(sch)
        stored_risks = _file_stored_risks(sch)
        if not factors and not bcwc and not stored_risks:
            st.sra_import_msg = (
                "This schedule carries no stored SRA fields ('SRA Risk Ranking Factors' / "
                "Best/Worst Case Duration / SSI SRA Risk fields) — nothing to load."
            )
            st.sra_import_is_error = True
        else:
            st.sra_factors = factors
            st.sra_bcwc = bcwc
            # ADR-0360: the register rides along — SSI reads its risks off these same fields,
            # so loading factors without them reproduced the input mismatch by another door.
            # A file with NO stored risk fields leaves the operator's register untouched.
            risk_note = ""
            if stored_risks:
                st.sra_risks = stored_risks
                risk_note = f" and {len(stored_risks)} register risk(s)"
            st.sra_import_msg = (
                f"Loaded the schedule's own stored SRA inputs: {len(factors)} Risk Ranking "
                f"Factor(s), {len(bcwc)} Best/Worst Case pair(s){risk_note} "
                "(incomplete activities)."
            )
            st.sra_import_is_error = False
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
                want = {int(t) for t in re.split(r"[,\s]+", uids.strip()) if _decimal_digits(t)}
            for t in non_summary(sch):
                u = t.unique_id
                if u not in st.sra_factors or (want is not None and u not in want):
                    continue
                # a completed activity gets no Best/Worst spread (ADR-0307) — the engine holds it
                # at a point mass, so auto-calc must not leave a range the run will not use. Drop
                # any stale entry (calculated before completion, or restored from a setup) rather
                # than merely skipping the recalculation (ADR-0308).
                if _is_completed(t):
                    st.sra_bcwc.pop(u, None)
                    continue
                rem = (
                    t.remaining_duration_minutes
                    if t.remaining_duration_minutes is not None
                    else t.duration_minutes
                )
                bc, _ml, wc = factor_to_bc_wc(rem, st.sra_factors[u], tbl)
                st.sra_bcwc[u] = (bc, wc)
        return RedirectResponse(url="/sra", status_code=303)

    def _sra_reuse_key(st: SessionState, key: str) -> tuple[object, ...]:
        """The full resolved-input identity of an SSI run / OAT sweep (ADR-0360 export reuse).

        Compared by equality, never hashed. Any input change — a factor, a Best/Worst pair, a
        register row, the focus, the sampler, the correlation spec, the factor table, the
        session SCOPE, or the schedule bytes themselves (``content_hashes``) — changes the
        tuple, so a cached result can never be served across an input edit or a re-uploaded
        file of the same name.

        The scope signature is load-bearing and was MISSING (SRA-EXPORT-STALE-SCOPE, audit
        2026-08-16). The SRA does not run on the raw file: ``_sra_selected`` returns
        ``analysis.scoped``, so the active group/filter is a real input to the cached run.
        ``content_hashes`` cannot stand in for it — that hashes the FILE, which a filter does
        not touch. Observed pre-fix: with ``scope_signature()`` moving from ``A=1`` to
        ``F=(('name', [...]))A=1`` the key was unchanged and ``/export/{fmt}/sra`` handed back
        the object cached under the previous scope."""
        return (
            key,
            st.content_hashes.get(key),
            st.scope_signature(),
            st.sra_focus_uid,
            st.sra_use_risk_register,
            st.sra_occurrence_mode,
            st.sra_correlation,
            _correlation_spec(st),
            st.sra_sampling,
            st.sra_lhs_centered,
            st.sra_factor_rows,
            tuple(sorted(st.sra_factors.items())),
            tuple(sorted(st.sra_bcwc.items())),
            tuple(sorted(st.sra_overrides.items())),
            (st.sra_low, st.sra_ml, st.sra_high),
            tuple(st.sra_risks),
            tuple(st.sra_branches),
            tuple(st.sra_conditionals),
        )

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
            correlation_matrix=_correlation_spec(st),
            sampling=st.sra_sampling,
            lhs_centered=st.sra_lhs_centered,
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
                branches=_schedule_branches(st),
                conditionals=_schedule_conditionals(st),
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        # cache this run's per-activity Criticality Index (ADR-0272) so the SSI grid Gantt can tint
        # its bars by "how often critical" — the grid is a separate fetch, so it reads the last run.
        st.sra_criticality = {int(u): ci for u, ci in result.criticality}
        st.sra_criticality_iters = result.iterations
        # ADR-0360: remember the run under its full input identity so ⤓ EXCEL exports THIS
        # result instead of re-running the model for minutes on click.
        st.sra_run_cache = (_sra_reuse_key(st, _key), result)
        return JSONResponse(_ssi_data(sch, result))

    @app.post("/sra/jcl-config")
    def sra_jcl_config(
        target_date: str = Form(""),
        target_cost: str = Form(""),
        td_share: str = Form(""),
        cost_low: str = Form(""),
        cost_ml: str = Form(""),
        cost_high: str = Form(""),
        confidence: str = Form(""),
        reset: str = Form(""),
    ) -> RedirectResponse:
        """Persist the JCL settings (ADR-0269) on the session, then redirect back to /sra.

        Blank targets mean "use the run's deterministic finish / EAC" (stored ``None``);
        percent inputs are scaled to fractions, clamped, and order-coerced (low <= ml <=
        high); an unparseable target date leaves the stored value unchanged; ``reset``
        restores every default."""
        st = session()
        if reset.strip():
            st.jcl_target_date = None
            st.jcl_target_cost = None
            st.jcl_td_share = 1.0
            st.jcl_cost_low = st.jcl_cost_ml = st.jcl_cost_high = 1.0
            st.jcl_confidence = 0.70
            return RedirectResponse(url="/sra", status_code=303)
        raw_date = target_date.strip()
        if raw_date:
            with contextlib.suppress(ValueError):
                st.jcl_target_date = dt.date.fromisoformat(raw_date).isoformat()
        else:
            st.jcl_target_date = None
        raw_cost = target_cost.strip()
        if raw_cost:
            with contextlib.suppress(ValueError):
                st.jcl_target_cost = float(raw_cost)
        else:
            st.jcl_target_cost = None
        if td_share.strip():
            st.jcl_td_share = _clamp_float(td_share, 0.0, 1.0, st.jcl_td_share, scale=0.01)
        lo, mid, hi = st.jcl_cost_low, st.jcl_cost_ml, st.jcl_cost_high
        if cost_low.strip():
            lo = _clamp_float(cost_low, 0.1, 1.5, lo, scale=0.01)
        if cost_ml.strip():
            mid = _clamp_float(cost_ml, 0.5, 1.5, mid, scale=0.01)
        if cost_high.strip():
            hi = _clamp_float(cost_high, 1.0, 3.0, hi, scale=0.01)
        mid = max(lo, mid)
        hi = max(mid, hi)
        st.jcl_cost_low, st.jcl_cost_ml, st.jcl_cost_high = lo, mid, hi
        if confidence.strip():
            st.jcl_confidence = _clamp_float(confidence, 0.10, 0.95, st.jcl_confidence, scale=0.01)
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/api/sra/jcl")
    def sra_jcl_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        """The joint cost-&-schedule Monte-Carlo (ADR-0269): the SAME schedule inputs as the
        ``/api/sra/ssi`` run (so the finish marginal is identical — the equivalence a test
        pins) plus the session's JCL cost settings. An honest 422 when the file is not
        cost-loaded — a duration-only run is an SCL and is never labeled JCL (Law 2)."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        if cost_loaded_total(sch) <= 0.0:
            return JSONResponse(
                {
                    "error": "This schedule is not cost-loaded (no budgeted cost on its "
                    "tasks) — a duration-only run is a schedule confidence level (SCL), "
                    "not a JCL. Load a cost-loaded schedule to run the joint simulation."
                },
                status_code=422,
            )
        cfg = SRAConfig(
            iterations=max(100, min(10000, iterations)),
            distribution="pert" if distribution == "pert" else "triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
            correlation_matrix=_correlation_spec(st),
            sampling=st.sra_sampling,
            lhs_centered=st.sra_lhs_centered,
        )
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        try:
            result = run_maybe_offloaded(
                heavy,
                compute_jcl,
                sch,
                config=cfg,
                three_point=_ssi_three_point(st, sch),
                risks=_schedule_risks(st),
                branches=_schedule_branches(st),
                conditionals=_schedule_conditionals(st),
                jcl=_jcl_config_from_state(st),
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_jcl_data(sch, result))

    @app.get("/api/sra/oat")
    def sra_oat_json() -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        # ADR-0359: risk-affected activities keep their own duration rows AND the register
        # contributes fired-alone R/O rows — SSI's Sensitivity export lists both, so nothing
        # is excluded any more.
        exclude: frozenset[int] = frozenset()
        oat_risks = _schedule_risks(st) if st.sra_use_risk_register else ()
        three_point = _ssi_three_point(st, sch)
        # ADR-0261 P5: the sweep is TWO CPM solves per candidate activity and was unbounded — a
        # huge schedule could pin the worker for hours. Above the cap, sweep only the candidates
        # with the LARGEST ML/remaining duration (the biggest possible swing; deterministic uid
        # tiebreak) and DISCLOSE it in the payload + on the panel — never a silent subset. The
        # engine itself is untouched; below the cap the sweep is byte-identical to before.
        candidates = [u for u in three_point if u not in exclude]
        capped = len(candidates) > _OAT_MAX_ACTIVITIES
        if capped:
            keep = sorted(candidates, key=lambda u: (-three_point[u][1], u))[:_OAT_MAX_ACTIVITIES]
            three_point = {u: three_point[u] for u in keep}
        # the OAT sweep is one CPM solve per task — offload it on big schedules too
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        oat_key = (_sra_reuse_key(st, _key), tuple(sorted(three_point.items())))
        ocache = st.sra_oat_cache
        if ocache is not None and ocache[0] == oat_key:
            oat = cast(tuple[OATSensitivity, ...], ocache[1])  # ADR-0360: same inputs, same rows
        else:
            try:
                oat = run_maybe_offloaded(
                    heavy,
                    compute_oat_sensitivity,
                    sch,
                    three_point=three_point,
                    target_uid=st.sra_focus_uid,
                    exclude_uids=exclude,
                    risks=oat_risks,
                )
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            st.sra_oat_cache = (oat_key, oat)
        names = sch.tasks_by_id
        mpd = sch.calendar.working_minutes_per_day or 480
        payload: dict[str, object] = {
            "rows": [
                {
                    "uid": o.unique_id,
                    # an R/O row (ADR-0359) is the register risk fired alone on its affected
                    # activity — named for the risk, like SSI's own Sensitivity export
                    "name": (
                        f"R/O — {o.risk_name or o.risk_id}"
                        if o.risk_id
                        else (names[o.unique_id].name if o.unique_id in names else "")
                    ),
                    "risk_id": o.risk_id,
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
        if capped:
            payload["note"] = (
                f"Sensitivity swept the {_OAT_MAX_ACTIVITIES} largest-remaining of "
                f"{len(candidates)} candidate activities (size cap — narrow with a filter or "
                "target for a full sweep of a smaller population)."
            )
        return JSONResponse(payload)

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
                # criticality-tint provenance (ADR-0272): whether the last SSI run's CI is available
                # to tint by, and at what iteration count — the grid labels the tint honestly.
                "criticality_available": bool(st.sra_criticality),
                "criticality_iters": st.sra_criticality_iters,
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
            # ADR-0308: a completed activity carries no Best/Worst spread, so the grid must neither
            # derive one from a factor nor accept a hand-typed one — the run would ignore it and the
            # operator would be looking at a range that does not exist. The factor itself is still
            # recorded (it is the operator's ranking), only the range is refused.
            done_task = _is_completed(task)
            if done_task:
                st.sra_bcwc.pop(uid, None)
            if d.get("factor") not in (None, ""):
                try:
                    # factor 0 is VALID (no Best/Worst uncertainty -> use remaining); only 1..5 carry
                    # a Best/Worst spread, so clamp to 0..5, not 1..5
                    f = min(5, max(0, int(d["factor"])))
                except (TypeError, ValueError):
                    f = None
                if f is not None:
                    st.sra_factors[uid] = f
                    if not done_task:
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
            if manual and not done_task:  # a completed row never takes a range (ADR-0308)
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
        version applies cleanly to another.

        ADR-0313: the read is **bounded** and every rejection is **reported**. This route used to
        do an unbounded ``setup.file.read()`` and then redirect in total silence on bad JSON —
        so an operator who picked the wrong file saw their previous setup apparently survive with
        no indication their load had failed. Its two sibling importers already read
        ``_MAX_UPLOAD_BYTES + 1`` and report; this is conformance to that convention, not new policy.
        """
        st = session()
        # A setup JSON is small by construction (scalars + per-UID factor maps), so it gets its own
        # far tighter cap than the 500 MB schedule-file limit rather than inheriting a bound sized
        # for an .mpp. Sized to hold a per-task factor + BC/WC entry for a schedule far larger than
        # any reference file, with room to spare.
        data = setup.file.read(_MAX_SETUP_BYTES + 1)
        if len(data) > _MAX_SETUP_BYTES:
            st.sra_import_msg = (
                f"SSI setup not loaded — file exceeds the {_MAX_SETUP_BYTES // (1024 * 1024)} MB "
                "cap for a setup file. Nothing on this page was changed."
            )
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        try:
            payload = json.loads(data)
        except (ValueError, TypeError) as exc:
            st.sra_import_msg = (
                f"SSI setup not loaded — that file is not readable JSON: {exc}. "
                "Nothing on this page was changed."
            )
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        if isinstance(payload, dict):
            _apply_ssi_setup(st, payload)
            # ADR-0356: a setup replayed onto a changed schedule must announce itself — the
            # root-caused SSI delta was exactly this, silent (605 of 783 factors stale).
            chosen = _sra_selected(st)
            warning = (
                _setup_vintage_warning(st, chosen[1], payload.get("schedule_fingerprint"))
                if chosen is not None
                else None
            )
            if warning:
                st.sra_import_msg = f"SSI setup loaded — CHECK INPUTS: {warning}"
                st.sra_import_is_error = True
            else:
                st.sra_import_msg = "SSI setup loaded."
        else:
            st.sra_import_msg = (
                "SSI setup not loaded — that JSON is not an SSI setup object. "
                "Nothing on this page was changed."
            )
            st.sra_import_is_error = True
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
            correlation_matrix=_correlation_spec(st),
            sampling=st.sra_sampling,
            lhs_centered=st.sra_lhs_centered,
        )
        heavy = len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD
        # ADR-0360: this endpoint used to re-run the Monte-Carlo AND the full OAT sweep on
        # every ⤓ EXCEL click — measured 140 s on the committed 2,125-task SRA schedule, which
        # reads as a dead button. When the page has already run on identical inputs, export
        # EXACTLY that result (fidelity bonus: the workbook now always matches the screen —
        # including the operator's chosen iteration count instead of a hardcoded 2000).
        rk = _sra_reuse_key(st, _key)
        rcache = st.sra_run_cache
        if rcache is not None and rcache[0] == rk:
            result = cast(SSIResult, rcache[1])
        else:
            result = run_maybe_offloaded(
                heavy,
                compute_sra_ssi,
                sch,
                config=cfg,
                three_point=tp,
                risks=_schedule_risks(st),
                branches=_schedule_branches(st),
                conditionals=_schedule_conditionals(st),
            )
            st.sra_run_cache = (rk, result)
        oat_key = (rk, tuple(sorted(tp.items())))
        ocache = st.sra_oat_cache
        if ocache is not None and ocache[0] == oat_key:
            oat = cast(tuple[OATSensitivity, ...], ocache[1])
        else:
            oat = run_maybe_offloaded(
                heavy,
                compute_oat_sensitivity,
                sch,
                three_point=tp,
                target_uid=st.sra_focus_uid,
                risks=_schedule_risks(st) if st.sra_use_risk_register else (),
            )
            st.sra_oat_cache = (oat_key, oat)
        if fmt == "docx":
            # the comprehensive narrative SRA report (PM summary -> per-section detail + vector
            # charts + the 5x5 matrices + assumptions); ADR-0124
            return Response(
                content=render_document(_sra_report_blocks(st, sch, result, oat)),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="sra-report.docx"'},
            )
        tables = _ssi_export_tables(st, sch, result, oat)
        if cost_loaded_total(sch) > 0.0:
            # cost-loaded file: append the JCL sheets (ADR-0269) — same schedule inputs as
            # the SSI run above, branches/conditionals included (JCL-BR-01, ADR-0408), so
            # the joint sample's finish marginal matches it exactly: one workbook, one story
            jr = run_maybe_offloaded(
                heavy,
                compute_jcl,
                sch,
                config=cfg,
                three_point=tp,
                risks=_schedule_risks(st),
                branches=_schedule_branches(st),
                conditionals=_schedule_conditionals(st),
                jcl=_jcl_config_from_state(st),
            )
            tables = TableSet(tables.title, tables.tables + _jcl_export_tables(jr))
        return _export_response(fmt, tables, "sra-ssi")

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
            correlation_matrix=_correlation_spec(st),
            sampling=st.sra_sampling,
            lhs_centered=st.sra_lhs_centered,
        )
        result = run_maybe_offloaded(
            len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD,
            compute_sra_ssi,
            sch,
            config=cfg,
            three_point=tp,
            risks=_schedule_risks(st),
            branches=_schedule_branches(st),
            conditionals=_schedule_conditionals(st),
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
            st.sra_import_is_error = True
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
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        try:
            sheets = read_xlsx(data)
        except XlsxError as exc:
            st.sra_import_msg = f"Could not read that file: {exc}"
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        summary = _import_risk_register(st, sch, sheets)
        if "error" in summary:
            st.sra_import_msg = f"Risk register not imported — {summary['error']}."
            st.sra_import_is_error = True
        else:
            malformed = int(cast(int, summary.get("malformed", 0)))
            st.sra_import_msg = (
                f"Imported {summary['imported']} risk(s); skipped {summary['skipped']} incomplete "
                f"row(s); dropped {summary['dropped_uids']} unmatched UID(s)"
                + (
                    f"; SKIPPED {malformed} row(s) with an unreadable impact figure — "
                    "those risks are NOT in the register."
                    if malformed
                    else "."
                )
            )
            st.sra_import_is_error = bool(malformed)
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/import/task-risk")
    def sra_import_task_risk(file: UploadFile) -> RedirectResponse:
        """Apply per-task Risk Ranking Factors + Best/Worst-Case durations from a filled-in template,
        then redirect to /sra with a one-shot summary."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            st.sra_import_msg = "Load a schedule before importing task risk inputs."
            st.sra_import_is_error = True
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
            st.sra_import_is_error = True
            return RedirectResponse(url="/sra", status_code=303)
        summary = _import_task_risk(st, sch, sheets)
        if "error" in summary:
            st.sra_import_msg = f"Task risk inputs not imported — {summary['error']}."
            st.sra_import_is_error = True
        else:
            st.sra_import_msg = (
                f"Set {summary['factors']} Risk Ranking Factor(s) and {summary['bcwc']} Best/Worst "
                f"duration pair(s); dropped {summary['dropped_uids']} unmatched UID(s)."
            )
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/export/{fmt}/brief")
    def export_brief(fmt: str) -> Response:
        st = session()
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        # PAIR versions for the version-pair questions (ADR-0371) — same basis as /brief.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        brief = build_brief(schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms)
        if fmt == "docx":
            # the exported exhibit's locality sentence follows the OBSERVED banner (DoD 001b)
            blocks = cast(
                "list[Block]",
                brief_blocks(brief, ai_is_local=not _observed_banner(st).cloud_active),
            )
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
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        # PAIR versions for section 3.1's entered/left (ADR-0371) — same basis as /briefing.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        briefing = st.briefing_for(
            schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms
        )
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
        # PAIR versions for section 3.1's entered/left (ADR-0371): the diff never truncates.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        briefing = st.briefing_for(
            schedules, cpms, pair_schedules=pair_schedules, pair_cpms=pair_cpms
        )
        body = (
            _the_briefing_header(
                briefing,
                schedules[-1],
                cpms[-1],
                acumen_parity=st.dcma_acumen_parity,
            )
            + _skipped_notice(skipped)
            + '<div id=briefingBody data-ai-endpoint="/api/ai/briefing">'
            + _briefing_body(briefing, prov=_series_prov_chip(schedules))
            + '</div><script src="/static/ai_polish.js"></script>'
            # ADR-0337: panelkit.js drives the head strip's ⤓ / ⛶. It is loaded ONCE per page and
            # binds a delegated listener on `document`, so it keeps driving the briefing after
            # ai_polish.js swaps `#briefingBody`'s innerHTML out from under it.
            + '<script src="/static/panelkit.js"></script>'
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
            narrative = _polished_narrative(st, key, analysis.scoped, analysis)
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
        # PAIR versions for section 3.1's entered/left (ADR-0371) — same basis as /briefing.
        pair_schedules, pair_cpms, _pskipped = _pair_versions()
        try:
            briefing = build_briefing(
                schedules,
                cpms=cpms,
                backend=backend,
                acumen_parity=st.dcma_acumen_parity,
                pair_schedules=pair_schedules,
                pair_cpms=pair_cpms,
            )
            # ADR-0337: the SAME provenance chip the server-rendered body carries. ai_polish.js
            # replaces the whole of `#briefingBody`, so omitting it here would make the chip
            # disappear the moment a local model polished the briefing.
            html = _briefing_body(briefing, prov=_series_prov_chip(schedules))
        except Exception:
            logger.warning("AI briefing endpoint failed; client keeps the deterministic briefing")
            return JSONResponse({"polished": False})
        return JSONResponse({"polished": True, "html": html})

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> HTMLResponse:
        st = session()
        note = _ai_runtime_note(getattr(app.state, "ollama", None))
        return _page(st, "AI Settings", _settings_body(st, runtime_note=note))

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
        gateway_endpoint: str = Form(""),
        gateway_approved: str = Form(""),
        gateway_api_key: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        try:
            cls = Classification(classification)
        except ValueError:
            cls = Classification.CLASSIFIED  # unknown -> safe default
        if qa_mode not in ("annotate", "strict", "interpretive", "unrestricted"):
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
        # the approved gateway (ADR-0402): only an exact allowlisted endpoint may sit in the
        # config — anything else clears to "" (gateway off). The constructor re-refuses too;
        # this keeps an unapproved URL from ever LOOKING accepted on the settings page.
        gateway_endpoint = gateway_endpoint.strip()
        if gateway_endpoint and not is_approved_gateway_endpoint(gateway_endpoint):
            gateway_endpoint = ""
        # the key field is masked and never echoed back, so every ordinary re-save posts it
        # BLANK — blank means KEEP the held key (a save of any other setting must not
        # silently de-authenticate the gateway); a non-blank value replaces it (ADR-0403)
        gateway_api_key = gateway_api_key.strip() or st.ai_config.gateway_api_key
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
            gateway_endpoint=gateway_endpoint,
            # an absent checkbox posts nothing — only the literal checked value records the
            # operator's approval assertion; anything else is False (fail closed)
            gateway_approved=gateway_approved == "1",
            gateway_api_key=gateway_api_key,
        )
        st.backend_cache = None  # re-route immediately — a settings change must take effect now
        st.second_cache = None
        try:  # ADR-0404: settings survive the quit — the next launch comes up as configured
            save_ai_config(st.ai_config)
        except Exception:
            logger.warning("could not persist AI settings; they will not survive this session")
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
        """Probe a model server for the model ids it currently serves.

        Feeds the live model dropdowns in AI Settings so the operator picks a real, valid id
        (especially for OpenAI-compatible servers, where the loaded model id must match exactly).
        Fail-closed on the destination: the two local kinds refuse any non-loopback endpoint and
        never reach out (Law 1); ``kind=gateway`` (ADR-0402) refuses anything but an EXACT
        approved-gateway endpoint, and its probe — like every gateway request — is recorded in
        the AI transaction log."""
        kind = kind if kind in ("ollama", "openai", "gateway") else "ollama"
        ep = endpoint.strip()
        if kind == "gateway":
            if not is_approved_gateway_endpoint(ep):
                return JSONResponse(
                    {
                        "reachable": False,
                        "models": [],
                        "reason": "endpoint must be an approved gateway "
                        "(select it from the approved list)",
                    }
                )
            try:
                # authenticate with the SESSION's resolved key (config, else env) — the
                # credential never travels in the probe URL (ADR-0403)
                be: AIBackend = GatewayBackend(
                    endpoint=ep,
                    model="",
                    classification=str(session().ai_config.classification),
                    api_key=resolve_gateway_api_key(session().ai_config),
                    timeout=8.0,
                )
            except Exception as exc:  # allowlist guard — report, never raise outward
                return JSONResponse({"reachable": False, "models": [], "reason": str(exc)})
        else:
            default = "http://127.0.0.1:11434" if kind == "ollama" else "http://127.0.0.1:1234"
            if ep and not is_local_http_endpoint(ep):
                return JSONResponse(
                    {"reachable": False, "models": [], "reason": "endpoint must be a loopback URL"}
                )
            try:
                be = (
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
        try:  # ADR-0404: OFF is a setting too — the next launch must come up off and keyless
            save_ai_config(st.ai_config)
        except Exception:
            logger.warning("could not persist AI settings; they will not survive this session")
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

    @app.post("/dcma/scope")
    def set_dcma_scope(parity: str = Form(""), next: str = Form("/")) -> RedirectResponse:
        """Toggle the single Acumen-parity DCMA mode (ADR-0280). The checkbox is absent when
        unchecked, so the POST carries its full current state. Funnels through the SessionState
        setter, which re-keys the analysis cache epoch so the audit recomputes on the next render
        (never a stale audit across the toggle)."""
        session().set_dcma_acumen_parity(bool(parity))
        # local redirect only: a path on this app, never a scheme/host ("//host" included)
        dest = next if next.startswith("/") and not next.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/project/select")
    def select_project(pid: str = Form(""), next_url: str = Form("/")) -> RedirectResponse:
        """Set the session's ACTIVE project (ADR-0258) — the banner switcher and Portfolio's
        "Analyze" action. Selection is population-only (per-key caches stay valid; nothing is
        invalidated); an unknown/stale pid is ignored (fail-soft). Returns to the page the
        operator was on, carried as an explicit ``next_url`` (the app sends
        ``Referrer-Policy: no-referrer``, so the Referer header is never available)."""
        if pid:
            session().set_active_project(pid)
        # local redirect only: a path on this app, never a scheme/host ("//host" included)
        dest = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/project/exclude")
    def exclude_version(key: str = Form(""), excluded: str = Form("")) -> RedirectResponse:
        """Portfolio's duplicate/revision resolution (ADR-0259): EXCLUDE one loaded version from
        every analysis population, or RESTORE it. Reversible — the file stays loaded and listed
        (badged); nothing is deleted or merged silently. Unknown keys are ignored (fail-soft)."""
        session().set_excluded(key, excluded == "1")
        return RedirectResponse(url="/portfolio", status_code=303)

    @app.post("/project/combine")
    def combine_projects_route(
        pids: tuple[str, ...] = Form(()), title: str = Form("")
    ) -> RedirectResponse:
        """Portfolio's explicit "these files are ONE project" override (operator 2026-08-20).

        Automatic grouping never merges differing titles on its own — per-update P6 exports
        carry per-copy Project IDs, and a renamed project name shatters one real project into
        N one-version populations, disabling every cross-version view. This route is the
        operator saying they belong together: the selected populations are re-labeled with one
        shared ingestion folder (``SessionState.combine_projects``), the combined Project
        becomes active, and the wall's version series light up. Fail-soft on unknown or
        too-few pids and on a blank name, like every project action."""
        session().combine_projects(pids, title)
        return RedirectResponse(url="/portfolio", status_code=303)

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
            # ADR-0332: reset by REFLECTION, not by naming fields. This handler used to enumerate
            # them and had fallen 27 fields behind the dataclass — the whole SRA setup (factors,
            # Best/Worst pairs, the correlation matrix, the cached Criticality Index), every JCL
            # cost setting, margin_rate, the AI translations of imported activity names, and
            # dcma_acumen_parity (a metric-MODE flag) all survived a "wipe". Since the SRA maps
            # are keyed by UniqueID, the next project loaded inherited the previous one's risk
            # inputs wherever UIDs collided. `reset()` now returns every field to its default
            # except state.WIPE_PRESERVED, so a NEW field is wiped by default.
            st.reset()
            # ADR-0263: bump the wipe generation FIRST, then clear the on-disk CUI cache (parsed
            # schedules + derived metrics) UNDER the same lock that gates every store — so an
            # in-flight compute that started pre-wipe can never re-insert the operator's data
            # (in memory or on disk) after this point. "Nothing survives the reset" holds.
            # wipe_gen is in WIPE_PRESERVED precisely so reset() cannot rewind this guard to 0.
            st.wipe_gen += 1
            get_default_cache().clear()
            # A wipe is a full reset: turn the AI back off and stop any local model it is
            # running, so a wiped session never leaves Ollama consuming RAM/CPU (operator
            # report: Ollama survived a Wipe → Quit). Re-enabling is one click in AI Settings.
            # The classification is carried across deliberately — it describes the OPERATOR's
            # handling posture, not the schedules that were just discarded.
            st.ai_config = AIConfig(classification=st.ai_config.classification, backend="null")
            try:  # ADR-0404: a wipe's AI reset persists like any other settings change
                save_ai_config(st.ai_config)
            except Exception:
                logger.warning("could not persist AI settings; they will not survive this session")
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
    """A friendly schedule key: the filename with all supported extensions stripped.

    Control characters are stripped too (ADR-0263): the epoch cache keys join
    ``key␟scope-signature`` on ``\\x1f``, so a filename smuggling that byte could make one
    session key collide with another key's epoch key. The identity anchor would still catch a
    wrong-schedule hit, but the key space itself must be collision-free by construction."""
    exts = {e.lower() for e in supported_extensions()}
    cleaned = "".join(ch for ch in Path(name).name if ch >= " ")
    path = Path(cleaned)
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
    # native .mpp / .mpt — needs the MPXJ runner + a JRE. ADR-0293: ask the ingest-scoped
    # capability probe FIRST. On a machine that cannot convert .mpp at all the answer is the same
    # for every file, so spilling each one to disk before finding out just writes (and discards) a
    # folder's worth of megabytes; the operator sees the identical message either way.
    capability = mpp_capability()
    if not capability.available:
        raise ImporterError(capability.reason)
    # Write into a temp *directory* and close the file before parsing: on Windows an open
    # NamedTemporaryFile handle blocks the MPXJ java subprocess from reading the path (the
    # upload would always fail on Windows).
    with tempfile.TemporaryDirectory(prefix="sf-upload-") as tmp:
        temp_path = Path(tmp) / f"upload{suffix or '.mpp'}"
        temp_path.write_bytes(data)
        return load_schedule(temp_path)


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


# NASA Schedule Management Handbook citations — verified against the committed reference PDF
# (00_REFERENCE_INTAKE/references/schedule-management-handbook-20240315-update.zip); the section
# numbers and the 50%-consumed corrective threshold are quoted from that document, not invented.
# CITATION CORRECTED (ADR-0254, verified against the PDF): the sentence "The corrective action
# threshold is set where the margin is 50% consumed" lives in §7.3.3.2.3 "Sufficiency of Margin"
# (printed p.324 / PDF p.325), NOT §7.3.3.1.6 as ADR-0230 recorded — and it is EXAMPLE-framed
# there ("In this example case, the P/p has chosen..."). §7.3.3.1.6's own Thresholds paragraph is
# deliberately non-numeric ("corrective action is required when significant margin is consumed");
# the handbook's general rule is that thresholds are program-set in the SMP.
_HB_CONSUME_SEC = "&sect;7.3.3.2.3 Sufficiency of Margin (the handbook's example threshold)"


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


def _ssi_three_point(st: SessionState, sch: Schedule) -> dict[int, tuple[int, int, int]]:
    """Per-task ``(BestCase, MostLikely=remaining, WorstCase)`` minutes for the SSI run — a manual /
    auto Best-Worst override when present, else derived from the task's Risk Ranking Factor. Tasks
    with neither are absent (the engine treats them as a point mass = no duration uncertainty)."""
    tbl = RiskFactorTable(rows=st.sra_factor_rows)
    out: dict[int, tuple[int, int, int]] = {}
    for t in non_summary(sch):
        u = t.unique_id
        if _is_completed(t):
            continue  # completed work is a recorded fact, never a forecast (ADR-0307)
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


def _schedule_branches(st: SessionState) -> tuple[ProbabilisticBranch, ...]:
    """The probabilistic branches for the SSI run (ADR-0273), stored ready-to-use on the session."""
    return tuple(st.sra_branches)


def _schedule_conditionals(st: SessionState) -> tuple[ConditionalBranch, ...]:
    """The conditional branches for the SSI run (ADR-0274), stored ready-to-use on the session."""
    return tuple(st.sra_conditionals)


#: The accepted numeric grammar for an operator-entered SRA magnitude, applied BEFORE ``float()``
#: (ADR-0313). Deliberately stricter than **both** permissive parsers this value used to meet:
#: Python's ``float()`` accepts ``"1_000"`` / ``"inf"`` / ``"nan"``, and JS ``parseFloat`` accepts a
#: numeric PREFIX (``parseFloat("1.2.3") == 1.2``, ``parseFloat("5 days") == 5``). Those two
#: permissive sets do not agree, which is exactly how the server and ``sra_risk.js`` came to read
#: different numbers from the same keystroke. One shared grammar is the only shape in which they
#: cannot: `tests/web/js/magnitude_cases.json` is the single case table both sides are pinned to.
_MAGNITUDE_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

#: Longest magnitude string accepted. A real entry is a handful of characters, and this bound is
#: what makes the overflow class unreachable (``float("1" * 400)`` is ``inf``) **without** inventing
#: a magnitude ceiling — "how many days is too many" is a product decision, deliberately not made
#: here, because a schedule-risk impact has no defensible universal maximum.
_MAGNITUDE_MAX_LEN = 32


@dataclass(frozen=True)
class _Magnitude:
    """One operator-entered SRA magnitude in three distinguishable states (ADR-0313).

    ``absent`` (nothing typed) must stay distinct from ``invalid`` (something typed that is not a
    number). Absent is the signal to **derive** this magnitude from the other one; collapsing the
    two is what made an unparseable entry silently *suppress* that derivation and substitute a
    locked zero, leaving one risk row whose two magnitudes described two different events.
    """

    value: float | None = None
    reason: str | None = None

    @property
    def is_absent(self) -> bool:
        return self.value is None and self.reason is None

    @property
    def is_invalid(self) -> bool:
        return self.reason is not None


def _parse_magnitude(raw: str, *, label: str) -> _Magnitude:
    """Parse one SRA magnitude field into absent / valid / invalid-with-a-reason (ADR-0313).

    The reason is operator-facing text, so it names the field and quotes what was entered — never
    a stack trace and never a silent default.
    """
    text = raw.strip()
    if not text:
        return _Magnitude()
    if len(text) > _MAGNITUDE_MAX_LEN:
        return _Magnitude(
            reason=f"{label} is too long (limit {_MAGNITUDE_MAX_LEN} characters) — enter a number."
        )
    if not _MAGNITUDE_RE.match(text):
        return _Magnitude(reason=f"{label} is not a number: {text!r}.")
    try:
        value = float(text)
    except (ValueError, OverflowError):  # pragma: no cover - the grammar already excludes these
        return _Magnitude(reason=f"{label} is not a number: {text!r}.")
    if not math.isfinite(value):  # pragma: no cover - "inf"/"nan" cannot match the grammar
        return _Magnitude(reason=f"{label} is not a finite number: {text!r}.")
    return _Magnitude(value=value)


def _reconcile_magnitudes(
    days_str: str, pct_str: str, days_locked: bool, pct_locked: bool, avg_rem: float
) -> tuple[float, float, bool, bool, tuple[str, ...]]:
    """Parse the two magnitudes and derive whichever the operator did not supply, using ``avg_rem``
    (days = pct/100 x avg ; pct = days/avg x 100). A field that was supplied (or flagged) is locked
    and used verbatim. Mirrors the client-side ``sra_risk.js`` so the JS-off / load path agrees.

    Returns ``(days, pct, days_locked, pct_locked, problems)``. **``problems`` is not advisory** —
    a caller that ignores it stores a magnitude the operator never entered (ADR-0313). An invalid
    field yields no value at all rather than a locked zero, so the caller's only options are to
    report or to refuse; it cannot accidentally proceed with a fabricated figure.
    """
    days_field = _parse_magnitude(days_str, label="Impact (working days)")
    pct_field = _parse_magnitude(pct_str, label="Impact (%)")
    problems = tuple(f.reason for f in (days_field, pct_field) if f.reason is not None)
    days = days_field.value
    pct = pct_field.value
    # An INVALID field is not "supplied": locking it would pin the very value we refused to read.
    dl = (days_locked and not days_field.is_invalid) or days is not None
    pl = (pct_locked and not pct_field.is_invalid) or pct is not None
    if avg_rem > 0:
        if days is not None and pct is None and not pct_field.is_invalid:
            pct = round(days / avg_rem * 100.0, 2)
        elif pct is not None and days is None and not days_field.is_invalid:
            days = round(pct / 100.0 * avg_rem, 2)
    return (days or 0.0), (pct or 0.0), dl, pl, problems


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
    skipped = dropped_uids = malformed = 0
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
        days, pct, dl, pl, problems = _reconcile_magnitudes(
            _cell(row, c_days), "", True, False, avg_rem
        )
        if problems:
            # ADR-0313: this function's own contract already promises "a missing figure is skipped
            # and reported, never guessed" — that promise was untrue for a MALFORMED figure, which
            # took the silent-zero path instead. Counted separately from `skipped` because
            # "unreadable" and "incomplete" are different things for the operator to go fix.
            malformed += 1
            continue
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
    return {
        "imported": len(imported),
        "skipped": skipped,
        "dropped_uids": dropped_uids,
        "malformed": malformed,
    }


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


def _correlation_spec(st: SessionState) -> CorrelationSpec | None:
    """The session's correlation-matrix inputs as the engine's frozen :class:`CorrelationSpec`,
    or ``None`` when both are empty (the scalar blanket-correlation path then runs). ADR-0270."""
    if not st.sra_corr_pairs and not st.sra_corr_groups:
        return None
    return CorrelationSpec(pairs=st.sra_corr_pairs, groups=st.sra_corr_groups)


def _jcl_config_from_state(st: SessionState) -> JCLConfig:
    """The session's JCL settings as the engine's frozen config (ADR-0269)."""
    target: dt.date | None = None
    if st.jcl_target_date:
        with contextlib.suppress(ValueError):
            target = dt.date.fromisoformat(st.jcl_target_date)
    return JCLConfig(
        target_date=target,
        target_cost=st.jcl_target_cost,
        td_share=st.jcl_td_share,
        cost_low=st.jcl_cost_low,
        cost_ml=st.jcl_cost_ml,
        cost_high=st.jcl_cost_high,
        confidence=st.jcl_confidence,
    )


def _jcl_data(sch: Schedule, result: JCLResult) -> dict[str, object]:
    """The JCL run payload for ``sra_jcl.js`` — the joint statement, the football-scatter
    sample, the frontier, and the cost marginal (dates realigned like the SSI result)."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    pct = 100.0
    return {
        "target_uid": result.target_uid,
        "focus_name": focus,
        "iterations": result.iterations,
        "sampling": result.sampling,
        "deterministic": {
            "date": result.deterministic_finish_date,
            "eac": result.deterministic_eac,
        },
        "targets": {
            "date": result.target_date,
            "cost": result.target_cost,
            "confidence": round(result.confidence * pct, 1),
        },
        "levels": {
            "scl": round(result.scl * pct, 1),
            "ccl": round(result.ccl * pct, 1),
            "jcl": round(result.jcl * pct, 1),
        },
        "quadrants": {
            "both": round(result.q_both * pct, 1),
            "date_only": round(result.q_date_only * pct, 1),
            "cost_only": round(result.q_cost_only * pct, 1),
            "neither": round(result.q_neither * pct, 1),
        },
        "finish_percentiles": [
            {"label": "P10", "date": result.finish_p10_date},
            {"label": "P50", "date": result.finish_p50_date},
            {"label": "P80", "date": result.finish_p80_date},
            {"label": "P90", "date": result.finish_p90_date},
        ],
        "cost_percentiles": [
            {"label": "P10", "value": result.cost_p10},
            {"label": "P50", "value": result.cost_p50},
            {"label": "P80", "value": result.cost_p80},
            {"label": "P90", "value": result.cost_p90},
        ],
        "cost_mean": result.cost_mean,
        "cost_std": result.cost_std,
        "cost_min": result.cost_min,
        "cost_max": result.cost_max,
        "points": [[d, c] for d, c in result.points],
        "frontier": [[d, c] for d, c in result.frontier],
        "cost_cdf": [[c, p] for c, p in result.cost_cdf],
        "provenance": {
            "sunk": result.sunk_total,
            "remaining_ti": result.remaining_ti_total,
            "remaining_td": result.remaining_td_total,
            "completed": result.completed_count,
            "incomplete_costed": result.incomplete_costed_count,
            "td_share_pct": round(result.td_share * pct, 1),
            "cost_uncertainty_on": result.cost_uncertainty_on,
        },
        "correlation_matrix": {
            "applied": result.correlation_matrix_applied,
            "repaired": result.correlation_matrix_repaired,
            "min_eigenvalue": round(result.correlation_min_eigenvalue, 4),
            "frobenius_distance": round(result.correlation_frobenius_distance, 4),
        },
    }


def _jcl_export_tables(result: JCLResult) -> tuple[Table, ...]:
    """The JCL sheets appended to the SRA Excel hand-out when the file is cost-loaded
    (ADR-0269): the headline joint statement + provenance, the iso-confidence frontier, and
    the joint sample behind the football scatter. Every figure is the engine's own."""
    pct = 100.0
    headline_rows: tuple[tuple[Cell, ...], ...] = (
        ("Iterations", result.iterations),
        (
            "Focus event UID",
            result.target_uid if result.target_uid is not None else "project finish",
        ),
        ("Deterministic finish (all-ML)", result.deterministic_finish_date),
        ("Deterministic EAC = AC + (BAC - EV)", result.deterministic_eac),
        ("Target date", result.target_date),
        ("Target cost", result.target_cost),
        ("SCL - P(finish on/before target date) %", round(result.scl * pct, 1)),
        ("CCL - P(EAC at/below target cost) %", round(result.ccl * pct, 1)),
        ("JCL - P(both) %", round(result.jcl * pct, 1)),
        ("Quadrant: on time AND on cost %", round(result.q_both * pct, 1)),
        ("Quadrant: on time, over cost %", round(result.q_date_only * pct, 1)),
        ("Quadrant: late, on cost %", round(result.q_cost_only * pct, 1)),
        ("Quadrant: late AND over cost %", round(result.q_neither * pct, 1)),
        ("EAC P10", result.cost_p10),
        ("EAC P50", result.cost_p50),
        ("EAC P80", result.cost_p80),
        ("EAC P90", result.cost_p90),
        ("EAC mean", result.cost_mean),
        ("EAC std deviation", result.cost_std),
        ("Sunk (actuals + completed finals)", result.sunk_total),
        ("Remaining budget - time-independent", result.remaining_ti_total),
        ("Remaining budget - time-dependent", result.remaining_td_total),
        ("Time-dependent share (tau) %", round(result.td_share * pct, 1)),
        (
            "Cost-estimating uncertainty",
            "on" if result.cost_uncertainty_on else "off (duration-driven cost only)",
        ),
    )
    headline = Table("JCL - joint cost & schedule confidence", ("Measure", "Value"), headline_rows)
    frontier = Table(
        f"JCL frontier (P{round(result.confidence * pct):g})",
        ("Finish on/before", "Minimum EAC target achieving the confidence jointly"),
        tuple((d, c) for d, c in result.frontier),
    )
    sample = Table(
        "JCL joint sample",
        ("Iteration finish date", "Iteration EAC"),
        tuple((d, c) for d, c in result.points),
    )
    return (headline, frontier, sample)


def _groups_field_options(fields: Sequence[str], selected: str) -> str:
    """``<option>`` list of the given selectable fields with one pre-selected."""
    opts = ['<option value="">(field…)</option>']
    for f in fields:
        sel = " selected" if f == selected else ""
        opts.append(f'<option value="{_e(f)}"{sel}>{_e(f)}</option>')
    return "".join(opts)


def _groups_form(
    versions: list[tuple[str, Schedule]],
    version_key: str,
    sch: Schedule,
    criteria: list[Criterion],
    breakdown: str,
) -> str:
    """The scope controls: filter rows (applied session-wide to every file), a preview-version
    picker, and a breakdown field. Field options are the union across all loaded files."""
    fields = sorted(available_fields_union([s for _, s in versions]), key=str.casefold)  # A-Z menu
    vsel = ""
    if len(versions) > 1:
        vopts = "".join(
            f'<option value="{_e(k)}"{" selected" if k == version_key else ""}>'
            f"{_e(s.source_file or s.name)}</option>"
            for k, s in versions
        )
        vsel = f"<label>Preview file: <select name=version>{vopts}</select></label> "
    # MAX_FIELDS filter rows, each a pair of simple alphabetical dropdowns (operator 2026-07-17,
    # replacing the MS-Project checkbox popup): a FIELD <select> and a VALUE <select>. The value
    # options are the field's distinct values (A-Z, union across files - the same source as
    # /api/group-values); groups.js repopulates the value menu when the field or preview version
    # changes. Server-rendered so the current selection round-trips and it works without JS.
    rows = []
    all_schedules = [s for _, s in versions]
    for i in range(MAX_FIELDS):
        f, v = criteria[i] if i < len(criteria) else ("", "")
        selected = _criterion_value_list(v)
        sel_val = selected[0] if selected else ""  # single-value dropdown
        data_sel = _e(json.dumps(selected))
        value_opts = ['<option value="">(any value)</option>']
        if f:
            for x in distinct_values(all_schedules, f):
                sv = " selected" if x == sel_val else ""
                value_opts.append(f'<option value="{_e(x)}"{sv}>{_e(x)}</option>')
        valsel = (
            f'<select name="value{i}" class=gf-valsel aria-label="Filter value">'
            f"{''.join(value_opts)}</select>"
        )
        rows.append(
            f'<div class=group-row data-row="{i}" data-selected="{data_sel}">'
            f'<select name=field class=gf-field aria-label="Filter field">{_groups_field_options(fields, f)}</select> '
            f"{valsel}</div>"
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
<p class=muted style="margin:.3em 0 0">Pick a field (standard or custom, e.g. <b>CA-WBS</b>) from the
alphabetical menu, then choose a <b>value</b> from its dropdown. <b>Apply</b> makes it the session-wide
scope &mdash; <b>every</b> metric on <b>every</b> page, for <b>every</b> loaded file, then runs over the
matching activities until you clear it. Combine up to {MAX_FIELDS} fields (AND). <b>Break down by</b> a
field to score each of its values separately (one BEI per group) on the preview file below.</p></div>
<script src="/static/groups.js"></script>"""


def _groups_breakdown_table(sub: Schedule, field: str, *, prov: str = "") -> str:
    """One row per distinct value of ``field`` in ``sub`` — population, % complete, and BEI.
    ``prov`` is the preview FILE's chip (codex-review round): the enlarged overlay hides the
    page's file picker, so the pivot must attribute its own source like the scorecard preview
    beside it. The no-values branch is a notice and stays bare."""
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
        total = len(tasks)
        complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
        bei = compute_bei(group)
        bei_cell = f"{round(bei.value, 2)}" if bei.population else "<span class=muted>—</span>"
        # ADR-0343 / Law 2 (ADR-0306 sweep row 3, settled by rendering the page). ``group_values``
        # scans EVERY task, summaries included, so a value carried only by rollup rows — WBS "0",
        # Activity Type "Summary" (19 activities on both goldens) — reaches here with an EMPTY
        # non-summary population. The old ``or 1`` put a fabricated denominator under a numerator
        # that is also 0 and rendered "0%", i.e. "nothing in this group is complete", beside a BEI
        # cell already reading "—" for that same empty population. Measured: 19 of 145 WBS rows and
        # 1 of 2 Activity Type rows on each golden. An empty population is NOT_APPLICABLE — the
        # rule ``engine/metrics/dcma14.py`` already applies to its own denominators.
        pct_cell = f"{100.0 * complete / total:.0f}%" if total else "<span class=muted>—</span>"
        rows.append(
            f"<tr><td>{_e(value)}</td><td class=num>{len(uids)}</td>"
            f"<td class=num>{pct_cell}</td>"
            f"<td class=num>{bei_cell} <span class=muted>({bei.count}/{bei.population})</span></td></tr>"
        )
    more = (
        f"<p class=muted>Showing the first {limit} of {len(groups)} values.</p>"
        if len(groups) > limit
        else ""
    )
    # rank 12 (ADR-0327): the populated pivot wears the contract head (h3 → the panel-anatomy
    # h2; the pinned assertions match the TEXT, which is unchanged) + ⛶. No ⤓ — no export
    # covers this pivot (and it truncates at 200 values, so a partial export would also lie).
    return (
        f"<div class=panel>"
        f"{_panel_head(f'Breakdown by {_e(field)} &mdash; {len(groups)} value(s)', tools=_shell_tools(), prov=prov)}"
        "<p class=muted>One row per distinct value of the chosen field within the current "
        "scope: activity count, completion, and the value's own BEI (baseline throughput).</p>"
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


def _saved_group_table(sch: Schedule, group: SavedGroup, *, prov: str = "") -> str:
    """The active saved group realized on the preview file: one row per bucket (in the group's
    own order), with the bucket's activity count and completion split. Presentation only.
    ``prov`` is the preview FILE's chip (codex-review round) — same rationale as the
    breakdown pivot: an enlarged overlay must keep its own source attribution."""
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
        f"<div class=panel>"
        f"{_panel_head(f'Grouped preview — {_e(group.display_name)}', tools=_shell_tools(), prov=prov)}"
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
    file. ``applied`` marks whether ``criteria`` is the live session scope (vs a URL preview).

    Panel contract (rank 12 toolbar sweep, ADR-0327): the data-visual panels (the Active-scope
    reach table, the preview scorecard, the breakdown and saved-group pivots) wear the head
    strip + ⛶ ENLARGE + a provenance chip. **No panel carries ⤓ EXCEL** — no existing export
    covers what these panels draw, and the preview scorecard can show an UNAPPLIED URL-preview
    scope while every export route reads the APPLIED session scope, so a pinned URL could hand
    the operator different figures than the panel shows (the round-10 live-state defect class).
    The filter-builder form and the status-notice Active-scope branches are not data visuals —
    no toolbar. No ▦ DATA: each panel's table IS its data (the home-shell precedent)."""
    form = _groups_form(versions, version_key, sch, criteria, breakdown)
    sub = filter_schedule(sch, criteria) if criteria else sch
    series_prov = _series_prov_chip([s for _k, s in versions])

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
            f"<div class=panel>"
            f"{_panel_head('Active scope', tools=_shell_tools(), prov=series_prov)}"
            f"<p>{chips}</p>"
            f"<p class=muted>{live}<b>every metric on every page</b>, for all loaded files "
            "(logical AND across rows).</p>"
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
        # ADR-0354 migration report: when this filter compares a DURATION against a literal or
        # prompt, show how the corrected (MPXJ-conformant) duration semantics moved its
        # population vs the retired hard-coded 480-minute table — the operator sees the shift
        # instead of silently inheriting it. Version-invariant filters render no note.
        mig_note = ""
        # RAW answers — the delta coerces them under EACH evaluator version internally, so
        # prompt-only population movement surfaces too (ADR-0355, Codex C2)
        delta = selection_migration_delta(sch, saved, st.saved_filter_prompts)
        if delta is not None and set(delta[0]) != set(delta[1]):
            v1_n, v2_n = len(delta[0]), len(delta[1])
            mig_note = (
                f"<p class=muted><b>Duration semantics corrected (evaluator v{EVALUATOR_VERSION}, "
                f"ADR-0354):</b> in the preview file this filter now selects <b>{v2_n}</b> "
                f"activities; the retired 480-minute-day reading selected {v1_n}. Elapsed "
                f"literals (“2.0ed”) now measure wall-clock time, and day/week/month/"
                f"year literals use this file's own calendar scale.</p>"
            )
        summary = (
            f"<div class=panel><h2>Active scope</h2><p>Saved filter "
            f"<b>{_e(saved.display_name)}</b> "
            f'<span class="dp-chip">{_e(_criteria_text(saved.criteria))}</span></p>'
            f"<p class=muted>{reach}</p>{mig_note}</div>"
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
            f"<div class=panel>"
            f"{_panel_head(f'Preview &mdash; metric scorecard for {preview_name}', tools=_shell_tools(), prov=_prov_chip(sch))}"
            f"<p class=muted>The same scope drives this file's full report and every other page.</p>"
            f"{cards}{table}</div>"
        )

    breakdown_html = (
        _groups_breakdown_table(sub, breakdown, prov=_prov_chip(sch))
        if breakdown and breakdown in available_fields(sch)
        else ""
    )
    # the session-wide SAVED group realized on the (scoped) preview file — presentation only
    group_html = ""
    if st is not None and st.active_saved_group is not None:
        group_html = _saved_group_table(st.scope(sch), st.active_saved_group, prov=_prov_chip(sch))
    tip = _user_tip(
        "Build a filter here and <b>Apply to all pages</b> to scope <b>every</b> metric on "
        "<b>every</b> page across all loaded files at once. Rows are AND-ed together "
        "(one value per field)."
    )
    _all = len(non_summary(sch))
    _sel = len(non_summary(sub))
    if criteria:
        _head = (
            f"This filter selects {_sel} of {_all} activities in the preview file."
            if _sel
            else f"This filter selects NO activities out of {_all} in the preview file."
        )
        _lede = (
            "Applied to every page and every loaded file &mdash; the scope below is live."
            if applied
            else "A preview only. <b>Apply to all pages</b> to make it the session scope."
        )
    else:
        _head = f"No filter is active &mdash; every page sees all {_all} activities."
        _lede = (
            "Build a filter above to scope every metric, path and forecast on every page, across "
            "all loaded files at once."
        )
    body = (
        _utility_takeaway(_head, _lede)
        + tip
        + form
        + summary
        + group_html
        + scorecard
        + breakdown_html
    )
    # the include rides ONLY a render that actually carries a contract control (the r11 law:
    # a script with nothing to drive is a dead promise — e.g. a summaries-only preview file
    # renders notice panels with no toolbar at all)
    if "data-sf-" in body:
        body += '\n<script src="/static/panelkit.js"></script>'
    return body


def _dashboard_data(st: SessionState) -> dict[str, object]:
    """Per-loaded-schedule health snapshot for the Dashboard cards: status mix, critical
    exposure, computed finish vs baseline, and the DCMA-14 verdicts. Reads the lightweight card
    tier (:meth:`SessionState.dashboard_core_for`, ADR-0281) — the three engine figures the card
    needs, never a full analysis — so a many-version portfolio renders (and refreshes) without
    LRU-thrashing the analysis cache; an unschedulable file degrades to a flagged card."""
    cards: list[dict[str, object]] = []
    gen = st.wipe_gen  # ADR-0291/0263: cards built for THIS epoch only (see dashboard_card_store)
    # the home dashboard is the session MANIFEST: one self-contained card per loaded file, every
    # Project, excluded versions included — nothing here blends files (ADR-0258)
    for key, sch in st.all_versions():  # earliest -> latest data date
        # ADR-0291: the whole per-version projection below is deterministic for a given
        # (key, scope-epoch), so a warm refresh serves it from the memo and re-derives NOTHING.
        # Previously `scope()` rebuilt a scoped Schedule and `non_summary()` / activity-makeup /
        # the status-UID partition ran again for every card on every refresh — ~3.6 ms per version
        # even with the ADR-0281 card tier fully warm (measured: 30 versions = 117 ms of pure
        # re-derivation). The cached value IS the finished card, so the payload is byte-identical.
        memo = st.dashboard_card_cached(key, sch)
        if memo is not None:
            cards.append(memo)
            continue
        scoped = st.scope(sch)  # the active filter applies to the dashboard cards too
        card: dict[str, object] = {
            "key": key,
            "name": sch.name,
            "source_file": sch.source_file,
            # OR-01 (ADR-0321): the two per-file fields the card was missing — Site / Company
            # (the source header, None when the source carried none) and the effective schedule
            # margin from the SAME cached summary tier the Portfolio row reads (st.summary_for —
            # cheap, memoised, never a full analysis; None when unsolvable or n/a, never 0).
            # Both ride the memoised card, so a warm refresh still re-derives nothing.
            "site": sch.company or None,
            "margin_days": st.summary_for(key, sch).effective_margin_days,
            "activities": len(non_summary(scoped)),
            "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        }
        try:
            core = st.dashboard_core_for(key, sch)
        except CPMError:
            card["solvable"] = False
            st.dashboard_card_store(key, sch, card, gen)  # unsolvable cards cache too
            cards.append(card)
            continue
        makeup = compute_activity_makeup(scoped)
        total = makeup.complete + makeup.in_progress + makeup.planned
        # ADR-0296: the card no longer ships the per-segment UID arrays (measured 87.6% of the
        # whole /api/dashboard payload — data only ever read on a click). The status bar marks
        # each segment with its NAME and the drill resolves the set on demand via `_drill_uid_set`
        # against THIS card's file (ADR-0295), using the same predicates `compute_activity_makeup`
        # used — so the drill rows are byte-identical, just no longer pre-shipped.
        cpm_finish = offset_to_datetime(
            scoped.project_start, core.project_finish, scoped.calendar
        ).date()
        baseline_dates = [
            t.baseline_finish for t in non_summary(scoped) if t.baseline_finish is not None
        ]
        baseline_finish = max(baseline_dates).date() if baseline_dates else None
        card.update(
            {
                "solvable": True,
                "status_mix": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                },
                "percent_complete": round(100 * makeup.complete / total, 1) if total else 0.0,
                "critical_count": core.critical_count,
                "critical_pct": round(core.critical_pct, 1),
                "cpm_finish": cpm_finish.isoformat(),
                "baseline_finish": baseline_finish.isoformat() if baseline_finish else None,
                # positive = computed finish later than baseline (a slip)
                "finish_delta_days": (cpm_finish - baseline_finish).days
                if baseline_finish
                else None,
                "dcma": [
                    {"id": mid, "name": nm, "status": status} for mid, nm, status in core.dcma
                ],
            }
        )
        st.dashboard_card_store(key, sch, card, gen)
        cards.append(card)
    return {"cards": cards}


@contextlib.asynccontextmanager
async def _cui_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Clear the on-disk CUI cache as the ASGI app is torn down (ADR-0335).

    This is the hook that covers **SIGTERM**, and it is the only one that does. Measured, with a
    real server in a subprocess: uvicorn does handle SIGTERM gracefully, but ``capture_signals``
    restores the original handler and then re-raises the signal it captured, so the process dies
    of the default SIGTERM disposition *before* ``serve()`` returns — ``launcher.main``'s
    ``finally`` and the ``atexit`` backstop both never run (exit ``-15``, no hooks). SIGINT
    escapes that fate only because ``serve()`` deliberately suppresses ``KeyboardInterrupt``.

    | exit | lifespan | `finally` | `atexit` |
    | --- | --- | --- | --- |
    | Quit / `POST /api/shutdown` / watchdog / SIGINT | ✓ | ✓ | ✓ |
    | **SIGTERM** (logout, `kill`, system shutdown) | **✓** | ✗ | ✗ |
    | SIGKILL / `TerminateProcess` (Task Manager) | ✗ | ✗ | ✗ — see below |

    The SIGKILL row is the one no in-process hook can ever cover, and since ADR-0336 it is handled
    from the other end: the run marker a write leaves in the cache is still there at the next
    launch, which reads it as proof the previous run never reached a clear and empties the cache
    before doing anything else. :meth:`ScheduleCache.prune` remains the belt for what that does not
    reach — a cache written by a build older than the marker.

    Without this, an operator on macOS or Linux who simply logs out or shuts the machine down —
    a normal way to finish for the day — left the whole parsed-schedule cache on disk. Nothing
    is awaited before the clear: on a double Ctrl+C uvicorn sets ``force_exit`` and skips the
    ASGI shutdown event, and this body then runs only via task cancellation.
    """
    try:
        yield
    finally:
        cache = get_default_cache()
        cache.seal()  # the app is going away; nothing may write to disk from here on
        cache.clear()


def _trigger_shutdown(app: FastAPI) -> None:
    """Request a graceful server stop, once (idempotent). No-op if no server is wired.

    ADR-0335: a stop is also when the on-disk CUI cache (parsed schedule content + derived
    metrics) leaves the disk. Every graceful exit funnels through here — the in-page Quit
    control, ``POST /api/shutdown`` (including the stand-down a new launcher sends its
    predecessor, ADR-0334), and the browser-gone watchdog — so this is the one place that covers
    them all. ``launcher.main`` clears again in its ``finally`` and registers an ``atexit``
    backstop; this site is what covers ``web.app.run()``/``serve()`` used without the launcher.

    Order matters, and all three steps are deliberate:

    1. **Seal first.** uvicorn keeps serving until in-flight requests drain, so an import that
       started before Quit finishes *after* this clear and writes the schedule it just parsed
       back to disk (measured). ADR-0263's ``wipe_gen`` does not cover a shutdown — only
       ``/session/wipe`` bumps it. Sealing is instantaneous and closes that window for good.
    2. **Then request the stop**, so the listening socket starts closing immediately: a
       predecessor being stood down has only ``launcher._HANDOVER_TIMEOUT`` seconds to release
       the port before the replacement launch refuses to start.
    3. **Then clear**, off the critical path.
    """
    if app.state.shutting_down:
        return
    app.state.shutting_down = True
    cache = get_default_cache()
    cache.seal()
    callback = app.state.request_shutdown
    if callback is not None:
        callback()
    cache.clear()


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
