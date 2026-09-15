# ADR-0493 — The installed build is measured from the screenshot's own wording (v1.0.255/256, not v1.0.257+); the gateway key path is proven on the wire and on real Windows; a Save says what it did with each credential, and the page states its version (OR-17)

- **Status:** Accepted — 2026-09-15 (operator directive, the same day: *"… solve … by getting to the root cause and creating tests, pass and fail, and testing your solution in a sandbox environment until you find a solution that fixes the problem."* — OR-17)
- **Version:** 1.0.261
- **Extends:** ADR-0403 (the gateway credential's rules — never a page, a log, a repr, a URL; the LENGTH is the one disclosed fact), ADR-0404 (the persistent store and its Windows DPAPI protector — its "no DPAPI testing in CI" clause is closed here), ADR-0485 (the local server's token — the second masked field), ADR-0488 (OR-16's diagnostics and the one-backend disclosure — measured never to have reached the operator's machine), ADR-0393 (QC-1 / QC-2).
- **Shipped:** `web/state.py` (`_SettingsReceipt`, `SessionState.settings_receipt`), `web/app.py` (the POST computes the receipt, the GET consumes it once), `web/settings.py` (`_settings_receipt`, `_receipt_html`, the `tool version` chip, the local-token label), `ai/refusal.py` (a scheme-only challenge as the last-resort reason; `_body_reason` factored), `.github/workflows/installer-smoke.yml` (the real-Windows DPAPI round-trip + tamper step), `tests/ai/test_dpapi_marshaling.py` (8, NEW), `tests/web/test_gateway_wire.py` (6, NEW), `tests/web/test_settings_receipt_browser.py` (4 themes, NEW), `tests/web/test_gateway_settings.py` (+6), `tests/ai/test_refusal_reason.py` (+1); `docs/STATE/OPERATOR-REQUESTS.md` (OR-17 measured; OR-16b's stale status corrected).

## Context

**The report, verbatim:** *"This is what I am getting when I try and activate the AI models
approved for ITAR and CUI. I input the API code as I always have and it doesn't work. I also
have no clue what 'Local server API token (LM Studio …)' means or does. This is new."* The
screenshot (registered by the previous session in OR-17): Backend = Approved AI gateway,
`https://proxy.fast.luna.nasa.gov`, approval checked, the key field's placeholder *"(a key is
saved — leave blank to keep it)"*, the red panel *"could not reach … server returned HTTP 401.
The gateway answered but requires authentication: paste your organization-issued key …"*, the
Model row *"qwen2.5:7b-instruct — not installed · not reachable: server returned HTTP 401"*, and
every backend's fields rendered at once. The kickoff's hypotheses, in order: the Windows DPAPI
branch of the key store (UNVERIFIED since ADR-0488) · the header shape · the catalog probe's 401
masking a working generation · an expired or unentitled key (V-4 only).

**First measurement — the installed build, from the words on the screen.** The kickoff said
"establish the version from the banner"; the page carries no version anywhere (only the static
asset URLs do, `?v=`), so the banner cannot say. The wording can. `git show` at the three release
commits: the placeholder *"a key is saved — leave blank to keep it"* exists at v1.0.255
(`2ae8d06b`) and v1.0.256 (`c31259fe`) and reads *"a key is saved — N characters; …"* at v1.0.257
(`6708cbff`); the banner's *"could not reach … requires authentication"* with a key held is the
pre-0.257 text (0.257 reads *"refused the credential the tool sent"*); `data-backend-only` (the
one-backend rule) has 0 hits at 0.255 / 0.256 and 5 at 0.257. The *Local server API token* field
was introduced in 0.255. **The installed build is v1.0.255 or v1.0.256.** Nothing OR-16 shipped
(the quoted reason, the key's length, one backend at a time) had reached the operator; the
"every backend at once" is that build, not a regression. The previous session had already
handed the operator the three PowerShell steps for the v1.0.260 installer.

**The kickoff's first hypothesis, refuted on the Python side and pinned on the Win32 side.**
`config_store._dpapi_protect` / `_dpapi_unprotect` had never executed under a test (every store
test injects a lambda protector; the functions are `pragma: no cover`). Driven against a fake
`crypt32` that reads the input blob through the same pointer and length the real
`CryptProtectData` would (`gc.collect()` inside the read, so a temporary buffer the caller failed
to keep alive dies there): five keys round-trip byte for byte (1, 25, 67 bytes, UTF-8, 4 KiB),
`cbData` is the key's length, the flags are 0 (user scope), one `LocalFree` per call, a tampered
blob raises. The struct is `{DWORD; BYTE*}` with native alignment — Win32's `DATA_BLOB` — and
`ctypes.cast` keeps the buffer alive through `_objects`. The real Win32 calls run where the repo
runs on Windows: a new `installer-smoke` step through the installed venv on `windows-latest`
saves a 25- and a 67-character key, asserts no plaintext and the dpapi field at rest, reloads
them, then flips one byte of the blob and requires a KEYLESS load with the other credential
intact. **Its first verdict is CI's, not this file's** — the SESSION-LOG follow-up carries it.
And the screenshot itself refutes the "saved but empty" reading: a failed unprotect comes up
with *"(none set — paste your key)"*, never *"a key is saved"*.

**The key path on the wire, measured for the first time.** ADR-0488 verified the path with
injected openers; `gateway._urllib_gateway_opener` (the real transport) had never met a server in
a test. Against a loopback fake of the gateway that answers only to the exact
`Authorization: Bearer <key>` and refuses with a `WWW-Authenticate` challenge plus a JSON body:
the header reaches the socket byte for byte with a dead corporate proxy in the environment (the
empty `ProxyHandler` is what keeps it direct); a refused key reaches the diagnostics as
`server returned HTTP 401 (its reason: "The access token expired")`; a key pasted once through the
form, persisted, and reloaded by a fresh launcher-path app authenticates the catalog AND a
generation; a stale key on disk renders the photographed banner with the gateway's own reason and
*"the saved key, 25 characters"* through the real `_gateway_or_none`. The one liberty is at the
socket — the approved host is rewritten to the loopback address inside a transport shim — and a
test pins that the allowlist still refuses the loopback address at construction.

**The failure the installed build could not show — and could not name.** On v1.0.255 / 256 two
look-alike masked fields sit one above the other, the local server's token first. Reproduced red
on the pristine tree: a fresh key pasted into *Local server API token* under the gateway backend
is stored as the local token, the gateway key stays the OLD one (blank keeps — ADR-0403's rule,
correct), the page reads *"a key is saved"* and the gateway keeps refusing, and no word above the
form says where the paste went. Whether this is what happened on 2026-09-15 is UNVERIFIED; that
it CAN happen on the operator's build with nothing to show for it is measured.

**What the evidence still says about the key itself.** On 2026-09-12 the same key answered
HTTP 401 outside the tool (`Invoke-WebRequest …/v1/models`, ADR-0488). A key that answered on
09-11 21:58Z and is refused since 09-12 has expired, been rotated or lost its entitlement —
unless it is not the key being pasted, which is the paragraph above. Nothing in this repository
changes that; what this unit changes is that the next screenshot will say which.

## Decision

1. **A Save answers with a receipt, once.** `POST /settings` records on the session what it did
   with each credential — `replaced` when the field carried a value, `kept` when it was blank
   and a value was held, `none` — with the gateway key's length now held (the one comparable
   fact; never its characters), and names a credential pasted into a field that NO selected
   backend (primary or cross-check) uses as **misplaced**. `GET /settings` renders it as
   `.notice.ok` (and `.notice.warn` for a misplaced paste: *"A token was pasted into Local server
   API token — a field only the OpenAI-compatible (local) backend uses; the Approved AI gateway
   never sends it. If that was your gateway key, paste it into the Gateway API key field below
   and Save. The Gateway API key itself was kept …"*) and clears it — one-shot, like the import
   flash. The save still stores the misplaced value (a token is a token; moving a secret between
   fields silently is refused).
2. **The page states its version.** The status line carries `tool version: <installed package
   version>` from `chrome._ASSET_VERSION` (the installed metadata, never a literal), so a
   screenshot pins the build.
3. **The local-token label names its owner and its non-owner:** *used ONLY by the
   OpenAI-compatible (local) backend … the Approved AI gateway never sends it — the gateway's key
   goes in the Gateway API key field.* (On 0.257+ the field is hidden under a gateway primary by
   `settings.js`; the label is for the build without it and the page without JavaScript.)
4. **A scheme-only challenge is quoted as the reason, last.** `http_refusal_detail` falls
   through the error fields and the body to the bare challenge — `challenge: Basic realm="…"` —
   so the banner shows the scheme the gateway wants; a body reason still outranks it, a blank
   challenge is no reason, every prior pin holds byte for byte.
5. **The DPAPI branch is measured on real Windows in CI** (the `installer-smoke` step above),
   closing ADR-0404's "no DPAPI testing in CI"; its Python is measured on every platform against
   the fake `crypt32`.

## Deliberately NOT done

- **Sending the key in a second header (`x-api-key`) or a second scheme:** the gateway accepted
  `Bearer` on 09-11 (ADR-0486's answers came through it); a change of scheme is a hypothesis V-4
  refutes or confirms in one line, and the banner now quotes a scheme-only challenge. ADR-0403's
  and ADR-0485's refusals stand.
- **A completion-shaped availability probe when the catalog is refused** (the "catalog 401 masks
  a working generation" hypothesis): the tool gates routing on `GET /v1/models` by design
  (`route_backend`), and the catalog loaded on 09-11 with the same scheme. Registered UNVERIFIED
  with the one request that settles it (OR-17 §4); not built on a hypothesis.
- **Hiding the local-token row server-side:** ADR-0488's pin ("nothing hidden server-side, so no
  JavaScript shows everything") stands; the receipt catches the wrong-field paste on every build
  and every page.
- **Normalising a pasted key** (stripping a `Bearer ` prefix or quotes): a credential is stored
  as pasted, trimmed of surrounding whitespace only (unchanged); the receipt's length is what
  shows a cut or padded paste.
- **The catalog's `— not installed` wording and the Ollama default model under the gateway**
  (ADR-0488's residual): unchanged, a small follow-on.

## Verification (QC-1)

- **Red first, on the pristine tree** (four executable probes before a line changed): the
  misplaced paste leaves the OLD key, the page says *"a key is saved"* + HTTP 401 and nothing
  about the paste — RED; the version absent from the visible text — RED; a scheme-only challenge
  yields `""` — RED; the real transport puts the Bearer header on the wire and a 401's challenge
  reaches `probe_error_text` — GREEN (the chain proof, pinned so it cannot regress). After the
  change: the touched five modules **63 passed**; the four-theme Chromium test of the receipt
  (visible box inside the panel, the theme's notice border, the version chip, gone on reload,
  the placeholder then stating the length) **4 passed**; the DPAPI marshaling module 8 passed
  (green on the pristine code by construction — its teeth are the six DPAPI mutants below).
- **Mutation battery, 20 mutants on a shadowed copy** (`PYTHONPATH` shadow, a plugin refusing to
  run unless the imported package IS the copy; the control run 19 passed first): **20 / 20 RED by
  name** after two instrument fixes the first pass exposed — the rig's by-name matcher did not
  match parametrized ids (M13 / M17 read "red (other)" while their named test's cases were the
  failures), and the proxy test survived a proxy-consulting mutant (M19) because the build
  environment's `NO_PROXY` excluded 127.0.0.1: the test now deletes `NO_PROXY` / `no_proxy` (the
  corporate-laptop shape `_make_opener` exists for) and reads red. By name: the bare-challenge
  fallback dropped · the challenge outranking the body · a posted key reading `kept` · misplaced
  detection removed · the gateway "using" the local token · the cross-check backend ignored · the
  held length omitted · the version chip a literal · the GET never consuming the receipt · a blank
  post reading `replaced` · the local token's post dropped · the label losing the gateway sentence
  · `cbData` off by one · machine-scope flags · a failed unprotect returning empty · `LocalFree`
  dropped · the unprotect read truncated · the transport dropping the headers · the transport
  consulting the system proxy · the probe text dropping the reason.
- Statics: both ruff binaries (0.15.8 on PATH, CI's 0.16.7) clean · `ruff format --check` clean ·
  mypy strict 165 files · bandit exit 0 · `node --check` clean. The full suite, `-m parity` and
  the Windows step's first verdict are in the SESSION-LOG's follow-up with the PR number.

## Consequences

- **OR-17 is SHIPPED IN PART:** the operator installs v1.0.261, pastes the CURRENT key from the
  NASA AI Hub into *Gateway API key*, and reads the receipt (*replaced — N characters*) and the
  banner (the gateway's own words, the length sent, the version). If the banner still refuses
  the replaced key, the key or the gateway is the cause and V-4's text names which; the
  completion request in OR-17 §4 settles the catalog hypothesis. Neither is this repository's
  to change.
- **UNVERIFIED, stated:** the real-Windows DPAPI verdict until the `windows` check reads green on
  this PR; whether the 09-15 paste landed in the wrong field; the gateway's refusal text (V-4);
  the current key's validity.
- **Residual, registered:** the receipt is per-session in-memory (a second browser tab that
  loads /settings first consumes it — one operator, one tab, by design); the wire tests rewrite
  the approved host inside a shim (stated in the module; the allowlist pin guards the boundary).
- Review cover is still absent (Codex quota exhausted); this unit's review is the battery and the gate.
