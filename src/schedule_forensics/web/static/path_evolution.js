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
 *
 * Each row also carries grid columns beside the bar — % complete, duration (working days),
 * start and finish — with the activity name wrapped small (no longer truncated). A
 * "hide completed" toggle drops finished activities, using the robust complete flag
 * (≥100% OR an actual finish — ADR-0051), so a real .mpp/.xer reporting 99.x% still hides.
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

  var data = null, index = 0, timer = null, lo = 0, hi = 1, hideDone = false;

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

  // wrap a name into <=maxLines lines of <=perLine chars (word-aware; last line ellipsized)
  function wrapName(name, perLine, maxLines) {
    var words = String(name || "").split(/\s+/), lines = [], cur = "";
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!cur) cur = w;
      else if ((cur + " " + w).length <= perLine) cur += " " + w;
      else { lines.push(cur); cur = w; if (lines.length === maxLines - 1) break; }
    }
    if (cur && lines.length < maxLines) lines.push(cur);
    // any words left after the line budget → ellipsize the final line
    if (lines.length === maxLines) {
      var consumed = lines.join(" ").length;
      if (consumed < String(name || "").length) lines[maxLines - 1] = clip(lines[maxLines - 1] + " …", perLine);
    }
    return lines.length ? lines : [""];
  }
  function fmtDate(iso) { return iso ? String(iso) : "—"; }

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

  // column layout: a left grid (name + %/dur/start/finish), then the Gantt plot, then the chip
  var COL = { name: 6, pct: 300, dur: 348, start: 360, finish: 432, plotL: 512 };

  // rows: [{uid, name, start, finish, kind, durBadge, reason, detail, percent_complete, duration, complete}]
  function gantt(rows) {
    var wrap = el("div", "evo-gantt");
    if (!rows.length) { wrap.appendChild(el("p", "muted", "—")); return wrap; }
    var W = 1180, rowH = 30, padT = 46, padB = 8, plotL = COL.plotL, plotR = W - 130;
    var H = padT + rows.length * rowH + padB;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var x = function (ms) { return plotL + ((ms - lo) / (hi - lo)) * (plotR - plotL); };

    function colText(xx, yy, s, opts) {
      opts = opts || {};
      var t = svgEl("text", { x: xx, y: yy, "font-size": opts.size || 10, fill: opts.fill || "var(--ink)" });
      if (opts.anchor) t.setAttribute("text-anchor", opts.anchor);
      t.textContent = s;
      svg.appendChild(t);
      return t;
    }

    // header row: column titles + the locked axis gridlines/years
    colText(COL.name, padT - 26, "Activity", { fill: "var(--muted)" });
    colText(COL.pct, padT - 26, "%", { fill: "var(--muted)", anchor: "end" });
    colText(COL.dur, padT - 26, "Dur", { fill: "var(--muted)", anchor: "end" });
    colText(COL.start, padT - 26, "Start", { fill: "var(--muted)" });
    colText(COL.finish, padT - 26, "Finish", { fill: "var(--muted)" });
    var d = new Date(lo); d.setMonth(0, 1); d.setHours(0, 0, 0, 0);
    while (d.getTime() <= hi) {
      var tx = x(d.getTime());
      if (tx >= plotL) {
        svg.appendChild(svgEl("line", { x1: tx, y1: padT - 12, x2: tx, y2: H - padB, stroke: "var(--line)", "stroke-width": 1 }));
        colText(tx + 2, padT - 15, d.getFullYear(), { fill: "var(--muted)" });
      }
      d.setFullYear(d.getFullYear() + 1);
    }
    svg.appendChild(svgEl("line", { x1: COL.name, y1: padT - 8, x2: W, y2: padT - 8, stroke: "var(--line)", "stroke-width": 1 }));

    rows.forEach(function (r, i) {
      var top = padT + i * rowH, cy = top + rowH / 2;
      var labelColor = r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--ink)";

      // name wrapped to <=2 small lines, prefixed with the UID; struck through if it left
      var lines = wrapName(r.name, 38, 2);
      var nameTop = cy - (lines.length - 1) * 5 - 2;
      var lab = svgEl("text", { x: COL.name, y: nameTop, "font-size": 10, fill: labelColor });
      if (r.kind === "left") lab.setAttribute("text-decoration", "line-through");
      lines.forEach(function (ln, li) {
        var ts = svgEl("tspan", { x: COL.name, dy: li === 0 ? 0 : 11 });
        ts.textContent = (li === 0 ? "U" + r.uid + " · " : "") + ln;
        lab.appendChild(ts);
      });
      svg.appendChild(lab);

      // grid columns: % complete, duration, start, finish
      if (r.percent_complete != null) colText(COL.pct, cy + 3, r.percent_complete + "%", { anchor: "end", fill: "var(--muted)" });
      if (r.duration) colText(COL.dur, cy + 3, r.duration, { anchor: "end", fill: "var(--muted)" });
      colText(COL.start, cy + 3, fmtDate(r.start), { size: 9, fill: "var(--muted)" });
      colText(COL.finish, cy + 3, fmtDate(r.finish), { size: 9, fill: "var(--muted)" });

      if (r.start && r.finish) {
        var x1 = x(Date.parse(r.start)), x2 = x(Date.parse(r.finish));
        var bw = Math.max(2, x2 - x1);
        var barColor = r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--accent)";
        var rect = svgEl("rect", { x: x1, y: cy - 6, width: bw, height: 12, rx: 2, fill: barColor });
        if (r.kind === "left") { rect.setAttribute("opacity", "0.45"); rect.setAttribute("stroke-dasharray", "3 2"); }
        svg.appendChild(rect);
        if (r.durBadge) colText(x2 + 3, cy + 4, "▲", { size: 11, fill: "var(--warn)" });
      }

      if (r.reason && REASON[r.reason]) {
        var rc = REASON[r.reason];
        var t = colText(plotR + 8, cy + 4, rc.label, { fill: rc.color });
        if (r.detail) { var ti = svgEl("title", {}); ti.textContent = r.detail; t.appendChild(ti); }
      }
    });
    wrap.appendChild(svg);
    return wrap;
  }

  function carry(r, extra) {
    var o = {
      uid: r.uid, name: r.name, start: r.start, finish: r.finish,
      percent_complete: r.percent_complete, duration: r.duration, complete: r.complete,
    };
    for (var k in extra) o[k] = extra[k];
    return o;
  }
  function currentRows(snap) {
    return snap.critical_rows.map(function (r) {
      return carry(r, {
        kind: r.entered ? "entered" : "stayed",
        durBadge: r.duration_changed, reason: r.entered ? r.reason : null, detail: r.detail,
      });
    });
  }
  function leftRows(snap) {
    return snap.left_rows.map(function (r) {
      return carry(r, { kind: "left", durBadge: false, reason: r.reason, detail: r.detail });
    });
  }
  function visible(rows) { return hideDone ? rows.filter(function (r) { return !r.complete; }) : rows; }

  function render() {
    var snap = data.snapshots[index];
    document.getElementById("evoLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label +
      (snap.status_date ? " (data date " + snap.status_date + ")" : "");
    box.innerHTML = "";
    box.appendChild(callout(snap));
    box.appendChild(legend());
    var crit = visible(currentRows(snap));
    var hidden = snap.critical_rows.length - crit.length;
    box.appendChild(el("h3", null, "Critical path — " + crit.length + " activities" +
      (hidden > 0 ? " (" + hidden + " completed hidden)" : "")));
    box.appendChild(gantt(crit));
    var leftV = visible(leftRows(snap));
    if (leftV.length) {
      box.appendChild(el("h3", null, "Left the critical path (" + leftV.length + ") — where they were, and why"));
      box.appendChild(gantt(leftV));
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
      var hd = document.getElementById("evoHideDone");
      if (hd) hd.addEventListener("change", function () { hideDone = hd.checked; render(); });
    })
    .catch(function () { box.textContent = "Failed to load the path-evolution data."; });
})();
