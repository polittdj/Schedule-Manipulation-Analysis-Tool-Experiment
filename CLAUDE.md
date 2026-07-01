# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local, offline, **CUI-safe forensic schedule-analysis** tool. It ingests MS Project / Primavera
schedules, runs CPM + DCMA-14 / Acumen Fuse v8.11.0 / SSI / EVM parity metrics + manipulation-trend
detection, and serves an interactive, locally-rendered report with a cited local-AI narrative. Python
3.11+, FastAPI, standard-library-only I/O. `docs/STATE/HANDOFF.md` is the live "where we are" doc.

## The two non-negotiable laws

1. **Data sovereignty (CUI).** No schedule content or derived metric ever leaves the machine; the AI is
   loopback-only and fails closed. **Never commit CUI files** — real `.mpp` / `.xlsx` / `.aft` / `.xer`
   / `.docx` schedules and reference exports. A pre-commit guard (`.githooks`, activated by the
   SessionStart hook) blocks them; intake/golden files live git-ignored under `00_REFERENCE_INTAKE/`.
   **CUI boundary (operator-confirmed):** the *build/reference* inputs used to develop and parity-test
   the tool — including `Large_Test_File.mpp`, the SSI/Acumen exports, and golden inputs — are **NOT
   CUI** and may be loaded into a build session (e.g. uploaded to Claude Code). They are kept out of git
   as large binaries / defense-in-depth, not because they are CUI. **Real CUI is only ever the
   operator's production schedules loaded into the deployed tool, which runs locally and never touches a
   build session.** The pre-commit guard still blocks `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` regardless,
   so no binary reference file lands in the repo.
   Runtime I/O is **std-lib only** (no `requests`/`httpx`/etc.); a net-egress guard fails the build if a
   forbidden HTTP client enters the runtime, and an air-gap test fails if a served page references a
   remote asset.
2. **Fidelity over speed.** Numbers must match the reference tools on the same inputs; a fast wrong
   number is worthless in a testimony context. Parity is gate-locked (`pytest -m parity`).

## Commands

Full gate — run before every commit (CI runs it on Python 3.11 + 3.13):

```bash
ruff check src/ tests/
ruff format --check .
python -m mypy src/                                    # strict
bandit -q -r src                                       # only a non-zero EXIT is a failure (nosec warnings are not)
python -m pytest -q                                    # coverage gates: engine >=85%, overall >=70%
node --check src/schedule_forensics/web/static/*.js    # vendored JS, no build step
```

- Single test: `python -m pytest tests/web/test_groups_view.py::test_filter_scopes_the_population -q`
- Parity gate only: `python -m pytest -m parity`
- Run the app: `schedule-forensics` (or `python -m schedule_forensics.launcher`) — binds 127.0.0.1 and opens the browser.
- `.mpp` → MSPDI XML (needs Java 17+): `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in.mpp> <out.xml>`

`src/schedule_forensics/web/app.py` is **exempt from E501** (line-length) in `pyproject.toml` — don't
fight long HTML f-strings there; everywhere else the limit is 100.

## Architecture (the big picture)

Flow: **importer → `Schedule` model → engine (CPM + metrics) → `web/app.py` (FastAPI) → server-rendered
HTML + vendored JS charts**, with the AI layer polishing narrative on top of already-computed figures.

- **`model/`** — frozen pydantic models (`Task`, `Schedule`, `Calendar`). `Task.unique_id` is the
  **sole** cross-version identity (never the row id, which renumbers; never the name). Durations are
  integer **working minutes** (480 = one 8-hour day); the days conversion happens only at the
  presentation boundary. CPM dates/float are **derived by the engine, never stored** on the task.
  Optional date/cost fields default to `None` meaning "the source didn't provide it" — never assume 0.
- **`engine/`** — `cpm.py` (CPM solver → `CPMResult`); `metrics/` (one module per family: `dcma14`,
  `cei`, `hmi`, `fei_bri`, `float_ratio`, `float_bands`, `schedule_quality`, `evm`,
  `completion_performance`, …), each returning the frozen `MetricResult` from `metrics/_common.py`;
  `trend.py` (cross-version series); `grouping.py` (field filters); plus `driving_slack`, `manipulation`,
  `recommend`, `narrative`. Crucial for Acumen parity: `_common.effective_total_float` /
  `is_effective_critical` prefer the source tool's **stored, progress-aware** Total Slack / Critical flag
  over recomputed pure-logic CPM float when the file carries it.
- **`importers/`** — `mspdi` (MS Project XML, the richest path), `xer` (Primavera), `json_schedule` (the
  tool's own). Native `.mpp` has **no Python parser** — it is converted to MSPDI via the vendored MPXJ
  (`tools/mpxj/`, Java), auto-discovered, no Maven/build step.
- **`ai/`** — the `AIBackend` protocol (`generate` / `list_models` / `pull_model` / `is_available`) with
  `NullBackend` (deterministic offline default — returns the prompt unchanged), `OllamaBackend`, and
  `OpenAICompatBackend` (both **loopback-validated at construction**; `route_backend` fails closed to
  Null and never auto-reaches cloud). Used for narrative polish, Ask-the-AI Q&A, the executive briefing,
  and translation. The **narrative / briefing / translation** paths re-verify every AI-emitted figure
  against engine citations (`ai.citations.reattach` — a numeric subset gate). It guards *digits*
  (figure preservation, sign-aware) **and**, since ADR-0132 (audit H2), rejects a rephrase that
  *introduces an accusatory/intent term the engine never asserted* (fraud, deliberate, concealed, …
  via `introduces_loaded_terms`) — but it does not otherwise constrain prose wording, so a model can
  still reword non-accusatorily. **Ask-the-AI Q&A is operator-mode-gated** (ADR-0129): `strict` discards any answer
  containing an unsourced figure, `annotate` (default) keeps the answer but flags AI-derived figures in
  a footer, and `interpretive` returns the model's text verbatim and is *not* figure-gated (the operator
  opts into raw analysis, with the standing "AI can err — verify against the citations" disclaimer). So
  "no unsourced number reaches the analyst" holds for narrative/briefing and the strict/annotate Q&A
  modes — not for interpretive. The strict/annotate gate is **role-aware** (audit F-11, ADR-0137):
  `ai/qa.py::_figure_roles` splits the cited figures into **value** figures (a digit appearing in a
  fact's text *outside* any cited activity name/`UID n`) and **identifier** figures (carried by a
  citation's task name or unique id). A digit that matches **only** an identifier — e.g. a name-digit
  `2099` from "Milestone 2099" re-used as a finish year, or UID `6077` re-used as a count — is one the
  model re-roled: **strict discards** that answer, **annotate flags** it (`_ROLE_NOTE`). The split is
  **collision-safe** — a digit that is *both* a value and an identifier (a count `5` that is also some
  UID `5`) counts as a value and is never discarded, which is why a blunt set-exclusion (that couldn't
  tell UID `5` from count `5`) was wrong. Interpretive stays ungated by design. A fuller *semantic* role
  model (beyond value-vs-identifier) remains the `AI-DERIVED-METRICS-SCOPE.md` Layer B direction.
- **`web/app.py`** — the entire UI in one (large) file: routes + server-rendered HTML + a Jinja layout.
  `SessionState` is the in-memory, per-process session (loaded `schedules`, `ai_config`,
  `active_filter`, `language`, caches). The per-schedule analysis chokepoint is `_Analysis`, built once
  by `_compute_analysis(sch)` (a single CPM pass reused by every view) and cached via
  `SessionState.analysis_for(key, sch)`. The **session-wide group/filter** funnels through
  `SessionState.scope()`: `analysis_for` scopes internally and `ordered()` returns the scoped
  multi-version list, so a filter set on `/groups` applies to every page and every loaded file. Static
  JS/CSS are vendored (no CDN, no bundler) and a strict CSP enforces the air-gap.
- **`web/i18n.py`** — EN/ES/FR/DE/PT: a hand-built catalog (`_TERMS`, english → per-language) + an AI
  fallback (`/api/translate`) + non-destructive client-side DOM translation (`static/translate.js`).

## Metric formulas come from "the Bible"

Authoritative metric formulas are taken from the **NASA Acumen metric library**
(`NASA_Metrics_Complete_*.aft`, an XML `<MetricLibraryFile>` of `<Metric>` Name/Formula) — a CUI intake
file kept **outside the repo** (operator upload). When adding or auditing a metric, pull the formula
verbatim from that `.aft` and validate against the operator's Acumen comparison exports. Each metric's
definition + formula + source lives in `web/help.py`; `docs/METRIC-DICTIONARY.md` is **generated** from
it, so after editing `help.py` regenerate it (a test enforces sync):

```bash
python -c "from schedule_forensics.web.help import render_dictionary_markdown as r; open('docs/METRIC-DICTIONARY.md','w',encoding='utf-8').write(r())"
```

## Durable state & the drift guard

- `docs/STATE/HANDOFF.md` — **read first**; single source of truth for "where we are / what's next."
- `docs/STATE/SESSION-LOG.md` — append-only per-session history.
- `docs/adr/NNNN-*.md` — one ADR per significant decision.
- `tests/test_state_docs.py` **fails** unless the highest ADR number on disk appears in BOTH `HANDOFF.md`
  and `SESSION-LOG.md` — so any change that adds an ADR must refresh both docs in the same commit.

## Workflow

- Branch from `main`, open a **draft PR**, get CI green, squash-merge. Squash-merges make stacked
  branches conflict, so branch fresh from `main` and merge-resolve rather than stacking.
- **Always `git fetch origin` before you branch or rebase** (best practice, all sessions). The local
  `main` goes stale between sessions; `git fetch origin` updates the remote-tracking refs *without*
  touching your working branches, so you branch/rebase onto the real latest `origin/main`
  (e.g. `git fetch origin && git switch -c <branch> origin/main`) instead of a stale local copy.
- The `qc-checker` subagent (`.claude/agents/`) runs the full gate, triages real errors vs
  environment-gated skips / flakes, and fixes them — on demand or via a throttled SessionStart trigger.
