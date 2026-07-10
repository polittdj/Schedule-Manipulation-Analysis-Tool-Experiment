# Automated exhibit reports (headless CLI)

`schedule-forensics-report` renders the critical-path-volatility exhibit pack (EX-00…EX-08
SVG + CSV siblings + a self-contained `report.html` + optional `summary.json`) with **no
browser and no server** — it imports the exhibits library directly, so the launcher's
browser-heartbeat watchdog is irrelevant to scheduled runs.

Until the CP-basis engine lands (see `audit/PARK-LIST.md`), `--inputs` runs exit with code
`4` (engine artifacts missing); render from a prebuilt payload with `--payload`.

Exit codes: `0` success · `2` input/ingest hard-fail · `3` terminus not designated ·
`4` engine artifacts missing · `5` output dir not empty without `--force`.

Determinism: `run_id = sha256(sorted input hashes + canonicalized config)[:16]`; no
timestamps in any filename, metadata, or content — two identical runs are byte-identical.

## Windows Task Scheduler registration (PowerShell)

```powershell
$py = "C:\SMAT\.venv\Scripts\schedule-forensics-report.exe"
$args = '--payload C:\SMAT\runs\latest\payload.json --out C:\SMAT\reports\latest --force --json-summary'
$action = New-ScheduledTaskAction -Execute $py -Argument $args
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 06:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "SMAT weekly exhibit pack" -Action $action -Trigger $trigger -Settings $settings -Description "CP-volatility exhibit pack (no browser, no server)"
```

```powershell
Start-ScheduledTask -TaskName "SMAT weekly exhibit pack"
Get-ScheduledTaskInfo -TaskName "SMAT weekly exhibit pack"
```

```powershell
Unregister-ScheduledTask -TaskName "SMAT weekly exhibit pack" -Confirm:$false
```
