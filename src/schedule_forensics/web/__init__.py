"""Web UI layer — local-only FastAPI + Jinja2 + HTMX, dark NASA theme.

Upload (≤10 native ``.mpp``), dashboard, interactive Power-BI-style visuals
(vendored ECharts + Tabulator, air-gapped), the in-tool metric dictionary, and
the model-settings panel. Milestones **M13-M14**; see ``docs/PLAN/BUILD-PLAN.md``.
"""

from __future__ import annotations

from schedule_forensics.web.app import SessionState, create_app, run
from schedule_forensics.web.help import METRIC_DICTIONARY, MetricDoc, metric_doc

__all__ = [
    "METRIC_DICTIONARY",
    "MetricDoc",
    "SessionState",
    "create_app",
    "metric_doc",
    "run",
]
