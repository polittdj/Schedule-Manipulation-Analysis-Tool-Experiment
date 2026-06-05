"""Tests for the shared importer value-parsing helpers (M3)."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.importers._common import (
    ImporterError,
    hours_to_minutes,
    iso_duration_to_minutes,
    parse_datetime,
    parse_float,
    parse_percent,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PT16H0M0S", 960),
        ("PT8H30M0S", 510),
        ("PT0H0M0S", 0),
        ("PT80H0M0S", 4800),
        ("PT90M", 90),
        ("P1DT0H0M0S", 1440),  # ISO-8601 "D" is a calendar (24h) day
        ("PT0H0M30S", 1),  # 30s == 0.5min, ROUND_HALF_UP -> 1
        (None, 0),
        ("", 0),
        ("   ", 0),
    ],
)
def test_iso_duration_to_minutes(value: str | None, expected: int) -> None:
    assert iso_duration_to_minutes(value) == expected


def test_iso_duration_rejects_garbage() -> None:
    with pytest.raises(ImporterError, match="ISO-8601 duration"):
        iso_duration_to_minutes("garbage")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("8", 480),
        ("-4", -240),  # a lead
        ("7.5", 450),
        ("0", 0),
        (None, 0),
        ("", 0),
    ],
)
def test_hours_to_minutes(value: str | None, expected: int) -> None:
    assert hours_to_minutes(value) == expected


def test_hours_to_minutes_rejects_garbage() -> None:
    with pytest.raises(ImporterError, match="hour count"):
        hours_to_minutes("abc")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025-01-06T08:00:00", dt.datetime(2025, 1, 6, 8, 0)),
        ("2025-01-06 08:00", dt.datetime(2025, 1, 6, 8, 0)),
        ("1984-01-01T00:00:00", None),  # pre-1985 sentinel
        ("not-a-date", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_datetime(value: str | None, expected: dt.datetime | None) -> None:
    assert parse_datetime(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("150", 150.0), ("95.5", 95.5), ("0", 0.0), ("", None), (None, None)],
)
def test_parse_float(value: str | None, expected: float | None) -> None:
    assert parse_float(value) == expected


def test_parse_float_rejects_garbage() -> None:
    with pytest.raises(ImporterError, match="number"):
        parse_float("x")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("50", 50.0), ("100", 100.0), (None, 0.0), ("", 0.0)],
)
def test_parse_percent(value: str | None, expected: float) -> None:
    assert parse_percent(value) == expected
