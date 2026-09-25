"""Executable red/green tests for the 2026-09-23 read-only audit: the PROCESS / TEST findings.

One test per finding id (A0923-TST-001 .. A0923-TST-013). Every test here is a VALIDATED-DEFECT
test in the sense of ``test_audit_findings.py``: it asserts the CORRECT state and FAILS (red)
against the audited commit 8c71c639 — that red is the proof the finding is real. Each is marked
``xfail(strict=True, raises=AssertionError)`` so the suite stays green today AND so a fix that
makes it pass is flagged (XPASS under strict = failure => remove the marker in the fixing commit,
and the test stands as the permanent pin).

These findings are about the project's INSTRUMENTS — skills, agents, CI files, hooks, guards. A
reproducer compares what a skill/agent/doc says against the source of truth parsed AT TEST TIME:
CI job names and steps read from ``.github/workflows/*.yml`` by a small line-based reader (no
PyYAML), ``.claude/settings.json`` read with ``json``, the pre-commit hook's behaviour measured by
running a COPY of ``.githooks/pre-commit`` in a throwaway git repository under ``tmp_path`` (the
real repository's index is never touched), node's behaviour by running the documented command in
a throwaway tree. Nothing measured by the audit is transcribed as an expectation, and a fix that
corrects or deletes the statement makes the test pass.

Scope: where the verifier narrowed the finder's scope, the verifier wins; each docstring names
what is and is not checked.

Drop-in path: tests/audit/ .  Run: pytest tests/audit/test_audit_20260923_tst.py -rA
"""

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

SRC = Path(schedule_forensics.__file__).resolve().parent
REPO = SRC.parent.parent  # .../src/schedule_forensics -> repo root
WORKFLOWS = REPO / ".github" / "workflows"
SKILLS = REPO / ".claude" / "skills"
AGENTS = REPO / ".claude" / "agents"

_NUMBER_WORDS = {
    w: n
    for n, w in enumerate(
        (
            *("zero", "one", "two", "three", "four", "five", "six"),
            *("seven", "eight", "nine", "ten", "eleven", "twelve"),
        )
    )
}


# --------------------------------------------------------------------------------------------
# helpers — documents, git, the in-process app
# --------------------------------------------------------------------------------------------
def _read(rel: str) -> str:
    """A tracked file's text; a deleted file carries no claim, so it reads as empty."""
    path = REPO / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _plain(text: str) -> str:
    """Prose as a reader sees it: blockquote and emphasis markers dropped, hard wraps joined."""
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    text = text.replace("**", "")
    return re.sub(r"\s+", " ", text)


def _number(token: str) -> int:
    token = token.strip().lower()
    return int(token) if token.isdigit() else _NUMBER_WORDS[token]


def _git_env(home: Path | None = None) -> dict[str, str]:
    """The environment for a git subprocess: no inherited GIT_* redirection (GIT_DIR, GIT_INDEX_FILE
    …) can point it at another repository, and a throwaway HOME keeps user config out."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    if home is not None:
        env.update(HOME=str(home), GIT_CONFIG_NOSYSTEM="1")
    return env


@cache
def _tracked_files() -> tuple[str, ...]:
    if shutil.which("git") is None:
        pytest.skip("git is not available; tracked-file facts cannot be read")
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=False, env=_git_env()
    )
    if proc.returncode != 0:
        pytest.skip("the tree is not a git work tree; tracked-file facts cannot be read")
    return tuple(p for p in proc.stdout.decode("utf-8").split("\0") if p)


def _load_by_path(name: str, path: Path) -> Any:
    """Load a repo module that is not importable by name (a guard test module)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _css_rules(css: str) -> list[tuple[tuple[str, ...], str, str]]:
    """(enclosing at-rule / nesting preludes, selector, declarations) for every style rule."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[tuple[str, ...], str, str]] = []
    stack: list[str] = []
    start = i = 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            prelude = css[start:i].strip()
            close, nested = css.find("}", i + 1), css.find("{", i + 1)
            close = len(css) if close == -1 else close
            if prelude.startswith("@") or (nested != -1 and nested < close):
                stack.append(prelude)
                start = i + 1
            else:
                rules.append((tuple(stack), prelude, css[i + 1 : close]))
                i, start = close, close + 1
        elif ch == "}":
            if stack:
                stack.pop()
            start = i + 1
        elif ch == ";":  # the end of a block-less at-rule statement (@import …;)
            start = i + 1
        i += 1
    return rules


def _static_css_rules() -> list[tuple[str, tuple[str, ...], str, str]]:
    return [
        (css.name, *rule)
        for css in sorted((SRC / "web" / "static").glob("*.css"))
        for rule in _css_rules(css.read_text(encoding="utf-8"))
    ]


def _globstar(pattern: str) -> re.Pattern[str]:
    """A settings glob as the docs describe it ("patterns match against absolute file paths"):
    ``**/`` spans zero or more directories, ``**`` anything, ``*`` / ``?`` stay within one."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out)


# --------------------------------------------------------------------------------------------
# helpers — a line-based reader of the GitHub-workflow subset the CI files use (no PyYAML)
# --------------------------------------------------------------------------------------------
@dataclasses.dataclass
class _Job:
    id: str
    name: str | None = None
    matrix: dict[str, list[str]] = dataclasses.field(default_factory=dict)
    runs: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class _Workflow:
    pull_request: bool = False
    pr_paths: list[str] | None = None  # None = no paths filter
    jobs: list[_Job] = dataclasses.field(default_factory=list)


def _yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _yaml_uncomment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or line[i - 1] in " :[,"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _yaml_items(text: str) -> list[tuple[int, str, str | None]]:
    """(indent, content, block-scalar text or None), comments and blank lines dropped."""
    lines = text.splitlines()
    out: list[tuple[int, str, str | None]] = []
    i = 0
    while i < len(lines):
        line = _yaml_uncomment(lines[i])
        if not line.strip():
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if re.match(r"(?:- )?[\w.-]+:\s*[|>][-+]?$", content):
            key_indent = indent + (2 if content.startswith("- ") else 0)
            j, block = i + 1, []
            while j < len(lines) and (
                not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip(" ")) > key_indent
            ):
                block.append(lines[j])
                j += 1
            out.append((indent, content, "\n".join(block)))
            i = j
            continue
        out.append((indent, content, None))
        i += 1
    return out


def _workflow(path: Path) -> _Workflow:
    wf = _Workflow()
    section = ""
    in_pr = in_paths = False
    job: _Job | None = None
    matrix_indent: int | None = None
    axis = ""
    for indent, content, block in _yaml_items(path.read_text(encoding="utf-8")):
        if indent == 0:
            key, _, rest = content.partition(":")
            section = _yaml_scalar(key)
            if section == "on" and rest.strip():  # `on: [push, pull_request]`
                wf.pull_request = "pull_request" in rest
            continue
        if section == "on":
            if indent == 2:
                in_pr = content.split(":")[0] == "pull_request"
                in_paths = False
                wf.pull_request = wf.pull_request or in_pr
            elif in_pr and indent == 4:
                in_paths = content.startswith("paths:")
                if in_paths:
                    wf.pr_paths = []
            elif in_pr and in_paths and content.startswith("- ") and wf.pr_paths is not None:
                wf.pr_paths.append(_yaml_scalar(content[2:]))
        elif section == "jobs":
            if indent == 2 and content.endswith(":"):
                job = _Job(content[:-1])
                wf.jobs.append(job)
                matrix_indent = None
                continue
            if job is None:
                continue
            if matrix_indent is not None and indent <= matrix_indent:
                matrix_indent = None
            if indent == 4 and content.startswith("name:"):
                job.name = _yaml_scalar(content.split(":", 1)[1])
            elif content == "matrix:":
                matrix_indent = indent
            elif matrix_indent is not None and indent == matrix_indent + 2 and ":" in content:
                axis, _, val = (s.strip() for s in content.partition(":"))
                values = val.strip("[]").split(",") if val.startswith("[") else []
                job.matrix[axis] = [_yaml_scalar(v) for v in values if v.strip()]
            elif matrix_indent is not None and content.startswith("- ") and axis in job.matrix:
                job.matrix[axis].append(_yaml_scalar(content[2:]))
            run = re.match(r"(?:- )?run:\s*(.*)$", content)
            if run:
                job.runs.append(block if block is not None else run.group(1))
    return wf


def _contexts(job: _Job) -> list[str]:
    """The check-run names GitHub posts for a job: its name (matrix values substituted, or
    appended in parentheses) or, unnamed, its id plus the matrix values."""
    if not job.matrix:
        return [job.name or job.id]
    out = []
    for combo in itertools.product(*job.matrix.values()):
        name = job.name or job.id
        if "${{" in name:
            for key, value in zip(job.matrix, combo, strict=True):
                name = re.sub(r"\$\{\{\s*matrix\." + re.escape(key) + r"\s*\}\}", value, name)
            out.append(name)
        else:
            out.append(f"{name} ({', '.join(combo)})")
    return out


def _workflows() -> dict[str, _Workflow]:
    return {p.name: _workflow(p) for p in sorted(WORKFLOWS.glob("*.yml"))}


# --------------------------------------------------------------------------------------------
# A0923-TST-001
# --------------------------------------------------------------------------------------------
def _documented_node_checks() -> list[tuple[str, str]]:
    """(where, command) for every node --check invocation CLAUDE.md and the steward skill print —
    a fenced line (joined with its enclosing `for … done` loop) or an inline code span that
    carries arguments (a bare mention of the flag is not a command)."""
    out: list[tuple[str, str]] = []
    for rel in ("CLAUDE.md", ".claude/skills/steward/SKILL.md"):
        lines = _read(rel).splitlines()
        fence_start: int | None = None
        for n, line in enumerate(lines):
            if line.lstrip().startswith("```"):
                fence_start = n if fence_start is None else None
                continue
            if "node --check" not in line:
                continue
            if fence_start is not None:
                cmd = line.strip()
                if "done" not in cmd:  # a multi-line loop: take it whole, within this fence
                    block_end = next(
                        (k for k in range(n, len(lines)) if lines[k].lstrip().startswith("```")),
                        len(lines),
                    )
                    first = next(
                        (
                            k
                            for k in range(n, fence_start, -1)
                            if lines[k].lstrip().startswith("for ")
                        ),
                        n,
                    )
                    last = next((k for k in range(n, block_end) if "done" in lines[k]), n)
                    cmd = "\n".join(lines[first : last + 1]) if first < n else cmd
                out.append((f"{rel}:{n + 1}", cmd))
            else:
                for span in re.findall(r"`([^`]*node --check[^`]*)`", line):
                    if span.strip() != "node --check":
                        out.append((f"{rel}:{n + 1}", span.strip()))
    return out


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-001: the documented `node --check static/*.js` gate checks only the first "
    "file and passes a tree whose later file is broken",
)
def test_a0923_tst_001_documented_node_check_catches_a_broken_later_file(tmp_path: Path) -> None:
    """Every documented ``node --check`` gate command must report a syntax error in ANY file.

    Claim (A0923-TST-001): at 8c71c639 the documented gate step
    ``node --check src/schedule_forensics/web/static/*.js`` exits 0 on a tree whose later file
    carries a syntax error — node treats every argument after the first script as an argument
    to it (``node [options] [ script.js ] [arguments]``), so only the first glob match is checked.
    Authority (verbatim): CLAUDE.md:181 "Full gate — run before every commit." and :189 "node
    --check src/schedule_forensics/web/static/*.js    # vendored JS, no build step";
    .claude/skills/steward/SKILL.md:98 "`node --check src/schedule_forensics/web/static/*.js` (each
    file)". Checked: each documented command, run by bash in a throwaway tree whose
    static/ holds a good ``a_ok.js`` and a broken ``z_bad.js``; it must exit non-zero or name the
    broken file. Needs node and bash (skipped without them). Tier T5.
    """
    if shutil.which("node") is None or shutil.which("bash") is None:
        pytest.skip("node and bash are needed to run the documented command")
    static = tmp_path / "src" / "schedule_forensics" / "web" / "static"
    static.mkdir(parents=True)
    (static / "a_ok.js").write_text("var ok = 1;\n", encoding="utf-8")
    (static / "z_bad.js").write_text("function broken( {\n", encoding="utf-8")
    missed = []
    for where, cmd in _documented_node_checks():
        proc = subprocess.run(
            ["bash", "-c", cmd], cwd=tmp_path, capture_output=True, text=True, timeout=120
        )
        if proc.returncode == 0 and "z_bad.js" not in proc.stdout + proc.stderr:
            missed.append(f"{where}: `{cmd}` exits 0 and never names z_bad.js")
    assert not missed, "; ".join(missed)


# --------------------------------------------------------------------------------------------
# A0923-TST-002
# --------------------------------------------------------------------------------------------
def _ruff_check_paths(commands: str) -> list[list[str]]:
    return [
        m.group(1).split()
        for m in re.finditer(r"(?m)^\s*(?:python3? -m )?ruff check((?: [^\s#;|&]+)*)", commands)
    ]


def _covers(scope: list[str], path: str) -> bool:
    norm = [s.rstrip("/").removeprefix("./") or "." for s in scope]
    path = path.rstrip("/").removeprefix("./") or "."
    return any(s == "." or path == s or path.startswith(s + "/") for s in norm)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-002: the qc-checker's 'full gate' lints `src/ tests/` while CI lints the "
    "whole tree",
)
def test_a0923_tst_002_qc_checker_lints_at_least_what_ci_lints() -> None:
    """The qc-checker's ruff scope must cover every path CI's ruff step lints.

    Claim (A0923-TST-002): at 8c71c639 the qc-checker's ``ruff check src/ tests/`` lints 710 files
    while CI's ``ruff check .`` lints 719 (tools/, packaging/, pyproject.toml), so a planted error
    in tools/intake_manifest.py passes the agent and fails CI — the exact failure ADR-0347:145-152
    recorded. Authority (verbatim): .claude/agents/qc-checker.md:20 "## 1. Run the full gate" and
    :25 "ruff check src/ tests/"; .claude/agents/README.md:9 "Runs the full gate (ruff · ruff
    format · mypy · bandit · pytest · `node --check` · the"; the source of truth,
    .github/workflows/ci.yml:50-51 "- name: Lint (ruff)" / "run: ruff check .". Checked: every CI
    ``ruff check`` path must lie inside the agent's scope. Tier T5.
    """
    ci_scopes = [
        scope or ["."]
        for wf in _workflows().values()
        for job in wf.jobs
        for run in job.runs
        for scope in _ruff_check_paths(run)
    ]
    agent = _read(".claude/agents/qc-checker.md")
    agent_scopes = [scope or ["."] for scope in _ruff_check_paths(agent)]
    uncovered = [
        (" ".join(agent_scope), path)
        for agent_scope in agent_scopes
        for ci_scope in ci_scopes
        for path in ci_scope
        if not _covers(agent_scope, path)
    ]
    assert not uncovered, f"the qc-checker's ruff scope misses what CI lints: {uncovered}"


# --------------------------------------------------------------------------------------------
# A0923-TST-004
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-004: session-close says SEVEN checks (no cui-guard) and FOUR outside "
    "installer paths; the workflows post 8 and 6",
)
def test_a0923_tst_004_session_close_check_set_is_the_workflows() -> None:
    """session-close §8's check set and counts must be the contexts the workflows post on a PR.

    Claim (A0923-TST-004): at 8c71c639 ci.yml posts 6 check contexts (test (3.11), test (3.13),
    browser, floor, cui-guard, check) and installer-smoke.yml 2 (windows, linux, path-filtered to
    the installers) = 8 on an installer PR, 6 otherwise. Authority (verbatim),
    .claude/skills/session-close/SKILL.md:125-131 "On a PR that touches the installers,
    **seven** checks must go green: `check` · `floor (declared minimum)` · `linux` · `windows` ·
    `browser (measured-box proof)` · `test (3.11)` · `test (3.13)`. ... so a PR outside those
    paths legitimately shows **four**." Checked: the stated counts and the listed names against
    the contexts derived from .github/workflows/*.yml (job name or id, matrix expanded; a
    workflow counts for an installer PR when its pull_request paths filter admits an installer
    file). Tier T5.
    """
    installer_file = next(
        (p.relative_to(REPO).as_posix() for p in sorted((REPO / "installer").glob("*"))),
        "installer/x",
    )
    on_installer_pr: list[str] = []
    elsewhere: list[str] = []
    for wf in _workflows().values():
        if not wf.pull_request:
            continue
        contexts = [c for job in wf.jobs for c in _contexts(job)]
        if wf.pr_paths is None:
            elsewhere += contexts
        if wf.pr_paths is None or any(_globstar(p).fullmatch(installer_file) for p in wf.pr_paths):
            on_installer_pr += contexts
    text = _plain(_read(".claude/skills/session-close/SKILL.md"))
    wrong: list[str] = []
    m = re.search(
        r"On a PR that touches the installers, (\w+) checks must go green: "
        r"((?:`[^`]+`(?: · )?)+)",
        text,
    )
    if m:
        listed = re.findall(r"`([^`]+)`", m.group(2))
        if _number(m.group(1)) != len(on_installer_pr):
            wrong.append(
                f"'{m.group(1)}' checks on an installer PR; workflows post {len(on_installer_pr)}"
            )
        named = {c for c in on_installer_pr for d in listed if c == d or c.startswith(d + " (")}
        if named != set(on_installer_pr) or len(listed) != len(named):
            wrong.append(f"listed {listed}; workflows post {on_installer_pr}")
    m = re.search(r"a PR outside those paths legitimately shows (\w+)", text)
    if m and _number(m.group(1)) != len(elsewhere):
        wrong.append(f"'{m.group(1)}' outside installer paths; workflows post {len(elsewhere)}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-005
# --------------------------------------------------------------------------------------------
def _modules_run(job: _Job) -> set[str]:
    """The test modules a job's `pytest` steps run — explicit paths, and a shell variable set
    from a `$(python tools/….py)` census, which is executed here exactly as CI executes it."""
    modules: set[str] = set()
    for run in job.runs:
        computed: dict[str, list[str]] = {}
        for var, cmd in re.findall(r'(\w+)="\$\((python3? [^)]*)\)"', run):
            out = subprocess.run(
                [sys.executable, *cmd.split()[1:]],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            computed[var] = out.stdout.split()
        for line in run.splitlines():
            if not re.match(r"\s*(?:python3? -m )?pytest\b", line):
                continue
            for token in line.split():
                if token.startswith("$") and token[1:] in computed:
                    modules.update(computed[token[1:]])
                elif re.fullmatch(r"tests/\S+\.py", token):
                    modules.add(token)
    return modules


def _parity_collected() -> int:
    """``pytest --collect-only -m parity`` in a child process, exactly the skill's command. The
    child gets no coverage / route-coverage / addopts plumbing from this run, so it measures
    collection only and writes nothing into the tree."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("COV_CORE_", "PYTEST_")) and k != "SF_ROUTE_COVERAGE"
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            "parity",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
        env=env,
    )
    m = re.search(r"(\d+)(?:/\d+)? tests? collected", proc.stdout)
    if m is None:
        pytest.fail(
            f"could not read the parity collection: {proc.stdout[-500:]}{proc.stderr[-500:]}"
        )
    return int(m.group(1))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-005: full-gate's CI model is stale — browser job 'only r11', tip family run "
    "by no CI job, parity '49 tests', CI resolves 'ruff>=0.6'",
)
def test_a0923_tst_005_full_gate_ci_model_is_the_workflows() -> None:
    """The full-gate skill's four statements about CI must match ci.yml, pyproject and pytest.

    Claim (A0923-TST-005): at 8c71c639 CI's browser job runs ``pytest -q $(python
    tools/browser_modules.py)`` (55 modules incl. both tip-family modules) plus the LibreOffice
    interop test, ``pytest -m parity`` collects 249 tests, and pyproject bounds ruff to
    >=0.16.1,<0.17. Authority (verbatim), .claude/skills/full-gate/SKILL.md:114
    "| `browser (measured-box proof)` | `.[dev,browser]` | **only**
    `tests/web/test_r11_panel_contract.py` |"; :116-117 "~19 browser tests start executing that
    **no CI job ever runs** — including the tip family above"; :69 "python -m pytest -m parity
    # the Law-2 acceptance gate (~250 s, 49 tests)"; :34-35 "**fails CI**, which resolves
    `ruff>=0.6` to the latest".
    Checked: the named job's modules (its census executed as CI executes it), the tip-family
    modules against every job that installs the browser extra, a ``--collect-only -m parity``
    subprocess, and pyproject's ruff requirement. The '~250 s' timing is not measured. Tier T5.
    """
    raw = _read(".claude/skills/full-gate/SKILL.md")
    text = _plain(raw)
    jobs = [job for wf in _workflows().values() for job in wf.jobs]
    wrong: list[str] = []
    for ctx, only in re.findall(r"(?m)^\| `([^`]+)` \| `[^`]*` \| \*\*only\*\* `([^`]+)` \|", raw):
        job = next((j for j in jobs if ctx in _contexts(j)), None)
        runs = _modules_run(job) if job else set()
        if runs != {only}:
            wrong.append(f"'{ctx}' runs only {only}: it runs {len(runs)} modules")
    tip = re.search(r"tip family \(((?:`[^`]+`(?:, )?)+)\)", text)
    if tip and "no CI job ever runs" in text:
        family = set(re.findall(r"`([^`]+)`", tip.group(1)))
        browser_jobs = [j for j in jobs if any(".[dev,browser]" in r for r in j.runs)]
        executed = set().union(*(_modules_run(j) for j in browser_jobs)) if browser_jobs else set()
        if family & executed:
            wrong.append(
                f"'no CI job ever runs' the tip family; CI runs {sorted(family & executed)}"
            )
    count = re.search(r"pytest -m parity[ \t]+#[^\n]*?(\d[\d,]*) tests\b", raw)
    if count:
        collected = _parity_collected()
        if int(count.group(1).replace(",", "")) != collected:
            wrong.append(f"'-m parity' is '{count.group(1)} tests'; pytest collects {collected}")
    spec = re.search(r"which resolves `(ruff[^`]*)` to the latest", text)
    if spec:
        extras = tomllib.loads(_read("pyproject.toml"))["project"].get("optional-dependencies", {})
        declared = {
            r.replace(" ", "") for reqs in extras.values() for r in reqs if r.startswith("ruff")
        }
        if spec.group(1).replace(" ", "") not in declared:
            wrong.append(f"CI resolves `{spec.group(1)}`; pyproject declares {sorted(declared)}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-006
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-006: qc-checker/full-gate wave through skips for tracked Project2/5.mpp "
    "'CUI intake' and an 'openpyxl not installed' skip no test has",
)
def test_a0923_tst_006_triage_lists_name_only_real_env_gated_skips() -> None:
    """Each 'expected env-gated skip' the triage lists name must be able to happen for that reason.

    Claim (A0923-TST-006): at 8c71c639 00_REFERENCE_INTAKE/mpp/Project2.mpp and Project5.mpp are
    tracked (so present in every checkout; non-CUI per CLAUDE.md:18-24) and no test carries an
    'openpyxl not installed' skip, yet both triage lists tell the triager these skips are expected.
    Authority (verbatim): .claude/agents/qc-checker.md:42-43 "- pytest `SKIPPED` for missing CUI
    intake files (`Project2.mpp`, `Project5.mpp`, real `.mpp`/`.xlsx`) or "no Java runtime" /
    "openpyxl not installed" — these are deliberately env-gated.";
    .claude/skills/full-gate/SKILL.md:98-99 "- `SKIPPED` for missing CUI intake (`Project2.mpp`,
    `Project5.mpp`, real
    `.mpp`/`.xlsx`), "no Java runtime", "openpyxl not installed", "playwright not installed" —
    deliberately env-gated." Checked: a named intake file must not be tracked; a named "X not
    installed" reason must exist as a skip in tests/ (importorskip / find_spec / the reason text).
    The generic "real .mpp/.xlsx" clause and the paraphrased "no Java runtime" are not checked.
    Tier T5.
    """
    tracked = _tracked_files()
    this_module = Path(__file__).resolve()
    test_texts = [
        p.read_text(encoding="utf-8")
        for p in (REPO / "tests").rglob("*.py")
        if p.resolve() != this_module
    ]
    wrong: list[str] = []
    for rel in (".claude/agents/qc-checker.md", ".claude/skills/full-gate/SKILL.md"):
        text = _plain(_read(rel))
        for m in re.finditer(r"SKIPPED` for missing CUI intake(?: files)? \(([^)]*)\)", text):
            for name in re.findall(r"`([^`./][^`]*\.\w+)`", m.group(1)):
                copies = [p for p in tracked if Path(p).name == name]
                if copies:
                    wrong.append(f"{rel}: '{name}' is tracked ({copies[0]}) so cannot go missing")
        bullet = re.search(r"SKIPPED` for missing CUI intake.*?deliberately env-gated", text)
        for module in re.findall(r'"(\w+) not installed"', bullet.group(0) if bullet else ""):
            pattern = re.compile(  # a skip construct, not a mention in prose
                rf"importorskip\(\s*['\"]{module}['\"]|find_spec\(\s*['\"]{module}['\"]"
                rf"|(?:skip\(|reason\s*=)\s*[rbuf]*['\"][^'\"]*{module} (?:is )?not installed",
                re.I,
            )
            if not any(pattern.search(t) for t in test_texts):
                wrong.append(f"{rel}: no test skips with '{module} not installed'")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-007
# --------------------------------------------------------------------------------------------
def _split_depth0(text: str, seps: str) -> list[str]:
    """Split at separator characters that sit outside every parenthesis."""
    parts, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and ch in seps:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return [*parts, cur]


def _subject(selector: str) -> str:
    """The compound selector a rule styles: the last one, with its :not(…)/:has(…) arguments
    dropped — those name other elements, not the one the declarations land on."""
    parts = [p for p in _split_depth0(selector.strip(), " \t\n>+~") if p]
    subject = parts[-1] if parts else ""
    previous = None
    while previous != subject:
        previous, subject = subject, re.sub(r"\([^()]*\)", "", subject)
    return subject


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-007: render-verify/ui-change teach the pre-ADR-0305 `.is-big` and the "
    "pre-ADR-0461 chartframe.js load order",
)
def test_a0923_tst_007_skills_describe_the_shipped_ui_mechanisms() -> None:
    """The skills' `.is-big` and chartframe.js mechanism statements must match the shipped UI.

    Claim (A0923-TST-007): at 8c71c639 base.css:675-677 gives a non-tile ``.panel.is-big``
    ``position:fixed;inset:3vh 12px`` (the ADR-0305 focus overlay) and the layout loads
    chartframe.js synchronously in <head> (ADR-0461). Authority (verbatim):
    .claude/skills/render-verify/SKILL.md:81-82 "A class read-back is **not** a proof — `.is-big`
    is only `grid-column:1/-1`, so on a block-layout panel it is inert while the assertion passes
    (ADR-0304)."; .claude/skills/ui-change/SKILL.md:73-74 "`.is-big` is only `grid-column:1/-1`,
    inert on a block-layout panel"; :46 "| Data-date line | `SFGantt.dataDateLine`, styled by
    `.ch-dd` | ADR-0342 — most charted pages draw at parse time, before `chartframe.js` exists |".
    Checked: every declaration a shipped stylesheet (print media excluded) puts on the `.is-big`
    element itself; the served landing page's chartframe.js <script> against </head> and <main>.
    Tier T5.
    """
    wrong: list[str] = []
    only_grid = r"`\.is-big` is only `grid-column:1/-1`"
    stating = [
        rel
        for rel in (".claude/skills/render-verify/SKILL.md", ".claude/skills/ui-change/SKILL.md")
        if re.search(only_grid, _plain(_read(rel)))
    ]
    if stating:
        extra = sorted(
            f"{name}: {selector.strip()} {{{body.strip()}}}"
            for name, context, selector, body in _static_css_rules()
            if not any(c.startswith("@media print") for c in context)
            for sel in _split_depth0(selector, ",")
            if ".is-big" in _subject(sel)
            and {d.split(":", 1)[0].strip() for d in body.split(";") if ":" in d} - {"grid-column"}
        )
        if extra:
            wrong.append(f"{stating} say `.is-big` is only grid-column:1/-1; shipped: {extra[:2]}")
    ui_change = _plain(_read(".claude/skills/ui-change/SKILL.md"))
    if re.search(r"draw at parse time, before `chartframe\.js` exists", ui_change):
        page = TestClient(create_app(SessionState())).get("/").text
        tag = re.search(r"<script\b[^>]*src=\"?/static/chartframe\.js[^>]*>", page)
        head_end, main = page.find("</head>"), page.find("<main")
        parse_time = tag is not None and not re.search(r"\b(?:defer|async)\b", tag.group(0))
        if tag and parse_time and tag.start() < head_end and (main == -1 or tag.start() < main):
            wrong.append(
                f"ui-change: charts draw before chartframe.js exists; <head> loads it: {tag[0]}"
            )
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-008
# --------------------------------------------------------------------------------------------
_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
_PAINT_ATTR = re.compile(
    r"\b(style|fill|stroke|stop-color|color)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-008: 'a hex value in page markup is a build failure', yet /analysis and "
    "/sra serve hex fallbacks and nothing fails",
)
def test_a0923_tst_008_page_markup_carries_no_hex_when_that_is_a_build_failure() -> None:
    """If the rulebook calls a markup hex a build failure, the pages must serve none.

    Claim (A0923-TST-008): at 8c71c639 rendering /analysis/<TP1> and /sra in-process serves
    ``var(--sf-accent,#2a7)`` and ``var(--sf-border,#888)`` x2 in page markup, neither token is
    defined in any shipped CSS (so the hex always paints), and no build step fails. Authority
    (verbatim): docs/DESIGN-SYSTEM.md:13-15 and .claude/skills/ui-change/SKILL.md:13-15 "A hex
    value in page markup is a build failure (exceptions: the fixed CUI marking colors and the
    risk-heat band colors)." Checked: while either statement stands, the style / paint
    attributes of the two named pages (TP1 uploaded) carry no hex outside the exception palette,
    which is read at test time from the shipped CSS (the ``.cui-banner`` and ``.rk-*`` rules).
    Tier T5.
    """
    stating = [
        rel
        for rel in ("docs/DESIGN-SYSTEM.md", ".claude/skills/ui-change/SKILL.md")
        if "A hex value in page markup is a build failure" in _plain(_read(rel))
    ]
    if not stating:
        return  # the rule is gone: nothing left to be false
    exempt = {
        h.lower()
        for _name, _ctx, selector, body in _static_css_rules()
        if re.search(r"cui|\.rk-", selector)
        for h in _HEX.findall(body)
    }
    state = SessionState()
    client = TestClient(create_app(state))
    tp1 = REPO / "tests" / "fixtures" / "test_projects" / "TP1_Library_Progressed.xml"
    client.post("/upload", files={"files": (tp1.name, tp1.read_bytes(), "text/xml")})
    key = next(iter(state.schedules))
    found = []
    for route in (f"/analysis/{key}", "/sra"):
        html = client.get(route).text
        for attr, value in _PAINT_ATTR.findall(html):
            found += [(route, attr, h) for h in _HEX.findall(value) if h.lower() not in exempt]
    assert not found, f"{stating} call a markup hex a build failure; served: {found}"


# --------------------------------------------------------------------------------------------
# A0923-TST-009
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-009: session-close/steward/skills-README point at a 4-line header, an 'ASK "
    "FIRST' list and '3,000 lines' that no longer exist",
)
def test_a0923_tst_009_skill_pointers_into_state_docs_hold() -> None:
    """The three structural pointers the skills give into the state docs must hold on the tree.

    Claim (A0923-TST-009): at 8c71c639 HANDOFF-ARCHIVE.md's first archived section starts at line
    4 (a 3-line header), NEXT-SESSION-PROMPT.md holds no 'ASK FIRST' list, and LESSONS-LEARNED.md
    is 8,733 lines. Authority (verbatim): .claude/skills/session-close/SKILL.md:37-38 "**Prepend**
    it to `docs/STATE/HANDOFF-ARCHIVE.md`, immediately after that file's 4-line header";
    .claude/skills/steward/SKILL.md:131 "(the "ASK FIRST" list in
    `docs/STATE/NEXT-SESSION-PROMPT.md`)"; .claude/skills/README.md:24 "3,000 lines of
    `docs/STATE/LESSONS-LEARNED.md`". Checked: the header length (lines before the first
    ``# (prior)`` heading), the list's presence (any spelling), and the line count — the README's
    figure is a round approximation, so it must be within 10 % of ``wc -l``. Tier T5.
    """
    wrong: list[str] = []
    close = _plain(_read(".claude/skills/session-close/SKILL.md"))
    archive = _read("docs/STATE/HANDOFF-ARCHIVE.md").splitlines()
    first = next((i for i, ln in enumerate(archive) if ln.startswith("# (prior)")), None)
    for m in re.finditer(
        r"HANDOFF-ARCHIVE\.md`, immediately after that file's (\d+)-line header", close
    ):
        if first is not None and int(m.group(1)) != first:
            wrong.append(f"session-close: a {m.group(1)}-line header; the archive's is {first}")
    steward = _plain(_read(".claude/skills/steward/SKILL.md"))
    prompt = _read("docs/STATE/NEXT-SESSION-PROMPT.md")
    pointer = r"the \"ASK FIRST\" list in `docs/STATE/NEXT-SESSION-PROMPT\.md`"
    if re.search(pointer, steward) and not re.search(r"ask[-_ ]?first", prompt, re.I):
        wrong.append("steward: the 'ASK FIRST' list is not in NEXT-SESSION-PROMPT.md")
    readme = _plain(_read(".claude/skills/README.md"))
    lessons = (REPO / "docs" / "STATE" / "LESSONS-LEARNED.md").read_bytes().count(b"\n")
    for m in re.finditer(r"([\d,]+) lines of `docs/STATE/LESSONS-LEARNED\.md`", readme):
        stated = int(m.group(1).replace(",", ""))
        if abs(stated - lessons) > 0.10 * lessons:
            wrong.append(f"skills README: {m.group(1)} lines of LESSONS-LEARNED; wc -l {lessons}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-010
# --------------------------------------------------------------------------------------------
def _scratch_git(repo: Path, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_git_env(home),
    )


def _hook_verdicts(tmp_path: Path, probes: list[tuple[str, bytes]]) -> dict[str, bool]:
    """Stage each probe ALONE in a throwaway repo under tmp_path and run a COPY of the real
    pre-commit hook; True = blocked. `ref/inherited.mpp` and `ref/tampered.mpp` are committed to a
    fake origin/main first, so the inherited-blob allowance is live (and a modified upstream file
    is testable); the real repository is never touched."""
    repo, home = tmp_path / "scratch", tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    hook = repo / ".githooks" / "pre-commit"
    hook.parent.mkdir()
    shutil.copy2(REPO / ".githooks" / "pre-commit", hook)
    _scratch_git(repo, home, "init", "-q", "-b", "main")
    _scratch_git(repo, home, "config", "user.email", "audit@example.invalid")
    _scratch_git(repo, home, "config", "user.name", "audit")
    (repo / "ref").mkdir()
    for upstream in ("inherited.mpp", "tampered.mpp"):
        (repo / "ref" / upstream).write_bytes(b"upstream-bytes")
        _scratch_git(repo, home, "add", "-f", f"ref/{upstream}")
    _scratch_git(repo, home, "commit", "-q", "--no-verify", "-m", "upstream")
    _scratch_git(repo, home, "update-ref", "refs/remotes/origin/main", "main")
    _scratch_git(repo, home, "checkout", "-q", "--orphan", "work")
    verdicts: dict[str, bool] = {}
    for name, body in probes:
        _scratch_git(repo, home, "rm", "-rq", "--cached", "--ignore-unmatch", ".")
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        _scratch_git(repo, home, "add", "-f", "--", name)
        staged = _scratch_git(repo, home, "diff", "--cached", "--name-only").stdout.split("\n")
        assert [s for s in staged if s] == [name], f"scratch index holds {staged} (not {name})"
        proc = subprocess.run(
            ["bash", str(hook)], cwd=repo, capture_output=True, text=True, env=_git_env(home)
        )
        verdicts[name] = proc.returncode != 0
    return verdicts


def _section_one(text: str) -> str:
    """cui-guard's rule statement: its '## 1.' section up to the first '###' subsection."""
    parts = re.split(r"(?m)^## ", text)
    one = next((p for p in parts if p.startswith("1.")), "")
    return one.split("\n### ", 1)[0]


def _named_allowance(name: str, named: set[str], hook_prefixes: list[str]) -> bool:
    """Does a doc-named allowance (full or trailing form, e.g. `web/examples/`) cover ``name``?"""
    full = [p for p in hook_prefixes if any(p.endswith(t) for t in named)]
    return any(name.startswith(p) for p in [*full, *named])


def _hook_allow_prefixes() -> list[str]:
    text = _read(".githooks/pre-commit")
    block = (
        text.split("allow_prefixes=(", 1)[1].split(")", 1)[0] if "allow_prefixes=(" in text else ""
    )
    return re.findall(r"'([^']+/)'", block)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is needed to run the hook copy")
@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is needed to run the hook copy")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-010: cui-guard §1 and README.md:133 describe the pre-ADR-0347 guard; the "
    "real hook blocks and allows differently",
)
def test_a0923_tst_010_cui_guard_docs_predict_what_the_hook_does(tmp_path: Path) -> None:
    """The guard model the cui-guard skill and the README state must predict the real hook.

    Claim (A0923-TST-010): at 8c71c639 a copy of .githooks/pre-commit run in a scratch repo blocks
    data.mpp.bak, sched.mpp.zip, plan.p6xml, book.xlsm and a plan.json carrying the Save-format
    signature, and allows src/schedule_forensics/web/examples/foo.mpp (ADR-0347/0399), while the
    docs state the older model. Authority (verbatim), .claude/skills/cui-guard/SKILL.md:13-21 "The
    pre-commit guard (`.githooks/pre-commit`, activated by the SessionStart hook) blocks staged
    files matching `.(mpp|mpt|mpx|xer|xml|pmxml|csv|xls|xlsx|pbix|mspdi|pkl|pickle|aft|docx|doc)$`
    with exactly **two** exceptions: 1. **`tests/fixtures/`** ... 2. **`inherited_from_main`**";
    README.md:132-134 "the pre-commit guard blocks `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` outside the
    committed reference set and the `tests/fixtures/` synthetic allowlist." Checked (probes staged
    one at a time; the skill's printed pattern is read as the file extension it transcribed, i.e.
    with its leading dot escaped): the skill's pattern + named allowances + content-sniff mention
    must predict every probe; its stated number of exceptions must equal the hook's; the README
    must name every allowance under which the hook admits a blocked extension. Tier T5.
    """
    save_format = (SRC / "web" / "examples" / "house_build.json").read_bytes()
    prefixes = _hook_allow_prefixes()
    probes: list[tuple[str, bytes]] = [
        ("foo.mpp", b"x"),
        *((f"{p}foo.mpp", b"x") for p in prefixes),
        ("data.mpp.bak", b"x"),
        ("sched.mpp.zip", b"x"),
        ("plan.p6xml", b"x"),
        ("book.xlsm", b"x"),
        ("notes.pdf", b"x"),
        ("readme.md", b"# notes\n"),
        ("plan.json", save_format),
        ("ref/inherited.mpp", b"upstream-bytes"),
        ("ref/tampered.mpp", b"TAMPERED-bytes"),
    ]
    hook = _hook_verdicts(tmp_path, probes)
    admitted_prefixes = [p for p in prefixes if not hook[f"{p}foo.mpp"]]
    allowances = len(admitted_prefixes) + (not hook["ref/inherited.mpp"])
    wrong: list[str] = []

    skill = _plain(_section_one(_read(".claude/skills/cui-guard/SKILL.md")))
    pattern = re.search(r"blocks staged files matching `([^`]+)`", skill)
    named = set(re.findall(r"`([\w./-]+/)`", skill))
    if pattern:
        regex = re.compile(re.sub(r"^\.\(", r"\\.(", pattern.group(1)), re.I)
        sniffs = bool(re.search(r"sniff|signature", skill, re.I))
        inherited = "inherited_from_main" in skill
        for name, body in probes:
            allowed = _named_allowance(name, named, prefixes) or (
                inherited and name == "ref/inherited.mpp"
            )
            by_content = sniffs and body == save_format
            predicted = (bool(regex.search(name)) or by_content) and not allowed
            if predicted != hook[name]:
                wrong.append(f"skill predicts {name} {'BLOCK' if predicted else 'ALLOW'}")
    count = re.search(r"with exactly (\w+) exceptions", skill)
    if count and _number(count.group(1)) != allowances:
        wrong.append(f"skill: exactly {count.group(1)} exceptions; the hook has {allowances}")
    readme = _plain(_read("README.md"))
    stated = re.search(r"the pre-commit guard blocks (.+?) outside (.+?)\.", readme)
    if stated:
        readme_named = set(re.findall(r"`([\w./-]+/)`", stated.group(2)))
        missing = [p for p in admitted_prefixes if not any(p.endswith(t) for t in readme_named)]
        if missing:
            wrong.append(f"README omits the hook's allowance(s) {missing}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-TST-011
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-011: the EVM2 residual pin's docstring says UID 25's material window is "
    "read; booking_span_driven == (23,)",
)
def test_a0923_tst_011_evm2_residual_docstring_names_the_windows_the_engine_reads() -> None:
    """The UIDs the residual pin says are finished by read MATERIAL windows must be the engine's.

    Claim (A0923-TST-011): at 8c71c639 the EVM2 residual pin's docstring credits the engine with
    reading UID 25's material window, but ``compute_cpm(EVM2).booking_span_driven == (23,)`` (the
    leg builder runs only for tasks with ``duration_minutes > 0``, cpm.py:903); UID 25's unread
    window IS the remaining working day. The pinned figures themselves are right. Authority
    (verbatim), tests/engine/test_evm_acumen_reference.py:120-121 "ADR-0487 closed **1 more**:
    UIDs 23 and 25 are finished by MATERIAL bookings whose recorded windows the engine now reads";
    the engine's own disclosure contract, engine/cpm.py:267-272 "UniqueIDs whose early FINISH a
    MATERIAL / COST booking's RECORDED span decides (ADR-0487)". Checked: every UID such a
    sentence names must be in ``booking_span_driven`` (a docstring fix or the engine fix passes).
    Tier T5.
    """
    text = re.sub(r"\s+", " ", _read("tests/engine/test_evm_acumen_reference.py"))
    named = {
        int(u)
        for m in re.finditer(
            r"UIDs? ((?:\d+(?:, | and |/))*\d+) (?:is|are) finished by (?:a )?MATERIAL bookings? "
            r"whose recorded windows? the engine (?:now )?reads",
            text,
        )
        for u in re.findall(r"\d+", m.group(1))
    }
    evm2 = REPO / "tests" / "fixtures" / "golden" / "evm" / "EVM2.mspdi.xml"
    sch = parse_mspdi_text(evm2.read_text(encoding="utf-8"), source_file="EVM2.mpp")
    driven = set(compute_cpm(sch).booking_span_driven)
    assert named <= driven, (
        f"the docstring says UIDs {sorted(named)} are finished by read material windows; "
        f"booking_span_driven = {sorted(driven)}"
    )


# --------------------------------------------------------------------------------------------
# A0923-TST-012
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-012: the living R-register guard rejects a well-formed row R-100 (its id "
    "pattern is R-\\d{2})",
)
def test_a0923_tst_012_register_guard_accepts_the_next_three_digit_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The WP8 roadmap guard must accept a well-formed row whose id is three digits (R-100).

    Claim (A0923-TST-012): at 8c71c639 the pricing guard of the living R-register
    (tests/guards/test_audit_report_wp8.py:108 ``assert re.fullmatch(r"R-\\d{2}", ref), ref``)
    rejects R-100 while accepting R-81/R-99; the register grows a row per fix session (R-44 on
    2026-09-07 .. R-80 on 2026-09-21), so a legitimate 100th row turns the guard red. Authority:
    the guard's own stated property, tests/guards/test_audit_report_wp8.py:11-12 "**Pricing** —
    every roadmap row is priced (S/M/L) or owned (ASK/ORG/HELD/CLOSED-WP8) and names its first
    executable step or its settling observation" (no id width is part of it), and ADR-0472
    Decisions §1. Probe (built inline): copy the report, clone its last roadmap row verbatim with
    only the id changed to R-<max(100, highest+1)> directly beneath it, point the guard module's
    REPORT at the copy (monkeypatch) and call its pricing test function; correct = no
    AssertionError. The ROW_ID ledger regex (:37) is load-bearing and NOT checked. Tier T5.
    """
    guard = _load_by_path(
        "_a0923_wp8_guard", REPO / "tests" / "guards" / "test_audit_report_wp8.py"
    )
    lines = guard.REPORT.read_text(encoding="utf-8").splitlines(keepends=True)
    heading = next(
        i for i, ln in enumerate(lines) if ln.startswith("#") and "The repair roadmap" in ln
    )
    rows = []
    for i in range(heading + 1, len(lines)):
        if lines[i].startswith("#"):
            break
        if re.match(r"\| R-\d+ \|", lines[i]):
            rows.append(i)
    last = rows[-1]
    highest = max(int(re.match(r"\| R-(\d+)", lines[i]).group(1)) for i in rows)  # type: ignore[union-attr]
    new_id = f"R-{max(100, highest + 1)}"
    clone = re.sub(r"^\| R-\d+ \|", f"| {new_id} |", lines[last])
    probe = tmp_path / guard.REPORT.name
    probe.write_text("".join([*lines[: last + 1], clone, *lines[last + 1 :]]), encoding="utf-8")
    monkeypatch.setattr(guard, "REPORT", probe)
    guard.test_every_roadmap_row_is_priced_or_owned_and_names_its_first_step()


# --------------------------------------------------------------------------------------------
# A0923-TST-013
# --------------------------------------------------------------------------------------------
_REMOTE_ASSET = re.compile(
    r"\b(?:linked|loaded|served|pulled|fetched)\s+from\s+(?:the\s+)?(?:[\w.-]+\s+){0,3}CDN\b"
    r"|\bGoogle Fonts\b"
    r"|\b(?:fonts\.googleapis\.com|fonts\.gstatic\.com|unpkg\.com|cdn\.jsdelivr\.net"
    r"|cdnjs\.cloudflare\.com)\b",
    re.I,
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-TST-013: two nested intake CLAUDE.md files that load on demand carry remote-"
    "asset directives contradicting the root air-gap rule; none is excluded",
)
def test_a0923_tst_013_no_loadable_nested_claude_md_contradicts_the_air_gap_rule() -> None:
    """A nested CLAUDE.md Claude Code would load must not direct remote assets — or be excluded.

    Claim (A0923-TST-013): at 8c71c639 00_REFERENCE_INTAKE/CLAUDE.md (and the design-handoff
    bundle's CLAUDE.md) are tracked; subdirectory CLAUDE.md files "load on demand when Claude
    reads files in those directories" (https://code.claude.com/docs/en/memory, retrieved
    2026-09-23) and ``claudeMdExcludes`` "skips specific files by path or glob pattern so they
    never load" (https://code.claude.com/docs/en/large-codebases, retrieved 2026-09-23); the
    first carries CDN / Google Fonts directives, and .claude/settings.json has no
    ``claudeMdExcludes``. Authority (verbatim): the root rule, CLAUDE.md:290-291 "Static JS/CSS
    are vendored (no CDN, no bundler) and a strict CSP enforces the air-gap."; the contradicting
    directives, 00_REFERENCE_INTAKE/CLAUDE.md:141 "Lucide is linked from CDN in specimen cards"
    and :192 "**Fonts** are loaded from Google Fonts CDN". Correct state: no tracked nested
    CLAUDE.md that is not excluded by the committed settings carries a remote-asset directive
    (a negated "no CDN" is not one). Tier T5.
    """
    if not re.search(r"no CDN", _read("CLAUDE.md")):
        return  # no root air-gap rule to contradict
    settings = json.loads(_read(".claude/settings.json") or "{}")
    excludes = settings.get("claudeMdExcludes", [])
    offenders = []
    for rel in _tracked_files():
        if Path(rel).name not in ("CLAUDE.md", "CLAUDE.local.md") or "/" not in rel:
            continue
        absolute = (REPO / rel).resolve().as_posix()
        if any(_globstar(pat).fullmatch(absolute) for pat in excludes):
            continue
        for n, line in enumerate((REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
            if _REMOTE_ASSET.search(line):
                offenders.append(f"{rel}:{n}")
    assert not offenders, (
        f"loadable nested CLAUDE.md files direct remote assets (claudeMdExcludes={excludes}): "
        f"{offenders}"
    )
