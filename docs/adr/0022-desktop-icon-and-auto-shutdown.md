# ADR-0022: Windows desktop icon + auto-shutdown on browser close

- **Status:** Accepted
- **Date:** 2026-06-09 (post-build enhancement, requested by the operator)
- **Relates to:** §6.A ("launches from a desktop icon"), §6.G/Law 1 (local-only), ADR-0018/0020 (web app + launcher)

## Context
After the build merged, the operator asked for a **double-clickable Windows desktop icon** that
launches the tool, and for the tool to **turn everything off when they close out of it**. The
M16 launcher ran the server in a foreground console (`uvicorn.run`, stop via Ctrl-C) — there was
no clean "close the window → everything stops", and no Windows icon that hides the console.

## Decision
1. **Graceful, programmable shutdown.** `web.app.serve()` now drives a `uvicorn.Server` (instead
   of `uvicorn.run`) and wires `app.state.request_shutdown` to flip `server.should_exit`. Three
   paths call it: the in-page **Quit** link, `POST /api/shutdown` (sent by the page), and the
   browser-gone **watchdog**. No signals, cross-platform.
2. **Browser-gone watchdog = "close the window turns it off".** Every page beats `POST
   /api/heartbeat` every 3s. When `create_app(auto_shutdown=True)` (the launcher's mode),
   `serve()` starts a daemon watchdog: once a browser has connected and then goes quiet for
   `idle_grace` (10s), it requests shutdown. Closing the last window stops the beats → the server
   exits cleanly within a few seconds; a refresh or a second tab keeps it alive (no false kill).
   The decision is the pure, tested `_is_idle(browser_seen, idle_seconds, grace)`.
3. **Windows double-click, no console.** A PowerShell installer
   (`packaging/windows/Install-Desktop-Shortcut.ps1`) creates a Desktop `.lnk` targeting
   **`pythonw.exe -m schedule_forensics.launcher`** (pythonw = no console window) with a bundled
   icon. A portable `Schedule Forensics.vbs` (hidden `WScript.Shell.Run`) is the no-installer
   alternative. The icon `schedule-forensics.ico` is generated stdlib-only by
   `packaging/make_icon.py` (PNG-in-ICO; no Pillow).
4. **CUI unchanged.** The server still binds 127.0.0.1 only (`serve()` refuses a non-loopback
   host); no new dependency; the egress + air-gap guards stay green. `auto_shutdown` defaults to
   **False** so tests and dev `run()` don't self-terminate; only the launcher enables it.

## Consequences
- Closing the browser (or clicking Quit) stops the local server with nothing left running — the
  requested "turn everything off when I close out of it". On Windows it launches from a Desktop
  icon with no console window.
- `serve()`/watchdog/`_is_idle` are unit-tested (injected fake server; thread-based watchdog with
  a tiny grace); launcher 100%, web/app 93%; full gate + parity + air-gap green; no new deps.
- The heartbeat/quit JS lives in the shared layout, so it applies to every page. (Note: this does
  not manage Ollama — the AI runs as a separate local service the user controls; the tool simply
  routes to it and never starts/leaves a model process of its own.)
