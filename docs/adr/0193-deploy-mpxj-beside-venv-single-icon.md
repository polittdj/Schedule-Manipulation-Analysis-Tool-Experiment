# ADR-0193 — Deploy MPXJ beside the venv; one self-stopping desktop icon

## Status

Accepted. Operator 2026-07-10 (screenshot of the freshly deployed tool): every native `.mpp`
upload failed — "MPXJ runner not found under C:\…\ScheduleForensics\venv\Lib\tools\mpxj — run
tools/mpxj/setup.sh or set SF_MPXJ_HOME" — and "I want one icon that I can open the tool with
and when I close the tool for all processes to stop including the AI."

## Context

1. The wheel is pure Python; the 17 MB vendored Java converter (`tools/mpxj`) lives only in
   the repo. `_mpxj_home()` resolved `parents[3]/tools/mpxj`, which lands INSIDE the deployed
   venv (`venv\Lib\tools\mpxj`) — so a deployed install could never open a native `.mpp`,
   even with Java present. Embedding the jars in the wheel would balloon the nine base64
   installers committed to git by ~200 MB per rebuild — not acceptable.
2. The install created THREE touchpoints (Start icon, Stop icon, plus whatever older icons
   the operator had) for a tool that already stops itself: `create_app(auto_shutdown=True)`
   shuts the server down when the browser closes, and the Ollama manager (ADR-0122) kills
   the tray + server on exit via `finally`/`atexit`.

## Decisions

1. **Runtime walk-up discovery**: `_mpxj_home()` keeps `SF_MPXJ_HOME` first, then walks EVERY
   enclosing folder of the module looking for `tools/mpxj/classes/MpxjToMspdi.class` — the
   repo layout (parents[3]) and the deployed layout (`…\ScheduleForensics\tools\mpxj`, a few
   levels above site-packages) are both found with zero configuration. The historical repo
   default remains the fallback so the not-found error still names a concrete path.
2. **Installers copy the converter beside the venv** (all three OS families): the repo's
   `tools/mpxj` (found relative to the installer script) is copied to
   `<install root>/tools/mpxj`, with an honest "native .mpp import stays OFF" warning when
   the installer is run outside a checkout.
3. **One desktop icon** — "Schedule Forensics.lnk" targets the venv's `pythonw.exe` directly
   (no console window, no wrapper): the app self-stops on browser close / Quit and tears the
   local AI down in-process, so no Stop icon is needed. The previous Start/Stop desktop and
   Start-Menu icons are removed on upgrade install and by the uninstaller (which also removes
   the new name). `Stop-ScheduleForensics.cmd` stays in the install folder as a
   troubleshooting fallback and the README says so.

## Consequences

- Sandbox-verified end-to-end in-container: a fresh venv from the wheel + `tools/mpxj`
  copied beside it parses the operator's exact failing file (`Hard_File.mpp`, 142 tasks);
  removing the copy reproduces the honest ImporterError; the repo layout still resolves; the
  actual Linux installer run in smoke mode deploys the converter and ITS venv parses the
  same `.mpp`.
- Regression pins: `_mpxj_home` walk-up unit test (fake deployed tree), installer static
  pins (copy step + honest warning in ps1/sh/command; single icon; legacy-icon cleanup).
