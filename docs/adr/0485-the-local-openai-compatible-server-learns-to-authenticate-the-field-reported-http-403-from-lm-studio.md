# ADR-0485 — The local OpenAI-compatible server learns to authenticate: the field-reported HTTP 403 from LM Studio closes the credential dimension the local backend never had, and the Ask panel's note now names the field instead of a page

- **Status:** Accepted — 2026-09-11 (operator directive, same day: *"do a deep dive and figure out why the ASK the AI is not working the way it should and fix it."* — OR-14)
- **Version:** 1.0.255
- **Extends:** ADR-0403 (the gateway learned to authenticate — the same defect class, on the REMOTE backend), ADR-0404 (the persistent settings store and its key protector), ADR-0478 (`/api/ask` says WHY there is no written answer), ADR-0129 (Ask-the-AI), ADR-0393 (QC-1 / QC-2)
- **Shipped:** `ai/backend.py` (`AIConfig.openai_api_key`, `repr=False`), `ai/ollama.py` (`HeaderOpener`, `_urllib_header_opener`, `is_auth_refusal`), `ai/openai_compat.py` (`OpenAICompatBackend(api_key=…)` — the token on EVERY request; the opener is now 4-arg), `ai/factory.py` (the token threaded to the primary AND the cross-check second backend), `ai/config_store.py` (a second protected field: `openai_api_key_dpapi` / `openai_api_key_plain`), `web/settings.py` (the **Local server API token** field; the refused-probe hint), `web/app.py` (the POST's blank-means-keep; the models probe authenticates with the SESSION's token; `_generation_failed_note`'s 401/403 branch, `_no_model_note`'s refused-probe branch, and the gateway-endpoint label fix), `tests/web/test_openai_compat_auth.py` (15, NEW — the end-to-end reproduction against a loopback stub), `tests/ai/test_backends.py` (+5; the five OpenAI-compatible doubles become 4-arg), `tests/ai/test_config_store.py` (+5), `tests/guards/test_observed_banner.py` (the shared double accepts the fourth argument)

## Context

The operator photographed `/integrity`'s Ask panel with the backend set to the OpenAI-compatible
server (LM Studio on `http://127.0.0.1:1234`), a schedule-manipulation question in the box, and
this result line where the written answer should be:

> the model server at http://127.0.0.1:1234 was reachable, but the generation itself failed:
> server returned HTTP 403. AI Settings shows its live status. These are the engine's cited facts
> that match your question — open AI Settings.

**The sentence is true and useless.** "Reachable" is `GET /v1/models` answering (the availability
probe passed, so the backend routed); the 403 is `POST /v1/chat/completions` refusing the
generation. AI Settings then reads *Local AI is ON* — the page the note sends the operator to
cannot show anything wrong, because the probe it renders from succeeded. There was nothing on
that page, or anywhere in the tool, that could resolve a refusal.

**The deep dive, refuted before reported.** Three hypotheses died on the code before the fourth
survived:

1. *A corporate proxy in the path* — refuted: `openai_compat` already sends every request through
   `ollama._NO_REDIRECT_OPENER`, built with an EMPTY `ProxyHandler` (a direct loopback connection,
   no redirects), so no proxy sees the request; and a proxy refusal would have failed the probe
   too.
2. *The wrong model id* (the docstring's inherited claim that an empty id routes to the loaded
   model) — not the cause: a wrong model id on an OpenAI-compatible server is a 404 / 400 with a
   JSON error, not a 403; and the tool cannot verify the claim anyway (§ Residuals).
3. *The Ollama path* — not involved: `backend == "openai"` never touches `OllamaBackend`.
4. **The backend has ZERO credential surface — measured across every layer.** No `AIConfig`
   field, no settings-form field (the form's only password input is `gateway_api_key`), no
   constructor parameter (`OpenAICompatBackend(endpoint, model, *, timeout, probe_timeout,
   opener)`), no argument at either factory call site, and no header slot in its 3-arg opener
   (`Opener = Callable[[str, bytes | None, float], str]` — the gateway grew a 4-arg
   `GatewayOpener` for exactly this reason in ADR-0403, and the local backend was left on the
   3-arg one because "a loopback Ollama never has that dimension"). The only 401/403 diagnostic in
   the tree is `_gateway_status_note`'s, gateway-only.

**The vendor side (read 2026-09-11 from LM Studio's documentation repository on GitHub — the
`authentication.mdx` page; lmstudio.ai itself was egress-blocked from the build session, so no
verified URL is recorded here and the page path should be verified against the live docs).**
LM Studio's local server can *Require Authentication*: it is off by default, switched on under
the Developer page's Server Settings, tokens are issued under *Manage Tokens*, and a client sends
`Authorization: Bearer <token>`. The 0.4.0 release notes list "Authentication configuration with
API tokens", which post-dates this backend's integration. **UNVERIFIED and NOT documented on the
page read:** the exact status code for a missing or wrong token (401 vs 403), and whether
`GET /v1/models` is exempt. The operator's screenshot is the only evidence on both: a 403, with the
catalog open. The stub this ADR is proven against encodes THAT observed shape (and, as a second
mode, a catalog that demands the token too — the shape the docs leave open).

**Reproduced on the wire, on the pristine tree, before a line was written.** A loopback
`http.server` in the operator's shape (catalog 200, chat 403 without the Bearer) behind a real
`/api/ask` through a real `OpenAICompatBackend` and the real urllib transport produced, verbatim:
*"the model server at http://127.0.0.1:35801 was reachable, but the generation itself failed:
server returned HTTP 403. AI Settings shows its live status."*

## Decisions

Standard OpenAI-compatible Bearer authentication for the LOCAL server, with the credential handled
as a credential — ADR-0403's rules, applied to the backend ADR-0403 left out:

1. **`AIConfig.openai_api_key`** — `field(default="", repr=False)`: out of every accidental
   repr/str, still in equality (a new token busts the routed-backend cache immediately).
2. **The local backends' transport grows the header dimension in ONE place.** `ai/ollama.py`
   defines `HeaderOpener` (`(url, data, timeout, headers) -> body`) and `_urllib_header_opener`
   beside the 3-arg `Opener` / `_urllib_opener`; `OpenAICompatBackend` binds the 4-arg pair, Ollama
   keeps the 3-arg pair (it has no auth dimension; nothing about Ollama changes). The transport
   body is the gateway's, duplicated deliberately: its `nosec` justification is different
   (loopback-validated endpoint, not the approved-gateway allowlist), and ADR-0403's gateway
   module is untouched by this change.
3. **`OpenAICompatBackend(api_key=…)` sends `Authorization: Bearer <token>` on EVERY request** —
   the availability probe, the catalog, the generation. A server that guards its catalog is
   otherwise refused at the probe and never routes (the second stub mode proves the token fixes
   that too). An empty token sends **no header at all** — never a malformed bare `Bearer ` — so
   a server with authentication off receives byte-for-byte the request it received before the
   field existed.
4. **The token reaches every construction.** `factory.openai_or_none` AND `factory.second_or_none`
   thread it (the cross-check second model reads the same server); `/api/ai/models?kind=openai`
   authenticates with the **session's saved** token server-side — the credential never travels in
   the probe's query string (ADR-0403's log-leak rule).
5. **It persists like the gateway key** (ADR-0404): `config_store` wraps it with the same
   protector into `openai_api_key_dpapi` (Windows, DPAPI user scope) or `openai_api_key_plain`
   (POSIX, 0600 file); a failing protector omits the token and keeps everything else; an
   unrecoverable blob comes up tokenless, never broken. The single-key machinery became
   `_protect_into` / `_load_key(doc, field, what)` over two fields.
6. **The form field is a credential field.** *Local server API token* — `type=password`, renders
   `value=""` every time, only its placeholder discloses whether a token is held; blank on a
   re-save means KEEP (the form never echoes it, so every ordinary save posts it blank); a value
   replaces; *Turn the AI off* and a session wipe rebuild the config and so forget it.
7. **The note names the field, and states the cause it cannot see.** `is_auth_refusal` (word-
   bounded `HTTP 401|403`; `HTTP 4013` is not one) gates a new branch of `_generation_failed_note`:
   for the local server — *"answered the generation with server returned HTTP 403 — it refused the
   request, not the connection. If your server requires authentication (LM Studio: Developer >
   Server Settings > Require Authentication, then Manage Tokens), paste its API token into the
   Local server API token field in AI Settings and Save (no token is saved / a token is saved — if
   it still gets this, the token may be wrong or revoked). If authentication is off, the refusal
   came from the server itself or from something in front of it on this machine (a proxy or
   endpoint-security agent) — check the server's log."* The tool cannot see whether the server's
   authentication is on, so the alternative is stated, never hidden. The gateway gets its own
   branch naming the *Gateway API key* field; Ollama stays on the generic line (no auth dimension).
   The settings page's refused-probe hint says the same instead of *"Start your local server"* —
   advice that is exactly wrong for a server that answered — and so does the Ask panel's
   `_no_model_note` when the availability probe itself is refused (a server that guards its
   catalog never routes; before this its note read *"could not reach … Start it"*).
8. **A mislabel fixed on the way through:** `_generation_failed_note` read `cfg.openai_endpoint`
   for every non-Ollama backend, so a GATEWAY generation failure was reported at
   `http://127.0.0.1:1234`. Each backend now names its own endpoint.
9. **Refused:** an `SF_OPENAI_API_KEY`-style environment fallback (ADR-0403's existed because the
   config was per-launch in-memory; ADR-0404 made it persistent, so the friction it solved is
   gone — YAGNI); an `x-api-key` header (a search result mentioned it; the documentation page read
   documents Bearer, and sending an undocumented second header on every request is speculation).
   Neither is a loss the operator can feel; both are one line if the field ever proves it.

**Shipped code changed → v1.0.254 → v1.0.255**, wheel + nine installers rebuilt
(`SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca`; on the unshallowed clone
`git log -1 -- tools/mpxj` reads that sha itself).

## Verification (QC-1)

*Red first, on a pristine `origin/main` worktree* (the three test files copied in, the package
imported from that worktree — proven by `schedule_forensics.__file__`): the **25 new tests → 23
failed, 2 passed**, and the four OpenAI-compatible doubles that moved to the 4-arg contract failed
too (a 3-arg backend cannot call a 4-arg double — the contract change, by design): 27 failed / 24
passed over the three files' 51 tests. The 23 are the missing capability by name (no field, no
parameter, no header, no branch, no persistence). The two greens are the NEGATIVE pins
(`test_other_local_failures_do_not_blame_the_token`, `test_an_ollama_403_stays_on_the_generic_line`)
— green by construction on a tree where the field does not exist; their teeth are proven below by
mutants that make the branch fire where it must not (M21 / M22 / M24 / M30). The end-to-end test's
red is the operator's sentence, verbatim, on the wire.

*Green:* the new tests and every touched neighbour (13 files — backends, config store, observed
banner, gateway settings, the no-answer census, both coverage pins, txlog, the endpoint-scheme and
loopback guards) — **314 passed, 2 skipped.** Full suite after the bump and the rebuild: 5,238 passed / 5 skipped in 35:52.
`-m parity`: 96 passed. Both ruff binaries (0.16.7 = CI's, and the 0.15.8 that shadows it on PATH),
mypy strict (163 files), bandit, `node --check`: clean.

*Teeth:* a **30-mutant** battery on a SCRATCH copy of the package under a PYTHONPATH shadow (the
instrument — `tests/` — never mutated; the shadow proven by `schedule_forensics.__file__`), each
mutant counted only when the run is red AND the named test is among the failures — **30/30 caught
by name**: `header_dropped_on_generate` · `header_dropped_on_get` · `bare_bearer_when_empty` ·
`token_in_backend_repr` · `token_in_config_repr` · `factory_drops_primary_token` ·
`factory_drops_second_token` · `probe_drops_session_token` · `store_skips_the_protector` ·
`store_skips_chmod` · `store_drops_token_on_load` · `store_reads_the_gateway_field` ·
`store_token_not_persisted` · `post_ignores_blank_keeps` · `form_echoes_the_token` ·
`form_unmasked` · `note_loses_the_field_name` · `note_loses_the_honest_alternative` ·
`note_always_says_no_token_saved` · `note_prints_the_token` · `auth_refusal_matches_404` ·
`auth_refusal_unbounded` · `gateway_label_regression` · `ollama_gets_the_token_note` ·
`hint_loses_the_field` · `hint_not_taken_on_refusal` · `transport_drops_headers` ·
`ai_off_keeps_the_token` · `probe_note_branch_not_taken` · `probe_note_for_ollama_too`.

*One instrument found weak while it was being written, before the battery:* the settings-page test
first asserted the field name page-wide — and the form's own label carries that name, so the
assertion could never fail. It reads the `notice err` element now, and also pins that *"Start your
local server"* is absent from it. *And the battery's own guard fired once:* when the refused-probe
branch was added, its `held` block was byte-identical to the generation note's, and two mutants
anchored on that block ABORTED as `ANCHOR x2` (28/30) instead of silently mutating the wrong
branch — ADR-0484's lesson, working; both were re-aimed on the branch's own text (30/30).

## Consequences

- The operator's next step is one field: paste the LM Studio token into **Local server API token**
  and Save. If the 403 persists with a token saved, the note says so and where to look (the
  server's log; something in front of the server) — the tool no longer claims to know.
- `OpenAICompatBackend`'s injected opener is 4-arg from here on; the five doubles in
  `tests/ai/test_backends.py` and the shared `_up` in `tests/guards/test_observed_banner.py` were
  moved deliberately, in this commit, and the module docstring says which backend takes which shape.
- **UNVERIFIED, stated:** LM Studio's exact refusal status (401 vs 403) and whether its catalog is
  exempt — the stub covers both catalog shapes, and `is_auth_refusal` accepts both codes, so the
  fix does not depend on the answer; the wording of LM Studio's menu path in the note and the
  field's tooltip is as read from the docs on 2026-09-11 and can drift with the vendor's UI; the
  backend's docstring claim that an empty model id routes to the loaded model is INHERITED and now
  says so (the live model dropdown exists so the operator never relies on it).
- **Residuals, not taken:** `_gateway_status_note` still detects a refusal with the substring
  `"401" in reason or "403" in reason` (ADR-0403's code, pinned by its own test; `is_auth_refusal`
  would be the tidier check — a one-line unit with its own red); the live model dropdown probes
  with the SAVED token, so a token typed into the field is not used by the dropdown until Save
  (the gateway behaves the same way; a pre-save probe would put the credential in a GET) ;
  `x-api-key` and an env-var fallback, as refused above.
- Review cover is still absent (Codex quota exhausted on #655–#668); this unit's review is the
  battery and the gate.
