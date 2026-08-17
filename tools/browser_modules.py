"""Print every test module that launches a browser, so CI never carries a hand-listed set.

BROWSER-ORPHAN-01: the ``browser`` job named ONE module by hand. Twenty-three more existed, and
because nothing recomputed that list, none of them ever ran — 94 tests, five of them failing, in a
suite that reported green. A list a human maintains is a list that goes stale; the cure is to
compute it at the moment of use.

CI calls this and feeds the result straight to pytest::

    pytest -q $(python tools/browser_modules.py) -p no:cacheprovider

so a NEW browser module is covered the day it lands, with no workflow edit. The census is pinned
from the other side by ``tests/guards/test_browser_resolver.py``, which recomputes it independently
and fails if CI's mechanism stops covering what it finds.

Matching the LAUNCH call — not an import, not the word "playwright" in prose — keeps this a census
of behaviour rather than of vocabulary.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

_LAUNCH = re.compile(r"\.chromium\.launch\(")


def browser_modules() -> list[str]:
    """Repo-relative POSIX paths of every test module that launches a browser, sorted."""
    return sorted(
        f.relative_to(ROOT).as_posix()
        for f in TESTS.rglob("test_*.py")
        if _LAUNCH.search(f.read_text(encoding="utf-8"))
    )


def main() -> int:
    mods = browser_modules()
    if not mods:
        # An empty census would hand pytest no paths, and pytest with no paths runs the WHOLE
        # suite — which would look like a pass while proving nothing about browsers. Fail loudly.
        print("no browser test modules found — the census is broken", file=sys.stderr)
        return 1
    print(" ".join(mods))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
