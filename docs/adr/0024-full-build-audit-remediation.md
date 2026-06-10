# ADR-0024: Full-build audit remediation (bugs, perf, CI, cleanup)

- **Status:** Accepted
- **Date:** 2026-06-10 (post-build audit, requested by the operator)
- **Relates to:** §6.A (web UX), §6.D/E (engine/manipulation), §6.F (AI), §7 (QC/CI), ADR-0023
  (the file-first dashboard this work hardens), ADR-0005/0010 (CPM determinism + date math)

## Context
After M1–M17 the operator asked for a top-to-bottom audit — "correct, improve, clean up, speed up."
A three-track review (engine/model/importers; web/AI/launcher/packaging; tests/CI/docs/hygiene) found
29 issues. The most consequential was a **Windows-only `.mpp` upload failure** (the operator's OS): the
upload kept a `NamedTemporaryFile` open while the MPXJ Java subprocess tried to read it, which Windows
blocks. The dropzone also POSTed via `fetch()` and then navigated to `/`, so the new import-feedback
flash and the single-file→report redirect never showed in a real browser.

## Decision
Ship the fixes as 13 ordered commits on the open PR (#58), bugs → perf → CI → cleanup so a partial
revert stays clean:

1. **Bugs.** Dropzone submits the real `<form>` (browser follows the 303, so flash + single-file
   redirect survive). Native `.mpp` upload writes into a `TemporaryDirectory` and closes the file
   before parsing. `/session/wipe` and `/example` are **POST-only** (a GET could be link-prefetched and
   mutate state); `/download` filename strips quote/backslash/CRLF. `manipulation._deleted_logic` cites
   `prior.source_file` (the engine's only previously-uncited citation — §6 contract). `evm._spi_t`
   drops dead "interpolation" (`lo + (hi - lo) == hi`) for an honest step function.
2. **Perf.** `Schedule.tasks_by_id`/`resources_by_id` are `cached_property` (the model is frozen, so the
   maps cannot stale; `model_copy` drops the cache so a copy rebuilds from its own fields). Each report
   computes one `_Analysis` (a single CPM) cached on the session and reused by the page, the JSON the
   page fetches, and the driving view (was 5+ CPM solves per view). `cpm._count_working_days` /
   `offset_to_datetime` use full-weeks arithmetic + holiday compensation instead of a day-by-day walk —
   O(weeks) not O(days). Ollama availability probes use a 2 s timeout (was the 120 s generate timeout).
3. **CI.** `push` runs on `main` only (a PR push no longer runs the matrix twice; PR runs carry the
   branch-protection contexts); `actions/checkout@v5` + `actions/setup-python@v6` (Node-20 retirement);
   pip cache keyed on `pyproject.toml`.
4. **Cleanup/docs.** Web CSS/JS extracted to `static/base.css` + `static/heartbeat.js` +
   `static/home.js`; flattened `_DATE_FIELDS`; one shared `SEVERITY_ORDER`; session-scoped golden test
   fixtures + a central warning filter; README/HANDOFF/FINAL-REPORT refreshed; `pyproject` → `1.0.0`
   with `[project.urls]`.

## Why these are safe (fidelity, Law 2)
- The CPM date-math rewrite is the trust root, so it ships with `tests/engine/test_cpm_date_equivalence.py`:
  the **verbatim** old day-by-day loops are kept as a reference oracle and the new arithmetic is swept
  over thousands of randomized calendars, spans and offsets — byte-identical. The parity gate (10/10)
  and every CPM test are unchanged.
- The SPI(t) and `_compliance_findings(cpm)` changes are behavior-preserving (existing golden/range
  tests pin the output).
- `cached_property` on a frozen pydantic v2 model is supported and field-driven hash/eq ignore the
  non-field cache (verified by tests).

## Consequences
- The Windows `.mpp` path works; import feedback and the single-file redirect work via drag/drop and the
  picker; destructive routes can't be prefetched.
- Full suite **469 passing, 3 skipped**; engine ≈99%, overall ≈99%; parity 10/10; egress + air-gap green;
  zero new runtime dependencies (still stdlib-only I/O).
- LICENSE remains the explicit placeholder (operator decision, unchanged).
