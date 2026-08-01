# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.145**, highest ADR **0329**; a three-merge day —
**#503 (PR-10/OR-03, ADR-0328)**, **#504 (session close + the OR-04 collection kit)**, and
**#505 (batch 3c-i, ADR-0329)** all MERGED; #505 landed as `085da7b`. Verify with
`git fetch --prune origin` and restart your branch from `origin/main`. Fresh container:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build` first.

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm `085da7b` (#505) is main's ancestor and check whether
   the session-close docs PR is merged; restart your branch fresh from `origin/main`.
2. Then BUILD **batch 3c-ii — sra_jcl.js + sra_ssi.js join the caption convention** (the
   AXIS-TITLES finale: PENDING → empty closes the ledger for good). Prerequisite FIRST: teach
   `test_axis_titles_visual.py` to CLICK the Run buttons (`#jclRun`, `#ssiRun`) on `/sra` —
   both modules fetch and render only on demand, so their captions are unmeasurable until the
   harness clicks (the recorded reason for the 3c split, ADR-0329). Then caption: the JCL
   football (x finish date · y EAC — its corner quadrant %-labels sit EXACTLY in both caption
   corners and must yield per ADR-0303, likely the live-box mechanism), the cost S-curve
   (x EAC · y cumulative %), the SSI S-curve (x finish date · y cumulative %) and SSI
   histogram (x finish date · y simulated finishes). The FICSM strip is a labeled bar strip →
   recorded not-axis-chart (decision A1); the 5×5 matrices are natively-labeled HTML tables
   (ADR-0326's other medium). Both modules draw inside fetch callbacks (chartframe.js long
   loaded) — the ADR-0316 defer trap does NOT bite here, but CHECK script order anyway (the
   standing harness note). AXIS_CALL_SITES re-baselines 24 → N deliberately, prior entries
   byte-untouched; neither module is in PAGE_SCRIPTS.
3. Behind it: **the OR-04 ball stays with the operator** (run
   `audit/operator-artifacts/collect-ollama-artifacts.ps1` on the deployed box after one
   Ask-the-AI question; commit outputs + `smoke-results.md`) · the 7-module `DOM_PENDING`
   ledger · Phase 3 (CC-01 rendering half, 74 sites, Fable 5 Max) · Phase 4 (P1–P6) · rank
   13/14 · OR-03 residuals parked in ADR-0328 (operator's-ear hum acceptance; ogg fallback
   HELD). Known intermittent: the /analysis focus→tip family (dismiss + scroll siblings) —
   pre-existing, adjudicated in HANDOFF's carried list; do not chase it as a regression.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a
test; a fast wrong number is worthless) · ADR-0240 model/audit protocol · READ EVERYTHING,
ASSUME NOTHING, VERIFY EVERYTHING. Full gate before every commit; statics FOREGROUND first;
proved-able-to-fail on every new behavioral test; HANDOFF rotation + SESSION-LOG +
LESSONS-LEARNED same commit; wheel + nine installers ONCE after all code lands (bump the
version BEFORE launching the full background suite, or its installer-lockstep tests
red-herring against the stale wheel).
