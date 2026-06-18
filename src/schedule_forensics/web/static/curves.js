/* Schedule Forensics — Finish & Slippage month curves (PBIX pages 6, 7, 12).
 *
 * Dependency-free SVG line charts (no CDN — air-gap posture). Three charts over the
 * shared month axis from /api/curves:
 *   • Finishes        — actual vs baseline finishes for the latest version (2 lines)
 *   • DATA Date Finishes — one actual-finish curve per version (the bow wave as lines)
 *   • Slippage        — per version, a start curve (solid) and a finish curve (dashed)
 * The count axis of each chart is locked to that chart's own tallest point so the
 * curves never rescale misleadingly between series.
 */
"use strict";

(function () {
  var NS = "http://www.w3.org/2000/svg";
  var GOLD = "var(--warn)", BLUE = "var(--accent)";
  // a fixed, theme-independent palette for the per-version overlays (distinct hues that
  // read on both light and dark backgrounds); cycled if there are more versions than hues
  var PALETTE = [
    "#4f8cff", "#ff7043", "#26a69a", "#ab47bc", "#ffca28",
    "#66bb6a", "#ec407a", "#8d6e63", "#29b6f6", "#d4e157",
  ];

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  // Legend labels for the versions. Prefer the DATA DATE (short, uniform, the order the
  // versions are drawn in) so the per-version legend stays readable; fall back to the
  // prefix-stripped filename only when a version has no data date.
  function shortLabels(versions) {
    if (versions.some(function (v) { return v.status_date; })) {
      return versions.map(function (v, i) { return v.status_date || "v" + (i + 1); });
    }
    var labels = versions.map(function (v) { return v.label; });
    if (labels.length < 2) return labels.map(function (l) { return l.slice(0, 22); });
    var prefix = labels[0];
    labels.forEach(function (l) {
      var i = 0;
      while (i < prefix.length && i < l.length && prefix[i] === l[i]) i++;
      prefix = prefix.slice(0, i);
    });
    var cut = prefix.length >= 6 ? prefix.length : 0;
    return labels.map(function (l, i) {
      var s = (cut ? l.slice(cut) : l).replace(/\.(mpp|xml|xer|json|mspdi)$/i, "");
      if (!s) return "v" + (i + 1);
      if (cut) s = "…" + s;
      return s.length > 22 ? s.slice(0, 21) + "…" : s;
    });
  }

  // One month-axis line chart. series = [{values, color, dashed, label}]. statusIndex
  // (optional) draws a dashed data-date marker. Renders into the given container element.
  function lineChart(box, months, series, statusIndex, name) {
    if (!box) return;
    box.innerHTML = "";
    var W = 980, H = 320, padL = 36, padR = 14, padT = 24, padB = 46;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = months.length;
    var top = 1;
    series.forEach(function (s) {
      s.values.forEach(function (v) { if (v > top) top = v; });
    });
    var x = function (i) { return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1)); };
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };

    // y gridlines + labels
    [0, 0.25, 0.5, 0.75, 1].forEach(function (frac) {
      var gy = y(top * frac);
      svg.appendChild(svgEl("line", {
        x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1,
      }));
      var lab = svgEl("text", {
        x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
      });
      lab.textContent = String(Math.round(top * frac));
      svg.appendChild(lab);
    });

    // month labels, thinned to avoid overlap
    var step = Math.max(1, Math.ceil(n / 16));
    for (var i = 0; i < n; i++) {
      if (i % step === 0) {
        var ml = svgEl("text", {
          x: x(i), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + x(i) + " " + (H - padB + 16) + ")",
        });
        ml.textContent = months[i];
        svg.appendChild(ml);
      }
    }

    // dashed data-date marker (right edge of the data-date month)
    if (statusIndex != null) {
      var sx = x(statusIndex);
      svg.appendChild(svgEl("line", {
        x1: sx, y1: padT, x2: sx, y2: y(0), stroke: BLUE, "stroke-width": 2, "stroke-dasharray": "6 5",
      }));
      var sl = svgEl("text", { x: sx, y: padT - 4, "text-anchor": "middle", fill: BLUE, "font-size": 10 });
      sl.textContent = "data date";
      svg.appendChild(sl);
    }

    // the lines
    series.forEach(function (s) {
      var pts = s.values.map(function (v, idx) { return x(idx) + "," + y(v); });
      var attrs = {
        points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2,
      };
      if (s.dashed) attrs["stroke-dasharray"] = "5 4";
      svg.appendChild(svgEl("polyline", attrs));
    });

    // legend
    var lx = padL, ly = H - 6;
    series.forEach(function (s) {
      var line = svgEl("line", {
        x1: lx, y1: ly - 4, x2: lx + 16, y2: ly - 4, stroke: s.color, "stroke-width": 2,
      });
      if (s.dashed) line.setAttribute("stroke-dasharray", "5 4");
      svg.appendChild(line);
      var lt = svgEl("text", { x: lx + 20, y: ly, fill: "var(--muted)", "font-size": 11 });
      lt.textContent = s.label;
      svg.appendChild(lt);
      lx += 20 + s.label.length * 6 + 22;
    });

    if (window.SFA11y) SFA11y.label(svg, name || "Chart");
    box.appendChild(svg);
    // A3: a visually-hidden data-table fallback so screen readers can read the numbers
    if (window.SFA11y) {
      var headers = ["Month"].concat(series.map(function (s) { return s.label; }));
      var trows = months.map(function (m, i) {
        return [m].concat(series.map(function (s) { return s.values[i]; }));
      });
      box.appendChild(SFA11y.table((name || "Chart") + " — data", headers, trows));
    }
  }

  fetch("/api/curves")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var months = data.months;
      var versions = data.versions;
      var labels = shortLabels(versions);

      // ── Finishes (latest version): actual vs baseline ──────────────────────────
      var latest = versions[versions.length - 1];
      lineChart(
        document.getElementById("finishesChart"),
        months,
        [
          { values: latest.baseline_finishes, color: GOLD, label: "Baseline finishes" },
          { values: latest.actual_finishes, color: BLUE, label: "Actual / scheduled finishes" },
        ],
        latest.status_index,
        "Finishes — actual vs baseline finishes by month"
      );

      // ── DATA Date Finishes: one actual-finish curve per version ─────────────────
      lineChart(
        document.getElementById("dataDateChart"),
        months,
        versions.map(function (v, i) {
          return { values: v.actual_finishes, color: PALETTE[i % PALETTE.length], label: labels[i] };
        }),
        null,
        "Data-date finishes — actual-finish curve per version"
      );

      // ── Slippage: per version, start (solid) + finish (dashed) curves ───────────
      var slipSeries = [];
      versions.forEach(function (v, i) {
        var col = PALETTE[i % PALETTE.length];
        slipSeries.push({ values: v.actual_starts, color: col, label: labels[i] + " starts" });
        slipSeries.push({ values: v.actual_finishes, color: col, dashed: true, label: labels[i] + " finishes" });
      });
      lineChart(
        document.getElementById("slippageChart"), months, slipSeries, null,
        "Slippage — start and finish curves per version"
      );
    })
    .catch(function () {
      ["finishesChart", "dataDateChart", "slippageChart"].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.textContent = "Failed to load the curve data.";
      });
    });
})();
