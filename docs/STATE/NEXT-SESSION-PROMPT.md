# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a **pointer, not a status
snapshot** — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. Refresh this file whenever the queue changes — a stale kickoff
steers a fresh session at work that is already done.)

> It once went EIGHT SLICES stale (slice 14 → 22) and handed a session work finished five slices
> earlier; only the auto-injected handoff caught it. It carries no drift guard, unlike `HANDOFF.md`
> — which is exactly why it rots. Refreshing it is part of session close, not an optional tidy.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.196, highest ADR 0389,
SCHEMA 2.11.0** — the 2026-08-12 (b) session closed phase-4 slice 24 (ADR-0389): FOUR page families
out with ZERO descents — `web/curves.py` (155 lines) · `web/ribbon.py` (300) · `web/workbench.py`
(94) · `web/volatility.py` (217) — plus a SEVENTH oracle stage. `app.py` 9,125 → **8,482** wc-truth
(17,197 when phase 3 began).

**THE ZERO-DESCENT SET IS NOW ACTUALLY EMPTY.** Outside `groups` (fenced, ADR-0343), **`settings`
is the only page family left in `app.py`.**

**THE FINDING to carry:** `settings`' three "descents" are **CANDIDATES, and none is FORCED.**
ADR-0351's rule permits TWO remedies — descend into `components.py`, or **move into the family
module**, since `app.py` is the top layer and reaches anything through the `X as X` re-export.
Only a referrer in **another EXTRACTED module** forces the first. All three blockers live in
`app.py` itself; an AST scan over all 28 extracted view modules finds ZERO references to them
(positive control `_e`: 26 modules). A rule you have written down is not a rule you have applied —
and a count that reads as a verdict gets spent as one.

## ⇢ WHAT'S DONE — do NOT re-open

Monolith split phases 1–2 (`state.py`, `chrome.py`) + phase 3/4 slices 1–24: components · driving ·
evolution · integrity · margin · trend · ssi · mission · sra · forecast · portfolio · analysis · evm
· performance · resources · scurve · path · compare · risks · standards · wbs · brief + card +
scorecards (ADR-0387) · briefing + cei (ADR-0388) · **curves + ribbon + workbench + volatility
(ADR-0389)**. The question-word censuses are RETIRED. Intake manifest CURRENT at 433 files / 99
mismatches; `.mpp` census pin 28. The 2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369).
Target-UID pair scope CLOSED (ADR-0370/0371). FX fixture verdicts FINAL.

## ⇢ DO THIS FIRST — the queue

**Phase 4 slice 25 — `settings` (7 movers / 347 ast lines), the LAST page family outside the fenced
`groups`.** Re-price by referrer walk anyway (the table is a snapshot; it happened to hold last
slice, which is only knowable by re-walking). Then **TEST THE FINDING**: measure whether
`_ollama_or_none` / `_openai_or_none` / `_second_backend` can simply move INTO `settings.py` — with
`app.py`'s stayers (`_active_backend` at module level, `_ask_response` nested in `create_app`)
reaching them through the re-export — rather than descending into `components.py`.

**Expect the ADR-0297 monkeypatch trap to be LIVE this time.** `tests/web/test_ai_wiring.py` and
`tests/web/test_coverage_app_extra.py` patch `app_module._ollama_or_none` / `_openai_or_none`, and
`_ai_status_note` (a settings MOVER) resolves them — once both move, the mover reads them from
`settings`' globals and the patches stop reaching it. Repoint in the same commit, and make the
sweep **FORCE the non-zero case** rather than trust a green run.

Recipe per slice (ADR-0365 + 0372 + 0387 + 0388 + 0389): closure before cut · span-scoped probe
with a POSITIVE CONTROL that ABORTS · the mutation battery · the committed oracle. **Import the
oracle, don't rebuild it:** `python tests/web/oracle_corpus.py --out <dir>` with
`PYTHONPATH=<tree>/src SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and
the cut tree, then `diff -r` on the **DIRECTORIES** (a manifest diff is the wrong surface —
filenames are LABEL-addressed). Corpus is now **948 labels**: `[empty]` 60 `{200:41,400:17,422:2}`
+ **SIX** loaded stages of 148 `{200:125,404:4,422:19}`. Export fmts are `xlsx` and `docx`, NOT csv;
`{name}` keys drop the `.xml`; target UID 22; keep the `[grouped]` labels; `/openapi.json` is the
60th parameterless GET. A corpus render is **~36 s** — budget N+2 renders for an N-member probe.

**Environment note** (this container had NOTHING installed): `python -m pip install -e '.[dev]'`
before anything, and `python -m pip install build` before the wheel. It is also a `--depth 1` clone,
so **`git fetch --unshallow` BEFORE building installers** or the MPXJ pin silently becomes the clone
boundary (correct value `42d92dc`).

Then the standing queue: `mpxj_ref()` shallow-clone hardening (still a documented workaround, not a
guard) · stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages
(`/briefing`, `/path`, `/compare`) · `/groups` Activities (ADR-0343) · installers vs known-good
constraints · P80/P90 recurring-exception residual · the doc-drift sweep (`docs/PARITY-REPORT.md`
still calls the reference .mpps git-ignored; `docs/FINAL-REPORT.md`'s blanket "Exact match";
**`LESSONS-LEARNED` Part VIII's 2026-08-10(e) entry is still at the BOTTOM of the file instead of
newest-first** — the 2026-08-12 one was lifted in ADR-0389) · ~150 MB RSS retained per loaded 9 MB
file · Phase 6 docs.

**Operator only:** re-convert FX-03/FX-04 (open the authored `.xml`, VERIFY UID17=5d / UID131=1w
before save — MS Project re-derives Duration from stored dates and silently un-edits; the finish
MUST move) then re-run Fuse and replace the two oracles · one Acumen run on a crafted
sub-day-negative-float schedule (closes the Negative-Float O1 gap — the AFT has NO formula) ·
license · branch-protection contexts · proprietary reruns · OR-04 · July `mpp/` re-export decision.

## ⇢ TIMING — MEASURED, not estimated

Full LOCAL suite ~21 min (`python -u -m pytest -q` in the BACKGROUND, read the tail; ~28 with
playwright installed). CI end-to-end is **~60 MINUTES**, measured across four consecutive runs
(57.5 / 60.7 / 61.8 / 62.5). The `test (3.11)` and `test (3.13)` jobs alone take ~61 min — they run
coverage-instrumented pytest PLUS ruff, mypy, a SECOND pytest for the parity gate, bandit and
pip-audit; `floor` runs the same suite WITHOUT coverage in 22 min, which is why the gap is
structural, not a hang. `check` is a gate job (`needs: [test, floor]`) and only registers after
those finish — its absence early in a run is sequencing, NOT a failure. CI has
`cancel-in-progress: true`, so never push while a run you need the signal from is in flight.

## ⇢ THE TRAPS PAID FOR — check BY NAME

A **rule you have written down is not a rule you have applied** (ADR-0389) — ADR-0351's descent rule
permits two remedies and three ADRs used only one; label a column for what it HOLDS, because a count
that reads as a verdict gets spent as one. When a member is **dark**, ask what the corpus has NEVER
rendered, not what the member needs (ADR-0389: the answer was a whole CLASS of input — a
fully-progressed as-built). An oracle stage can be a **byte transform of an existing fixture**, and
it must **assert its own landed count** (ADR-0389). Choosing a mutation's **ANCHOR is part of the
mutation** (ADR-0389): a colliding anchor is not span-scoped, and a unique anchor some test asserts
scores for the WRONG reason. A **zero-asserting spy** is only adjudicated by FORCING the non-zero
case (ADR-0386, fired again in 0389). A priced table is a SNAPSHOT and decays silently (ADR-0388) —
re-walk, and make the walk reproduce something KNOWN before believing it about something unknown; a
re-walk that reproduces is still worth running. A control that names an expected VALUE beats one
that names a direction (ADR-0388): "zero members" and "no seed routes" both print as small, clean,
wrong answers. An instrument is not evidence until it has been shown to FAIL (ADR-0387); a positive
control that ABORTS beats one that prints. A probe's marker must match the RETURN TYPE (ADR-0386).
Check what a name is DERIVED from before diffing it (ADR-0387) — oracle_corpus's filenames are
LABEL-addressed. A descent is forced by a MOVER, not by sharing, and a route-only referrer NEVER
blocks (ADR-0378/0387/0388). An export's relationship to its page is PER-FAMILY and must be measured.
The monkeypatch sweep's population is the names a module BINDS, not the ones it MOVES (ADR-0387) —
and watch for BASENAME collisions (`ai/briefing.py` vs `web/briefing.py`). A sweep's POPULATION is
part of its claim (ADR-0386): exclude `build/dist/.venv/caches` and STATE the file count (now **517**).
`build/` is a stale copy of `src/`. A prefix that is a prefix OF ANOTHER FAMILY fuses two censuses
(ADR-0386) — seed on EXACT route lists (`brief` vs `briefing`), and check the real route path
(`/card/{name}`, not `/card`). A parallel session can take your ADR number (ADR-0386) — `git fetch
origin` before you write the number AND again before you commit. `ast` col_offset is a BYTE offset —
splice on bytes, re-parse before writing (ADR-0384); prefer whole-line regions. Never MEASURE a tree
a battery is mutating (ADR-0376); restore from a scratchpad `cp`, never `git checkout`; md5-verify
the restore, and re-render the corpus AFTER the battery. A mutation is "caught" only when the failure
summary NAMES the test (pytest exit ≠ failing test). A normalizer that can fail silently is a FLAP
FACTORY (ADR-0377); fingerprints carry their SCOPE. An anchor that collides is not span-scoped
(ADR-0377): assert `count == 1` IN FILE before every splice. Constants carry `#:` doc-comment blocks
the `ast` span does NOT see — extend regions by eye. A scratchpad-resident harness must HARDCODE the
repo root. `python -m pytest` prepends CWD to `sys.path`; bare `pytest` does NOT (CI runs the bare
form). Two ruffs live on PATH — run `python -m ruff`, and always `ruff check .` (THE WHOLE TREE). An
environment defect can masquerade as a product defect — a pristine-main worktree is the cheap
decisive adjudicator. `grep -c` exits 1 on zero. `round()` sends exact halves to EVEN (240 min → 0
wd); MSPDI import DERIVES Duration from stored dates. bandit B608 on HTML f-strings with "from" →
house `# nosec B608`. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus.
`strip_title=True` or a multi-file pool becomes one-version Projects and every multi-version page
serves its placeholder (ADR-0375).

## ⇢ Measured-false / load-sensitive, do NOT re-chase

Baseline-PRESENCE as the parity population (F5) — the AFT's filter is `Baseline Duration GreaterThan
0`, verbatim. The `/analysis` focus→tip family is load-sensitive. FIVE playwright-only failures are
PRE-EXISTING and CI-invisible (blob-URL download reporting on `/trend` `/curves` `/scurve` `/cei`;
SRA single-bin histogram caption contrast) — pristine-main adjudicated 2026-08-08. `pydantic>=2` is
NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens
cannot render a driving corridor (ADR-0351), `/evolution`'s counterfactual (ADR-0352), or
`/integrity`'s artifact-cluster (ADR-0358) — byte-identity is the guard there. The
period-over-period families match UIDs across versions on the FOCUSED scope BY DESIGN (ADR-0371,
parity-oracled). ADR-0373's three oracle-dark SRA members are route-covered in Python — the MSPDI
fixture is the named gap, not a regression.

## ⇢ Standing rules (binding)

Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING,
VERIFY EVERYTHING · ADR-0240 model protocol (parity-, engine-, testimony- or CUI-relevant work stays
on the strongest model) · full gate before every commit · handoff rotation + SESSION-LOG +
LESSONS-LEARNED + THIS FILE in the same commit · wheel + nine installers ONCE per shipped-code change
(bump BEFORE the suite; REBUILD if code changes after; the rebuild PRECEDES the final suite run) · a
number written mid-session is not a measurement (`wc` decides). Use the skills (`.claude/skills/`):
`full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`,
`session-close`.
