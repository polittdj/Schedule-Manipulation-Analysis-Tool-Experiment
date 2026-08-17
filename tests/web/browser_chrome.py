"""The ONE place that decides how a browser test finds chromium (ADR-0406, generalised).

ADR-0406 diagnosed the defect in ``tests/web/test_r11_panel_contract.py``: a module that pins a
sandbox path and skips when it is absent is not performing a browser-availability check, it is
performing a *this-container* check. On CI, ``playwright install chromium`` puts the browser under
``~/.cache/ms-playwright/…``, so the pinned ``/opt/pw-browsers`` was missing, every test in the
module SKIPPED, and the job went green having proved nothing.

That fix was applied to ONE module. A computed census (``tests/guards/test_browser_resolver.py``)
found the same hardcoded pattern in **23** more, holding **94** browser tests that never executed
in either CI path. This module is the shared cure, and that guard is what stops it regressing.

The rule, in order:

1. Prefer an explicitly vendored binary when one is present — offline dev containers have no
   download and must not reach the network to run a test.
2. Otherwise return NO ``executable_path`` at all and let playwright resolve its own download.
   A runner takes this branch, which is precisely the branch the hardcoded modules could not take.

GLOBBED, never a pinned build number: the vendored directory is versioned (``chromium-1194``,
``chromium_headless_shell-1194``, …) and a container bump would silently reintroduce the skip.

Import spelling — this cost CI three jobs at once once already (see
``tests/guards/test_render_oracle_corpus.py``). ``from tests.web.x import y`` works under
``python -m pytest`` (which prepends CWD) and dies under the bare ``pytest`` CI runs. Because
``tests/web/`` carries an ``__init__.py``, pytest's prepend import mode puts ``tests/`` on
``sys.path`` when it collects this package, so the spelling that survives BOTH is::

    from web.browser_chrome import chrome_kwargs

Modules outside ``tests/web/`` (``tests/perf/``) have no such package parent and load it by path
via :func:`load_by_path`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

#: Where an offline dev container vendors its browsers. Absent on a GitHub runner — which is the
#: whole point: absence must fall through to playwright, never to a skip.
VENDOR_ROOT = Path("/opt/pw-browsers")

#: Both shapes playwright vendors: the full browser and the headless shell.
VENDOR_GLOBS = (
    "chromium*/chrome-linux/chrome",
    "chromium_headless_shell*/*/chrome-headless-shell",
)


def chrome_kwargs() -> dict[str, Any]:
    """Launch kwargs for ``p.chromium.launch``: the vendored binary if present, else playwright's.

    Returning ``{}`` is not a failure path — it is the runner path, and it is why this helper
    replaced ``pytest.mark.skipif(not CHROME.exists())``.
    """
    for pattern in VENDOR_GLOBS:
        for candidate in sorted(VENDOR_ROOT.glob(pattern)):
            if candidate.exists():
                return {"executable_path": str(candidate)}
    return {}


def load_by_path() -> Any:
    """Import this module from a test package that cannot spell ``web.browser_chrome``.

    ``tests/perf/`` has no ``__init__.py``, so pytest never puts ``tests/`` on ``sys.path`` for it.
    The by-path idiom is the same one ``tests/guards/test_render_oracle_corpus.py`` already uses.
    """
    import importlib.util
    import sys

    name = "sf_browser_chrome"
    if name in sys.modules:  # pragma: no cover - trivial cache branch
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve())
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
