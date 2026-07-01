"""Layer B — the verified ad-hoc derivation gate for Ask-the-AI Q&A.

When a local model writes a number that is NOT literally present in the engine's cited facts, this
module tries to **reconstruct** it deterministically from the sourced figures over a *closed
whitelist* of standard operations (percentage-of-population, ratio, percent-change, difference,
sum). If a reconstruction reproduces the figure, it is *verified-derived* — a standard combination
of engine figures, shown with its reconstruction — rather than an unsourced/invented number.

**Matching is precision-honest (QC audit 2026-07-01, D1/D23):** an INTEGER target must be
reproduced exactly (a count is exact — ``0.8 / 27 * 100 = 2.963`` does NOT verify an invented
``3``); a decimal target matches at one decimal place (the engine's own ratio display precision).
Operands are capped (:data:`_MAX_OPERANDS`, fact-order first) so the gate's cost is bounded.

This upgrades the annotate footer from *flag* to *verify-or-flag* and lets strict mode accept a
ratio-class reconstruction (see :func:`schedule_forensics.ai.qa.answer_question`). It is the
``docs/PLAN/AI-DERIVED-METRICS-SCOPE.md`` Layer B design and serves the operator's direction: the AI
may derive metrics from the engine's metrics, **but only by a standard operation, verified**.

**It verifies the arithmetic, not the meaning.** A reconstruction proves the number is a standard
combination of sourced figures; it cannot prove the relationship is *meaningful*. So the
reconstruction is always shown to the analyst, and ratio-class ops (far less prone to a coincidental
match than integer differences) are the only ones strict mode trusts.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

#: Ratios/percentages display precision (matches the engine + the Layer A contract rounding rule).
_DP = 1

#: Exact-match tolerance for integer targets (floating-point noise only, e.g. 12/24*100).
_EXACT_EPS = 1e-9

#: Most distinct operands considered, in fact order. Bounds the O(n^2) pair scans per figure so a
#: large workbook fact sheet cannot cost seconds per answer (QC audit D23); 64 comfortably exceeds
#: a real fact sheet's distinct-figure count.
_MAX_OPERANDS = 64

_INT_TOKEN_RE = re.compile(r"-?\d+$")

#: Ratio-class reconstructions are schedule-meaningful rates and far less prone to a coincidental
#: numeric match than additive ones; only these are trusted in strict mode (qa.answer_question).
RATIO_KINDS = frozenset({"percent_of", "ratio", "percent_change"})


@dataclass(frozen=True)
class Derivation:
    """A reconstruction of a figure from sourced figures via one whitelisted operation."""

    value: float
    kind: str  # "percent_of" | "ratio" | "percent_change" | "difference" | "sum"
    expression: str  # human-readable, e.g. "12 / 126 * 100 = 9.5"


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _matches(candidate: float, target: float, *, exact: bool) -> bool:
    if exact:
        return abs(candidate - target) < _EXACT_EPS
    return round(candidate, _DP) == round(target, _DP)


def verify_derivation(target_token: str, sourced: Sequence[float]) -> Derivation | None:
    """Reconstruct ``target_token`` from ``sourced`` figures via a standard operation, or ``None``.

    Tries each whitelisted binary operation over ordered pairs of distinct sourced figures and
    returns the **first match in priority order** (ratio-class first — the most schedule-meaningful
    and least coincidence-prone — then additive). Only the engine-sourced figures are operands; the
    model never supplies one. An integer token must be reproduced **exactly** (counts are exact —
    the 1-dp tolerance applies only to decimal ratio targets), so a near-miss can never be
    "verified" (QC audit D1). Returns ``None`` when the token is non-numeric or no reconstruction
    reproduces it.
    """
    try:
        target = float(target_token)
    except ValueError:
        return None
    exact = bool(_INT_TOKEN_RE.match(target_token.strip()))

    values: list[float] = []
    for v in sourced:
        if v not in values:
            values.append(v)
        if len(values) >= _MAX_OPERANDS:
            break

    # priority: percentage-of-population, percent-change, ratio (ratio-class), then difference, sum
    for a in values:
        for b in values:
            if a == b:
                continue
            if b != 0 and _matches(a / b * 100, target, exact=exact):
                return Derivation(
                    round(a / b * 100, _DP),
                    "percent_of",
                    f"{_fmt(a)} / {_fmt(b)} * 100 = {_fmt(round(a / b * 100, _DP))}",
                )
    for a in values:
        for b in values:
            if a == b or b == 0:
                continue
            if _matches((a - b) / b * 100, target, exact=exact):
                val = round((a - b) / b * 100, _DP)
                return Derivation(
                    val,
                    "percent_change",
                    f"({_fmt(a)} - {_fmt(b)}) / {_fmt(b)} * 100 = {_fmt(val)}",
                )
    for a in values:
        for b in values:
            if a == b or b == 0:
                continue
            if _matches(a / b, target, exact=exact):
                val = round(a / b, _DP)
                return Derivation(val, "ratio", f"{_fmt(a)} / {_fmt(b)} = {_fmt(val)}")
    # additive ops (offered for annotate transparency; NOT trusted by strict) — skip a 0 operand
    for a in values:
        for b in values:
            if a == b or a == 0 or b == 0:
                continue
            if _matches(a - b, target, exact=exact):
                return Derivation(a - b, "difference", f"{_fmt(a)} - {_fmt(b)} = {_fmt(a - b)}")
    seen_sum: set[frozenset[float]] = set()
    for a in values:
        for b in values:
            if a == b or a == 0 or b == 0:
                continue
            key = frozenset((a, b))
            if key in seen_sum:
                continue
            seen_sum.add(key)
            if _matches(a + b, target, exact=exact):
                return Derivation(a + b, "sum", f"{_fmt(a)} + {_fmt(b)} = {_fmt(a + b)}")
    return None
