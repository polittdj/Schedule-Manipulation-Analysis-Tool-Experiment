"""Schedule Forensics localhost web UI (Flask 3.x).

LAW 1 compliance:
- Server binds HOST = "127.0.0.1" only (module constant; tested).
- No external CDN references; all CSS/JS is inline in the template.
- Schedule data is never written to disk; all parse/analysis state lives in
  the module-level _STATE dict (in-memory only).
- Reports are streamed from io.BytesIO, never written to a path.
- POST /wipe destroys all in-memory state.
"""

from schedule_forensics.webapp.app import HOST, create_app, main

__all__ = ["HOST", "create_app", "main"]
