# ADR-0469 — WP7: the AI transaction log under Law 1 by execution (a closed error vocabulary — a malformed gateway reply was landing in the audit record), and the twenty-one never-adverse routes driven adversely (two 500-class defects and one fabricated zero fixed red-first)

- **Status:** Accepted — 2026-09-06 (POLARIS² audit campaign, WP7 — thin dimensions; SOLO lead, fix-as-verified)
- **Version:** 1.0.241
- **Extends:** ADR-0402 (the gateway + `ai/txlog.py`), ADR-0403 (the credential never reaches the log), ADR-0455 (RC-01/RC-02, the route-coverage instrument), ADR-0467 (RC-02's never-2xx list), ADR-0313 (refuse rather than store a magnitude the operator never entered), ADR-0393 (QC-1/QC-2)
- **Ledger:** `docs/STATE/AUDIT-2026-08-27.md` (WP7 section)
- **Shipped:** `ai/txlog.py` (`error_summary`) · `ai/gateway.py` (the `*.done` failure record) · `web/app.py` (`/sra/branch`, `/sra/jcl-config`, `/sra/risk`) · `web/settings.py` (the retention sentence) · `tests/ai/test_txlog_law1.py` (8, NEW) · `tests/web/test_rc02_adverse_paths.py` (64, NEW)

## Context

WP7 is the campaign's "thin dimensions" pass: the parts of the tool that hold the strongest claims with
the thinnest coverage. The kickoff put `ai/txlog.py` first because it is Law 1's own record — every
off-machine transmission the approved gateway makes is written there BEFORE it leaves (ADR-0402) —
and the record's three promises (what LEAVES is recorded before it leaves; what is LOGGED can never make
the log itself CUI; what is RETAINED outlives the session) had one executable pin each, all through an
injected opener. RC-02 (ADR-0455, re-derived by ADR-0467) named fifteen POST routes and six exports that
the whole suite reached but never drove adversely — no 4xx/5xx, no empty-state 2xx — so their fail-soft
contracts were docstrings, not measurements.

### The transaction log — refutation attempts, by promise

| promise | the attempt | what execution showed | verdict |
| --- | --- | --- | --- |
| **what is logged** — "error text is the short sanitized probe reason, never a raw exception body" | a loopback peer answering a MALFORMED status line carrying a sentinel, reached through the REAL `urllib` opener (only the allowlist predicate patched) | `http.client.BadStatusLine(line)` carries the reply's first line verbatim; `probe_error_text`'s fallback is `str(exc)`; the sentinel landed in the `generate.done` record. A misbehaving gateway's reply is model output derived from the prompt — the log had a path to becoming CUI | **CONFIRMED-FIXED** — `txlog.error_summary`: an HTTP status, one of three fixed transport reasons, else the exception's CLASS name; the settings diagnostic keeps the fuller local text |
| the record's vocabulary | every request kind, both outcomes, through an opener whose failure message carries the sentinel | keys ⊆ {ts, kind, endpoint, model, classification, prompt_sha256, prompt_bytes, response_bytes, ok, error}; `error` matches the closed shape only after the fix | **PINNED** (a new field or free text goes red) |
| **what leaves** — nothing before consent | the endpoint chosen, the acknowledgment withheld; `GET /settings` with the real opener replaced by a spy | no call, no record. The operator-initiated catalog probe (`/api/ai/models?kind=gateway`) DOES transmit before the acknowledgment — a body-less `GET /v1/models` carrying the session's key — and is recorded as `probe.sent/done` + `models.sent/done` with no prompt fields | **REFUTED as a defect; DISCLOSED** — the probe carries no schedule content and is the dropdown's own fetch (ADR-0402's design); pinned as such |
| what leaves — the transport inventory | a census of every module whose code names a transport primitive (`urllib.request.Request(`, `build_opener(`, `socket.*(`, `subprocess.*(`, `HTTP*Connection(`) | exactly six: `ai/gateway.py` (the recorded remote path), `ai/ollama.py`, `ai/ollama_process.py` (loopback), `launcher.py` (the loopback handshake), `web/system.py`, `importers/mpp_mpxj.py` (local binaries) | **PINNED** — a seventh is a Law-1 event by name |
| **what is retained** — the record outlives the session | DEFAULT paths under a scratch HOME (every suite override removed): a probe record, then `ScheduleCache.clear()` (the quit path, ADR-0335) and `POST /session/wipe` | the log lives under `~/.local/state`, the cache under `~/.cache`; both wipes leave the record whole | **REFUTED as a risk; PINNED** (a clear that reaches the state dir goes red) |
| a completion record is best-effort | the opener replaces the log FILE with a directory between `sent` and `done` | the answer is returned; the sent record documented the egress | **PINNED** |
| retention is SAID | the armed ON notice on /settings | it named the path but not the rule | **CONFIRMED-FIXED (disclosure)** — "append-only; retained until you delete it — nothing in the tool purges it" |

### RC-02 — the twenty-one routes driven adversely

Every route was driven with what a form can carry: an empty session, an unknown key or UID, a value
outside its range, `nan` / `inf` / `1e999` (`float()` parses all three), a double sign, a superscript
digit, a host-bearing redirect target. Eighteen answered as their docstrings promise — a LOCAL 303 with
the session state unchanged, a clamped value, or a refusal by name — and those contracts are now pinned
(`test_rc02_adverse_paths.py`, 64 cases). Three did not:

| route | measured (pre-fix) | verdict |
| --- | --- | --- |
| `POST /sra/branch` | `after_uid="--5"`: `int(x) if _decimal_digits(x.lstrip("-"))` — the lstrip-then-int pattern `/sra/conditional`'s own comment (audit L5) says it replaced; `int("--5")` → **500** | **CONFIRMED-FIXED** — `_parse_uid` (positive integers, never a raise) |
| `POST /sra/jcl-config` | `target_cost="nan"` / `"inf"` / `"1e999"` under a bare `suppress(ValueError)` → stored as the JCL cost target — the one site that bypassed the audit-L2 boundary rule `_to_float` enforces everywhere else | **CONFIRMED-FIXED** — a non-finite parse leaves the stored value |
| `POST /sra/risk` | `opt_days="nan"` (or `"abc"`, or `"-3"`) on a real UID → `_to_float` fell back to 0.0 and the route stored a **`(0, 0, 0)` three-point override** — a zero-duration point mass the operator never entered, run by every later simulation | **CONFIRMED-FIXED** — a supplied field that is not a finite non-negative number is refused by name (`sra_import_msg`, ADR-0313's rule); blank fields keep the order coercion |

The six exports on an empty session: `evm` · `scurve` · `risks` · `ribbon` 422, `workbench` 400, `mission`
a valid workbook whose one row says why (ADR-0268, by design) — pinned, with an unknown format 404 on all
six. Observed, left: the 400/422 split between `workbench` and its siblings (a convention, not a figure).

## Decisions

1. **An audit record's error field has a closed vocabulary.** `txlog.error_summary` is the boundary; the
   gateway's failure record uses it; `probe_error_text` stays what it is — a LOCAL diagnostic.
2. **The pre-consent catalog probe is design, disclosed** — body-less, key-bearing, recorded. Changing it
   would mean a model dropdown that cannot populate before the acknowledgment; that is the operator's
   call, not an audit fix.
3. **The transport inventory is pinned by census**, not by memory: six modules, named.
4. **Refuse by name, never a zero** — `/sra/risk` joins `/sra/risk-register` (ADR-0313) and `/sra/factor-table`
   (ADR-0467 MC-07); `/sra/branch` and `/sra/jcl-config` join every other route on `_parse_uid` / the
   finite-boundary rule.

## Verification (QC-1)

- **Red first, on the pristine tree:** `test_txlog_law1.py` 3 failed / 4 passed (the sentinel IN the
  record; the bounded-error pin; the missing helper); `test_rc02_adverse_paths.py` 7 failed / 57 passed
  (the 500, four non-finite targets, the `(0, 0, 0)` override, and one premise of mine — the mission note
  is asserted on its ROW text because Excel truncates a sheet name to 31 characters).
- **Green:** 8 + 64; the neighbouring suites the fixes touch (`tests/ai` · the SRA and JCL web modules ·
  the gateway settings · the route-coverage and egress guards) **537 passed**; mypy --strict 163 files;
  bandit exit 0.
- **Mutation, on scratch copies of the FINAL code under `PYTHONPATH` (every anchor asserted — a
  mutation that does not land aborts the battery), each RED BY NAME — 10/10:** the `.done` error
  reverted to `probe_error_text` · the prompt text logged · the consent gates dropped (factory + the
  settings early return) · `clear()` reaching the state dir · the success `.done` no longer best-effort
  · a seventh transport module · the branch endpoints back to `int()` behind `lstrip` · the non-finite
  cost target stored · the `(0, 0, 0)` override stored · the retention sentence dropped.

## Deliberately NOT done (measured, left alone)

- The pre-consent catalog probe (decision 2). · The `workbench` 400 vs the siblings' 422. · The record
  carries no schema version and no session/file correlation (by design: no CUI, no names) — a design
  question for WP8, not a defect. · `~/.local/state` on Windows (works; unidiomatic). · Concurrency of
  two PROCESSES appending one log (single-process app; the lock covers threads).
- The `/margin/confirm` contract that turns an all-unknown tick list into a deliberate "no margin"
  (`frozenset()`) — documented behaviour, pinned as such, named here.

## Consequences

- The audit log can no longer be made CUI by a reply; what leaves, what is logged and what is retained are
  each pinned by a check that was watched fail. RC-02's never-adverse list is empty: 21 routes carry an
  adverse test each; three defects that no user had reported are gone.
- Version 1.0.240 → **1.0.241** with ADR-0470; wheel + nine installers rebuilt in lockstep as the LAST step.
