# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

> **This file went EIGHT SLICES stale** (last refreshed 2026-08-09 at slice 14 / v1.0.186 /
> ADR-0378; slices 15–21 all skipped it). The 2026-08-11 (b) session was handed that text and
> told to "resume at slice 15" — work finished five slices earlier. Only the auto-injected
> handoff caught it. Refreshing this file is part of session close, not an optional tidy.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.194, highest ADR
0387, SCHEMA 2.11.0** — the 2026-08-11 (b) session closed phase-4 slice 22 (ADR-0387): THREE
page families out in one slice — `web/brief.py` (86 lines: `_BRIEF_XLSX_TITLE`, `_brief_body`) ·
`web/card.py` (184: `_count_bar_table`, `_card_body`) · `web/scorecards.py` (204:
`_parse_committed_date`, `_sc_status_class`, `_scorecard_export_table`, `_scorecard_panel`,
`_scorecards_body`) — **plus ONE descent**, `_sources_line` → `components.py`. app.py
**9,936 → 9,593** wc-truth (17,197 when phase 3 began). All seven CI checks GREEN on PR #572.

THE FINDING to carry: **the render probe could not have reported anything but zero.** It scored
`_brief_body` oracle-dark; `_brief_body` is not dark. The harness diffed `manifest.json`'s
VALUES, and `oracle_corpus._iter_out` names each body file `sha256(LABEL)[:16].bin` — derived
from the LABEL, not the content — so the compared value is constant across every run of every
tree. It could not have reported a difference for ANY member, and said "0 moved" in the voice of
a measurement. Fixed: compare **body bytes**, and a **positive control runs FIRST and ABORTS on
zero**, plus a second independent check that the marker TEXT reached a rendered body. **An
instrument is not evidence until it has been shown to fail** — and one whose failure mode is
SILENCE cannot be sanity-checked by reading its output, because its broken output and its most
interesting finding are the same string.

⇢ WHAT'S DONE — do NOT re-open. Monolith split phases 1–2 (state.py, chrome.py) + phase 3/4
slices 1–22: components · driving · evolution · integrity · margin · trend · ssi · mission · sra ·
forecast · portfolio · analysis · evm · performance · resources · scurve · path · compare · risks ·
standards · wbs (ADR-0386) · **brief + card + scorecards (ADR-0387)**. The question-word censuses
are RETIRED. Intake manifest CURRENT at 433 files / 99 mismatches; .mpp census pin 28. The
2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369). Target-UID pair scope CLOSED
(ADR-0370/0371). FX fixture verdicts FINAL.

⇢ DO THIS FIRST — the queue

**Phase 4 slice 23. The zero-descent set is EXHAUSTED** — all eight remaining families outside
`groups` carry descents. By size: `briefing` (4 movers / 194 / **3** descents — `_ollama_or_none`,
`_openai_or_none`, `_active_backend`, shared with `_ai_status_note` / `_settings_body` /
`_polished_narrative` / `_translate_batch`), then `settings` (318) and `cei` (262), which also
carry real ones. **Re-price EVERY family by referrer walk before cutting — ADR-0383's table has
now been wrong about `briefing` once** (it says 4 descents; two independent walks find 3).
`groups` (430) stays OUTSIDE the list while ADR-0343 feature work is queued against it.

Recipe per slice (ADR-0365 + ADR-0372 + ADR-0387): closure before cut · span-scoped probe with a
POSITIVE CONTROL that aborts · the six-mutation battery · the committed oracle. **Import the
oracle, don't rebuild it:** `python tests/web/oracle_corpus.py --out <dir>` with
`PYTHONPATH=<tree>/src SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and
the cut tree, then **`diff -r` on the DIRECTORIES** (a manifest diff is the wrong surface —
filenames are label-addressed). Corpus is now **652** labels: `[empty]` 60
`{200:41,400:17,422:2}` + four loaded stages of 148 `{200:125,404:4,422:19}`. Export fmts are
xlsx and docx, NOT csv; `{name}` keys drop the `.xml`; target UID 22; keep the `[grouped]` labels;
`/openapi.json` is the 60th parameterless GET.

Then the standing queue: **`mpxj_ref()` shallow-clone hardening** (it pins the nine installers to
`git log -1 -- tools/mpxj`, which in a `--depth 1` clone returns the CLONE BOUNDARY — always
`git fetch --unshallow` before building, or the pin drifts; correct value is `42d92dc`) ·
stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages
(/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
constraints · P80/P90 recurring-exception residual · the doc-drift sweep (CLAUDE.md's phase-3 +
E501 lines lag — `brief.py`, `card.py`, `scorecards.py` join `wbs.py` on the unpatched list;
docs/PARITY-REPORT.md still calls the reference .mpps git-ignored; docs/FINAL-REPORT.md's blanket
"Exact match") · ~150 MB RSS retained per loaded 9 MB file · Phase 6 docs.

**Operator only:** re-convert FX-03/FX-04 (open the authored .xml, VERIFY UID17=5d / UID131=1w
before save — MS Project re-derives Duration from stored dates and silently un-edits; the finish
MUST move) then re-run Fuse and replace the two oracles · one Acumen run on a crafted
sub-day-negative-float schedule (closes the Negative-Float O1 gap — the AFT has NO formula) ·
license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.

⇢ TIMING — MEASURED, not estimated (the old "~30 min" here was wrong by 2×)

Full LOCAL suite **~21 min** (`python -u -m pytest -q` in the BACKGROUND, read the tail; ~28 with
playwright installed). **CI end-to-end is ~60 MINUTES**, measured across four consecutive runs
(57.5 / 60.7 / 61.8 / 62.5). The `test (3.11)` and `test (3.13)` jobs alone take **~61 min** —
they run coverage-instrumented pytest PLUS ruff, mypy, a SECOND pytest for the parity gate,
bandit and pip-audit; `floor` runs the same suite WITHOUT coverage in 22 min, which is why the
gap is structural, not a hang. `check` is a gate job (`needs: [test, floor]`) and only registers
after those finish — its absence early in a run is sequencing, NOT a failure. CI has
`cancel-in-progress: true`, so **never push while a run you need the signal from is in flight**.

⇢ THE TRAPS PAID FOR — check BY NAME

An instrument is not evidence until it has been shown to FAIL (ADR-0387). A positive control that
ABORTS beats one that prints; a control that only prints gets read past.
Check what a name is DERIVED from before diffing it (ADR-0387) — a 16-hex filename looks
content-addressed; `oracle_corpus`'s is LABEL-addressed.
A descent is forced by a MOVER, not by sharing (ADR-0387): route-only referrers never block, but
a mover calling a shared name means the name must live BELOW, or go there.
An export's relationship to its page is PER-FAMILY and must be measured (ADR-0387) — three
families in one slice gave three different answers.
Extending the oracle is part of the method (ADR-0374/0379/0387) when a member is dark for want of
a render CONDITION, not for want of reachability.
A shared doc-comment is not a movable unit (ADR-0387) — splitting it beat leaving a false
sentence behind.
A plausible module name is not a measurement (ADR-0387) — this slice's ADR first named a
`reports/brief_tables.py` that does not exist.
The monkeypatch sweep's population is the names a module BINDS, not the ones it MOVES (ADR-0387).
And a spy that asserts ZERO cannot be checked by running it — force the non-zero case.
A sweep's POPULATION is part of its claim (ADR-0386): exclude build/dist/.venv/caches and STATE
the file count. `build/` is a stale copy of `src/` left by `python -m build`.
A prefix that is a prefix OF ANOTHER FAMILY fuses two censuses (ADR-0386) — seed on EXACT route
lists (`brief` vs `briefing`).
A probe's marker must match the RETURN TYPE (ADR-0386); a census can be exact and still not be
membership (ADR-0378); sweep by BARE NAME, never a module-qualified regex (ADR-0378).
A parallel session can take your ADR number (ADR-0386) — `git fetch origin` before you write the
number AND again before you commit.
`ast` col_offset is a BYTE offset — splice on bytes, re-parse before writing (ADR-0384).
Never MEASURE a tree a battery is mutating (ADR-0376); restore from a scratchpad cp, never
`git checkout`; md5-verify the restore.
A mutation is "caught" only when the failure summary NAMES the test (pytest exit ≠ failing test).
A normalizer that can fail silently is a FLAP FACTORY (ADR-0377); fingerprints carry their SCOPE.
An anchor that collides is not span-scoped (ADR-0377): assert count == 1 IN FILE and the anchor
line INSIDE the member's ast span, before every probe.
Constants carry `#:` doc-comment blocks the ast span does NOT see — extend regions by eye.
A scratchpad-resident harness must HARDCODE the repo root — a walk-up loops silently at `/`.
`python -m pytest` prepends CWD to `sys.path`; bare `pytest` does NOT (CI runs the bare form).
Two ruffs live on PATH — run `python -m ruff`, and always `ruff check .` (THE WHOLE TREE).
An environment defect can masquerade as a product defect — a pristine-main worktree is the cheap
decisive adjudicator.
`grep -c` exits 1 on zero; an EMPTY sweep is evidence only with a positive-control self-test.
round() sends exact halves to EVEN (240 min → 0 wd); MSPDI import DERIVES Duration from stored
dates — diff every round-trip. bandit B608 on HTML f-strings with "from" → house `# nosec B608`.
`_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form.

⇢ Measured-false / load-sensitive, do NOT re-chase

Baseline-PRESENCE as the parity population (F5) — the AFT's filter is `Baseline Duration
GreaterThan 0`, verbatim. The /analysis focus→tip family is load-sensitive. FIVE playwright-only
failures are PRE-EXISTING and CI-invisible (blob-URL download reporting on /trend /curves /scurve
/cei; SRA single-bin histogram caption contrast) — pristine-main adjudicated 2026-08-08.
`pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2
floor). TP4/goldens cannot render a driving corridor (ADR-0351), /evolution's counterfactual
(ADR-0352), or /integrity's artifact-cluster (ADR-0358) — byte-identity is the guard there. The
period-over-period families match UIDs across versions on the FOCUSED scope BY DESIGN (ADR-0371,
parity-oracled). ADR-0373's three oracle-dark SRA members are route-covered in Python — the MSPDI
fixture is the named gap, not a regression.

⇢ Standing rules (binding)

Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING,
VERIFY EVERYTHING · ADR-0240 model protocol (parity-, engine-, testimony- or CUI-relevant work
stays on the strongest model) · full gate before every commit · handoff rotation + SESSION-LOG +
LESSONS-LEARNED **+ THIS FILE** in the same commit · wheel + nine installers ONCE per shipped-code
change (bump BEFORE the suite; REBUILD if code changes after; the rebuild PRECEDES the final
suite run) · a number written mid-session is not a measurement (wc decides). Use the skills
(`.claude/skills/`): full-gate, prove-able-to-fail, metric-parity, ui-change, cui-guard,
render-verify, session-close.
