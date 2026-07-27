/* Schedule Forensics — Finish & Slippage month curves (PBIX pages 6, 7, 12).
 *
 * Dependency-free SVG line charts (no CDN — air-gap posture). Three charts over the
 * shared month axis from /api/curves:
 *   • Finishes        — actual vs baseline finishes for the latest version (2 lines)
 *   • DATA Date Finishes — the per-version actual-finish curves
 *   • Slippage        — per version, a start curve (solid) and a finish curve (dashed)
 * The count axis of each chart is locked to that chart's own tallest point so the
 * curves never rescale misleadingly between series.
 *
 * Trends-animation package: with 2+ files loaded, the DATA Date Finishes and Slippage
 * charts no longer overlay every version at once — they ANIMATE, one file per frame, on a
 * date axis and count axis both HELD FIXED across frames (so curve movement is real
 * movement), with a ‹ Prev / ▶ Play / Next › stepper and a "file X of N — name (data
 * date …)" provenance label (Mission-Control conventions; reduced-motion respected). With
 * one file the classic single-version behavior is preserved. Every chart also gets the
 * wall's ⛶ Enlarge and ▦ Data toggles, and a ▶ Play all / ⏭ Step all pair (#sfPlayAll /
 * #sfStepAll) advances every stepper in lockstep like mission.js.
 */
"use strict";

(function () {
  var NS = "http://www.w3.org/2000/svg";
  var GOLD = "var(--warn)", BLUE = "var(--accent)";
  var gran = "month";     // time-scale granularity for the stacked tier axis: year | quarter | month
  var lastData = null;    // last fetched payload, so the granularity selector can re-render
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

  // ── Trends-animation package: Mission-Control-style per-chart controls ────────
  var SF_REDUCED =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SF_ON_WALL = !!document.getElementById("missionGrid");

  function sfCaption(k, n, name, date) {
    var src = String(name || "v" + (k + 1)) + (date ? " (data date " + date + ")" : "");
    return n > 1 ? "file " + (k + 1) + " of " + n + " — " + src : "Source: " + src;
  }

  // Wrap a chart host in a shell that carries the control row + the expand/data state
  // classes (the host's innards are wiped on every re-render, the shell survives).
  // Re-renders (hide-completed / granularity) drop the stale control row first.
  function sfShell(box) {
    if (!box || !box.parentNode) return null;
    var shell =
      box.parentNode.classList && box.parentNode.classList.contains("sf-tilebox")
        ? box.parentNode
        : null;
    if (!shell) {
      shell = document.createElement("div");
      shell.className = "sf-tilebox";
      box.parentNode.insertBefore(shell, box);
      shell.appendChild(box);
    }
    var old = shell.querySelector(".sf-chart-controls");
    if (old && old.parentNode) old.parentNode.removeChild(old);
    return shell;
  }

  // Attach the Mission-Control-style control row: ⛶ Enlarge (tile-expand → tile-expanded),
  // ▦ Data (tile-data → show-data), and — for multi-file charts — a ‹ Prev / ▶ Play / Next ›
  // stepper (one FILE per frame) with the provenance label. Play honors
  // prefers-reduced-motion (one frame per press, no timer); the master "Play all" clicks
  // every .sf-frame-next so the animations advance in lockstep.
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
    var idx = frames.n - 1; // start on the newest file
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

  // master "Play all / Step all" for the curves page (the mission.js pattern), appended to
  // the page's existing top control row once the steppers exist.
  function sfMasterBar() {
    if (SF_ON_WALL || document.getElementById("sfPlayAll")) return;
    if (!document.querySelector(".sf-frame-next")) return; // nothing to animate (one file)
    var hide = document.getElementById("curvesHideDone");
    var row = hide && hide.closest ? hide.closest(".viz-controls") : null;
    if (!row) return;
    function mkBtn(id, text) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = id;
      b.textContent = text;
      row.appendChild(b);
      return b;
    }
    var play = mkBtn("sfPlayAll", "▶ Play all");
    var stepBtn = mkBtn("sfStepAll", "⏭ Step all");
    var timer = null;
    function stepAll() {
      Array.prototype.forEach.call(
        document.querySelectorAll(".sf-frame-next"),
        function (b) { b.click(); }
      );
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
  }

  // E: a clickable, keyboard-operable show/hide legend for the overlaid line families. Each entry
  // is a real <button> (native keyboard + focus-ring), toggling its line's visibility; with many
  // series a Show-all / Hide-all pair lets you isolate one version from the clutter.
  function buildLegend(series, lines) {
    var shown = series.map(function () { return true; });
    var items = [];
    function apply() {
      lines.forEach(function (pl, i) {
        pl.style.display = shown[i] ? "" : "none";
        items[i].setAttribute("aria-pressed", shown[i] ? "true" : "false");
        items[i].classList.toggle("off", !shown[i]);
      });
    }
    var wrap = document.createElement("div");
    wrap.className = "curve-legend";
    series.forEach(function (s, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "curve-legend-item";
      btn.title = "Show / hide " + s.label;
      var sw = document.createElement("span");
      sw.className = "curve-swatch";
      sw.style.borderTopColor = s.color;
      sw.style.borderTopStyle = s.dashed ? "dashed" : "solid";
      btn.appendChild(sw);
      btn.appendChild(document.createTextNode(s.label));
      btn.addEventListener("click", function () { shown[i] = !shown[i]; apply(); });
      items.push(btn);
      wrap.appendChild(btn);
    });
    if (series.length > 2) {
      var ctrl = document.createElement("span");
      ctrl.className = "curve-legend-ctrl";
      [["Show all", true], ["Hide all", false]].forEach(function (pair) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "sf-link";
        b.textContent = pair[0];
        b.addEventListener("click", function () {
          for (var i = 0; i < shown.length; i++) shown[i] = pair[1];
          apply();
        });
        ctrl.appendChild(b);
      });
      wrap.appendChild(ctrl);
    }
    apply();
    return wrap;
  }

  // One month-axis line chart. series = [{values, color, dashed, label}]. statusIndex
  // (optional) draws a dashed data-date marker. Renders into the given container element.
  // lockTop (optional) pins the count axis to a caller-computed maximum so it stays FIXED
  // across animation frames (movement between files is real movement, never a rescale).
  function lineChart(box, months, series, statusIndex, name, lockTop) {
    if (!box) return;
    box.innerHTML = "";
    var W = 980, H = 320, padL = 36, padR = 14, padB = 18;
    var n = months.length;
    var slot = (n <= 1) ? (W - padL - padR) : (W - padL - padR) / (n - 1);
    var x = function (i) { return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1)); };
    // stacked Year/Quarter/Month time-tier header at the top; padT grows with the tier count
    var TIER_TOP = 8, ROW_H = 16;
    var padT = TIER_TOP + SFTimeAxis.tiersFor(months, gran).length * ROW_H + 8;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var top = lockTop || 1;
    series.forEach(function (s) {
      s.values.forEach(function (v) { if (v > top) top = v; });
    });
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };
    SFTimeAxis.draw(svg, { months: months, xOf: x, slot: slot, padL: padL, rightPx: W - padR,
      top: TIER_TOP, rowH: ROW_H, gran: gran });

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

    // (month/quarter/year scale is the stacked tier header drawn above the plot)

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

    // the lines — keep a ref per series so the legend can show/hide each
    var lines = series.map(function (s) {
      var pts = s.values.map(function (v, idx) { return x(idx) + "," + y(v); });
      var attrs = { points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2, pathLength: "1" };
      if (s.dashed) attrs["stroke-dasharray"] = "5 4";
      else attrs["class"] = "sf-curve-line";  // solid lines can draw-in on the Mission Control wall
      var pl = svgEl("polyline", attrs);
      svg.appendChild(pl);
      return pl;
    });

    // per-point hover call-outs: a transparent per-month hit-strip over the plot, each a <title>
    // listing every series' value at that month (read by the shared chartframe tooltip). The
    // lines are polylines with no per-point shapes, so the strips give the chart real hover data.
    for (var hi = 0; hi < n; hi++) {
      var hx = (n <= 1) ? padL : x(hi) - slot / 2;
      var hw = (n <= 1) ? (W - padL - padR) : slot;
      if (hx < padL) { hw -= padL - hx; hx = padL; }
      if (hx + hw > W - padR) hw = (W - padR) - hx;
      var strip = svgEl("rect", {
        x: hx, y: padT, width: Math.max(hw, 1), height: (H - padB) - padT, fill: "transparent",
      });
      var rows = [months[hi]];
      series.forEach(function (s) {
        rows.push(s.label + ": " + Math.round(s.values[hi] * 100) / 100);
      });
      var ttl = svgEl("title", {});
      ttl.textContent = rows.join("\n");
      strip.appendChild(ttl);
      svg.appendChild(strip);
    }

    if (window.SFA11y) SFA11y.label(svg, name || "Chart");
    box.appendChild(svg);
    // E: the clickable, keyboard-operable show/hide legend (replaces the old static in-SVG one)
    box.appendChild(buildLegend(series, lines));
    // A3: a visually-hidden data-table fallback so screen readers can read the numbers
    if (window.SFA11y) {
      var headers = ["Month"].concat(series.map(function (s) { return s.label; }));
      var trows = months.map(function (m, i) {
        return [m].concat(series.map(function (s) { return s.values[i]; }));
      });
      box.appendChild(SFA11y.table((name || "Chart") + " — data", headers, trows));
    }
  }

  function render(data) {
    lastData = data;
    var months = data.months;
    var versions = data.versions;
    if (!versions || !versions.length) {
      ["finishesChart", "dataDateChart", "slippageChart"].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.textContent = "No activities to plot — try showing completed work.";
      });
      return;
    }
    var labels = shortLabels(versions);
    var nV = versions.length;
    function fname(k) { return versions[k].label; }
    function fdate(k) { return versions[k].status_date; }

    // ── Finishes (latest version): actual vs baseline ──────────────────────────
    var latest = versions[versions.length - 1];
    var finBox = document.getElementById("finishesChart");
    var finShell = sfShell(finBox);
    lineChart(
      finBox,
      months,
      [
        { values: latest.baseline_finishes, color: GOLD, label: "Baseline finishes" },
        { values: latest.actual_finishes, color: BLUE, label: "Actual / scheduled finishes" },
      ],
      latest.status_index,
      "Finishes — actual vs baseline finishes by month"
    );
    if (finShell) {
      sfChartControls(finShell, function (bar) { finShell.insertBefore(bar, finBox); }, {
        data: !!window.SFA11y,
        source: { name: latest.label, date: latest.status_date },
      });
    }

    // ── DATA Date Finishes: ONE FILE PER FRAME on the fixed month/count axes ────
    var ddBox = document.getElementById("dataDateChart");
    var ddShell = sfShell(ddBox);
    var ddTop = 1; // count axis locked to the tallest point of EVERY file
    versions.forEach(function (v) {
      v.actual_finishes.forEach(function (c) { if (c > ddTop) ddTop = c; });
    });
    function ddDraw(k) {
      lineChart(ddBox, months,
        [{ values: versions[k].actual_finishes, color: PALETTE[k % PALETTE.length], label: labels[k] }],
        nV >= 2 ? versions[k].status_index : null,
        "Data-date finishes — actual-finish curve per version (one file per frame)",
        ddTop);
    }
    if (ddShell && nV >= 2) {
      sfChartControls(ddShell, function (bar) { ddShell.insertBefore(bar, ddBox); }, {
        data: !!window.SFA11y,
        frames: { n: nV, name: fname, date: fdate, draw: ddDraw },
      });
    } else {
      ddDraw(nV - 1); // single version: the curve shows that version alone (classic view)
      if (ddShell) {
        sfChartControls(ddShell, function (bar) { ddShell.insertBefore(bar, ddBox); }, {
          data: !!window.SFA11y,
          source: { name: versions[nV - 1].label, date: versions[nV - 1].status_date },
        });
      }
    }

    // ── Slippage: ONE FILE PER FRAME — start (solid) + finish (dashed) curves ───
    var slBox = document.getElementById("slippageChart");
    var slShell = sfShell(slBox);
    var slTop = 1; // count axis locked across every file's start AND finish curves
    versions.forEach(function (v) {
      v.actual_starts.concat(v.actual_finishes).forEach(function (c) { if (c > slTop) slTop = c; });
    });
    function slDraw(k) {
      var col = PALETTE[k % PALETTE.length];
      lineChart(slBox, months,
        [
          { values: versions[k].actual_starts, color: col, label: labels[k] + " starts" },
          { values: versions[k].actual_finishes, color: col, dashed: true, label: labels[k] + " finishes" },
        ],
        nV >= 2 ? versions[k].status_index : null,
        "Slippage — start and finish curves per version (one file per frame)",
        slTop);
    }
    if (slShell && nV >= 2) {
      sfChartControls(slShell, function (bar) { slShell.insertBefore(bar, slBox); }, {
        data: !!window.SFA11y,
        frames: { n: nV, name: fname, date: fdate, draw: slDraw },
      });
    } else {
      slDraw(nV - 1); // single version: the classic start/finish pair for that file
      if (slShell) {
        sfChartControls(slShell, function (bar) { slShell.insertBefore(bar, slBox); }, {
          data: !!window.SFA11y,
          source: { name: versions[nV - 1].label, date: versions[nV - 1].status_date },
        });
      }
    }

    // master Play all / Step all (injected once, after the steppers exist)
    sfMasterBar();
  }

  // ?hide_complete=1 drops 100%-complete activities so the curves show only remaining/forecast work
  function load() {
    var hide = document.getElementById("curvesHideDone");
    fetch("/api/curves" + (hide && hide.checked ? "?hide_complete=1" : ""))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(render)
      .catch(function () {
        ["finishesChart", "dataDateChart", "slippageChart"].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.textContent = "Failed to load the curve data.";
        });
      });
  }

  var hideEl = document.getElementById("curvesHideDone");
  if (hideEl) hideEl.addEventListener("change", load);
  var granEl = document.getElementById("curvesGran");
  if (granEl) granEl.addEventListener("change", function () {
    gran = granEl.value;
    if (lastData) render(lastData);  // re-draw with the new granularity (no re-fetch needed)
  });
  load();
})();
