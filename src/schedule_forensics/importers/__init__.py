"""Importer layer — native ingestion into the domain model.

MSPDI (MS Project XML) and XER (Primavera P6) parsers (M3) read a schedule file into
the frozen, UniqueID-keyed :class:`~schedule_forensics.model.schedule.Schedule`.
Native ``.mpp`` via the vendored MPXJ runner (M4, :func:`parse_mpp`) and the
multi-file loader (:func:`load_schedules`, ≤10, UniqueID-keyed) build on them; an
optional Windows COM path arrives later. See ``docs/PLAN/BUILD-PLAN.md``. A malformed
source raises :class:`ImporterError`.
"""

from __future__ import annotations

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.loader import (
    MAX_FILES,
    load_schedule,
    load_schedules,
    supported_extensions,
)
from schedule_forensics.importers.mpp_mpxj import parse_mpp
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.importers.xer import parse_xer, parse_xer_text

__all__ = [
    "MAX_FILES",
    "ImporterError",
    "load_schedule",
    "load_schedules",
    "parse_mpp",
    "parse_mspdi",
    "parse_mspdi_text",
    "parse_xer",
    "parse_xer_text",
    "supported_extensions",
]
