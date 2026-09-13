# ADR-0488 — A refused gateway key is named with the gateway's own reason and the credential the tool sent; AI Settings shows one backend's fields at a time (OR-16)

- **Status:** Accepted — 2026-09-12 (the operator's two mid-session messages, in the order they arrived).
- **Version:** 1.0.257
- **Extends:** ADR-0403 (the gateway credential: never a page, a log or a repr — the LENGTH is disclosed here, never the characters), ADR-0485 (whose registered residual — the refusal detected by substring — this closes), ADR-0486 (the once-read 400 body is now shared), ADR-0402 / ADR-0404 (the armed-once gateway flow), the design system (ADR-0195) for the settings page.
- **Shipped:** `ai/refusal.py` (NEW: `http_error_body`, `http_refusal_detail`, `MAX_REASON_CHARS`), `ai/ollama.py` (`probe_error_text` quotes the reason), `ai/completion.py` (`limit_rejected` shares the body), `web/settings.py` (the refusal note; the key placeholder's length; the `data-backend-only` groups), `web/static/settings.js` (`syncVisibility`), `tests/ai/test_refusal_reason.py` (9), `tests/web/test_gateway_settings.py` (+4), `tests/web/test_settings_disclosure.py` (5), `tests/web/test_settings_disclosure_browser.py` (4 themes); `docs/STATE/OPERATOR-REQUESTS.md` OR-16 / OR-16b / V-4.

## Context

**The report, verbatim:** *"I can't log into Opus 4.8 Thinking even if I put in the API Gateway
Key."* — with the AI Settings screenshot: v1.0.256, Backend = Approved AI gateway, the key
field's placeholder *"a key is saved"*, the banner *"could not reach
https://proxy.fast.luna.nasa.gov : server returned HTTP 401. The gateway answered but requires
authentication: paste your organization-issued key …"*, and the Model dropdown showing
`qwen2.5:7b-instruct — not installed` (the catalog never loaded; the gateway model could not be
picked — the "can't log in").

**Refuted first — the tool's key path.** The diff between v1.0.254 (which answered the operator
on 2026-09-11 21:44–21:58Z) and v1.0.256 touches nothing on the path form → session → DPAPI
store → reload → `Authorization: Bearer` on `GET /v1/models`; on the real code a saved key
round-trips byte-for-byte, the probe carries it, a stale key yields exactly the photographed
text, a pasted key replaces and a blank keeps (an executable check plus the 32 existing gateway
and store tests). Then the discriminator, at this session's request, on the NASA machine and
outside the tool: `Invoke-WebRequest …/v1/models -Headers @{Authorization="Bearer <key>"}` →
**HTTP 401** with the same key (the masked paste read 25 characters). **The gateway refuses the
key itself**; no code in this repository changes that. A key accepted at 21:58Z on 09-11 and
refused on 09-12 has expired, been rotated, or is not the key being pasted.

**What the tool got wrong, measured on the code:** the banner discarded the gateway's own
reason — `probe_error_text` returned the status alone, though a 401 almost always carries one
(RFC 6750 puts it in the `WWW-Authenticate` challenge, OpenAI-style servers in `error.message`);
it could not say which credential it had sent; *"paste your key"* is the wrong advice when a key
IS saved; and it detected the refusal by substring (`"401" in reason` — ADR-0485's residual).
The operator had to reproduce the request in PowerShell to learn anything the response had
already said.

**The second message, verbatim:** *"I want the AI setup to be as user friendly and simple as
possible."* The page rendered every backend's rows at once: two look-alike masked secret fields
one above the other (the *Local server API token* directly above the *Gateway API key*), Ollama's
endpoint, context window and runtime note under a gateway session, the OpenAI-compatible endpoint
under an Ollama one.

## Decision

1. **The server's own reason is quoted, bounded.** `ai/refusal.py::http_refusal_detail` reads the
   `WWW-Authenticate` challenge (`error_description`, then `error`) and else the body — a JSON
   error document's reason string (`error.message`, `error`, `message`, `detail`, `reason`) or the
   first line of plain text — at most `MAX_REASON_CHARS` (160) on one line; markup is never quoted
   (an HTML error page names nothing an operator can act on); a truncated body still yields its
   reason field's opening run. `probe_error_text` renders it as `server returned HTTP 401 (its
   reason: "…")` and returns the bare status when there is none, so every prior pin holds byte for
   byte; `is_auth_refusal` still matches. Every backend gets it — a local server's 401 body says
   "invalid token" too. The transaction log keeps its closed vocabulary (`txlog.error_summary`,
   WP7): the reason reaches the page and the Ask panel only.
2. **The body is read once and shared.** `http_error_body` caches the bytes on the exception;
   `completion.limit_rejected` (the 400-that-names-`max_tokens` fallback, ADR-0486) reads through
   it, so the diagnostics and the fallback see the same bytes in either order.
3. **The refusal names the credential the tool sent.** With a key held, the gateway banner reads
   *"answered but refused the request: … The gateway answered and refused the credential the tool
   sent — the saved key, 25 characters …"* (or *the `SF_GATEWAY_API_KEY` environment variable*),
   says that a key which worked before and is refused now has usually expired or been rotated at
   the AI Hub or is not entitled, and sends the operator for the CURRENT key (what is pasted
   replaces; blank keeps). With no key held, the earlier *"requires authentication … paste your
   key"* text stands. The refusal is detected word-bounded (`is_auth_refusal`). The key's
   placeholder states its length (*"a key is saved — 25 characters; …"*): a cut paste is invisible
   behind a masked field, and the length is the one thing the operator can compare with the Hub.
   The characters are never disclosed (ADR-0403).
4. **One backend's fields at a time (OR-16b).** Every backend-specific row carries
   `data-backend-only="<backend …>"` — the Ollama window, cost note and endpoint (and the Ollama
   runtime note above the form); the OpenAI-compatible endpoint and local token; the gateway
   endpoint, acknowledgment and key; the answer-length limit for `openai gateway`. `settings.js`
   shows a row when one of its backends is the primary OR the cross-check backend and hides it
   otherwise (the `hidden` attribute), on load and on either picker's change — no save, no reload.
   Nothing is removed from the form: every field still posts, and without JavaScript every row
   shows. The always-on rows — classification, backend, model, timeout, answer mode, the
   cross-check picker, Save — carry no marker. What "simple" does NOT mean, and was refused: the
   classification, the approval acknowledgment and the loopback locks stay (Law 1).

## Verification

- **Red first.** `tests/ai/test_refusal_reason.py` cannot import on the pristine tree; the four
  new settings pins fail on the pristine `settings.py` by name (4 failed / 24 passed); the five
  disclosure pins fail 3 / 2 on the pristine page (the two greens are the negative pins — the
  always-on rows unmarked, nothing hidden server-side — green by construction until a mutant
  marks them). Green: the AI + settings neighbourhood 160 passed, then 100 passed with the
  disclosure; the four-theme Chromium test passes (console / daylight / apollo / jarvis).
- **Mutation battery, 11 mutants for this unit — 11 / 11 RED by name** on shadowed copies (the
  instrument never mutated): the reason always empty · the challenge ignored · the cap removed ·
  markup quoted · the substring refusal restored · the credential source swapped · the length
  omitted · the body not cached · `limit_rejected` consuming the body · the placeholder's length
  omitted · the probe text dropping the reason. One anchor went stale when a variable was
  renamed for mypy and was re-aimed; every mutant then read red.
- **Two instrument findings, recorded:** a page-wide substring assertion (*"requires
  authentication"* absent) matched the OpenAI field's title text — the pins read the gateway
  banner alone now; and a 10 KB body exceeded the read limit, so the JSON no longer parsed and
  the reason was dropped rather than bounded — the truncated-body fallback exists because that
  test failed.
- Statics: both ruff binaries (0.15.8 on PATH, CI's 0.16.7) clean · format clean · mypy strict
  165 files · bandit exit 0 · `node --check` clean.

## Consequences

- **OR-16 is SHIPPED in this version's diagnostics; the key itself is the operator's to renew.**
  V-4 (the gateway's reason text) is pending: the step-2 PowerShell (`WWW-Authenticate` + the
  401 body) was requested and had not arrived when this shipped; the v1.0.257 banner will show
  the same text.
- **OR-16b's disclosure is shipped**; a *Test connection* button was NOT added — the banner on
  load and the *Refresh models* status line already report the probe's verdict inline, and a
  third surface saying the same thing is not simpler.
- Residual, registered: under the gateway backend a saved model the catalog cannot confirm still
  reads *"— not installed"*, Ollama's wording; a fresh config's default model is an Ollama id
  (`qwen2.5:7b-instruct`) whatever the backend — the screenshot's dropdown. A gateway-aware
  default and wording is a small follow-on.
