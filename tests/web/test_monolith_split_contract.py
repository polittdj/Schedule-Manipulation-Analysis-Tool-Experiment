"""The structural contract the monolith split rests on (ADR-0297 phase 1, ADR-0349 phase 2).

The split is only safe while three things stay true, and every one of them is the kind of
invariant that rots silently rather than failing loudly:

1. **`app.py` re-exports every extracted name, as the SAME object.** ADR-0297 chose the
   explicit ``X as X`` idiom precisely so existing ``web.app`` import paths keep working. A
   name added to ``chrome.py`` but not re-exported breaks nothing *here* and everything in a
   caller; worse, a stray *copy* left behind in ``app.py`` would keep every import green while
   the two modules drifted apart.
2. **The dependency runs one way.** ``chrome`` → ``state`` → engine/ai/model. An import of
   ``web.app`` from ``chrome.py`` would make the cut circular; Python would often *tolerate*
   it, so no test would notice until an unrelated import-order change detonated.
3. **The layout lives where the source-text guards look for it.** Several guards read a
   module's *text* and search for ``_LAYOUT``'s script order (test_axis_titles,
   test_dd_line_ledger, test_bar_drill). Phase 2 taught the lesson the hard way: moving
   ``_LAYOUT`` out of ``app.py`` did not make those guards fail — it made them search a file
   that no longer contained their subject, which is a guard that has quietly stopped guarding.
   Phase 3 moves ~11k more lines, so the trap is pinned here rather than re-learned.
"""

from __future__ import annotations

import ast
from pathlib import Path

import schedule_forensics.web.app as app_mod
import schedule_forensics.web.chrome as chrome_mod

WEB = Path(app_mod.__file__).parent


def _module_level_names(path: Path) -> set[str]:
    """Names BOUND by this module's own code — definitions and assignments, never imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Try):  # the `_ASSET_VERSION` try/except import-version dance
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    names.update(t.id for t in sub.targets if isinstance(t, ast.Name))
    return names


def test_every_chrome_name_is_reexported_by_app_as_the_same_object() -> None:
    """`web.app.X is web.chrome.X` for every name chrome.py defines — ADR-0297's `X as X` idiom.

    `is`, not `==`: a re-export that resolved to a *copy* left behind in app.py would compare
    equal for a constant and pass, while the two modules silently diverged.
    """
    defined = _module_level_names(WEB / "chrome.py")
    assert defined, "chrome.py defines nothing — the AST scan is broken, not the module"
    missing = sorted(n for n in defined if not hasattr(app_mod, n))
    assert not missing, (
        "chrome.py defines names web.app does not re-export, so any caller still importing them "
        f"from web.app breaks: {missing}. Add `from ...chrome import X as X`."
    )
    drifted = sorted(n for n in defined if getattr(app_mod, n) is not getattr(chrome_mod, n))
    assert not drifted, (
        "web.app re-binds these to something other than chrome.py's object — a leftover copy in "
        f"app.py, or a shadowing definition: {drifted}"
    )


def test_chrome_never_imports_app() -> None:
    """The cut is acyclic by construction: chrome.py may not reach back into app.py."""
    tree = ast.parse((WEB / "chrome.py").read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("web.app"):
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            offenders += [
                f"line {node.lineno}: import {a.name}"
                for a in node.names
                if a.name.endswith("web.app")
            ]
    assert not offenders, (
        "chrome.py imports web.app — the split's dependency direction is chrome → state → "
        f"engine, never back up into the routes: {offenders}"
    )


def test_the_layout_lives_where_the_source_text_guards_look_for_it() -> None:
    """`_LAYOUT` is defined EXACTLY ONCE in the web package, in the module the guards read.

    This is a signpost, not a style rule. Guards in test_axis_titles / test_dd_line_ledger /
    test_bar_drill read a module's raw text and assert the layout's script ORDER. Move the
    layout without moving them and they go on passing against a file that no longer contains
    it. When phase 3 moves this, fix those guards in the same commit — that is what this
    failure means.
    """
    holders = sorted(
        p.name for p in WEB.glob("*.py") if "_LAYOUT = Template(" in p.read_text(encoding="utf-8")
    )
    assert holders == ["chrome.py"], (
        "the page layout moved (or was duplicated). The source-text guards in "
        "tests/web/test_axis_titles.py, test_dd_line_ledger.py and test_bar_drill.py read it by "
        f"FILE PATH and must be repointed in the same commit — found in: {holders}"
    )
