# ADR-0136 — AI consistency: deterministic decoding + grounding/blind-spot regression guards

## Status

Accepted.

## Context

A "Claude Council" review of *how to make the tool's responses most accurate and most consistent within
its scope* concluded: **accuracy is oracle-bound** (it needs the operator's Fuse/`.aft`/`.mpp`/SSI
reference exports — artifact-gated) while **consistency is model-bound** and largely fixable in-env. The
CPM engine and metrics are already deterministic; the variability is the **local model's prose** and the
**parity gate's blindness** to populations the goldens don't contain. This batch lands the in-env
consistency wins (Council steps 2–4); the oracle-dependent accuracy work stays gated on the operator's
files (`audit/PARK-LIST.md`).

## Decision

1. **Deterministic decoding for every local backend.** `OllamaBackend.generate` and
   `OpenAICompatBackend.generate` now send `temperature 0` + a fixed `seed` (and `top_p 1.0` for Ollama)
   via shared constants in `ai/backend.py` (`DETERMINISTIC_TEMPERATURE/SEED/TOP_P`). The same prompt now
   yields the same answer run-to-run — a forensic tool must not give two analysts different prose for the
   same question. The engine was already deterministic; this removes the model as a variability source.
   (Law 1 unaffected — both backends remain loopback-validated, stdlib-only, fail-closed.)

2. **Golden Q&A grounding regression.** `tests/ai/test_qa_golden.py` pins, for the committed Project5
   golden, *which cited-fact family each representative analyst question retrieves* (hard constraints,
   finish forecast, completion, float, findings, the Layer-A DCMA pass rate). The model is variable; the
   **grounding** must be stable, so a change to fact-building/selection that silently moves what a
   question is answered from fails loudly. Deterministic (exercises `build_fact_sheet` + `relevant_facts`,
   no live model).

3. **Blind-spot population guard.** `tests/engine/test_blind_spot_populations.py` exercises — in one
   synthetic schedule — the populations the parity goldens lack (a summary, an inactive task, an elapsed
   in-progress activity) and pins that `non_summary` / the CPM network / the metric populations apply the
   summary + inactive exclusions (ADR-0128) and score the elapsed activity correctly (NEW-1). This closes
   the "gate is blind to these populations" gap that once let the inactive-task and Float-Ratio bugs hide.

## Consequences

- AI answers are now **reproducible** for a given prompt + model; the figure layers (Layer A/B,
  ADR-0133/0135) already made AI *numbers* sourced/verified, and this makes the *prose* stable too.
- The grounding and blind-spot guards convert two classes of silent regression (what a question is
  grounded on; whether a blind-spot population leaks into a metric) into loud test failures.
- **No parity number moves; no engine/metric math changed** — determinism is a request parameter, the
  new tests are additive. Full gate green.

## Alternatives considered

- **Leave decoding at the server default.** Rejected: server defaults sample (temperature > 0), so the
  same question can give different prose across runs — unacceptable for a testimony tool whose outputs may
  be quoted.
- **Pin determinism only in strict mode.** Rejected: consistency should not depend on the operator's
  figure-mode choice; the decoding parameters are mode-independent.
- **Chase the accuracy ceiling (data-date CPM, Fuse parity) here.** Out of scope and artifact-gated:
  ADR-0108 records two reverted data-date attempts, and `ENGINE==FUSE` needs the operator's exports
  (`audit/PARK-LIST.md`). Those remain the operator-gated next step.
