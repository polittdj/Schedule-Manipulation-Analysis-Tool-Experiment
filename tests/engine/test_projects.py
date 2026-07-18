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
    chash: str | None = None,
    excluded: bool = False,
) -> IngestRecord:
    return IngestRecord(
        key=key,
        project_title=title,
        filename=filename or (key + ".mspdi"),
        status_date_ordinal=sd,
        folder=folder,
        mtime=mtime,
        content_hash=chash,
        excluded=excluded,
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


# — duplicate/revision review (ADR-0259) ————————————————————————————————————————————————


def test_same_date_with_different_content_flags_pending_review() -> None:
    # two files statused the same day whose bytes PROVABLY differ → the operator must decide
    recs = [
        _rec("a", title="P", sd=1.0e9, mtime=10.0, chash="hash-A"),
        _rec("b", title="P", sd=1.0e9, mtime=20.0, chash="hash-B"),
    ]
    p = group_into_projects(recs)[0]
    assert p.pending_review is True
    assert any("different content" in n for n in p.notices)
    # both filenames are named in the notice — the operator can tell which is which
    assert any("a.mspdi" in n and "b.mspdi" in n for n in p.notices)


def test_same_date_without_hashes_is_not_flagged_for_review() -> None:
    # no content hashes (loaded outside /upload) → difference is unprovable; only the ordering
    # tiebreak notice appears, never a false "different content" accusation
    recs = [
        _rec("a", title="P", sd=1.0e9, mtime=10.0),
        _rec("b", title="P", sd=1.0e9, mtime=20.0),
    ]
    p = group_into_projects(recs)[0]
    assert p.pending_review is False
    assert not any("different content" in n for n in p.notices)
    assert any("last-modified" in n for n in p.notices)  # the tiebreak notice still fires


def test_excluding_one_copy_resolves_pending_review() -> None:
    recs = [
        _rec("a", title="P", sd=1.0e9, mtime=10.0, chash="hash-A"),
        _rec("b", title="P", sd=1.0e9, mtime=20.0, chash="hash-B", excluded=True),
    ]
    p = group_into_projects(recs)[0]
    assert p.pending_review is False  # the surviving population has one file per date
    # the excluded version stays LISTED (Portfolio shows it, badged) — never dropped
    assert [v.key for v in p.versions] == ["a", "b"]
    assert [v.excluded for v in p.versions] == [False, True]


# — title collisions across origins (ADR-0258; the filename-equals-folder-name case) ——————


def test_folder_containing_a_file_named_like_it_is_one_project() -> None:
    # the operator's §2.3 case: folder "Artemis" holding "Artemis.mpp" must NOT split or collide
    recs = [_rec("k", folder="Artemis", filename="Artemis.mpp", title=None, sd=1.0)]
    projects = group_into_projects(recs)
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "Artemis" and p.origin == "folder"
    assert not any("share the title" in n for n in p.notices)


def test_folder_and_loose_file_with_same_title_stay_separate_with_notices() -> None:
    # a folder "Artemis" AND a loose file titled "Artemis": merging would be a guess, so both
    # stay separate — but BOTH rows say why two same-named Projects exist (never a silent mystery)
    recs = [
        _rec("f", folder="Artemis", sd=1.0),
        _rec("l", title="Artemis", sd=2.0),
    ]
    projects = group_into_projects(recs)
    assert len(projects) == 2
    assert all(any("share the title" in n for n in p.notices) for p in projects)
    assert {p.origin for p in projects} == {"folder", "title"}


def test_pids_are_stable_and_distinct() -> None:
    recs = [
        _rec("f", folder="Artemis", sd=1.0),
        _rec("l", title="Artemis", sd=2.0),
        _rec("o", title=None, filename="orphan.mpp", sd=1.0),
    ]
    pids = [p.pid for p in group_into_projects(recs)]
    assert pids == ["folder:Artemis", "title:artemis", "file:o"]
    # loading MORE files later must not change existing pids (the session stores them) — the
    # list ORDER may shift (projects group by origin), the pid VALUES may not
    more = [*recs, _rec("f2", folder="Artemis", sd=3.0), _rec("l2", title="New Prog", sd=1.0)]
    pids_after = {p.pid for p in group_into_projects(more)}
    assert set(pids) <= pids_after  # every existing pid survives unchanged
    assert "title:new prog" in pids_after
