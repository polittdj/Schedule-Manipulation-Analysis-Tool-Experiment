# ADR-0071 — Local AI that just works: auto-manage Ollama, longer probe, install-aware model picker

Date: 2026-06-18 · Status: accepted

## Context

Two operator requests, both about making the local AI actually run on their machine (a managed
corporate Windows laptop):

1. *"Make it so that when the tool is activated by clicking the desktop icon, Ollama is also
   activated automatically, and when the tool is shut off Ollama is shut off."*
2. *"The Local AI is still not working. Fix it."* — after ADR-0070 shipped its diagnostics, the
   settings page reported **"timed out"** (not "connection refused") reaching `127.0.0.1:11434`: a
   *direct* loopback connection that hangs rather than being refused, which on a corporate laptop is
   the endpoint-security software inspecting each new local connection and pushing the first response
   past the 2-second probe window. Then, once Ollama was reachable, the diagnostic correctly caught
   the next blocker: the configured model `llama3.1:8b` **isn't installed** — the operator has
   `llama3.2:latest`, `schedule-analyst:latest`, `qwen2.5:7b-instruct`.

## Decision

1. **Auto-manage a local Ollama (`ai/ollama_process.py` `OllamaLauncher`).** On desktop launch the
   tool starts a local `ollama serve` if one isn't already listening, so Ask-the-AI works without the
   operator starting Ollama by hand, and stops it again on shutdown — **but only if we started it**
   (an Ollama the operator already had running is used as-is and never killed). The launcher
   (`launcher.main`) runs `ensure_running()` on a background thread (never blocking the server/browser)
   and calls `shutdown()` in a `finally` after `serve()` returns plus via `atexit` as a backstop. All
   loopback/local: the child is pinned to a loopback `OLLAMA_HOST` and we never run `ollama pull`
   (which would fetch over the network), so nothing leaves the machine (Law 1). Every bit of process
   I/O (find the binary, probe the port, spawn, terminate) is injectable, so the lifecycle is
   unit-tested without a real Ollama or subprocess. `manage_ollama` defaults on; the entry point can
   disable it.
2. **Generous availability-probe timeout (2 s → 8 s, `ai/ollama.py` / `ai/openai_compat.py`).** A
   local server that is merely *slow* to answer the first request (the endpoint-security latency
   above) now reads as reachable, while a genuinely dead/dropped port still can't stall the page
   indefinitely. `generate`/`pull` keep the long 120 s timeout.
3. **Install-aware model picker (`/settings`).** When a real local backend is active and reporting its
   installed models, the **Model** field becomes a dropdown of those models — one click to select,
   e.g., a purpose-built `schedule-analyst:latest`, instead of a free-text box the operator must match
   exactly. The configured model is always kept as a (selected) option, flagged *"— not installed"* if
   absent, so a Save never silently loses it; the offline diagnostic now points at the dropdown. A
   Null/offline backend keeps the plain text input (its placeholder model list is not selectable).

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. Air-gap unchanged/strengthened: `ollama serve` binds
loopback only and no model is ever pulled automatically; `ollama_process` uses a fixed
`["<ollama>", "serve"]` argv (no shell, bandit-clean). Tests: `OllamaLauncher` starts only when the
port is down, stops only what it started (idempotent), and no-ops when Ollama isn't installed; the
launcher wires `ensure_running`/`shutdown`; the probe-timeout default is pinned ≥ 8 s; the settings
Model field renders as an installed-model dropdown with the configured-but-missing model flagged.
Full suite **922 passed**, 3 skipped; engine cov 97%; overall 95%; ruff/format/mypy/bandit clean.
