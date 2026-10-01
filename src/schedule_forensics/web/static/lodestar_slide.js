// lodestar_slide.js — LODESTAR 2.0's slide painter (ADR-0543, the "Console" design handoff).
//
// Paints the layout the SERVER computed (reports/onepager.py, reports/onepager_compare.py —
// the same geometry the PowerPoint export draws) as one SVG in the slide's own 960 × 540-point
// coordinates. Nothing here computes geometry: every x, y, size and route arrives in the layout;
// this file only chooses the paint, in the design's z-order —
//   lanes and grid → logic-link SHAFTS → items (bars, diamonds, ghosts, badges, haloed names)
//   → arrowheads and type tags → the data-date line → the legend → pick rings and the drag lead
// — so a link passes BEHIND every bar and name it crosses and its head stays on top. Every colour
// is a token (lodestar_tokens.css), so the four views restyle the slide.
//
// It also draws the overlays the studio drives (the FROM / TO pick rings, the hover ring, a
// demo's pulsing ring, the drag lead) and moves the red line for the data-date scrubber while it
// is dragged — the one position computed here, and only as feedback until the server's own layout
// for the new date arrives (lodestar_studio.js asks /api/preview).
//
// Strict CSP (script-src 'self'): no inline script and no inline handlers anywhere.
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var PAL = [3, 1, 2, 5, 4, 6]; // swimlane i → --viz-PAL[i mod 6] (the design's order)

  function el(tag, attrs, text) {
    var n = document.createElementNS(NS, tag);
    if (attrs) for (var k in attrs) if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    if (text !== null && text !== undefined) n.textContent = text;
    return n;
  }
  function pts(a) { return a.map(function (p) { return p[0] + "," + p[1]; }).join(" "); }
  function diamond(x, y, h) { return x + "," + (y - h) + " " + (x + h) + "," + y + " " + x + "," + (y + h) + " " + (x - h) + "," + y; }
  function laneColor(L, laneIdx) {
    var ln = L.lanes[laneIdx], i = ln && typeof ln.index === "number" ? ln.index : laneIdx;
    return "var(--viz-" + PAL[((i % 6) + 6) % 6] + ")";
  }
  function slug(s) { return String(s || "").replace(/ /g, "-"); }

  // ── item extents (what the hit area, the rings and the router's crossings all read) ──
  function shapeX(L, p) {
    if (p.x0 === null || p.x0 === undefined) return null;
    if (p.milestone) { var h = (p.ms || L.ms) / 2; return [p.x0 - h, p.x0 + h]; }
    return [p.x0, p.x1];
  }
  function ghostX(L, p) {
    if (p.ghost_x0 === null || p.ghost_x0 === undefined) return null;
    if (p.ghost_milestone) { var h = (p.ghost_ms || L.ms) / 2; return [p.ghost_x0 - h, p.ghost_x0 + h]; }
    return [p.ghost_x0, p.ghost_x1];
  }
  function labelX(p) {
    var x = p.label_x, w = p.label_w || 0;
    if (p.label_anchor === "end" && p.badge) x = p.label_x - (p.badge_w || 0) - 2;
    return p.label_anchor === "end" ? [x - w, x] : [x, x + w];
  }
  function extent(L, p) {
    var xs = [], s = shapeX(L, p), g = ghostX(L, p), lab = labelX(p);
    if (s) xs.push(s[0], s[1]);
    if (g) xs.push(g[0], g[1]);
    if (p.arrow_x0 !== null && p.arrow_x0 !== undefined) xs.push(p.arrow_x0, p.arrow_x1);
    xs.push(lab[0], lab[1]);
    if (p.badge) xs.push(p.badge_x, p.badge_x + p.badge_w);
    if (p.done && p.done_x !== null && p.done_x !== undefined) xs.push(p.done_x - p.done_r, p.done_x + p.done_r);
    return [Math.min.apply(null, xs), Math.max.apply(null, xs)];
  }

  function doneBadge(parent, cx, cy, r) {
    parent.appendChild(el("circle", { cx: cx, cy: cy, r: r, class: "lss-done" }));
    parent.appendChild(el("polyline", {
      points: (cx - 0.5 * r) + "," + (cy + 0.02 * r) + " " + (cx - 0.12 * r) + "," + (cy + 0.42 * r) + " " + (cx + 0.55 * r) + "," + (cy - 0.4 * r),
      class: "lss-done-check", "stroke-width": Math.max(0.35, r * 0.32),
    }));
  }
  function moveArrow(parent, x0, x1, y, head, slip) {
    var d = x1 >= x0 ? 1 : -1, c = slip ? " is-slip" : " is-pull";
    parent.appendChild(el("line", { x1: x0, y1: y, x2: x1, y2: y, class: "lss-move" + c }));
    parent.appendChild(el("polygon", {
      points: x1 + "," + y + " " + (x1 - d * head) + "," + (y - head * 0.5) + " " + (x1 - d * head) + "," + (y + head * 0.5),
      class: "lss-movehead" + c,
    }));
  }
  function span(s, f) { return s === f ? f : s + " → " + f; }
  function tip(L, p) {
    if (p.status === undefined) {
      return p.name + (p.milestone ? " — " + p.finish : " — " + p.start + " → " + p.finish) +
        (p.done ? " · complete" + (L.status_label ? " (" + L.status_label + ")" : "") : "");
    }
    var parts = [p.name];
    if (p.current_start && p.prior_start === p.current_start && p.prior_finish === p.current_finish) parts.push(span(p.current_start, p.current_finish));
    else {
      if (p.prior_start) parts.push("prior " + span(p.prior_start, p.prior_finish));
      if (p.current_start) parts.push("current " + span(p.current_start, p.current_finish));
    }
    if (p.finish_delta_days) parts.push("finish " + (p.finish_delta_days >= 0 ? "+" : "−") + Math.abs(p.finish_delta_days) + " cal d");
    if (p.start_delta_days) parts.push("start " + (p.start_delta_days >= 0 ? "+" : "−") + Math.abs(p.start_delta_days) + " cal d");
    parts.push(p.status);
    if (p.done) parts.push("complete (" + (L.status_label || "status column") + ")");
    return parts.join(" · ");
  }

  // ── the data-date marker: a dashed red line, a downward triangle at its top, its caption ──
  function dataDate(layer, L, x, label, labelX, anchor) {
    var g = el("g", { class: "lss-dd", "data-ls-dd": "1" });
    g.appendChild(el("line", { x1: x, y1: L.year_y0, x2: x, y2: L.lanes_y1 }));
    g.appendChild(el("polygon", { points: (x - 3) + "," + L.year_y0 + " " + (x + 3) + "," + L.year_y0 + " " + x + "," + (L.year_y0 + 4) }));
    g.appendChild(el("text", { x: labelX, y: L.today_label_y, "text-anchor": anchor }, label));
    g.appendChild(el("title", {}, "DATA DATE " + L.today_iso));
    layer.appendChild(g);
    return g;
  }

  // ── the legend ──
  function legend(svg, L, right) {
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.legend_y0, x2: right, y2: L.legend_y0, class: "lss-rule" }));
    (L.legend || []).forEach(function (e) {
      var g = el("g", { class: "lss-legend", "data-kind": e.kind }), cy = e.y - 2.5;
      if (e.kind === "activity") g.appendChild(el("rect", { x: e.x, y: cy - 2.5, width: 10, height: 5, rx: 1, class: "lss-legend-sym" }));
      else if (e.kind === "milestone") g.appendChild(el("polygon", { points: diamond(e.x + 5, cy, 3.5), class: "lss-legend-sym" }));
      else if (e.kind === "done") doneBadge(g, e.x + 5, cy, 3);
      else if (e.kind === "today") g.appendChild(el("line", { x1: e.x + 5, y1: cy - 4, x2: e.x + 5, y2: cy + 4, class: "lss-legend-dd" }));
      else if (e.kind === "ghost" || e.kind === "removed") g.appendChild(el("rect", { x: e.x, y: cy - 2.5, width: 10, height: 5, rx: 1, class: "lss-legend-ghost" }));
      else if (e.kind === "slip") moveArrow(g, e.x, e.x + 10, cy, 2.4, true);
      else if (e.kind === "pull") moveArrow(g, e.x + 10, e.x, cy, 2.4, false);
      else if (e.kind === "new") g.appendChild(el("text", { x: e.x, y: cy + 2, class: "lss-legend-new" }, "NEW"));
      else if (e.kind === "link") {
        g.appendChild(el("line", { x1: e.x, y1: cy, x2: e.x + 7.4, y2: cy, class: "lss-legend-linkline" }));
        g.appendChild(el("polygon", { points: (e.x + 10) + "," + cy + " " + (e.x + 7.4) + "," + (cy - 1.3) + " " + (e.x + 7.4) + "," + (cy + 1.3), class: "lss-head" }));
      } else {
        g.appendChild(el("rect", { x: e.x, y: cy - 3, width: 10, height: 6, rx: 1, fill: "var(--viz-" + PAL[((e.color % 6) + 6) % 6] + ")" }));
      }
      g.appendChild(el("text", { x: e.x + 13, y: e.y, class: "lss-legend-text", "font-size": L.legend_pt }, e.label));
      svg.appendChild(g);
    });
  }

  // ── the whole slide ──
  function paint(host, L, opts) {
    opts = opts || {};
    var linkable = opts.linkable || null; // {key: true} — what a pick or a drag may join
    var compare = !!L.summaries;
    var right = L.summary_x1 || L.x1;
    var svg = el("svg", {
      viewBox: "0 0 " + L.w + " " + L.h, class: "lss" + (opts.reveal ? " is-reveal" : ""),
      role: "img", "aria-label": L.title, "data-ls-slide": "1", preserveAspectRatio: "xMidYMid meet",
    });
    svg.appendChild(el("rect", { x: 0, y: 0, width: L.w, height: L.h, class: "lss-bg" }));
    svg.appendChild(el("text", { x: L.lane_col_x0, y: L.title_y, class: "lss-title" }, L.title));
    if (L.subtitle) svg.appendChild(el("text", { x: L.lane_col_x0, y: L.sub_y, class: "lss-sub" }, L.subtitle));
    // ── the timescale: year bands and labels, the dotted month grid, the header rule ──
    L.years.forEach(function (b) {
      svg.appendChild(el("rect", { x: b.x0, y: L.year_y0, width: Math.max(0, b.x1 - b.x0), height: L.lanes_y1 - L.year_y0, class: "lss-year" + (b.shade ? " is-shade" : "") }));
      svg.appendChild(el("line", { x1: b.x0, y1: L.year_y0, x2: b.x0, y2: L.lanes_y1, class: "lss-year-line" }));
      if (b.x1 - b.x0 > 18) svg.appendChild(el("text", { x: (b.x0 + b.x1) / 2, y: L.year_y0 + 8.5, "text-anchor": "middle", class: "lss-year-label" }, b.label));
    });
    svg.appendChild(el("line", { x1: L.x1, y1: L.year_y0, x2: L.x1, y2: L.lanes_y1, class: "lss-year-line" }));
    L.months.forEach(function (m) {
      svg.appendChild(el("line", { x1: m.x, y1: L.year_y1, x2: m.x, y2: L.lanes_y1, class: "lss-month-line" }));
      if (m.label) svg.appendChild(el("text", { x: m.label_x, y: L.mon_y1 - 3.5, "text-anchor": "middle", class: "lss-month-label", "font-size": L.month_pt }, m.label));
    });
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.mon_y1, x2: right, y2: L.mon_y1, class: "lss-rule" }));
    if (compare) svg.appendChild(el("text", { x: L.summary_x0 + 2, y: L.mon_y1 - 3.5, class: "lss-sum-head" }, "CHANGE SUMMARY"));
    // ── the swimlanes: band, name block, edge, divider, name ──
    L.lanes.forEach(function (ln, i) {
      var c = laneColor(L, i), lh = ln.name_pt * 1.2, top = (ln.y0 + ln.y1) / 2 - (ln.lines.length - 1) * lh / 2;
      var g = el("g", { class: "lss-lane", style: "--d:" + (i * 70) + "ms" });
      g.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: L.x1 - L.lane_col_x0, height: ln.y1 - ln.y0, fill: c, class: "lss-band" }));
      g.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: L.lane_col_x1 - L.lane_col_x0, height: ln.y1 - ln.y0, fill: c, class: "lss-namebg" }));
      g.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: 3, height: ln.y1 - ln.y0, fill: c }));
      g.appendChild(el("line", { x1: L.lane_col_x0, y1: ln.y1, x2: right, y2: ln.y1, class: "lss-lane-line" }));
      ln.lines.forEach(function (line, j) {
        g.appendChild(el("text", { x: L.lane_col_x0 + 7, y: top + j * lh + ln.name_pt * 0.35, class: "lss-lane-name", "font-size": ln.name_pt }, line));
      });
      svg.appendChild(g);
    });
    (L.summaries || []).forEach(function (s) {
      var g = el("g", { class: "lss-summary" }), lh = s.pt * 1.25, top = (s.y0 + s.y1) / 2 - (s.lines.length - 1) * lh / 2;
      g.appendChild(el("rect", { x: s.x0, y: s.y0, width: s.x1 - s.x0, height: s.y1 - s.y0, rx: 1, fill: laneColor(L, s.lane), class: "lss-sum-bg" }));
      s.lines.forEach(function (line, j) {
        g.appendChild(el("text", { x: s.x0 + 2.5, y: top + j * lh + s.pt * 0.35, class: "lss-sum-text", "font-size": s.pt }, line));
      });
      svg.appendChild(g);
    });
    // ── the logic links' SHAFTS — under every item ──
    var shafts = el("g", { class: "lss-shafts", "aria-hidden": "true" });
    (L.links || []).forEach(function (ln) {
      var len = 0;
      for (var i = 1; i < ln.shaft.length; i++) len += Math.abs(ln.shaft[i][0] - ln.shaft[i - 1][0]) + Math.abs(ln.shaft[i][1] - ln.shaft[i - 1][1]);
      shafts.appendChild(el("polyline", {
        points: pts(ln.shaft), class: "lss-shaft", style: "--len:" + len.toFixed(2),
        "data-pred": ln.pred, "data-succ": ln.succ, "data-kind": ln.kind,
      }));
    });
    svg.appendChild(shafts);
    // ── the items ──
    var items = el("g", { class: "lss-items" }), index = {};
    var barH = L.bar_h, rowH = L.row_h || 10;
    L.items.forEach(function (p) {
      var c = laneColor(L, p.lane), key = p.key || "", hot = !!(key && (!linkable || linkable[key]));
      var g = el("g", {
        class: "lss-item" + (hot ? " is-hot" : "") + (p.status ? " is-st-row-" + slug(p.status) : ""),
        "data-key": key || null, "data-status": p.status || null,
      });
      g.appendChild(el("title", {}, tip(L, p)));
      var ext = extent(L, p);
      g.appendChild(el("rect", { x: ext[0] - 1, y: p.y - rowH / 2 + 0.5, width: ext[1] - ext[0] + 2, height: Math.max(1, rowH - 1), class: "lss-hit" }));
      var gx = ghostX(L, p);
      if (gx) {
        if (p.ghost_milestone) g.appendChild(el("polygon", { points: diamond(p.ghost_x0, p.y, (p.ghost_ms || L.ms) / 2), stroke: c, class: "lss-ghost" }));
        else g.appendChild(el("rect", { x: p.ghost_x0, y: p.y - barH / 2, width: Math.max(0, p.ghost_x1 - p.ghost_x0), height: barH, rx: 1.2, stroke: c, class: "lss-ghost" }));
      }
      if (p.arrow_x0 !== null && p.arrow_x0 !== undefined) moveArrow(g, p.arrow_x0, p.arrow_x1, p.arrow_y, L.arrow_head, p.status === "slipped");
      if (p.x0 !== null && p.x0 !== undefined) {
        var origin = "transform-origin:" + p.x0 + "px " + p.y + "px;--d:" + (p.lane * 70 + 60) + "ms";
        if (p.milestone) g.appendChild(el("polygon", { points: diamond(p.x0, p.y, (p.ms || L.ms) / 2), fill: c, class: "lss-glyph", style: origin }));
        else g.appendChild(el("rect", { x: p.x0, y: p.y - barH / 2, width: Math.max(0, p.x1 - p.x0), height: barH, rx: 1.2, fill: c, class: "lss-glyph", style: origin }));
      }
      if (p.done && p.done_x !== null && p.done_x !== undefined) doneBadge(g, p.done_x, p.y, p.done_r);
      var tx = (p.label_anchor === "end" && p.badge) ? p.label_x - p.badge_w - 2 : p.label_x;
      var t = el("text", {
        x: tx, y: p.y + L.label_pt * 0.35, "text-anchor": p.label_anchor, "font-size": L.label_pt,
        class: "lss-label" + (p.inside ? " is-in" : ""), "stroke-width": p.inside ? null : (0.42 * L.label_pt).toFixed(3),
      }, p.label);
      if (p.delta) t.appendChild(el("tspan", { class: "lss-delta is-st-" + slug(p.status) }, " " + p.delta));
      g.appendChild(t);
      if (p.badge) {
        g.appendChild(el("rect", { x: p.badge_x, y: p.y - L.label_pt * 0.6, width: p.badge_w, height: L.label_pt * 1.2, rx: 1, class: "lss-badge-bg is-st-" + slug(p.status) }));
        g.appendChild(el("text", { x: p.badge_x + 1.6, y: p.y + L.label_pt * 0.35, class: "lss-badge is-st-" + slug(p.status), "font-size": L.label_pt, "stroke-width": (0.42 * L.label_pt).toFixed(3) }, p.badge));
      }
      items.appendChild(g);
      if (key) index[key] = { p: p, g: g, label: t };
    });
    svg.appendChild(items);
    // ── the heads and the type tags — over the items ──
    var heads = el("g", { class: "lss-heads", "aria-hidden": "true" });
    (L.links || []).forEach(function (ln) {
      var g = el("g", { class: "lss-link-head", "data-pred": ln.pred, "data-succ": ln.succ, "data-kind": ln.kind });
      g.appendChild(el("title", {}, ln.pred_name + " → " + ln.succ_name + " (" + ln.kind + ")"));
      g.appendChild(el("polygon", { points: pts(ln.head), class: "lss-head" }));
      if (ln.tag) g.appendChild(el("text", { x: ln.tag_x, y: ln.tag_y, "text-anchor": ln.tag_anchor || "start", class: "lss-tag" }, ln.tag));
      heads.appendChild(g);
    });
    svg.appendChild(heads);
    // ── the data date (its own layer, so the scrubber can redraw it in place) ──
    var ddLayer = el("g", { class: "lss-dd-layer" });
    svg.appendChild(ddLayer);
    if (L.today_x !== null && L.today_x !== undefined) dataDate(ddLayer, L, L.today_x, L.today_label, L.today_label_x, L.today_label_anchor);
    // ── the legend ──
    legend(svg, L, right);
    // ── the overlays: rings (picks, hover, demo) and the drag lead — never printed ──
    var rings = el("g", { class: "lss-rings", "data-noprint": "1" });
    var lead = el("g", { class: "lss-drag", "data-noprint": "1" });
    svg.appendChild(rings);
    svg.appendChild(lead);
    host.textContent = "";
    host.appendChild(svg);
    // a name the face draws wider than the layout reserved is held to its reserved width, so the
    // server's geometry — what the router and the PowerPoint read — stays the truth
    fitLabels(index);
    return { svg: svg, L: L, index: index, rings: rings, lead: lead, dd: ddLayer };
  }

  function fitLabels(index) {
    Object.keys(index).forEach(function (k) {
      var it = index[k], t = it.label, w = it.p.label_w;
      if (!w || it.p.inside || !t.getComputedTextLength) return;
      try {
        var have = t.getComputedTextLength();
        if (have > w * 1.02) { t.setAttribute("textLength", w.toFixed(2)); t.setAttribute("lengthAdjust", "spacingAndGlyphs"); }
      } catch (e) { /* not laid out (hidden): leave it */ }
    });
  }

  // ── overlays the studio drives ──
  function ringBox(ctx, p) {
    var L = ctx.L, s = shapeX(L, p) || ghostX(L, p) || [p.label_x, p.label_x], hh = Math.max(L.bar_h, L.ms) / 2, pad = 1.8;
    return { x: s[0] - pad, y: p.y - hh - pad, w: s[1] - s[0] + 2 * pad, h: 2 * hh + 2 * pad };
  }
  function ring(ctx, key, cls, tag) {
    var it = ctx.index[key];
    if (!it) return;
    var b = ringBox(ctx, it.p);
    ctx.rings.appendChild(el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 1.5, class: "lss-ring " + cls }));
    if (tag) ctx.rings.appendChild(el("text", { x: b.x, y: b.y - 1.2, class: "lss-ring-tag " + cls }, tag));
  }
  function setRings(ctx, o) {
    if (!ctx) return;
    while (ctx.rings.firstChild) ctx.rings.removeChild(ctx.rings.firstChild);
    o = o || {};
    if (o.from) ring(ctx, o.from, "is-from", "FROM");
    if (o.to) ring(ctx, o.to, "is-to", "TO");
    if (o.hover && o.hover !== o.from && o.hover !== o.to) ring(ctx, o.hover, "is-hover", null);
    (o.demo || []).forEach(function (k) { ring(ctx, k, "is-demo", o.demoTag || null); });
  }
  function setLead(ctx, d) {
    if (!ctx) return;
    while (ctx.lead.firstChild) ctx.lead.removeChild(ctx.lead.firstChild);
    if (!d || d.x === null || d.x === undefined) return;
    var it = ctx.index[d.from];
    if (!it) return;
    var s = shapeX(ctx.L, it.p) || [it.p.label_x, it.p.label_x];
    ctx.lead.appendChild(el("line", { x1: s[1], y1: it.p.y, x2: d.x, y2: d.y }));
    ctx.lead.appendChild(el("circle", { cx: d.x, cy: d.y, r: 2.4 }));
    ctx.lead.appendChild(el("text", { x: d.x + 4, y: d.y - 3 }, d.over ? "release to link (" + (d.kind || "FS") + ")" : "drop on the successor"));
  }
  function point(svg, ev) {
    if (!svg || !svg.createSVGPoint) return null;
    var pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    var m = svg.getScreenCTM();
    if (!m) return null;
    var loc = pt.matrixTransform(m.inverse());
    return { x: loc.x, y: loc.y };
  }
  // the scrubber's feedback: the red line at ``iso`` on THIS layout's timescale, until the
  // server's layout for that date arrives (a date can re-lay the slide when no window is set)
  function days(a, b) {
    var p = a.split("-"), q = b.split("-");
    return (Date.UTC(+q[0], +q[1] - 1, +q[2]) - Date.UTC(+p[0], +p[1] - 1, +p[2])) / 86400000;
  }
  function mdy(iso) { var p = iso.split("-"); return (+p[1]) + "/" + (+p[2]) + "/" + p[0].slice(2); }
  function moveDataDate(ctx, iso) {
    if (!ctx) return;
    var L = ctx.L, total = days(L.t0, L.t1), off = days(L.t0, iso);
    while (ctx.dd.firstChild) ctx.dd.removeChild(ctx.dd.firstChild);
    if (!(total > 0) || off < 0 || off >= total) return;
    var x = L.x0 + off / total * (L.x1 - L.x0), anchor = x > L.x1 - 110 ? "end" : "start";
    dataDate(ctx.dd, L, x, "DATA DATE " + mdy(iso), x + (anchor === "end" ? -3 : 3), anchor);
  }

  window.LSSlide = {
    paint: paint, setRings: setRings, setLead: setLead, point: point, moveDataDate: moveDataDate,
    days: days, mdy: mdy, extent: extent,
  };
})();
