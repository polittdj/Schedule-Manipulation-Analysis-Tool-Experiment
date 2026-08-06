"""The SSI grid reads the schedule's OWN stored SRA fields, and a stale setup announces
itself (ADR-0356).

Root-caused on the operator's 2026-08-06 SSI-vs-tool delta: the session could not read the
file's stored 'SRA Risk Ranking Factors' / Best-Worst fields at all, so a setup captured
against an earlier vintage of the schedule was the only way to fill the grid — and it
replayed 605 stale factors onto an edited file with no warning. The engine was exonerated by
a file-true re-run (sigma within 2.5% of SSI's occurrence-weighted histogram); the product
defect was the silent input divergence, fixed here twice over: a 'Load from schedule' seed
and a vintage warning on setup load.
"""

from __future__ import annotations

import datetime as dt
import json

from fastapi.testclient import TestClient

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import (
    SessionState,
    _file_stored_sra_inputs,
    _schedule_sra_fingerprint,
    create_app,
)

DAY = 480


def _t(uid: int, name: str, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=2 * DAY, **kw)  # type: ignore[arg-type]


def _sched_with_stored_fields() -> Schedule:
    """Four leaves: a factor+BCWC carrier, a factor-only, a completed carrier (excluded), and
    a BC-only row (excluded — the pair rule)."""
    return Schedule(
        name="s",
        source_file="s.mpp",
        project_start=dt.datetime(2027, 1, 4, 8),
        tasks=(
            _t(
                1,
                "carrier",
                custom_fields=(
                    ("SRA Risk Ranking Factors", "3"),
                    ("Best Case Duration", "PT8H0M0S"),
                    ("Worst Case Duration", "PT24H0M0S"),
                ),
            ),
            _t(2, "factor-only", custom_fields=(("SRA Risk Ranking Factors", "5"),)),
            _t(
                3,
                "completed",
                percent_complete=100.0,
                custom_fields=(
                    ("SRA Risk Ranking Factors", "4"),
                    ("Best Case Duration", "PT4H0M0S"),
                    ("Worst Case Duration", "PT12H0M0S"),
                ),
            ),
            _t(4, "bc-only", custom_fields=(("Best Case Duration", "PT4H0M0S"),)),
        ),
    )


def _client(sch: Schedule) -> tuple[TestClient, SessionState]:
    st = SessionState()
    st.schedules[sch.source_file] = sch
    return TestClient(create_app(st)), st


def test_file_stored_inputs_read_verbatim_with_the_adr_0307_exclusions() -> None:
    factors, bcwc = _file_stored_sra_inputs(_sched_with_stored_fields())
    assert factors == {1: 3, 2: 5}  # the completed carrier (uid 3) is excluded
    assert bcwc == {1: (480, 1440)}  # verbatim minutes; bc-only (uid 4) has no pair


def test_load_from_schedule_seeds_and_replaces_the_grid() -> None:
    client, st = _client(_sched_with_stored_fields())
    st.sra_factors = {99: 1}  # a stale entry the seed must replace, not merge
    st.sra_bcwc = {99: (1, 2)}
    r = client.post("/sra/load-from-schedule", follow_redirects=False)
    assert r.status_code == 303
    assert st.sra_factors == {1: 3, 2: 5}
    assert st.sra_bcwc == {1: (480, 1440)}
    assert st.sra_import_is_error is False
    assert "2 Risk Ranking Factor(s)" in (st.sra_import_msg or "")
    assert "1 Best/Worst Case pair(s)" in (st.sra_import_msg or "")


def test_load_from_schedule_reports_a_field_less_file() -> None:
    bare = Schedule(
        name="bare",
        source_file="bare.mpp",
        project_start=dt.datetime(2027, 1, 4, 8),
        tasks=(_t(1, "plain"),),
    )
    client, st = _client(bare)
    st.sra_factors = {7: 2}
    client.post("/sra/load-from-schedule", follow_redirects=False)
    assert st.sra_import_is_error is True
    assert "no stored SRA fields" in (st.sra_import_msg or "")
    assert st.sra_factors == {7: 2}  # nothing was replaced on the error path


def test_stale_setup_load_warns_with_counts_and_matching_load_does_not() -> None:
    """The vintage warning fires when the loaded values disagree with the file's stored
    fields — and stays silent on a like-for-like load (no noise on the honest path)."""
    client, st = _client(_sched_with_stored_fields())
    stale = {
        "setup_version": 4,
        "schedule_fingerprint": {
            "source_file": "old_vintage.mpp",
            "stored_sra_hash": "not-the-current-hash",
        },
        "factors": {"1": 5},  # file says uid 1 is factor 3; uid 2 (file factor 5) is absent
        "bcwc_minutes": {"1": [100, 200]},  # file stores (480, 1440)
        "risks": [],
    }
    client.post(
        "/sra/ssi/load",
        files=[("setup", ("s.json", json.dumps(stale).encode(), "application/json"))],
        follow_redirects=False,
    )
    msg = st.sra_import_msg or ""
    assert "CHECK INPUTS" in msg
    assert "different vintage" in msg and "old_vintage.mpp" in msg
    assert "1 factor(s) disagree" in msg
    assert "1 file factor task(s) are absent" in msg
    assert "1 Best/Worst pair(s) differ" in msg
    assert st.sra_import_is_error is True

    # a like-for-like setup (the file's own values) loads with no warning
    clean = {
        "setup_version": 4,
        "factors": {"1": 3, "2": 5},
        "bcwc_minutes": {"1": [480, 1440]},
        "risks": [],
    }
    client.post(
        "/sra/ssi/load",
        files=[("setup", ("c.json", json.dumps(clean).encode(), "application/json"))],
        follow_redirects=False,
    )
    assert st.sra_import_msg == "SSI setup loaded."


def test_saved_setup_carries_the_fingerprint() -> None:
    """The hash is pinned by its PROPERTIES, never by re-calling the same function (a mutated
    helper would agree with itself — the self-referential-oracle trap, caught by mutation)."""
    client, _st = _client(_sched_with_stored_fields())
    payload = json.loads(client.get("/sra/ssi/save").text)
    assert payload["setup_version"] == 4
    fp = payload["schedule_fingerprint"]
    assert fp["source_file"] == "s.mpp"
    assert fp["stored_factor_count"] == 2 and fp["stored_bcwc_count"] == 1
    h = fp["stored_sra_hash"]
    assert isinstance(h, str) and len(h) == 64
    int(h, 16)  # a real sha256 hex digest, not a placeholder
    # and it is a VINTAGE: one changed stored factor -> a different hash
    changed = _sched_with_stored_fields().model_copy(
        update={
            "tasks": (
                _t(
                    1,
                    "carrier",
                    custom_fields=(
                        ("SRA Risk Ranking Factors", "4"),  # was 3
                        ("Best Case Duration", "PT8H0M0S"),
                        ("Worst Case Duration", "PT24H0M0S"),
                    ),
                ),
                _t(2, "factor-only", custom_fields=(("SRA Risk Ranking Factors", "5"),)),
            )
        }
    )
    assert _schedule_sra_fingerprint(changed)["stored_sra_hash"] != h
