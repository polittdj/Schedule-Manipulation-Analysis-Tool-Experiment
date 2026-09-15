# ADR-0496 — The gateway's own verdict was "Expired Key": the tool sent the pasted key intact and the credential had expired at the AI Hub; a re-paste of the held key is named as such, and an expiry verdict leads the banner with the date and the one remedy (OR-17 §4 answered; OR-19)

- **Status:** Accepted — 2026-09-15 (the operator's screenshot of v1.0.262, 17:05Z: *"I am still getting this error message when I try to connect to the NASA approved API LLMs … Find the root cause for this error and fix it."*).
- **Version:** 1.0.264
- **Extends:** ADR-0493 (OR-17 — the key path proven on the wire, the receipt, the banner quoting the gateway's own reason; §4 asked the operator for exactly the evidence this screenshot carries), ADR-0488 (OR-16 — the reason read from the response).
- **Shipped:** `ai/refusal.py` (`ExpiredKey`, `expired_key_details` — the server's expiry verdict, word-bounded, with its two optional timestamps), `web/settings.py` (`_settings_receipt` names a re-paste of the held credential `unchanged`; `_receipt_html` renders it as a warning; the refused-key banner leads with the expiry when the gateway names one), `web/state.py` (the receipt's vocabulary), `web/app.py` (the Save handler passes the credentials held BEFORE the save), `tests/web/test_gateway_wire.py` (the re-paste in one process, on the wire), `tests/web/test_gateway_settings.py`, `tests/web/test_settings_receipt_browser.py`, `tests/ai/test_refusal_reason.py`.

## Context

The v1.0.262 screenshot — the first from a build that states its version and quotes the gateway
(OR-17 / OR-18 shipped this morning) — shows, on one page: the receipt *"Saved. Gateway API key:
**replaced** — 25 characters now held. Local server API token: none held."*, then the banner
*"Approved-gateway AI is OFF — `https://proxy.fast.luna.nasa.gov` answered but refused the request:
server returned HTTP 401 (its reason: **"Authentication Error - Expired Key. Key Expiry time
2026-09-12 20:36:47.844000+00:00 and current time 2026-09-15 17:05:33.767685+00:00"**). The gateway
answered and refused the credential the tool sent — the saved key, 25 characters. A key that worked
before and is refused now has usually expired or been rotated at the AI Hub …"* — and the operator
asked the tool to be fixed.

### What the screenshot settles (QC-2: read as evidence, not as a complaint)

1. **V-4 is answered.** The gateway's own refusal reason — the one thing OR-17 §4 said only the
   operator could supply — is on the page: an **expired credential**, with the gateway's record of
   the expiry (2026-09-12 20:36:47 UTC) and its own clock (2026-09-15 17:05:33 UTC): **2 days 20
   hours** after the expiry.
2. **The key path is proven by the gateway itself, not by our tests.** A gateway cannot report a
   credential it does not recognise as *expired*: an unknown, cut, garbled or wrongly-headed key is
   *invalid*, not *expired*. The gateway found the 25 characters the tool sent in its own key
   records and read that record's expiry. So the pasted key left the form, the store and the
   `Authorization: Bearer` header **intact** — the DPAPI round trip (ADR-0493's real-Windows
   step), the header shape and the field placement are all confirmed on the operator's machine by
   the server's answer, in one line.
3. **The length is a whole key, not a cut paste.** 25 characters is `sk-` + 22 URL-safe characters
   — the shape a LiteLLM-style proxy issues (`"sk-" + token_urlsafe(16)`); the wording *"Authentication
   Error - Expired Key. Key Expiry time … and current time …"* is that proxy family's expired-key
   message. Both statements are from memory of that project's source, **not verified against it** —
   nothing here depends on them; the gateway's verdict stands on its own.
4. **The operator's history fits.** *"I input the API code as I always have"*: the same key,
   re-pasted. On 2026-09-12 the same key answered HTTP 401 outside the tool (PowerShell); the
   gateway's expiry for it is 2026-09-12 20:36:47 UTC — which side of that instant the PowerShell
   request fell on is UNVERIFIED and no longer matters. The 09-11 morning **403** is a different
   status and stays a separate question (the transaction-log lines the register still asks for).

### The one competing hypothesis, refuted before this was reported (QC-1)

*The tool keeps sending a key held in memory from BEFORE the Save, so the receipt says "replaced"
while the wire carries the old key.* ADR-0493's wire test drove a fresh process, not a re-paste in
the same one. Read first: the settings banner probes with a backend built from `state.ai_config`
at render time (`settings._gateway_or_none` is the factory's constructor, no cache), the Save
handler assigns a new `AIConfig` and nulls `backend_cache`, and that cache's key is the config
value with the credential as a compared field. Then executed:
`test_a_key_re_pasted_in_the_same_process_is_the_key_sent_on_both_paths` pastes a wrong key and
then the right key in ONE process against the loopback fake gateway on the REAL transport — the
settings probe and the Ask path's routed backend both carry the key pasted LAST, byte for byte
(green on the pristine tree; mutant M4 below makes the handler keep the old key and the test goes
red by name). The hypothesis is dead. **The root cause is the credential: it expired at the AI Hub
on 2026-09-12 20:36:47 UTC, and no change to this tool can renew a key.**

### Why the tool still changes

Two things on that page let the operator believe the tool was at fault, and both were the tool's
to fix:

- The receipt said **"replaced"** for a key identical to the one already held. "Replaced" implies
  that something changed; nothing had. A paste identical to the held credential must be named as
  a *re-paste*, with its consequence (a refused key re-pasted stays refused).
- The banner quoted the verdict but then offered the generic guess (*"has usually expired or been
  rotated … or is not entitled"*) as if the reason were unknown. When the gateway's own words name
  an expiry, the banner must lead with the fact — the date, how long before the request — and the
  one remedy: **a NEW key from the Hub**; re-pasting the expired one changes nothing.

## Decision

1. **The receipt tells a re-paste from a replacement.** `_settings_receipt` receives the credentials
   held BEFORE the save; a posted value equal to the held one is `unchanged` — rendered *"re-pasted
   — identical to the key already held (N characters); if the gateway refuses this key, pasting it
   again changes nothing — get a NEW key from the AI Hub"* as a **warning**, not a success; a
   different value of any length is `replaced` as before; blank still keeps. The local server's
   token follows the same rule. Never the characters (ADR-0403).
2. **An expiry verdict leads the banner.** `ai.refusal.expired_key_details` recognises a reason that
   says *expired / expires / expiry* (word-bounded) and takes, when they parse, the expiry
   timestamp after *"expiry time / at / on"* and the server's clock after *"current time"*
   (ISO-8601, `Z` or an offset, naive read as UTC). The banner then reads: *"… refused the
   credential the tool sent — the saved key, 25 characters — because it has **EXPIRED on 2026-09-12
   20:36 UTC** — 2 days 20 hours before this request. Nothing in this tool can renew a key:
   **generate a NEW key at the AI Hub**, then paste the CURRENT key from the Hub into the Gateway
   API key field below and Save (re-pasting the expired key changes nothing …)"*, the expiry on a
   `data-sf-key-expired` attribute for the pins. A reason that says only *"expired"* gets the
   date-less form; a server clock behind the expiry claims no elapsed time; the gateway's own
   words still ride the banner in full.
3. **The re-paste wire test stays** as the regression guard for the refuted hypothesis.

## Verification (QC-1)

- **Red-first, by name, on the pristine tree:**
  `test_an_expired_key_verdict_is_parsed_with_its_expiry_and_the_gateways_clock` (no parser),
  `test_an_expired_key_verdict_leads_the_banner_with_the_expiry_and_the_only_remedy` (the generic
  guess), `test_re_pasting_the_identical_credential_is_named_as_such_never_as_replaced`
  ("replaced" twice); the date-less / skewed-clock parser test fails on import for the same reason.
  After: **130 passed** across `test_refusal_reason`, `test_gateway_settings`, `test_gateway_wire`,
  `test_settings_receipt_browser` and the monolith-split contract.
- **Measured in Chromium** (`test_settings_receipt_browser`, four themes at 1,440 px, the real
  form): each theme pastes a distinct 25-character key (the shared server would otherwise read
  every theme after the first as a re-paste — which it now honestly is), the "replaced" receipt is
  a laid-out, bordered box inside the panel; then the SAME key pasted again renders the re-paste
  receipt — visible, bordered in the theme's notice tokens, reading *"re-pasted — identical to the
  key already held"* and never "replaced"; the key never in the page.
- **Mutation battery on a shadowed copy** (`-p mutcheck` asserting `ai.refusal`, `web.settings`
  and `web.app` are the copy): the verdict is recorded in the SESSION-LOG entry.
- Statics clean under both ruff binaries, `ruff format --check`, mypy strict, bandit,
  `node --check`. Version 1.0.264; wheel + nine installers rebuilt; the full suite and `-m parity`
  on the final tree: the SESSION-LOG entry.

## Consequences

- **OR-17 §4 is answered; OR-19 registers this unit.** What remains is the operator's alone and is
  now stated on the page: generate a NEW key at the NASA AI Hub (and read its expiry there when it
  is issued — the Hub sets it; the tool learns it only when the gateway refuses), paste it, Save.
  The `/v1/chat/completions` request ADR-0493 asked for is no longer needed for V-4. The 09-11
  `"ok": false` lines stay the only evidence that decides the prompt-size question.
- The receipt's vocabulary gains `unchanged`; every renderer of `_SettingsReceipt` handles it.
- A refusal whose reason merely contains the word "expired" (an OAuth *"The access token expired"*)
  takes the same lead — the class is the same: the server says the credential's time is over.

## Deliberately NOT done

- **No code can renew, refresh or extend a key** — no auto-retry, no "renew" button, no countdown:
  the tool never sees an expiry until the gateway refuses, and inventing one would be a figure the
  file did not give.
- The proxy-family claims in §3 above are not verified against that project's source and nothing
  is built on them.
- The 09-11 HTTP 403 (a different status) is not re-diagnosed here.
