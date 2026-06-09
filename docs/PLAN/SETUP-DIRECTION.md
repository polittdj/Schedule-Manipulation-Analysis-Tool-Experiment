# Setup direction (Gate 2) — settings, permissions, hooks, env for the autonomous build

Apply this before replying `GO` for Phase 2. It extends
`AUTONOMOUS-BUILD-SETUP-CHECKLIST.md` (the baseline) with what Phase 1 surfaced. Items marked
**[build]** are for the build sessions; **[runtime]** are constraints the shipped tool must
enforce (and that the build must implement), and **[action]** is something you (the user) do.

## 1. Model & mode (every session)
- **[build]** Opus 4.8 (1M context) + **Ultracode** — unchanged across all `A<n>` sessions.
- **[build]** Plan mode + sub-agents enabled (Phase 2 parallelizes Explore/Plan/implementer
  agents). Phase 1 already used sub-agents to extract the catalog/parity targets.

## 2. Permissions (curated allowlist — avoid "skip all")
Allow without prompt (in `.claude/settings.json`): `git` (add/commit/branch/checkout/push),
`python`/`python -m pytest`, `pip`/`pip install`, `ruff`, `mypy`, `bandit`, `pip-audit`,
`ollama` (list/pull/run), `java` + `javac` (MPXJ native `.mpp`), and `node`/`npm` **only if**
we bundle JS viz assets via a local toolchain. Keep destructive ops (rm -rf, force-push) prompting.

## 3. Hooks (CUI defense + green baseline)
- **[action]** **Pre-commit hook** that blocks committing any schedule/Office/`.pbix`/pickle
  artifact (defense-in-depth behind `.gitignore`). Fail closed. (We can generate it in Phase 2.)
- **[action]** **SessionStart hook** that verifies the toolchain is present (python 3.12+, JDK
  ≥17, ollama reachable) and prints versions, so a session fails fast if the env is wrong.

## 4. Environment prerequisites (build/run machine)
- **[action]** **Python 3.11+** + venv (`pip install -e '.[dev]'`). *Note: this hosted build
  container runs **Python 3.11.15**, so `pyproject.toml` targets `>=3.11` (also matches the CI
  matrix 3.11/3.13). If you standardize the build host on 3.12+, bump it back.*
- **[verified ✓]** **JDK 21** is present in this hosted container, and the **MPXJ runner is
  vendored** — so native `.mpp` parsing works here now (no extra install). On any other build
  host, install **JDK ≥ 17**. Verify `java -version`.
- **[action]** **Ollama** on `localhost:11434` with a capable model pulled (see §6).
- **[action, optional]** Windows **MS Project + pywin32** if you want the COM cross-check path
  (Acumen/SSI were produced on **MS Project Online Desktop Client, MSO 2603, Build
  16.0.19822.20240, 64-bit** — matching that build's calc helps parity).
- **[build]** **GitHub MCP** enabled (draft PRs) — in use.

## 5. CUI siting (decided)
- **[build]** Reference/golden files are **non-CUI** (ADR-0003) → this hosted session is fine for
  the build. **[runtime]** The shipped tool will analyze **CUI** schedules → it must default to
  local Ollama, never call cloud by default, show a persistent external-endpoint banner only when
  a project is explicitly toggled "unclassified," and transfer nothing off-machine. The build
  must implement and test that (egress guard, §7/§6.G).

## 6. Local AI model (default for a high-end workstation; §6.F)
- **[action]** Pull a capable instruct model as the default, e.g. **`qwen2.5:32b-instruct`** or
  **`llama3.1:70b`** (quality) with a lighter fallback **`llama3.1:8b`** / **`qwen2.5:14b`** for
  speed. Final default chosen in the §6.F milestone; the tool must let the user **list / pull /
  switch** models in-app, so the exact pick isn't load-bearing now.
- Narrative quality may trade for performance, but **every AI sentence must carry citations**
  (file + UniqueID + task name) — enforced in code, not left to the model.

## 7. Phase-1-specific gaps to close before/at Phase 2
- **✅ `Project2.mpp` + `Project5.mpp` provided** (2026-06-05). The user said "Project4" but the
  folder has **Project5** (typo; Project5 is the correct target for all golden numbers). Source
  set complete.
- **[action] Power BI `.pbix`:** the 14 MB `NSATDeploymentRevisionAlpha.pbix` can't be parsed
  through the Drive connector in a hosted session (binary/too large to stream into context). To
  use its extra metrics/visuals, either (a) run the relevant build milestone on a machine with the
  file locally (unzip → read `DataModelSchema` for DAX + `Report/Layout` for visuals), or (b)
  export the **DAX measures** (Tabular Editor) + **visual screenshots** and drop them in the
  folder. Not blocking Gate 2; deferred to the UI/metrics milestone.
- **[action] Confirm the authoritative DCMA reference.** The golden exports use the **DCMA-14
  ribbon**; the `.xlsx` is the broader **DECM V7.0** EVMS set. Tell me if the audit should target
  classic DCMA-14 (default) and treat DECM as an optional extended audit.
- **[action] Confirm Acumen Fuse parity version = v8.11.0** (not printed in the exports).

## 8. Repo settings
- **[action]** Keep auto-merge **disabled**; all Claude PRs stay **draft**. Enable branch
  protection so CI must pass before any merge (CI gets the real lint/type/test/security/parity
  pipeline in Phase 2).

---
When §3–§7 **[action]** items are addressed (at minimum: provide the `.mpp` files, pull an Ollama
model, install JDK 17 + Python 3.12 on the eventual build/run machine), reply **`GO`** to start
**Phase 2** (the Plan session: full `BUILD-PLAN.md` + complete `RTM.md`).
