# Handoff — 2026-08-03d (External audit adjudicated; the logging-isolation leak closed; ADR-0345; v1.0.160)

> ## STATUS (current) — **IN FLIGHT as #528.** #527 (skills) MERGED as `d57e230`.
> Branch `claude/polaris-phase-4-engine-zpo69e`, based on `1119162`, **merged with `origin/main`
> (`d57e230`)** to resolve the four state-doc conflicts #527 created. ADR-**0345**, **v1.0.160**.
> **ADR number collision resolved:** #527 took 0344 while this branch was open, so this work
> renumbered 0344 → **0345**. Check the highest ADR on disk before choosing a number.
>
> ## Already merged and usable — #527's seven project skills (`.claude/skills/`)
> `full-gate` · `prove-able-to-fail` · `render-verify` · `metric-parity` · `ui-change` ·
> `cui-guard` · `session-close`. They encode the standing rituals that prose reminders kept losing.
> **Use them** — `session-close` carries this exact rotation's shape, `full-gate` the piped-exit-code
> and per-file `node --check` traps, `render-verify` the ADR-0343 "I did not execute the page" class.
> Both skill catalogs were searched and had nothing new to install; that empty result is ADR-0344 so
> nobody repeats the search.
>
> ## The audit verdict — 13 claims, every one tested (this branch)
> **No product-correctness defect was found.** No computed number, metric, parity value or rendered
> figure is implicated. Full evidence: `audit/EXTERNAL-AUDIT-20260803.md`.
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
> Fix: **one autouse fixture**, `tests/conftest.py::_restore_redacting_logging`. Per-site requests
> were rejected — they fix 17 sites and not the 18th.
>
> `tests/test_logging_isolation.py` (2) pins the **state, not the symptom** (a caplog test would
> pass on pytest 9 either way). Revert `autouse=True`→`False`: `test_b` fails on 9.1.1 alone, 9.1.1
> after `tests/perf`, and 8.4.2 — true-positive twin `test_a` green in every case.
> **My first draft asserted a PRISTINE state and failed the full suite** — bisected to `tests/perf`,
> whose module-scoped fixture configures logging before any function-scoped one can snapshot it.
>
> ## Next — the audit's remaining P0/P1 (Opus 5 until Thu 01:00)
> **P0-2 constraints/upper bounds** (root cause of #1 AND #2 — `filterwarnings` already silences the
> starlette httpx deprecation instead of bounding it) · **P0-3** `pytest.importorskip` in
> `tests/perf/test_observer_storm.py` and `tests/web/test_launch_invalidation.py` (they ERROR, not
> skip, without playwright) · **P1** intake manifest + extension↔content regression test ·
> risk-register reconcile (R-03/R-12) · CUI hook hardening (`.json` content sniff, `.p6xml`,
> `*.mpp.*`) · Action SHA pinning.
> **Fable 5 (Thu):** CC-01 · SRA-LEGACY · V3. **Operator only:** license, branch-protection read,
> intake re-upload, proprietary-tool reruns for #12.
>
> ## Carried forward
> **The `/analysis` focus→tip family — measured twice, and the second measurement corrected the
> first.** Still do NOT chase. It failed **3/3** in one window AND **identically on `origin/main`
> with changes stashed** (so: pre-existing ✔, not ours ✔), then **passed** in the next full run.
> So it is **load-sensitive, not deterministic and not random**: `playwright wait_for_function`
> with a **4000 ms** budget, which this container misses only when busy. Never fails on CI ✔.
> *Do not restate "deterministic" — one clean run disproved it.*
> `pgrep -f` self-matches. pytest stdout to a FILE is block-buffered (`python -u`). `cd` persists
> across Bash calls. `--bad` is the red token. Never `git checkout <file>` to undo a test mutation —
> `cp` from a scratchpad copy. `/briefing`, `/path`, `/compare` still carry no `page-lede`; the
> `/groups` "Activities" column still counts summary rows.
>
> **New this session:** *an audit's confidence deserves as much testing as its doubts.* Three
> "VERIFIED CONTROL" items reproduced exactly; the one HIGH it was surest about was **17× larger**.
> My own magic-byte sniffer produced 3 false positives (a 64-byte window splitting a multi-byte
> char) — audit your audit tooling. And **a per-test fixture cannot undo a higher-scoped one**:
> assert the guarantee your mechanism provides, not the outcome you wish it provided.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
