# Handoff — 2026-07-17 (audit-F: deterministic perf/memory-regression harness; v1.0.58; highest ADR 0249)

> ## STATUS (current) — ADR-0249: closes audit finding F (no perf-regression gate) with a DETERMINISTIC harness — operation-count + cache-residency + relative-memory assertions, NEVER wall-clock latency (which flakes on CI). Test-only (no `src/` change → version stays 1.0.58). Full gate green incl. `parity`.
>
> - **`tests/perf/test_perf_regression.py`** gates the perf properties ADR-0248 shipped, so a future
>   change that undoes them fails CI:
>   - **audit-C (SRA finish-rank reuse):** spies `_average_ranks` across one `compute_sra` — `N`
>     activities ⇒ exactly `N + 1` calls (1 hoisted finish rank + 1 duration rank each), not `2N`.
>     Un-hoisting makes it `2N` and fails.
>   - **#4 (analysis-cache LRU):** after opening `3 × cap` versions, `len(analyses) <=
>     _ANALYSIS_CACHE_MAX` (memory ∝ residency) and the newest version stays resident; reverting to a
>     plain dict makes residency == version count and fails.
>   - **#4 relative memory:** a `tracemalloc` comparison — a bounded cache traces a lower peak than an
>     unbounded one over the same workload (a DIRECTION, not an absolute ceiling, so it never flakes).
> - **Deliberately excluded (documented in the harness + ADR):** wall-clock latency gates (CPM / SRA /
>   filter toggle — need a warm-up benchmark + machine baseline, a flaky fit for a unit gate) and the
>   deferred-feature memory items — import peak memory rides **#9** (MSPDI streaming), AI-cancellation
>   behavior rides **#10**. Each is gated by its own PR when that work lands (not by pinning today's
>   un-optimized status quo).
> - **State:** v1.0.58 unchanged — **test-only** (one new test module + ADR), no `src/` change, so the
>   wheel + 9 installers stay in lockstep (no rebuild); **ADR-0249**; full gate green (ruff / ruff
>   format --check / mypy --strict / bandit exit 0 / node --check / full pytest incl. the `parity`
>   gate; the harness is deterministic — verified stable across repeated runs).
> - **NEXT (the deferred PR-P1 items, now with a regression baseline; each its OWN PR with a
>   byte-identical/parity proof):** **#8.1** compile CPM topology once per SRA run (HIGH parity risk —
>   gate-locked solver; keep the per-iteration path as a proven-equivalent fallback) · **#9** MSPDI
>   iterparse (HIGH risk, large; keep the DOM parser as a fallback until parity proven + fresh
>   XXE/billion-laughs tests) · **#10** cancellable AI generation-job API (large UX feature) · **#3**
>   path-adjacency memo (premature — behind the audit's "only if benchmarks show measurable benefit"
>   gate; `id()`-reuse staleness hazard). Then **#13** XER per-task calendars → base-CPM
>   single-calendar fail-soft disclosure (**#26**) → **F3c** parameterized expected margin → roles
>   front-end (v4 F4). Optional: extend per-task Gantt shading to the path-evolution + SRA grids.
>   Operator-side (no code): apply the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web
>   UI + the §4 root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
