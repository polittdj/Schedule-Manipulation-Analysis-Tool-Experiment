"""Self-contained static report: inline SVG, inline CSS, ZERO <script>, print-ready.

Every exhibit is a page-break-avoided section; every date in the document derives from the
payload (no wall-clock reads); no external URL of any kind (the air-gap test greps for it).
"""

from __future__ import annotations

from jinja2 import Template

from schedule_forensics.exhibits.payload import ExhibitPayload
from schedule_forensics.exhibits.render_svg import EXHIBITS

_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
body { font-family: "Segoe UI", Arial, sans-serif; color: #1a2330; margin: 24px; }
h1 { font-size: 20px; } h2 { font-size: 15px; margin: 18px 0 6px; }
.exhibit { page-break-inside: avoid; border: 1px solid #c7cdd6; border-radius: 6px;
  padding: 10px; margin: 0 0 18px; }
.meta { font-size: 11px; color: #5f6b7a; white-space: pre-line; }
svg { max-width: 100%; height: auto; }
@media print { .exhibit { border: none; padding: 0; } }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<p class="meta">{{ meta }}</p>
{% for ex in exhibits %}
<section class="exhibit"><h2>{{ ex.id }} — {{ ex.name }}</h2>{{ ex.svg }}</section>
{% endfor %}
</body>
</html>
"""
)


def render_report(payload: ExhibitPayload) -> str:
    """The one-file HTML report (inline SVG/CSS, no scripts, print-ready)."""
    m = payload.manifest
    exhibits = [
        {"id": ex_id, "name": stem.replace("_", " "), "svg": renderer(payload)}
        for ex_id, (stem, renderer) in EXHIBITS.items()
    ]
    dates = [f.status_date for f in m.files]
    meta = (
        f"SMAT {m.smat_version} · git {m.git_sha[:8]} · run {m.run_id}\n"
        f"basis={m.basis} lf_mode={m.lf_mode} "
        f"tf_threshold={m.tf_threshold_minutes // 480}wd terminus={list(m.terminus_uids)}\n"
        f"files={len(m.files)} · dates {dates[0] if dates else '?'}-"
        f"{dates[-1] if dates else '?'} · unmatched={m.unmatched_count} · "
        f"transitions n={len(payload.transitions)}"
    )
    # str(...) — CI's mypy sees jinja2's render as Any (no type stubs); the render IS a str
    return str(
        _TEMPLATE.render(
            title=f"Critical-Path Volatility Exhibits — run {m.run_id}",
            meta=meta,
            exhibits=exhibits,
        )
    )
