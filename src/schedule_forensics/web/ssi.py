"""The SSI run machinery - the /api/sra/ssi data builder, the factor grid rows, and the
setup Save/Load (dict + apply + vintage warning + the schedule's own stored SRA fields).

Monolith split, phase 3 slice 7 (ADR-0365), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour
(the ``/api/sra/ssi``, ``/api/sra/grid``, ``/sra/ssi/save`` + ``/sra/ssi/load`` routes'
builders): 11 names / 576 lines whose external referrers are all ``create_app`` routes,
which import downward and stay put. The census's ``_ssi_panel`` (235 lines) is NOT here -
its sole referrer is ``_sra_body``, so it is /sra page family and moves when that family
does; same for ``_ssi_export_tables`` (``_sra_report_blocks`` + the sra export routes).
Three 2-family names descended into ``web/components.py`` instead of moving here
(``_REMAIN_DAYS_DP``, ``_affected_avg_remaining_days``, ``_ssi_matrix_counts``): each is
needed by a mover AND by an sra-family member that stays, and a symbol an extracted module
needs must live at or below that module's layer (the ADR-0351 rule - the FIRST slice of a
pair forces the descent). ``_ssi_three_point`` (7 route families), ``_correlation_spec``
(6) and ``_MAX_SETUP_BYTES`` (handler-only, the upload-cap group) stay in ``app.py`` -
shared route machinery no page owns.

Layering: ``app`` -> ``ssi`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import contextlib
import hashlib
from typing import cast

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.sra import (
    BranchPlan,
    ConditionalBranch,
    ProbabilisticBranch,
    RiskFactorTable,
    SSIResult,
    _is_completed,
    factor_to_bc_wc,
)
from schedule_forensics.engine.sra_conclusions import conclusions_as_dicts, conclusions_from_ssi
from schedule_forensics.importers._common import iso_duration_to_minutes
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.components import (
    _affected_avg_remaining_days,
    _sra_selected,
    _ssi_matrix_counts,
)
from schedule_forensics.web.state import SessionState, UnifiedRisk, _activity_rows

_SRA_FACTOR_FIELD = "SRA Risk Ranking Factors"
_SRA_BC_FIELD = "Best Case Duration"
_SRA_WC_FIELD = "Worst Case Duration"


def _file_stored_sra_inputs(sch: Schedule) -> tuple[dict[int, int], dict[int, tuple[int, int]]]:
    """The schedule's OWN stored SSI inputs, read verbatim (ADR-0356; Law 2: these are the very
    values SSI itself reads, so no derivation happens here).

    Factors come from the ``SRA Risk Ranking Factors`` custom field (1..5; 0/blank = none);
    Best/Worst pairs from ``Best Case Duration`` / ``Worst Case Duration`` when BOTH are
    present. Incomplete leaves only — a completed activity's duration is a recorded fact, not
    a forecast (ADR-0307). The root-caused SSI delta (ADR-0356) happened because the session
    could not read these fields at all: a stale setup was the only way to populate the grid,
    and it replayed a different vintage's factors onto an edited file, silently."""
    factors: dict[int, int] = {}
    bcwc: dict[int, tuple[int, int]] = {}
    for t in non_summary(sch):
        if _is_completed(t):
            continue
        fields = dict(t.custom_fields)
        raw_f = fields.get(_SRA_FACTOR_FIELD)
        if raw_f not in (None, ""):
            try:
                f = int(float(str(raw_f)))
            except (TypeError, ValueError):
                f = 0
            if 1 <= f <= 5:
                factors[t.unique_id] = f
        b = fields.get(_SRA_BC_FIELD)
        w = fields.get(_SRA_WC_FIELD)
        bm = iso_duration_to_minutes(b) if b else None
        wm = iso_duration_to_minutes(w) if w else None
        if bm is not None and wm is not None:
            bcwc[t.unique_id] = (bm, wm)
    return factors, bcwc


def _schedule_sra_fingerprint(sch: Schedule) -> dict[str, object]:
    """A compact identity of the schedule's SRA-input vintage, stamped into saved setups
    (ADR-0356). The hash covers the FILE's stored factors + Best/Worst pairs, so two versions
    of one schedule whose SRA fields changed get different fingerprints even at equal task
    counts."""
    factors, bcwc = _file_stored_sra_inputs(sch)
    canon = ";".join(
        f"{u}:{factors.get(u, 0)}:{bcwc.get(u, (0, 0))[0]}:{bcwc.get(u, (0, 0))[1]}"
        for u in sorted(set(factors) | set(bcwc))
    )
    return {
        "source_file": sch.source_file,
        "schedule_name": sch.name,
        "tasks": len(sch.tasks),
        "status_date": sch.status_date.isoformat() if sch.status_date else None,
        "stored_sra_hash": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
        "stored_factor_count": len(factors),
        "stored_bcwc_count": len(bcwc),
    }


def _setup_vintage_warning(st: SessionState, sch: Schedule, fingerprint: object) -> str | None:
    """The ADR-0356 mismatch warning: how the JUST-LOADED setup disagrees with the ACTIVE
    schedule's own stored SRA fields, with counts — or ``None`` when nothing disagrees.

    Runs against the live comparison regardless of whether the setup carries a fingerprint
    (a v3 setup has none but can still be stale); the fingerprint, when present and different,
    adds where the setup came from. The run will still use the SETUP's values — the warning
    exists so the operator chooses that knowingly instead of silently."""
    f_file, b_file = _file_stored_sra_inputs(sch)
    f_dis = sum(1 for u, f in st.sra_factors.items() if u in f_file and f_file[u] != f)
    f_missing = sum(1 for u in f_file if u not in st.sra_factors)
    b_dis = sum(1 for u, p in st.sra_bcwc.items() if u in b_file and b_file[u] != p)
    if not (f_dis or f_missing or b_dis):
        return None
    parts: list[str] = []
    if isinstance(fingerprint, dict):
        fp_now = _schedule_sra_fingerprint(sch)
        if fingerprint.get("stored_sra_hash") not in (None, fp_now["stored_sra_hash"]):
            src = (
                fingerprint.get("source_file") or fingerprint.get("schedule_name") or "another file"
            )
            parts.append(
                f"This setup was captured against a different vintage of the schedule ({src})."
            )
    detail: list[str] = []
    if f_dis:
        detail.append(f"{f_dis} factor(s) disagree with the file's stored Risk Ranking Factors")
    if f_missing:
        detail.append(f"{f_missing} file factor task(s) are absent from the setup")
    if b_dis:
        detail.append(f"{b_dis} Best/Worst pair(s) differ from the file's stored durations")
    parts.append(
        "Loaded values vs this schedule's own stored SRA fields: " + "; ".join(detail) + ". "
        "The run will use the LOADED values — use 'Load from schedule' to run the file's own."
    )
    return " ".join(parts)


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
        "sampling": result.sampling,
        # per-activity Criticality Index from this run (ADR-0272): the risk-critical Gantt tint's
        # source, also exposed here for API consumers (uid -> fraction of iterations critical).
        "criticality": [{"uid": u, "ci": round(ci, 4)} for u, ci in result.criticality],
        "correlation_matrix": {
            "applied": result.correlation_matrix_applied,
            "repaired": result.correlation_matrix_repaired,
            "min_eigenvalue": round(result.correlation_min_eigenvalue, 4),
            "frobenius_distance": round(result.correlation_frobenius_distance, 4),
        },
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
                # ADR-0308: False when every affected activity is complete, so the risk fired but
                # moved nothing — sra_ssi.js renders it as "inert (activity complete)"
                "applied": r.applied,
            }
            for r in result.risks
        ],
        "risk_matrix": _ssi_matrix_counts(result.risks, opportunity=False),
        "opportunity_matrix": _ssi_matrix_counts(result.risks, opportunity=True),
        # probabilistic-branch outcomes (ADR-0273): fired fraction, rework magnitude, finish impact,
        # and the inert flag (a branch whose FS tie was absent) — sra_ssi.js renders the table.
        "branches": [
            {
                "id": br.id,
                "name": br.name,
                "probability": round(br.probability * 100, 1),
                "applied": br.applied,
                "hits": br.hits,
                "fired_pct": round(br.fired_fraction * 100, 1),
                "mean_fragnet_days": br.mean_fragnet_days,
                "mean_delta_days": br.mean_delta_days,
            }
            for br in result.branches
        ],
        # conditional-branch outcomes (ADR-0274): which plan won how often + the mean finish delta of
        # falling to the contingency, and the inert flag — sra_ssi.js renders the table.
        "conditionals": [
            {
                "id": cs.id,
                "name": cs.name,
                "monitor_uid": cs.monitor_uid,
                "metric": cs.metric,
                "threshold_days": round(
                    cs.threshold_minutes / (sch.calendar.working_minutes_per_day or 480), 2
                ),
                "trip_when": cs.trip_when,
                "applied": cs.applied,
                "plan_a_name": cs.plan_a_name,
                "plan_b_name": cs.plan_b_name,
                "plan_a_pct": round(cs.plan_a_fraction * 100, 1),
                "plan_b_pct": round(cs.plan_b_fraction * 100, 1),
                "mean_a_days": cs.mean_a_finish_days,
                "mean_b_days": cs.mean_b_finish_days,
                "mean_delta_days": cs.mean_delta_days,
            }
            for cs in result.conditionals
        ],
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
        # a completed activity carries no Best/Worst spread (ADR-0307/0308), so the grid must not
        # SHOW one the simulation ignores, nor accept a new one
        completed = task is not None and _is_completed(task)
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
        if uid in st.sra_bcwc and mpd and not completed:
            bc_days = round(st.sra_bcwc[uid][0] / mpd, 1)
            wc_days = round(st.sra_bcwc[uid][1] / mpd, 1)
        row.update(
            {
                "remaining_days": rem_days,
                "factor": st.sra_factors.get(uid),
                "bc_days": bc_days,
                "wc_days": wc_days,
                "completed": completed,
                "has_risk": uid in risk_uids,
                "is_focus": uid == st.sra_focus_uid,
                "editable": editable,
                # the last SSI run's Criticality Index for this activity (ADR-0272), or None if no
                # run yet / the activity was absent — the Gantt bar tints by "how often critical".
                "criticality_index": st.sra_criticality.get(uid),
            }
        )
    return rows


_SSI_SETUP_VERSION = (
    # 2: + legacy triangular (low/ml/high) + per-activity overrides (whole setup)
    # 3: ADR-0307 corrected the Best Case (a % OF the ML, not a % to subtract), so every
    #    factor-derived Best/Worst stored by a version <= 2 setup carries the OLD inverted value.
    #    Loading one must NOT keep running the formula ADR-0307 fixed — see _apply_ssi_setup.
    # 4: ADR-0356 — the setup carries a schedule_fingerprint (the SRA-input vintage it was
    #    captured against), so loading it onto a changed schedule can say WHERE it came from.
    #    The stale-vs-file comparison itself runs on every load, fingerprint or not.
    4
)


def _ssi_setup_dict(st: SessionState) -> dict[str, object]:
    """The WHOLE SRA setup as a plain, versioned, JSON-serialisable dict (Save/Load + Excel) — both
    models: the SSI factor/BC-WC/risk inputs AND the legacy global triangular + per-activity
    overrides, so a load restores every model's inputs verbatim."""
    chosen = _sra_selected(st)
    return {
        "setup_version": _SSI_SETUP_VERSION,
        # ADR-0356: the SRA-input vintage this setup was captured against (None with no schedule)
        "schedule_fingerprint": None if chosen is None else _schedule_sra_fingerprint(chosen[1]),
        "focus_uid": st.sra_focus_uid,
        "occurrence_mode": st.sra_occurrence_mode,
        "use_risk_register": st.sra_use_risk_register,
        "correlation": st.sra_correlation,
        "sampling": st.sra_sampling,
        "lhs_centered": st.sra_lhs_centered,
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
        # probabilistic branches (ADR-0273) — durations in working minutes, restored verbatim
        "branches": [
            {
                "id": b.id,
                "name": b.name,
                "probability": b.probability,
                "after_uid": b.after_uid,
                "before_uid": b.before_uid,
                "low": b.low,
                "ml": b.ml,
                "high": b.high,
            }
            for b in st.sra_branches
        ],
        # conditional branches (ADR-0274) — durations/threshold in working minutes, restored verbatim
        "conditionals": [
            {
                "id": c.id,
                "name": c.name,
                "monitor_uid": c.monitor_uid,
                "metric": c.metric,
                "threshold_minutes": c.threshold_minutes,
                "trip_when": c.trip_when,
                "plan_a": {
                    "after_uid": c.plan_a.after_uid,
                    "before_uid": c.plan_a.before_uid,
                    "low": c.plan_a.low,
                    "ml": c.plan_a.ml,
                    "high": c.plan_a.high,
                    "name": c.plan_a.name,
                },
                "plan_b": {
                    "after_uid": c.plan_b.after_uid,
                    "before_uid": c.plan_b.before_uid,
                    "low": c.plan_b.low,
                    "ml": c.plan_b.ml,
                    "high": c.plan_b.high,
                    "name": c.plan_b.name,
                },
            }
            for c in st.sra_conditionals
        ],
    }


def _apply_ssi_setup(st: SessionState, data: dict[str, object]) -> None:
    """Repopulate the SSI SessionState from a saved setup dict, validating against the active
    schedule: unknown / summary UIDs are dropped, factors clamped 1..5, probabilities 0..1."""
    chosen = _sra_selected(st)
    by_uid: dict[int, Task] = {} if chosen is None else dict(chosen[1].tasks_by_id)
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
    st.sra_sampling = "lhs" if data.get("sampling") == "lhs" else "mc"
    st.sra_lhs_centered = bool(data.get("lhs_centered", False))
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
    # ADR-0308: a setup written before ADR-0307 stores Best/Worst values computed with the INVERTED
    # Best-Case formula, and _ssi_three_point gives a stored range precedence over factor_to_bc_wc —
    # so loading one silently re-runs the very bug ADR-0307 fixed (the committed reference setup
    # holds 783 such pairs, e.g. UID 427 factor 5 with BC 432 on ML 480 = the old 0.90*ML). A stored
    # entry does not record whether it was factor-derived or hand-typed, so on a pre-v3 setup we drop
    # exactly those whose uid ALSO carries a factor (they get recomputed correctly) and keep the rest.
    try:
        loaded_version = int(cast("int", data.get("setup_version") or 1))
    except (TypeError, ValueError):
        loaded_version = 1
    stale_factor_derived = loaded_version < 3
    bcwc: dict[int, tuple[int, int]] = {}
    raw_bcwc = data.get("bcwc_minutes")
    if isinstance(raw_bcwc, dict):
        for key, pair in raw_bcwc.items():
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            if stale_factor_derived and uid in factors:
                # recompute from the CORRECTED formula instead of trusting the stored value. The
                # run would be right either way (_ssi_three_point falls back to the factor when no
                # range is stored), but recomputing means the grid shows the corrected numbers and
                # the setup round-trips instead of reading blank until the operator re-runs auto-calc.
                task = by_uid.get(uid)
                if task is not None and not _is_completed(task):
                    rem_min = (
                        task.remaining_duration_minutes
                        if task.remaining_duration_minutes is not None
                        else task.duration_minutes
                    )
                    fixed_bc, _ml, fixed_wc = factor_to_bc_wc(
                        rem_min, factors[uid], RiskFactorTable(rows=st.sra_factor_rows)
                    )
                    bcwc[uid] = (fixed_bc, fixed_wc)
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
    # probabilistic branches (ADR-0273): restore verbatim (durations already in working minutes)
    branches: list[ProbabilisticBranch] = []
    bseq = 0
    raw_branches = data.get("branches")
    if isinstance(raw_branches, list):
        for item in raw_branches:
            if not isinstance(item, dict):
                continue
            with contextlib.suppress(TypeError, ValueError):
                a, bef = int(item["after_uid"]), int(item["before_uid"])
                lo = max(0, int(item.get("low", 0)))
                mid = max(lo, int(item.get("ml", lo)))
                hi = max(mid, int(item.get("high", mid)))
                bseq += 1
                branches.append(
                    # REGENERATE ids densely (B1..Bn) rather than trusting the saved id — a saved
                    # gap (e.g. only "B3" survives) would otherwise leave the counter below the
                    # highest suffix, so a later add could recreate an in-use id and collide the
                    # fragnet mapping. Dense ids keep `sra_branch_seq == len(branches)` collision-free.
                    ProbabilisticBranch(
                        id=f"B{bseq}",
                        name=str(item.get("name") or f"Branch {bseq}"),
                        probability=min(1.0, max(0.0, float(item.get("probability", 0.0)))),
                        after_uid=a,
                        before_uid=bef,
                        low=lo,
                        ml=mid,
                        high=hi,
                    )
                )
    st.sra_branches = branches
    st.sra_branch_seq = bseq
    # conditional branches (ADR-0274): restore verbatim (durations/threshold already in working
    # minutes), regenerating ids densely (C1..Cn) so `sra_conditional_seq == len` is collision-free
    # (the same Save/Load id-density guard as #8's probabilistic branches).
    conditionals: list[ConditionalBranch] = []
    cseq = 0
    raw_conditionals = data.get("conditionals")
    if isinstance(raw_conditionals, list):
        for item in raw_conditionals:
            if not isinstance(item, dict):
                continue
            pa = item.get("plan_a")
            pb = item.get("plan_b")
            if not (isinstance(pa, dict) and isinstance(pb, dict)):
                continue
            with contextlib.suppress(TypeError, ValueError, KeyError):
                a_lo = max(0, int(pa.get("low", 0)))
                a_mid = max(a_lo, int(pa.get("ml", a_lo)))
                a_hi = max(a_mid, int(pa.get("high", a_mid)))
                b_lo = max(0, int(pb.get("low", 0)))
                b_mid = max(b_lo, int(pb.get("ml", b_lo)))
                b_hi = max(b_mid, int(pb.get("high", b_mid)))
                metric = str(item.get("metric", "duration"))
                metric = metric if metric in ("duration", "finish") else "duration"
                trip = str(item.get("trip_when", "at_or_above"))
                trip = trip if trip in ("at_or_above", "below") else "at_or_above"
                cseq += 1
                conditionals.append(
                    ConditionalBranch(
                        id=f"C{cseq}",
                        name=str(item.get("name") or f"Contingency {cseq}"),
                        monitor_uid=int(item["monitor_uid"]),
                        metric=metric,
                        threshold_minutes=max(0, int(item.get("threshold_minutes", 0))),
                        plan_a=BranchPlan(
                            after_uid=int(pa["after_uid"]),
                            before_uid=int(pa["before_uid"]),
                            low=a_lo,
                            ml=a_mid,
                            high=a_hi,
                            name=str(pa.get("name") or "Plan A"),
                        ),
                        plan_b=BranchPlan(
                            after_uid=int(pb["after_uid"]),
                            before_uid=int(pb["before_uid"]),
                            low=b_lo,
                            ml=b_mid,
                            high=b_hi,
                            name=str(pb.get("name") or "Plan B"),
                        ),
                        trip_when=trip,
                    )
                )
    st.sra_conditionals = conditionals
    st.sra_conditional_seq = cseq
