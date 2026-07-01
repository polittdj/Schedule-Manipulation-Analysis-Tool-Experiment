"""Derived metrics — standard secondary figures computed deterministically from the engine's
already-computed *primary* metrics (never the AI).

Each function here is a **pure function of figures the engine already produced** (a count and its
population, the DCMA pass/fail tally), mapped to a named, sourced formula in
:mod:`schedule_forensics.web.help`. Because the engine — not a language model — computes them, a
derived metric is as trustworthy as any primary metric and cannot disagree with it. This is Layer A
of ``docs/PLAN/AI-DERIVED-METRICS-SCOPE.md``: the "derive per industry standard, verified" path
lives in tested code with a cited source, not in model prose.

Verification-contract rounding rule (scope §3.3): ratios/percentages round to **one decimal place**
(the engine's display precision); counts are exact.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

#: Display precision for derived ratios/percentages (the verification-contract rounding rule).
_RATIO_DP = 1


def _half_up(value: float) -> float:
    """Half-up at the contract's decimal places — the Fuse-side convention used everywhere the
    engine rounds a displayed rate (plain round() is banker's; QC audit D19)."""
    q = Decimal(1).scaleb(-_RATIO_DP)
    return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))


def population_share(count: int, population: int) -> float | None:
    """The share of a population a count represents, as a percentage to one decimal place.

    ``population_share(12, 126) == 9.5``. Returns ``None`` when the population is empty (no share is
    defined — never a fabricated ``0``). Source: standard ratio normalisation / the Acumen
    population-ratio metrics (see ``web/help.py`` → ``population_share``).
    """
    if population <= 0:
        return None
    return _half_up(count / population * 100)


def dcma_pass_rate(passed: int, failed: int) -> float | None:
    """Percentage of **applicable** DCMA-14 checks that pass, to one decimal place.

    The denominator is the applicable checks only — not-applicable checks are excluded (DCMA
    convention), so this is ``passed / (passed + failed) x 100``. Returns ``None`` when no check is
    applicable. Source: the DCMA 14-Point Assessment (see ``web/help.py`` → ``dcma_pass_rate``).
    """
    applicable = passed + failed
    if applicable <= 0:
        return None
    return _half_up(passed / applicable * 100)
