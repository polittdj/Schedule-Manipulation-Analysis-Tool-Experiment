# Approved AI gateway — the situation, the guard gap, and what an honest integration requires

> **Status: RECORDED, NOT BUILT.** Nothing in this document is implemented in this repository.
> It exists because the operator now runs a NASA-approved AI gateway against POLARIS on their own
> machine, and the repo had **no record of that at all**. Written 2026-08-13 against `main` at
> `cacd769` (v1.0.198) from a reconciled seven-dimension audit; every claim below carries a
> file:line anchor and was re-verified by an adversarial pass.

## 1. What the operator did

NASA approved an AI gateway. POLARIS was pointed at it **on the operator's Windows machine**:

- `POLARIS_GATEWAY_ENDPOINT = https://proxy.fast.luna.nasa.gov`
- `POLARIS_GATEWAY_MODEL = claude-opus-4.8-thinking-itar`

A separate assistant session patched `ai/backend.py`, `web/app.py` and `web/settings.py` and added a
hostname allowlist entry **in that local install**. It works — the model catalog populates and
answers return from Opus 4.8.

**None of it is in this repository.** Verified: zero hits for `POLARIS_GATEWAY`, `luna.nasa.gov` or
`opus-4.8` across `src/`, `tests/`, `tools/`, `installer/`. The work is unversioned, untested,
outside CI, and lost with that machine.

**Do not read the absence of those tokens as evidence the gateway is not in use.** It is in use.
The repo simply does not know.

## 2. The guard gap — the single most important finding in the audit

The whole Law-1 locality guarantee funnels through one frozenset:

```
net_guard.py:127   _LOOPBACK_HOSTNAMES = frozenset({"localhost", "ip6-localhost"})
net_guard.py:223   if candidate in _LOOPBACK_HOSTNAMES: return True   # is_loopback_host
net_guard.py:237   is_local_http_endpoint()  -> scheme check + is_loopback_host
```

Every enforcement point depends on it: `ai/ollama.py:130`, `ai/openai_compat.py:39`,
`web/app.py:6549/6551/6590`, `launcher.py:232`, `web/app.py:8161`.
*(Anchor correction, ADR-0394: the `web/app.py` numbers were recorded against `cacd769` as
`6406/6408/6447` and `8018` and had drifted; re-derived above. The `net_guard.py` anchors in this
section were re-checked and still hold exactly.)*

**No test pins its contents.** An auditing agent executed the experiment in memory (no repo file
touched): widening `_LOOPBACK_HOSTNAMES` to include `proxy.fast.luna.nasa.gov` and running the
guard, AI, air-gap and startup suites gave **226 passed**; a second agent reproduced it across a
wider selection at **854 tests green**. The negative cases the suites do pin are only sampled
literals (`8.8.8.8`, `example.com`, `10.0.0.5`, `169.254.1.1`, `evil.com`, …) — a *named* allowlist
entry is invisible to all of them.

So the exact modification made on the operator's machine is **undetectable by this repo's CI, by
review, or by a future audit reading a green suite**. The guard's strength lives entirely in a data
literal that nothing pins.

## 3. The architecture channels a legitimate need into the most dangerous change

There is **no working approved-gateway path**. `route_backend()` accepts a `cloud_backend`
(`ai/backend.py:117`, used at `:134-140`) but **no production caller ever supplies it** —
`web/app.py:832-837` and `web/settings.py:346-351` pass only null/ollama/openai, and `ai/cloud.py`
does not exist. Yet the settings form still offers `<option value=cloud>Cloud (UNCLASSIFIED only)`
(`web/settings.py:449`). Selecting it falls closed to Null and no AI at all.

An operator with a genuine, approved remote-model requirement therefore has exactly one route that
works: **widen the loopback validator** — which silently re-labels a remote host as "local"
everywhere in the codebase at once, including in every sovereignty claim on screen.

That is a design defect, not operator error.

## 4. Why the banner then lies

**The sovereignty claim is enforced by an endpoint validator, not by observation.**

- `route_backend()` builds `local_banner` once (`ai/backend.py:129-131`) and returns it verbatim for
  **both** the `ollama` and `openai` paths (`:144-147`) with no classification check and no endpoint
  inspection.
- `banner_for()` (`:99-108`) is **config-derived** — it describes what was configured, never what
  resolved. `web/chrome.py:175` renders exactly that (`banner = banner_for(state.ai_config)`), so if
  the gateway is unreachable and routing correctly falls closed to Null, the page still announces
  the gateway. `route_backend`'s own Banner is effectively dead code.
- `AIBackend.is_local` is a hardcoded class constant (`ai/openai_compat.py:27-28`,
  `ai/ollama.py`), never computed from the endpoint, and `route_backend` never reads it. There is no
  runtime concept of "this backend is remote" anywhere in the object graph.

An executed probe confirmed the end state: with the allowlist widened and
`AIConfig(classification=CLASSIFIED, backend="openai", endpoint="https://proxy.fast.luna.nasa.gov")`,
`is_local_http_endpoint()` returns **True**, the backend constructs, and the banner reads
**"Local-only — no data leaves this machine."**

### The claims that become false

| # | File:line | String |
|---|---|---|
| 1 | `ai/backend.py:107` | `Local-only — no data leaves this machine.` (`banner_for`) |
| 2 | `ai/backend.py:130` | same literal (`route_backend`) |
| 3 | `web/chrome.py:97` | `…binds 127.0.0.1 only and no schedule content ever leaves this machine.` (CUI drawer) |
| 4 | `web/settings.py:434` | `…nothing ever leaves this machine.` |
| 5 | `web/app.py:1299` | `Load a schedule to begin — nothing you load ever leaves this machine.` |
| 6 | `web/app.py:1396` | `…a cited AI narrative — nothing leaves this computer.` |

Plus `web/i18n.py:887` (translated into es/fr/de/pt), and — flagged by the audit and worth its own
line — **two of these ship inside exported documents** (`ai/brief.py:625`, `web/sra.py:1076`), so an
exhibit that leaves the machine can carry a printed assurance that nothing left the machine.

`web/settings.py:328` already contains a truthful `Data LEAVES this machine.` string, built for the
cloud path that was never wired.

**Important scoping correction from the adversarial pass:** nothing in *this repo* falsifies those
sentences. The shipped build's validators still hold, so as shipped the claims are true. They are
false only of a **patched install** — which is precisely the operator's. The docs are not wrong
today; they are unconditional where they should be conditional, and they describe a guarantee whose
enforcement nothing pins.

## 5. The encouraging part: no new dependency is needed

`ai/openai_compat.py` transports over **std-lib `urllib`** (`_urllib_opener`, imported from
`ai/ollama.py`) and already speaks the OpenAI `/v1/chat/completions` wire format. An in-repo gateway
backend therefore needs **zero** third-party HTTP client — `litellm`, `openai`, `anthropic`, `boto3`
and friends stay banned (`net_guard.py:60-120`), the egress guard keeps passing, and the runtime
stays std-lib-only. This is a surgical change, not an architectural one.

It also means the loopback shim the demo currently relies on is strictly worse than a direct
backend: a shim is third-party software with a banned dependency tree, in no ATO, and — being on
loopback — **structurally unverifiable** by the tool. A direct, allowlisted gateway is verifiable.

## 6. What an honest integration requires

Sequenced so each step is provable before the next:

1. ~~**Pin the allowlist.**~~ **DONE — ADR-0394**, `tests/guards/test_loopback_allowlist.py`.
   Both frozensets are asserted exactly, against test-side literals never imported from the module
   under test, **plus** behavioural closure sweeps over a curated non-loopback population. Both
   layers were required on evidence: 3 of the 9 battery mutations (`suffix_bypass`,
   `substring_bypass`, `always_true`) bypass the allowlist while leaving both frozensets provably
   untouched, so the data pins alone stayed green on them. **9/9 mutations caught by name**, with a
   sandbox canary, a control run, and an md5 check that the instrument was never mutated. The §2
   premise was re-measured rather than inherited: **336 passed, 0 failed** under the widening.
2. **Make the banner OBSERVED.** Thread `route_backend`'s Banner through to the renderer; make
   `chrome.py:97` conditional on the same derivation. Prove it can go red by routing a non-local
   fake and asserting the page changes.
3. **Make `is_local` real.** Derive it from the validated endpoint; have `route_backend` refuse to
   return a local banner for any backend whose `is_local` is False.
4. **Decide the cloud option's fate (ADR).** Either delete the dead `cloud` option from the settings
   form, or build a first-class `ai/gateway.py` `GatewayBackend` with `is_local = False`, its **own**
   named allowlist constant (never a widening of the loopback set), its own config field, its own
   `route_backend` branch, a **mandatory** non-local banner, and a required classification gate.
5. **Add an AI transaction log** — what left, when, to which endpoint, under which classification.
   A CUI tool that sends anywhere needs a record; there is none today.
6. **Then** wire the gateway, and update the six strings + four translations + the three asserting
   test modules + the render oracle.

## 7. Standing risk to name out loud

The operator reported loading **real program IMS files** (`USA IPMR Format 6_November 2025 r1.mpp`,
`USA OTB Master IMS`) on the machine while the gateway was armed. Whatever the accreditation status
of `proxy.fast.luna.nasa.gov`, the tool's on-screen assurance at that moment stated the opposite of
what was happening. An allowlist entry typed into code is an **organizational assertion, not
evidence** — the tool cannot verify an ATO, and it must not imply that it has.

**A second unpinned security frozenset, found while closing 001a (ADR-0394).** `web/app.py:1076`
holds `_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})` — the
DNS-rebinding Host-header guard. **No test file names it.** Measured: with
`proxy.fast.luna.nasa.gov` added to it in a sandbox, `tests/web/test_sec_hardening.py` and
`tests/test_launcher.py` ran **23 passed, 0 failed**. Same defect class as §2, a different security
property (request admission rather than egress), still unpinned. Not fixed in ADR-0394 because 001a
was specified to land alone; it is the next cheap, high-value pin.

A related gap the audit surfaced independently: the pre-commit CUI guard has **no image detector**
(`.githooks/pre-commit:36` blocked_re lists no image extension; the content sniff at `:40` covers
only `.json`/`.txt`/extension-less), and **120 tracked PNGs** live under `00_REFERENCE_INTAKE/`.
Rendered screenshots of a real IMS would not be caught. That is a separate, real Law-1 hole.
