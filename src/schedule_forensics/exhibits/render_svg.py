"""Static exhibit renderers — pure ``payload -> svg_str`` functions, stdlib string building.

INTENTIONAL divergence from the interactive layer: standalone SVG files open OUTSIDE the app,
where the CSS custom properties do not exist (``var(--ok)`` renders black/unstyled), so this
module emits **literal hex** from the single :data:`PALETTE` below (light-theme values matching
``base.css``: ok≈green, bad≈red, warn≈amber, accent≈blue, ink/muted/line grays). The
interactive JS keeps using CSS vars.

Rendering rules (hard rails): ZERO arithmetic beyond axis scaling/tick placement — every
value drawn is a payload field; no wall-clock reads; gaps render as GAPS with the payload's
stated reason, never interpolation; EX-03 breaks its line at every rebaseline boundary; the
grayscale-survivable EX-01 uses one glyph + fill per state with constraint-critical hatched
via ``<pattern>``. Every figure carries the provenance footer so a screenshot stays citable.
"""

from __future__ import annotations

from schedule_forensics.exhibits.payload import ExhibitPayload, TaskUpdateCell, states

#: Literal-hex palette (light-theme values mirroring base.css; see module docstring).
PALETTE: dict[str, str] = {
    "ok": "#2e7d32",
    "bad": "#c62828",
    "warn": "#b26a00",
    "accent": "#1565c0",
    "ink": "#1a2330",
    "muted": "#5f6b7a",
    "line": "#c7cdd6",
    "field": "#f2f4f7",
    "purple": "#6a4fa3",
}

#: state -> (fill, glyph) — the two most-conflated states (driving- vs constraint-critical)
#: are the two most visually distinct: solid red block vs hatched purple with a cross glyph.
STATE_STYLE: dict[str, tuple[str, str]] = {
    "DRIVING_CRITICAL": (PALETTE["bad"], "▓"),
    "DRIVING_FLOAT": (PALETTE["accent"], "▒"),
    "CONSTRAINT_CRITICAL": ("url(#sfHatch)", "X"),
    "NONCRITICAL": (PALETTE["muted"], "·"),
    "COMPLETE": (PALETTE["ok"], "✓"),
    "ABSENT": ("none", ""),
}

_FONT = 'font-family="Segoe UI, Arial, sans-serif"'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _footer(p: ExhibitPayload, y: int, width: int) -> str:
    """The provenance footer rendered INSIDE every figure (screenshots stay citable)."""
    m = p.manifest
    dates = [f.status_date for f in m.files]
    nz = sum(1 for f in m.files if (f.recompute_delta_nonzero_task_count or 0) > 0)
    lines = [
        f"SMAT {m.smat_version} · git {m.git_sha[:8]} · run {m.run_id}",
        f"basis={m.basis} lf_mode={m.lf_mode} tf_threshold="
        f"{m.tf_threshold_minutes // 480}wd terminus={list(m.terminus_uids)}",
        f"files={len(m.files)} (SHA-256 in manifest) · dates "
        f"{dates[0] if dates else '?'}-{dates[-1] if dates else '?'}",
        f"unmatched={m.unmatched_count} · transitions n={len(p.transitions)} · "
        f"nonzero-recompute-delta files={nz}",
    ]
    out = []
    for i, ln in enumerate(lines):
        out.append(
            f'<text x="8" y="{y + 11 + i * 11}" font-size="8" fill="{PALETTE["muted"]}" '
            f"{_FONT}>{_esc(ln)}</text>"
        )
    out.append(
        f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{PALETTE["line"]}" '
        'stroke-width="0.6"/>'
    )
    return "".join(out)


def _doc(width: int, height: int, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{_esc(title)}">'
        "<defs>"
        f'<pattern id="sfHatch" width="5" height="5" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse">'
        f'<rect width="5" height="5" fill="{PALETTE["field"]}"/>'
        f'<line x1="0" y1="0" x2="0" y2="5" stroke="{PALETTE["purple"]}" stroke-width="2.2"/>'
        "</pattern></defs>"
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
        f'<text x="8" y="16" font-size="12" font-weight="bold" fill="{PALETTE["ink"]}" '
        f"{_FONT}>{_esc(title)}</text>" + body + "</svg>"
    )


def _dates(p: ExhibitPayload) -> list[str]:
    return [u.status_date for u in p.update_summaries]


FOOTER_H = 52
ROW_CAP = 40


def render_ex00_provenance(p: ExhibitPayload) -> str:
    """EX-00: one cell per status date; marked when the file shows a nonzero recompute delta
    (resave signal); 'n/a' glyph when the recompute check is unavailable for that file."""
    files = p.manifest.files
    w, cell = 900, max(30, min(90, 860 // max(1, len(files))))
    h = 96 + FOOTER_H
    body = []
    for i, f in enumerate(files):
        x = 8 + i * (cell + 4)
        nz = f.recompute_delta_nonzero_task_count
        fill = PALETTE["field"] if nz in (None, 0) else PALETTE["warn"]
        body.append(
            f'<rect x="{x}" y="30" width="{cell}" height="26" fill="{fill}" '
            f'stroke="{PALETTE["line"]}"/>'
        )
        mark = "n/a" if nz is None else ("⚠" if nz else "✓")
        body.append(
            f'<text x="{x + cell / 2}" y="47" font-size="10" text-anchor="middle" '
            f'fill="{PALETTE["ink"]}" {_FONT}>{mark}</text>'
        )
        body.append(
            f'<text x="{x + cell / 2}" y="70" font-size="8" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(f.status_date)}</text>'
        )
    body.append(
        f'<text x="8" y="88" font-size="8.5" fill="{PALETTE["muted"]}" {_FONT}>'
        "⚠ = nonzero recompute delta (file was resaved/recomputed outside statusing); "
        "✓ = clean; n/a = recompute check unavailable for this file</text>"
    )
    body.append(_footer(p, 96, w))
    return _doc(w, h, "EX-00 Provenance rail", "".join(body))


def _instability_order(p: ExhibitPayload) -> list[int]:
    """Row order for EX-01/EX-02: weighted_instability DESCENDING (flappers first) — explicitly
    not tenure and not ECI. Tasks without the measure sort after those with it."""

    def key(uid: int) -> tuple[int, float, int]:
        ts = next((t for t in p.task_summaries if t.task_uid == uid), None)
        wi = ts.weighted_instability if ts and ts.weighted_instability is not None else None
        return (0, -(wi if wi is not None else 0.0), uid) if wi is not None else (1, 0.0, uid)

    uids = sorted({c.task_uid for c in p.cells})
    return sorted(uids, key=key)


def _cells_by(p: ExhibitPayload) -> dict[tuple[int, str], TaskUpdateCell]:
    return {(c.task_uid, c.status_date): c for c in p.cells}


def render_ex01_barcode(p: ExhibitPayload) -> str:
    """EX-01: six-state criticality barcode, instability-sorted, glyph + fill per state
    (grayscale-printer survivable; constraint-critical hatched via <pattern>)."""
    dates = _dates(p)
    order = _instability_order(p)[:ROW_CAP]
    dropped = max(0, len({c.task_uid for c in p.cells}) - ROW_CAP)
    by = _cells_by(p)
    cw, rh = max(18, min(60, 700 // max(1, len(dates)))), 16
    w = 190 + len(dates) * cw + 16
    h = 46 + len(order) * rh + 30 + FOOTER_H
    body = []
    for j, d in enumerate(dates):
        body.append(
            f'<text x="{190 + j * cw + cw / 2}" y="40" font-size="7.5" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(d[5:])}</text>'
        )
    for i, uid in enumerate(order):
        y = 46 + i * rh
        name = next((c.task_name for c in p.cells if c.task_uid == uid), str(uid))
        body.append(
            f'<text x="186" y="{y + 11}" font-size="8" text-anchor="end" '
            f'fill="{PALETTE["ink"]}" {_FONT}>{_esc(str(uid) + " " + name[:24])}</text>'
        )
        for j, d in enumerate(dates):
            cell = by.get((uid, d))
            state = cell.state if cell else "ABSENT"
            fill, glyph = STATE_STYLE[state]
            x = 190 + j * cw
            if fill != "none":
                body.append(
                    f'<rect x="{x}" y="{y}" width="{cw - 2}" height="{rh - 2}" fill="{fill}" '
                    f'stroke="{PALETTE["line"]}" stroke-width="0.4" data-state="{state}"/>'
                )
            if glyph:
                body.append(
                    f'<text x="{x + (cw - 2) / 2}" y="{y + 11.5}" font-size="9" '
                    f'text-anchor="middle" fill="#ffffff" {_FONT}>{glyph}</text>'
                )
    ly = 46 + len(order) * rh + 14
    lx = 190
    for st in states():
        fill, glyph = STATE_STYLE[st]
        if fill != "none":
            body.append(
                f'<rect x="{lx}" y="{ly - 9}" width="12" height="10" fill="{fill}" '
                f'stroke="{PALETTE["line"]}" stroke-width="0.4"/>'
            )
        body.append(
            f'<text x="{lx + 15}" y="{ly}" font-size="7.5" fill="{PALETTE["muted"]}" '
            f"{_FONT}>{glyph} {st}</text>"
        )
        lx += 15 + 7 * len(st) + 18
    note = f"top {len(order)} by weighted instability (descending)" + (
        f"; {dropped} further task(s) not shown" if dropped else ""
    )
    body.append(
        f'<text x="8" y="{ly}" font-size="8" fill="{PALETTE["muted"]}" {_FONT}>{_esc(note)}</text>'
    )
    body.append(_footer(p, 46 + len(order) * rh + 30, w))
    return _doc(w, h, "EX-01 Six-state criticality barcode", "".join(body))


def render_ex03_volatility_vs_null(p: ExhibitPayload) -> str:
    """EX-03: observed churn line over the expected (null-model) band; the line BREAKS at every
    rebaseline boundary; transitions with above-median edit counts are marked; a missing null
    model renders as 'null model unavailable' (no band), never a fabricated one."""
    trans = p.transitions
    w, h = 900, 250 + FOOTER_H
    left, right, top, bot = 46, 892, 30, 210
    n = max(1, len(trans))
    maxv = max(
        [0.05]
        + [t.observed_churn for t in trans]
        + [t.expected_churn for t in trans if t.expected_churn is not None]
    )

    def x(i: int) -> float:
        return left + (right - left) * ((i + 0.5) / n)

    def y(v: float) -> float:
        return bot - (bot - top) * (v / (maxv * 1.15))

    body = [
        f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{PALETTE["line"]}"/>',
    ]
    # edit counts live on the DESTINATION update's summary (join by to_status_date)
    ups_by_date = {u.status_date: u for u in p.update_summaries}

    def _edits(tr_to: str) -> int:
        u = ups_by_date.get(tr_to)
        if u is None:
            return 0
        return u.logic_edits_count + u.constraint_edits_count + u.duration_edits_count

    edits = sorted(_edits(t.to_status_date) for t in trans)
    median_edits = edits[len(edits) // 2] if edits else 0
    has_null = all(t.expected_churn is not None for t in trans) and bool(trans)
    if has_null:
        band = " ".join(f"{x(i):.1f},{y(t.expected_churn or 0.0):.1f}" for i, t in enumerate(trans))
        base = " ".join(f"{x(i):.1f},{bot}" for i in range(len(trans) - 1, -1, -1))
        body.append(f'<polygon points="{band} {base}" fill="{PALETTE["accent"]}" opacity="0.18"/>')
    else:
        body.append(
            f'<text x="{left + 4}" y="{top + 10}" font-size="9" fill="{PALETTE["warn"]}" '
            f"{_FONT}>null model unavailable — expected-churn band not drawn (parked engine "
            "artifact)</text>"
        )
    seg: list[str] = []
    segs: list[list[str]] = [seg]
    for i, t in enumerate(trans):
        if t.crosses_rebaseline and seg:
            seg = []
            segs.append(seg)
        seg.append(f"{x(i):.1f},{y(t.observed_churn):.1f}")
    for s in segs:
        if len(s) >= 2:
            body.append(
                f'<polyline points="{" ".join(s)}" fill="none" stroke="{PALETTE["bad"]}" '
                'stroke-width="1.8" class="churn-seg"/>'
            )
        elif len(s) == 1:
            cx, cy = s[0].split(",")
            body.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{PALETTE["bad"]}"/>')
    for i, t in enumerate(trans):
        te = _edits(t.to_status_date)
        if te > median_edits:
            body.append(
                f'<text x="{x(i):.1f}" y="{y(t.observed_churn) - 6:.1f}" font-size="9" '
                f'text-anchor="middle" fill="{PALETTE["warn"]}" {_FONT}>✎{te}</text>'
            )
        if t.attributable_churn is not None:
            body.append(
                f'<text x="{x(i):.1f}" y="{bot + 12}" font-size="7.5" text-anchor="middle" '
                f'fill="{PALETTE["muted"]}" {_FONT}>+{t.attributable_churn:.2f}</text>'
            )
        if t.crosses_rebaseline:
            body.append(
                f'<line x1="{x(i) - (right - left) / (2 * n):.1f}" y1="{top}" '
                f'x2="{x(i) - (right - left) / (2 * n):.1f}" y2="{bot}" '
                f'stroke="{PALETTE["purple"]}" stroke-dasharray="4 3" class="rebaseline"/>'
            )
        body.append(
            f'<text x="{x(i):.1f}" y="{bot + 24}" font-size="7.5" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(t.to_status_date[5:])}</text>'
        )
    body.append(_footer(p, 250, w))
    return _doc(w, h, f"EX-03 Volatility vs null model (n={len(trans)} transitions)", "".join(body))


def render_ex04_cic_trend(p: ExhibitPayload) -> str:
    """EX-04: CIC per update; a null CIC is a GAP annotated with its reason (never zero,
    never interpolated); a marker where the driving tree was incomplete."""
    ups = p.update_summaries
    w, h = 900, 230 + FOOTER_H
    left, right, top, bot = 46, 892, 30, 190
    n = max(1, len(ups))
    vals = [u.cic for u in ups if u.cic is not None]
    maxv = max([0.1, *vals])

    def x(i: int) -> float:
        return left + (right - left) * ((i + 0.5) / n)

    def y(v: float) -> float:
        return bot - (bot - top) * (v / (maxv * 1.2))

    body = [f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{PALETTE["line"]}"/>']
    seg: list[str] = []
    segs: list[list[str]] = [seg]
    for i, u in enumerate(ups):
        if u.cic is None:
            if seg:
                seg = []
                segs.append(seg)
            body.append(
                f'<text x="{x(i):.1f}" y="{(top + bot) / 2:.1f}" font-size="8" '
                f'text-anchor="middle" fill="{PALETTE["warn"]}" {_FONT} class="cic-gap">'
                f"{_esc(u.cic_null_reason or 'CIC undefined')}</text>"
            )
        else:
            seg.append(f"{x(i):.1f},{y(u.cic):.1f}")
        if u.driving_tree_incomplete:
            body.append(
                f'<text x="{x(i):.1f}" y="{top + 10}" font-size="10" text-anchor="middle" '
                f'fill="{PALETTE["bad"]}" {_FONT}>⚠</text>'
            )
        body.append(
            f'<text x="{x(i):.1f}" y="{bot + 12}" font-size="7.5" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(u.status_date[5:])}</text>'
        )
    for s in segs:
        if len(s) >= 2:
            body.append(
                f'<polyline points="{" ".join(s)}" fill="none" stroke="{PALETTE["accent"]}" '
                'stroke-width="1.8" class="cic-seg"/>'
            )
        elif len(s) == 1:
            cx, cy = s[0].split(",")
            body.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{PALETTE["accent"]}"/>')
    body.append(_footer(p, 230, w))
    return _doc(w, h, "EX-04 CIC trend", "".join(body))


def render_ex05_band_migration(p: ExhibitPayload) -> str:
    """EX-05: stacked share of remaining tasks per total-float band per update (payload bands,
    stacked verbatim — the ≤10-workday band is the NASA-documented near-critical threshold)."""
    dates = _dates(p)
    bands: list[str] = []
    for c in p.cells:
        if c.tf_band not in bands and c.state not in ("COMPLETE", "ABSENT"):
            bands.append(c.tf_band)
    bands.sort()
    counts: dict[str, dict[str, int]] = {d: dict.fromkeys(bands, 0) for d in dates}
    for c in p.cells:
        if c.state in ("COMPLETE", "ABSENT"):
            continue
        if c.status_date in counts and c.tf_band in counts[c.status_date]:
            counts[c.status_date][c.tf_band] += 1
    w, h = 900, 240 + FOOTER_H
    left, top, bot = 46, 30, 200
    colw = (892 - left) / max(1, len(dates))
    colors = [
        PALETTE["bad"],
        PALETTE["warn"],
        PALETTE["accent"],
        PALETTE["ok"],
        PALETTE["muted"],
        PALETTE["purple"],
    ]
    body = []
    for j, d in enumerate(dates):
        total = sum(counts[d].values()) or 1
        y0 = float(bot)
        for bi, b in enumerate(bands):
            frac = counts[d][b] / total
            hh = (bot - top) * frac
            y0 -= hh
            body.append(
                f'<rect x="{left + j * colw + 2:.1f}" y="{y0:.1f}" width="{colw - 4:.1f}" '
                f'height="{hh:.1f}" fill="{colors[bi % len(colors)]}" opacity="0.85" '
                f'data-band="{_esc(b)}"/>'
            )
        body.append(
            f'<text x="{left + j * colw + colw / 2:.1f}" y="{bot + 12}" font-size="7.5" '
            f'text-anchor="middle" fill="{PALETTE["muted"]}" {_FONT}>{_esc(d[5:])}</text>'
        )
    lx = left
    for bi, b in enumerate(bands):
        body.append(
            f'<rect x="{lx}" y="{bot + 20}" width="10" height="9" '
            f'fill="{colors[bi % len(colors)]}"/>'
        )
        body.append(
            f'<text x="{lx + 13}" y="{bot + 28}" font-size="8" fill="{PALETTE["muted"]}" '
            f"{_FONT}>{_esc(b)}</text>"
        )
        lx += 13 + int(6.2 * len(b)) + 14
    body.append(_footer(p, 240, w))
    return _doc(
        w,
        h,
        "EX-05 Float-band migration (share of remaining tasks; ≤10wd band = "
        "NASA near-critical reporting threshold)",
        "".join(body),
    )


def render_ex06_tornado(p: ExhibitPayload) -> str:
    """EX-06: top 15 tasks by weighted instability; the ECI label comes from the payload."""
    ts = [t for t in p.task_summaries if t.weighted_instability is not None]
    ts.sort(key=lambda t: -(t.weighted_instability or 0.0))
    ts = ts[:15]
    w = 900
    rh = 18
    h = 40 + len(ts) * rh + 10 + FOOTER_H
    maxv = max([1e-9, *(t.weighted_instability or 0.0 for t in ts)])
    body = []
    for i, t in enumerate(ts):
        y = 34 + i * rh
        bwid = 560 * ((t.weighted_instability or 0.0) / maxv)
        body.append(
            f'<text x="216" y="{y + 12}" font-size="8" text-anchor="end" '
            f'fill="{PALETTE["ink"]}" {_FONT}>'
            f"{_esc(str(t.task_uid) + ' ' + t.task_name[:30])}</text>"
        )
        body.append(
            f'<rect x="220" y="{y + 3}" width="{bwid:.1f}" height="{rh - 6}" '
            f'fill="{PALETTE["warn"]}"/>'
        )
        body.append(
            f'<text x="{224 + bwid:.1f}" y="{y + 12}" font-size="8" fill="{PALETTE["muted"]}" '
            f"{_FONT}>ECI = {t.eci:.2f}</text>"
        )
    if not ts:
        body.append(
            f'<text x="8" y="40" font-size="9" fill="{PALETTE["warn"]}" {_FONT}>'
            "weighted instability unavailable (parked engine artifact) — no rows</text>"
        )
    body.append(_footer(p, 40 + len(ts) * rh + 10, w))
    return _doc(w, h, "EX-06 Instability tornado (top 15 by weighted instability)", "".join(body))


def render_ex07_edge_vs_task(p: ExhibitPayload) -> str:
    """EX-07: edge-Jaccard vs weighted task Jaccard on ONE 0-1 axis, dash-pattern per series;
    divergence = logic rewired under stable membership."""
    trans = p.transitions
    w, h = 900, 230 + FOOTER_H
    left, right, top, bot = 46, 892, 30, 190
    n = max(1, len(trans))

    def x(i: int) -> float:
        return left + (right - left) * ((i + 0.5) / n)

    def y(v: float) -> float:
        return bot - (bot - top) * v

    body = [f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{PALETTE["line"]}"/>']
    for g in (0.0, 0.5, 1.0):
        body.append(
            f'<text x="{left - 4}" y="{y(g) + 3:.1f}" font-size="8" text-anchor="end" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{g:g}</text>'
        )
    e_pts = " ".join(f"{x(i):.1f},{y(t.edge_jaccard):.1f}" for i, t in enumerate(trans))
    t_pts = " ".join(f"{x(i):.1f},{y(t.weighted_jaccard):.1f}" for i, t in enumerate(trans))
    if len(trans) >= 2:
        body.append(
            f'<polyline points="{e_pts}" fill="none" stroke="{PALETTE["accent"]}" '
            'stroke-width="1.8" class="edge-series"/>'
        )
        body.append(
            f'<polyline points="{t_pts}" fill="none" stroke="{PALETTE["ink"]}" '
            'stroke-width="1.8" stroke-dasharray="5 3" class="task-series"/>'
        )
    for i, t in enumerate(trans):
        body.append(
            f'<text x="{x(i):.1f}" y="{bot + 12}" font-size="7.5" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(t.to_status_date[5:])}</text>'
        )
    body.append(
        f'<text x="{left}" y="{bot + 26}" font-size="8.5" fill="{PALETTE["muted"]}" {_FONT}>'
        "solid = edge Jaccard (driving-tree logic); dashed = weighted task Jaccard "
        "(membership) — solid dropping while dashed holds = logic rewired under stable "
        "membership</text>"
    )
    body.append(_footer(p, 230, w))
    return _doc(w, h, "EX-07 Edge vs task churn (one 0-1 axis)", "".join(body))


def render_ex08_band_matrices(p: ExhibitPayload) -> str:
    """EX-08 (appendix): per-transition band-migration matrices as small multiples."""
    trans = p.transitions
    bands: list[str] = []
    for t in trans:
        for bm in t.band_migrations:
            for b in (bm.from_band, bm.to_band):
                if b not in bands:
                    bands.append(b)
    bands.sort()
    nb = max(1, len(bands))
    cell = 16
    mw = 90 + nb * cell
    per_row = max(1, 880 // mw)
    rows = (len(trans) + per_row - 1) // per_row if trans else 1
    mh = 46 + nb * cell
    w, h = 900, 30 + rows * mh + FOOTER_H
    body = []
    for ti, t in enumerate(trans):
        ox = 8 + (ti % per_row) * mw
        oy = 26 + (ti // per_row) * mh
        body.append(
            f'<text x="{ox}" y="{oy + 10}" font-size="8" fill="{PALETTE["ink"]}" {_FONT}>'
            f"{_esc(t.from_status_date[5:] + ' → ' + t.to_status_date[5:])}</text>"
        )
        counts = {(bm.from_band, bm.to_band): bm.task_count for bm in t.band_migrations}
        maxc = max([1, *counts.values()])
        for r, fb in enumerate(bands):
            for c2, tb in enumerate(bands):
                v = counts.get((fb, tb), 0)
                op = 0.12 + 0.88 * (v / maxc) if v else 0.0
                body.append(
                    f'<rect x="{ox + 60 + c2 * cell}" y="{oy + 16 + r * cell}" '
                    f'width="{cell - 1}" height="{cell - 1}" fill="{PALETTE["accent"]}" '
                    f'opacity="{op:.2f}" stroke="{PALETTE["line"]}" stroke-width="0.3"/>'
                )
                if v:
                    body.append(
                        f'<text x="{ox + 60 + c2 * cell + cell / 2 - 0.5}" '
                        f'y="{oy + 16 + r * cell + 11}" font-size="7" text-anchor="middle" '
                        f'fill="{PALETTE["ink"]}" {_FONT}>{v}</text>'
                    )
        for r, fb in enumerate(bands):
            body.append(
                f'<text x="{ox + 56}" y="{oy + 16 + r * cell + 11}" font-size="6.5" '
                f'text-anchor="end" fill="{PALETTE["muted"]}" {_FONT}>{_esc(fb)}</text>'
            )
    body.append(_footer(p, 30 + rows * mh, w))
    return _doc(w, h, "EX-08 Band transition matrices (appendix)", "".join(body))


def render_ex02_float_heatmap(p: ExhibitPayload) -> str:
    """EX-02: total-float heatmap, diverging around exactly 0 (neutral gray), clipped at the
    5th/95th percentile with over/under glyphs."""
    dates = _dates(p)
    order = _instability_order(p)[:ROW_CAP]
    by = _cells_by(p)
    tfs = sorted(c.total_float_minutes for c in p.cells if c.total_float_minutes is not None)
    if tfs:
        lo = tfs[max(0, int(len(tfs) * 0.05) - 1) if int(len(tfs) * 0.05) else 0]
        hi = tfs[min(len(tfs) - 1, int(len(tfs) * 0.95))]
    else:
        lo, hi = -1, 1
    cw, rh = max(18, min(60, 700 // max(1, len(dates)))), 16
    w = 190 + len(dates) * cw + 16
    h = 46 + len(order) * rh + 24 + FOOTER_H
    body = []
    for j, d in enumerate(dates):
        body.append(
            f'<text x="{190 + j * cw + cw / 2}" y="40" font-size="7.5" text-anchor="middle" '
            f'fill="{PALETTE["muted"]}" {_FONT}>{_esc(d[5:])}</text>'
        )
    for i, uid in enumerate(order):
        y = 46 + i * rh
        name = next((c.task_name for c in p.cells if c.task_uid == uid), str(uid))
        body.append(
            f'<text x="186" y="{y + 11}" font-size="8" text-anchor="end" '
            f'fill="{PALETTE["ink"]}" {_FONT}>{_esc(str(uid) + " " + name[:24])}</text>'
        )
        for j, d in enumerate(dates):
            cell = by.get((uid, d))
            x = 190 + j * cw
            if cell is None or cell.total_float_minutes is None:
                continue
            tf = cell.total_float_minutes
            clipped = "▼" if tf < lo else "▲" if tf > hi else ""
            v = max(lo, min(hi, tf))
            if v < 0:
                op = 0.15 + 0.85 * (v / lo if lo else 0.0)
                fill = PALETTE["bad"]
            elif v > 0:
                op = 0.15 + 0.85 * (v / hi if hi else 0.0)
                fill = PALETTE["ok"]
            else:
                op, fill = 0.5, PALETTE["muted"]
            body.append(
                f'<rect x="{x}" y="{y}" width="{cw - 2}" height="{rh - 2}" fill="{fill}" '
                f'opacity="{op:.2f}" stroke="{PALETTE["line"]}" stroke-width="0.3"/>'
            )
            if clipped:
                body.append(
                    f'<text x="{x + (cw - 2) / 2}" y="{y + 11}" font-size="8" '
                    f'text-anchor="middle" fill="{PALETTE["ink"]}" {_FONT}>{clipped}</text>'
                )
    body.append(
        f'<text x="8" y="{46 + len(order) * rh + 14}" font-size="8" fill="{PALETTE["muted"]}" '
        f"{_FONT}>red = negative float, green = positive, gray = exactly 0; ▲/▼ = "
        f"clipped at the 5th/95th percentile ({lo}-{hi} min)</text>"
    )
    body.append(_footer(p, 46 + len(order) * rh + 24, w))
    return _doc(w, h, "EX-02 Total-float heatmap", "".join(body))


#: exhibit id -> (title-stem, renderer)
EXHIBITS = {
    "EX-00": ("provenance_rail", render_ex00_provenance),
    "EX-01": ("state_barcode", render_ex01_barcode),
    "EX-02": ("float_heatmap", render_ex02_float_heatmap),
    "EX-03": ("volatility_vs_null", render_ex03_volatility_vs_null),
    "EX-04": ("cic_trend", render_ex04_cic_trend),
    "EX-05": ("band_migration", render_ex05_band_migration),
    "EX-06": ("instability_tornado", render_ex06_tornado),
    "EX-07": ("edge_vs_task_churn", render_ex07_edge_vs_task),
    "EX-08": ("band_matrices", render_ex08_band_matrices),
}
