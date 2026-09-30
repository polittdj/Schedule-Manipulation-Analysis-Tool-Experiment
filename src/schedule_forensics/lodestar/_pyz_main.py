"""The ``__main__`` of LODESTAR.pyz — copied into the archive's root VERBATIM by
``tools/lodestar/build_lodestar.py`` (ADR-0539). Kept in ``src`` so lint, types and tests see it.

It does three things before LODESTAR starts, in this order:

1. refuses a Python older than 3.10, in words (not a traceback);
2. keeps ONLY the archive itself and the standard library's own directories on the import path
   — no site-packages, and no directory a ``.pth`` file added (an editable install of another
   program) — so nothing LODESTAR imports can come from another installed program: if it ever
   tried, it would fail loudly here, on the build machine's tests, rather than quietly load a
   stranger;
3. after LODESTAR's own modules are imported, checks that every module that import brought in
   is the standard library's or LODESTAR's own — and refuses to start otherwise (Law 1: a
   network client can never ride in unnoticed). Modules the interpreter loaded BEFORE this file
   ran (a site hook) are not LODESTAR's and are left alone.
"""

import os
import sys

# deliberately "outdated" for the package's floor: THIS file runs on whatever Python the operator
# double-clicked it with, and an older one must get a sentence, not a traceback
if sys.version_info < (3, 10):  # noqa: UP036
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"LODESTAR needs Python 3.10 or newer (this is {major}.{minor}).\n")
    raise SystemExit(1)

#: What the interpreter had loaded before LODESTAR's own code ran (a site hook's modules are
#: not LODESTAR's, so the check below leaves them alone).
_BEFORE = set(sys.modules)


def _standard_dirs() -> set[str]:
    """The standard library's own directories, spelled as CPython's start-up (``getpath``) puts
    them on the path — its zip, its source directory and its extension-module directory
    (``lib-dynload``; on Windows ``DLLs``, plus the install folder Windows also lists) — worked
    out from ``sys`` alone. Nothing is imported to find them: an import here would still search
    the path being cleaned (``sysconfig``, the obvious source of these names, is not loaded at
    start-up, so a PYTHONPATH entry ahead of the std-lib would supply it)."""
    major, minor = sys.version_info[:2]
    base, plat, lib = sys.base_prefix, sys.base_exec_prefix, sys.platlibdir
    dirs: list[str] = []
    if os.name == "nt":
        dirs += [os.path.join(base, "Lib"), os.path.join(plat, lib), os.path.join(plat, "DLLs")]
        dirs += [base, plat]
        for folder in (base, plat):
            dirs += [os.path.join(folder, f"python{major}{minor}{d}.zip") for d in ("", "_d")]
    else:
        # a free-threaded build ("t" in abiflags) may name its std-lib python3.Nt
        for t in ("", "t") if "t" in getattr(sys, "abiflags", "") else ("",):
            dirs += [
                os.path.join(base, lib, f"python{major}{minor}{t}.zip"),
                os.path.join(base, lib, f"python{major}.{minor}{t}"),
                os.path.join(plat, lib, f"python{major}.{minor}{t}", "lib-dynload"),
            ]
    stdlib_dir = getattr(sys, "_stdlib_dir", None)  # 3.11+: the one start-up itself computed
    if stdlib_dir:
        dirs.append(stdlib_dir)
    return {os.path.normcase(os.path.abspath(d)) for d in dirs}


def _isolate() -> None:
    """The import path becomes the archive (``sys.path[0]`` — kept whatever its folder is named)
    plus the standard library's OWN directories, each matched by its exact path — never "anything
    under the install prefix" (on a distro Python the prefix is ``/usr``, so a PYTHONPATH entry
    such as ``/usr/lib`` or ``/usr/share/…`` stayed on the path AHEAD of the std-lib; and with a
    prefix of ``/`` no std-lib directory matched at all). Everything else goes: site-packages,
    user site, a ``.pth`` file's directory (an editable install of another program), PYTHONPATH."""
    keep = _standard_dirs()
    archive, rest = sys.path[:1], sys.path[1:]
    sys.path[:] = archive + [p for p in rest if p and os.path.normcase(os.path.abspath(p)) in keep]


def _foreign(before: set[str]) -> list[str]:
    """Top-level names imported since ``before`` that are neither std-lib nor LODESTAR's."""
    allowed = set(sys.stdlib_module_names) | {"schedule_forensics", "__main__"}
    new = {name.split(".")[0] for name in set(sys.modules) - before}
    return sorted(new - allowed)


def run() -> int:
    _isolate()
    from schedule_forensics.lodestar.__main__ import main

    foreign = _foreign(_BEFORE)
    if foreign:
        sys.stderr.write(f"LODESTAR refuses to start: it loaded {', '.join(foreign)}.\n")
        return 2
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
