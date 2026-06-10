"""W5 regression guard: the JSON and driving views reuse the report's cached analysis.

A report used to re-solve the CPM 5+ times — the server render, the JSON the page fetches, and
the driving view each re-ran the whole analysis, because the web layer never passed the
precomputed CPM down. The session now computes one _Analysis per schedule and reuses it, so the
extra views add zero further network solves. (The page itself legitimately solves the network a
few times — the DCMA-14 critical-path test perturbs the network and re-solves on purpose; what
must not happen is each *view* repeating that whole set.)"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.narrative as narrative_mod
import schedule_forensics.engine.cpm as cpm_mod
import schedule_forensics.engine.driving_slack as driving_mod
import schedule_forensics.engine.float_analysis as float_mod
import schedule_forensics.engine.manipulation as manip_mod
import schedule_forensics.engine.metrics.change_metrics as change_mod
import schedule_forensics.engine.metrics.dcma14 as dcma_mod
import schedule_forensics.engine.metrics.schedule_quality as quality_mod
import schedule_forensics.engine.recommendations as rec_mod
import schedule_forensics.web.app as app_mod
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)

# every module that holds a bound `compute_cpm` reference — patch them all so the count is
# honest no matter which call site fires.
_CPM_HOLDERS = (
    cpm_mod,
    app_mod,
    rec_mod,
    manip_mod,
    narrative_mod,
    driving_mod,
    float_mod,
    dcma_mod,
    change_mod,
    quality_mod,
)


def test_one_cpm_per_schedule_across_page_json_and_driving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    real = cpm_mod.compute_cpm

    def counting(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return real(*args, **kwargs)

    for mod in _CPM_HOLDERS:
        if getattr(mod, "compute_cpm", None) is not None:
            monkeypatch.setattr(mod, "compute_cpm", counting)

    client = TestClient(create_app(SessionState()))
    client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,  # don't let the single-file 303 build the cache before we count
    )

    calls["n"] = 0
    assert client.get("/analysis/plan").status_code == 200  # builds & caches the analysis
    after_page = calls["n"]
    assert after_page >= 1  # the report did solve the network (sanity)

    # the JSON the page fetches and the Gantt driving trace must reuse the cached analysis —
    # the W5 bug was each of these re-running the whole analysis (another full set of solves).
    assert client.get("/api/analysis/plan").status_code == 200
    assert client.get("/api/driving/plan?target=9").status_code == 200
    assert calls["n"] == after_page  # zero additional network solves across the extra views
