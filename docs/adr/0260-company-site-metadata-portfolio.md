# ADR-0260 — Company/Site metadata: MSPDI Company → Portfolio "Site / Company" column

## Status

Accepted. Third piece of the 2026-07-18 session (with ADR-0258/0259). The Portfolio site *map*
(US map of NASA installations) is explicitly **deferred** — the operator's Claude-Design prompt
for the visual pass has not arrived; building the map now would invent a design twice.

## Context

The master prompt's §2.1 wanted the document **Company** field as the site/location signal
("Company field → site/location"), feeding a Portfolio site dimension. Nothing in the model or
importers carried it: MSPDI `<Company>` was unread, and the recon confirmed golden fixtures
(Project2, EVM1/2) do carry the element.

## Decision

- **Model:** `Schedule.company: str | None = None` — additive, frozen-model-safe, no cache-schema
  impact (`VersionSummary` unchanged; the value reads straight off the in-session Schedule).
- **Importers:** MSPDI reads `<Company>` verbatim (None when absent — never guessed). XER/P6
  exports carry **no company-equivalent header field** — documented in the importer, stays None
  (honest absence beats a fabricated mapping). The tool's own JSON round-trips it.
- **Portfolio:** a "Site / Company" column per Project row, from the latest included version
  (em-dash when absent). No engine math; presentation only.
- **Deferred:** the interactive US-map site view and any Company→NASA-installation mapping
  table await the design prompt; a site drill-down beyond the column is out of scope until then.

## Consequences

- MSPDI-sourced projects show their site/company on Portfolio today; XER projects honestly show
  "—". Tests: importer extraction + Portfolio column (`tests/web/test_project_scope.py`);
  fixture `<Company>` presence confirmed. Version 1.0.66 → 1.0.67.
