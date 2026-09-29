"""Start LODESTAR: serve the two One-Pager pages on this computer only and open the browser.

``python LODESTAR.pyz`` (or a double-click) lands here through the archive's own ``__main__``
(:mod:`schedule_forensics.lodestar._pyz_main`). The console window it runs in IS its lifetime:
close the window, press Ctrl+C, or press Quit on the page, and LODESTAR stops — everything it
held was in memory and is gone.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser

from schedule_forensics.lodestar.server import serve
from schedule_forensics.web.lodestar_shell import AUTHOR, CONTACT, NAME, TAGLINE, VERSION

#: Tried first so the browser's saved view (a per-address preference) survives a restart; any
#: free port the system picks when it is taken.
PREFERRED_PORT = 47810


def banner(url: str) -> str:
    return (
        f"{NAME} {VERSION} — {TAGLINE}\n"
        f"Created by {AUTHOR} · questions or issues: {CONTACT}\n"
        f"Running at {url} (this computer only — nothing you load leaves it; no AI).\n"
        "Leave this window open while you work. Close it, press Ctrl+C, or press Quit on the "
        "page to stop."
    )


def _say(text: str) -> None:
    """Print to the console LODESTAR runs in — never failing on one that cannot show "—" or "·"
    (a redirected Windows code page), and never failing with no console at all (``pythonw``)."""
    out = sys.stdout
    if out is None:
        return
    try:
        print(text, file=out, flush=True)
    except UnicodeEncodeError:
        ascii_text = text.replace("—", "-").replace("·", "-")
        print(ascii_text.encode("ascii", "replace").decode("ascii"), file=out, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="LODESTAR",
        description=f"{NAME} {VERSION} — {TAGLINE}. Created by {AUTHOR} ({CONTACT}).",
    )
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    parser.add_argument("--port", type=int, default=PREFERRED_PORT, help="the port to try first")
    parser.add_argument("--version", action="version", version=f"{NAME} {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        server = serve(args.port)
    except (OSError, OverflowError):
        server = serve(0)
    url = f"http://127.0.0.1:{server.server_port}/onepager"
    _say(banner(url))
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    _say(f"{NAME} stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
