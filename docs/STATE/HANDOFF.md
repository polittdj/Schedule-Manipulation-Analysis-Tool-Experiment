# Handoff — 2026-06-08

This session: A13 (continuous build — see directive)     Next session: A14
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M11 complete (full analysis engine done). Next milestone = M12 (local AI backend + cited narrative).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST)
Build lives on `claude/clever-carson-uovtkk` (PR #55), full A1–A13 lineage. A14: if your assigned branch
is behind, find the latest tip (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`),
confirm it has this M11 work (`git log --oneline | grep m11`), and `git merge --ff-only` onto it. Never
start from greenfield.

Green baseline (all green — **385 passed, 3 skipped; parity gate 10/10; engine ~99%; overall ~99%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m pytest -m parity && python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; 3 skipped tests are the real-`.mpp` integration tests — expected.

## Completed this session (M11 — version diff + manipulation trends, §6.D)
- **M11** `1b841cc`: `engine/diff.py` (`diff_versions` by UniqueID → `VersionDiff`) + `engine/manipulation.py`
  (`detect_manipulation` → cited Findings: deleted tasks/logic, shortened durations, baseline 29I401a +
  actual 06A504* date edits; **no false positives on the honest P2→P5**; `trend_across_versions` →
  CPM/progress trend). ADR-0016; RTM D1 → ▣, B3 → ✔. + the M11 durable-state commit.

## Engine status — the analysis core is COMPLETE (M1–M11)
`model/` · `importers/` (MSPDI/XER/MPXJ, ≤10 loader) · `engine/`: cpm, float_analysis, driving_slack/
path_trace, metrics/{dcma14, schedule_quality, evm, change_metrics}, dcma_audit, recommendations, diff,
manipulation. Parity gate green. **Remaining = product surface:** `ai/` (M12), `web/` (M13/M14), `.pbix`
(M15), `launcher.py` (M16), docs/final report (M17).

## Next session (A14 — Milestone **M12**: local AI backend (Ollama) + cited narrative, §6.D/§6.F)
- **Milestone (BUILD-PLAN M12, RTM D1/D2/F1/F2/F3, G1):** a **pluggable** AI backend (Null default +
  Ollama) that can list/pull/select local models in-app, plus a "generate a story" narrative where
  **every sentence is cited** (file + UID + task), built on the M10/M11 `Finding`/`TrendPoint` signals.
  CUI fail-closed routing: local Ollama only by default; cloud only behind an explicit "unclassified"
  toggle with a **persistent banner naming the endpoint**; never auto-fall-back to cloud.
- **CUI / egress (HARD — Law 1):** the egress guard forbids `requests`/`httpx`/`aiohttp`/`urllib3`/
  websockets as **runtime** deps and forbids cloud SDK modules; loopback (`127.0.0.1`/`localhost`) is
  allowed. So the **Ollama backend must use stdlib `urllib.request` to `http://127.0.0.1:11434`** (the
  guard already names this) and add **no** forbidden runtime dependency. `tests/guards/test_egress.py`
  must stay green. Validate the target host with `net_guard`'s loopback check before any call.
- **Acceptance criteria:**
  1. `ai/backend.py` — `AIBackend` protocol (`generate`, `list_models`, `pull_model`, `is_available`) +
     an `AIConfig` (classification CLASSIFIED default / UNCLASSIFIED; active model; endpoint).
  2. `ai/null.py` — `NullBackend` (deterministic, offline, **default**): renders the narrative from the
     cited findings with no model — used in CI and as the fail-closed fallback.
  3. `ai/ollama.py` — `OllamaBackend` via **stdlib urllib to 127.0.0.1:11434** (list/pull/generate);
     fail-loud if unreachable; never a remote host. Unit-test request/payload construction without a live
     server (inject a transport / monkeypatch urlopen); mark any live-server test skip-if-unavailable.
  4. `ai/citations.py` — enforce that **every sentence** in the narrative carries ≥1 citation; raise if
     not (a test feeds an uncited sentence and asserts the raise). `ai/narrative.py` — assemble the
     "story" (CPM trend, manipulation trends, audit, recommendations) as cited statements; if a backend
     polishes the prose, re-verify citation coverage on the output (AI rephrases, never invents).
  5. CUI routing: `route_backend(config)` returns the local backend when CLASSIFIED; cloud only when
     UNCLASSIFIED **and** a banner is produced naming the endpoint; fail closed to Null otherwise. Test
     the fail-closed paths. Egress guard + full gate + parity stay green; engine ≥85 / overall ≥70.
- **Files:** `ai/{backend,null,ollama,citations,narrative}.py`, `tests/ai/test_*`; export via `ai/__init__.py`;
  ADR-0017; update RTM D1/D2/F1/F2/F3. Do **not** add runtime deps (stdlib only for AI transport).
- **First steps:** (1) start ritual + confirm 385 baseline + egress guard green; (2) design `AIBackend`
  protocol + `CitedStatement`/`Narrative` types (sentence → citations); (3) NullBackend + citations
  enforcement first (CI-safe), then OllamaBackend (urllib/loopback) + CUI routing; full gate; → M13.

## Milestones remaining: M12 (local AI + cited narrative), M13 (web UI shell + dark NASA theme + settings
+ in-tool help/metric dictionary), M14 (interactive visuals + drill-down), M15 (.pbix enrich), M16
(desktop launcher), M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none. M12 guardrail: keep AI transport **stdlib-only to loopback**; the
narrative's facts come from the cited engine Findings (the model only rephrases) so the story can never
fabricate or leak — that is both the §6.D citation requirement and the §6.G/Law 1 CUI defense.
