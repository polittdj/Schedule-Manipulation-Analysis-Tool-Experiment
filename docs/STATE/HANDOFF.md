# Handoff — 2026-08-03c (External audit adjudicated; the logging-isolation leak closed; ADR-0345; v1.0.160)

> ## STATUS (current) — **IN FLIGHT.** 13 external audit claims adjudicated by measurement; P0-1 fixed.
> Branch `claude/polaris-phase-4-engine-zpo69e` from `origin/main` at **`1119162`**.
> ADR-**0345**, **v1.0.160**. Nothing else in flight (#525, #526 merged earlier today).
>
> ## The audit verdict — 13 claims, every one tested
> **No product-correctness defect was found.** No computed number, metric, or rendered figure is
> implicated. Full evidence in `audit/EXTERNAL-AUDIT-20260803.md`.
>
> | # | claim | verdict |
> | --- | --- | --- |
> | 1 | dependency reproducibility | structure CONFIRMED; stated failure REFUTED (clean 3.11 **and** 3.13 installs rc=0) |
> | 2 | test pollution | **CONFIRMED — 17 polluters / 4 victims, not 1** |
> | 3 | mislabeled intake files | CONFIRMED (**89**), but SCOPED to `00_REFERENCE_INTAKE/` |
> | 4 | stale risk register (R-03, R-12) | CONFIRMED |
> | 5 | CUI hook coverage | CONFIRMED, wider than reported |
> | 6 | license placeholder | CONFIRMED verbatim |
> | 7 | mutable action tags + unchecksummed ollama | CONFIRMED |
> | 8 | `check` doesn't gate on `browser` | mechanism CONFIRMED; **policy half unverifiable here** |
> | 9 | MPXJ class == source | **REPRODUCED** (`1a2c05dc…` both) |
> | 10 | installer lockstep 62 | **REPRODUCED** (52+4+6, all pass) |
> | 11 | egress guards 68 | **REPRODUCED** |
> | 12 | parity 49 + oracle limit | **REPRODUCED**; limit real and already documented in-repo |
>
> **#3 is scoped, and that is the important part.** Verified intact: **65/65** shipped static
> assets, both `.aft` libraries (**1443** / **1403** `<Metric>`), **16** golden MSPDI + **1** XER +
> **20** `.mpp`. The corruption is a bulk-upload name/content rotation in intake only.
>
> ## What landed — ADR-0345
> `configure_logging()` sets `propagate=False` (correct, Law 1) and **17 tests** across
> `test_cli_guards.py` (1) · `test_launcher.py` (12) · `test_logging_redaction.py` (4) left it set.
> `caplog` captures by propagation, so 4 importer calendar-warning tests read an empty
> `caplog.text`. **Version-sensitive:** pytest **8.0.2 / 8.4.2 FAIL** (full suite 5 failed / 3301
> passed), **9.1.1 passes** — it also attaches its handler to the logger itself and masks the leak.
> The project declares `minversion = "8.0"` and `pytest>=8` unbounded, so the resolver decides.
>
> Fix: **one autouse fixture**, `tests/conftest.py::_restore_redacting_logging`, snapshot+restore.
> Per-site requests were rejected — they fix 17 sites and not the 18th.
>
> ## Verification
> `tests/test_logging_isolation.py` (2) pins the **state, not the symptom** — a caplog test would
> pass on pytest 9 either way (coverage theatre). Revert `autouse=True`→`False`: `test_b` **fails
> on BOTH 9.1.1 and 8.4.2** while the true-positive twin `test_a` passes; the 4 real victims fail
> under 8.4.2. With the fix, pytest 8.4.2: polluter+victims **126 passed**, the three polluting
> modules + all importers **404 passed**.
>
> ## Next — the audit's remaining P0/P1 (Opus 5 until Thu 01:00)
> **P0-2 constraints/upper bounds** (root cause of #1 AND #2 — `filterwarnings` already silences
> the starlette httpx deprecation instead of bounding it; add a constraints file + a floor-version
> CI leg) · **P0-3** `pytest.importorskip` in `tests/perf/test_observer_storm.py` and
> `tests/web/test_launch_invalidation.py` (they ERROR, not skip, without playwright) ·
> **P1** intake manifest + extension↔content regression test · risk-register reconcile (R-03/R-12)
> · CUI hook hardening (`.json` content sniff, `.p6xml`, `*.mpp.*`) · Action SHA pinning.
> **Fable 5 (Thu):** CC-01 · SRA-LEGACY · V3. **Operator only:** license, branch-protection read,
> intake re-upload, proprietary-tool reruns for #12.
>
> ## Carried forward, unchanged
> **The `/analysis` focus→tip family, re-characterised 2026-08-03:** still do NOT chase, but it
> is NOT "intermittent" here — `test_float_tip_dismiss` fails **3/3** locally and **identically
> on `origin/main` with changes stashed**. Cause: `playwright wait_for_function` **4000 ms**
> timeout under container load. Pre-existing ✔, never fails on CI ✔, deterministic locally. `pgrep -f` self-matches.
> pytest stdout to a FILE is block-buffered (`python -u`). `cd` persists across Bash calls.
> `--bad` is the red token. Never `git checkout <file>` to undo a test mutation — `cp` from a
> scratchpad copy (used for both revert probes this session). `/briefing`, `/path`, `/compare`
> still carry no `page-lede`; the `/groups` "Activities" column still counts summary rows.
>
> **New this session:** *an audit's own uncertainty markers are the test plan* — but so is its
> confidence. Three "VERIFIED CONTROL" items reproduced exactly, and the one HIGH it was surest
> about was **17× larger** than reported. Verify the confident claims too. Also: my own magic-byte
> sniffer produced 3 false positives (a 64-byte window splitting a multi-byte char) — the tool you
> audit with needs auditing.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
