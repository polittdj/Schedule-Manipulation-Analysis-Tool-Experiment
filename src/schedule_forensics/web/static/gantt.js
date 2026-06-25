/* Schedule Forensics — shared Microsoft-Project-style Gantt timeline primitives.
 *
 * Operator: "Make the Gantt mirror Microsoft Project on all pages — the three-tier timeline
 * (Year / Quarter / Month), the gridlines, the WBS indentation, zoom." This is the single
 * implementation of that timeline header + gridlines, so every HTML Gantt on the site (the
 * activity grid, the driving-path trace, the path workspace, the corridor animation) reads
 * identically. Dependency-free, air-gap-safe (no CDN). window.SFGantt.
 *
 * The contract is a tiny "axis" object: { t0, t1, width, x(ms) -> px } where t0/t1 are epoch
 * milliseconds spanning the chart and x() maps a timestamp to a pixel offset. Each page keeps
 * its own axis construction (zoom = pixels-per-day differs per view) and only swaps its old
 * single-tier header for buildTierScale() and adds gridLines() down each track.
 */
"use strict";

window.SFGantt = (function () {
  var DAY_MS = 86400000;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") node.textContent = attrs[k];
        else if (k === "class") node.className = attrs[k];
        else node.setAttribute(k, attrs[k]);
      });
    }
    return node;
  }

  // Year / Quarter / Month bands across the axis, each spanning [period-start, next-start) in
  // pixels. Narrow bands collapse their label (a quarter to "Q1", a month to a single letter)
  // exactly like Microsoft Project's timeline does as you zoom out.
  function timeTiers(axis) {
    function bands(startOf, advance, label) {
      var out = [];
      var cur = new Date(axis.t0);
      startOf(cur);
      var guard = 0;
      while (cur.getTime() <= axis.t1 && guard++ < 6000) {
        var next = new Date(cur);
        advance(next);
        var left = axis.x(cur.getTime());
        var right = axis.x(next.getTime());
        var w = right - left;
        if (right > 0 && left < axis.width) {
          out.push({ left: Math.max(0, left), width: Math.max(1, w), label: label(cur, w) });
        }
        cur.setTime(next.getTime());
      }
      return out;
    }
    var years = bands(
      function (d) { d.setUTCMonth(0, 1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCFullYear(d.getUTCFullYear() + 1); },
      function (d) { return String(d.getUTCFullYear()); }
    );
    var quarters = bands(
      function (d) { d.setUTCMonth(Math.floor(d.getUTCMonth() / 3) * 3, 1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCMonth(d.getUTCMonth() + 3); },
      function (d, w) {
        return w < 34 ? "Q" + (Math.floor(d.getUTCMonth() / 3) + 1)
          : "Qtr " + (Math.floor(d.getUTCMonth() / 3) + 1) + " " + d.getUTCFullYear();
      }
    );
    var months = bands(
      function (d) { d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0); },
      function (d) { d.setUTCMonth(d.getUTCMonth() + 1); },
      function (d, w) { return w < 22 ? MONTHS[d.getUTCMonth()][0] : MONTHS[d.getUTCMonth()]; }
    );
    return { years: years, quarters: quarters, months: months };
  }

  // The stacked Year/Quarter/Month header element (Microsoft Project timeline). `baseClass` is
  // the page's own scale class (so its width/flex rules still apply); `anchorIso`, when given,
  // draws the data-date / now line through the header.
  function buildTierScale(axis, baseClass, anchorIso) {
    var scale = el("div", { class: baseClass + " g-scale-tiered", style: "width:" + axis.width + "px" });
    var tiers = timeTiers(axis);
    [["yr", tiers.years], ["qtr", tiers.quarters], ["mo", tiers.months]].forEach(function (t) {
      var row = el("div", { class: "g-tier g-tier-" + t[0] });
      t[1].forEach(function (b) {
        row.appendChild(el("div", {
          class: "g-band", title: b.label, text: b.label,
          style: "left:" + b.left + "px;width:" + b.width + "px",
        }));
      });
      scale.appendChild(row);
    });
    if (anchorIso) {
      var a = Date.parse(anchorIso);
      if (!isNaN(a)) scale.appendChild(el("div", { class: "pv-now", style: "left:" + axis.x(a) + "px" }));
    }
    return scale;
  }

  // Vertical gridlines down a chart: light at month starts, heavier at quarter, heaviest at
  // year — positioned in pixels so they line up with the header bands (MS-Project gridlines).
  function gridLines(axis) {
    var lines = [];
    var d = new Date(axis.t0);
    d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0);
    var guard = 0;
    while (d.getTime() <= axis.t1 && guard++ < 6000) {
      var left = axis.x(d.getTime());
      if (left >= 0 && left <= axis.width) {
        var m = d.getUTCMonth();
        var cls = m === 0 ? "g-grid g-grid-yr" : m % 3 === 0 ? "g-grid g-grid-qtr" : "g-grid";
        lines.push({ left: left, cls: cls });
      }
      d.setUTCMonth(d.getUTCMonth() + 1);
    }
    return lines;
  }

  // Append month/quarter/year gridline divs into a track element (small convenience used by the
  // HTML Gantts so each track carries the same vertical rules as the header).
  function paintGrid(track, lines) {
    (lines || []).forEach(function (g) {
      track.appendChild(el("div", { class: g.cls, style: "left:" + g.left + "px" }));
    });
  }

  // MS-Project frozen columns: pin every data column (all but the final, scalable timeline column)
  // to the left edge so the data stays visible while the wide timeline scrolls left↔right. The
  // rendered header widths give each column's cumulative left offset; we set position:sticky + that
  // offset on the column's header, filter-row and body cells (the CSS gives them an opaque canvas
  // background + a freeze line). Returns the total frozen width (px) so a caller can size the
  // remaining timeline to exactly fill the page. Idempotent — safe to re-run after a body repaint
  // or a column resize. Works whether the body rows live in a <tbody> or are bare <tr> children.
  function freezeColumns(table) {
    if (!table) return 0;
    var headRow = table.querySelector("thead tr");
    if (!headRow) return 0;
    var headCells = headRow.children;
    var frozen = headCells.length - 1; // the last column is the scalable timeline — it must scroll
    if (frozen < 1) return 0;
    var offsets = [];
    var acc = 0;
    for (var i = 0; i < frozen; i++) {
      offsets.push(acc);
      acc += headCells[i].offsetWidth;
    }
    var rows = table.rows; // every row: the header rows, the filter row, and all body rows
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].children;
      for (var c = 0; c < frozen && c < cells.length; c++) {
        var cell = cells[c];
        cell.style.position = "sticky";
        cell.style.left = offsets[c] + "px";
        cell.classList.add("sf-frozen-col");
        if (c === frozen - 1) cell.classList.add("sf-frozen-last");
        else cell.classList.remove("sf-frozen-last");
      }
    }
    return acc;
  }

  return {
    DAY_MS: DAY_MS, MONTHS: MONTHS, el: el,
    timeTiers: timeTiers, buildTierScale: buildTierScale,
    gridLines: gridLines, paintGrid: paintGrid, freezeColumns: freezeColumns,
  };
})();
