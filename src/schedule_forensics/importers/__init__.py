"""Importer layer — native ingestion into the domain model.

MSPDI (MS Project XML) and XER (Primavera P6) parsers (M3) read a schedule file into
the frozen, UniqueID-keyed :class:`~schedule_forensics.model.schedule.Schedule`.
Native ``.mpp`` via the vendored MPXJ runner and the multi-file loader (≤10,
UniqueID-keyed) and an optional Windows COM path arrive in M4. See
``docs/PLAN/BUILD-PLAN.md``. A malformed source raises :class:`ImporterError`.
"""

from __future__ import annotations

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.importers.xer import parse_xer, parse_xer_text

__all__ = [
    "ImporterError",
    "parse_mspdi",
    "parse_mspdi_text",
    "parse_xer",
    "parse_xer_text",
]
