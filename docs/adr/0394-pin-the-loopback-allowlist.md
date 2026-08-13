# ADR-0394 — Pin the loopback allowlist: the Law-1 guarantee was a data literal nothing asserted

Status: accepted (2026-08-13). Closes **DoD 001a**. Test-only — `src/` is untouched, v1.0.200 stands.

## Context

Every locality decision POLARIS makes funnels through two frozensets in `net_guard`:

```
net_guard.py:127   _LOOPBACK_HOSTNAMES = frozenset({"localhost", "ip6-localhost"})
net_guard.py:223       if candidate in _LOOPBACK_HOSTNAMES: return True      # is_loopback_host
net_guard.py:234   _LOCAL_HTTP_SCHEMES = frozenset({"http", "https"})
net_guard.py:237   is_local_http_endpoint()  ->  scheme check AND is_loopback_host
```

Through those two predicates runs every enforcement point in the product: `ai/ollama.py:130`,
`ai/openai_compat.py:39`, the settings endpoint validators at `web/app.py:6549` / `:6551` / `:6590`,
and the bind checks at `launcher.py:232` and `web/app.py:8161`. (The audit recorded these as
`6406/6408/6447` and `8018`; `app.py` has moved since, and the anchors above were re-derived here.
The `net_guard` anchors the audit cited were re-checked and still hold exactly.)

**Nothing pinned the contents of either set.** The existing guard suites
(`tests/guards/test_egress.py`, `tests/guards/test_endpoint_scheme.py`) pin *sampled negatives* —
`8.8.8.8`, `example.com`, `10.0.0.5`, `evil.com`, `169.254.1.1`. A sampled negative can never see a
*named* allowlist entry that was added beside it. Neither could they see a **narrowing**:
`ip6-localhost` was in the allowlist and in no test at all, so deleting it was equally invisible.

This is not hypothetical. Per `docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md`, the operator runs POLARIS
against a NASA-approved gateway (`https://proxy.fast.luna.nasa.gov`) on their own Windows machine,
and a separate assistant session made it work the only way the architecture allows — by adding that
hostname to the loopback allowlist in that local install. That edit silently re-labels a remote host
as "local" *everywhere in the codebase at once*, including in every on-screen sovereignty claim.

### The inherited premise was re-measured, not trusted (QC-2)

The audit reported 226 tests green under the widening, reproduced at 854. Those numbers are
testimony about a selection this session did not run, so the premise was re-derived. In a sandbox
copy of `src/` with `proxy.fast.luna.nasa.gov` added to `_LOOPBACK_HOSTNAMES` — verified in-process
to make `is_loopback_host("proxy.fast.luna.nasa.gov")` return `True` — the guard, AI, air-gap,
startup, launcher and exhibit-CLI suites ran **336 passed, 0 failed** with the new module
deselected. Different population, same conclusion: **the pre-existing suites are blind to it.**

## Decision

Add `tests/guards/test_loopback_allowlist.py`, which pins the guarantee in **two independent
layers**, because either alone is escapable:

1. **Data pins.** `_LOOPBACK_HOSTNAMES` and `_LOCAL_HTTP_SCHEMES` are asserted *exactly* equal to
   test-side literals, with failure messages that say what the constant governs and that changing it
   is an ADR-level decision. These catch widening and narrowing by name.
2. **Behavioural closure sweeps.** Over a hand-curated population of hosts that are, by
   construction, not this machine — the gateway and every parent domain of it, remote and
   private-range IPs, wildcard binds, a Cyrillic-`о` homograph, a decimal-packed `2130706433`, and
   generated confusables (`localhost.example.com`, `notlocalhost`, `localhost.nasa.gov`, `www.localhost`,
   …) — the sweeps assert *what is actually accepted*, in both directions, plus a scheme sweep that
   pins acceptance to exactly `{http, https}`.

The expected values are **written in the test file, never imported from `net_guard`**: an oracle
that reads the value it judges cannot refute anything (QC-1). The populations are likewise fixed and
hand-audited rather than derived from `is_loopback_host`, so the expected verdict for every
non-loopback member is the constant `False` — justified by construction, not by asking the
implementation what it thinks.

### Why both layers, empirically

The battery settled this rather than taste. Three mutations — `suffix_bypass` (a
`candidate.endswith(".nasa.gov")` short-circuit added *above* the frozenset check),
`substring_bypass` (equality softened to `any(n in candidate ...)`, which accepts
`localhost.evil.com`), and `always_true` — leave **both frozensets provably untouched**. The data
pins stayed green on all three; only the behavioural sweeps caught them. Conversely `widen_other`
was caught by the data pins with a precise, named diff. Neither layer subsumes the other.

## Verification (QC-1)

A mutation battery (9 mutations) runs pytest against a **sandbox copy** of `src/`, mutating only the
copy — the instrument is never touched. It carries two self-checks that make a meaningless result
impossible to report as a real one:

- a **sandbox canary** that aborts the whole battery unless a mutation to the copy actually changes
  the outcome (proving `PYTHONPATH` really shadows the editable install's `.pth`, rather than the
  battery quietly measuring the real tree); and
- a **control run** on the unmutated sandbox, which must be green, so every failure below is
  attributable to its mutation and not to the sandbox.

| # | Mutation | Caught | Failing tests |
|---|----------|--------|---------------|
| 1 | `widen_gateway` — the operator's exact edit | ✅ | 8 |
| 2 | `widen_other` — any other name added | ✅ | 2 |
| 3 | `narrow_drop_ip6` — an entry silently dropped | ✅ | 4 |
| 4 | `scheme_widen_ftp` — non-HTTP scheme allowed | ✅ | 2 |
| 5 | `suffix_bypass` — frozensets untouched | ✅ | 6 |
| 6 | `substring_bypass` — frozensets untouched | ✅ | 4 |
| 7 | `always_true` — guard disabled outright | ✅ | 6 |
| 8 | `drop_scheme_check` | ✅ | 1 |
| 9 | `drop_host_check` | ✅ | 2 |

**9/9 caught by name**, counted as distinct failing test *functions* (deduped across parametrized
cases). Control green; canary red; `src/schedule_forensics/net_guard.py` md5
`ff76e70c…` identical before and after the battery. Re-run in full against the final shipped file
after lint fixes, so the reported result corresponds to what actually lands.

**The battery's own reporter needed the same scepticism.** Its first pass counted `always_true` as
**4** failing tests; a direct re-count with a wide `COLUMNS` and `-rf --tb=no` showed **6**. The
battery ran pytest with a minimal environment, and at the default 80-column width the long assertion
messages wrapped in a way its `FAILED`-line parser mis-read. The *verdicts* were never affected —
those come from the process exit code, and every mutation was caught in every run — but the
published counts were re-derived with a verified command before they were written down. **An
instrument that summarizes a measurement is itself a measurement**, and this one was never shown to
be right about counts, only about pass/fail.

Red-before-green is satisfied by the battery itself: the module was **observed to fail** in the
state where its claim is false, which is the only state in which the pin means anything. Passing on
the pristine tree proves nothing on its own and is not offered as proof.

## Consequences

- The exact modification made on the operator's machine now fails CI **by name**, with a message
  pointing at `docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md` §6 and at building a named non-local
  backend instead of widening the loopback set.
- Law 2 is respected in the other direction: `test_every_loopback_host_is_still_accepted` means the
  pin cannot be satisfied by breaking the feature. `ip6-localhost` now has test coverage for the
  first time.
- **This does not make the on-screen sovereignty banner honest.** The banner remains
  config-derived (`ai/backend.py:99-108` → `web/chrome.py:175`) and still reads "Local-only — no
  data leaves this machine." for a routed-but-unreachable backend. That is DoD **001b**, deliberately
  not bundled here: 001a was specified to land alone so the security pin is reviewable in isolation.

## Finding recorded, not fixed here: `_ALLOWED_HOSTS` is the same defect, second surface

While tracing locality decisions that bypass `net_guard`, `web/app.py:1076` turned up:

```python
_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})
```

— the DNS-rebinding Host-header guard. **No test file names it.** Measured: with
`proxy.fast.luna.nasa.gov` added to it in a sandbox, `tests/web/test_sec_hardening.py` and
`tests/test_launcher.py` ran **23 passed, 0 failed**. Same class as the defect this ADR closes, a
different security property (request admission, not egress), and unpinned.

It is **not** fixed here, because DoD 001a says land alone and first, and because a Host-header pin
belongs with the web security suite rather than the egress guard. It is carried into the handoff as
the next cheap, high-value pin.

## Alternatives considered

- **Data pins only** — rejected on evidence: three mutations escape them (see above).
- **Behavioural sweeps only** — rejected: they cannot report *which literal* changed, and a
  narrowing that removes an untested name would be caught only if the population happened to
  include it. The exact-equality assertion is what makes the diff unmissable in review.
- **A `hypothesis` property test** — rejected: `hypothesis` is not a dependency of this repo, and a
  randomized population would make the guard's failure non-deterministic in CI. The curated
  population is reproducible and hand-auditable, which is what a testimony-context guard needs.
- **Asserting the frozensets from a hash of the source line** — rejected: it would break on
  reformatting and says nothing about behaviour.
