"""The local server's security policy — the Content-Security-Policy and hardening headers, the
DNS-rebinding Host allowlist (SEC-3) and the cross-site-request gate (SEC-2) — in a leaf module
that imports nothing but the standard library (ADR-0539).

Moved VERBATIM out of ``app.py``, which re-exports every name with the ``X as X`` idiom (pinned
by ``tests/web/test_monolith_split_contract.py``), so Polaris²'s middleware is unchanged. It lives
here so LODESTAR — the standalone One-Pager program, a std-lib server with no FastAPI — enforces
the SAME policy by importing the same objects rather than a copy that could drift: a second
server on 127.0.0.1 is a second CSRF and DNS-rebinding surface, and it gets no weaker rules.
"""

from __future__ import annotations

from urllib.parse import urlsplit

#: Content-Security-Policy that enforces the air-gap (Law 1) in EVERY browser at runtime, not
#: just in the test: ``default-src``/``connect-src``/``img-src`` are ``'self'`` so the page can
#: never pull or beacon to a remote host (no CDN, no font, no exfil fetch). ``script-src`` is
#: STRICT ``'self'`` (ADR-0268, closing the long-tracked follow-up): every former inline
#: handler is delegated in ``chrome.js`` via ``data-sf-*`` attributes, and every boot payload
#: is a non-executable ``<script type="application/json">`` block its consumer parses — so an
#: injected inline script or ``on*=`` handler cannot execute even if markup escaping ever
#: failed (defense in depth: the tool renders opposing-party file content). ``style-src`` keeps
#: ``'unsafe-inline'`` for the UI's legitimate inline ``style=`` (the Gantt's px widths) —
#: inline styles cannot execute code and remote styles stay forbidden.
_CSP = (
    "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
    "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'"
)
#: Security headers added to every response (CSP enforces the air-gap; nosniff/Referrer/Frame
#: are free hardening for the CUI threat model — the operator analyzes opposing-party files).
_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

#: SEC-3 (ADR-0264): the Host allowlist. The tool binds loopback only, but a DNS-rebinding
#: page (an attacker domain the victim's browser re-resolves to 127.0.0.1) reaches it with the
#: ATTACKER'S name in the Host header — on a production machine that is a read path to real
#: CUI. Only genuine loopback names are served. "testserver" is Starlette TestClient's default
#: base host: a single-label name public DNS cannot resolve, so admitting it adds no rebinding
#: surface (rebinding needs an attacker-controlled RESOLVABLE domain riding in Host).
_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})


def _host_allowed(host_header: str) -> bool:
    """True when the Host header names a loopback (or test) host — port ignored, IPv6 brackets
    handled. An absent/unparseable Host is rejected (HTTP/1.1 requires one)."""
    try:
        hostname = urlsplit("//" + host_header.strip()).hostname
    except ValueError:
        return False
    return hostname is not None and hostname in _ALLOWED_HOSTS


def _origin_allowed(origin_header: str | None) -> bool:
    """The FALLBACK CSRF check (used only when ``Sec-Fetch-Site`` is absent): True when the
    Origin is absent or loopback. An ABSENT Origin is a non-browser local client (curl,
    tests, the launcher's probes), not the CSRF vector, so it passes; a foreign or ``null``
    Origin is rejected."""
    if origin_header is None:
        return True
    try:
        parts = urlsplit(origin_header)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and parts.hostname in _ALLOWED_HOSTS


def _csrf_safe(sec_fetch_site: str | None, origin_header: str | None) -> bool:
    """SEC-2 (ADR-0264, corrected ADR-0268): is a state-mutating request non-cross-site?

    The PRIMARY signal is ``Sec-Fetch-Site`` — a browser-set forbidden header a cross-site
    page cannot forge, and (unlike ``Origin``) NOT nulled by the app's ``Referrer-Policy:
    no-referrer`` on same-origin **form** navigations. ``same-origin`` (the tool's own
    forms/fetches) and ``none`` (a user-initiated top-level navigation — address bar,
    bookmark; not a CSRF vector) pass; ``cross-site`` / ``same-site`` / ``cross-origin`` are
    the CSRF signatures and are refused. When the header is ABSENT (a non-browser client, or
    a browser too old to send Fetch Metadata) we fall back to the Origin check, which passes
    absent-Origin non-browser clients and loopback origins while refusing foreign ones.

    Why the correction: the Origin-only gate refused EVERY real-browser POST **form**
    navigation — ``no-referrer`` makes Chromium send ``Origin: null`` on those, which the old
    gate read as cross-site (surfaced by ADR-0268's browser verification; the ADR-0264 probe
    had only exercised ``fetch`` POSTs, which do carry a real Origin)."""
    if sec_fetch_site is not None:
        return sec_fetch_site in ("same-origin", "none")
    return _origin_allowed(origin_header)


#: methods that can change session state — the only ones SEC-2 gates (Sec-Fetch-Site/Origin
#: are not sent on same-origin GET navigations, so gating reads would break normal use)
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
