/* Schedule Forensics — Critical-Path Evolution Gantt stepper (M18 item 7 + follow-up).
 *
 * Dependency-free SVG (no CDN — air-gap posture). A Prev/Next/Auto-play stepper over
 * /api/evolution: each frame draws one version's critical path as a Gantt on a LOCKED date
 * axis (held fixed across every version so the path visibly extends as the finish slips).
 * Activities that ENTERED the path are green, those that STAYED grey, and a ▲ marks a
 * duration change; activities that LEFT the path are drawn below as dashed/struck ghost bars
 * at their prior position. Every entered/left activity carries a reason chip explaining WHY
 * it moved (new task / duration change / logic change / constraint / slip / completed) — hover
 * for the detail.
 */
"use strict";

(function () {
  var box = document.getElementById("evoChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var DAY = 86400000;

  // reason code -> { short label, theme color }
  var REASON = {
    new: { label: "new task", color: "var(--ok)" },
    duration_up: { label: "duration ↑", color: "var(--warn)" },
    duration_down: { label: "duration ↓", color: "var(--warn)" },
    constraint: { label: "constraint", color: "var(--warn)" },
    logic_added: { label: "logic added", color: "var(--accent)" },
    logic_removed: { label: "logic removed", color: "var(--bad)" },
    slack_consumed: { label: "slip elsewhere", color: "var(--muted)" },
    completed: { label: "completed", color: "var(--ok)" },
    removed: { label: "removed", color: "var(--bad)" },
    gained_float: { label: "gained float", color: "var(--muted)" },
  };

  var data = null, index = 0, timer = null, lo = 0, hi = 1;

  function svgEl(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        n.style[k] = attrs[k];
      } else n.setAttribute(k, attrs[k]);
    }
    return n;
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function clip(s, n) { s = String(s || ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; }

  function callout(snap) {
    var c = el("div", "ev-callout");
    var move = snap.finish_delta_days;
    var moveText = move == null ? "" :
      move > 0 ? " (slipped " + move + "d)" :
      move < 0 ? " (pulled in " + (-move) + "d)" : " (no move)";
    c.appendChild(el("span", "ev-finish", "Project finish: " + snap.project_finish + moveText));
    var sig = el("span", "ev-signals");
    var bits = [
      snap.entered.length + " entered",
      snap.left.length + " left",
      snap.duration_changed.length + " duration-changed on path",
    ];
    if (snap.shortened_on_path.length) bits.push(snap.shortened_on_path.length + " shortened on path");
    if (snap.removed_logic_count) bits.push(snap.removed_logic_count + " logic links removed");
    sig.textContent = bits.join(" · ");
    if ((snap.shortened_on_path.length || snap.removed_logic_count || snap.left.length) &&
        move != null && move <= 0) {
      sig.classList.add("ev-flag");
    }
    c.appendChild(sig);
    return c;
  }

  function legend() {
    var wrap = el("div", "legend");
    [["ev-entered", "entered the path"], ["ev-stayed", "stayed"], ["ev-left", "left the path"]]
      .forEach(function (p) { wrap.appendChild(el("span", p[0], p[1])); });
    wrap.appendChild(el("span", "ev-stayed", "▲ duration change · hover a reason for detail"));
    return wrap;
  }

  // rows: [{uid, name, start, finish, kind:"entered"|"stayed"|"left", durBadge, reason, detail}]
  function gantt(rows) {
    var wrap = el("div", "evo-gantt");
    if (!rows.length) { wrap.appendChild(el("p", "muted", "—")); return wrap; }
    var W = 980, rowH = 20, padT = 34, padB = 8, plotL = 322, plotR = W - 150;
    var H = padT + rows.length * rowH + padB;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var x = function (ms) { return plotL + ((ms - lo) / (hi - lo)) * (plotR - plotL); };

    // year gridlines across the locked axis
    var d = new Date(lo); d.setMonth(0, 1); d.setHours(0, 0, 0, 0);
    while (d.getTime() <= hi) {
      var tx = x(d.getTime());
      if (tx >= plotL) {
        svg.appendChild(svgEl("line", { x1: tx, y1: padT - 12, x2: tx, y2: H - padB, stroke: "var(--line)", "stroke-width": 1 }));
        var yl = svgEl("text", { x: tx + 2, y: padT - 15, fill: "var(--muted)", "font-size": 10 });
        yl.textContent = d.getFullYear();
        svg.appendChild(yl);
      }
      d.setFullYear(d.getFullYear() + 1);
    }

    rows.forEach(function (r, i) {
      var cy = padT + i * rowH + rowH / 2;
      var labelColor = r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--ink)";
      var lab = svgEl("text", { x: 6, y: cy + 4, "font-size": 11, fill: labelColor });
      lab.textContent = "UID " + r.uid + "  " + clip(r.name, 30);
      if (r.kind === "left") lab.setAttribute("text-decoration", "line-through");
      svg.appendChild(lab);

      if (r.start && r.finish) {
        var x1 = x(Date.parse(r.start)), x2 = x(Date.parse(r.finish));
        var bw = Math.max(2, x2 - x1);
        var barColor = r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--accent)";
        var rect = svgEl("rect", { x: x1, y: cy - 6, width: bw, height: 12, rx: 2, fill: barColor });
        if (r.kind === "left") { rect.setAttribute("opacity", "0.45"); rect.setAttribute("stroke-dasharray", "3 2"); }
        svg.appendChild(rect);
        if (r.durBadge) {
          var b = svgEl("text", { x: x2 + 3, y: cy + 4, "font-size": 11, fill: "var(--warn)" });
          b.textContent = "▲";
          svg.appendChild(b);
        }
      }

      if (r.reason && REASON[r.reason]) {
        var rc = REASON[r.reason];
        var t = svgEl("text", { x: plotR + 8, y: cy + 4, "font-size": 10, fill: rc.color });
        t.textContent = rc.label;
        if (r.detail) { var ti = svgEl("title", {}); ti.textContent = r.detail; t.appendChild(ti); }
        svg.appendChild(t);
      }
    });
    wrap.appendChild(svg);
    return wrap;
  }

  function currentRows(snap) {
    return snap.critical_rows.map(function (r) {
      return {
        uid: r.uid, name: r.name, start: r.start, finish: r.finish,
        kind: r.entered ? "entered" : "stayed",
        durBadge: r.duration_changed, reason: r.entered ? r.reason : null, detail: r.detail,
      };
    });
  }
  function leftRows(snap) {
    return snap.left_rows.map(function (r) {
      return {
        uid: r.uid, name: r.name, start: r.start, finish: r.finish,
        kind: "left", durBadge: false, reason: r.reason, detail: r.detail,
      };
    });
  }

  function render() {
    var snap = data.snapshots[index];
    document.getElementById("evoLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label +
      (snap.status_date ? " (data date " + snap.status_date + ")" : "");
    box.innerHTML = "";
    box.appendChild(callout(snap));
    box.appendChild(legend());
    box.appendChild(el("h3", null, "Critical path — " + snap.critical_rows.length + " activities"));
    box.appendChild(gantt(currentRows(snap)));
    if (snap.left_rows.length) {
      box.appendChild(el("h3", null, "Left the critical path (" + snap.left_rows.length + ") — where they were, and why"));
      box.appendChild(gantt(leftRows(snap)));
    }
  }

  function step(delta) {
    index = (index + delta + data.snapshots.length) % data.snapshots.length;
    render();
  }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("evoPlay").textContent = "▶ Auto-play";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    document.getElementById("evoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1800);
  }

  fetch("/api/evolution")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      if (d.axis && d.axis.min && d.axis.max) {
        lo = Date.parse(d.axis.min); hi = Date.parse(d.axis.max);
        if (!(hi > lo)) hi = lo + 30 * DAY;
        var pad = (hi - lo) * 0.04;
        lo -= pad; hi += pad;
      }
      render();
      document.getElementById("prevEvo").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("nextEvo").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("evoPlay").addEventListener("click", toggleAuto);
    })
    .catch(function () { box.textContent = "Failed to load the path-evolution data."; });
})();
