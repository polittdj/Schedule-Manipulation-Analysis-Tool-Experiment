"""Shared month-axis primitives — calendar-month bucketing for the curve views.

The bow-wave (``engine/bow_wave.py``) and the finish/slippage month curves
(``engine/month_curves.py``) both bucket dates into calendar months on a shared
integer axis. These three primitives are the common vocabulary:

* :func:`month_index` — a date's month as a single orderable integer (year*12 + month-1);
* :func:`month_label` — that integer back to the deck's ``"Mon-YY"`` label;
* :func:`bucket` — count a list of dates into ``n`` month buckets starting at ``lo``.

The complex axis-window / cap logic stays with each caller (the bow-wave clamps around
status dates with a CEI period that must never be shed; the month curves span the full
data range capped oldest-first) — only the primitives are shared.
"""

from __future__ import annotations

import datetime as dt

_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month_index(d: dt.datetime) -> int:
    """A date's month as a single orderable integer (year*12 + month-1)."""
    return d.year * 12 + (d.month - 1)


def month_label(ym: int) -> str:
    """Render a month integer as the deck's ``"Mon-YY"`` label (e.g. ``"Mar-27"``)."""
    year, month = divmod(ym, 12)
    return f"{_MONTH_ABBR[month]}-{year % 100:02d}"


def bucket(dates: list[dt.datetime], lo: int, n: int) -> tuple[int, ...]:
    """Count ``dates`` into ``n`` month buckets, bucket 0 = month ``lo``.

    Dates outside the ``[lo, lo+n)`` window are dropped (the axis is bounded; an
    outlier date can't extend or explode it).
    """
    counts = [0] * n
    for d in dates:
        i = month_index(d) - lo
        if 0 <= i < n:
            counts[i] += 1
    return tuple(counts)
