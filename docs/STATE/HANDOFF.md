# Handoff — 2026-08-12 (c) (phase 4 slice 25: the LAST page family out; ADR-0390; v1.0.197)

> ## STATUS (current) — **MERGED.** #575 (slice 25) and #576 (probe fixture · SRA-vs-SSI
> measurements · Definition of Done v2 · the parity-oracle fix) are both in `main` at **b72f887**,
> all CI green. The branch has been restarted from the new `main`. **Read
> `docs/PLAN/DEFINITION-OF-DONE-V2.md` before planning anything** — the operator has declared a
> second finish line and made all **117** items REQUIREMENTS ("I don't want to skip anything"),
> banded by how wrong the tool is rather than by effort. The old standing queue is superseded.
>
> Landed after the slice-25 text below: **(a)** `docs/PLAN/SRA-VS-SSI-LARGE-TEST-FILE2.md` — two of
> the operator's three SRA complaints REVERSE on measurement (our Mean/StdDev are within 3 days and
> 3.4% of SSI's OWN exported distribution; the sensitivity VALUES match to one decimal) while the
> third is real and under-reported (the tornado mislabels risk drivers with their host task's name;
> the run is ~2.9 min with **63% of the work provably irrelevant** to the focus event).
> **(b)** The Negative-Float probe fixture + guard, awaiting ONE operator Fuse run.
> **(c)** A parity-oracle defect fixed: `test_sra_ssi_oracle_uid152.py` chose its input with
> `sorted(glob(...))[-1]`, so the operator's second SSI upload silently re-pointed every assertion
> at a different distribution and reported as a numeric regression. Pinned by name now.
>
> (historical, slice 25) — originally pushed as a draft PR on `claude/polaris-settings-extraction-kvhryw`
> (this container's designated branch). It started AT `main` **c03bf28** — #574 had already
> squash-merged, so no restart was needed. **Shipped code changed** — version bumped
> **v1.0.196 → v1.0.197** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0). Highest ADR now **ADR-0390** (re-fetched before numbering
> AND before committing).
>
> **Slice 25: the `settings` family → `web/settings.py` (525 lines), TWELVE names / 437 ast
> lines, ZERO forced descents.** `app.py` **8,482 → 8,037** wc-truth (17,197 when phase 3 began).
> `LAYER_ORDER` `… → volatility → settings → app`; `settings.py` joins pyproject's E501 list,
> `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and BOTH whole-view-layer guard tuples.
>
> **OUTSIDE THE FENCED `groups`, `app.py` NO LONGER HOLDS A PAGE FAMILY.** Phase 4's
> page-family work is DONE. The monolith split's remaining work is not "another slice".
>
> ## THE FINDING — the record's 3 descent candidates were really 5, one hop further out
> ADR-0389 asked slice 25 to test whether `settings`' three candidates are FORCED. Both halves
> moved. The 7 movers and 347 ast lines reproduce EXACTLY (measured twice — ast, and
> independently by awk). The candidate list does not: `_settings_body` calls `_second_backend`,
> and `_second_backend` needs `_BACKEND_PROBE_TTL` and `_UseMarking`, both shared with the stayer
> `_active_backend` in the IDENTICAL shape the record used to flag the other three. **The closure
> had been taken to a fixed point of the MOVERS, not of the BLOCKERS** — and the second hop is
> where a cut breaks: the recorded price would have produced a module that does not import, or a
> `settings` → `app` cycle.
>
> **ZERO descents are forced.** AST scan over **32** modules — the 31 already-extracted view
> modules (list read from `EXTRACTED`, never hand-typed) PLUS **`state.py`**, which is in
> `LAYER_ORDER` but not `EXTRACTED` and is the BOTTOM layer, so a referrer there would force a
> descent too — across FOUR channels (`ImportFrom` alias, `ast.Name`, `ast.Attribute.attr` for the
> `app_mod._foo` reach, `ast.Constant` strings for `getattr` dispatch): **zero references to any of
> the twelve**. Positive control `_e` = **29 of 32**, and all three misses (`ssi.py`,
> `volatility.py`, `state.py`) are exactly the modules with no HTML — the control's shortfall is
> EXPLAINED rather than tolerated. An adversarial verifier re-derived it over a superset (all **91**
> names bound at `app.py` module level): also zero. `components.py` was
> rejected on ITS OWN CHARTER (membership measured at 3+ families of shared PRESENTATION
> primitives; AI-backend construction is neither), not on layering. Fenced `groups` (8 movers,
> 430 ast lines) has zero overlap and zero blockers — placing `settings` directly below `app`
> cannot force a descent when `groups` is eventually cut.
>
> ## The oracle grew an EIGHTH stage: 948 → 1096
> The probe ran TWICE against TWO instruments, so "dark" and "lit" are two measurements, not one
> plus a story. **Probe A (committed 7-stage oracle): 7/12 render-proven, 5 DARK**, control
> `_page` **263** decomposing as `[empty]` 29 + 6 × 39. One cause, not five: EVERY stage runs on
> the shipped default `AIConfig`, so the corpus had never rendered a non-default backend, a
> configured second model, an attached launcher manager, or any `OLLAMA_*` environment.
> **`[aiconfig]`** is that render condition — every form key is one `update_settings` DECLARES,
> `classification` stays CLASSIFIED, both endpoints stay loopback (**no egress**, Law 1), the
> stage runs LAST, and `render()` now snapshots/restores `os.environ` so the mutation cannot
> escape. **Probe B's control was a FORWARD PREDICTION** — 29 + 7 × 39 = **302** — and landed
> exactly, 39 in the new stage. `_openai_or_none` then moves exactly ONE label,
> `[aiconfig] GET /settings`, and nothing else. **`_UseMarking` and `_BACKEND_PROBE_TTL` stay
> dark BY CONSTRUCTION** (a wrapper needing a live model; a cache TTL that cannot change bytes) —
> unit-covered, reported as a NAMED GAP, not smoothed over.
>
> ## The ADR-0297 monkeypatch trap FIRED — and the repoint is per CALL SITE, not per name
> Sweep population **518** `.py` files (517 pre-cut) over the 25 names `settings.py` BINDS: 187
> `X.setattr(mod, "name", …)` calls, **21 hits** → **14 repointed, 7 deliberately left alone**.
> `_ollama_or_none` and `_second_backend` each appear on BOTH sides — patched then driven through
> `/settings` the consumer MOVED; through `/api/ask` it did NOT. A name-keyed repoint would have
> broken seven working tests while fixing fourteen. **The FIRST sweep was WRONG and the battery's
> pre-mutation control caught it** — its regex anchored on `monkeypatch.setattr` while
> `test_coverage_app.py` binds `mp = monkeypatch`, hiding FOUR sites; the battery's baseline went
> RED before any mutation was applied. A sweep's PATTERN is part of its claim, like its population.
> **Three of the fourteen would have passed SILENTLY**, so
> the non-zero case was FORCED with counting spies: app-globals **0×** / settings-globals **1×**
> on all three, and the control is the MIRROR IMAGE on the same name (`_active_backend`: **1× /
> 0×**).
>
> ## Verbatim text is not always verbatim behaviour
> `_UseMarking` logs via `logging.getLogger(__name__)`. The line moves byte-for-byte; `__name__`
> is not text, so the logger name follows the module (`web.app` → `web.settings`). Nothing
> observes it (it fires only when a `record_use` hook raises); rewriting it to a literal would
> trade a verbatim move for a hard-coded lie, so it moved as-is and is NAMED in the ADR. It is the
> only module-identity-sensitive construct in the moved bytes — grep `__name__` / `__file__` /
> `__module__` / `globals()` / `sys.modules` before claiming byte-identity means behaviour-identity.
>
> ## Verification
> **1096/1096 byte-identical** pristine vs cut, `diff -r` itself SHOWN TO FAIL (one-byte append →
> exit 1; md5-verified restore → exit 0) · reproducibility control on BOTH instruments (948/948,
> 1096/1096) so the probe's zeros are real zeros · verbatim BY CONSTRUCTION (the moved text is a
> byte slice of `app.py`, re-read FROM DISK and asserted present in `settings.py`; all 12
> definitions asserted ABSENT from `app.py`) · **dropped imports ZERO** (`/api/ai/models` stayed
> and still uses the backend classes) · determinism ×2 processes on BOTH trees, **0 flapping**, the
> second pair reproducing byte-identity independently · **battery 6/6 caught BY NAME** (M6 caught by
> BOTH repointed tests, so the repoint is proven to REACH the moved code; **M7 oracle-scored** — unit
> selection rc=0 / zero named failures, oracle **8 differing labels**, matching the probe's own
> independent count for `_ai_backend_explainer`) · `mypy --strict` clean over **149** files ·
> `ruff check .` clean whole-tree · bandit exit 0 · `node --check` clean · corpus re-rendered AFTER
> the battery, byte-identical to the pre-battery cut render.
>
> ## Next
> **The page-family queue is EMPTY.** Two follow-ups this slice deliberately declined, both queued
> rather than done: (1) **`web/backends.py`** — promote the five-name AI-backend kernel out of the
> `settings` page module into its own module; layer-legal, more cohesive, and a SEPARATE
> architectural decision that would have made neither reviewable if merged into this slice.
> (2) **`_active_backend`** — route-reached only, so moving it is permitted, but it would widen the
> monkeypatch trap across the seven call sites that currently still work; measured trade, declined.
> Then the standing queue: **`mpxj_ref()` shallow-clone hardening** · stored-SRA-fields MSPDI
> fixture · driving-corridor fixture · three page-lede-less pages · `/groups` Activities (ADR-0343)
> · installers vs known-good constraints · P80/P90 residual · the doc-drift sweep
> (`docs/PARITY-REPORT.md` still calls the reference .mpps git-ignored; `docs/FINAL-REPORT.md`'s
> blanket "Exact match"; `LESSONS-LEARNED` Part VIII's 2026-08-10(e) straggler) · ~150 MB RSS per
> loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 + re-run Fuse · one Acumen run on a crafted sub-day-negative-
> float schedule · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
> re-export decision.
>
> ## Carried forward
> ADR-0353..0390 closed — do not re-open. **The oracle is committed: import it, don't rebuild it.**
> `python tests/web/oracle_corpus.py --out <dir>` with `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and the cut tree, then
> `diff -r` on the DIRECTORIES (filenames are LABEL-addressed). NEW lessons: (1) a closure is not
> closed until it stops growing — iterate to a fixed point of the BLOCKERS and say which hop each
> member arrived on; (2) relabelling a figure is not re-measuring it; (3) the monkeypatch repoint
> is keyed on the CALLER, not the name, and the two sets share names; (4) verbatim text is not
> always verbatim behaviour (`__name__`); (5) "what has the corpus NEVER rendered?" is now the
> standing FIRST question — two consecutive slices found dark members with a whole-class cause;
> (6) a control whose shortfall you can EXPLAIN beats a perfect one; (7) PREDICT the control, then
> run it; (8) **never mutate an instrument a measurement is using** (the mirror of "never measure a
> tree a battery is mutating" — editing `oracle_corpus.py` mid-probe changed the label set under a
> running probe; it aborted cleanly, and the redo is why the before/after columns exist).
> Standing traps unchanged (an instrument is not evidence until shown to FAIL · a probe's marker
> must match the RETURN TYPE · a priced table is a snapshot · a control that names a VALUE beats
> one that names a direction · `ast` col_offset is a BYTE offset · a census can be exact and still
> not be membership · route-only referrers never force a descent · sweep by BARE NAME · a sweep's
> POPULATION is part of its claim · a prefix that is a prefix OF ANOTHER FAMILY fuses two censuses
> · the MPXJ pin drifts in a shallow clone · a parallel session can take your ADR number · never
> MEASURE a tree a battery is mutating · a normalizer that fails silently is a flap factory ·
> fingerprints carry their SCOPE · the installer lockstep guard makes the rebuild a PREREQUISITE of
> the final suite · round-half-even 240→0 · MSPDI re-derives Duration · env-defect masquerade ·
> named-failure rule · empty sweep needs a positive control · `grep -c` exits 1 on zero · B608
> house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing,
> CI-invisible · scratchpad harnesses hardcode the repo root · `python -m pytest` prepends CWD to
> `sys.path` and bare `pytest` does NOT · two ruffs on PATH, run `python -m ruff`). A number
> written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
