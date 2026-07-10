"""Per-exhibit CSV siblings — the EXACT rows each renderer consumed (auditability twin).

Stdlib ``csv``; deterministic ordering (payload order / the same instability sort the
renderers use); explicit empty string for None (a gap stays visibly a gap in the CSV too).
"""

from __future__ import annotations

import csv
import io

from schedule_forensics.exhibits.payload import ExhibitPayload
from schedule_forensics.exhibits.render_svg import ROW_CAP, _instability_order


def _emit(headers: list[str], rows: list[list[object]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(headers)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def csv_ex00(p: ExhibitPayload) -> str:
    return _emit(
        [
            "path",
            "sha256",
            "status_date",
            "recompute_delta_nonzero_task_count",
            "recompute_delta_max_abs_minutes",
        ],
        [
            [
                f.path,
                f.sha256,
                f.status_date,
                f.recompute_delta_nonzero_task_count,
                f.recompute_delta_max_abs_minutes,
            ]
            for f in p.manifest.files
        ],
    )


def _cell_rows(p: ExhibitPayload) -> list[list[object]]:
    order = _instability_order(p)[:ROW_CAP]
    pos = {uid: i for i, uid in enumerate(order)}
    cells = [c for c in p.cells if c.task_uid in pos]
    cells.sort(key=lambda c: (pos[c.task_uid], c.status_date))
    return [
        [
            c.task_uid,
            c.task_name,
            c.status_date,
            c.state,
            c.tf_band,
            c.total_float_minutes,
            c.remaining_duration_minutes,
            c.on_driving_tree,
            c.co_bound_by_constraint,
        ]
        for c in cells
    ]


def csv_ex01(p: ExhibitPayload) -> str:
    return _emit(
        [
            "task_uid",
            "task_name",
            "status_date",
            "state",
            "tf_band",
            "total_float_minutes",
            "remaining_duration_minutes",
            "on_driving_tree",
            "co_bound_by_constraint",
        ],
        _cell_rows(p),
    )


csv_ex02 = csv_ex01  # the float heatmap consumes exactly the same cell rows


def csv_ex03(p: ExhibitPayload) -> str:
    ups = {u.status_date: u for u in p.update_summaries}
    rows = []
    for t in p.transitions:
        u = ups.get(t.to_status_date)
        rows.append(
            [
                t.from_status_date,
                t.to_status_date,
                t.crosses_rebaseline,
                t.observed_churn,
                t.expected_churn,
                t.attributable_churn,
                u.logic_edits_count if u else None,
                u.constraint_edits_count if u else None,
                u.duration_edits_count if u else None,
            ]
        )
    return _emit(
        [
            "from_status_date",
            "to_status_date",
            "crosses_rebaseline",
            "observed_churn",
            "expected_churn",
            "attributable_churn",
            "logic_edits_count",
            "constraint_edits_count",
            "duration_edits_count",
        ],
        rows,
    )


def csv_ex04(p: ExhibitPayload) -> str:
    return _emit(
        ["status_date", "cic", "cic_null_reason", "driving_tree_incomplete", "incomplete_reason"],
        [
            [
                u.status_date,
                u.cic,
                u.cic_null_reason,
                u.driving_tree_incomplete,
                u.incomplete_reason,
            ]
            for u in p.update_summaries
        ],
    )


def csv_ex05(p: ExhibitPayload) -> str:
    rows = [
        [c.status_date, c.tf_band, c.task_uid]
        for c in p.cells
        if c.state not in ("COMPLETE", "ABSENT")
    ]
    rows.sort(key=lambda r: (str(r[0]), str(r[1]), int(str(r[2]))))
    return _emit(["status_date", "tf_band", "task_uid"], list(rows))


def csv_ex06(p: ExhibitPayload) -> str:
    ts = [t for t in p.task_summaries if t.weighted_instability is not None]
    ts.sort(key=lambda t: -(t.weighted_instability or 0.0))
    return _emit(
        [
            "task_uid",
            "task_name",
            "weighted_instability",
            "eci",
            "entropy_h",
            "mean_remaining_duration_minutes",
        ],
        [
            [
                t.task_uid,
                t.task_name,
                t.weighted_instability,
                t.eci,
                t.entropy_h,
                t.mean_remaining_duration_minutes,
            ]
            for t in ts[:15]
        ],
    )


def csv_ex07(p: ExhibitPayload) -> str:
    return _emit(
        ["from_status_date", "to_status_date", "edge_jaccard", "weighted_jaccard"],
        [
            [t.from_status_date, t.to_status_date, t.edge_jaccard, t.weighted_jaccard]
            for t in p.transitions
        ],
    )


def csv_ex08(p: ExhibitPayload) -> str:
    rows: list[list[object]] = []
    for t in p.transitions:
        for bm in t.band_migrations:
            rows.append(
                [t.from_status_date, t.to_status_date, bm.from_band, bm.to_band, bm.task_count]
            )
    return _emit(["from_status_date", "to_status_date", "from_band", "to_band", "task_count"], rows)


CSV_WRITERS = {
    "EX-00": csv_ex00,
    "EX-01": csv_ex01,
    "EX-02": csv_ex02,
    "EX-03": csv_ex03,
    "EX-04": csv_ex04,
    "EX-05": csv_ex05,
    "EX-06": csv_ex06,
    "EX-07": csv_ex07,
    "EX-08": csv_ex08,
}
