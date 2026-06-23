/* Schedule Forensics — shared stacked time-tier axis (Year / Quarter / Month).
 *
 * Operator: "On all visuals with time scales I want three tiers stacked — years on top, then
 * quarters, then months." This is the reusable renderer for that header: given the deck's "Mon-YY"
 * month labels, a pixel x-mapping, and a granularity, it draws the stacked tier bands into an SVG.
 * The S-curve has its own copy (kept stable); this module brings the same axis to the other
 * month-axis charts (curves, …). Dependency-free, air-gap-safe (no CDN). window.SFTimeAxis.
 */
"use strict";

window.SFTimeAxis = (function () {
  var NS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      // CSS var() only resolves in a style property, not a presentation attribute
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  var MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
    Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
  function parseMonth(label) {
    var m = /^([A-Za-z]{3})-(\d{2})$/.exec(String(label));
    if (!m || MONTHS[m[1]] == null) return null;
    return { y: 2000 + parseInt(m[2], 10), m: MONTHS[m[1]] };
  }
  function tierRuns(months, keyOf, labelOf) {
    var out = [], cur = null;
    for (var i = 0; i < months.length; i++) {
      var pm = parseMonth(months[i]);
      var k = pm ? keyOf(pm) : "?" + i;
      if (cur && cur.key === k) { cur.end = i; } else {
        cur = { key: k, start: i, end: i, label: pm ? labelOf(pm) : months[i] };
        out.push(cur);
      }
    }
    return out;
  }
  function yearRuns(months) {
    return tierRuns(months, function (p) { return p.y; }, function (p) { return String(p.y); });
  }
  function quarterRuns(months) {
    return tierRuns(months,
      function (p) { return p.y + "Q" + (Math.floor(p.m / 3) + 1); },
      function (p) { return "Q" + (Math.floor(p.m / 3) + 1) + " '" + String(p.y % 100); });
  }
  function monthRuns(months) {
    // first letter of each month (J F M A M J J A S O N D) — the tiers above carry the context
    return tierRuns(months, function (p) { return p.y + "-" + p.m; },
      function (p) { return "JFMAMJJASOND".charAt(p.m); });
  }

  // the stacked tiers for a granularity, top -> bottom (Year always; + Quarter / Month)
  function tiersFor(months, gran) {
    if (!months.length || !parseMonth(months[0])) {
      return [{ runs: months.map(function (l, i) {
        return { start: i, end: i, label: l };
      }), minW: 22 }];  // non-standard labels -> one flat month tier
    }
    var tiers = [{ runs: yearRuns(months), minW: 30 }];
    if (gran === "month" || gran === "quarter") tiers.push({ runs: quarterRuns(months), minW: 34 });
    if (gran === "month") tiers.push({ runs: monthRuns(months), minW: 9 });
    return tiers;
  }

  // draw the stacked tier header into `svg`; returns the number of tier rows drawn.
  // opts: { months, xOf(i)->px, slot, padL, rightPx, top, rowH, gran }
  function draw(svg, opts) {
    var months = opts.months, tiers = tiersFor(months, opts.gran || "month");
    var x = opts.xOf, slot = opts.slot, padL = opts.padL, rightPx = opts.rightPx;
    var top = opts.top || 8, rowH = opts.rowH || 16, n = months.length;
    function edges(s, e) {
      var l = (n <= 1) ? padL : x(s) - slot / 2;
      var r = (n <= 1) ? rightPx : x(e) + slot / 2;
      return [Math.max(padL, l), Math.min(rightPx, r)];
    }
    tiers.forEach(function (tier, r) {
      var rowTop = top + r * rowH;
      tier.runs.forEach(function (run) {
        var ed = edges(run.start, run.end);
        svg.appendChild(svgEl("line", { x1: ed[0], y1: rowTop, x2: ed[0], y2: rowTop + rowH,
          stroke: "var(--line)", "stroke-width": 1 }));
        if (ed[1] - ed[0] >= tier.minW) {
          var t = svgEl("text", { x: (ed[0] + ed[1]) / 2, y: rowTop + rowH - 4,
            "text-anchor": "middle", fill: "var(--muted)", "font-size": 10 });
          t.textContent = run.label;
          svg.appendChild(t);
        }
      });
      svg.appendChild(svgEl("line", { x1: padL, y1: rowTop + rowH, x2: rightPx, y2: rowTop + rowH,
        stroke: "var(--line)", "stroke-width": 1 }));
    });
    svg.appendChild(svgEl("line", { x1: rightPx, y1: top, x2: rightPx, y2: top + tiers.length * rowH,
      stroke: "var(--line)", "stroke-width": 1 }));
    return tiers.length;
  }

  return { parseMonth: parseMonth, tiersFor: tiersFor, draw: draw };
})();
