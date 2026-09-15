"""The server's OWN reason for an HTTP refusal reaches the diagnostics, bounded (OR-16).

Field report 2026-09-12: the approved gateway answered the availability probe with HTTP 401
while a key was saved; the settings banner said "server returned HTTP 401" and nothing else,
and the operator had to reproduce the request in PowerShell to learn anything more. The
response carried the reason all along — RFC 6750 puts it in the ``WWW-Authenticate``
challenge, OpenAI-style servers in ``error.message`` — and the tool threw it away.

Red first: this module cannot import on the pristine tree (``ai.refusal`` does not exist), and
``probe_error_text`` there returns the bare status for a body that names the reason.
"""

from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

from schedule_forensics.ai.completion import limit_rejected
from schedule_forensics.ai.ollama import is_auth_refusal, probe_error_text
from schedule_forensics.ai.refusal import MAX_REASON_CHARS, http_error_body, http_refusal_detail

URL = "https://proxy.fast.luna.nasa.gov/v1/models"


def _err(
    code: int, body: bytes = b"", headers: dict[str, str] | None = None
) -> urllib.error.HTTPError:
    msg = Message()
    for name, value in (headers or {}).items():
        msg[name] = value
    return urllib.error.HTTPError(URL, code, "refused", msg, io.BytesIO(body))


def test_an_openai_style_error_message_is_the_reason() -> None:
    body = json.dumps({"error": {"message": "Invalid API key provided", "type": "auth"}}).encode()
    assert http_refusal_detail(_err(401, body)) == "Invalid API key provided"


def test_bare_error_message_and_detail_strings_are_reasons() -> None:
    assert http_refusal_detail(_err(401, b'{"error": "invalid_token"}')) == "invalid_token"
    assert http_refusal_detail(_err(403, b'{"message": "Not entitled"}')) == "Not entitled"
    assert http_refusal_detail(_err(401, b'{"detail": "Not authenticated"}')) == "Not authenticated"


def test_the_www_authenticate_challenge_wins_over_the_body() -> None:
    hdr = {
        "WWW-Authenticate": (
            'Bearer realm="hub", error="invalid_token", '
            'error_description="The access token expired"'
        )
    }
    assert (
        http_refusal_detail(_err(401, b'{"error": "ignored"}', hdr)) == "The access token expired"
    )
    # a challenge with only the error code names that code
    assert (
        http_refusal_detail(_err(401, b"", {"WWW-Authenticate": 'Bearer error="invalid_token"'}))
        == "invalid_token"
    )


def test_markup_bodies_name_nothing_an_operator_can_act_on() -> None:
    html = b"<html><head><title>401 Authorization Required</title></head><body>nginx</body></html>"
    assert http_refusal_detail(_err(401, html)) == ""


def test_a_plain_text_body_gives_its_first_line() -> None:
    assert http_refusal_detail(
        _err(403, b"Forbidden: key not entitled to this model\nsecond line")
    ) == ("Forbidden: key not entitled to this model")


def test_the_reason_is_bounded_to_one_line() -> None:
    body = json.dumps({"error": {"message": "x" * 5000 + "\n" + "y" * 5000}}).encode()
    reason = http_refusal_detail(_err(401, body))
    assert len(reason) <= MAX_REASON_CHARS and "\n" not in reason and reason.endswith("…")


def test_an_unreadable_or_absent_body_is_no_reason_and_never_raises() -> None:
    bodiless = urllib.error.HTTPError(URL, 503, "busy", Message(), None)  # type: ignore[arg-type]
    assert http_refusal_detail(bodiless) == ""
    assert http_error_body(bodiless) == b""
    assert http_refusal_detail(ValueError("not http")) == ""
    assert http_refusal_detail(_err(401, b"{not json")) == ""


def test_probe_text_carries_the_reason_and_stays_a_refusal() -> None:
    text = probe_error_text(_err(401, b'{"error": {"message": "invalid api key"}}'))
    assert text == 'server returned HTTP 401 (its reason: "invalid api key")'
    assert is_auth_refusal(text)
    # no reason -> the text every existing pin expects, byte for byte
    assert probe_error_text(_err(503)) == "server returned HTTP 503"


def test_the_body_is_read_once_and_shared_by_every_reader() -> None:
    """``HTTPError.read()`` consumes the response. ``limit_rejected`` (a 400 naming the
    answer budget) and the diagnostics both need the bytes, in either order."""
    body = b'{"error": {"message": "max_tokens is too large for this model"}}'
    first = _err(400, body)
    assert limit_rejected(first) and "max_tokens is too large" in probe_error_text(first)
    second = _err(400, body)
    assert "max_tokens is too large" in probe_error_text(second) and limit_rejected(second)
    assert http_error_body(second) == body


def test_a_challenge_without_error_fields_names_its_scheme_last() -> None:
    """OR-17 (ADR-0493): a 401 whose challenge carries no error field and whose body says
    nothing still names the SCHEME the server wants — the one fact that decides whether
    ``Authorization: Bearer`` is the right shape. It is the LAST resort: error fields and a
    body reason still win; a blank challenge is no reason."""
    assert (
        http_refusal_detail(_err(401, b"", {"WWW-Authenticate": 'Basic realm="luna"'}))
        == 'challenge: Basic realm="luna"'
    )
    assert (
        http_refusal_detail(_err(401, b"<html>401</html>", {"WWW-Authenticate": "Bearer"}))
        == "challenge: Bearer"
    )
    # the body's reason still outranks a bare challenge
    assert (
        http_refusal_detail(
            _err(401, b'{"detail": "Not authenticated"}', {"WWW-Authenticate": "Bearer"})
        )
        == "Not authenticated"
    )
    assert http_refusal_detail(_err(401, b"", {"WWW-Authenticate": "   "})) == ""
    text = probe_error_text(_err(401, b"", {"WWW-Authenticate": 'Bearer realm="luna"'}))
    assert text == 'server returned HTTP 401 (its reason: "challenge: Bearer realm="luna"")'
    assert is_auth_refusal(text)


# --- an EXPIRED credential, in the gateway's own words (OR-19, ADR-0496) -----------------------


def test_an_expired_key_verdict_is_parsed_with_its_expiry_and_the_gateways_clock() -> None:
    """The 2026-09-15 v1.0.262 screenshot, verbatim: the approved gateway's reason names the
    key's expiry and its own clock; the banner needs both — the date to state, the delta to say
    how stale the paste is."""
    import datetime as dt

    from schedule_forensics.ai.refusal import expired_key_details

    reason = (
        'server returned HTTP 401 (its reason: "Authentication Error - Expired Key. Key Expiry '
        "time 2026-09-12 20:36:47.844000+00:00 and current time 2026-09-15 "
        '17:05:33.767685+00:00")'
    )
    found = expired_key_details(reason)
    assert found is not None
    assert found.expiry == dt.datetime(2026, 9, 12, 20, 36, 47, 844000, tzinfo=dt.UTC)
    assert found.current == dt.datetime(2026, 9, 15, 17, 5, 33, 767685, tzinfo=dt.UTC)
    assert found.expiry_text == "2026-09-12 20:36 UTC"
    assert found.expired_for == "2 days 20 hours"


def test_an_expiry_without_timestamps_is_still_an_expiry_and_a_plain_refusal_is_not() -> None:
    from schedule_forensics.ai.refusal import expired_key_details

    found = expired_key_details('server returned HTTP 401 (its reason: "The access token expired")')
    assert found is not None and found.expiry is None and found.current is None
    assert found.expiry_text == "" and found.expired_for == ""
    assert expired_key_details('server returned HTTP 401 (its reason: "Invalid API key")') is None
    assert expired_key_details("server returned HTTP 401") is None
    # a clock that runs BEHIND the expiry (skew) names the date but claims no elapsed time
    skewed = expired_key_details(
        "Expired Key. Key Expiry time 2026-09-15T18:00:00Z and current time 2026-09-15T17:00:00Z"
    )
    assert skewed is not None and skewed.expiry_text == "2026-09-15 18:00 UTC"
    assert skewed.expired_for == ""
