---
name: cui-guard
description: Check a POLARIS/SMAT change against Law 1 (data sovereignty / CUI) before it lands. Use whenever adding or changing a dependency, an HTTP client, a subprocess, a log statement, a served asset, a font, an AI backend or endpoint, a file-upload path, or anything that reads or writes a schedule file; whenever staging a schedule or Office binary (.mpp/.xer/.xlsx/.aft/.docx/.xml/.csv/.pbix/.pkl); and whenever asked about air-gap, egress, offline, CUI, the pre-commit guard, CSP, or whether data can leave the machine. The cost of a miss here is the highest in the repo.
---

# Law 1 — data sovereignty (CUI)

**No schedule content or derived metric ever leaves the machine.** The AI is loopback-only and fails
closed. This is not a preference; it is the tool's reason to exist in a testimony context.

## 1. What may and may not be committed

The pre-commit guard (`.githooks/pre-commit`, activated by the SessionStart hook) blocks staged files
matching `.(mpp|mpt|mpx|xer|xml|pmxml|csv|xls|xlsx|pbix|mspdi|pkl|pickle|aft|docx|doc)$` with exactly
**two** exceptions:

1. **`tests/fixtures/`** — synthetic, hand-authored, non-CUI fixtures only.
2. **`inherited_from_main`** — a staged blob byte-identical to `origin/main` at the same path.

A **new** or **modified** (tampered) blocked-extension file anywhere outside those two allowances is
still blocked, so no real CUI schedule from a build session can land in the repo.

Two extensions in that list surprise people: **`.xml` and `.csv` are blocked.** An MSPDI export is
`.xml`, so a converted schedule is caught like a native one — which is why every committed MSPDI
fixture lives under `tests/fixtures/`. Note also what is **not** in the list (`.pptx`, `.pdf`, `.jpg`,
`.mp4`): the guard is a schedule/Office-document blocklist, not a completeness proof. Judgement still
applies to anything carrying schedule content.

### The CUI boundary (operator-confirmed)

- The **build/reference** inputs used to develop and parity-test the tool — `Large_Test_File.mpp`, the
  SSI/Acumen exports, the NASA `.aft` metric library, the golden inputs — are **NOT CUI** and are
  **committed** under `00_REFERENCE_INTAKE/` (ADR-0152, superseding the earlier keep-binaries-out
  posture).
- **Real CUI is only ever the operator's production schedules, loaded into the deployed tool**, which
  runs locally and never touches a build session.

**Never `git add -f` past the guard.** If it fires, the file is either misplaced (belongs under
`tests/fixtures/` if synthetic) or must not be committed at all.

Exception #2 exists because the operator committed the reference intake to `main` via the GitHub web
UI, which no local hook can see — without the byte-identity carve-out every `git merge origin/main`
wedged. Corollary: **never amend or rebase `origin/main`'s squash commits.** Rewriting published
history forks the branch from main and breaks `inherited_from_main`.

## 2. Runtime I/O is standard-library only

`net_guard.py` fails the build if a forbidden HTTP client enters the **runtime** dependency set —
`requests`, `httpx`, `urllib3`, `websockets`, `aiohttp`, or an importable cloud SDK. Tested by
`tests/guards/test_egress.py`.

- Do **not** add any cloud/remote-HTTP client to `[project] dependencies` without an explicit ADR.
- `uvicorn` must stay the **plain** build — `uvicorn[standard]` pulls the forbidden `websockets`.
- `httpx` and `playwright` are **dev-only** (`[dev]` / `[browser]` extras). `httpx` backs starlette's
  TestClient; it must never enter `dependencies`.
- Version floors exist to remediate published CVEs (`jinja2>=3.1.6`, `python-multipart>=0.0.18`,
  `setuptools>=83.0.0`) — do not lower them.

```bash
python -m pytest tests/guards -q          # egress + endpoint-scheme + pre-commit blocklist
pip-audit --progress-spinner=off
```

## 3. The served page must reference no remote asset

A strict CSP (`script-src 'self'`) enforces the air-gap, and `tests/web/test_airgap.py` fails if a
served page references a remote asset. So:

- **No CDN, no bundler, no remote font.** Type is vendored or a system stack.
- **No shipped audio asset** — sound is synthesized WebAudio (ADR-0328), which keeps the air-gap and
  the lean wheel trivially true.
- Any new static file is vendored under `web/static/` and declared in
  `[tool.setuptools.package-data]` — the wheel once omitted `web/static` and every deployed install
  crashed at startup while every `pip install -e` dev env worked (ADR-0144).

## 4. The AI layer fails closed

- `OllamaBackend` and `OpenAICompatBackend` are **loopback-validated at construction**;
  `route_backend` fails closed to `NullBackend` and never auto-reaches cloud.
- `NullBackend` is the deterministic offline default (returns the prompt unchanged).
- Narrative / briefing / translation re-verify every AI-emitted figure against engine citations
  (`ai.citations.reattach`). Ask-the-AI Q&A is **operator-mode-gated**: `strict` discards an answer
  containing an unsourced figure, `annotate` (default) flags AI-derived figures, `interpretive`
  returns verbatim and is **not** figure-gated by design.
- The figure gate is a **token** gate: it polices a number's presence and value, not its meaning.
  It has been falsified and re-hardened ~8 times (ADR-0129 → 0239). Do not re-litigate it from
  scratch, and do not widen `interpretive`'s scope without an ADR.

## 5. Logging and subprocesses

- CUI log redaction (`logging_redaction.py`) must stay **wired at runtime**, not merely tested. The
  "dead defense-in-depth" class — guards that existed with zero runtime callers — was a top recurring
  defect (wired at ADR-0241; a redaction leak fix was then found incomplete in the very next audit).
- Never log a task name, date, UniqueID or file path unredacted.
- Every subprocess carries `CREATE_NO_WINDOW` + `stdin=DEVNULL` (AST-guarded by
  `tests/test_windowless_subprocess.py`) — a windowless telemetry loop once flashed a console every
  5 s on the operator's Windows box.

## 6. Preflight before staging

```bash
git status --short                     # nothing unexpected
git diff --cached --name-only          # what the guard will actually see
python -m pytest tests/guards tests/web/test_airgap.py tests/web/test_csp_strict_scripts.py -q
```

**Wire every guard at runtime with a startup assertion AND a test that the assertion runs.** A
guarantee that lives only in a test is not a guarantee — and verify security gates in a **real
browser**, not just a TestClient: the SEC-2 CSRF gate would have 403'd every POST form in the field
because the suite only ever tested `fetch`, never a real form navigation (ADR-0264 → 0268).
