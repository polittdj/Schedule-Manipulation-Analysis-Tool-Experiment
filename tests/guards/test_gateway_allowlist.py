"""The approved-gateway allowlist is DATA — and unpinned data is not a guarantee (ADR-0402).

ADR-0394 pinned the loopback allowlist because a named entry added to it was invisible to
every sampled negative in CI. ADR-0402 then introduced the ONE sanctioned non-local
destination set — ``net_guard.APPROVED_GATEWAY_ENDPOINTS`` — and this module gives it the
same two-layer treatment from birth, because the same escape routes exist:

* **Data pins** assert the frozenset is *exactly* its expected literal, so widening it (a
  second gateway quietly added) and narrowing it (the approved endpoint dropped, silently
  disarming the feature) both fail by name.
* **Behavioural closure sweeps** assert what :func:`net_guard.is_approved_gateway_endpoint`
  — and through it the :class:`~schedule_forensics.ai.gateway.GatewayBackend` constructor —
  actually ACCEPTS, over a hand-curated population of confusables. These still fire when the
  predicate is bypassed rather than the data widened (a ``.endswith(".nasa.gov")``
  short-circuit leaves the literal provably untouched).

The expected values are test-side literals, deliberately NOT imported from ``net_guard``
(an oracle that reads the value it judges cannot refute anything — QC-1), and the
populations are fixed and hand-audited rather than derived from the predicate.

The loopback set's own pins live in ``test_loopback_allowlist.py`` and are untouched: the
gateway is a SEPARATE, disjoint taxonomy — the sweeps below prove the disjointness in both
directions (no gateway endpoint is ever local; no loopback endpoint is ever a gateway).
"""

from __future__ import annotations

import pytest

from schedule_forensics import net_guard
from schedule_forensics.ai.gateway import GatewayBackend
from schedule_forensics.net_guard import CUIEgressError

# --------------------------------------------------------------------------------------
# Expected values — test-side literals, NEVER imported from net_guard (QC-1).
# --------------------------------------------------------------------------------------

#: The complete approved-gateway set: the NASA-approved AI gateway (ADR-0402; recorded in
#: docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md §1). Growing this set is an ADR-level decision
#: — update this literal ONLY together with that ADR.
EXPECTED_GATEWAY_ENDPOINTS = frozenset({"https://proxy.fast.luna.nasa.gov"})

#: Exact strings the predicate must ACCEPT: the canonical form and its trailing-slash
#: variant (the only normalization the predicate performs is strip + rstrip("/")).
_ACCEPTED: tuple[str, ...] = (
    "https://proxy.fast.luna.nasa.gov",
    "https://proxy.fast.luna.nasa.gov/",
    "  https://proxy.fast.luna.nasa.gov  ",
)

#: Endpoint strings that must NEVER be accepted. Curated, not derived. Every member is one
#: deliberate mutation away from the approved endpoint — the shapes a well-meaning patch or
#: an attacker reaches for.
_REFUSED: tuple[str, ...] = (
    # -- scheme downgrades / swaps: controlled data never transits in cleartext ---------
    "http://proxy.fast.luna.nasa.gov",
    "ftp://proxy.fast.luna.nasa.gov",
    "ws://proxy.fast.luna.nasa.gov",
    # -- host confusables: sub/superdomains, prefixes, suffixes, lookalikes -------------
    "https://proxy.fast.luna.nasa.gov.evil.com",
    "https://evil.proxy.fast.luna.nasa.gov",
    "https://xproxy.fast.luna.nasa.gov",
    "https://proxy.fast.luna.nasa.gov2",
    "https://fast.luna.nasa.gov",
    "https://luna.nasa.gov",
    "https://nasa.gov",
    "https://proxy.slow.luna.nasa.gov",
    # -- authority tricks: userinfo, port, path, query, fragment ------------------------
    "https://proxy.fast.luna.nasa.gov@evil.com",
    "https://evil.com@proxy.fast.luna.nasa.gov",
    "https://proxy.fast.luna.nasa.gov:8443",
    "https://proxy.fast.luna.nasa.gov/v1",
    "https://proxy.fast.luna.nasa.gov/../evil",
    "https://proxy.fast.luna.nasa.gov?x=1",
    "https://proxy.fast.luna.nasa.gov#frag",
    # -- case variant: exact-match means exact; refusing is the fail-closed direction ---
    "https://PROXY.FAST.LUNA.NASA.GOV",
    # -- every loopback/local form: a "local gateway" is a category error ---------------
    "https://127.0.0.1:11434",
    "http://127.0.0.1:11434",
    "https://localhost",
    "https://[::1]:1234",
    # -- ordinary remote hosts (the old cloud field shapes) -----------------------------
    "https://api.openai.com",
    "https://api.example.com",
    "https://evil.com",
    # -- degenerate input ---------------------------------------------------------------
    "",
    "   ",
    "proxy.fast.luna.nasa.gov",  # bare host, no scheme
    "not-a-url",
)


# --------------------------------------------------------------------------------------
# 1. Data pins — exact contents, by name.
# --------------------------------------------------------------------------------------


def test_the_gateway_allowlist_is_exactly_the_expected_endpoints() -> None:
    """The allowlist is a security constant; its contents are pinned like one.

    An entry here is the ONE place the product may send schedule content off the machine.
    Adding an endpoint is an organizational-approval decision recorded by ADR (and it must
    also be consciously reflected in test_airgap.py's text-only exemption); removing the
    entry silently disarms the operator's approved-gateway feature. Neither may happen as
    incidental churn.
    """
    assert net_guard.APPROVED_GATEWAY_ENDPOINTS == EXPECTED_GATEWAY_ENDPOINTS, (
        "net_guard.APPROVED_GATEWAY_ENDPOINTS changed. This frozenset is the complete set "
        "of destinations the AI layer may ever transmit to (ADR-0402): every entry must be "
        "an exact https base URL your organization has approved for controlled schedule "
        "data. If this change is genuinely intended, write the ADR first, then update "
        "EXPECTED_GATEWAY_ENDPOINTS here and the text-only exemption in test_airgap.py."
    )


def test_the_gateway_allowlist_stays_small_enough_to_audit_by_eye() -> None:
    """A destination set nobody can read at a glance is a destination set nobody checks."""
    assert len(net_guard.APPROVED_GATEWAY_ENDPOINTS) == 1


def test_every_allowlisted_entry_is_a_bare_https_base_url() -> None:
    """Shape invariant over the DATA itself: https, no port, no path/query/fragment, no
    userinfo, no trailing slash — so the exact-match predicate can never be satisfied by a
    sloppier entry sneaking structure past the sweeps below."""
    from urllib.parse import urlparse

    for entry in net_guard.APPROVED_GATEWAY_ENDPOINTS:
        parsed = urlparse(entry)
        assert parsed.scheme == "https", entry
        assert parsed.hostname and parsed.port is None, entry
        assert parsed.path == "" and not parsed.query and not parsed.fragment, entry
        assert "@" not in parsed.netloc, entry
        assert not entry.endswith("/"), entry


# --------------------------------------------------------------------------------------
# 2. Behavioural closure — what is ACCEPTED, not merely what is stored.
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", _ACCEPTED)
def test_every_approved_form_is_accepted(endpoint: str) -> None:
    """The pin must not be satisfiable by breaking the feature (never weaken to pass)."""
    assert net_guard.is_approved_gateway_endpoint(endpoint) is True


@pytest.mark.parametrize("endpoint", _REFUSED)
def test_no_confusable_endpoint_is_accepted(endpoint: str) -> None:
    assert net_guard.is_approved_gateway_endpoint(endpoint) is False


def test_accepted_endpoints_are_exactly_the_expected_ones() -> None:
    """Closure over the whole population in one assertion, offenders named."""
    population = _ACCEPTED + _REFUSED
    accepted = {e for e in population if net_guard.is_approved_gateway_endpoint(e)}
    assert accepted == set(_ACCEPTED), (
        f"unexpectedly accepted as an approved gateway: {sorted(accepted - set(_ACCEPTED))!r}; "
        f"unexpectedly refused: {sorted(set(_ACCEPTED) - accepted)!r}"
    )


def test_the_backend_constructor_enforces_the_same_closure() -> None:
    """The guard composed into the object that actually transmits: every refused string
    must raise at construction (fail closed), every accepted one must construct."""
    for endpoint in _REFUSED:
        with pytest.raises(CUIEgressError):
            GatewayBackend(endpoint)
    for endpoint in _ACCEPTED:
        backend = GatewayBackend(endpoint)
        assert backend.endpoint == endpoint.strip().rstrip("/")


# --------------------------------------------------------------------------------------
# 3. Disjointness — the gateway taxonomy never intersects the local one.
# --------------------------------------------------------------------------------------


def test_no_gateway_endpoint_is_ever_local() -> None:
    """Both directions, over the DATA and over the constructed object: an approved gateway
    is remote by definition (`is_local` False — so ADR-0396's banner chain warns on every
    page and in every export), and no loopback endpoint can ever be a gateway."""
    for entry in net_guard.APPROVED_GATEWAY_ENDPOINTS:
        assert net_guard.is_local_http_endpoint(entry) is False
        assert net_guard.is_loopback_host(entry.removeprefix("https://")) is False
    for local in ("https://127.0.0.1:11434", "http://localhost:1234", "https://[::1]"):
        assert net_guard.is_approved_gateway_endpoint(local) is False


def test_gateway_locality_verdicts_are_instance_measurements_not_class_constants() -> None:
    """ADR-0396 discipline, applied to the new backend from birth: ``is_local`` and
    ``is_approved_gateway`` record validator verdicts on the ACTUAL endpoint at
    construction — a class constant is an assertion that survives any endpoint."""
    assert "is_local" not in vars(GatewayBackend)
    assert "is_approved_gateway" not in vars(GatewayBackend)
    backend = GatewayBackend("https://proxy.fast.luna.nasa.gov")
    assert backend.is_local is False and "is_local" in vars(backend)
    assert backend.is_approved_gateway is True and "is_approved_gateway" in vars(backend)
