"""LODESTAR's local web server — the standard library's ``http.server``, nothing else (ADR-0539).

LODESTAR is the One-Pager Timeline and the One-Pager Compare as a program of their own, shared as
ONE file that needs nothing but Python. So it cannot use Polaris²'s FastAPI stack: this module
is the whole server, and it is a thin adapter — every route calls the SAME action
(:mod:`schedule_forensics.web.onepager_actions`) and renders the SAME page body Polaris² does.

Security is Polaris²'s policy, imported rather than copied (:mod:`schedule_forensics.web.security`),
plus what a standard-library server needs on top — each item measured by ADR-0539's red team:

* **HTTP/1.0 framing, and every refusal closes the connection.** On HTTP/1.1 keep-alive a
  refused request whose body was never read left that body on the socket, where it was parsed as
  the NEXT request — past the Host and CSRF gates. A ``Transfer-Encoding`` (chunked) body is
  refused outright: this server never de-chunks.
* **Size before bytes.** A POST's ``Content-Length`` is checked against the cap BEFORE anything
  is read (``rfile.read(n)`` allocates ``n`` up front), then the body is read in chunks, against
  a deadline for the WHOLE body — and read and parsed BEFORE the state lock is taken, so a client
  that stalls or trickles its body holds up only itself. An upload's cap is the FILE cap plus
  the multipart framing around the file, so a list just over the file cap reaches the route and
  is refused by name on its page; a body past even that is refused unread, with the page's frame
  (the credit and the marking), never a bare document (ADR-0539's review, UILD-4).
* **A multipart upload is pre-scanned** — a few parts, each with short headers, none that is
  itself split into parts (``multipart/*`` or ``message/*``, as the email parser reads the part's
  own headers) — or it is refused before the email parser sees it: its cost grows faster than
  the body on exactly those shapes. The boundary is ONE plain RFC 2046 parameter, and the parser
  is handed that boundary in a header rebuilt from it, never the client's header, which it would
  read its own way (review SLA-1: a duplicated, quoted or commented boundary split differently).
* **Host is exactly this server** — ``127.0.0.1:<port>`` or ``localhost:<port>`` — a stricter
  form of the SEC-3 DNS-rebinding allowlist; **SEC-2's cross-site gate** on every POST.
* **Static files come from a fixed allowlist loaded at start**, never from a path joined onto a
  request (a filesystem package would serve ``../`` from a joined path).
* **Nothing about a request is logged** — not its path, not its file name (the CUI log rule):
  ``log_message`` / ``log_error`` / ``handle_error`` are silenced, and an unexpected error is a
  generic 500 page. With no console at all (``pythonw``) the server still answers.
* **CSP, nosniff, no-referrer and frame-deny on every response**, including every refusal — the
  standard library's own error pages too (an unknown method, a malformed request line, one
  refused before its version was read: the handler's default version is HTTP/1.0, not the
  standard library's HTTP/0.9, which writes no status line and no header) — and
  ``Cache-Control: no-store`` on every page and export.
* **The cross-site gate is exact.** Without ``Sec-Fetch-Site`` an ``Origin`` must be THIS server
  (``127.0.0.1:<port>`` / ``localhost:<port>``), not any loopback port.
* **No socket code here** — the listening socket is the standard server's own — so the Law-1
  transport census (``tests/ai/test_txlog_law1.py``) sees no new network site.
"""

from __future__ import annotations

import datetime as dt
import email.parser
import email.policy
import http.server
import json
import re
import socketserver
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from importlib.resources import files
from typing import Any
from urllib.parse import parse_qs, urlsplit

from schedule_forensics.reports.onepager import OnePagerDoc, layout_json, parse_date
from schedule_forensics.reports.onepager_compare import compare_layout_json
from schedule_forensics.reports.onepager_links import Link
from schedule_forensics.reports.tableset import TableSet
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.web import lodestar_actions as studio_actions
from schedule_forensics.web import onepager_actions as actions
from schedule_forensics.web.lodestar_history import History
from schedule_forensics.web.lodestar_launch import lodestar_launch_html
from schedule_forensics.web.lodestar_shell import NAME, lodestar_page, marking, stopped_page
from schedule_forensics.web.lodestar_studio import PAGES, studio_page, studio_state
from schedule_forensics.web.onepager import onepager_layout, onepager_template
from schedule_forensics.web.onepager_compare import onepager_compare_layout
from schedule_forensics.web.security import _SECURITY_HEADERS, _csrf_safe

#: An upload is a One-Pager list — a small workbook. Twenty megabytes is far past any list; the
#: email parser holds about 13x a real upload (a file and two fields) in memory, and a body of
#: many small parts — which costs it far more — is refused before it is parsed (``_prescan``;
#: ADR-0539 and its review, measured).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
#: The multipart framing around the file in an upload's BODY — the delimiters, each part's short
#: header block, the page's one or two small fields (Chromium's, measured through each page's own
#: form with a 205-character file name: 531 and 627 bytes). The body cap carries it, so a file just
#: over :data:`MAX_UPLOAD_BYTES` reaches the route and is refused BY NAME on its page
#: (``read_list``), not by a raw 413 (review UILD-4).
MULTIPART_FRAMING_BYTES = 64 * 1024
#: The upload routes' cap on the whole body — checked, like every cap, before a byte is read.
UPLOAD_BODY_CAP = MAX_UPLOAD_BYTES + MULTIPART_FRAMING_BYTES
#: Every other POST is a small form (a title, two dates, a link's two keys).
MAX_FORM_BYTES = 64 * 1024
#: A connection that sends nothing for this long is dropped...
TIMEOUT_S = 30
#: ...and a request body that has not arrived IN FULL by then is refused (a trickle of one byte
#: every few seconds would otherwise hold its thread for as long as it liked).
BODY_DEADLINE_S = 60
#: An upload form carries a file and at most two fields; a few more parts are tolerated, and each
#: part's header block is short — anything past these is refused before it is parsed.
MAX_PARTS = 8
MAX_PART_HEADER_BYTES = 8 * 1024
#: RFC 2046's boundary: one to seventy of its ``bchars``, the last one not a space.
_BOUNDARY = re.compile(r"[0-9A-Za-z'()+_,\-./:=? ]{0,69}[0-9A-Za-z'()+_,\-./:=?]")
#: A ``boundary`` parameter as any MIME reader may take one — after ``;``, ``,`` or white space, in
#: any case, RFC 2231's ``boundary*`` / ``boundary*0`` forms included — so no second one hides.
_BOUNDARY_PARAM = re.compile(r"(?i)(?:^|[;,\s])boundary(\*\d*\*?)?\s*=\s*")
#: The rest of a delimiter's own line (RFC 2046's padding, then the line end — the email parser
#: also takes a bare CR or LF): the part's headers start after it.
_DELIMITER_LINE = re.compile(rb"[ \t]*(?:\r\n|\r|\n)")
#: The upload routes and the page each belongs to: ``route -> (page, its tab's name)``.
_UPLOAD_PAGES: dict[str, tuple[str, str]] = {
    "/onepager/upload": ("/onepager", "Timeline"),
    "/onepager-compare/upload": ("/onepager-compare", "Compare"),
}

#: The ONLY static files LODESTAR serves (ADR-0543, LODESTAR 2.0 — none of Polaris²'s): the view
#: switch (pre-paint), the A1 design tokens and the studio's styles, the slide's painter, the
#: studio's controller, the launch page's script and styles, the vendored fonts and their licence,
#: and the icon. Loaded once, at start, from the package (inside the .pyz or on disk alike); a name
#: is looked up EXACTLY — never joined onto a path — and anything else under /static/ is a 404.
STATIC_ASSETS: dict[str, str] = {
    "lodestar_view.js": "text/javascript; charset=utf-8",
    "lodestar_slide.js": "text/javascript; charset=utf-8",
    "lodestar_studio.js": "text/javascript; charset=utf-8",
    "lodestar_launch.js": "text/javascript; charset=utf-8",
    "lodestar_tokens.css": "text/css; charset=utf-8",
    "lodestar_studio.css": "text/css; charset=utf-8",
    "lodestar_launch.css": "text/css; charset=utf-8",
    "lodestar.ico": "image/x-icon",
    "fonts/LICENSE-fonts.txt": "text/plain; charset=utf-8",
    "fonts/space-grotesk-latin-500-normal.woff2": "font/woff2",
    "fonts/space-grotesk-latin-600-normal.woff2": "font/woff2",
    "fonts/space-grotesk-latin-700-normal.woff2": "font/woff2",
    "fonts/ibm-plex-sans-latin-400-normal.woff2": "font/woff2",
    "fonts/ibm-plex-sans-latin-500-normal.woff2": "font/woff2",
    "fonts/ibm-plex-sans-latin-600-normal.woff2": "font/woff2",
    "fonts/ibm-plex-sans-latin-700-normal.woff2": "font/woff2",
    "fonts/ibm-plex-mono-latin-400-normal.woff2": "font/woff2",
    "fonts/ibm-plex-mono-latin-500-normal.woff2": "font/woff2",
    "fonts/ibm-plex-mono-latin-600-normal.woff2": "font/woff2",
    "fonts/ibm-plex-mono-latin-700-normal.woff2": "font/woff2",
}
#: The ⤓ EXCEL exports (the list, the comparison, the template). No Word export: no LODESTAR page
#: offers one, and a document titled by Polaris²'s table sets would say POLARIS² (ADR-0539).
_EXPORT_MEDIA: dict[str, tuple[str, Callable[[TableSet], bytes]]] = {
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", render_xlsx),
}
_HTML = "text/html; charset=utf-8"
_JSON = "application/json; charset=utf-8"
#: The v1 form routes and the studio action each one is: ``path -> (action, page)``.
_FORM_ROUTES: dict[str, tuple[str, str]] = {
    "/onepager/title": ("title", "timeline"),
    "/onepager/window": ("window", "timeline"),
    "/onepager/today": ("today", "timeline"),
    "/onepager/clear": ("clear", "timeline"),
    "/onepager/links": ("links", "timeline"),
    "/onepager/example": ("example", "timeline"),
    "/onepager-compare/title": ("title", "compare"),
    "/onepager-compare/window": ("window", "compare"),
    "/onepager-compare/today": ("today", "compare"),
    "/onepager-compare/clear": ("clear", "compare"),
    "/onepager-compare/links": ("links", "compare"),
    "/onepager-compare/swap": ("swap", "compare"),
    "/onepager-compare/example": ("example", "compare"),
}
#: Where a form route lands after its redirect (the links block, as v1 did, for a link change).
_LANDING = {"links": "#lsLinks"}


def load_assets() -> dict[str, tuple[bytes, str]]:
    """Every allowlisted static file's bytes and type — read once, from the package."""
    static = files("schedule_forensics.web").joinpath("static")
    out: dict[str, tuple[bytes, str]] = {}
    for name, ct in STATIC_ASSETS.items():
        node = static
        for part in name.split("/"):  # a sub-path one segment at a time: any Traversable takes it
            node = node.joinpath(part)
        out[name] = (node.read_bytes(), ct)
    return out


@dataclass
class LodestarState:
    """Everything LODESTAR holds, in memory only: the two pages' lists, titles, windows, links and
    one-shot messages (the :class:`~schedule_forensics.web.onepager_common.OnePagerSession`
    protocol — the same attributes Polaris²'s session carries), the marking choice, and the
    session log every committed change is undone and redone from (ADR-0543)."""

    onepager: OnePagerDoc | None = None
    onepager_title: str = ""
    onepager_msg: str | None = None
    onepager_is_error: bool = False
    onepager_today: dt.date | None = None
    onepager_window: tuple[dt.date, dt.date] | None = None
    onepager_prior: OnePagerDoc | None = None
    onepager_current: OnePagerDoc | None = None
    onepager_compare_title: str = ""
    onepager_compare_msg: str | None = None
    onepager_compare_is_error: bool = False
    onepager_compare_window: tuple[dt.date, dt.date] | None = None
    onepager_links: tuple[Link, ...] = ()
    onepager_compare_links: tuple[Link, ...] = ()
    onepager_links_msg: str | None = None
    onepager_links_is_error: bool = False
    onepager_compare_links_msg: str | None = None
    onepager_compare_links_is_error: bool = False
    onepager_cache: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    unclassified: bool = False
    #: the session log — undo and redo for every committed change (ADR-0543)
    history: History = field(default_factory=History, repr=False)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


class _Refused(Exception):
    """A request refused before any route logic ran: its status and its one-line reason."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class _Reply:
    status: int
    body: bytes
    content_type: str
    headers: tuple[tuple[str, str], ...] = ()


def _redirect(location: str) -> _Reply:
    return _Reply(303, b"", _HTML, (("Location", location),))


def _json_error(message: str, status: int = 422) -> _Reply:
    text = message.replace("\\", "\\\\").replace('"', '\\"')
    return _Reply(status, f'{{"error": "{text}"}}'.encode(), "application/json")


def _html(page: str) -> _Reply:
    return _Reply(200, page.encode("utf-8"), _HTML)


def _safe_header(value: str) -> str:
    """A header value that can be sent: no CR or LF (no header injection) and Latin-1 only."""
    if "\r" in value or "\n" in value:
        raise ValueError("header value carries a line break")
    value.encode("latin-1")
    return value


class LodestarServer(http.server.ThreadingHTTPServer):
    """The standard threading server, bound to 127.0.0.1 only, with the host-name lookup
    ``HTTPServer.server_bind`` performs (``getfqdn``) skipped and every error kept off the
    console."""

    daemon_threads = True

    def __init__(self, port: int, state: LodestarState, today: dt.date | None = None) -> None:
        self.state = state
        self.today = today
        self.assets = load_assets()
        super().__init__(("127.0.0.1", port), _Handler)

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)

    def handle_error(self, request: object, client_address: object) -> None:
        """Say nothing: a traceback could carry a file name or a task name (the CUI log rule)."""

    @property
    def origin_hosts(self) -> frozenset[str]:
        return frozenset({f"127.0.0.1:{self.server_port}", f"localhost:{self.server_port}"})


class _Handler(http.server.BaseHTTPRequestHandler):
    """One request. HTTP/1.0 on purpose (see the module docstring) — never raise it."""

    protocol_version = "HTTP/1.0"
    #: What a request line refused BEFORE its version is read is answered as (a malformed line,
    #: ``HTTP/2.0``, an HTTP/0.9 ``GET /x``): the standard library's ``HTTP/0.9`` writes neither a
    #: status line nor a header — so no CSP, nosniff or frame-deny (review SLA-3).
    default_request_version = "HTTP/1.0"
    timeout = TIMEOUT_S
    server: LodestarServer
    server_version = NAME
    sys_version = ""
    #: the header names this response has sent so far, and whether it is Quit's
    _sent: set[str]
    _quit: bool = False

    # ── silence: nothing about a request reaches a console or a log ──
    def log_message(self, format: str, *args: object) -> None:
        return

    def log_error(self, format: str, *args: object) -> None:
        return

    # ── the security headers on EVERY response — the standard library's own error pages too
    # (an unknown method, a malformed request line, a too-long URI): whatever sends the headers,
    # what it did not send itself is added before the headers end ──
    def send_response(self, code: int, message: str | None = None) -> None:
        self._sent = set()
        super().send_response(code, message)

    def send_header(self, keyword: str, value: str) -> None:
        sent: set[str] = getattr(self, "_sent", set())
        sent.add(keyword.lower())
        super().send_header(keyword, value)

    def end_headers(self) -> None:
        sent: set[str] = getattr(self, "_sent", set())
        for key, value in {**_SECURITY_HEADERS, "Cache-Control": "no-store"}.items():
            if key.lower() not in sent:
                super().send_header(key, value)
        super().end_headers()

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_OPTIONS(self) -> None:
        self._dispatch("OPTIONS")

    # ── the one dispatcher: gates in a fixed order, then the route, then the reply ──
    def _dispatch(self, method: str) -> None:
        self._quit = False
        try:
            self._gate(method)
            reply = self._route(method)
        except _Refused as refused:
            self.close_connection = True
            reply = self._refusal(refused)
        except Exception:
            self.close_connection = True
            reply = _Reply(500, b"LODESTAR hit an unexpected error.", "text/plain; charset=utf-8")
        self._send(reply, head_only=method == "HEAD")
        if self._quit:
            # only now, with the "stopped" page written and flushed, does the server stop
            self.close_connection = True
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _refusal(self, refused: _Refused) -> _Reply:
        """A refusal's reply: its reason as JSON — except a body too large on an upload route. A
        person meets that one by choosing too big a file in the page's own form, so it is that
        page's FRAME (the credit, the CURRENT marking top and bottom) with the cap named and a
        way back, still 413 and still unread (review UILD-4)."""
        page = _UPLOAD_PAGES.get(urlsplit(self.path).path)
        if refused.status == 413 and page is not None and self._wants_json():
            # the studio posted the file with fetch: it shows the page's own sentence
            cap = MAX_UPLOAD_BYTES // (1024 * 1024)
            return _json_error(f"List not loaded — the upload is over the {cap} MB cap.", 413)
        if refused.status != 413 or page is None:
            return _json_error(refused.reason, refused.status)
        back, name = page
        body = (
            '<div class="notice warn" role=alert>List not loaded — the upload is over the '
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB cap.</div>"
            f'<p><a href="{back}">Back to the {name}</a></p>'
        )
        unclassified = self.server.state.unclassified
        page_html = lodestar_page(name, body, path=back, unclassified=unclassified)
        return _Reply(413, page_html.encode("utf-8"), _HTML)

    def _gate(self, method: str) -> None:
        host = self.headers.get("Host", "").strip().lower()
        if host not in self.server.origin_hosts:
            raise _Refused(400, "invalid host header")
        if method not in ("GET", "HEAD", "POST"):
            raise _Refused(405, "method not allowed")
        if "Transfer-Encoding" in self.headers:
            raise _Refused(400, "chunked request bodies are not accepted")
        if method == "POST":
            fetch_site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin")
            if not (
                _csrf_safe(fetch_site, origin)
                and _same_origin(fetch_site, origin, self.server.origin_hosts)
            ):
                raise _Refused(403, "cross-site request refused")

    def _body(self, cap: int) -> bytes:
        raw = self.headers.get("Content-Length")
        if raw is None or not raw.strip().isdecimal():
            raise _Refused(411, "a POST needs a Content-Length")
        size = int(raw)
        if size > cap:
            limit = f"{cap // (1024 * 1024)} MB" if cap >= 1024 * 1024 else f"{cap // 1024} KB"
            raise _Refused(413, f"request too large (over {limit})")
        chunks: list[bytes] = []
        left = size
        deadline = time.monotonic() + BODY_DEADLINE_S
        while left > 0:
            chunk = self.rfile.read1(min(left, 65536))
            if not chunk:
                raise _Refused(400, "the request body ended early")
            if time.monotonic() > deadline:
                raise _Refused(408, "the request body took too long to arrive")
            chunks.append(chunk)
            left -= len(chunk)
        return b"".join(chunks)

    def _form(self) -> dict[str, str]:
        body = self._body(MAX_FORM_BYTES).decode("utf-8", "replace")
        return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}

    def _upload(self) -> tuple[dict[str, str], str | None, bytes]:
        """``(fields, file name, file bytes)`` of a multipart form — parsed by the standard
        library's email parser (round-trip-exact on binary workbooks, ADR-0539 measured)."""
        ctype = self.headers.get("Content-Type", "")
        if not ctype.lower().startswith("multipart/form-data"):
            raise _Refused(400, "an upload must be multipart/form-data")
        body = self._body(UPLOAD_BODY_CAP)
        boundary = _prescan(ctype, body)
        # the parser splits on the boundary the prescan split on — never the client's header
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            _multipart_head(boundary) + body
        )
        if not msg.is_multipart():
            raise _Refused(400, "the upload carried no parts")
        fields: dict[str, str] = {}
        name: str | None = None
        data: bytes | None = None
        for part in msg.iter_parts():
            key = part.get_param("name", header="content-disposition")
            if not isinstance(key, str):
                continue
            payload = part.get_payload(decode=True)
            content = payload if isinstance(payload, bytes) else b""
            if key == "file" and data is None:
                name, data = part.get_filename(), content
            elif key != "file":
                fields[key] = content.decode("utf-8", "replace")
        if data is None:
            raise _Refused(400, "the upload carried no file")
        return fields, name, data

    def _dates(self) -> tuple[dt.date, dt.date]:
        """``(data date, prepared)`` as Polaris²'s routes derive them (ADR-0541): the data date
        is the operator's when set, else the clock; ``prepared`` is the clock — the server's
        fixed one when a test gave it one, else the computer's date."""
        st = self.server.state
        clock = self.server.today or dt.date.today()
        return st.onepager_today or clock, clock

    def _route(self, method: str) -> _Reply:
        path = urlsplit(self.path).path
        st = self.server.state
        if method == "POST":
            # the body is read and parsed BEFORE the lock: a slow client holds up only itself
            upload = self._upload() if path.endswith("/upload") else None
            body: dict[str, str] = {}
            preview: dict[str, Any] = {}
            if upload is None and path.startswith("/api/"):
                preview = self._json_body()
                body = {k: v for k, v in preview.items() if isinstance(v, str)}
            elif upload is None:
                body = self._form()
            with st.lock:
                if path.startswith("/api/"):
                    return self._api(path, body, preview)
                return self._post(path, upload, body)
        if method in ("GET", "HEAD"):
            if path == "/" or path == "":
                return _redirect("/onepager")
            if path.startswith("/static/") or path == "/favicon.ico":
                # /favicon.ico is LODESTAR's own icon (ADR-0541), not Polaris²'s; a static name is
                # looked up EXACTLY in the allowlist — never joined onto a filesystem path
                name = "lodestar.ico" if path == "/favicon.ico" else path[len("/static/") :]
                asset = self.server.assets.get(name)
                if asset is None:
                    return _Reply(404, b"not found", "text/plain; charset=utf-8")
                return _Reply(200, asset[0], asset[1], (("Cache-Control", "no-cache"),))
            with st.lock:
                return self._get(path)
        raise _Refused(405, "method not allowed")

    def _json_body(self) -> dict[str, Any]:
        """A studio API call's body: one small JSON object (``Content-Type: application/json``,
        the form cap) whose values are strings — or, for a preview, a list of two dates and a
        flag. Anything else is refused before the lock is taken."""
        ctype = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            raise _Refused(415, "a studio call must be application/json")
        raw = self._body(MAX_FORM_BYTES)
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, ValueError) as exc:
            raise _Refused(400, "the request body is not JSON") from exc
        if not isinstance(data, dict):
            raise _Refused(400, "the request body must be a JSON object")
        out: dict[str, Any] = {}
        for key, value in data.items():
            if not isinstance(key, str) or len(key) > 32:
                raise _Refused(400, "a request field name is not valid")
            if isinstance(value, bool) or value is None:
                out[key] = value
            elif isinstance(value, str | int | float):
                out[key] = str(value)[:256]
            elif (
                isinstance(value, list)
                and len(value) <= 2
                and all(isinstance(v, str) and len(v) <= 40 for v in value)
            ):
                out[key] = list(value)
            else:
                raise _Refused(400, "a request field is not a string")
        return out

    def _studio(self, page: str, *, reveal: bool = False, outcome: Any = None) -> _Reply:
        """The page's state as JSON (the regions included) — what every studio call answers."""
        st = self.server.state
        today, made = self._dates()
        state = studio_state(st, st.history, page, today, made, reveal=reveal)
        if outcome is not None:
            state["label"] = outcome.label
            state["toast"] = (
                {"text": outcome.toast, "status": outcome.status} if outcome.toast else None
            )
        return _Reply(200, json.dumps(state, ensure_ascii=False).encode("utf-8"), _JSON)

    def _api(self, path: str, body: dict[str, str], raw: dict[str, Any]) -> _Reply:
        """``POST /api/<action>`` — the studio's live path (ADR-0543): every change is the SAME
        action the form routes take (:func:`~schedule_forensics.web.lodestar_actions.perform`),
        answered with the page's whole state instead of a redirect."""
        st = self.server.state
        name = path[len("/api/") :]
        page = studio_actions.page_of(body.get("page"))
        if name in ("undo", "redo"):
            label = st.history.undo(st) if name == "undo" else st.history.redo(st)
            outcome = studio_actions.Outcome(
                label,
                (f"Undid: {label}" if name == "undo" else f"Redid: {label}")
                if label
                else ("Nothing to undo." if name == "undo" else "Nothing to redo."),
                "info",
            )
            return self._studio(page, outcome=outcome)
        if name == "preview":
            return self._preview(page, raw)
        if name not in studio_actions.ACTIONS or name == "upload":
            return _json_error(f"no studio action named {name[:24]!r}", 404)
        outcome = studio_actions.perform(st, st.history, name, body, max_bytes=MAX_UPLOAD_BYTES)
        return self._studio(page, reveal=name == "example", outcome=outcome)

    def _preview(self, page: str, raw: dict[str, Any]) -> _Reply:
        """``POST /api/preview`` — the slide for a PROPOSED change, never committed: a copy of the
        session (its own empty layout cache, its own empty log) takes the change and is laid out;
        the session itself, its cache and its log are untouched. The scrubber asks it while it is
        dragged; the Show-me demos run on it. Proposals: ``today`` (an ISO date), ``window``
        (two ISO dates, or null for all dates), ``link`` (``pred`` / ``succ`` / ``kind``) and
        ``example`` (the example list or pair, when the page has none)."""
        st = self.server.state
        today, made = self._dates()
        copy = replace(st, onepager_cache={}, history=History(), lock=threading.RLock())
        compare = page == "compare"
        if raw.get("example") is True:
            has = st.onepager_prior is not None and st.onepager_current is not None
            if not (has if compare else st.onepager is not None):
                studio_actions.example_session(copy, page, max_bytes=MAX_UPLOAD_BYTES)
        when = raw.get("today")
        if isinstance(when, str) and when:
            got = parse_date(when[:40])
            if got is not None:
                today = got[0]
                copy.onepager_today = today
        if "window" in raw:
            win = raw.get("window")
            if win is None:
                window = None
            elif isinstance(win, list) and len(win) == 2:
                parsed = actions.parse_window(win[0], win[1])
                window = None if isinstance(parsed, str) else parsed
            else:
                window = None
            if compare:
                copy.onepager_compare_window = window
            else:
                copy.onepager_window = window
        if isinstance(raw.get("pred"), str) and isinstance(raw.get("succ"), str):
            actions.edit_links(
                copy,
                "compare" if compare else "onepager",
                "add",
                raw["pred"],
                raw["succ"],
                str(raw.get("kind") or "FS"),
            )
        if compare:
            clay = onepager_compare_layout(copy, today, made)
            blob = compare_layout_json(clay) if clay is not None else None
        else:
            lay = onepager_layout(copy, today, made)
            blob = layout_json(lay) if lay is not None else None
        out = {"page": page, "layout": blob, "dataDate": today.isoformat()}
        return _Reply(200, json.dumps(out, ensure_ascii=False).encode("utf-8"), _JSON)

    def _get(self, path: str) -> _Reply:
        st = self.server.state
        today, made = self._dates()
        _cls, text = marking(st.unclassified)
        if path == "/launch":
            # the boot screen the program opens on (ADR-0541) — outside the frame
            chosen = st.onepager_today is not None
            return _html(
                lodestar_launch_html(st, unclassified=st.unclassified, today=today, chosen=chosen)
            )
        for page, (route, _label, _icon, _eyebrow) in PAGES.items():
            if path == route:
                return _html(studio_page(st, st.history, page, today, made))
        if path == "/api/state":
            query = parse_qs(urlsplit(self.path).query)
            return self._studio(studio_actions.page_of((query.get("page") or ["timeline"])[0]))
        if path == "/export/pptx/onepager":
            return self._download(actions.onepager_pptx(st, today, text, NAME, made))
        if path == "/export/pptx/onepager-compare":
            return self._download(actions.compare_pptx(st, today, text, NAME, made))
        for stem, fname in (
            ("onepager-template", "one-pager-template"),
            ("onepager-compare", "one-pager-compare"),
            ("onepager", "one-pager-list"),
        ):
            for fmt, (media, render) in _EXPORT_MEDIA.items():
                if path != f"/export/{fmt}/{stem}":
                    continue
                if stem == "onepager-template":
                    got: TableSet | str = onepager_template()
                elif stem == "onepager":
                    got = actions.onepager_workbook(st, today, made)
                else:
                    got = actions.compare_workbook(st, today, made)
                if isinstance(got, str):
                    return _json_error(got)
                return _Reply(
                    200,
                    render(got),
                    media,
                    (("Content-Disposition", f'attachment; filename="{fname}.{fmt}"'),),
                )
        return _Reply(404, b"not found", "text/plain; charset=utf-8")

    def _wants_json(self) -> bool:
        return "application/json" in self.headers.get("Accept", "")

    def _post(
        self,
        path: str,
        upload: tuple[dict[str, str], str | None, bytes] | None,
        form: dict[str, str],
    ) -> _Reply:
        st = self.server.state
        if path in ("/onepager/upload", "/onepager-compare/upload") and upload is not None:
            fields, name, data = upload
            page = "compare" if path.startswith("/onepager-compare") else "timeline"
            params = {**fields, "page": page}
            outcome = studio_actions.perform(
                st, st.history, "upload", params, max_bytes=MAX_UPLOAD_BYTES, upload=(name, data)
            )
            if self._wants_json():
                # the studio posts the file with fetch and repaints from the answer
                return self._studio(page, reveal=outcome.label is not None, outcome=outcome)
            return _redirect(PAGES[page][0])
        get = form.get
        if path == "/quit":
            self._quit = True  # the server stops once this page is written (``_dispatch``)
            return _html(stopped_page(unclassified=st.unclassified))
        back = get("next", "")
        back = back if back in ("/onepager", "/onepager-compare") else "/onepager"
        if path == "/marking":
            studio_actions.perform(
                st,
                st.history,
                "marking",
                {"marking": get("marking", "")},
                max_bytes=MAX_UPLOAD_BYTES,
            )
            return _redirect(back)
        if path in ("/undo", "/redo"):
            # the header's two buttons with scripting off (the studio posts /api/undo / redo)
            if path == "/undo":
                st.history.undo(st)
            else:
                st.history.redo(st)
            return _redirect(back)
        route = _FORM_ROUTES.get(path)
        if route is None:
            return _Reply(404, b"not found", "text/plain; charset=utf-8")
        action, page = route
        studio_actions.perform(
            st, st.history, action, {**form, "page": page}, max_bytes=MAX_UPLOAD_BYTES
        )
        return _redirect(PAGES[page][0] + _LANDING.get(action, ""))

    def _download(self, got: actions.Download | str) -> _Reply:
        if isinstance(got, str):
            return _json_error(got)
        return _Reply(200, got.content, got.media_type, (("Content-Disposition", got.disposition),))

    def _send(self, reply: _Reply, *, head_only: bool) -> None:
        try:
            self.send_response(reply.status)
            self.send_header("Content-Type", reply.content_type)
            self.send_header("Content-Length", str(len(reply.body)))
            headers = dict(reply.headers)
            headers.setdefault("Cache-Control", "no-store")
            for key, value in {**_SECURITY_HEADERS, **headers}.items():
                self.send_header(key, _safe_header(value))
            if self.close_connection:
                self.send_header("Connection", "close")
            self.end_headers()
            if not head_only:
                self.wfile.write(reply.body)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True


def _same_origin(fetch_site: str | None, origin: str | None, hosts: frozenset[str]) -> bool:
    """LODESTAR's origin rule ON TOP of Polaris²'s gate (``_csrf_safe``): that gate lets an Origin
    from ANY loopback port through when the browser sends no ``Sec-Fetch-Site`` (and a test
    client's ``testserver``); LODESTAR's own origin is exact, as its Host gate already is."""
    if fetch_site is not None or origin is None:
        return True
    return urlsplit(origin.strip()).netloc.lower() in hosts


def _multipart_head(boundary: str) -> bytes:
    """The header the email parser is handed: ``multipart/form-data`` with THIS boundary, quoted
    (a plain RFC 2046 boundary carries no quote or backslash)."""
    return (
        b'Content-Type: multipart/form-data; boundary="' + boundary.encode("ascii") + b'"\r\n\r\n'
    )


def _boundary(ctype: str) -> str:
    """The ONE boundary ``ctype`` names — refused unless there is exactly one ``boundary``
    parameter and it is plain: RFC 2046's characters, 1 to 70 of them, a space only inside quotes;
    and unless the email parser reads the rebuilt header back as that same boundary."""
    found = list(_BOUNDARY_PARAM.finditer(ctype))
    if not found:
        raise _Refused(400, "the upload names no multipart boundary")
    if len(found) > 1:
        raise _Refused(400, "the upload names more than one multipart boundary")
    param = found[0]
    rest = ctype[param.end() :]
    if rest.startswith('"'):
        value, closed, _after = rest[1:].partition('"')
        plain = bool(closed)
    else:
        value = rest.split(";", 1)[0].strip()
        plain = " " not in value
    if not (plain and param.group(1) is None and _BOUNDARY.fullmatch(value)):
        raise _Refused(400, "the upload's multipart boundary is not a plain one")
    head = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        _multipart_head(value), headersonly=True
    )
    if head.get_boundary() != value:
        raise _Refused(400, "the upload's multipart boundary is not a plain one")
    return value


def _prescan(ctype: str, body: bytes) -> str:
    """Refuse a multipart body the upload form never sends, before the email parser — whose cost
    grows faster than the body on exactly these shapes — ever sees it; return the boundary it
    was split on, the one the parser must use.

    Refused: a boundary that is not ONE plain parameter (:func:`_boundary`); more than
    :data:`MAX_PARTS` parts; a part whose header block runs past :data:`MAX_PART_HEADER_BYTES` or
    never ends; a part that is itself split into parts — ``multipart/*``, or ``message/*`` (the
    parser reads a message part's body as a message, which may be multipart). A part's type is
    taken as the email parser itself reads that part's header block, so an encoded word or a
    folded line reads the same to both. Every delimiter but a closing one opens a part — the LAST
    one too when no closing delimiter follows (the parser reads that part to the end)."""
    boundary = _boundary(ctype)
    parts = [p for p in body.split(b"--" + boundary.encode("ascii"))[1:] if not p.startswith(b"--")]
    if len(parts) > MAX_PARTS:
        raise _Refused(400, "the upload carried too many parts")
    for part in parts:
        end = part.find(b"\r\n\r\n")
        if end < 0 or end > MAX_PART_HEADER_BYTES:
            raise _Refused(400, "an upload part's headers are too long or unfinished")
        line = _DELIMITER_LINE.match(part)
        head = part[line.end() if line else 0 : end + 4]
        kind = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(head, headersonly=True)
        if kind.get_content_maintype() in ("multipart", "message"):
            raise _Refused(400, "an upload part may not itself hold parts")
    return boundary


def serve(port: int = 0, state: LodestarState | None = None) -> LodestarServer:
    """A LODESTAR server bound to 127.0.0.1 (``port`` 0: any free port the system picks)."""
    return LodestarServer(port, state or LodestarState())
