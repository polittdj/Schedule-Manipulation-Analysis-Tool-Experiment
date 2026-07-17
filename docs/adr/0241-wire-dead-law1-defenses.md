# ADR-0241 — Wire the dead Law-1 defenses: startup redaction + egress guard, enumerated air-gap scan, version pin (PR-R2)

## Status

Accepted. The remaining VALID-AND-OPEN Law-1 items from the validated prior audits
(2026-07-13/14: M6, L3, L5, and M11's durable fix), queued as PR-R2 since ADR-0234.

## Context

Two Law-1 defenses existed as code but were dead at runtime, and two guards had
hand-kept blind spots:

- **M6:** `logging_redaction.configure_logging()` had zero runtime callers, so the
  CUI-redacting JSON handler was never installed — a `WARNING+` record from any
  `schedule_forensics.*` logger hit `logging.lastResort` unredacted. No call site leaked
  today (they log counts/suffixes only), but the guarantee rested on every present and
  future log call being hand-safe — exactly the fragility redaction was built to remove.
- **L3:** `net_guard.assert_local_only()` was invoked by no entry point (tests only), and
  its docstring falsely claimed "application entry points call it on startup."
- **L5:** the air-gap scan (`tests/web/test_airgap.py`) walked a hand-kept page list that
  had drifted: /mission, /compare, /path, /evm, /performance, /volatility, /integrity,
  /evolution, /workbench, /brief, /risks (and later /standards) were never scanned.
- **M11 (durable fix):** the state-docs guard pinned only the latest ADR token, so a
  version bump without an ADR (the 1.0.18 case) could ship while HANDOFF still presented
  the prior version as current.

## Decision

1. **Startup wiring (M6+L3):** `launcher.main()` calls `configure_logging()` then
   `assert_local_only()` immediately after stream rebinding, and `create_app()` repeats
   both at its top — every web entry path (desktop icon, `run()`, tests, embedding) now
   activates redaction and fails closed (`CUIEgressError` aborts construction) before
   anything is served. The audit named only those two, but the package ships a THIRD
   entry point — the headless `schedule-forensics-report` CLI (`exhibits.cli.main`),
   which renders CUI-derived payloads and whose future `--inputs` path will run the
   logging importers — so it gets the same two calls before argument handling: a tripped
   guard propagates loudly and writes nothing. `configure_logging` is
   idempotent-by-replacement, so repeated calls are safe; the launcher-side call covers
   the window before app construction.
2. **Startup assertion tests:** `tests/web/test_startup_guards.py` pins the wiring —
   handler structure (CUIJsonFormatter + CUIRedactingFilter, `propagate=False`), a
   behavioral redaction proof through the *installed* handler chain, and fail-closed
   construction on a tripped guard. `tests/test_launcher.py` gains the launcher-side
   twins (redaction active after `main()`; a tripped guard serves nothing and opens no
   browser), and `tests/exhibits/test_cli_guards.py` the CLI twins (tripped guard ⇒
   nothing written, not even the output directory).
3. **Enumerated air-gap scan (L5):** the scan now walks every GET route on the live
   `app.routes` table (path params filled from `_PARAM_FILLERS`; an unknown parameter
   fails loudly) and every vendored `.js`/`.css` in the static directory on disk —
   98 GET routes (32 HTML + 45 JSON scanned; 21 xlsx exports content-type-skipped) and
   58 assets vs the old 13 pages + 23 assets. An HTML route that fails to render (or any
   route that 5xxs) fails the walk — a broken page can no longer pass the scan vacuously.
   `_MUST_ENUMERATE` pins the known page set so the enumeration itself cannot silently
   regress to scanning nothing.
4. **Version pin (M11):** `tests/test_state_docs.py` also asserts the `pyproject.toml`
   version string appears in HANDOFF's top (pre-`# (prior)`) STATUS section — an
   ADR-less version bump now forces the handoff refresh in the same change.

## Consequences

- The two "docstring claims it, runtime doesn't do it" gaps are closed with the
  docstrings corrected to name the actual wiring; the redaction guarantee no longer
  depends on every log call being hand-safe.
- `create_app()` construction now costs one `assert_local_only()` pass (~10 `find_spec`
  probes + one metadata read) — negligible, and the dev-only `httpx` (TestClient) stays
  legal because the guard checks *declared runtime* dependencies by design.
- A new page or static asset is air-gap-scanned the moment it exists; a new path
  parameter name deliberately breaks the walk until a filler is added consciously.
- Uvicorn's own `uvicorn.*` loggers remain outside the redaction namespace (access
  logging stays off at `log_level="warning"`); extending coverage there is future work,
  not regression.
