"""MC-07 (WP6b, ADR-0467), the web half: an SSI setup whose factor table does not cover 1..5 is
NOT restored — the session keeps the table it had, instead of a table the engine would refuse
(or, before the engine refused it, silently read as a zero Best Case).

Red-first (2026-09-06): the five-duplicate table replaced the session's rows.
"""

from __future__ import annotations

from schedule_forensics.web.ssi import _apply_ssi_setup
from schedule_forensics.web.state import SessionState

DEFAULT = ((1, 50.0, 10.0), (2, 40.0, 20.0), (3, 30.0, 30.0), (4, 20.0, 40.0), (5, 10.0, 50.0))


def test_a_setup_table_with_duplicate_factors_is_ignored() -> None:
    st = SessionState()
    assert st.sra_factor_rows == DEFAULT
    _apply_ssi_setup(st, {"factor_table": [[1, 50, 10]] * 5})
    assert st.sra_factor_rows == DEFAULT


def test_a_valid_custom_table_is_restored_and_clamped() -> None:
    st = SessionState()
    table = [[5, 10, 50], [4, 20, 40], [3, 30, 30], [2, 40, 20], [1, 150, 10]]
    _apply_ssi_setup(st, {"factor_table": table})
    assert dict((f, (s, a)) for f, s, a in st.sra_factor_rows) == {
        1: (100.0, 10.0),
        2: (40.0, 20.0),
        3: (30.0, 30.0),
        4: (20.0, 40.0),
        5: (10.0, 50.0),
    }
