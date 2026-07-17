# ADR-0240: Standing model/audit protocol, the reference-intake INDEX, and the 2026-07-17 doc-truth pass

- **Status:** Accepted (operator-directed)
- **Date:** 2026-07-17

## Context

The operator issued two standing directives at the close of the 2026-07-17 session:

1. *"Audit the repo and read everything. Assume nothing. … READ EVERYTHING, ASSUME NOTHING,
   VERIFY EVERYTHING, update the handoff and all other documentation in the repo that needs to be
   updated or revised after first verifying that any finding is first valid and not a mistake on
   your part. Also organize all the files in the 00_REFERENCE_INTAKE folder and put them in a
   logical order as well as retitle them if necessary and update your index of what is there and
   how it is all to be used, what tests each can verify…"*
2. An attached rule file (now preserved at `00_REFERENCE_INTAKE/Use Fable 5 Ultracode.md`):
   *"Make this a rule and always read the below and choose based off the prompt you are given for
   this project before starting to respond…"* — Fable 5 Ultracode for overall audits (security,
   architecture, performance, tests, documentation, dependencies, UI, data validation, scheduling
   algorithms), one lead agent to reconcile conflicts and validate every major finding with code
   evidence and executable tests, Fable 5 Max afterward for targeted deep dives (CPM calculation
   correctness / schedule-forensics algorithms / performance bottlenecks / a disputed audit
   finding / a difficult architectural decision). The operator additionally allowed: other models
   may be used when it makes sense, **but not at the risk of error or inaccuracy**.

The read-everything audit ran as four parallel read-only agents (code, prior-audit claims,
reference corpus, docs/state) with this session acting as the lead agent, independently
re-verifying every major finding against the working tree before acting on it.

## Audit verdict (2026-07-17, v1.0.51 / ADR-0239 baseline)

- **Code: green.** Full gate passes (ruff / ruff format / mypy --strict / bandit exit 0 /
  node --check / full pytest incl. `-m parity`). No BLOCKER/HIGH/MEDIUM code defect found that is
  not already queued (PR-R2/R3 remediation queue re-confirmed accurate: dead Law-1 defenses
  `configure_logging`/`assert_local_only` still uncalled at startup; air-gap page list still
  hard-coded; state-docs guard does not pin the pyproject version; margin-erosion mixed-basis fit;
  XER worked-weekend exceptions; egress-set additions; 24h-calendar MPXJ golden).
- **Docs: drifted in verified places, now fixed** (see Decision 3).
- **Reference intake: complete and tracked**, but unorganized at the root and carrying
  known byte-conflicts that are now documented in the INDEX (see Decision 2).

## Decision

1. **The model/audit protocol is a durable repo rule.** Recorded in `CLAUDE.md` ("Model & audit
   protocol"), faithful to the operator's file, with the operator's addendum: other models when it
   makes sense, never at the risk of error or inaccuracy — anything parity-, engine-, testimony-,
   or CUI-relevant stays on the strongest available model and every delegated result is
   lead-validated against code evidence and executable tests.

2. **`00_REFERENCE_INTAKE/INDEX.md` is the intake catalog** — logical grouping, per-file purpose,
   which tests each file verifies, verified duplicate/byte-conflict table, and a proposed
   reorganization/rename map. **Physical renames/moves are operator-side (GitHub web UI) by
   design:** the CUI pre-commit guard scans renames (`--diff-filter=AMR`) and a renamed
   blocked-extension binary's new path is not on `origin/main`, so a local `git mv` is blocked.
   That is the guard working as intended (ADR-0152's `inherited_from_main` exception is
   deliberately path-exact) — the guard is **not** weakened for housekeeping. `.gitignore` gains a
   single `!00_REFERENCE_INTAKE/INDEX.md` exception so the catalog itself is committable locally.

3. **Doc-truth fixes, each independently verified against the tree before editing:**
   - `docs/STATE/NEXT-SESSION-PROMPT.md` — was frozen at v1.0.46/ADR-0234 with a queue of
     already-merged PRs; rewritten to the v1.0.51/ADR-0240 state and live queue.
   - `docs/STATE/REPO-INVENTORY.md` — `SCHEMA_VERSION` said 2.7.0 (source says 2.8.0 since
     ADR-0234); version/ADR stamps said 1.0.46/0234 (and an appendix said 1.0.39); the engine map
     lacked `metrics/sem.py` and the `/standards` page; the ADR count was stale; the RTM summary
     quoted superseded parity numbers.
   - `docs/USER-GUIDE.md` — header stamp was v1.0.18/2026-07-13; restamped with a short
     "what's new" pointer (full guide refresh remains future work).
   - `docs/PLAN/RTM.md` — B2/C2 cited the deleted `ssi_uid143` golden and superseded numbers
     ("SSI 107/107", Net Finish Impact "−99"). The live parity gate asserts: SSI UID-145
     all-dependencies **108/108** (plus UID-67/UID-152/UID-152-leveled/UID-155 goldens) and Net
     Finish Impact **−148** on the engine-CPM basis, reconciled day-exact to Fuse's stored-basis
     **−134** (ADR-0108/0112).
   - `tests/fixtures/golden/ssi_uid145/case.json` `_source` — pointed at a dead
     `00_REFERENCE_INTAKE/audit/ssi_uid145/` path; now cites the real tracked export. Verified
     provenance-only (no test reads `_source`).
   - `tests/engine/test_chain_acumen_reference.py` — comment cited a dead
     `audit/2345_bundle/…` path; the tracked source is `00_REFERENCE_INTAKE/P2-P5 - Metric
     History Report.xlsx`. Comment-only change; pinned values untouched.
   - `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` — claimed the folder is "git-ignored so it can never
     be committed"; superseded by ADR-0151/0152 (the suite **is** tracked, committed via the
     GitHub web UI). Corrected with a pointer to INDEX.md.

## Consequences

- Every future overall audit follows the Ultracode-then-Max protocol with lead validation;
  findings without code evidence + an executable test do not land.
- The intake folder has a single authoritative catalog; test-load-bearing paths are labeled so
  the operator's web-UI reorganization cannot silently break the suite.
- Superseded parity numbers no longer appear in living docs; RTM evidence now matches what the
  parity gate actually asserts.
