/* Schedule Forensics — schedule-margin burndown across versions (Trend page).
 *
 * Dependency-free SVG (no CDN — air-gap posture, same-origin only). Two lines over the loaded
 * versions on one LOCKED y-axis (working days): TOTAL margin (var(--accent)) = the buffer nominally
 * in the schedule; EFFECTIVE margin (var(--ok)) = the buffer actually protecting the finish. The
 * x-axis is each version's data date (fallback v1, v2 …), so a buffer being spent or quietly removed
 * reads as a falling line left to right. Data: local /api/margin.
 *
 * Trends-animation package: the chart carries Mission-Control-style controls — ⛶ Enlarge and
 * ▦ Data toggles plus (with 2+ files) a ‹ Prev / ▶ Play / Next › stepper that progressively
 * reveals the versions on the LOCKED axes, with a "file X of N — name (data date …)" provenance
 * label. Reduced motion is honored; the page's master "Play all" clicks .sf-frame-next in lockstep.
 */
"use strict";

(function () {
  var box = document.getElementById("marginBurndown");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var TOTAL = "var(--accent)", EFFECTIVE = "var(--ok)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function xLabels(versions) {
    return versions.map(function (v, i) { return v.status_date || "v" + (i + 1); });
  }

  // ── Trends-animation package: Mission-Control-style per-chart controls ────────
  var SF_REDUCED =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SF_ON_WALL = !!document.getElementById("missionGrid");

  function sfCaption(k, n, name, date) {
    var src = String(name || "v" + (k + 1)) + (date ? " (data date " + date + ")" : "");
    return n > 1 ? "file " + (k + 1) + " of " + n + " — " + src : "Source: " + src;
  }

  // shell around the host so the control row + expand/data state survive per-frame re-renders
  function sfShell(host) {
    if (!host || !host.parentNode) return null;
    var shell =
      host.parentNode.classList && host.parentNode.classList.contains("sf-tilebox")
        ? host.parentNode
        : null;
    if (!shell) {
      shell = document.createElement("div");
      shell.className = "sf-tilebox";
      host.parentNode.insertBefore(shell, host);
      shell.appendChild(host);
    }
    var old = shell.querySelector(".sf-chart-controls");
    if (old && old.parentNode) old.parentNode.removeChild(old);
    return shell;
  }

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

  function draw(versions) {
    var shell = sfShell(box);
    var labels = xLabels(versions);
    var totals = versions.map(function (v) { return v.total; });
    var effectives = versions.map(function (v) { return v.effective; });

    var W = 980, H = 320, padL = 40, padR = 14, padT = 24, padB = 50;
    var n = versions.length;
    // LOCKED y-axis: the tallest of either line across EVERY version (min 1), so the two series
    // are directly comparable and the axis never rescales between animation frames.
    var top = 1;
    totals.concat(effectives).forEach(function (v) { if (v > top) top = v; });
    var x = function (i) { return padL + (n <= 1 ? (W - padL - padR) / 2 : (i * (W - padL - padR)) / (n - 1)); };
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };

    // one frame of the burndown: versions 0…k revealed on the locked axes
    function frame(k) {
      box.innerHTML = "";
      var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });

      // y gridlines + working-day labels
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
      var unit = svgEl("text", { x: padL - 6, y: padT - 8, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
      unit.textContent = "working days";
      svg.appendChild(unit);

      // x (version) labels, thinned to avoid overlap, rotated for legibility — the version
      // axis is drawn in full every frame (LOCKED), so movement is visible frame to frame
      var step = Math.max(1, Math.ceil(n / 16));
      for (var i = 0; i < n; i++) {
        if (i % step === 0) {
          var ml = svgEl("text", {
            x: x(i), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
            transform: "rotate(-35 " + x(i) + " " + (H - padB + 16) + ")",
          });
          ml.textContent = labels[i];
          svg.appendChild(ml);
        }
      }

      // the two lines + a marker per point, revealed up to version k
      [
        { values: totals, color: TOTAL },
        { values: effectives, color: EFFECTIVE },
      ].forEach(function (s) {
        var pts = [];
        s.values.forEach(function (v, idx) { if (idx <= k) pts.push(x(idx) + "," + y(v)); });
        svg.appendChild(svgEl("polyline", {
          points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2,
          "class": "sf-curve-line",
        }));
        s.values.forEach(function (v, idx) {
          if (idx > k) return;
          svg.appendChild(svgEl("circle", { cx: x(idx), cy: y(v), r: idx === k ? 4 : 3, fill: s.color }));
        });
      });
      // the current frame's version, marked on the locked axis
      if (n > 1) {
        svg.appendChild(svgEl("line", {
          x1: x(k), y1: padT, x2: x(k), y2: H - padB, stroke: "var(--focus)",
          "stroke-width": 1.5, "stroke-dasharray": "3 3", "class": "sf-frame-guide",
        }));
      }

      // legend
      var legend = [["Total margin", TOTAL], ["Effective margin", EFFECTIVE]];
      var lx = padL;
      legend.forEach(function (item) {
        svg.appendChild(svgEl("line", { x1: lx, y1: H - 6, x2: lx + 16, y2: H - 6, stroke: item[1], "stroke-width": 3 }));
        var lt = svgEl("text", { x: lx + 20, y: H - 2, fill: "var(--muted)", "font-size": 11 });
        lt.textContent = item[0];
        svg.appendChild(lt);
        lx += 20 + item[0].length * 6 + 24;
      });

      if (window.SFA11y) SFA11y.label(svg, "Schedule margin burndown — total vs effective margin by version");
      box.appendChild(svg);

      // A11y (WCAG 1.1.1): a visually-hidden data table of the numbers the lines draw —
      // always the FULL series, whatever frame is showing (the Data toggle reveals it).
      if (window.SFA11y) {
        box.appendChild(SFA11y.table(
          "Schedule margin burndown — total and effective margin (working days) by version",
          ["Version", "Total wd", "Effective wd"],
          versions.map(function (v, i) { return [labels[i], v.total, v.effective]; })
        ));
      }
    }

    var frames = n >= 2
      ? {
          n: n,
          name: function (k) { return versions[k].label; },
          date: function (k) { return versions[k].status_date; },
          draw: frame,
        }
      : null;
    if (!frames) frame(n - 1);
    if (shell) {
      sfChartControls(shell, function (bar) { shell.insertBefore(bar, box); }, {
        data: !!window.SFA11y,
        frames: frames,
        source: n === 1 ? { name: versions[0].label, date: versions[0].status_date } : null,
      });
    } else if (frames) frame(n - 1);
  }

  fetch("/api/margin")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var versions = data.versions || [];
      if (!versions.length) { box.textContent = "No data."; return; }
      var anyMargin = versions.some(function (v) { return v.total || v.effective; });
      if (!anyMargin) {
        var note = document.createElement("p");
        note.className = "muted";
        note.textContent = "No schedule-margin tasks (named 'margin') in any loaded version.";
        box.innerHTML = "";
        box.appendChild(note);
        return;
      }
      draw(versions);
    })
    .catch(function () { box.textContent = "Failed to load the schedule-margin data."; });
})();
