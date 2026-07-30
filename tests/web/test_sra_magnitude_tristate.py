"""The SRA magnitude parser: absent / valid / invalid must stay three things (ADR-0313, V1/V2, H3).

`_reconcile_magnitudes` could already tell *absent* (nothing typed) from *present*, but not
*present-and-valid* from *present-and-garbage* — it collapsed the third case onto "value 0, locked".
Absent is the signal to DERIVE the other magnitude, so collapsing them meant an unparseable entry
silently SUPPRESSED that derivation and substituted a zero the operator never entered.

The measured consequence, and the reason this is not merely cosmetic: with a valid `%` and a garbage
`days`, the additive/SSI model saw a 0-day impact while the legacy multiplicative model saw the real
uplift — one risk row whose two magnitudes describe two different events.

`tests/web/js/magnitude_cases.json` is shared with the node harness so the server and
`sra_risk.js` are pinned to ONE grammar. They previously had two.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schedule_forensics.web.app import (
    _MAGNITUDE_MAX_LEN,
    _parse_magnitude,
    _reconcile_magnitudes,
)

CASES = json.loads((Path(__file__).parent / "js" / "magnitude_cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['state']}:{c['input']!r}")
def test_the_shared_grammar_table_holds_on_the_server(case: dict[str, object]) -> None:
    """Every case in the table the node harness also reads. A case added here is exercised twice."""
    field = _parse_magnitude(str(case["input"]), label="Impact (working days)")
    state = case["state"]
    if state == "absent":
        assert field.is_absent, f"{case['input']!r} should be absent, got {field}"
        assert field.value is None and field.reason is None
    elif state == "valid":
        assert field.value == pytest.approx(case["value"]), case
        assert field.reason is None
    else:
        assert field.is_invalid, f"{case['input']!r} should be invalid, got {field}"
        assert field.value is None, "an invalid field must carry NO value, not a zero"


def test_an_invalid_reason_names_the_field_and_quotes_the_entry() -> None:
    """The reason is operator-facing, so it has to say which box and what was in it."""
    field = _parse_magnitude("5 days", label="Impact (working days)")
    assert field.reason is not None
    assert "Impact (working days)" in field.reason
    assert "5 days" in field.reason


def test_an_over_long_entry_is_rejected_by_length_not_by_overflow() -> None:
    """The length bound is what makes the overflow class unreachable without inventing a maximum
    number of days — a product decision ADR-0313 deliberately does not make."""
    field = _parse_magnitude("1" * (_MAGNITUDE_MAX_LEN + 1), label="Impact (%)")
    assert field.is_invalid and field.reason is not None
    assert "too long" in field.reason


# --- the three states, through the reconciler ---------------------------------------


def test_absent_still_derives_which_is_the_behaviour_being_protected() -> None:
    """The control case. 50 % of a 10-day average IS 5 days, and that derivation is the function's
    entire purpose — the bug was an invalid entry silently disabling it."""
    days, pct, dl, pl, problems = _reconcile_magnitudes("", "50", False, False, 10.0)
    assert (days, pct) == (5.0, 50.0)
    assert (dl, pl) == (False, True)
    assert problems == ()


def test_a_garbage_entry_no_longer_locks_a_zero_it_reports() -> None:
    days, pct, dl, _pl, problems = _reconcile_magnitudes("abc", "50", False, False, 10.0)
    assert problems, "an unparseable magnitude must be reported, not absorbed"
    assert dl is False, "the refused field must NOT be locked — locking pins the value we rejected"
    assert days == 0.0 and pct == 50.0  # the caller refuses on `problems`; it never stores these


def test_the_cross_model_disagreement_is_reported_in_both_directions() -> None:
    """Garbage in EITHER magnitude used to leave the two models describing different events."""
    for bad_days, bad_pct in (("abc", "50"), ("7", "abc")):
        *_, problems = _reconcile_magnitudes(bad_days, bad_pct, False, False, 10.0)
        assert problems, (bad_days, bad_pct)


def test_garbage_in_both_reports_both() -> None:
    *_, problems = _reconcile_magnitudes("abc", "xyz", False, False, 10.0)
    assert len(problems) == 2


def test_an_explicit_lock_flag_cannot_resurrect_an_invalid_field() -> None:
    """The hidden `*_locked` flag is client-supplied, so it must not be able to pin a value the
    server refused to read."""
    _days, _pct, dl, pl, problems = _reconcile_magnitudes("abc", "xyz", True, True, 10.0)
    assert problems
    assert (dl, pl) == (False, False)


def test_valid_input_is_unchanged_by_the_tri_state() -> None:
    """The regression bound: every previously-working combination behaves exactly as before."""
    assert _reconcile_magnitudes("3", "", False, False, 15.0)[:4] == (3.0, 20.0, True, False)
    assert _reconcile_magnitudes("", "10", False, False, 15.0)[:4] == (1.5, 10.0, False, True)
    assert _reconcile_magnitudes("1", "", False, False, 15.0)[:4] == (1.0, 6.67, True, False)
    assert _reconcile_magnitudes("", "", False, False, 15.0)[:4] == (0.0, 0.0, False, False)
    # no derivation basis: nothing is derived, and that is not an error
    assert _reconcile_magnitudes("3", "", False, False, 0.0) == (3.0, 0.0, True, False, ())
