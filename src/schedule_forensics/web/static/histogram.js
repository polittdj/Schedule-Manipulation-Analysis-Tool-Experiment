/* Schedule Forensics — total-float distribution histogram (handbook §6.3.2.5.2.2; assessment deck).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Bins every non-summary activity by its Total Float
 * (working days) into DCMA-aligned buckets, so the *shape* of the float distribution is visible: mass
 * at 0 / negative is the critical+behind core, a spike in the high (> 44 d) bucket is float padding /
 * missing successor logic. Data: the local /api/analysis/<name> endpoint (the same activity rows the
 * grid and scatter use); the page's full activity grid is the accessible data table.
 */
"use strict";

(function () {
  var box = document.getElementById("floatHist");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";

  // fixed, meaningful buckets (aligned to the DCMA float bands: 0, <5, <10, high > 44 working days)
  var BUCKETS = [
    { label: "< 0", lo: -Infinity, hi: 0, crit: true },     // negative float — behind a constraint
    { label: "0", lo: 0, hi: 0, crit: true },               // zero float — critical
    { label: "1–5", lo: 1, hi: 5 },
    { label: "6–10", lo: 6, hi: 10 },
    { label: "11–20", lo: 11, hi: 20 },
    { label: "21–44", lo: 21, hi: 44 },
    { label: "> 44", lo: 45, hi: Infinity, high: true },    // high float — DCMA-06 / missing logic
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

  function bucketOf(v) {
    if (v < 0) return 0;
    if (v === 0) return 1;
    for (var i = 2; i < BUCKETS.length; i++) {
      if (v >= BUCKETS[i].lo && v <= BUCKETS[i].hi) return i;
    }
    return BUCKETS.length - 1;  // the open-ended high bucket
  }

  function render(floats) {
    box.innerHTML = "";
    var counts = BUCKETS.map(function () { return 0; });
    floats.forEach(function (v) { counts[bucketOf(v)] += 1; });
    var top = Math.max.apply(null, counts) || 1;
    var total = floats.length;

    var n = BUCKETS.length;
    var W = 940, H = 360, padL = 44, padR = 16, padT = 18, padB = 54;
    var slot = (W - padL - padR) / n;
    var barW = slot * 0.7;
    var y = function (c) { return padT + (1 - c / top) * (H - padT - padB); };
    var xc = function (i) { return padL + i * slot + slot / 2; };

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "Total-float distribution histogram");

    // y gridlines + count labels
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

    BUCKETS.forEach(function (b, i) {
      var c = counts[i];
      var col = b.crit ? "var(--bad)" : (b.high ? "var(--warn)" : "var(--accent)");
      if (c > 0) {
        var pct = total ? Math.round((c / total) * 100) : 0;
        var bar = svgEl("rect", {
          x: xc(i) - barW / 2, y: y(c), width: barW, height: y(0) - y(c), fill: col,
        });
        var bt = svgEl("title", {});
        bt.textContent =
          b.label + " working days: " + c + (c === 1 ? " activity" : " activities") +
          " (" + pct + "% of " + total + ")";
        bar.appendChild(bt);  // shared chartframe call-out reads this on hover
        svg.appendChild(bar);
        var cn = svgEl("text", {
          x: xc(i), y: y(c) - 5, "text-anchor": "middle", fill: "var(--ink)", "font-size": 11,
        });
        cn.textContent = String(c);
        svg.appendChild(cn);
      }
      var lab = svgEl("text", {
        x: xc(i), y: H - padB + 18, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11,
      });
      lab.textContent = b.label;
      svg.appendChild(lab);
    });
    // x-axis caption
    var cap = svgEl("text", {
      x: (padL + W - padR) / 2, y: H - 6, "text-anchor": "middle", fill: "var(--muted)",
      "font-size": 11,
    });
    cap.textContent = "Total float (working days)";
    svg.appendChild(cap);
    box.appendChild(svg);

    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Total-float distribution — activity count per band",
        ["Total float (working days)", "Activities"],
        BUCKETS.map(function (b, i) { return [b.label, counts[i]]; })
      ));
    }
  }

  var name = box.getAttribute("data-name") || "";
  fetch("/api/analysis/" + encodeURIComponent(name))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      var floats = (d.activities || [])
        .filter(function (a) { return !a.is_summary && a.total_float_days != null; })
        .map(function (a) { return a.total_float_days; });
      if (!floats.length) { box.textContent = "No activity float data to plot."; return; }
      render(floats);
    })
    .catch(function () { box.textContent = "Failed to load the float-distribution data."; });
})();
