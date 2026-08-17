"""The scoped-population contract: a page that renders a filter banner must not also render
figures computed on the RAW file (audit 2026-08-16, the three MIXED-POPULATION claims).

``SessionState.analysis_for`` computes over ``st.scope(sch)`` and hands the exact population back
as ``_Analysis.scoped`` — ADR-0263 added that field precisely so a caller pairs the analysis with
the population it was computed FROM. ``ordered_versions()``'s own docstring says its schedules are
UNSCOPED and that callers "hand the schedule to analysis_for (which scopes it)". Three surfaces
took the raw schedule and paired it with the scoped ``analysis.cpm`` anyway:

* ``/analysis`` — ``compute_activity_makeup(sch)`` in the "Where we stand" header, against a grid
  built from ``analysis.activity_rows``. Measured before the fix: one filtered page rendering
  ``<div class="stack-foot">9 activities</div>`` AND ``8 activities in the grid``.
* ``/ribbon`` — ``compute_ribbon`` / ``compute_schedule_quality`` / ``ribbon_offender_map`` all
  took the raw ``sch``. Measured: "Missing logic: 2 / Logic wired 7" **identically** with and
  without a reduce filter; the honest scoped figure is 5 of 8.
* ``/export/{fmt}/analysis`` — ``compute_schedule_quality(sch, analysis.cpm)``: raw tasks scored
  against a CPM solved on a different task set (2 of 9 where the page's own population gives 5
  of 8).

The oracle here is DIFFERENTIAL and the control is load-bearing: a figure that is genuinely
scoped MOVES when the filter moves. ``st.scope()`` returns the schedule unchanged when nothing
narrows, so every assertion below is identical to pre-fix behaviour in the unfiltered case —
which is what the unfiltered controls pin.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)
KEY = "house"

#: the example has 9 activities, exactly one of which is a milestone, so an
#: "Activity Type: Normal" reduce filter narrows the population 9 -> 8 and — because the
#: milestone carried logic — moves the missing-logic count 2 -> 5. A filter that changed
#: nothing would make every assertion below vacuous, so the fixture asserts the narrowing.
_RAW_TASKS = 9
_SCOPED_TASKS = 8


@pytest.fixture
def st() -> SessionState:
    state = SessionState()
    state.schedules[KEY] = parse_json_text(EXAMPLE.read_text(encoding="utf-8"))
    return state


@pytest.fixture
def client(st: SessionState) -> TestClient:
    return TestClient(create_app(st))


def _filter(st: SessionState) -> None:
    st.set_filter([("Activity Type", "Normal")])
    st.set_filter_mode("reduce")


def test_the_filter_actually_narrows_this_fixture(st: SessionState) -> None:
    """Guard the guard: every test below is vacuous if the filter does not bite."""
    raw = st.schedules[KEY]
    assert len(raw.tasks) == _RAW_TASKS
    assert st.scope(raw) is raw, "unfiltered scope() must be the identity"
    _filter(st)
    assert len(st.scope(raw).tasks) == _SCOPED_TASKS
    before = compute_schedule_quality(raw, st.analysis_for(KEY, raw).cpm)["missing_logic"]
    after_pop = st.analysis_for(KEY, raw).scoped
    after = compute_schedule_quality(after_pop, st.analysis_for(KEY, raw).cpm)["missing_logic"]
    assert (before.count, before.population) == (2, 9)
    assert (after.count, after.population) == (5, 8), "the two populations must differ visibly"


def _activity_counts(page: str) -> set[int]:
    """Every "<n> activities" the page states about ITS OWN population.

    The explainer prose quotes a worked example ("10 of 600 activities (1.7%)") and findings
    titles count offenders ("2 activities baselined-due are not complete") — neither is a claim
    about this file's population, so both are excluded structurally rather than by value.
    """
    stripped = re.sub(r"<p><b>Pass example:</b>.*?</p>", "", page, flags=re.S)
    stripped = re.sub(r"Pass example:.*?FAIL", "", stripped, flags=re.S)
    out = set()
    for m in re.finditer(r'class="stack-foot">(\d+) activities<', stripped):
        out.add(int(m.group(1)))
    for m in re.finditer(r"(\d+) activities in the grid", stripped):
        out.add(int(m.group(1)))
    return out


def test_analysis_header_and_grid_state_one_population(
    st: SessionState, client: TestClient
) -> None:
    """ANALYSIS-HEADER-MIXED-POPULATION: the header's activity makeup and the activity grid are
    two views of ONE population and must never disagree on its size."""
    unfiltered = _activity_counts(client.get(f"/analysis/{KEY}").text)
    assert unfiltered == {_RAW_TASKS}, f"unfiltered control drifted: {unfiltered}"

    _filter(st)
    filtered = _activity_counts(client.get(f"/analysis/{KEY}").text)
    assert filtered == {_SCOPED_TASKS}, (
        f"the filtered page states {sorted(filtered)} activities — the header is counting the "
        "raw file while the grid counts the scoped population"
    )


def test_api_analysis_task_count_matches_its_own_activity_rows(
    st: SessionState, client: TestClient
) -> None:
    """The JSON payload carries both numbers, so a mismatch ships to any consumer of the API."""
    body = client.get(f"/api/analysis/{KEY}").json()
    assert body["tasks"] == _RAW_TASKS
    assert body["tasks"] == len(body["activities"])

    _filter(st)
    body = client.get(f"/api/analysis/{KEY}").json()
    assert len(body["activities"]) == _SCOPED_TASKS  # the grid follows the scope
    assert body["tasks"] == len(body["activities"]), (
        f"'tasks'={body['tasks']} but the payload carries {len(body['activities'])} activities"
    )


def test_ribbon_quality_follows_the_active_filter(st: SessionState, client: TestClient) -> None:
    """RIBBON-MIXED-POPULATION: the ribbon scored the raw file, so its figures did not move at
    all under a reduce filter — while the page chrome told the operator one was active."""
    before = client.get("/ribbon").text
    assert "Missing logic: 2" in before, "unfiltered control"
    assert "Logic wired <b>7</b>" in before

    _filter(st)
    after = client.get("/ribbon").text
    assert "Missing logic: 5" in after, (
        "the ribbon still scores the unfiltered file — its missing-logic count did not move"
    )
    assert "Logic wired <b>3</b>" in after


def _quality_row(book: bytes, metric: str) -> tuple[int, int]:
    """(count, population) for one row of the workbook's real "Schedule quality" sheet.

    Reads the SHIPPED bytes, not a re-derivation: an assertion re-running the engine the way the
    route SHOULD have would pass against the broken route (it did, on the first draft of this
    module — a test that could not fail).
    """
    with zipfile.ZipFile(io.BytesIO(book)) as z:
        names = re.findall(
            r'<sheet name="([^"]+)"[^>]*r:id="rId(\d+)"', z.read("xl/workbook.xml").decode()
        )
        sheet = next(idx for name, idx in names if name == "Schedule quality")
        xml = z.read(f"xl/worksheets/sheet{sheet}.xml").decode()
    row = next(r for r in re.findall(r"<row .*?</row>", xml, re.S) if f"<t>{metric}</t>" in r)
    numbers = [int(v) for v in re.findall(r"<v>(-?\d+)</v>", row)]
    return numbers[0], numbers[1]  # Count, Population


def test_analysis_export_quality_uses_the_scoped_population(
    st: SessionState, client: TestClient
) -> None:
    """ANALYSIS-EXPORT-QUALITY-UNSCOPED: an exported workbook leaves the tool and gets quoted,
    so it must state the same population the screen does. Asserted on the workbook's own cells."""
    unfiltered = client.get(f"/export/xlsx/analysis/{KEY}")
    assert unfiltered.status_code == 200
    assert _quality_row(unfiltered.content, "Missing Logic") == (2, _RAW_TASKS)

    _filter(st)
    filtered = client.get(f"/export/xlsx/analysis/{KEY}")
    assert filtered.status_code == 200
    assert _quality_row(filtered.content, "Missing Logic") == (5, _SCOPED_TASKS), (
        "the workbook scored the raw file against a CPM solved on the scoped one"
    )


# --- the standing computed guard -------------------------------------------------------------
#
# The three ledger rows were three instances of a CLASS. A computed census over the view layer
# found the same shape in five more route functions (schedule_card, standards_view,
# _schedule_facts — which builds the AI's citable fact sheet — export_ribbon and
# export_ribbon_drill). A hand-maintained list of call sites is a stale list waiting to happen,
# so the contract is enforced by re-deriving the census, not by naming the sites.


def _mixed_population_sites() -> list[tuple[str, str, int, str]]:
    """Every place a view function pairs a scoped ``_Analysis`` with the RAW schedule.

    Shape: inside ONE function, a name bound from ``st.analysis_for(..., sch)`` is passed (or one
    of its analysis attributes is) to a call that ALSO receives the raw schedule argument handed
    to ``analysis_for``. Attribution is to the INNERMOST enclosing function: ``create_app``
    lexically contains every route, so walking it whole unions bindings and uses from unrelated
    routes and manufactures false positives.
    """
    import ast

    web = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web"
    attrs = {
        "cpm",
        "audit",
        "compliance",
        "float_bands",
        "completion",
        "findings",
        "narrative",
        "activity_rows",
    }
    hits: list[tuple[str, str, int, str]] = []

    def own_nodes(fn: ast.AST) -> list[ast.AST]:
        """Nodes belonging to ``fn`` itself — not to a function nested inside it."""
        out: list[ast.AST] = []
        stack = list(ast.iter_child_nodes(fn))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            out.append(node)
            stack.extend(ast.iter_child_nodes(node))
        return out

    for path in sorted(web.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]:
            body = own_nodes(fn)
            pairs: dict[str, str] = {}
            for n in body:
                if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)):
                    continue
                f = n.value.func
                if not (isinstance(f, ast.Attribute) and f.attr == "analysis_for"):
                    continue
                if n.value.args and isinstance(n.value.args[-1], ast.Name):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            pairs[t.id] = n.value.args[-1].id
            if not pairs:
                continue
            for call in [c for c in body if isinstance(c, ast.Call)]:
                args = list(call.args) + [k.value for k in call.keywords]
                raw = {a.id for a in args if isinstance(a, ast.Name) and a.id in pairs.values()}
                scoped = {
                    f"{a.value.id}.{a.attr}"
                    for a in args
                    if isinstance(a, ast.Attribute)
                    and a.attr in attrs
                    and isinstance(a.value, ast.Name)
                    and a.value.id in pairs
                } | {a.id for a in args if isinstance(a, ast.Name) and a.id in pairs}
                if raw and scoped:
                    called = getattr(call.func, "id", getattr(call.func, "attr", "?"))
                    hits.append((path.name, fn.name, call.lineno, called))
    return sorted(hits)


def test_no_view_pairs_a_scoped_analysis_with_a_raw_population() -> None:
    """A scoped CPM scoring an unscoped task set is incoherent: tasks the CPM never saw are
    graded by it, and the page states two population sizes at once. The census must stay empty."""
    sites = _mixed_population_sites()
    assert sites == [], "mixed-population call sites reintroduced:\n" + "\n".join(
        f"  {f}::{fn} L{ln} -> {called}(raw schedule + scoped analysis)"
        for f, fn, ln, called in sites
    )


def test_the_mixed_population_census_can_actually_see_a_violation() -> None:
    """Prove the guard has teeth (it currently reports zero, which is also what a broken census
    reports). Re-run the same detector over a synthetic module carrying one known violation."""
    import ast

    source = """
def route(st, name, sch):
    analysis = st.analysis_for(name, sch)
    return render(sch, analysis.cpm)
"""
    tree = ast.parse(source)
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    pairs, found = {}, []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
            f = n.value.func
            if isinstance(f, ast.Attribute) and f.attr == "analysis_for":
                pairs[n.targets[0].id] = n.value.args[-1].id  # type: ignore[attr-defined]
    for call in [c for c in ast.walk(fn) if isinstance(c, ast.Call)]:
        args = list(call.args)
        raw = {a.id for a in args if isinstance(a, ast.Name) and a.id in pairs.values()}
        scoped = {
            a.attr
            for a in args
            if isinstance(a, ast.Attribute)
            and isinstance(a.value, ast.Name)
            and a.value.id in pairs
        }
        if raw and scoped:
            found.append(call.lineno)
    assert found, "the detector cannot see a violation it is pointed straight at"
