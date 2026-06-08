"""Analysis engine — pure-Python, deterministic, fidelity-over-speed.

CPM forward/backward pass, total/free float and SSI driving slack, path tracing
to a target UniqueID, the Acumen/DCMA-14/EVM/DECM metric set, version diff,
manipulation-trend detection, DCMA audit, and recommendations. Built across
milestones **M5-M11** (see ``docs/PLAN/BUILD-PLAN.md``). Coverage gate: >=85%.
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import (
    CPMError,
    CPMResult,
    TaskTiming,
    compute_cpm,
    datetime_to_offset,
    offset_to_datetime,
)
from schedule_forensics.engine.float_analysis import (
    FloatResult,
    ScheduleFloatSummary,
    analyze_floats,
    summarize_floats,
)

__all__ = [
    "CPMError",
    "CPMResult",
    "FloatResult",
    "ScheduleFloatSummary",
    "TaskTiming",
    "analyze_floats",
    "compute_cpm",
    "datetime_to_offset",
    "offset_to_datetime",
    "summarize_floats",
]
