# Handoff — 2026-07-30 (OR-04 shipped: the GPU is freed on exit in three tiers, and the three decisions are ANSWERED; ADR-0315; v1.0.133)

> ## STATUS (current) — **OR-04 (`llama-server.exe` holding dedicated GPU memory after quit) is FIXED per the operator-gated lifecycle audit. Version 1.0.133, highest ADR ADR-0315, wheel + nine installers regenerated. The three briefed decisions are ANSWERED (A1 · B1 · C1) — rank 12's remainder is UNGATED.**
> The operator's audit prompt ran REPORT-ONLY first (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`,
> committed at `cac0991`, audited tree `d508250`), then the apply was gated open. Confirmed in code:
> the ENGAGED path's own cleanup manufactured the orphan — unverified unload → `TerminateProcess` on
> the parent serve → an image sweep (`ollama app.exe`/`ollama.exe`) that finds only dead processes
> while the reparented runner survives holding ~11 GB VRAM (F-7, Critical; the operator's two
> "process not found" taskkills are that code's exact output). Used-but-never-engaged sessions
> no-opped entirely (`_engaged` set only by the Settings POST — F-4); every failure was invisible
> (`check=False` results discarded, listing failures silently `return 0` — F-5/F-6); nothing
> reconciled at startup (F-2); engagement died with the process (F-1/F-3); orphans COMPOUND per
> enable→ask→quit cycle (F-17).
>
> ## What shipped (ADR-0315)
> Three-tier `OllamaLauncher.shutdown()`: **engaged** → unload-all + bounded `/api/ps` re-probe
> (`unload-incomplete` at WARNING when it doesn't drain) + **pid-rooted tree-kill of the serve WE
> spawned while our un-reaped handle still pins its pid** (`taskkill /F /T /PID` / `killpg`; the
> POSIX branch refuses a target sharing our own process group) + the ADR-0122 image sweep with
> returncodes read (0/1/128 = fine, anything else WARNING); **used-but-never-engaged** →
> `record_use(model, endpoint)` fires on generate SUCCESS only (a `_UseMarking` wrapper in
> `_active_backend`/`_second_backend`; probes and the settings render never mark — pinned) and
> shutdown unloads ONLY those models, touching no process (operator ruling 2026-07-30);
> **never used** → total no-op. A durable marker (`$SF_CACHE_DIR`/ollama-engagement.json —
> endpoint+models+ts, never schedule content) survives a hard kill; `reconcile_at_startup()`
> (launcher, daemon thread, TCP-gated) reclaims marker-proven leftovers or surfaces
> `orphan-suspected`, and touches NOTHING without the marker. `generate` now sends
> `keep_alive:"5m"` (hardening — override vs `OLLAMA_KEEP_ALIVE=-1` is UNVERIFIED, F-13, park #3).
> Settings gains AI-runtime diagnostics: `manager.status` (F-16 — `no-binary` was WRITE-ONLY) +
> the four `OLLAMA_*` env values (reported, never overridden — F-10). NO image-name kill of the
> runner — rejected (llama.cpp/LM Studio collision) and pinned by test.
>
> ## Verification (all read from runs this session)
> Focused suites (`tests/ai/test_ollama_process.py` · `test_coverage_ollama_process.py` ·
> `test_backends.py` · `tests/web/test_ai_wiring.py`): **84 passed** in 7.38 s at first green,
> including the operator-scenario regression (use the AI without opening Settings → close →
> unloader called with exactly the used set, stopper/tree-kill NEVER called), alive-at-kill
> ordering, unload verification, marker/reconciliation, the llama-server exclusion pin, and the
> settings surfacing pair. **Proved able to fail:** src stashed → the three key tests fail
> (3 failed, read) → popped. `ruff` + `ruff format --check` + `mypy --strict` green on 117 src
> files; `bandit` exit 0 (one B110 fixed by logging instead of passing — this PR's own visibility
> law); `node --check` clean on all vendored JS. **Full suite on THIS tree (read): 3136 passed,
> 1 skipped, exit 0, in 890 s** — Playwright+vendored Chromium were installed in the container,
> so the browser-marked tests ran locally too. One full-run failure en route (`test_launcher`'s
> fake manager lacks `reconcile_at_startup`) was fixed with the same getattr-guard pattern as
> `record_use`, wheel+installers rebuilt, and the suite re-run IN FULL on the final tree.
> **4-theme render check (measured, read):** the two diagnostics notices render with real boxes
> in console/daylight/apollo/jarvis (heights 64/43/64/64 px) against a live server with a stub
> manager + `OLLAMA_KEEP_ALIVE=-1`. The real GPU machine is the operator's: the PR body carries
> the four-scenario smoke script (A: the bug path — ask without Settings, quit → `ollama ps`
> empty, runner gone, Ollama itself alive; B: ADR-0122 intact; C: never-used untouched; D:
> hard-kill backstop).
>
> ## ⇢ NEXT
> 1. **Operator park artifacts stay open** (audit §8): #1 `where ollama` (the PATH branch), #3 the
>    `keep_alive:0`-vs-`OLLAMA_KEEP_ALIVE=-1` probe (the severity fork for the unload strategy),
>    #5 runner PPID + instance count (orphan signature + accumulation), #4 the model-identity
>    manifest. They refine, not gate, the shipped fix.
> 2. **The approved queue** (`docs/STATE/PLAN-20260730.md` — operator-approved, decisions + red-team
>    digest recorded there; do NOT re-ask A/B/C): PR-2 `/performance` first-paint `defer` (S) →
>    PR-3 scatter panel's one-⛶ merge (S–M) → PR-4 `data-noprint` C1 one-liner (S) → PR-5
>    `/resources` X-caption yields (S–M) → PR-6 `/evolution` exports honor trace options (M) →
>    PR-7 OR-01 roll-up titles (M) → PR-8 AXIS-TITLES 3b-i `margin_dashboard` per A1 (M) → PR-9
>    rank-12 toolbar/read-me + B1 caption mechanism (M–L) → PR-10 OR-03 launch motion +
>    synthesized hum (M–L).
> 3. Behind the queue: **Phase 3** (CC-01 rendering half, 74 call sites, Fable-5-Max deep dive;
>    V3 elapsed literals) and **Phase 4** (P1–P6, measured but unremediated); rank 13/14.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) — import half closed by ADR-0312, **rendering half open**, 74 call sites; its two
> named residuals are ADR-0312's inclusive boundary (`start_tod + per_day == 1440` renders an
> exact-multiple offset at 00:00 of the FOLLOWING date) and `Calendar` still having no shift-start
> field · **CC-05** (H5) negative sub-day slack floor, oracle-gated · **V3** (H4) elapsed literals,
> `engine/msp_filters.py` the sole violator of a convention the repo already follows eight times ·
> the **legacy `/sra` cross-basis defect** (`_build_result` reads a full-duration deterministic
> against a remaining-duration sample, no realignment; reaches `/api/sra`, the SRA report,
> `sra_conclusions`, and `scorecards.reserve_recommendation`) · **a committed SSI export contradicts
> ADR-0307's Best-Case rule** (Project5 shows the pre-0307 ratios; ADR-0307 stands for the artifact
> we match) · `resume` is read from **MSPDI only** · the forward pass still packs **completed** work
> from `project_start` (724 tasks, median −1458 d vs stored actuals; Phase 7) · **per-task calendars
> are an out-of-domain pairing ADR-0312 does not reach** · several importer warnings (notably the
> **assumed** calendar, +25 % on duration-days when a 10-hour calendar fails to resolve) belong on
> the page via `Schedule.import_notes` and have not migrated.
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309 (#483/#484): det percentile **40.70 % → 6.65 %** (SSI **5.75 %**), σ **125.5 → 65.5** cal d
> (SSI **64.744**, 1.2 %), mean **+26 → +109** (SSI **+111.45**), P10/P50/P80/P90 within
> **7/1/0/3** days, all five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — MS Project's own `<Resume>` — never a blanket
>   data-date floor.** ADR-0108's two reverts were both unconditional floors; EVM1 UID 18 has
>   `resume == stop` and must not move.
> - **A floor built from the STORED remaining destroys the Monte-Carlo's upside variance**
>   (`det_pctile = 100 %`, σ 20.3). It must follow `duration_overrides`. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198)** — computed
>   over the 245 DISTINCT dates with `Occurrences` dropped.
>   `test_the_summary_cells_are_not_the_parity_target` pins the trap shut.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7, **plus**: reverting ADR-0307's Best-Case rule;
> an **unconditional** data-date floor (ADR-0108's two reverts, superseded by ADR-0309); "the four
> Setup pages have no chapter kicker" (ADR-0311); **"the xlsx writer needs a formula-injection
> guard"** (ADR-0313 — it emits no `<f>`; the CSV sibling was the real vector); **"OR-02 is in
> the hint/tooltip layer"** (ADR-0314 — the callout is app.js's DCMA float tip); **an image-name
> sweep of the model runner** (ADR-0315 — `llama-server` is llama.cpp's generic binary, the tool's
> own OpenAI-compat backend runs one; pid-rooted tree-kill instead, exclusion pinned by test); and
> **asserting** that a per-request `keep_alive:0` overrides `OLLAMA_KEEP_ALIVE=-1` (UNVERIFIED,
> audit F-13 — park #3 decides; never state it in either direction).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status. CI can take ~11 min to register check runs (`total_count: 0` = "not
> yet"). `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`).
> Full `pytest -q` ≈ 14 m; `pytest -m parity` ≈ 40 s. Wheel: `--outdir dist/wheel`, ONCE, after
> all code lands. **Headless Chromium hides scrollbars** — any geometry that depends on viewport
> width MUST also be probed with `ignore_default_args=["--hide-scrollbars"]`. **A remote-session
> resume can silently revert / flip uncommitted working-tree files** — diff the tree after every
> resume. **NEW:** `caplog` here needs `logger="schedule_forensics.<module>"` (the redaction layer
> stops propagation; the importer tests carry the working pattern), and the autouse `SF_CACHE_DIR`
> fixture isolates the new Ollama engagement marker per test for free.
>
> **Standing rule:** do not put a test result in prose unless the number appeared in output you
> read that turn. **A launched run is not a result, and a piped exit code is not the command's.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
