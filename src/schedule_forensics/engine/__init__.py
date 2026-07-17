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
    off_project_calendars,
    offset_to_datetime,
)
from schedule_forensics.engine.dcma_audit import (
    AuditCheck,
    Citation,
    ScheduleAudit,
    audit_schedule,
)
from schedule_forensics.engine.diff import (
    FieldDelta,
    TaskDiff,
    VersionDiff,
    diff_versions,
)
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    DrivingSlackResult,
    PathTier,
    compute_driving_slack,
    driving_path,
)
from schedule_forensics.engine.float_analysis import (
    FloatResult,
    ScheduleFloatSummary,
    analyze_floats,
    summarize_floats,
)
from schedule_forensics.engine.manipulation import (
    TrendPoint,
    detect_manipulation,
    trend_across_versions,
)
from schedule_forensics.engine.path_trace import ancestors_of, topo_order
from schedule_forensics.engine.recommendations import (
    Category,
    Finding,
    Severity,
    recommend,
)
from schedule_forensics.engine.trend import (
    MetricTrend,
    compute_quality_trend,
    order_versions,
)

__all__ = [
    "DEFAULT_SECONDARY_MAX_DAYS",
    "DEFAULT_TERTIARY_MAX_DAYS",
    "AuditCheck",
    "CPMError",
    "CPMResult",
    "Category",
    "Citation",
    "DrivingSlackResult",
    "FieldDelta",
    "Finding",
    "FloatResult",
    "MetricTrend",
    "PathTier",
    "ScheduleAudit",
    "ScheduleFloatSummary",
    "Severity",
    "TaskDiff",
    "TaskTiming",
    "TrendPoint",
    "VersionDiff",
    "analyze_floats",
    "ancestors_of",
    "audit_schedule",
    "compute_cpm",
    "compute_driving_slack",
    "compute_quality_trend",
    "datetime_to_offset",
    "detect_manipulation",
    "diff_versions",
    "driving_path",
    "off_project_calendars",
    "offset_to_datetime",
    "order_versions",
    "recommend",
    "summarize_floats",
    "topo_order",
    "trend_across_versions",
]
