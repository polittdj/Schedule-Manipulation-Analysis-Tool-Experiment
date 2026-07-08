"""Every runtime subprocess spawn must be console-window-safe (ADR-0149).

The deployed desktop app runs **windowless** (``pythonw.exe`` on Windows). A child console
process spawned without ``CREATE_NO_WINDOW`` flashes a black popup window — and a probe loop
doing so every few seconds flashes it continuously from tool open to quit (operator report,
2026-07-07: the telemetry layer's ``nvidia-smi``/``powershell`` probes). ``mpp_mpxj.py`` had
already learned this lesson for the Java converter; this test generalizes it: **every**
``subprocess.run(...)`` / ``subprocess.Popen(...)`` call in ``src/schedule_forensics/`` must
pass an explicit ``creationflags`` (0 / no-op on POSIX) and an explicit ``stdin`` (a console
child inheriting an invalid console stdin handle can hang forever).
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "schedule_forensics"


def _spawn_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (
            isinstance(fn, ast.Attribute)
            and fn.attr in ("run", "Popen", "check_output", "check_call", "call")
            and isinstance(fn.value, ast.Name)
            and fn.value.id == "subprocess"
        ):
            calls.append(node)
    return calls


def test_every_subprocess_spawn_is_windowless_and_stdin_safe() -> None:
    offenders: list[str] = []
    total = 0
    for py in sorted(SRC.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for call in _spawn_calls(tree):
            total += 1
            kwargs = {kw.arg for kw in call.keywords if kw.arg}
            missing = {"creationflags", "stdin"} - kwargs
            if missing:
                rel = py.relative_to(SRC.parents[1])
                offenders.append(f"{rel}:{call.lineno} missing {sorted(missing)}")
    assert total >= 7, "expected to find the known spawn sites — AST scan broke?"
    assert not offenders, (
        "subprocess spawns without explicit creationflags/stdin — on a windowless "
        "(pythonw) deployment each spawn flashes a console popup and can hang on an "
        "inherited console handle. Add creationflags=<CREATE_NO_WINDOW-or-0> and "
        "stdin=subprocess.DEVNULL:\n" + "\n".join(offenders)
    )
