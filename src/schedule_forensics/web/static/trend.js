/* Schedule Forensics — cross-version trend charts (PBIX pages 4 + 5).
 *
 * Dependency-free SVG charts (no CDN, no external fetch — air-gap posture). Data comes from
 * /api/trend. Every chart carries a legend and a one-line description of what it conveys, and
 * thins its x-axis labels so they never overlap (readable on 10+ version workbooks).
 *
 * Trends-animation package: every chart also carries Mission-Control-style controls — a
 * ⛶ Enlarge and ▦ Data toggle, and (with 2+ files loaded) a ‹ Prev / ▶ Play / Next › stepper
 * that progressively reveals the versions on a LOCKED axis with a "file X of N — name
 * (data date …)" provenance label. A page-level ▶ Play all / ⏭ Step all (#sfPlayAll /
 * #sfStepAll) advances every stepper in lockstep, exactly like mission.js on the wall.
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

  // Axis labels for the versions. Prefer the DATA DATE (short, uniform, and the very order
  // the versions are sorted by) so a 10+ version workbook never collapses into an unreadable
  // smear of long filenames. Only when no version carries a data date do we fall back to the
  // filenames, stripping the long common prefix so the remaining text doesn't overlap.
  function shortLabels(versions) {
    if (versions.some(function (v) { return v.status_date; })) {
      return versions.map(function (v, i) { return v.status_date || "v" + (i + 1); });
    }
    var labels = versions.map(function (v) { return v.label; });
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
      if (!s) return "v" + (i + 1);
      if (cut) s = "…" + s;
      return s.length > 16 ? s.slice(0, 15) + "…" : s;
    });
  }

  // ── Trends-animation package: Mission-Control-style per-chart controls ────────
  // Every chart gets the wall's ⛶ Enlarge (tile-expand → tile-expanded) and ▦ Data
  // (tile-data → show-data) toggles, plus — because these charts plot VERSION-INDEXED
  // series (x axis = one point per loaded file) — a ‹ Prev / ▶ Play / Next › stepper that
  // progressively REVEALS versions on a LOCKED x-axis: frame k shows files 1…k+1 and the
  // axis never rescales, so movement is visible frame to frame. A provenance label names
  // frame k's file ("file X of N — name (data date …)"). Play honors
  // prefers-reduced-motion (one frame per press, no timer), and the master "Play all"
  // (mission.js on the wall, #sfPlayAll here) clicks every .sf-frame-next so all the
  // animated visuals advance in lockstep.
  var SF_REDUCED =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SF_ON_WALL = !!document.getElementById("missionGrid");
  var sfMeta = null; // { n, names, dates } — the loaded files, set from /api/trend versions

  function sfCaption(k, n, name, date) {
    var src = String(name || "v" + (k + 1)) + (date ? " (data date " + date + ")" : "");
    return n > 1 ? "file " + (k + 1) + " of " + n + " — " + src : "Source: " + src;
  }

  // the current frame's version, marked on the locked axis (a dashed vertical guide)
  function sfFrameGuide(gx, y1, y2) {
    return svgEl("line", {
      x1: gx, y1: y1, x2: gx, y2: y2, stroke: "var(--focus)", "stroke-width": 1.5,
      "stroke-dasharray": "3 3", "class": "sf-frame-guide",
    });
  }

  // frames descriptor for a version-indexed chart (progressive reveal on a locked axis)
  function sfFrames(draw) {
    if (!sfMeta || sfMeta.n < 2) return null;
    return {
      n: sfMeta.n,
      name: function (k) { return sfMeta.names[k]; },
      date: function (k) { return sfMeta.dates[k]; },
      draw: draw,
    };
  }

  // single-file provenance ("Source: <name>") when there is nothing to step through
  function sfSource() {
    return sfMeta && sfMeta.n === 1 ? { name: sfMeta.names[0], date: sfMeta.dates[0] } : null;
  }

  // Attach the Mission-Control-style control row to a chart. host gets the state classes
  // (tile-expanded / show-data); mount(bar) places the row; opts = { data, frames, source }.
  function sfChartControls(host, mount, opts) {
    var bar = document.createElement("div");
    bar.className = "viz-controls sf-chart-controls";
    function btn(cls, text, title) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = cls;
      b.textContent = text;
      if (title) b.title = title;
      bar.appendChild(b);
      return b;
    }
    if (!SF_ON_WALL) { // on the Mission wall the tile header already carries these
      var big = btn("tile-expand", "⛶ Enlarge", "Enlarge / shrink this chart");
      big.setAttribute("aria-pressed", "false");
      big.addEventListener("click", function (e) {
        e.stopPropagation(); // never reaches a surrounding tile's delegated handler
        var on = host.classList.toggle("tile-expanded");
        big.setAttribute("aria-pressed", on ? "true" : "false");
        big.textContent = on ? "⛶ Shrink" : "⛶ Enlarge";
        if (on && host.scrollIntoView) host.scrollIntoView({ block: "nearest" });
      });
      if (opts.data) {
        var dat = btn("tile-data", "▦ Data", "Show / hide the underlying data table");
        dat.setAttribute("aria-pressed", "false");
        dat.addEventListener("click", function (e) {
          e.stopPropagation();
          var on = host.classList.toggle("show-data");
          dat.setAttribute("aria-pressed", on ? "true" : "false");
          dat.textContent = on ? "▦ Hide data" : "▦ Data";
        });
      }
    }
    var label = document.createElement("span");
    label.className = "sf-frame-label muted";
    label.setAttribute("data-no-i18n", ""); // file names / dates — never machine-translated
    var frames = opts.frames;
    if (!frames) {
      if (opts.source) { // single file → provenance only, no stepper
        label.textContent = sfCaption(0, 1, opts.source.name, opts.source.date);
        bar.appendChild(label);
      }
      if (bar.firstChild) mount(bar);
      return;
    }
    var idx = frames.n - 1; // start fully revealed (= the classic all-versions chart)
    var timer = null;
    var prev = btn("sf-frame-prev", "‹ Prev", "Previous file");
    bar.appendChild(label);
    var next = btn("sf-frame-next", "Next ›", "Next file");
    var play = btn("sf-frame-play", "▶ Play", "Animate through the loaded files");
    function show(k) {
      idx = (k + frames.n) % frames.n;
      label.textContent = sfCaption(idx, frames.n, frames.name(idx), frames.date(idx));
      frames.draw(idx);
    }
    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
      play.textContent = "▶ Play";
    }
    prev.addEventListener("click", function () { stop(); show(idx - 1); });
    next.addEventListener("click", function () { stop(); show(idx + 1); });
    play.addEventListener("click", function () {
      if (timer) { stop(); return; }
      if (SF_REDUCED) { show(idx + 1); return; } // reduced motion: one frame per press
      show(idx + 1);
      timer = setInterval(function () { show(idx + 1); }, 1600);
      play.textContent = "⏸ Stop";
    });
    show(idx);
    mount(bar);
  }

  // master "Play all / Step all" for the whole Trends page (the mission.js pattern): one
  // beat clicks every per-chart Next (.sf-frame-next — trend, margin) plus the quality
  // drill-down's #qualNext, so the entire page animates through the files in lockstep.
  function sfMasterBar() {
    if (SF_ON_WALL || document.getElementById("sfPlayAll")) return;
    if (!sfMeta || sfMeta.n < 2) return;
    var panel = box.closest ? box.closest(".panel") : null;
    if (!panel || !panel.parentNode) return;
    var bar = document.createElement("div");
    bar.className = "panel viz-controls sf-master-controls";
    function mkBtn(id, text) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = id;
      b.textContent = text;
      bar.appendChild(b);
      return b;
    }
    var play = mkBtn("sfPlayAll", "▶ Play all");
    var stepBtn = mkBtn("sfStepAll", "⏭ Step all");
    var note = document.createElement("span");
    note.className = "muted";
    note.textContent =
      "Animate every chart on this page through the loaded files in lockstep (one beat per file).";
    bar.appendChild(note);
    var timer = null;
    function stepAll() {
      Array.prototype.forEach.call(
        document.querySelectorAll(".sf-frame-next"),
        function (b) { b.click(); }
      );
      var q = document.getElementById("qualNext"); // the quality drill-down joins the beat
      if (q) q.click();
    }
    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
      play.textContent = "▶ Play all";
    }
    play.addEventListener("click", function () {
      if (timer) { stop(); return; }
      if (SF_REDUCED) { stepAll(); return; } // reduced motion: advance one frame per press
      stepAll();
      timer = setInterval(stepAll, 1600);
      play.textContent = "⏸ Pause all";
    });
    stepBtn.addEventListener("click", stepAll);
    panel.parentNode.insertBefore(bar, panel);
  }

  // ── helpers ──────────────────────────────────────────────────────────────────

  function xTick(i, n, W, padL, padR) {
    return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1));
  }

  // one x-axis label every `step` so they never overlap (rotated -35° for legibility)
  function labelStep(n) { return Math.max(1, Math.ceil(n / 14)); }

  function chartWrap(title, desc) {
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    if (desc) {
      var p = document.createElement("p");
      p.className = "chart-desc";
      p.textContent = desc;
      wrap.appendChild(p);
    }
    return wrap;
  }

  // a small color-key legend row appended under the chart (rect/line swatch + label)
  function legend(wrap, items) {
    var row = document.createElement("div");
    row.className = "chart-legend";
    items.forEach(function (it) {
      var sw = document.createElement("span");
      sw.className = "chart-swatch";
      sw.style.background = it.color;
      if (it.dashed) sw.classList.add("dashed");
      var lab = document.createElement("span");
      lab.textContent = it.label;
      var cell = document.createElement("span");
      cell.className = "chart-legend-item";
      cell.appendChild(sw);
      cell.appendChild(lab);
      row.appendChild(cell);
    });
    wrap.appendChild(row);
  }

  // One line chart: values per version; null = no data (never fabricated as 0).
  function lineChart(title, labels, values, valueText, color, desc, seriesLabel) {
    var W = 460, H = 210, padL = 14, padR = 14, padT = 26, padB = 54;
    var known = values.filter(function (v) { return v != null; });
    if (!known.length) return;
    var wrap = chartWrap(title, desc);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, title);
    var lo = Math.min.apply(null, known), hi = Math.max.apply(null, known);
    if (lo === hi) { lo -= 1; hi += 1; }
    var n = values.length;
    var step = labelStep(n);
    var x = function (i) { return xTick(i, n, W, padL, padR); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    // static x-axis labels — the version axis is LOCKED across animation frames
    values.forEach(function (v, i) {
      if (i % step === 0) {
        var lab = svgEl("text", {
          x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
        });
        lab.textContent = labels[i];
        svg.appendChild(lab);
      }
    });
    // the data layer, re-drawn per frame: frame k reveals versions 0…k on the locked axis
    var layer = svgEl("g", { "class": "sf-frame-layer" });
    svg.appendChild(layer);
    function drawData(k) {
      while (layer.firstChild) layer.removeChild(layer.firstChild);
      var pts = [];
      values.forEach(function (v, i) { if (v != null && i <= k) pts.push(x(i) + "," + y(v)); });
      layer.appendChild(svgEl("polyline", {
        points: pts.join(" "), fill: "none", stroke: color, "stroke-width": 2.5,
        "class": "sf-curve-line", pathLength: "1",
      }));
      values.forEach(function (v, i) {
        if (v == null || i > k) return;
        var dot = svgEl("circle", { cx: x(i), cy: y(v), r: i === k ? 5 : 4, fill: color });
        var dtt = svgEl("title", {});  // hover call-out (same as the top tiles' charts)
        dtt.textContent =
          labels[i] + " · " + (seriesLabel || title.split(" (")[0]) + ": " + valueText(v, i);
        dot.appendChild(dtt);
        layer.appendChild(dot);
        var val = svgEl("text", {
          x: x(i), y: y(v) - 9, "text-anchor": "middle", fill: "var(--ink)", "font-size": 12,
        });
        val.textContent = valueText(v, i);
        layer.appendChild(val);
      });
      if (sfMeta && sfMeta.n > 1) layer.appendChild(sfFrameGuide(x(k), padT, H - padB));
    }
    wrap.appendChild(svg);
    legend(wrap, [{ color: color, label: seriesLabel || title.split(" (")[0] }]);
    if (window.SFA11y) {
      wrap.appendChild(SFA11y.table(
        title + " — data",
        ["Version", seriesLabel || title.split(" (")[0]],
        labels.map(function (l, i) {
          return [l, values[i] == null ? "" : valueText(values[i], i)];
        })
      ));
    }
    var frames = sfFrames(drawData);
    if (!frames) drawData(n - 1);
    sfChartControls(wrap, function (bar) { wrap.insertBefore(bar, svg); }, {
      data: !!window.SFA11y, frames: frames, source: sfSource(),
    });
    box.appendChild(wrap);
  }

  // Multi-line chart: series is [{label, values, color}].
  function multiLineChart(title, labels, series, desc) {
    var W = 460, H = 210, padL = 14, padR = 14, padT = 26, padB = 54;
    var allVals = [];
    series.forEach(function (s) {
      s.values.forEach(function (v) { if (v != null) allVals.push(v); });
    });
    if (!allVals.length) return;
    var wrap = chartWrap(title, desc);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, title);
    var lo = Math.min.apply(null, allVals), hi = Math.max.apply(null, allVals);
    if (lo === hi) { lo -= 0.05; hi += 0.05; }
    var n = labels.length;
    var step = labelStep(n);
    var x = function (i) { return xTick(i, n, W, padL, padR); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    // static x-axis labels — the version axis is LOCKED across animation frames
    labels.forEach(function (l, i) {
      if (i % step !== 0) return;
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
      });
      lab.textContent = l;
      svg.appendChild(lab);
    });
    // the data layer, re-drawn per frame: frame k reveals versions 0…k on the locked axis
    var layer = svgEl("g", { "class": "sf-frame-layer" });
    svg.appendChild(layer);
    function drawData(k) {
      while (layer.firstChild) layer.removeChild(layer.firstChild);
      series.forEach(function (s) {
        var pts = [];
        s.values.forEach(function (v, i) { if (v != null && i <= k) pts.push(x(i) + "," + y(v)); });
        if (pts.length) {
          layer.appendChild(svgEl("polyline", {
            points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2.5,
            "class": "sf-curve-line", pathLength: "1",
          }));
        }
        s.values.forEach(function (v, i) {
          if (v != null && i <= k) {
            var dot = svgEl("circle", { cx: x(i), cy: y(v), r: i === k ? 5 : 4, fill: s.color });
            var dtt = svgEl("title", {});  // hover call-out
            dtt.textContent = labels[i] + " · " + s.label + ": " + v.toFixed(2);
            dot.appendChild(dtt);
            layer.appendChild(dot);
            var val = svgEl("text", {
              x: x(i), y: y(v) - 8, "text-anchor": "middle", fill: "var(--ink)", "font-size": 10,
            });
            val.textContent = v.toFixed(2);
            layer.appendChild(val);
          }
        });
      });
      if (sfMeta && sfMeta.n > 1) layer.appendChild(sfFrameGuide(x(k), padT, H - padB));
    }
    wrap.appendChild(svg);
    legend(wrap, series.map(function (s) { return { color: s.color, label: s.label }; }));
    if (window.SFA11y) {
      wrap.appendChild(SFA11y.table(
        title + " — data",
        ["Version"].concat(series.map(function (s) { return s.label; })),
        labels.map(function (l, i) {
          return [l].concat(series.map(function (s) {
            return s.values[i] == null ? "" : s.values[i].toFixed(2);
          }));
        })
      ));
    }
    var frames = sfFrames(drawData);
    if (!frames) drawData(n - 1);
    sfChartControls(wrap, function (bar) { wrap.insertBefore(bar, svg); }, {
      data: !!window.SFA11y, frames: frames, source: sfSource(),
    });
    box.appendChild(wrap);
  }

  // Signed variance trend (handbook Figs 7-12/7-13): one value per version on a zero-baselined
  // axis with a shaded favorable (>= 0, ahead) band above and unfavorable (< 0, behind) band
  // below; markers/labels colored by sign. Used for SVt (working days). `unit` suffixes the labels.
  function varianceTrendChart(title, labels, values, desc, unit) {
    var W = 460, H = 210, padL = 30, padR = 14, padT = 26, padB = 54;
    var present = values.filter(function (v) { return v != null; });
    if (!present.length) return;
    var suffix = unit ? (" " + unit) : "";
    var wrap = chartWrap(title, desc);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, title);
    // always include zero so the favorable/unfavorable split is meaningful
    var lo = Math.min(0, Math.min.apply(null, present));
    var hi = Math.max(0, Math.max.apply(null, present));
    if (lo === hi) { lo -= 1; hi += 1; }
    var n = labels.length;
    var step = labelStep(n);
    var x = function (i) { return xTick(i, n, W, padL, padR); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    var zeroY = y(0);
    var right = W - padR;
    // favorable band (above zero) and unfavorable band (below zero), faint tints
    svg.appendChild(svgEl("rect", {
      x: padL, y: padT, width: right - padL, height: Math.max(0, zeroY - padT),
      fill: "var(--ok)", opacity: 0.08,
    }));
    svg.appendChild(svgEl("rect", {
      x: padL, y: zeroY, width: right - padL, height: Math.max(0, H - padB - zeroY),
      fill: "var(--bad)", opacity: 0.08,
    }));
    // zero baseline
    svg.appendChild(svgEl("line", {
      x1: padL, y1: zeroY, x2: right, y2: zeroY, stroke: "var(--ink)", "stroke-width": 1,
      "stroke-dasharray": "4 3",
    }));
    // y labels: hi / 0 / lo
    [hi, 0, lo].forEach(function (v) {
      var lab = svgEl("text", {
        x: padL - 4, y: y(v) + 3, "text-anchor": "end", fill: "var(--muted)", "font-size": 9,
      });
      lab.textContent = (v > 0 ? "+" : "") + Math.round(v);
      svg.appendChild(lab);
    });
    // static x-axis labels — the version axis is LOCKED across animation frames
    labels.forEach(function (l, i) {
      if (i % step !== 0) return;
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
        transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
      });
      lab.textContent = l;
      svg.appendChild(lab);
    });
    // the SVt line + markers, re-drawn per frame (frame k reveals versions 0…k)
    var layer = svgEl("g", { "class": "sf-frame-layer" });
    svg.appendChild(layer);
    function drawData(k) {
      while (layer.firstChild) layer.removeChild(layer.firstChild);
      var pts = [];
      values.forEach(function (v, i) { if (v != null && i <= k) pts.push(x(i) + "," + y(v)); });
      if (pts.length > 1) {
        layer.appendChild(svgEl("polyline", {
          points: pts.join(" "), fill: "none", stroke: "var(--accent)", "stroke-width": 2.5,
          "class": "sf-curve-line", pathLength: "1",
        }));
      }
      // markers + value labels, green when ahead (>= 0) / red when behind (< 0)
      values.forEach(function (v, i) {
        if (v == null || i > k) return;
        var color = v >= 0 ? "var(--ok)" : "var(--bad)";
        layer.appendChild(svgEl("circle", { cx: x(i), cy: y(v), r: i === k ? 5 : 4, fill: color }));
        var val = svgEl("text", {
          x: x(i), y: y(v) - 8, "text-anchor": "middle", fill: "var(--ink)", "font-size": 10,
        });
        val.textContent = (v > 0 ? "+" : "") + v + suffix;
        layer.appendChild(val);
      });
      if (sfMeta && sfMeta.n > 1) layer.appendChild(sfFrameGuide(x(k), padT, H - padB));
    }
    wrap.appendChild(svg);
    legend(wrap, [
      { color: "var(--ok)", label: "Ahead (favorable)" },
      { color: "var(--bad)", label: "Behind (unfavorable)" },
    ]);
    if (window.SFA11y) {
      wrap.appendChild(SFA11y.table(
        title + " — data",
        ["Version", "SVt" + (unit ? (" (" + unit + ")") : "")],
        labels.map(function (l, i) {
          return [l, values[i] == null ? "" : ((values[i] > 0 ? "+" : "") + values[i])];
        })
      ));
    }
    var frames = sfFrames(drawData);
    if (!frames) drawData(n - 1);
    sfChartControls(wrap, function (bar) { wrap.insertBefore(bar, svg); }, {
      data: !!window.SFA11y, frames: frames, source: sfSource(),
    });
    box.appendChild(wrap);
  }

  // Stacked bar chart: segments is [{key, label, color}]; data is array of objects.
  function stackedBarChart(title, labels, data, segments, desc) {
    var W = 460, H = 220, padL = 34, padR = 14, padT = 26, padB = 54;
    var maxTotal = 0;
    data.forEach(function (d) {
      var tot = 0;
      segments.forEach(function (s) { tot += (d[s.key] || 0); });
      if (tot > maxTotal) maxTotal = tot;
    });
    if (!maxTotal) return;
    var wrap = chartWrap(title, desc);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, title);
    var n = data.length;
    var step = labelStep(n);
    var bw = Math.max(8, (W - padL - padR) / (n * 1.6) | 0);
    var gap = (W - padL - padR - n * bw) / Math.max(n - 1, 1);
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
      t.textContent = Math.round(f * maxTotal);
      svg.appendChild(t);
    });
    // static x-axis labels — the version axis is LOCKED across animation frames
    data.forEach(function (d, i) {
      if (i % step === 0) {
        var cx = padL + i * (bw + gap) + bw / 2;
        var lab = svgEl("text", {
          x: cx, y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + cx + " " + (H - padB + 14) + ")",
        });
        lab.textContent = labels[i];
        svg.appendChild(lab);
      }
    });
    // the bars, re-drawn per frame: frame k reveals versions 0…k on the locked axis
    var layer = svgEl("g", { "class": "sf-frame-layer" });
    svg.appendChild(layer);
    function drawData(k) {
      while (layer.firstChild) layer.removeChild(layer.firstChild);
      data.forEach(function (d, i) {
        if (i > k) return;
        var cx = padL + i * (bw + gap) + bw / 2;
        var yBase = padT + barH;
        segments.forEach(function (s) {
          var v = d[s.key] || 0;
          if (!v) return;
          var bH = (v / maxTotal) * barH;
          layer.appendChild(svgEl("rect", {
            x: cx - bw / 2, y: yBase - bH, width: bw, height: bH, fill: s.color,
          }));
          yBase -= bH;
        });
      });
      if (sfMeta && sfMeta.n > 1) {
        layer.appendChild(sfFrameGuide(padL + k * (bw + gap) + bw / 2, padT, padT + barH));
      }
    }
    wrap.appendChild(svg);
    legend(wrap, segments.map(function (s) { return { color: s.color, label: s.label }; }));
    if (window.SFA11y) {
      wrap.appendChild(SFA11y.table(
        title + " — data",
        ["Version"].concat(segments.map(function (s) { return s.label; })),
        labels.map(function (l, i) {
          return [l].concat(segments.map(function (s) { return data[i][s.key] || 0; }));
        })
      ));
    }
    var frames = sfFrames(drawData);
    if (!frames) drawData(n - 1);
    sfChartControls(wrap, function (bar) { wrap.insertBefore(bar, svg); }, {
      data: !!window.SFA11y, frames: frames, source: sfSource(),
    });
    box.appendChild(wrap);
  }

  // Grouped bar chart: groups is [{key, label, color}]; data is [{group values}] per version.
  function groupedBarChart(title, labels, data, groups, desc) {
    var W = 460, H = 220, padL = 34, padR = 14, padT = 26, padB = 54;
    var maxVal = 0;
    data.forEach(function (d) {
      groups.forEach(function (g) { if ((d[g.key] || 0) > maxVal) maxVal = d[g.key] || 0; });
    });
    if (!maxVal) return;
    var wrap = chartWrap(title, desc);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, title);
    var n = data.length, ng = groups.length;
    var step = labelStep(n);
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
    // static x-axis labels — the version axis is LOCKED across animation frames
    data.forEach(function (d, i) {
      if (i % step === 0) {
        var cx = padL + i * (totalBw + gap) + totalBw / 2;
        var lab = svgEl("text", {
          x: cx, y: H - padB + 14, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + cx + " " + (H - padB + 14) + ")",
        });
        lab.textContent = labels[i];
        svg.appendChild(lab);
      }
    });
    // the bars, re-drawn per frame: frame k reveals versions 0…k on the locked axis
    var layer = svgEl("g", { "class": "sf-frame-layer" });
    svg.appendChild(layer);
    function drawData(k) {
      while (layer.firstChild) layer.removeChild(layer.firstChild);
      data.forEach(function (d, i) {
        if (i > k) return;
        var gx0 = padL + i * (totalBw + gap);
        groups.forEach(function (g, gi) {
          var v = d[g.key] || 0;
          var bH = (v / maxVal) * barH;
          if (bH > 0) {
            layer.appendChild(svgEl("rect", {
              x: gx0 + gi * bw, y: padT + barH - bH, width: bw - 1, height: bH, fill: g.color,
            }));
          }
        });
      });
      if (sfMeta && sfMeta.n > 1) {
        layer.appendChild(sfFrameGuide(padL + k * (totalBw + gap) + totalBw / 2, padT, padT + barH));
      }
    }
    wrap.appendChild(svg);
    legend(wrap, groups.map(function (g) { return { color: g.color, label: g.label }; }));
    if (window.SFA11y) {
      wrap.appendChild(SFA11y.table(
        title + " — data",
        ["Version"].concat(groups.map(function (g) { return g.label; })),
        labels.map(function (l, i) {
          return [l].concat(groups.map(function (g) { return data[i][g.key] || 0; }));
        })
      ));
    }
    var frames = sfFrames(drawData);
    if (!frames) drawData(n - 1);
    sfChartControls(wrap, function (bar) { wrap.insertBefore(bar, svg); }, {
      data: !!window.SFA11y, frames: frames, source: sfSource(),
    });
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
      // the loaded files (in version order) — powers every chart's stepper + provenance label
      sfMeta = {
        n: data.versions.length,
        names: data.versions.map(function (v) { return v.label; }),
        dates: data.versions.map(function (v) { return v.status_date || ""; }),
      };

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
          "var(--focus)",
          "The focus activity's computed finish across the versions, in days relative to the first version (0 = same as first; positive = later).",
          "Focus finish (Δdays)"
        );
      }

      // ── PBIX p3 / existing: headline finish + quality ─────────────────────────
      sectionHead("Schedule progress");
      var finishDays = data.versions.map(function (v) { return Date.parse(v.finish) / 86400000; });
      var base = null;
      finishDays.forEach(function (d) { if (base == null && !isNaN(d)) base = d; });
      lineChart(
        "Project finish (days vs first version)",
        labels,
        finishDays.map(function (d) { return base == null || isNaN(d) ? null : d - base; }),
        function (v, i) { return data.versions[i].finish; },
        "var(--accent)",
        "How the computed project finish moves across versions, in days relative to the first version. A rising line is a slipping finish.",
        "Project finish (Δdays)"
      );
      lineChart("Completed activities", labels,
        data.versions.map(function (v) { return v.completed; }),
        function (v) { return String(v); }, "var(--ok)",
        "Count of activities reported 100% complete in each version (work delivered over time).",
        "Completed");
      lineChart("Critical (incomplete) activities", labels,
        data.versions.map(function (v) { return v.critical; }),
        function (v) { return String(v); }, "var(--bad)",
        "Count of incomplete activities on the critical path (total float ≤ 0) per version — the size of the at-risk path.",
        "Critical");
      var ml = data.quality.missing_logic;
      if (ml) {
        lineChart("Missing logic (activities)", labels, ml.values,
          function (v) { return String(v); }, "var(--warn)",
          "Activities missing a predecessor or successor link (DCMA open-ends) per version — lower is better.",
          "Missing logic");
      }

      // ── PBIX p4 — Cross File Comparison ───────────────────────────────────────
      var hasP4 = data.versions.length && data.versions[0].status_split;
      if (hasP4) {
        sectionHead("Cross File Comparison (PBIX page 4)");

        stackedBarChart(
          "Activity Status by Data Date",
          labels,
          data.versions.map(function (v) { return v.status_split || {}; }),
          [
            { key: "complete",    label: "Complete",     color: "var(--ok)" },
            { key: "in_progress", label: "In Progress",  color: "var(--warn)" },
            { key: "planned",     label: "Planned",      color: "var(--accent)" },
          ],
          "Each version's activities split into complete / in-progress / planned (stacked to the total) — the makeup shifting toward 'complete' is healthy progress."
        );

        stackedBarChart(
          "Activity Type by Data Date",
          labels,
          data.versions.map(function (v) { return v.makeup || {}; }),
          [
            { key: "milestones", label: "Milestone",  color: "var(--focus)" },
            { key: "normal",     label: "Normal",     color: "var(--accent)" },
            { key: "summaries",  label: "Summary",    color: "var(--muted)" },
          ],
          "The activity-type makeup (milestones / normal tasks / summaries) per version — a sudden change can signal a re-baseline or restructure."
        );

        stackedBarChart(
          "Completion Performance by Data Date",
          labels,
          data.versions.map(function (v) { return v.completion_perf || {}; }),
          [
            { key: "ahead",       label: "Ahead",       color: "var(--ok)" },
            { key: "on_schedule", label: "On Schedule",  color: "var(--accent)" },
            { key: "behind",      label: "Behind",       color: "var(--bad)" },
          ],
          "Of the completed activities, how many finished ahead / on / behind their baseline, per version — a growing 'behind' band is slippage being realized."
        );

        // Handbook Fig. 7-21 "are we executing the plan?" — the three headline execution indices
        // (BEI cumulative, CEI this-period forecast, HMI this-period baseline) overlaid on ONE
        // axis for an at-a-glance read, before the per-family index charts below.
        var execSeries = [
          { key: "bei", label: "BEI", color: "var(--warn)" },
          { key: "cei_tasks", label: "CEI", color: "var(--accent)" },
          { key: "hmi_tasks", label: "HMI", color: "var(--ok)" },
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
        if (execSeries.length) {
          multiLineChart("Execution indices — BEI / CEI / HMI (are we executing the plan?)", labels, execSeries,
            "The handbook's combined execution panel (Fig. 7-21): BEI (cumulative baseline execution), CEI (this period's forecast execution), and HMI (this period's baseline execution) on one axis. At or above 1.0 is on-plan; all three falling together is systemic slippage, while BEI healthy but CEI/HMI sagging is recent erosion the cumulative index has not caught up to yet.");
        }

        // Handbook Figs 7-12/7-13: the SVt (Earned-Schedule time variance) trend, zero-baselined
        // with favorable/unfavorable bands, so accumulating slip across submissions reads at a glance.
        var svtValues = data.versions.map(function (v) {
          return v.svt_days == null ? null : v.svt_days;
        });
        if (svtValues.some(function (v) { return v != null; })) {
          varianceTrendChart("Schedule variance (SVt) across versions", labels, svtValues,
            "SVt = ES − AT in working days per version (the count-based Earned-Schedule time variance). Above the zero line is ahead of plan (favorable); below is behind (unfavorable). A line trending downward across submissions is accumulating schedule slip.",
            "wd");
        }

        // Schedule-health indices — one chart PER index (operator #71). These four indices carry
        // different scales/meanings, so a shared axis obscured each series; separate small charts
        // keep every trend legible. (The BEI/CEI/HMI execution panel above stays combined by
        // design — it mirrors the handbook's Fig 7-21 single-axis execution view.)
        [
          { key: "mei", label: "MEI (milestone execution)", color: "var(--ok)",
            desc: "Milestone Execution Index per version: of the milestones baselined to finish by the data date, the share actually finished. Near or above 1.0 is on-plan." },
          { key: "bei", label: "BEI (baseline execution)", color: "var(--warn)",
            desc: "Baseline Execution Index per version: tasks completed vs the tasks the baseline placed on or before the data date. Near or above 1.0 is on-plan." },
          { key: "epi", label: "EPI (execution performance)", color: "var(--accent)",
            desc: "Execution Performance Index per version: how completed work is tracking against plan. Near or above 1.0 is on-plan." },
          { key: "bri", label: "BRI (baseline realism)", color: "var(--bad)",
            desc: "Baseline Realism Index per version: of what was baselined-due, how much actually finished. Near or above 1.0 means the baseline was realistic." },
        ].forEach(function (s) {
          var values = data.versions.map(function (v) {
            return v.indices ? v.indices[s.key] : null;
          });
          if (values.some(function (v) { return v != null; })) {
            lineChart(s.label + " across versions", labels, values,
              function (v) { return v == null ? "—" : v.toFixed(2); }, s.color, s.desc, s.label);
          }
        });

        var feiSeries = [
          { key: "fei_starts", label: "FEI (Starts)", color: "var(--accent)" },
          { key: "fei_finish", label: "FEI (Finish)", color: "var(--warn)" },
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
        if (feiSeries.length) {
          multiLineChart("Forecast Execution Index (FEI) across versions", labels, feiSeries,
            "Forecast (to-go) execution vs the baseline for the REMAINING work: count of activities still forecast to start/finish ahead, over the count the baseline placed there. Above 1.0 means more work is forecast in the remaining window than baselined — a to-go bow wave.");
        }

        var hmiSeries = [
          { key: "hmi_tasks", label: "HMI (Tasks)", color: "var(--accent)" },
          { key: "hmi_milestones", label: "HMI (Milestones)", color: "var(--ok)" },
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
        if (hmiSeries.length) {
          multiLineChart("Hit or Miss Index (HMI) across periods", labels, hmiSeries,
            "Period-over-period baseline execution: of the activities the baseline placed to finish in each status period, the share that actually completed in it. The first version has no prior period. 1.0 = every commitment for that period was met.");
        }

        var ceiSeries = [
          { key: "cei_tasks", label: "CEI (Tasks)", color: "var(--accent)" },
          { key: "cei_milestones", label: "CEI (Milestones)", color: "var(--ok)" },
          { key: "cei_starts", label: "CEI (Starts)", color: "var(--warn)" },
          { key: "cei_critical", label: "Critical CEI", color: "var(--bad)" },
          { key: "cei_adjusted", label: "CEI (adjusted)", color: "var(--muted)" },
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
        if (ceiSeries.length) {
          multiLineChart("Current Execution Index (CEI) across periods", labels, ceiSeries,
            "Period-over-period forecast execution: of the activities the PRIOR schedule forecast to finish in each status period, the share that actually completed by the data date. The first version has no prior period. 1.0 = the team executed everything it last committed to.");
        }

        var floatRatioSeries = [
          { key: "float_ratio", label: "Float Ratio", color: "var(--accent)" },
          { key: "float_ratio_aggregate", label: "Float Ratio (aggregate)", color: "var(--muted)" },
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
        if (floatRatioSeries.length) {
          multiLineChart("Float Ratio™ across periods", labels, floatRatioSeries,
            "Average activity total float divided by remaining duration (the 'Float Ratio™' metric), over the normal planned/in-progress activities, scored per version so it reads period to period. Higher = more float per day of remaining work. Bands: <0.1 very tight, 0.1–0.3 tight, 0.3–0.6 healthy, >0.6 generous (check for missing logic). A falling ratio means the schedule is losing room; the solid line is the mean-of-ratios, the muted line the more outlier-robust ratio-of-means.");
        }

        var sfrVals = data.versions.map(function (v) {
          return v.indices ? v.indices.sfr : null;
        });
        if (sfrVals.some(function (v) { return v != null; })) {
          lineChart(
            "Start-to-Finish Ratio across versions",
            labels, sfrVals,
            function (v) { return v.toFixed(2); },
            "var(--focus)",
            "The ratio of activity starts to finishes per version — a sustained imbalance flags work starting faster than it finishes.",
            "Start/Finish ratio"
          );
        }
      }

      // ── PBIX p5 — Float Analysis ──────────────────────────────────────────────
      var hasP5 = data.versions.length && data.versions[0].float_sums;
      if (hasP5) {
        sectionHead("Float Analysis (PBIX page 5)");

        groupedBarChart(
          "Float Sums by Version (working days)",
          labels,
          data.versions.map(function (v) { return v.float_sums || {}; }),
          [
            { key: "total_days", label: "Total Float", color: "var(--accent)" },
            { key: "free_days",  label: "Free Float",  color: "var(--ok)" },
          ],
          "Total and free float summed across the schedule (working days) per version — shrinking float means a tightening, more fragile plan."
        );

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
          ],
          "Share of incomplete activities with low total float (0 / under 5 / under 10 working days) per version — more low-float work is more critical/near-critical exposure."
        );

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
          ],
          "Share of incomplete activities with low free float per version — free float is the tighter constraint, so a rising 0-day band is immediate downstream pressure."
        );
      }

      // master "Play all / Step all" for the whole Trends page (mission.js pattern)
      sfMasterBar();
    })
    .catch(function () { box.textContent = "Failed to load trend data."; });
})();
