# ADR-0528 — Every AI transaction record carries a format version and a random per-process run id (R-13 CLOSED)

**Status:** Accepted · **Date:** 2026-09-24 · **Extends:** ADR-0402 (the AI transaction log), ADR-0469 (WP7, the log under Law 1) · **Closes:** R-13

## Context

R-13: the AI transaction record carried no schema version and no session correlation, so a reader
of `ai-transactions.jsonl` years later could not tell which record shape a line held, nor which
lines one run of the tool wrote. The row's settling condition was the operator's ruling that a
correlation id is acceptable (it carries no CUI). **Ruled 2026-09-24: yes.**

## Decision

`ai/txlog.py` adds two keys to every record, at the one writer (`record()`):

| key | value | why it cannot carry CUI |
| --- | --- | --- |
| `v` | `FORMAT_VERSION = 1` — bump when a key is added, removed or changes meaning | a constant |
| `run` | `RUN_ID = secrets.token_hex(8)` — 16 hex characters, drawn ONCE at import | random; derived from nothing on the machine or in the schedule |

The /settings "gateway ON" sentence says so ("Each record carries a format version and a random id
for the run that wrote it — no names, no paths"). TX-02's closed key vocabulary
(`tests/ai/test_txlog_law1.py::RECORD_KEYS`) is re-baselined 10 → 12, dated, so a future key
still cannot smuggle content in.

## QC-3 — assumptions attacked before the edit

| Assumption | Attack | Verdict |
| --- | --- | --- |
| `record()` is the only writer of the log | censused every reference to `txlog.`, `LOG_FILENAME`, `ai-transactions` and `jsonl` in `src/` | **held** — one writer, one calling module (`ai/gateway.py`) |
| "per process" is testable, not just "per import in one test" | the test spawns two real interpreters writing to one log | **held**, and it is the ONLY check that kills a machine-derived id |
| a literal "names nothing" check is enough | mutant: `run` = sha256(hostname)[:16] | **FELL** — the substring check passes it; the two-process test kills it |

## Verification

Red-first: `tests/ai/test_txlog_r13.py` 3/3 red on pristine. Mutation: 3/3 red by name — a
per-record id (the one-run-one-id test), a hostname-derived id (the two-process test), a dropped
version (the key test). `tests/ai` + settings: 381 passed.

## Deliberately NOT done

* No migration of existing log lines — a line without `v` is, by definition, the pre-version shape.
* No per-SESSION (browser) id: the ruling was for a per-process id with no names; a session id would
  tie records to a user's activity, which is a different question.
