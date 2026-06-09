"""Units / presentation-boundary tests (§3, RTM U1-U3).

Covers deterministic minutes↔days conversion (no binary-float drift, U3), the
``"<n> day(s)"`` duration format (U1), and signed-percent formatting (U2).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from schedule_forensics.model import units


# --------------------------------------------------------------------------- #
# constants                                                                    #
# --------------------------------------------------------------------------- #
def test_minutes_per_day_is_canonical_eight_hour_day() -> None:
    assert units.MINUTES_PER_DAY == 480
    assert 44 * units.MINUTES_PER_DAY == 21120  # the DCMA "44 working days" threshold


# --------------------------------------------------------------------------- #
# minutes_to_days — deterministic decimal conversion (U3)                       #
# --------------------------------------------------------------------------- #
def test_minutes_to_days_whole_and_fractional() -> None:
    assert units.minutes_to_days(480) == Decimal("1.00")
    assert units.minutes_to_days(720) == Decimal("1.50")
    assert units.minutes_to_days(0) == Decimal("0.00")
    assert units.minutes_to_days(240) == Decimal("0.50")


def test_minutes_to_days_returns_decimal_not_float() -> None:
    result = units.minutes_to_days(720)
    assert isinstance(result, Decimal)


def test_minutes_to_days_negative() -> None:
    assert units.minutes_to_days(-480) == Decimal("-1.00")


def test_minutes_to_days_rounds_half_up() -> None:
    # 1 / 8 == 0.125 exactly; HALF_UP at 2 places -> 0.13 (5 rounds away from zero).
    assert units.minutes_to_days(1, minutes_per_day=8, places=2) == Decimal("0.13")
    assert units.minutes_to_days(1, minutes_per_day=8, places=3) == Decimal("0.125")


def test_minutes_to_days_is_deterministic_no_drift() -> None:
    # A value that would drift under binary float: 1/3 of a day, many places.
    one_third = units.minutes_to_days(160, places=10)  # 160/480 == 0.3333...
    assert one_third == Decimal("0.3333333333")
    # Repeated calls are bit-identical (no accumulating float error).
    assert all(units.minutes_to_days(160, places=10) == one_third for _ in range(100))


def test_minutes_to_days_custom_calendar_axis() -> None:
    # A 10-hour (600-minute) working day.
    assert units.minutes_to_days(600, minutes_per_day=600) == Decimal("1.00")


def test_minutes_to_days_accepts_float_input_without_binary_noise() -> None:
    assert units.minutes_to_days(0.5, places=4) == Decimal("0.0010")  # 0.5/480


@pytest.mark.parametrize("bad", [0, -1])
def test_minutes_to_days_rejects_nonpositive_day_length(bad: int) -> None:
    with pytest.raises(ValueError, match="minutes_per_day"):
        units.minutes_to_days(480, minutes_per_day=bad)


def test_minutes_to_days_rejects_negative_places() -> None:
    with pytest.raises(ValueError, match="places"):
        units.minutes_to_days(480, places=-1)


def test_minutes_to_days_rejects_bool() -> None:
    with pytest.raises(TypeError):
        units.minutes_to_days(True)  # type: ignore[arg-type]


def test_minutes_to_days_rejects_unsupported_type() -> None:
    with pytest.raises(TypeError):
        units.minutes_to_days("480")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# days_to_minutes — inverse                                                    #
# --------------------------------------------------------------------------- #
def test_days_to_minutes_inverse() -> None:
    assert units.days_to_minutes(1) == 480
    assert units.days_to_minutes(Decimal("1.5")) == 720
    assert units.days_to_minutes(0.5) == 240
    assert isinstance(units.days_to_minutes(1), int)


def test_days_to_minutes_rounds_half_up() -> None:
    # 1.001 day * 480 == 480.48 -> 480
    assert units.days_to_minutes(Decimal("1.001")) == 480
    # exactly .5 minute rounds up
    assert units.days_to_minutes(Decimal("0.5"), minutes_per_day=1) == 1


def test_days_to_minutes_rejects_nonpositive_day_length() -> None:
    with pytest.raises(ValueError, match="minutes_per_day"):
        units.days_to_minutes(1, minutes_per_day=0)


# --------------------------------------------------------------------------- #
# format_days — "<n> day(s)" (U1)                                              #
# --------------------------------------------------------------------------- #
def test_format_days_none_is_na() -> None:
    assert units.format_days(None) == "n/a"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0 days"),
        (1, "1 day"),
        (2, "2 days"),
        (-1, "-1 day"),
        (-2, "-2 days"),
        (2.5, "2.5 days"),
        (1.0, "1 day"),
        (Decimal("2.50"), "2.5 days"),
        (Decimal("100"), "100 days"),
        (0.5, "0.5 days"),
    ],
)
def test_format_days_unsigned(value: object, expected: str) -> None:
    assert units.format_days(value) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0 days"),  # zero never gets a +
        (2, "+2 days"),
        (-1, "-1 day"),
        (2.5, "+2.5 days"),
        (-0.5, "-0.5 days"),
    ],
)
def test_format_days_signed(value: object, expected: str) -> None:
    assert units.format_days(value, signed=True) == expected  # type: ignore[arg-type]
    assert units.format_signed_days(value) == expected  # type: ignore[arg-type]


def test_format_days_rejects_bool() -> None:
    with pytest.raises(TypeError):
        units.format_days(True)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# format_minutes_as_days — boundary helper                                     #
# --------------------------------------------------------------------------- #
def test_format_minutes_as_days() -> None:
    assert units.format_minutes_as_days(480) == "1 day"
    assert units.format_minutes_as_days(720) == "1.5 days"
    assert units.format_minutes_as_days(0) == "0 days"
    assert units.format_minutes_as_days(None) == "n/a"


def test_format_minutes_as_days_signed() -> None:
    assert units.format_minutes_as_days(720, signed=True) == "+1.5 days"
    assert units.format_minutes_as_days(-480, signed=True) == "-1 day"


def test_format_minutes_as_days_custom_axis() -> None:
    assert units.format_minutes_as_days(600, minutes_per_day=600) == "1 day"


# --------------------------------------------------------------------------- #
# format_percent — always carries its % sign (U2)                              #
# --------------------------------------------------------------------------- #
def test_format_percent_none_is_na() -> None:
    assert units.format_percent(None) == "n/a"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (100, "100%"),
        (0, "0%"),
        (3.17, "3.17%"),
        (-5, "-5%"),
        (3.1, "3.1%"),
        (Decimal("50.00"), "50%"),
    ],
)
def test_format_percent_unsigned(value: object, expected: str) -> None:
    assert units.format_percent(value) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (100, "+100%"),
        (0, "0%"),
        (-5, "-5%"),
        (3.17, "+3.17%"),
    ],
)
def test_format_percent_signed(value: object, expected: str) -> None:
    assert units.format_percent(value, signed=True) == expected  # type: ignore[arg-type]
    assert units.format_signed_percent(value) == expected  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# ratio_to_percent                                                             #
# --------------------------------------------------------------------------- #
def test_ratio_to_percent() -> None:
    assert units.ratio_to_percent(0.5) == Decimal("50.00")
    assert units.ratio_to_percent(1) == Decimal("100.00")
    assert units.ratio_to_percent(0) == Decimal("0.00")
    assert units.ratio_to_percent(Decimal("0.0317"), places=2) == Decimal("3.17")


def test_ratio_to_percent_then_format() -> None:
    assert units.format_percent(units.ratio_to_percent(0.5)) == "50%"


def test_ratio_to_percent_rejects_negative_places() -> None:
    with pytest.raises(ValueError, match="places"):
        units.ratio_to_percent(0.5, places=-1)
