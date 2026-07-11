# SMAT-SANDBOX — a safe mirror of Schedule Forensics

This repository is a **faithful backup / experiment sandbox** of the production tool
[`polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment).
The application code, engine, tests, and reference intake are **identical** to production as of
the mirror commit — the tool functions exactly the same.

## The one intentional difference: a separate desktop icon

The installers here are branded so the sandbox **installs and runs beside** your production
install instead of overwriting it:

| | Production | Sandbox (this repo) |
|---|---|---|
| Desktop icon | **Schedule Forensics** | **SMAT Sandbox** (custom orange glyph) |
| Windows install dir | `%LOCALAPPDATA%\ScheduleForensics` | `%LOCALAPPDATA%\ScheduleForensicsSandbox` |
| Local port | `127.0.0.1:8321` | `127.0.0.1:8322` |
| macOS / Linux dir | `…/ScheduleForensics` | `…/ScheduleForensicsSandbox` |

Because the install dir, port, and shortcut name all differ, installing the sandbox **never
touches** the production install — both icons live on the desktop, both can run at the same
time, and the sandbox uninstaller removes only the sandbox.

## Install (Windows)

```powershell
git clone https://github.com/polittdj/SMAT-SANDBOX.git
cd SMAT-SANDBOX
powershell -ExecutionPolicy Bypass -File .\installer\install-tier1.ps1
```

Then double-click the **SMAT Sandbox** icon. Close the browser window to stop everything
(server + local AI), exactly like production.

Everything else — the full gate, lockstep wheel/installers, MPXJ native-`.mpp` support, and
the two non-negotiable laws (local-only data sovereignty; fidelity over speed) — is unchanged
from production.
