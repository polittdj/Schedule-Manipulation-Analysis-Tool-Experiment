"""Local-AI layer (pluggable, CUI fail-closed).

Backend interface with Null (default) and Ollama implementations plus an explicit
unclassified-cloud toggle behind a persistent banner; the cited narrative generator and
``citations.py`` (every AI statement carries file + UniqueID + task name). Milestone
**M12**; see ``docs/PLAN/BUILD-PLAN.md``. AI transport is stdlib-only to a loopback host —
no forbidden HTTP distribution enters the runtime (``net_guard``).
"""

from __future__ import annotations

from schedule_forensics.ai.backend import (
    AIBackend,
    AIConfig,
    Banner,
    Classification,
    banner_for,
    route_backend,
)
from schedule_forensics.ai.citations import (
    CitedStatement,
    Narrative,
    UncitedStatementError,
    assert_all_cited,
    preserves_figures,
    reattach,
)
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.ollama import OllamaBackend

__all__ = [
    "AIBackend",
    "AIConfig",
    "Banner",
    "CitedStatement",
    "Classification",
    "Narrative",
    "NullBackend",
    "OllamaBackend",
    "UncitedStatementError",
    "assert_all_cited",
    "banner_for",
    "build_narrative",
    "preserves_figures",
    "reattach",
    "route_backend",
]
