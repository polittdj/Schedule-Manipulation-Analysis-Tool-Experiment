# Handoff — 2026-07-17 (PR-P1 safe increment: analysis-cache LRU, summary-edge guard, SRA finish-rank reuse; v1.0.58; highest ADR 0248)

> ## STATUS (current) — ADR-0248: PR-P1's first increment ships the three VALIDATED perf items that are provably output-preserving (each lead-verified against HEAD by a 6-agent parity-risk pass, then re-checked in code). The parity-critical/large items are deferred to their own PRs, matching the committed audit's required-action-order. Full gate green incl. `parity`.
>
> - **#4 — analysis-cache LRU (`web/app.py`).** `SessionState.analyses` + `polished` are now backed
>   by a std-lib `_LRUCache(OrderedDict)` (no cachetools): `get_lru` marks MRU, `put` evicts the LRU
>   past `_ANALYSIS_CACHE_MAX` (48), under the existing `_lock`. Only these two heavy caches are
>   capped; `schedules` + the cheap `summaries` tier (portfolio scale) stay uncapped. Parity-risk
>   NONE — an evicted entry recomputes byte-identically (pinned by a recompute-equivalence test:
>   evict → re-request → identical CPM finish / critical path / floats).
> - **audit-E — summary-edge guard (`engine/summary_logic.py` + `cpm.py`).**
>   `lower_summary_relationships` projects the fan-out from lengths only and RAISES
>   `SummaryLogicExplosion` past `SUMMARY_EDGE_CEILING` (250 000) — fail loud, never silently truncate
>   (truncation would drop real logic → change CPM dates → Law-2 break). `compute_cpm` re-raises it as
>   `CPMError` so the web layer degrades to a disclosed 422, not a 500/hang/OOM. Below the ceiling the
>   lowering is byte-identical (parity goldens carry no summary logic → guard never reached); a test
>   pins the ceiling far above a large realistic summary schedule.
> - **audit-C — SRA finish-rank hoist (`engine/sra.py`).** `_build_result` computes the finish ranks
>   ONCE (`finish_ranks = _average_ranks(finishes_f)`) and calls
>   `_pearson(_average_ranks(durs_f), finish_ranks)` per activity instead of re-ranking the identical
>   finish vector N times. Byte-identical (a test asserts `==`, not approx, across tied/zero-variance
>   series; SRA determinism + parity gates confirm the `SRAResult` is unchanged).
> - **Deferred (each its own PR — parity-critical or large, per the audit's required-action-order):**
>   **#8.1** compiled CPM topology (HIGH parity risk — gate-locked solver) · **#9** MSPDI iterparse
>   (HIGH risk, large; keep the DOM parser as a fallback until parity proven + fresh XXE/billion-laughs
>   tests) · **#10** cancellable AI generation-job API (large UX feature) · **#3** path-adjacency memo
>   (premature — behind the audit's "only if benchmarks show measurable benefit" gate; `id()`-reuse
>   staleness hazard). A perf/memory-regression harness (audit-F) is the recommended enabling first
>   step before any HIGH-risk item.
> - **State:** v1.0.57 → **1.0.58** (src changed: `app.py`, `sra.py`, `summary_logic.py`, `cpm.py`);
>   wheel + 9 installers rebuilt in lockstep; **ADR-0248**; full gate green (ruff / ruff format --check
>   / mypy --strict / bandit exit 0 / node --check / full pytest incl. the `parity` gate).
> - **NEXT:** the deferred PR-P1 items above (start with the **audit-F perf/memory-regression
>   harness**, then #8.1 / #9 / #10 / #3 each in its own PR with a byte-identical/parity proof) →
>   **#13** XER per-task calendars → base-CPM single-calendar fail-soft disclosure (**#26**) → **F3c**
>   parameterized expected margin → roles front-end (v4 F4). Optional follow-up: extend the per-task
>   Gantt shading to the path-evolution + SRA grids. Operator-side (no code): apply the
>   `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI + the §4 root-vs-mpp
>   `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
