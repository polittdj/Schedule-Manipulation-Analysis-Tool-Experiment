"""A browser test must be *runnable on a runner*, and CI must actually run it (BROWSER-ORPHAN-01).

ADR-0406 diagnosed the defect in one module: pinning the dev container's vendored chromium and
skipping when it is absent is not a browser-availability check, it is a *this-container* check. On
a GitHub runner ``playwright install chromium`` writes to ``~/.cache/ms-playwright/…``, so the
pinned ``/opt/pw-browsers`` was missing, every test SKIPPED, and the job went green in 59 seconds
having proved nothing.

That fix reached exactly one module. A computed census found the identical pattern in **23** more,
holding **94** browser tests — measured by bind-mounting an empty directory over
``/opt/pw-browsers`` (a runner-shaped filesystem) and counting: ``86 passed, 94 skipped``. Neither
CI path executed any of them: the ``test`` matrix installs no browser, and the ``browser`` job
named a single module.
Five of the 94 were failing the whole time.

So the fix has two halves, and the second is the one that matters — a repointed module that no job
runs will rot again the moment it is green. These guards pin both:

1. **No module may gate on a hardcoded vendored path.** Resolution belongs to
   ``tests/web/browser_chrome.py``, whose fallback is "let playwright resolve its own", which is
   the branch a runner takes.
2. **CI must run every browser module it has**, and a skip must be a FAILURE there — the same rule
   the ``browser`` job already applied to its one module, now applied to the set.

Deliberately COMPUTED from the tree, never a hand-listed set: a hand-maintained list of call sites
is a stale list waiting to happen, which is the defect this file exists to retire.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

#: The sanctioned resolver. Everything that drives a browser goes through it.
RESOLVER = TESTS / "web" / "browser_chrome.py"

#: A module "drives a browser" if it launches one. Matching the LAUNCH (not an import, not the
#: string "playwright" in prose) is what makes this census about behaviour rather than vocabulary.
_LAUNCH = re.compile(r"\.chromium\.launch\(")

#: The banned shape: a filesystem path under the vendored root used as a gate. The old modules
#: spelled it `Path("/opt/pw-browsers").glob(...)` then skipped on `not CHROME.exists()`.
_VENDOR_LITERAL = re.compile(r'["\']/opt/pw-browsers')


def _browser_modules() -> list[Path]:
    """Every test module that launches a browser, computed from the tree."""
    return [
        f for f in sorted(TESTS.rglob("test_*.py")) if _LAUNCH.search(f.read_text(encoding="utf-8"))
    ]


def test_the_census_is_not_empty() -> None:
    """The sweep must find modules, or every assertion below passes vacuously.

    This is the ADR-0304 anti-pattern guard: a census whose population is zero proves nothing while
    looking exhaustive. 24 is the measured population at the time of writing; the floor is
    deliberately loose (a module may legitimately be deleted) but non-zero.
    """
    mods = _browser_modules()
    assert len(mods) >= 20, f"the browser census collapsed to {len(mods)} modules — check _LAUNCH"


def test_no_browser_module_gates_on_a_hardcoded_vendored_path() -> None:
    """The BROWSER-ORPHAN-01 property: resolution is the resolver's job, nobody else's.

    ``browser_chrome.py`` itself owns the literal — it is the one place allowed to know where a
    container vendors its browsers. ``test_r11_panel_contract.py`` keeps its own ``_chrome()``
    (ADR-0406's original, already runner-compatible) and is exempted BY NAME so the guard stays a
    statement about the pattern rather than about the spelling.
    """
    allowed = {RESOLVER.resolve(), (TESTS / "web" / "test_r11_panel_contract.py").resolve()}
    offenders = [
        f.relative_to(ROOT)
        for f in _browser_modules()
        if f.resolve() not in allowed and _VENDOR_LITERAL.search(f.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "these modules pin a vendored chromium path instead of using "
        f"web.browser_chrome.chrome_kwargs(), so they SKIP on a CI runner: {offenders}"
    )


def test_every_browser_module_is_executed_by_ci() -> None:
    """A repointed module that no job runs is still orphaned — the half that actually bites.

    CI must select the suite by COMPUTING it (``tools/browser_modules.py``), never by listing paths
    in the workflow: the hand-listed form is what let 23 modules sit unexecuted. So the assertion is
    about the mechanism, and then about agreement — this file's own independent sweep must match
    what the tool reports, the "enumerated twice, independently" rule the route census already uses.
    """
    assert WORKFLOW.exists(), WORKFLOW
    ci = WORKFLOW.read_text(encoding="utf-8")
    assert "tools/browser_modules.py" in ci, (
        "the browser job no longer computes its population — a hand-listed set is what "
        "orphaned 23 modules (BROWSER-ORPHAN-01)"
    )

    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "sf_browser_modules_guard", ROOT / "tools" / "browser_modules.py"
    )
    assert spec is not None and spec.loader is not None
    tool = importlib.util.module_from_spec(spec)
    sys.modules["sf_browser_modules_guard"] = tool
    spec.loader.exec_module(tool)

    from_tool = set(tool.browser_modules())
    from_here = {m.relative_to(ROOT).as_posix() for m in _browser_modules()}
    assert from_tool == from_here, (
        "the two independent browser censuses disagree — CI would run a different set than this "
        f"guard checks. only-in-tool={sorted(from_tool - from_here)} "
        f"only-in-guard={sorted(from_here - from_tool)}"
    )


def test_the_browser_job_treats_a_skip_as_a_failure() -> None:
    """The guard that caught the original: a job can go green while everything in it skipped.

    ``browser`` already enforced this for its single module. The property must survive the job
    growing to cover the whole set, so it is asserted rather than assumed.
    """
    ci = WORKFLOW.read_text(encoding="utf-8")
    # Matching ANY skip, never a reason string — enumerating skip reasons is the same mistake as
    # enumerating failure modes (this guard's own paid-for lesson). The pattern must match a bare
    # `SKIPPED` line OR pytest's "N skipped" tally, and the branch must EXIT NON-ZERO: a grep whose
    # body does not fail the job detects the skip and then shrugs.
    guard = re.search(r'if grep -qE "\^SKIPPED\|\[0-9\]\+ skipped" out\.txt; then(.*?)fi', ci, re.S)
    assert guard, (
        "the browser job's skip-is-a-failure guard is gone or no longer matches ANY skip — a job "
        "whose tests all skipped would report green, which is exactly BROWSER-ORPHAN-01"
    )
    assert "exit 1" in guard.group(1), "the skip guard detects a skip but does not fail the job"


def test_the_resolver_falls_back_to_playwrights_own_resolution() -> None:
    """The single behaviour that makes a runner work: no vendored binary => NO executable_path.

    Asserted on the real function against a directory that cannot exist, because this is the exact
    branch the 23 orphaned modules could not take.
    """
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("sf_browser_chrome_guard", RESOLVER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sf_browser_chrome_guard"] = mod
    spec.loader.exec_module(mod)

    mod.VENDOR_ROOT = Path("/nonexistent-vendor-root-for-this-guard")
    assert mod.chrome_kwargs() == {}, (
        "with no vendored binary the resolver must return NO executable_path and let playwright "
        "resolve its own — returning a pinned path is what made 94 tests skip on CI"
    )
