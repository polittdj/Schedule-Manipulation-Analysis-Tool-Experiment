"""Units and presentation-boundary formatting (global rules §3, RTM U1-U3).

The two unit rules every module obeys:

* **Durations / floats / lags are stored internally in integer working minutes**
  (``480`` working minutes == one 8-hour working day -- the same axis Acumen Fuse
  and the prior reference build use, and the basis for the DCMA "> 44 working
  days" thresholds, ``44 * 480 == 21120`` minutes). Integer minutes are exact, so
  no binary-float drift can accumulate in the engine.
* **Conversion to days happens only at the presentation boundary**, here, with
  **deterministic decimal rounding** (:class:`decimal.Decimal` + ``ROUND_HALF_UP``)
  -- never plain ``float`` division. ``minutes / 480.0`` would reintroduce the very
  binary-float drift U3 forbids; ``Decimal`` makes every rendered value reproducible
  bit-for-bit, which matters in a forensic / testimony context.

Formatting helpers render the two display conventions §3 fixes:

* durations as ``"<n> day(s)"`` (pluralised; integer when whole) -- U1, and
* percentages always carrying their ``%`` sign, with explicit ``+`` available for
  signed deltas/variances -- U2.

Nothing here imports the model layer, so the model modules may depend on it.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

#: Working minutes in one standard 8-hour working day. The canonical duration axis
#: (matches Acumen Fuse and the DCMA "44 working days" == ``44 * 480`` threshold).
#: A non-8-hour calendar carries its own ``working_minutes_per_day`` and is passed
#: explicitly to the converters below.
MINUTES_PER_DAY: int = 480

#: Default number of decimal places when rendering a day quantity.
_DAY_PLACES: int = 2

Number = Decimal | int | float


def _to_decimal(value: Number) -> Decimal:
    """Coerce an int/float/Decimal to an exact :class:`Decimal`.

    Floats are routed through ``str`` so that e.g. ``0.1`` becomes ``Decimal("0.1")``
    rather than the binary-noise expansion ``Decimal(0.1)`` would produce.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):  # bool is an int subclass; reject to avoid surprises
        raise TypeError("bool is not a valid quantity")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    raise TypeError(f"unsupported quantity type: {type(value)!r}")


def minutes_to_days(
    minutes: Number,
    *,
    places: int = _DAY_PLACES,
    minutes_per_day: int = MINUTES_PER_DAY,
) -> Decimal:
    """Convert working ``minutes`` to working days, deterministically rounded.

    Returns a :class:`Decimal` quantised to ``places`` decimal places with
    ``ROUND_HALF_UP`` -- the same inputs always yield the same value, with no
    binary-float drift (U3). ``minutes_per_day`` lets a non-8-hour calendar convert
    on its own axis.
    """
    if minutes_per_day <= 0:
        raise ValueError("minutes_per_day must be positive")
    if places < 0:
        raise ValueError("places must be non-negative")
    quantum = Decimal(1).scaleb(-places)  # e.g. places=2 -> Decimal("0.01")
    return (_to_decimal(minutes) / Decimal(minutes_per_day)).quantize(
        quantum, rounding=ROUND_HALF_UP
    )


def days_to_minutes(days: Number, *, minutes_per_day: int = MINUTES_PER_DAY) -> int:
    """Convert a day quantity to whole working minutes (``ROUND_HALF_UP``).

    Inverse of :func:`minutes_to_days` for importers that receive durations in days.
    """
    if minutes_per_day <= 0:
        raise ValueError("minutes_per_day must be positive")
    minutes = (_to_decimal(days) * Decimal(minutes_per_day)).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return int(minutes)


def _render_quantity(value: Number, *, signed: bool) -> tuple[str, bool]:
    """Render a numeric quantity to a sign-aware string.

    Returns ``(text, abs_is_one)``. Whole values render without a decimal point;
    fractional values keep their significant decimals with trailing zeros stripped.
    A ``+`` is prepended only when ``signed`` is set and the value is strictly
    positive (zero is never signed; negatives carry their intrinsic ``-``).
    """
    d = _to_decimal(value)
    if d == d.to_integral_value():
        i = int(d)
        text = f"{i:+d}" if (signed and i != 0) else f"{i}"
        return text, abs(i) == 1
    # Fixed-point (never scientific) string, trailing zeros trimmed: 2.50 -> "2.5".
    text = format(d, "f").rstrip("0").rstrip(".")
    trimmed = Decimal(text)
    if signed and trimmed > 0:
        text = f"+{text}"
    return text, abs(trimmed) == 1


def format_days(value: Number | None, *, signed: bool = False) -> str:
    """Render a *day* quantity as ``"<n> day(s)"`` (U1).

    ``None`` -> ``"n/a"``; whole values are integers (``"2 days"``, ``"1 day"``,
    ``"0 days"``); fractional values keep their decimals (``"2.5 days"``); ``signed``
    prepends ``+`` to positive values (``"+2 days"``). Pluralisation follows the
    magnitude (singular only when it is exactly one day).
    """
    if value is None:
        return "n/a"
    text, abs_is_one = _render_quantity(value, signed=signed)
    unit = "day" if abs_is_one else "days"
    return f"{text} {unit}"


def format_signed_days(value: Number | None) -> str:
    """:func:`format_days` with an explicit sign -- for deltas/variances."""
    return format_days(value, signed=True)


def format_minutes_as_days(
    minutes: Number | None,
    *,
    signed: bool = False,
    places: int = _DAY_PLACES,
    minutes_per_day: int = MINUTES_PER_DAY,
) -> str:
    """Convert working ``minutes`` to days and render as ``"<n> day(s)"``.

    The one-call presentation-boundary helper: deterministic conversion (U3) +
    day formatting (U1). ``None`` -> ``"n/a"``.
    """
    if minutes is None:
        return "n/a"
    days = minutes_to_days(minutes, places=places, minutes_per_day=minutes_per_day)
    return format_days(days, signed=signed)


def format_percent(value: Number | None, *, signed: bool = False) -> str:
    """Render a *percentage* value (already in percent units) as ``"<n>%"`` (U2).

    ``format_percent(100)`` -> ``"100%"``; ``format_percent(3.17)`` -> ``"3.17%"``;
    ``None`` -> ``"n/a"``. Negatives carry their ``-``; ``signed`` additionally
    prepends ``+`` to positive values (``"+5%"``). The ``%`` sign is always present,
    satisfying §3 ("percentages render with the sign, e.g. 100%").
    """
    if value is None:
        return "n/a"
    text, _ = _render_quantity(value, signed=signed)
    return f"{text}%"


def format_signed_percent(value: Number | None) -> str:
    """:func:`format_percent` with an explicit ``+`` on positive values."""
    return format_percent(value, signed=True)


def ratio_to_percent(ratio: Number, *, places: int = _DAY_PLACES) -> Decimal:
    """Convert a ``[0, 1]``-style ratio to a percentage number, deterministically.

    ``0.5`` -> ``Decimal("50.00")``. Use with :func:`format_percent` to render a
    ratio (e.g. a computed metric fraction) with its sign.
    """
    if places < 0:
        raise ValueError("places must be non-negative")
    quantum = Decimal(1).scaleb(-places)
    return (_to_decimal(ratio) * Decimal(100)).quantize(quantum, rounding=ROUND_HALF_UP)
