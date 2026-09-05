// onepager_compare.js — paints the One-Pager COMPARE slide the server laid out
// (reports/onepager_compare.py) as ONE SVG in the same logical coordinates the .pptx export uses
// (960 x 540 points, 16:9). The ADR-0446 one-pager language plus the delta encoding: the CURRENT
// position solid, the PRIOR as a dashed ghost, an arrow from the old finish to the new one with the
// move in calendar days, NEW / REMOVED / DUPLICATE NAME tags, and a per-swimlane summary column.
// Geometry is never computed here — only painted — so the page is an honest preview of the slide.
//
// Strict CSP (script-src 'self'): the layout arrives in a non-executable JSON block (#opcData).
// The data-date marker is the tool-wide SFGantt.dataDateLine (ADR-0342; here the data date is
// TODAY) and the axis captions go through SFChartFrame.axisTitles (ADR-0298).
//
// Intake: TWO slots — PRIOR and CURRENT — each its own form. A drop lands on the slot it was
// dropped on; a drop anywhere else is refused with a hint, because which list is the prior one is
// the operator's choice and the page never guesses it from a file name or a drop position.
(function () {
  "use strict";
  var SVG = "http://www.w3.org/2000/svg";
  function el(tag, attrs, text) {
    var n = document.createElementNS(SVG, tag);
    for (var k in attrs) if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    if (text !== null && text !== undefined) n.textContent = text;
    return n;
  }
  function laneVar(i) { return "var(--lane-" + ((i % 10) + 1) + ")"; }
  function slug(status) { return status.replace(/ /g, "-"); }
  function diamondPoints(x, y, h) {
    return x + "," + (y - h) + " " + (x + h) + "," + y + " " + x + "," + (y + h) + " " + (x - h) + "," + y;
  }
  // an arrow along y from x0 to x1: a line plus a solid head at x1 pointing the way it moved
  function arrow(parent, x0, x1, y, head, cls) {
    var d = x1 >= x0 ? 1 : -1;
    parent.appendChild(el("line", { x1: x0, y1: y, x2: x1, y2: y, class: "opc-arrow " + cls }));
    parent.appendChild(el("polygon", {
      points: x1 + "," + y + " " + (x1 - d * head) + "," + (y - head * 0.5) + " " + (x1 - d * head) + "," + (y + head * 0.5),
      class: "opc-arrow-head opc-arrow-head-" + cls.replace("opc-arrow-", ""),
    }));
  }
  function tip(p) {
    var parts = [p.name];
    if (p.prior_start) parts.push("prior " + (p.prior_start === p.prior_finish ? p.prior_finish : p.prior_start + " → " + p.prior_finish));
    if (p.current_start) parts.push("current " + (p.current_start === p.current_finish ? p.current_finish : p.current_start + " → " + p.current_finish));
    if (p.finish_delta_days !== null && p.finish_delta_days !== undefined) parts.push("finish " + (p.finish_delta_days >= 0 ? "+" : "−") + Math.abs(p.finish_delta_days) + " cal d");
    if (p.start_delta_days) parts.push("start " + (p.start_delta_days >= 0 ? "+" : "−") + Math.abs(p.start_delta_days) + " cal d");
    parts.push(p.status);
    return parts.join(" · ");
  }

  function paint(host, L) {
    var svg = el("svg", { viewBox: "0 0 " + L.w + " " + L.h, class: "op-svg opc-svg", role: "img", "aria-label": L.title });
    svg.appendChild(el("rect", { x: 0, y: 0, width: L.w, height: L.h, class: "op-bg" }));
    svg.appendChild(el("text", { x: L.lane_col_x0, y: L.title_y, class: "op-title" }, L.title));
    if (L.subtitle) svg.appendChild(el("text", { x: L.lane_col_x0, y: L.sub_y, class: "op-sub" }, L.subtitle));
    // ── header: year bands, month grid ──
    L.years.forEach(function (b) {
      svg.appendChild(el("rect", { x: b.x0, y: L.year_y0, width: b.x1 - b.x0, height: L.lanes_y1 - L.year_y0, class: "op-year op-year-" + b.shade }));
      svg.appendChild(el("line", { x1: b.x0, y1: L.year_y0, x2: b.x0, y2: L.lanes_y1, class: "op-year-line" }));
      if (b.x1 - b.x0 > 18) svg.appendChild(el("text", { x: (b.x0 + b.x1) / 2, y: L.year_y0 + 9, "text-anchor": "middle", class: "op-year-label" }, b.label));
    });
    svg.appendChild(el("line", { x1: L.x1, y1: L.year_y0, x2: L.x1, y2: L.lanes_y1, class: "op-year-line" }));
    L.months.forEach(function (m) {
      svg.appendChild(el("line", { x1: m.x, y1: L.year_y1, x2: m.x, y2: L.lanes_y1, class: "op-month-line" }));
      if (m.label) svg.appendChild(el("text", { x: m.label_x, y: L.mon_y1 - 3.5, "text-anchor": "middle", class: "op-month-label", style: "font-size:" + L.month_pt + "px" }, m.label));
    });
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.mon_y1, x2: L.summary_x1, y2: L.mon_y1, class: "op-header-line" }));
    svg.appendChild(el("text", { x: L.summary_x0 + 2, y: L.mon_y1 - 3.5, class: "op-month-label opc-sum-head", style: "font-size:5.5px" }, "CHANGE SUMMARY"));
    // ── swimlanes: band, name block, summary box ──
    L.lanes.forEach(function (ln) {
      var fill = laneVar(ln.color);
      svg.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: L.x1 - L.lane_col_x0, height: ln.y1 - ln.y0, fill: fill, class: "op-lane-band" }));
      svg.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: L.lane_col_x1 - L.lane_col_x0, height: ln.y1 - ln.y0, fill: fill, class: "op-lane-name-bg" }));
      svg.appendChild(el("rect", { x: L.lane_col_x0, y: ln.y0, width: 3, height: ln.y1 - ln.y0, fill: fill, class: "op-lane-edge" }));
      var lh = ln.name_pt * 1.2, top = (ln.y0 + ln.y1) / 2 - (ln.lines.length - 1) * lh / 2;
      ln.lines.forEach(function (line, i) {
        svg.appendChild(el("text", { x: L.lane_col_x0 + 7, y: top + i * lh + ln.name_pt * 0.35, class: "op-lane-name", style: "font-size:" + ln.name_pt + "px" }, line));
      });
    });
    L.summaries.forEach(function (s) {
      var fill = laneVar(L.lanes[s.lane].color), g = el("g", { class: "opc-summary" });
      g.appendChild(el("rect", { x: s.x0, y: s.y0, width: s.x1 - s.x0, height: s.y1 - s.y0, fill: fill, class: "opc-sum-bg" }));
      var lh = s.pt * 1.25, top = (s.y0 + s.y1) / 2 - (s.lines.length - 1) * lh / 2;
      s.lines.forEach(function (line, i) {
        g.appendChild(el("text", { x: s.x0 + 2.5, y: top + i * lh + s.pt * 0.35, class: "opc-sum-text", style: "font-size:" + s.pt + "px" }, line));
      });
      svg.appendChild(g);
    });
    // ── items: ghost, arrow, current shape, label with its delta, tag ──
    var barH = L.bar_h, ms = L.ms;
    L.items.forEach(function (p) {
      var fill = laneVar(L.lanes[p.lane].color), st = slug(p.status);
      var g = el("g", { class: "opc-item opc-" + st + (p.milestone ? " op-ms" : " op-act"), "data-status": p.status });
      g.appendChild(el("title", {}, tip(p)));
      if (p.ghost_x0 !== null) {
        if (p.ghost_milestone) g.appendChild(el("polygon", { points: diamondPoints(p.ghost_x0, p.y, ms / 2), stroke: fill, class: "opc-ghost opc-ghost-ms" }));
        else g.appendChild(el("rect", { x: p.ghost_x0, y: p.y - barH / 2, width: p.ghost_x1 - p.ghost_x0, height: barH, rx: 1.2, stroke: fill, class: "opc-ghost" }));
      }
      if (p.arrow_x0 !== null) arrow(g, p.arrow_x0, p.arrow_x1, p.arrow_y, L.arrow_head, p.status === "slipped" ? "opc-arrow-slip" : "opc-arrow-pull");
      if (p.x0 !== null) {
        if (p.milestone) g.appendChild(el("polygon", { points: diamondPoints(p.x0, p.y, ms / 2), fill: fill, class: "op-diamond" }));
        else g.appendChild(el("rect", { x: p.x0, y: p.y - barH / 2, width: p.x1 - p.x0, height: barH, rx: 1.2, fill: fill, class: "op-bar" }));
      }
      var tx = (p.label_anchor === "end" && p.badge) ? p.label_x - p.badge_w - 2 : p.label_x;
      var t = el("text", { x: tx, y: p.y + L.label_pt * 0.35, "text-anchor": p.label_anchor, class: "op-label" + (p.inside ? " op-label-in" : ""), style: "font-size:" + L.label_pt + "px" }, p.label);
      if (p.delta) t.appendChild(el("tspan", { class: "opc-delta opc-delta-" + st }, " " + p.delta));
      g.appendChild(t);
      if (p.badge) {
        g.appendChild(el("rect", { x: p.badge_x, y: p.y - L.label_pt * 0.6, width: p.badge_w, height: L.label_pt * 1.2, rx: 1, class: "opc-badge opc-badge-" + st }));
        g.appendChild(el("text", { x: p.badge_x + 1.6, y: p.y + L.label_pt * 0.35, class: "opc-badge-text", style: "font-size:" + L.label_pt + "px" }, p.badge));
      }
      svg.appendChild(g);
    });
    // ── today: the tool-wide DD marker, plus the one-pager's own dated caption ──
    if (L.today_x !== null && window.SFGantt && SFGantt.dataDateLine) {
      SFGantt.dataDateLine(svg, { x: L.today_x, top: L.year_y0, bottom: L.lanes_y1, iso: L.today_iso });
      svg.appendChild(el("text", { x: L.today_label_x, y: L.today_label_y, "text-anchor": L.today_label_anchor, class: "op-today" }, L.today_label));
    }
    // ── legend: the encoding first, then one chip per swimlane ──
    L.legend.forEach(function (e) {
      var g = el("g", { class: "op-legend-item opc-legend-" + e.kind }), cy = e.y - 2.5;
      if (e.kind === "activity") g.appendChild(el("rect", { x: e.x, y: cy - 2.5, width: 10, height: 5, rx: 1, class: "op-legend-bar" }));
      else if (e.kind === "ghost" || e.kind === "removed") g.appendChild(el("rect", { x: e.x, y: cy - 2.5, width: 10, height: 5, rx: 1, class: "opc-legend-ghost" }));
      else if (e.kind === "slip") arrow(g, e.x, e.x + 10, cy, 2.2, "opc-arrow-slip");
      else if (e.kind === "pull") arrow(g, e.x + 10, e.x, cy, 2.2, "opc-arrow-pull");
      else if (e.kind === "new") g.appendChild(el("rect", { x: e.x, y: cy - 3, width: 10, height: 6, rx: 1, class: "opc-badge opc-badge-new" }));
      else if (e.kind === "today") g.appendChild(el("line", { x1: e.x + 5, y1: cy - 4, x2: e.x + 5, y2: cy + 4, class: "op-legend-today" }));
      else g.appendChild(el("rect", { x: e.x, y: cy - 3, width: 10, height: 6, rx: 1, fill: laneVar(e.color), class: "op-legend-lane" }));
      g.appendChild(el("text", { x: e.x + 13, y: e.y, class: "op-legend-text", style: "font-size:" + L.legend_pt + "px" }, e.label));
      svg.appendChild(g);
    });
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.legend_y0, x2: L.summary_x1, y2: L.legend_y0, class: "op-header-line" }));
    if (window.SFChartFrame && SFChartFrame.axisTitles) {
      SFChartFrame.axisTitles(svg, {
        L: L.lane_col_x0 - 4, R: L.x1, T: L.lanes_y0 - 12, B: L.legend_y0 - 1,
      }, {
        xLabel: "Timeline by month and year (prior as ghost, current solid)", yLabel: "Swimlane",
      });
    }
    host.textContent = "";
    host.appendChild(svg);
    return svg;
  }

  function boot() {
    var host = document.getElementById("opcHost"), data = document.getElementById("opcData");
    if (!host || !data) return;
    var L;
    try { L = JSON.parse(data.textContent || "null"); } catch (e) { L = null; }
    if (!L) return;
    paint(host, L);
  }
  // ── intake: two slots, each the home.js idiom (a dropped workbook is handed to the SAME form the
  // picker submits, so there is one upload path per slot and it works without fetch) ──
  function intake() {
    var hint = document.getElementById("opcHint");
    var slots = ["Prior", "Current"].map(function (k) {
      return {
        form: document.getElementById("opcForm" + k), input: document.getElementById("opcFile" + k),
        pick: document.getElementById("opcPick" + k), dz: document.getElementById("opcDrop" + k),
      };
    }).filter(function (s) { return s.form && s.input && s.dz; });
    if (!slots.length) return;
    function submit(s, files) {
      if (!files || !files.length) return;
      try {
        var dt = new DataTransfer();
        dt.items.add(files[0]);
        s.input.files = dt.files;
      } catch (e) { return; }
      s.dz.classList.add("busy");
      s.form.submit();
    }
    slots.forEach(function (s) {
      if (s.pick) s.pick.addEventListener("click", function () { s.input.click(); });
      s.input.addEventListener("change", function () { if (s.input.files && s.input.files.length) { s.dz.classList.add("busy"); s.form.submit(); } });
      ["dragover", "dragenter"].forEach(function (e) {
        s.dz.addEventListener(e, function (ev) { ev.preventDefault(); ev.stopPropagation(); s.dz.classList.add("over"); });
      });
      s.dz.addEventListener("dragleave", function () { s.dz.classList.remove("over"); });
      s.dz.addEventListener("drop", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        s.dz.classList.remove("over");
        if (hint) hint.hidden = true;
        submit(s, ev.dataTransfer && ev.dataTransfer.files);
      }, false);
    });
    // a drop anywhere else is refused, not guessed into a slot
    window.addEventListener("dragover", function (ev) { ev.preventDefault(); }, false);
    window.addEventListener("drop", function (ev) {
      ev.preventDefault();
      slots.forEach(function (s) { s.dz.classList.remove("over"); });
      if (hint) {
        hint.textContent = "Drop the workbook onto the PRIOR or the CURRENT slot — the page never guesses which list is which.";
        hint.hidden = false;
      }
    }, false);
  }

  window.SFOnePagerCompare = { paint: paint };
  function init() { boot(); intake(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
