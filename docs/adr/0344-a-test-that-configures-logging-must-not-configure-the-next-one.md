# ADR-0344 — A test that configures logging must not configure the next one

**Status:** Accepted · **Date:** 2026-08-03 · **Audit:** external review 2026-08-03, lead item 2
(HIGH CI reliability / LOW product impact) · **Related:** ADR-0250 (dependency floors)

## Context

An external review reported that `tests/exhibits/test_cli_guards.py::test_cli_fails_closed_before_
any_output_when_egress_guard_trips` calls `cli.main()` without resetting logging, and that later
`caplog` tests therefore fail. It asked two questions this ADR answers by measurement: **is it
pytest-version-sensitive, and does hosted CI reproduce it?**

`configure_logging()` sets `propagate = False` on the `schedule_forensics` logger and installs a
process-global redacting handler. That is correct and deliberate for the shipped tool — Law 1
requires that records never reach an unredacted root handler — and it is reached from
`cli.main()`, `launcher.main()`, and, on first use, from `get_logger()`. pytest's `caplog`
captures by **propagation to the root logger**, so a leaked `propagate = False` silently empties
`caplog.text` for every later test.

### What measurement found

**The reported test is one of seventeen.** A per-test bisect (each candidate run immediately
before a known victim) named every polluter:

| module | polluting tests |
|---|---|
| `tests/exhibits/test_cli_guards.py` | 1 |
| `tests/test_launcher.py` | 12 |
| `tests/test_logging_redaction.py` | 4 |

and four victims, all `caplog`-based: `tests/importers/test_mspdi.py` ×2,
`tests/importers/test_xer.py` ×2.

**It is version-sensitive, and hosted CI does not currently reproduce it.** Same tree, same
commit, only the pytest version changed:

| pytest | victim alone | victim after a polluter | full suite |
|---|---|---|---|
| 9.1.1 | pass | **pass** | 3400 passed |
| 8.4.2 | pass | **FAIL** | **5 failed**, 3301 passed |
| 8.0.2 | pass | **FAIL** | — |

pytest 9.1.x additionally attaches its capture handler to the `schedule_forensics` logger itself,
which masks the leak. The leak is nonetheless **live on 9.1.1** — the logger really is left at
`propagate = False`, measured directly.

**This matters because the project declares support for the failing range.**
`[tool.pytest.ini_options] minversion = "8.0"` and `dev = ["pytest>=8"]` — unbounded. Which
behaviour a checkout gets is decided by the resolver on the day, not by this repository. CI is
green today only because `pytest>=8` currently resolves to 9.1.1.

## Decision

**Restore the logging state after every test, in one autouse fixture, rather than adding a fixture
request to each of the seventeen sites.** `tests/conftest.py::_restore_redacting_logging`
snapshots the `schedule_forensics` logger's handlers / `propagate` / level plus
`logging_redaction._configured` before each test and restores them after.

Per-site fixture requests were rejected: they fix the seventeen known sites and do nothing about
the eighteenth. Any new test that calls an entry point would reintroduce the leak silently, and
the symptom is invisible on the pytest version CI resolves.

`configure_logging` itself is untouched — `propagate = False` is a Law-1 requirement of the
shipped tool, not a defect. This is a test-isolation fix only.

The existing `reset_redacting_logging` fixture is unrelated and stays: it *pre*-clears so a
startup-wiring test must freshly install the handler (audit re-review 2026-07-17). The new fixture
*post*-restores. Being autouse it is set up first and torn down last, so it runs after that
fixture's own restore.

## Consequences

No product code changes; no rendered figure, metric, or parity value moves.

Under **pytest 8.4.2**, with the fix: the polluter plus all four victims **126 passed**; the three
polluting modules plus every importer test **404 passed**. Without it, the same selection gives
**4 failed**.

**`tests/test_logging_isolation.py` (2 tests) pins the state, not the symptom — deliberately.**
A `caplog`-based regression test would pass on pytest 9.1.x with or without the fix, i.e. coverage
theatre on the version CI actually installs. The *leak* is not version-sensitive, so asserting on
the state fails on **every** pytest version when the fixture is absent. The two tests are a
true-positive / isolation pair: `test_a` asserts `configure_logging` really does stop propagation
and install a handler (so a "fix" that neutered it would fail), `test_b` asserts the next test
starts where `test_a` started.

**What the tests assert is the guarantee the fixture actually makes, and the first draft got this
wrong.** `test_b` originally asserted a *pristine* `propagate is True`. That passed the module in
isolation and **failed the full suite** — bisected to `tests/perf`, whose module-scoped `served`
fixture starts a real server. Higher-scoped fixtures are set up *before* function-scoped ones, so
that configuration happens outside any per-test window and legitimately moves the session baseline;
a function-scoped restore cannot undo it. The assertion was a stronger claim than the mechanism
supports. Comparing against the baseline `test_a` records is exact under either condition and still
fails hard on the original defect. **A module-scoped fixture that configures logging is therefore a
known, accepted limit of this fix** — it changes the baseline for everything after it, which is
harmless (no `caplog` test follows `tests/perf` in collection order) but is recorded here rather
than left to be rediscovered.

**Proved able to fail:**

| revert | pytest 9.1.1 alone | 9.1.1 after `tests/perf` | pytest 8.4.2 alone |
|---|---|---|---|
| `autouse=True` → `autouse=False` | `test_b` **fails** | `test_b` **fails** | `test_b` **fails** |
| same revert, four real victims | (masked) | — | **4 failed** |

In every cell exactly one of the two fails: the true-positive twin `test_a` stays green, so the
pair discriminates rather than both keying off one condition.

## Deliberately NOT done here

**The unbounded dependency ranges that make this reachable are not fixed by this ADR.** No upper
bounds and no lock/constraints file mean the suite's pass/fail depends on resolution date — this
defect is the existence proof. `pyproject.toml` already carries
`filterwarnings = ["ignore:Using \`httpx\` with \`starlette.testclient\`:DeprecationWarning"]`,
i.e. an upstream deprecation was silenced rather than bounded; Starlette 1.3.1 raises outright if
neither `httpx2` nor `httpx` is present. That is its own change (constraints file + a floor-version
CI leg) and is tracked as the next unit.

**Two modules error instead of skipping without playwright** — `tests/perf/test_observer_storm.py`
and `tests/web/test_launch_invalidation.py` use a bare `from playwright.sync_api import …` where
`tests/web/test_r11_panel_contract.py:817` correctly uses `pytest.importorskip`. Measured, small,
and separable; tracked with the constraints work.
