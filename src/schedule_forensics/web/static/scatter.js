/* Schedule Forensics — activity scatter plot (handbook §6.3.2.5.2.1; assessment-deck visual).
 *
 * Dependency-free SVG (no CDN — air-gap posture). One dot per non-summary activity: Total Float
 * (x, working days) against Duration (y, working days), red = critical, diamond = milestone. The
 * bottom-left (long duration, little float) is where the schedule's pressure points hide — a
 * pattern no count metric reveals. Data: the local /api/analysis/<name> endpoint (the activity
 * rows the grid already uses); the page's full activity grid is the accessible data table.
 *
 * Trends-animation package: the plot carries the Mission-Control tile conventions — a
 * ⛶ Enlarge toggle (tile-expand → tile-expanded) and a visible provenance label naming the
 * schedule it draws from (the host's data-name, the same key it fetches).
 */
"use strict";

(function () {
  var box = document.getElementById("scatterChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";

  // ── Mission-Control-style Enlarge + provenance (Trends-animation package) ────
  function sfControls(host, name) {
    if (!host || !host.parentNode) return;
    var shell = document.createElement("div");
    shell.className = "sf-tilebox";
    host.parentNode.insertBefore(shell, host);
    shell.appendChild(host);
    var bar = document.createElement("div");
    bar.className = "viz-controls sf-chart-controls";
    var big = document.createElement("button");
    big.type = "button";
    big.className = "tile-expand";
    big.textContent = "⛶ Enlarge";
    big.title = "Enlarge / shrink this chart";
    big.setAttribute("aria-pressed", "false");
    big.addEventListener("click", function (e) {
      e.stopPropagation();
      var on = shell.classList.toggle("tile-expanded");
      big.setAttribute("aria-pressed", on ? "true" : "false");
      big.textContent = on ? "⛶ Shrink" : "⛶ Enlarge";
      if (on && shell.scrollIntoView) shell.scrollIntoView({ block: "nearest" });
    });
    bar.appendChild(big);
    var label = document.createElement("span");
    label.className = "sf-frame-label muted";
    label.setAttribute("data-no-i18n", ""); // the schedule name — never machine-translated
    label.textContent = "Source: " + name;
    bar.appendChild(label);
    shell.insertBefore(bar, host);
  }

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function render(pts) {
    box.innerHTML = "";
    var W = 940, H = 420, padL = 50, padR = 16, padT = 18, padB = 46;
    var xs = pts.map(function (p) { return p.x; });
    var ys = pts.map(function (p) { return p.y; });
    var xMax = Math.max.apply(null, xs), xMin = Math.min(0, Math.min.apply(null, xs));
    if (xMax === xMin) xMax = xMin + 1;
    var yMax = Math.max(1, Math.max.apply(null, ys));
    var x = function (v) { return padL + ((v - xMin) / (xMax - xMin)) * (W - padL - padR); };
    var y = function (v) { return padT + (1 - v / yMax) * (H - padT - padB); };

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "Activity scatter — total float versus duration");

    // y gridlines + labels
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var gy = y(yMax * f);
      svg.appendChild(svgEl("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1 }));
      var lab = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
      lab.textContent = String(Math.round(yMax * f));
      svg.appendChild(lab);
    });
    // x gridlines + labels
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var vx = xMin + (xMax - xMin) * f, gx = x(vx);
      svg.appendChild(svgEl("line", { x1: gx, y1: padT, x2: gx, y2: H - padB, stroke: "var(--line)", "stroke-width": 1 }));
      var lab = svgEl("text", { x: gx, y: H - padB + 14, "text-anchor": "middle", fill: "var(--muted)", "font-size": 10 });
      lab.textContent = String(Math.round(vx));
      svg.appendChild(lab);
    });
    // zero-float reference line (the critical boundary), if 0 is in range
    if (xMin <= 0 && xMax >= 0) {
      var zx = x(0);
      svg.appendChild(svgEl("line", { x1: zx, y1: padT, x2: zx, y2: H - padB, stroke: "var(--warn)", "stroke-width": 1.5, "stroke-dasharray": "5 4" }));
      var zl = svgEl("text", { x: zx + 3, y: padT + 10, fill: "var(--warn)", "font-size": 10 });
      zl.textContent = "0 float";
      svg.appendChild(zl);
    }
    // axis titles
    var xt = svgEl("text", { x: (padL + W - padR) / 2, y: H - 6, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11 });
    xt.textContent = "Total float (working days)";
    svg.appendChild(xt);
    var yt = svgEl("text", { x: 12, y: (padT + H - padB) / 2, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11, transform: "rotate(-90 12 " + (padT + H - padB) / 2 + ")" });
    yt.textContent = "Duration (working days)";
    svg.appendChild(yt);

    // dots: circle per activity (diamond for milestones), red when critical
    pts.forEach(function (p) {
      var cx = x(p.x), cy = y(p.y), col = p.crit ? "var(--bad)" : "var(--accent)";
      var node;
      if (p.ms) {
        var s = 4;
        node = svgEl("path", { d: "M" + cx + " " + (cy - s) + " L" + (cx + s) + " " + cy + " L" + cx + " " + (cy + s) + " L" + (cx - s) + " " + cy + " Z", fill: col, opacity: 0.85 });
      } else {
        node = svgEl("circle", { cx: cx, cy: cy, r: 3.2, fill: col, opacity: 0.65 });
      }
      var t = svgEl("title", {});
      t.textContent = "UID " + p.uid + (p.name ? " " + p.name : "") +
        " — float " + p.x + " wd, duration " + p.y + " wd" + (p.crit ? " (critical)" : "");
      node.appendChild(t);
      svg.appendChild(node);
    });
    box.appendChild(svg);

    var leg = document.createElement("div");
    leg.className = "chart-legend";
    [["Critical", "var(--bad)"], ["Non-critical", "var(--accent)"], ["◆ Milestone", "var(--muted)"]]
      .forEach(function (it) {
        var cell = document.createElement("span");
        cell.className = "chart-legend-item";
        var sw = document.createElement("span");
        sw.className = "chart-swatch";
        sw.style.background = it[1];
        cell.appendChild(sw);
        cell.appendChild(document.createTextNode(it[0]));
        leg.appendChild(cell);
      });
    box.appendChild(leg);
  }

  var name = box.getAttribute("data-name") || "";
  fetch("/api/analysis/" + encodeURIComponent(name))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      var pts = (d.activities || [])
        .filter(function (a) { return !a.is_summary; })
        .map(function (a) {
          return {
            x: a.total_float_days, y: a.duration_days, crit: a.is_critical,
            ms: a.is_milestone, uid: a.unique_id, name: a.name,
          };
        })
        .filter(function (p) { return p.x != null && p.y != null; });
      if (!pts.length) { box.textContent = "No activity data to plot."; return; }
      render(pts);
      sfControls(box, name || "current schedule"); // ⛶ Enlarge + "Source: <schedule>"
    })
    .catch(function () { box.textContent = "Failed to load the scatter data."; });
})();
