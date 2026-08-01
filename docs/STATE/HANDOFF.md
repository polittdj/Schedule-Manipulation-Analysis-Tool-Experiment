# Handoff — 2026-08-01j (Phase 1a: a wipe is total, by reflection; ADR-0332; v1.0.148)

> ## STATUS (current) — **Phase 1a BUILT AND GATED on this tree (ADR-0332).** Phase 0 MERGED as
> `5c829e4` (#508). A reflection sweep of `SessionState` vs the `/session/wipe` handler found the
> handler reset fields by NAMING them and had fallen behind the dataclass: of **72 declared fields,
> 27 of real operator state survived a wipe** — the whole SRA setup (factor rows, per-UID Risk
> Ranking Factors, Best/Worst pairs, the correlation matrix, the cached Criticality Index), all
> seven `jcl_*` cost settings, `margin_rate` (while `margin_band_*` WERE reset — an unnoticed
> inconsistency), `translations` (AI translations of imported ACTIVITY NAMES), and
> **`dcma_acumen_parity` — a metric-MODE flag**. **This is Law 2, not housekeeping:** the SRA maps
> are keyed by UniqueID, so project B silently inherited project A's risk inputs wherever UIDs
> collided. **Fix: `SessionState.reset()` returns every field to its default except a named
> `WIPE_PRESERVED` (7 entries, each justified) — the default is now RESET, so the NEXT field added
> is wiped without anyone remembering.** Client side: the ADR-0324 launch guard gained
> `GLOBAL_KEYS` for cross-page schedule-derived keys — `sf-story-visited` stored
> `/analysis/<the operator's FILENAME>` and outlived every launch and wipe. Preferences
> (theme/scale/telemetry/**boot-hum mute**) deliberately NOT swept — a blanket prefix sweep would
> un-mute ADR-0328's hum every launch. Version **1.0.148**, highest ADR **ADR-0332**.
>
> ## Verification (all read from runs this session)
> New `tests/web/test_session_wipe_is_total.py`: **5 passed**, including a CONTROL asserting the
> fixture dirtied ≥40 fields (so the sweep cannot pass vacuously). Session neighbours
> (launch-invalidation · session-consistency · saved-filter · sra-view · jcl-web · ai-wiring)
> together with it: **81 passed**. **Proved able to fail, watched:** reverting ONLY the handler
> (keeping the new API, so the failure is behavioural not an ImportError) fails the route test with
> `assert {7: 3} == {}` — the per-UID Risk Ranking Factor still resident after a wipe; reverting
> `persist.js` fails the browser test with `'["/analysis/SecretProject.mpp","/"]'` still stored.
> Statics foreground: ruff "All checks passed!" · format clean (838) · mypy --strict clean (117) ·
> node --check clean. Full-suite result: see SESSION-LOG (recorded after the run completed).
>
> ## ⇢ NEXT — the approved plan (`/root/.claude/plans/merry-juggling-owl.md`)
> 1. **Phase 1b — the launcher, and it is BLOCKED ON ONE OPERATOR MEASUREMENT.** On the deployed
>    box: launch, close ONLY the browser, then `netstat -ano | findstr :8321` — **one PID or two?**
>    — then relaunch and re-check. One PID ⇒ the second launch died mute and the browser reattached
>    to the survivor. TWO ⇒ Windows `SO_REUSEADDR` let a second server bind the same port (uvicorn
>    never sets `SO_EXCLUSIVEADDRUSE`), so routing is indeterminate and a bind-error reporter would
>    fix nothing. Either way the fix is an explicit single-instance PROBE before serving; the answer
>    decides what the test must pin. **Do NOT "move the browser timer after serve_fn" — `serve_fn`
>    blocks for process life.** Disk cache: clear on CLEAN SHUTDOWN + atexit, never at launch
>    (launch-clearing leaves data at rest over the between-sessions window and throws away a 9×
>    warm start), plus a size and age cap.
> 2. **Phase 2 — performance.** Idle pumps are exactly TWO: `sysmon.js` (2 s) and `heartbeat.js`
>    (3 s). **Do NOT pause the heartbeat** — `idle_grace=600` would shut the tool down after 10
>    minutes minimized and LOSE THE SESSION. Lead the observer fix with the records-based rewrite
>    (`tooltips.js:71-79`, walk `addedNodes`); scoping is the secondary belt. The `setInterval(…,
>    1600)` steppers are Play-GATED, not idle (11 modules / 12 sites incl. `margin.js` and
>    `driving_path.js`) — real crash-prevention work, wrong bucket. New caches MUST key through
>    `_cache_key`/`_invalidate_scope` (filter+target scoped) or they serve a differently-scoped
>    number — Law 2.
> 3. **Phase 3 — UI (hybrid).** Four unconverted Act III pages (`/sra`, `/risks`, `/briefing`,
>    `/brief`), `DOM_PENDING` (7), then the DoD ledgers. DD-line ledger must EXCLUDE non-time-axis
>    charts (`histogram.js`, `scatter.js`, `sra_jcl.js` cost axis).
> 4. Behind: Phase 4 engine · Phase 5 monolith split 2–3 · Phase 6 docs/operator queue (OR-04).
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** · **SPLIT-23** · **A0293-UI** · Project5's SSI export
> contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass packing ·
> ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase · **ADR-0332 scope note:** a within-session `sf-story-visited` still
> records the current chapter's route (filename included) — deliberate, the name is already in the
> URL; only cross-session persistence was the exposure.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus:** "the caption can
> move out of the ink" (placement frozen; the data cannot yield when the data IS the plot — halo);
> "a blanket white halo" (two of three chart families are not on white); "ink-present ⇒
> halo-required is a sufficient test" (true on 79 % of renders — measure pixels); **"listing the
> fields to reset is maintainable"** (it fell 27 behind — reset by reflection); "a blanket
> `sf-`/`sf.` localStorage sweep" (un-mutes the boot hum, resets theme — split state from prefs).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart.**
> `pytest --timeout=N` is NOT installed. **Read the tool's own summary line** (`| tail` masks the
> real exit code). `pkill -f` with the pattern in the killer's own command line kills the killer.
> CI can take ~11 min to register check runs. `TestClient` follows 303 and CONSUMES one-shot
> banners. Parity marker ≈2m38s. Headless Chromium hides scrollbars. `caplog` needs
> `logger="schedule_forensics.<module>"`. **Playwright `bounding_box` and `page.screenshot(clip=…)`
> are VIEWPORT-relative — a node below the fold needs `handle.screenshot()`.** **localStorage is
> per-ORIGIN.** Containers RESTART mid-run: statics FOREGROUND first, reinstall pip after resume.
> After a squash-merge: `git fetch --prune origin && git remote set-head origin -a && git checkout
> -B <branch> origin/main` — **NEVER amend the merged commits to satisfy the stop hook** (they are
> published history; restarting the branch is the fix). **Version-bump sequencing:** bump BEFORE
> the suite. Never sleep in a sync-Playwright route handler. Never `from tests.web...` in a test.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** (ADR-0316).
> **A stray `*/` makes CSS error-recovery swallow the NEXT rule silently — only a computed-style
> read catches it.** **`cd` in a Bash call persists across calls — use absolute paths.**
> **When reverting to prove able-to-fail, revert the CALLER not the API** — reverting both turns a
> behavioural failure into an ImportError, which proves nothing.
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
