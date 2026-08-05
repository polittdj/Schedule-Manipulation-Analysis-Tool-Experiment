# Handoff — 2026-08-05 (phase 3 slice 2: the driving-path family; the oracle that proved nothing; ADR-0351; v1.0.166)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0351, **v1.0.166**.
> ADR-0350 (slice 1, the shared kernel) **MERGED as `0674dd9`** (PR #540). Slice 2 extracts the
> **driving-path page family → `web/driving.py` (842 lines)**, `app.py` **19,944 → 19,139**
> (−805). First per-PAGE module. Wheel + nine installers rebuilt at **v1.0.166**.
>
> ## ADR-0350's "the LAST slice of a pair collects them" WAS WRONG
> It said `_task_name_across` / `_EVO_TIER_LABEL` stay in `app.py` until both owners move. But
> **`driving.py` needs both**, so leaving them would force a page module to import UPWARD — a
> cycle, caught by the layering test I added last unit. Corrected rule, now binding:
> **a symbol an extracted module needs must live AT OR BELOW that module's layer; the FIRST
> slice of a pair forces the descent, not the last.** Both descended into `components.py`.
> `LAYER_ORDER` is now `state → chrome → components → driving → app`.
>
> ## THE RENDER DIFF PROVED NOTHING HERE — AND ONLY FALSIFICATION SHOWED IT
> It reported **60/60 byte-identical**. Then the mandatory sensitivity check: one char inside a
> moved `driving.py` function moved **0 of 60**. Reloading with the Project2/Project5 golden pair
> (63 routes, deterministic) — still **0 of 63**. The repo already knew why:
> `test_page_memory.py` says the corridor panel "only renders when a real driving corridor exists
> across versions (**which the golden pair doesn't produce**)". **No fixture in the corpus can
> render this family's deep panels.** So the render diff is NOT the oracle here; it only proves
> the 63 routes that do render are unchanged. Had I skipped the falsification I would have
> shipped quoting 60/60 as proof of code it never touched.
> **What replaced it:** per-definition AST byte-identity against the pre-move source — **9/9
> identical** (`_driving_tiers_panel` 8,000 B, `_driving_tier_trend` 4,443 B, …). Plus file-level
> verbatim (47 added = preamble + re-exports + one `PathTier` import; **0 removed**).
> **Coverage stated plainly:** 5 of 7 moved driving names have direct unit tests;
> **`_driving_tiers_panel` and `_driving_tier_trend` have NONE**, nor do `_task_name_across` /
> `_EVO_TIER_LABEL`. Their only guard is `test_page_memory`'s source-text check.
> **NAMED GAP: a fixture that produces a real driving corridor.** Until one exists this family
> cannot be refactored with behavioural evidence again. Worth its own unit.
>
> ## BOTH TRAPS FIRED, ONE OF EACH KIND, IN ONE COMMIT
> **Phase 1's (monkeypatch):** `test_coverage_app_extra` patches three names on `web.app` then
> calls `_driving_path_body`. One failed LOUDLY (`AttributeError`). The other two are the
> dangerous shape — `_driving_path_gantt` / `_corridor_chips` are **still re-exported by
> `app.py`**, so the patch SUCCEEDS and does NOTHING while the caller (now in `driving.py`)
> resolves them locally; the test would have asserted against the real renderers. All three now
> patch `drvmod`. **My first sweep missed them** because it compared against names `driving.py`
> *imports*; these are names it *defines*. **Sweep every name the new module BINDS, imported or
> defined.**
> **Phase 2's (source text):** `test_page_memory` read `app.py` for `dpFind`/`dpBarDates`, which
> moved. Direction matters and differs from last unit's: this guard's subject is the driving-path
> markup, so it **FOLLOWS** the subject to `driving.py`; the two whole-view-layer guards
> **WIDEN**. Getting it backwards would have left the one untestable panel guarded by nothing.
> **Phase 2's a THIRD time, and the sweep COULD NOT have found it.**
> `test_gantt_find_coverage` reads **`Path(app_module.__file__)`** — the module OBJECT, not a
> literal `"app.py"` — so `grep -rln 'app\.py' tests/` never listed it. It survived the pre-cut
> sweep, three sibling repointings and every fast check, and **only the full 20-min suite caught
> it.** The standing sweep is incomplete as written: **also grep `__file__)\.read_text` and
> `getsource`.** A repo-wide check found one other (`test_installers`, whose subject
> `@app.post("/api/shutdown")` correctly stayed in `app.py`).
> **ADR-0350's enumeration guard worked on its first real outing** — adding `driving.py` to
> `VIEW_MODULES` made it fail and name both files to widen. It does NOT cover the `__file__`
> class (that guard's claim is "this markup exists", a follow-the-subject case).
>
> ## Verification
> Five mutations, each verified-mutated by re-reading the file and restored from a scratchpad
> copy: dropped re-export → contract names `_driving_data`; **deferred** upward import in
> `_corridor_chips` → layering guard; `dpFind` removed → repointed page-memory guard;
> `id=dpFind` broken → repointed gantt-find guard; plus the enumeration guard's live failure.
> **TWO mutations were themselves wrong first, both flattering** — each read exactly like "this
> guard cannot fail": (1) replacing only the FIRST of two `dpFind` occurrences; (2) `id=dpFind`
> → `id=dpFind**Z**`, where the guard asserts `"id=dpFind" in src` and the original is a
> **SUBSTRING of the replacement**. Working mutation: a same-length non-superstring (`id=dpQind`).
> **Rule: after mutating, assert the ORIGINAL anchor is ABSENT from the re-read file.**
>
> ## Next
> Twelve page families remain: `evolution` 429 · `integrity` 402 · `margin` 379 · `trend` 348 ·
> `ssi` 335 · `mission` 304 · `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 ·
> `evm` 208 · `forecast` 204. **Each must add its module to `LAYER_ORDER` + `VIEW_MODULES`** (the
> contract test fails until it does), **run the monkeypatch sweep over ALL names the new module
> binds**, and **check whether its family is renderable by any fixture BEFORE quoting a render
> diff**. Then: a driving-corridor fixture · the three pages with no `page-lede` (`/briefing`,
> `/path`, `/compare`) · `/groups` "Activities" counting summary rows (ADR-0343) · the nine
> installers vs `-c constraints/known-good.txt` (62 lockstep tests, own unit) · Phase 6 docs.
> **Reserved for Fable 5 Max (ADR-0240), do NOT start on Opus:** **SRA-LEGACY**
> (`audit/SRA-ROOTCAUSE-20260730.md`) · ADR-0348's **`tod + per_day == 1440`** residual · **V3**
> (`engine/msp_filters.py`).
> **Operator only:** license selection · branch-protection required contexts · intake re-upload ·
> proprietary-tool reruns · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — passes in isolation, never red on CI.
> Do NOT chase (re-confirmed: it fails WORSE on the pre-change tree). Do NOT re-derive CC-01's
> "74 call sites". `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP
> VIOLATION (0.110.2 is the floor). **Run `ruff check .` — the WHOLE tree**, as **`python -m
> ruff`**. Never `git checkout <file>` to undo a mutation — `cp` from a scratchpad copy. The
> render oracle needs the launch-token/pid normalization and `/api/system` excluded, or it is
> nondeterministic across processes.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
