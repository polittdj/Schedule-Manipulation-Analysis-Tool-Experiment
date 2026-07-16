"""The MPXJ saved-views sidecar (feature #10 ingest): parser, .mpp wiring, and the
MPXJ-oracle parity gate.

The sidecar parser and the ``parse_mpp`` attachment are covered without a JVM by faking
the converter subprocess (the same idiom as ``test_mpp_mpxj.py``). The real-file tests
convert the operator's committed ``Large Test File Leveled.mpp`` and — the point of the
whole feature — pin our evaluator's match sets to MPXJ's own ``Filter.evaluate()``
output (``MpxjToMspdi --eval``), so "faithful reproduction" is proven against the
reference implementation, not assumed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404  # test-only: runs the vendored MPXJ oracle (no shell)
import types
from pathlib import Path

import pytest

from schedule_forensics.engine.msp_filters import required_prompts, select
from schedule_forensics.engine.saved_grouping import group_by_clauses
from schedule_forensics.importers import ImporterError, mpp_mpxj, parse_mpp
from schedule_forensics.importers.msp_views import parse_views_json_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
LEVELED = REPO / "00_REFERENCE_INTAKE" / "mpp" / "Large Test File Leveled.mpp"

needs_java = pytest.mark.skipif(
    shutil.which("java") is None,
    reason="Java runtime not available in this environment",
)
needs_leveled = pytest.mark.skipif(
    not LEVELED.is_file(),
    reason="Large Test File Leveled.mpp not present",
)

#: The 10 saved task filters in the reference file — the feature-#10 reproduction target.
LEVELED_FILTER_NAMES = (
    "All Tasks",
    "All Resources",
    "SVT-",
    "No SVT-",
    "SVT",
    "Date Range...",
    "CAM_Tasks",
    "_MCexportedTasks",
    "_MCTasks",
    "_RiskRegTasks",
)

# --- sidecar parser (no JVM) -------------------------------------------------------


_SIDECAR = json.dumps(
    {
        "filters": [
            {"name": "All Tasks", "isTaskFilter": True, "criteria": None},
            {
                "name": "Late + prompt",
                "isTaskFilter": True,
                "showRelatedSummaryRows": True,
                "promptCount": 1,
                "criteria": {
                    "op": "AND",
                    "children": [
                        {
                            "op": "IS_GREATER_THAN",
                            "field": "Duration9",
                            "fieldEnum": "DURATION9",
                            "operands": [
                                {"kind": "field", "text": "Duration8", "fieldEnum": "DURATION8"}
                            ],
                        },
                        {
                            "op": "IS_LESS_THAN_OR_EQUAL_TO",
                            "field": "Start",
                            "fieldEnum": "START",
                            "operands": [{"kind": "prompt", "text": "Show tasks before:"}],
                        },
                        {
                            "op": "EQUALS",
                            "field": "Actual Finish",
                            "fieldEnum": "ACTUAL_FINISH",
                            "operands": [{"kind": "null"}],
                        },
                        {
                            "op": "CONTAINS",
                            "field": "Task Name",
                            "fieldEnum": "NAME",
                            "operands": [
                                {"kind": "literal", "text": "SVT-", "valueType": "String"}
                            ],
                        },
                    ],
                },
            },
        ],
        "groups": [
            {"name": "&No Group", "showSummaryTasks": False, "clauses": []},
            {
                "name": "Complete bands",
                "showSummaryTasks": True,
                "clauses": [
                    {
                        "field": "% Complete",
                        "fieldEnum": "PERCENT_COMPLETE",
                        "ascending": True,
                        "groupOn": 2,
                        "interval": "0",
                        "startAt": "0",
                    },
                    {
                        "field": "Milestone",
                        "fieldEnum": "MILESTONE",
                        "ascending": False,
                        "groupOn": 0,
                        "interval": None,
                        "startAt": "false",
                    },
                ],
            },
        ],
    }
)


def test_parser_reproduces_every_shape() -> None:
    filters, groups = parse_views_json_text(_SIDECAR)
    assert [f.name for f in filters] == ["All Tasks", "Late + prompt"]
    assert filters[0].criteria is None  # match-all
    late = filters[1]
    assert late.show_related_summary_rows is True and late.prompt_count == 1
    assert late.criteria is not None and late.criteria.operator == "AND"
    kids = late.criteria.children
    # field-to-field, prompt, null, and literal operands all survive verbatim
    assert kids[0].operands[0].kind == "field" and kids[0].operands[0].field_enum == "DURATION8"
    assert kids[1].operands[0].kind == "prompt" and kids[1].operands[0].text == "Show tasks before:"
    assert kids[2].operands[0].kind == "null"
    assert kids[3].operands[0].kind == "literal" and kids[3].operands[0].value_type == "String"
    assert [g.name for g in groups] == ["&No Group", "Complete bands"]
    assert groups[0].clauses == ()
    c0, c1 = groups[1].clauses
    assert c0.group_on == 2 and c0.interval == "0" and c0.ascending is True
    assert c1.group_on == 0 and c1.interval is None and c1.ascending is False


def test_parser_empty_sidecar_and_defaults() -> None:
    filters, groups = parse_views_json_text('{"filters": [], "groups": []}')
    assert filters == () and groups == ()
    # omitted flags fall back to the model defaults
    filters, _ = parse_views_json_text('{"filters": [{"name": "F", "criteria": null}]}')
    assert filters[0].is_task_filter is True and filters[0].prompt_count == 0


@pytest.mark.parametrize(
    "text",
    [
        "not json at all",
        "[1, 2]",  # top level not an object
        '{"filters": {}}',  # filters not a list
        '{"filters": [{"criteria": null}]}',  # filter with no name
        '{"filters": [{"name": "F", "criteria": {"field": "Start"}}]}',  # criterion no op
        '{"filters": [{"name": "F", "criteria": {"op": "EQUALS", "operands": [{}]}}]}',  # no kind
        '{"groups": [{"name": "G", "clauses": [7]}]}',  # clause not an object
    ],
)
def test_parser_fails_loud_on_malformation(text: str) -> None:
    with pytest.raises(ImporterError):
        parse_views_json_text(text)


# --- parse_mpp wiring (faked converter, no JVM) --------------------------------------

_MINIMAL_MSPDI = (
    '<Project xmlns="http://schemas.microsoft.com/project">'
    "<StartDate>2025-01-06T08:00:00</StartDate>"
    "<Tasks><Task><UID>1</UID><Name>Solo</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    "</Project>"
)


def _fake_converter(sidecar_text: str | None):
    """A fake ``subprocess.run`` writing the MSPDI (+ optionally a sidecar) like the real one."""

    def _run(cmd, *_args, **_kwargs):
        Path(cmd[5]).write_text(_MINIMAL_MSPDI, encoding="utf-8")
        if sidecar_text is not None:
            Path(cmd[5] + ".views.json").write_text(sidecar_text, encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stderr="")

    return _run


def _parse_with_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sidecar_text: str | None
) -> Schedule:
    sample = tmp_path / "sample.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", lambda _n: "/usr/bin/java")
    monkeypatch.setattr(mpp_mpxj.subprocess, "run", _fake_converter(sidecar_text))
    return parse_mpp(sample)


def test_parse_mpp_attaches_the_sidecar_views(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _parse_with_fake(tmp_path, monkeypatch, _SIDECAR)
    assert [f.name for f in s.saved_filters] == ["All Tasks", "Late + prompt"]
    assert [g.name for g in s.saved_groups] == ["&No Group", "Complete bands"]
    assert s.task_by_id(1).name == "Solo"  # the schedule itself is unchanged


def test_parse_mpp_without_a_sidecar_has_no_views(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _parse_with_fake(tmp_path, monkeypatch, None)
    assert s.saved_filters == () and s.saved_groups == ()


def test_parse_mpp_fails_loud_on_a_corrupt_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ImporterError, match="views sidecar"):
        _parse_with_fake(tmp_path, monkeypatch, "{corrupt")


# --- the real file: ingest + the MPXJ parity oracle ----------------------------------


@pytest.fixture(scope="module")
def leveled() -> Schedule:
    return parse_mpp(LEVELED)


@needs_java
@needs_leveled
def test_real_file_carries_the_10_filters_and_25_groups(leveled: Schedule) -> None:
    assert tuple(f.name for f in leveled.saved_filters) == LEVELED_FILTER_NAMES
    assert len(leveled.saved_groups) == 25
    # spot-check the interactive filter and one criteria tree against the ground truth
    date_range = next(f for f in leveled.saved_filters if f.name == "Date Range...")
    assert date_range.prompt_count == 2 and date_range.show_related_summary_rows is True
    assert len(required_prompts(date_range)) == 2
    cam = next(f for f in leveled.saved_filters if f.name == "CAM_Tasks")
    assert cam.criteria is not None and cam.criteria.operator == "AND"
    text9 = cam.criteria.children[0]
    assert text9.field == "Text9" and text9.operands[0].text == "ZIN"
    mc = next(f for f in leveled.saved_filters if f.name == "_MCTasks")
    assert mc.criteria is not None and len(mc.criteria.children) == 8
    kinds = [c.operands[0].kind for c in mc.criteria.children]
    assert "field" in kinds and "null" in kinds  # field-to-field + the null test survive


@needs_java
@needs_leveled
def test_real_file_groups_resolve_faithfully(leveled: Schedule) -> None:
    """The real file's saved groups must actually bucket, not collapse to a single ``(ungrouped)``
    bin (audit F1/F2/F3). Pins the groups whose clause fields the tool can resolve; the ones that
    reference data the model does not carry (Priority/Status — PR-C.2; Board Status/Sprint — Agile
    add-in) are allowed to degrade, since grouping them faithfully needs source data we don't have.
    """
    by_name = {g.name: g for g in leveled.saved_groups}

    def buckets(name: str) -> list[tuple[str, tuple[int, ...]]]:
        return group_by_clauses(leveled, by_name[name])

    def labels(name: str) -> list[str]:
        return [b[0] for b in buckets(name)]

    # F1: the Duration column arrives as DURATION_TEXT — it must group per value, not degrade.
    assert labels("&Duration") != ["(ungrouped)"]
    assert len(buckets("&Duration")) > 1
    assert labels("D&uration then Priority") != ["(ungrouped)"]
    # F2: "Complete and Incomplete Tasks" (% Complete, interval="0") → exactly the two-bucket split.
    assert labels("Complete and &Incomplete Tasks") == ["Incomplete", "Complete"]
    # F3: Task Mode → Auto vs Manually Scheduled.
    assert labels("Auto Scheduled vs. Manually Scheduled") == [
        "Auto Scheduled",
        "Manually Scheduled",
    ]
    # custom text groups resolve via the two-hop label lookup.
    assert labels("IPT") != ["(ungrouped)"] and len(buckets("IPT")) > 1
    # every bucket partitions the population (no task lost or double-counted) for a resolved group.
    all_uids = {t.unique_id for t in leveled.tasks}
    grouped = [u for _, uids in buckets("&Duration") for u in uids]
    assert sorted(grouped) == sorted(all_uids) and len(grouped) == len(all_uids)


@needs_java
@needs_leveled
@pytest.mark.parity
def test_select_matches_mpxj_evaluate_on_every_saved_filter(
    leveled: Schedule, tmp_path: Path
) -> None:
    """The feature-#10 parity gate: for every prompt-free saved task filter in the real
    file, our evaluator's match set must equal MPXJ's own ``Filter.evaluate()`` output."""
    java = mpp_mpxj._find_java()
    assert java is not None
    home = mpp_mpxj._mpxj_home()
    out = tmp_path / "eval.json"
    classpath = os.pathsep.join([str(home / "classes"), str(home / "lib" / "*")])
    result = subprocess.run(  # nosec B603  # fixed argv, shell=False, vendored tool
        [java, "-cp", classpath, "MpxjToMspdi", "--eval", str(LEVELED), str(out)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    oracle: dict[str, list[int]] = json.loads(out.read_text(encoding="utf-8"))
    assert len(oracle) == 9  # every saved task filter except the 2-prompt "Date Range..."
    compared = 0
    for filt in leveled.saved_filters:
        if not filt.is_task_filter or filt.prompt_count:
            continue
        assert filt.name in oracle
        assert set(select(leveled, filt)) == set(oracle[filt.name]), filt.name
        compared += 1
    assert compared == 9
    # sanity: the oracle is not trivially empty — _MCTasks matches a large real subset
    assert len(oracle["_MCTasks"]) > 500
