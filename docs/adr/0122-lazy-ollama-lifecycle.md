# ADR-0122 — Ollama runs only when the operator enables AI, and is tidied up on close

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: ADR-0022 (desktop launcher + auto-shutdown), the M12 Ollama lifecycle
  (`OllamaLauncher`)

## Context

Operator report (Task Manager screenshot): after wiping the session, quitting the tool, and
closing the browser, Ollama was **still running** — an `ollama.exe` holding ~40% of RAM (a resident
72B model) plus the `ollama app.exe` tray. Two things were wrong:

1. **The launcher started `ollama serve` at every launch** (`manage_ollama=True` →
   `ensure_running()` on a background thread), regardless of whether the operator ever used the AI.
   So the tool spun Ollama up for sessions that never touched it.
2. **Shutdown only stopped an Ollama the tool itself had started.** On a machine where the Ollama
   **Windows desktop app** auto-starts `ollama serve` at login, the tool saw "already-running,"
   never owned it, and never freed the model RAM on close.

Operator requirement: *Ollama should run only when the user sets up the AI in the tool, and close
when the tool is closed.*

## Decision

Make the tool's Ollama management **lazy and self-cleaning**, gated on a single
`OllamaLauncher._engaged` flag set the first time `ensure_running()` is called:

1. **Lazy start.** The launcher no longer calls `ensure_running()` at launch; it hands the manager
   to `create_app(ollama=…)`. The `/settings` POST starts it (off-thread) **only when the operator
   selects the Ollama backend** (primary or cross-check). A session that never enables AI never
   starts Ollama.
2. **Tidy up on close.** `shutdown()` (run from the launcher's `finally` + `atexit`):
   - is a **no-op if the tool never engaged Ollama** — a pre-existing Ollama the operator runs
     themselves is left entirely alone;
   - otherwise **unloads every in-memory model** (`GET /api/ps` then `POST /api/generate` with
     `keep_alive: 0`, std-lib `urllib` over loopback only — Law 1), freeing the model RAM **even
     when the tool only adopted a running server**; **terminates the `ollama serve` it started**
     gracefully (if any); and then — operator's explicit choice — **stops any Ollama server still
     running**, including one the Windows desktop app (tray) started that the tool merely adopted
     (`taskkill /F /T /IM ollama.exe` on Windows, `pkill -x ollama` elsewhere — local OS tools, no
     network, best-effort). So closing the tool leaves no Ollama server running.

## Consequences

- Ollama is started by the tool **only** on AI enable, and on tool close the model RAM is freed and
  **the Ollama server is stopped** — not just the `serve` the tool launched, but any server still
  running (e.g. one the Windows tray started that the tool adopted). Closing the tool no longer
  leaves a resident model or a running server. Per the operator's choice this stops a server the
  tool did not start; the trade-off (another app using the same local Ollama loses it) is accepted
  on a single-operator workstation, and is only reached when the operator actually enabled the AI.
- **The one piece the tool cannot own:** the Ollama Windows desktop **app** (`ollama app.exe`)
  re-launches a server **at next login**. The tool stops the *server* on close but does not remove
  the tray app, so the AI Settings page and `docs/CONNECT-A-BIGGER-AI-MODEL.md` tell the operator
  how to disable that auto-start (tray → Settings → uncheck "Run at login", or Windows Startup apps)
  so Ollama runs *only* with the tool from then on.
- No model/schema change. Tests: `OllamaLauncher` adopt-vs-start, unload-on-close, and
  no-op-when-never-engaged; the launcher hands the manager to the app without starting it; the
  settings POST starts it lazily for the Ollama backend (and is a no-op without a manager). Std-lib
  `urllib` keeps the net-egress guard green.
