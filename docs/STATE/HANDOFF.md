# Handoff — 2026-07-29 (round 11 shipped; the ⛶ that finally moves; ADR-0305; v1.0.121)

> ## STATUS (current) — Round 11 COMPLETE on branch `claude/schedule-forensics-continue-gkju7l` (draft PR open). Version **1.0.121**, wheel + nine installers regenerated. Highest ADR **ADR-0305**. Tail rank 11 done; **next is rank 12 — the Library/Setup sweep (`/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`, `/wbs/{name}`).**
>
> ### What shipped
> `/path`, `/driving-path`, `/evolution` and `/volatility` now wear the panel contract — **and the
> contract's ⛶ ENLARGE works on a block-layout panel for the first time.** Five surveys + a
> cross-cutting mechanism audit + a reconciling lead, six serialized implementers, three adversarial
> verifiers, every claim re-verified by the orchestrator. `engine/`, `model/`, `importers/` and
> `ai/` are **untouched** (`git diff origin/main --stat` on those paths is empty).
>
> ### ⚠️ THE ROUND'S CENTRAL RESULT (ADR-0305) — the operator's amendment paid for itself immediately
> Requirement 2 as amended (*"prove every control changes a measured box, not just a class"*) is what
> forced ADR-0304's deferred open item to a decision. Measured on **untouched merged `main`**, real
> clicks, four themes:
> ```
> pristine   moved=68   NO-OP=192      <- every one of the 192 is a block-layout .panel
> patched    moved=252  NO-OP=4        <- 184 NO-OP -> MOVED, 0 MOVED -> NO-OP
> ```
> The 4 survivors are exactly `/analysis` panel 5 × 4 themes — the `:has(.sf-tilebox)` exclusion
> firing where intended. The fix **borrows** `.sf-tilebox.tile-expanded`'s geometry (the project
> already had **five** enlarge vocabularies) rather than minting a sixth, and is toggled-state-only:
> 128 default-render measurements pristine-vs-patched resolved to **0 differences**, untoggled server
> HTML byte-identical 13/13 routes.
>
> ### ⚠️ AND THE FIX NEARLY REPEATED ROUND 10'S FAILURE INSIDE ITSELF
> The obvious inset — copying the shipped tilebox's `inset:4vh 3vw` — was **measured and rejected**.
> **Daylight has no 236px left rail** (`main` x=0 w=1440, panel **1384px**) while console/apollo/jarvis
> do (`main` x=236 w=1204, panel 1148px), so a `3vw` box is **1354px — narrower than a daylight
> panel**: measured `/scurve` daylight `1384x752 → 1354x828`, svg `1354x436 → 1324x426`. ⛶ would have
> made the chart **smaller in one of four themes**. `inset:3vh 12px` is theme-independent (1416px) and
> grows the svg in every theme. **The generalisable rule: when you give a control an effect, measure
> that effect in EVERY theme and at every scale — the obvious geometry can be right in three of four.**
>
> ### The deliberate negatives (each is a decision, each was attacked)
> - **`/path` ships NO ⤓** — `/export/xlsx/path/{name}` has `target: int = Query(...)` REQUIRED and
>   returns **422** without it, while `st.target_uid` is legitimately `None`. **NO prov chip** either:
>   the panel's version is chosen CLIENT-side by `#pathSchedule`, so a server chip would lie.
> - **`/evolution` ships NO ⤓ ANYWHERE** — `export_evolution` reads `session().target_uid` and silently
>   IGNORES the page's `?target=`; `?target=19&ignore_constraints=1` returns the byte-identical bare
>   workbook (md5 `f8e7cd26…`). **A live-but-WRONG export is worse than a dead one.**
> - **`/driving-path`'s "All driving-tier activities" ships NO ⤓** — driving_tiers.js rebuilds `&cols=`
>   live and persist.js remembers it, while panelkit reads a STATIC `data-export`: the round-10
>   `/performance` defect exactly. Same reasoning for both what-if panels (whatif.js owns their Excel).
> - **"Corridor over time" gets NO ⛶** — after `#dpFit` the mount grows to 1386px while the table stays
>   1102px. A control that is right before Fit and wrong after it is worse than no control.
> - **The single-open invariant is OVERLAY-ONLY** — mosaic tiles stay in the flow and do not obscure
>   each other, so two-tiles-open on the Mission wall is a working round-10 capability a blanket
>   invariant would have destroyed. It decides which is which by asking the browser for the computed
>   `position`, **not** by re-deriving base.css's selector in JS — one owner for the rule.
>
> ### THE FIVE STANDING REQUIREMENTS (carry all five; 2 stays amended)
> 1. **JARVIS PROBE + PROMOTION CENSUS.** *(Round 11: 24 census groups across 6 routes × 4 themes,
>    `.panel`/`.panel-head`/`.sf-tools`/`[data-sf-big]` identical in all 24; 0 promotions.)*
> 2. **THE CONTROL MUST MOVE A MEASURED BOX (ADR-0304/0305).** A class read-back is not a proof.
>    panelkit is a PER-PAGE include; `_page` cache-busts `src` to `?v=` — match a SUBSTRING.
> 3. **LOADED-TERMS AUDIT WITH A CONTROL.** ⚠️ **NEW TRAP:** the hint machinery **strips `title` off
>    every `[data-sf-excel]`/`[data-sf-big]` at runtime** and re-homes it as `data-sf-hint`/
>    `data-sf-title`. A harvester reading `title` alone MISSES every ⤓ hover string on all ten
>    contract pages.
> 4. **SHAPE THE PROOF TO THE PAGE'S OWN HAZARD.**
> 5. **THE AXIS CAPTIONS ARE FINISHED.** ⚠️ **The instrument changed:** the per-call-site md5 file was
>    **retired** (it missed one of `trend.js`'s five call sites and included `chartframe.js`'s
>    definition). Use a **whole-file md5 census of the 12 files owning the 16
>    `SFChartFrame.axisTitles(` call sites** (+ chartframe.js). **An instrument that cannot reproduce
>    its own baseline on an unmodified tree is worse than none** — it teaches the next agent to ignore
>    a red result.
>
> ### ⚠️ NEW ORCHESTRATION HAZARD, LEARNED THE HARD WAY — `git stash` IS NOT READ-ONLY
> The first verification launch told three "read-only" agents to `git stash` to compare against
> pristine. They share ONE working tree: verifier L1 stashed the entire round out from under verifier
> L3, which was mid-measurement, **and** out from under the lead's concurrent `pytest`. Caught by
> noticing `pyproject.toml` had reverted to 1.0.120. **Any agent that needs a pristine comparison must
> get `isolation: "worktree"`, never a shared-tree stash.** Recovery patch was snapshotted before
> touching anything; nothing was lost.
>
> ### OPEN — decision-ready, each with a measurement, none silent
> 1. **`[data-noprint]` has ZERO CSS rules anywhere** (`grep -rn data-noprint static/*.css` → nothing)
>    while the attribute is set on 10+ elements; `.sf-tools` computes `display:flex` under print media.
>    DESIGN-SYSTEM §7 requires those controls hidden in print. One line fixes it — on **ten** merged
>    contract pages. **Operator decision.** *(The `.panel.is-big` print reset WAS shipped: this round
>    created that hazard, so it fixed it.)*
> 2. **`/analysis/{name}` panel 5 carries TWO ⛶** — the panel-head `⛶ ENLARGE` (inert) and scatter.js's
>    `⛶ Enlarge` (working). Pre-existing; the round-10 shadowing shape. Not fixed in rank 11.
> 3. **`/driving-path` overflows horizontally** — `scrollWidth` 1719 vs `clientWidth` 1440; the
>    11-column drill table overflows `main`. Pre-existing on both trees; the fix is in
>    `driving_tiers.js`, which is in the axis-caption freeze set.
>
> ### Also carried forward
> - **`docs/STATE/OPERATOR-REQUESTS.md` is NEW durable state** — the operator's 2026-07-28 notes:
>   OR-01 per-project metric roll-ups whose TITLES say what they compute, OR-02 the DCMA-11 call-out
>   that covers the left nav and will not dismiss (**a bug**), OR-03 Launch Sequence motion + a
>   ≥1-minute non-repeating boot "Hum" for the whole load. **None absorbed into round 11** — they
>   arrived mid-flight and an in-flight round is not a licence to widen scope.
> - **AXIS-TITLES batch 3b** — `PENDING` at **5** (`margin_dashboard`, `sra`, `sra_jcl`, `sra_ssi`,
>   `volatility`). Round 11 recorded `/volatility`'s caption state and changed nothing.
> - Still open: the `/resources` X-caption collision; the `/performance` `SFChartFrame` first-paint
>   race; monolith split phases 2-3; a DOM caption mechanism for the 13 `NO_SVG_AXES` visuals;
>   `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the `.mpp` probe UI (ADR-0293); GUIDED-MODE (5) +
>   VOICE-DECISION (4), parked on the operator.
>
> ### Remaining redesign tail
> **rank 12 — Library/Setup sweep** (`/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`,
> `/wbs/{name}`) · rank 13 — vendored typography (local IBM Plex Mono + Barlow woff2) · rank 14 —
> prototype token aliases (`--cnv`/`--pn2`/`--glow`) + universal `⊞ EXPLORE` drill wiring.
>
> ### Harness notes that saved this round (rebuild them, don't rediscover them)
> - **Upload the fixtures as ONE project.** Without the browser's `file_meta` companion JSON (a shared
>   `rel` top folder) five files load as five one-version projects and `/evolution` + `/volatility`
>   render their **"load at least two analyzable versions" FALLBACK**. The lead measured four empty
>   pages before catching it. `/path` also needs `POST /target uid=26`; `/driving-path` needs
>   `?source=11&target=26` (bare renders only the picker).
> - **Daylight's sticky header is ~359px tall** and steals clicks from any button scrolled above it
>   (`elementFromPoint` returns `SELECT`). Assert the button is the element at the click point BEFORE
>   clicking or you will report false no-ops — it reproduces on merged `/performance` too.
> - **Static CSS/JS is served live from disk; app.py is imported at boot.** A CSS change needs only a
>   reload; an app.py change needs a fresh server. One agent took a "before" baseline on an
>   already-patched tree and got a clean 0/0.
> - **Check the port is free** (`ss -lnt`) — an agent measured another session's server and got a
>   silently wrong baseline. And **never `pkill -f <pattern>` matching your own command line**: two
>   agents killed their own shells this round.
> - Known pre-existing flakes, refuted as regressions by repeat-runs on an UNCHANGED tree: `/analysis`
>   apollo panel 4 Gantt svg width (2275/2273/2364), `/curves` panel heights unsettled at 700ms,
>   `/trend` jarvis default caption y bimodal ±4px.
> - **⚠️ BUILD TRAP (still true):** `python -m build --wheel` writes to `dist/`, but
>   `tools/installer/build_installers.py` defaults to **`dist/wheel/*.whl`** and will silently embed a
>   STALE wheel. Always `--outdir dist/wheel`, regenerate, and run it in the BACKGROUND. ADR-0148's
>   lockstep test fires on ANY packaged-file change, so regenerate ONCE after all code edits land.
>
> ### DEPLOY (operator has no local clone)
> Download `installer/install-tier2.ps1` from the GitHub web UI and run
> `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
> One file; it fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit on
> `main`. An existing converter is never destroyed. Offline: Code → Download ZIP, run from inside the
> extracted folder.




# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
