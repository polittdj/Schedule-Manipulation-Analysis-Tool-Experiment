# ADR-0232 — MPXJ saved-views sidecar export + the filter parity oracle (feature #10, PR-B)

## Status

Accepted. PR-B of the flagship "Groups & Filters" feature #10. PR-A (ADR-0231) landed the criteria
model and the faithful evaluator but left `Schedule.saved_filters` / `saved_groups` empty — no ingest
path existed. This PR makes the vendored Java converter export every `.mpp`'s saved filters + groups
to a sidecar JSON, wires the importer to load it, and gate-locks our evaluator's match sets to MPXJ's
own `Filter.evaluate()` on the operator's real reference file.

## Context

MSPDI XML — the interchange format the vendored `MpxjToMspdi` converter emits and the pure-Python
importer parses — **cannot carry saved views**: the MSPDI schema has no filter/group definitions, so
converting a `.mpp` silently dropped exactly the definitions feature #10 must reproduce. The
definitions exist only in the native `.mpp`, which only the out-of-process MPXJ JVM can read (the
tool's one sanctioned native parser; no JPype — ADR-0018/0193 posture).

Separately, PR-A's evaluator semantics were derived from the MPXJ 16.2.0 **bytecode** and tested
against hand-built populations. That proves the *rules* as read; it does not prove the whole chain
(`.mpp` → MSPDI conversion → model → raw-field resolver → evaluator) reproduces what MS Project /
MPXJ actually match on a real 2,126-task file.

## Decision

1. **Sidecar, not schema abuse.** Every successful conversion (one-shot **and** `--server` batch mode)
   now also writes `<output>.views.json` beside the MSPDI: all saved filters (name, task/resource
   flag, show-related-summary-rows, prompt count, and the full recursive criteria tree with
   `literal` / `field` / `prompt` / `null` operands, each literal carrying MPXJ's runtime type name)
   and all groups (name, show-summary-tasks, and each clause's field / ascending / groupOn /
   interval / startAt). The exporter dedupes the built-in filters the MPP reader registers in both
   the task and the resource list (key: type + name). JSON is emitted by a dependency-free string
   writer inside `MpxjToMspdi.java` — no Jackson coupling, still one vendored class file.
   A file with no saved views gets an empty sidecar; a *missing* sidecar (older converter, non-.mpp
   input) simply means "no views".
2. **Ingest = parse + attach.** `importers/msp_views.py::parse_views_json_text` maps the sidecar
   one-to-one onto the frozen `SavedFilter`/`SavedGroup` models; `parse_mpp` reads the sidecar inside
   the conversion tempdir and attaches the views via `model_copy`. A **malformed** sidecar raises
   `ImporterError` — it is produced by our own converter in the same conversion, so damage means the
   conversion itself is suspect; fail loud, never silently drop a saved view (Law 2). The MSPDI/XER
   import paths are untouched (those sources never had saved views to lose).
3. **The parity oracle.** A new converter mode — `MpxjToMspdi --eval <input> <out.json>` — evaluates
   every prompt-free saved task filter with **MPXJ's own `Filter.evaluate()`** over every task and
   dumps `{filter name: [matching unique ids]}`. A `parity`-marked test converts the operator's real
   `Large Test File Leveled.mpp` and asserts `engine.msp_filters.select()` returns **exactly** the
   oracle's UID set for each of the 9 prompt-free filters (the 2-prompt "Date Range…" is pinned by
   unit tests instead, since an oracle run cannot answer prompts). Result on the real file: **9/9
   exact-set matches over 2,126 tasks** — including `_MCTasks` (943 matches; 8 AND'd conditions with
   a field-to-field `Duration9 > Duration8` and an `Actual Finish EQUALS <null>` test). "Faithful
   reproduction" is now proven against the reference implementation, not assumed.

## Consequences

- `.mpp` uploads now populate `Schedule.saved_filters` / `saved_groups` (JSON round-trip already
  handled since SCHEMA_VERSION 2.7.0); PR-C/D can consume them with zero further ingest work.
- The evaluator is gate-locked to MPXJ: a future semantic regression in `msp_filters.py` /
  `msp_field_resolver.py` fails `pytest -m parity` on CI (Java + the committed reference `.mpp` are
  both present there), in addition to the PR-A unit pins.
- The vendored `tools/mpxj/classes/MpxjToMspdi.class` is recompiled (`--release 17`, still a single
  class file); the converter's header comment documents all three modes. Deployed installs pick the
  new converter up via the existing tools-beside-venv layout (ADR-0193) on the next installer run.
- Non-`.mpp` sources (MSPDI XML, XER, the tool's own JSON) still carry no saved views — correct, as
  their formats define none (the tool's JSON round-trips whatever a `.mpp` ingest attached).
- Test-suite fakes that emulate the converter without writing a sidecar keep working: the absent
  sidecar path is the documented "no views" behavior.
