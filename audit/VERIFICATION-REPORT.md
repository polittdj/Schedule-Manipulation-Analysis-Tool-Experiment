# VERIFICATION-REPORT — exhibits layer session (2026-07-10)

Every §2 pre-flight claim, with the command run and its observed result.

## 2.1 Tree + interpreter
- `pwd` → /home/user/Schedule-Manipulation-Analysis-Tool-Experiment
- `git rev-parse --abbrev-ref HEAD` → claude/schedule-tool-forensic-reaudit-7da8p1
- `git rev-parse HEAD` → 6e4b9637ccb3… (branch tip = origin/main at session start)
- `python -c "import sys; print(sys.executable)"` → .venv/bin/python (3.11.15)

## 2.2 Engine artifacts
- `grep -rln 'criticality_instability|tau_b|edge_jaccard|null_model|recompute_delta|\bCIC\b' src/schedule_forensics/`
  → NO MATCHES. CP-basis engine artifacts absent → fixtures-first per the prompt's
  dependency clause; live wiring parked (PARK-LIST P1/P2).

## 2.3 volData construction
- `grep -rn "volData" src/` → built inline in `web/app.py::_volatility_body`
  (`<script type="application/json" id=volData>{blob}</script>`), data from
  `web/app.py::_volatility_data`. Splice point identified; migration parked with P2.

## 2.4 SSI collision
- `grep -rln "\bSSI\b" src/ tests/ pyproject.toml` → 10+ files spanning BOTH meanings
  (vendor: parity marker/goldens; metric: `sra_ssi.js`, engine/sra). Fallback executed:
  gate test `tests/exhibits/test_exhibits_gate.py::test_no_bare_ssi_in_exhibits`
  (new-code gate) + PARK-LIST P3 for the full rename.

## 2.5 C1 round-trip
- `python -m pytest tests/importers/test_json_schedule.py -q` → 19 passed.
  C1 closed (introspection guard + full-fidelity round-trip in suite).

## Exit-criteria evidence (§9)
- `python -m pytest tests/exhibits/ -q` → 14 passed (includes: determinism double-run
  byte-equality; air-gap grep over every emitted artifact; CLI exit codes 0/2/3/4/5;
  `var(--` absent from every standalone SVG; EX-01 pattern reference; EX-03 exactly one
  boundary break; EX-04 exactly one annotated CIC gap; static≡interactive payload bytes).
- Grayscale legibility: EX-01 uses distinct GLYPHS (▓ ▒ ╳ · ✓ / blank) per state on top of
  fills, constraint-critical hatched via <pattern> — the states remain distinguishable with
  color removed; I rendered the fixture barcode and reviewed the glyph set. Stated per §9.4.
