# Desktop launcher & shortcuts

One-click, **fully offline** launch of the Schedule Forensics dashboard. The launcher starts
the local server on `127.0.0.1` (a free ephemeral port) and opens your default browser — no
data ever leaves the machine (CUI-safe; the AI defaults to local Ollama / offline Null).

**Closing the tool turns everything off.** Every page sends a heartbeat; when you close the
last browser window the server detects the browser is gone and **shuts itself down** within a
few seconds — no orphaned process. The **Quit** link in the top nav stops it immediately.

## Install (once)

```bash
python -m venv .venv && . .venv/bin/activate      # (Windows: .venv\Scripts\Activate.ps1)
pip install -e .                                   # installs the `schedule-forensics` command
```

## Windows — desktop icon (recommended)

From the activated venv, run the installer once to get a **Desktop icon** you double-click:

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
powershell -ExecutionPolicy Bypass -File packaging\windows\Install-Desktop-Shortcut.ps1
```

This creates **“Schedule Forensics”** on your Desktop (with the tool's own icon). Double-click it:
the tool starts with **no console window** (it runs `pythonw.exe -m schedule_forensics.launcher`),
opens your browser, and **stops automatically when you close the window**. No admin rights are
needed — the shortcut lives in your own Desktop folder.

- **The icon is the tool's unique mark** — the dark dashboard tile with the white ▲, the
  red/blue/green Gantt waterfall, and the gold dashed **data-date line** cutting through it —
  rendered at 256/128/64/32/16 px so it is crisp on the desktop, taskbar, and Alt-Tab. The same
  image is the **browser-tab favicon**, so the running tool matches the icon you clicked.
- Portable alternative (no installer): double-click **`packaging\windows\Schedule Forensics.vbs`**
  — works when `pythonw` is on PATH (i.e. the venv is active/installed).
- Regenerate the icon (Windows `.ico`, Linux `.png`, web favicon — always in sync) with
  `python packaging\make_icon.py`.

## Run (other ways / other OSes)

- **Any OS (terminal):** `schedule-forensics`  (or `python -m schedule_forensics.launcher`)
- **Linux desktop icon:** copy `schedule-forensics.desktop` to `~/.local/share/applications/`
  (and/or `~/Desktop/`); mark it trusted/executable, and point its `Icon=` line at your clone's
  `packaging/schedule-forensics.png` (absolute path) for the tool's mark.
- **macOS:** double-click `schedule-forensics.command` (run `chmod +x` on it once).

All paths call the same entry point (`schedule_forensics.launcher:main`). The server binds
**127.0.0.1 only** and refuses any non-loopback host. You can also stop it with `Ctrl-C` in a
terminal, **Quit** in the app, or simply by closing the browser window.

## Local AI (optional)

The dashboard works offline with the deterministic Null backend. For AI-polished narratives,
install [Ollama](https://ollama.com) and pull a local model; the in-app **AI Settings** panel
lists/pulls/selects models and shows the persistent classification banner. The tool only ever
reaches a **loopback** model server while CLASSIFIED.
