# ADR-0058 — Third audit remediation: loopback AI-endpoint scheme validation + no-redirect egress (CUI Law 1)

- **Status:** accepted
- **Date:** 2026-06-17
- **Drivers:** external QC audit ("connect to the repo, find every error, triple-check each is
  real, write a sandbox test for each proposed fix, then implement"). Exactly **one** real defect
  surfaced; the rest of the audit verified clean (CPM forward/backward bound math, the MSPDI
  pre-parse XXE/billion-laughs defense, the MPXJ `.mpp` subprocess argv/timeout handling, the web
  upload path-/header-safety, and the EVM zero-division guards were all hand-checked and, where
  feasible, empirically attacked). Native-`.mpp` parity cases were un-skipped against a
  re-deposited `Project2.mpp`. Follows the remediation pattern of ADR-0024 / ADR-0026.

## Decision 1 — the loopback AI guard validates scheme AND host (not host alone)

The local-AI backends (`OllamaBackend`, `OpenAICompatBackend`) and the settings handler in
`web/app.py` validated only the endpoint **host** via
`is_loopback_host(urlparse(endpoint).hostname)`. A loopback host is necessary but **not
sufficient**: `file://localhost/etc/passwd`, `ftp://127.0.0.1/…`, and `gopher://localhost/…` all
carry a loopback host yet are not HTTP, so each passed the guard. Empirically,
`OllamaBackend(endpoint="file://localhost/…")` constructed successfully and the "loopback-only"
stdlib opener **read a local file off disk**. The `# nosec B310` suppression asserted in a comment
that the URL could "never be a remote/file/custom scheme" — a guarantee the code did not enforce.

New `net_guard.is_local_http_endpoint(endpoint)` requires **both** `scheme ∈ {http, https}` **and**
a loopback host; all three call sites switch to it. `is_loopback_host` is left unchanged — it is
still correct for the bind-host checks in `web/app.py` (`serve`) and `launcher.py`, which take a
*host string*, not a URL.

Severity is **defense-in-depth, not active egress**: `file://` reads a *local* file (no network
leaves the machine), and tripping it requires a crafted/mistyped endpoint in the operator's own AI
config or a compromised local server. But the guard now matches its own comment and fails closed,
which is the bar Law 1 sets.

## Decision 2 — the local-AI opener refuses HTTP redirects

The loopback/scheme check runs **once**, against the initial endpoint. `urllib` follows 3xx
redirects by default, so a loopback server returning `307 Location: https://remote/…` would
transparently re-send the request body — i.e. the CUI prompt — to a remote host. The shared opener
is now built with a `_NoRedirect` handler whose `redirect_request` returns `None`, so `urllib`
surfaces a 3xx as an error instead of bouncing off-machine. `OpenAICompatBackend` reuses
`ollama._urllib_opener`, so it inherits this protection for free.

## Decision 3 — native-`.mpp` parity skip-guard made per-file; structural parse confirmed

`tests/importers/test_mpp_mpxj.py::test_parse_real_mpp` is parametrized over `Project2.mpp` **and**
`Project5.mpp`, but its skip guard checked only `Project2.is_file()`. Depositing `Project2.mpp`
alone therefore un-skipped the *Project5* case too, which then errored on the absent file. The
guard is now **per-parameter** (each case skips on its own file's absence; Java is gated once,
separately). This is test-guard correctness, not "editing tests to pass" — the absent fixture is
skipped honestly rather than faked.

With `Project2.mpp` re-deposited into the git-ignored `00_REFERENCE_INTAKE/mpp/` this session, the
native MPXJ read was confirmed **exact**: **145 rows** (the UID-0 project summary + 144 activities,
UID 1 absent), project name **"Commercial Construction"** — matching the committed golden MSPDI for
the same sample. `Project5.mpp` was not provided this session, so its case skips; **full numeric
Acumen Fuse v8.11.0 / SSI parity on a raw `.mpp` still awaits the golden exports** (tracked under
R-02 / R-03 — this decision confirms the *structural* `.mpp → MSPDI → model` read, not the metric
parity, which continues to run on the committed golden MSPDI via `pytest -m parity`).

The `.mpp` is **not** committed — it is double git-ignored (`*.mpp` and `00_REFERENCE_INTAKE/*`),
verified with `git check-ignore`. Per `00_REFERENCE_INTAKE/DEPOSIT-HERE.md`, schedule files are CUI
by default and must not be deposited in a cloud session unless the data owner confirms they are
non-CUI/authorized; the operator made that call by uploading the file directly for this validation.

## Consequences

- **CI: 872 passed, 3 skipped** (+22 new guard tests in `tests/guards/test_endpoint_scheme.py`).
  The 3 skips are the real-`.mpp` cases (no fixture travels into CI). **Locally with `Project2.mpp`
  deposited: 874 passed, 1 skipped** — the two native-parse cases run and pass; only the
  Project5 case remains skipped.
- ruff / ruff-format / mypy `--strict` / bandit / pip-audit all clean; **parity 10/10** unchanged.
  Every edit is on the AI egress guard plus one test guard — no scheduling, metric, importer, or
  web-report behavior changed.
- The adversarial re-test is locked in by the new tests: `file://`, `ftp://`, `gopher://`,
  `data:`, and remote `http(s)` endpoints are rejected by **both** backends; loopback `http(s)`
  (including `http://[::1]`) is still accepted; redirects are refused (`_NoRedirect` returns
  `None`).
