/* Schedule Forensics — cross-version trend charts (PBIX pages 4 + 5).
 *
 * Dependency-free SVG charts (no CDN, no external fetch — air-gap posture).
 * Data comes from /api/trend: per-version headline numbers, the quality-metric
 * series (existing), and per-version cross-file + float-analysis data (ADR-0039).
 */
"use strict";

(function () {
  var box = document.getElementById("trendCharts");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  // Strip a long common prefix from version labels so axis text doesn't overlap.
  function shortLabels(versions) {
    var labels = versions.map(function (v) { return v.label; });
    function fallback(i) { return versions[i].status_date || "v" + (i + 1); }
    if (labels.length < 2) return labels.map(function (l) { return l.slice(0, 16); });
    var prefix = labels[0];
    labels.forEach(function (l) {
      var i = 0;
      while (i < prefix.length && i < l.length && prefix[i] === l[i]) i++;
      prefix = prefix.slice(0, i);
    });
    var cut = prefix.length >= 6 ? prefix.length : 0;
    return labels.map(function (l, i) {
      var s = (cut ? l.slice(cut) : l).replace(/\.(mpp|xml|xer|json|mspdi)$/i, "");
      if (!s) return fallback(i);
      if (cut) s = "…" + s;
      return s.length > 16 ? s.slice(0, 15) + "…" : s;
    });
  }

  // ── helpers ──────────────────────────────────────────────────────────────────

  function xTick(i, n, W, padL, padR) {
    return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1));
  }

  // One line chart: values per version; null = no data (never fabricated as 0).
  function lineChart(title, labels, values, valueText, color) {
    var W = 460, H = 210, padL = 14, padR = 14, padT = 26, padB = 54;
    var known = values.filter(function (v) { return v != null; });
    if (!known.length) return;
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var lo = Math.min.apply(null, known), hi = Math.max.apply(null, known);
    if (lo === hi) { lo -= 1; hi += 1; }
    var n = values.length;
    var x = function (i) { return xTick(i, n, W, padL, padR); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    var pts = [];
    values.forEach(function (v, i) { if (v != null) pts.push(x(i) + "," + y(v)); });
    svg.appendChild(svgEl("polyline", {
      points: pts.join(" "), fill: "none", stroke: color, "stroke-width": 2.5,
    }));
    values.forEach(function (v, i) {
      if (v != null) {
        svg.appendChild(svgEl("circle", { cx: x(i), cy: y(v), r: 4, fill: color }));
        var val = svgEl("text", {
          x: x(i), y: y(v) - 9, "text-anchor": "middle", fill: "var(--ink)", "font-size": 12,
        });
        val.textContent = valueText(v, i);
        svg.appendChild(val);
      }
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
      });
      lab.textContent = labels[i];
      svg.appendChild(lab);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  // Multi-line chart: series is [{label, values, color}].
  function multiLineChart(title, labels, series) {
    var W = 460, H = 210, padL = 14, padR = 14, padT = 26, padB = 54;
    var allVals = [];
    series.forEach(function (s) {
      s.values.forEach(function (v) { if (v != null) allVals.push(v); });
    });
    if (!allVals.length) return;
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var lo = Math.min.apply(null, allVals), hi = Math.max.apply(null, allVals);
    if (lo === hi) { lo -= 0.05; hi += 0.05; }
    var n = labels.length;
    var x = function (i) { return xTick(i, n, W, padL, padR); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    series.forEach(function (s) {
      var pts = [];
      s.values.forEach(function (v, i) { if (v != null) pts.push(x(i) + "," + y(v)); });
      if (pts.length) {
        svg.appendChild(svgEl("polyline", {
          points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2.5,
        }));
      }
      s.values.forEach(function (v, i) {
        if (v != null) {
          svg.appendChild(svgEl("circle", { cx: x(i), cy: y(v), r: 4, fill: s.color }));
          var val = svgEl("text", {
            x: x(i), y: y(v) - 8, "text-anchor": "middle", fill: "var(--ink)", "font-size": 10,
          });
          val.textContent = v.toFixed(2);
          svg.appendChild(val);
        }
      });
    });
    // axis labels (bottom)
    labels.forEach(function (l, i) {
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
      });
      lab.textContent = l;
      svg.appendChild(lab);
    });
    // legend
    var legY = padT - 2;
    series.forEach(function (s, si) {
      var legX = padL + si * 80;
      svg.appendChild(svgEl("line", {
        x1: legX, y1: legY, x2: legX + 14, y2: legY,
        stroke: s.color, "stroke-width": 2.5,
      }));
      var lt = svgEl("text", {
        x: legX + 17, y: legY + 4, fill: "var(--ink)", "font-size": 10,
      });
      lt.textContent = s.label;
      svg.appendChild(lt);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  // Stacked bar chart: segments is [{key, label, color}]; data is array of objects.
  function stackedBarChart(title, labels, data, segments) {
    var W = 460, H = 220, padL = 34, padR = 14, padT = 26, padB = 54;
    var maxTotal = 0;
    data.forEach(function (d) {
      var tot = 0;
      segments.forEach(function (s) { tot += (d[s.key] || 0); });
      if (tot > maxTotal) maxTotal = tot;
    });
    if (!maxTotal) return;
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = data.length;
    var bw = Math.max(8, (W - padL - padR) / (n * 1.6) | 0);
    var gap = (W - padL - padR - n * bw) / Math.max(n - 1, 1);
    var barH = H - padT - padB;
    // y axis ticks
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var yv = padT + barH * (1 - f);
      svg.appendChild(svgEl("line", {
        x1: padL - 4, y1: yv, x2: W - padR, y2: yv,
        stroke: "var(--muted)", "stroke-width": 0.5, "stroke-dasharray": "2,2",
      }));
      var t = svgEl("text", {
        x: padL - 6, y: yv + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 9,
      });
      t.textContent = Math.round(f * maxTotal);
      svg.appendChild(t);
    });
    data.forEach(function (d, i) {
      var cx = padL + i * (bw + gap) + bw / 2;
      var yBase = padT + barH;
      segments.forEach(function (s) {
        var v = d[s.key] || 0;
        if (!v) return;
        var bH = (v / maxTotal) * barH;
        svg.appendChild(svgEl("rect", {
          x: cx - bw / 2, y: yBase - bH, width: bw, height: bH, fill: s.color,
        }));
        yBase -= bH;
      });
      var lab = svgEl("text", {
        x: cx, y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + cx + " " + (H - padB + 14) + ")",
      });
      lab.textContent = labels[i];
      svg.appendChild(lab);
    });
    // legend
    var legY = padT - 2;
    segments.forEach(function (s, si) {
      var legX = padL + si * 80;
      svg.appendChild(svgEl("rect", { x: legX, y: legY - 7, width: 12, height: 8, fill: s.color }));
      var lt = svgEl("text", {
        x: legX + 15, y: legY, fill: "var(--ink)", "font-size": 10,
      });
      lt.textContent = s.label;
      svg.appendChild(lt);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  // Grouped bar chart: groups is [{key, label, color}]; data is [{group values}] per version.
  function groupedBarChart(title, labels, data, groups) {
    var W = 460, H = 220, padL = 34, padR = 14, padT = 26, padB = 54;
    var maxVal = 0;
    data.forEach(function (d) {
      groups.forEach(function (g) { if ((d[g.key] || 0) > maxVal) maxVal = d[g.key] || 0; });
    });
    if (!maxVal) return;
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = data.length, ng = groups.length;
    var totalBw = Math.max(8 * ng, ((W - padL - padR) / (n * 1.6)) | 0);
    var bw = totalBw / ng;
    var gap = (W - padL - padR - n * totalBw) / Math.max(n - 1, 1);
    var barH = H - padT - padB;
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var yv = padT + barH * (1 - f);
      svg.appendChild(svgEl("line", {
        x1: padL - 4, y1: yv, x2: W - padR, y2: yv,
        stroke: "var(--muted)", "stroke-width": 0.5, "stroke-dasharray": "2,2",
      }));
      var t = svgEl("text", {
        x: padL - 6, y: yv + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 9,
      });
      t.textContent = f.toFixed(0) === "1" ? maxVal.toFixed(0) : (f * maxVal).toFixed(0);
      svg.appendChild(t);
    });
    data.forEach(function (d, i) {
      var gx0 = padL + i * (totalBw + gap);
      var cx = gx0 + totalBw / 2;
      groups.forEach(function (g, gi) {
        var v = d[g.key] || 0;
        var bH = (v / maxVal) * barH;
        if (bH > 0) {
          svg.appendChild(svgEl("rect", {
            x: gx0 + gi * bw, y: padT + barH - bH, width: bw - 1, height: bH, fill: g.color,
          }));
        }
      });
      var lab = svgEl("text", {
        x: cx, y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + cx + " " + (H - padB + 14) + ")",
      });
      lab.textContent = labels[i];
      svg.appendChild(lab);
    });
    var legY = padT - 2;
    groups.forEach(function (g, gi) {
      var legX = padL + gi * 80;
      svg.appendChild(svgEl("rect", { x: legX, y: legY - 7, width: 12, height: 8, fill: g.color }));
      var lt = svgEl("text", { x: legX + 15, y: legY, fill: "var(--ink)", "font-size": 10 });
      lt.textContent = g.label;
      svg.appendChild(lt);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  // ── section heading helper ────────────────────────────────────────────────────
  function sectionHead(text) {
    var h = document.createElement("h3");
    h.className = "trend-section";
    h.textContent = text;
    box.appendChild(h);
  }

  // ── main ─────────────────────────────────────────────────────────────────────
  var target = box.dataset.target;
  fetch("/api/trend?target=" + encodeURIComponent(target || ""))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var labels = shortLabels(data.versions);

      // ── focus-activity finish movement ────────────────────────────────────────
      if (data.target && data.target.finishes && data.target.finishes.some(function (f) { return f; })) {
        var fin = data.target.finishes.map(function (f) { return f ? Date.parse(f) / 86400000 : null; });
        var fbase = null;
        fin.forEach(function (v) { if (fbase == null && v != null) fbase = v; });
        lineChart(
          "UID " + data.target.uid + (data.target.name ? " — " + data.target.name : "") + " finish (days vs first)",
          labels,
          fin.map(function (v) { return v == null ? null : v - fbase; }),
          function (v, i) { return data.target.finishes[i] || "n/a"; },
          "var(--focus)"
        );
      }

      // ── PBIX p3 / existing: headline finish + quality ─────────────────────────
      sectionHead("Schedule progress");
      var finishDays = data.versions.map(function (v) { return Date.parse(v.finish) / 86400000; });
      var base = finishDays[0];
      lineChart(
        "Project finish (days vs first version)",
        labels,
        finishDays.map(function (d) { return d - base; }),
        function (v, i) { return data.versions[i].finish; },
        "var(--accent)"
      );
      lineChart("Completed activities", labels,
        data.versions.map(function (v) { return v.completed; }),
        function (v) { return String(v); }, "var(--ok)");
      lineChart("Critical (incomplete) activities", labels,
        data.versions.map(function (v) { return v.critical; }),
        function (v) { return String(v); }, "var(--bad)");
      var ml = data.quality.missing_logic;
      if (ml) {
        lineChart("Missing logic (activities)", labels, ml.values,
          function (v) { return String(v); }, "var(--warn)");
      }

      // ── PBIX p4 — Cross File Comparison ───────────────────────────────────────
      var hasP4 = data.versions.length && data.versions[0].status_split;
      if (hasP4) {
        sectionHead("Cross File Comparison (PBIX page 4)");

        // Activity Status by version: complete / in-progress / planned
        stackedBarChart(
          "Activity Status by Data Date",
          labels,
          data.versions.map(function (v) { return v.status_split || {}; }),
          [
            { key: "complete",    label: "Complete",     color: "var(--ok)" },
            { key: "in_progress", label: "In Progress",  color: "var(--warn)" },
            { key: "planned",     label: "Planned",      color: "var(--accent)" },
          ]
        );

        // Activity Type by version: milestones / normal / summaries
        stackedBarChart(
          "Activity Type by Data Date",
          labels,
          data.versions.map(function (v) { return v.makeup || {}; }),
          [
            { key: "milestones", label: "Milestone",  color: "var(--focus)" },
            { key: "normal",     label: "Normal",     color: "var(--accent)" },
            { key: "summaries",  label: "Summary",    color: "var(--muted)" },
          ]
        );

        // Completion Performance (ahead/on-schedule/behind)
        stackedBarChart(
          "Completion Performance by Data Date",
          labels,
          data.versions.map(function (v) { return v.completion_perf || {}; }),
          [
            { key: "ahead",       label: "Ahead",       color: "var(--ok)" },
            { key: "on_schedule", label: "On Schedule",  color: "var(--accent)" },
            { key: "behind",      label: "Behind",       color: "var(--bad)" },
          ]
        );

        // MEI / BEI / EPI multi-line
        var idxSeries = [
          { key: "mei", label: "MEI", color: "var(--ok)" },
          { key: "bei", label: "BEI", color: "var(--warn)" },
          { key: "epi", label: "EPI", color: "var(--accent)" },
        ].filter(function (s) {
          return data.versions.some(function (v) {
            return v.indices && v.indices[s.key] != null;
          });
        }).map(function (s) {
          return {
            label: s.label,
            color: s.color,
            values: data.versions.map(function (v) {
              return v.indices ? v.indices[s.key] : null;
            }),
          };
        });
        if (idxSeries.length) {
          multiLineChart("MEI / BEI / EPI across versions", labels, idxSeries);
        }

        // Start-to-Finish Ratio
        var sfrVals = data.versions.map(function (v) {
          return v.indices ? v.indices.sfr : null;
        });
        if (sfrVals.some(function (v) { return v != null; })) {
          lineChart(
            "Start-to-Finish Ratio across versions",
            labels, sfrVals,
            function (v) { return v.toFixed(2); },
            "var(--focus)"
          );
        }
      }

      // ── PBIX p5 — Float Analysis ──────────────────────────────────────────────
      var hasP5 = data.versions.length && data.versions[0].float_sums;
      if (hasP5) {
        sectionHead("Float Analysis (PBIX page 5)");

        // TotalFloatSum + FreeFloatSum grouped bar
        groupedBarChart(
          "Float Sums by Version (working days)",
          labels,
          data.versions.map(function (v) { return v.float_sums || {}; }),
          [
            { key: "total_days", label: "Total Float", color: "var(--accent)" },
            { key: "free_days",  label: "Free Float",  color: "var(--ok)" },
          ]
        );

        // % Total Float by band (0, <5, <10) as grouped bar
        groupedBarChart(
          "% Total Float by Days (0 / <5 / <10)",
          labels,
          data.versions.map(function (v) {
            var fb = v.float_bands || {};
            return {
              t0:   (fb.float_total_0   || {}).pct || 0,
              t5:   (fb.float_total_lt5  || {}).pct || 0,
              t10:  (fb.float_total_lt10 || {}).pct || 0,
            };
          }),
          [
            { key: "t0",  label: "0 days",  color: "var(--bad)" },
            { key: "t5",  label: "<5 days", color: "var(--warn)" },
            { key: "t10", label: "<10 days", color: "var(--accent)" },
          ]
        );

        // % Free Float by band
        groupedBarChart(
          "% Free Float by Days (0 / <5 / <10)",
          labels,
          data.versions.map(function (v) {
            var fb = v.float_bands || {};
            return {
              f0:  (fb.float_free_0   || {}).pct || 0,
              f5:  (fb.float_free_lt5  || {}).pct || 0,
              f10: (fb.float_free_lt10 || {}).pct || 0,
            };
          }),
          [
            { key: "f0",  label: "0 days",  color: "var(--bad)" },
            { key: "f5",  label: "<5 days", color: "var(--warn)" },
            { key: "f10", label: "<10 days", color: "var(--accent)" },
          ]
        );
      }
    })
    .catch(function () { box.textContent = "Failed to load trend data."; });
})();
