# ADR-0410 — MF-01: TCPI was scored with its PASS direction inverted, so unaffordable programmes reported PASS

**Status:** Accepted · **Date:** 2026-08-16 · **Closes:** MF-01 (deep-dive audit round 2,
`engine_metrics` dimension; lead-verified) · **Severity:** high (Law 2) ·
**Version:** v1.0.207 → **v1.0.208** (shipped code) — wheel + nine installers rebuilt,
lockstep 64/64.

## Context

`engine/metrics/evm.py::_index()` built all three EVM indices with a hardcoded
`Direction.GE` against a 1.0 threshold. For **SPI** and **CPI** that is right: higher is
better. **TCPI is inverted by definition.**

TCPI = (BAC − EV) / (BAC − AC) is the cost efficiency the *remaining* work must achieve to
land on budget. Above 1.0 the programme must **outperform its own plan** — bad news. At or
below 1.0 it has room — good news.

The repo already published exactly that. `web/help.py:571`:

> "TCPI **<= 1.0** means the remaining work can complete within budget at the current
> efficiency; **> 1.0 requires better-than-planned performance**."

…and the formula line reads `(pass <= 1.0 when cost-loaded)`. The engine scored the
opposite. Measured on the unfixed tree:

| programme | TCPI | reported |
| --- | --- | --- |
| 20% earned for half the budget — needs **1.6×** planned efficiency | 1.6 | **PASS** |
| 80% earned for a fifth of the budget — needs 0.25× | 0.25 | **FAIL** |

TCPI sits in `_DIM_AFFORDABILITY`, so the affordability dimension showed green precisely on
the programmes that could not afford to finish — the worst direction to be wrong in for a
figure quoted in testimony (Law 2).

**The number was always right.** The NASA metric library
(`00_REFERENCE_INTAKE/NASA Metrics_Complete_*.aft`) defines TCPI(BAC) as
`sum((BaselineCost-BCWPEV))/sum((BaselineCost-ACWPAC))`, which the engine matches and
`tests/engine/test_aft_formula_audit.py` already pinned as MATCH. Only the **verdict** was
wrong, so no parity value moves and `help.py` needed no edit — the fix makes the code obey
the documentation it already shipped.

## Decision

`_index()` takes an explicit `direction` argument, defaulting to `GE` (correct for SPI/CPI)
and **stated by the caller** for TCPI as `Direction.LE`. The default is deliberately kept so
the diff stays minimal, but the docstring now records that direction is *not* a shared
property of the family — that assumption is what produced the defect.

### Three oracles pinned the defect in place

`_EVM_SEEDS` in `tests/test_projects/test_pass_fail_battery.py` is documented as "the EXACT
set of status flips it must cause — **measured, then pinned**." It had been measured against
the inverted direction, so the fixture *encoded* the bug:

- `("cost_blowout", …, frozenset({"cpi"}))` — a blowout at CPI 0.54 was declared to flip
  *only* CPI;
- `assert blown["tcpi"].status is CheckStatus.PASS` — a fixture literally named `blown`,
  spending ~2× per unit of work, asserting its affordability index **passes**;
- `test_evm.py` — `assert e["tcpi"].status is CheckStatus.FAIL` on a TCPI of **0.5**.

All three are repointed in this commit with the reason recorded inline. This is the
**third** instance of the ADR-0385 stale-guard class (after M15 in ADR-0405 and the
`BLOCKED` pin): *a test that pins today's output is not a test of correctness, and when the
output is wrong the test becomes the defect's bodyguard.*

## Verification (QC-1)

- **Sandbox first.** The fix was applied to a PYTHONPATH shadow of `src/` and measured there
  **before the real tree was touched** (operator directive): TCPI 1.6 → FAIL, 0.25 → PASS,
  SPI/CPI unmoved. The blast radius was then measured in the shadow across all 26
  EVM-touching test files: exactly **4 failures / 430**, every one an oracle pinning the
  defect — no genuine regression anywhere.
- **Red first.** `test_tcpi_passes_low_and_fails_high_as_its_published_definition_states`
  and the repointed NA-case assertion failed **by name** on the unfixed engine; the
  blast-radius set is **432 passed** after.
- **Mutation battery 4/4 caught by the named tests** (shadow sandbox, import-origin canary,
  instruments md5-identical, pristine controls green both sides): M1 the original GE call ·
  M2 `_index` ignoring its direction when evaluating · M3 evaluating correctly but
  *reporting* GE in the result · M4 SPI flipped to LE — M4 exists so the
  neighbours-unchanged control is proved to have teeth rather than assumed to.
- **Four independent instruments** agree: the published `help.py` text, a live probe, the
  mutation battery, and the NASA `.aft` formula row (which confirms the value is unchanged).

## Deliberately NOT done

- **No `help.py` edit** — the documentation was already correct; the code was wrong.
- **No change to SPI/CPI** — measured as correct, and M4 guards the claim.
- **No new "inverted index" abstraction** — one caller states one direction; a framework
  here would hide the very assumption that caused the defect.
