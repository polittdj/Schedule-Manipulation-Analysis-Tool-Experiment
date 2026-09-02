// onepager.js — paints the One-Pager the server laid out (reports/onepager.py) as ONE SVG in the
// same logical coordinates the .pptx export uses (960 x 540 points, 16:9), so the page IS the
// preview of the slide: every bar, diamond, label, month line and legend chip sits where the
// exported shape will. Geometry is never computed here — only painted — which is what keeps the
// two renderings identical and the layout testable without a browser.
//
// Strict CSP (script-src 'self'): the layout arrives in a non-executable JSON block
// (#opData), the launch.js idiom. The data-date marker is the tool-wide SFGantt.dataDateLine
// (ADR-0342) — here the data date is TODAY, which is the red line the one-pager convention
// wants — and the axis captions go through SFChartFrame.axisTitles (ADR-0298).
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

  function paint(host, L) {
    var svg = el("svg", { viewBox: "0 0 " + L.w + " " + L.h, class: "op-svg", role: "img", "aria-label": L.title });
    svg.appendChild(el("rect", { x: 0, y: 0, width: L.w, height: L.h, class: "op-bg" }));
    // ── title block ──
    svg.appendChild(el("text", { x: L.lane_col_x0, y: L.title_y, class: "op-title" }, L.title));
    if (L.subtitle) svg.appendChild(el("text", { x: L.lane_col_x0, y: L.sub_y, class: "op-sub" }, L.subtitle));
    // ── year bands (alternating tint, full chart height) + the year labels ──
    L.years.forEach(function (b) {
      svg.appendChild(el("rect", { x: b.x0, y: L.year_y0, width: b.x1 - b.x0, height: L.lanes_y1 - L.year_y0, class: "op-year op-year-" + b.shade }));
      svg.appendChild(el("line", { x1: b.x0, y1: L.year_y0, x2: b.x0, y2: L.lanes_y1, class: "op-year-line" }));
      if (b.x1 - b.x0 > 18) svg.appendChild(el("text", { x: (b.x0 + b.x1) / 2, y: L.year_y0 + 9, "text-anchor": "middle", class: "op-year-label" }, b.label));
    });
    svg.appendChild(el("line", { x1: L.x1, y1: L.year_y0, x2: L.x1, y2: L.lanes_y1, class: "op-year-line" }));
    // ── month grid: dotted lines through every lane, letters/abbreviations in the month band ──
    L.months.forEach(function (m) {
      svg.appendChild(el("line", { x1: m.x, y1: L.year_y1, x2: m.x, y2: L.lanes_y1, class: "op-month-line" }));
      if (m.label) svg.appendChild(el("text", { x: m.label_x, y: L.mon_y1 - 3.5, "text-anchor": "middle", class: "op-month-label", style: "font-size:" + L.month_pt + "px" }, m.label));
    });
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.mon_y1, x2: L.x1, y2: L.mon_y1, class: "op-header-line" }));
    // ── swimlanes: band, name block, then the items ──
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
    var barH = L.bar_h, ms = L.ms;
    L.items.forEach(function (p) {
      var fill = laneVar(L.lanes[p.lane].color), g = el("g", { class: "op-item" + (p.milestone ? " op-ms" : " op-act") });
      var title = el("title", {}, p.name + (p.milestone ? " — " + p.finish : " — " + p.start + " → " + p.finish));
      g.appendChild(title);
      if (p.milestone) {
        var h = ms / 2;
        g.appendChild(el("polygon", { points: p.x0 + "," + (p.y - h) + " " + (p.x0 + h) + "," + p.y + " " + p.x0 + "," + (p.y + h) + " " + (p.x0 - h) + "," + p.y, fill: fill, class: "op-diamond" }));
      } else {
        g.appendChild(el("rect", { x: p.x0, y: p.y - barH / 2, width: p.x1 - p.x0, height: barH, rx: 1.2, fill: fill, class: "op-bar" }));
      }
      g.appendChild(el("text", { x: p.label_x, y: p.y + L.label_pt * 0.35, "text-anchor": p.label_anchor, class: "op-label" + (p.inside ? " op-label-in" : ""), style: "font-size:" + L.label_pt + "px" }, p.label));
      svg.appendChild(g);
    });
    // ── today: the tool-wide DD marker, plus the one-pager's own dated caption ──
    if (L.today_x !== null && window.SFGantt && SFGantt.dataDateLine) {
      SFGantt.dataDateLine(svg, { x: L.today_x, top: L.year_y0, bottom: L.lanes_y1, iso: L.today_iso });
      svg.appendChild(el("text", { x: L.today_label_x, y: L.today_label_y, "text-anchor": L.today_label_anchor, class: "op-today" }, L.today_label));
    }
    // ── legend ──
    L.legend.forEach(function (e) {
      var g = el("g", { class: "op-legend-item" }), cy = e.y - 2.5;
      if (e.kind === "activity") g.appendChild(el("rect", { x: e.x, y: cy - 2.5, width: 10, height: 5, rx: 1, class: "op-legend-bar" }));
      else if (e.kind === "milestone") g.appendChild(el("polygon", { points: (e.x + 5) + "," + (cy - 3.5) + " " + (e.x + 8.5) + "," + cy + " " + (e.x + 5) + "," + (cy + 3.5) + " " + (e.x + 1.5) + "," + cy, class: "op-legend-ms" }));
      else if (e.kind === "today") g.appendChild(el("line", { x1: e.x + 5, y1: cy - 4, x2: e.x + 5, y2: cy + 4, class: "op-legend-today" }));
      else g.appendChild(el("rect", { x: e.x, y: cy - 3, width: 10, height: 6, rx: 1, fill: laneVar(e.color), class: "op-legend-lane" }));
      g.appendChild(el("text", { x: e.x + 13, y: e.y, class: "op-legend-text", style: "font-size:" + L.legend_pt + "px" }, e.label));
      svg.appendChild(g);
    });
    svg.appendChild(el("line", { x1: L.lane_col_x0, y1: L.legend_y0, x2: L.x1, y2: L.legend_y0, class: "op-header-line" }));
    if (window.SFChartFrame && SFChartFrame.axisTitles) {
      SFChartFrame.axisTitles(svg, {
        L: L.lane_col_x0 - 4, R: L.x1, T: L.lanes_y0 - 12, B: L.legend_y0 - 1,
      }, {
        xLabel: "Timeline by month and year", yLabel: "Swimlane",
      });
    }
    host.textContent = "";
    host.appendChild(svg);
    return svg;
  }

  function boot() {
    var host = document.getElementById("opHost"), data = document.getElementById("opData");
    if (!host || !data) return;
    var L;
    try { L = JSON.parse(data.textContent || "null"); } catch (e) { L = null; }
    if (!L) return;
    paint(host, L);
  }
  // ── intake: the file picker and window-wide drag-and-drop, the home.js idiom ──
  // A dropped workbook is handed to the SAME form the picker submits (the input's FileList is
  // replaced through a DataTransfer), so there is one upload path and it works without fetch.
  function intake() {
    var form = document.getElementById("opForm"), input = document.getElementById("opFile"),
      pick = document.getElementById("opPick"), dz = document.getElementById("opDrop");
    if (!form || !input || !dz) return;
    function submit(files) {
      if (!files || !files.length) return;
      try {
        var dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
      } catch (e) { return; }
      dz.classList.add("busy");
      form.submit();
    }
    if (pick) pick.addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () { if (input.files && input.files.length) { dz.classList.add("busy"); form.submit(); } });
    window.addEventListener("dragover", function (ev) { ev.preventDefault(); }, false);
    window.addEventListener("drop", function (ev) {
      ev.preventDefault();
      dz.classList.remove("over");
      submit(ev.dataTransfer && ev.dataTransfer.files);
    }, false);
    ["dragover", "dragenter"].forEach(function (e) {
      dz.addEventListener(e, function (ev) { ev.preventDefault(); dz.classList.add("over"); });
    });
    dz.addEventListener("dragleave", function () { dz.classList.remove("over"); });
  }

  window.SFOnePager = { paint: paint };
  function init() { boot(); intake(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
