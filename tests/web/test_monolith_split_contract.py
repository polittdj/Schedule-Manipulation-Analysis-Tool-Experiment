"""The structural contract the monolith split rests on (ADR-0297 p1, ADR-0349 p2, ADR-0350 p3).

The split is only safe while these stay true, and every one of them is the kind of
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
4. **A "nowhere in the view layer" guard reads EVERY view module.** ADR-0350's own near-miss:
   `_stat_cards` moved to ``components.py`` while the em-dash sentinel guard still read only
   ``app.py`` + ``chrome.py``. It would have gone on passing over a shrunken subject. Each
   split silently narrows those guards, so the module list they must enumerate is pinned here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import schedule_forensics.web.app as app_mod
import schedule_forensics.web.chrome as chrome_mod
import schedule_forensics.web.components as components_mod

WEB = Path(app_mod.__file__).parent

#: Modules extracted OUT of app.py, newest last. Every name each defines must be re-exported.
EXTRACTED = {"chrome.py": chrome_mod, "components.py": components_mod}

#: The view layer, lowest layer FIRST. A module may import only from those before it — that is
#: the whole acyclicity argument, and it scales to the per-page modules phase 3 still has to cut.
LAYER_ORDER = ("state.py", "chrome.py", "components.py", "app.py")

#: Guards whose claim is "nowhere in the view layer" (as opposed to "in this module's markup").
#: They read raw source BY PATH, so a new view module shrinks their reach without going red.
WHOLE_VIEW_LAYER_GUARDS = ("test_bar_drill.py", "test_presentation_fixes.py")

#: The modules such a guard has to read. Markup-carrying only — `state.py` holds no HTML.
VIEW_MODULES = ("app.py", "chrome.py", "components.py")


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


@pytest.mark.parametrize("module_name", sorted(EXTRACTED))
def test_every_extracted_name_is_reexported_by_app_as_the_same_object(module_name: str) -> None:
    """`web.app.X is web.<mod>.X` for every name the module defines — ADR-0297's `X as X` idiom.

    `is`, not `==`: a re-export that resolved to a *copy* left behind in app.py would compare
    equal for a constant and pass, while the two modules silently diverged.
    """
    module = EXTRACTED[module_name]
    defined = _module_level_names(WEB / module_name)
    assert defined, f"{module_name} defines nothing — the AST scan is broken, not the module"
    missing = sorted(n for n in defined if not hasattr(app_mod, n))
    assert not missing, (
        f"{module_name} defines names web.app does not re-export, so any caller still importing "
        f"them from web.app breaks: {missing}. Add `from ...{module_name[:-3]} import X as X`."
    )
    drifted = sorted(n for n in defined if getattr(app_mod, n) is not getattr(module, n))
    assert not drifted, (
        f"web.app re-binds these to something other than {module_name}'s object — a leftover "
        f"copy in app.py, or a shadowing definition: {drifted}"
    )


@pytest.mark.parametrize("module_name", LAYER_ORDER)
def test_the_view_layer_only_ever_imports_downward(module_name: str) -> None:
    """A view module may import only from LOWER layers — `app → components → chrome → state`.

    This subsumes "chrome never imports app" and adds the direction ADR-0350 introduced:
    `components` imports `_e` from `chrome`, so a `chrome` → `components` import would close a
    cycle. Python often *tolerates* a cycle at runtime, so nothing else would notice until an
    unrelated import-order change detonated it.
    """
    allowed = set(LAYER_ORDER[: LAYER_ORDER.index(module_name)])
    forbidden = {m[:-3] for m in LAYER_ORDER if m not in allowed and m != module_name}
    tree = ast.parse((WEB / module_name).read_text(encoding="utf-8"))
    offenders: list[str] = []

    def _flag(dotted: str, lineno: int) -> None:
        """Flag `...web.<forbidden>`, however it is spelled."""
        parts = dotted.split(".")
        if len(parts) >= 2 and parts[-2] == "web" and parts[-1] in forbidden:
            offenders.append(f"line {lineno}: {dotted}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                _flag(a.name, node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module:
            _flag(node.module, node.lineno)
            # `from schedule_forensics.web import app` — the module is the PACKAGE here.
            if node.module.split(".")[-1] == "web":
                for a in node.names:
                    _flag(f"{node.module}.{a.name}", node.lineno)
    assert not offenders, (
        f"{module_name} imports UPWARD in the view layer, which makes the split circular. The "
        f"order is {' → '.join(reversed(LAYER_ORDER))} (each may use only what precedes it): "
        f"{offenders}"
    )


@pytest.mark.parametrize("guard_file", WHOLE_VIEW_LAYER_GUARDS)
def test_whole_view_layer_guards_actually_read_the_whole_view_layer(guard_file: str) -> None:
    """A guard claiming "nowhere in the view layer" must name EVERY view module.

    ADR-0350's near-miss, pinned so phase 4 cannot repeat it: `_stat_cards` moved into
    `components.py` while the em-dash sentinel guard still read `app.py` + `chrome.py` only. It
    kept passing — over a subject that had shrunk. Adding a view module without widening these
    guards is invisible by construction, so it fails HERE instead.
    """
    src = (Path(__file__).parent / guard_file).read_text(encoding="utf-8")
    unread = [m for m in VIEW_MODULES if f'"{m}"' not in src]
    assert not unread, (
        f"{guard_file} asserts over the view layer but never reads {unread}. Its claim is "
        "'nowhere in the view layer', so it must read all of "
        f"{list(VIEW_MODULES)} — otherwise the guard quietly stops covering the moved code."
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
