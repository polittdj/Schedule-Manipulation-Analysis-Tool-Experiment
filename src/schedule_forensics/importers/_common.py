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


class ImporterError(ValueError):
    """A source file could not be parsed into a valid :class:`Schedule`.

    Subclasses :class:`ValueError`; importers wrap lower-level parse failures and
    pydantic ``ValidationError`` in this type so callers get one clean, CUI-safe
    contract (the message names *what* is wrong, never the file's contents).
    """


#: Both MS Project and P6 write "no date" as a pre-1985 sentinel (year 0/1, or a
#: 1984 placeholder). A parsed datetime before this is treated as absent.
_MIN_REAL_YEAR = 1985

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
    return int((hours * _MINUTES_PER_HOUR).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_float(value: str | None) -> float | None:
    """Parse an optional decimal number; ``None``/empty → ``None`` (never 0)."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(Decimal(text))
    except InvalidOperation as exc:
        raise ImporterError(f"unparseable number: {value!r}") from exc


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
