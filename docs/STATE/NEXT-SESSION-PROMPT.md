# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins.)

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` FIRST** — its top
section is the current state and the NEXT queue (the SessionStart hook auto-injects it, so it is
already in front of you). As of this file's last refresh that meant: `main` green at **v1.0.59**,
highest ADR **0250**, full gate green (ruff / ruff format --check / mypy --strict / bandit exit 0 /
node --check / full pytest incl. the `parity` gate). PR #389 (ADR-0250, the deep-audit remediation)
is the last landed work — **confirm it merged** before starting; if it is still open, get it green
and squash-merged first.

**Standing rules (CLAUDE.md — read them, they are binding):**
(1) **Data sovereignty (CUI)** — no schedule content or derived metric leaves the machine; AI
loopback-only, fails closed; runtime I/O std-lib only; never commit a real CUI schedule (the
pre-commit guard blocks blocked-extension files outside the allowlists, including renames).
(2) **Fidelity over speed** — numbers must match the reference tools (Acumen Fuse v8.11.0 / SSI /
MSP) on the same inputs; never fabricate (NA reads "—", never a placeholder 0); parity is
gate-locked (`pytest -m parity`); never weaken a test or guard.
(3) **Model & audit protocol (ADR-0240)** — read the CLAUDE.md rule and choose based off the
prompt before starting: Fable 5 Ultracode for overall audits (one lead agent reconciles and
validates every major finding with code evidence + executable tests), Fable 5 Max for targeted
deep dives (CPM correctness, forensic algorithms, perf bottlenecks, disputed findings, hard
architecture); other models only when it makes sense and never at the risk of error or
inaccuracy. READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING.

**Per-PR workflow:** fresh branch off `origin/main` (always `git fetch origin` first; squash-merges
make stacked branches conflict) → make the change → full gate (ruff / ruff format --check / mypy
--strict / bandit **exit code read directly** / `pytest -q` / `node --check` for JS) → 4-theme
Chromium check for any UI change → for src changes: bump `pyproject.toml` + rebuild the wheel
(`pip wheel . --no-deps -w dist/wheel`, or `python -m build --wheel --outdir dist/wheel`) + the 9
installers
(`python tools/installer/build_installers.py dist/wheel/schedule_forensics-<v>-py3-none-any.whl`),
rebuilt AFTER any reformat → new ADR + refresh `HANDOFF.md` and `SESSION-LOG.md` in the same
commit (drift guard) → commit with the required trailers → push → **draft PR** →
`subscribe_pr_activity`. After a merge, restart the branch fresh from `origin/main` with
`--prune`. Never put the model id in any commit/PR/code.

**The work queue (rationale + detail in HANDOFF's NEXT section):**

1. **OPERATOR DECISION first — the one ADR-0250 finding left unfixed (`ignore-toggles-noop-on-dated`):**
   the `/driving-path` "Ignore constraints" / "Ignore leveling delay" trace options do NOT use
   recomputed CPM dates for tasks that carry stored dates, so for a dated schedule the toggle is a
   no-op while the docstring/UI implies it re-derives the path. Two honest resolutions, and the choice
   is a product call: **(a)** change the trace to recompute dates under the toggle (a behavior change
   with parity implications — must be re-validated against Acumen/SSI), or **(b)** correct the
   docstring + UI copy to describe what the toggle actually does. Do NOT guess — ask the operator which,
   then implement + regression-test.
2. **#13** XER per-task calendars (real JUICE `.xer` files show `cals=0`; operator will re-add real
   `.xer`) → **base-CPM single-calendar fail-soft disclosure** (task #26) → **F3c** parameterized
   expected margin → **roles front-end** (v4 F4).
3. **Deferred perf items (were parked in ADR-0249's audit-F harness):** import peak memory rides the
   MSPDI-streaming work; AI-cancellation behavior rides its own PR — each gets a deterministic gate in
   `tests/perf/test_perf_regression.py` when that work lands (do NOT add flaky wall-clock latency
   gates).
4. **Operator-side (no code):** apply the `00_REFERENCE_INTAKE/INDEX.md` §3 reorganization map via the
   GitHub web UI when convenient (the CUI guard rightly blocks local renames), including the §4
   root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

Work autonomously: full gate before every commit, draft PR per increment, pause only for genuinely
operator-only decisions (item 1 is one — ask before coding it).
