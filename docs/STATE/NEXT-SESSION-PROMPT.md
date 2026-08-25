# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS² (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue.
As of last close: v1.0.221 · highest ADR 0439 · SCHEMA 2.11.0 · main = dfa09ac (the #610 squash).
IN FLIGHT: only the 2026-08-25 audit PR from `claude/polaris-resume-audit-ndwcc5` (ADR-0439,
tests+docs only, no version bump) — check whether it merged before you branch. git fetch origin
before you branch, number an ADR, or commit — and RE-fetch before writing the docs (a prior
session had main move UNDER the branch at close and had to redo the whole state-doc rotation).

⇢ WHAT'S DONE — do not re-open. 2026-08-25 (ADR-0439, v1.0.221 unchanged): PAGE MODULES got their
first-ever audit — operator file content is DATA, not markup. Verdict CLEAN and MEASURED: 81 scored
server responses · 33 rendered pages in real Chromium · 44 export archives under an XML-hostile
name, zero leaks; the vendored JS is structurally immune (createElement + textContent) and the
seven non-clearing innerHTML sinks are literals, esc()'d text, or server-built HTML. Two standing
censuses now hold it (tests/web/test_operator_content_escaping.py +
test_operator_content_dom_browser.py, the latter auto-discovered by tools/browser_modules.py).
MF-02 was found STALE IN THE LEDGER — it shipped as ADR-0411 — and is corrected; the
`value is not None` class it asked about is closed (3 AST sites, all correct). Before that:
2026-08-21 multi-folder drop + /driving-path whole-schedule (ADR-0437/0438, v1.0.221), the POLARIS²
rename (ADR-0436), and the 2026-08-20 four asks (ADR-0431..0435) — all merged and verified.

⇢ OPERATOR FOLLOW-THROUGH (ask, don't assume): has the JUICE UVS .xer update set been re-loaded on
v1.0.220+? The Mission Control wall should light; if the per-update exports rename the project NAME
too, Portfolio → Combine Projects is the remedy. Check any render report against the BUILD it came
from (the v1.0.148 lesson, ADR-0435).

⇢ RESUME ORDER — start at 1.

1. DOCS/CONFIG/CI — the LAST never-audited dimension. 2026-08-25 gave it only a PARTIAL pass:
   CLAUDE.md's documented gate was verified against .github/workflows/ci.yml and [tool.mypy]
   (they agree; bare `mypy` == `mypy src/` strict via files=["src"]), and two stale pyproject
   comments were fixed. UNTOUCHED: .githooks, installer-smoke.yml, constraints/, the docs guards
   themselves, .gitattributes/.gitignore, the SessionStart hook. Page modules A/B is now DONE for
   the escaping/fabricated-zero/export-integrity classes — other page-module classes remain fair
   game but the dimension is no longer a zero.
2. The AI figure-gates ADVERSARIAL pass — `ai/qa.py::_figure_roles`, `_classify_figures`
   (`handled` added on the first non-value occurrence), `_MAX_GATED_FIGURES = 24`,
   `ai/derivation.py` Layer B. Fold in the f.text-never-f.rendered() finding (Ask prompt assembly,
   ai/qa.py ~910/931/942). Annotate-mode gap: gate scores against `model_evidence` while the
   analyst sees `relevant_facts`.
3. The 25-route adverse gap (19 are `POST /sra/*`; `/sra/factor-table` never touched at all).
   Report coverage as the bracket 25 <= gap <= 66.
4. Remaining REPORTED ledger rows: CPM-01..04 · MF-03/04/06..10 · MC-02..08 · IMP-02..06 ·
   MAN-01..03 · REC-02 · JS-02..06 · TST-02/03. (MF-02 REMOVED — it was stale, see above.)
5. Smaller carried-forward items: sibling degrade notes (/trend /cei /evolution /volatility
   /integrity) could gain ADR-0431's other-projects tail · consider a browser assertion for the
   Utilization panel rows (currently server+probe-verified) · ADR-0424's leftover:
   `engine/pair_series.py` + `ai/pair_facts.py` never audited.

⇢ DO-NOT-FIX-BLIND LIST. MF-05 (empty-population PASS may be correct Acumen parity) · MC-01's
parity leg UNVERIFIED by design (ADR-0414) · ADR-0417 needs a non-degenerate SRA fixture ·
ADR-0419's MinutesPerDay leg needs an operator file · `citations.reattach` drops `pinned` —
measured unreachable; fix only if made reachable. NEW 2026-08-25: the SIX dead E501
per-file-ignores (scurve, standards, brief, briefing, curves, workbench) — provably dead by two
oracles, but the stated policy attaches the exemption to what a module IS, so removing them fights
the intent and breaks the next HTML edit · `evolution.py`'s completed-on-path table renders `0%`
for an absent activity beside a cell that correctly renders `—` — measured UNREACHABLE, latent.

⇢ MEASURED-FALSE / BLOCKED — do NOT re-chase. Insufficient Detail V05/V06 and TP2's 6-vs-7: six
hypotheses measured and refuted (ADR-0430); blocked on ONE operator artifact — the named activities
behind Fuse's "Insufficient Detail — 5" cell (click it in the Fuse Starlight workbook or export the
ribbon to Excel), then re-upload. The /path timescale screenshot: NOT reproducible on ≥ v1.0.219;
property-guarded in chromium.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME. New last session: a census that HAND-WRITES its
population will always find it clean — `/analysis` and `/wbs` are `/{name}` routes, so a hand-listed
page sweep 404'd on them and scored the 404s as ESCAPED, while skipping every parameterized route
(enumerate from the app object; NEVER score a non-success response) · a positive control can be
wrong about WHERE the defect lands: `</td></tr>` assigned to a `<td>`'s own innerHTML is discarded
by the parser, so that symptom only exists when a whole table STRING goes into a container · a
population FLOOR placed before the substantive assertion reports the wrong cause (a corruption
shrank the population and the guard cried "enumerator broken") — substantive assertion first · a
work QUEUE is data and goes stale unless something asserts it (MF-02 sat "unfixed" for a week after
ADR-0411 shipped it). Prior: never revert a mutation with `git checkout <file>` while the file
carries uncommitted feature work — mutate/restore through a scratch `.bak` copy, always · this
remote container's clone is SHALLOW — `git fetch --unshallow origin` before an installer build · a
new always-on panel flips an absence census · key-valued options with a label-accepting resolver
(_find_schedule) widens a picker without breaking bookmarks · a screenshot is testimony about a
VERSION · an "identity" must survive the workflow that produces the files · seat scrolls from LIVE
geometry · a new sentinel sweeps the existing pins · contract growth is a NAMED re-baseline · a
div-list chart must not wear `.chart-host` · ruff B008 rejects `Form([])` AND
`Form(default_factory=…)`; `Form(())` passes · a first-run green is a twin or a vacuum. Standing: a
bounded sweep looks exhaustive and is not · a fix can be wrong in the direction you did not test ·
the product is often its own oracle · a refuted hypothesis is a result · a count may be counting the
SYMPTOM · an oracle giving the same verdict in both worlds is BLIND · a red for the WRONG REASON is
not a red · monkeypatch per CALL SITE · never measure a tree a battery is mutating · use
`python -m ruff` · `ruff format` also formats python inside MARKDOWN — re-run the WHOLE gate after
the LAST file change · `| tail` masks exit codes · fetch before numbering AND committing · wc decides.

⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` +
`pip install build playwright` first (~2 min total). Full suite ~27-32 min; `pytest -m parity`
~9 min; browser census `pytest $(python tools/browser_modules.py)` ~7-9 min (the new DOM census
adds ~1 min). CI budget ~75 min for a full verdict; `cancel-in-progress: true` — never push while
you need a run's signal. Installer build needs an UNSHALLOW clone (`git fetch --unshallow origin`);
`python -m build --wheel --outdir dist/wheel && python tools/installer/build_installers.py` ~2 min,
rewrites all nine.

⇢ OPERATOR-OWNED, not agent work: the Fuse Insufficient-Detail artifact (above) · V-1/V-2/V-3
gateway verification · DISC-01 · the CEI/HMI vendor export blocking PO-04/05 · an SSI export showing
a fired negative-impact register entry (ADR-0414) · an MSPDI DayWorking=1-no-times file (ADR-0419) ·
branch cleanup · re-loading the JUICE set on the current build.

⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
QC-1 / QC-2 (CLAUDE.md; ADR-0393, pinned by tests/test_standing_rules.py) · ADR-0240 model protocol
(the LEAD re-verifies every finding) · full gate before every commit · handoff + SESSION-LOG +
LESSONS-LEARNED + kickoff in the same commit · wheel + nine installers ONCE per shipped-code change
(ADR-0148) — check `git status src/` before assuming you owe one. Skills: full-gate,
prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change, session-close.
