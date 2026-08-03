"""Every dependency is bounded, and the declared floor is the one CI executes (ADR-0346).

The defect this module exists for is not a wrong number — it is that the SAME TREE passed or
failed on whatever pip resolved that day. Measured, not supposed: one commit gave pytest 8.0.2
FAIL / 8.4.2 FAIL / 9.1.1 PASS (ADR-0345). Nothing bounded the resolution from above and nothing
tested it from below, so "we support pytest 8.0" (`[tool.pytest.ini_options] minversion`) was an
assertion no run could contradict.

Three artifacts answer that, and this module is what keeps them from drifting apart:

* ``pyproject.toml`` — every requirement now carries an upper bound as well as a lower one.
* ``constraints/floor.txt`` — the declared lower bounds, pinned, and RUN by CI's ``floor`` job.
* ``constraints/known-good.txt`` — one full transitive resolution measured green, for reproducing
  a build exactly (an offline operator install, or a "did the code change or did the resolution?"
  bisect).

Two of the floors were simply untrue when measured, which is the whole argument for executing
them: ``pydantic>=2`` would not install beside ``fastapi>=0.110`` at all (fastapi 0.110 excludes
pydantic 2.0.0/2.0.1/2.1.0), and once installable, pydantic 2.0.2-2.5.3 failed
``tests/model/test_schedule.py::test_cache_does_not_perturb_hash_or_equality``.

Deliberately offline and fast: it reads files, never the network. Whether the floor set actually
*resolves and passes* is CI's ``floor`` job, which is the only place that can honestly answer it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
FLOOR = ROOT / "constraints" / "floor.txt"
KNOWN_GOOD = ROOT / "constraints" / "known-good.txt"

#: Exempt from the upper-bound rule, each for a reason written beside the pin in ``pyproject.toml``.
#: This is an EQUALITY check below, not a skip-list: adding a new unbounded requirement fails, and
#: so does bounding one of these without removing it here. An exemption has to be argued, not
#: inherited.
UNBOUNDED_BY_DESIGN = frozenset({"setuptools"})

#: The distributions ``constraints/floor.txt`` pins and CI's ``floor`` job installs — the floors
#: that are EXECUTED. The QC tools (ruff / mypy / bandit / pip-audit / setuptools) are deliberately
#: not here: their output is version-sensitive by design, so running the gate against an old one
#: measures the tool rather than the product. Their floors are ADVISORY and narrowed instead.
EXECUTED_FLOORS = frozenset(
    {
        "pydantic",
        "fastapi",
        "uvicorn",
        "jinja2",
        "python-multipart",
        "pytest",
        "pytest-cov",
        "httpx",
    }
)

#: ``constraints/known-good.txt`` is the closure of ``pip install -e '.[dev]'`` — so it must cover
#: the runtime deps and the dev extra, and must NOT be expected to carry ``monitor`` / ``browser``.
KNOWN_GOOD_GROUPS = ("dependencies", "dev")


def _pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _declared() -> dict[str, list[tuple[str, Requirement]]]:
    """Every declared requirement, keyed by canonical name → [(group, Requirement), ...]."""
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    groups: list[tuple[str, list[str]]] = [("dependencies", list(project["dependencies"]))]
    optional = project.get("optional-dependencies", {})
    assert isinstance(optional, dict)
    groups += [(name, list(specs)) for name, specs in sorted(optional.items())]

    out: dict[str, list[tuple[str, Requirement]]] = {}
    for group, specs in groups:
        for spec in specs:
            req = Requirement(spec)
            out.setdefault(canonicalize_name(req.name), []).append((group, req))
    return out


def _pins(path: Path) -> dict[str, Version]:
    """Parse a ``name==version`` constraints file, ignoring comments and blank lines."""
    pins: dict[str, Version] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        assert "==" in line, f"{path.name}: every line must be an exact pin; got {raw!r}"
        name, _, version = line.partition("==")
        pins[canonicalize_name(name.strip())] = Version(version.strip())
    return pins


def _lower_bound(req: Requirement) -> Version | None:
    lows = [Version(s.version) for s in req.specifier if s.operator in (">=", "==")]
    return max(lows) if lows else None


def _has_upper_bound(req: Requirement) -> bool:
    return any(s.operator in ("<", "<=", "==", "~=") for s in req.specifier)


# ---- the bounds themselves ---------------------------------------------------------------


def test_every_declared_requirement_has_a_lower_bound() -> None:
    """No exemptions on this half — an unfloored dependency can resolve to anything, including a
    release with a published CVE that our own floors (jinja2, python-multipart, setuptools) exist
    to exclude."""
    missing = [
        f"{group}: {req}"
        for reqs in _declared().values()
        for group, req in reqs
        if _lower_bound(req) is None
    ]
    assert not missing, f"requirements with no lower bound: {missing}"


def test_the_only_unbounded_requirements_are_the_named_exemptions() -> None:
    """An EQUALITY check, so the exemption set cannot grow by accident.

    Adding a new requirement without an upper bound fails here; so does bounding ``setuptools``
    without removing it from ``UNBOUNDED_BY_DESIGN``. Either way the change has to be argued in a
    diff rather than inherited silently — which is exactly how the tree arrived at zero upper
    bounds in the first place.
    """
    unbounded = {
        name
        for name, reqs in _declared().items()
        if not all(_has_upper_bound(req) for _group, req in reqs)
    }
    assert unbounded == set(UNBOUNDED_BY_DESIGN), (
        f"unbounded requirements {sorted(unbounded)} != documented exemptions "
        f"{sorted(UNBOUNDED_BY_DESIGN)}"
    )


# ---- constraints/floor.txt is the declared floor, not a separate opinion ------------------


def test_floor_file_pins_exactly_the_executed_floor_set() -> None:
    assert set(_pins(FLOOR)) == set(EXECUTED_FLOORS)


def test_every_floor_pin_equals_the_declared_lower_bound() -> None:
    """The two files must say the same thing. Raising a bound in ``pyproject.toml`` without
    re-pinning here would leave CI's ``floor`` job testing a version we no longer claim to
    support — a green job that proves the wrong proposition."""
    declared = _declared()
    for name, pinned in _pins(FLOOR).items():
        for group, req in declared[name]:
            low = _lower_bound(req)
            assert low is not None and low == pinned, (
                f"constraints/floor.txt pins {name}=={pinned} but {group} declares {req}"
            )


def test_pytest_minversion_matches_the_floor_pin() -> None:
    """``minversion`` is a support claim; the floor job is what tests it. They must agree."""
    tool = _pyproject()["tool"]
    assert isinstance(tool, dict)
    minversion = tool["pytest"]["ini_options"]["minversion"]  # type: ignore[index]
    assert Version(str(minversion)) == _pins(FLOOR)["pytest"]


# ---- constraints/known-good.txt cannot contradict the declared ranges ---------------------


def test_known_good_pins_satisfy_the_declared_ranges() -> None:
    declared = _declared()
    for name, pinned in _pins(KNOWN_GOOD).items():
        for group, req in declared.get(name, []):
            assert req.specifier.contains(pinned, prereleases=True), (
                f"constraints/known-good.txt pins {name}=={pinned}, outside {group}'s {req}"
            )


def test_known_good_covers_every_runtime_and_dev_requirement() -> None:
    """It is the closure of ``pip install -e '.[dev]'``; a declared requirement missing from it
    means the capture is stale, and a stale lock is worse than none — it reproduces a build that
    was never the one under test."""
    pins = _pins(KNOWN_GOOD)
    expected = {
        name
        for name, reqs in _declared().items()
        if any(group in KNOWN_GOOD_GROUPS for group, _req in reqs)
    }
    missing = sorted(expected - set(pins))
    assert not missing, f"missing from known-good.txt: {missing}"
