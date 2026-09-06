"""RC-02 (WP7, ADR-0469): the fifteen POST routes and six exports the route-coverage instrument
found reached but NEVER ADVERSELY — no test had ever driven a 4xx/5xx or an empty-state 2xx
through them (``tools/route_coverage.py``; ADR-0455's census, re-derived by ADR-0467).

Each route is driven with the inputs a form can actually carry — an empty session, an unknown
key or UID, a value outside its range, ``nan``/``inf`` (``float()`` parses both), a double sign,
a superscript digit, a host-bearing redirect target — and the honest outcome is pinned: a LOCAL
redirect with the session state unchanged (the routes are fail-soft by contract), a clamped
value where the contract clamps, a named refusal where the contract refuses, and never a 500.

Two of the twenty-one were defects, observed RED here before the fix:

* ``POST /sra/branch`` parsed its endpoints as ``int(x) if _decimal_digits(x.lstrip("-"))`` —
  the lstrip-then-int pattern ``/sra/conditional``'s own comment (audit L5) says it replaced;
  ``--5`` passed the guard and ``int("--5")`` answered 500.
* ``POST /sra/jcl-config`` stored ``float(target_cost)`` under a bare ``suppress(ValueError)``,
  so ``nan`` / ``inf`` / ``1e999`` became the JCL cost target — the one route that bypassed the
  audit-L2 boundary rule ``_to_float`` enforces everywhere else.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
HOSTILE_TARGETS = ("//evil.example", "https://evil.example/x", "javascript:alert(1)", "")


@pytest.fixture
def empty() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


@pytest.fixture
def loaded() -> Iterator[tuple[SessionState, TestClient, str, int, int]]:
    """Project5 loaded; the key, one real non-summary active UID, and a second distinct one."""
    st = SessionState()
    client = TestClient(create_app(st))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    assert (
        client.post(
            "/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}
        ).status_code
        == 200
    )
    (key,) = list(st.schedules)
    real = [t.unique_id for t in st.schedules[key].tasks if not t.is_summary and t.is_active]
    assert len(real) >= 2
    yield st, client, key, real[0], real[1]


def _post(client: TestClient, path: str, form: dict[str, str]) -> str:
    """POST a form; the route must answer a LOCAL 303 (never a 5xx); returns the location."""
    resp = client.post(path, data=form, follow_redirects=False)
    assert resp.status_code == 303, (path, form, resp.status_code, resp.text[:200])
    location = resp.headers["location"]
    assert location.startswith("/") and not location.startswith("//"), (path, location)
    return location


# ── the fifteen POSTs on an EMPTY session: local redirect, nothing stored ──────────────────

EMPTY_SESSION_CASES: tuple[tuple[str, dict[str, str], str, Callable[[SessionState], bool]], ...] = (
    (
        "/dcma/scope",
        {"parity": "", "next": "/analysis"},
        "/analysis",
        lambda st: st.dcma_acumen_parity is False,
    ),
    (
        "/fields/roles",
        {"wbs": "NoSuchField", "cost_account": "Text9"},
        "/groups",
        lambda st: st.field_roles == {},
    ),
    (
        "/margin/band",
        {
            "phase0": "2026-01-01",
            "phase1": "not-a-date",
            "low0": "nan",
            "high0": "inf",
            "watch_pct": "nan",
        },
        "/margin",
        lambda st: st.margin_band_dates is None,
    ),
    (
        "/margin/confirm",
        {"key": "no-such-file", "uid": "12", "back": "https://evil.example"},
        "/analysis/no-such-file",
        lambda st: st.margin_overlay == {},
    ),
    (
        "/project/combine",
        {"pids": "only-one", "title": "Combined"},
        "/portfolio",
        lambda st: st.active_project is None,
    ),
    (
        "/project/exclude",
        {"key": "no-such-file", "excluded": "1"},
        "/portfolio",
        lambda st: not st.excluded_keys,
    ),
    (
        "/project/select",
        {"pid": "no-such-pid", "next_url": "/mission"},
        "/mission",
        lambda st: st.active_project is None,
    ),
    (
        "/sra/auto-calc",
        {"scope": "selected", "uids": "abc, --5, 12"},
        "/sra",
        lambda st: st.sra_bcwc == {},
    ),
    (
        "/sra/branch",
        {"action": "add", "name": "B", "after_uid": "1", "before_uid": "2", "prob": "50"},
        "/sra",
        lambda st: st.sra_branches == [],
    ),
    (
        "/sra/conditional",
        {
            "action": "add",
            "name": "C",
            "monitor_uid": "1",
            "metric": "duration",
            "threshold": "5",
            "a_after": "1",
            "a_before": "2",
            "b_after": "3",
            "b_before": "4",
        },
        "/sra",
        lambda st: st.sra_conditionals == [],
    ),
    (
        "/sra/correlation-matrix",
        {"action": "add-pair", "uid_a": "1", "uid_b": "2", "rho": "0.5"},
        "/sra",
        lambda st: st.sra_corr_pairs == (),
    ),
    (
        "/sra/jcl-config",
        {"target_date": "not-a-date", "target_cost": "abc", "confidence": "500", "td_share": "-5"},
        "/sra",
        lambda st: (
            st.jcl_target_date is None
            and st.jcl_target_cost is None
            and st.jcl_confidence == 0.95
            and st.jcl_td_share == 0.0
        ),
    ),
    (
        "/sra/load-from-schedule",
        {},
        "/sra",
        lambda st: (
            st.sra_import_is_error is True and "Load a schedule" in (st.sra_import_msg or "")
        ),
    ),
    (
        "/sra/risk",
        {"low": "abc", "ml": "nan", "high": "999", "uid": "x", "opt_days": "inf"},
        "/sra",
        lambda st: st.sra_high == 3.0 and st.sra_overrides == {},
    ),
    (
        "/sra/risk-register",
        {"action": "add", "name": "R", "prob": "150", "affected": "1, 2", "impact_days": "5"},
        "/sra",
        lambda st: st.sra_risks == [],
    ),
)


@pytest.mark.parametrize(
    "path,form,location,unchanged", EMPTY_SESSION_CASES, ids=[c[0] for c in EMPTY_SESSION_CASES]
)
def test_each_never_adverse_post_answers_a_local_redirect_on_an_empty_session(
    empty: tuple[SessionState, TestClient],
    path: str,
    form: dict[str, str],
    location: str,
    unchanged: Callable[[SessionState], bool],
) -> None:
    st, client = empty
    assert _post(client, path, form) == location
    assert unchanged(st), path


# ── redirect targets: a host-bearing value is refused for the app's own default ────────────

REDIRECT_CASES = (
    ("/dcma/scope", "next", "/"),
    ("/project/select", "next_url", "/"),
    ("/fields/roles", "next_url", "/groups"),
)


@pytest.mark.parametrize("path,field,default", REDIRECT_CASES, ids=[c[0] for c in REDIRECT_CASES])
@pytest.mark.parametrize("target", HOSTILE_TARGETS)
def test_a_host_bearing_redirect_target_is_refused(
    empty: tuple[SessionState, TestClient], path: str, field: str, default: str, target: str
) -> None:
    _st, client = empty
    assert _post(client, path, {field: target}) == default


def test_margin_confirm_refuses_a_back_target_outside_analysis(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, key, uid, _other = loaded
    for back in (*HOSTILE_TARGETS, "/mission"):
        assert _post(
            client, "/margin/confirm", {"key": key, "uid": str(uid), "back": back}
        ).startswith("/analysis/")
    assert st.margin_overlay[key] == frozenset({uid})


# ── the two defects: a double sign that 500'd, a non-finite cost target that was stored ─────


@pytest.mark.parametrize("bad", ["--5", "-", "²", "5.0", "abc", ""])
def test_sra_branch_refuses_an_unparseable_endpoint_without_a_500(loaded, bad: str) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, uid, _other = loaded
    form = {
        "action": "add",
        "name": "B",
        "after_uid": bad,
        "before_uid": str(uid),
        "prob": "50",
        "ml": "3",
    }
    assert _post(client, "/sra/branch", form) == "/sra"
    assert st.sra_branches == []


def test_sra_branch_still_adds_a_real_pair_and_refuses_a_self_tie(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, a, b = loaded
    _post(
        client,
        "/sra/branch",
        {
            "action": "add",
            "name": "B",
            "after_uid": str(a),
            "before_uid": str(a),
            "prob": "50",
            "ml": "3",
        },
    )
    assert st.sra_branches == []
    _post(
        client,
        "/sra/branch",
        {
            "action": "add",
            "name": "B",
            "after_uid": str(a),
            "before_uid": str(b),
            "prob": "150",
            "ml": "3",
        },
    )
    assert len(st.sra_branches) == 1 and st.sra_branches[0].probability == 1.0


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "1e999"])
def test_jcl_config_refuses_a_non_finite_cost_target(
    empty: tuple[SessionState, TestClient], raw: str
) -> None:
    st, client = empty
    _post(client, "/sra/jcl-config", {"target_cost": "1500"})
    assert st.jcl_target_cost == 1500.0
    _post(client, "/sra/jcl-config", {"target_cost": raw})
    assert st.jcl_target_cost == 1500.0, raw  # kept — never a non-finite target


def test_jcl_config_blank_cost_clears_and_bounds_hold(
    empty: tuple[SessionState, TestClient],
) -> None:
    st, client = empty
    _post(
        client,
        "/sra/jcl-config",
        {"target_cost": "1500", "cost_low": "5", "cost_high": "900", "confidence": "1"},
    )
    assert st.jcl_target_cost == 1500.0 and st.jcl_cost_low == 0.1 and st.jcl_cost_high == 3.0
    assert st.jcl_confidence == 0.10
    _post(client, "/sra/jcl-config", {"target_cost": ""})
    assert st.jcl_target_cost is None


# ── clamps and refusals on a LOADED session ───────────────────────────────────────────────


def test_sra_risk_clamps_the_globals_and_ignores_an_unknown_override(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, uid, _other = loaded
    _post(
        client,
        "/sra/risk",
        {"low": "0", "ml": "abc", "high": "999", "uid": "999999", "opt_days": "1"},
    )
    assert (st.sra_low, st.sra_high) == (0.05, 3.0) and st.sra_overrides == {}
    for bad in ({"opt_days": "nan", "ml_days": "inf"}, {"opt_days": "abc"}, {"pess_days": "-3"}):
        _post(client, "/sra/risk", {"uid": str(uid)} | bad)
        assert st.sra_overrides == {}  # never a (0, 0, 0) point mass from garbage
        assert st.sra_import_is_error is True and "not stored" in (st.sra_import_msg or "")
    _post(client, "/sra/risk", {"uid": str(uid), "opt_days": "3", "ml_days": "1", "pess_days": "2"})
    o, m, p = st.sra_overrides[uid]
    assert o <= m <= p  # order-coerced, never a negative spread


def test_sra_risk_register_drops_unknown_uids_and_clamps_probability_and_consequence(
    loaded,
) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, uid, _other = loaded
    _post(
        client,
        "/sra/risk-register",
        {"action": "add", "name": "R", "prob": "50", "affected": "999999", "impact_days": "5"},
    )
    assert st.sra_risks == []
    _post(
        client,
        "/sra/risk-register",
        {
            "action": "add",
            "name": "R",
            "prob": "150",
            "affected": f"{uid}, 999999",
            "impact_days": "5",
            "consequence": "9",
        },
    )
    (risk,) = st.sra_risks
    assert risk.probability == 1.0 and risk.affected == (uid,) and risk.consequence_rating == 5
    _post(
        client,
        "/sra/risk-register",
        {"action": "add", "name": "R2", "prob": "50", "affected": str(uid), "impact_days": "nan"},
    )
    assert len(st.sra_risks) == 1 and st.sra_import_is_error is True  # refused by name (ADR-0313)


def test_sra_correlation_matrix_refuses_a_self_pair_and_clamps_rho(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, a, b = loaded
    _post(
        client,
        "/sra/correlation-matrix",
        {"action": "add-pair", "uid_a": str(a), "uid_b": str(a), "rho": "0.5"},
    )
    assert st.sra_corr_pairs == ()
    _post(
        client,
        "/sra/correlation-matrix",
        {"action": "add-pair", "uid_a": str(a), "uid_b": str(b), "rho": "5"},
    )
    assert st.sra_corr_pairs == ((a, b, 1.0),)
    _post(
        client,
        "/sra/correlation-matrix",
        {"action": "add-group", "uids": f"{a}, abc", "group_rho": "0.3"},
    )
    assert st.sra_corr_groups == ()  # a group needs two valid members


def test_sra_conditional_refuses_an_unknown_metric_or_trip_rule(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, a, b = loaded
    base = {
        "action": "add",
        "name": "C",
        "monitor_uid": str(a),
        "threshold": "5",
        "a_after": str(a),
        "a_before": str(b),
        "b_after": str(a),
        "b_before": str(b),
    }
    _post(client, "/sra/conditional", base | {"metric": "bogus"})
    _post(client, "/sra/conditional", base | {"trip_when": "sideways"})
    _post(client, "/sra/conditional", base | {"monitor_uid": "--5"})
    assert st.sra_conditionals == []


def test_margin_band_keeps_the_current_values_on_invalid_pieces(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key, _uid, _other = loaded
    rates, pcts = st.margin_band_rates, st.margin_risk_pcts
    _post(
        client,
        "/margin/band",
        {
            "phase0": "2026-01-01",
            "phase1": "2025-01-01",
            "phase2": "2027-01-01",
            "phase3": "2028-01-01",
            "low0": "nan",
            "high0": "5",
            "low1": "1",
            "high1": "2",
            "low2": "1",
            "high2": "inf",
            "watch_pct": "5",
            "ca_pct": "50",
        },
    )
    assert (
        st.margin_band_dates is None
        and st.margin_band_rates == rates
        and st.margin_risk_pcts == pcts
    )


def test_project_routes_ignore_unknown_ids_on_a_loaded_session(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, key, _uid, _other = loaded
    active = st.active_project
    _post(client, "/project/select", {"pid": "no-such-pid", "next_url": "/mission"})
    _post(client, "/project/exclude", {"key": "no-such-file", "excluded": "1"})
    _post(client, "/project/combine", {"pids": "no-such-pid", "title": "X"})
    assert st.active_project == active and not st.excluded_keys
    _post(client, "/project/exclude", {"key": key, "excluded": "1"})
    assert st.excluded_keys == {key}
    _post(client, "/project/exclude", {"key": key, "excluded": "0"})
    assert not st.excluded_keys


# ── the six exports on an EMPTY session and with a bad format ─────────────────────────────

EXPORTS = ("evm", "scurve", "risks", "mission", "ribbon", "workbench")


@pytest.mark.parametrize("name", EXPORTS)
@pytest.mark.parametrize("fmt", ["xlsx", "docx"])
def test_each_never_adverse_export_refuses_or_discloses_an_empty_session(
    empty: tuple[SessionState, TestClient], name: str, fmt: str
) -> None:
    _st, client = empty
    resp = client.get(f"/export/{fmt}/{name}")
    if name == "mission":
        # ADR-0268: a valid workbook whose one row says why the wall's series are empty
        assert resp.status_code == 200 and resp.content[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            text = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
        assert b"load another analyzable version of the active project" in text
    else:
        assert resp.status_code in (400, 422), (name, resp.status_code)
        assert "load" in resp.json()["error"].lower()


@pytest.mark.parametrize("name", EXPORTS)
def test_each_export_refuses_an_unknown_format(
    empty: tuple[SessionState, TestClient], name: str
) -> None:
    _st, client = empty
    assert client.get(f"/export/exe/{name}").status_code == 404
