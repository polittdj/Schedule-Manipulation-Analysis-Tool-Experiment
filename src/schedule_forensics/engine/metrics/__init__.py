"""Metric implementations to exact Acumen Fuse v8.11.0 / SSI parity.

``dcma14.py`` (DCMA-14 ribbon), ``schedule_quality.py`` (Acumen Schedule
Quality), ``evm.py`` (SPI/SPI(t)/CPI/BEI/CPLI/CEI/TCPI), and ``decm.py``
(DECM V7.0 extended audit). Milestones **M7-M8**; see ``docs/PLAN/RTM.md``.
"""

from __future__ import annotations

from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    Direction,
    MetricResult,
)
from schedule_forensics.engine.metrics.cei import compute_cei
from schedule_forensics.engine.metrics.change_metrics import (
    compute_change_metrics,
    compute_net_finish_impact,
)
from schedule_forensics.engine.metrics.completion_performance import (
    compute_completion_performance,
)
from schedule_forensics.engine.metrics.dcma14 import compute_bei, compute_dcma14
from schedule_forensics.engine.metrics.derived import dcma_pass_rate, population_share
from schedule_forensics.engine.metrics.evm import (
    compute_baseline_compliance,
    compute_evm_indices,
)
from schedule_forensics.engine.metrics.fei_bri import compute_bri, compute_fei
from schedule_forensics.engine.metrics.float_bands import (
    FloatSums,
    compute_float_bands,
    compute_float_sums,
)
from schedule_forensics.engine.metrics.float_ratio import compute_float_ratio
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.engine.metrics.ribbon import RibbonMetrics, compute_ribbon
from schedule_forensics.engine.metrics.schedule_card import (
    ActivityMakeup,
    ConstraintCount,
    compute_activity_makeup,
    compute_constraint_distribution,
)
from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
from schedule_forensics.engine.metrics.wbs_breakdown import (
    WBSGroup,
    compute_wbs_breakdown,
)

__all__ = [
    "ActivityMakeup",
    "CheckStatus",
    "ConstraintCount",
    "Direction",
    "FloatSums",
    "MetricResult",
    "RibbonMetrics",
    "WBSGroup",
    "compute_activity_makeup",
    "compute_baseline_compliance",
    "compute_bei",
    "compute_bri",
    "compute_cei",
    "compute_change_metrics",
    "compute_completion_performance",
    "compute_constraint_distribution",
    "compute_dcma14",
    "compute_evm_indices",
    "compute_fei",
    "compute_float_bands",
    "compute_float_ratio",
    "compute_float_sums",
    "compute_hmi",
    "compute_net_finish_impact",
    "compute_ribbon",
    "compute_schedule_quality",
    "compute_wbs_breakdown",
    "dcma_pass_rate",
    "population_share",
]
