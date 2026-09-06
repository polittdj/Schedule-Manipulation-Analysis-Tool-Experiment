"""MF-03 / MF-04 (WP6b, ADR-0467): a published formula describes the basis the code uses.

``critical`` is scored on the source tool's STORED Critical flag (pure-logic float only where no
flag is stored — ``_common.is_effective_critical``), but the dictionary said
``count(total_float <= 0 and incomplete)``; the ribbon's lag / lead counters count DISTINCT
successor ACTIVITIES (the Fuse activity scope, QC audit D22 fixed the DCMA twins) while their
formulas said ``count(lag > 0) / activities``. ``negative_float`` already stated its stored basis
(ADR-0430) — the guard here holds on both trees. ``cei_critical`` reads NA on a file whose source
wrote no Critical flag (a P6 XER) — its definition now says so (MF-06, measured: the finder's
proposed ``is_effective_critical`` basis would exclude every completed activity and empty the
numerator).

Red-first (2026-09-06): the four amended entries lacked the words their code implements.
"""

from __future__ import annotations

from schedule_forensics.web.help import METRIC_DICTIONARY as D


def test_critical_names_the_stored_flag_basis() -> None:
    assert "flag" in D["critical"].formula.lower(), D["critical"].formula


def test_lag_and_lead_counters_say_distinct_successor_activities() -> None:
    for key in ("number_of_lags", "number_of_leads"):
        formula = D[key].formula.lower()
        assert "distinct" in formula and "successor" in formula, (key, D[key].formula)


def test_negative_float_already_states_the_stored_basis() -> None:
    assert "stored" in D["negative_float"].formula.lower()


def test_critical_cei_discloses_na_without_a_stored_flag() -> None:
    text = (D["cei_critical"].definition + " " + D["cei_critical"].formula).lower()
    assert "flag" in text and ("n/a" in text or "not applicable" in text), text
