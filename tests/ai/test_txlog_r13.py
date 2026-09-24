"""R-13 (operator ruling 2026-09-24, ADR-0528): every AI transaction record carries a schema
version and a random per-process run id.

A reader of the log years later could not tell which record shape a line held, nor which lines
one run of the tool wrote. The operator ruled a correlation id acceptable because it carries no
CUI: ``run`` is 16 hex characters from :mod:`secrets` — no name, no path, no host, nothing
derived from the machine or the schedule — drawn once per process, and ``v`` is the record
format's version (1).

Red-first (2026-09-24): on the pristine tree a record carried neither key.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

from schedule_forensics.ai import txlog

RUN_SHAPE = re.compile(r"^[0-9a-f]{16}$")


def _write(path: Path, n: int = 2) -> list[dict[str, object]]:
    for i in range(n):
        txlog.record(
            path, kind=f"probe.{i}", endpoint="https://x.invalid", model="m", classification="c"
        )
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_every_record_carries_the_format_version_and_this_processes_run_id(
    tmp_path: Path,
) -> None:
    recs = _write(tmp_path / "log.jsonl")
    assert [r["v"] for r in recs] == [1, 1]
    runs = {r["run"] for r in recs}
    assert len(runs) == 1  # one process, one run id
    run = runs.pop()
    assert isinstance(run, str) and RUN_SHAPE.match(run)
    assert run == txlog.RUN_ID


def test_the_run_id_names_nothing_about_the_machine_or_its_user(tmp_path: Path) -> None:
    run = str(_write(tmp_path / "log.jsonl", 1)[0]["run"])
    for fact in (getpass.getuser(), socket.gethostname(), str(Path.home()), str(os.getpid())):
        assert fact.lower() not in run
    assert str(tmp_path) not in (tmp_path / "log.jsonl").read_text(encoding="utf-8")


def test_each_process_draws_its_own_run_id(tmp_path: Path) -> None:
    """Per PROCESS, not per install: two runs of the tool are told apart in one log."""
    log = tmp_path / "log.jsonl"
    code = (
        "import sys; from pathlib import Path; from schedule_forensics.ai import txlog; "
        "txlog.record(Path(sys.argv[1]), kind='k', endpoint='e', model='m', classification='c')"
    )
    for _ in range(2):
        subprocess.run([sys.executable, "-c", code, str(log)], check=True, timeout=60)
    runs = [json.loads(line)["run"] for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(runs) == 2 and runs[0] != runs[1]
    assert all(RUN_SHAPE.match(r) for r in runs)
