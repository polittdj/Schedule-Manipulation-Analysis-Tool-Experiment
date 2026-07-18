@echo off
REM Windows: double-clickable console launcher. Starts the local dashboard (127.0.0.1) and
REM opens your browser. Requires the package installed (pip install -e .) so the console script
REM `schedule-forensics` is on PATH; otherwise falls back to the guarded module entry point.
REM This launcher keeps a console window open, so any error is visible here; the NO-console
REM icon is "Schedule Forensics.vbs" / the Install-Desktop-Shortcut.ps1 shortcut, which surface
REM startup errors via a message box instead.
REM NOTE: redirect to `nul` (Windows), not `/dev/null` — the latter created a stray "dev\null"
REM file and made `where` fail on some machines.
where schedule-forensics >nul 2>nul
if %errorlevel%==0 (
  schedule-forensics
) else (
  python -m schedule_forensics
)
