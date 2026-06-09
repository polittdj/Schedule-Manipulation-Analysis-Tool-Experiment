# ADR-0006: M1 build rails — egress-guard scoping, CUI hooks, and CI gates

- **Status:** Accepted
- **Date:** 2026-06-05 (session A3 — Phase 2 build, milestone M1)
- **Relates to:** §6.G (data locality), §7 (QC/PM regime: egress guard, CI, coverage),
  §0 (CUI guardrails). Builds on ADR-0004 (stack) and ADR-0002 (feature-branch policy).

## Context
M1 stands up the real project skeleton and the "green rails" every later milestone depends
on: lint/types/tests/security CI, coverage gates, the network-egress guard, CUI-redacted
logging, and CUI defense hooks. Several design choices were non-obvious and are recorded here.

## Decisions

### 1. The egress guard checks the *declared runtime dependency closure*, not raw importability
A naive "fail if `requests` / `urllib3` is importable" check is a **false positive** in this
repo: the dev/CI toolchain (`pip-audit` → `CacheControl` → `requests` → `urllib3`) legitimately
installs those into the build environment. They must never become **runtime** dependencies of
the shipped tool, but they are fine at build time. So `net_guard`:
- matches `FORBIDDEN_RUNTIME_DISTRIBUTIONS` against the package's **base runtime requirements**
  (`importlib.metadata.requires`, dropping `extra`-gated dev deps) — meaningful from M12 when
  the Ollama client lands (it must be loopback-only, not a generic cloud HTTP client); and
- additionally asserts a curated set of **pure cloud-provider SDK modules**
  (`openai`/`anthropic`/`boto3`/`google.generativeai`/…) is not importable. These are never
  transitive dependencies of the build toolchain, so the check is a true signal with no false
  positives.
`assert_local_only()` is the fail-closed entry-point used at app startup; the egress test is
the §7 acceptance gate. `is_loopback_host()` is the predicate the future Ollama client uses so
a CUI project can only reach `127.0.0.1`.

### 2. CUI logging redaction uses an inert, idempotent token
`logging_redaction.redact()` replaces schedule/Office file names and absolute paths with a
stable `<file:mpp#hash>` / `<path:xer#hash>` token (blake2b, 4 bytes). The token deliberately
**omits the dot before the extension** so it cannot be re-matched by the sensitive-file regex —
`redact()` is therefore idempotent, which matters because the JSON formatter may redact an
already-filtered message a second time. Loopback URLs (the Ollama endpoint) are preserved.

### 3. Two complementary CUI hooks
- A **git `pre-commit` hook** (`.githooks/pre-commit`, activated via `core.hooksPath`) blocks
  staged schedule/Office/`.pbix`/pickle artifacts for *any* committer (not just Claude Code) —
  defense-in-depth behind `.gitignore`, exempting synthetic `tests/fixtures/`.
- A **Claude Code `SessionStart` hook** (`.claude/hooks/session_start.sh`) verifies the
  toolchain (python/jdk/node/ollama) and re-activates the git guard each session. It is
  fail-soft (always exits 0; a missing optional tool warns, never blocks).

### 4. Coverage gates: overall ≥70% in pytest, engine ≥85% as a dedicated step
The overall gate is `--cov-fail-under=70`. The engine gate is a separate
`coverage report --include='*/engine/*' --fail-under=85` step so it scopes correctly to the
fidelity-critical package; each layer `__init__` carries an `__all__` so the gate is
well-defined (100%, trivially passing) even before engine code lands in M5.

### 5. CI keeps the existing status-check context names
The real pipeline reuses the job id `test` (matrix `3.11`/`3.13`) and the `check` aggregate so
the branch-protection contexts `test (3.11)`, `test (3.13)`, `check` stay satisfied with no
reconfiguration. CI is Python-only at M1; JDK/MPXJ jobs arrive with ingestion (M4), and Ollama
is never required in CI (local-only).

### 6. Branch continuation: assigned branch fast-forwarded onto the completed plan
This session was assigned `claude/intelligent-johnson-18yZD`, a fresh branch at the greenfield
reset `882dec3` with none of the A1/A2 work (which lives on `claude/intelligent-fermat-3MBqk`,
PR #51, tip `9ffe53e`). Because `882dec3` is the direct ancestor of `9ffe53e`, the assigned
branch was **fast-forwarded** onto the completed plan (lossless, full history preserved), and
M1 was built on top. All pushes go only to the assigned branch (never to `fermat`). The
`johnson` PR therefore supersedes/continues PR #51; see `SESSION-LOG.md` (A3) and `HANDOFF.md`.

## The one item deferred to user approval
`.claude/settings.json` (curated permission allowlist + the SessionStart hook registration)
could not be written by the agent: doing so widens the agent's own permission rules, which the
Claude Code safety classifier reserves for explicit user approval. The exact recommended
content is captured in `docs/PLAN/CLAUDE-CODE-SETTINGS.md` for the user to apply; the git
pre-commit guard is already active independently of it.

## Consequences
- Every later milestone inherits red-blocks-merge CI, coverage gates, a tested egress guard,
  and CUI-redacted logging from commit one.
- The egress guard becomes load-bearing at M12 (Ollama) and will fail CI if any cloud/remote
  HTTP client is added to runtime dependencies without an ADR.
- Parity is not yet in CI (no parity tests until M9); the §7 "parity in CI" clause is satisfied
  when the M9 suite lands.
