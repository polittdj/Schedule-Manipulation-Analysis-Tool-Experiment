# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done, which is exactly what happened to the
pre-redesign version of this file.)

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` FIRST** — its top
section is the current state and the NEXT queue, and the SessionStart hook auto-injects it, so it is
already in front of you.

As of this file's last refresh: `main` green at **v1.0.121**, highest ADR **0305**, nothing in
flight (round 11 merged as #476, its verification follow-up as #477). Four CI checks must be green:
`test (3.11)`, `test (3.13)`, **`browser (measured-box proof)`**, and the `check` aggregate.
**Confirm `origin/main` still matches that** before starting.

**Standing rules (CLAUDE.md — read them, they are binding):**
(1) **Data sovereignty (CUI)** — no schedule content or derived metric leaves the machine; AI
loopback-only, fails closed; runtime I/O std-lib only; never commit a real CUI schedule (the
pre-commit guard blocks blocked-extension files outside the allowlists, including renames).
(2) **Fidelity over speed** — numbers must match the reference tools (Acumen Fuse v8.11.0 / SSI /
MSP) on the same inputs; never fabricate (NA reads "—", never a placeholder 0); parity is
gate-locked (`pytest -m parity`); never weaken a test or guard.
(3) **Model & audit protocol (ADR-0240)** — read the CLAUDE.md rule and choose based off the prompt
before starting: Fable 5 Ultracode for overall audits (one lead agent reconciles and validates every
major finding with code evidence + executable tests), Fable 5 Max for targeted deep dives (CPM
correctness, forensic algorithms, perf bottlenecks, disputed findings, hard architecture); other
models only when it makes sense and never at the risk of error or inaccuracy.
**READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING.**

**THE FIVE STANDING REQUIREMENTS for any UI round** are in HANDOFF's own section — carry all five.
Requirement 2 is the one this project keeps paying for: **a control must change a MEASURED BOX**
(`getBoundingClientRect()` before/after a real click), never just a class or a label.

**Per-PR workflow:** fresh branch off `origin/main` (always `git fetch origin` first; squash-merges
make stacked branches conflict) → make the change → full gate (ruff / `ruff format --check` / mypy
--strict / bandit **exit code read directly** / `pytest -q` / `node --check` for JS) → 4-theme
Chromium check for any UI change → for src changes: bump `pyproject.toml` + rebuild the wheel
(`python -m build --wheel --outdir dist/wheel`) + the 9 installers
(`python tools/installer/build_installers.py dist/wheel/schedule_forensics-<v>-py3-none-any.whl`),
rebuilt AFTER any reformat and ONCE after all code edits land (the ADR-0148 lockstep test fires on
any packaged-file change) → new ADR + refresh `HANDOFF.md`, `SESSION-LOG.md` and
`LESSONS-LEARNED.md` in the same commit (drift guard) → commit with the required trailers → push →
**draft PR** → `subscribe_pr_activity`. After a merge, restart the branch fresh from `origin/main`
with `--prune`. Never put the model id in any commit/PR/code.

**The work queue (rationale + detail in HANDOFF):**

1. **Redesign tail rank 12 — the Library/Setup sweep**: `/workbench`, `/groups`, `/standards`,
   `/margin`, `/card/{name}`, `/wbs/{name}`. Then rank 13 (vendored typography — local IBM Plex Mono
   + Barlow woff2; today the stacks are name-only) and rank 14 (prototype token aliases
   `--cnv`/`--pn2`/`--glow` + universal `⊞ EXPLORE` drill wiring).
2. **Operator decisions queued** (each already measured, none silent): `[data-noprint]` has **zero
   CSS rules anywhere** while set on 10+ elements across ten contract pages (DESIGN-SYSTEM §7 wants
   those controls hidden in print); `/analysis/{name}` panel 5 carries **two ⛶** (the panel-head one
   inert beside scatter.js's working one); `/evolution`'s pre-existing `⬇ Excel / ⬇ Word` bar is
   **target-blind** yet sits under a banner promising the exports honour the trace options.
3. **`docs/STATE/OPERATOR-REQUESTS.md`** — three operator requests raised 2026-07-28, none absorbed
   into an in-flight round: OR-01 per-project metric roll-ups whose TITLES say what they compute,
   OR-02 the DCMA-11 call-out that covers the left nav and will not dismiss (**a bug**), OR-03
   Launch Sequence motion + a ≥1-minute non-repeating boot "Hum" for the whole load.
4. **AXIS-TITLES batch 3b** — `PENDING` at 5 (`margin_dashboard`, `sra`, `sra_jcl`, `sra_ssi`,
   `volatility`). Plus the older backlog: the `/resources` X-caption collision, the `/performance`
   `SFChartFrame` first-paint race, monolith split phases 2-3, a DOM caption mechanism for the 13
   `NO_SVG_AXES` visuals, `_ANALYSIS_CACHE_MAX = 48` (ADR-0292), the `.mpp` probe UI (ADR-0293),
   GUIDED-MODE (5) + VOICE-DECISION (4).

**Harness notes that cost real time — rebuild them, do not rediscover them** (full detail in
HANDOFF): upload the fixtures as ONE project via the browser's `file_meta` companion JSON or
`/evolution` + `/volatility` render their "load at least two analyzable versions" FALLBACK; `/path`
needs `POST /target uid=26` and `/driving-path` needs `?source=11&target=26`; a **git worktree does
not change what Python imports** (the editable-install `.pth` pins the MAIN checkout's `src`, so pin
`PYTHONPATH` and assert the served bytes); a free port can be taken by another session minutes
later, so md5 what you actually measured; daylight's sticky header is ~359px and steals clicks
(assert `elementFromPoint` is the button before clicking); static CSS/JS is served live from disk
while app.py is imported at boot; `pytest --cov` is ~3x slower than plain `pytest`, so a long CI run
is usually slow, not hung.

Work autonomously: full gate before every commit, draft PR per increment, pause only for genuinely
operator-only decisions.
