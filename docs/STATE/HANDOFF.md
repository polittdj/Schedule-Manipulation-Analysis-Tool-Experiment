# Handoff — 2026-08-03f (P0 closed: the dependencies are bounded, and the floor found a Law 1 defect; ADR-0346; v1.0.161)

> ## STATUS (current) — branch `claude/resume-polaris-v1-geq9o7`, draft PR open, CI pending.
> **ADR-0346**, **v1.0.161**. The audit's P0-2 (bound the dependencies) and P0-3 (`importorskip`)
> are both delivered in one unit, because P0-3 had to land first — the new floor CI leg would have
> been red on day one from two bare `from playwright.sync_api import …`.
>
> ## THE HEADLINE — the floor job found an air-gap violation on its first run
> `pyproject.toml` declared `fastapi>=0.110`. **fastapi 0.110.0 and 0.110.1 serialize a
> `RequestValidationError` with pydantic's `url` key intact**, so a 422 body served by the
> air-gapped tool carries `https://errors.pydantic.dev/<ver>/v/missing` — an **external reference
> on the CUI boundary**, on **10 routes**.
> `tests/web/test_airgap.py::test_every_get_route_serves_no_external_reference` catches it perfectly
> and always would have; **no configuration had ever asked it the question.** Isolated to fastapi,
> not pydantic, by holding each fixed: 0.110.0 fails under pydantic **2.6.0 AND 2.13.4**; 0.110.2 /
> 0.110.3 / 0.111.0 / 0.112.0 / 0.115.0 / 0.141.1 all pass. **Floor raised to `fastapi>=0.110.2`.**
> *Two correct controls that never meet prove nothing — the job is what introduces them.*
>
> ## THREE declared floors were false. All were measured, none was guessed.
> | declared | measured |
> | --- | --- |
> | `pydantic>=2` + `fastapi>=0.110` | **unsatisfiable** — fastapi 0.110 excludes pydantic 2.0.0/2.0.1/2.1.0 |
> | `pydantic>=2` (once installable) | 2.0.2 · 2.4.2 · 2.5.0 · 2.5.3 FAIL the frozen-`Schedule` hash test; **2.6.0 first to pass** |
> | `fastapi>=0.110` | **air-gap violation** on 10 routes; **0.110.2 first clean** |
>
> The pydantic one is a *product* mechanism: its generated `hash_func` hashed
> `self.__dict__.values()`, which on a frozen `Schedule` includes the `tasks_by_id` cache →
> `TypeError: unhashable type: 'mappingproxy'`.
>
> ## What landed
> * **Upper bounds on every requirement.** `setuptools` is the ONE exemption, named in
>   `UNBOUNDED_BY_DESIGN` and asserted **by equality** so it cannot grow silently — an upper bound
>   there would block the next CVE remediation, which is why its floor exists (ADR-0250).
> * **`constraints/floor.txt`** (8 pins, the declared lower bounds) and **`constraints/known-good.txt`**
>   (59 pins, the full `.[dev]` closure on 3.11, where **starlette** is pinned — nothing under `src/`
>   imports it, so a constraints file is where bounding it belongs).
> * **CI job `floor`** (Python 3.11): resolve the lock · install at the floors · **verify the floors
>   actually bound** · full suite · parity. **In `check`'s `needs`**, so a false support range blocks
>   merge without the operator's branch-protection change (audit #8).
> * **`tests/test_dependency_bounds.py`** (7) — bounds exist · unbounded set **equals** the exemption
>   set · floor file pins exactly the executed set · every floor pin **equals** the declared bound ·
>   `minversion` equals the pytest pin · known-good sits inside the ranges · known-good is complete.
> * **`ruff>=0.16.1,<0.17`** — `ruff format --check` is a gate step and its output moves across
>   minors. `.[dev]` now installs the gate's ruff; **the manual `pip install 'ruff==0.16.1'` is gone.**
> * `pytest.importorskip("playwright")` in the two unguarded modules. Lean venv (pytest 8.0.2, no
>   playwright): **`1 failed, 3 passed, 2 errors` → `3 passed, 2 skipped`**. With playwright present
>   all **6** tests still collect (checked — a guard that over-skips is the same defect).
>
> ## Verification
> * **All 7 guard assertions proved able to fail**, each on its own mutation; tree restored
>   byte-identical from a scratchpad copy.
> * **The guard caught a real defect on its first run — in my own artifact.** `pip freeze` omits
>   `setuptools` (pip treats it, `pip` and `wheel` as "self"), so the first `known-good.txt` dropped
>   the ONE pin that exists for a CVE remediation. Regenerate with `--all`.
> * **The "floors must actually bind" CI step proved able to fail**: run against the current venv it
>   reports **7 of 8** pins unbound, `rc=1`. A constraints file only binds what gets installed, so a
>   typo'd pin is a silent no-op and the job would go green having tested the newest resolution.
> * Full suite **at the corrected floor** (pydantic 2.6.0 · fastapi 0.110.2 · starlette 0.37.2 ·
>   uvicorn 0.29.0 · jinja2 3.1.6 · python-multipart 0.0.18 · pytest 8.0.0 · pytest-cov 5.0.0 ·
>   httpx 0.27.0, CPython 3.11): **3315 passed, 44 skipped, 0 failed** (12:03). Parity at that
>   floor: **49 passed**, 14 skipped (Law 2 — the numbers do not move with the resolver).
>   *The first attempt read `3 failed, 3312 passed` and every failure was `test_state_docs.py`
>   reading HANDOFF/SESSION-LOG **while I was mid-rotation**. I re-ran rather than reconstruct
>   `3312 + 3` — a composite assembled by argument is not a measurement.*
> * Final gate on this tree: ruff · ruff-format (**460**) · mypy-strict (**117**) · bandit **0** ·
>   `node --check` **60/60** (per file) · full suite **3410 passed, 3 skipped, 1 failed** ·
>   `-m parity` **49 passed**. The one failure is the named **load-sensitive** `/analysis`
>   focus→tip family — `test_float_tip_dismiss`, its documented signature verbatim
>   (`page.wait_for_function(TIP_VISIBLE, timeout=4000)` at `test_float_tip_dismiss.py:112`).
>   Re-run unloaded with its sibling module: **19 passed**. Nothing in this diff touches `src/`
>   or the vendored JS, so it cannot be caused by it; never red on CI. Do NOT chase.
> * `tests/guards` **68 passed** · installer lockstep **62 passed** · wheel + nine installers rebuilt
>   at v1.0.161 (`Requires-Dist: fastapi<1,>=0.110.2` ships in the metadata — **a bounds change is a
>   shipped change even when `src/` is untouched**).
>
> ## Deliberately NOT done
> * **Actions stay on mutable tags** (`@v4`/`@v5`/`@v6`), including the two the new `floor` job adds.
>   SHA pinning is audit #7 / P1 and wants one mechanical sweep, not a mixed-style file. Recorded so
>   the next session does not read the new job as an oversight.
> * **The installers do not install with `-c constraints/known-good.txt`** — they embed a wheel whose
>   *metadata* carries the bounds, which is the part that governs what an operator resolves. Wiring
>   the lock into the nine scripts touches 62 lockstep tests and is its own unit.
> * **The `filterwarnings` ignore stays** — the deprecation is genuinely upstream and unactionable in
>   a product that imports neither httpx nor starlette. What changed is that it is no longer the
>   *whole* answer: the comment now points at the bound and the pin that carry the real risk.
> * `pytest-cov` / `bandit` / `pip-audit` floors were **not** bisected the way pydantic's was — they
>   are ADVISORY (their output is version-sensitive by design) and bounded instead.
>
> ## Next — P1
> Intake manifest + extension↔content regression test (**89** mismatched files, ALL in
> `00_REFERENCE_INTAKE/`) · reconcile R-03/R-12 · CUI hook hardening (`.json` content sniff,
> `.p6xml`, `*.mpp.*`) · **Action SHA pinning**. Then Fable 5: CC-01 · SRA-LEGACY · V3.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — not intermittent, not deterministic.
> Pre-existing, never red on CI. Do NOT chase. `/briefing`, `/path`, `/compare` still carry no
> `page-lede`; the `/groups` "Activities" column still counts summary rows. `pgrep -f` self-matches.
> pytest stdout to a FILE is block-buffered (`python -u`). Never `git checkout <file>` to undo a test
> mutation — `cp` from a scratchpad copy.
>
> **New this session:** *ask not "is there a test?" but "is there a configuration in which that test
> has ever been asked the question?"* And: **a capture tool's default exclusions are part of your
> data** — `pip freeze` quietly dropping `setuptools` is the same shape as July's 64-byte magic-byte
> window inventing three false positives.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
