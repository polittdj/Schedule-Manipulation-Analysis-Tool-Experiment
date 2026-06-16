/* Schedule Forensics — SPI(t) & Earned Schedule by WBS combo chart (PBIX page 9).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Per WBS group: SPI(t) as bars on the
 * left axis (red below the 1.0 on-plan reference line, green at/above it) and Earned
 * Schedule (working days) as a line on the right axis. Groups with no SPI(t) (no
 * completions / no baseline finishes) leave a gap — never a fabricated 0. Data: the
 * local /api/wbs/<name> endpoint (the name is read from the chart container's data-name).
 */
"use strict";

(function () {
  var box = document.getElementById("wbsChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var OK = "var(--ok)", BAD = "var(--bad)", LINE = "var(--accent)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  // the page is /wbs/<name>; derive the API path from the location so the chart is
  // self-contained (no server-injected name needed)
  var name = decodeURIComponent(location.pathname.replace(/^\/wbs\//, ""));

  fetch("/api/wbs/" + encodeURIComponent(name))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var groups = data.groups || [];
      if (!groups.length) { box.textContent = "No WBS groups to chart."; return; }

      var W = 980, H = 340, padL = 36, padR = 40, padT = 24, padB = 50;
      var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
      var n = groups.length;
      var slot = (W - padL - padR) / n;
      var barW = Math.max(3, Math.min(26, slot * 0.5));

      // left axis: SPI(t), 0..max(1.2, observed max). right axis: ES days, 0..max ES.
      var spiVals = groups.map(function (g) { return g.spi_t; }).filter(function (v) { return v != null; });
      var spiTop = Math.max(1.2, spiVals.length ? Math.max.apply(null, spiVals) : 1.2);
      var esVals = groups.map(function (g) { return g.earned_schedule_days; }).filter(function (v) { return v != null; });
      var esTop = Math.max(1, esVals.length ? Math.max.apply(null, esVals) : 1);
      var yL = function (v) { return padT + (1 - v / spiTop) * (H - padT - padB); };
      var yR = function (v) { return padT + (1 - v / esTop) * (H - padT - padB); };

      // left-axis gridlines + labels
      [0, 0.25, 0.5, 0.75, 1].forEach(function (frac) {
        var gy = yL(spiTop * frac);
        svg.appendChild(svgEl("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1 }));
        var lab = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
        lab.textContent = (spiTop * frac).toFixed(1);
        svg.appendChild(lab);
      });
      // right-axis tick labels (ES days) at the same gridlines
      [0, 0.5, 1].forEach(function (frac) {
        var gy = yR(esTop * frac);
        var lab = svgEl("text", { x: W - padR + 6, y: gy + 4, "text-anchor": "start", fill: "var(--muted)", "font-size": 10 });
        lab.textContent = String(Math.round(esTop * frac));
        svg.appendChild(lab);
      });

      // SPI(t) = 1.0 on-plan reference line
      var refY = yL(1.0);
      svg.appendChild(svgEl("line", { x1: padL, y1: refY, x2: W - padR, y2: refY, stroke: "var(--warn)", "stroke-width": 1.5, "stroke-dasharray": "6 4" }));
      var refLab = svgEl("text", { x: padL + 2, y: refY - 4, fill: "var(--warn)", "font-size": 10 });
      refLab.textContent = "SPI(t) = 1.0 (on plan)";
      svg.appendChild(refLab);

      // SPI bars
      groups.forEach(function (g, i) {
        var cx = padL + i * slot + slot / 2;
        if (g.spi_t != null) {
          var h = yL(0) - yL(g.spi_t);
          svg.appendChild(svgEl("rect", {
            x: cx - barW / 2, y: yL(g.spi_t), width: barW, height: h,
            fill: g.spi_t >= 1.0 ? OK : BAD,
          }));
        }
        // x labels, thinned to avoid overlap
        var step = Math.max(1, Math.ceil(n / 24));
        if (i % step === 0) {
          var ml = svgEl("text", { x: cx, y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
            transform: "rotate(-35 " + cx + " " + (H - padB + 16) + ")" });
          ml.textContent = g.wbs;
          svg.appendChild(ml);
        }
      });

      // Earned-Schedule line (right axis), skipping gaps
      var prev = null;
      groups.forEach(function (g, i) {
        var cx = padL + i * slot + slot / 2;
        if (g.earned_schedule_days != null) {
          var py = yR(g.earned_schedule_days);
          svg.appendChild(svgEl("circle", { cx: cx, cy: py, r: 3, fill: LINE }));
          if (prev) {
            svg.appendChild(svgEl("line", { x1: prev[0], y1: prev[1], x2: cx, y2: py, stroke: LINE, "stroke-width": 2 }));
          }
          prev = [cx, py];
        } else {
          prev = null;  // a gap breaks the line (no fabricated bridge)
        }
      });

      // legend
      var legend = [["SPI(t) ≥ 1", OK], ["SPI(t) < 1", BAD], ["Earned schedule (wd)", LINE]];
      var lx = padL;
      legend.forEach(function (item) {
        svg.appendChild(svgEl("rect", { x: lx, y: H - 12, width: 10, height: 10, fill: item[1] }));
        var lt = svgEl("text", { x: lx + 14, y: H - 3, fill: "var(--muted)", "font-size": 11 });
        lt.textContent = item[0];
        svg.appendChild(lt);
        lx += 14 + item[0].length * 6 + 22;
      });

      box.appendChild(svg);
    })
    .catch(function () { box.textContent = "Failed to load the WBS data."; });
})();
