# Handoff — 2026-06-09

This session: A17 (continuous build — see directive)     Next session: A18
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M14 + M16 complete. M15 (.pbix) BLOCKED. Next milestone = M17 (docs + final report + RTM closeout → DONE).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → after EACH milestone commit + push + refresh durable state.

## Branch note (READ FIRST)
Build lives on `claude/clever-carson-uovtkk` (PR #55), full A1–A17 lineage. If a fresh branch is behind,
`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/` → confirm it has M16
(`git log --oneline | grep m16`) → `git merge --ff-only`. Never start from greenfield.

### CI hygiene (LESSON): `git add -A` every milestone; run the gate with **honored exit codes**
(never `bandit | tail` — it hid a red CI for ~3 milestones). After pushing, verify the run's conclusion
is `success` (webhooks don't deliver CI success).

Green baseline (all green — **424 passed, 3 skipped; parity 10/10; egress 22/22; air-gap pass; launcher 100%; engine ~99%; overall ~99%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
pytest --cov=schedule_forensics --cov-fail-under=70 &&
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
pytest -m parity && bandit -q -r src && pip-audit --progress-spinner=off` — all exit 0.
Launch: `schedule-forensics` (or `python -m schedule_forensics.launcher`) → opens 127.0.0.1 dashboard.

## Completed this session (M16 — desktop launcher + packaging, §6.A)
- **M16** `d1b3cdd`: `launcher.py` (`main` → free loopback port + browser open + uvicorn on 127.0.0.1,
  non-loopback refused; injectable for tests, 100% cov) + `[project.scripts] schedule-forensics` +
  `packaging/` (Linux `.desktop`, macOS `.command`, Windows `.bat`, README). ADR-0020; RTM A2 → ✔.

## What exists now (M1–M14 + M16) — a complete, runnable, local forensic tool
Engine (CPM/float/driving-slack, DCMA-14, Acumen §A/§C, EVM, §E change, manipulation, audit,
recommendations) + AI (Null/Ollama, cited narrative) + web (dark-NASA dashboard, upload, audit,
recommendations, narrative, compare, interactive charts/grid/Gantt, settings, metric dictionary, wipe)
+ desktop launcher. Parity-green, air-gapped. **Remaining:** M15 (.pbix — BLOCKED on deposit), M17 (docs).

## Next session (A18 — Milestone **M17**: docs + final report + RTM closeout → DONE)
- **Milestone (BUILD-PLAN M17, RTM Q8 + §8 DoD):** the closing documentation set.
  1. **User guide** (`docs/USER-GUIDE.md`): install (`pip install -e .`), launch (`schedule-forensics`),
     upload ≤10 schedules, read the dashboard (audit, findings, narrative, interactive charts/grid/Gantt,
     compare), AI settings + classification banner, session wipe. Reference `packaging/README.md`.
  2. **Metric dictionary doc** (`docs/METRIC-DICTIONARY.md`): generate from `web/help.METRIC_DICTIONARY`
     (definition + formula + source per metric) — or point to the in-tool `/help`. Keep them consistent.
  3. **Parity report** (`docs/PARITY-REPORT.md`): the computed-vs-golden table for SSI (107/107), Acumen
     §A, §B (13/14 + High-Float +1), §C (counts+BFC; BSC residual), §E + Net Finish Impact −99, with the
     documented residuals + their root cause (progress-aware float, ADR-0012/0013/0014) and disposition.
  4. **Final report** (`docs/FINAL-REPORT.md`): map every §6.A–§6.G requirement → module(s) → test/evidence
     → status, citing the RTM. State the one externally-gated item: **M15 (.pbix) pending operator deposit**
     (not a defect). Note CUI posture (egress guard, air-gap test, loopback-only, fail-closed AI).
  5. Flip `docs/STATE/HANDOFF.md` Phase/Gate to **DONE** once the docs land and the gate is green; update
     the RTM so every row is ✔ except M15's `.pbix`-dependent enrichment (mark ◻ BLOCKED with the reason).
- **Acceptance:** docs present + internally consistent (a test may assert the metric-dictionary doc covers
  every emitted metric, mirroring `tests/web/test_help.py`); full gate + parity green; ADR-0021; HANDOFF DONE.
- **First steps:** (1) start ritual + confirm 424 baseline; (2) write the 4 docs (append in chunks to
  avoid stream-idle on long files); (3) RTM closeout + HANDOFF → DONE; full gate; final draft-PR refresh.

## Milestones remaining: M15 (.pbix — BLOCKED on deposit), M17 (docs + final report → DONE).
At DONE: every §6 RTM row ✔ except M15's `.pbix` enrichment (◻ BLOCKED — external input), with the
parity gate green and the tool runnable from a desktop icon, fully offline.

Open questions / blockers: only M15 (.pbix deposit). M17 completes everything else; the final report
documents M15 as the single pending operator-input item.
