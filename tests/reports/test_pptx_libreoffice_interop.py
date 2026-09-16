"""The exported ``.pptx`` is READ BACK by an independent implementation — LibreOffice Impress.

Every other ``.pptx`` test in this tree reads the package with the standard library and checks
the XML *we* wrote. That proves the writer is self-consistent; it cannot prove another program
can open the file. This module closes that gap: it hands both decks to LibreOffice headless and
asserts the slide comes back with its shapes and its words intact.

**The trap this module exists to refuse (R-52, ADR-0498).** The audit register carried, from
2026-09-07, "the exported ``.pptx`` — the one-pager AND the compare deck — does not load in
LibreOffice 7 headless (*source file could not be loaded*)". Re-measured 2026-09-15: that same
error is what a LibreOffice install with **no presentation import filter** says about *any*
presentation — a PowerPoint-authored deck and a Microsoft-authored ``.xlsx`` are refused with
the identical sentence. ``libreoffice-core`` + ``libreoffice-common`` without
``libreoffice-impress`` is such an install, and it is what the container had. The finding was an
instrument reading, not a defect in the package.

So this module never decides our deck is broken until it has watched the instrument load a deck
**PowerPoint itself wrote** (``00_REFERENCE_INTAKE/mpp/Politte Schedule Tool.pptx``, committed and
non-CUI per ADR-0152). Three outcomes, on purpose:

* no ``soffice`` on PATH, or no reference deck on disk -> ``skip`` naming what is missing;
* ``soffice`` present but the **control** deck does not load -> ``skip`` saying the filter is
  absent — a red here would accuse the writer of the environment's fault;
* control loads and ours does not -> **fail**, and that is the only configuration in which this
  module accuses the writer.

CI turns the skips back into failures: the ``browser`` job installs ``libreoffice-impress`` and
runs this module with a skip treated as a failure, so the environment can never silently stop
measuring (the same discipline the parity gate and the browser census use).

``soffice`` **exits 0 when it refuses a file** — measured: ``Error: source file could not be
loaded`` on stderr, ``rc=0``. Nothing here reads the return code; the question is always whether
the converted artifact exists.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from schedule_forensics.reports.onepager import OnePagerDoc, OnePagerItem, build_layout
from schedule_forensics.reports.onepager_compare import build_compare_layout, compare_onepager_docs
from schedule_forensics.reports.pptx import render_onepager_compare_pptx, render_onepager_pptx

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: A deck PowerPoint wrote — the control. Independent of everything this repo generates.
_CONTROL = _REPO_ROOT / "00_REFERENCE_INTAKE" / "mpp" / "Politte Schedule Tool.pptx"
_TODAY = dt.date(2026, 6, 15)
_MARKING = "Controlled Unclassified Information • CUI"
#: LibreOffice's cold start plus an import is seconds; a minute is a hang, not a slow box.
_TIMEOUT = 300


#: ``(lane, name, start, finish, sheet row)`` — two lanes of activities and two milestones.
_ROWS: tuple[tuple[str, str, dt.date, dt.date, int], ...] = (
    ("Design", "Preliminary design review", dt.date(2026, 1, 5), dt.date(2026, 3, 20), 2),
    ("Design", "Critical design review", dt.date(2026, 4, 1), dt.date(2026, 4, 1), 3),
    ("Build", "Structure fabrication", dt.date(2026, 4, 6), dt.date(2026, 8, 14), 4),
    ("Test", "Environmental test campaign", dt.date(2026, 8, 17), dt.date(2026, 11, 27), 5),
    ("Test", "Ready to Ship", dt.date(2026, 12, 4), dt.date(2026, 12, 4), 6),
)


def _items(shift_days: int) -> tuple[OnePagerItem, ...]:
    """The rows above, shifted whole calendar days — the compare deck needs a moved twin."""
    d = dt.timedelta(days=shift_days)
    return tuple(
        OnePagerItem(lane, name, start + d, finish + d, row)
        for lane, name, start, finish, row in _ROWS
    )


def _onepager_bytes() -> bytes:
    lay = build_layout(list(_items(0)), _TODAY, "Program One-Pager", "Prepared 2026-06-15")
    return render_onepager_pptx(lay, marking=_MARKING, source="Source: probe.xlsx · 5 items")


def _compare_bytes() -> bytes:
    prior = OnePagerDoc("prior.xlsx", "Sheet1", _items(0), (), ())
    current = OnePagerDoc("current.xlsx", "Sheet1", _items(12), (), ())
    lay = build_compare_layout(
        compare_onepager_docs(prior, current), _TODAY, "Program Compare", "Prior vs Current"
    )
    return render_onepager_compare_pptx(lay, marking=_MARKING, source="Prior: prior.xlsx")


def _convert(soffice: str, src: Path, outdir: Path) -> tuple[Path | None, str]:
    """``src`` -> flat ODF in ``outdir``: ``(path, "")``, or ``(None, what it said)`` if refused.

    Flat ODF (``.fodp``) rather than PDF on purpose: it is LibreOffice's own object model written
    out as plain XML, so a passing assertion here says *Impress parsed these shapes and this
    text*, not merely *a file opened*. A PDF would need a text-extraction dependency and would
    read glyphs out of a subset font.

    The expected output is UNLINKED first. The artifact is the verdict, so a leftover from an
    earlier run in a reused directory would read a refusal as a success — the exact class of
    mistake this module exists to catch.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    produced = outdir / (src.stem + ".fodp")
    produced.unlink(missing_ok=True)
    done = subprocess.run(
        [
            soffice,
            f"-env:UserInstallation=file://{outdir / '_lo_profile'}",
            "--headless",
            "--norestore",
            "--convert-to",
            "fodp",
            "--outdir",
            str(outdir),
            str(src),
        ],
        capture_output=True,
        timeout=_TIMEOUT,
        check=False,  # a refusal EXITS 0; the artifact is the verdict, never the code
    )
    if produced.exists():
        return produced, ""
    said = (done.stderr or done.stdout or b"").decode("utf-8", "replace").strip()
    return None, said or f"(nothing on stderr; rc={done.returncode})"


@pytest.fixture(scope="module")
def soffice(tmp_path_factory: pytest.TempPathFactory) -> str:
    """LibreOffice, PROVEN able to import a PowerPoint-authored deck before anything else runs."""
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if exe is None:
        pytest.skip("LibreOffice (soffice) is not on PATH — nothing to read the deck back with")
    if not _CONTROL.exists():
        pytest.skip(f"the PowerPoint-authored control deck is absent: {_CONTROL}")
    control, said = _convert(exe, _CONTROL, tmp_path_factory.mktemp("control"))
    if control is None:
        pytest.skip(
            "this LibreOffice cannot import a PowerPoint-authored .pptx either — it has no "
            "PresentationML filter (install libreoffice-impress). The instrument is unusable; "
            f"a failure here would be the environment's, not the writer's. It said: {said}"
        )
    return exe


def _loaded(soffice: str, data: bytes, tmp_path: Path, name: str) -> ET.Element:
    src = tmp_path / f"{name}.pptx"
    src.write_bytes(data)
    produced, said = _convert(soffice, src, tmp_path / "out")
    assert produced is not None, (
        f"LibreOffice refused {name}.pptx while loading the PowerPoint-authored control deck "
        f"in the same run — the package is the problem, not the instrument. It said: {said}"
    )
    return ET.parse(produced).getroot()


def _pages(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if el.tag.endswith("}page")]


def _words(root: ET.Element) -> str:
    return " ".join(t.strip() for t in root.itertext() if t and t.strip())


def _shape_names(root: ET.Element) -> set[str]:
    out = set()
    for el in root.iter():
        for key, value in el.attrib.items():
            if key.endswith("}name") and value:
                out.add(value)
    return out


def test_libreoffice_loads_the_one_pager_deck(soffice: str, tmp_path: Path) -> None:
    root = _loaded(soffice, _onepager_bytes(), tmp_path, "onepager")
    assert len(_pages(root)) == 1, "the one-pager is ONE slide"
    words = _words(root)
    for probe in (
        _MARKING,  # the CUI banner — Law 1 travels with the artifact
        "Program One-Pager",
        "Preliminary design review",
        "Critical design review",  # a milestone
        "Structure fabrication",
        "Ready to Ship",
        "Design",  # the swimlane label
        "2026",  # the year band
    ):
        assert probe in words, f"LibreOffice loaded the deck but lost {probe!r}"
    # Every shape is a named, selectable object (the module's promise to the operator) — the
    # names survive the round trip into another program's object model.
    names = _shape_names(root)
    assert "CUI marking (top)" in names and "CUI marking (bottom)" in names


def test_libreoffice_loads_the_compare_deck(soffice: str, tmp_path: Path) -> None:
    root = _loaded(soffice, _compare_bytes(), tmp_path, "compare")
    assert len(_pages(root)) == 1, "the compare deck is ONE slide"
    words = _words(root)
    for probe in (_MARKING, "Program Compare", "Structure fabrication", "+12 cal d"):
        assert probe in words, f"LibreOffice loaded the compare deck but lost {probe!r}"
