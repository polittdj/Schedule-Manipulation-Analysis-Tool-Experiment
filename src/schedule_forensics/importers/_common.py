"""Shared importer utilities (M3): a loud error type + source-faithful parsing.

Both the MSPDI (MS Project XML) and XER (Primavera P6) importers convert the units
their source files record into the model's canonical axes:

* **Durations / lags → integer working minutes** (``480`` working minutes == one
  8-hour day; see :mod:`schedule_forensics.model.units`). MSPDI encodes spans as
  ISO-8601 ``PnDTnHnMnS``; XER encodes them as a decimal hour count. Both are
  converted with :class:`decimal.Decimal` + ``ROUND_HALF_UP`` so the same input
  always yields the same minute count (no binary-float drift — Law 2, fidelity).
* **Dates → :class:`datetime.datetime`** via ISO-8601, with the pre-1985 "not set"
  sentinel both tools write mapped to ``None`` (never a fabricated date).

A parse that cannot form a valid schedule raises :class:`ImporterError` — the model
is strict and closed, so malformed input fails loudly here rather than silently
dropping metadata.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from schedule_forensics.model.task import ConstraintType


class ImporterError(ValueError):
    """A source file could not be parsed into a valid :class:`Schedule`.

    Subclasses :class:`ValueError`; importers wrap lower-level parse failures and
    pydantic ``ValidationError`` in this type so callers get one clean, CUI-safe
    contract (the message names *what* is wrong, never the file's contents).
    """


#: Both MS Project and P6 write "no date" as a pre-1985 sentinel (year 0/1, or a
#: 1984 placeholder). A parsed datetime before this is treated as absent.
_MIN_REAL_YEAR = 1985

#: Constraints that require a date to be meaningful (and that the CPM engine acts on); a
#: real-world export sometimes carries one of these with the date cleared (a stale
#: leftover) — meaningless and unschedulable, so importers normalize it to ASAP. Shared
#: by the MSPDI and XER importers so the tolerance classes cannot drift apart.
DATE_REQUIRING_CONSTRAINTS = frozenset(
    {
        ConstraintType.SNET,
        ConstraintType.FNET,
        ConstraintType.SNLT,
        ConstraintType.FNLT,
        ConstraintType.MSO,
        ConstraintType.MFO,
    }
)

#: ISO-8601 duration grammar (``PnDTnHnMnS``); every component optional, decimals
#: allowed. MS Project task durations are almost always ``PT<h>H<m>M<s>S`` (working
#: hours); the ``D`` term is the calendar-day (24 h) component per ISO-8601.
_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)

_MINUTES_PER_HOUR = Decimal(60)
_MINUTES_PER_ISO_DAY = Decimal(24 * 60)  # ISO-8601 "D" is a calendar (24 h) day


def parse_datetime(value: str | None) -> dt.datetime | None:
    """Parse an ISO-8601 datetime; ``None`` for missing/empty/sentinel values.

    MSPDI (``2025-01-06T08:00:00``) and XER (``2025-01-06 08:00``) datetimes are
    both ISO-8601, so :func:`datetime.datetime.fromisoformat` parses either. An
    unparseable or pre-1985 value is the source's "not set" marker → ``None``
    (these optional fields legitimately carry junk/sentinels; structural problems
    are raised elsewhere, not here).
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.year < _MIN_REAL_YEAR:
        return None
    # some exports tag datetimes with an offset/Z; the working-time axis is wall-clock local,
    # and mixing aware + naive datetimes breaks comparisons downstream — keep the local time.
    return parsed.replace(tzinfo=None)


def _dec(group: str | None) -> Decimal:
    """A regex group (or ``None``) → exact :class:`Decimal` (``None``/empty → 0)."""
    return Decimal(group) if group else Decimal(0)


def iso_duration_to_minutes(value: str | None) -> int:
    """Convert an ISO-8601 ``PnDTnHnMnS`` span to whole working minutes.

    ``None``/empty → ``0`` (a 0-minute, milestone-style span). The span is summed
    in :class:`~decimal.Decimal` and rounded ``ROUND_HALF_UP`` for determinism.
    MS Project encodes *working* hours in the span (``PT16H0M0S`` == 16 working
    hours == 960 minutes == 2 working days at 480/day). A non-ISO string raises
    :class:`ImporterError` (loud — never a silent 0).
    """
    if value is None:
        return 0
    text = value.strip()
    if not text:
        return 0
    match = _ISO_DURATION_RE.match(text)
    if match is None:
        raise ImporterError(f"unparseable ISO-8601 duration: {value!r}")
    total = (
        _dec(match["days"]) * _MINUTES_PER_ISO_DAY
        + _dec(match["hours"]) * _MINUTES_PER_HOUR
        + _dec(match["minutes"])
        + _dec(match["seconds"]) / _MINUTES_PER_HOUR
    )
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def hours_to_minutes(value: str | None) -> int:
    """Convert a decimal hour count (XER ``*_hr_cnt``) to whole working minutes.

    ``None``/empty → ``0``. The sign is preserved (a negative ``lag_hr_cnt`` is a
    lead). Rounded ``ROUND_HALF_UP`` in :class:`~decimal.Decimal`. A non-numeric
    string raises :class:`ImporterError`.
    """
    if value is None:
        return 0
    text = value.strip()
    if not text:
        return 0
    try:
        hours = Decimal(text)
    except InvalidOperation as exc:
        raise ImporterError(f"unparseable hour count: {value!r}") from exc
    if not hours.is_finite():
        return 0  # "NaN"/"Infinity" parse as Decimals but are data noise — same as empty
    return int((hours * _MINUTES_PER_HOUR).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_float(value: str | None) -> float | None:
    """Parse an optional decimal number; ``None``/empty → ``None`` (never 0).

    ``"NaN"``/``"Infinity"`` are valid :class:`Decimal` constructions but poison
    every downstream sum/comparison — they are data noise and read as absent.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ImporterError(f"unparseable number: {value!r}") from exc
    return float(number) if number.is_finite() else None


def weekday_from_source(day: int) -> int | None:
    """MSPDI/XER day-of-week (``1``=Sunday … ``7``=Saturday) → ``date.weekday()``
    (Mon=0 … Sun=6). Out-of-range values are data noise → ``None``."""
    return (day + 5) % 7 if 1 <= day <= 7 else None


def clock_minutes(value: str | None) -> int | None:
    """A wall-clock time-of-day (``HH:MM`` or ``HH:MM:SS``) → minutes since midnight.

    ``None`` for absent/garbage values (calendar fields legitimately carry noise; a bad
    working-time span must not sink the file). Seconds are dropped — working-time grids
    are minute-resolution.
    """
    if value is None:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", value.strip())
    if match is None:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 24 or minutes > 59:
        return None
    return hours * 60 + minutes


def working_time_span(start: str | None, finish: str | None) -> tuple[int, int] | None:
    """One working-time block as ``(from, to)`` minutes-from-midnight, ``None`` when unusable.

    A finish of ``00:00`` with a later start is the sources' end-of-day midnight (24:00) —
    P6 and MS Project both write it for spans that run to midnight.
    """
    from_min = clock_minutes(start)
    to_min = clock_minutes(finish)
    if from_min is None or to_min is None:
        return None
    if to_min == 0 and from_min > 0:
        to_min = 24 * 60
    if to_min <= from_min:
        return None
    return (from_min, to_min)


def working_span_minutes(start: str | None, finish: str | None) -> int:
    """Length of one working-time span (``08:00``→``12:00`` = 240), 0 when unusable."""
    span = working_time_span(start, finish)
    return 0 if span is None else span[1] - span[0]


def dominant_day_minutes(day_totals: list[int]) -> int | None:
    """The most common positive per-day working-minute total (ties → the larger).

    The engine models one contiguous working block per day, so a calendar whose days
    differ (e.g. a half-day Friday) is represented by its dominant day length —
    deterministic and documented (ADR-0028). ``None`` when no day has positive minutes.
    """
    positives = [m for m in day_totals if m > 0]
    if not positives:
        return None
    counts: dict[int, int] = {}
    for m in positives:
        counts[m] = counts.get(m, 0) + 1
    return max(counts, key=lambda m: (counts[m], m))


#: P6 stores calendar exception dates as Excel serial day numbers (days since 1899-12-30).
_EXCEL_EPOCH = dt.date(1899, 12, 30)


def excel_serial_to_date(serial: int) -> dt.date | None:
    """An Excel serial day number → :class:`datetime.date`; ``None`` outside 1985..2200
    (the same "not set"/noise window as :func:`parse_datetime`)."""
    try:
        day = _EXCEL_EPOCH + dt.timedelta(days=serial)
    except OverflowError:
        return None
    return day if _MIN_REAL_YEAR <= day.year <= 2200 else None


def clamped_percent_or_none(value: str | None) -> float | None:
    """Optional percent clamped to 0..100; absent stays ``None`` (same noise class as
    :func:`parse_percent` — an out-of-range physical % must not sink the file)."""
    parsed = parse_float(value)
    return None if parsed is None else min(100.0, max(0.0, parsed))


def parse_percent(value: str | None) -> float:
    """Parse a percent value, clamped to ``0..100``; ``None``/empty → ``0.0``.

    Real exports occasionally carry out-of-range percents (tool quirks, P6 round-trips);
    they are data noise, not corruption — clamp to the valid range rather than reject the
    whole file (the model still bounds-checks ``0 <= pct <= 100`` as the backstop).
    """
    parsed = parse_float(value)
    if parsed is None:
        return 0.0
    return min(100.0, max(0.0, parsed))
