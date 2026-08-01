"""The OR-04 operator collection kit (audit §8, turnkey) keeps its safety contract.

``audit/operator-artifacts/`` is the deposit location the Ollama-lifecycle audit names for the
operator-run park-list probes (F-12/F-13/F-15/F-16/F-17/F-18), and ``collect-ollama-artifacts.ps1``
is the one-command collector for them. The script runs on the OPERATOR'S deployed Windows box —
this suite can only pin its TEXT, and that is exactly what matters: the audit's DON'T
(``ollama list`` / ``ollama run`` respawn the server and poison the probes), loopback-only
networking, read-only behavior (it must never kill or spawn anything), and the presence of each
§8 probe. The four-scenario ADR-0315 smoke, previously only in #490's PR body, must live in the
README so the acceptance script survives in-repo.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "audit" / "operator-artifacts"
README = KIT / "README.md"
SCRIPT = KIT / "collect-ollama-artifacts.ps1"

#: the §8 sha the manifest probe greps for (F-18)
SHA = "4824460d29f2058aaf6e1118a63a7a197a09bed509f0e7d4e2efb1ee273b447d"


def _script_code_lines() -> list[str]:
    """The .ps1 minus comment-only lines — the DON'T strings may appear in prose."""
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if not ln.lstrip().startswith("#")]


def test_the_kit_exists_where_the_audit_points() -> None:
    assert README.is_file() and SCRIPT.is_file()
    report = (ROOT / "audit" / "VERIFICATION-REPORT-ollama-lifecycle.md").read_text(
        encoding="utf-8"
    )
    assert "operator-artifacts" in report  # the deposit contract is two-sided


def test_readme_names_every_deposit_slot_and_the_smoke() -> None:
    text = README.read_text(encoding="utf-8")
    for slot in (
        "01-where-ollama.txt",
        "02-api-ps.json",
        "03-keepalive-override.txt",
        "04-manifest/",
        "05-runner-ppid.txt",
        "smoke-results.md",
    ):
        assert slot in text, slot
    # the four-scenario ADR-0315 smoke, in-repo instead of only in #490's PR body
    for scenario in ("A — the bug path", "B — ADR-0122 intact", "C — never used", "D — hard-kill"):
        assert scenario in text, scenario
    assert "review each" in text and "no schedule content" in text  # the commit-safety note


def test_collector_never_invokes_the_server_spawning_commands() -> None:
    """The audit's DON'T, executable: no code line runs ``ollama list`` or ``ollama run``
    (either respawns/spawns a server and poisons probes 2/3/5)."""
    code = "\n".join(_script_code_lines())
    assert "ollama list" not in code and "ollama run" not in code


def test_collector_is_loopback_only() -> None:
    """Law 1 posture for the operator's box: every URL in the script is the local Ollama API."""
    text = SCRIPT.read_text(encoding="utf-8")
    urls = re.findall(r"https?://[^\s\"')]+", text)
    assert urls, "the collector must actually call the loopback API"
    for url in urls:
        assert url.startswith("http://127.0.0.1"), url


def test_collector_is_read_only() -> None:
    """It never kills, stops, or spawns a process — collection only."""
    code = "\n".join(_script_code_lines())
    for banned in ("taskkill", "Stop-Process", "Start-Process", "Remove-Item", "Stop-Service"):
        assert banned not in code, banned


def test_collector_carries_each_section8_probe() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "where.exe ollama" in text  # §8-1 (F-16)
    assert "/api/ps" in text  # §8-2 (F-12)
    assert "keep_alive = 0" in text and "/api/generate" in text  # §8-3 (F-13/F-15)
    assert SHA in text  # §8-4 (F-18)
    assert "Win32_Process" in text and "llama-server.exe" in text  # §8-5 (F-7)
    assert "instance count" in text  # §8-5's F-17 accumulation reading
    assert "Start-Sleep -Seconds 10" in text  # §8-3's specified 10 s wait
