@echo off
REM Windows: double-clickable launcher. Starts the local dashboard (127.0.0.1) and opens
REM your browser. Requires the package installed (pip install -e .) so the console script
REM `schedule-forensics` is on PATH; otherwise falls back to the module entry point.
where schedule-forensics >/dev/null 2>/dev/null
if %errorlevel%==0 (
  schedule-forensics
) else (
  python -m schedule_forensics.launcher
)
