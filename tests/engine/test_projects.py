"""Grouped ingestion: grouping files into Projects (v4). Pure, deterministic; no I/O."""

from __future__ import annotations

from schedule_forensics.engine.projects import IngestRecord, group_into_projects


def _rec(
    key: str,
    *,
    title: str | None = None,
    filename: str | None = None,
    sd: float | None = None,
    folder: str | None = None,
    mtime: float | None = None,
) -> IngestRecord:
    return IngestRecord(
        key=key,
        project_title=title,
        filename=filename or (key + ".mspdi"),
        status_date_ordinal=sd,
        folder=folder,
        mtime=mtime,
    )


def test_loose_files_group_by_title_case_insensitive_trimmed() -> None:
    recs = [
        _rec("a", title="Commercial Construction", sd=1.0),
        _rec(
            "b", title=" commercial construction ", sd=2.0
        ),  # same project, different casing/space
        _rec("c", title="Bridge Retrofit", sd=1.0),
    ]
    projects = group_into_projects(recs)
    assert len(projects) == 2
    cc = next(p for p in projects if p.title == "Commercial Construction")
    assert cc.origin == "title" and not cc.needs_attention
    assert [v.key for v in cc.versions] == ["a", "b"]  # oldest data date first
    assert {p.title for p in projects} == {"Commercial Construction", "Bridge Retrofit"}


def test_loose_file_without_title_is_its_own_needs_attention_project() -> None:
    projects = group_into_projects([_rec("x", title=None, filename="mystery.xer", sd=1.0)])
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "mystery.xer" and p.origin == "filename"
    assert p.needs_attention is True
    assert p.notices and "no project title" in p.notices[0]
    assert [v.key for v in p.versions] == ["x"]


def test_folder_is_exactly_one_project_named_by_folder_regardless_of_depth() -> None:
    # a folder nested any depth: sub-folders (years/months) are ignored — all files are one Project
    recs = [
        _rec("j", folder="AcmeProgram", filename="AcmeProgram/2023/Jan/a.mspdi", sd=1.0),
        _rec("f", folder="AcmeProgram", filename="AcmeProgram/2023/Feb/b.mspdi", sd=2.0),
        _rec("y", folder="AcmeProgram", filename="AcmeProgram/2024/c.mspdi", sd=3.0),
    ]
    projects = group_into_projects(recs)
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "AcmeProgram" and p.origin == "folder" and not p.needs_attention
    assert [v.key for v in p.versions] == ["j", "f", "y"]  # oldest-first by data date


def test_folder_with_disagreeing_internal_titles_records_nonblocking_notice() -> None:
    recs = [
        _rec("a", folder="Q3Review", title="Widget Program", sd=1.0),
        _rec("b", folder="Q3Review", title="Gadget Program", sd=2.0),  # disagrees — folder wins
    ]
    projects = group_into_projects(recs)
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "Q3Review"  # folder name wins
    assert p.needs_attention is False  # never blocks
    assert any("different document titles" in n for n in p.notices)


def test_mtime_tiebreak_orders_tied_and_undated_versions_and_flags_it() -> None:
    # two files share a data date, one has none → mtime decides, and a notice is raised
    recs = [
        _rec("late_sd", title="P", sd=5.0, mtime=100.0),
        _rec("tie_b", title="P", sd=1.0, mtime=20.0),
        _rec("tie_a", title="P", sd=1.0, mtime=10.0),  # same sd as tie_b, earlier mtime
        _rec("undated", title="P", sd=None, mtime=999.0),
    ]
    projects = group_into_projects(recs)
    assert len(projects) == 1
    p = projects[0]
    # tie broken by mtime (tie_a before tie_b), dated before undated, undated last
    assert [v.key for v in p.versions] == ["tie_a", "tie_b", "late_sd", "undated"]
    assert any("last-modified" in n for n in p.notices)


def test_no_tiebreak_notice_when_data_dates_are_distinct() -> None:
    recs = [_rec("a", title="P", sd=1.0), _rec("b", title="P", sd=2.0)]
    p = group_into_projects(recs)[0]
    assert [v.key for v in p.versions] == ["a", "b"]
    assert p.notices == ()  # clean data-date order, no fallback warning


def test_projects_come_back_in_first_seen_order() -> None:
    recs = [
        _rec("z", title="Zulu", sd=1.0),
        _rec("a", title="Alpha", sd=1.0),
        _rec("z2", title="zulu", sd=2.0),
    ]
    projects = group_into_projects(recs)
    assert [p.title for p in projects] == ["Zulu", "Alpha"]  # first-seen, not alphabetical


def test_folders_and_loose_files_coexist() -> None:
    recs = [
        _rec("f1", folder="ProgA", sd=1.0),
        _rec("loose", title="ProgB", sd=1.0),
        _rec("f2", folder="ProgA", sd=2.0),
        _rec("orphan", title=None, filename="orphan.mpp", sd=1.0),
    ]
    projects = group_into_projects(recs)
    titles = [p.title for p in projects]
    assert titles == ["ProgA", "ProgB", "orphan.mpp"]
    assert next(p for p in projects if p.title == "ProgA").origin == "folder"
    assert next(p for p in projects if p.title == "orphan.mpp").needs_attention is True
