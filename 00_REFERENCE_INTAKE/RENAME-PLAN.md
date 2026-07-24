# RENAME-PLAN — mechanical package rename (NAMES PROPOSED, awaiting your choice)

Per PROMPT 5 §1 this stops at the name choice. §2's blast-radius plan is below and is name-agnostic — it uses `<pkg>` (import name, snake_case), `<dist>` (distribution name, kebab-case) and `<Display>` (the human name) so it applies verbatim once you choose.

*This workspace has no Python runtime and no network, so §5's gate must run in the repo. Every file class in §3 was verified against the repo at tree `10b2cc1b0625` (version `1.0.95`).*

---

## 0. Recommendation first: consider **never**

The prompt already says it — zero user-visible benefit, ~350–400 files, and it can break the lockstep gate. Two facts sharpen that:

1. **The user-visible name is already decoupled.** The UI shows a display name from the header chrome, not the package name; DESIGN-SYSTEM §2 only forbids the word "NASA". You can ship `<Display>` on every screen, in every export and in the CUI-marked briefing **today**, with a one-line copy change and zero rename risk.
2. **The rename's real cost is in the gates, not the code.** `tests/test_packaging.py` asserts on the literal filenames `schedule-forensics.desktop` / `.command` / `.bat` / `.ico` / `.png` **and** on the exact string `"-m schedule_forensics"` inside the Windows shortcut arguments (L14–16, L30–31), while `tests/installer/test_installers.py` asserts the embedded wheel is named `schedule_forensics-{version}` (L82–83) and byte-compares every packaged `schedule_forensics/**` path against the source tree (L120). A rename rewrites all of those simultaneously — which is exactly the "indistinguishable failure" the prompt wants to avoid, and it is why this must be one commit that either goes fully green or is reverted whole.

**My advice: do the display-name change now, and only rename the package if it must be the import name in someone else's environment** (a second tool importing it, an external distribution, or a legal/branding requirement). If you accept that, PROMPT 5 becomes a 20-minute copy change and this plan goes in the drawer.

If you still want the rename, everything below is ready.

---

## 1. Five names

| # | `<Display>` | `<dist>` | `<pkg>` | Why | Risk |
|---|---|---|---|---|---|
| 1 | **Astrolabe** | `astrolabe-forensics` | `astrolabe` | The name already carried by the design prototype and the redesigned UI — renaming to it makes the code match the product the operator has been reviewing. An astrolabe is an instrument for fixing your position from fixed bodies: exactly what the tool does with a schedule | `astrolabe` exists on PyPI; irrelevant while `Private :: Do Not Upload` holds, but the dist name is kept distinct anyway |
| 2 | **Orrery** | `orrery` | `orrery` | A geared model that shows where bodies are *and predicts where they will be* — the closest single word to "past, present and forecast of a schedule". Short, memorable, near-certainly unclaimed | Slightly obscure; people mispronounce it (OR-uh-ree) |
| 3 | **Plumbline** | `plumbline` | `plumbline` | The forensic metaphor: a plumb line cannot be argued with. Reads well in a claim or deposition context | Less evocative of schedule/time |
| 4 | **Sextant** | `sextant-sf` | `sextant` | Navigation instrument; fits the mission-ops chrome and the "instruments, not widgets" doctrine | Common word, several existing tools/products use it |
| 5 | **Keelson** | `keelson` | `keelson` | The structural spine a hull is built on — the schedule as the spine of a programme. Almost certainly collision-free | Hard to spell and say; weakest of the five, listed for completeness |

**My pick: Astrolabe** — it is the only one that removes an existing inconsistency (prototype/UI say one thing, package says another) rather than adding a new name to remember. Note the knock-on: the voice clips in `docs/VOICE-DECISION.md` bake a spoken name, so choosing here settles that question too.

---

## 2. Scope rule

One commit. Zero behaviour change. No feature work, no formatting sweep, no import reordering beyond what the rename forces, no version-content change other than the bump. If `git diff` shows a line that is not a name, it does not belong in this commit.

---

## 3. Every file class that changes (verified)

### 3.1 `pyproject.toml` — 6 sites, and two the prompt lists that do **not** need changing

| Site | Now | Becomes |
|---|---|---|
| `[project] name` | `"schedule-forensics"` | `"<dist>"` |
| `[project] version` | `"1.0.95"` | bumped (§5) |
| `[project.scripts]` #1 | `schedule-forensics = "schedule_forensics.launcher:main"` | `<dist> = "<pkg>.launcher:main"` |
| `[project.scripts]` #2 | `schedule-forensics-report = "schedule_forensics.exhibits.cli:main"` | `<dist>-report = "<pkg>.exhibits.cli:main"` |
| `[tool.setuptools.package-data]` key | `schedule_forensics = ["web/static/*", "web/examples/*"]` | `<pkg> = [...]` — **if this key is missed the wheel installs and the app crashes mounting `/static`**, which is the failure the Linux end-to-end run caught on 2026-07-02 |
| `[tool.ruff.lint.per-file-ignores]` | `"src/schedule_forensics/web/app.py" = ["E501"]` | `"src/<pkg>/web/app.py"` — miss it and ruff fails on ~19k lines of embedded HTML |
| `[tool.coverage.run] source` | `["schedule_forensics"]` | `["<pkg>"]` — miss it and coverage reports 0% and the ≥70 gate fails |
| `[tool.mypy]` | `files = ["src"]` | **no change** — path-based, not name-based (the prompt assumed otherwise) |
| `[tool.bandit] exclude_dirs` | `["tests", ".venv", "tools"]` | **no change** — path-based |
| `[project.urls]`, description, keywords | mention the old name/product | judgement call: update description and `<Display>`; leaving the GitHub URLs alone is correct if the repo is not renamed |

### 3.2 The package directory — the bulk of the diff

`git mv src/schedule_forensics src/<pkg>`, then rewrite intra-package imports. Repo tree reports **180 files under `src/schedule_forensics/`**. Count the actual import surface before starting, and again after, so the numbers must match:

```bash
grep -rn "schedule_forensics" src/ tests/ tools/ packaging/ .github/ docs/ *.md *.toml | wc -l
grep -rln "^\(from\|import\) schedule_forensics" src/ tests/ | wc -l
```

`web/app.py` alone carries **88** occurrences of the literal (measured), so do not hand-edit it — use a scripted replace and review the diff.

**Two name-bearing runtime paths that are easy to miss:** `src/<pkg>/net_guard.py` (the egress guard, asserted by `tests/guards/test_egress.py`) and `src/<pkg>/__main__.py` (the guarded `-m <pkg>` bootstrap that `tests/test_packaging.py` asserts on by literal string).

### 3.3 `packaging/` — filenames encode the name

`packaging/schedule-forensics.png` · `packaging/windows/schedule-forensics.ico` · the generated `schedule-forensics.desktop` / `.command` / `.bat` / `.vbs` · `packaging/make_icon.py` (writes those filenames) · `packaging/README.md` (**8** name-bearing lines, measured).

`tests/test_packaging.py` asserts these exact filenames (L14–16, L36, L64–65) **and** that `favicon.ico` at `src/schedule_forensics/web/static/favicon.ico` byte-matches the packaging icon (L66) — so the icon move and the test update are the same edit.

### 3.4 The installer templates and the 9 generated installers

`tools/installer/template.ps1` · `template.sh` · `template.command` encode: the wheel filename, `-m schedule_forensics`, the install-root name, and the generated helper scripts `start-` / `stop-` / `uninstall-schedule-forensics.{sh,ps1}` (visible in `installer-smoke.yml` L97/L101/L106). `tools/installer/build_installers.py` defaults to the glob `dist/wheel/schedule_forensics-*.whl`.

The **9 installers are build output** — they are regenerated, never hand-edited:

```bash
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/<pkg>-*.whl
```

### 3.5 CI

`.github/workflows/ci.yml` — 2 lines (`--cov=schedule_forensics`, `--include='*/schedule_forensics/engine/*'`).
`.github/workflows/installer-smoke.yml` — **6** lines, including the two import probes `import schedule_forensics; from schedule_forensics.launcher import main` (L57) and the static-assets check `import schedule_forensics.web.app as a` (L58), plus the three generated helper-script names (L97, L101, L106).

### 3.6 Tests that assert on the name (expect these to fail first)

`tests/test_packaging.py` (12 lines) · `tests/installer/test_installers.py` (wheel name L82–83, packaged-path comparison L120) · `tests/guards/test_egress.py` · `tests/test_launcher.py` · `tests/test_startup_bootstrap.py` · `tests/web/test_docs.py` (regenerates `docs/METRIC-DICTIONARY.md` from `<pkg>.web.help`) · `tests/test_state_docs.py`.

### 3.7 Docs

`CLAUDE.md` · `README.md` · `docs/DESIGN-SYSTEM.md` · `docs/USER-GUIDE.md` · `docs/METRIC-DICTIONARY.md` (**generated** — regenerate, do not edit) · `installer/README-DISTRIBUTABLE.md` · `packaging/README.md` · `docs/UI-INVENTORY.md` (all its `src/schedule_forensics/...` paths) · the 288 ADRs — **do not rewrite history**: ADRs record what was true when written; add one new ADR recording the rename instead.

---

## 4. Execution order (one commit, but do it in this sequence locally)

1. `git checkout -b rename/<pkg>` — and change nothing else on this branch, ever.
2. `git mv src/schedule_forensics src/<pkg>`; `git mv` the four `packaging/` assets.
3. Scripted replace of `schedule_forensics` → `<pkg>` and `schedule-forensics` → `<dist>` across `src/ tests/ tools/ packaging/ .github/ docs/` and the root `*.md`/`*.toml`, **excluding `docs/adr/`**.
4. Hand-check the six `pyproject.toml` sites in §3.1 (a scripted replace gets five of them; the ruff per-file-ignores path is the one that silently survives).
5. Regenerate what is generated: `docs/METRIC-DICTIONARY.md`, the icons if `make_icon.py` output filenames changed, then the wheel and the 9 installers (§3.4).
6. Bump `[project] version` — `1.0.95` → `1.1.0` (a rename is not a patch).
7. Add `docs/adr/0285-package-rename-to-<pkg>.md`: what changed, what did not (no behaviour, no engine, no payload), and the fact that ADRs 0001–0284 keep the old name deliberately.
8. Run the full gate (§5). One commit, one PR.

---

## 5. Gate — all of it, or revert

```bash
ruff check . && ruff format --check . && mypy
pytest --cov=<pkg> --cov-report=term-missing --cov-fail-under=70
coverage report --include='*/<pkg>/engine/*' --fail-under=85
pytest -m parity -p no:cacheprovider
bandit -q -r src && pip-audit --progress-spinner=off
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/<pkg>-*.whl
pytest tests/installer/test_installers.py tests/test_packaging.py -q
grep -rn "schedule_forensics\|schedule-forensics" --exclude-dir=docs/adr --exclude-dir=.git . | grep -v "^docs/adr" | wc -l   # expect 0
```

Plus, per the prompt: **installer-smoke green on both `windows-latest` and Linux** — that workflow is the only place the renamed wheel is actually installed and imported (`installer-smoke.yml` L57–58), so a green unit suite with a red smoke run means the rename is not done.

**Invariants that must not move:**
- The three dashboard goldens — `_SHA_TWO_VERSION` `d62a4f9e…58d1`, `_SHA_UNSOLVABLE` `8d7bcc38…fc16`, `_SHA_TWO_VERSION_PARITY` `51691cb7…504cb`. A rename cannot touch a payload; if one moves, something non-mechanical happened.
- Parity results (`pytest -m parity`), engine coverage ≥85%, DCMA counts (173 parity / 182 default on the reference file).

**Revert rule:** if any gate is red after one honest debugging pass, `git checkout main && git branch -D rename/<pkg>`. Do not land a partial rename, do not `# type: ignore` a rename, do not relax an installer assertion to make the wheel name match. A half-renamed package is worse than no rename — that is the prompt's rule and it is the right one.

---

## STOP — one decision

**Which name?** (Or "never", and I do the display-name-only change instead.) Nothing will be moved until you answer, and once you do, this becomes a single mechanical branch with the gate above as its only definition of done.
