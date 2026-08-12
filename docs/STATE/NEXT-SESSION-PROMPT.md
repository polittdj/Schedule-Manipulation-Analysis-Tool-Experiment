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
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.197, highest ADR 0390,
SCHEMA 2.11.0** — the 2026-08-12 (c) session closed phase-4 slice 25 (ADR-0390): the **`settings`
family**, the LAST page family, out into `web/settings.py` (525 lines) — **TWELVE names / 437 ast
lines, ZERO forced descents**. `app.py` **8,482 → 8,037** wc-truth (17,197 when phase 3 began).

**OUTSIDE THE FENCED `groups`, `app.py` NO LONGER HOLDS A PAGE FAMILY.** Phase 4's page-family work
is DONE. There is no "slice 26" of the same shape — the next monolith work is a different decision,
described below.

⇢ THE FINDINGS to carry
1. **A closure is not closed until it stops growing.** The record priced `settings` at 7 movers /
   347 ast lines / **3** descent candidates. The 7 and the 347 reproduce EXACTLY (measured twice —
   ast, and independently by awk). The candidate count was **5**: `_settings_body` → `_second_backend`
   → `_BACKEND_PROBE_TTL` + `_UseMarking`, both shared with the stayer `_active_backend` in the
   IDENTICAL shape the record used to flag the other three. The closure had been taken to a fixed
   point of the MOVERS, not the BLOCKERS. Iterate until it stops growing; say which hop each member
   arrived on.
2. **The ADR-0297 monkeypatch repoint is keyed on the CALLER, not the name.** 21 hits → **14
   repointed, 7 deliberately left alone**; `_ollama_or_none` and `_second_backend` each appear on
   BOTH sides. Three of the fourteen would have passed SILENTLY, adjudicated only by FORCING the
   non-zero case (app-globals 0× / settings-globals 1×, with the mirror control 1× / 0× on the same
   name).
3. **A sweep's PATTERN is part of its claim, like its population.** The first sweep anchored on
   `monkeypatch.setattr`; `test_coverage_app.py` binds `mp = monkeypatch`, hiding FOUR sites. Nothing
   in the sweep could reveal that — the **mutation battery's pre-mutation GREEN control** did, going
   red before any mutation was applied. Never skip that control.
4. **Verbatim text is not always verbatim behaviour.** `_UseMarking` logs via
   `logging.getLogger(__name__)`; the bytes move unchanged but the logger name follows the module.
   Grep moved bytes for `__name__` / `__file__` / `__module__` / `globals()` / `sys.modules`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split phases 1–2 (`state.py`, `chrome.py`) + phase 3/4 slices 1–25: components · driving ·
evolution · integrity · margin · trend · ssi · mission · sra · forecast · portfolio · analysis · evm
· performance · resources · scurve · path · compare · risks · standards · wbs · brief + card +
scorecards · briefing + cei · curves + ribbon + workbench + volatility · **settings (ADR-0390)**.
The question-word censuses are RETIRED. Intake manifest CURRENT at 433 files / 99 mismatches; `.mpp`
census pin 28. The 2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369). Target-UID pair scope
CLOSED (ADR-0370/0371). FX fixture verdicts FINAL.

⇢ DO THIS FIRST — the queue
The page-family queue is EMPTY. Two follow-ups slice 25 deliberately DECLINED rather than did, both
now first in line:
1. **`web/backends.py`** — promote the five-name AI-backend kernel (`_ollama_or_none`,
   `_openai_or_none`, `_second_backend`, `_UseMarking`, `_BACKEND_PROBE_TTL`) out of the `settings`
   PAGE module into its own module. Layer-legal and more cohesive; it was declined only because
   conflating a kernel extraction with the last page-family cut would have made neither reviewable.
   Note this MOVES the monkeypatch targets again — re-run the receiver-agnostic sweep and expect the
   14 repointed sites to need a second look.
2. **`_active_backend`** — route-reached only, so moving it is PERMITTED, but measured and declined:
   it would take four more names out of `app.py`'s globals and thereby WIDEN the monkeypatch trap
   across the seven call sites that currently still work. If it moves, those seven move with it.
Then the standing queue: `mpxj_ref()` shallow-clone hardening (still a documented workaround, not a
guard) · stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages
(`/briefing`, `/path`, `/compare`) · `/groups` Activities (ADR-0343) · installers vs known-good
constraints · P80/P90 recurring-exception residual · the doc-drift sweep (`docs/PARITY-REPORT.md`
still calls the reference .mpps git-ignored; `docs/FINAL-REPORT.md`'s blanket "Exact match";
`LESSONS-LEARNED` Part VIII's 2026-08-10(e) entry is still at the BOTTOM of the file instead of
newest-first) · ~150 MB RSS retained per loaded 9 MB file · Phase 6 docs.
Operator only: re-convert FX-03/FX-04 (open the authored `.xml`, VERIFY UID17=5d / UID131=1w before
save — MS Project re-derives Duration from stored dates and silently un-edits; the finish MUST move)
then re-run Fuse and replace the two oracles · one Acumen run on a crafted sub-day-negative-float
schedule (closes the Negative-Float O1 gap — the AFT has NO formula) · license · branch-protection
contexts · proprietary reruns · OR-04 · July `mpp/` re-export decision.

⇢ THE ORACLE — now EIGHT stages, 1096 labels
Import it, don't rebuild it: `python tests/web/oracle_corpus.py --out <dir>` with
`PYTHONPATH=<tree>/src SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and the
cut tree, then `diff -r` on the DIRECTORIES (filenames are LABEL-addressed, so a manifest diff is the
wrong surface). Fingerprint: `[empty]` 60 `{200:41,400:17,422:2}` + **SEVEN** loaded stages of 148
`{200:125,404:4,422:19}` = **1096**. The eighth stage is **`[aiconfig]`** (ADR-0390): a non-default
AI configuration — `backend=openai`, `second_backend=ollama`, a launcher stub on `app.state`, and
`OLLAMA_KEEP_ALIVE` set. It runs LAST because it mutates session config, `app.state` AND process
environment; `render()` snapshots/restores `os.environ` around the whole run. Export fmts are `xlsx`
and `docx`, NOT csv; `{name}` keys drop the `.xml`; target UID 22; keep the `[grouped]` labels;
`/openapi.json` is the 60th parameterless GET. A corpus render is ~40 s — budget N+2 renders for an
N-member probe.

Environment note (this container had NOTHING installed): `python -m pip install -e '.[dev]'` before
anything, and `python -m pip install build` before the wheel. It is also a `--depth 1` clone, so
`git fetch --unshallow` BEFORE building installers or the MPXJ pin silently becomes the clone
boundary (correct value `42d92dc`).

⇢ TIMING — MEASURED, not estimated
Full LOCAL suite ~21 min (`python -u -m pytest -q` in the BACKGROUND, read the tail; ~28 with
playwright installed). CI end-to-end is ~60 MINUTES, measured across four consecutive runs (57.5 /
60.7 / 61.8 / 62.5). The `test (3.11)` and `test (3.13)` jobs alone take ~61 min — they run
coverage-instrumented pytest PLUS ruff, mypy, a SECOND pytest for the parity gate, bandit and
pip-audit; `floor` runs the same suite WITHOUT coverage in 22 min, which is why the gap is
structural, not a hang. `check` is a gate job (`needs: [test, floor]`) and only registers after
those finish — its absence early in a run is sequencing, NOT a failure. CI has
`cancel-in-progress: true`, so never push while a run you need the signal from is in flight.

⇢ THE TRAPS PAID FOR — check BY NAME
A closure is not closed until it stops growing (ADR-0390) — fixed-point the BLOCKERS, not the movers.
A sweep's PATTERN is part of its claim, and the battery's pre-mutation GREEN control is what catches
a bad pattern (ADR-0390). The monkeypatch repoint is keyed on the CALLER, not the name, and the two
sets SHARE names (ADR-0390). Verbatim text is not always verbatim behaviour — `__name__` (ADR-0390).
NEVER MUTATE AN INSTRUMENT A MEASUREMENT IS USING (ADR-0390, the mirror of "never MEASURE a tree a
battery is mutating") — editing `oracle_corpus.py` mid-probe changed the label set under a running
probe. Ask what the corpus has NEVER rendered, not what the member needs — TWO consecutive slices
(ADR-0389 an as-built, ADR-0390 a configured AI). PREDICT the control, then run it (ADR-0390: 29 +
7×39 = 302, landed exactly). A control whose SHORTFALL you can explain beats a perfect one
(ADR-0390: `_e` 29/31, the two misses being the two no-HTML modules). A rule you have written down
is not a rule you have applied (ADR-0389). An oracle stage can be a byte transform of an existing
fixture, and it must assert its own landed count (ADR-0389). Choosing a mutation's ANCHOR is part of
the mutation (ADR-0389). A zero-asserting spy is only adjudicated by FORCING the non-zero case
(ADR-0386/0389/0390). A priced table is a SNAPSHOT and decays silently (ADR-0388). An instrument is
not evidence until it has been shown to FAIL (ADR-0387). A probe's marker must match the RETURN TYPE
(ADR-0386). Check what a name is DERIVED from before diffing it (ADR-0387). A descent is forced by a
MOVER in ANOTHER EXTRACTED MODULE, and a route-only referrer NEVER blocks (ADR-0378/0387/0388/0390).
A sweep's POPULATION is part of its claim (ADR-0386) — exclude `build/dist/.venv/caches` and STATE
the count (517 pre-cut, 518 after); `build/` is a stale copy of `src/`. A prefix that is a prefix OF
ANOTHER FAMILY fuses two censuses (ADR-0386) — seed on EXACT route lists. A parallel session can take
your ADR number (ADR-0386) — `git fetch origin` before you write the number AND again before you
commit. `ast` col_offset is a BYTE offset (ADR-0384); prefer whole-line regions. Never MEASURE a tree
a battery is mutating (ADR-0376); restore from a scratchpad `cp`, never `git checkout`; md5-verify
the restore, and re-render the corpus AFTER the battery. A mutation is "caught" only when the failure
summary NAMES the test. A normalizer that can fail silently is a FLAP FACTORY (ADR-0377);
fingerprints carry their SCOPE. An anchor that collides is not span-scoped (ADR-0377): assert
`count == 1` IN FILE before every splice. Constants carry `#:` doc-comment blocks the `ast` span does
NOT see — extend regions by eye (whole-line regions handle this for free). A scratchpad-resident
harness must HARDCODE the repo root. `python -m pytest` prepends CWD to `sys.path`; bare `pytest`
does NOT (CI runs the bare form). Two ruffs live on PATH — run `python -m ruff`, and always
`ruff check .` (THE WHOLE TREE). An environment defect can masquerade as a product defect — a
pristine-main worktree is the cheap decisive adjudicator. `grep -c` exits 1 on zero. `round()` sends
exact halves to EVEN (240 min → 0 wd); MSPDI import DERIVES Duration from stored dates. bandit B608
on HTML f-strings with "from" → house `# nosec B608`. `_parse_uid` maps 0 → "clear", so UID 0 can
never be the focus. `strip_title=True` or a multi-file pool becomes one-version Projects and every
multi-version page serves its placeholder (ADR-0375).

⇢ Measured-false / load-sensitive, do NOT re-chase
Baseline-PRESENCE as the parity population (F5) — the AFT's filter is `Baseline Duration
GreaterThan 0`, verbatim. The `/analysis` focus→tip family is load-sensitive. FIVE playwright-only
failures are PRE-EXISTING and CI-invisible (blob-URL download reporting on `/trend` `/curves`
`/scurve` `/cei`; SRA single-bin histogram caption contrast) — pristine-main adjudicated 2026-08-08.
`pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2 floor).
TP4/goldens cannot render a driving corridor (ADR-0351), `/evolution`'s counterfactual (ADR-0352), or
`/integrity`'s artifact-cluster (ADR-0358) — byte-identity is the guard there. The period-over-period
families match UIDs across versions on the FOCUSED scope BY DESIGN (ADR-0371, parity-oracled).
ADR-0373's three oracle-dark SRA members are route-covered in Python — the MSPDI fixture is the named
gap, not a regression. **`_UseMarking` and `_BACKEND_PROBE_TTL` are oracle-dark BY CONSTRUCTION**
(ADR-0390: a wrapper needing a live local model; a cache TTL that cannot change rendered bytes) —
unit-covered, a named gap, NOT a regression and NOT worth another oracle stage.

⇢ Standing rules (binding)
Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING,
VERIFY EVERYTHING · ADR-0240 model protocol (parity-, engine-, testimony- or CUI-relevant work stays
on the strongest model) · full gate before every commit · handoff rotation + SESSION-LOG +
LESSONS-LEARNED + THIS FILE in the same commit · wheel + nine installers ONCE per shipped-code change
(bump BEFORE the suite; REBUILD if code changes after; the rebuild PRECEDES the final suite run) · a
number written mid-session is not a measurement (`wc` decides). Use the skills (`.claude/skills/`):
`full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`,
`session-close`.
