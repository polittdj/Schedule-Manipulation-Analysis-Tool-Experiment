"""Critical-path-volatility exhibits layer (operator 2026-07-10, ADR-0184).

One payload builder feeds three consumers so they can never disagree:

- the **static exhibit pack** (:mod:`render_svg` + :mod:`report_html` + :mod:`csvout`) — a
  printable, deterministic set of SVG/CSV/HTML files rendered entirely in stdlib Python;
- the **interactive volatility page** (the existing ``volatility.js``), which embeds the same
  serialized payload bytes;
- the **headless CLI** (:mod:`cli`, console script ``schedule-forensics-report``).

The payload schema (:mod:`payload`) is the contract. The CP-basis engine artifacts the schema
carries (CIC, τ-b, null-model churn, recompute deltas) do NOT exist in the engine yet; per the
build order, the models and renderers are developed and tested against the golden fixture
payloads under ``tests/exhibits/fixtures/`` and the live wiring is PARKED (see
``audit/PARK-LIST.md``) — no engine output is fabricated.
"""

from schedule_forensics.exhibits.payload import ExhibitPayload, canonical_json, load_payload

__all__ = ["ExhibitPayload", "canonical_json", "load_payload"]
