# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins.)

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` FIRST** — its top
section is the current state and the NEXT queue. As of this file's last refresh that meant:
`main` green at **v1.0.52**, highest ADR **0241**, full gate green (ruff / ruff format --check /
mypy --strict / bandit exit 0 / node --check / full pytest incl. the `parity` gate).

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
(`python -m build --wheel --outdir dist/wheel`) + the 9 installers
(`python tools/installer/build_installers.py dist/wheel/schedule_forensics-<v>-py3-none-any.whl`),
rebuilt AFTER any reformat → new ADR + refresh `HANDOFF.md` and `SESSION-LOG.md` in the same
commit (drift guard) → commit with the required trailers → push → **draft PR** →
`subscribe_pr_activity`. After a merge, restart the branch fresh from `origin/main` with
`--prune`. Never put the model id in any commit/PR/code.

**The work queue (rationale + goldens in HANDOFF's NEXT section):**

1. **PR-R3 — data-fidelity residue:** margin-erosion fit restricted to a single margin basis (or
   an explicit mixed-basis warning); XER worked-weekend calendar exceptions; egress-guard set
   additions (modern LLM/telemetry hosts); commit the 24h-calendar MPXJ golden (SSI pair:
   `Hard_File_updated3` UID-155 slack 32d ↔ `Hard_File_updated4 24 hour calendar` 18d, same
   100-row path — files + Fuse fieldmap already in `00_REFERENCE_INTAKE/`, see its INDEX.md).
2. **PR-P1 — validated perf items** (CoPilot #3/#4/#8/#9/#10 + the audit-E summary-logic edge
   guard; the refuted claims #1/#5/#6/#7-race are documented — do NOT "fix" them).
3. **#13** XER per-task calendars (real JUICE `.xer` files show `cals=0`; operator will re-add
   real `.xer`) → **base-CPM single-calendar fail-soft disclosure** (task #26) → **F3c**
   parameterized expected margin → **roles front-end** (v4 F4).
4. **Operator-side (no code):** apply the `00_REFERENCE_INTAKE/INDEX.md` §3 reorganization map
   via the GitHub web UI when convenient (the CUI guard rightly blocks local renames), including
   the §4 root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

Work autonomously: full gate before every commit, draft PR per increment, pause only for genuinely
operator-only decisions.
