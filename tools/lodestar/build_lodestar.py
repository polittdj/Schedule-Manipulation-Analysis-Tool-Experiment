"""Build ``lodestar/LODESTAR.pyz`` — LODESTAR, the One-Pager Timeline and Compare as ONE file that
needs nothing but Python 3.10+ (ADR-0539). Created by David Politte (david.j.politte@nasa.gov).

Usage (from the repo root)::

    python tools/lodestar/build_lodestar.py            # (re)write lodestar/LODESTAR.pyz
    python tools/lodestar/build_lodestar.py --check    # exit 1 if the committed file is stale

Every member is a file of ``src/`` copied VERBATIM — the same bytes Polaris² runs (a text file's
line endings read as LF, so a Windows checkout builds the same archive) — named in
:data:`MODULES` / the server's static allowlist, plus exactly two members whose SOURCE is also a
file of ``src/`` but whose archive name differs: the archive's own ``__main__.py`` (from
``schedule_forensics/lodestar/_pyz_main.py``) and ``schedule_forensics/web/__init__.py`` (from
``schedule_forensics/lodestar/_pyz_web_init.py`` — Polaris²'s real one imports the whole app).

Byte-deterministic by construction, so the committed file can be held in lockstep with ``src``
by a byte comparison (``tests/lodestar/test_lodestar_pyz.py``): members STORED (no compressor
whose output could vary with the zlib build), sorted, no directory entries, a fixed timestamp, a
fixed "made on UNIX" host and fixed permissions, behind a fixed shebang. Std-lib only.

Re-run it whenever a member changes — the lockstep test names this command when it goes red.
"""

from __future__ import annotations

import argparse
import ast
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
OUT = ROOT / "lodestar" / "LODESTAR.pyz"
SHEBANG = b"#!/usr/bin/env python3\n"
_EPOCH = (1980, 1, 1, 0, 0, 0)
#: The command that rebuilds the file — printed by ``--check`` and by the lockstep test.
REBUILD = "python tools/lodestar/build_lodestar.py"

#: The Python modules LODESTAR runs, relative to ``src/`` — its archive names are the same.
MODULES: tuple[str, ...] = (
    "schedule_forensics/__init__.py",
    "schedule_forensics/reports/__init__.py",
    "schedule_forensics/reports/tableset.py",
    "schedule_forensics/reports/onepager.py",
    "schedule_forensics/reports/onepager_links.py",
    "schedule_forensics/reports/onepager_compare.py",
    "schedule_forensics/reports/pptx.py",
    "schedule_forensics/reports/xlsx.py",
    "schedule_forensics/reports/xlsx_read.py",
    "schedule_forensics/web/htmlkit.py",
    "schedule_forensics/web/security.py",
    "schedule_forensics/web/onepager_common.py",
    "schedule_forensics/web/onepager.py",
    "schedule_forensics/web/onepager_compare.py",
    "schedule_forensics/web/onepager_actions.py",
    "schedule_forensics/web/lodestar_shell.py",
    "schedule_forensics/web/lodestar_launch.py",
    "schedule_forensics/desktop_icon.py",
    "schedule_forensics/lodestar/__init__.py",
    "schedule_forensics/lodestar/__main__.py",
    "schedule_forensics/lodestar/server.py",
    "schedule_forensics/lodestar/shortcut.py",
)
#: ``archive name -> src path`` for the two members that live under another name.
RENAMED: dict[str, str] = {
    "__main__.py": "schedule_forensics/lodestar/_pyz_main.py",
    "schedule_forensics/web/__init__.py": "schedule_forensics/lodestar/_pyz_web_init.py",
}


def static_assets() -> tuple[str, ...]:
    """The server's static allowlist — the ONE list — read out of ``lodestar/server.py``'s source
    (its ``STATIC_ASSETS`` dict literal), never by importing it: importing the server would load
    Polaris²'s web package, and this tool must run anywhere the source is."""
    tree = ast.parse((SRC / "schedule_forensics/lodestar/server.py").read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(target, ast.Name) and target.id == "STATIC_ASSETS":
            if not isinstance(node.value, ast.Dict):
                break
            names = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
            return tuple(sorted(str(n) for n in names))
    raise SystemExit("lodestar/server.py has no STATIC_ASSETS dict literal")


def members() -> dict[str, Path]:
    """``archive name -> source file`` for every member, sorted by archive name."""
    out: dict[str, Path] = {name: SRC / name for name in MODULES}
    out.update({name: SRC / src for name, src in RENAMED.items()})
    for asset in static_assets():
        name = f"schedule_forensics/web/static/{asset}"
        out[name] = SRC / name
    return dict(sorted(out.items()))


#: Members read as text: a CRLF checkout (Git for Windows' autocrlf) must build the SAME archive.
_TEXT = (".py", ".js", ".css")


def _member_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix in _TEXT else data


def build() -> bytes:
    """The archive's bytes (deterministic)."""
    buf = io.BytesIO()
    buf.write(SHEBANG)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, path in members().items():
            info = zipfile.ZipInfo(name, date_time=_EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3  # "UNIX", wherever it is built
            info.external_attr = 0o644 << 16
            zf.writestr(info, _member_bytes(path))
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed pyz is stale")
    args = parser.parse_args(argv)
    data = build()
    if args.check:
        current = OUT.read_bytes() if OUT.exists() else b""
        if current != data:
            print(f"{OUT.relative_to(ROOT)} is stale — run: {REBUILD}")
            return 1
        print(f"{OUT.relative_to(ROOT)} is current ({len(data):,} bytes)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(data):,} bytes, {len(members())} members)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
