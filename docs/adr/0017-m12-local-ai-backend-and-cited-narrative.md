# ADR-0017: M12 local-AI backend (Ollama) + cited narrative, CUI fail-closed

- **Status:** Accepted
- **Date:** 2026-06-08 (session A14 — Phase 2 build, milestone M12, continuous A7 sitting)
- **Relates to:** §6.D (AI story, cited), §6.F (local AI default + model mgmt), §6.G/§0 (data locality), `BUILD-PLAN.md M12`
- **Builds on:** ADR-0006 (egress guard / net_guard), ADR-0015 (Finding/Citation), ADR-0016 (manipulation/trend)

## Context
§6.F wants a **local** AI (Ollama default) with in-app list/pull/select, §6.D wants it to
"generate a story" with **every statement cited**, and §0/§6.G forbid any CUI egress. The
challenge is to add a model layer without (a) any forbidden HTTP distribution entering the
runtime (the egress guard fails CI otherwise) or (b) the model ever fabricating or leaking.

## Decision
1. **Pluggable backend (`ai/backend.py`).** An `AIBackend` `Protocol` (`generate`,
   `list_models`, `pull_model`, `is_available`, `is_local`) with `AIConfig`
   (classification, backend, model, endpoint). Default config = **CLASSIFIED + local Ollama**.
2. **`NullBackend` is the default/fallback (`ai/null.py`).** Deterministic, offline, always
   available; `generate` returns the prompt **verbatim** (no model → the cited findings are
   emitted exactly). Used in CI and as the fail-closed target.
3. **`OllamaBackend` is stdlib-only over loopback (`ai/ollama.py`).** Talks to
   `127.0.0.1:11434` with `urllib.request` — **no** `requests`/`httpx`/cloud SDK, so the
   runtime dependency set stays clean and `tests/guards/test_egress.py` stays green. The
   endpoint host is validated with `net_guard.is_loopback_host` **at construction** — a
   remote host raises `CUIEgressError` (fail closed; a CUI project can never be pointed at a
   remote model server). The HTTP opener is injectable, so list/pull/generate are unit-tested
   without a live server; the real `urllib` opener is the only line needing a running Ollama
   (covered like the real-`.mpp` integration tests: exercised locally, not in CI).
4. **Fail-closed routing (`route_backend`).** CLASSIFIED returns **only** a local backend
   (Ollama if available, else Null) and **refuses cloud outright**. Cloud is returned only
   when the operator set classification = UNCLASSIFIED **and** `backend == "cloud"` **and** a
   cloud backend was supplied — and then a persistent `Banner` naming the external endpoint
   is returned with it. Anything ambiguous (ollama down, no cloud backend) falls closed to
   Null. The tool never auto-falls-back to cloud (Guardrail §0.2).
5. **Citations are enforced, not trusted (`ai/citations.py`, `ai/narrative.py`).** The
   narrative is assembled from the already-cited engine `Finding`s (recommendations +
   manipulation) as `CitedStatement`s; `assert_all_cited` is a hard gate. A backend may
   **rephrase** each statement's prose, but citations come only from the engine and are
   re-attached (`reattach`) and re-verified on the model's output — so the AI can polish
   wording yet can **never** drop a citation or invent a fact. A finding-free schedule still
   gets a cited "clean bill" statement (cites the finish-controlling activities).

## Consequences
- RTM **D1 → ✔** (AI story over the CPM/manipulation/trend signals), **D2 → ✔** (every
  statement cited, enforced), **F1/F2/F3 → ✔** (Ollama default, list/pull/select, sensible
  default model + no cloud by default), and **G1** runtime routing is now local-fail-closed
  (the egress guard + loopback validation enforce it).
- The web layer (M13) wires `route_backend` + the model-settings panel + the persistent
  banner to the UI; the narrative + banner feed the dashboard and the M17 report.
- ai: backend/narrative/null 100%, citations 100%, ollama 88% (live opener only); full suite
  402 passing; egress guard + parity gate green; no runtime deps added (stdlib transport).
