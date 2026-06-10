name: CI

# Real QC/PM pipeline (AUTONOMOUS-BUILD-PROMPT.md §7), stood up in milestone M1.
# Lint + format + types (strict) + tests + coverage gates + security on every push
# and PR; a red run blocks merge. The status-check context names are kept identical
# to the prior greenfield placeholder (`test (3.11)`, `test (3.13)`, `check`) so
# branch protection stays satisfied without reconfiguration.
#
# This pipeline is Python-only by design at M1 (no schedule logic yet). The JDK /
# MPXJ native-`.mpp` jobs are added when ingestion lands (M4); Ollama is never
# required in CI (local-only, §6.F).

on:
  # Push runs only on main; branch pushes are covered by their pull_request run (which also
  # carries the branch-protection contexts), so a PR push no longer triggers the matrix twice.
  push:
    branches: ["main"]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.13"]
    steps:
      - uses: actions/checkout@v5

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install (package + dev toolchain)
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e '.[dev]'

      - name: Lint (ruff)
        run: ruff check .

      - name: Format check (ruff)
        run: ruff format --check .

      - name: Types (mypy, strict)
        run: mypy

      - name: Tests + overall coverage gate (>=70%)
        run: pytest --cov=schedule_forensics --cov-report=term-missing --cov-fail-under=70

      - name: Engine coverage gate (>=85%)
        run: coverage report --include='*/schedule_forensics/engine/*' --fail-under=85

      - name: Parity gate (Acumen Fuse v8.11.0 + SSI golden, §6.B)
        run: pytest -m parity -p no:cacheprovider

      - name: Security (bandit)
        run: bandit -q -r src

      - name: Dependency audit (pip-audit)
        run: pip-audit --progress-spinner=off

  # Stable aggregate status (named "check") so branch protection has a single
  # context to require regardless of the matrix dimensions.
  check:
    name: check
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "all matrix jobs passed"
