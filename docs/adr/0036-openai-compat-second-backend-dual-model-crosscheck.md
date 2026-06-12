# ADR-0036 — The second local backend (OpenAI-compatible) and the dual-model cross-check

Date: 2026-06-12 · Status: accepted

## Context

The closing piece of the operator's M18 "AI at full power" order: *"add a SECOND local
backend (any OpenAI-compatible local endpoint, e.g. LM Studio/llamafile) and a
dual-model cross-check/collaboration mode. Loopback-only egress stays non-negotiable."*

## Decisions

1. **`OpenAICompatBackend`** (`ai/openai_compat.py`): any server speaking the OpenAI
   ``/v1`` dialect — LM Studio (default ``http://127.0.0.1:1234``), llamafile (``:8080``),
   text-generation-webui, vLLM. Same construction guarantees as `OllamaBackend`:
   **stdlib-only HTTP** (`urllib`; the egress guard forbids requests/httpx) and
   **loopback enforced at construction** (`CUIEgressError` on a remote host — Law 1).
   Probes (``/v1/models``) use the 2s timeout; ``generate`` is one non-streaming
   ``/v1/chat/completions`` call; ``pull_model`` raises (these servers load models in
   their own UI). Malformed responses degrade to empty prose, never an exception.
2. **Usable as the primary backend**: `AIConfig.backend` gains ``"openai"`` and
   `route_backend` routes to it when available — fail-closed to Null otherwise,
   identical to the Ollama path. The settings page gets the backend option and a
   loopback-only endpoint field (`AIConfig.openai_endpoint`); the settings handler
   additionally resets any non-loopback endpoint to the default so a typo'd remote
   host can never sit in the config looking accepted.
3. **The dual-model cross-check** (`AIConfig.second_backend`: ``none`` | ``ollama`` |
   ``openai``; `second_model` id; cloud is not constructible as a second model by
   design): when configured and reachable (probe cached with the same 15s TTL as the
   primary), **both local models answer every ask independently** in the configured
   answer mode. The response carries ``second_answer``/``second_model`` and an
   ``agreement`` note from `ai.qa.figure_agreement` — a **deterministic, engine-computed**
   multiset comparison of the two answers' numeric figures ("identical figures" vs
   "DIFFER on figures (…)" naming the disagreeing numbers). No third model judges;
   agreement is corroboration, the cited facts stay the ground truth.
4. **Surfaces**: the shared ask panel renders the second answer (indented) and colors
   the agreement note (ok/warn); the settings page reports the cross-check model's
   reachability. The narrative/briefing polish pipelines stay single-backend (verbatim
   evidence surfaces, ADR-0035 §5 unchanged).

## Closes

M18 item 4 in full (with ADR-0035). Remaining M18 items: forecast-drift animation +
locked Y-axes (5), PBIX visual reproduction (6), CPM path-evolution animation (7),
forecast explainer + trend expansion (8).
