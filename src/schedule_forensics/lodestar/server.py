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
  that stalls or trickles its body holds up only itself. A multipart upload is pre-scanned: a few
  parts, each with short headers, or it is refused before the email parser sees it (its cost
  grows faster than the body with many parts or long encoded headers — ADR-0539's review).
* **Host is exactly this server** — ``127.0.0.1:<port>`` or ``localhost:<port>`` — a stricter
  form of the SEC-3 DNS-rebinding allowlist; **SEC-2's cross-site gate** on every POST.
* **Static files come from a fixed allowlist loaded at start**, never from a path joined onto a
  request (a filesystem package would serve ``../`` from a joined path).
* **Nothing about a request is logged** — not its path, not its file name (the CUI log rule):
  ``log_message`` / ``log_error`` / ``handle_error`` are silenced, and an unexpected error is a
  generic 500 page. With no console at all (``pythonw``) the server still answers.
* **CSP, nosniff, no-referrer and frame-deny on every response**, including every refusal — the
  standard library's own error pages too (an unknown method, a malformed request line) — and
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
import socketserver
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_links import Link
from schedule_forensics.reports.tableset import TableSet
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.web import onepager_actions as actions
from schedule_forensics.web.lodestar_shell import NAME, lodestar_page, marking, stopped_page
from schedule_forensics.web.onepager import _onepager_body, onepager_template
from schedule_forensics.web.onepager_compare import _onepager_compare_body
from schedule_forensics.web.security import _SECURITY_HEADERS, _csrf_safe

#: An upload is a One-Pager list — a small workbook. Twenty megabytes is far past any list; the
#: email parser holds about 13x a real upload (a file and two fields) in memory, and a body of
#: many small parts — which costs it far more — is refused before it is parsed (``_prescan``;
#: ADR-0539 and its review, measured).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
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

#: The ONLY static files LODESTAR serves — the two pages' painters, the panel toolkit, the theme
#: switch, the data-date line and axis-caption helpers, the styles and the icon. Loaded once, at
#: start, from the package (inside the .pyz or on disk alike); any other /static/ name is a 404.
STATIC_ASSETS: dict[str, str] = {
    "onepager.js": "text/javascript; charset=utf-8",
    "onepager_compare.js": "text/javascript; charset=utf-8",
    "onepager_links.js": "text/javascript; charset=utf-8",
    "panelkit.js": "text/javascript; charset=utf-8",
    "theme.js": "text/javascript; charset=utf-8",
    "gantt.js": "text/javascript; charset=utf-8",
    "chartframe.js": "text/javascript; charset=utf-8",
    "base.css": "text/css; charset=utf-8",
    "app.css": "text/css; charset=utf-8",
    "hud.css": "text/css; charset=utf-8",
    "sf-themes.css": "text/css; charset=utf-8",
    "lodestar.css": "text/css; charset=utf-8",
    "favicon.ico": "image/x-icon",
}
#: The ⤓ EXCEL exports (the list, the comparison, the template). No Word export: no LODESTAR page
#: offers one, and a document titled by Polaris²'s table sets would say POLARIS² (ADR-0539).
_EXPORT_MEDIA: dict[str, tuple[str, Callable[[TableSet], bytes]]] = {
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", render_xlsx),
}
_HTML = "text/html; charset=utf-8"


def load_assets() -> dict[str, tuple[bytes, str]]:
    """Every allowlisted static file's bytes and type — read once, from the package."""
    static = files("schedule_forensics.web").joinpath("static")
    return {name: (static.joinpath(name).read_bytes(), ct) for name, ct in STATIC_ASSETS.items()}


@dataclass
class LodestarState:
    """Everything LODESTAR holds, in memory only: the two pages' lists, titles, windows, links and
    one-shot messages (the :class:`~schedule_forensics.web.onepager_common.OnePagerSession`
    protocol — the same attributes Polaris²'s session carries), plus the marking choice."""

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
    unclassified: bool = False
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
            reply = _json_error(refused.reason, refused.status)
        except Exception:
            self.close_connection = True
            reply = _Reply(500, b"LODESTAR hit an unexpected error.", "text/plain; charset=utf-8")
        self._send(reply, head_only=method == "HEAD")
        if self._quit:
            # only now, with the "stopped" page written and flushed, does the server stop
            self.close_connection = True
            threading.Thread(target=self.server.shutdown, daemon=True).start()

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
        body = self._body(MAX_UPLOAD_BYTES)
        _prescan(ctype, body)
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + ctype.encode("latin-1", "replace") + b"\r\n\r\n" + body
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

    def _today(self) -> dt.date:
        st = self.server.state
        return st.onepager_today or self.server.today or dt.date.today()

    def _route(self, method: str) -> _Reply:
        path = urlsplit(self.path).path
        st = self.server.state
        if method == "POST":
            # the body is read and parsed BEFORE the lock: a slow client holds up only itself
            upload = self._upload() if path.endswith("/upload") else None
            form = None if upload is not None else self._form()
            with st.lock:
                return self._post(path, upload, form or {})
        if method in ("GET", "HEAD"):
            if path == "/" or path == "":
                return _redirect("/onepager")
            if path.startswith("/static/") or path == "/favicon.ico":
                name = path.rsplit("/", 1)[-1]
                asset = self.server.assets.get(name)
                if asset is None or path not in (f"/static/{name}", "/favicon.ico"):
                    return _Reply(404, b"not found", "text/plain; charset=utf-8")
                return _Reply(200, asset[0], asset[1], (("Cache-Control", "no-cache"),))
            with st.lock:
                return self._get(path)
        raise _Refused(405, "method not allowed")

    def _get(self, path: str) -> _Reply:
        st = self.server.state
        today = self._today()
        _cls, text = marking(st.unclassified)
        if path == "/onepager":
            body = _onepager_body(st, today)
            return _html(lodestar_page("Timeline", body, path=path, unclassified=st.unclassified))
        if path == "/onepager-compare":
            body = _onepager_compare_body(st, today)
            return _html(lodestar_page("Compare", body, path=path, unclassified=st.unclassified))
        if path == "/export/pptx/onepager":
            return self._download(actions.onepager_pptx(st, today, text, NAME))
        if path == "/export/pptx/onepager-compare":
            return self._download(actions.compare_pptx(st, today, text, NAME))
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
                    got = actions.onepager_workbook(st, today)
                else:
                    got = actions.compare_workbook(st, today)
                if isinstance(got, str):
                    return _json_error(got)
                return _Reply(
                    200,
                    render(got),
                    media,
                    (("Content-Disposition", f'attachment; filename="{fname}.{fmt}"'),),
                )
        return _Reply(404, b"not found", "text/plain; charset=utf-8")

    def _post(
        self,
        path: str,
        upload: tuple[dict[str, str], str | None, bytes] | None,
        form: dict[str, str],
    ) -> _Reply:
        st = self.server.state
        if path == "/onepager/upload" and upload is not None:
            fields, name, data = upload
            actions.load_list(
                st, name, data, max_bytes=MAX_UPLOAD_BYTES, layout=fields.get("layout", "auto")
            )
            return _redirect("/onepager")
        if path == "/onepager-compare/upload" and upload is not None:
            fields, name, data = upload
            actions.load_compare(
                st,
                fields.get("slot", "current"),
                name,
                data,
                max_bytes=MAX_UPLOAD_BYTES,
                layout=fields.get("layout", "auto"),
            )
            return _redirect("/onepager-compare")
        get = form.get
        if path == "/quit":
            self._quit = True  # the server stops once this page is written (``_dispatch``)
            return _html(stopped_page())
        if path == "/marking":
            st.unclassified = get("marking") == "unclassified"
            back = get("next", "")
            return _redirect(back if back in ("/onepager", "/onepager-compare") else "/onepager")
        if path == "/onepager/title":
            actions.set_title(st, get("title", ""))
        elif path == "/onepager/window":
            actions.set_window(st, get("start", ""), get("end", ""), get("action", "apply"))
        elif path == "/onepager/clear":
            actions.clear_list(st)
        elif path == "/onepager/links":
            actions.edit_links(
                st,
                "onepager",
                get("action", "add"),
                get("pred", ""),
                get("succ", ""),
                get("kind", "FS"),
            )
            return _redirect("/onepager#opLinks")
        elif path == "/onepager-compare/swap":
            actions.swap_compare(st)
        elif path == "/onepager-compare/title":
            actions.set_compare_title(st, get("title", ""))
        elif path == "/onepager-compare/window":
            actions.set_compare_window(st, get("start", ""), get("end", ""), get("action", "apply"))
        elif path == "/onepager-compare/clear":
            actions.clear_compare(st)
        elif path == "/onepager-compare/links":
            actions.edit_links(
                st,
                "compare",
                get("action", "add"),
                get("pred", ""),
                get("succ", ""),
                get("kind", "FS"),
            )
            return _redirect("/onepager-compare#opcLinks")
        else:
            return _Reply(404, b"not found", "text/plain; charset=utf-8")
        return _redirect(
            "/onepager-compare" if path.startswith("/onepager-compare") else "/onepager"
        )

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


def _prescan(ctype: str, body: bytes) -> None:
    """Refuse a multipart body the upload form never sends — more than :data:`MAX_PARTS` parts,
    or a part whose header block runs past :data:`MAX_PART_HEADER_BYTES` — before the email
    parser, whose cost grows faster than the body on exactly those shapes, ever sees it."""
    boundary = ""
    for param in ctype.split(";")[1:]:
        key, _, value = param.strip().partition("=")
        if key.strip().lower() == "boundary":
            boundary = value.strip().strip('"')
    if not boundary:
        raise _Refused(400, "the upload names no multipart boundary")
    parts = body.split(b"--" + boundary.encode("latin-1", "replace"))[1:-1]
    if len(parts) > MAX_PARTS:
        raise _Refused(400, "the upload carried too many parts")
    for part in parts:
        end = part.find(b"\r\n\r\n")
        if end < 0 or end > MAX_PART_HEADER_BYTES:
            raise _Refused(400, "an upload part's headers are too long or unfinished")


def serve(port: int = 0, state: LodestarState | None = None) -> LodestarServer:
    """A LODESTAR server bound to 127.0.0.1 (``port`` 0: any free port the system picks)."""
    return LodestarServer(port, state or LodestarState())
