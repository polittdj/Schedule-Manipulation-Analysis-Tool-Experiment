---
name: full-gate
description: Run POLARIS/SMAT's complete pre-commit quality gate (ruff, ruff format, mypy --strict, bandit, pytest, node --check, parity) and triage every failure as real-vs-environment before touching anything. Use before EVERY commit, push, or PR in this repo; when asked to "run the gate", "run the tests", "run the checks", "is it green?", "check CI will pass"; after any edit to src/, tests/, docs/ or the vendored JS; and whenever a suite result needs to be reported. Encodes the exit-code, buffering and per-file traps this repo has already paid for.
---

# The full gate

CLAUDE.md: **run this before every commit.** CI (Python 3.11 + 3.13) runs the Python steps plus
`pip-audit` and enforces the coverage gates. The `node --check` step is local-only. Plain local
`pytest -q` does **not** collect coverage — the 85/70 numbers are CI-enforced, so a local green
`pytest` is not a coverage claim.

## 0. Preconditions (fresh container)

```bash
python -m pip install -e ".[dev]"
python -m pip install playwright 'ruff==0.16.1' build     # measured-box proof + wheel build
```

### Verify WHICH ruff you are about to run — it is not necessarily the one you installed

```bash
which -a ruff && pip show ruff | head -2      # PATH order vs installed version
```

**Measured 2026-08-03:** `pip install 'ruff==0.16.1'` landed in `/usr/local/bin`, while a stale
**0.15.8** in `/root/.local/bin` shadowed it on PATH. The two disagree on scope, not just style:

| binary | `ruff format --check .` covers |
| --- | --- |
| 0.15.8 | **458** files — python only |
| 0.16.1 | **867** files — python **plus fenced `python` blocks inside markdown** |

So a `SKILL.md`, ADR or doc containing an unformatted `python` block passes locally under the
shadowed 0.15.x and **fails CI**, which resolves `ruff>=0.6` to the latest. If the two disagree, run
the absolute path of the version CI will use. (`audit/*.md` is excluded in `pyproject.toml` on purpose
— a formatter must never rewrite quoted evidence.)

This is the repo's own "a green gate proves nothing if the binary isn't the one CI runs"
(LESSONS-LEARNED 2026-07-29 cont.3) in a new costume. Check the binary, not just the exit code.

## 1. Statics FIRST, in the foreground

Run the cheap checks before the suite (last measured **27:30** locally; budget 21–30 min), and run
them in the **foreground** — a backgrounded static check whose output you never read is not a check.

```bash
ruff check src/ tests/
ruff format --check .
python -m mypy src/                       # strict
bandit -q -r src ; echo "bandit exit: $?"
for f in src/schedule_forensics/web/static/*.js; do node --check "$f" || echo "JS FAIL: $f"; done
```

**`node --check` must be PER FILE.** `node --check src/.../static/*.js` checks only the **first**
glob match and exits 0 — the loop above is the only correct form.

**Only a non-zero `bandit` EXIT is a failure.** `nosec encountered … but no failed test`
warnings are not failures. Print the exit code explicitly, as above.

## 2. The suite

```bash
python -m pytest -q                                   # full suite
python -m pytest -m parity                            # the Law-2 acceptance gate (~250 s, 49 tests)
```

Single test / module:
```bash
python -m pytest tests/web/test_groups_view.py::test_filter_scopes_the_population -q
```

Optional CI-equivalent coverage run (slower):
```bash
python -m pytest --cov=schedule_forensics --cov-report=term-missing --cov-fail-under=70
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85
```

## 3. The four traps that have burned this repo

1. **A piped exit code is not the command's exit code.** `cmd | tail` reports `tail`'s status.
   A real `bandit` failure hid behind exactly this, and `pytest --timeout=` (which is **NOT**
   installed here) exits **0** with a usage error through a `| tail` pipeline. Capture the status
   of the command itself (`; echo "exit: $?"` immediately after it, or `set -o pipefail`).
2. **pytest stdout to a FILE is block-buffered.** Use `python -u -m pytest …` when redirecting.
   An empty output file is not a stall.
3. **Never report a suite you did not read.** "I reported a green suite I never read"
   (LESSONS-LEARNED 2026-07-30 cont.2) — read the summary line and the counts before saying green.
4. **`cd` in a Bash call persists across calls.** Use absolute paths.

## 4. Triage — real error vs environment (decide BEFORE editing)

**NOT errors in this environment — never "fix" these:**
- `SKIPPED` for missing CUI intake (`Project2.mpp`, `Project5.mpp`, real `.mpp`/`.xlsx`),
  "no Java runtime", "openpyxl not installed", "playwright not installed" — deliberately env-gated.
- Anything needing network, Ollama, or a model — this environment has none by design.
- `bandit` nosec *warnings* (see above).
- A test that passes on a clean targeted re-run — that is a flake. Note it; do not edit it.
- **Known intermittent:** the `/analysis` focus→tip family (`tests/web/test_float_tip_dismiss.py`,
  `tests/web/test_float_tip_scroll.py`) — adjudicated, pre-existing, has **never** failed on CI.
  Do NOT chase.

### Installing playwright locally makes CI-invisible tests execute

Verified from `.github/workflows/ci.yml` + `pyproject.toml`, 2026-08-03:

| job | installs | runs |
| --- | --- | --- |
| `test (3.11)` / `test (3.13)` | `.[dev]` — **no playwright** | everything; all playwright-gated tests **skip** |
| `browser (measured-box proof)` | `.[dev,browser]` | **only** `tests/web/test_r11_panel_contract.py` |

`playwright` lives in its own `[browser]` extra, not `[dev]`. So the moment you
`pip install playwright` locally, ~19 browser tests start executing that **no CI job ever runs** —
including the tip family above. Measured the same day: that family returned **2 failed**, then
**0 failed** (pristine tree), then **1 failed** — three different answers on trees whose only
difference was *markdown*. A varying count on an identical tree is the proof of a flake; **a pristine
pass is not a discriminator when the diff cannot be causal — it is just another sample.**

Practical rule: a local red confined to the tip family is **expected** and is not a CI signal. Report
it, name it, and do not chase it. Do not "fix" it by widening its 4 s `wait_for_function` timeout —
that weakens a test to silence an environment.

**Real errors — fix these:**
- `ruff check` violations, `ruff format` would-reformat, any `mypy` error, non-zero `bandit` exit.
- A `FAILED` that **reproduces** on a targeted re-run (`python -m pytest <nodeid> -q`).
- `node --check` syntax errors in the vendored JS.
- Doc drift:
  - `tests/web/test_docs.py` → regenerate the dictionary:
    ```bash
    python -c "from schedule_forensics.web.help import render_dictionary_markdown as r; open('docs/METRIC-DICTIONARY.md','w',encoding='utf-8').write(r())"
    ```
  - `tests/test_state_docs.py` → the highest ADR on disk must appear in **both**
    `docs/STATE/HANDOFF.md` and `docs/STATE/SESSION-LOG.md`; `HANDOFF.md` must carry
    `pyproject.toml`'s version in its **top** section, stay ≤64 KB, and hold exactly one
    `# (prior)` heading. See the `session-close` skill. Never invent an ADR to satisfy it.

## 5. Fix discipline

Smallest correct change that resolves the root cause; match surrounding style and comment density.
**Never** silence a check by deleting a test, adding a blanket `# noqa` / `# type: ignore`, or
weakening an assertion — Law 2 outranks a green gate. If a real error needs a large refactor or a
judgment call, report it with a precise diagnosis instead of fixing it.

After fixing, **re-run the affected check and then the whole gate**. A fix verified only against the
test it targeted is how this repo shipped regressions.

## 6. Report

State each check's result with counts, then the split: real errors fixed · triaged as
environment/flake (so they are not re-investigated) · genuine but out of scope.
