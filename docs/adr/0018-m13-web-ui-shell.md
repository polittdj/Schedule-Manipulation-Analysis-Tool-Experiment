# ADR-0018: M13 local FastAPI web shell — dashboard, AI settings, metric dictionary

- **Status:** Accepted
- **Date:** 2026-06-08 (session A15 — Phase 2 build, milestone M13, continuous A7 sitting)
- **Relates to:** §6.A (platform/UX, in-tool help), §6.F (model settings), §6.G/§0 (local-only), `BUILD-PLAN.md M13`
- **Builds on:** ADR-0017 (AI backend/banner), ADR-0015/0016 (audit/recommendations/manipulation), ADR-0006 (egress guard)

## Context
M13 puts a usable, local, dark NASA-themed surface on the M1–M12 engine: upload schedules,
read the audit/metrics/findings/narrative, manage the local AI, and explain every metric —
all without any data leaving the machine.

## Decision
1. **FastAPI app, local-only (`web/app.py`).** `create_app(state)` builds the app (DI-friendly
   `SessionState` = in-memory schedules + AIConfig; no disk persistence). `run()` binds
   **127.0.0.1 only** and refuses a non-loopback host (`net_guard.is_loopback_host`). Routes:
   dashboard + upload (≤10, parsed locally — MSPDI/XER in memory, `.mpp` via a temp file +
   MPXJ), per-schedule analysis (DCMA audit + cited recommendations + AI narrative), `/compare`
   (manipulation trends + CPM/progress trend), `/settings` (classification + model list/pull/
   select), `/help` (metric dictionary), `/session/wipe`, and a JSON `/api/analysis/{name}`
   (the M14 visuals seam). Dark NASA theme via an inline CSS + Jinja `Template` (no CDN).
2. **In-tool metric dictionary (`web/help.py`).** A `MetricDoc` (definition + formula + source +
   citation basis) for **every** metric the engine emits; a coverage test gathers all emitted
   `metric_id`s on the golden schedules and asserts each is documented — the help can never
   show an unexplained figure (§6.A).
3. **Persistent CUI banner is config-driven (`ai.banner_for`).** The banner reflects the
   project's classification *intent* (UNCLASSIFIED + cloud → a red banner naming the external
   endpoint; else a green local-only banner), shown on every page — separate from the
   fail-closed backend *selection* (`route_backend`), which still only ever reaches cloud when
   a real cloud backend is wired and the project is UNCLASSIFIED.
4. **CUI / dependencies.** Runtime deps added: `fastapi`, **plain `uvicorn`** (NOT
   `uvicorn[standard]` → avoids the forbidden `websockets` distribution), `jinja2`,
   `python-multipart`; `httpx` is **dev-only** (starlette TestClient). The egress guard stays
   green (22/22) — no forbidden runtime distribution, no importable cloud SDK. No schedule
   content is logged (paths/counts only). Form posts use `fastapi.Form`; output is
   HTML-escaped. `E501` is per-file-ignored for `web/app.py` (HTML/CSS literals).

## Consequences
- RTM **A3 → ✔** (dark NASA UI), **A5 → ✔** (in-tool metric dictionary, coverage-tested),
  **F2 → ✔** (in-app list/pull/select + classification toggle); **A2** has the local
  browser server (`run()` on 127.0.0.1) — the desktop icon/packaging is M16; **A4** (interactive
  drill-down visuals) is M14, seeded by the JSON API.
- web/app 92% (uncovered: the `.mpp`-upload temp-file path — needs a JRE, like the skipped
  `.mpp` tests — and a few exception fallbacks) / web/help 100%; full suite 414 passing; egress
  + parity green.
- M14 layers vendored ECharts/Tabulator on `/api/analysis`; M16 wraps `web.run()` in a desktop
  launcher; M17's user guide reuses the metric dictionary.
