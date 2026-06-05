"""Smoke tests — the package and every layer sub-package import cleanly.

M1 stands up the real package skeleton; these guard against an import-time
regression in any layer as later milestones fill them in.
"""

from __future__ import annotations

import importlib

import schedule_forensics

LAYER_MODULES = [
    "schedule_forensics.model",
    "schedule_forensics.importers",
    "schedule_forensics.engine",
    "schedule_forensics.engine.metrics",
    "schedule_forensics.ai",
    "schedule_forensics.web",
    "schedule_forensics.reports",
    "schedule_forensics.net_guard",
    "schedule_forensics.logging_redaction",
]


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(schedule_forensics.__version__, str)
    assert schedule_forensics.__version__


def test_every_layer_imports() -> None:
    for name in LAYER_MODULES:
        module = importlib.import_module(name)
        assert module is not None
