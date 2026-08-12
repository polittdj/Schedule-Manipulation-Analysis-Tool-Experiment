# Handoff — 2026-08-12 (phase 4 slice 23: /briefing + /cei out, zero descents; ADR-0388; v1.0.195)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase-4-slice-23-1powiz`
> (this container's designated branch). It started AT `main` **85b470f** — #572 had already
> squash-merged, so no restart was needed. **Shipped code changed** — version bumped
> **v1.0.194 → v1.0.195** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0). Highest ADR now **ADR-0388** (re-fetched before numbering
> AND before committing).
>
> **Slice 23: TWO page families → `web/briefing.py` (252 lines) · `web/cei.py` (304), ZERO
> descents.** app.py **9,593 → 9,125** wc-truth (17,197 when phase 3 began). `LAYER_ORDER`
> `… → scorecards → briefing → cei → app`; both join pyproject's E501 list, `EXTRACTED`,
> `LAYER_ORDER`, `VIEW_MODULES` and BOTH whole-view-layer guard tuples.
>
> ## THE FINDING — "the zero-descent set is EXHAUSTED" is measured FALSE
> The queue opened this slice asserting all eight remaining families carry descents, `briefing`
> first at **3**. Re-walked: `briefing` carries **ZERO**, and **six of eight** families do.
> `_ollama_or_none` / `_openai_or_none` belong to **`settings`** (reached from `_ai_status_note`
> and `_settings_body`); `_active_backend` is reached only from the `/api/ai/briefing` **ROUTE**,
> and a route-only referrer never forces a descent (ADR-0378, restated by ADR-0387 — applied here
> to the family whose price it had been inflating for three ADRs). Even `settings`' real trio is
> not the recorded one: `_active_backend` out, `_second_backend` in. **Re-priced table (movers /
> lines / descents):** `groups` 8/430/0 *(fenced)* · **`settings` 7/347/3** · `cei` 4/262/0 ·
> `ribbon` 9/243/0 · `briefing` 5/198/0 · `volatility` 2/192/0 · `curves` 3/131/0 ·
> `workbench` 1/67/0.
>
> ## The walk reproduced the record before it was allowed to correct it
> Pointed at the pre-slice-22 tree it had to reproduce ADR-0387's three shipped modules exactly —
> names, line counts AND spans (`brief` 2/48, `card` 2/140, `scorecards` 5/151). It **failed that
> control twice first**, both real defects: (1) `ast.walk(create_app)` yields `create_app` itself,
> so every name inside it got one poison referrer and EVERY family priced at **zero members**;
> (2) the `card` seed used `GET /card`, but the route is `GET /card/{name}`, so it had no seed
> routes — zero again. Both print as a small tidy number. *(ADR-0387's closure table says `brief`
> 1/44 — the function only; its DECISION table and the shipped module say 2/48. The shipped module
> is the record that matters.)*
>
> ## The oracle grew a sixth stage: 652 → 800
> The probe scored **8/9** with `_stack_not_measured` **dark** — not unreachable, but the Law-2
> panel `_work_piling_header` renders INSTEAD of a bar when `/cei` has no scored month. Measured,
> not guessed: of every 2-combination of available fixtures, exactly three produce
> `cei_period=None`, all from the `jacked_up_schedule_*` pair. A query-string variant could not
> reach it (the condition is a POPULATION property), so **`[ceidark]`** was added — that pair,
> `strip_title=True` (intact they become two one-version Projects and `/cei` serves its
> placeholder — the ADR-0375 trap). The member then moves **exactly the two `[ceidark] /cei`
> labels and nothing else**, so the stage is provably load-bearing (battery mutation 5).
>
> ## The probe aborted on its own control, again
> `_page` moved **zero** labels. Not darkness: the injector handled `str`/`dict` and `_page`
> returns an **`HTMLResponse`**. **A probe's marker must match the RETURN TYPE** (ADR-0386) —
> named in the trap list and still the first thing that broke. Repaired (append to
> `Response.body`, re-stamp `content-length`), the control moves **224/224**.
>
> ## Verification
> Probe **9/9 render-proven, ZERO dark** (fourteenth consecutive). Fingerprint (scope: ALL SIX
> stages) `[empty]` 60 `{200:41,400:17,422:2}` + five loaded stages of 148
> `{200:125,404:4,422:19}` = **800** · **800/800 byte-identical** pristine vs cut, and the
> `diff -r` itself SHOWN TO FAIL (one-byte perturbation → exit 1) · determinism ×2 processes on
> BOTH trees **0 flapping** · per-definition byte-identity **9/9 IDENTICAL** (re-read from disk
> AFTER `ruff --fix` + `format`), every def asserted ABSENT from post-cut app.py · multiset
> **95 added / 7 removed — ZERO code lines removed** (4 import-list entries + 3 deliberately
> rewritten comment lines) · battery **7/7 caught** · mypy strict clean over **144** files ·
> `ruff check .` clean whole-tree · corpus re-rendered AFTER the battery, still 800/800.
>
> **Both exports contribute NOTHING, and two instruments say so** — the call graph finds no mover
> referenced by `export_briefing`/`export_cei`, and the probe finds no member moving any
> `/export/` label. Unlike `scorecards` (ADR-0387, 8 export labels), these pages and their
> workbooks share no app-level surface.
>
> **Sweeps (population STATED: 513 .py files, build/dist/.venv/caches excluded).** Dropped-import
> **TWO** (`BowWave`, `Citation`) — zero readers via `web.app`, control `create_app` = 177 files.
> Monkeypatch over the names the new modules **BIND** (26 names, 197 setattr calls): **2 hits**,
> both `audit_schedule` in `tests/ai/test_briefing.py:230-231` — **NOT the ADR-0297 trap**: the
> targets are `ai.briefing` / `engine.recommendations`, a different module from the new
> `web.briefing` (a real BASENAME COLLISION worth knowing), and that test asserts
> `calls == ["audit"]`, a NON-zero assertion, so a dead spy fails loudly. Import sweep **FOUR live
> readers** that must keep working via re-export (`_cei_body` ×2, `_briefing_table_html`,
> `_briefing_body`) — all green. Source-text **37 files**, zero repoints, both whole-view-layer
> guards widened (mutation 4 proves it).
>
> **Three battery mutations did not score on the first pose, and that was the useful part.** M1's
> module-scope upward import is a REAL cycle → pytest died at COLLECTION (exit 2), so the guard
> never ran; re-posed under `TYPE_CHECKING` it is caught BY NAME — and that is the likelier
> smuggling route anyway. M6/M7 edited moved markup and **no unit test noticed** — a true
> measurement about the unit tests, re-scored against the oracle at 2 and 5 labels, which **match
> the probe's independent per-member counts exactly**.
>
> ## The mpxj trap fired exactly as documented
> This container is a `--depth 1` clone; `git log -1 -- tools/mpxj` returned **`3a925b0`** — the
> CLONE BOUNDARY. `git fetch --unshallow` first, and the nine installers pin **`42d92dc`** as they
> must. **The build still has no guard** — it prints the ref and trusts the operator. Still queued.
>
> ## Next
> **Phase 4 slice 24.** Six zero-descent families remain outside `groups`: `ribbon` (9/243),
> `volatility` (2/192), `curves` (3/131), `workbench` (1/67) — and **`settings` (7/347) is the
> only one carrying real descents** (`_ollama_or_none`, `_openai_or_none`, `_second_backend`),
> so it deserves its own slice. **Re-price by referrer walk anyway; the table above is a snapshot,
> and snapshots decay.** Then the standing queue: **`mpxj_ref()` shallow-clone hardening** ·
> stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages ·
> /groups Activities (ADR-0343) · installers vs known-good constraints · P80/P90 residual ·
> doc-drift sweep (`docs/PARITY-REPORT.md` still calls the reference .mpps git-ignored;
> `docs/FINAL-REPORT.md`'s blanket "Exact match") · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 + re-run Fuse · one Acumen run on a crafted sub-day-negative-
> float schedule · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
> re-export decision.
>
> ## Carried forward
> ADR-0353..0388 closed — do not re-open. **The oracle is committed: import it, don't rebuild it.**
> `python tests/web/oracle_corpus.py --out <dir>` with `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and the cut tree, then
> `diff -r` on the DIRECTORIES (filenames are LABEL-addressed, so a manifest diff is the wrong
> surface). NEW lessons: (1) a priced table is a snapshot and decays silently — re-walk, and make
> the walk reproduce something KNOWN before believing it about something unknown; (2) a control
> that names an expected VALUE beats one that names a direction ("zero members" and "no seed
> routes" both print as plausible output); (3) a doc-comment that names a FUTURE has an expiry
> date — grep the moved names to find them; (4) a mutation that does not score can be the most
> informative one in the battery; (5) the oracle extension is only honest if the member then moves
> exactly the labels the condition added. Standing traps unchanged (an instrument is not evidence
> until shown to FAIL · a probe's marker must match the RETURN TYPE · `ast` col_offset is a BYTE
> offset · a census can be exact and still not be membership · a page-only anchor understates an
> export-feeding member · route-only referrers never force a descent · sweep by BARE NAME · a
> sweep's POPULATION is part of its claim · a prefix that is a prefix OF ANOTHER FAMILY fuses two
> censuses — seed on exact route lists · the MPXJ pin drifts in a shallow clone · a parallel
> session can take your ADR number · never MEASURE a tree a battery is mutating · a normalizer
> that fails silently is a flap factory · fingerprints carry their SCOPE · the installer lockstep
> guard makes the rebuild a PREREQUISITE of the final suite · round-half-even 240→0 · MSPDI
> re-derives Duration · env-defect masquerade · named-failure rule · empty sweep needs a positive
> control · `grep -c` exits 1 on zero · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors ·
> five playwright-only failures pre-existing, CI-invisible · scratchpad harnesses hardcode the
> repo root · `python -m pytest` prepends CWD to `sys.path` and bare `pytest` does NOT · two ruffs
> on PATH, run `python -m ruff`). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
