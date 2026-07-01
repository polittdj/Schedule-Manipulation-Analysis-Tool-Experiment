# ADR-0142 — Instruction-wrapped polish prompt, session lock, and operational polish

## Status

Accepted. Final batch (R6) of the 2026-07-01 QC audit remediation.

## Context / Decisions

- **D17 (MEDIUM) — the narrative/briefing "polish" sent the bare engine sentence as the whole
  prompt.** A completion model *continues* a bare declarative sentence rather than rephrasing it,
  so nearly every generation failed `preserves_figures` and burned up to `gen_timeout` per
  statement for a verbatim fallback. **Fixed:** all three polish paths (`ai/narrative.py`,
  `ai/briefing.py`, `web/app.py`) send an instruction-wrapped rephrase prompt
  (`polish_prompt`: keep every figure exactly, add nothing, reply with the rewrite only), and a
  `clean_polish` normalizer strips a leading `REWRITE:` and returns `""` on prompt-echo
  (scaffolding in the reply) so `reattach` falls back to the verbatim engine sentence — fail
  closed. The Null backend now *skips* generation outright in every path (its echo IS the verbatim
  text), instead of relying on echo-through. The `reattach` figure/loaded-term gate is unchanged
  and still verifies whatever a live model returns.
- **D18 (LOW) — SessionState had no concurrency guard.** Routes are sync `def` (Starlette
  threadpool ⇒ real concurrency) and the scope/analysis caches were mutated with no lock; the QC
  audit live-reproduced a `KeyError` on `/trend` under concurrent filter+render hammering.
  **Fixed:** a reentrant `threading.RLock` on `SessionState`; `scope` / `set_filter` /
  `set_target` / `ordered` / `ordered_versions` / `analysis_for` and the wipe route's multi-step
  reset are atomic. Single-operator local tool: contention is negligible, and first-compute
  serialization is bounded by the analysis cache.
- **D25 (LOW) — XER dropped-link tolerance was invisible.** The drop-and-count path logged at
  INFO, which the default logging config never surfaces, while DCMA logic-density denominators
  silently changed. **Fixed:** the drop count logs at WARNING.
- **INFO — per-file upload cap.** Whole-file reads are memory-bound; a 500 MB per-file cap rejects
  an oversized upload with a named reason instead of exhausting RAM (batch count was already
  capped by `MAX_FILES`).
- **INFO — JSON-in-`<script>` escape consistency.** The two embeds using the weaker
  `</`-only escape (verified non-exploitable in the audit) now use the stronger `\\u003c` form the
  other embeds use — one convention everywhere.

## Consequences

- Polish becomes a functioning feature on live local models instead of per-request dead weight;
  its safety posture is unchanged (reattach gates figures; echo/scaffolding forces the verbatim
  fallback; Null costs zero). Test fakes now model an instruction-following reply (extract the
  STATEMENT, transform, return the rewrite).
- The reproduced SessionState race class is closed; upload memory is bounded; XER link drops are
  operator-visible; one script-embed escape convention.
- Full gate + parity green.

## Alternatives considered

- **Retire the polish feature.** Rejected: with a real instruction, local instruction-tuned models
  (the deployment target) can rephrase within the figure gate; the feature was dead only because
  of the missing instruction.
- **Lock-free snapshot reads instead of an RLock.** Rejected: covers iteration races but not the
  read-modify-write cache updates; the RLock is provably sufficient and contention-free for a
  single operator.
