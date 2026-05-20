"""Enumerations shared across the data model and the metrics layer."""

from __future__ import annotations

from enum import StrEnum


class RelationType(StrEnum):
    """Precedence relationship types (predecessor -> successor)."""

    FS = "FS"  # Finish-to-Start
    SS = "SS"  # Start-to-Start
    FF = "FF"  # Finish-to-Finish
    SF = "SF"  # Start-to-Finish


class ConstraintType(StrEnum):
    """MS Project task date constraints.

    Soft (logic-driven): ASAP, ALAP, SNET (Start No Earlier Than), FNET (Finish No Earlier
    Than). Hard (can override logic / cause negative float): SNLT (Start No Later Than),
    FNLT (Finish No Later Than), MSO (Must Start On), MFO (Must Finish On). The CPM engine
    schedules under MS Project's default "honor constraint dates" behaviour.
    """

    ASAP = "ASAP"
    ALAP = "ALAP"
    SNET = "SNET"
    SNLT = "SNLT"
    FNET = "FNET"
    FNLT = "FNLT"
    MSO = "MSO"
    MFO = "MFO"

    @property
    def is_hard(self) -> bool:
        """Whether this is a hard constraint (DCMA Metric 5 counts these)."""
        return self in {
            ConstraintType.SNLT,
            ConstraintType.FNLT,
            ConstraintType.MSO,
            ConstraintType.MFO,
        }

    @property
    def needs_date(self) -> bool:
        """Whether this constraint requires a constraint_date (all but ASAP/ALAP)."""
        return self not in {ConstraintType.ASAP, ConstraintType.ALAP}


class Severity(StrEnum):
    """Metric outcome severity. Exactly three states — no ERROR, no fourth state.

    A metric that cannot run raises rather than returning a fabricated result.
    """

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class Direction(StrEnum):
    """Direction of a threshold comparison: the value passes when it is at most /
    at least the threshold."""

    AT_MOST = "<="
    AT_LEAST = ">="
