# ADR-0346 — A support range nobody runs is not a support range

**Status:** Accepted · **Date:** 2026-08-03 · **Extends:** ADR-0345 (logging isolation),
ADR-0250 (CVE floors) · **Answers:** external audit 2026-08-03 findings **#1** (dependency
reproducibility) and the skip-vs-error half of **#2**

## Context

ADR-0345 closed a test-isolation leak whose symptom was version-dependent: the *same tree* gave

| pytest | full suite |
| --- | --- |
| 8.0.2 | FAIL |
| 8.4.2 | FAIL (5 failed, 3301 passed, 42 skipped, 2 errors) |
| 9.1.1 | PASS (3400 passed, 3 skipped) |

That is not a fact about pytest. It is a fact about a repository whose declared dependency ranges
were open at the top (**no upper bound anywhere**, **no lock or constraints file**) and untested at
the bottom (`pytest>=8` and `[tool.pytest.ini_options] minversion = "8.0"`, with nothing that ever
installed pytest 8). Whether CI was green depended on what pip resolved that morning. ADR-0345's
autouse fixture and #529's ADR-uniqueness guard were both patches on symptoms of this.

The audit also noted that `filterwarnings` already carried
`ignore:Using \`httpx\` with \`starlette.testclient\`` — **the upstream deprecation had been
silenced rather than bounded**. starlette 1.3.1 imports `httpx2`, falls back to `httpx` with that
warning, and raises `RuntimeError` if neither is present; a starlette that finishes the transition
breaks every web test at import time, and nothing in the tree constrained which starlette arrives.

### What measurement found when the floors were actually tried

Three live falsehoods in `pyproject.toml`, not hypotheticals — and the third is a **Law 1** matter:

| declared | measured |
| --- | --- |
| `pydantic>=2` with `fastapi>=0.110` | **does not resolve at all** — fastapi 0.110.0 requires `pydantic!=2.0.0,!=2.0.1,!=2.1.0`, so the declared pair is unsatisfiable at its own floors |
| `pydantic>=2` (once installable) | 2.0.2 · 2.4.2 · 2.5.0 · 2.5.3 **FAIL** `tests/model/test_schedule.py::test_cache_does_not_perturb_hash_or_equality`; **2.6.0 is the first release that passes** |
| `fastapi>=0.110` | **AIR-GAP VIOLATION.** 0.110.0 and 0.110.1 fail `tests/web/test_airgap.py::test_every_get_route_serves_no_external_reference` on **10 routes**; **0.110.2 is the first clean release** |

The pydantic failure is worth recording because it is a *product* mechanism, not a tooling one:
pydantic's generated `hash_func` used to hash `self.__dict__.values()`, and on a frozen `Schedule`
that dict includes the `tasks_by_id` cache — `TypeError: unhashable type: 'mappingproxy'`. The
frozen-model identity contract this repo depends on simply did not hold below pydantic 2.6.

**The fastapi row is the one that justifies the whole unit.** fastapi 0.110.0/0.110.1 serialize a
`RequestValidationError` with pydantic's `url` key intact, so a 422 body served by the air-gapped
tool contains `https://errors.pydantic.dev/<ver>/v/missing` — an external reference, on the CUI
boundary, in a product whose first law is that nothing leaves the machine. The guard that catches it
has existed all along and is correct; what was missing was anything that ever *ran* at the bottom of
the declared range.

**Mechanism confirmed by source diff**, not inferred from the URL's shape — the two wheels were
downloaded and compared. `fastapi/_compat.py`, 0.110.0 → 0.110.2:

```diff
-                    errors=exc.errors(), loc_prefix=loc
+                    errors=exc.errors(include_url=False), loc_prefix=loc
@@
-        ).errors()[0]
+        ).errors(include_url=False)[0]
```

`include_url=False` is the entire fix upstream, and it is absent below 0.110.2. Isolated to fastapi
and not pydantic, by holding each fixed in turn:

| fastapi | pydantic | `test_airgap.py` |
| --- | --- | --- |
| 0.110.0 | 2.6.0 | **1 failed**, 3 passed |
| 0.110.0 | 2.13.4 | **1 failed**, 3 passed |
| 0.110.1 | 2.6.0 | **1 failed**, 3 passed |
| 0.110.2 | 2.6.0 | 4 passed |
| 0.110.3 · 0.111.0 · 0.112.0 · 0.115.0 | 2.6.0 / 2.13.4 | 4 passed |
| 0.141.1 (today's resolution) | 2.13.4 | 4 passed |

So `fastapi>=0.110` had **declared support for an air-gap violation**, invisibly, for as long as the
line has existed. The floor is now `>=0.110.2`.

### The skip-vs-error gap (audit #2's remainder)

Of the pytest-8 "5 failed / 2 errors", four were ADR-0345's leak. The rest were
`ModuleNotFoundError: playwright` — `tests/perf/test_observer_storm.py` and
`tests/web/test_launch_invalidation.py` used a bare `from playwright.sync_api import …` where the
other 21 playwright-touching modules use `pytest.importorskip`. A census of all 23 confirmed those
two, and only those two, lacked a guard. Reproduced in a lean venv (pytest 8.0.2, no playwright):
**`1 failed, 3 passed, 2 errors`**.

## Decision

**Bound the range, pin a point inside it, and execute the bottom of it.**

1. **Upper bounds on every requirement**, with one named exemption. `pydantic>=2.6,<3`,
   `fastapi>=0.110.2,<1`, `uvicorn>=0.29,<1`, `jinja2>=3.1.6,<4`, `python-multipart>=0.0.18,<1`,
   `psutil>=5.9,<8`, `playwright>=1.44,<2`, `pytest>=8,<10`, `pytest-cov>=5,<8`,
   `ruff>=0.16.1,<0.17`, `mypy>=2,<3`, `bandit>=1.7,<2`, `pip-audit>=2.7,<3`, `httpx>=0.27,<1`.
   `setuptools>=83.0.0` stays open **on purpose**: it majors on a calendar cadence, and an upper
   bound is precisely what would block the next CVE remediation — the reason its floor exists at
   all (ADR-0250).
2. **`constraints/floor.txt`** — the declared lower bounds, pinned, and **run by CI**.
3. **`constraints/known-good.txt`** — the full 59-pin transitive closure of `pip install -e '.[dev]'`
   on CPython 3.11, measured green, for reproducing a build exactly (offline operator install, or a
   "did the code change or did the resolution?" bisect). This is where **starlette is pinned**: it
   is not a declared dependency — nothing under `src/` imports it (verified, zero matches) — so a
   constraints file, not `project.dependencies`, is where bounding it belongs.
4. **A new CI job, `floor`** (Python 3.11, `requires-python`'s own minimum): resolve the known-good
   lock, install at the floors, **verify the floors actually bound**, run the whole suite, run the
   parity gate. It is in `check`'s `needs`.
5. **`pytest.importorskip("playwright")`** in the two unguarded modules — module-level in
   `test_observer_storm.py` (every test there needs a browser), and inside the `served` fixture in
   `test_launch_invalidation.py` (only one of its four tests does, and guarding the fixture rather
   than the test body means no uvicorn server is started only to be discarded).
6. **`tests/test_dependency_bounds.py`** (7 assertions) keeps the three artifacts from drifting
   apart: every requirement has both bounds · the unbounded set **equals** the documented exemption
   set · the floor file pins exactly the executed-floor distributions · every floor pin **equals**
   the declared lower bound · `minversion` equals the pytest floor pin · every known-good pin sits
   inside its declared range · known-good covers every runtime and dev requirement.

### Two kinds of lower bound, named as such

The QC tools (ruff, mypy, bandit, pip-audit, setuptools) are deliberately **absent** from
`constraints/floor.txt`. Their *output* is version-sensitive by design — `ruff format` began
rewriting fenced Markdown at 0.16, which is why `[tool.ruff.format] exclude` exists — so running
the gate against an old one measures the tool, not the product. Those floors are **advisory** and
their ranges narrowed instead; the rest are **executed**. Calling the distinction out in the test
is the point: an unexecuted floor is a claim, and claims should be labelled.

`ruff>=0.16.1,<0.17` is the sharpest of these. `ruff format --check` is a gate step, so an
unbounded `ruff>=0.6` meant a new minor could redden CI on a tree nobody touched.

## Consequences

* **The floor job paid for itself on its first run.** It did not merely confirm a support range — it
  surfaced a Law 1 defect (`fastapi` 0.110.0/0.110.1 serving an external URL) that the existing
  air-gap guard was already written to catch and had simply never been given the chance to. Two
  correct controls that never meet prove nothing; the job is the thing that introduces them.
* The `test` matrix stays **unconstrained on purpose** — it is the canary that catches an upstream
  release early. `known-good.txt` is what makes one point inside the band exactly repeatable; using
  it in the canary would trade a known-late failure for an unknown-late one.
* CI gains one ~30-minute parallel job. `floor` is in `check`'s `needs` (unlike `browser`, excluded
  for its documented render flakes): it runs no browser, is deterministic, and a red floor means the
  declared support range is false — which must block a merge **without** waiting on the
  branch-protection change that audit #8 leaves to the operator.
* Bumping a bound now costs a deliberate three-file commit. That is the intended friction.
* The floor job carries an explicit **"the floors must actually be the floors"** step. A constraints
  file only binds packages that get installed, so a typo'd or renamed pin is a silent no-op and the
  job would go green having tested the newest resolution — the same shape as the measured-box tests
  that skipped and passed (ADR-0304/0305). Proved able to fail: run against the current venv and it
  reports 7 of 8 pins unbound, `rc=1`.
* `.[dev]` now installs mypy 2.x by declaration rather than by resolution. Anyone pinned to mypy 1.x
  must bump.

## Verification

* **All 7 guard assertions proved able to fail**, each on its own targeted mutation (strip a lower
  bound · strip an upper bound · drop a floor pin · make the floor pin disagree with the declaration
  · drift `minversion` · put a known-good pin outside its range · drop a covered requirement), tree
  restored byte-identical from a scratchpad copy afterwards.
* The guard **caught a real defect on its first run**: `pip freeze` omits `setuptools` (pip treats
  it, `pip` and `wheel` as "self" packages), so the first known-good capture dropped the one pin that
  exists for a CVE remediation. The regeneration recipe in the file now uses `--all`.
* **P0-3, before → after** in a lean venv (pytest 8.0.2, no playwright):
  `1 failed, 3 passed, 2 errors` → **`3 passed, 2 skipped`**, both skips reporting
  *"playwright not installed (runtime stays stdlib-only)"*. And the other half of that check, which
  is the one a careless `importorskip` gets wrong: **with playwright present all 6 tests still
  collect** across the two modules. A guard that over-skips is the same defect wearing the other
  sign.
* A census of **all 23** playwright-touching test modules confirmed these two, and only these two,
  lacked a guard — the audit's figure, re-derived here rather than transcribed.
* Full suite **at the corrected declared floors** (pydantic 2.6.0 · fastapi 0.110.2 · uvicorn 0.29.0
  · jinja2 3.1.6 · python-multipart 0.0.18 · pytest 8.0.0 · pytest-cov 5.0.0 · httpx 0.27.0 ·
  starlette 0.37.2, CPython 3.11): **3315 passed, 44 skipped, 0 failed** (12:03). The parity gate at
  that same floor: **49 passed**, 14 skipped — Law 2 holds, the reported numbers do not move with the
  resolver. The 44 skips are the playwright-gated browser modules, which is the P0-3 fix working at
  scale.
* **The first attempt at that number was contaminated and was re-run, not reconstructed.** It read
  `3 failed, 3312 passed`, and all three failures were `tests/test_state_docs.py` reading
  `HANDOFF.md` / `SESSION-LOG.md` *while this session was mid-rotation* — the drift guard reads those
  files from disk at test time. Re-running gave `3315 passed`. Reporting `3312 + 3` would have been a
  composite assembled by argument, which is not a measurement — and this figure is the ADR's headline
  evidence.
* `tests/guards` **68 passed** with the new specifiers — `net_guard.runtime_requirement_names()`
  parses the bounded requirement strings unchanged (checked after `pip install -e .` so the
  dist-info metadata was regenerated, not the stale pre-edit copy).

## Deliberately NOT done

* **`setuptools` is left unbounded**, named in `UNBOUNDED_BY_DESIGN`, and the test asserts that set
  by **equality** so the exemption cannot grow silently. `build-system.requires` is untouched for
  the same reason and is a different resolver.
* **The `filterwarnings` ignore stays.** The deprecation is genuinely upstream and unactionable in a
  product that imports neither httpx nor starlette. What changed is that it is no longer the *whole*
  answer: the comment now points at the bound (`fastapi<1`) and the pin (`starlette` in
  known-good.txt) that carry the actual risk.
* **Actions are still on mutable tags** (`@v4`/`@v5`/`@v6`), including the two the new `floor` job
  adds. SHA pinning is audit #7 and P1; mixing styles inside one file would be worse than doing it
  in one mechanical sweep. Recorded so the next session does not read the new job as an oversight.
* **The installers do not yet install with `-c constraints/known-good.txt`.** They now embed a wheel
  whose *metadata* carries the bounds, which is the part that governs what an operator's machine
  resolves. Wiring the lock into the nine installer scripts touches 62 lockstep tests and is its own
  unit.
* **`pytest-cov`, `bandit` and `pip-audit` floors were not bisected** the way pydantic's was. They
  are advisory and bounded; bisecting each would spend hours to make an untested claim slightly less
  untested.
