# ADR-0020: M16 desktop launcher + packaging

- **Status:** Accepted
- **Date:** 2026-06-09 (session A17 — Phase 2 build, milestone M16, continuous A7 sitting)
- **Relates to:** §6.A ("launches from a desktop icon; runs 100% locally; opens in a browser"), `BUILD-PLAN.md M16`, RTM A2
- **Builds on:** ADR-0018 (web app + `run()`), ADR-0006 (egress guard / loopback)

## Context
§6.A requires the tool to launch from a **desktop icon**, run **100% locally**, and **open in
a web browser**. M13 gave the app a `run()` on 127.0.0.1; M16 adds the one-click launcher and
the OS shortcuts.

## Decision
1. **`src/schedule_forensics/launcher.py`** — `main()` picks a free **loopback** ephemeral
   port (`find_free_port`), schedules the default browser to open at the dashboard after a
   short delay (so the server is accepting connections), and serves the FastAPI app via
   `uvicorn.run` on 127.0.0.1. It **refuses any non-loopback host** (`net_guard.is_loopback_host`)
   — the tool is local-only (Law 1). The server, browser-open, and timer are **injectable**,
   so the wiring is unit-tested without binding a real port or spawning a browser (launcher
   at 100% coverage); a live run confirmed it serves and prints the URL.
2. **Console entry point** `schedule-forensics = schedule_forensics.launcher:main`
   (`[project.scripts]`), plus `python -m schedule_forensics.launcher`.
3. **OS shortcuts under `packaging/`** that all call the same entry point: a Linux
   `.desktop`, a macOS `.command` (executable), and a Windows `.bat` (with a
   `python -m` fallback), and a `README.md` with one-time install + per-OS instructions.

## Consequences
- RTM **A2 → ✔** (desktop icon → local server → browser, offline). With M13/M14 the product
  surface is complete and runnable end-to-end on a workstation with no network.
- launcher 100% cov; full suite 424 passing; egress + parity + air-gap green; no new deps
  (uvicorn/webbrowser/socket/threading are already available).
- M17 (docs + final report) is the last milestone: user guide (incl. the launcher steps),
  metric dictionary (already in `web/help.py`), parity report (the gate output), and the
  requirement→evidence map; then `HANDOFF → DONE`, with M15 (.pbix) the one externally-gated
  item pending the operator's deposit.
