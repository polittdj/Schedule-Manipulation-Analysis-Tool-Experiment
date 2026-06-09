# Desktop launcher & shortcuts

One-click, **fully offline** launch of the Schedule Forensics dashboard. The launcher starts
the local server on `127.0.0.1` (a free ephemeral port) and opens your default browser — no
data ever leaves the machine (CUI-safe; the AI defaults to local Ollama / offline Null).

## Install (once)

```bash
python -m venv .venv && . .venv/bin/activate      # (Windows: .venv\Scripts\activate)
pip install -e .                                   # installs the `schedule-forensics` command
```

## Run

- **Any OS (terminal):** `schedule-forensics`  (or `python -m schedule_forensics.launcher`)
- **Linux desktop icon:** copy `schedule-forensics.desktop` to `~/.local/share/applications/`
  (and/or `~/Desktop/`); mark it trusted/executable. It runs the `schedule-forensics` command.
- **macOS:** double-click `schedule-forensics.command` (run `chmod +x` on it once).
- **Windows:** double-click `schedule-forensics.bat` (or create a shortcut to it on the Desktop).

All shortcuts call the same entry point (`schedule_forensics.launcher:main`). The server binds
**127.0.0.1 only** and refuses any non-loopback host. Stop it with `Ctrl-C`.

## Local AI (optional)

The dashboard works offline with the deterministic Null backend. For AI-polished narratives,
install [Ollama](https://ollama.com) and pull a local model; the in-app **AI Settings** panel
lists/pulls/selects models and shows the persistent classification banner. The tool only ever
reaches a **loopback** model server while CLASSIFIED.
