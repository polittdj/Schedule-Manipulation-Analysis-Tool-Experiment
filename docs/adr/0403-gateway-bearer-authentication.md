# ADR-0403 — The gateway learns to authenticate: the field-reported HTTP 401 closes the auth dimension the plan never recorded

**Status:** Accepted · **Date:** 2026-08-14 · **Extends:** ADR-0402 (the approved-gateway backend).

## Context

Minutes after v1.0.202 reached the operator's NASA-connected machine, they sent a screenshot of
the settings page in the armed state: banner, endpoint select, acknowledgment — all rendering as
designed — and the diagnostic **"Approved-gateway AI is OFF — could not reach
`https://proxy.fast.luna.nasa.gov`: server returned HTTP 401"**, with the model dropdown empty
("the models dont show up" — the catalog is the `GET /v1/models` the 401 refuses).

A 401 is a *positive* transport result: DNS resolved, TLS completed, the gateway ANSWERED — and
demanded a credential the integration never sends. `APPROVED-GATEWAY-INTEGRATION.md` §1 recorded
the operator's unversioned patch as endpoint + model env vars only; how that patch authenticated
was never captured (**UNVERIFIED** — the patch worked, so an auth element must have existed or the
gateway has since enabled auth; the operator's "NASA AI Hub form setup" bookmark suggests
key-issuance is the current mechanism). The lesson stands regardless: **the integration was built
faithfully to the recorded spec, and the spec was missing a dimension only the field could reveal.**

## Decision

Standard OpenAI-compatible Bearer authentication, with the credential handled as a credential:

1. **`AIConfig.gateway_api_key`** — `field(default="", repr=False)`: out of every accidental
   repr/str, still in equality (pasting a new key busts the routed-backend cache immediately).
2. **`GatewayBackend(api_key=…)`** sends `Authorization: Bearer <key>` on **every** gateway
   request (probe, catalog, generation) via a new gateway-specific opener contract
   (`GatewayOpener(url, data, timeout, headers)` — the local backends' 3-arg opener has no header
   dimension and is untouched). An empty key sends **no** header at all, never a malformed bare
   `Bearer `. The default opener reuses the shared no-proxy/no-redirect urllib opener, so neither
   the body nor the header can be bounced off the allowlisted destination.
3. **The key never leaves the header.** Not in the transaction log (no new txlog field), not in
   any rendered page (the form input is `type=password`, renders `value=""` every time; only a
   placeholder discloses *whether* a key is held), not in a repr, and never in a URL
   (`/api/ai/models?kind=gateway` authenticates with the **session's** resolved key server-side —
   a credential in a GET query string is a log-leak shape).
4. **Blank means keep.** The form never echoes the key, so every ordinary re-save posts the field
   blank — the POST handler treats blank as "keep the held key" (a save of any other setting must
   not silently de-authenticate the gateway). A non-blank value replaces it. `ai-off`, wipe, and
   quitting forget it (in-memory config, unchanged).
5. **`SF_GATEWAY_API_KEY` env fallback** (`factory.resolve_gateway_api_key`: config key first,
   env second): the config is per-launch in-memory and a long pasted key per launch is real
   friction, while the acknowledgment stays one deliberate click. This does not contradict
   ADR-0402's no-env-seeding posture: the env var chooses only a *credential for the
   already-allowlisted destination* — it can never choose a destination, a model, or consent.
6. **The 401/403 diagnostic says what to DO** — "the gateway answered but requires
   authentication: paste your organization-issued key (e.g. from the NASA AI Hub) into the
   Gateway API key field and Save" — instead of just repeating the status code.

**Shipped code changed → v1.0.202 → v1.0.203**, wheel + nine installers rebuilt (lockstep 64/64).

## Verification (QC-1)

*Red first:* the new auth tests ran against the pre-fix tree — **17 failed** (the missing
capability, by name), then green after implementation with the whole gateway/allowlist/banner/
wiring/air-gap/audit/contract sweep at **242 passed**.

*Teeth:* an 8-mutant sandboxed battery (same PYTHONPATH-shadow rig as ADR-0402; instruments
md5-identical) — **8/8 caught by the named test**: `header_dropped` · `header_always_sent` ·
`key_echoed_into_form` · `blank_clears_instead_of_keeps` · `key_written_to_txlog` ·
`repr_leaks_key` · `models_probe_unauthenticated` · `env_fallback_dropped`.

Full gate on the final tree: figures in the handoff's Gate-at-close section.

## Deliberately NOT done

- **No Bearer alternative headers** (Azure-style `api-key`, Negotiate/mTLS): Bearer is the
  OpenAI-compatible convention and by far the likeliest for this gateway class. If the operator's
  gateway still 401s *with* a key saved, the diagnostic names that state ("expired or not yet
  entitled") and a follow-on ADR adds the scheme the gateway actually documents — with evidence,
  not guesses.
- **No on-disk key persistence / keyring**: the in-memory-per-launch model is the consent design;
  the env var is the sanctioned convenience. A DPAPI/keyring store is future work if the operator
  asks.
- **No key-clear control**: quitting, `ai-off`, or wipe already forget it; a dedicated clear
  affordance wasn't worth the surface.
