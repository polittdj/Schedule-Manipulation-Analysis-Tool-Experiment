"""Local-model endpoint scheme guard (Law 1, CUI).

Regression tests for the gap where the loopback guard validated only the *host*
of a model-server endpoint, never the *scheme* — so a ``file://localhost/...`` or
``ftp://localhost/...`` endpoint passed validation and the "loopback-only" stdlib
opener would read a local file (or speak FTP) through it. The ``# nosec B310``
suppression on the opener is justified by "never a remote/file/custom scheme", so
that guarantee must actually hold.
"""

from __future__ import annotations

import pytest

from schedule_forensics import net_guard
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend
from schedule_forensics.net_guard import CUIEgressError


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:11434",
        "http://localhost:1234",
        "https://127.0.0.1:8443",
        "https://localhost/v1",
        "http://[::1]:11434",
    ],
)
def test_local_http_endpoints_allowed(endpoint: str) -> None:
    assert net_guard.is_local_http_endpoint(endpoint) is True


@pytest.mark.parametrize(
    "endpoint",
    [
        # loopback host but a scheme that does not reach a local HTTP model server
        "file://localhost/etc/passwd",
        "file:///etc/passwd",
        "ftp://localhost/secret",
        "gopher://localhost/",
        "data:text/plain;base64,AAAA",
        # right scheme, wrong (remote) host
        "http://evil.com",
        "https://api.example.com/v1",
        "http://10.0.0.5:11434",
        # garbage / empty
        "",
        "not-a-url",
    ],
)
def test_non_local_http_endpoints_rejected(endpoint: str) -> None:
    assert net_guard.is_local_http_endpoint(endpoint) is False


@pytest.mark.parametrize(
    "endpoint",
    ["file://localhost/etc/passwd", "ftp://localhost/x", "gopher://localhost/"],
)
def test_ollama_rejects_non_http_loopback_scheme(endpoint: str) -> None:
    with pytest.raises(CUIEgressError):
        OllamaBackend(endpoint=endpoint)


@pytest.mark.parametrize(
    "endpoint",
    ["file://localhost/etc/passwd", "ftp://localhost/x", "gopher://localhost/"],
)
def test_openai_compat_rejects_non_http_loopback_scheme(endpoint: str) -> None:
    with pytest.raises(CUIEgressError):
        OpenAICompatBackend(endpoint=endpoint)


def test_default_opener_refuses_redirects() -> None:
    """The stdlib opener must not FOLLOW a redirect — a loopback endpoint must not be
    able to bounce a CUI request (and its POST body) onward to a remote host."""
    from schedule_forensics.ai import ollama

    handler = ollama._NoRedirect()
    # redirect_request returning None == "do not follow"; urllib then raises on the 3xx.
    result = handler.redirect_request(
        req=None, fp=None, code=302, msg="Found", headers={}, newurl="http://evil.com/"
    )
    assert result is None
