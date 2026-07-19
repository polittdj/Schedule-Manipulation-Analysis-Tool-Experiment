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
   SessionStart hook) blocks them.
   **CUI boundary (operator-confirmed):** the *build/reference* inputs used to develop and parity-test
   the tool — including `Large_Test_File.mpp`, the SSI/Acumen exports, the NASA `.aft` metric library,
   and golden inputs — are **NOT CUI** and may be loaded into a build session (e.g. uploaded to Claude
   Code). **Real CUI is only ever the operator's production schedules loaded into the deployed tool,
   which runs locally and never touches a build session.** Because those reference inputs are not CUI,
   the operator chose (ADR-0152) to commit the intake suite under `00_REFERENCE_INTAKE/` to `main` (via
   the GitHub web UI), formally superseding the earlier "keep the binaries out of git" defense-in-depth
   posture — so the reference binaries **do** live in the repo now. The pre-commit guard still blocks
   `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` everywhere except the `tests/fixtures/` allowlist (synthetic,
   hand-authored, non-CUI fixtures only) **and** except a staged blob that is byte-identical to
   `origin/main` at the same path (ADR-0152's `inherited_from_main` exception, so `git merge origin/main`
   isn't wedged by the already-public intake blobs). A **new** or **modified** (tampered) blocked-extension
   file anywhere outside those two allowances is still blocked — so no real CUI schedule from a build
   session can land in the repo.
   Runtime I/O is **std-lib only** (no `requests`/`httpx`/etc.); a net-egress guard fails the build if a
   forbidden HTTP client enters the runtime, and an air-gap test fails if a served page references a
   remote asset.
2. **Fidelity over speed.** Numbers must match the reference tools on the same inputs; a fast wrong
   number is worthless in a testimony context. Parity is gate-locked (`pytest -m parity`).

## Model & audit protocol (standing operator rule, ADR-0240)

**Always read this rule and choose based off the prompt you are given for this project before
starting to respond** (operator directive 2026-07-17; the original directive file is preserved at
`00_REFERENCE_INTAKE/Use Fable 5 Ultracode.md`):

- **Use Fable 5 Ultracode for the overall audit**: security, architecture, performance, tests,
  documentation, dependencies, UI, data validation, and scheduling algorithms.
- **Require one lead agent to reconcile conflicts and validate every major finding using code
  evidence and executable tests** — no finding is reported until the lead has independently
  re-verified it against the actual code/fixtures (audit findings have been wrong before; a
  mistaken "fix" is worse than the drift it chases).
- **Use Fable 5 Max afterward for targeted deep dives** into: CPM calculation correctness ·
  schedule-forensics algorithms · performance bottlenecks · a disputed audit finding · a
  difficult architectural decision.
- **Other models may be used when it makes sense** (cheap mechanical sweeps, formatting,
  broad read-only reconnaissance) **but never at the risk of error or inaccuracy** — anything
  parity-, engine-, testimony-, or CUI-relevant stays on the strongest available model, and every
  delegated result is re-validated by the lead before it lands (Law 2 always wins).

"Fable 5 Ultracode" = the operator's label for the full multi-agent orchestrated audit;
"Fable 5 Max" = the maximum-effort single-focus deep dive. Companion working rules that ride with
this protocol: **READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING** — verify a finding is real
(not your own mistake) before changing anything it touches.

## Commands

Full gate — run before every commit. CI (Python 3.11 + 3.13) runs the Python steps plus pip-audit and enforces the coverage gates; the `node --check` step is local-only, and plain local `pytest -q` does NOT collect coverage (the 85/70 numbers are CI-enforced):

```bash
ruff check src/ tests/
ruff format --check .
python -m mypy src/                                    # strict
bandit -q -r src                                       # only a non-zero EXIT is a failure (nosec warnings are not)
python -m pytest -q                                    # coverage gates (CI-enforced): engine >=85%, overall >=70%
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
  `recommendations` (findings/risk matrix; AI narrative lives in `ai/`). Crucial for Acumen parity: `_common.effective_total_float` /
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
  modes — not for interpretive. The strict/annotate gate is **role-aware** (audit F-11, ADR-0137;
  hardened ADR-0138): `ai/qa.py::_figure_roles` splits the cited figures into **value** figures (a
  token in a fact's text outside every cited activity-name/`UID n` **span**) and **identifier**
  figures (carried by a citation's task name or unique id). A digit that matches **only** an
  identifier and is used **as a value** — a name-digit `2099` re-used as a finish year, UID `6077`
  re-used as a count — is discarded (strict) / flagged (annotate); writing an identifier *as* an
  identifier (`UID 143`, a quoted cited name) passes. The split is **collision-safe** (a digit that
  is both value and identifier counts as a value) and hardened per the 2026-07-01 QC audit: ISO
  dates tokenize **whole** (`citations.figure_tokens` — no month/day pseudo-figures can seed the
  Layer-B operand pool), integer derivation targets must reconstruct **exactly** (counts are exact;
  1-dp tolerance is for decimal ratios only), the identifier check runs **before** the derivation
  check (no laundering a re-roled UID through a coincidental ratio), and identifier extraction is
  span-based (an empty/digit-bearing task name cannot shred the value set). The unit-role step
  (ADR-0145) adds the first semantic check: an explicit-unit contradiction (a "5%"-only figure
  re-used as "5 days") is discarded/flagged; bare usages and multi-unit tokens never are.
  Interpretive stays ungated by design. A fuller semantic role model remains future work.
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
(`NASA Metrics_Complete_*.aft`, an XML `<MetricLibraryFile>` of `<Metric>` Name/Formula). This
reference `.aft` is **non-CUI** (operator-confirmed, see the Law-1 note above) and is **committed**
under `00_REFERENCE_INTAKE/` per ADR-0151/0152, so the formula-pinning test
(`tests/engine/test_aft_formula_audit.py`) runs against the real library (on CI too). A **real CUI**
`.aft` from a production machine is still never committed — the pre-commit guard blocks it. When adding
or auditing a metric, pull the formula verbatim from that `.aft` and validate against the operator's
Acumen comparison exports. Each metric's
definition + formula + source lives in `web/help.py`; `docs/METRIC-DICTIONARY.md` is **generated** from
it, so after editing `help.py` regenerate it (a test enforces sync):

```bash
python -c "from schedule_forensics.web.help import render_dictionary_markdown as r; open('docs/METRIC-DICTIONARY.md','w',encoding='utf-8').write(r())"
```

## Design system (web UI)

Any change that touches the web UI must follow **`docs/DESIGN-SYSTEM.md`** (the Mission Ops
rulebook, ADR-0195): color/type/radius come only from theme tokens (`sf-themes.css` — four
views: console default / daylight / apollo / jarvis; verify in all four), every data visual
honors the chart contract (takeaway headline, labeled axes, legend, DD line, hover callout,
provenance chip, ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE toolbar), and its Definition-of-Done checklist
runs before every UI PR. The redesign integrates in phases — tokens (done) → global chrome →
one page shell per PR → new panels; never big-bang, and never touch `engine/` for a UI change.

## Durable state & the drift guard

- `docs/STATE/HANDOFF.md` — **read first**; the live "where we are / what's next." Since ADR-0246 it
  holds ONLY the current STATUS section plus a single `# (prior) handoffs — archived` pointer, and the
  SessionStart hook (`.claude/hooks/session_start.sh`) **auto-injects that section into every session**
  (startup + resume) so it is always read without relying on a manual `Read`. **Writing the next
  handoff MOVES the current section to the TOP of `HANDOFF-ARCHIVE.md`** (demote its `# Handoff` →
  `# (prior) Handoff`) **and REPLACES the section in `HANDOFF.md`** — never stack a new `# (prior)`
  section in `HANDOFF.md`, or the size guard fails.
- `docs/STATE/HANDOFF-ARCHIVE.md` — the older handoff sections (newest-first, verbatim), moved out so
  the live handoff stays small enough to read in full in one pass.
- `docs/STATE/SESSION-LOG.md` — append-only per-session history (the full running log; the archive is
  handoff snapshots).
- `docs/STATE/LESSONS-LEARNED.md` — the **living lessons-learned log** (what we've done, what we tried,
  what didn't work, and the forward-looking "how would we build this better" analysis). **STANDING RULE
  (operator directive 2026-07-19): UPDATE THIS LOG DAILY** — every session that changes the codebase,
  and at least once per working day of active work, appends a dated entry to its Part VIII at the
  moment a lesson is learned (a bug that fought back, a reverted fix, a dead end, a parity/packaging/
  deploy surprise, a decision that paid off or backfired). Do not batch it for the end. When a lesson
  generalizes, promote it into the relevant themed section (Parts IV–VI). This log is a first-class
  durable-state doc alongside HANDOFF/SESSION-LOG — treat keeping it current as part of the
  end-of-session ritual.
- `docs/adr/NNNN-*.md` — one ADR per significant decision.
- `tests/test_state_docs.py` **fails** unless the highest ADR number on disk appears in BOTH `HANDOFF.md`
  and `SESSION-LOG.md` (so any change that adds an ADR must refresh both docs in the same commit) **and**
  unless `HANDOFF.md` stays ≤64 KB with exactly one `# (prior)` heading (so it can never grow back past
  one-pass readability).

## Workflow

- Branch from `main`, open a **draft PR**, get CI green, squash-merge. Squash-merges make stacked
  branches conflict, so branch fresh from `main` and merge-resolve rather than stacking.
- **Always `git fetch origin` before you branch or rebase** (best practice, all sessions). The local
  `main` goes stale between sessions; `git fetch origin` updates the remote-tracking refs *without*
  touching your working branches, so you branch/rebase onto the real latest `origin/main`
  (e.g. `git fetch origin && git switch -c <branch> origin/main`) instead of a stale local copy.
- **After a squash-merge, restart the branch with `--prune`.** GitHub auto-deletes the merged head
  branch, so the local remote-tracking ref goes stale — the stop hook then compares against it and
  mis-reports GitHub's own squash commit (committer `noreply@github.com`, i.e. `origin/main`'s tip)
  as an "unverified unpushed commit". Run
  `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
  **Never** amend/rebase that squash commit to satisfy the hook — it is published `origin/main`
  history; rewriting it forks the branch from main and breaks the CUI guard's
  `inherited_from_main` rule.
- The `qc-checker` subagent (`.claude/agents/`) runs the full gate, triages real errors vs
  environment-gated skips / flakes, and fixes them — on demand or via a throttled SessionStart trigger.
