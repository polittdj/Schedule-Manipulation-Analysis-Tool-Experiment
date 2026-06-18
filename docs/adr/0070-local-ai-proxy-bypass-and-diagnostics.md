# ADR-0070 — Local AI works on a corporate laptop: bypass the system proxy + actionable diagnostics

Date: 2026-06-18 · Status: accepted

## Context

Operator report (with a screenshot of `/settings`): with **Ollama (local)** selected and
`llama3.1:8b` configured, the tool showed **"Active backend: null · installed models: null
(deterministic, no model) · cross-check model: configured but not reachable"** — i.e. the local
model never activated, so Ask-the-AI only returned the deterministic cited facts, never the
interpreted analysis. *"Fix the AI so that it will work and allow it to use its full potential to
interpret data and answer questions."*

Diagnosis: both the primary and the cross-check Ollama (same `http://127.0.0.1:11434`) read as
**not reachable**, so the availability probe (`GET /api/tags`) was failing. The interpretive
answering path (ADR-0035/0059) and its full-evidence prompt were already correct — the *only*
blocker was the backend never connecting. The operator runs on a **corporate Windows laptop**, and
the local-AI HTTP client was built with `urllib.request.build_opener(...)`, whose **default
`ProxyHandler` reads the machine's proxy settings**. On a managed laptop that routes even a
`127.0.0.1:11434` request through the company proxy, which refuses it (probe fails → backend null)
— and, worse for Law 1, a proxy in the path could forward the request body off-machine.

## Decision

1. **Never route loopback AI traffic through a system/corporate proxy (`ai/ollama.py`).** The
   shared opener is built via `_make_opener()` = `build_opener(ProxyHandler({}), _NoRedirect())`.
   The **empty** `ProxyHandler` makes `build_opener` skip its default system-proxy handler, forcing
   a **direct** connection to the loopback endpoint (the client only ever talks to a loopback host,
   enforced by `is_local_http_endpoint`, so a proxy must never be consulted — both a correctness fix
   and Law-1 hardening). `_NoRedirect` still refuses 3xx bounces. Covers both backends (the
   OpenAI-compatible one shares the opener).
2. **Actionable settings diagnostics.** A silent "Active backend: null" gave the operator nothing to
   act on. `OllamaBackend`/`OpenAICompatBackend` gain `unavailable_reason()` (and a shared
   `probe_error_text`) that maps a failed probe to a human reason — *connection refused* /
   *timed out* / *host could not be resolved* / *HTTP nnn*. The `/settings` page now shows, under the
   backend line, either **"Local AI is ON — Ollama reachable …"** or **"Local AI is OFF — could not
   reach Ollama at `<endpoint>`: <reason>"** with a fix hint (start the Ollama app / `ollama serve`,
   check the port; on a work laptop it connects directly, never via a proxy). When the server is
   reachable but the configured model isn't pulled, it says so and gives the exact
   `ollama pull <model>` (tag-tolerant match, so `llama3.1` ≈ `llama3.1:8b`).
3. **Editable Ollama endpoint.** The settings form never exposed the Ollama endpoint (it was pinned
   to the default), so a non-default port couldn't be set in the UI. Added a loopback-validated
   `endpoint` field (mirrors the existing OpenAI-compatible endpoint field; a non-loopback value
   falls back to `http://127.0.0.1:11434`, Law 1).

The interpretive mode + full cited-evidence prompt (`ai/qa.py`) are unchanged — once the backend
connects, the model already gets the whole cited picture and is asked to analyse, name risks, and
suggest recovery. No new dependency; still stdlib-only, loopback-only.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. The egress posture is *strengthened* (a proxy can
no longer sit between the tool and the local model). Tests: a regression guard builds the AI opener
under a proxied environment and asserts it carries **no** proxy while a default opener does; the new
`unavailable_reason()` is pinned (refused → reason, reachable → `None`); the settings page is pinned
to show the editable Ollama endpoint and the offline diagnostic, and to persist a custom loopback
port while refusing a remote one. Full suite **913 passed**, 3 skipped; engine cov 97%; overall
95%; ruff/format/mypy/bandit clean.
